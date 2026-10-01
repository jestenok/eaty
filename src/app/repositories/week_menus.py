import datetime as dt

from app.models import MENU_DAYS, WeekMenu
from core.repository import UserScopedRepository

MENU_SPAN = dt.timedelta(days=MENU_DAYS)


class WeekMenuRepository(UserScopedRepository[WeekMenu]):
    model = WeekMenu

    async def overlapping(self, start: dt.date) -> list[WeekMenu]:
        """Menus that share a day with a menu starting at `start`."""
        return await self.find(WeekMenu.start > start - MENU_SPAN, WeekMenu.start < start + MENU_SPAN,
                               order_by=[WeekMenu.start])

    async def not_over(self, since: dt.date, status: str | None = None) -> list[WeekMenu]:
        """Menus with days on or after `since`."""
        where = [WeekMenu.start > since - MENU_SPAN]
        if status:
            where.append(WeekMenu.status == status)
        return await self.find(*where, order_by=[WeekMenu.start])

    async def awaiting_order(self) -> list[WeekMenu]:
        """Newest first: an order belongs to the latest menu sent to ordering before it."""
        return await self.find(WeekMenu.status == "awaiting_order", order_by=[WeekMenu.confirmed_at.desc()])
