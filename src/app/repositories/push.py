import datetime as dt
from collections.abc import Callable, Iterable

from sqlalchemy import Row, delete, func, select, tuple_
from sqlalchemy.dialects.postgresql import insert

from app.models import PushKey, PushSubscription, TimerAlarm
from core.repository import BaseRepository, UserScopedRepository


class PushKeyRepository(BaseRepository[PushKey]):
    model = PushKey

    async def get_or_create(self, make: Callable[[], tuple[str, str]]) -> PushKey:
        """The one key; `make` gives (private PEM, public key) when there's none yet. Two app instances
        starting at once keep the first one's."""
        key = await self.get(1)
        if key is None:
            private_key, public_key = make()
            await self.upsert(dict(id=1, private_key=private_key, public_key=public_key), conflict=("id",), update=())
            key = await self.get_one(1)
        return key


class PushSubscriptionRepository(UserScopedRepository[PushSubscription]):
    model = PushSubscription

    async def save(self, endpoint: str, p256dh: str, auth: str) -> None:
        """A browser has one endpoint: signing in to another account there moves it to that account."""
        stmt = insert(PushSubscription).values(user_id=self.user_id, endpoint=endpoint, p256dh=p256dh, auth=auth)
        await self.session.execute(stmt.on_conflict_do_update(
            index_elements=["endpoint"], set_={c: stmt.excluded[c] for c in ("user_id", "p256dh", "auth")}))

    async def remove(self, endpoint: str) -> None:
        await self.delete_where(PushSubscription.endpoint == endpoint)


class TimerAlarmRepository(UserScopedRepository[TimerAlarm]):
    model = TimerAlarm

    async def set(self, key: str, label: str, url: str, seconds: float) -> None:
        await self.upsert(dict(key=key, label=label, url=url, fire_at=func.now() + dt.timedelta(seconds=seconds)),
                          conflict=("key",))

    async def cancel(self, key: str) -> None:
        await self.delete_where(TimerAlarm.key == key)


class PushQueueRepository(BaseRepository[TimerAlarm]):
    """For the push job, across all users."""

    model = TimerAlarm

    async def take_due(self, limit: int = 100) -> list[Row]:
        """(user_id, key, label, url) of timers that are up, taken off the table. SKIP LOCKED: another app
        instance taking them at the same time gets the others."""
        due = (select(TimerAlarm.user_id, TimerAlarm.key).where(TimerAlarm.fire_at <= func.now())
               .order_by(TimerAlarm.fire_at).limit(limit).with_for_update(skip_locked=True))
        stmt = (delete(TimerAlarm).where(tuple_(TimerAlarm.user_id, TimerAlarm.key).in_(due))
                .returning(TimerAlarm.user_id, TimerAlarm.key, TimerAlarm.label, TimerAlarm.url))
        return list((await self.session.execute(stmt)).all())

    async def subscriptions(self, user_ids: Iterable[int]) -> list[PushSubscription]:
        return list(await self.session.scalars(select(PushSubscription).where(PushSubscription.user_id.in_(list(user_ids)))))

    async def forget(self, endpoints: Iterable[str]) -> None:
        await self.session.execute(delete(PushSubscription).where(PushSubscription.endpoint.in_(list(endpoints))))
