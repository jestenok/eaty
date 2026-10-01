from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from app.models import User
from core.repository import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def by_login(self, login: str) -> User | None:
        return await self.session.scalar(select(User).where(User.login == login))

    async def create(self, login: str, password_hash: str) -> User | None:
        """A new account; None if the login is taken."""
        user_id = await self.session.scalar(
            insert(User).values(login=login, password_hash=password_hash).on_conflict_do_nothing().returning(User.id))
        return user_id and await self.get(user_id)

    async def take_over_unclaimed(self, login: str, password_hash: str) -> User | None:
        """The account holding the data from before sign-ups, if nobody has taken it yet.
        One UPDATE, so two sign-ups at once can't both get it."""
        user_id = await self.session.scalar(
            update(User).where(User.login == "").values(login=login, password_hash=password_hash).returning(User.id))
        return user_id and await self.get(user_id)
