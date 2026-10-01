import datetime as dt

from sqlalchemy import delete, select

from app.models import LoginSession, User
from core.repository import BaseRepository


class LoginSessionRepository(BaseRepository[LoginSession]):
    model = LoginSession

    async def user_for(self, token_hash: str, now: dt.datetime) -> User | None:
        return await self.session.scalar(
            select(User).join(LoginSession).where(LoginSession.token_hash == token_hash, LoginSession.expires_at > now))

    async def delete(self, token_hash: str) -> None:
        await self.session.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash))

    async def delete_expired(self, user_id: int, now: dt.datetime) -> None:
        await self.session.execute(delete(LoginSession).where(LoginSession.user_id == user_id, LoginSession.expires_at <= now))
