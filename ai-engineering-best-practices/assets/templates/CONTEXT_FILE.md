# Context file: {{title}}

> Use when: creating or reviewing a file in the enterprise context layer (definitions, rules, reference data, documents the agent reads as tools), or specifying what a decision record must contain.
> Fill with the developer; don't invent facts — leave TODO where unknown.

> Guidance: The context layer gives the agent four kinds of context: what the data means, how the work is done, what the agent may see and do, and where it came from. Business teams and data governance own the files; the agent only reads them. Every file names its source system, owner and review date, and every answer the agent gets names the file it came from. Remove the `> Use when`, `> Fill` and `> Guidance` lines when done.

## 1. Header (every file)

For a YAML file, put the header at the top; for a Markdown document, put it in front matter.

```yaml
# {{One or two lines: what the file holds and who reads it.}}

source:
  system: {{the system this stands in for, e.g. Policy administration}}
  owner: {{accountable owner, e.g. Product}}
  reviewed: "{{YYYY-MM-DD}}"
version: "{{document version, if the file is a versioned document}}"
```

| Field | Rule |
| --- | --- |
| title | what the file is, in the owner's words |
| source (system) | where the data really comes from; one system per file |
| owner | a role or team that can answer for it, not a person who may leave |
| reviewed | the date the owner last confirmed it; set a review interval and flag stale files |
| version | for documents whose version goes on decisions (such as a manual or a wording) |

Example (UnderCover): `source: {system: Claims operations, owner: Head of claims operations, reviewed: "2026-09-01"}`, plus `version: "2026.2"` on the claims manual.

## 2. Body shapes

> Guidance: One shape per file. Keep entries short and in the owner's own words. Each entry names where in the source it comes from, so the agent can cite it.

### Glossary (defined terms)

```yaml
terms:
  - term: {{Term}}
    definition: {{the definition in the source document's own words}}
    sections: [{{section number}}]
```

### Rules (how the work is done)

```yaml
rules:
  - rule: {{machine_name}}
    name: {{Readable name}}
    {{number: 90, with its unit, e.g. days}}
    applies: >-
      {{When and how the rule applies, including how to count.}}
    sections: [{{Source document and section}}]
```

### Reference data (facts from outside, with provenance and dates)

```yaml
topics:
  - topic: {{events | places | products}}
    description: {{what these facts are and where they come from}}
    facts:
      - >-
        {{Provider, date: the fact, with the dates it applies to.}}
```

### Data dictionary (what each field means)

```yaml
records:
  - record: {{record name}}
    description: {{what the record is}}
    source_system: {{system}}
    fields:
      - field: {{field_name}}
        meaning: {{what it means, and common mistakes in filling it}}
        values: [{{allowed values, if a closed set}}]
        personal: {{true | false}}
```

### Documents (policy wording, manuals, procedures)

Markdown with the front matter above, numbered headings so answers can cite a section, and a version number stated in the first paragraph.

## 3. How the layer serves them

- Loaded once when the server starts; read-only; one lookup tool per file kind (search, read a section, define a term, apply a rule).
- Each answer names its files with source, owner and review date.
- Nobody but the owner changes a file; changes go through the owner's review and bump `reviewed` and `version`.
- Personal fields are marked, so privacy rules can apply to them.

## 4. The decision record the agent must write

> Guidance: The context layer also says what a finished decision must contain. The app should refuse a record that falls short and say what is missing, and treat a decision with no reason on file as not yet made. Adapt the fields to your domain; the shape below is claims manual section 14.

| Field | Content |
| --- | --- |
| decision | {{approve / decline / refer}} |
| amount | {{payout or other quantity}} |
| calculation | {{line by line, produced by code; must equal the amount}} |
| section relied on | {{document and section that supports it}} |
| reason | {{plain language, 2 or 3 sentences}} |
| made by, and when | {{the agent with its version, or the check that made it; timestamp}} |
| sign-off | {{for an amount over the limit: who signed off, and when}} |
| document version in force | {{version of the manual or wording applied}} |

Example (UnderCover): the claims manual's section 14 asks for exactly this, plus the manual's own version; a referral by the security check has no section of the wording, so its section says it came from the security check.
