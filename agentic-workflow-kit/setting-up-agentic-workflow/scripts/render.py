#!/usr/bin/env python3
"""Render the agentic-workflow kit into a project: pick templates, apply line markers, fill placeholders, write configs.

Usage: python scripts/render.py --answers tasks/000-setup/answers.json --target <project dir> [--dry-run]
--dry-run prints the plan (file tree, config summaries, placeholders) and writes nothing. Otherwise it writes,
re-reads what it wrote (no {{NAME}}, no "<!-- if:", JSON parses) and, in a git repository's root, runs the installed
guard's `check`. It never overwrites: existing target files are listed and nothing is written (exit 1); .gitignore
gets missing lines, an existing .claude/settings.local.json missing hook events. Errors: stderr, exit 1. Python >= 3.9.

answers.json (every key required; keys starting with "_" are comments):
  level           "starter" | "standard" | "full"
  instructions    "claude" (CLAUDE.md) | "agents" (AGENTS.md + a CLAUDE.md that imports it)
  guard           true | false (false at starter)
  hooks_location  "shared" (hooks in .claude/settings.json) | "local" (in .claude/settings.local.json)
  os              "windows" | "macos" | "linux" (windows adds a PowerShell(...) twin to every Bash(...) rule)
  python_cmd      one executable, "python" or "python3": the command of the guard hooks
  values          {"PROJECT_NAME": "...", "PROJECT_PURPOSE", "PRODUCT_RULES", "STACK", "ENVIRONMENT", "TEST_COMMAND",
                   "LINT_COMMAND", "RUN_COMMAND", ...}: the {{NAME}} placeholders; "" is only allowed for *_COMMAND
  source_dirs     ["src"]  and  test_dirs ["tests"]: repo-relative folders, at least one each
  owned_paths     ["rates/*.csv"]: patterns added to the guard's protected list
  gitignore_extra ["__pycache__/"]: extra .gitignore lines
  mcp             {"context7": true, "playwright_version": "0.0.41"} ("" = no Playwright)
Derived: {{PYTHON_CMD}}, {{SOURCE_DIRS}} and {{TEST_DIRS}} ("`src/`, `lib/`"), {{OWNED_PATHS}}. An empty *_COMMAND
renders as "not set up yet"; backticks around a placeholder are dropped when its value is that or has backticks.
A Markdown line ending in markers `<!-- if:NAME -->` stays only if all hold (full; lite = starter or standard;
skills = standard or full; guard; noguard; agents-md; claude-only); the markers are then removed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parents[1] / "templates" / "project"
CHOICES = {"level": ("starter", "standard", "full"), "instructions": ("claude", "agents"),
           "hooks_location": ("shared", "local"), "os": ("windows", "macos", "linux")}
LISTS = ("source_dirs", "test_dirs", "owned_paths", "gitignore_extra")
KEYS = set(CHOICES) | set(LISTS) | {"guard", "python_cmd", "values", "mcp"}
DERIVED = {"PYTHON_CMD", "SOURCE_DIRS", "TEST_DIRS", "OWNED_PATHS"}
GENERATED = {"dot-claude/settings.json", "dot-claude/hooks/guard.config.json"}
JUNK = {"__pycache__", ".DS_Store", "Thumbs.db"}
NOT_SET = "not set up yet"
OWNED_WORDS = "agent setup files, CI workflows, deployment and infrastructure files"
GITIGNORE = [".env", ".env.*", "!.env.example", ".claude/settings.local.json"]
PLACEHOLDER = re.compile(r"(`?)\{\{([A-Z][A-Z0-9_]*)\}\}(`?)")
LEFTOVER = re.compile(r"\{\{[A-Z0-9_]+\}\}|<!-- if:")
MARKER, MARKER_TAIL = re.compile(r"<!-- if:(\S*) -->"), re.compile(r"(?:\s*<!-- if:\S* -->)+\s*$")
ONE_LINE, NPM, NBSP = re.compile(r"[^\r\n]*\S[^\r\n]*"), re.compile(r"^npm(?=\s|$)"), chr(160)
VERSION = re.compile(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?")
FOLDER = re.compile(r"(?!/)(?!(?:.*/)?\.{0,2}(?:/|$))[^\\*?\[]+")  # relative, no glob, no empty/./.. segment

class RenderError(Exception):
    """args[0] is the list of problems; they are printed one per line."""

def load_answers(path: Path) -> dict:
    try:
        a = json.loads(path.read_bytes().decode("utf-8-sig"))
    except (OSError, ValueError) as e:
        raise RenderError([f"answers file {path}: {e}"]) from e
    keys = {k for k in a if not k.startswith("_")} if isinstance(a, dict) else set()
    if keys != KEYS:
        raise RenderError([f"answers must be one JSON object with the keys {sorted(KEYS)}: missing "
                           f"{sorted(KEYS - keys)}, unknown {sorted(keys - KEYS)}"])
    v, m, owned = a["values"], a["mcp"], a["owned_paths"]
    ok = {k: isinstance(a[k], list) and all(isinstance(x, str) and ONE_LINE.fullmatch(x) for x in a[k]) for k in LISTS}
    checks = [(a[k] in allowed, k, f"one of {list(allowed)}") for k, allowed in CHOICES.items()]
    checks += [(ok[k], k, "a list of one-line strings") for k in LISTS] + [
        (not ok[k] or (a[k] and all(FOLDER.fullmatch(d.rstrip("/")) for d in a[k])), k,
         "at least one repo-relative folder like \"src\"")
        for k in ("source_dirs", "test_dirs")] + [
        (not ok["owned_paths"] or not any("\\" in x or x.startswith(("/", "./")) for x in owned), "owned_paths",
         "patterns with '/' like \"rates/*.csv\""),
        (isinstance(a["guard"], bool) and not (a["guard"] and a["level"] == "starter"), "guard",
         "true or false, and false at level starter"),
        (isinstance(a["python_cmd"], str) and re.fullmatch(r"\S+", a["python_cmd"]), "python_cmd",
         "one executable without spaces, like \"python\" (it runs the hooks)"),
        (isinstance(v, dict) and all(isinstance(x, str) and re.fullmatch(r"[A-Z][A-Z0-9_]*", k) and k not in DERIVED
                                     for k, x in v.items()), "values",
         f"an object of UPPER_SNAKE names (not {sorted(DERIVED)}) to strings"),
        (isinstance(m, dict) and set(m) == {"context7", "playwright_version"} and isinstance(m["context7"], bool)
         and isinstance(m["playwright_version"], str)
         and (not m["playwright_version"] or VERSION.fullmatch(m["playwright_version"])), "mcp",
         "an object with context7 (true/false) and playwright_version (a pinned version like 0.0.41, or \"\")")]
    problems = [f"{k} must be {want}, got {a[k]!r}" for passed, k, want in checks if not passed]
    if problems:
        raise RenderError(problems)
    a["source_dirs"], a["test_dirs"] = ([d.rstrip("/") for d in a[k]] for k in ("source_dirs", "test_dirs"))
    return a

def context(a: dict):  # the marker conditions and the placeholder values
    level, guard, agents = a["level"], a["guard"], a["instructions"] == "agents"
    conds = {"full": level == "full", "lite": level != "full", "skills": level != "starter", "guard": guard,
             "noguard": not guard, "agents-md": agents, "claude-only": not agents}
    subs = {"PYTHON_CMD": a["python_cmd"], "SOURCE_DIRS": ", ".join(f"`{d}/`" for d in a["source_dirs"]),
            "TEST_DIRS": ", ".join(f"`{d}/`" for d in a["test_dirs"]),
            "OWNED_PATHS": OWNED_WORDS + "".join(f", `{x}`" for x in a["owned_paths"])}
    subs.update((k, NOT_SET if k.endswith("_COMMAND") and not x.strip() else x) for k, x in a["values"].items())
    return conds, subs

def apply_markers(rel: str, text: str, conds: dict, problems: list) -> str:
    lines, out = text.split("\n"), []
    fm_end = next((i for i in range(1, len(lines)) if lines[i] == "---"), 0) if lines[0] == "---" else 0
    for i, line in enumerate(lines, 1):
        tail = MARKER_TAIL.search(line)
        if tail:
            names = MARKER.findall(tail.group(0))
            unknown = [n for n in names if n not in conds]
            if unknown or (fm_end and i <= fm_end + 1):
                problems.append(f"{rel}:{i}: " + (f"unknown marker {unknown}" if unknown else "marker in frontmatter"))
                continue
            if not all(conds[n] for n in names):
                continue
            line = line[:tail.start()].rstrip()
        if "<!-- if:" in line:
            problems.append(f"{rel}:{i}: malformed '<!-- if:' marker, or not at the end of the line")
        out.append(line)
    return "\n".join(out)

def fill(rel: str, text: str, subs: dict, missing: dict) -> str:
    def repl(m):
        value = subs.get(m.group(2))
        if value is None or not value.strip():  # recorded as missing; the text stays as it was
            return missing.setdefault(m.group(2), set()).add(rel) or m.group(0)
        bare = m.group(1) and m.group(3) and (value == NOT_SET or "`" in value)  # no `not set up yet`, no ``x``
        return value if bare else m.group(1) + value + m.group(3)
    return PLACEHOLDER.sub(repl, text)

def target_for(rel: str, a: dict):
    """(target path, None) for a template to copy, or (None, reason) when the answers leave it out."""
    level, agents = a["level"], a["instructions"] == "agents"
    name = re.sub(r"^dot-claude/", ".claude/", re.sub(r"\.tmpl$", "", rel))
    if rel == "dot-claude/skills/task/assets/spec-template.md" and level == "standard":
        return "tasks/SPEC-TEMPLATE.md", None
    rules = [  # (template matches, target, keep it, reason when left out)
        (rel == "CLAUDE.md.tmpl", "CLAUDE.md", not agents, "instructions claude only"),
        (rel in ("AGENTS.md.tmpl", "CLAUDE-wrapper.md.tmpl"), name.replace("-wrapper", ""), agents,
         "instructions agents only"),
        (rel.startswith("docs/") or rel in ("tasks/README.md", "dot-claude/rules/tests.md"), name, True, ""),
        (rel.startswith(("dot-claude/skills/grill-me/", "dot-claude/skills/managing-known-issues/")), name,
         level != "starter", "standard and full only"),
        (rel.startswith(("dot-claude/agents/", "dot-claude/skills/task/")), name, level == "full", "full only"),
        (rel == "dot-claude/hooks/guard.py" or bool(re.fullmatch(r"dot-claude/hooks/tests/[^/]+\.py", rel)), name,
         a["guard"], "guard on only")]
    for matches, dest, keep, reason in rules:
        if matches:
            return (dest, None) if keep else (None, reason)
    raise RenderError([f"template {rel} is not covered by the selection rules in render.py"])

def dump(obj) -> bytes:
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")

def settings_parts(a: dict):
    text = (TEMPLATES / "dot-claude/settings.json").read_text(encoding="utf-8")
    tpl = json.loads(text.replace("{{PYTHON_CMD}}", json.dumps(a["python_cmd"])[1:-1]))
    perms = dict(tpl["permissions"])
    cmds = [a["values"].get(k, "").strip() for k in ("TEST_COMMAND", "LINT_COMMAND")]
    perms["allow"] = [r for c in cmds if c for r in (f"Bash({c})", f"Bash({c} *)")] + \
        [r for r in perms["allow"] if a["guard"] or ".claude/hooks/" not in r]
    for k in ("allow", "deny", "ask"):  # PowerShell twin: the same command, npm -> npm.cmd
        twins = ["PowerShell(" + NPM.sub("npm.cmd", r[5:-1]) + ")" for r in perms[k] if r.startswith("Bash(")]
        perms[k] = list(dict.fromkeys(perms[k] + (twins if a["os"] == "windows" else [])))
    settings = {k: (perms if k == "permissions" else v) for k, v in tpl.items() if k != "hooks"}
    if a["guard"] and a["hooks_location"] == "shared":
        settings["hooks"] = tpl["hooks"]
    return settings, tpl["hooks"]

def guard_config(a: dict) -> dict:
    tpl = json.loads((TEMPLATES / "dot-claude/hooks/guard.config.json").read_text(encoding="utf-8"))
    src, tst, full = [f"{d}/**" for d in a["source_dirs"]], [f"{d}/**" for d in a["test_dirs"]], a["level"] == "full"
    cfg = {"_comment": [
        "Read by .claude/hooks/guard.py, whose docstring documents every key. Change it only with the user's approval.",
        ("roles: the six subagent roles, each limited to its own paths" if full else "roles is {}: no subagent roles; "
         "subagents may write anything not protected and not a committed test") + ". Folders: " + ", ".join(src + tst)]}
    cfg.update((k, v) for k, v in tpl.items() if not k.startswith("_"))
    swap = {"src/**": src, "tests/**": tst}
    cfg["roles"] = {r: list(dict.fromkeys(q for x in pats for q in swap.get(x, [x])))
                    for r, pats in tpl["roles"].items()} if full else {}
    cfg["unknown_subagents"], cfg["test_writers"] = ("read-only", tpl["test_writers"]) if full else ("allow", [])
    cfg["tests"] = list(dict.fromkeys(tst + [x for x in tpl["tests"] if not x.endswith("/**")]))
    cfg["protected"] = list(dict.fromkeys(tpl["protected"] + a["owned_paths"]))
    return cfg

def is_git_root(target: Path) -> bool:
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=target, capture_output=True, text=True)
    except FileNotFoundError:
        return False
    return top.returncode == 0 and os.path.samefile(top.stdout.strip(), target)

def build_plan(a: dict, target: Path) -> dict:
    (conds, subs), problems, missing, creates, merges, skipped = context(a), [], {}, {}, {}, {}
    for path in sorted(TEMPLATES.rglob("*")):
        rel = path.relative_to(TEMPLATES).as_posix()
        if path.is_dir() or JUNK & set(rel.split("/")) or rel.endswith(".pyc") or rel in GENERATED:
            continue
        dest, reason = target_for(rel, a)
        if dest is None:
            skipped.setdefault(reason, []).append(rel)
            continue
        data = path.read_bytes()
        if rel.endswith((".md", ".tmpl")):
            text = apply_markers(rel, data.decode("utf-8").replace("\r\n", "\n"), conds, problems)
            data = fill(rel, text, subs, missing).encode("utf-8")
        creates[dest] = (data, rel)
    problems += [f"no value for {k} (used in {', '.join(sorted(f))})" for k, f in sorted(missing.items())]
    if problems:
        raise RenderError(problems)
    settings, hooks = settings_parts(a)
    servers, version = {}, a["mcp"]["playwright_version"]
    if a["mcp"]["context7"]:
        servers["context7"] = {"type": "http", "url": "https://mcp.context7.com/mcp"}
    if version:
        npx = ["npx", "-y", f"@playwright/mcp@{version}"]
        servers["playwright"] = {"type": "stdio", "command": "cmd", "args": ["/c", *npx]} if a["os"] == "windows" \
            else {"type": "stdio", "command": "npx", "args": npx[1:]}
    generated = {".claude/settings.json": settings, ".claude/hooks/guard.config.json": a["guard"] and guard_config(a),
                 ".mcp.json": servers and {"mcpServers": servers}}
    creates.update((rel, (dump(obj), "generated")) for rel, obj in generated.items() if obj)
    conflicts, local = [d for d in creates if (target / d).exists()], target / ".claude/settings.local.json"
    if a["guard"] and a["hooks_location"] == "local":
        try:
            cur = json.loads(local.read_bytes().decode("utf-8-sig")) if local.exists() else {}
        except ValueError as e:
            raise RenderError([f"{local} is not valid JSON: {e}"]) from e
        have = cur.get("hooks", {}) if isinstance(cur, dict) else None
        clash = sorted(set(hooks) & set(have)) if isinstance(have, dict) else ["(its hooks are not an object)"]
        conflicts += [f".claude/settings.local.json (it already has hooks {', '.join(clash)})"] * bool(clash)
        entry = (dump({**cur, "hooks": {**have, **hooks}}), "add hooks " + ", ".join(hooks)) if not clash else None
        (merges if local.exists() else creates).update({".claude/settings.local.json": entry} if entry else {})
    ignore = target / ".gitignore"
    old = ignore.read_bytes() if ignore.exists() else b""
    have = {x.strip() for x in old.decode("utf-8-sig").splitlines()}
    add = [x for x in dict.fromkeys(GITIGNORE + ["__pycache__/"] * a["guard"] + a["gitignore_extra"]) if x not in have]
    if ".env.*" in add and "!.env.example" not in add:
        add.insert(add.index(".env.*") + 1, "!.env.example")  # an earlier !.env.example line would be overridden
    if add:
        nl = b"\r\n" if b"\r\n" in old else b"\n"
        data = old + (nl if old and not old.endswith(b"\n") else b"") + nl.join(x.encode() for x in add) + nl
        (merges if ignore.exists() else creates)[".gitignore"] = (data, "append " + ", ".join(add))
    return {"creates": creates, "merges": merges, "skipped": skipped, "conflicts": conflicts, "subs": subs,
            "settings": settings, "hooks": hooks, "servers": servers, "verify": a["guard"] and is_git_root(target)}

def wrap(label: str, items) -> str:  # "  label: a, b, c" wrapped between items, never inside one
    return textwrap.fill(f"{label}: " + ", ".join(i.replace(" ", NBSP) for i in items), 116, initial_indent="  ",
                         subsequent_indent="    ", break_long_words=False, break_on_hyphens=False).replace(NBSP, " ")

def plan_text(plan: dict, a: dict, target: Path) -> str:
    creates, shown, perms = plan["creates"], set(), plan["settings"]["permissions"]
    out = [f"Plan for {target}", f"  level {a['level']}, instructions {a['instructions']}, guard "
           f"{'on' if a['guard'] else 'off'}, hooks {a['hooks_location']}, os {a['os']}, python {a['python_cmd']}",
           f"\nFiles to create ({len(creates)}):"]
    for rel in sorted(creates, key=lambda r: [(1, x) for x in r.split("/")[:-1]] + [(0, r.split("/")[-1])]):
        parts = rel.split("/")
        for i in range(len(parts) - 1):
            if "/".join(parts[:i + 1]) not in shown:
                shown.add("/".join(parts[:i + 1]))
                out.append("  " * (i + 1) + parts[i] + "/")
        data, note = creates[rel]
        if note.endswith((".md", ".tmpl", ".py")):  # a template: named only when the file name changes
            note = "from " + note if Path(note).name.replace(".tmpl", "") != parts[-1] else ""
        kb = f"{len(data) / 1024:.1f} KB" if len(data) >= 1024 else f"{len(data)} B"
        out.append(textwrap.fill(f"{'  ' * len(parts) + parts[-1]:<50}{kb:>9}  {note}".rstrip(), 120,
                                 subsequent_indent=" " * 63, break_long_words=False, break_on_hyphens=False))
    out += [f"\nMerge into existing {rel}: {note}" for rel, (_, note) in plan["merges"].items()]
    out += ["\nTemplates not used:"] if plan["skipped"] else []
    out += [wrap(why, sorted({r.rsplit("/", 1)[0] + "/" if "/" in r else r for r in rels}))
            for why, rels in plan["skipped"].items()]
    out.append("\nPlaceholders:")
    for k, v in sorted(plan["subs"].items()):
        first, more = (v.splitlines() or [""])[0], len(v.splitlines()) - 1
        out.append(f"  {k:<16} {first[:80]}" + "..." * (len(first) > 80) + (f" (+{more} more)" if more else ""))
    out.append("\n.claude/settings.json" + " (+ a PowerShell twin of each Bash rule)" * (a["os"] == "windows") + ":")
    out += [wrap(k, [r for r in perms[k] if not r.startswith("PowerShell(")] or ["(none)"])
            for k in ("allow", "deny", "ask")]
    where = ".claude/settings.json" if a["hooks_location"] == "shared" else ".claude/settings.local.json"
    out.append(wrap(f"hooks in {where}, {a['python_cmd']} .claude/hooks/guard.py pre|post|stop on", plan["hooks"])
               if a["guard"] else "  hooks: none (guard off)")
    if a["guard"]:
        cfg = json.loads(creates[".claude/hooks/guard.config.json"][0])
        roles = "as above" if cfg["roles"] else "{} (no role checks)"
        out += ["\n.claude/hooks/guard.config.json:"] + [wrap("role " + r, p) for r, p in cfg["roles"].items()]
        out += [f"  roles: {roles}, unknown_subagents: {cfg['unknown_subagents']}, test_writers: {cfg['test_writers']}",
                wrap("tests", cfg["tests"]), wrap("protected", cfg["protected"]),
                wrap("size limits (warn/block lines)", [f"{p} {w}/{b}" for p, w, b in cfg["size_limits"]])]
    out.append("\n.mcp.json: " + (", ".join(f"{n} ({s.get('url') or ' '.join([s['command'], *s['args']])})"
                                            for n, s in plan["servers"].items()) or "not created (no MCP server)"))
    return "\n".join(out)

def write_and_verify(plan: dict, a: dict, target: Path) -> str:
    written, problems = {**plan["creates"], **plan["merges"]}, []
    for rel, (data, _) in written.items():
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        (target / rel).write_bytes(data)
    for rel in written:
        text = (target / rel).read_bytes().decode("utf-8", "replace")
        problems += [f"{rel}:{n}: left over: {x.strip()}" for n, x in enumerate(text.splitlines(), 1)
                     if LEFTOVER.search(x)]
        try:
            json.loads(text) if rel.endswith(".json") else None
        except ValueError as e:
            problems.append(f"{rel}: invalid JSON: {e}")
    if problems:
        raise RenderError(problems)
    report = (f"Created ({len(plan['creates'])}):\n" + "".join(f"  {r}\n" for r in sorted(plan["creates"]))
              + "".join(f"Merged: {r} ({note})\n" for r, (_, note) in plan["merges"].items())
              + "Verified: no {{NAME}} placeholder or '<!-- if:' marker left; every JSON file parses.")
    if not (a["guard"] and plan["verify"]):
        return report + "\nGuard config: not verified (the target is not the root of a git repository)." * a["guard"]
    r = subprocess.run([sys.executable, str(target / ".claude/hooks/guard.py"), "check"], cwd=target, text=True,
                       capture_output=True, env=dict(os.environ, CLAUDE_PROJECT_DIR=str(target)))
    if r.returncode not in (0, 1):  # 1 = findings: the config loaded
        raise RenderError([f"the installed guard failed (exit {r.returncode}):\n{r.stdout}{r.stderr}"])
    return (report + f"\nGuard config loads ({Path(sys.executable).name} .claude/hooks/guard.py check):\n"
            + r.stdout.rstrip() + ("\nNOTE: these findings are in the existing working tree, not in the rendered "
                                   "files: show them to the user." if r.returncode else ""))

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render the agentic-workflow kit into a project (see the docstring).")
    ap.add_argument("--answers", required=True, type=Path, help="answers.json written after the interview")
    ap.add_argument("--target", required=True, type=Path, help="the project root")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and write nothing")
    args = ap.parse_args(argv)
    target = args.target.resolve()
    if not target.is_dir():
        raise RenderError([f"target {target} is not an existing directory"])
    a = load_answers(args.answers)
    plan = build_plan(a, target)
    if args.dry_run:
        print(plan_text(plan, a, target))
    if plan["conflicts"]:
        sys.stderr.write("render.py: nothing written; these already exist (resolve them with the user):\n"
                         + "".join(f"- {c}\n" for c in plan["conflicts"]))
        return 1
    if not args.dry_run:
        print(write_and_verify(plan, a, target))
    return 0

if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):  # values and paths may be non-ASCII; Windows pipes default to cp1252
        stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        sys.exit(main())
    except RenderError as e:
        sys.stderr.write("render.py: cannot render:\n" + "".join(f"- {p}\n" for p in e.args[0]))
        sys.exit(1)
