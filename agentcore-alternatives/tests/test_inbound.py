"""Inbound identity: agents' keys and JWTs from an identity provider."""

from __future__ import annotations

import pytest
from fastmcp.server.auth.providers.jwt import RSAKeyPair

from diy_gateway.config import InboundSettings
from diy_gateway.credentials import SecretResolver
from diy_gateway.inbound import PRINCIPAL_ID, PRINCIPAL_TYPE, GatewayTokenVerifier
from tests.conftest import AGENT_KEY

ISSUER = "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_EXAMPLE"


def cognito_settings(rsa_key: RSAKeyPair) -> InboundSettings:
    return InboundSettings.model_validate(
        {
            "mode": "tokens",
            "jwt": {
                "public_key": rsa_key.public_key,
                "issuer": ISSUER,
                "principal_type": "Agent",
                "principal_claim": "client_id",
                "allowed_client_ids": ["claim-agent-client"],
                "required_claims": {"token_use": "access"},
            },
        }
    )


async def test_an_agents_key_is_its_principal():
    settings = InboundSettings.model_validate(
        {"mode": "tokens", "api_keys": [{"principal_id": "claim-agent", "secret": "env:GATEWAY_CLAIM_AGENT_KEY"}]}
    )
    verifier = GatewayTokenVerifier(settings, SecretResolver())
    token = await verifier.verify_token(AGENT_KEY)
    assert token is not None
    assert (token.claims[PRINCIPAL_TYPE], token.claims[PRINCIPAL_ID]) == ("Agent", "claim-agent")
    assert await verifier.verify_token("another-key") is None


async def test_a_cognito_client_credentials_token_names_its_app_client(rsa_key: RSAKeyPair):
    verifier = GatewayTokenVerifier(cognito_settings(rsa_key), SecretResolver())
    token = rsa_key.create_token(
        subject="claim-agent-client",
        issuer=ISSUER,
        additional_claims={"client_id": "claim-agent-client", "token_use": "access"},
    )
    verified = await verifier.verify_token(token)
    assert verified is not None
    assert verified.claims[PRINCIPAL_ID] == "claim-agent-client"


@pytest.mark.parametrize(
    "claims",
    [
        {"client_id": "some-other-client", "token_use": "access"},
        {"client_id": "claim-agent-client", "token_use": "id"},
    ],
)
async def test_another_client_or_kind_of_token_is_refused(rsa_key: RSAKeyPair, claims: dict[str, str]):
    verifier = GatewayTokenVerifier(cognito_settings(rsa_key), SecretResolver())
    token = rsa_key.create_token(subject="x", issuer=ISSUER, additional_claims=claims)
    assert await verifier.verify_token(token) is None


def token_without_expiry(rsa_key: RSAKeyPair, claims: dict[str, str]) -> str:
    import fastmcp.server.auth.providers.jwt as fastmcp_jwt  # noqa: PLC0415 - FastMCP's own signer, as create_token uses

    key = fastmcp_jwt._import_key_for_algorithm(rsa_key.private_key.get_secret_value(), "RS256")  # noqa: SLF001
    return fastmcp_jwt.jwt.encode({"alg": "RS256"}, claims, key, algorithms=["RS256"])


async def test_a_token_with_no_expiry_is_refused(rsa_key: RSAKeyPair):
    verifier = GatewayTokenVerifier(cognito_settings(rsa_key), SecretResolver())
    claims = {"sub": "x", "iss": ISSUER, "client_id": "claim-agent-client", "token_use": "access"}
    assert await verifier.verify_token(token_without_expiry(rsa_key, claims)) is None


@pytest.mark.parametrize(
    "jwt",
    [
        {"public_key": "k", "audience": "gw"},
        {"public_key": "k", "issuer": "https://idp.test"},
    ],
)
def test_jwt_settings_must_name_the_issuer_and_the_audience_or_clients(jwt: dict[str, str]):
    with pytest.raises(ValueError, match="needs"):
        InboundSettings.model_validate({"mode": "tokens", "jwt": jwt})
