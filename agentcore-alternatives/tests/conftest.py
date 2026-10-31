"""Shared fixtures: the demo stand-ins, a gateway config, and real HTTP servers in threads."""

from __future__ import annotations

import io
import json
import socket
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx2
import pytest
import uvicorn
from fastmcp.server.auth.providers.jwt import RSAKeyPair

from diy_gateway.app import Upstreams
from diy_gateway.config import GatewayConfig, load_config
from examples.demo_upstreams import app as demo_app
from examples.demo_upstreams.context_server import context

ROOT = Path(__file__).resolve().parents[1]
AGENT_KEY = "test-agent-key-0123456789abcdef"
APP_KEY = "test-app-key-0123456789abcdef"


@pytest.fixture(autouse=True)
def keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GATEWAY_CLAIM_AGENT_KEY", AGENT_KEY)
    monkeypatch.setenv("DEMO_APP_API_KEY", APP_KEY)
    demo_app.DECISIONS.clear()
    demo_app.PAYMENTS.clear()


def spec_transport(seen: list[dict[str, str]]) -> httpx2.MockTransport:
    """Serves the demo app's agent document, recording the headers the gateway sent."""

    def handle(request: httpx2.Request) -> httpx2.Response:
        seen.append(dict(request.headers))
        if request.headers.get("x-api-key") != APP_KEY:
            return httpx2.Response(401, json={"detail": "key needed"})
        return httpx2.Response(200, json=demo_app.agent_openapi())

    return httpx2.MockTransport(handle)


@pytest.fixture
def spec_requests() -> list[dict[str, str]]:
    return []


@pytest.fixture
def upstreams(spec_requests: list[dict[str, str]]) -> Upstreams:
    return Upstreams(
        http={"undercover-app": httpx2.ASGITransport(app=demo_app.app)},
        spec_http={"undercover-app": spec_transport(spec_requests)},
        mcp={"undercover-context": context},
    )


@pytest.fixture
def demo_config() -> GatewayConfig:
    return load_config(ROOT / "gateway.demo.yaml")


def with_changes(config: GatewayConfig, **sections: dict[str, Any]) -> GatewayConfig:
    """The config with some sections' fields changed, validated again."""
    data = config.model_dump(mode="json")
    for section, changes in sections.items():
        data[section] = {**data[section], **changes} if isinstance(data[section], dict) else changes
    return GatewayConfig.model_validate(data)


@pytest.fixture
def audit() -> io.StringIO:
    return io.StringIO()


def audit_records(stream: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(line) for line in stream.getvalue().splitlines()]


@pytest.fixture(scope="session")
def rsa_key() -> RSAKeyPair:
    return RSAKeyPair.generate()


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def serve() -> Iterator[Callable[[Any], str]]:
    """Starts an ASGI app on a free local port in a thread and gives its base URL."""
    servers: list[tuple[uvicorn.Server, threading.Thread]] = []

    def start(app: Any) -> str:
        port = _free_port()
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        deadline = time.monotonic() + 10
        while not server.started:
            if time.monotonic() > deadline:
                raise RuntimeError("server did not start")
            time.sleep(0.02)
        servers.append((server, thread))
        return f"http://127.0.0.1:{port}"

    yield start
    for server, thread in servers:
        server.should_exit = True
        thread.join(timeout=10)
