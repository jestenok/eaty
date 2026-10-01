"""The MCP SDK's OAuth endpoints (/register, /authorize, /token, /revoke) on eaty's accounts.

The SDK calls the provider outside any request of ours, so every call is its own unit of work,
like a background job's.
"""

from collections.abc import Callable
from urllib.parse import urlencode

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from sqlalchemy.ext.asyncio import AsyncSession

from app.service.oauth import OAuthService
from core.db import Database

CONSENT_PATH = "/oauth/consent"


def consent_query(client_id: str, params: AuthorizationParams) -> str:
    """The authorization request, carried to the consent page in its URL. Safe to show: the page
    checks the client and redirect URI again, and the code is bound to the PKCE challenge."""
    query = {"client_id": client_id, "redirect_uri": str(params.redirect_uri),
             "explicit": "1" if params.redirect_uri_provided_explicitly else "0",
             "code_challenge": params.code_challenge, "state": params.state,
             "scope": " ".join(params.scopes) if params.scopes else None, "resource": params.resource}
    return urlencode({k: v for k, v in query.items() if v is not None})


class EatyOAuthProvider(OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]):
    def __init__(self, database: Database, service: Callable[[AsyncSession], OAuthService], public_url: str):
        self.database = database
        self.service = service              # built per transaction: see oauth_service_factory
        self.consent_url = public_url.rstrip("/") + CONSENT_PATH

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        async with self.database.transaction() as session:
            return await self.service(session).get_client(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        async with self.database.transaction() as session:
            await self.service(session).register_client(client_info)

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        """Off to the consent page: sign in there if needed, then allow or deny."""
        return f"{self.consent_url}?{consent_query(client.client_id, params)}"

    async def load_authorization_code(self, client: OAuthClientInformationFull,
                                      authorization_code: str) -> AuthorizationCode | None:
        async with self.database.transaction() as session:
            return await self.service(session).load_code(client, authorization_code)

    async def exchange_authorization_code(self, client: OAuthClientInformationFull,
                                          authorization_code: AuthorizationCode) -> OAuthToken:
        async with self.database.transaction() as session:
            return await self.service(session).exchange_code(client, authorization_code)

    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str) -> RefreshToken | None:
        async with self.database.transaction() as session:
            return await self.service(session).load_refresh_token(client, refresh_token)

    async def exchange_refresh_token(self, client: OAuthClientInformationFull, refresh_token: RefreshToken,
                                     scopes: list[str]) -> OAuthToken:
        async with self.database.transaction() as session:
            return await self.service(session).exchange_refresh_token(client, refresh_token, scopes)

    async def load_access_token(self, token: str) -> AccessToken | None:
        async with self.database.transaction() as session:
            return await self.service(session).load_access_token(token)

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        async with self.database.transaction() as session:
            await self.service(session).revoke(token.token)
