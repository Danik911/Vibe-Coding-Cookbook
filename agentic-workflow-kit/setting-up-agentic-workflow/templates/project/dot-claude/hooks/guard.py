#!/usr/bin/env python3
"""Config-driven guard for Claude Code hooks: who may write what, locked tests and file-size caps.

Install at <project>/.claude/hooks/guard.py with guard.config.json beside it. Stdlib only, Python >= 3.9,
Windows, macOS and Linux. Needs git: a "committed" (locked) test is a test file tracked at HEAD.

Modes (wired in .claude/settings.json, exec form):
  pre    PreToolUse  Write|Edit|MultiEdit|NotebookEdit -> "deny" / "ask" JSON on stdout, or silence
  post   PostToolUse (same tools) -> exit 2 + stderr note when a file is at or above its warn size
  stop   Stop / SubagentStop -> size and locked-test checks on the git working tree
  check  CLI: python .claude/hooks/guard.py check [--since SHA] -> "guard check: OK" (exit 0), or the
         oversized files and changed committed tests since SHA (default HEAD) and exit 1

pre decides per file. The actor is the main thread when the payload has no agent_id, otherwise the
subagent's agent_type, lowercased; a subagent that is not a key of "roles" is "unknown".
  - A path outside the project: silence.
  - "protected": main thread -> ask; any subagent -> deny.
  - "tests": test_writers may write every test path. Any other actor on a test committed at HEAD
    (even if deleted since): main thread -> ask; subagent -> deny with the TEST-DISPUTE instruction.
    A new (untracked) test file follows the role rules below.
  - Roles: a known role may write only paths matching its patterns; an unknown subagent is denied
    when unknown_subagents is "read-only". The main thread is not limited by roles.
  - Size: deny when the projected file is above its block limit AND larger than before (shrinking
    always passes). Skipped for "size_exempt" paths, extensions not in "sized_extensions", paths no
    size limit matches, and NotebookEdit.
  In bypassPermissions mode nobody answers an "ask", so the main thread's asks become denials.
  The guard never answers "allow" (that would skip the normal permission prompts): silence means
  "no objection" and the normal permission flow continues.

stop, SubagentStop (exit 2 sends the subagent back once; stop_hook_active lets it stop next time):
  a subagent that may write (a known role, or any subagent when unknown_subagents is "allow") is
  checked for changed files above their block size inside the paths it may write and, unless it is
  a test_writer, for committed tests changed or deleted since HEAD. The check uses git, so edits made
  through the shell count. Read-only unknown subagents (built-in helpers such as Explore) pass.
stop, Stop (main thread): the same checks over the whole tree, shown to the user as a systemMessage;
  it never blocks.

Config: guard.config.json, one JSON object. Keys starting with "_" are comments; all others are required
and unknown keys are errors.
  roles              {"<agent name>": ["<pattern>", ...]}: the paths each subagent role may write.
                     {} = no per-role checks; every subagent is then governed by unknown_subagents.
  unknown_subagents  "read-only" (deny every write in the project) or "allow".
  protected          patterns only the main thread may change, after asking the user.
  tests              patterns of test files; the committed ones are locked.
  test_writers       role names (keys of roles) that may edit committed tests.
  size_limits        [["<pattern>", warn_lines, block_lines], ...], 0 < warn <= block. The first
                     match wins; a path no pattern matches has no limit, so end with ["*", w, b].
  size_exempt        patterns never size-checked (lock files, fixtures, generated code).
  sized_extensions   extensions that are size-checked, for example [".py", ".ts", ".md"].
Patterns: fnmatch on the lowercase, repo-relative, forward-slash path, and "*" also matches "/":
"src/*" and "src/**" both match everything under src/; "*/tests/**" matches a tests/ folder at any
depth below the root ("tests/**" is the top-level one); "*.test.ts" matches at any depth. Write them
relative to the project root, with "/" and without a leading "/" or "./"; matching ignores case.
Keep ".claude/**" protected, or agents can rewrite the guard and its config.

Fails closed and loud: a missing or invalid config, a malformed payload, a git failure or a guard
that is not at <CLAUDE_PROJECT_DIR>/.claude/hooks/guard.py (on Windows the Git Bash form /c/... is accepted
for CLAUDE_PROJECT_DIR and file paths) prints the reason on stderr and exits 2,
which blocks the action; any unexpected error prints a traceback and exits 2.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
import traceback
from pathlib import Path

CONFIG_NAME = "guard.config.json"
REQUIRED_KEYS = {"roles", "unknown_subagents", "protected", "tests", "test_writers", "size_limits",
                 "size_exempt", "sized_extensions"}
TEST_DISPUTE = ("locked at the RED commit - do not edit it through the shell either. If the test is wrong, stop and "
                "return 'TEST-DISPUTE: <test> | <AC> | evidence | proposed change' for the user to decide.")


class GuardError(Exception):
    pass


def need(ok: bool, message: str) -> None:
    if not ok:
        raise GuardError(message)


def patterns_of(where: str, value) -> tuple:
    need(isinstance(value, list) and all(isinstance(p, str) and p.strip() for p in value),
         f"{where} must be a list of non-empty strings, got {value!r}")
    bad = [p for p in value if "\\" in p or p.startswith(("/", "./"))]
    need(not bad, f"{where}: write patterns relative to the project root with '/', not {bad}")
    return tuple(p.lower() for p in value)


def load_config(path: Path) -> dict:
    need(path.is_file(), f"config {path} is missing: the guard cannot run without it (schema: guard.py docstring)")
    try:
        raw = json.loads(path.read_bytes().decode("utf-8-sig"))
    except ValueError as e:  # UnicodeDecodeError and JSONDecodeError are both ValueErrors
        raise GuardError(f"config {path} is not valid UTF-8 JSON: {e}") from e
    need(isinstance(raw, dict), f"config {path} must hold one JSON object")
    keys = {k for k in raw if not k.startswith("_")}
    need(keys == REQUIRED_KEYS, f"config {path}: missing keys {sorted(REQUIRED_KEYS - keys)}, "
                                f"unknown keys {sorted(keys - REQUIRED_KEYS)}")
    need(isinstance(raw["roles"], dict),
         f"config roles must map each role name to a list of patterns, got {raw['roles']!r}")
    roles = {name.lower(): patterns_of(f"config roles.{name}", pats) for name, pats in raw["roles"].items()}
    need(len(roles) == len(raw["roles"]) and not roles.keys() & {"main", "unknown"},
         f"config roles: names must be unique ignoring case and not 'main' or 'unknown': {sorted(raw['roles'])}")
    need(raw["unknown_subagents"] in ("read-only", "allow"),
         f"config unknown_subagents must be \"read-only\" or \"allow\", got {raw['unknown_subagents']!r}")
    writers = raw["test_writers"]
    need(isinstance(writers, list) and all(isinstance(n, str) and n.lower() in roles for n in writers),
         f"config test_writers must list names from roles {sorted(roles)}, got {writers!r}")
    need(isinstance(raw["size_limits"], list), f"config size_limits must be a list, got {raw['size_limits']!r}")
    limits = []
    for item in raw["size_limits"]:
        need(isinstance(item, list) and len(item) == 3 and all(type(n) is int for n in item[1:])
             and 0 < item[1] <= item[2], f"config size_limits entries must be [\"<pattern>\", warn, block] "
                                         f"with 0 < warn <= block, got {item!r}")
        limits.append((patterns_of("config size_limits", [item[0]])[0], item[1], item[2]))
    exts = raw["sized_extensions"]
    need(isinstance(exts, list) and all(isinstance(e, str) and len(e) > 1 and e.startswith(".") for e in exts),
         f"config sized_extensions must be a list like [\".py\", \".md\"], got {exts!r}")
    return {"roles": roles, "unknown_subagents": raw["unknown_subagents"],
            "protected": patterns_of("config protected", raw["protected"]),
            "tests": patterns_of("config tests", raw["tests"]),
            "test_writers": {n.lower() for n in writers}, "size_limits": limits,
            "size_exempt": patterns_of("config size_exempt", raw["size_exempt"]),
            "sized_extensions": {e.lower() for e in exts}}


def matches(rel: str, patterns) -> bool:
    return any(fnmatch.fnmatchcase(rel, p) for p in patterns)


def git(root: Path, *args: str) -> str:
    try:
        r = subprocess.run(["git", *args], cwd=root, capture_output=True)
    except FileNotFoundError as e:
        raise GuardError("git is not on PATH: the guard needs it to find committed tests and changes") from e
    if r.returncode != 0:
        raise GuardError(f"git {' '.join(args)} failed: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout.decode("utf-8", "replace")


def split_z(out: str) -> list:
    return [p for p in out.split("\0") if p]


def rev_exists(root: Path, rev: str) -> bool:
    """False for an unborn HEAD (nothing committed yet); raises for any other unknown revision."""
    git(root, "rev-parse", "--git-dir")  # raises when this is not a git repository
    found = subprocess.run(["git", "rev-parse", "--verify", "-q", rev + "^{commit}"],
                           cwd=root, capture_output=True).returncode == 0
    need(found or rev == "HEAD", f"unknown revision {rev!r}")
    return found


def tracked(root: Path, rev: str) -> set:
    if not rev_exists(root, rev):
        return set()
    return {p.lower() for p in split_z(git(root, "ls-tree", "-r", "-z", "--name-only", rev))}


def read_text(path: Path) -> str:
    return path.read_bytes().decode("utf-8", "replace") if path.is_file() else ""


def count_lines(text: str) -> int:
    return text.count("\n") + (1 if text and not text.endswith("\n") else 0)


def native(raw: str) -> str:
    """Forward slashes; on Windows also turn a Git Bash path /c/Users/... into c:/Users/..."""
    s = raw.replace("\\", "/")
    m = re.match(r"^/([a-zA-Z])(/.*)?$", s) if os.name == "nt" else None
    return f"{m.group(1)}:{m.group(2) or '/'}" if m else s


def rel_path(raw: str, root: Path):
    """Return (lowercase repo-relative path, absolute Path) or None when outside the project."""
    p = Path(native(raw))
    if not p.is_absolute():
        p = root / p
    p = p.resolve()
    full = str(p).replace("\\", "/").lower()
    base = str(root).replace("\\", "/").lower().rstrip("/")
    return (full[len(base) + 1:], p) if full.startswith(base + "/") else None


def target(root: Path, data: dict):
    ti = data.get("tool_input") or {}
    raw = ti.get("file_path") or ti.get("notebook_path")
    need(bool(raw), f"{data.get('tool_name')} payload has no tool_input.file_path/notebook_path")
    return rel_path(raw, root)


def actor_of(cfg: dict, data: dict):
    agent_type = str(data.get("agent_type") or "")
    if not data.get("agent_id"):
        return "main", agent_type
    return (agent_type.lower() if agent_type.lower() in cfg["roles"] else "unknown"), agent_type


def may_write(cfg: dict, actor: str, rel: str) -> bool:
    """Role rule only; protected paths and committed tests are checked separately."""
    if actor == "main":
        return True
    if actor == "unknown":
        return cfg["unknown_subagents"] == "allow"
    return matches(rel, cfg["roles"][actor]) or (actor in cfg["test_writers"] and matches(rel, cfg["tests"]))


def decide(cfg: dict, actor: str, rel: str, is_committed) -> list:
    """Return the objections as (level, reason) pairs, level 'ask' or 'deny'; [] means stay silent."""
    main = actor == "main"
    found = []
    if matches(rel, cfg["protected"]):
        found.append(("ask", f"{rel} is protected: it changes only with the user's approval") if main else
                     ("deny", f"{rel} is protected: only the main thread may change it, with the user's approval"))
    if matches(rel, cfg["tests"]) and actor not in cfg["test_writers"] and is_committed():
        found.append(("ask", f"{rel} is a committed test: confirm the change does not weaken it") if main else
                     ("deny", f"{rel} is a committed test, {TEST_DISPUTE}"))
    if not may_write(cfg, actor, rel):
        found.append(("deny", f"{rel}: subagents outside the configured roles are read-only in this project"
                      if actor == "unknown" else f"{rel}: '{actor}' may write only {list(cfg['roles'][actor])}"))
    return found


def limits(cfg: dict, rel: str):
    """(warn, block) lines for a size-checked path, else None."""
    if Path(rel).suffix not in cfg["sized_extensions"] or matches(rel, cfg["size_exempt"]):
        return None
    return next(((w, b) for pat, w, b in cfg["size_limits"] if fnmatch.fnmatchcase(rel, pat)), None)


def too_big(rel: str, block: int, new: str, old: str):
    """Reason when `new` is above the block limit AND larger than `old` (shrinking is always allowed)."""
    n_new, n_old = count_lines(new), count_lines(old)
    if n_new > block and n_new > n_old:
        return f"{rel} would be {n_new} lines (limit {block}): split it by responsibility first"
    return None


def projected(tool: str, ti: dict, path: Path):
    current = read_text(path)
    if tool == "Write":
        return current, ti["content"]
    new = current
    for e in (ti.get("edits") or []) if tool == "MultiEdit" else [ti]:
        old, rep = e.get("old_string", ""), e.get("new_string", "")
        if old:
            new = new.replace(old, rep) if e.get("replace_all") else new.replace(old, rep, 1)
        elif not new:
            new = rep
    return current, new


def mode_pre(root: Path, cfg: dict, data: dict) -> int:
    found = target(root, data)
    if found is None:
        return 0
    rel, path = found
    tool, ti = data.get("tool_name", ""), data.get("tool_input") or {}
    actor, agent_type = actor_of(cfg, data)
    results = decide(cfg, actor, rel, lambda: rel in tracked(root, "HEAD"))
    lim = limits(cfg, rel)
    if tool != "NotebookEdit" and lim:
        current, new = projected(tool, ti, path)
        reason = too_big(rel, lim[1], new, current)
        if reason:
            results.append(("deny", reason))
    if not results:
        return 0
    level = "deny" if any(lvl == "deny" for lvl, _ in results) else "ask"
    reasons = [msg for _, msg in results]
    if level == "ask" and data.get("permission_mode") == "bypassPermissions":
        level = "deny"
        reasons.append("bypass mode cannot ask the user, so this is denied - switch permission mode to approve it")
    msg = f"[guard] actor={actor} agent_type={agent_type or '-'}: " + " | ".join(reasons)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": level,
                                             "permissionDecisionReason": msg}}))
    return 0


def mode_post(root: Path, cfg: dict, data: dict) -> int:
    found = target(root, data)
    lim = limits(cfg, found[0]) if found else None
    if not lim or not found[1].is_file():
        return 0
    rel, path = found
    lines = count_lines(read_text(path))
    warn, block = lim
    if lines < warn:
        return 0
    sys.stderr.write(f"[guard] NOTE: {rel} is {lines} lines (warn {warn}, block {block}). "
                     f"Plan a split by responsibility before it reaches {block}.\n")
    return 2


def changed_paths(root: Path, rev: str) -> set:
    out = set(split_z(git(root, "ls-files", "--others", "--exclude-standard", "-z")))
    if rev_exists(root, rev):
        out |= set(split_z(git(root, "diff", "--name-only", "-z", rev)))
    return out


def oversized_changes(root: Path, cfg: dict, rev: str, keep=lambda rel: True) -> list:
    problems = []
    base = tracked(root, rev)
    for p in sorted(changed_paths(root, rev)):
        rel, path = p.lower(), root / p
        lim = limits(cfg, rel)
        if not lim or not keep(rel) or not path.is_file():
            continue
        old = git(root, "show", f"{rev}:{p}") if rel in base else ""
        reason = too_big(rel, lim[1], read_text(path), old)
        if reason:
            problems.append(reason.replace(" would be ", " is "))
    return problems


def locked_test_changes(root: Path, cfg: dict, rev: str) -> list:
    if not rev_exists(root, rev):
        return []
    changed = split_z(git(root, "diff", "--name-only", "-z", "--diff-filter=MDT", rev))
    return [f"{p}: committed test changed or deleted since {rev}. If you did this, restore it with "
            f"'git restore --source={rev} -- {p}' and raise a TEST-DISPUTE instead; if you did not, leave it "
            f"and say so in your report" for p in changed if matches(p.lower(), cfg["tests"])]


def mode_stop(root: Path, cfg: dict, data: dict) -> int:
    if data.get("stop_hook_active"):
        return 0
    actor, _ = actor_of(cfg, data)
    if data.get("hook_event_name") == "SubagentStop":
        need(actor != "main", "SubagentStop payload has no agent_id")
        if actor == "unknown" and cfg["unknown_subagents"] == "read-only":
            return 0
        problems = oversized_changes(root, cfg, "HEAD", lambda rel: may_write(cfg, actor, rel))
        if actor not in cfg["test_writers"]:
            problems += locked_test_changes(root, cfg, "HEAD")
        if not problems:
            return 0
        sys.stderr.write("[guard] Fix these before finishing:\n- " + "\n- ".join(problems) + "\n")
        return 2
    problems = oversized_changes(root, cfg, "HEAD") + locked_test_changes(root, cfg, "HEAD")
    if problems:  # main thread: inform the user, never block
        print(json.dumps({"systemMessage": "[guard] Attention:\n- " + "\n- ".join(problems)}))
    return 0


def mode_check(root: Path, cfg: dict, args: list) -> int:
    need(args == [] or (len(args) == 2 and args[0] == "--since"), f"usage: guard.py check [--since SHA], got {args}")
    rev = args[1] if args else "HEAD"
    problems = oversized_changes(root, cfg, rev) + locked_test_changes(root, cfg, rev)
    for p in problems:
        print(f"- {p}")
    print(f"guard check: {len(problems)} finding(s)" if problems else "guard check: OK")
    return 1 if problems else 0


def main(argv: list) -> int:
    here = Path(__file__).resolve()
    need(here.parent.name == "hooks" and here.parent.parent.name == ".claude",
         f"guard must live at <project>/.claude/hooks/guard.py, not {here}")
    root = here.parents[2]
    env_root = os.environ.get("CLAUDE_PROJECT_DIR")
    need(not env_root or os.path.normcase(str(Path(native(env_root)).resolve())) == os.path.normcase(str(root)),
         f"this guard belongs to {root}, but CLAUDE_PROJECT_DIR is {env_root}")
    cfg = load_config(here.parent / CONFIG_NAME)
    mode, args = (argv[1], argv[2:]) if len(argv) > 1 else ("", [])
    if mode == "check":
        return mode_check(root, cfg, args)
    handlers = {"pre": mode_pre, "post": mode_post, "stop": mode_stop}
    need(mode in handlers and not args, f"unknown mode {argv[1:]}: expected pre, post, stop or check [--since SHA]")
    try:  # utf-8-sig: Claude Code sends plain UTF-8; PowerShell 5.1 pipes add a BOM when testing by hand
        data = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    except ValueError as e:
        raise GuardError(f"hook payload on stdin is not UTF-8 JSON: {e}") from e
    need(isinstance(data, dict), f"hook payload must be a JSON object, got {type(data).__name__}")
    return handlers[mode](root, cfg, data)


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        sys.exit(main(sys.argv))
    except SystemExit:
        raise
    except GuardError as e:
        sys.stderr.write(f"[guard] ERROR - failing closed; tell the user: {e}\n")
        sys.exit(2)
    except BaseException:
        sys.stderr.write("[guard] internal error - failing closed; tell the user:\n" + traceback.format_exc())
        sys.exit(2)
