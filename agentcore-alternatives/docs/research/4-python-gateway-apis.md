> Research report by a sub-agent (Claude Sonnet 5.5) on 31 October 2026, kept as written. It cites its sources; anything marked UNVERIFIED wasn't confirmed. The code and docs in this folder supersede it where they differ.

# Research report: current Python APIs for a DIY MCP gateway (31 Oct 2026)

I verified almost everything below by installing the packages on Windows 11 with Python 3.12.10 and running them. Where I only read docs, I say so. Anything unverified is marked **UNVERIFIED**.

## 0. Critical findings

1. **The stack moved a major version.** Latest FastMCP is **4.1.4**, which sits on **MCP Python SDK v2** (`mcp` 2.3.0) and **httpx2**, not httpx.
2. **FastMCP 4 and `langchain-mcp-adapters` cannot share an environment.**
   - `langchain-mcp-adapters` 0.3.2 requires `mcp<2.0.0`. FastMCP 4.1.4 requires `mcp>=2.3.0,<3` (`fastmcp-slim` metadata on PyPI).
   - The README at https://github.com/langchain-ai/langchain-mcp-adapters says "This repository is no longer actively maintained". MCP support moved to `langchain.mcp` (`langchain[mcp]>=1.4.0`, which depends on `fastmcp>=4.0.11,<5`).
   - `agentcore-alternatives/uv.lock` pins `langchain-mcp-adapters 0.3.1` and `mcp 2.3.0` together. I verified that this combination fails on import: `ImportError: cannot import name 'RequestContext' from 'mcp.shared.context'`. Version 0.3.1 has no `mcp` cap. The cap was added in 0.3.2 (commit `d4a1caa9`, 2026-08-06).
   - Fix: use `langchain[mcp]` with FastMCP 4 (verified, section 3). Or stay on FastMCP 3.4.11 with `langchain-mcp-adapters` 0.3.2. In that case you need separate environments for the gateway and the agent unless both are on `mcp<2`.
3. **FastMCP's proxy forwards the caller's `Authorization` header upstream by default** (verified on 4.1.4). Set `forward_incoming_headers=False` on `ProxyClient` (4.x only). On 3.4.11 you cannot disable it (see 1.4).
4. **Cedar fails open in two ways, and floats break the request.**
   - An evaluation error inside a `forbid` returns `Allow` with `diagnostics.errors` populated.
   - A float, `None`, or an int above i64 in the context returns `NoDecision` rather than raising.

## 1. FastMCP

**Versions** (https://pypi.org/pypi/fastmcp/json)

| Line | Latest | Date |
|---|---|---|
| 4.x | **4.1.4** (4.2.0a1 is a pre-release, 2026-10-27) | 2026-10-26 |
| 4.0.0 | | 2026-08-31 |
| 3.x | 3.4.11 (still patched) | 2026-10-20 |
| 3.0.0 | | 2026-02-18 |
| 2.x | 2.14.7, last | 2026-04-13 |

`fastmcp` is a thin wrapper over `fastmcp-slim[client,server]`.

**Breaking changes**
- **2.x → 3.0** (https://gofastmcp.com/getting-started/upgrading/from-fastmcp-2.md):
  - `FastMCP()` no longer accepts `host`, `port`, `stateless_http`, `json_response`. Pass them to `run()` or `http_app()`.
  - `mount(prefix=)` became `mount(namespace=)`.
  - `FastMCP.as_proxy(url)` became `fastmcp.server.create_proxy`.
  - `FastMCPOpenAPI` became `OpenAPIProvider` (`fastmcp.server.providers.openapi`).
  - `fastmcp.server.proxy` became `fastmcp.server.providers.proxy`.
  - `get_tools()` became `list_tools()` and returns a list.
  - The OpenAPI `timeout` kwarg is removed. Set the timeout on the client.
- **3.x → 4.0** (https://gofastmcp.com/getting-started/upgrading/from-fastmcp-3.md):
  - Built on `mcp` v2 and `mcp-types`. Model fields are snake_case (camelCase reads still work with a warning).
  - **httpx → httpx2** everywhere. Custom `httpx.Auth`, client factories and `from_openapi(client=)` should be httpx2 objects. The doc says old `httpx.AsyncClient` is "temporarily accepted via duck typing" for `from_openapi`, with a deprecation warning.
  - `FastMCP.as_proxy`, `mount(prefix=/as_proxy=)`, `import_server`, `add_tool_transformation` and `StreamableHttpTransport(sse_read_timeout=)` are removed.
  - `McpError(ErrorData(...))` is replaced by `McpError(code=, message=)`.
  - Floors: pydantic>=2.12, starlette>=1.0.1, FastAPI>=0.133.

### 1.1 `from_openapi`

Signature on 4.1.4 (verified):
```python
FastMCP.from_openapi(openapi_spec: dict, client: httpx2.AsyncClient | None = None, name: str = 'OpenAPI Server',
    route_maps: list[RouteMap] | None = None, route_map_fn=None, mcp_component_fn=None,
    mcp_names: dict[str, str] | None = None, tags: set[str] | None = None, validate_output: bool = True, **settings) -> Self
```
On 3.4.11 the signature is identical except `client: httpx.AsyncClient`.

- The provider form is `from fastmcp.server.providers.openapi import OpenAPIProvider, RouteMap, MCPType`. `OpenAPIProvider(openapi_spec, client=None, *, route_maps, route_map_fn, mcp_component_fn, mcp_names, tags, validate_output)` exists on both lines.
- **Base URL and headers.** A spec with no `servers` needs a client with a base URL, because the omitted-client default uses the first spec server. Verified:
  ```python
  api = httpx2.AsyncClient(base_url=base, headers={"X-API-Key": key}, timeout=30)
  ```
  A custom `auth=` on the client is also an option. `X-API-Key` is not exposed as a tool input: the `pay_claim` input schema contained only `claim_id` and `amount`, even with a FastAPI `APIKeyHeader` security scheme in the spec. Docs: https://gofastmcp.com/integrations/openapi.md
- **Tool names.** The default is the `operationId` up to the first `__`, slugified and capped at 56 characters. `mcp_names={"get_claim": "undercover-app___get_claim"}` produced `undercover_app_get_claim` (verified), so `mcp_names` cannot create the triple underscore.
- The default route map makes every route a tool. Use `RouteMap(mcp_type=MCPType.EXCLUDE)` to allow-list.

### 1.2 Proxying a remote streamable-HTTP server

```python
from fastmcp.server import create_proxy                      # (target, *, mode=None, **settings) -> FastMCPProxy   [4.1.4]
from fastmcp.server.providers.proxy import ProxyClient, ProxyProvider, FastMCPProxy
from fastmcp.client.transports import StreamableHttpTransport
```

| Item | 4.1.4 | 3.4.11 |
|---|---|---|
| `StreamableHttpTransport` | `(url, headers=None, auth: httpx2.Auth \| 'oauth' \| str \| None = None, httpx_client_factory=None, verify=None, *, max_sse_event_size=1048576)` | same plus `sse_read_timeout`, `auth: httpx.Auth` |
| `ProxyClient` | `(transport, *, forward_incoming_headers: bool = True, **kwargs)`, defaults to `mode="legacy"` when built directly | `(transport, **kwargs)` |
| `ProxyProvider` | `(client_factory, cache_ttl=None)` | same |
| `create_proxy` | `(target, *, mode=None, **settings)` | `(target, **settings)` |

- **4.1.4:** `create_proxy(url)` with no `mode` mirrors the caller's protocol era. A directly built `ProxyClient` is pinned to the handshake era. That is what you want for an upstream built on `mcp.server.fastmcp` v1.
- **3.4.11:** the opt-out kwarg does not exist (`TypeError`). `create_proxy()` also force-sets `transport.forward_incoming_headers = True` (source of `_create_client_factory`), so setting the attribute does not help.
- **Portable fix (verified on 3.4.11):** pass an `httpx.Auth` that pops `authorization`, or the SigV4 auth, which overwrites it.
- Per-call sessions are the default. A shared-session `FastMCPProxy(client_factory=lambda: shared)` is an option for stateless backends (docs). Docs: https://gofastmcp.com/servers/providers/proxy.md

### 1.3 `mount` and the `___` separator

```python
FastMCP.mount(self, server, namespace: str | None = None, tool_names: dict[str, str] | None = None) -> None   # 4.1.4
# 3.4.11 additionally has as_proxy= and the deprecated prefix=
FastMCP.add_provider(self, provider, *, namespace: str = "") -> None
```

- The `Namespace` transform hardcodes `f"{prefix}_"`. Source: `fastmcp.server.transforms.Namespace`, with `self._name_prefix = f"{prefix}_"`.
- **Public-API trick (verified):** `gw.mount(srv, namespace="undercover-app__")` gives `undercover-app___get_claim`. The middleware on the parent sees the prefixed name.
- **Subclass alternative (verified, private attribute):**
  ```python
  class TripleNS(Namespace):
      def __init__(self, p):
          super().__init__(p)
          self._name_prefix = f"{p}___"
  gw.add_provider(FastMCPProvider(proxy).wrap_transform(TripleNS("undercover-context")))
  ```
- **Fully public alternative:** write a `Transform` with `list_tools` and `get_tool`, as `agentcore-alternatives/diy_gateway/targets.py:TargetPrefix` does. All of its imports resolve on 4.1.4: `fastmcp.tools.base.Tool`, `fastmcp.utilities.versions.VersionSpec`, `fastmcp.server.transforms.GetToolNext`, `Transform`.
- `mount(tool_names={...})` renames individual tools, and renames apply before the namespace.
- Namespaces also rewrite resource URIs. That is irrelevant for tool-only use.

### 1.4 Middleware

```python
from fastmcp.server.middleware import Middleware, MiddlewareContext, CallNext
class M(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):   # context.message.name, .arguments (dict | None)
```

Verified:
- Reading `context.message.name` and `context.message.arguments` works.
- `raise ToolError("Tool Execution Denied: …")` (from `fastmcp.exceptions`) reaches the client as a normal result with `is_error=True` and that text. Under langchain this becomes `ToolMessage(status="error")`, so the agent can self-correct.
- `raise McpError(code=-32003, message="Tool Execution Denied: …")` reaches the client as a JSON-RPC error, raised as `mcp.shared.exceptions.MCPError`. On 4.x the constructor is `McpError(code, message, data=None)`. On 3.x it is `McpError(error: ErrorData)`.
- Middleware docs: parent middleware runs for all mounted servers. Do not return error values; raise (https://gofastmcp.com/servers/middleware.md).

### 1.5 Access token and auth providers

```python
from fastmcp.server.dependencies import get_access_token        # () -> AccessToken | None
from fastmcp.server.auth import AccessToken, MultiAuth, TokenVerifier
from fastmcp.server.auth.providers.jwt import JWTVerifier, StaticTokenVerifier, RSAKeyPair
```

- `get_access_token()` works inside `on_call_tool` (verified).
- **`AccessToken` fields:**
  - 4.1.4: `token, client_id, scopes, expires_at, resource, subject, claims, original_client_id`.
  - 3.4.11: no `original_client_id`, and `JWTVerifier` does not populate `subject`.
  - Portable: use `tok.claims["sub"]`.
- `get_http_headers()` excludes `authorization` by default (https://gofastmcp.com/servers/dependency-injection.md).
- **`JWTVerifier`** (identical on 3.4.11 and 4.1.4):
  ```python
  JWTVerifier(*, public_key=None, jwks_uri=None, issuer: str|list[str]|None=None, audience: str|list[str]|None=None,
              algorithm=None, required_scopes=None, base_url=None, ssrf_safe=False, http_client=None, jwks_refresh_interval=30.0)
  ```
  The client id is taken from `client_id`, then `azp`, then `sub`.
- **Cognito (verified with a local JWKS):** the JWKS URI is `https://cognito-idp.<region>.amazonaws.com/<poolId>/.well-known/jwks.json`. Issuer is the same URL without `/.well-known/jwks.json`. Access tokens carry `client_id` and `cognito:groups` but no `aud`, so omit `audience` (https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-verifying-a-jwt.html). ID tokens carry `aud`. A wrong issuer returns `None`.
- `fastmcp.server.auth.providers.aws.AWSCognitoProvider` exists, but it is an OAuth proxy (needs `user_pool_id`, `client_id`, `client_secret`, `base_url`, `aws_region` defaulting to `eu-central-1`). It is not a plain JWT verifier. A `SupabaseProvider` also exists (`project_url`, `base_url`, `algorithm='ES256'`).
- **`MultiAuth`** (since 3.1.0): 4.1.4 takes `verifiers: Mapping[str, TokenVerifier] | Sequence | TokenVerifier`. 3.4.11 takes a list or a single verifier. A bad token returns 401.
- **`StaticTokenVerifier(tokens: dict[str, dict], required_scopes=None)`:** the FastMCP docs say it is dev-only (plain-text tokens). For production, subclass `TokenVerifier` with `async verify_token(token) -> AccessToken | None` and use `hmac.compare_digest` (**UNVERIFIED**, a simple pattern). The HTTP deployment doc imports `StaticTokenVerifier` from `fastmcp.server.auth`, but it is not in that module's `dir()` on 4.1.4. Use the `providers.jwt` path.

### 1.6 HTTP app, uvicorn and Mangum

```python
FastMCP.http_app(path=None, middleware=None, json_response=None, stateless_http=None, transport='http', event_store=None,
    retry_interval=None, host_origin_protection=None, allowed_hosts=None, allowed_origins=None, session_idle_timeout=None) -> StarletteWithLifespan
app = gw.http_app(path="/mcp", stateless_http=True, json_response=True)     # uvicorn gateway:app
```

- On 3.4.11 the signature is the same without `session_idle_timeout`. The environment variable `FASTMCP_STATELESS_HTTP` also works.
- If you mount the app inside Starlette or FastAPI, you must pass `lifespan=mcp_app.lifespan`.
- `custom_route`s are not auth-protected. Host/Origin protection is off by default (https://gofastmcp.com/deployment/http.md).
- **Mangum 0.22.0 (verified on 4.1.4):**
  - `Mangum(app, lifespan="auto")` handled 4 consecutive invocations of the full gateway, with auth, middleware, both targets and a module-level `httpx2.AsyncClient`. A bad token returned 401.
  - `lifespan="off"` returns 500 ("Task group is not initialized").
  - `diy_gateway/lambda_handler.py` rebuilds the gateway per request because "the session manager can only start once". That limit applies to the mcp v1 `StreamableHTTPSessionManager`. I did not see it with FastMCP 4.1.4.
  - Not tested: real Lambda freeze/thaw, concurrency, and multi-invocation on 3.4.11. Re-test in your harness.

## 2. MCP Python SDK

| | `mcp` 1.30.0 (2026-09-07, last 1.x) | `mcp` **2.3.0** (2026-10-02, latest; 2.0.0 was 2026-07-28) |
|---|---|---|
| Error class | `from mcp.shared.exceptions import McpError`, `McpError(error: ErrorData)` | `McpError` **removed**. `from mcp.shared.exceptions import MCPError`, `MCPError(code, message, data=None)` |
| Streamable HTTP client | `from mcp.client.streamable_http import streamablehttp_client` `(url, headers=None, timeout=30, sse_read_timeout=300, terminate_on_close=True, httpx_client_factory=..., auth: httpx.Auth \| None=None)`. The newer `streamable_http_client(url, *, http_client: httpx.AsyncClient \| None, terminate_on_close)` also exists | `streamablehttp_client` **removed**. `streamable_http_client(url, *, http_client: httpx2.AsyncClient \| None=None, terminate_on_close=True, max_sse_event_size=...)` |
| High-level server | `mcp.server.fastmcp.FastMCP` (FastMCP 1.0) with `streamable_http_app()`, `stateless_http`, `json_response` kwargs | `mcp.server.MCPServer`; new `mcp.client.Client` |
| Low-level | `mcp.server.lowlevel.Server(name, version, instructions, website_url, icons, lifespan)` with decorators | `Server(name, *, ..., on_call_tool=..., on_list_tools=..., ...)` handler kwargs |

- A proxy on the low-level `Server` is possible (forward `on_list_tools` and `on_call_tool` to a client session). I did not build one: **UNVERIFIED**. The FastMCP proxy is the proven path.
- Dependencies: v1 needs `httpx`. v2 needs `httpx2>=2.10`, `mcp-types==2.3.0`, `pywin32` on Windows.
- httpx2 latest is 2.16.0 (2026-10-21, https://github.com/pydantic/httpx2). It is a drop-in fork with the same `Auth` API.

## 3. Agent client

### `langchain-mcp-adapters` 0.3.2 (2026-08-06, unmaintained, `mcp<2`)

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
MultiServerMCPClient(connections=None, *, callbacks=None, tool_interceptors=None, tool_name_prefix=False, handle_tool_errors=True)
```

- Methods: `get_tools`, `get_prompt`, `get_resources`, `get_server_info`, `session`.
- `StreamableHttpConnection` keys: `transport` (`"streamable_http"`), `url`, `headers`, `timeout`, `sse_read_timeout`, `terminate_on_close`, `session_kwargs`, `httpx_client_factory`, `auth` (an `httpx.Auth`).
- **Verified against the FastMCP 4.1.4 gateway** (an mcp 1.30 client talking to an mcp 2.3 server worked): `headers={"Authorization": "Bearer …"}` and `auth=<httpx.Auth>` both work. `tool.ainvoke({...})` returns a list of text blocks.
- Errors: a denial (`isError=True`) becomes a `ToolMessage` with `status="error"` by default. With `handle_tool_errors=False` it raises `langchain_mcp_adapters.tools._MCPToolExecutionError`. JSON-RPC errors and transport failures always raise (per the source docstring). A missing token raises an `ExceptionGroup` wrapping `HTTPStatusError`.
- Interceptors: `ToolCallInterceptor`, `MCPToolCallRequest(name, args, server_name, headers, runtime)` with `.override()`.

### The supported replacement: `langchain[mcp]` 1.4.7 (2026-10-21; beta, emits `LangChainBetaWarning`)

```python
from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport
from langchain.mcp import MCPAdapter          # also as_langchain_tool, MCPToolArtifact
async with MCPAdapter(Client(StreamableHttpTransport(url, headers={...}, auth=<httpx2.Auth>))) as ad:
    tools = await ad.list_tools()             # list_tools(*, cache_mode="use")
```

- The target can be a URL, a `fastmcp.Client`, an `MCPConfig` dict or a `ClientGroup`. A bearer string works as `Client(url, auth=token)`.
- Verified in one environment (`langchain[mcp]==1.4.7` + `langchain-aws==1.9.1`, fastmcp 4.1.4, mcp 2.3.0, langchain-core 1.7.3, langgraph 1.2.19):
  - Three auth variants (bearer string, transport headers, custom `httpx2.Auth`) each listed 7 tools.
  - A denial arrived as `ToolMessage(status="error")` with the message text.
  - `ChatBedrockConverse.bind_tools(tools)` worked.
- `tool_interceptors` and `handle_tool_errors` are gone. Use LangChain's `@wrap_tool_call` middleware. Tool names are unprefixed for a single-client target. A multi-server config uses `{server}_{tool}`.
- Docs: https://docs.langchain.com/oss/python/migrate/langchain-mcp-adapters, `/langchain/mcp/auth.md`, `/langchain/mcp/connections.md`.

## 4. langchain-aws and Bedrock

`langchain-aws` **1.9.1** (2026-10-26). `from langchain_aws import ChatBedrockConverse` (verified; also exports `ChatAnthropicBedrock`, `ChatBedrock`).

- `ChatBedrockConverse(model=..., region_name=..., temperature=..., max_tokens=...)`. `model` is the alias of the field `model_id`, and both spellings work.
- Other fields: `provider`, `credentials_profile_name`, `aws_access_key_id`, `bedrock_api_key`, `endpoint_url` (alias `base_url`), `guardrail_config`, `additional_model_request_fields`, `service_tier`, `performance_config`, `reasoning_effort`, `max_retries`.
- `bind_tools(tools, *, tool_choice=None, strict=None, **kwargs)` returns a runnable.
- **Windows gotcha:** my machine's AWS config uses a login-credential profile. Creating the model failed with `pip install "botocore[crt]"` required. Install `botocore[crt]` or use env creds.
- **Model IDs** (from the AWS model cards, https://docs.aws.amazon.com/bedrock/latest/userguide/model-cards.html):

| Model | Inference-profile id | Notes |
|---|---|---|
| Claude Sonnet 5.5 (launched 2026-09-28) | `us.anthropic.claude-sonnet-5-5` or `global.anthropic.claude-sonnet-5-5` | Client-side tool calling on `bedrock-runtime`, **`tool_choice` auto/none only** |
| Claude Haiku 5.5 | `us.anthropic.claude-haiku-5-5` | Tool-calling support **UNVERIFIED** (card not parsed) |
| Claude Haiku 4.5 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Tool calling supported; EOL "no sooner than 2026-10-16" |
| Claude Sonnet 4.5 | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | Tool-calling support **UNVERIFIED** (card not parsed) |
| Nova 2 Lite | `us.amazon.nova-2-lite-v1:0` | Tool calling supported; EOL no sooner than 2026-12-02 |
| Nova Pro | `us.amazon.nova-pro-v1:0` | The card's feature table does not list tool calling: **UNVERIFIED** |

I made no live Bedrock calls (no credentials).

## 5. cedarpy

**4.12.2** (2026-10-14, https://pypi.org/project/cedarpy/). Wheels exist for **win_amd64** on cp310–cp314 and manylinux_2_17 x86_64 and aarch64 (Lambda-ready). I did not see a Windows ARM wheel. Repo: https://github.com/k9securityio/cedar-py

```python
from cedarpy import is_authorized, Decision, PolicySet, Entities
is_authorized(request: dict, policies: str | PolicySet, entities: str | list[dict] | Entities,
              schema: str | dict | Schema | None = None, verbose: bool = False) -> AuthzResult
```

- The request is `{"principal": 'User::"alice"', "action": 'Action::"tool"', "resource": 'Gateway::"g"', "context": {...}}`. Each entity reference can also be `{"type": ..., "id": ...}`. Entities are `[{"uid": {"type","id"}, "attrs": {}, "parents": [{"type","id"}]}]`.
- Result: `.decision` (`Decision.Allow | Deny | NoDecision`), `.allowed` (bool), `.diagnostics.reasons` (policy ids), `.diagnostics.errors` (list of str), `.metrics`, `.correlation_id`. Precompiled handles via `PolicySet.from_str` and `Entities.from_json_str` work.
- **Verified number handling:**

| Context value | Result |
|---|---|
| `{"amount": 1500}` (int) | Long compare `context.amount > 1000` works |
| `{"amount": 1500.5}` (float) | `NoDecision`, `errors=['failed to build request: … RawCedarValueJson']` (no exception) |
| Int above i64 | Same `NoDecision` |
| Int or string passed to `.greaterThan(decimal(...))` | Evaluation error: `expected decimal, got long` (or string) |
| `{"amount": {"__extn": {"fn": "decimal", "arg": "1500.5000"}}}` | `context.amount.greaterThan(decimal("1000.00"))` works (max 4 fractional digits) |
| Forbid referencing a missing attribute | **Allow** with `errors` populated (fail-open) |
| Empty policy set | Deny |

- **One policy for both int and float amounts.** Normalise in Python so every float, and the key `amount`, becomes the `__extn` decimal form (the `to_cedar` helper in the sketch). Then use:
  ```cedar
  permit(principal, action, resource);
  forbid(principal, action == Action::"undercover-app___pay_claim", resource)
  when { !(context has amount) || context.amount.greaterThan(decimal("1000.00")) }
  unless { principal in Role::"senior" };
  ```
  The alternative is a pre-computed Long such as `amount_cents`.
- Always treat non-empty `diagnostics.errors` as a deny (done in the sketch).
- Test results: ints 1500 and floats 1500.5 and 1000.01 denied; 999 and 1000 allowed; a missing amount denied; a senior-role principal allowed.

## 6. SigV4 for httpx

Tested offline with fake credentials against `MockTransport` for both `httpx` and `httpx2`. The signed headers were `content-type;host;x-amz-date;x-amz-security-token`, and a streamed request body was read and hashed. The code is in the sketch (`SigV4Auth`).

- `requires_request_body = True` is required so the body is hashed before `auth_flow` runs.
- Sign only a minimal header set. `botocore.auth.SigV4Auth` signs every header you hand it, including `Connection` and `Accept-Encoding`, which intermediaries can alter.
- Call `get_frozen_credentials()` per request so role credentials refresh.
- Service names are `"lambda"` for Function URLs and `"execute-api"` for API Gateway. The Lambda docs state that `AWS_IAM` function URLs need every request signed with SigV4 (https://docs.aws.amazon.com/lambda/latest/dg/urls-invocation.html). **I did not verify the literal service name or the signature against a live endpoint (no AWS credentials).**
- **IAM permissions:** new Function URLs require both `lambda:InvokeFunctionUrl` and `lambda:InvokeFunction` (https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html).
- **`aws/mcp-proxy-for-aws`** (366★, library on PyPI as `mcp-proxy-for-aws` 1.7.0): `from mcp_proxy_for_aws.client import aws_iam_streamablehttp_client` takes `endpoint`, `aws_region`, `aws_service`, `credentials`. It pins `fastmcp<3.5,>=3.2`, so it conflicts with FastMCP 4.

## 7. Open-source projects

I found no single project that combines FastMCP + OpenAPI-to-MCP + proxy + JWT/API-key auth + Cedar (cedarpy) + audit. Stars and last push are as of 2026-10-31 (GitHub API).

| Project | Stars | Last push | Notes |
|---|---|---|---|
| https://github.com/IBM/mcp-context-forge | 4,731 | 2026-10-30 | Python gateway, v1.1.0. Cedar via a `cedar-agent` sidecar over HTTP (`plugins/unified_pdp/engines/cedar_engine.py`), not cedarpy. Heavy |
| https://github.com/agentgateway/agentgateway | 5,822 | 2026-10-30 | Rust |
| https://github.com/docker/mcp-gateway | 1,617 | 2026-10-26 | Go |
| https://github.com/microsoft/mcp-gateway | 899 | 2026-10-30 | C# |
| https://github.com/sparfenyuk/mcp-proxy | 2,812 | 2026-10-29 | Python proxy only |
| https://github.com/Ultrathink-Solutions/fastmcp-gateway | 3 | 2026-10-31 | PyPI 0.35.0, progressive discovery, access policy; no OpenAPI or Cedar |
| https://github.com/cedar-policy/cedar-for-agents | 57 | 2026-10-28 | Rust crates for Cedar schemas from MCP tools, with WASM and Python bindings; not inspected further |
| https://github.com/k9securityio/cedar-py | 69 | 2026-10-20 | cedarpy itself |

## 8. Reference `gateway.py` (tested end to end on FastMCP 4.1.4)

This ran under both uvicorn and Mangum on Windows. A local FastAPI backend (6 operations, `X-API-Key`, no `servers`) and a local stateless FastMCP context server stood in for the two targets. The run showed the following (the 3.4.11 run was done on an earlier variant of the sketch):

- Static key accepted; a bad token returned 401.
- `pay_claim` of 500 allowed; of 1500 denied with "Tool Execution Denied".
- The upstream context server received no `Authorization` header.
- 6 audit lines written in the uvicorn run.

On 3.4.11 an earlier variant of the sketch worked with the `httpx` fallback import. That earlier variant had the transport-attribute opt-out and leaked the header. The `StripAuthorization` fix was tested separately on 3.4.11, and the final sketch was run on 4.1.4 only.

```python
import json, os, time
from decimal import ROUND_HALF_UP, Decimal
try:
    import httpx2 as httpx                      # FastMCP >= 4 uses httpx2
except ImportError:
    import httpx                                # FastMCP 3.x uses httpx
import boto3, cedarpy
from botocore.auth import SigV4Auth as BotoSigV4
from botocore.awsrequest import AWSRequest
from fastmcp import FastMCP
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.exceptions import ToolError
from fastmcp.server import create_proxy
from fastmcp.server.auth import MultiAuth
from fastmcp.server.auth.providers.jwt import JWTVerifier, StaticTokenVerifier
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.providers.proxy import ProxyClient

POLICIES = os.environ.get("CEDAR_POLICIES") or '''
permit(principal, action, resource);
forbid(principal, action == Action::"undercover-app___pay_claim", resource)
when { !(context has amount) || context.amount.greaterThan(decimal("1000.00")) }
unless { principal in Role::"senior" };
'''

def secret(name: str) -> str:                   # env first, else AWS Secrets Manager (<NAME>_ARN)  [Secrets Manager call UNVERIFIED]
    if name in os.environ:
        return os.environ[name]
    return boto3.client("secretsmanager").get_secret_value(SecretId=os.environ[name + "_ARN"])["SecretString"]

class StripAuthorization(httpx.Auth):           # never leak the caller's bearer token to an upstream
    def auth_flow(self, request):
        request.headers.pop("authorization", None)
        yield request

class SigV4Auth(httpx.Auth):                    # outbound IAM auth; "lambda" (Function URL) / "execute-api"   [UNVERIFIED vs live AWS]
    requires_request_body = True                # body is hashed, so it must be read before auth_flow
    def __init__(self, service="lambda", region=None):
        self.session, self.service = boto3.Session(), service
        self.region = region or self.session.region_name or "us-east-1"
    def auth_flow(self, request):
        creds = self.session.get_credentials().get_frozen_credentials()      # refreshes expiring role creds
        host = request.url.netloc.decode() if isinstance(request.url.netloc, bytes) else request.url.netloc
        headers = {"Host": host, **({"Content-Type": request.headers["content-type"]} if "content-type" in request.headers else {})}
        aws = AWSRequest(method=request.method, url=str(request.url), data=request.content, headers=headers)
        BotoSigV4(creds, self.service, self.region).add_auth(aws)
        request.headers.update({k: aws.headers[k] for k in ("Authorization", "X-Amz-Date", "X-Amz-Security-Token") if k in aws.headers})
        yield request

def to_cedar(v, key=None):                      # Cedar JSON has no floats/None: floats and "amount" become decimal()
    if v is None or isinstance(v, (bool, str)):
        return v
    if isinstance(v, (int, float)):
        if isinstance(v, float) or key == "amount":
            return {"__extn": {"fn": "decimal", "arg": format(Decimal(str(v)).quantize(Decimal("0.0001"), ROUND_HALF_UP), "f")}}
        return v
    if isinstance(v, dict):
        return {k: to_cedar(x, k) for k, x in v.items() if x is not None}
    return [to_cedar(x) for x in v if x is not None] if isinstance(v, (list, tuple)) else str(v)

class CedarPolicy(Middleware):
    def __init__(self, mode="enforce", audit_file=None):
        self.mode, self.audit_file = mode, audit_file                         # off | log_only | enforce
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        if self.mode == "off":
            return await call_next(context)
        tool, args = context.message.name, context.message.arguments or {}
        tok = get_access_token()                                              # None if unauthenticated
        claims = tok.claims if tok else {}
        sub = claims.get("sub") or (tok.client_id if tok else "anonymous")
        roles = claims.get("cognito:groups") or claims.get("roles") or []
        ents = [{"uid": {"type": "User", "id": sub}, "attrs": {}, "parents": [{"type": "Role", "id": r} for r in roles]}]
        ents += [{"uid": {"type": "Role", "id": r}, "attrs": {}, "parents": []} for r in roles]
        res = cedarpy.is_authorized({"principal": f'User::"{sub}"', "action": f'Action::"{tool}"',
                                     "resource": 'Gateway::"undercover"', "context": to_cedar(args)}, POLICIES, ents)
        allowed = res.allowed and not res.diagnostics.errors                  # a Cedar error inside a forbid fails OPEN: deny instead
        rec = {"ts": time.time(), "principal": sub, "tool": tool, "decision": res.decision.value, "allowed": allowed,
               "reasons": res.diagnostics.reasons, "errors": res.diagnostics.errors, "mode": self.mode}
        print(json.dumps(rec), flush=True)                                    # JSON lines -> stdout / CloudWatch
        if self.audit_file:
            with open(self.audit_file, "a") as f:
                f.write(json.dumps(rec) + "\n")
        if not allowed and self.mode == "enforce":
            raise ToolError(f"Tool Execution Denied: {tool} is not permitted for {sub}")   # arrives as isError=True result
        return await call_next(context)

def build_auth():
    verifiers = []
    if os.environ.get("JWKS_URI"):              # Cognito: https://cognito-idp.<region>.amazonaws.com/<pool>/.well-known/jwks.json
        verifiers.append(JWTVerifier(jwks_uri=os.environ["JWKS_URI"], issuer=os.environ["JWT_ISSUER"],
                                     audience=os.environ.get("JWT_AUDIENCE") or None))   # Cognito access tokens carry no `aud`
    if os.environ.get("GATEWAY_API_KEY"):       # StaticTokenVerifier is dev-only per FastMCP docs; see 1.5
        verifiers.append(StaticTokenVerifier(tokens={secret("GATEWAY_API_KEY"): {"client_id": "static-key", "sub": "static-key", "scopes": [], "roles": ["service"]}}))
    return MultiAuth(verifiers=verifiers)

def build_gateway() -> FastMCP:
    base = os.environ["APP_BASE_URL"]
    spec = httpx.get(f"{base}/api/agent/openapi.json", timeout=15).json(); spec.pop("servers", None)
    api = httpx.AsyncClient(base_url=base, headers={"X-API-Key": secret("APP_API_KEY")}, timeout=30)   # key never becomes a tool input
    gw = FastMCP("undercover-gateway", auth=build_auth(),
                 middleware=[CedarPolicy(os.environ.get("POLICY_MODE", "enforce"), os.environ.get("AUDIT_FILE"))])
    # Namespace joins prefix + "_", so a "__"-suffixed namespace yields "<target>___<tool>"
    gw.mount(FastMCP.from_openapi(spec, client=api, name="undercover-app"), namespace="undercover-app__")
    url = os.environ.get("CONTEXT_URL", "http://127.0.0.1:8006/mcp")
    transport = StreamableHttpTransport(url, auth=SigV4Auth("lambda") if ".lambda-url." in url else StripAuthorization())
    try:
        client = ProxyClient(transport, forward_incoming_headers=False)      # FastMCP 4
    except TypeError:
        client = ProxyClient(transport)                                      # FastMCP 3.x always forwards; the auth object above overwrites/strips it
    gw.mount(create_proxy(client, name="undercover-context"), namespace="undercover-context__")
    return gw

app = build_gateway().http_app(path="/mcp", stateless_http=True, json_response=True)   # local: uvicorn gateway:app --port 8100
def handler(event, context, _m=[]):                                                    # Lambda: Mangum runs lifespan startup/shutdown per call
    from mangum import Mangum
    _m or _m.append(Mangum(app, lifespan="auto"))
    return _m[0](event, context)
```

**Lines or behaviours I did not verify**
- **`secret()`:** the Secrets Manager call (no AWS access).
- **`SigV4Auth`:** acceptance by a live Lambda Function URL, and the `".lambda-url." in url` heuristic.
- **`JWTVerifier` branch:** it was not exercised inside the sketch run. I verified the same constructor and Cognito-style claims separately against a local JWKS server.
- **Mangum on 3.4.11:** multi-invocation. Also real Lambda cold starts, concurrency and the Function URL event shape. I used a synthetic payload-v2 event on 4.1.4 only.
- **`StaticTokenVerifier` in production:** FastMCP calls it dev-only.
- **Mixed `httpx` / `httpx2` pairing:** on FastMCP 4, passing a plain `httpx.Auth` to a transport. The docs say it must be `httpx2`; I did not test that case.
- **Real Bedrock calls:** none made.
- **`AWSCognitoProvider` and `SupabaseProvider`:** signatures only, not run.

**Environment notes**
- On this OneDrive-synced profile, `uv`'s default hardlink cache failed with OS error 396. Setting `UV_LINK_MODE=copy` and a cache dir outside OneDrive fixed it.
- I left the repo untouched (`git status` shows only the pre-existing untracked `.github/`, `agentcore-alternatives/`, `slides/`) and stopped all test servers.
