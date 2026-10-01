import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Query

from api.dependencies import PlanServiceDep
from app.schemas.plan import CookedIn, Meal, PlanRowIn, PlanRowOut, WeekIn

router = APIRouter()


@router.get("", summary="План питания на несколько дней", response_model=list[PlanRowOut])
async def get_plan(service: PlanServiceDep, start: dt.date | None = None, days: Annotated[int, Query(ge=1, le=31)] = 7):
    return await service.get(start or dt.date.today(), days)


@router.put("/{day}/{meal}", summary="Что готовим в этот приём пищи", response_model=list[PlanRowOut])
async def set_meal(service: PlanServiceDep, day: dt.date, meal: Meal, dto: PlanRowIn):
    return await service.set_meal(day, meal, dto)


@router.post("/week", summary="Заполнить пустые дни недели стандартным меню", response_model=list[PlanRowOut])
async def fill_week(service: PlanServiceDep, dto: WeekIn):
    return await service.fill_week(dto.start)


@router.post("/{day}/{meal}/cooked", summary="Отметить приготовленным (списывает продукты)", response_model=list[PlanRowOut])
async def set_cooked(service: PlanServiceDep, day: dt.date, meal: Meal, dto: CookedIn):
    return await service.set_cooked(day, meal, dto.cooked)
