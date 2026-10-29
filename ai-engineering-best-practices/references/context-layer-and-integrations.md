# Context layer and enterprise integrations

> When to read this: the agent needs the business's own knowledge (definitions, rules, manuals, reference data), you must decide where each kind of data lives (context layer, memory, database, gateway), or the client asks how the agent connects to enterprise systems and how its decisions are audited. Also read it before any "give the agent access to our data" conversation.

## Contents

- [Key principles](#key-principles)
- [From context engineering to the enterprise context layer](#from-context-engineering-to-the-enterprise-context-layer)
- [The gateway and the sources of data](#the-gateway-and-the-sources-of-data)
- [Source, owner and review date on every file](#source-owner-and-review-date-on-every-file)
- [Building the context layer as an MCP server](#building-the-context-layer-as-an-mcp-server)
- [Deploying it behind the gateway](#deploying-it-behind-the-gateway)
- [How the agent reaches it](#how-the-agent-reaches-it)
- [Memory, briefly](#memory-briefly)
- [Auditability](#auditability)
- [Enterprise data concerns and integration questions](#enterprise-data-concerns-and-integration-questions)
- [Enterprise MCP architecture](#enterprise-mcp-architecture)
- [The market as taught](#the-market-as-taught-oct-2026)
- [Decisions to make with the developer](#decisions-to-make-with-the-developer)
- [Pitfalls and anti-patterns](#pitfalls-and-anti-patterns)
- [In UnderCover](#in-undercover)

## Key principles

1. **Give the agent the business's knowledge as a governed, read-only service, not as text pasted into a prompt.** An agent with access to every record still gets rules wrong (for example applying a deductible to a benefit it does not cover) unless the wording's rule is in front of it at run time. Lookups also keep the prompt small and the content current.
2. **Every piece of data has one owner, and the owner is not the agent.** Business teams own the context layer, the security team owns gateway policy, the app owns the database, the agent owns only its own notes. Who writes a source decides how the agent may touch it.
3. **Most of a context layer is old data governance.** Glossaries, data dictionaries, procedure manuals, access controls and lineage already exist in mature clients. Find them and expose them; do not invent a parallel set that nobody reviews.
4. **Each file names its source system, its owner and its review date.** The agent, the handler and the auditor can then see where an answer came from and how stale it might be.
5. **The agent reaches business records only through the app's API.** The API enforces the rules and the checks; a direct database connection bypasses all of them.
6. **Put the context layer behind the same gateway as the company's APIs.** One MCP client, one tool list, one place for authentication and policy. The context layer is read-only, so the gateway can allow it freely.
7. **Keep the agent's memory apart from business-owned truth.** Memory holds what the agent noticed about a customer. Rules, wording and plans belong in the context layer; counts that drive a rule (such as repeat claims) come from the records.
8. **Fill in identity in code, not in the model's tool inputs.** The agent's tools supply the claim id, the customer and who is deciding. The model cannot ask for another customer's data, so a data-boundary rule becomes a property of the system.
9. **Make every decision auditable in full.** Record what was decided, the calculation, the rule relied on, who or what decided and when, which version of the manual applied, and which context was looked up. Reject an incomplete record at the API.
10. **Do not edit governed content to make the agent work.** If a source is wrong or unclear, route the fix to its owner. The agent's engineer owns the server and the tools, not the facts.

## From context engineering to the enterprise context layer

Context engineering (named in mid-2025; Philipp Schmid's version: get the right information and tools to the model, in the right format, at the right time) covers instructions, the user prompt, tools, short- and long-term memory, retrieved information and structured output. The enterprise context layer (Atlan's definition, June 2026, as taught: a system that turns an organisation's knowledge, expertise and norms into context machines can use) applies the same idea at company scale and makes it a governed asset rather than a prompt-writing craft.

It has four parts. The course teaches them as the four kinds of context an agent needs at run time, usually delivered over MCP:

| Part | The question it answers | Typical content | Where it lives in UnderCover |
|---|---|---|---|
| What the data means | What does this field or term mean here? | Data dictionary, glossary, reference data, plan limits | Context layer |
| How the work is done | What is the procedure and what are the rules? | Procedures, manuals, business rules | Context layer (claims manual, claim rules) |
| What the agent may see and do | Is this agent allowed to look at or do this? | Permissions, approvals, limits | Gateway Policy, the agent's IAM role, the approval limit (Week 3 Day 2) |
| Where it came from | Who says so, and how fresh is it? | Source, owner, lineage, review date | Each file's header, repeated in every answer |

Gartner's note on master data management (June 2026, titled as taught "How Master Data Management Boosts the Context Layer for AI Agents") says MDM strengthens a context layer by supplying semantics (what the data means), provenance (where it came from) and operational state (one golden record per customer and product). Use this when a client says "we have no context layer": ask about their MDM, data catalog and governance team first.

Most of this is long-standing governance work. The new part is serving it to an agent as tools, with the source attached to every answer. Slide 52's lesson: three of the four parts are the context layer you build; the fourth (what the agent may see and do) is the gateway and IAM you already built in the security work (see [security-and-guardrails.md](security-and-guardrails.md)).

## The gateway and the sources of data

The agent works with a gateway and three sources of data (slide 53), which the later production slide (slide 72) calls four sources of data and integration. Each has a different owner and a different access mode:

| Source | Owner (who writes it) | What it holds | How the agent reaches it | Read / write |
|---|---|---|---|---|
| Gateway | Security team | Rules for tool calls, such as the payout limit | Every call passes through it | Cannot change it |
| Context layer | Business teams (data governance model) | Data from other systems: definitions, plans, rules, reference data, documents | As tools through the gateway | Reads only |
| Memory | The agent | Its own notes, kept separately for each customer (or handler) | Its memory tools, straight to the memory service, limited by its IAM role | Reads and writes |
| Database | The app and the agent | Records and checkpoints: the system of record | Through the app's API, never directly | Reads and writes, with the app checking each write |

Placement test for any piece of data:

| If it is... | Put it in... |
|---|---|
| Knowledge a business team owns and reviews (definitions, rules, manuals, plans, outside facts) | Context layer |
| A statement the agent learned from working with someone, useful on their next visit | Memory |
| A record with state that must be correct and transactional (claims, payments, decisions, customers) | Database, via the app's API |
| A rule about whether a tool call is allowed (limits, who may call what) | Gateway policy |
| Short, stable, needed on every call | The agent's instructions |

UnderCover keeps the two governing documents at the end of the agent's instructions and also serves them as lookups. That is a trade-off: the instructions cost tokens on every call but never depend on a tool call; lookups are cheaper and can be as large as needed but the model must decide to ask. Large or volatile content belongs behind lookups.

## Source, owner and review date on every file

Every context file starts with a header naming where it came from. YAML files carry it at the top; Markdown documents carry it as front matter, together with a version.

```yaml
source:
  system: Claims operations        # the system of record or provider it stands in for
  owner: Head of claims operations # a role that can answer for the content
  reviewed: "2026-09-01"           # when the owner last checked it
```

```markdown
---
source:
  system: Claims operations
  owner: Head of claims operations
  reviewed: "2026-09-01"
version: "2026.2"
---
```

UnderCover's seven files, each standing in for a system a real client has (as taught, slide 60):

| File | Holds | Source system | Owner |
|---|---|---|---|
| `data_dictionary.yaml` | Meaning of each field the agent sees | The data catalog | Data governance |
| `glossary.yaml` | Defined terms from the policy wording | The policy wording | Legal |
| `plans.yaml` | Each plan's limits, waiting periods, deductible, add-ons | Policy administration | Product |
| `claim_rules.yaml` | Filing window, look-back, repeat claims, meals without receipts | Claims operations | Head of claims operations |
| `reference_data.yaml` | Outside events, places, product prices | Outside data providers | Claims operations |
| `policy_wording.md` | The contract, by numbered section | Published policy documents | Legal |
| `claims_manual.md` | How handlers work a claim, by numbered section | Claims operations | Head of claims operations |

Rules for the headers (see [the template](../assets/templates/CONTEXT_FILE.md)):

- Require all three fields; fail the server at start-up, or in CI, if one is missing. A file without an owner has nobody to fix it.
- Return the header with every answer drawn from the file (file name, system, owner, reviewed). The agent, the claim page and the audit trail all use it.
- Version documents that decisions depend on, and stamp the version on every decision record.
- Show the review date to humans and treat an old one as a prompt to ask the owner, not as proof the content is wrong. Decide a staleness threshold with the owner (a default such as "older than the review cycle" works, but the course does not set one).
- Where an app also needs the same facts (UnderCover's payout check reads the plans), seed both from the one governed file so the app and the agent never disagree.
- Never edit a governed file as a side effect of a build. Ask the owner.

## Building the context layer as an MCP server

The context layer is its own small service: an MCP server (FastMCP from the `mcp` package, as taught) with read-only lookup, search and read tools over the files. Keeping it separate from the app lets data governance own it, lets the gateway govern it, and lets any agent use it (the Copilot reuses the same seven tools).

UnderCover's tools (names and shapes are from the final build):

| Tool | Input | Answers |
|---|---|---|
| `lookup_term` | `term` | The glossary definition and its wording sections, matched whatever the case; for an unknown term, the list of terms it does define |
| `describe_fields` | `record`: claim, policy or previous_claim | The data dictionary's fields and what they mean |
| `get_plan` | `plan`: economy, premium or first | Limits, waiting periods, deductible, which benefits the deductible applies to, add-ons |
| `get_claim_rules` | none | The claim rules |
| `search_reference_data` | `query` | Facts containing every word of the query, each with its topic |
| `search_documents` | `query` | Sections of the wording and manual whose title or text contains the phrase, with the matching paragraphs and the file of each |
| `read_section` | `document`, `number` | One numbered section in full, with the document's title and version |

Design rules:

1. **Read-only, annotated so.** Mark every tool `readOnlyHint`. The server writes nothing and reads only files from its own package.
2. **Load once, serve many.** Read and parse the files when the process starts, never per request. Split documents at their numbered headings into sections tagged with document, number and title; keep the front matter out of the sections.
3. **Every answer carries its sources.** Return a `sources` list (file, system, owner, reviewed). A search that finds nothing returns no sources.
4. **Small, strict inputs.** One-line docstring as the tool description, no optional inputs, `Literal` types for closed sets (record names, plan names, document names). A model cannot misspell an enum.
5. **Refusals with a reason.** An unknown section raises a refusal with its reason; an unknown glossary term returns the list of terms that exist, so the model can correct itself.
6. **State matching behaviour in the description.** Document search matches the phrase as written; say so, or make the match word-based (see pitfalls).
7. **Stateless HTTP.** Serve MCP at `/mcp`, stateless, JSON responses, so it runs unchanged on a laptop and on Lambda.

```python
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

READ_ONLY = ToolAnnotations(readOnlyHint=True)

def build_server(security=None) -> FastMCP:
    server = FastMCP("undercover-context", port=8006, stateless_http=True,
                     json_response=True, transport_security=security)

    @server.tool(annotations=READ_ONLY)
    def lookup_term(term: str) -> dict:
        """Look up a term the policy wording defines: its definition and sections."""
        return files.lookup_term(term)   # answer includes "sources": [...]

    return server
```

```python
def lookup_term(term: str) -> dict:
    for entry in GLOSSARY["terms"]:
        if entry["term"].lower() == term.strip().lower():
            return entry | {"sources": [GLOSSARY["source"]]}
    return {"answer": f'The glossary does not define "{term}". These are the terms it does.',
            "terms": [e["term"] for e in GLOSSARY["terms"]],
            "sources": [GLOSSARY["source"]]}
```

Start it with a one-line command beside the backend in development (UnderCover: `uv run -m context`, port 8006, started by `npm run dev`).

## Deploying it behind the gateway

As taught on AWS (Oct 2026; deployment mechanics live in [production-deployment-aws.md](production-deployment-aws.md)):

- **Package and function.** The context layer gets its own dependency group with only what the server needs (the MCP package, Mangum, a YAML reader) and its own zip: the `context/` folder plus those packages built for Linux and Python 3.12. It needs no environment variables because everything it serves is in its package.
- **Function URL with `AWS_IAM` auth.** Unlike the app's public URL, only callers signed with AWS credentials allowed to invoke it can reach it. The gateway's role is allowed; an unsigned request is refused.
- **A fresh MCP server for each Lambda request.** Mangum wraps every request in the app's start-up and shutdown, while FastMCP's session manager can only be started once. So build the server inside the handler and read the files once, at import. When the host is local, FastMCP turns on DNS-rebinding protection, which refuses a Function URL's host; turn it off on Lambda, where IAM auth guards the server.

```python
def handler(event, context):
    app = build_server(TransportSecuritySettings(enable_dns_rebinding_protection=False)).streamable_http_app()
    return Mangum(app, lifespan="auto")(event, context)
```

- **A gateway target for the server.** The Gateway can take three kinds of target: an OpenAPI described API, a Lambda function, or an MCP server. The app is an OpenAPI target with its API key held in AgentCore Identity and sent as a header. The context layer is an MCP server target whose outbound credential is the gateway's own IAM role signing for the `lambda` service, so the context layer needs no key.
- **Policy is deny by default once an engine is attached.** Add a Cedar `permit` for each target's tools, and keep the `forbid` rules (for example a payment over a limit) beside them. See [security-and-guardrails.md](security-and-guardrails.md).
- **Tool names.** The Gateway names each tool `<target>___<operation>` (`undercover-context___lookup_term`). The agent sees one list of tools from all targets.
- **Propagation delay.** A new role or permission may take up to a minute before AgentCore sees it. Make deployment scripts retry when they see "role" errors or "Failed to obtain execution role credentials".
- **Teardown.** Delete targets before the gateway and policies before the engine; the Lambda functions can stay for later builds.

On a free route, the context layer runs on the laptop beside the agent (no Gateway, no Memory) and the app runs on Render. The design survives because the agent's tools sit on a route abstraction (next section).

## How the agent reaches it

Give the agent two interchangeable routes to the same tools, chosen when a run is built, not on import:

| Route | When | Tools reach | Signing |
|---|---|---|---|
| Gateway | `UNDERCOVER_GATEWAY_URL` is set | `undercover-app___<op>` and `undercover-context___<tool>` over MCP streamable HTTP | AWS SigV4 for `bedrock-agentcore`, with the AWS CLI's credentials and region |
| Direct | not set | The app's API with the agent's key; the context layer over MCP at its own URL | Key for the app; none for the local context layer |

```python
class Route(Protocol):
    def call(self, target: Target, operation: str, inputs: dict) -> Any: ...
    def name(self, target: Target, operation: str) -> str: ...
```

Practices that made this work:

- **One interface, two modules.** The model sees the same tools with the same names and inputs on either route; only the code under them changes. Tests cover both with stand-ins.
- **Thin agent-side tools.** Each tool wraps a route call and fills in what the agent already knows (claim id, policy, customer, who is deciding), so the model supplies only the question.
- **Return the answer and a step.** Context tools give the model the answer, and give the app a lookup step (what was looked up, which files with their sources) as the tool's artifact. That feeds the audit trail.
- **Handle refusals as refusals.** With the MCP client's default error handling, an app that refuses a call can come back looking like a success; switch that handling off so a refusal raises an error and the model is told it was refused. A Gateway Policy refusal raises an MCP error ("Tool Execution Denied"); record it as the gateway's refusal and let the work go on.
- **Keep bookkeeping off the gateway.** Starting a claim, recording steps and model calls and the security check's read are the agent's own plumbing, called straight to the app with the key. Only what the model chooses to do, and the payment, go through the gateway so policy sees them.
- **Bridge async tools carefully.** The MCP client is async; a synchronous agent should run each call on a loop of its own, because `asyncio.run` on the main thread can leave it with no event loop on Python 3.12.
- **List tools once per run.** A context layer that is down then fails the run at start with a clear line, rather than midway.

## Memory, briefly

Memory is the agent's own notes. Details and strategies are in [rag-memory-and-mcp.md](rag-memory-and-mcp.md); the context-layer view is about the boundary:

- **Namespaces keep owners apart.** Per customer for the claim agent (`/customers/{actorId}/facts/` for facts, `/customers/{actorId}/claims/{sessionId}/` for each claim's summary), per handler for the Copilot. A search covers everything in the current customer's namespace and nothing else.
- **Save in code, not at the model's choice.** After a decision is recorded, the graph saves two events (the claim and the decision) with the customer as the actor and the claim as the session. The model decides only whether to search.
- **Save little, and never untrusted text.** Save the summary, benefit, date, place, items and the decision. Leave out the customer's story (a place where text could try to instruct the agent) and the documents (they hold whole medical records). Save nothing for a claim the injection check referred, and nothing for an evaluation's copy of a claim.
- **Memory adds; records decide.** A returning customer's earlier claims help the agent understand context; the claim history in the system of record stays what counts for rules such as repeat claims.
- **Evaluations run without memory** so scores do not depend on it.
- **Failure must not lose the decision.** If the memory service is unreachable, log a warning and keep the decision; a search returns the error to the model as a refusal.
- **The agent decides whether to look.** On some runs it will not search, so never put a rule in memory that the agent must follow.
- **Latency.** AgentCore extracts memories in the background, usually within two minutes; events expire (the lab set the shortest, 7 days).
- **Access path.** Memory calls go straight to the memory service, limited by the agent's IAM role, not through the gateway. Treat the IAM role as the memory's access control.

## Auditability

An agent decision must be reconstructable. Two layers, both built in the course:

**1. A complete decision record.** UnderCover's claims manual (section 14) defines what one must contain; copy the pattern and apply the client's own record rules: the decision, the payout, the calculation, the section relied on, a plain-language reason, who or what decided and when, the manual version in force, and, for payouts above the limit, who signed off and when. A decision with no reason on file counts as not made yet.

- Enforce it in the API, not the prompt: refuse an incomplete record with a 422 that names the rule and says what is missing so the agent can fix it and retry.
- Check what can be checked mechanically: a blank reason, section or maker; an approval that pays nothing; a decline or referral that pays something; an approval whose payout is not the calculation on file for this attempt.
- Store the calculation line by line, `decided_by` (the agent with its configuration version, or the security check) and the manual's version.

```python
def check_calculation(payout, calculation):
    if calculation is None:
        raise falls_short("an approval needs the calculation of its payout. Work it out with calculate_payout")
    if payout != calculation.payout:
        raise falls_short(f"the payout must be the calculation's {calculation.payout}")
    return calculation
```

**2. A visible trail of context used.** Each lookup becomes its own kind of step on the case page: what was looked up and which file answered with that file's system, owner and review date. Add a "Context used" panel listing everything looked up once each, grouped by file with the file's source, and show memory searches and saves, gateway refusals and refusals by the record check as distinct, visible steps. A reviewer then sees why the agent decided, from what, and how old it was.

## Enterprise data concerns and integration questions

The course (slide 57) gives four concerns to review for any architecture. Here they are as questions to put to the design, with what UnderCover did:

| Concern | Put to the design | What UnderCover did |
|---|---|---|
| Systems of record | Which system is the master for each kind of record? | Policies, customers and claims are read through the app's API |
| Read and write access | What is the agent able to change? | Two writes only, a decision and a payment, each validated by the app |
| Data boundaries | Where is the data allowed to travel? | Claims manual section 11 keeps each customer's data to their own claims and within the platform |
| Permissions | Under whose access does the agent act? | Its own IAM role and API key, with the gateway's policy checking each call |

Extend them into an integration interview for each system the agent will touch (the skill's synthesis from those four, for use in discovery):

- Which system is the record for each entity, and who owns it? Is there a catalog or MDM we should read from instead of building?
- Is access read-only or read-write? What is the smallest write that does the job, and who checks it (the API, a policy, a human)?
- Which identity does the agent use: its own, or the user's? (Own identity for a back-office agent; the user's identity for a copilot, see [copilot-pattern.md](copilot-pattern.md).)
- What may leave the platform: to the model provider, to a third party, into memory or logs? Does the provider's training or retention policy fit?
- How fresh must the data be, and what is the review cycle of each source?
- What happens when the source is down, slow, or returns a refusal?
- How does each call get logged for audit, and who reads the log?

## Enterprise MCP architecture

One gateway sits in front of everything the agent calls, so the agent needs one MCP client and the company has one place for identity and policy (slide 58).

```text
Agent (one MCP client)
   | MCP, signed
   v
MCP gateway (AgentCore Gateway in the course): Identity + Policy
   |--> Company APIs        (tools generated from their OpenAPI document)
   |--> Context layer       (definitions and procedures as tools)
   '--> External tools      (for example Jira)

Agent --> Memory: per customer facts, per session summary, per handler notes
          (direct, limited by the agent's IAM role)
```

What the Gateway does per call (recap, as taught): checks inbound authentication (IAM or an OAuth token), evaluates Cedar policy on every call, adds the target's outbound credentials (API key, OAuth or IAM), and forwards to an OpenAPI API, a Lambda function or an MCP server. Ed's advice from the security work is to stay lightweight while gateway products change, and the Week 3 Day 1 architecture advice is to start simple and expect a redesign within a year.

## The market as taught (Oct 2026)

Time-sensitive: re-check vendor documentation before recommending any product.

**Context layer products** (slide 54, checked against vendor docs in October 2026). Most of the big products cover all four parts and offer MCP access. Filled = generally available; open = preview, beta or a narrow version; blank = not covered.

| Product | Meaning of the data | Work procedures | Agent access rules | Provenance | MCP access | Works across |
|---|---|---|---|---|---|---|
| Atlan | yes | open | yes | yes | yes | many platforms |
| Collibra | yes | none | open | yes | yes | many platforms |
| Alation | yes | yes | yes | yes | yes | many platforms |
| DataHub | yes | open | open | yes | yes | many platforms |
| Snowflake Horizon Catalog | yes | yes | yes | yes | yes | Snowflake |
| Databricks Unity Catalog | yes | yes | yes | yes | open | Databricks |
| Google Cloud Knowledge Catalog | yes | yes | yes | yes | yes | Google Cloud |
| Microsoft Fabric IQ | yes | yes | yes | yes | yes | Fabric |
| Palantir Ontology | yes | yes | yes | yes | yes | Foundry |

**Memory products** (slide 56, October 2026; "open" is partial: paid plan only, preview or limited):

| Product | Managed | Open source | Facts and preferences | Summaries | Episodes | Knowledge graph | LangGraph integration |
|---|---|---|---|---|---|---|---|
| AgentCore Memory (AWS) | yes | no | yes | yes | yes | no | yes |
| Zep | yes | open | yes | yes | no | yes | yes |
| Mem0 | yes | yes | yes | open | no | open | open |
| Letta | yes | yes | yes | open | no | no | no |
| Cognee | yes | yes | yes | no | open | yes | open |
| LangGraph store with LangMem | open | yes | yes | no | yes | no | yes |
| Memory Bank (Google Cloud) | yes | no | yes | no | no | no | no |

How to use it: the market sells catalogs that already hold governance data; the course builds a small server over files to show the shape. Choose the vendor that matches where the client's data already lives; pick a memory design by testing strategies against the business metric, and prefer the simpler one.

## Decisions to make with the developer

| Decision | Options and trade-offs | Sensible default |
|---|---|---|
| What goes where: context layer, memory, database, gateway policy, instructions | Use the placement test above. Misplacing is the usual error: rules in memory, notes in the context layer, direct reads of the database | Rules, wording, definitions in the context layer; notes in memory; records in the database through the API; limits in gateway policy |
| Build or buy a context layer | Reuse a catalog the client already runs (Atlan, Collibra, Alation, DataHub, a cloud vendor's) and expose it as an MCP target; or build a small FastMCP server over governed files | If a catalog exists and has MCP access, wrap or use it. If the knowledge is a handful of documents and tables, build the small server. This is the skill's advice, not the course's explicit rule |
| Owner and review cycle for each source | A named role per file; a review date in the header; a stale-content rule | Every file has system, owner and reviewed; the owner agrees how often it is reviewed |
| Does the agent need memory at all? | Facts per customer, summaries, episodes, or none. Start without if the agent does not meet the same person repeatedly | Start with none; add semantic facts plus claim summaries when returning users matter; test against the metric; leave out evaluations |
| How the agent reaches the context layer and the APIs | Through one gateway with IAM; directly (dev, or a free route) | Gateway for deployed runs, direct route for the laptop, both behind one interface |
| What may be saved to memory or logs | Everything; or a whitelist of fields | A whitelist of fields; never untrusted text, medical or other sensitive documents |
| Instructions or lookup for documents | Inline text is simple and reliable; lookup scales | Inline only short, stable essentials; the rest behind lookups |

## Pitfalls and anti-patterns

- **Document search that matches the whole phrase.** "Trip Interruption" misses a heading "Trip Cancellation and Interruption". Match every word or tell the model to search one word, and keep a way to list or read sections by number.
- **No review date.** Context nobody reviews goes stale silently and the agent applies it with confidence. Header the file; surface the date.
- **Letting the agent hit the database directly.** It bypasses the rules, the checks and the audit. Only the app's API reads and writes records.
- **Mixing agent memory with business-owned truth.** A fact the agent remembered is not a rule. Do not store wording, plans or procedures in memory, and do not count rule-driving history from memory.
- **Saving untrusted text to memory.** It carries an injection into the customer's later claims.
- **Taking identity from the model.** If the tool accepts a customer id, the model can request another customer's records. Fill it in from run context.
- **A public or unauthenticated context server.** Use IAM auth or equivalent, even when read-only; the data is the business's.
- **Reading files per request.** Slow and fragile on Lambda; read once at start.
- **Treating a refusal as a success.** Check how the MCP client reports an error from a tool; make the model see a refusal.
- **Changing governed files to unblock the agent.** Change the tool, the prompt or ask the owner.
- **Rebuilding what the client's catalog already does.** Discovery should find it first.
- **Wording and manual placed in memory.** The last architecture slide of Week 3 Day 2 shows them there; the course's correction is that wording and the manual belong in the context layer, while memory holds the agent's notes on each customer.

## In UnderCover

Built on Week 3 Day 3 (brief `labs/week3day3_product_CONTEXT.md`, plan `docs/PLAN_CONTEXT.md`):

- A context layer of seven files in `context/`, each naming a source, an owner and a review date, served by `context/server.py` (FastMCP, seven read-only tools) over `context/files.py`. Locally it listens at `http://127.0.0.1:8006/mcp`; on Lambda it runs as `context.server.handler` behind a Function URL with IAM auth.
- The claim agent's tools go through the Gateway (`undercover-app` and `undercover-context` targets) when `UNDERCOVER_GATEWAY_URL` is set, otherwise directly (`agent/gateway.py`, `agent/direct.py`, `agent/routes.py`). Context tools live in `agent/context_tools.py` and return a lookup step with the file's source.
- Seeding loads the plans into the app's payout rules, and the documents into the documents table with their versions, from the same governed files; the app no longer serves the documents.
- Every decision record meets claims manual section 14 (checked in `backend/records.py`, refused with a 422 naming section 14). The record carries the calculation, `decided_by` and the manual's version.
- AgentCore Memory (Semantic facts and Summary of each claim) holds notes on each customer, saved in code after a decision. Oliver Grant's coconut claim (CLM-1006) can recall his giraffe claim (CLM-1005).
- The claim page shows each tool call, lookup, memory step and refusal, with a Context used panel grouped by file.
- The Copilot (Week 3 Day 5) reuses the same context tools, on the same route, and keeps memory per handler.

## Related

- [rag-memory-and-mcp.md](rag-memory-and-mcp.md): MCP basics, RAG, memory strategies and namespaces.
- [security-and-guardrails.md](security-and-guardrails.md): the gateway's Policy, lethal trifecta, hidden-instruction check, API keys.
- [production-deployment-aws.md](production-deployment-aws.md): Lambda packaging, Function URLs, Gateway creation, memory creation, teardown.
- [copilot-pattern.md](copilot-pattern.md): an agent that uses the user's identity and keeps memory per handler.
- [agent-architecture.md](agent-architecture.md): systems around the agent, business logic in code.
- [evals-and-observability.md](evals-and-observability.md): why evaluations run without memory.
- [../assets/templates/CONTEXT_FILE.md](../assets/templates/CONTEXT_FILE.md): template for a context file with its source header.

## Sources

- `guides/for_agents/AGENT_GUIDE_WEEK3.md` (Day 2 correction on memory versus context layer; Day 3 watch-outs and corrections)
- W3D3 slides 50-54, 57-62, 66; W3D4 slide 72 (four sources of data and integration); slides 55-56 for memory
- `labs/week3day3_product_CONTEXT.md`; `labs/week3day3.ipynb` (Parts 2-5)
- `context/*.yaml`, `context/*.md` on `main` (source headers); `context/claims_manual.md` section 14
- `origin/week3day5-end:context/server.py`, `context/files.py`, `agent/context_tools.py`, `agent/gateway.py`, `agent/direct.py`, `agent/routes.py`, `agent/memory.py`, `backend/records.py`, `backend/context_files.py`
- `origin/week3day3-end:docs/PLAN_CONTEXT.md`
