"""OAuth for MCP clients (Claude): an app registers itself, the user lets it in on the consent
page, and it gets tokens to call eaty's MCP server as that user. Codes and tokens are stored
as hashes only, like sign-ins."""

import datetime as dt

from core.db import JSONB, Base, Boolean, DateTime, ForeignKey, Mp, String, Text, func, mc


class OAuthClient(Base):
    """An app that registered itself (RFC 7591 dynamic client registration): Claude in the
    browser, Claude Desktop, Claude Code. `info` is its registration as the MCP SDK models it."""

    __tablename__ = "oauth_client"  # not "o_auth_client"

    client_id: Mp[str] = mc(String(64), primary_key=True)
    info: Mp[dict] = mc(JSONB)
    created_at: Mp[dt.datetime] = mc(DateTime(timezone=True), server_default=func.now())


class OAuthCode(Base):
    """An authorization code: what the consent page hands the app to trade for tokens, once."""

    __tablename__ = "oauth_code"

    code_hash: Mp[str] = mc(String(64), primary_key=True)  # sha256, hex
    client_id: Mp[str] = mc(ForeignKey("oauth_client.client_id", ondelete="CASCADE"))
    user_id: Mp[int] = mc(ForeignKey("app_user.id", ondelete="CASCADE"))
    redirect_uri: Mp[str] = mc(Text)
    redirect_uri_provided_explicitly: Mp[bool] = mc(Boolean)
    code_challenge: Mp[str] = mc(String(128))              # PKCE, S256
    scopes: Mp[str] = mc(Text)                             # space-separated
    resource: Mp[str | None] = mc(Text)                    # RFC 8707: the MCP server's URL
    expires_at: Mp[dt.datetime] = mc(DateTime(timezone=True))


class OAuthToken(Base):
    """An access or refresh token. Tokens issued together share a `grant`: a refresh replaces
    the whole grant, and revoking either token revokes both."""

    __tablename__ = "oauth_token"

    token_hash: Mp[str] = mc(String(64), primary_key=True)  # sha256, hex
    kind: Mp[str] = mc(String(16))                          # 'access' | 'refresh'
    grant: Mp[str] = mc(String(64), index=True)
    client_id: Mp[str] = mc(ForeignKey("oauth_client.client_id", ondelete="CASCADE"))
    user_id: Mp[int] = mc(ForeignKey("app_user.id", ondelete="CASCADE"), index=True)
    scopes: Mp[str] = mc(Text)
    resource: Mp[str | None] = mc(Text)
    created_at: Mp[dt.datetime] = mc(DateTime(timezone=True), server_default=func.now())
    expires_at: Mp[dt.datetime] = mc(DateTime(timezone=True))
