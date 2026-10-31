"""Inbound identity: who is calling the gateway.

Each caller becomes a `Principal`, the subject of every policy decision: an agent with
its own key, a user with a JWT from an identity provider, or an AWS identity whose
SigV4 signature AWS checked in front of the gateway.
"""

from __future__ import annotations

import hmac
import re
from dataclasses import dataclass, field
from typing import Any

from fastmcp.server.auth.auth import AccessToken, TokenVerifier
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token, get_http_request

from diy_gateway.config import InboundSettings, JwtSettings
from diy_gateway.credentials import SecretResolver

PRINCIPAL_TYPE = "gw_principal_type"
PRINCIPAL_ID = "gw_principal_id"
PRINCIPAL_ATTRIBUTES = "gw_principal_attributes"


@dataclass(frozen=True)
class Principal:
    type: str
    id: str
    attributes: dict[str, Any] = field(default_factory=dict)


ANONYMOUS = Principal("Anonymous", "local")


class GatewayTokenVerifier(TokenVerifier):
    """Accepts an agent's static key or a JWT, and records the principal in the token's claims."""

    def __init__(self, settings: InboundSettings, resolver: SecretResolver) -> None:
        super().__init__()
        self._api_keys = settings.api_keys
        self._resolver = resolver
        self._jwt_settings = settings.jwt
        self._jwt = _jwt_verifier(settings.jwt) if settings.jwt else None

    async def verify_token(self, token: str) -> AccessToken | None:
        for identity in self._api_keys:
            expected = self._resolver.get(identity.secret).encode()
            if hmac.compare_digest(token.encode(), expected):
                return AccessToken(
                    token=token,
                    client_id=identity.principal_id,
                    scopes=[],
                    claims={PRINCIPAL_TYPE: identity.principal_type, PRINCIPAL_ID: identity.principal_id},
                )
        if self._jwt is None or self._jwt_settings is None:
            return None
        verified = await self._jwt.verify_token(token)
        if verified is None or not isinstance(verified.claims.get("exp"), int | float):
            return None  # FastMCP accepts a token with no exp forever; a gateway shouldn't
        settings = self._jwt_settings
        if not _claims_match(verified.claims, settings):
            return None
        subject = verified.claims.get(settings.principal_claim)
        if not isinstance(subject, str) or not subject:
            return None
        attributes = {
            name: verified.claims[name]
            for name in settings.attribute_claims
            if isinstance(verified.claims.get(name), str | int | bool)
        }
        attributes["scopes"] = list(verified.scopes)
        claims = {
            **verified.claims,
            PRINCIPAL_TYPE: settings.principal_type,
            PRINCIPAL_ID: subject,
            PRINCIPAL_ATTRIBUTES: attributes,
        }
        return verified.model_copy(update={"claims": claims})


def _claims_match(claims: dict[str, Any], settings: JwtSettings) -> bool:
    """The checks a signature and audience can't make, such as Cognito's client_id and token_use.

    Cognito's access tokens carry no `aud`: the app client is in `client_id`.
    """
    if settings.allowed_client_ids:
        client = claims.get("client_id") or claims.get("azp")
        if client not in settings.allowed_client_ids:
            return False
    return all(claims.get(name) == value for name, value in settings.required_claims.items())


def _jwt_verifier(settings: JwtSettings) -> JWTVerifier:
    return JWTVerifier(
        jwks_uri=settings.jwks_uri,
        public_key=settings.public_key,
        issuer=settings.issuer,
        audience=settings.audience,
        algorithm=settings.algorithm,
    )


def current_principal(mode: str) -> Principal | None:
    """The caller of the request being handled, or None when it can't be told."""
    if mode == "none":
        return ANONYMOUS
    if mode == "iam":
        return _iam_principal()
    token = get_access_token()
    if token is None:
        return None
    principal_type = token.claims.get(PRINCIPAL_TYPE)
    principal_id = token.claims.get(PRINCIPAL_ID)
    if not principal_type or not principal_id:
        return None
    return Principal(str(principal_type), str(principal_id), dict(token.claims.get(PRINCIPAL_ATTRIBUTES, {})))


def _iam_principal() -> Principal | None:
    """The AWS identity a Lambda Function URL with AWS_IAM auth has already verified.

    An assumed role's session ARN becomes the role's ARN, so a policy can name the role.
    """
    try:
        event = get_http_request().scope.get("aws.event") or {}
    except RuntimeError:
        return None
    iam = event.get("requestContext", {}).get("authorizer", {}).get("iam") or {}
    arn = iam.get("userArn")
    if not arn:
        return None
    return Principal("IamEntity", role_arn(arn), {"account": str(iam.get("accountId", ""))})


def role_arn(arn: str) -> str:
    """`arn:aws:sts::<account>:assumed-role/<role>/<session>` as `arn:aws:iam::<account>:role/<role>`."""
    match = re.fullmatch(r"arn:(aws[a-z-]*):sts::(\d{12}):assumed-role/([^/]+)/.+", arn)
    if match is None:
        return arn
    partition, account, role = match.groups()
    return f"arn:{partition}:iam::{account}:role/{role}"
