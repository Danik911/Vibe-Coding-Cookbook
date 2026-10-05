# Editor notes for the cookbook draft

What I changed in your draft and why. Delete this file before you share the cookbook.
All product claims were checked against the vendors' documentation on 2026-09-25.

## Corrections to what you wrote

1. **Agent teams don't share a context window.** Each teammate has its own context window. They coordinate
   through a shared task list and a mailbox per agent, and the lead collects their results. The feature is still
   experimental (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`), and token use grows with every teammate. Your repo turns it
   off with `"0"` in `.claude/settings.json`.
   Source: https://code.claude.com/docs/en/agent-teams
2. **Subagents are mostly as you described, with two corrections.**
   - **You were right:** the main agent receives only the subagent's final summary, never its reasoning or tool calls.
   - **Transcripts are kept.** They are saved on disk (`~/.claude/projects/<project>/<session>/subagents/`) and you can
     open them from `/tasks`.
   - **Subagents can be resumed.** A subagent picks up again with its full history when the main agent sends it a
     message (`SendMessage`), so "stateless" is too strong.
   - **The cookbook now says:** subagents are isolated, and their context ends with the session. Your artifact-file
     advice stands.

   Source: https://code.claude.com/docs/en/sub-agents
3. **A hook can't launch the doc-keeper.** No hook can start a named subagent. The deterministic checks go in hooks:
   tests, file size, documentation drift. The order of steps goes in a skill (`/task`). A Stop hook can refuse to let
   the agent finish and give a reason, but the model still decides how to act on it. A SubagentStop hook that blocks
   sends its message to the subagent, not to the main agent.
   Source: https://code.claude.com/docs/en/hooks
4. **The workflow order was different in your draft.**
   - **Tester first:** the tester writes failing tests *before* the developer starts (RED). After the developer, the
     tester checks again (VERIFY).
   - **Debugger:** it runs only if VERIFY fails.
   - **Reviewer:** it was missing from your list of subagents. It runs after VERIFY and before the doc-keeper.
   - **Your end-to-end check:** it happens at the last gate (G3).
5. **AGENTS.md.** Claude Code now reads `AGENTS.md` natively, but by default only when there is no `CLAUDE.md`.
   Otherwise, import it from CLAUDE.md with `@AGENTS.md`.
   Source: https://code.claude.com/docs/en/memory
6. **PRP means two things.** In the community, a PRP is a "Product Requirement Prompt": a PRD plus curated codebase
   context plus a runbook for the agent (Rasmus Widing, https://github.com/Wirasm/prp). The old repository name,
   `PRPs-agentic-eng`, now redirects there. Your repository uses PRP to mean "product requirements plan". The cookbook
   explains both meanings.
7. **grill-me comes from Matt Pocock's skills repository** (https://github.com/mattpocock/skills). The current version
   there is a thin wrapper around a larger `grilling` skill. Your repository keeps the older nine-line version, which
   is a nice example of a minimal skill.
8. **The meta skill and the self-improvement skill.** Anthropic publishes an official meta skill, `skill-creator`,
   which writes skills, runs evaluations on them and tunes their descriptions. The cookbook recommends it alongside
   your own `meta-skill-guide`. For self-improvement, it pairs your `improving-skills` (the CAPTURE protocol) with
   Anthropic's `claude-md-management` plugin and the built-in auto memory. I quoted none of the example scenarios in
   `improving-skills`, because they name internal resources.
9. **"We don't need to validate every line."** I kept your point but reframed it: you don't read the lines, you check
   the behaviour through tests, reviews, static checks and hooks. I also softened "thousands of lines per minute" to
   "in minutes".
10. **MCP.** I kept Context7, Playwright and a cloud server (AWS knowledge in your repository; Azure MCP for Azure
    teams). I added two current facts:
    - Anthropic and Microsoft both say a CLI or a skill is often cheaper in tokens than an MCP server.
    - Claude Code now loads MCP tool schemas only when they are needed.
11. **Your list of folders.** The repository has decisions, issues, lessons learned, architecture, project structure
    and tests. It has no technical-debt or code-style folder:
    - **Code style** is enforced by the linters and `.claude/rules/`.
    - **Technical debt** sits in the reviewer's "Minor" notes and the issue catalog.

    The cookbook keeps your recommendation and shows where ServiceFlow keeps each item.

## Gaps in your own setup that the cookbook exposes

These are observations only. I changed nothing in the repository.

- **Deployment files are not protected.** Your draft says files that belong to DevOps are yours: workflows,
  deployment files, `.env`. `guard.py` protects `.env` reads (settings), `.claude/`, CLAUDE.md files, `.mcp.json` and
  the design contract. It does **not** protect `compose.yaml` or the `Dockerfile`s. The developer can edit those, and
  only the task gates would catch it. Adding them to the guard's SETUP class would make the cookbook's advice true of
  your own repository.
- **Your sound notifications aren't shared.** They live in `.claude/settings.local.json`, which is gitignored, so
  colleagues who clone the repository won't get them. The cookbook presents them as a personal setting.
- **Two docs have an outdated command.** `backend/README.md` and `ARCHITECTURE.md` still show plain
  `uv run lint-imports`. Only `CLAUDE.md` has the `PYTHONUTF8=1` fix (ISSUE-002). The cookbook quotes CLAUDE.md.

## Added after the blog research

On 2026-09-28 I checked about 90 posts, papers and docs, from Karpathy, Willison, Osmani, Beck, Böckeler
(martinfowler.com), Ronacher, Hashimoto, Steinberger, Yegge and others, plus productivity studies and security
reports. You asked for a light touch, so I added only these:
- **Intro, "What 'vibe coding' means here".** It gives Karpathy's original meaning and Willison's definition, and
  says what this cookbook actually teaches: "agentic engineering", with the autonomy slider.
- **§1.1, "Read by risk, not by volume".** Read the code where mistakes are expensive: money, security, client data
  and business rules. Never ship code you can't explain, which is Willison's rule. The paragraph includes his
  walkthrough prompt.
- **§1.3, "Git is your undo button".** Commit save points, work on branches, and learn the undo commands. It also
  covers the limits of `/rewind`: it does not restore subagent or shell edits.
- **§3.3, a warning before "Skills I recommend".** Read third-party skills, hooks and plugins before installing them.
  It includes Snyk's February 2026 scan (36.82% had a flaw, 76 confirmed malicious payloads) and Anthropic's plugin
  security page, and says to check `.claude/` in cloned client repositories.
- **Part 6, new principle 14, "Always keep a way back".** "Build while you learn" is now principle 15.

Not added, but researched and available if you want them later:
- security and client-data handling (retention, zero data retention, prompt injection, sandboxing);
- a playbook for existing client codebases;
- the productivity evidence (METR, DORA, Stack Overflow);
- cost and model choice;
- planned clean-up passes;
- the Learning output style.

## The Agentic Workflow Kit (Part 7)

`agentic-workflow-kit/` is the component that the cookbook's closing section hands to the reader's agent. It is one
Agent Skill, `setting-up-agentic-workflow/`, which works in Claude Code, Copilot, Codex and Cursor. It contains:
- **`SKILL.md`:** the procedure the agent follows: read the project, interview, dry-run for approval, render, verify,
  hand over.
- **`references/`:** the cookbook's rules, loaded only when needed.
- **`scripts/render.py`:** creates the files deterministically and never overwrites anything.
- **`templates/project/`:** the files it creates, with level markers.
- **A generic version of your guard:** config-driven, with its own unit tests.

Levels: Starter, Standard or Full, the autonomy slider.

It was built and checked in rounds:
- **Guard:** 25 unit tests, plus mutation checks.
- **Render script:** 17 tests. Every valid combination of level, instruction file and guard renders cleanly.
- **End-to-end tests:** agents playing a colleague ran the whole skill in sample projects:
  - Scenario A: a new project at Full.
  - Scenario B: an existing codebase at Standard, for a mixed Claude Code and Copilot team.

  Round 1 found real problems, including a Standard-level config that blocked every edit. Those led to the render
  script and the markers.

## Worth knowing: your setup is portable

The research for the "In other agents" boxes turned up a useful point for colleagues on other tools:
- **Shared formats:** GitHub Copilot, OpenAI Codex and Cursor all read `AGENTS.md`, support the same Agent Skills
  format (`SKILL.md` folders), and have subagents and hooks.
- **Claude Code files:** Copilot (in VS Code) and Cursor also read `CLAUDE.md`, `.claude/skills/` and
  `.claude/agents/`, and Cursor loads Claude Code hooks by default.

So most of what the cookbook shows transfers with little change.

## How this draft was checked

- **Written by subagents.** Four subagents wrote the parts in parallel, and one more researched Copilot, Codex and
  Cursor. Each wrote a file, which I merged. This is the artifact pattern from Part 3.4.
- **Checked by an independent subagent.** A separate subagent, which had not written anything, fact-checked the
  merged draft:
  - **Repo excerpts:** all verbatim. Two line ranges were off by one; both are fixed.
  - **Numbers:** all correct.
  - **Claude Code quotes:** all match the current docs.
  - **Other issues:** 1 error, 8 warnings and 23 notes. All are fixed, including:
    - "Bypass mode skips ask rules." It doesn't: explicit `ask` rules still prompt.
    - The 5.4 hook recipe failed open on a crash.
    - Plan mode is not a hard block in every setup.
    - Not every subagent loads CLAUDE.md.
- **The 5.4 recipe was run in five situations**, and each behaved as the text says:
  - a crash blocks with exit 2;
  - `stop_hook_active` lets the developer stop;
  - a missing project folder blocks;
  - a failing suite blocks and sends the output back;
  - your real green backend suite passes with exit 0.
- **Rendering:** the mermaid chart renders (mermaid-cli), the table of contents anchors match the headings, and the
  code fences are balanced.

## Length

The draft is about 1,840 lines (about 105 KB), more than the ~1,300 I planned. About a third of it is verbatim excerpts. If
you want it shorter, the easiest cuts are:
- the longer excerpts in 4.2 (the task 002 walkthrough);
- the full `mode_stop` function in 5.3;
- the `.mcp.json` listing in 3.6.

## Things to confirm

- I wrote "Most of its code is written by agents following the workflow in Part 4" in the introduction. Please check
  that this is accurate.
- The presentation-skill anecdote (Part 3.3) says only what you told me: you built a skill for EY-style
  presentations. Add the details you want to share.
- Real names are kept (ServiceFlow AI, MSL Motor Group, Mercedes-Benz, Ireland), as you chose. None of the PRP's sample
  people (the hero repair order's customer, advisor or technician) appear in the cookbook.
- **Principle 3 ("Talk to your agent")** says "I dictated the first outline and the agent structured it". I inferred
  this from your message; delete the sentence if it isn't true.
- **Voice dictation at EY.** `/voice` in Claude Code works only with a Claude.ai login, not an API key, Bedrock or
  Foundry, and it sends the audio to Anthropic. If EY colleagues use Claude through a cloud provider, the Win+H
  fallback is the one they'll use. The principle says to check the firm's policy first.
- Part 2.2 quotes the source line of `PRODUCT_SPEC.md`, which names Maks Kampinen as the spec's author. Keep it or
  replace it with "our product partner".
