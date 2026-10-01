from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Path, Query

from api.dependencies import PushJobDep, PushServiceDep
from app.schemas.push import PushKeyOut, PushSubscriptionIn, TimerAlarmIn

router = APIRouter()

TimerKey = Annotated[str, Path(max_length=100)]


@router.get("/key", summary="Ключ приложения (VAPID): с ним браузер подписывается на уведомления",
            response_model=PushKeyOut)
async def key(service: PushServiceDep):
    return service.key()


@router.put("/subscription", status_code=204, summary="Этот браузер разрешил уведомления")
async def subscribe(service: PushServiceDep, subscription: PushSubscriptionIn):
    await service.subscribe(subscription)


@router.delete("/subscription", status_code=204, summary="Этот браузер больше не ждёт уведомлений")
async def unsubscribe(service: PushServiceDep, endpoint: Annotated[str, Query(max_length=2000)]):
    await service.unsubscribe(endpoint)


@router.put("/timers/{key}", status_code=204, summary="Таймер идёт: прислать «Готово!», когда выйдет время")
async def set_timer(service: PushServiceDep, job: PushJobDep, background: BackgroundTasks, key: TimerKey,
                    timer: TimerAlarmIn):
    await service.set_timer(key, timer)
    background.add_task(job.wake)   # once committed: a short timer goes now, not on the next round


@router.delete("/timers/{key}", status_code=204, summary="Таймер остановлен или на паузе: не присылать")
async def cancel_timer(service: PushServiceDep, key: TimerKey):
    await service.cancel_timer(key)
