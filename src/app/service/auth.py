"""Sign-up and sign-in.

A sign-in is a random token: the browser keeps it in an HttpOnly cookie, the Chrome
extension in its storage, the database only has its hash. Everything a user owns (plan,
pantry, Wolt orders) is reached through repositories scoped to the signed-in user.
"""

import asyncio
import datetime as dt
from collections.abc import Callable

from app.models import LoginSession
from app.repositories.login_sessions import LoginSessionRepository
from app.repositories.meal_plans import MealPlanRepository
from app.repositories.users import UserRepository
from app.schemas.auth import UserOut
from app.utils.security import hash_password, new_token, token_hash, verify_password
from core.error import ConflictError, UnauthorizedError
from core.service import BaseService


class AuthService(BaseService[UserRepository]):
    def __init__(self, repository: UserRepository, logins: LoginSessionRepository,
                 plans_of: Callable[[int], MealPlanRepository], session_days: int):
        super().__init__(repository)
        self.logins = logins
        self.plans_of = plans_of            # the new user's plan: built in the composition root
        self.session_days = session_days

    async def register(self, login: str, password: str) -> tuple[UserOut, str]:
        """A new account (the first one takes over the data from before accounts), signed in,
        with the standard week planned if it has no plan yet."""
        if await self.repository.by_login(login):
            raise ConflictError("Такой логин уже занят")
        password_hash = await asyncio.to_thread(hash_password, password)  # CPU-heavy on purpose
        user = (await self.repository.take_over_unclaimed(login, password_hash)
                or await self.repository.create(login, password_hash))
        if user is None:  # someone took the login a moment ago
            raise ConflictError("Такой логин уже занят")
        plans = self.plans_of(user.id)
        if await plans.is_empty():
            await plans.fill_from_template(dt.date.today())
        return UserOut.model_validate(user), await self._sign_in(user.id)

    async def login(self, login: str, password: str) -> tuple[UserOut, str]:
        user = await self.repository.by_login(login) if login else None
        if not await asyncio.to_thread(verify_password, password, user and user.password_hash):
            raise UnauthorizedError("Неверный логин или пароль")
        return UserOut.model_validate(user), await self._sign_in(user.id)

    async def sign_in_again(self, user_id: int) -> str:
        """One more sign-in for a signed-in user: the Chrome extension takes it from the app's
        page instead of asking for the password. A token of its own, so signing out on the site
        doesn't sign the extension out."""
        return await self._sign_in(user_id)

    async def user_for_token(self, token: str | None) -> UserOut:
        user = token and await self.logins.user_for(token_hash(token), self._now())
        if not user:
            raise UnauthorizedError("Нужно войти")
        return UserOut.model_validate(user)

    async def logout(self, token: str | None) -> None:
        if token:
            await self.logins.delete(token_hash(token))

    async def _sign_in(self, user_id: int) -> str:
        now = self._now()
        await self.logins.delete_expired(user_id, now)
        token = new_token()
        await self.logins.add(LoginSession(
            token_hash=token_hash(token), user_id=user_id, expires_at=now + dt.timedelta(days=self.session_days)))
        return token

    @staticmethod
    def _now() -> dt.datetime:
        return dt.datetime.now(dt.timezone.utc)
