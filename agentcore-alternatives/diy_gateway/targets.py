"""Targets: the APIs and MCP servers behind the gateway, as AgentCore Gateway's targets.

Each target's tools are named `<target><separator><tool>`, by default
`undercover-app___pay_claim`, as AgentCore names them.
"""

from __future__ import annotations

import copy
from collections.abc import Sequence
from typing import Any

import httpx2
from fastmcp import FastMCP
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.prompts.base import Prompt
from fastmcp.resources.base import Resource
from fastmcp.resources.template import ResourceTemplate
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.providers import Provider
from fastmcp.server.providers.openapi import MCPType, OpenAPIProvider, RouteMap
from fastmcp.server.providers.proxy import ProxyClient, ProxyProvider
from fastmcp.server.transforms import (
    GetPromptNext,
    GetResourceNext,
    GetResourceTemplateNext,
    GetToolNext,
    Transform,
)
from fastmcp.tools.base import Tool
from fastmcp.utilities.versions import VersionSpec

from diy_gateway.config import (
    ApiKeyCredentials,
    BearerCredentials,
    Credentials,
    McpTarget,
    OpenApiTarget,
    SigV4Credentials,
)
from diy_gateway.credentials import ApiKeyAuth, BearerAuth, SecretResolver, SigV4Auth

HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}


class TargetPrefix(Transform):
    """Names a target's tools `<target><separator><tool>` and finds them by that name.

    A target exposes only its tools, as AgentCore Gateway does: its resources and prompts
    are hidden, since no policy decides them and their names could collide across targets.
    """

    def __init__(self, target: str, separator: str) -> None:
        self._prefix = f"{target}{separator}"

    async def list_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]:
        return [tool.model_copy(update={"name": self._prefix + tool.name}) for tool in tools]

    async def get_tool(self, name: str, call_next: GetToolNext, *, version: VersionSpec | None = None) -> Tool | None:
        if not name.startswith(self._prefix):
            return None
        tool = await call_next(name.removeprefix(self._prefix), version=version)
        return tool.model_copy(update={"name": name}) if tool else None

    async def list_resources(self, resources: Sequence[Resource]) -> Sequence[Resource]:
        return []

    async def get_resource(
        self, uri: str, call_next: GetResourceNext, *, version: VersionSpec | None = None
    ) -> Resource | None:
        return None

    async def list_resource_templates(self, templates: Sequence[ResourceTemplate]) -> Sequence[ResourceTemplate]:
        return []

    async def get_resource_template(
        self, uri: str, call_next: GetResourceTemplateNext, *, version: VersionSpec | None = None
    ) -> ResourceTemplate | None:
        return None

    async def list_prompts(self, prompts: Sequence[Prompt]) -> Sequence[Prompt]:
        return []

    async def get_prompt(
        self, name: str, call_next: GetPromptNext, *, version: VersionSpec | None = None
    ) -> Prompt | None:
        return None


def outbound_auth(credentials: Credentials, resolver: SecretResolver) -> httpx2.Auth | None:
    match credentials:
        case ApiKeyCredentials(header=header, secret=secret):
            return ApiKeyAuth(resolver, secret, header)
        case BearerCredentials(secret=secret):
            return BearerAuth(resolver, secret)
        case SigV4Credentials(service=service, region=region):
            return SigV4Auth(service, region)
        case _:
            return None


def only_operations(spec: dict[str, Any], operation_ids: Sequence[str]) -> dict[str, Any]:
    """The spec with only the named operations, and no `servers`: the gateway sets the address.

    Whatever is in the spec, the agent can call, so an allow-list here keeps
    human-only routes away from the agent even when the document has them.
    """
    spec = copy.deepcopy(spec)
    spec.pop("servers", None)
    if not operation_ids:
        return spec
    wanted = set(operation_ids)
    paths: dict[str, Any] = {}
    for path, item in spec.get("paths", {}).items():
        kept = {
            key: value for key, value in item.items() if key not in HTTP_METHODS or value.get("operationId") in wanted
        }
        if HTTP_METHODS & kept.keys():
            paths[path] = kept
    spec["paths"] = paths
    found = {op.get("operationId") for item in paths.values() for key, op in item.items() if key in HTTP_METHODS}
    missing = wanted - found
    if missing:
        raise ValueError(f"operations not in the spec: {', '.join(sorted(missing))}")
    return spec


async def drop_caller_headers(request: httpx2.Request) -> None:
    """Removes the caller's HTTP headers that FastMCP's OpenAPI tools copy onto each upstream request.

    FastMCP leaves out Authorization and Cookie, but passes on the rest, so a caller could
    send a header the API trusts, such as X-User-Id. The gateway sends only what it decides:
    the request built from the tool's arguments and the target's own credential.
    """
    for name, value in get_http_headers().items():
        if request.headers.get(name) == value:
            del request.headers[name]


def openapi_provider(
    target: OpenApiTarget,
    spec: dict[str, Any],
    resolver: SecretResolver,
    transport: httpx2.AsyncBaseTransport | None = None,
) -> Provider:
    """Every operation in the spec as a tool that calls the API with the target's credential."""
    client = httpx2.AsyncClient(
        base_url=target.base_url,
        auth=outbound_auth(target.credentials, resolver),
        timeout=target.timeout_seconds,
        transport=transport,
        event_hooks={"request": [drop_caller_headers]},
    )
    return OpenAPIProvider(
        openapi_spec=only_operations(spec, target.include_operations),
        client=client,
        route_maps=[RouteMap(mcp_type=MCPType.TOOL)],
        validate_output=target.validate_output,
    )


def mcp_provider(target: McpTarget, resolver: SecretResolver, upstream: FastMCP | None = None) -> Provider:
    """The tools of another MCP server, each call forwarded with the target's credential.

    FastMCP's proxy forwards the caller's headers, Authorization among them, unless told
    not to. MCP's authorization spec forbids passing a client's token on, so the gateway
    turns that off: an upstream only ever sees the target's own credential.
    """
    if upstream is not None:
        return ProxyProvider(
            lambda: ProxyClient(upstream, forward_incoming_headers=False), cache_ttl=target.cache_ttl_seconds
        )
    auth = outbound_auth(target.credentials, resolver)
    return ProxyProvider(
        lambda: ProxyClient(StreamableHttpTransport(target.url, auth=auth), forward_incoming_headers=False),
        cache_ttl=target.cache_ttl_seconds,
    )


def fetch_spec(target: OpenApiTarget, resolver: SecretResolver, transport: httpx2.BaseTransport | None = None) -> dict:
    """The OpenAPI document, read with the target's credential when it comes from the API itself."""
    if target.spec_url is None:
        raise ValueError(f"target {target.name!r} has no spec_url")
    with httpx2.Client(
        auth=outbound_auth(target.credentials, resolver),
        timeout=target.timeout_seconds,
        transport=transport,
    ) as client:
        response = client.get(target.spec_url)
        response.raise_for_status()
        return response.json()
