"""OAuth 2.1 authorization server for the MCP server: Claude registers itself, the user lets it
in on the consent page, and Claude trades the code for tokens (PKCE checked by the MCP SDK).

Works with the MCP SDK's models; api/mcp/oauth.py adapts it to the SDK's provider protocol.
Like sign-ins, codes and tokens are stored as hashes only.
"""

import datetime as dt
import secrets

from mcp.server.auth.provider import AccessToken, AuthorizationCode, RefreshToken, TokenError
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyUrl

from app.models import OAuthClient, OAuthCode, OAuthToken as OAuthTokenRow
from app.repositories.oauth import OAuthClientRepository, OAuthCodeRepository, OAuthTokenRepository
from app.utils.security import new_token, token_hash
from core.service import BaseService

SCOPE = "eaty"                      # the one scope: everything the user can do in eaty
CODE_LIFETIME = dt.timedelta(minutes=5)


class OAuthService(BaseService[OAuthClientRepository]):
    def __init__(self, repository: OAuthClientRepository, codes: OAuthCodeRepository, tokens: OAuthTokenRepository,
                 access_lifetime: dt.timedelta, refresh_lifetime: dt.timedelta):
        super().__init__(repository)
        self.codes = codes
        self.tokens = tokens
        self.access_lifetime = access_lifetime
        self.refresh_lifetime = refresh_lifetime

    # ---------- clients ----------

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        row = await self.repository.get(client_id)
        return OAuthClientInformationFull.model_validate(row.info) if row else None

    async def register_client(self, client: OAuthClientInformationFull) -> None:
        await self.repository.add(OAuthClient(client_id=client.client_id, info=client.model_dump(mode="json")))

    # ---------- the consent page ----------

    async def grant_code(self, user_id: int, client: OAuthClientInformationFull, redirect_uri: AnyUrl,
                         redirect_uri_provided_explicitly: bool, code_challenge: str, scopes: list[str] | None,
                         resource: str | None) -> str:
        """The user said yes: a code for the app to trade for tokens (in the redirect to it)."""
        now = self._now()
        await self.codes.delete_expired(now)
        code = secrets.token_urlsafe(32)  # 256 bits
        await self.codes.add(OAuthCode(
            code_hash=token_hash(code), client_id=client.client_id, user_id=user_id, redirect_uri=str(redirect_uri),
            redirect_uri_provided_explicitly=redirect_uri_provided_explicitly, code_challenge=code_challenge,
            scopes=" ".join(scopes or self.default_scopes(client)), resource=resource, expires_at=now + CODE_LIFETIME))
        return code

    @staticmethod
    def default_scopes(client: OAuthClientInformationFull) -> list[str]:
        return client.scope.split() if client.scope else [SCOPE]

    # ---------- the token endpoint ----------

    async def load_code(self, client: OAuthClientInformationFull, code: str) -> AuthorizationCode | None:
        """The code, used up: the SDK checks it (expiry, redirect URI, PKCE) right after loading,
        and a code that failed a check must not work a second time either."""
        row = await self.codes.take(token_hash(code), client.client_id)
        if row is None:
            return None
        return AuthorizationCode(
            code=code, scopes=row.scopes.split(), expires_at=row.expires_at.timestamp(), client_id=row.client_id,
            code_challenge=row.code_challenge, redirect_uri=AnyUrl(row.redirect_uri),
            redirect_uri_provided_explicitly=row.redirect_uri_provided_explicitly, resource=row.resource,
            subject=str(row.user_id))

    async def exchange_code(self, client: OAuthClientInformationFull, code: AuthorizationCode) -> OAuthToken:
        return await self._issue(int(code.subject), client.client_id, code.scopes, code.resource)

    async def load_refresh_token(self, client: OAuthClientInformationFull, token: str) -> RefreshToken | None:
        row = await self.tokens.valid(token_hash(token), "refresh", self._now())
        if row is None or row.client_id != client.client_id:
            return None
        return RefreshToken(token=token, client_id=row.client_id, scopes=row.scopes.split(),
                            expires_at=int(row.expires_at.timestamp()), resource=row.resource, subject=str(row.user_id))

    async def exchange_refresh_token(self, client: OAuthClientInformationFull, token: RefreshToken,
                                     scopes: list[str]) -> OAuthToken:
        """New tokens for the old pair (rotation): the old refresh token stops working."""
        row = await self.tokens.valid(token_hash(token.token), "refresh", self._now())
        if row is None:  # refreshed by a parallel request a moment ago
            raise TokenError("invalid_grant", "refresh token is no longer valid")
        await self.tokens.delete_grant(row.grant)
        return await self._issue(row.user_id, client.client_id, scopes or token.scopes, token.resource)

    # ---------- the MCP server ----------

    async def load_access_token(self, token: str) -> AccessToken | None:
        row = await self.tokens.valid(token_hash(token), "access", self._now())
        if row is None:
            return None
        return AccessToken(token=token, client_id=row.client_id, scopes=row.scopes.split(),
                           expires_at=int(row.expires_at.timestamp()), resource=row.resource, subject=str(row.user_id))

    async def revoke(self, token: str) -> None:
        """Revoking either token of a pair revokes both."""
        row = await self.tokens.get(token_hash(token))
        if row is not None:
            await self.tokens.delete_grant(row.grant)

    async def _issue(self, user_id: int, client_id: str, scopes: list[str], resource: str | None) -> OAuthToken:
        now = self._now()
        await self.tokens.delete_expired(user_id, now)
        grant = secrets.token_hex(16)
        access, refresh = new_token(), new_token()
        await self.tokens.add_all([
            OAuthTokenRow(token_hash=token_hash(access), kind="access", grant=grant, client_id=client_id, user_id=user_id,
                          scopes=" ".join(scopes), resource=resource, expires_at=now + self.access_lifetime),
            OAuthTokenRow(token_hash=token_hash(refresh), kind="refresh", grant=grant, client_id=client_id,
                          user_id=user_id, scopes=" ".join(scopes), resource=resource,
                          expires_at=now + self.refresh_lifetime),
        ])
        return OAuthToken(access_token=access, expires_in=int(self.access_lifetime.total_seconds()),
                          scope=" ".join(scopes), refresh_token=refresh)

    @staticmethod
    def _now() -> dt.datetime:
        return dt.datetime.now(dt.timezone.utc)
