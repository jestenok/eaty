"""Week menus: put one together from the recipes, swap what you don't like, send it to
ordering, and see it ordered when the Wolt orders come back through the extension."""

import datetime as dt
import random

from app.models import MENU_DAYS, MealPlan, WeekMenu, WoltOrder
from app.repositories.meal_plans import MealPlanRepository
from app.repositories.recipes import RecipeRepository
from app.repositories.week_menus import WeekMenuRepository
from app.repositories.wolt_orders import WoltOrderRepository
from app.schemas.menu import MenuMealOut, MenuOrderLinkOut, MenuOrderOut, MenuOut, MenuStatus
from app.schemas.plan import Meal
from app.service import menu_builder as builder
from app.service.order_task import order_task, period
from app.service.plan import plan_row_out
from app.service.shopping import ShoppingService
from core.error import ConflictError, NotFoundError
from core.service import BaseService

STATUS_NAMES = {"draft": "черновик", "awaiting_order": "ждёт заказа", "ordered": "заказано"}
# draft <-> awaiting_order <-> ordered: going back is always one step
TRANSITIONS = {("draft", "awaiting_order"), ("awaiting_order", "draft"),
               ("awaiting_order", "ordered"), ("ordered", "awaiting_order")}


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class MenuService(BaseService[WeekMenuRepository]):
    def __init__(self, repository: WeekMenuRepository, plans: MealPlanRepository, recipes: RecipeRepository,
                 orders: WoltOrderRepository, shopping: ShoppingService, rng: random.Random):
        super().__init__(repository)
        self.plans = plans
        self.recipes = recipes
        self.orders = orders
        self.shopping = shopping
        self.rng = rng

    async def active(self, since: dt.date, status: MenuStatus | None = None) -> list[MenuOut]:
        return [await self._out(m) for m in await self.repository.not_over(since, status)]

    async def get(self, menu_id: int) -> MenuOut:
        return await self._out(await self.repository.get_one(menu_id))

    async def create(self, start: dt.date) -> MenuOut:
        """A new draft for the 7 days from `start`. A draft on these days is put together anew;
        meals already cooked stay as they are."""
        overlapping = await self.repository.overlapping(start)
        if busy := [m for m in overlapping if m.status != "draft"]:
            m = busy[0]
            raise ConflictError(
                f"На {period(m.start, m.end - dt.timedelta(days=1))} уже есть меню, оно {STATUS_NAMES[m.status]}. "
                f"Начни новое с {m.end:%d.%m} или верни то в черновик.")
        menu = next((m for m in overlapping if m.start == start), None) or WeekMenu(start=start)
        if others := [m.id for m in overlapping if m is not menu]:
            await self.repository.delete_where(WeekMenu.id.in_(others))

        dishes = await self._dishes()
        eve = await self.plans.get(start - builder.ONE_DAY, "dinner")
        week = builder.build_week(dishes, start, self.rng, MENU_DAYS, before=eve and self._slot(eve, dishes))
        await self.plans.clear_uncooked(start, MENU_DAYS)
        await self.plans.insert_missing([self._row(s) for s in week])   # cooked meals stay
        menu.created_at = now()
        await self.repository.add(menu)
        await self._reread(menu)
        return await self._out(menu)

    async def swap(self, menu_id: int, day: dt.date, meal: Meal) -> MenuOut:
        """Another recipe for this meal (didn't like it)."""
        menu = await self.repository.get_one(menu_id)
        if menu.status != "draft":
            raise ConflictError("Меню уже утверждено: верни его в черновик, чтобы менять рецепты")
        if not menu.start <= day < menu.end:
            raise NotFoundError(f"В меню с {menu.start:%d.%m} нет дня {day:%d.%m}")
        dishes = await self._dishes()
        week = [self._slot(p, dishes) for p in await self.plans.between(menu.start, MENU_DAYS)]
        slot = next((s for s in week if (s.day, s.meal) == (day, meal)), None)
        if slot is None or slot.dish is None:
            raise ConflictError("Здесь нет рецепта: это остатки ужина или пусто — поменяй ужин накануне")
        if slot.cooked:
            raise ConflictError("Это уже приготовлено")
        changed = builder.swap(week, slot, dishes, self.rng)
        if changed is None:
            raise ConflictError("Заменить не на что: других рецептов для этого приёма пищи нет")
        await self.plans.upsert([self._row(s) for s in changed], conflict=["day", "meal"],
                                update=["recipe_id", "multiplier", "note"])
        await self._reread(menu)
        return await self._out(menu)

    async def set_status(self, menu_id: int, status: MenuStatus) -> MenuOut:
        menu = await self.repository.get_one(menu_id)
        if menu.status != status:
            if (menu.status, status) not in TRANSITIONS:
                raise ConflictError(f"Из «{STATUS_NAMES[menu.status]}» сразу в «{STATUS_NAMES[status]}» нельзя")
            if status == "awaiting_order" and menu.status == "draft":
                menu.confirmed_at = now()       # orders placed from now on are this menu's
            menu.ordered_at = now() if status == "ordered" else None
            if status == "draft":
                menu.confirmed_at = None
            menu.status = status
        return await self._out(menu)

    async def order(self, menu_id: int, today: dt.date) -> MenuOrderOut:
        """What to buy so that everything planned from today to the menu's last day is at home:
        the plan's needs minus what's at home, by store."""
        menu = await self.repository.get_one(menu_id)
        last_day = menu.end - builder.ONE_DAY
        first_day = min(max(today, menu.start), last_day)
        shopping = await self.shopping.build(today, max((menu.end - today).days, 0))
        return MenuOrderOut(menu_id=menu.id, status=menu.status, first_day=first_day, last_day=last_day,
                            shopping=shopping, task=order_task(first_day, last_day, shopping))

    async def take_orders(self, orders: list[tuple[str, dt.datetime | None]], today: dt.date) -> int:
        """Orders the extension brought go to the latest menu sent to ordering before they were
        placed. A menu whose orders cover everything it needs is ordered. Returns how many."""
        menus = await self.repository.awaiting_order()
        if not menus:
            return 0
        by_menu: dict[int, list[str]] = {}
        for order_id, placed_at in orders:
            menu = next((m for m in menus if m.confirmed_at <= (placed_at or now())), None)
            if menu:
                by_menu.setdefault(menu.id, []).append(order_id)
        for menu_id, ids in by_menu.items():
            await self.orders.link_to_menu(ids, menu_id)

        ordered = 0
        for menu in menus:
            if not await self.orders.exists(WoltOrder.week_menu_id == menu.id):
                continue
            left = await self.shopping.build(today, max((menu.end - today).days, 0))
            if not left.stores:
                menu.status, menu.ordered_at = "ordered", now()
                ordered += 1
        return ordered

    async def _dishes(self) -> list[builder.Dish]:
        return [builder.Dish(r.id, r.title, frozenset(r.meals), batch=bool(r.batch_note))
                for r in await self.recipes.all()]

    @staticmethod
    def _slot(p: MealPlan, dishes: list[builder.Dish]) -> builder.Slot:
        dish = next((d for d in dishes if d.id == p.recipe_id), None)
        return builder.Slot(p.day, p.meal, dish, p.multiplier, p.note, cooked=p.cooked_at is not None)

    @staticmethod
    def _row(s: builder.Slot) -> dict:
        return dict(day=s.day, meal=s.meal, recipe_id=s.dish and s.dish.id, multiplier=s.multiplier, note=s.note)

    async def _reread(self, menu: WeekMenu) -> None:
        """After plan rows were written with UPSERTs, which bypass the identity map: flush and
        expire everything, so the rows are read again as they are now in this transaction."""
        session = self.repository.session
        await session.flush()
        session.expire_all()
        await session.refresh(menu)

    async def _out(self, menu: WeekMenu) -> MenuOut:
        draft = menu.status == "draft"
        meals = [MenuMealOut(**plan_row_out(p).model_dump(), swappable=draft and p.recipe_id is not None and not p.cooked_at)
                 for p in await self.plans.between(menu.start, MENU_DAYS)]
        orders = [MenuOrderLinkOut.model_validate(o) for o in await self.orders.of_menu(menu.id)]
        return MenuOut(id=menu.id, start=menu.start, last_day=menu.end - builder.ONE_DAY, status=menu.status,
                       created_at=menu.created_at, confirmed_at=menu.confirmed_at, ordered_at=menu.ordered_at,
                       meals=meals, orders=orders)
