"""Tests for scripts/render.py. Run from the kit: python -B -m unittest discover -s scripts/tests -v

FixtureTests copy render.py into <tmp>/kit/scripts/ next to a small synthetic template set (plus the kit's real
settings.json, guard.config.json and guard files) and run it as a subprocess, as the setup agent does.
RealTemplateTests render the kit's real templates for every level x instructions x guard combination.
Every subprocess runs with PYTHONDONTWRITEBYTECODE=1, so no __pycache__ is left anywhere.
"""
import copy
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
REAL = KIT / "templates" / "project"
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
GUIDE = ("always\nfull <!-- if:full -->\nlite <!-- if:lite -->\nskills <!-- if:skills -->\nguard <!-- if:guard -->\n"
         "noguard <!-- if:noguard -->\nagents <!-- if:agents-md -->\nclaude <!-- if:claude-only -->\n"
         "full+guard <!-- if:full --> <!-- if:guard -->   \n| row | x | <!-- if:full -->\nkeep two spaces  \n")
FIXTURE = {
    "CLAUDE.md.tmpl": "# {{PROJECT_NAME}}\n- Tests: `{{TEST_COMMAND}}`\n- Lint: `{{LINT_COMMAND}}`\n"
                      "- Code: `{{SOURCE_DIRS}}`, tests {{TEST_DIRS}}\n- Owned: {{OWNED_PATHS}}\n"
                      "- Guard: `{{PYTHON_CMD}} .claude/hooks/guard.py check` <!-- if:guard -->\n"
                      "- Full: {{FULL_ONLY}} <!-- if:full -->\n",
    "AGENTS.md.tmpl": "# {{PROJECT_NAME}} (shared)\n",
    "CLAUDE-wrapper.md.tmpl": "@AGENTS.md\n",
    "docs/guide.md": GUIDE,
    "tasks/README.md": "tasks\n",
    "dot-claude/rules/tests.md": "rules\n",
    "dot-claude/agents/dev.md": "---\nname: dev\n---\nagent\n",
    "dot-claude/skills/grill-me/SKILL.md.tmpl": "grill\n",
    "dot-claude/skills/managing-known-issues/SKILL.md.tmpl": "issues\n",
    "dot-claude/skills/task/SKILL.md.tmpl": "task: {{PYTHON_CMD}}\n",
    "dot-claude/skills/task/assets/spec-template.md": "spec\n",
    "dot-claude/hooks/tests/__pycache__/test_guard.cpython-313.pyc": "bytecode",
    "dot-claude/hooks/guard.pyc": "bytecode outside __pycache__",
}
REAL_COPIES = ["dot-claude/settings.json", "dot-claude/hooks/guard.config.json", "dot-claude/hooks/guard.py",
               "dot-claude/hooks/tests/test_guard.py"]
BASE = {"level": "full", "instructions": "claude", "guard": True, "hooks_location": "shared", "os": "windows",
        "python_cmd": "python", "source_dirs": ["src", "lib/"], "test_dirs": ["tests"], "owned_paths": ["rates/*.csv"],
        "gitignore_extra": ["dist/"], "mcp": {"context7": False, "playwright_version": ""},
        "values": {"PROJECT_NAME": "Demo", "PROJECT_PURPOSE": "A demo.", "PRODUCT_RULES": "- rule one\n- rule two",
                   "STACK": "Python 3.13", "ENVIRONMENT": "- Windows 11", "TEST_COMMAND": "python -m unittest",
                   "LINT_COMMAND": "", "RUN_COMMAND": "python -m demo", "FULL_ONLY": "full value"}}


def answers(**changes):
    a = copy.deepcopy(BASE)
    a.update(changes)
    return a


def rmtree(path):
    def fix(func, p, _):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=fix)
    else:
        shutil.rmtree(path, onerror=fix)


def files_under(root: Path) -> set:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts}


class RenderCase(unittest.TestCase):
    render_py = KIT / "scripts" / "render.py"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.n = 0

    def tearDown(self):
        rmtree(self.tmp)

    def target(self, git=True):
        self.n += 1
        t = self.tmp / f"project{self.n}"
        t.mkdir()
        if git:
            subprocess.run(["git", "init", "-q"], cwd=t, check=True)
        return t

    def render(self, a, target, *args):
        path = self.tmp / "answers.json"
        path.write_text(json.dumps(a), encoding="utf-8")
        return subprocess.run([sys.executable, str(self.render_py), "--answers", str(path), "--target", str(target),
                               *args], capture_output=True, text=True, encoding="utf-8", env=ENV)

    def ok(self, a, target, *args):
        r = self.render(a, target, *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r


class FixtureTests(RenderCase):
    def setUp(self):
        super().setUp()
        templates = self.tmp / "kit" / "templates" / "project"
        for rel, text in FIXTURE.items():
            (templates / rel).parent.mkdir(parents=True, exist_ok=True)
            (templates / rel).write_text(text, encoding="utf-8", newline="\n")
        for rel in REAL_COPIES:
            shutil.copy(REAL / rel, templates / rel)
        (self.tmp / "kit" / "scripts").mkdir()
        self.render_py = self.tmp / "kit" / "scripts" / "render.py"
        shutil.copy(KIT / "scripts" / "render.py", self.render_py)
        self.templates = templates

    def test_01_markers_keep_a_line_only_when_all_its_conditions_hold(self):
        expected = {
            ("full", "claude", True): "always\nfull\nskills\nguard\nclaude\nfull+guard\n| row | x |\n",
            ("full", "agents", False): "always\nfull\nskills\nnoguard\nagents\n| row | x |\n",
            ("standard", "agents", True): "always\nlite\nskills\nguard\nagents\n",
            ("starter", "claude", False): "always\nlite\nnoguard\nclaude\n",
        }
        for (level, instructions, guard), lines in expected.items():
            with self.subTest(level=level, instructions=instructions, guard=guard):
                t = self.target(git=False)
                self.ok(answers(level=level, instructions=instructions, guard=guard), t)
                self.assertEqual((t / "docs/guide.md").read_text(encoding="utf-8"), lines + "keep two spaces  \n")

    def test_02_bad_markers_fail_before_anything_is_written(self):
        cases = {"docs/guide.md": ("x <!-- if:ful -->\n", "docs/guide.md:1: unknown marker ['ful']"),
                 "tasks/README.md": ("a <!-- if:full --> b\n", "tasks/README.md:1: malformed"),
                 "dot-claude/agents/dev.md": ("---\nname: dev <!-- if:full -->\n---\n", "dev.md:2: marker in frontmatter")}
        for rel, (text, message) in cases.items():
            with self.subTest(rel=rel):
                original = (self.templates / rel).read_text(encoding="utf-8")
                (self.templates / rel).write_text(text, encoding="utf-8")
                t = self.target()
                r = self.render(answers(), t)
                self.assertEqual(r.returncode, 1)
                self.assertIn(message, r.stderr)
                self.assertEqual(files_under(t), set())
                (self.templates / rel).write_text(original, encoding="utf-8")

    def test_03_naming_and_file_selection_per_level_and_switch(self):
        t = self.target()
        self.ok(answers(), t)
        got = files_under(t)
        for rel in ("CLAUDE.md", ".claude/agents/dev.md", ".claude/skills/task/SKILL.md", ".claude/rules/tests.md",
                    ".claude/skills/task/assets/spec-template.md", ".claude/skills/grill-me/SKILL.md",
                    ".claude/hooks/guard.py", ".claude/hooks/tests/test_guard.py", ".claude/hooks/guard.config.json"):
            self.assertIn(rel, got)
        self.assertFalse({"AGENTS.md", "tasks/SPEC-TEMPLATE.md"} & got)
        self.assertFalse([p for p in got if p.endswith((".tmpl", ".pyc")) or "dot-claude" in p or "__pycache__" in p])
        self.assertEqual((t / ".claude/skills/task/SKILL.md").read_text(encoding="utf-8"), "task: python\n")
        t = self.target()
        self.ok(answers(level="standard", instructions="agents", guard=False), t)
        got = files_under(t)
        self.assertEqual((t / "CLAUDE.md").read_text(encoding="utf-8"), "@AGENTS.md\n")
        self.assertEqual((t / "AGENTS.md").read_text(encoding="utf-8"), "# Demo (shared)\n")
        self.assertEqual((t / "tasks/SPEC-TEMPLATE.md").read_text(encoding="utf-8"), "spec\n")
        self.assertIn(".claude/skills/managing-known-issues/SKILL.md", got)
        self.assertFalse([p for p in got if p.startswith((".claude/agents", ".claude/skills/task", ".claude/hooks"))])
        t = self.target()
        self.ok(answers(level="starter", guard=False), t)
        self.assertEqual({p for p in files_under(t) if p.startswith(".claude/")},
                         {".claude/rules/tests.md", ".claude/settings.json"})

    def test_04_placeholders_derived_values_and_empty_commands(self):
        t = self.target()
        self.ok(answers(os="macos", python_cmd="python3"), t)
        self.assertEqual((t / "CLAUDE.md").read_text(encoding="utf-8"),
                         "# Demo\n- Tests: `python -m unittest`\n- Lint: not set up yet\n"
                         "- Code: `src/`, `lib/`, tests `tests/`\n- Owned: agent setup files, CI workflows, deployment "
                         "and infrastructure files, `rates/*.csv`\n- Guard: `python3 .claude/hooks/guard.py check`\n"
                         "- Full: full value\n")

    def test_05_missing_values_are_listed_and_nothing_is_written(self):
        values = dict(BASE["values"])
        del values["PROJECT_NAME"], values["FULL_ONLY"]
        t = self.target()
        r = self.render(answers(level="standard", values=values), t)  # FULL_ONLY is only on a full-level line
        self.assertEqual(r.returncode, 1)
        self.assertIn("no value for PROJECT_NAME (used in CLAUDE.md.tmpl)", r.stderr)
        self.assertNotIn("FULL_ONLY", r.stderr)
        r = self.render(answers(values=dict(BASE["values"], FULL_ONLY=" ")), t)
        self.assertEqual(r.returncode, 1)
        self.assertIn("no value for FULL_ONLY", r.stderr)
        self.assertEqual(files_under(t), set())

    def test_06_existing_files_are_never_overwritten(self):
        t = self.target()
        (t / "CLAUDE.md").write_text("mine\n", encoding="utf-8")
        (t / "docs").mkdir()
        (t / "docs/guide.md").write_text("mine too\n", encoding="utf-8")
        for args in ((), ("--dry-run",)):
            with self.subTest(args=args):
                r = self.render(answers(), t, *args)
                self.assertEqual(r.returncode, 1)
                self.assertIn("nothing written", r.stderr)
                self.assertIn("- CLAUDE.md\n- docs/guide.md\n", r.stderr)
                self.assertEqual(files_under(t), {"CLAUDE.md", "docs/guide.md"})
        self.assertEqual((t / "CLAUDE.md").read_text(encoding="utf-8"), "mine\n")

    def test_07_gitignore_is_created_or_appended_to(self):
        t = self.target()
        self.ok(answers(), t)
        self.assertEqual((t / ".gitignore").read_bytes(),
                         b".env\n.env.*\n!.env.example\n.claude/settings.local.json\n__pycache__/\ndist/\n")
        t = self.target()
        (t / ".gitignore").write_bytes(b"node_modules/\r\n!.env.example\r\n.env")  # CRLF, no final newline
        r = self.ok(answers(guard=False, gitignore_extra=["node_modules/"]), t)
        self.assertEqual((t / ".gitignore").read_bytes(), b"node_modules/\r\n!.env.example\r\n.env\r\n"
                                                          b".env.*\r\n!.env.example\r\n.claude/settings.local.json\r\n")
        self.assertIn("Merged: .gitignore (append .env.*, !.env.example, .claude/settings.local.json)", r.stdout)

    def test_08_settings_local_json_is_created_merged_or_a_conflict(self):
        t = self.target()
        self.ok(answers(hooks_location="local"), t)
        hooks = json.loads((t / ".claude/settings.local.json").read_text(encoding="utf-8"))["hooks"]
        self.assertEqual(sorted(hooks), ["PostToolUse", "PreToolUse", "Stop", "SubagentStop"])
        self.assertNotIn("hooks", json.loads((t / ".claude/settings.json").read_text(encoding="utf-8")))
        t = self.target()
        (t / ".claude").mkdir()
        mine = {"permissions": {"allow": ["Bash(ls)"]}, "hooks": {"Notification": [{"hooks": []}]}}
        (t / ".claude/settings.local.json").write_text(json.dumps(mine), encoding="utf-8")
        r = self.ok(answers(hooks_location="local"), t)
        merged = json.loads((t / ".claude/settings.local.json").read_text(encoding="utf-8"))
        self.assertEqual(merged["permissions"], mine["permissions"])
        self.assertEqual(sorted(merged["hooks"]), ["Notification", "PostToolUse", "PreToolUse", "Stop", "SubagentStop"])
        self.assertIn("Merged: .claude/settings.local.json", r.stdout)
        t = self.target()
        (t / ".claude").mkdir()
        (t / ".claude/settings.local.json").write_text('{"hooks": {"Stop": []}}', encoding="utf-8")
        r = self.render(answers(hooks_location="local"), t)
        self.assertEqual(r.returncode, 1)
        self.assertIn(".claude/settings.local.json (it already has hooks Stop)", r.stderr)
        self.assertEqual(files_under(t), {".claude/settings.local.json"})

    def test_09_permissions_powershell_twins_and_the_fixed_rules(self):
        t = self.target()
        self.ok(answers(), t)
        perms = json.loads((t / ".claude/settings.json").read_text(encoding="utf-8"))["permissions"]
        for k in ("allow", "deny", "ask"):
            bash = [r for r in perms[k] if r.startswith("Bash(")]
            twins = {"PowerShell(" + re.sub(r"^npm ", "npm.cmd ", r[5:-1]) + ")" for r in bash}
            self.assertEqual(twins, {r for r in perms[k] if r.startswith("PowerShell(")}, k)
        self.assertIn("PowerShell(npm.cmd install *)", perms["ask"])
        for rule in ("Bash(python -m unittest)", "Bash(python -m unittest *)", "Bash(python .claude/hooks/guard.py check)",
                     "Bash(python .claude/hooks/guard.py check *)", "Bash(python -m unittest discover -s .claude/hooks/tests)"):
            self.assertIn(rule, perms["allow"])
        self.assertFalse([r for r in perms["allow"] if "lint" in r.lower()])  # LINT_COMMAND is empty
        for rule in ("Read(./.env)", "Read(./.env.local)", "Read(./.env.*.local)", "Read(./.env.production)",
                     "Bash(git reset --hard)", "Bash(git commit --amend)", "Bash(git update-index *)"):
            self.assertIn(rule, perms["deny"])
        self.assertNotIn("Read(./.env.*)", perms["deny"])  # would also hide .env.example
        t = self.target()
        self.ok(answers(os="linux", python_cmd="python3", guard=False, level="standard"), t)
        settings = json.loads((t / ".claude/settings.json").read_text(encoding="utf-8"))
        self.assertNotIn("hooks", settings)
        self.assertFalse([r for k in ("allow", "deny", "ask") for r in settings["permissions"][k]
                          if r.startswith("PowerShell(") or ".claude/hooks" in r])
        t = self.target()
        self.ok(answers(os="macos", python_cmd="python3"), t)
        hook = json.loads((t / ".claude/settings.json").read_text(encoding="utf-8"))["hooks"]["PreToolUse"][0]
        self.assertEqual(hook["hooks"][0]["command"], "python3")

    def test_10_guard_config_per_level(self):
        t = self.target()
        r = self.ok(answers(), t)
        self.assertIn("guard check: OK", r.stdout)
        cfg = json.loads((t / ".claude/hooks/guard.config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["roles"]["developer"], ["src/**", "lib/**", "tests/**", "tasks/*/dev.md", "docs/issues/**"])
        self.assertEqual(sorted(cfg["roles"]), ["debugger", "developer", "doc-keeper", "planner", "reviewer", "tester"])
        self.assertEqual((cfg["test_writers"], cfg["unknown_subagents"]), (["tester"], "read-only"))
        self.assertEqual(cfg["tests"], ["tests/**", "test_*.py", "*/test_*.py", "*.test.ts", "*.spec.ts"])
        for pattern in ("rates/*.csv", "infra/**", "*.tf", ".github/copilot-instructions.md", ".github/instructions/**",
                        ".github/agents/**", ".github/skills/**", ".github/hooks/**", ".cursor/**", ".codex/**",
                        ".agents/**", ".claude/**", "CLAUDE.md", "AGENTS.md", ".mcp.json"):
            self.assertIn(pattern, cfg["protected"])
        self.assertNotIn("setup skill", json.dumps(cfg["_comment"]))
        t = self.target()
        self.assertIn("guard check: OK", self.ok(answers(level="standard"), t).stdout)
        cfg = json.loads((t / ".claude/hooks/guard.config.json").read_text(encoding="utf-8"))
        self.assertEqual((cfg["roles"], cfg["test_writers"], cfg["unknown_subagents"]), ({}, [], "allow"))

    def test_11_mcp_json(self):
        cases = {("windows", True, "0.0.82"): {"context7": {"type": "http", "url": "https://mcp.context7.com/mcp"},
                                               "playwright": {"type": "stdio", "command": "cmd",
                                                              "args": ["/c", "npx", "-y", "@playwright/mcp@0.0.82"]}},
                 ("macos", False, "0.0.82"): {"playwright": {"type": "stdio", "command": "npx",
                                                             "args": ["-y", "@playwright/mcp@0.0.82"]}}}
        for (system, context7, version), servers in cases.items():
            t = self.target()
            self.ok(answers(os=system, mcp={"context7": context7, "playwright_version": version}), t)
            self.assertEqual(json.loads((t / ".mcp.json").read_text(encoding="utf-8")), {"mcpServers": servers})
        t = self.target()
        self.ok(answers(), t)
        self.assertFalse((t / ".mcp.json").exists())

    def test_12_invalid_answers_are_refused(self):
        cases = [(dict(level="starter", guard=True), "guard must be true or false, and false at level starter"),
                 (dict(level="pro"), "level must be one of"),
                 (dict(python_cmd="py -3"), "python_cmd must be one executable"),
                 (dict(source_dirs=[]), "source_dirs must be at least one"),
                 (dict(source_dirs=["../src"]), "source_dirs must be at least one"),
                 (dict(test_dirs=["/abs/tests"]), "test_dirs must be at least one"),
                 (dict(test_dirs=["tests/*"]), "test_dirs must be at least one"),
                 (dict(owned_paths=["rates\\x.csv"]), "owned_paths must be patterns"),
                 (dict(gitignore_extra=["a\nb"]), "gitignore_extra must be a list of one-line strings"),
                 (dict(values={"project_name": "x"}), "values must be an object of UPPER_SNAKE"),
                 (dict(values={"PYTHON_CMD": "x"}), "values must be an object of UPPER_SNAKE"),
                 (dict(mcp={"context7": True, "playwright_version": "latest"}), "mcp must be"),
                 (dict(extra=1), "unknown ['extra']")]
        t = self.target()
        for change, message in cases:
            with self.subTest(change=change):
                r = self.render(answers(**change), t)
                self.assertEqual(r.returncode, 1)
                self.assertIn(message, r.stderr)
        a = answers()
        del a["mcp"]
        self.assertIn("missing ['mcp']", self.render(a, t).stderr)
        self.assertEqual(files_under(t), set())
        self.ok(answers(source_dirs=[".github/scripts", "app/"]), t)  # dot folders and a trailing slash are fine

    def test_13_dry_run_prints_the_plan_and_writes_nothing(self):
        t = self.target()
        out = self.ok(answers(mcp={"context7": True, "playwright_version": ""}), t, "--dry-run").stdout
        for text in ("level full, instructions claude, guard on, hooks shared, os windows, python python",
                     "Files to create (", "\n  .claude/\n", "\n    settings.json ", "generated",
                     "Templates not used:\n  instructions agents only: AGENTS.md.tmpl, CLAUDE-wrapper.md.tmpl",
                     "  LINT_COMMAND     not set up yet", "  PRODUCT_RULES    - rule one (+1 more)",
                     "(+ a PowerShell twin of each Bash rule)", "  role developer: src/**, lib/**, tests/**",
                     "unknown_subagents: read-only, test_writers: ['tester']", "rates/*.csv",
                     ".mcp.json: context7 (https://mcp.context7.com/mcp)"):
            self.assertIn(text, out)
        self.assertTrue(all(len(line) <= 120 for line in out.splitlines() if not line.startswith("Plan for")))
        self.assertEqual(files_under(t), set())

    def test_14_guard_config_is_verified_only_at_a_git_root(self):
        t = self.target(git=False)
        self.assertIn("Guard config: not verified", self.ok(answers(), t).stdout)
        t = self.target()
        (t / "sub").mkdir()
        self.assertIn("Guard config: not verified", self.ok(answers(), t / "sub").stdout)
        t = self.target()
        self.assertIn("guard check: OK", self.ok(answers(), t).stdout)

    def test_15_an_unknown_template_file_fails_loudly(self):
        (self.templates / "stray.txt").write_text("?", encoding="utf-8")
        r = self.render(answers(), self.target())
        self.assertEqual(r.returncode, 1)
        self.assertIn("template stray.txt is not covered", r.stderr)


class RealTemplateTests(RenderCase):
    LEVELS = ("starter", "standard", "full")

    def real_answers(self, level, instructions, guard, n):
        values = {"PROJECT_NAME": "Invoice checker", "PROJECT_PURPOSE": "Checks VAT on invoices.",
                  "PRODUCT_RULES": "- Rates come from the rate table.", "STACK": "Python 3.13, unittest",
                  "ENVIRONMENT": "- Windows 11, PowerShell", "TEST_COMMAND": "python -m unittest discover -s tests",
                  "LINT_COMMAND": "", "RUN_COMMAND": "python -m src.app"}
        return answers(level=level, instructions=instructions, guard=guard, values=values,
                       hooks_location="local" if instructions == "agents" else "shared",
                       os="windows" if n % 2 else "linux", mcp={"context7": level == "full", "playwright_version": ""})

    def test_20_every_combination_renders_cleanly(self):
        rendered, n = {}, 0
        for level in self.LEVELS:
            for instructions in ("claude", "agents"):
                for guard in (True, False):
                    n += 1
                    with self.subTest(level=level, instructions=instructions, guard=guard):
                        t = self.target()
                        r = self.render(self.real_answers(level, instructions, guard, n), t)
                        if level == "starter" and guard:
                            self.assertEqual(r.returncode, 1)
                            self.assertIn("false at level starter", r.stderr)
                            self.assertEqual(files_under(t), set())
                            continue
                        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                        created = files_under(t)
                        self.assertEqual("AGENTS.md" in created, instructions == "agents")
                        self.assertEqual(".claude/hooks/guard.py" in created, guard)
                        self.assertEqual(any(p.startswith(".claude/agents/") for p in created), level == "full")
                        for rel in created:
                            text = (t / rel).read_text(encoding="utf-8")
                            self.assertNotIn("{{", text, rel)
                            self.assertNotIn("<!-- if:", text, rel)
                            if rel.endswith(".json"):
                                json.loads(text)
                        if guard:
                            self.assertIn("guard check: OK", r.stdout)
                            check = subprocess.run([sys.executable, ".claude/hooks/guard.py", "check"], cwd=t, env=dict(
                                ENV, CLAUDE_PROJECT_DIR=str(t)), capture_output=True, text=True)
                            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
                            rendered.setdefault(level, t)
        for level in ("full", "standard"):  # the installed guard's own unit tests pass in the rendered project
            with self.subTest(guard_tests=level):
                self.assertIn(level, rendered, f"no {level} project with the guard rendered cleanly")
                r = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", ".claude/hooks/tests"],
                                   cwd=rendered[level], env=ENV, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr[-3000:])
                self.assertRegex(r.stderr, r"Ran \d+ tests")

    def test_21_lower_levels_and_switched_off_parts_leave_no_references(self):
        """Needs the <!-- if:... --> markers in the Markdown templates; lists every stale line it finds."""
        stale = []
        for n, (level, instructions, guard) in enumerate([("starter", "claude", False), ("standard", "agents", False),
                                                          ("standard", "claude", True)]):
            t = self.target()
            self.ok(self.real_answers(level, instructions, guard, n), t)
            checks = [(r"\.claude/agents|/task\b|\b(planner|tester|developer|debugger|reviewer|doc-keeper)\b",
                       "full-level reference")]
            checks += [(r"guard\.py|guard\.config\.json", "guard reference")] if not guard else []
            checks += [(r"grill-me|managing-known-issues", "skill reference")] if level == "starter" else []
            for rel in sorted(p for p in files_under(t) if p.endswith(".md")):
                for i, line in enumerate((t / rel).read_text(encoding="utf-8").splitlines(), 1):
                    stale += [f"{level}/{instructions}/guard={guard} {rel}:{i}: {why}: {line.strip()[:100]}"
                              for pattern, why in checks if re.search(pattern, line)]
        self.assertEqual(stale, [], f"{len(stale)} stale lines:\n" + "\n".join(stale))


if __name__ == "__main__":
    unittest.main()
