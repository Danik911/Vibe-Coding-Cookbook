"""The gateway's configuration, read from one YAML file.

Secrets are never written in the file: each one is a reference that
`credentials.SecretResolver` resolves when it's needed, such as
`env:UNDERCOVER_API_KEY` or `aws-secretsmanager:undercover/app-key#api_key`.
"""

from __future__ import annotations

import os
import re
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PolicyMode(StrEnum):
    OFF = "off"
    LOG_ONLY = "log_only"
    ENFORCE = "enforce"


class ApiKeyIdentity(Strict):
    """A machine caller, such as the claim agent, that sends a static key as its bearer token."""

    principal_id: str
    principal_type: str = "Agent"
    secret: str


class JwtSettings(Strict):
    """Callers with a JWT from an identity provider (Cognito, Supabase, Keycloak, Entra ID).

    Every token must name the issuer, carry an expiry, and be for this gateway: its
    audience, or for Cognito's access tokens (which have none) an allowed app client.
    Claims named in `attribute_claims` become the principal's attributes in Cedar;
    declare them in the schema too when one is set.
    """

    jwks_uri: str | None = None
    public_key: str | None = None
    issuer: str | None = None
    audience: str | None = None
    algorithm: str = "RS256"
    principal_type: str = "User"
    principal_claim: str = "sub"
    attribute_claims: tuple[str, ...] = ()
    allowed_client_ids: tuple[str, ...] = ()
    required_claims: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _one_key_source(self) -> JwtSettings:
        if (self.jwks_uri is None) == (self.public_key is None):
            raise ValueError("jwt needs exactly one of jwks_uri or public_key")
        if not self.issuer:
            raise ValueError("jwt needs issuer, so tokens from another issuer are refused")
        if not self.audience and not self.allowed_client_ids:
            raise ValueError("jwt needs audience or allowed_client_ids, so tokens for another service are refused")
        return self


class InboundSettings(Strict):
    """How callers prove who they are.

    - `tokens`: bearer tokens, checked against `api_keys` and then `jwt`.
    - `iam`: AWS checks a SigV4 signature in front of the gateway (a Lambda Function URL
      with AWS_IAM auth), and the gateway reads the caller's ARN from the Lambda event.
    - `none`: local development only; every caller is `Anonymous::"local"`.
    """

    mode: Literal["tokens", "iam", "none"] = "tokens"
    api_keys: tuple[ApiKeyIdentity, ...] = ()
    jwt: JwtSettings | None = None

    @model_validator(mode="after")
    def _tokens_need_a_verifier(self) -> InboundSettings:
        if self.mode == "tokens" and not self.api_keys and self.jwt is None:
            raise ValueError("inbound mode 'tokens' needs api_keys or jwt")
        return self


class NoCredentials(Strict):
    type: Literal["none"] = "none"


class ApiKeyCredentials(Strict):
    """Adds a header from a secret to every request, as AgentCore Identity's API key provider does."""

    type: Literal["api_key"]
    header: str = "X-API-Key"
    secret: str


class BearerCredentials(Strict):
    type: Literal["bearer"]
    secret: str


class SigV4Credentials(Strict):
    """Signs every request with the gateway's own AWS role (`lambda` for a Function URL)."""

    type: Literal["sigv4"]
    service: str = "lambda"
    region: str | None = None


Credentials = Annotated[
    NoCredentials | ApiKeyCredentials | BearerCredentials | SigV4Credentials,
    Field(discriminator="type"),
]


class OpenApiTarget(Strict):
    """A REST API described by OpenAPI: each operation becomes a tool named after its operationId."""

    name: str
    type: Literal["openapi"]
    base_url: str
    spec_url: str | None = None
    spec_file: str | None = None
    include_operations: tuple[str, ...] = ()
    credentials: Credentials = NoCredentials()
    timeout_seconds: float = 30.0
    validate_output: bool = False

    @model_validator(mode="after")
    def _one_spec_source(self) -> OpenApiTarget:
        if (self.spec_url is None) == (self.spec_file is None):
            raise ValueError(f"target {self.name!r} needs exactly one of spec_url or spec_file")
        return self


class McpTarget(Strict):
    """Another MCP server over streamable HTTP, whose tools the gateway passes on."""

    name: str
    type: Literal["mcp"]
    url: str
    credentials: Credentials = NoCredentials()
    cache_ttl_seconds: float = 300.0


Target = Annotated[OpenApiTarget | McpTarget, Field(discriminator="type")]


class VerifiedPermissionsSettings(Strict):
    policy_store_id: str
    region: str | None = None


class PolicySettings(Strict):
    engine: Literal["cedar", "verified_permissions"] = "cedar"
    mode: PolicyMode = PolicyMode.LOG_ONLY
    policies_file: str | None = None
    schema_file: str | None = None
    namespace: str = "Mcp"
    resource_id: str = "gateway"
    denial: Literal["protocol_error", "tool_error"] = "protocol_error"
    hide_unpermitted_tools: bool = True
    deny_on_evaluation_errors: bool = True
    verified_permissions: VerifiedPermissionsSettings | None = None

    @model_validator(mode="after")
    def _engine_settings(self) -> PolicySettings:
        if self.mode is PolicyMode.OFF:
            return self
        if self.engine == "cedar" and self.policies_file is None:
            raise ValueError("the cedar engine needs policies_file")
        if self.engine == "verified_permissions" and self.verified_permissions is None:
            raise ValueError("the verified_permissions engine needs verified_permissions settings")
        return self


class AuditSettings(Strict):
    destination: str = "stdout"
    log_argument_values: bool = False
    emf_metrics: bool = False
    metrics_namespace: str = "McpGateway"


TARGET_NAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?")
SEPARATOR = re.compile(r"[_.:~]+")


class GatewayConfig(Strict):
    name: str = "mcp-gateway"
    separator: str = "___"
    inbound: InboundSettings
    targets: tuple[Target, ...]
    policy: PolicySettings = PolicySettings(mode=PolicyMode.OFF)
    audit: AuditSettings = AuditSettings()
    base_dir: Path = Path()

    @model_validator(mode="after")
    def _unambiguous_tool_names(self) -> GatewayConfig:
        """Target names of letters, digits and inner hyphens, and a separator of none of those,
        so every `<target><separator><tool>` name belongs to exactly one target."""
        names = [target.name for target in self.targets]
        if len(names) != len(set(names)):
            raise ValueError("target names must be unique")
        if not SEPARATOR.fullmatch(self.separator):
            raise ValueError("the separator must be made of _ . : or ~")
        bad = [name for name in names if not TARGET_NAME.fullmatch(name)]
        if bad:
            raise ValueError(f"target names may hold only letters, digits and inner hyphens: {', '.join(bad)}")
        return self

    def resolve_path(self, path: str) -> Path:
        candidate = Path(path)
        return candidate if candidate.is_absolute() else self.base_dir / candidate


def load_config(path: str | Path) -> GatewayConfig:
    """Read a YAML config. Relative file paths in it are relative to the file.

    `${NAME}` is replaced by the environment variable NAME, for settings that differ
    between deployments, such as URLs and ARNs. Secrets stay references, never values.
    """
    file = Path(path)
    data = interpolate(yaml.safe_load(file.read_text(encoding="utf-8")))
    return GatewayConfig.model_validate({**data, "base_dir": file.resolve().parent})


def interpolate(value: Any) -> Any:
    """Every `${NAME}` in the config's string values, replaced from the environment."""
    if isinstance(value, dict):
        return {key: interpolate(item) for key, item in value.items()}
    if isinstance(value, list):
        return [interpolate(item) for item in value]
    if not isinstance(value, str):
        return value

    def setting(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in os.environ:
            raise ValueError(f"the config needs the environment variable {name}")
        return os.environ[name]

    return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", setting, value)
