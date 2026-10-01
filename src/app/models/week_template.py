from core.db import AMOUNT, Base, CheckConstraint, ForeignKey, Integer, Mp, String, Text, mc


class WeekTemplate(Base):
    """The standard week: what «Заполнить пустые дни» plans on day N (0–6) from the start."""

    day_offset: Mp[int] = mc(Integer, primary_key=True)
    meal: Mp[str] = mc(String(16), primary_key=True)        # breakfast | lunch | dinner
    recipe_id: Mp[int | None] = mc(ForeignKey("recipe.id", ondelete="SET NULL"))
    multiplier: Mp[float] = mc(AMOUNT, server_default="1")
    note: Mp[str] = mc(Text, server_default="")             # 'Окорочка со вчера'

    __table_args__ = (
        CheckConstraint("day_offset between 0 and 6", name="day_offset"),
        CheckConstraint("meal in ('breakfast', 'lunch', 'dinner')", name="meal"),
        CheckConstraint("multiplier > 0", name="multiplier_positive"),
    )
