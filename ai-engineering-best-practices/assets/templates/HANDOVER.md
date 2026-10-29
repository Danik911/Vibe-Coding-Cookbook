# Handover: {{project_name}}

> Use when: the build is ready to hand to the client's team, so that they can run, measure, change and, if needed, retire it without the FDE. Write it before the final sign-off and walk through it with the service owner.
> Fill with the developer; don't invent facts — leave TODO where unknown.

> Guidance: Handover has three parts (ownership and escalation, knowledge transfer, ongoing measurement) and adoption has four (training and support, sponsors and top-down change, demonstrating output accuracy, transparency on usage). A human stays accountable; the model is a tool, not the owner. Test the runbooks by having the client's team follow them. Product names and commands below are AWS AgentCore defaults as taught in the course (Oct 2026); re-check them. Remove the `> Use when`, `> Fill` and `> Guidance` lines when done.

**Release:** {{version}} | **Date:** {{date}} | **Service owner:** {{name}} | **Release approved by:** {{sponsor, date}}

## 1. What runs where

| Piece | Where | Account / region | Deployed from | Owner |
| --- | --- | --- | --- | --- |
| {{App API and UI}} | {{Lambda, Function URL}} | {{account, region}} | {{repo, command}} | {{team}} |
| {{Agent}} | {{AgentCore Runtime}} | {{...}} | {{...}} | {{team}} |
| {{Context layer}} | {{Lambda behind the Gateway}} | {{...}} | {{...}} | {{data governance}} |
| {{Gateway, Policy, Identity, Memory}} | {{AgentCore}} | {{...}} | {{...}} | {{security team}} |
| {{Database}} | {{provider}} | {{...}} | {{...}} | {{team}} |

Architecture and decisions: [ARCHITECTURE.md](ARCHITECTURE.md), ADRs in `{{path}}`.

## 2. Ownership and escalation

| Role | Name | Responsible for |
| --- | --- | --- |
| Accountable owner | {{name}} | outcomes and quality of decisions |
| Service owner | {{name}} | uptime, releases, incidents |
| Data owners | {{names}} | context files: source, owner, review date |
| Security | {{name}} | policies, keys, access reviews |
| Approvers (human in the loop) | {{roles}} | sign-offs and send-backs; backup when absent: {{who}} |

Escalation path: {{first line, second line, vendor support}}; severity levels and response times: {{table or link}}.

## 3. Runbooks

> Guidance: Each runbook has the exact commands, the expected output and who may run it.

| Runbook | When | Steps | Verify |
| --- | --- | --- | --- |
| Deploy | a new release | {{commands: build packages, `agentcore deploy`, update app, set env}} | {{health check, tiny eval set}} |
| Roll back | a bad release or a bad agent version | {{switch the agent's configuration to the previous version; redeploy the previous commit}} | {{health check, tiny eval set}} |
| Work stopped | a run or session died | {{how it is noticed, how the next start carries on from checkpoints}} | {{item states are correct; no side effect repeated}} |
| Rotate a key | schedule or incident | {{update the vault entry, redeploy dependants}} | {{calls succeed, old key refused}} |
| Teardown | retire or end of engagement | {{remove the runtimes, Gateway and Policy, credential providers, Memories, the Lambda functions and bootstrap resources; deactivate keys}} | {{list resources by name; search the account's region; check cost after a day or two, since budget figures lag}} |

## 4. Monitoring and cost

- Logs: {{CloudWatch groups}}; traces: {{tool, project}}; spend records per unit of work: {{where to read}}
- Alerts: {{what fires, to whom}}; budget: {{amount per month}}, alerts at {{thresholds}}; spend caps on provider keys: {{amounts}}
- Cost per unit of work: expected {{$}}, alarm above {{$}}. Known fixed costs: {{e.g. bootstrap resources, memory}}
- Usage report for sponsors: {{what is shared, how often, who sees it}}

## 5. Access and keys

| Credential | Where it lives | Who may read or rotate | Rotation |
| --- | --- | --- | --- |
| {{model provider key}} | {{vault}} | {{role}} | {{interval}} |
| {{agent API key}} | {{vault and Gateway credential provider}} | {{role}} | {{interval}} |
| {{database URL}} | {{vault}} | {{role}} | {{interval}} |

Who may invoke the agent: {{roles}}. Who may sign off: {{roles and limit}}. Access review: {{when}}.

## 6. Evals to re-run

| Eval | Set | When | Pass bar | Owner |
| --- | --- | --- | --- | --- |
| {{smoke}} | tiny | after every deploy | {{bar}} | {{owner}} |
| {{full}} | held-out | monthly, and after any model change | objectives in [EVAL_PLAN.md](EVAL_PLAN.md) | {{owner}} |
| {{security}} | injection set | after any change to checks | {{false alarms under X}} | {{owner}} |

Last results: {{date, scores, cost}}. Success criteria status: {{met / not met, per criterion}}.

## 7. Known limits

- {{Rate limits, concurrency caps, timeouts, session limits.}}
- {{What the agent cannot do, and what it refers to a human.}}
- {{Items deferred ("not for now") and open risks from [THREAT_MODEL.md](THREAT_MODEL.md).}}

## 8. Adoption and training

| Audience | Training | Support | Owner |
| --- | --- | --- | --- |
| {{users}} | {{session, guide, walkthrough of a real case}} | {{channel, hours}} | {{name}} |
| {{approvers}} | {{how to review, send back with a note}} | {{channel}} | {{name}} |

- Show accuracy: {{demo on real cases, eval results shared}}. Sponsor message: {{what leaders say and do}}. Feedback loop: {{how users flag bad outputs and who reads them}}.

## 9. Support contacts

| Need | Contact | Hours |
| --- | --- | --- |
| {{incident, change request, vendor}} | {{name, channel}} | {{hours}} |

## 10. Handover sign-off

Walkthrough held on {{date}} with {{attendees}}. Service owner accepts: {{name, date}}. Open items: {{list with owners and dates}}.
