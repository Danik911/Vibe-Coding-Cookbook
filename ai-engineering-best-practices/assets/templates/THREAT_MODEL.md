# Threat model: {{project_name}}

> Use when: before an agent gets real data, tools or a public address, and whenever it gains a tool, a data source or an identity. It lists what to protect, who might attack, and which layers stop each risk.
> Fill with the developer; don't invent facts — leave TODO where unknown.

> Guidance: Walk each agent through the lethal trifecta (Simon Willison): private data, untrusted content, external communication. An agent with all three can be steered into leaking data. Break at least one leg by design, then add layers, because no set of checks makes an agent bulletproof. Remove the `> Use when`, `> Fill` and `> Guidance` lines when done.

**Version:** {{version}} | **Owner:** {{security owner}} | **Reviewed:** {{date}} | Related: [ARCHITECTURE.md](ARCHITECTURE.md)

## 1. Assets

| Asset | Why it matters | Where it lives | Owner |
| --- | --- | --- | --- |
| {{money movement, records, personal data, keys, the agent's own rules}} | {{harm if lost, changed or leaked}} | {{system}} | {{owner}} |

## 2. Actors

| Actor | Trusted? | Can reach | Motive or failure |
| --- | --- | --- | --- |
| {{customer or outsider who writes text the agent reads}} | no | {{free-text fields, documents, email}} | {{inject instructions, fraud}} |
| {{user or operator}} | {{role-based}} | {{screens, API}} | {{mistake, misuse}} |
| {{the agent itself}} | no (can be steered or wrong) | {{tools it is given}} | {{error, injected goal}} |
| {{vendor or model provider}} | {{terms checked?}} | {{prompts and context sent}} | {{retention, training}} |

## 3. Lethal trifecta per agent

| Agent | Private data | Untrusted content | External communication | Leg broken, and how |
| --- | --- | --- | --- | --- |
| {{agent}} | yes/no: {{what}} | yes/no: {{what}} | yes/no: {{how it can send data out}} | {{removed a tool, a gateway rule, no outbound channel}} |

Example (UnderCover claim agent): private data yes (customer records); untrusted content yes (the customer's story); external communication no, since its only writes are a decision and a payment, both checked by the app.

## 4. Three kinds of risk

| Kind | Question | Controls here |
| --- | --- | --- |
| Runtime | What can the agent do where it runs? (permissions, sandbox, network, files) | {{IAM role with least privilege, read-only file system}} |
| APIs | What can it do through its tools? (scope, limits) | {{an API document with only the agent's operations; app-side limits}} |
| Prompt injection | Can text it reads change its goal? | {{see sections 5 and 8}} |

## 5. Guardrails: layers

> Guidance: Use independent layers so one failure is not fatal. Four kinds as taught: a model check, coded checks, flagging in the platform, and testing and audits.

| Layer | What it does | Fails open or closed? | Owner |
| --- | --- | --- | --- |
| Model check on input | a second, cheap model reads what customers wrote, with structured output (reason, then instructions_found); a hit is referred to a human and the main model never sees it | closed | {{team}} |
| Model or coded check on output | {{validator before anything goes out}} | {{closed}} | {{team}} |
| Gateway Policy | rules on every tool call, outside the agent's control | closed | {{security team}} |
| App-side limit | the app refuses the action itself, whatever the agent or Gateway does | closed | {{team}} |
| Flagging | users flag bad outputs; reviewed {{how often}} | n/a | {{team}} |
| Tests and audits | injection tests before release and continuously, via traces | n/a | {{team}} |

Keep the model check outside the agent's versioned configuration so the improver cannot weaken or disable it.

## 6. Policies

> Guidance: Write policies as Cedar rules at the AgentCore Gateway (as taught in the course, Oct 2026), first in log-only mode, then enforced. The security team owns them; the agent cannot change them. Keep the app's own limit as a second line.

| Rule in words | Tool and input | Mode | Owner |
| --- | --- | --- | --- |
| {{No payout over $X}} | `{{target}}___{{tool}}`, input `{{field}}` | log-only, then enforce | {{security team}} |

```cedar
forbid(
  principal is AgentCore::IamEntity,
  action == AgentCore::Action::"{{target}}___{{tool}}",
  resource == AgentCore::Gateway::"{{gateway_arn}}"
) when {
  context.input.{{field}}.greaterThan(decimal("{{limit}}"))
};
```

## 7. Identities and secrets

| Identity | Used by | Proves itself with | Can do | Cannot do |
| --- | --- | --- | --- | --- |
| Agent API key | the agent or the Gateway, to the app | header, compared in constant time | the agent's routes | stand in for a user |
| Runtime IAM role | the agent runtime | SigV4 | call the Gateway, use Memory | {{everything else}} |
| User's own sign-in | each person, and any assistant acting for them | their token | what that person may do | exceed their rights |

- Secrets live in {{AgentCore Identity or a vault}}, fetched at run time; none in code, logs, traces, frontend settings or saved state.
- Rotation: {{who, how often}}. Revocation: {{how, how fast}}.
- Public endpoints: {{list}}. A public address plus an API key protects the agent's routes but does not stop anyone calling the function; say what else limits it.
- Data boundary: {{one person's data only for that person's work}}; privacy with the model provider: {{training terms checked, minimized fields}}.

## 8. Prompt-injection tests

| # | Case | Expected | Result | Date |
| --- | --- | --- | --- | --- |
| 1 | hidden instruction in free text | flagged and referred | {{TODO}} | {{date}} |
| 2 | the same instruction reworded | flagged and referred | {{TODO}} | {{date}} |
| 3 | a smaller model on the same input | records which models fall for it | {{TODO}} | {{date}} |
| 4 | tool call over the limit | refused by the Gateway and the app | {{TODO}} | {{date}} |
| 5 | {{ordinary inputs, N of them}} | false-alarm rate {{target}} | {{TODO}} | {{date}} |

Example (UnderCover): one test claim hides an instruction to approve a $4,800 watch; the model check catches the original and the reworded version, and flags none of the 25 ordinary claims. A keyword list misses the reworded one.

> Guidance: Measure false alarms: a check that refers good inputs wastes people's time. Try to fool your own check, then improve it, and rerun after every change to the check or its model.

## 9. Residual risk

| Risk | Likelihood | Impact | Accepted by | Revisit |
| --- | --- | --- | --- | --- |
| {{risk left after the layers}} | {{L}} | {{I}} | {{name}} | {{date or trigger}} |

## 10. Sign-off

Security: {{name, date}} | Data and privacy: {{name, date}} | Sponsor: {{name, date}}
