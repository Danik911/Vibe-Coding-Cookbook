# Product

What we build and why. Everything downstream is cut from this folder: the product spec from the raw inputs, PRPs from
the spec, task specs from a PRP's task table. Agents read it before they plan.

| Path | What it holds |
|---|---|
| `inputs/` | Raw material as received: user stories, requirements, emails, call notes and transcripts, screenshots of the current process. One file per source, translated into the repository's language, with the source and date at the top. Stored as received, never rewritten. |
| `PRODUCT_SPEC.md` | The product specification: vision, the business problem, users, core flows, the outcomes we can measure, the rules the software must obey, what is out of scope, open questions. Written from the inputs with the user, or stored verbatim when the product owner supplies it. |
| `PRP-NNN-slug.md` | One product requirements plan per milestone, copied from [PRP-TEMPLATE.md](PRP-TEMPLATE.md): goal, audience, scope, domain rules, architecture and the ordered task table that task specs are cut from. Updated in place when a decision changes. |

The main thread writes these with the user; the doc-keeper keeps links and facts current. Read each PRP line by line <!-- if:full -->
The agent writes these with the user and keeps links and facts current. Read each PRP line by line <!-- if:lite -->
before its first task: everything downstream inherits its mistakes.

"PRP" here means *product requirements plan*. The term also names Rasmus Widing's *Product Requirement Prompt*, a
product requirements document plus the codebase context and runbook an agent needs (https://github.com/Wirasm/prp).
