"""Tests for .claude/hooks/guard.py. Run: python -m unittest discover -s .claude/hooks/tests -v

Each test builds a throwaway git repo, copies the guard and the fixed CONFIG below into <repo>/.claude/hooks/
and runs the guard as a subprocess, exactly as Claude Code does (JSON on stdin as UTF-8, CLAUDE_PROJECT_DIR
set). CONFIG is independent of the project's own guard.config.json, so the suite passes whatever the project
configured; test_23 checks that the project's real guard.config.json is valid.
"""
import copy
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
CONFIG = {
    "roles": {
        "planner": ["tasks/*/spec.md"],
        "tester": ["tests/**", "tasks/*/tests.md", "tasks/*/verify.md", "tasks/*/evidence/**"],
        "developer": ["src/**", "tests/**", "tasks/*/dev.md", "docs/issues/**"],
        "debugger": ["src/**", "tests/**", "tasks/*/debug.md", "tasks/*/evidence/**", "docs/issues/**"],
        "reviewer": ["tasks/*/review.md"],
        "doc-keeper": ["docs/**", "README.md", "*/README.md", "tasks/*/docs.md"],
    },
    "unknown_subagents": "read-only",
    "protected": ["CLAUDE.md", "*/CLAUDE.md", "AGENTS.md", ".claude/**", ".mcp.json", ".git/**",
                  ".github/workflows/**", "Dockerfile", "*/Dockerfile", "compose.yaml", "docker-compose.yml"],
    "tests": ["tests/**", "*/tests/**", "test_*.py", "*/test_*.py", "*.test.ts", "*.spec.ts"],
    "test_writers": ["tester"],
    "size_limits": [["CLAUDE.md", 150, 200], ["AGENTS.md", 150, 200], ["tasks/*", 150, 300],
                    ["docs/issues/ISSUE-*.md", 100, 150], ["*", 500, 1000]],
    "size_exempt": ["*.lock", "package-lock.json", "*/fixtures/**", "*/migrations/**", "*/generated/**"],
    "sized_extensions": [".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".cs", ".go", ".rb", ".md", ".sql", ".css"],
}


def rmtree(path):
    def fix(func, p, _):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=fix)
    else:
        shutil.rmtree(path, onerror=fix)


def lines(n):
    return "".join(f"x{i} = {i}\n" for i in range(n))


class GuardTestCase(unittest.TestCase):
    EDIT_TEST = dict(tool="Edit", old_string="1 == 1", new_string="True")

    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.hooks = self.root / ".claude" / "hooks"
        self.hooks.mkdir(parents=True)
        shutil.copy(HOOKS / "guard.py", self.hooks / "guard.py")
        self.config()
        for args in (["init", "-q"], ["config", "user.email", "t@example.com"], ["config", "user.name", "t"],
                     ["config", "core.autocrlf", "false"], ["config", "commit.gpgsign", "false"]):
            self.git(*args)
        self.write("tests/test_a.py", "def test_a():\n    assert 1 == 1\n")
        self.write("src/app.py", "x = 1\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "task-001: RED tests approved")

    def tearDown(self):
        rmtree(self.root)

    def config(self, **changes):
        cfg = dict(copy.deepcopy(CONFIG), **changes)
        (self.hooks / "guard.config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True).stdout.decode().strip()

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode("utf-8"))
        return p

    def run_guard(self, mode, payload=b"", project=None, args=()):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project or self.root))
        data = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return subprocess.run([sys.executable, str(self.hooks / "guard.py"), mode, *args],
                              input=data, capture_output=True, env=env)

    def pre(self, path, actor=None, tool="Write", agent_id="a1", permission_mode=None, **tool_input):
        absolute = path.startswith("/") or os.path.isabs(path)
        ti = {"file_path": path if absolute else str(self.root / path)}
        if tool == "Write":
            ti["content"] = "x\n"
        ti.update(tool_input)
        data = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": ti}
        if actor:
            data.update(agent_id=agent_id, agent_type=actor)
        if permission_mode:
            data["permission_mode"] = permission_mode
        r = self.run_guard("pre", data)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8"))
        out = r.stdout.decode("utf-8").strip()
        if not out:
            return None, ""
        hso = json.loads(out)["hookSpecificOutput"]
        self.assertIn(hso["permissionDecision"], ("ask", "deny"))  # never "allow"
        return hso["permissionDecision"], hso["permissionDecisionReason"]

    def stop(self, event="SubagentStop", actor=None, **fields):
        data = {"hook_event_name": event, **fields}
        if actor:
            data.update(agent_id="a1", agent_type=actor)
        return self.run_guard("stop", data)


class PreToolUseTests(GuardTestCase):
    def test_01_path_outside_the_project_is_silent(self):
        other = Path(tempfile.mkdtemp())
        try:
            self.assertEqual(self.pre(str(other / "x.py"), actor="planner"), (None, ""))
            self.assertEqual(self.pre(str(other / "CLAUDE.md")), (None, ""))
        finally:
            rmtree(other)

    def test_02_protected_paths_ask_the_main_thread_and_deny_subagents(self):
        level, reason = self.pre("CLAUDE.md")
        self.assertEqual(level, "ask")
        self.assertIn("claude.md is protected", reason)
        self.assertEqual(self.pre(".git/config")[0], "ask")
        for rel, actor in ((".claude/settings.json", "developer"), ("frontend/CLAUDE.md", "doc-keeper"),
                           (".claude/hooks/guard.config.json", "tester"), ("backend/Dockerfile", "developer"),
                           (".git/hooks/pre-commit", "debugger")):
            with self.subTest(rel=rel, actor=actor):
                self.assertEqual(self.pre(rel, actor=actor)[0], "deny")

    def test_03_bypass_mode_turns_asks_into_denials(self):
        level, reason = self.pre("CLAUDE.md", permission_mode="bypassPermissions")
        self.assertEqual(level, "deny")
        self.assertIn("bypass mode cannot ask the user", reason)
        self.assertEqual(self.pre("tests/test_a.py", permission_mode="bypassPermissions", **self.EDIT_TEST)[0], "deny")
        self.assertIsNone(self.pre("src/new.py", permission_mode="bypassPermissions")[0])

    def test_04_agent_type_without_agent_id_is_the_main_thread(self):
        level, reason = self.pre("tests/test_a.py", actor="developer", agent_id="", **self.EDIT_TEST)
        self.assertEqual(level, "ask")
        self.assertIn("actor=main agent_type=developer", reason)

    def test_05_roles_write_only_their_own_paths(self):
        for rel, actor in (("tasks/001-x/spec.md", "planner"), ("tasks/001-x/review.md", "reviewer"),
                           ("src/app.py", "developer"), ("src/pkg/deep/new.py", "Developer"),
                           ("docs/guide.md", "doc-keeper"), ("frontend/README.md", "doc-keeper"),
                           ("docs/issues/ISSUE-001-x.md", "debugger")):
            with self.subTest(rel=rel, actor=actor):
                self.assertEqual(self.pre(rel, actor=actor), (None, ""))
        level, reason = self.pre("tasks/001-x/spec.md", actor="reviewer")
        self.assertEqual(level, "deny")
        self.assertIn("'reviewer' may write only ['tasks/*/review.md']", reason)
        for rel, actor in (("src/app.py", "reviewer"), ("docs/guide.md", "planner"),
                           ("docs/guide.md", "developer"), ("NOTES.md", "developer")):
            with self.subTest(rel=rel, actor=actor):
                self.assertEqual(self.pre(rel, actor=actor)[0], "deny")

    def test_06_unknown_subagents_are_read_only_unless_allowed(self):
        level, reason = self.pre("src/new.py", actor="general-purpose")
        self.assertEqual(level, "deny")
        self.assertIn("actor=unknown agent_type=general-purpose", reason)
        self.assertIn("read-only", reason)
        self.config(unknown_subagents="allow")
        self.assertIsNone(self.pre("src/new.py", actor="general-purpose")[0])
        self.assertIsNone(self.pre("docs/any.md", actor="Explore")[0])
        self.assertEqual(self.pre("CLAUDE.md", actor="general-purpose")[0], "deny")
        self.assertIn("TEST-DISPUTE", self.pre("tests/test_a.py", actor="general-purpose", **self.EDIT_TEST)[1])

    def test_07_developer_cannot_edit_a_committed_test(self):
        level, reason = self.pre("tests/test_a.py", actor="developer", **self.EDIT_TEST)
        self.assertEqual(level, "deny")
        self.assertIn("locked at the RED commit", reason)
        self.assertIn("TEST-DISPUTE: <test> | <AC> | evidence | proposed change", reason)
        p = str(self.root / "Tests" / "Test_A.py").replace("\\", "/")  # mixed case
        if os.name == "nt":
            p = "/" + p[0].lower() + p[2:]  # and Git Bash style /c/Users/...
        self.assertIn("TEST-DISPUTE", self.pre(p, actor="developer", **self.EDIT_TEST)[1])
        (self.root / "tests" / "test_a.py").unlink()  # deleting it does not unlock it
        self.assertIn("TEST-DISPUTE", self.pre("tests/test_a.py", actor="debugger")[1])

    def test_08_new_test_files_follow_the_role_patterns(self):
        self.assertIsNone(self.pre("tests/test_new.py", actor="developer")[0])
        self.assertIsNone(self.pre("src/widget.test.ts", actor="developer")[0])
        self.assertEqual(self.pre("tests/test_new.py", actor="reviewer")[0], "deny")
        self.assertIsNone(self.pre("tests/test_new.py")[0])

    def test_09_test_writers_may_edit_committed_tests_anywhere(self):
        self.assertIsNone(self.pre("tests/test_a.py", actor="tester", **self.EDIT_TEST)[0])
        self.assertIsNone(self.pre("frontend/src/app.spec.ts", actor="tester")[0])  # outside its role patterns
        self.assertEqual(self.pre("src/app.py", actor="tester")[0], "deny")
        level, reason = self.pre("tests/test_big.py", actor="tester", content=lines(1001))  # still size-checked
        self.assertEqual(level, "deny")
        self.assertIn("1001 lines (limit 1000)", reason)

    def test_10_main_thread_is_asked_before_editing_a_committed_test(self):
        level, reason = self.pre("tests/test_a.py", **self.EDIT_TEST)
        self.assertEqual(level, "ask")
        self.assertIn("tests/test_a.py is a committed test", reason)

    def test_11_size_cap_blocks_growth_but_allows_shrinking(self):
        self.assertEqual(self.pre("src/big.py", content=lines(1001))[0], "deny")
        self.assertIsNone(self.pre("src/big.py", content=lines(1000))[0])
        level, reason = self.pre("tasks/001-x/spec.md", actor="planner", content=lines(301))  # first match wins
        self.assertEqual(level, "deny")
        self.assertIn("limit 300", reason)
        self.assertEqual(self.pre("CLAUDE.md", content=lines(201))[0], "deny")
        self.write("src/legacy.py", lines(1200))
        shrink = dict(tool="Edit", old_string="x0 = 0\n", new_string="")
        self.assertIsNone(self.pre("src/legacy.py", actor="developer", **shrink)[0])
        grow = dict(tool="Edit", old_string="x0 = 0\n", new_string="x0 = 0\ny = 1\n")
        self.assertEqual(self.pre("src/legacy.py", actor="developer", **grow)[0], "deny")

    def test_12_exempt_unsized_and_unlimited_files_are_ignored(self):
        self.assertIsNone(self.pre("package-lock.json", content=lines(5000))[0])
        self.assertIsNone(self.pre("src/fixtures/big.py", content=lines(5000))[0])
        self.assertIsNone(self.pre("src/data.json", content=lines(5000))[0])
        self.config(size_limits=[["src/*", 10, 20]])
        self.assertIsNone(self.pre("docs/long.md", content=lines(50))[0])  # no size limit matches
        self.assertEqual(self.pre("src/y.py", content=lines(21))[0], "deny")

    def test_13_projection_of_replace_all_multiedit_and_non_ascii(self):
        self.write("src/grow.py", "a\n" * 10)
        grow = dict(tool="Edit", old_string="a\n", new_string="a\n" * 110)
        self.assertEqual(self.pre("src/grow.py", replace_all=True, **grow)[0], "deny")
        self.assertIsNone(self.pre("src/grow.py", **grow)[0])
        self.write("src/two.py", "a\nb\n")
        edits = [{"old_string": "a\n", "new_string": "a\n" * 600}, {"old_string": "b\n", "new_string": "b\n" * 600}]
        self.assertEqual(self.pre("src/two.py", tool="MultiEdit", edits=edits)[0], "deny")
        # Cyrillic payload built from code points, so this source file stays ASCII
        cyrillic = "# " + "".join(map(chr, (0x43F, 0x440, 0x438, 0x432, 0x435, 0x442))) + "\n"
        self.assertIsNone(self.pre("src/ru.py", content=cyrillic * 10)[0])

    def test_14_empty_roles_disable_role_checks(self):
        self.config(roles={}, test_writers=[], unknown_subagents="allow")
        for rel in ("src/app.py", "docs/x.md", "tasks/001-x/spec.md", "tests/test_new.py"):
            with self.subTest(rel=rel):
                self.assertIsNone(self.pre(rel, actor="developer")[0])
        self.assertIn("TEST-DISPUTE", self.pre("tests/test_a.py", actor="tester", **self.EDIT_TEST)[1])
        self.assertEqual(self.pre("CLAUDE.md", actor="developer")[0], "deny")
        self.config(roles={}, test_writers=[])  # unknown_subagents stays read-only: only the main thread writes
        self.assertEqual(self.pre("src/app.py", actor="developer")[0], "deny")
        self.assertIsNone(self.pre("src/app.py")[0])


class PostStopCheckTests(GuardTestCase):
    def post(self, rel):
        return self.run_guard("post", {"hook_event_name": "PostToolUse", "tool_name": "Write",
                                       "tool_input": {"file_path": str(self.root / rel), "content": ""}})

    def test_15_post_warns_from_the_warn_size(self):
        self.write("src/w.py", "x\n" * 500)
        r = self.post("src/w.py")
        self.assertEqual(r.returncode, 2)
        self.assertIn("NOTE: src/w.py is 500 lines (warn 500, block 1000)", r.stderr.decode("utf-8"))
        self.write("src/w.py", "x\n" * 499)
        self.assertEqual(self.post("src/w.py").returncode, 0)
        self.write("src/fixtures/w.py", "x\n" * 900)
        self.assertEqual(self.post("src/fixtures/w.py").returncode, 0)
        self.assertEqual(self.post("../outside.py").returncode, 0)

    def test_16_subagent_stop_blocks_a_shell_edit_of_a_committed_test(self):
        self.write("tests/test_a.py", "def test_a():\n    pass\n")  # weakened through the shell
        r = self.stop(actor="developer")
        self.assertEqual(r.returncode, 2)
        self.assertIn("tests/test_a.py: committed test changed or deleted since HEAD", r.stderr.decode("utf-8"))
        self.assertEqual(self.stop(actor="reviewer").returncode, 2)  # every role that is not a test writer
        self.assertEqual(self.stop(actor="tester").returncode, 0)
        self.assertEqual(self.stop(actor="Explore").returncode, 0)  # read-only unknown subagent
        r = self.stop("Stop")  # main thread: informed, never blocked
        self.assertEqual(r.returncode, 0)
        self.assertIn("tests/test_a.py", json.loads(r.stdout.decode("utf-8"))["systemMessage"])
        (self.root / "tests" / "test_a.py").unlink()  # a deletion counts too
        self.assertIn("tests/test_a.py", self.stop(actor="debugger").stderr.decode("utf-8"))

    def test_17_stop_hook_active_short_circuits(self):
        self.write("tests/test_a.py", "")
        self.write("src/huge.py", lines(1001))
        for r in (self.stop(actor="developer", stop_hook_active=True), self.stop("Stop", stop_hook_active=True)):
            self.assertEqual((r.returncode, r.stdout, r.stderr), (0, b"", b""))

    def test_18_subagent_stop_checks_oversized_files_inside_its_own_paths(self):
        self.write("src/legacy.py", lines(1200))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "legacy")
        self.write("src/legacy.py", lines(1100))  # shrunk: fine
        self.assertEqual(self.stop(actor="developer").returncode, 0)
        self.write("src/huge.py", lines(1001))
        r = self.stop(actor="developer")
        self.assertEqual(r.returncode, 2)
        self.assertIn("src/huge.py is 1001 lines (limit 1000)", r.stderr.decode("utf-8"))
        self.assertNotIn("legacy", r.stderr.decode("utf-8"))
        self.assertEqual(self.stop(actor="doc-keeper").returncode, 0)  # not a path it may write
        r = self.stop("Stop")
        self.assertIn("src/huge.py is 1001 lines", json.loads(r.stdout.decode("utf-8"))["systemMessage"])
        self.config(unknown_subagents="allow")
        self.assertEqual(self.stop(actor="general-purpose").returncode, 2)

    def test_19_check_reports_ok_or_findings_since_a_commit(self):
        r = self.run_guard("check")
        self.assertEqual((r.returncode, r.stdout.decode("utf-8").strip()), (0, "guard check: OK"))
        base = self.git("rev-parse", "HEAD")
        self.write("tests/test_a.py", "def test_a():\n    pass\n")
        self.git("commit", "-q", "-am", "weaken the test")
        self.assertEqual(self.run_guard("check").returncode, 0)  # clean against HEAD
        self.write("src/huge.py", lines(1001))
        r = self.run_guard("check", args=["--since", base])
        out = r.stdout.decode("utf-8")
        self.assertEqual(r.returncode, 1, out)
        self.assertIn(f"tests/test_a.py: committed test changed or deleted since {base}", out)
        self.assertIn("src/huge.py is 1001 lines (limit 1000)", out)
        self.assertIn("guard check: 2 finding(s)", out)
        for args in (["--since", "no-such-rev"], ["--since"], ["--bogus"]):
            with self.subTest(args=args):
                self.assertEqual(self.run_guard("check", args=args).returncode, 2)

    def test_20_missing_or_invalid_config_fails_closed(self):
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Write",
                   "tool_input": {"file_path": str(self.root / "src" / "x.py"), "content": ""}}
        cases = {
            "not valid UTF-8 JSON": "{roles: }",
            "must hold one JSON object": "[]",
            "missing keys ['tests']": json.dumps({k: v for k, v in CONFIG.items() if k != "tests"}),
            "unknown keys ['test_writer']": json.dumps(dict(CONFIG, test_writer=[])),
            "test_writers must list names from roles": json.dumps(dict(CONFIG, test_writers=["qa"])),
            "unknown_subagents must be": json.dumps(dict(CONFIG, unknown_subagents="deny")),
            "not 'main' or 'unknown'": json.dumps(dict(CONFIG, roles={"main": []}, test_writers=[])),
            "with '/', not": json.dumps(dict(CONFIG, protected=["src\\secret.py"])),
            "0 < warn <= block": json.dumps(dict(CONFIG, size_limits=[["*", 1000, 500]])),
            "sized_extensions must be": json.dumps(dict(CONFIG, sized_extensions=["py"])),
        }
        path = self.hooks / "guard.config.json"
        for expected, text in cases.items():
            with self.subTest(expected=expected):
                path.write_text(text, encoding="utf-8")
                r = self.run_guard("pre", payload)
                self.assertEqual((r.returncode, r.stdout), (2, b""))
                self.assertIn("failing closed", r.stderr.decode("utf-8"))
                self.assertIn(expected, r.stderr.decode("utf-8"))
        path.unlink()
        for mode in ("pre", "post", "stop", "check"):
            with self.subTest(mode=mode):
                r = self.run_guard(mode, payload)
                self.assertEqual(r.returncode, 2)
                self.assertIn("guard.config.json is missing", r.stderr.decode("utf-8"))

    def test_21_malformed_payload_and_foreign_guard_fail_closed(self):
        r = self.run_guard("pre", b"{not json")
        self.assertEqual(r.returncode, 2)
        self.assertIn("not UTF-8 JSON", r.stderr.decode("utf-8"))
        self.assertEqual(self.run_guard("pre", b"[]").returncode, 2)
        r = self.run_guard("pre", {"tool_name": "Write", "tool_input": {}})
        self.assertEqual(r.returncode, 2)
        self.assertIn("no tool_input.file_path", r.stderr.decode("utf-8"))
        self.assertEqual(self.run_guard("stop", {"hook_event_name": "SubagentStop"}).returncode, 2)
        self.assertEqual(self.run_guard("bogus", {}).returncode, 2)
        other = Path(tempfile.mkdtemp())
        try:
            payload = {"tool_name": "Write", "tool_input": {"file_path": str(self.root / "x.py"), "content": ""}}
            r = self.run_guard("pre", payload, project=other)
            self.assertEqual(r.returncode, 2)
            self.assertIn("belongs to", r.stderr.decode("utf-8"))
        finally:
            rmtree(other)

    def test_22_utf8_bom_from_powershell_pipes_is_accepted(self):
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Write",
                   "tool_input": {"file_path": str(self.root / "CLAUDE.md"), "content": "x"}}
        r = self.run_guard("pre", b"\xef\xbb\xbf" + json.dumps(payload).encode("utf-8"))
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8"))
        self.assertEqual(json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_23_the_installed_config_is_valid(self):
        shutil.copy(HOOKS / "guard.config.json", self.hooks / "guard.config.json")
        r = self.run_guard("check")
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8") + r.stdout.decode("utf-8"))
        self.assertIn("guard check: OK", r.stdout.decode("utf-8"))

    def test_24_no_double_braces_in_the_guard_and_a_clear_roles_error(self):
        # setup checks search every installed file for two opening braces (an unfilled placeholder)
        self.assertNotIn("{" * 2, (HOOKS / "guard.py").read_text(encoding="utf-8"))
        self.config(roles=["developer"])
        r = self.run_guard("check")
        self.assertEqual(r.returncode, 2)
        self.assertIn("config roles must map each role name to a list of patterns", r.stderr.decode("utf-8"))

    def test_25_git_bash_style_project_dir_is_accepted_on_windows_only(self):
        def git_bash(path):
            p = str(path).replace("\\", "/")
            return "/" + p[0].lower() + p[2:] if os.name == "nt" else "/c" + p
        r = self.run_guard("check", project=git_bash(self.root))
        if os.name == "nt":
            self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8"))
            self.assertIn("guard check: OK", r.stdout.decode("utf-8"))
        else:  # /c/... is an ordinary path on macOS and Linux: no conversion, so it is a foreign project
            self.assertEqual(r.returncode, 2)
            self.assertIn("belongs to", r.stderr.decode("utf-8"))
        other = Path(tempfile.mkdtemp())
        try:
            r = self.run_guard("check", project=git_bash(other))
            self.assertEqual(r.returncode, 2)
            self.assertIn("belongs to", r.stderr.decode("utf-8"))
        finally:
            rmtree(other)


if __name__ == "__main__":
    unittest.main()
