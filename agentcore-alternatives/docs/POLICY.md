# Policy on every tool call, without AgentCore Policy

AgentCore Policy evaluates Cedar on every tool call that goes through the Gateway. This page shows how `diy_gateway` does the same, what can go wrong, and how the rule looks in other policy languages.

## The model

`diy_gateway` turns each tool call into one Cedar request, the same shape AgentCore uses, with a namespace of your choice (`Mcp` by default):

| Part | Value | AgentCore's equivalent |
|---|---|---|
| principal | `Mcp::Agent::"claim-agent"` (a key), `Mcp::User::"<sub>"` (a JWT), `Mcp::IamEntity::"arn:aws:iam::<acct>:role/<role>"` (SigV4) | `AgentCore::OAuthUser`, `AgentCore::IamEntity` |
| action | `Mcp::Action::"undercover-app___pay_claim"`, a member of the group `Mcp::Action::"undercover-app"` | `AgentCore::Action::"<target>___<tool>"` |
| resource | `Mcp::Gateway::"undercover-gateway"` | `AgentCore::Gateway::"<gateway ARN>"` |
| context | `{input: <the arguments>, target, tool}` | `context.input` |

As on AgentCore, **every JSON number in the input becomes a Cedar `decimal`**, so rules compare with `greaterThan(decimal("1000.0"))`, never `>`. Floats can't go to Cedar as they are: `cedarpy` returns `NoDecision` for a raw float. Cedar decimals have at most four decimal places, and `diy_gateway` refuses numbers outside Cedar's range.

The course's rules, in [`policies/gateway.cedar`](../policies/gateway.cedar):

```cedar
@id("claim-agent-app-tools")
permit (principal == Mcp::Agent::"claim-agent", action in Mcp::Action::"undercover-app",
        resource == Mcp::Gateway::"undercover-gateway");

@id("context-layer-read")
permit (principal, action in Mcp::Action::"undercover-context", resource == Mcp::Gateway::"undercover-gateway");

@id("payment-limit")
forbid (principal, action == Mcp::Action::"undercover-app___pay_claim", resource)
when { context.input has amount && context.input.amount.greaterThan(decimal("1000.0")) };

@id("payment-needs-amount")
forbid (principal, action == Mcp::Action::"undercover-app___pay_claim", resource)
unless { context.input has amount };
```

Nothing is allowed unless a `permit` allows it, and a `forbid` always wins. The `@id` names come back in the refusal (`refused by policy (payment-limit)`) and in the audit line.

## Fail closed

Cedar **ignores a policy whose evaluation errors**. So a `forbid` that errors, on a missing or non-numeric `amount` for example, doesn't block, and the call can be allowed with `diagnostics.errors` set. Rego and CEL `deny` rules behave the same way. `diy_gateway` closes this in three ways:

1. `deny_on_evaluation_errors: true` (the default) turns any allow that carries errors into a deny.
2. `payment-needs-amount` refuses a payment with no amount outright.
3. An optional **schema** ([`policies/gateway.schema.json`](../policies/gateway.schema.json)) declares each tool and its argument types. With `schema_file` set:
   - a call to a tool the schema doesn't declare is refused;
   - so is an unexpected argument, or an amount that isn't a number;
   - the policies are validated against it when the gateway starts.

   The schema doubles as a pin on the tools' definitions: regenerate it in CI from `tools/list` (for example with [cedar-for-agents](https://github.com/cedar-policy/cedar-for-agents)), and a changed tool fails the build.

A policy engine that can't answer (Verified Permissions unreachable, for example) also means deny, in every mode except `off`.

## Log-only, then enforce

| `policy.mode` | What happens |
|---|---|
| `off` | No decisions. Calls are still audited |
| `log_only` | Every call is decided and the decision is logged with `"enforced": false`, but nothing is refused. Run real traffic here first |
| `enforce` | A call the policy doesn't allow never reaches its target, and the caller gets `Tool Execution Denied` |

As in the course, try one call over the limit and one under it in each mode. In `log_only`, a $4,800 payment reaches the app, the app's own limit refuses it, and the audit shows `DENY`, `enforced: false`. In `enforce`, the gateway refuses it first. Neither Verified Permissions nor any open-source gateway found has a native log-only mode, so this lives in the gateway's middleware.

The refusal is a JSON-RPC error by default (`denial: protocol_error`), with `data: {"retryable": false, "policies": [...]}`, as AgentCore sends it. The MCP spec notes that protocol errors are less likely to be retried by a model than tool errors. The course's agent turns this error into "held for a handler's sign-off", and [`examples/agent/agent_bedrock.py`](../examples/agent/agent_bedrock.py) shows the same with a LangChain tool interceptor. `denial: tool_error` sends it as an `isError` result instead.

## Hiding tools a caller may never use

With `hide_unpermitted_tools: true` and `enforce`, `tools/list` leaves out the tools a caller could never call, so the Copilot's handler sees only the context layer. This uses **Cedar's partial evaluation** with the input unknown: a tool is hidden only when no input could be allowed. `pay_claim` stays listed for the claim agent even though some amounts are refused. Listing never decides a call: each call is still evaluated in full. Verified Permissions has no partial evaluation, so with that engine every tool is listed.

## cedarpy or Amazon Verified Permissions

| | `engine: cedar` (`cedarpy` in process) | `engine: verified_permissions` (AVP) |
|---|---|---|
| Latency | Microseconds: about 27 µs per evaluation measured with a pre-parsed policy set | A network round trip; AWS publishes no p50/p99 |
| Cost | None | $5 per million `IsAuthorized` calls; default quota of 200 RPS per policy store |
| Where the rules live | `policies/*.cedar` in git, reviewed in pull requests | An AWS policy store, with STRICT schema validation, the console, CloudFormation and IAM on who may change it |
| Maturity | `cedarpy` is community-maintained (k9securityio), tracking Cedar 4.12 | AWS-managed |
| Partial evaluation (hiding tools) | Yes (experimental upstream) | No |

**Both together** is a common pattern. Keep the policy store in AVP for review and audit, load its policies into `cedarpy` on a timer (`ListPolicies`/`GetPolicy`), and evaluate in process. AWS's [cedar-local-agent](https://github.com/cedar-policy/cedar-local-agent) does this in Rust. `diy_gateway` sends the same Cedar JSON to both engines, so moving between them is a config change.

## The same rule in other languages

You'll need these if you pick a gateway without Cedar. All were checked against each product's docs, and the Rego was run with OPA 1.22.0.

**CEL, agentgateway (`mcpGuardrails`, which can read arguments; `mcpAuthorization` can't):**

```yaml
- kind: expression
  condition: >-
    mcp.tool.target == "undercover-app" && mcp.params.name == "pay_claim" &&
    (!has(mcp.params.arguments.amount) || double(mcp.params.arguments.amount) > 1000.0)
  reject: "Tool Execution Denied: payments over $1,000 need a handler's sign-off"
```

**CEL, Agent Router (was Envoy AI Gateway):**

```yaml
- action: Deny
  target: { tools: [ { backend: undercover-app, tool: pay_claim } ] }
  cel: 'double(request.mcp.params.arguments.amount) > 1000.0'
```

An error in Agent Router's `cel` counts as no match, so this deny fails open. Prefer `require` rules where the product has them.

**Rego (OPA):**

```rego
package mcp.authz
import rego.v1
default allow := false
allow if count(deny) == 0
deny contains "payment-limit" if {
    input.tool == "pay_claim"
    numeric_amount
    input.arguments.amount > 1000
}
deny contains "payment-needs-amount" if {   # without this, a missing amount is allowed
    input.tool == "pay_claim"
    not numeric_amount
}
numeric_amount if is_number(input.arguments.amount)
```

**Cerbos:**

```yaml
- actions: ["pay_claim"]
  effect: EFFECT_DENY
  roles: ["agent"]
  condition:
    match:
      expr: request.resource.attr.arguments.amount > 1000
```

**ToolHive (Cedar, arguments as `arg_*`):**

```cedar
forbid(principal, action == Action::"call_tool", resource == Tool::"pay_claim") when { resource.arg_amount > 1000 };
```

## Keep the limit in the app too

A constant in a policy is a second copy of a business limit. UnderCover keeps the approval limit as a setting in the app, and the app refuses any payment over it whatever the gateway decides. The gateway's rule is the second layer, and a handler's sign-off is the third. When the setting changes, change the policy too. A test that reads both is a cheap way to catch drift.
