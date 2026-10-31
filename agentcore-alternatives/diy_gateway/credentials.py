"""Outbound credentials: what AgentCore Identity does for a Gateway target.

The gateway holds each target's credential and adds it to the request, so the agent
never sees it. A credential is a reference to a secret, resolved when a request needs
it and cached for a while, so a rotated secret is picked up without a restart.
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from collections.abc import AsyncGenerator, Callable, Generator
from typing import Any

import boto3
import httpx2
from botocore.auth import SigV4Auth as BotocoreSigV4
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

SECRETS_MANAGER = "aws-secretsmanager"


class SecretUnavailableError(RuntimeError):
    """A secret reference that can't be resolved. The message never holds the secret."""


class SecretResolver:
    """Resolves `env:NAME` and `aws-secretsmanager:<id or ARN>[#json-key]` references."""

    def __init__(
        self,
        ttl_seconds: float = 300.0,
        secrets_client_factory: Callable[[str | None], Any] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl_seconds
        self._client_factory = secrets_client_factory or _secrets_manager_client
        self._clock = clock
        self._cache: dict[str, tuple[float, str]] = {}
        self._lock = threading.Lock()

    def get(self, ref: str) -> str:
        scheme, _, rest = ref.partition(":")
        if scheme == "env":
            value = os.environ.get(rest, "")
            if not value:
                raise SecretUnavailableError(f"environment variable {rest} is not set")
            return value
        if scheme != SECRETS_MANAGER:
            raise SecretUnavailableError(f"unknown secret reference scheme {scheme!r}")
        with self._lock:
            cached = self._cache.get(ref)
            if cached and self._clock() - cached[0] < self._ttl:
                return cached[1]
        value = self._from_secrets_manager(rest)
        with self._lock:
            self._cache[ref] = (self._clock(), value)
        return value

    def _from_secrets_manager(self, rest: str) -> str:
        secret_id, _, key = rest.partition("#")
        region = secret_id.split(":")[3] if secret_id.startswith("arn:") else None
        response = self._client_factory(region).get_secret_value(SecretId=secret_id)
        value = response.get("SecretString")
        if value is None:
            raise SecretUnavailableError(f"secret {secret_id} has no string value")
        if key:
            try:
                value = json.loads(value)[key]
            except (ValueError, KeyError) as error:
                raise SecretUnavailableError(f"secret {secret_id} has no key {key!r}") from error
        return str(value)


def _secrets_manager_client(region: str | None) -> Any:
    return boto3.client("secretsmanager", region_name=region)


class _SecretHeaderAuth(httpx2.Auth):
    """Adds one header whose value comes from a secret, fetched off the event loop."""

    def __init__(self, resolver: SecretResolver, secret_ref: str, header: str, prefix: str = "") -> None:
        self._resolver = resolver
        self._secret_ref = secret_ref
        self._header = header
        self._prefix = prefix

    def auth_flow(self, request: httpx2.Request) -> Generator[httpx2.Request, httpx2.Response]:
        request.headers[self._header] = self._prefix + self._resolver.get(self._secret_ref)
        yield request

    async def async_auth_flow(self, request: httpx2.Request) -> AsyncGenerator[httpx2.Request, httpx2.Response]:
        value = await asyncio.to_thread(self._resolver.get, self._secret_ref)
        request.headers[self._header] = self._prefix + value
        yield request


class ApiKeyAuth(_SecretHeaderAuth):
    def __init__(self, resolver: SecretResolver, secret_ref: str, header: str = "X-API-Key") -> None:
        super().__init__(resolver, secret_ref, header)


class BearerAuth(_SecretHeaderAuth):
    def __init__(self, resolver: SecretResolver, secret_ref: str) -> None:
        super().__init__(resolver, secret_ref, "Authorization", prefix="Bearer ")


def sigv4_headers(
    *,
    method: str,
    url: str,
    body: bytes,
    content_type: str | None,
    service: str,
    region: str,
    credentials: Credentials,
) -> dict[str, str]:
    """The headers that sign one request with AWS Signature Version 4."""
    headers = {"Host": httpx2.URL(url).netloc.decode()}
    if content_type:
        headers["Content-Type"] = content_type
    signed = AWSRequest(method=method, url=url, data=body, headers=headers)
    BotocoreSigV4(credentials.get_frozen_credentials(), service, region).add_auth(signed)
    return {
        name: signed.headers[name]
        for name in ("Authorization", "X-Amz-Date", "X-Amz-Security-Token")
        if name in signed.headers
    }


class SigV4Auth(httpx2.Auth):
    """Signs each request with the process's AWS credentials, for an IAM-protected target."""

    requires_request_body = True

    def __init__(self, service: str, region: str | None = None, session: boto3.Session | None = None) -> None:
        self._session = session or boto3.Session()
        self._service = service
        self._region = region or self._session.region_name
        if not self._region:
            raise SecretUnavailableError("SigV4 signing needs an AWS region")

    def auth_flow(self, request: httpx2.Request) -> Generator[httpx2.Request, httpx2.Response]:
        credentials = self._session.get_credentials()
        if credentials is None:
            raise SecretUnavailableError("no AWS credentials found for SigV4 signing")
        request.headers.update(
            sigv4_headers(
                method=request.method,
                url=str(request.url),
                body=request.content,
                content_type=request.headers.get("content-type"),
                service=self._service,
                region=str(self._region),
                credentials=credentials,
            )
        )
        yield request
