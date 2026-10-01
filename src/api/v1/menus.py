import datetime as dt

from fastapi import APIRouter

from api.dependencies import MenuServiceDep
from app.schemas.menu import MenuIn, MenuOrderOut, MenuOut, MenuStatus, MenuStatusIn
from app.schemas.plan import Meal

router = APIRouter()


@router.get("", summary="Меню на неделю, которые ещё не закончились", response_model=list[MenuOut])
async def active_menus(service: MenuServiceDep, since: dt.date | None = None, status: MenuStatus | None = None):
    return await service.active(since or dt.date.today(), status)


@router.post("", summary="Накидать меню на неделю из рецептов (черновик на этих днях — заново); "
                         "from_home — только из того, что дома", response_model=MenuOut)
async def create_menu(service: MenuServiceDep, dto: MenuIn):
    return await service.create(dto.start, dto.from_home)


@router.get("/{menu_id}", summary="Меню на неделю", response_model=MenuOut)
async def get_menu(service: MenuServiceDep, menu_id: int):
    return await service.get(menu_id)


@router.post("/{menu_id}/{day}/{meal}/swap", summary="Заменить рецепт в черновике на другой (или подобрать на пустое место)",
             response_model=MenuOut)
async def swap_meal(service: MenuServiceDep, menu_id: int, day: dt.date, meal: Meal):
    return await service.swap(menu_id, day, meal)


@router.put("/{menu_id}/status", summary="Черновик → ждёт заказа → заказано (и на шаг назад)", response_model=MenuOut)
async def set_status(service: MenuServiceDep, menu_id: int, dto: MenuStatusIn):
    return await service.set_status(menu_id, dto.status)


@router.get("/{menu_id}/order", summary="Что заказать в Wolt по меню: корзины по магазинам и задание для Claude",
            response_model=MenuOrderOut)
async def menu_order(service: MenuServiceDep, menu_id: int, today: dt.date | None = None):
    return await service.order(menu_id, today or dt.date.today())
