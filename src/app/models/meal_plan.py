import datetime as dt

from core.db import AMOUNT, Base, CheckConstraint, Date, DateTime, ForeignKey, Mp, String, Text, mc, relationship


class MealPlan(Base):
    user_id: Mp[int] = mc(ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True)
    day: Mp[dt.date] = mc(Date, primary_key=True)
    meal: Mp[str] = mc(String(16), primary_key=True)        # breakfast | lunch | dinner
    recipe_id: Mp[int | None] = mc(ForeignKey("recipe.id", ondelete="SET NULL"))
    multiplier: Mp[float] = mc(AMOUNT, server_default="1")  # x2 = half of it is tomorrow's lunch
    note: Mp[str] = mc(Text, server_default="")             # 'Окорочка со вчера'
    cooked_at: Mp[dt.datetime | None] = mc(DateTime(timezone=True))

    # joined: the plan is always shown with recipe titles
    recipe: Mp["Recipe | None"] = relationship(lazy="joined")

    __table_args__ = (
        CheckConstraint("meal in ('breakfast', 'lunch', 'dinner')", name="meal"),
        CheckConstraint("multiplier > 0", name="multiplier_positive"),
    )
