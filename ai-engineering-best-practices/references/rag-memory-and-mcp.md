# RAG, Memory and MCP

> When to read this: the agent needs knowledge it does not have in its prompt (reference facts, documents, history), the developer asks "do we need a vector database / RAG / memory / MCP?", or you are designing what an agent remembers about a customer or user and who owns that data. For the business-owned data layer itself, see [context layer](context-layer-and-integrations.md).

## Contents

- Key principles
- RAG and agentic RAG
- Evaluating retrieval
- RAG, agentic RAG or fine-tuning
- MCP for your own agents
- Memory: short-term, long-term, and who owns what
- AgentCore Memory in practice
- Alternatives and the product landscape
- Decisions to make with the developer
- Pitfalls and anti-patterns
- In UnderCover

## Key principles

1. **Start with the simplest retrieval that could work, and measure it against a baseline.** A plain word search over a small fact file is the control; a vector database has to beat it on your own cases before it earns its place.
2. **Prefer agentic retrieval to a fixed pipeline when queries are unpredictable.** An agent that writes its own queries, and searches again when the first result is thin, finds facts a one-shot "embed the question, take the top k" pipeline misses.
3. **Score retrieval separately from the final answer.** If the answer is wrong you need to know whether the fact never came back or the model ignored it. Label which facts each test case needs and score whether they were retrieved.
4. **A tool used by only your own agent usually does not need MCP.** Use MCP for ready-made servers, for capabilities shared by several agents or owned by another team, and for anything that must sit behind a gateway.
5. **Give an agent read-only access to a knowledge store it only needs to search.** The agent that searches must not be able to rewrite the facts it relies on.
6. **Keep three kinds of knowledge apart, because they have different owners.** Business-owned reference data and procedures belong in the context layer, the agent's own notes about one customer or user belong in memory, and records the business must rely on belong in the system of record (the database).
7. **Make memory optional and partitioned.** Switch it on by configuration (an environment setting naming the memory), keep one namespace per customer or user, and derive that identity from verified data, never from model output.
8. **Decide in code what is always saved; let the model decide what it searches.** Saving after a decision is a business rule, so do it every time in code. Searching is the agent's judgment, so it may skip it. Anything that must always be consulted should be looked up in code instead.
9. **A memory failure must not fail the business action.** Log it, show it, and carry on without the memory.
10. **Do not save text that tried to instruct the agent, and do not save sensitive source documents.** Memory carries text into later runs, so an injected instruction would follow the customer.
11. **An agent can learn by changing its memory rather than its weights.** That is cheaper, inspectable and reversible, but it needs scoping, evaluation and a retention policy.
12. **Evaluate memory like any other change.** Try the strategies, compare them on your business metric, and keep the simpler one unless a specific problem needs more. Keep memory out of evaluation runs so scores stay comparable.

## RAG and agentic RAG

**RAG** is three steps: split documents into **chunks**, turn each chunk into an **embedding** (a vector that captures meaning) stored in a vector database, and at question time **search** by meaning to find the nearest chunks and place them in the prompt. A search by meaning can return a fact that shares no words with the query. In the course lab the search returned the 10 closest facts, nearest first.

**Agentic RAG** changes who runs the search. The search is a tool; the agent chooses when to call it and what to search for, and calls it as often as it needs. It can search alone, or hand the job to a **research subagent** that owns the retrieval tools and returns what it found, which keeps the main agent's context small (see [harness engineering](harness-engineering.md) for subagents).

| Approach | Who decides the query | Good for | Weak at |
|---|---|---|---|
| Plain word / keyword search | The tool matches the words given | Small, structured, well-named content; exact terms | Synonyms, near-matches (a whole-phrase match misses "Trip Cancellation and Interruption" when you ask for "Trip Interruption") |
| Classic RAG | Code embeds the user's question once | Q&A over documents where the question is the right query | Tasks where the needed fact is not named in the input, or needs several lookups |
| Agentic RAG | The agent, repeatedly | Tasks where the agent works out what it needs to know (a storm's naming date, what a device is) | Cost and latency of extra calls; agent may skip searching |

Practical lab pattern (Week 2 Day 2, as taught): hard claims needed facts not found in the claim itself. An assistant stored 33 facts through a vector-database MCP server (store and find tools). The claim agent then got only the **find** tool, in read-only mode, and one extra instruction: before deciding, search memory for any product, event or place in the claim you need to know more about.

Run the baseline first: replace the vector search with a simple tool that looks for the words of the query in the same fact file, give it to the same agent, and rerun the evaluation. The course sets this as an assignment. If the word search scores as well, you do not need embeddings yet.

Documents with a clear structure (a policy wording, a procedures manual) often need no vectors at all: search by words, then read the right section in full. UnderCover's claim agent does this with its documents. Test the phrasing risk above before relying on it.

## Evaluating retrieval

Use the same eval discipline as in [evals and observability](evals-and-observability.md), plus retrieval-specific scores.

| Metric | Question it answers |
|---|---|
| Precision | Of what came back, how much was relevant? Low precision floods the prompt with noise |
| Recall | Of what was needed, how much came back? Low recall means missing facts |
| Mean reciprocal rank (MRR) | How high in the ranking did the first relevant result appear? (average of 1/rank over queries) |
| Needed facts retrieved (the lab's `found_fact`) | For agentic RAG: did the agent's own searches bring back every fact this case needs? |

For agentic RAG the classic ranking metrics need a fixed query, but the agent writes its own, so the practical score is the last one: label each test case with the facts it needs, collect the text the search tool returned during the run, and check that every needed fact appears. Report it beside the answer-quality scores, not instead of them.

Lab result as taught (Week 2 Day 2, one of Ed's runs, GPT-6 Luna at low reasoning effort): 14 of 25 harder claims fully right (decision right and payout within a dollar) without memory, and all 25 with it. Treat the figures as an illustration, not a benchmark. Models vary between runs, so compare the two experiments run in the same session with the same settings, and run more than once (the notebook's default is a single run).

## RAG, agentic RAG or fine-tuning

| Need | Reach for | Why |
|---|---|---|
| The model lacks facts that change or are private | RAG or agentic RAG | Update the data, not the model; cite the source; delete a fact by deleting a row |
| The task needs several lookups chosen as the work unfolds | Agentic RAG | The agent adapts its queries to what it has found |
| The model must learn a style, format or narrow skill | Fine-tuning | Behaviour belongs in weights, not in retrieved text (the course does not build this) |
| The agent should get better with experience | Update its memory (and its configuration; see [self-improvement](self-improvement.md)) | Notes can be read, scoped, evaluated and rolled back; weights cannot |

The Week 2 Day 2 slides frame it this way: an agent can learn by updating its memory rather than its weights. Fine-tuning comparisons beyond this are general engineering judgment rather than something the course built, so treat them as defaults to test.

## MCP for your own agents

MCP is the Model Context Protocol, an open standard for connecting agents to tools. Three roles:

- **Host**: the application that runs the agent and the model.
- **Client**: the component in the host that connects to a server and exposes its tools to the agent. The course uses `MultiServerMCPClient` from `langchain-mcp-adapters`, which handles several servers at once.
- **Server**: a program that offers tools (a vector-database server, a Supabase server, UnderCover's context layer).

| Transport | Where the server runs | Course examples | Trade-offs |
|---|---|---|---|
| stdio | A local process the client starts (often via `uvx` or `npx`) | Qdrant memory server in the lab; Playwright, Supabase for the coding agent | Easy, no network or auth; in the lab each tool call started and stopped the server, which costs time; local databases may allow only one process |
| Streamable HTTP | A remote (or local HTTP) service | The context layer's server at `http://127.0.0.1:8006/mcp`; servers behind an AgentCore Gateway | Shareable, deployable, can be authenticated (IAM-signed requests in the course); needs hosting and credentials |

**When to use MCP**

- A ready-made server exists and works (vector store, database, browser automation).
- Several agents or hosts, or another team, will use the same tools; the server is the contract.
- You want one place to apply gateway rules, identity and policy (see [security and guardrails](security-and-guardrails.md)).
- **When not:** a capability only your own agent calls is simpler as a plain function tool. A tool is still a function; in the lab the notebook calls the MCP tool directly with `ainvoke` to test it.

**Safety:** run servers read-only whenever the agent only needs to look (the lab set `QDRANT_READ_ONLY=true` for the claim agent; the course's coding-agent setup uses a read-only Supabase server scoped to one project). Treat third-party servers as code you are running with the agent's authority; see the security reference.

**Coding-agent MCP is a different use** from MCP for your own agents. For the coding agent, an MCP server added without a scope is local (this user, this project); `--scope user` covers all projects and `-s project` shares it with the team (Claude Code, as taught).

### Practical gotchas (general lessons from the labs)

- **Pin versions, including the Python version, for `uvx` servers.** `uvx` ignores your repo's `.python-version`. The lab's Qdrant server version could not install on Python 3.14, and the symptom was a vague `McpError: Connection closed` when listing tools. Pass `--python 3.12.12` and pin the server version.
- **Local single-process databases break under concurrent calls.** Two parallel searches against a local Qdrant folder collided, so the lab added `ToolRetryMiddleware` with a few retries. Better: one long-lived server, or a networked database.
- **MCP tools may be async only.** From a synchronous agent, run each call on a private event loop that you close afterwards and never install as the thread's loop (installing it broke a Lambda adapter that expected the main thread's loop). Evaluation frameworks may run each experiment on its own loop, so also avoid reusing a connection opened on another loop (the lab used an HTTP client with no kept-alive connections).
- **Stdio servers inherit the parent's error stream.** Inside a notebook on Windows that stream is not a real file and the launcher can fail; the lab redirected the server's error log to a null device first.
- **Decide how tool errors surface.** The adapter's default can return a service's refusal as if it succeeded; turn that off so a refusal raises a tool error the agent can handle. A policy denial at a gateway arrives as an MCP error whose message starts "Tool Execution Denied".
- **Stateless servers can be called with a session per call** (about 0.75 seconds a call in the course experiment), which is simple but adds latency; budget for it.
- **Server tool names may be prefixed by the gateway** (target name, three underscores, tool name); show the tool's own name to humans.

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ToolRetryMiddleware
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "memory": {
        "transport": "stdio",
        "command": "uvx",
        "args": ["--python", "3.12.12", "mcp-server-qdrant@0.8.1"],  # pin both
        "env": {"QDRANT_LOCAL_PATH": "...", "COLLECTION_NAME": "memory",
                "QDRANT_READ_ONLY": "true"},  # the claim agent may search, not write
    }
})
search_tools = await client.get_tools()
agent = create_agent(model=model, tools=[*other_tools, *search_tools],
                     system_prompt=instructions,
                     middleware=[ToolRetryMiddleware(max_retries=3)])
```

Package names and versions above are as taught in the course (Oct 2026); re-check them. Enterprise-scale MCP (gateway in front of company APIs, context layer served as tools) is in [context layer and integrations](context-layer-and-integrations.md) and [security and guardrails](security-and-guardrails.md).

## Memory: short-term, long-term, and who owns what

**Short-term memory is the conversation history** for the current thread: the messages so far and the saved checkpoints of the run (see [durable state](durable-state-and-hitl.md) for checkpoints and thread design). It lets a run resume, but it ends with the thread.

**Long-term memory** is everything kept across threads: facts about a customer, preferences, summaries of past work, past episodes. It must be written, retrieved and governed deliberately.

The architecture the course ends with has three sources of data plus the gateway, each with a different owner:

| Source | What it holds | Written by | Agent's access |
|---|---|---|---|
| Gateway | Rules for tool calls (limits, policies) | Security team | Cannot change it; every call goes through it |
| Context layer | Definitions, procedures, reference data from other systems | Business teams (data governance) | Reads it, as tools through the gateway |
| Memory | The agent's own notes (per customer, per handler) | The agent | Reads and writes with its memory tools or store |
| Database | System of record: records, checkpoints | The app (and the agent through the app's API) | Reads and writes through the app's API |

**Placement rule:** If it is true for everyone and someone owns it (wording, manual, plan limits, outside events), it goes in the context layer with a source, owner and review date. If it is the agent's observation about one customer or user, it goes in memory. If the business must rely on it as the official record, it goes in the database. In Week 2 the lab stored shared facts in a vector memory for convenience; in the product those facts became context-layer reference data.

**Course correction (Week 3 Day 2/3):** one architecture slide lists "wording, manual and notes" under Memory. The wording and manual belong in the context layer, and memory holds only the agent's notes per customer.

**Memory adds, it never replaces.** In UnderCover the claim history in the records still decides repeat claims; memory adds what happened on earlier claims.

## AgentCore Memory in practice

AgentCore Memory is AWS's managed memory service, as taught in Week 3 (Oct 2026). The agent writes **events**, and the service turns events into **memory records** in the background using **strategies**.

### The four extraction strategies

| Strategy | Keeps | Example use |
|---|---|---|
| Semantic | Facts extracted from conversations | A customer's setup or circumstances |
| Preference (User Preference in the API) | User-related information | How a user likes answers set out |
| Summary | Compressed account of what happened | One summary per claim or session |
| Episodic | Past task episodes: actions and outcomes | Specific issues and their fixes |

The slides' guidance: find the right design by experiment, choosing the strategy that scores best on your business metric, and prefer simple over clever unless a specific problem needs more. Short-term memory is the conversation history; the four strategies above are all long-term.

### Namespaces, actors and sessions

- Each event has an **actor** (who it is about) and a **session** (the unit of work). Records land in **namespaces** built from templates such as `/customers/{actorId}/facts/`.
- Search is by **namespace prefix** plus a query, so one prefix can cover several kinds of record: `/customers/<id>` covers the customer's facts and every claim summary, and another customer's prefix returns nothing. If your IDs can share a prefix (for example `C-1` and `C-10`), end the prefix with a slash or use delimited IDs (verify the service's matching rule).
- Design namespaces so the actor is the privacy boundary and the prefix you search is the set of memories the agent should see.

```python
agentcore.create_memory(   # boto3 "bedrock-agentcore-control" client
    name="myapp_memory", description="The agent's memory of each customer",
    eventExpiryDuration=7,  # days; the course used the shortest allowed
    memoryStrategies=[
        {"semanticMemoryStrategy": {"name": "customer_facts",
            "namespaceTemplates": ["/customers/{actorId}/facts/"]}},
        {"summaryMemoryStrategy": {"name": "claim_summaries",
            "namespaceTemplates": ["/customers/{actorId}/claims/{sessionId}/"]}},
    ])
```

Creating a Memory took about two and a half minutes in the lab. Create it in a deployment step or notebook, not in application code. AgentCore Memory is missing from six AWS regions (as taught, Oct 2026), so check regional availability first; the course used us-east-1 throughout.

### The behaviours to design around

- **Extraction is asynchronous.** Memories usually appear within about two minutes (in the course's tests about 90 seconds). A fact saved this turn is not searchable this turn, so a preference shows up in the user's next conversation, and a lab that checks memory right after saving should poll.
- **The agent decides whether to search.** On some runs the second claim never searched memory. Say in the instructions what the tool is for and that it supplements the records. If a lookup must always happen, do it in code.
- **A search covers the whole namespace.** For the claim agent that is the customer's facts and every claim summary. The only thing left out is the current claim's own summary, filtered in code, so a claim that is worked again does not find its own earlier summary and reinforce itself.
- **Configuration by environment makes it optional.** When the memory-ID setting is unset there is no store, no search tool and no save node, and the agent works as before; evaluation runs build their graphs with no store at all. Memory calls go straight to AgentCore, limited by the agent's cloud role, not through the gateway.
- **Failure is soft.** After a decision, an unreachable memory logs a warning and the claim keeps its decision. The search tool raises a tool error the model sees as a refusal. The Copilot's lookup shows a refused card and the turn goes on.

### Saving, in code

Keep the store behind LangGraph's `BaseStore` interface. `AgentCoreMemoryStore` (package `langgraph-checkpoint-aws`; 1.2.4 in the course experiment, as taught) takes the memory ID as a keyword-only argument. A `put` writes one event, and the key is ignored.

```python
def memory_store() -> BaseStore | None:
    memory_id = os.getenv("MYAPP_MEMORY_ID")
    if not memory_id:
        return None                                   # memory is optional
    return AgentCoreMemoryStore(memory_id=memory_id,
                                region_name=boto3.Session().region_name)

def remember(store, customer_id, claim_id, claimed: str, decided: str):
    session = (customer_id, claim_id)                 # actor, session
    store.put(session, "claim", {"message": HumanMessage(claimed)})
    store.put(session, "decision", {"message": AIMessage(decided)})

def recall(store, customer_id, current_claim_id, query):
    found = store.search(("customers", customer_id), query=query, limit=5)
    own = f"/customers/{customer_id}/claims/{current_claim_id}/"
    return [i.value["content"] for i in found if own not in i.value["namespaces"]]
```

Details that matter:

- The text saved is the claim's summary, benefit, date, place and items, plus the decision with payout, section and reason. Never the free-text story (where a customer could try to instruct the agent) or the documents (which hold whole medical records).
- Save as a graph node of its own, so it runs once even when work resumes after a restart.
- Do not save a claim the injection check referred, and do not save an evaluation's copy of a claim.
- The identity comes from the claim record (claim agent) or the verified sign-in (Copilot), never from a name in the model's output or the user's message.

### Two memories in UnderCover

| | Claim agent | Copilot |
|---|---|---|
| Actor / session | Customer / claim | Handler (from the sign-in) / conversation |
| Strategies | Semantic + Summary | User Preference + Semantic |
| Namespaces | `/customers/{actorId}/facts/`, `/customers/{actorId}/claims/{sessionId}/` | `/handlers/{actorId}/preferences/`, `/handlers/{actorId}/facts/` |
| Saved | The claim and the decision, after a decision | The handler's message and the answer, after each turn, nothing else (no tool calls, results or sign-in) |
| Searched | When the model chooses, with a search tool | By code at the start of every turn, shown as a card and placed in the instructions |
| Setting | `UNDERCOVER_MEMORY_ID` | `UNDERCOVER_COPILOT_MEMORY_ID` |

The Copilot has a separate Memory resource because the claim agent's strategies file everything under `/customers/{actorId}/`. One handler's notes are never used for another, and the course checks this by asking the same question as two handlers. A conversation ID can double as the Runtime session ID and the memory session ID, with a length limit (at least 33 and at most 100 letters, digits and hyphens). See [copilot pattern](copilot-pattern.md).

## Alternatives and the product landscape

**Without AWS:** LangGraph's `PostgresStore` can hold memory in the database you already run (the course used Supabase), with **pgvector** for search and a namespace per customer, mirroring the AWS layout. This was the course's free-route assignment: save the claim and the decision when the agent decides, and give the agent a tool that searches its customer's memories. Because the code above sits behind `BaseStore`, the swap is mostly the store and the tool. What changes: you write what is stored, and any fact extraction or summarising the managed service did in the background becomes your job (inferred, verify).

**Plain files:** a Markdown file per customer with a read tool and an append tool is a legitimate baseline (a Week 2 assignment). Ask what should happen to the notes between evaluation runs: persistent memory contaminates repeated runs, so reset it or turn it off in evaluations.

**Product survey as taught (Oct 2026; time-sensitive, re-check before relying on it).** Yes = offered, Partial = paid plan only, preview or limited, "-" = not offered:

| Product | Managed service | Open source | Facts and preferences | Summaries | Episodes | Knowledge graph | LangGraph integration |
|---|---|---|---|---|---|---|---|
| AgentCore Memory (AWS) | Yes | - | Yes | Yes | Yes | - | Yes |
| Zep | Yes | Partial | Yes | Yes | - | Yes | Yes |
| Mem0 | Yes | Yes | Yes | Partial | - | Partial | Partial |
| Letta | Yes | Yes | Yes | Partial | - | - | - |
| Cognee | Yes | Yes | Yes | - | Partial | Yes | Partial |
| LangGraph store with LangMem | Partial | Yes | Yes | - | Yes | - | Yes |
| Memory Bank (Google Cloud) | Yes | - | Yes | - | - | - | - |

How to choose: if you already run on AWS AgentCore, its Memory removes the extraction pipeline. If you want to stay in your own database, a LangGraph store on Postgres keeps data and cost in your control. Pick on the features your design needs (episodes, knowledge graph), data residency and your evaluation results, not on the table alone.

## Decisions to make with the developer

| Decision | Questions to ask | Options and trade-offs | Sensible default |
|---|---|---|---|
| Do we need RAG at all? | What does the agent need to know that is not in the input or prompt? How big and how structured is it? How often does it change? | Put it in the prompt (small, stable); keyword search and read by section (structured documents); vector search (large, unstructured, meaning-based questions); agentic RAG (needs vary per task) | Prompt or keyword search first; add vectors only if an evaluation against the word-search baseline shows a gain |
| Vector database or keyword search? | Do queries share words with the content? Is a baseline score already good? | Keyword is simple and exact but brittle; vectors find meaning but need an embedding model, storage and tuning | Run both on the same eval set and keep the simpler one that meets the target |
| MCP or plain tool? | Who else will use this tool? Is there a ready-made server? Must it sit behind a gateway? | MCP gives sharing and central policy at the cost of a process or service, latency and version drift | Plain function tool for your own agent's private logic; MCP for ready-made or shared servers; read-only wherever possible |
| Memory scope and namespaces | Who is the actor (customer, user, team)? What may one run see? Which strategies? | Per-actor isolation is safest; shared memory is cheaper but leaks across actors; summaries per session add history | One namespace per actor derived from verified identity; start with Semantic plus Summary; add Preference or Episodic only if an evaluation shows a gain |
| Who triggers memory search and save? | Must the memory always be consulted? Can a missed search cost money? | Model-chosen search is flexible but may be skipped; code-chosen is reliable but adds noise | Save in code every time; search by the model's choice unless a lookup is mandatory, then in code |
| Retention and privacy | What personal data might end up in memory? How long may we keep it? Can a customer ask to be forgotten? Who can read it? | Short event expiry and saving only summaries lowers risk; keeping more raises usefulness | Save only the minimum (summary, decision), set the shortest sensible expiry, restrict reading to the agent's role, and write the deletion procedure before launch (verify how the service deletes extracted records) |
| Managed or self-hosted memory? | Are we already on AWS? Do we need data to stay in our database? | See the product survey above | AgentCore Memory if on AgentCore; otherwise a LangGraph store on Postgres with pgvector |

## Pitfalls and anti-patterns

- **Vectors by default.** Adding a vector database without a word-search baseline; you cannot tell whether it helped.
- **One mega-store.** Mixing business reference data, agent notes and system records in one memory, so nobody owns correctness and nothing has a review date.
- **Letting the agent write its own reference facts.** The agent that relies on a fact should read it, not edit it; use read-only servers.
- **Memory poisoning.** Saving a customer's raw story or a flagged claim, which carries injected instructions into later claims.
- **Identity from the model.** Taking the customer or handler ID from the message instead of the verified record or sign-in.
- **Expecting instant recall.** Testing "did it remember?" in the same turn or minute; extraction runs in the background.
- **Assuming the agent will search.** Relying on a model-chosen lookup for something mandatory.
- **Memory in evaluations.** Memory that persists between runs makes scores depend on history; evaluations should run without it or reset it.
- **Unpinned MCP launches.** A `uvx` server on whatever Python is the default, which fails with a vague "connection closed".
- **Hard failure on memory outage.** Letting a memory error block the payment or the answer.
- **Memory replacing the record.** Treating memory as authoritative for counts such as repeat claims instead of the system of record.
- **Unbounded context.** Dumping every memory into the prompt; retrieve a few (the course used five).

## In UnderCover

- **Week 2 Day 2 (lab, not product):** 25 harder claims that need outside facts. A vector-database MCP server held 33 facts, the claim agent searched them read-only, and Langfuse compared runs with and without it using a `found_fact` score. In the run the course reports, 14 of 25 were fully right without memory and all 25 with it. Assignments: a word-search baseline, a per-customer Markdown memory, and a research subagent.
- **Week 3 Day 3 (product):** the same facts moved to the context layer as reference data with a source, owner and review date. The claim agent's memory became AgentCore Memory, enabled by `UNDERCOVER_MEMORY_ID`. After a decision, a graph node saves the claim and decision as two events (customer as actor, claim as session), and Semantic and Summary strategies produce facts and a per-claim summary. A `search_memory` tool searches the customer's namespace. Oliver Grant's second claim (the coconut) can recall his first (the giraffe) if the agent searches. The claim page shows each memory search and save.
- **Week 3 Day 5 (product):** the Copilot got its own Memory per handler (preferences and facts), searched by code at the start of each turn and saved after each turn. It identifies the handler from the sign-in.
- **What was left out on purpose:** memory in evaluations, the Copilot reading the claim agent's customer memory, and (as stretch work) the Episodic strategy and a Postgres store.
- **Free route:** no AgentCore Memory; the agent works without memory, and a LangGraph `PostgresStore` with pgvector on Supabase was the assignment.

## Related

- [Context layer and integrations](context-layer-and-integrations.md): the business-owned data the agent reads (and enterprise MCP).
- [Security and guardrails](security-and-guardrails.md): gateways, policy, prompt injection and why untrusted text must not reach memory.
- [Production deployment on AWS](production-deployment-aws.md): configuration by environment, IAM roles for memory, regions, teardown (a deleted Memory removes its events and records).
- [Durable state and human in the loop](durable-state-and-hitl.md): checkpoints, which are the short-term side of memory.
- [Evals and observability](evals-and-observability.md): eval sets, noise, baselines.
- [Copilot pattern](copilot-pattern.md): per-handler memory and identity.
- [Harness engineering](harness-engineering.md): tools, subagents and instructions.

## Sources

- `guides/for_agents/AGENT_GUIDE_WEEK2.md` (Week 2 Day 2: slides summary, lab, watch-outs, assignments), `AGENT_GUIDE_WEEK3.md` (Week 3 Day 2 correction on memory; Day 3 memory notes and corrections; Day 5 per-handler memory), `AGENT_GUIDE_WEEK1.md` (Week 1 Day 3: MCP basics and scopes).
- Notebooks: `labs/week2day2.ipynb` (Qdrant MCP, `found_fact`, read-only server, retries), `labs/week3day3.ipynb` Part 4 and 5 (creating AgentCore Memory, namespaces, extraction, search), `labs/week3day3free.ipynb` (PostgresStore with pgvector as an assignment), `labs/week3day5_lab1.ipynb` (the Copilot's Memory).
- Slides: W3D3 slides 53, 55, 56, 58, 61 (three sources of data, strategies and namespaces, memory product survey, enterprise MCP, how UnderCover uses memory), W3D1 slide 18 (regional gaps).
- Briefs: `labs/week3day3_product_CONTEXT.md` (Step 4 and notes on AgentCore Memory and MCP), `labs/week3day5_product_COPILOT.md` (section 9, handler memory).
- Final code: `origin/week3day5-end:agent/memory.py`, `agent/agentcore_memory.py`, `agent/mcp_tools.py`, `agent/copilot/memory.py`, and the memory nodes in `agent/harness.py`, `agent/tools.py`, `agent/copilot/graph.py`.
