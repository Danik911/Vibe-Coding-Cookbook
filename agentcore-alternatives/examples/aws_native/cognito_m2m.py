"""An agent's machine identity from Amazon Cognito (OAuth client credentials), for a gateway
whose inbound auth is `jwt` instead of IAM. Cognito is generally available, unlike AgentCore Identity.

Cognito's access tokens carry `client_id` and `token_use`, not `aud`, so the gateway checks those:

  inbound:
    mode: tokens
    jwt:
      jwks_uri: https://cognito-idp.<region>.amazonaws.com/<pool-id>/.well-known/jwks.json
      issuer: https://cognito-idp.<region>.amazonaws.com/<pool-id>
      principal_type: Agent
      principal_claim: client_id
      allowed_client_ids: [<the claim agent's app client id>]
      required_claims: {token_use: access}

Run: uv run --env-file .env examples/aws_native/cognito_m2m.py
with COGNITO_DOMAIN (https://<prefix>.auth.<region>.amazoncognito.com), COGNITO_CLIENT_ID,
COGNITO_CLIENT_SECRET and COGNITO_SCOPES (such as "undercover-gateway/tools") in .env.
"""

from __future__ import annotations

import asyncio
import os
import time

import httpx2
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

EXPIRY_MARGIN_SECONDS = 60
_token: dict[str, float | str] = {}


def access_token() -> str:
    """A client-credentials token, reused until a minute before it expires (Cognito bills each request)."""
    if _token and float(_token["expires"]) - EXPIRY_MARGIN_SECONDS > time.time():
        return str(_token["value"])
    response = httpx2.post(
        f"{os.environ['COGNITO_DOMAIN']}/oauth2/token",
        data={"grant_type": "client_credentials", "scope": os.environ["COGNITO_SCOPES"]},
        auth=(os.environ["COGNITO_CLIENT_ID"], os.environ["COGNITO_CLIENT_SECRET"]),
        timeout=10,
    )
    response.raise_for_status()
    body = response.json()
    _token.update(value=body["access_token"], expires=time.time() + body["expires_in"])
    return body["access_token"]


async def main() -> None:
    gateway = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8210/mcp")
    async with Client(StreamableHttpTransport(gateway, auth=access_token())) as client:
        print([tool.name for tool in await client.list_tools()])


if __name__ == "__main__":
    asyncio.run(main())
