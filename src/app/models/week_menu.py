import datetime as dt

from core.db import Base, CheckConstraint, Date, DateTime, Mp, String, func, mc

MENU_DAYS = 7


class WeekMenu(Base):
    """A week of meals picked from the recipes, on its way to the kitchen:
    draft (recipes are still being swapped) -> awaiting_order (the shopping list goes to Wolt)
    -> ordered (the orders came back through the extension). The meals themselves are
    MealPlan rows of the menu's days."""

    id: Mp[int] = mc(primary_key=True)
    start: Mp[dt.date] = mc(Date, unique=True)
    status: Mp[str] = mc(String(16), server_default="draft")
    created_at: Mp[dt.datetime] = mc(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mp[dt.datetime | None] = mc(DateTime(timezone=True))   # went to ordering
    ordered_at: Mp[dt.datetime | None] = mc(DateTime(timezone=True))

    __table_args__ = (CheckConstraint("status in ('draft', 'awaiting_order', 'ordered')", name="status"),)

    @property
    def end(self) -> dt.date:
        """The day after the menu's last day."""
        return self.start + dt.timedelta(days=MENU_DAYS)
