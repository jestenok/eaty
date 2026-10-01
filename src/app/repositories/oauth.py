import datetime as dt

from sqlalchemy import delete, select

from app.models import OAuthClient, OAuthCode, OAuthToken
from core.repository import BaseRepository


class OAuthClientRepository(BaseRepository[OAuthClient]):
    model = OAuthClient


class OAuthCodeRepository(BaseRepository[OAuthCode]):
    model = OAuthCode

    async def take(self, code_hash: str, client_id: str) -> OAuthCode | None:
        """The code, deleted on the way: a code is good for one exchange only."""
        return await self.session.scalar(
            delete(OAuthCode).where(OAuthCode.code_hash == code_hash, OAuthCode.client_id == client_id)
            .returning(OAuthCode))

    async def delete_expired(self, now: dt.datetime) -> None:
        await self.session.execute(delete(OAuthCode).where(OAuthCode.expires_at <= now))


class OAuthTokenRepository(BaseRepository[OAuthToken]):
    model = OAuthToken

    async def valid(self, token_hash: str, kind: str, now: dt.datetime) -> OAuthToken | None:
        return await self.session.scalar(select(OAuthToken).where(
            OAuthToken.token_hash == token_hash, OAuthToken.kind == kind, OAuthToken.expires_at > now))

    async def delete_grant(self, grant: str) -> None:
        await self.session.execute(delete(OAuthToken).where(OAuthToken.grant == grant))

    async def delete_expired(self, user_id: int, now: dt.datetime) -> None:
        await self.session.execute(delete(OAuthToken).where(OAuthToken.user_id == user_id, OAuthToken.expires_at <= now))
