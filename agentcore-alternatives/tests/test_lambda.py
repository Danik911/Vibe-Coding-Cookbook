"""The gateway on Lambda: Function URL events, twice in one process, with inbound IAM."""

from __future__ import annotations

import base64
import json
from functools import partial
from typing import Any

import pytest

from diy_gateway import lambda_handler
from diy_gateway.app import GatewayFactory, Upstreams
from diy_gateway.config import GatewayConfig
from examples.demo_upstreams.context_server import context
from tests.conftest import with_changes

CALLER_ARN = "arn:aws:sts::123456789012:assumed-role/claim-agent-runtime/session-1"


def function_url_event(body: dict[str, Any], *, iam: bool) -> dict[str, Any]:
    host = "abc123.lambda-url.us-east-1.on.aws"
    context: dict[str, Any] = {
        "accountId": "123456789012",
        "apiId": "abc123",
        "domainName": host,
        "domainPrefix": "abc123",
        "http": {"method": "POST", "path": "/mcp", "protocol": "HTTP/1.1", "sourceIp": "10.0.0.1", "userAgent": "t"},
        "requestId": "request-1",
        "routeKey": "$default",
        "stage": "$default",
        "time": "31/Oct/2026:12:00:00 +0000",
        "timeEpoch": 1793448000000,
    }
    if iam:
        context["authorizer"] = {"iam": {"accountId": "123456789012", "userArn": CALLER_ARN, "callerId": "AROA:1"}}
    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/mcp",
        "rawQueryString": "",
        "headers": {
            "host": host,
            "content-type": "application/json",
            "accept": "application/json, text/event-stream",
        },
        "requestContext": context,
        "body": json.dumps(body),
        "isBase64Encoded": False,
    }


def response_body(response: dict[str, Any]) -> dict[str, Any]:
    body = response["body"]
    if response.get("isBase64Encoded"):
        body = base64.b64decode(body).decode()
    return json.loads(body)


@pytest.fixture
def iam_config(demo_config: GatewayConfig) -> GatewayConfig:
    context_target = demo_config.targets[1].model_dump(mode="json")
    return with_changes(demo_config, inbound={"mode": "iam", "api_keys": []}, targets=[context_target])


@pytest.fixture
def lambda_gateway(monkeypatch: pytest.MonkeyPatch, iam_config: GatewayConfig) -> None:
    monkeypatch.setattr(lambda_handler, "_state", {})
    monkeypatch.setattr(lambda_handler, "load_config", lambda _: iam_config)
    in_process = partial(GatewayFactory, upstreams=Upstreams(mcp={"undercover-context": context}))
    monkeypatch.setattr(lambda_handler, "GatewayFactory", in_process)


@pytest.mark.usefixtures("lambda_gateway")
def test_the_handler_answers_twice_in_one_process_as_the_iam_caller(capsys: pytest.CaptureFixture[str]):
    listing = lambda_handler.handler(
        function_url_event({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}, iam=True), None
    )
    factory = lambda_handler._state["factory"]
    call = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "undercover-context___get_plan", "arguments": {"plan": "premium"}},
    }
    result = lambda_handler.handler(function_url_event(call, iam=True), None)
    names = {tool["name"] for tool in response_body(listing)["result"]["tools"]}
    assert names == {"undercover-context___lookup_term", "undercover-context___get_plan"}
    assert response_body(result)["result"]["structuredContent"]["deductible"] == 50
    assert lambda_handler._state["factory"] is factory
    assert "IamEntity::arn:aws:iam::123456789012:role/claim-agent-runtime" in capsys.readouterr().out


@pytest.mark.usefixtures("lambda_gateway")
def test_without_a_verified_iam_caller_every_call_is_refused():
    call = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "undercover-context___get_plan", "arguments": {"plan": "premium"}},
    }
    response = response_body(lambda_handler.handler(function_url_event(call, iam=False), None))
    assert "Tool Execution Denied" in response["error"]["message"]
