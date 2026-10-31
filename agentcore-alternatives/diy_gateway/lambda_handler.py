"""The gateway on AWS Lambda, behind a Function URL or API Gateway.

Mangum runs an app's startup and shutdown around every request, and FastMCP's session
manager can only start once, so each request gets a freshly built gateway. One
`GatewayFactory` per process keeps the rest: the config, the secrets, the OpenAPI
documents, the token verifier (with its JWKS), the policy engine and the MCP proxies.

For inbound IAM, as AgentCore Gateway's AWS_IAM authorizer: give the Function URL
AWS_IAM auth and the config `inbound.mode: iam`; AWS checks the SigV4 signature and
the gateway reads the caller's role from the event.
"""

from __future__ import annotations

import os
from typing import Any

from mangum import Mangum

from diy_gateway.app import GatewayFactory, build_http_app
from diy_gateway.config import load_config

_state: dict[str, Any] = {}


def _factory() -> GatewayFactory:
    if "factory" not in _state:
        _state["factory"] = GatewayFactory(load_config(os.environ.get("GATEWAY_CONFIG", "gateway.yaml")))
    return _state["factory"]


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    app = build_http_app(_factory().build())
    return Mangum(app, lifespan="auto")(event, context)
