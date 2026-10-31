// The gateway's policy, in Cedar, evaluated on every tool call.
// It mirrors the AgentCore Policy from labs/week3day2_lab2.ipynb and labs/week3day3.ipynb:
// a permit for each target's tools and a forbid on payments over $1,000.
//
// - principal: Mcp::Agent::"<id>" (an agent's key), Mcp::User::"<sub>" (a JWT),
//   Mcp::IamEntity::"<arn>" (SigV4 on a Function URL)
// - action:    Mcp::Action::"<target>___<tool>", in the group Mcp::Action::"<target>"
// - resource:  Mcp::Gateway::"<resource_id>"
// - context:   { input: <the tool's arguments>, target: "<target>", tool: "<tool>" }
//
// Nothing is allowed unless a permit allows it, and a forbid always wins.
// A JSON number in the input is a Cedar decimal: compare with greaterThan, not >.

@id("claim-agent-app-tools")
permit (
  principal == Mcp::Agent::"claim-agent",
  action in Mcp::Action::"undercover-app",
  resource == Mcp::Gateway::"undercover-gateway"
);

// The context layer is read-only: every authenticated caller may read it,
// including the Copilot acting for a signed-in handler.
@id("context-layer-read")
permit (
  principal,
  action in Mcp::Action::"undercover-context",
  resource == Mcp::Gateway::"undercover-gateway"
);

@id("payment-limit")
forbid (
  principal,
  action == Mcp::Action::"undercover-app___pay_claim",
  resource
)
when { context.input has amount && context.input.amount.greaterThan(decimal("1000.0")) };

// Fail closed: a payment with no amount is refused here rather than left to the app.
// (A non-numeric amount makes the rule above error; the gateway denies on any error.)
@id("payment-needs-amount")
forbid (
  principal,
  action == Mcp::Action::"undercover-app___pay_claim",
  resource
)
unless { context.input has amount };
