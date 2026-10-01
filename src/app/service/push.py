"""Timers that ring on a locked phone: when a step's timer is up, the server pushes «Готово!» to the
user's browsers that allowed notifications (on an iPhone: eaty added to the home screen)."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from app.clients.web_push import PushTarget, is_push_service, new_vapid_key
from app.models import PushKey
from app.repositories.push import PushKeyRepository, PushQueueRepository, PushSubscriptionRepository, TimerAlarmRepository
from app.schemas.push import PushKeyOut, PushSubscriptionIn, TimerAlarmIn
from core.db import Database
from core.error import AppError
from core.service import BaseService

log = logging.getLogger(__name__)

Send = Callable[[PushTarget, dict[str, Any]], Awaitable[bool]]


async def load_push_key(database: Database) -> PushKey:
    """The app's VAPID key, made on the very first start (its own transaction)."""
    async with database.transaction() as session:
        return await PushKeyRepository(session).get_or_create(new_vapid_key)


class PushService(BaseService[PushSubscriptionRepository]):
    def __init__(self, repository: PushSubscriptionRepository, alarms: TimerAlarmRepository, public_key: str):
        super().__init__(repository)
        self.alarms = alarms
        self.public_key = public_key

    def key(self) -> PushKeyOut:
        return PushKeyOut(public_key=self.public_key)

    async def subscribe(self, subscription: PushSubscriptionIn) -> None:
        if not is_push_service(subscription.endpoint):
            raise AppError("Это не адрес для уведомлений браузера")
        await self.repository.save(subscription.endpoint, subscription.keys.p256dh, subscription.keys.auth)

    async def unsubscribe(self, endpoint: str) -> None:
        await self.repository.remove(endpoint)

    async def set_timer(self, key: str, timer: TimerAlarmIn) -> None:
        await self.alarms.set(key, timer.label, timer.url, timer.seconds)

    async def cancel_timer(self, key: str) -> None:
        await self.alarms.cancel(key)


class TimerPushJob:
    """Every `poll` seconds, and right away when woken (a timer was just set), sends the pushes for timers
    that are up. Owns its transactions: a timer is taken off the table in one, the subscriptions that turned
    out to be gone are forgotten in another; the sending itself is outside any."""

    def __init__(self, database: Database, send: Send, poll: float):
        self.database = database
        self.send = send
        self.poll = poll
        self.task: asyncio.Task | None = None
        self.woken = asyncio.Event()

    def start(self) -> None:
        if self.poll > 0 and self.task is None:
            self.task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self.task is not None:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
            self.task = None

    def wake(self) -> None:
        self.woken.set()

    async def _run(self) -> None:
        while True:
            try:
                await self.run_once()
            except Exception:  # the next round tries again; timers stay in the table until sent
                log.exception("Пуши таймеров: круг упал")
            try:
                await asyncio.wait_for(self.woken.wait(), self.poll)
            except TimeoutError:
                pass
            self.woken.clear()

    async def run_once(self) -> int:
        """Sends what's due; how many messages it sent (to the user's every browser that allowed them)."""
        async with self.database.transaction() as session:
            queue = PushQueueRepository(session)
            due = await queue.take_due()
            subscriptions = await queue.subscriptions({row.user_id for row in due}) if due else []
        messages = [(PushTarget(s.endpoint, s.p256dh, s.auth),
                     {"title": "Готово!", "body": row.label, "tag": f"timer:{row.key}", "url": row.url})
                    for row in due for s in subscriptions if s.user_id == row.user_id]
        alive = await asyncio.gather(*(self._send(target, payload) for target, payload in messages))
        gone = {target.endpoint for (target, _), ok in zip(messages, alive) if not ok}
        if gone:
            async with self.database.transaction() as session:
                await PushQueueRepository(session).forget(gone)
        return len(messages)

    async def _send(self, target: PushTarget, payload: dict[str, Any]) -> bool:
        try:
            return await self.send(target, payload)
        except (httpx.HTTPError, ValueError) as exc:   # a push service hiccup: the subscription stays
            log.warning("Пуш таймера не ушёл (%s): %s", target.endpoint.split("/")[2], exc)
            return True
