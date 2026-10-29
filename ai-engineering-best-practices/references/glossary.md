# Glossary

> When to read this: the developer or a source uses a term you must explain or use precisely (an AWS service, a LangGraph word, an eval metric, an autonomy tier). Each entry is short and points to the file that owns the detail. Product names, prices, limits and versions marked "(as taught, Oct 2026)" are time-sensitive: re-check them before quoting.

Terms are alphabetical. "UnderCover" is the course's fictional travel insurer; its figures are illustrations, not benchmarks.

## A

- **ADLC** — Used in two senses; say which. (1) Agent development lifecycle, building agents with code: discovery, R&D, development, implementation, maintenance, each ending in a sponsor's tollgate. (2) Building code with agents: how a developer and a coding agent deliver a product together (Harness, Harden, Humans).
  See: [fde-lifecycle-and-governance.md](fde-lifecycle-and-governance.md), [building-with-coding-agents.md](building-with-coding-agents.md)
- **ADR (architecture decision record)** — A short note on a decision that is costly to reverse or hard to explain later: context, options, the choice, consequences and a review date. It lets the next person see why.
  See: [agent-architecture.md](agent-architecture.md), [../assets/templates/ADR.md](../assets/templates/ADR.md)
- **Agent** — An LLM with tools, in a loop, working towards a goal; the model chooses the next step. Agent = model + harness. In a workflow, code chooses the next step instead.
  See: [agent-architecture.md](agent-architecture.md)
- **AgentCore (Amazon Bedrock AgentCore)** — AWS's suite for running agents; the course calls it "AWS Bedrock AgentCore". The slide lists fourteen services and the course used six: Gateway, Policy, Identity, Observability, Memory and Runtime, all in us-east-1 (as taught, Oct 2026).
  See: [production-deployment-aws.md](production-deployment-aws.md), [code-patterns-aws-agentcore.md](code-patterns-aws-agentcore.md)
- **AgentCore Gateway** — Turns APIs (OpenAPI), Lambda functions and MCP servers into one list of MCP tools. It checks inbound auth (IAM or OAuth), asks Policy, then adds outbound auth (API key, OAuth or IAM). Tools are named `<target>___<operation>` (as taught, Oct 2026).
  See: [security-and-guardrails.md](security-and-guardrails.md), [context-layer-and-integrations.md](context-layer-and-integrations.md), [code-patterns-aws-agentcore.md](code-patterns-aws-agentcore.md)
- **AgentCore Identity** — Holds agents' credentials, such as API keys, as credential providers in a token vault. The runtime fetches a value on its first request, so secrets stay out of code, images and logs (as taught, Oct 2026).
  See: [production-deployment-aws.md](production-deployment-aws.md), [code-patterns-aws-agentcore.md](code-patterns-aws-agentcore.md)
- **AgentCore Memory** — AWS's managed memory service. The agent writes events and the service extracts memory records in the background, using strategies, into namespaces. Extraction takes about two minutes; the service is missing from six AWS regions (as taught, Oct 2026).
  See: [rag-memory-and-mcp.md](rag-memory-and-mcp.md), [code-patterns-aws-agentcore.md](code-patterns-aws-agentcore.md)
- **AgentCore Observability** — Policy decisions and agent telemetry in CloudWatch (as taught, Oct 2026).
  See: [production-deployment-aws.md](production-deployment-aws.md)
- **AgentCore Policy** — Cedar rules checked on every Gateway tool call. Attach the engine log-only first, then enforce (as taught, Oct 2026).
  See: [security-and-guardrails.md](security-and-guardrails.md), [code-patterns-aws-agentcore.md](code-patterns-aws-agentcore.md)
- **AgentCore Runtime** — Serverless hosting for an agent: any framework and model, one session per microVM, billed while a session works. Its 60 seconds is an idle timeout, not a maximum; registered work keeps a session alive (up to 8 hours, as taught, Oct 2026).
  See: [production-deployment-aws.md](production-deployment-aws.md), [code-patterns-aws-agentcore.md](code-patterns-aws-agentcore.md)
- **Agentic RAG** — Retrieval where the search is a tool the agent calls, with queries it writes itself, as often as it needs. The alternative is classic RAG: embed the question once and take the top results. Compare against a plain word search first.
  See: [rag-memory-and-mcp.md](rag-memory-and-mcp.md)
- **AGENTS.md** — The file at a repo's root that a coding agent loads first. Keep it a short router that points to the docs (read in full, role, builds, rules, folder map), not an encyclopedia.
  See: [building-with-coding-agents.md](building-with-coding-agents.md), [../assets/templates/AGENTS.template.md](../assets/templates/AGENTS.template.md) (save it as `AGENTS.md` in the repo)
- **Answer key** — The labelled correct decisions for the eval sets. It lives in the backend that scores. The agent under test never sees it, and by default the coding agent does not open it either.
  See: [evals-and-observability.md](evals-and-observability.md)
- **Audit trail** — The record of every step the agent took and who approved each consequential action, with a full decision record. Show it to people, not only to engineers.
  See: [context-layer-and-integrations.md](context-layer-and-integrations.md), [fde-lifecycle-and-governance.md](fde-lifecycle-and-governance.md)
- **Automation, acceleration, differentiation** — The three categories of use case: do things cheaper, do them faster, do different things. Choose the metric by category (cost per unit of work, elapsed time, a new outcome); that mapping is guidance.
  See: [fde-lifecycle-and-governance.md](fde-lifecycle-and-governance.md)
- **Autonomy tiers** — Decided per action, not per agent: automatic, approval first or prohibited. Assess risk appetite, consequence, verifiability, reversibility, and security, privacy and IP. Enforce each tier outside the model (in the backend, at the gateway policy and through human sign-off above a threshold), not only in instructions, and review the tiers at each tollgate. Related outcomes, kept apart: held for sign-off, referral, left for a handler.
  See: [fde-lifecycle-and-governance.md](fde-lifecycle-and-governance.md), [security-and-guardrails.md](security-and-guardrails.md)

## B

- **Baseline** — What a reference policy scores on the same measures. The human baseline is what the current process achieves (accuracy, time, cost per item) and anchors the business case. Naive baselines are "approve everything" (on UnderCover's harder claims: 56% decision accuracy, kappa 0) and "refer everything" (0% straight-through, $950 of needless-referral cost over 25 claims).
  See: [evals-and-observability.md](evals-and-observability.md)
- **Budget alerts** — AWS has no hard spending cap, so a budget with alerts is the only brake (a budget that counts credits never fires). Add a credit limit on the model provider's key and spending limits in code.
  See: [production-deployment-aws.md](production-deployment-aws.md), [models-and-cost.md](models-and-cost.md), [code-patterns-aws-agentcore.md](code-patterns-aws-agentcore.md)
- **Business logic in code** — Calculations, rules, thresholds, state transitions and permission checks are deterministic tools; the model reads and judges. In Ed's runs, moving payout arithmetic into a tool cut wrong decisions or amounts from 36 to 8 of 75 (as taught, Oct 2026).
  See: [agent-architecture.md](agent-architecture.md)
- **BYOK (bring your own key)** — Routing through OpenRouter with your own provider key: free up to a monthly allowance, then 5% (as taught, Oct 2026; verify current terms).
  See: [models-and-cost.md](models-and-cost.md)

## C

- **Cedar** — The policy language of AgentCore Policy. With an engine attached, a call is refused unless a policy permits it, and a `forbid` always wins over a `permit`. A JSON number reads as a Cedar `decimal`, so compare with `greaterThan`, not `>`.
  See: [security-and-guardrails.md](security-and-guardrails.md), [code-patterns-aws-agentcore.md](code-patterns-aws-agentcore.md)
- **Checkpoint** — A snapshot of a graph's state saved after each super-step (one round of the graph). It is the resume point: a crash loses at most the step in progress. Rewinding to one rewinds state, not the world.
  See: [durable-state-and-hitl.md](durable-state-and-hitl.md), [code-patterns-langgraph.md](code-patterns-langgraph.md)
- **Claude Agent SDK** — Claude Code's harness as a library (file tools, task list, subagents). Claude models only, and it starts a Claude Code process per run.
  See: [harness-engineering.md](harness-engineering.md), [agent-architecture.md](agent-architecture.md)
- **Cohen's kappa** — Agreement beyond chance: 1 is perfect, 0 is no better than guessing from each side's decision frequencies. Use it beside accuracy because accuracy depends on the class mix. It also compares a judge with a human.
  See: [evals-and-observability.md](evals-and-observability.md)
- **Compensating action** — A business step (a refund, a reversal) that undoes an effect already made. Design it as its own step with its own approval; rewinding a checkpoint cannot do it.
  See: [durable-state-and-hitl.md](durable-state-and-hitl.md)
- **Configuration version** — A saved set of the agent's instructions, model and reasoning level, with a diff, a reason, proposer, approver, status (current, kept, rolled back, under test) and held-out scores. The backend owns versions, and every run records the one it used.
  See: [self-improvement.md](self-improvement.md)
- **Confusion matrix** — One row per expert decision, one column per agent decision. The diagonal is agreement and every other cell is a named kind of mistake. Precision (of what the agent approved, the share the expert approved) and recall (of what the expert approved, the share the agent approved) come from it. Weighting the cells by business cost gives the cost of mistakes.
  See: [evals-and-observability.md](evals-and-observability.md)
- **Context engineering** — Deciding what is in the model's window at each step: instructions, the prompt, tools, memory, retrieved facts, structured output. The middle of three levels: prompt engineering, context engineering, harness engineering.
  See: [harness-engineering.md](harness-engineering.md), [context-layer-and-integrations.md](context-layer-and-integrations.md)
- **Context file header** — The source system, owner and review date at the top of every context-layer file (YAML, or Markdown front matter with a version). Return it with every answer drawn from the file, and fail start-up if one is missing.
  See: [context-layer-and-integrations.md](context-layer-and-integrations.md), [../assets/templates/CONTEXT_FILE.md](../assets/templates/CONTEXT_FILE.md)
- **Context layer (enterprise)** — A governed, read-only service that gives agents the business's knowledge, usually as MCP tools. Four parts: what the data means; how the work is done; what the agent may see and do (served by the gateway and IAM, not the context server); where it came from. Most of it is existing data governance (as taught, Oct 2026).
  See: [context-layer-and-integrations.md](context-layer-and-integrations.md)
- **Context object (`context_schema`, `ToolRuntime`)** — The ids that scope a run (item, policy, customer, who is deciding) go in a context object that tools read, so the model never chooses them. A user's token also travels there, never in graph state or config, which checkpoints save.
  See: [harness-engineering.md](harness-engineering.md), [copilot-pattern.md](copilot-pattern.md)
- **Context window** — The most tokens (prompt plus reply) a model handles in one call, and its only working memory. Everything in it goes to the model provider.
  See: [models-and-cost.md](models-and-cost.md)
- **Copilot** — An agent beside a user in the product's UI that acts with the user's own sign-in, never the back-office agent's key. It checks permissions in code, confirms only consequential actions with a saved interrupt, keeps one durable thread per conversation, and has memory keyed to the verified user.
  See: [copilot-pattern.md](copilot-pattern.md)
- **Cost of mistakes** — The business cost of each kind of wrong decision, set with the business and kept apart from API cost. UnderCover: wrongful decline $1,500, wrongful approval its payout, needless referral $50, wrong amount the difference (as taught, Oct 2026).
  See: [evals-and-observability.md](evals-and-observability.md)
- **Cost per unit of work** — Model cost per claim, ticket or document, summed over every call including failed attempts, the judge and the checks. It is the figure a business understands, not cost per token.
  See: [models-and-cost.md](models-and-cost.md)
- **`create_agent`** — LangChain's agent factory: the loop, tools from plain functions, middleware, any model. It returns a compiled LangGraph graph. A good start; move to a hand-written graph for durable pauses, a fixed order or fan-out.
  See: [agent-architecture.md](agent-architecture.md), [harness-engineering.md](harness-engineering.md)

## D

- **Decision accuracy vs accuracy** — Decision accuracy counts only the decision. Strict accuracy also needs the amount within a tolerance (UnderCover: $1). Report both; the gap is amount errors.
  See: [evals-and-observability.md](evals-and-observability.md)
- **Decision record** — What to store for each decision so it can be audited: the decision, the calculation, the rule relied on, who or what decided and when, the manual version, and the context looked up. The API rejects an incomplete one.
  See: [context-layer-and-integrations.md](context-layer-and-integrations.md), [../assets/templates/CONTEXT_FILE.md](../assets/templates/CONTEXT_FILE.md)
- **Deep Agents** — LangChain's ready-made harness on `create_agent`: file tools, a `task` subagent tool, a to-do list and summarising of long conversations; open source, any model. Quick for file-shaped jobs, but state is files in a folder.
  See: [harness-engineering.md](harness-engineering.md)
- **Defence in depth** — For any consequential action (paying, deleting, sending), use at least three independent layers that could each stop it: the agent (instructions, a model check), a gateway policy, and the app's own limit. Test each layer on its own.
  See: [security-and-guardrails.md](security-and-guardrails.md)
- **Dispatcher** — A LangGraph graph with no model. It lists the items, fans out one worker per item with `Send`, caps parallelism with `max_concurrency`, and collects results with a reducer. Choosing the next item is a fixed rule, so a model adds only cost.
  See: [swarms-and-scale.md](swarms-and-scale.md), [code-patterns-langgraph.md](code-patterns-langgraph.md)
- **`durability="sync"`** — A LangGraph option: each step's checkpoint is saved before the next step starts. The default saves in the background, which risks losing the latest step in a crash (verify on your version).
  See: [durable-state-and-hitl.md](durable-state-and-hitl.md)
- **Durable execution** — A run can stop partway and carry on from where it got to, because state is saved in a database after every step. Needed for steps that wait on people, long runs, and hosts that can end the process.
  See: [durable-state-and-hitl.md](durable-state-and-hitl.md)

## E

- **Eval set (development set)** — The labelled items you look at, tune on and learn from (UnderCover: the 25 queue claims). Keep it apart from the held-out, adversarial, final test and tiny sets.
  See: [evals-and-observability.md](evals-and-observability.md)
- **Evals (three kinds)** — Direct measurement (code compares output with a known answer), LLM as a judge (for free text code cannot check), and human review (to sample, calibrate and build trust). Use the cheapest kind that answers the question.
  See: [evals-and-observability.md](evals-and-observability.md), [self-improvement.md](self-improvement.md)

## F

- **Fail closed** — If a safety check cannot answer (an error, or an unreadable reply after retries), the item stops and goes to a person. It is never waved through.
  See: [security-and-guardrails.md](security-and-guardrails.md)
- **FDE (forward deployed engineer)** — Narrow: a senior applied AI engineer embedded with a client. Broad: an applied AI engineer who solves commercial problems and delivers to customers. The term came from Palantir around 2007 (as taught, Oct 2026). The course covers AI engineering, AI architecture and forward deployed engineering.
  See: [fde-lifecycle-and-governance.md](fde-lifecycle-and-governance.md)
- **Fleet, swarm, team** — Three shapes, as named in the course (Oct 2026). Team: a few agents on one task. Swarm: many agents, each on one item of a batch, in parallel. Fleet: every agent a business runs, for governance, inventory and cost.
  See: [swarms-and-scale.md](swarms-and-scale.md)
- **Function URL** — A Lambda function's HTTPS address. Auth type `NONE` is public: it needs two permissions (`lambda:InvokeFunctionUrl` and `lambda:InvokeFunction` via the URL) or every request is a 403, and the app must do its own auth. Auth type `AWS_IAM` lets only signed, permitted callers in (the context-layer server).
  See: [security-and-guardrails.md](security-and-guardrails.md), [production-deployment-aws.md](production-deployment-aws.md), [code-patterns-platform.md](code-patterns-platform.md)

## G

- **Gateway (API, MCP, model)** — Three kinds. API gateway: the front door to company APIs (keys, rate limits, logs). MCP gateway: turns APIs into tools and controls who may call which. Model gateway: one API in front of many models (budgets, fallbacks). Products as taught (Oct 2026): AgentCore Gateway, Azure API Management, Kong, OpenRouter, LiteLLM. Start lightweight: an in-app key check and a model router.
  See: [security-and-guardrails.md](security-and-guardrails.md)
- **Guardrails** — Controls on what goes into and out of the model, and on tools. Four kinds: LLM validator, coded check, flagging in the platform, and testing and audits. The tool layer is stronger because it does not depend on the model reading anything correctly.
  See: [security-and-guardrails.md](security-and-guardrails.md)

## H

- **Handover** — The test of an engagement: the client's team can run, measure and change the system without the FDE. It covers ownership and escalation, knowledge transfer (runbook, ADRs, deploy, rotate secrets, tear down, roll back) and ongoing measurement, plus adoption.
  See: [fde-lifecycle-and-governance.md](fde-lifecycle-and-governance.md), [../assets/templates/HANDOVER.md](../assets/templates/HANDOVER.md)
- **Harness** — The software around a model that makes it an agent. Seven parts: context, workflow, state, subagents, permissions, observability, self-improvement.
  See: [harness-engineering.md](harness-engineering.md)
- **Harness engineering** — Designing the harness; the third level after prompt engineering and context engineering. With a coding agent you are a harness user; with the product's agent you are the harness builder.
  See: [harness-engineering.md](harness-engineering.md)
- **Harness, Harden, Humans** — The three parts of the second ADLC meaning. Harness: what you give the coding agent (docs, plan, tools, permissions). Harden: automated gates that catch its mistakes. Humans: what stays with people (accountability, evaluations, judgment, taste).
  See: [building-with-coding-agents.md](building-with-coding-agents.md)
- **Heartbeat (one run at a time)** — A database lock, not an in-process flag, decides that only one run works at a time. The agent reports every minute, and work silent for five minutes counts as stopped (UnderCover's values).
  See: [swarms-and-scale.md](swarms-and-scale.md), [production-deployment-aws.md](production-deployment-aws.md)
- **Held for sign-off** — An approval over the limit, waiting for an authorised person. It still counts as straight-through, and after sign-off the app pays. One of three outcomes to keep apart, with referral and left for a handler.
  See: [durable-state-and-hitl.md](durable-state-and-hitl.md), [harness-engineering.md](harness-engineering.md)
- **Held-out set** — Items the tuning loop never reads, with the same blend as the eval set. It checks that an improvement generalises; only scores, never items, reach the improver. Its scores choose which versions are kept, so a final check needs a separate test set.
  See: [evals-and-observability.md](evals-and-observability.md), [self-improvement.md](self-improvement.md)
- **HITL (human in the loop)** — A designed step where a person approves or corrects. Ask when, who, what they see, and what answers they have: sign off, or send back with a note. Make it durable with an interrupt, and read the answer from your own record.
  See: [durable-state-and-hitl.md](durable-state-and-hitl.md)

## I

- **Idempotency** — Repeating an action has no further effect. For pay-once: the side effect gets its own node, the system of record checks the item ID (for example a primary key with `ON CONFLICT DO NOTHING`), and the backend treats a repeat as done.
  See: [durable-state-and-hitl.md](durable-state-and-hitl.md), [code-patterns-langgraph.md](code-patterns-langgraph.md)
- **Improver** — An agent whose instructions are a recipe. It reads evaluation results and proposes a configuration change (a human approves), code runs the evaluations and keeps or rolls back, and it may propose an improved recipe under the same approval.
  See: [self-improvement.md](self-improvement.md)
- **Instructions as goals** — Give the model a goal and tools, and put anything that must always happen, or happen in order, in code. A numbered script of steps is a workflow written in prose.
  See: [harness-engineering.md](harness-engineering.md), [agent-architecture.md](agent-architecture.md)
- **`interrupt()` and `Command(resume=...)`** — LangGraph's pause and resume. `interrupt()` saves state and stops; `Command(resume=answer)` carries on, and the interrupted node reruns from its top. So put nothing with a side effect before `interrupt()`.
  See: [durable-state-and-hitl.md](durable-state-and-hitl.md)

## J

- **Jev** — A decision model from TypeSafe AI used as the course's judge: it returns probabilities over a fixed grade scale and writes no prose, called through OpenRouter's Decisions endpoint, which is in alpha (as taught, Oct 2026).
  See: [self-improvement.md](self-improvement.md)

## K

- **Keep or roll back** — The rule, in code, that decides whether a new configuration version stays. It uses held-out scores against objectives, noise thresholds, tolerances and a budget that the business owns and the improver cannot change. A version with no grade is rolled back.
  See: [self-improvement.md](self-improvement.md)

## L

- **Lambda (AWS Lambda)** — Serverless functions. In the course the app (FastAPI behind Mangum) and the context-layer server each run as a Lambda function, while the agent runs on AgentCore Runtime (as taught, Oct 2026).
  See: [production-deployment-aws.md](production-deployment-aws.md), [code-patterns-platform.md](code-patterns-platform.md)
- **Langfuse** — An open-source tracing and evaluation platform, self-hosted or cloud. Concepts: trace, dataset, experiment, score (as taught, Oct 2026).
  See: [evals-and-observability.md](evals-and-observability.md)
- **LangGraph** — A library for hand-written agent graphs: typed state, nodes, edges, conditional edges, reducers, checkpoints and interrupts.
  See: [durable-state-and-hitl.md](durable-state-and-hitl.md), [code-patterns-langgraph.md](code-patterns-langgraph.md)
- **Least privilege** — Each caller, role and tool gets only what it needs, so a leaked key or an injected agent reaches little. Separate roles for the app, the runtime, the Gateway and the human operator.
  See: [security-and-guardrails.md](security-and-guardrails.md), [production-deployment-aws.md](production-deployment-aws.md)
- **Left for a handler** — The item failed twice, so the agent produced no decision and a handler (a person) works it by hand. A reliability failure to fix. One of three outcomes to keep apart, with held for sign-off and referral.
  See: [harness-engineering.md](harness-engineering.md), [swarms-and-scale.md](swarms-and-scale.md)
- **Lethal trifecta** — Simon Willison's term: an agent is exposed to data theft and hijack when it combines private data, untrusted content and the ability to communicate externally. Break at least one leg; cutting external communication is usually cheapest. Bind identifiers in code.
  See: [security-and-guardrails.md](security-and-guardrails.md)
- **LLM as a judge** — A model that grades free text (such as a rationale) against an expert's reference, choosing from a fixed scale with a rubric rather than writing prose. Ground it, calibrate it, and keep it a different model from the agent.
  See: [self-improvement.md](self-improvement.md)
- **Log-only mode** — A policy engine mode that records what it would refuse and lets every call through. Watch the decisions, then switch to enforce.
  See: [security-and-guardrails.md](security-and-guardrails.md)

## M

- **Mangum** — An adapter that runs a web app (FastAPI, an MCP server) as a Lambda function. It runs an app's start-up and shutdown around every request, so a context server builds a fresh MCP server inside the handler.
  See: [code-patterns-platform.md](code-patterns-platform.md), [context-layer-and-integrations.md](context-layer-and-integrations.md)
- **MCP (Model Context Protocol)** — An open standard for connecting agents to tools. Roles: host (runs the agent), client (connects to a server) and server (offers tools). Transports: stdio (a local process the client starts) and Streamable HTTP (a remote or local HTTP service that can be authenticated). Use MCP for shared tools or tools behind a gateway; a tool only your agent calls can be a plain function.
  See: [rag-memory-and-mcp.md](rag-memory-and-mcp.md)
- **Memory (short-term, long-term, namespace)** — Short-term memory is the conversation history and checkpoints of one thread. Long-term memory persists across threads: facts, preferences, summaries, episodes. A namespace partitions it (for example `/customers/{actorId}/facts/`), and the actor is the privacy boundary. Decide in code what is always saved; the model decides what to search.
  See: [rag-memory-and-mcp.md](rag-memory-and-mcp.md)
- **Memory strategies** — AgentCore Memory's four extraction strategies: Semantic (facts), Preference (user-related information), Summary (a compressed account per claim or session) and Episodic (past task episodes). Choose by experiment on your business metric and prefer the simpler one (as taught, Oct 2026).
  See: [rag-memory-and-mcp.md](rag-memory-and-mcp.md)
- **Middleware hooks** — Points in LangChain's `create_agent` loop where your code runs: `before_agent` (once, before the model sees anything; screening), `before_model`, `after_model` (check the tool calls asked for), `wrap_model_call`, `wrap_tool_call`. End a run with `can_jump_to=["end"]`. A hand-written graph does the same with nodes.
  See: [harness-engineering.md](harness-engineering.md)
- **MoE (mixture of experts)** — A model with many total parameters that activates only a subset per token (the active parameters). You still need memory for all the weights. In `550b-a55b`, 550B is total and 55B active.
  See: [models-and-cost.md](models-and-cost.md)

## N

- **Noise threshold** — How far a measure must improve before the change counts. Find it by running the same version twice on the same set, and set the threshold just above the spread. A tolerance is how far another measure may worsen. Lab starting values: accuracy 0.10, grade 0.15, cost and time 15% (as taught, Oct 2026).
  See: [evals-and-observability.md](evals-and-observability.md), [self-improvement.md](self-improvement.md)

## O

- **OpenAPI document (for a Gateway)** — A document listing only the agent's operations; each becomes a tool. Give every operation an `operation_id` and a one-line description, no optional inputs, no servers and no security schemes. Operations left out, such as sign-off, cannot be reached by the agent.
  See: [security-and-guardrails.md](security-and-guardrails.md), [code-patterns-platform.md](code-patterns-platform.md)
- **OpenRouter** — A model router: one API in front of many models and providers, with per-call cost in the response (`usage.cost`) and routing controls such as `require_parameters`. Free models are for learning and fictional data only (as taught, Oct 2026).
  See: [models-and-cost.md](models-and-cost.md)
- **Open-weight** — A model whose weights are published, so anyone with hardware can serve it. Chosen for privacy and control, not necessarily lower cost; a third-party host still sees your prompts. Open-source also publishes nearly everything needed to reproduce it, and is rarer.
  See: [models-and-cost.md](models-and-cost.md)

## P

- **Pareto front** — The models that no other model beats on every axis (intelligence, speed, cost) at once. Start the shortlist there, then decide with your own evals.
  See: [models-and-cost.md](models-and-cost.md)
- **Progressive disclosure** — Keep the always-loaded file short and point to detail that is read on demand. This skill works that way: `SKILL.md`, then `references/`, then `assets/templates/`; `AGENTS.md` does the same for a repo.
  See: [building-with-coding-agents.md](building-with-coding-agents.md), [../README.md](../README.md)
- **Prompt caching** — The provider reuses its processing of a long, repeated beginning of a prompt and charges less for it. Put stable text first (instructions, wording, tool definitions) and the variable part last. Rules differ by provider (verify).
  See: [models-and-cost.md](models-and-cost.md)
- **Prompt injection** — Text the agent reads that tries to give it orders. Defend by breaking the lethal trifecta, screening input with a cheap model check before the agent's first model call, referring (not rejecting) flagged items, failing closed, and enforcing limits in code. No set of checks is bulletproof.
  See: [security-and-guardrails.md](security-and-guardrails.md)

## Q

- **Quantization** — Storing a model's weights at lower precision to save memory. 8-bit costs little accuracy; 4-bit starts to show. QAT (quantization-aware training) trains the model to hold up at low precision.
  See: [models-and-cost.md](models-and-cost.md)

## R

- **RAG (retrieval-augmented generation)** — Split documents into chunks, embed each chunk (a vector that captures meaning) into a vector database, and at question time search by meaning and put the nearest chunks in the prompt. Start with a plain word search as the control; the vector database must beat it on your own cases.
  See: [rag-memory-and-mcp.md](rag-memory-and-mcp.md)
- **Reasoning effort** — A setting (`none`, `minimal`, `low`, `medium`, `high`, depending on the model) for how many thinking tokens a model spends. Thinking tokens bill as output. Levels are model-specific and a provider may ignore your setting. Keep it in versioned configuration, and use a sentinel for "send no parameter".
  See: [models-and-cost.md](models-and-cost.md)
- **Reducer** — How an update to a state key is merged (`add_messages` appends, `operator.add` joins lists). Required when several nodes, such as parallel workers, write the same key in one step.
  See: [durable-state-and-hitl.md](durable-state-and-hitl.md), [swarms-and-scale.md](swarms-and-scale.md)
- **Referral** — The agent could not decide, or a guardrail flagged the item, so a handler looks at it. A valid, scored decision, not a failure, and not straight-through. One of three outcomes to keep apart, with held for sign-off and left for a handler.
  See: [harness-engineering.md](harness-engineering.md), [security-and-guardrails.md](security-and-guardrails.md)
- **Responsible AI** — Six pillars to budget and plan for during the project and after go-live: safety, fairness and bias, security, privacy, transparency and accountability. A human is always accountable.
  See: [fde-lifecycle-and-governance.md](fde-lifecycle-and-governance.md)
- **RetryPolicy** — LangGraph's retry of a whole node with growing waits (UnderCover: three attempts, starting at 10 seconds). Retry only errors that pass with time, such as rate limits and timeouts, and only where repeats are safe because the backend is idempotent.
  See: [swarms-and-scale.md](swarms-and-scale.md)
- **RSI (recursive self-improvement)** — A system that improves the process that improves it. The course's version is small and bounded: the improver edits the agent's configuration and its own recipe, inside business limits, with a human approving each step.
  See: [self-improvement.md](self-improvement.md)

## S

- **Send** — The LangGraph primitive for fan-out. A conditional edge returns one `Send("node", payload)` per item, and the workers run in parallel. If there is nothing to send, route straight to the end.
  See: [swarms-and-scale.md](swarms-and-scale.md)
- **Session (AgentCore Runtime)** — One microVM. The first call with a new session id is cold, later calls with the same id are warm; ids must be at least 33 characters. Use one session per unit of work (a dispatch, a conversation). Sessions are disposable, so nothing the agent needs lives in one.
  See: [production-deployment-aws.md](production-deployment-aws.md)
- **Sign-off and send back** — The two answers a person gives a held decision. Sign off: an authorised person releases it (the app performs the payment itself; it is not a Gateway tool). Send back with a note: the current decision is cleared, the old one stays on record, and the agent decides again. Read the answer from your own record, not the resume request.
  See: [durable-state-and-hitl.md](durable-state-and-hitl.md)
- **SigV4** — AWS request signing. The agent signs its calls to the Gateway with its runtime role, and the Gateway signs its calls to an IAM-protected Function URL with its own role.
  See: [context-layer-and-integrations.md](context-layer-and-integrations.md), [production-deployment-aws.md](production-deployment-aws.md)
- **Straight-through rate** — The share of items the agent handles without referring them to a person. It counts approvals held for sign-off, and an item the agent never decided counts as referred. Report it beside accuracy and the cost of mistakes.
  See: [evals-and-observability.md](evals-and-observability.md)
- **Structured outputs** — A model reply that must match a schema, so code can use it directly. Put the rationale field before the decision and amount, use `Literal` or enums for closed sets, and describe every field, including units.
  See: [agent-architecture.md](agent-architecture.md)
- **Subagent** — A helper that works one item in a fresh context and reports one line built from the system of record. Add another agent only to isolate context, add an independent check, use a different model, work in parallel or ring-fence permissions.
  See: [harness-engineering.md](harness-engineering.md), [agent-architecture.md](agent-architecture.md)
- **Success criteria** — A measurable statement with a measure, a baseline and a target, agreed at the first tollgate. Include at least one limit criterion (something that must always hold) beside the performance criteria.
  See: [fde-lifecycle-and-governance.md](fde-lifecycle-and-governance.md), [../assets/templates/EVAL_PLAN.md](../assets/templates/EVAL_PLAN.md)
- **Swarm** — See Fleet, swarm, team.
  See: [swarms-and-scale.md](swarms-and-scale.md)
- **System of record** — The database that holds the records the business relies on, and the agent's checkpoints. The agent reaches business records through the app's API, never the database, so the app's rules apply to every caller.
  See: [agent-architecture.md](agent-architecture.md), [context-layer-and-integrations.md](context-layer-and-integrations.md)

## T

- **Team** — See Fleet, swarm, team.
  See: [swarms-and-scale.md](swarms-and-scale.md)
- **Teardown** — Deleting what you built, by name and tag, and verifying three ways: by name, by account-wide index and by cost. Delete targets before the gateway and policies before the engine. Never create or delete cloud resources unless the developer asks.
  See: [production-deployment-aws.md](production-deployment-aws.md), [code-patterns-aws-agentcore.md](code-patterns-aws-agentcore.md)
- **Thread** — The id that groups one work item's checkpoints. Use one thread per item or conversation, so a pause on one item holds up no other.
  See: [durable-state-and-hitl.md](durable-state-and-hitl.md), [swarms-and-scale.md](swarms-and-scale.md), [code-patterns-langgraph.md](code-patterns-langgraph.md)
- **Three traps** — Common ways agent projects go wrong. "Agent for X": start from a measurable business problem. Human-like agents: start with one agent and add more only when they measurably help. Plausible versus accurate: measure with evals.
  See: [agent-architecture.md](agent-architecture.md)
- **Tiny set** — A handful of items (UnderCover: five per set, one of each kind) for smoke tests and free-model allowances. Never use it for conclusions or model rankings.
  See: [evals-and-observability.md](evals-and-observability.md)
- **Token** — A piece of text a model reads or writes (about three quarters of an English word). Billing has four parts: input, cached input, output and reasoning tokens; prices are quoted per million.
  See: [models-and-cost.md](models-and-cost.md)
- **Tollgate** — A sponsor's sign-off at the end of each lifecycle phase: agree scope and budget, approve the build, go/no-go, program success, change management. It forces an explicit decision instead of letting work slide forward.
  See: [fde-lifecycle-and-governance.md](fde-lifecycle-and-governance.md)
- **Tool artifact** — The second value a tool returns (`response_format="content_and_artifact"`). It never reaches the model; the harness records it, for example as a "reading" step for the UI.
  See: [harness-engineering.md](harness-engineering.md)

## U

- **UnderCover** — The course's fictional travel insurer. Its claims platform (a backend, a dashboard, a claim agent, later a swarm, an improver and a Copilot) is the worked example in every reference.
  See: [undercover-case-study.md](undercover-case-study.md)

## V

- **Vibe coding** — Prompting an LLM for code and accepting what comes back. Fine for small pieces; keep it short, simple and testable, and never accept code you cannot debug.
  See: [building-with-coding-agents.md](building-with-coding-agents.md)

## W

- **Work copy** — An evaluation runs on copies of the labelled items through the same dispatcher and agent as real work. Copies never reach the real queue, cannot be signed off, and their saved progress is cleared. Evaluate on copies, never on live data.
  See: [evals-and-observability.md](evals-and-observability.md)
- **Workflow** — A path through steps that the code decides, even if steps call a model, branch, loop or run in parallel. The line between workflow and agent is who chooses the next step.
  See: [agent-architecture.md](agent-architecture.md)
