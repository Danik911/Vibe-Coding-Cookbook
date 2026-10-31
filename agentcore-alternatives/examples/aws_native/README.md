# Option B: the gateway on AWS, without AgentCore

The self-built gateway (`diy_gateway/`) deployed with generally available AWS services. Each AgentCore piece from the course has a replacement:

| AgentCore, as in `labs/week3day2_lab2.ipynb` and `labs/week3day3.ipynb` | Here |
|---|---|
| Gateway, inbound `AWS_IAM` | Lambda with a Function URL whose AuthType is `AWS_IAM`: AWS checks each SigV4 signature before the code runs, and the gateway reads the caller's role from the event |
| OpenAPI target with an API key credential provider | `openapi` target; the key comes from Secrets Manager (cached for 5 minutes) and is added as `X-API-Key` |
| MCP-server target, signed with the Gateway's role | `mcp` target with `sigv4` credentials (service `lambda`) |
| Policy engine, Cedar, `LOG_ONLY` then `ENFORCE` | Amazon Verified Permissions (Cedar, `STRICT` schema validation); the gateway does log-only itself |
| Policy decisions in CloudWatch | One JSON line per decision in the function's log group, in Embedded Metric Format: `AllowDecisions`/`DenyDecisions` by `Mode`, under `UnderCover/Gateway` |

```text
claim agent (role: AgentRoleName) --SigV4, service "lambda"--> Function URL (AWS_IAM)
                                                                   |
                                                    Lambda "<project>-gateway" (diy_gateway + Mangum)
                                                     |  verifiedpermissions:IsAuthorized (policy store)
                                                     |  secretsmanager:GetSecretValue (the app's key)
                     +-------------------------------+-------------------------------+
                     | X-API-Key                                                     | SigV4 with the gateway's role
                     v                                                               v
          the app (OpenAPI, /api/agent/openapi.json)                 the context layer (FastMCP, AWS_IAM URL)
```

## Files

| File | What it is |
|---|---|
| `gateway.aws.yaml` | The gateway's config on Lambda. `${NAME}` values come from the function's environment |
| `template.yaml` | AWS SAM: the function, its Function URL, role and log group, the policy store with its schema and four policies, and a permission for the agent's role. Passes `cfn-lint` |
| `package_lambda.py` | Builds `dist/gateway.zip` with Linux x86_64 wheels for Python 3.12 (about 40 MB zipped, 98 MB unzipped) |
| `cognito_m2m.py` | The alternative to IAM inbound: an agent's client-credentials token from Cognito |

## Before you deploy

Nothing in this folder has been deployed. Read the template first, and agree it with whoever owns the AWS account.

- **Budget first.** Set a budget with alerts that excludes credits, as in the course's Week 3 Day 1.
- **Permissions.** You need to create Lambda functions, IAM roles, log groups, a Verified Permissions policy store, CloudFormation stacks and SAM's S3 bucket. You don't need any `bedrock-agentcore:*` permission.
- **The app and the context layer** must already be deployed, with the context layer behind an `AWS_IAM` Function URL, as in `labs/week3day3.ipynb`. On the free route (Render), use `inbound.mode: tokens` and run the gateway as a web service: `uvicorn` on the app from `diy_gateway.app.build_http_app`.

## Deploy

The commands work in PowerShell and in a macOS terminal. They assume the AWS CLI, the SAM CLI and `uv`, all in us-east-1.

```bash
# 1. Store the app's agent key in Secrets Manager (prompted, never echoed or kept in shell history)
uv run python -c "import boto3, getpass; print(boto3.client('secretsmanager').create_secret(Name='undercover/app-key', SecretString=getpass.getpass('App key: '))['ARN'])"

# 2. Build the package
uv run examples/aws_native/package_lambda.py

# 3. Deploy, log-only first
sam deploy --guided --template-file examples/aws_native/template.yaml --stack-name undercover-gateway --capabilities CAPABILITY_IAM --tags project=undercover
```

`sam deploy --guided` asks for `AppUrl`, `ContextUrl`, `ContextFunctionName`, `AppKeySecretArn`, `AgentRoleName` and `PolicyMode` (start with `log_only`).

The agent's role also needs an identity policy that lets it call the gateway. New Function URLs need both actions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": "lambda:InvokeFunctionUrl",
     "Resource": "arn:aws:lambda:us-east-1:<account>:function:undercover-gateway",
     "Condition": {"StringEquals": {"lambda:FunctionUrlAuthType": "AWS_IAM"}}},
    {"Effect": "Allow", "Action": "lambda:InvokeFunction",
     "Resource": "arn:aws:lambda:us-east-1:<account>:function:undercover-gateway",
     "Condition": {"Bool": {"lambda:InvokedViaFunctionUrl": "true"}}},
    {"Effect": "Allow", "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
     "Resource": ["arn:aws:bedrock:*:<account>:inference-profile/*", "arn:aws:bedrock:*::foundation-model/*"]}
  ]
}
```

## Try it, then enforce

```bash
cd examples/agent
uv run agent_bedrock.py --gateway https://<url-id>.lambda-url.us-east-1.on.aws/mcp --iam-region us-east-1 --tools-only
```

In `log_only`, a $4,800 `pay_claim` reaches the app, which refuses it with its own limit, and the log shows `"decision": "DENY", "enforced": false`. Once the log shows only the refusals you expect, switch to enforce:

```bash
sam deploy --template-file examples/aws_native/template.yaml --stack-name undercover-gateway --capabilities CAPABILITY_IAM --parameter-overrides PolicyMode=enforce --no-confirm-changeset
```

## Cost (as checked on 31 Oct 2026; check again)

- **Lambda:** within the free allowance at course volumes, and nothing while idle.
- **Verified Permissions:** $5 per million `IsAuthorized` calls. For no per-call cost, set `engine: cedar` and package `policies/` (the zip already includes them).
- **Secrets Manager:** $0.40 per secret per month.
- **CloudWatch Logs:** kept for 7 days.
- **Models:** Bedrock calls are billed separately, and they dominate.

## Teardown

```bash
sam delete --stack-name undercover-gateway        # the function, URL, role, log group, policy store and policies
aws secretsmanager delete-secret --secret-id undercover/app-key --recovery-window-in-days 7
```

SAM's managed bucket stack (`aws-sam-cli-managed-default`) stays: delete it only when no other SAM stack needs it. Then check that nothing named `undercover` remains: in Resource Explorer, in the Lambda and Verified Permissions consoles, and in the budget.
