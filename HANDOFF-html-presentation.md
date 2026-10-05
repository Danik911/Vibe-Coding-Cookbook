# Handoff: HTML presentation of The Vibe Coding Cookbook

## Goal Description
- Turn `COOKBOOK.md` into an **HTML slide presentation** that the author (an EY consultant) can present to EY
  colleagues and share afterwards. It should carry the cookbook's story and key ideas, not its full text. It ends by
  pointing colleagues to the Agentic Workflow Kit, so they can set up their own workflow with their own agent.
- Audience: EY consultants of mixed technical depth. Some code every day; some have never used a coding agent.

## Current State
- Folder: `C:\Users\anteb\Desktop\Vibe-Coding-Cookbook\` (not a git repository). Paths below are relative to it.
- **The cookbook is a finished draft:** `COOKBOOK.md`, ~1,875 lines, ~110 KB, English, written in the author's first
  person. Every product claim in it was checked against vendor documentation (2026-09-25 / 2026-09-28), and every
  excerpt is quoted verbatim from a real project, ServiceFlow AI.
- **The kit is built and tested:** `agentic-workflow-kit/` is an Agent Skill that interviews a colleague and sets up
  the workflow in their project.
- **Decisions already made by the author (do not reopen them):**
  - Keep real names (ServiceFlow AI, MSL Motor Group).
  - The title stays "The Vibe Coding Cookbook". A short section defines vibe coding versus agentic engineering, with
    the "autonomy slider".
  - Claude Code comes first, with short notes on Copilot, Codex and Cursor.
  - Review is risk-based ("read by risk, not by volume").
  - Git is the undo button.
  - Warn to read third-party skills and hooks before installing them.
  - Part 7 hands off to the kit.
- **No presentation work has started.**

## Tasks Done
- `COOKBOOK.md` written, fact-checked by an independent agent (1 error, 8 warnings and 23 notes, all fixed), then
  extended after research of about 90 sources.
- The kit is written and tested:
  - 17 render-script tests and 25 guard tests pass.
  - End-to-end runs in sample projects: scenario A2 passed; scenario B2's one major finding was fixed and covered by
    tests, but not re-run end to end.

## Tasks To Do
1. **Ask the author the open questions** under Issues / Blockers before designing anything.
2. **Draft the slide outline** (the storyline below is a starting point) and get the author's approval.
3. **Build the presentation** as one HTML file.
4. **Check every fact and number** against `COOKBOOK.md`, then check the slides visually in a browser.
5. **Hand it to the author for review.** Never call it done before the author confirms.

## Files / Important Paths
| Path | Status | Why it matters |
|---|---|---|
| `COOKBOOK.md` | read only | The only source of content. Section map below. |
| `EDITOR_NOTES.md` | read only, **never present** | Author-only notes. Its "Things to confirm" list names content that is not yet confirmed. |
| `agentic-workflow-kit/README.md` | read only | Source for the closing slides (install, levels, how to start). |
| `presentation/vibe-coding-cookbook.html` | to create | The deliverable (suggested path; confirm with the author). |

**Section map of `COOKBOOK.md`** (line numbers as of this handoff):

| Lines | Section | Slide material |
|---|---|---|
| 1–72 | Title, how to read, "What vibe coding means here", the ServiceFlow example | Karpathy and Willison definitions; autonomy slider; components table |
| 73–106 | 0. Pen and paper | The five-line template (Goal, Done when, Out of scope, Approach, How I check); plan mode |
| 107–246 | 1. Environment: who owns what | Ownership table (1.1); "read by risk"; permissions excerpt (1.2); git undo commands (1.3) |
| 247–460 | 2. Workflow foundation | Skeleton; raw inputs; PRP (two meanings); ADR with "Revisit when"; reuse ladder; living architecture |
| 461–917 | 3. Components | CLAUDE.md as a roadmap; memory layers table; skills and lazy loading (186 vs 3,024 lines); the warning about third-party skills (Snyk numbers); subagents (pros/cons, six roles table); agent teams (correction); MCP |
| 918–1231 | 4. Running the workflow | Loop diagram (mermaid, 4.1) plus stage table; task 002 story (124 RED tests → 128 passing → reviewer finds €354 instead of €402 → ISSUE-003 → one-line fix); FULL/LIGHT/TRIVIAL; issue catalog |
| 1232–1619 | 5. Guardrails | Guidance vs enforcement; allow/ask/deny; the guard (size caps: 15,534-line router evidence); SubagentStop recipe; doc-keeper ordering; notifications; static-checks table |
| 1620–1689 | 6. Principles | "No one size fits all" plus the 15 principles (talk to your agent, always keep a way back, build while you learn with the Karpathy quote) |
| 1690–1726 | 7. Your turn | Hand the kit to your agent: 3 steps, levels table |
| 1727–1875 | Appendix | Glossary, starter prompts, sources |

## Resources / Links
- `COOKBOOK.md` › Appendix C: every source URL. Cite from there; do not add new sources without checking them.
- `agentic-workflow-kit/README.md`: install table per tool and the level descriptions.
- For publishing as a claude.ai Artifact instead of a local file: the Artifact tool's rules allow external scripts
  only from cdnjs.cloudflare.com or cdn.jsdelivr.net, and require light and dark themes (load the `artifact-design`
  skill first).

## Issues / Blockers (ask the author first)
- **Style:** the author has an **EY-style presentation skill** (colours, fonts, slide rules) from earlier work. It is
  not in this folder. Ask for it, or for the EY brand guidance, before designing. Do not guess EY brand values from
  memory.
- **Length and use:** a live talk (how many minutes? speaker notes?) or a self-read deck? This decides the slide count
  (roughly 20–30 for a 30–45-minute talk).
- **Format:** a single self-contained HTML file that works offline and can be emailed (the default), or a published
  claude.ai Artifact link?
- **Unconfirmed content** (from `EDITOR_NOTES.md` › Things to confirm): the sentence "I dictated the first outline
  and the agent structured it" (Principle 3), "Most of its code is written by agents" (intro), and naming the spec
  author Maks Kampinen (§2.2). Leave these off the slides unless the author confirms them.

## Gotchas / Risks
- You have no conversation history; this file and `COOKBOOK.md` are your context.
- **Facts come only from `COOKBOOK.md`.** No new numbers, studies or quotes. Quotes stay verbatim and attributed
  (Karpathy, Willison, Anthropic docs, Snyk). The research behind the cookbook also found productivity studies (METR,
  DORA) and security incidents, but the author chose to leave them out. Do not add them.
- **Tone:** plain English, no marketing words, no emoji, the author's voice ("I"). Slides carry one idea each, not
  paragraphs.
- **Code on slides:** only short excerpts (5–10 lines) that make one point, such as the guard's size-limit table, the
  one-line `totals()` fix, or a deny rule. Keep the source path label.
- **The mermaid diagram (§4.1):** in an offline file, redraw it as inline HTML/SVG. Do not load mermaid from a CDN.
- **Do not modify** `COOKBOOK.md`, `EDITOR_NOTES.md` or `agentic-workflow-kit/`.

## Validation / Tests
- Not run: nothing presentation-related exists yet.
- For the deliverable:
  - Open it in a browser (Playwright MCP, if available) at 1920×1080 and 1440×900, and screenshot every slide: no
    overflow or cut-off text, and code readable.
  - Check keyboard navigation (arrows, Home/End) and print to PDF, one slide per page.
  - Check every number and quote on the slides against `COOKBOOK.md`, and list them in your report.

## Next Steps
1. Read `COOKBOOK.md` in full, then `agentic-workflow-kit/README.md`.
2. Ask the author the questions under Issues / Blockers, one at a time.
3. Propose the slide outline (title, one-line message, source lines per slide), and wait for approval.
4. Build `presentation/vibe-coding-cookbook.html`, verify it, and report.

## Prompt for Receiving Agent / Expected Output
```text
Context:
You are creating an HTML slide presentation from "The Vibe Coding Cookbook", a finished guide by an EY consultant
for EY colleagues on building software with AI coding agents (Claude Code first; Copilot, Codex, Cursor noted). The
source is C:\Users\anteb\Desktop\Vibe-Coding-Cookbook\COOKBOOK.md (~1,875 lines; Parts 0-7 plus an appendix). It
ends by handing colleagues a companion "Agentic Workflow Kit" (agentic-workflow-kit/README.md). Read
HANDOFF-html-presentation.md in the same folder first: it has the section map, the decisions already made, and the
open questions.

Limitations:
- Content comes only from COOKBOOK.md and the kit README. No new facts, numbers, studies or quotes. Quotes stay
  verbatim and attributed.
- Never show anything from EDITOR_NOTES.md. Leave its three unconfirmed items off the slides unless the author
  confirms them.
- Do not modify COOKBOOK.md, EDITOR_NOTES.md or agentic-workflow-kit/.
- Do not guess EY brand values. Ask for the author's EY presentation skill or brand guidance.
- Plain English, no emoji, no marketing language, one idea per slide.
- Single self-contained HTML file unless the author chooses otherwise: inline CSS and JS, no external requests.

Expectations:
- presentation/vibe-coding-cookbook.html: 16:9 slides; keyboard navigation (arrows, Home, End); a slide counter;
  prints to PDF one slide per page; readable code excerpts with source labels; optional speaker notes if the author
  wants them.
- A short report: slide list (title and source lines), every number and quote used with its COOKBOOK.md line, the
  screenshots taken, and open questions.
- Never claim it is done before the author has reviewed it.

Actions:
1. Read COOKBOOK.md fully and the kit README.
2. Ask the author, one question at a time: EY style source, talk length or self-read, format, speaker notes, and the
   three unconfirmed items.
3. Propose an outline (about 20-30 slides) following the cookbook's order: definition and autonomy slider, pen and
   paper, who owns what, foundation, components, the task 002 story, guardrails, principles, "Your turn" with the
   kit. Wait for approval.
4. Build the file. Redraw the Part 4 workflow diagram as inline SVG/HTML.
5. Verify in a browser at 1920x1080 and 1440x900 with a screenshot per slide, check every fact against
   COOKBOOK.md, then report.

Resources:
- COOKBOOK.md: the content (section map in the handoff).
- HANDOFF-html-presentation.md: decisions, open questions, risks.
- agentic-workflow-kit/README.md: closing slides (install per tool, levels, how to start).
- COOKBOOK.md Appendix C: source URLs for any citation on a slide.
```
