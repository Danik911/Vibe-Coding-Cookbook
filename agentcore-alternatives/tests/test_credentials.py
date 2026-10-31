"""Outbound credentials and the OpenAPI allow-list."""

from __future__ import annotations

import json
from typing import Any

import boto3
import httpx2
import pytest

from diy_gateway.credentials import ApiKeyAuth, SecretResolver, SecretUnavailableError, SigV4Auth
from diy_gateway.targets import only_operations


class FakeSecretsManager:
    def __init__(self) -> None:
        self.calls = 0

    def get_secret_value(self, SecretId: str) -> dict[str, Any]:  # noqa: N803 - boto3's name
        self.calls += 1
        return {"SecretString": json.dumps({"api_key": f"key-for-{SecretId.rsplit(':', 1)[-1]}"})}


def test_an_environment_secret(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SOME_KEY", "value")
    assert SecretResolver().get("env:SOME_KEY") == "value"


def test_a_missing_secret_names_it_without_a_value(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    with pytest.raises(SecretUnavailableError, match="MISSING_KEY"):
        SecretResolver().get("env:MISSING_KEY")


def test_secrets_manager_is_cached_until_the_ttl_passes():
    fake, regions, now = FakeSecretsManager(), [], [0.0]

    def factory(region: str | None) -> FakeSecretsManager:
        regions.append(region)
        return fake

    resolver = SecretResolver(ttl_seconds=60, secrets_client_factory=factory, clock=lambda: now[0])
    ref = "aws-secretsmanager:arn:aws:secretsmanager:eu-west-2:123456789012:secret:app#api_key"
    assert resolver.get(ref) == "key-for-app"
    resolver.get(ref)
    now[0] = 61
    resolver.get(ref)
    assert fake.calls == 2
    assert regions[0] == "eu-west-2"


def test_the_api_key_goes_in_its_header(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_KEY", "secret-value")
    seen: list[httpx2.Request] = []
    transport = httpx2.MockTransport(lambda request: seen.append(request) or httpx2.Response(200))
    with httpx2.Client(transport=transport, auth=ApiKeyAuth(SecretResolver(), "env:APP_KEY")) as client:
        client.get("https://app.test/api/claims/CLM-1")
    assert seen[0].headers["x-api-key"] == "secret-value"


def test_sigv4_signs_for_the_targets_service_and_region():
    session = boto3.Session(aws_access_key_id="AKIDEXAMPLE", aws_secret_access_key="secret", region_name="us-east-1")
    seen: list[httpx2.Request] = []
    transport = httpx2.MockTransport(lambda request: seen.append(request) or httpx2.Response(200))
    with httpx2.Client(transport=transport, auth=SigV4Auth("lambda", session=session)) as client:
        client.post("https://abc.lambda-url.us-east-1.on.aws/mcp", json={"jsonrpc": "2.0"})
    authorization = seen[0].headers["authorization"]
    assert authorization.startswith("AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/")
    assert "/us-east-1/lambda/aws4_request" in authorization
    assert "x-amz-date" in seen[0].headers


SPEC = {
    "openapi": "3.1.0",
    "servers": [{"url": "https://somewhere.else"}],
    "paths": {
        "/claims/{id}": {"get": {"operationId": "get_claim"}, "parameters": []},
        "/claims/{id}/sign-off": {"post": {"operationId": "sign_off_claim"}},
    },
}


def test_only_the_listed_operations_are_kept_and_servers_go():
    spec = only_operations(SPEC, ["get_claim"])
    assert "servers" not in spec
    assert list(spec["paths"]) == ["/claims/{id}"]


def test_an_operation_missing_from_the_spec_is_an_error():
    with pytest.raises(ValueError, match="pay_claim"):
        only_operations(SPEC, ["get_claim", "pay_claim"])
