"""Builds the gateway: one MCP endpoint over every target, with inbound auth and policy."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any, TextIO

import boto3
import httpx2
import yaml
from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from diy_gateway.audit import AuditLog
from diy_gateway.config import GatewayConfig, McpTarget, OpenApiTarget, PolicyMode
from diy_gateway.credentials import SecretResolver
from diy_gateway.inbound import GatewayTokenVerifier
from diy_gateway.middleware import PolicyMiddleware
from diy_gateway.policy import CedarEngine, CedarRequestBuilder, PolicyEngine, VerifiedPermissionsEngine
from diy_gateway.targets import TargetPrefix, fetch_spec, mcp_provider, openapi_provider

SPEC_TTL_SECONDS = 300.0


@dataclass
class Upstreams:
    """In-process stand-ins for targets, for tests and demos: no network needed."""

    http: dict[str, httpx2.AsyncBaseTransport] = field(default_factory=dict)
    spec_http: dict[str, httpx2.BaseTransport] = field(default_factory=dict)
    mcp: dict[str, FastMCP] = field(default_factory=dict)


class SpecCache:
    """Keeps each target's OpenAPI document for a while, so a gateway built per request
    (as on Lambda) doesn't fetch it every time."""

    def __init__(self, ttl_seconds: float = SPEC_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._specs: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def get(self, config: GatewayConfig, target: OpenApiTarget, resolver: SecretResolver, upstreams: Upstreams) -> dict:
        if target.spec_file is not None:
            text = config.resolve_path(target.spec_file).read_text(encoding="utf-8")
            return json.loads(text) if target.spec_file.endswith(".json") else yaml.safe_load(text)
        with self._lock:
            cached = self._specs.get(target.name)
            if cached and time.monotonic() - cached[0] < self._ttl:
                return cached[1]
        spec = fetch_spec(target, resolver, upstreams.spec_http.get(target.name))
        with self._lock:
            self._specs[target.name] = (time.monotonic(), spec)
        return spec


def policy_engine(config: GatewayConfig) -> PolicyEngine | None:
    settings = config.policy
    if settings.mode is PolicyMode.OFF:
        return None
    builder = CedarRequestBuilder(settings.namespace, settings.resource_id)
    if settings.engine == "verified_permissions" and settings.verified_permissions is not None:
        avp = settings.verified_permissions
        client = boto3.client("verifiedpermissions", region_name=avp.region)
        return VerifiedPermissionsEngine(client, avp.policy_store_id, builder)
    if settings.policies_file is None:
        raise ValueError("the cedar engine needs policies_file")
    policies = config.resolve_path(settings.policies_file).read_text(encoding="utf-8")
    schema = config.resolve_path(settings.schema_file).read_text(encoding="utf-8") if settings.schema_file else None
    return CedarEngine(policies, builder, schema)


class GatewayFactory:
    """Builds gateways from one config, sharing what can outlive a request.

    On Lambda each request needs a fresh FastMCP app (see lambda_handler.py). What is shared:
    - the secrets cache;
    - the OpenAPI documents;
    - the token verifier, with its JWKS;
    - the policy engine, with its parsed policies;
    - the MCP targets' proxies, with their cached tool lists.

    The OpenAPI targets' HTTP clients are new for each gateway, since they hold connections.
    """

    def __init__(
        self,
        config: GatewayConfig,
        *,
        resolver: SecretResolver | None = None,
        engine: PolicyEngine | None = None,
        upstreams: Upstreams | None = None,
        specs: SpecCache | None = None,
        audit_stream: TextIO | None = None,
    ) -> None:
        self.config = config
        self._resolver = resolver or SecretResolver()
        self._upstreams = upstreams or Upstreams()
        self._specs = specs or SpecCache()
        self._audit = AuditLog(config.audit, audit_stream)
        self._engine = engine or policy_engine(config)
        self._auth = GatewayTokenVerifier(config.inbound, self._resolver) if config.inbound.mode == "tokens" else None
        self._mcp_providers = {
            target.name: mcp_provider(target, self._resolver, self._upstreams.mcp.get(target.name))
            for target in config.targets
            if isinstance(target, McpTarget)
        }

    def build(self) -> FastMCP:
        config = self.config
        middleware = PolicyMiddleware(
            engine=self._engine,
            settings=config.policy,
            inbound_mode=config.inbound.mode,
            separator=config.separator,
            targets=tuple(target.name for target in config.targets),
            audit=self._audit,
        )
        gateway = FastMCP(config.name, auth=self._auth, middleware=[middleware])
        for target in config.targets:
            match target:
                case OpenApiTarget():
                    spec = self._specs.get(config, target, self._resolver, self._upstreams)
                    provider = openapi_provider(target, spec, self._resolver, self._upstreams.http.get(target.name))
                case McpTarget():
                    provider = self._mcp_providers[target.name]
            gateway.add_provider(provider.wrap_transform(TargetPrefix(target.name, config.separator)))

        @gateway.custom_route("/health", methods=["GET"])
        async def health(_: Request) -> JSONResponse:
            return JSONResponse({"healthy": True})

        return gateway


def build_gateway(config: GatewayConfig, **options: Any) -> FastMCP:
    """One gateway: the usual entry point outside Lambda. Options as for GatewayFactory."""
    return GatewayFactory(config, **options).build()


def build_http_app(gateway: FastMCP) -> Starlette:
    """Streamable HTTP at /mcp, stateless with JSON responses, as AgentCore Gateway serves it."""
    return gateway.http_app(path="/mcp", stateless_http=True, json_response=True)
