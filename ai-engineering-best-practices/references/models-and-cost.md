# Models and cost

> When to read this: the developer must choose a model (or several), set reasoning effort, decide between a frontier API, an open-weight model or a local one, estimate or cap what the system will cost, or answer a privacy question about where prompts go. Load it before writing the "models" and "cost" sections of an architecture document.

Names, prices, limits and model lineups below are "as taught in the course (Oct 2026)". Re-check them before quoting them to a customer.

## Contents

- [Key principles](#key-principles)
- [How an LLM becomes a product](#how-an-llm-becomes-a-product)
- [Tokens, context window and pricing](#tokens-context-window-and-pricing)
- [Comparing models](#comparing-models)
- [Reasoning effort and model as configuration](#reasoning-effort-and-model-as-configuration)
- [The selection method](#the-selection-method)
- [Proprietary, open-weight and open-source](#proprietary-open-weight-and-open-source)
- [Running models yourself](#running-models-yourself)
- [Routers and providers](#routers-and-providers)
- [Cost engineering](#cost-engineering)
- [Decisions to make with the developer](#decisions-to-make-with-the-developer)
- [Pitfalls and anti-patterns](#pitfalls-and-anti-patterns)
- [In UnderCover](#in-undercover) / [Related](#related) / [Sources](#sources)

## Key principles

1. **Shortlist with benchmarks, decide with your own evals.** Public leaderboards measure other people's tasks; only your eval set measures your customer's task. Never ship a model choice that rests on a leaderboard alone.
2. **Pick the cheapest model that consistently clears the quality bar.** Set the bar first (for example "at least 15 of 25 right, every run"), then walk down in price until it fails. Anything above that is paid for nothing.
3. **Run each candidate more than once.** Model output varies between runs, so one run of 25 items cannot rank models or show a small gain. Compare differences against the measured noise.
4. **Model and reasoning level are configuration, not code.** Keep both in a versioned config (with an environment override), so changing them is a config change that the evals can judge, not a refactor.
5. **Measure cost per unit of work, not per token.** "Cost per claim" (or per ticket, per document, per conversation) is the number the business understands and the one to record on every run.
6. **Weigh API cost against the business cost of mistakes.** A fraction of a cent per item is usually dwarfed by one costly wrong decision. Spend more where errors are expensive; economise where volume is high and errors are cheap.
7. **Every extra model call re-sends the context.** A tool loop, an agent or a swarm multiplies input tokens. Keep prompts lean, put stable text first (it can be cached), and ask whether a single call would do.
8. **Open weights buy privacy and control, not necessarily lower cost.** They only keep data private if you (or a party you trust) host them. Choose them for a stated privacy, control or sovereignty need.
9. **Put a hard limit outside your code.** Budgets in code can have bugs. Also set a credit limit on the provider key and a budget alert on the cloud account.
10. **Know where prompts go.** Everything in the context window is sent to the model provider. Check the training and retention terms, minimise personal data, and never send confidential data to free endpoints.

## How an LLM becomes a product

The course explains the gap between a raw language model and a chat product as six tricks. Use them to explain behaviour to a customer and to reason about cost:

| Trick | What it means for the architect |
|---|---|
| Autoregression | The model writes one token at a time, each conditioned on everything before it. Longer outputs cost more and take longer. |
| Chat | A fine-tuned model that follows a turn format (system, user, assistant). The system prompt sets behaviour. |
| Reasoning | The model writes "thinking" tokens before answering. Better on hard problems, slower, and billed as output tokens. |
| The illusion of memory | The model is stateless. The application re-sends the whole conversation on every call, and you pay for it every time. |
| Context | Anything the model needs (policy text, records, retrieved facts) must be put in the prompt. The context window is its only working memory. |
| Tools | The model asks for a function call; the application runs it and feeds back the result. This is the basis of agents (see [agent architecture](agent-architecture.md)). |

Consequences: the model knows nothing about the customer's data unless you supply it; each loop iteration costs a full prompt; and quality depends as much on what you put in the context as on which model you pick.

## Tokens, context window and pricing

**Tokens** are the pieces of text a model reads and writes. In English a token is roughly three quarters of a word. Prices are quoted in US dollars per million tokens.

**Context window** is the maximum number of tokens (prompt plus reply) a model can handle in one call. Check it against your largest realistic prompt. Local runtimes may set a smaller window than the model supports (see the Ollama note below).

**What you are billed for:**

| Component | Notes |
|---|---|
| Input tokens | Everything you send: system prompt, policy text, history, tool results, the item itself. |
| Cached input tokens | Input the provider has recently processed and can reuse, billed at a lower rate than fresh input. |
| Output tokens | What the model writes. Usually several times the price of input. |
| Reasoning tokens | Thinking tokens. Counted and billed as output, even though you may never see them. |

**Prompt caching.** When a long, stable beginning of a prompt repeats across calls, the provider can reuse its processing and charge less for it. Design for it: put stable content first (instructions, policy wording, tool definitions) and the variable part last (the individual claim). The course's prompts follow this shape, with instructions and wording in the system message and the claim in the user message. Rules differ per provider (minimum size, lifetime, discount, whether you must opt in); read the provider's documentation before promising savings `(verify)`.

**Worked example (Ed's runs, Oct 2026).** Prices per million tokens for the three models allowed in UnderCover's improver:

| Model | Input | Output | Reasoning levels offered |
|---|---|---|---|
| `openai/gpt-6-luna` | $0.10 | $0.50 | none, low, medium |
| `google/gemini-3.5-flash-lite` | $0.30 | $2.50 | minimal, low |
| `deepseek/deepseek-v4.1-flash` | $0.30 | $1.20 | low |

For the 25-claim queue, one run cost about $0.0042 on Luna at `low` and $0.0318 on Gemini 3.5 Flash Lite: roughly $0.0002 against $0.0013 a claim. The cheaper list price also gave the cheaper run here, but check this with your own prompts, since reasoning tokens and verbosity change the total.

**Smaller prompts are an easy saving.** Week 1 Day 4 trims the prompt three ways: a short version of the policy wording, only the sections that matter for the claim type, and compact JSON without ids or document text. This costs less, runs faster and suits small models, but can leave out something the model needs. Measure the effect on accuracy, do not assume it.

## Comparing models

Compare on three axes at once: **intelligence** (quality on tasks like yours), **speed** (latency and tokens per second) and **cost**.

- **Artificial Analysis** publishes intelligence, speed and price for many models. Read the **Pareto front**: the models that no other model beats on every axis at once. A model off the front is dominated (something is at least as good and cheaper or faster), so start the shortlist from the front.
- **METR time horizons** track how long a task (measured in human working time) models can complete at a stated success rate. Use it as a read on the trend in agentic capability, not as a way to choose a model for a narrow task.
- **Leaderboards are for shortlisting.** Take three to six candidates across price tiers and test them on the customer's own task with an eval set (see [evals and observability](evals-and-observability.md)).
- **Plot your own results.** The Week 1 Day 4 lab charts accuracy against cost, accuracy against speed and all three together for nine models. The best place on the first two charts is the top left (accurate and cheap, accurate and fast).
- **Include a naive baseline.** On the 20 non-manual claims, approving everything gets 60% of decisions right. A model that scores 65% is not impressive.
- **Report both a loose and a strict score.** The labs track decision accuracy and the stricter accuracy that also needs the payout within $1.

Useful extras the labs showed: a specialised fast model (Jev) can make the decision alone in a fraction of a second and return a confidence, so you can keep its confident answers and send the rest to a stronger model; Cerebras served a 27B model at about 1,850 tokens a second on its own chips.

## Reasoning effort and model as configuration

**Reasoning effort** (`none`, `minimal`, `low`, `medium`, `high`, depending on the model) controls how many thinking tokens a model spends. It is a tunable that trades cost and latency for quality, just like the model itself.

- **Levels are model-specific.** In the Day 4 lab, MiMo V2.6 Pro has no reasoning setting, GLM 5.3 Flash always reasons (`low` is its lowest), Nemotron 3 Ultra starts at `medium`, and Mistral Medium 3.5 offers only `high` or `none`. Each model ran at the lowest level it offers. Store the allowed levels per model.
- **A provider may ignore your setting.** One of GLM 5.3 Flash's providers disregarded `low` and spent as many as 3,000 thinking tokens on a single claim. The lab excluded that provider. Record which provider answered and watch tokens per call.
- **"No setting" is a value of its own.** OpenAI's `none` is a real level. The UnderCover backend uses a separate sentinel (`default`) to mean "send no reasoning parameter at all", and records it as such.
- **Free models can hang when you set a level.** The CPU lab leaves the default for free models for that reason.
- **Try reasoning before prompt rules.** In Ed's build the improver's recipe tries other models and reasoning levels before it adds rules to the prompt, and the claim agent starts at `none` so a higher level is a finding a round can make.

**Keep the choice in configuration**, not in code:

```json
{
  "model": "openai/gpt-6-luna",
  "reasoning_efforts": ["none", "low", "medium"],
  "input_price": 0.1,
  "output_price": 0.5
}
```

```python
NO_REASONING_EFFORT = "default"  # send nothing; "none" is a real OpenAI level

def chat_model(model: str, reasoning_effort: str, timeout: int = 120) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if reasoning_effort == NO_REASONING_EFFORT else reasoning_effort,
        timeout=timeout,
        max_retries=5,
    )

def model_or_override(model: str, effort: str) -> tuple[str, str]:
    override = os.getenv("MODEL_NAME")  # one place reads it
    return (override, NO_REASONING_EFFORT) if override else (model, effort)
```

Rules that follow from the course's build:

- One factory builds every chat model; the base URL is a setting, so a local or self-hosted endpoint is a configuration change (Day 4's stretch task says the product first needs a base URL setting).
- A single place reads the environment override (`MODEL_NAME` in UnderCover), and the override also replaces the price list (price 0) and the allowed list.
- The agent's configuration (instructions, model, reasoning effort) is versioned, and every run records which version it used. See [self-improvement](self-improvement.md).
- The list of models allowed, with prices, is business-owned data that an improver agent cannot edit.
- Set the override before seeding if the seed stores the model in the configuration (from Week 2 Day 5 in UnderCover).

## The selection method

This is the Week 1 Day 2 assignment generalised: find the cheapest model that **consistently** meets the bar with the architecture you will ship.

1. **Fix the task and the eval set.** Use labelled items with an answer key the model never sees (see [evals and observability](evals-and-observability.md)). Hold out a second set for final checks.
2. **Fix the bar.** For example "at least 60% accuracy" or "15 of 25 each run", plus limits on cost per item and seconds per item.
3. **Shortlist from the Pareto front and from your constraints** (privacy, region, licence, context length, structured outputs and tool-calling support).
4. **Run the real pipeline** (agent or single call, as you will ship it) with the same prompt and tools, recording accuracy, cost, tokens, seconds, provider and reasoning level per item.
5. **Repeat.** Run each candidate at least three times; Ed used three runs in Week 2 Day 1. Estimate the noise from two runs of the same version, and treat differences below it as no difference.
6. **Walk down the price ladder.** Try a cheaper model or a lower reasoning level until the bar fails, then go back one step.
7. **Check the misses.** Read the wrong answers: a pattern (missing document, wrong rule) often says "fix the prompt or the tool", not "buy a bigger model".
8. **Confirm on held-out items** and record the decision, the numbers and the date in an ADR (`../assets/templates/ADR.md`).
9. **Re-run when anything changes**: a new model, a new price, a prompt change, a provider switch.

Example from the labs: a single structured-output call on Luna at `low` beat or matched the LangChain agent on the same task, while the agent took longer and cost more. For a fixed workflow, do not assume an agent is the better design.

## Proprietary, open-weight and open-source

| Kind | What you get | Typical reasons to choose it |
|---|---|---|
| Proprietary (API only) | Hosted by the lab; weights are secret. | Highest capability, least operations work. |
| Open-weight | Weights are published; anyone with hardware can serve them. Licences vary. | Privacy and control (self-hosting), choice of hosts, fine-tuning, no vendor lock-in. |
| Open-source | Weights plus (nearly) everything needed to reproduce them, under an open licence. | Auditability and licence freedom. Rarer than open-weight. |

The definitions are the common ones; always read the licence of a model you adopt. Key points from Day 4:

- **Open weights are mostly about privacy and control, and are not necessarily cheaper.** Frontier APIs are priced aggressively, and self-hosting adds hardware, operations and idle capacity.
- **A third-party host of an open-weight model still sees your prompts.** The privacy benefit appears when you run it on hardware you control, or when the host's terms meet your need.
- **Dense versus mixture of experts (MoE).** A dense model uses all its parameters for every token. An MoE model has many total parameters but activates only a subset per token (the **active parameters**). MoE gives more capability per unit of compute, but you still need memory for all the weights. In a name like `nemotron-3-ultra-550b-a55b`, the first figure is total size and `a55b` the active size.
- **Quantization** stores weights at lower precision to shrink memory. 8-bit costs little accuracy; 4-bit starts to show. **QAT** (quantization-aware training) trains the model to hold up at low precision. The lab's `gemma4:e2b-it-qat` is an instruction-tuned model trained to run at 4 bits.
- **File formats:** safetensors (the common weights format), GGUF (used by llama.cpp and Ollama), MLX (Apple silicon).
- **Reading a model name**, using the course's examples:

| Fragment | Meaning |
|---|---|
| `qwen3.5:4b` | Family and version, then parameter count (4 billion). |
| `e2b`, `e4b` | A size tag of the Gemma 4 family (verify the exact meaning on the model card). |
| `it` | Instruction-tuned (follows chat instructions). |
| `qat` | Quantization-aware training. |
| `550b-a55b` | 550B total parameters, 55B active (MoE). |
| `flash`, `lite`, `luna`, `sol` | A vendor's tier names: smaller or cheaper versus larger or more capable. Check the vendor's list. |

## Running models yourself

**Tools.** Ollama (easy local runner; downloads with a pull, loads on first use, unloads after idle), LM Studio (desktop app), llama.cpp (the engine under many tools, GGUF files), vLLM (a high-throughput inference server, used on rented GPUs).

**What fits on a machine.** Weights need roughly parameters times bytes per weight (about 2 bytes at 16-bit, 1 at 8-bit, 0.5 at 4-bit), plus room for the context cache and the operating system `(rule of thumb)`. From the lab: `qwen3.5:4b` (3.4 GB) and `gemma4:e2b-it-qat` (4.3 GB) fit an 8 GB computer; `gemma4:e4b` (9.6 GB) needs 16 GB and was the slowest. The CPU lab uses models of 1 billion parameters or fewer (about 2.5 GB in total) and warns that they can give odd answers.

**Memory bandwidth sets speed.** Generating each token means reading the active weights from memory, so tokens per second is limited mainly by memory bandwidth, not just compute. GPUs and unified memory machines beat a plain CPU for this reason.

**Practical notes from the lab.**

- Constrain output to the schema (Ollama accepts a JSON schema as `format`), so even a small model returns valid JSON. Valid does not mean correct; still score it.
- `think=False` turns reasoning off to keep small models quick.
- Ollama sets the context window to 4,096 tokens whatever the model supports; set `num_ctx` explicitly or long prompts are silently cut.
- Unload a model (`keep_alive=0`) before loading the next so memory is free.
- Local cost per call is $0 in the lab's table, but hardware, power and your time are real. Small local models struggled with the claims.

**Ways to host an inference server.** The slides give four options and the slides are not in the repo, so treat this list as indicative `(verify)`: your own machine, a server in your own data centre or cloud account, a rented GPU (the course shows Runpod, running vLLM), or a managed or hosted service. A stretch task in the course points the product at a vLLM server on a rented GPU. Whatever the choice, the application should reach it through an OpenAI-compatible base URL setting.

**Bedrock correction.** Amazon Bedrock runs the models in AWS's own accounts and does not forward your calls to Anthropic. For a customer who wants prompts to stay within AWS accounts, that is a different proposition from calling the model lab's own API. UnderCover's model calls stay on OpenRouter throughout Week 3.

## Routers and providers

A router (OpenRouter, LiteLLM) puts one API in front of many models and providers. It makes model changes a config change and gives you one bill and one cost field.

- **Providers differ.** On OpenRouter most open-weight models have several providers that differ in **precision** (quantization), **features** (structured outputs, reasoning parameters), **price** and **speed**. Two providers of the same model can give different accuracy and cost.
- **Constrain routing.** `provider: {"require_parameters": True}` limits routing to providers that support every parameter you send, including structured outputs. `provider: {"ignore": ["<provider>"]}` skips one that misbehaves. Pinning a specific provider or order is also possible `(verify the field names in OpenRouter's documentation)`. Record the provider named in each response.
- **Cost comes back in the response** (`usage.cost` on OpenRouter). Some direct providers do not report cost (Cerebras did not in the lab), so compute it from token counts and a dated price constant, and keep the date next to it.
- **Direct provider accounts.** You can skip the router and call a provider directly (the lab does this with Cerebras, with `CEREBRAS_API_KEY`). The same OpenAI client works with a different base URL.
- **BYOK (bring your own key).** As taught: OpenRouter routing with your own provider key is free up to a monthly allowance, then costs 5%. Check current terms `(verify)`.
- **New accounts have rate limits.** The notebooks mention 20 requests a minute on new accounts and suggest a short sleep after each call. A swarm needs retries and a concurrency cap (see [swarms and scale](swarms-and-scale.md)).
- **Model gateways.** Slides 29 to 32 of Week 3 list model gateways (OpenRouter, LiteLLM, AgentCore Gateway) as "one API in front of many models, with budgets and fallbacks". Ed's advice is to stay lightweight (a key check in the app, a model router) until the heavyweight gateways settle. See [security and guardrails](security-and-guardrails.md).

**Free models.** Use them for learning, prototypes and fictional data only.

- `openrouter/free` picks a different free model on almost every request, so results vary and a model can wander off. For comparisons use one named model whose id ends in `:free`.
- Limits as taught: 20 requests a minute; 50 requests a day on an account that has never bought credit, 1,000 a day after buying $10. A negative balance returns a 402, even on free models.
- Free endpoints may train on your prompts. Never send customer or confidential data. Replies can be long (1,000 to 3,000 tokens is typical), so cap tokens and retry.
- A free model with `MODEL_NAME` set replaces every model in the product, with no reasoning setting and a price of 0.

**Privacy facts to tell the customer** (Week 3 Day 1, slide 14): prompts and everything in the context go to the provider. Business APIs usually don't train on your data; consumer chat products may, so check the terms and settings (paying does not by itself stop a provider training on your data). Send only what the task needs and redact the rest. A SOC 2 certified LLM provider is comparable to any SOC 2 certified vendor you already trust with data. Covered fully in [fde lifecycle and governance](fde-lifecycle-and-governance.md).

## Cost engineering

1. **Define the unit of work** and the target cost per unit (per claim, per ticket). Compare it with what a human's time on that unit costs; this is the comparison a customer cares about.
2. **Record model cost per call, per item and per run.** Take tokens and cost from the response (`usage.cost` from OpenRouter; LangChain exposes it in `response_metadata["token_usage"]`). Store input tokens, output tokens, cost, model, reasoning level, provider and seconds against the item and the run, including failed attempts. UnderCover does this for every claim, and its Scoreboard shows cost per claim and time per claim.
3. **Estimate before you spend.** Before any evaluation has run, make a pre-eval estimate (general practice, not taught as such in the course): `tokens in and out per call x model calls per item x price per token`, then multiply for retries, screening calls and judge calls, and for the number of items. Replace it with the measured cost per item as soon as evals run. The course's runtime guard works from measurements: UnderCover's improver is refused an evaluation likely to cost more than what is left of the round's limit, where the estimate is the highest cost per claim seen on that model times the number of claims; for a model with no history it scales the current model's figure by the larger of the input and output price ratios.
4. **Set limits at three levels.**
   - In code: a spending limit per round or per job, and a cap on model calls per run (the improver is capped at 20 calls a round; the Copilot at 25 a turn).
   - On the provider key: a credit limit, for example $5, with an optional daily, weekly or monthly reset. It holds whatever the code does. `GET https://openrouter.ai/api/v1/key` shows the limit, the remaining credit and the day's usage.
   - On the cloud account: a budget with email alerts (UnderCover's AWS budget is $10 a month; AWS has no hard cap). See [production deployment on AWS](production-deployment-aws.md).
5. **Set timeouts and retries** on every model call (UnderCover: 120 seconds and 5 retries) so a stuck call does not burn time or money, and cap output tokens where a runaway reply is possible.
6. **Watch the multipliers.** A tool loop sends the whole prompt on every step (the lab's agent made three model calls per claim). A swarm multiplies concurrency, and retries must not repeat a paid side effect (see [swarms and scale](swarms-and-scale.md)). Judges and improvers add model calls of their own; count them in the budget.
7. **Compare cost with the cost of mistakes.** UnderCover prices its errors in business terms: $1,500 for a wrongful decline, the payout itself for a wrongful approval, $50 for each needless referral, and the gap for a wrong amount. At roughly a hundredth of a cent per item, API cost is tiny beside those, so a more capable or higher-reasoning model can pay for itself; at high volume or with large prompts the sums reverse. Run both calculations (see [evals and observability](evals-and-observability.md)):

```text
monthly model cost    = items per month x cost per item
monthly mistake cost  = items per month x sum(error rate x cost of that error)
choose the option with the lowest total that still clears the quality bar
```

8. **Make cost visible.** Show cost and time per run to the people who own the budget, and review them after each model or prompt change. In production, logs and spend are part of configuration (slide 74: CloudWatch for logs and `monitor.py` for AWS spend).

## Decisions to make with the developer

Ask these in order and write the answers into the architecture document and an ADR.

**1. Where does the model run?**

| Option | Choose when | Watch out for |
|---|---|---|
| Frontier or proprietary API (direct or through a router) | Quality matters most, data may go to a vetted provider, you want least operations work. | Data leaves your boundary; check training and retention terms; vendor lock-in; price changes. |
| Open-weight model hosted by a provider (router or direct, such as OpenRouter or Cerebras) | Lower price or higher speed than frontier is enough; you want to switch models easily. | The host still sees prompts; providers differ in precision and features; pin or exclude providers. |
| Open-weight model you host (own cloud account, rented GPU with vLLM, on-prem) | Contractual or regulatory need to keep data under your control; steady high volume. | Hardware, operations, scaling and idle cost; you own quality and uptime. |
| Local on a laptop or workstation (Ollama, LM Studio) | Prototyping, offline use, strictly private data, small tasks. | Small models struggle with long prompts and tools; memory limits; speed set by memory bandwidth; context window defaults. |
| Cloud-native model service (for example Bedrock) | The customer wants models inside their own cloud account. | Model lineup and prices differ from the lab's; the course keeps model calls on OpenRouter. |

Sensible default: a router in front of a small, inexpensive hosted model (such as Luna) for the build, with any private option decided in discovery and kept behind a base URL setting.

**2. One model for everything, or a different model per step?**

Default to one model for the whole pipeline and measure first. Split when a step has a different need, which is one of the five reasons to add an agent (see [agent architecture](agent-architecture.md)):

| Step | Typical fit |
|---|---|
| Classification or screening (high volume, fixed question) | A small, cheap, fast model or a specialised decision model. |
| Main reasoning and tool use | The cheapest model that clears the bar at the lowest reasoning level that works. |
| Improvement or planning, run rarely | A stronger model at medium or high reasoning. |
| Judging and grading | A model different from the one being judged, grounded in a reference answer. |
| Interactive chat | A model tuned for latency; keep reasoning low. |

**3. Which reasoning level and which override?** Start at `none` or `low`, make it a config field, and let evals decide. Provide an environment override for model choice so a student, a tester or a customer can swap models without a code change.

**4. What is the budget and who can change it?** Agree the cost-per-unit target, the per-job limit, the key credit limit and the account budget. Keep limits and the list of allowed models in business-owned data that agents cannot edit.

**5. What may be sent to which provider?** Classify data, decide what is redacted, and record the provider's training and retention position. Free endpoints are for fictional data only.

## Pitfalls and anti-patterns

- Choosing from a leaderboard, a vendor blog or one lucky run instead of an eval set repeated several times.
- Comparing a cheap model on a simple prompt with an expensive one on a different prompt. Keep everything but the model fixed.
- Hard-coding a model name, price or reasoning level in several places. Prices go stale; keep a dated price list in one config file.
- Ignoring reasoning tokens. They are billed as output, and some providers or free models run on far longer than the setting suggests (one free reply wrote 16,000 tokens). Cap tokens and monitor tokens per call.
- Sending a reasoning parameter a model does not support. Check allowed levels per model.
- Trusting `openrouter/free` for a comparison or a repeatable test; it changes model per request.
- Believing "open weights" means private or free. Private needs your hosting; free ignores hardware and time.
- Forgetting that a small local model's default context window may truncate the prompt without an error.
- Setting a budget only in code. Add the key limit and the account budget.
- Building an agent loop where one structured call would do; the lab's agent cost more and did no better.
- Shipping one provider's quirks as the model's quality (precision and feature differences between providers).
- Letting an optimiser agent choose a model without a list of allowed models, prices and a spending limit.
- Quoting model names or prices as current without checking the date.

## In UnderCover

- **Pilot and Week 1.** Day 2 pits GPT-6 Luna against Gemini 3.5 Flash Lite on the 25-claim queue (GPT-6 Sol and Jev appear as extras) and also runs a LangChain agent on Luna at `low`. Day 4 compares six open-weight models on OpenRouter (MiMo V2.6 Pro, GLM 5.3 Flash, Kimi K3, DeepSeek V4.1 Flash, Nemotron 3 Ultra, Mistral Medium 3.5), three local models on Ollama and an optional Qwen 3.8 27B on Cerebras, using 20 claims and a trimmed prompt.
- **Model in Ed's build by stage.** The pilot (Week 1 Day 3) runs Luna at `low`. DeepSeek V4.1 Flash at `low` takes over from Week 1 Day 5 through Week 2 Day 3, and Luna at `low` returns in Week 2 Day 4. From Week 2 Day 5, version 1 of the configuration is Luna at `none`, which a round can change. `MODEL_NAME` in `.env` overrides the model everywhere (for example `openrouter/free`).
- **Model per role (final build).**

| Role | Model |
|---|---|
| Claim agent | Version's model, Luna at `none` to start |
| Improver | `openai/gpt-6.1-sol` at `medium` by default |
| Judge | Jev (`typesafe/jev-1.13`) through OpenRouter's Decisions endpoint |
| Check for hidden instructions | Luna at `none`, named outside the versions |
| Copilot | Luna at `low` |

- **Cost tracking.** One factory (`agent/openrouter.py`) builds the chat model with a 120-second timeout and 5 retries. Each reply's tokens and cost come from OpenRouter's usage, are saved per model call against the claim and the run, and feed the Scoreboard. The allowed models and their prices are in `data/models.json`.
- **Limits.** Each improvement round has a spending limit ($0.50 to start) covering the improver, evaluations and the judge; the backend refuses an evaluation estimated to exceed what is left (`backend/spending.py`); the OpenRouter key carries a credit limit set in the Week 2 Day 5 lab; AWS has a monthly budget with alerts, and `uv run monitor.py` shows spend.
- **Free route.** `backend/free_models.py` is the one place that reads `MODEL_NAME`. With it set, that model replaces every model, at no reasoning setting and a price of 0.
- **Why Luna.** On this task it cleared the bar at a low cost, and the corrected Day 2 figures show its queue cost under Gemini's. The business cost of a mistake, not API cost, drives accuracy goals in the evaluation (see [evals and observability](evals-and-observability.md)).

## Related

- [Evals and observability](evals-and-observability.md): eval sets, noise, cost of mistakes, tracing cost.
- [Agent architecture](agent-architecture.md): single versus multiple agents and a different model per step.
- [Self-improvement](self-improvement.md): config versions, an improver that changes model and reasoning, spending limits.
- [Swarms and scale](swarms-and-scale.md): rate limits, concurrency, retries.
- [Security and guardrails](security-and-guardrails.md): model gateways, data leaving the boundary.
- [Production deployment on AWS](production-deployment-aws.md): budgets, spend monitoring, teardown.
- [FDE lifecycle and governance](fde-lifecycle-and-governance.md): privacy and vendor review.
- [UnderCover case study](undercover-case-study.md): how the model choices evolved.

## Sources

- `guides/for_agents/AGENT_GUIDE_WEEK1.md` (Days 2 and 4, including the corrections on Gemini and Jev costs, Bedrock and BYOK), `AGENT_GUIDE_WEEK2.md` (Days 1 and 5), `AGENT_GUIDE_WEEK3.md` (Day 1 privacy correction, Day 2 gateways), `AGENT_GUIDE_FREE.md`, `AGENT_COURSE_GUIDE.md` (model by stage).
- Notebooks `labs/week1day2.ipynb`, `labs/week1day4.ipynb`, `labs/week1day4cpu.ipynb` (reasoning levels, provider settings, Ollama, Cerebras pricing), `labs/week2day5.ipynb` (config versions, allowed models, credit limit on the key).
- Week 3 slides 14 (privacy), 19 (AWS and API costs), 29 to 32 (gateways), 74 (production configuration and cost). Week 1 and 2 slides are not in the repo; the six tricks, the Pareto front and METR are taken from the week guides.
- `origin/week3day5-end:docs/TECH_STACK.md`, `agent/openrouter.py`, `backend/spending.py`, `backend/free_models.py`, `data/models.json`, `data/improvement.json`, `docs/IMPROVE.md`.
