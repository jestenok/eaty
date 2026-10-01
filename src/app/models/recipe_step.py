from core.db import Base, CheckConstraint, ForeignKey, Mp, Text, mc


class RecipeStep(Base):
    id: Mp[int] = mc(primary_key=True)
    recipe_id: Mp[int] = mc(ForeignKey("recipe.id", ondelete="CASCADE"), index=True)
    position: Mp[int]
    text: Mp[str] = mc(Text)
    timer_seconds: Mp[int | None]
    heat: Mp[str] = mc(Text, server_default="")             # 'средний огонь', '190 °C'

    __table_args__ = (CheckConstraint("timer_seconds > 0", name="timer_positive"),)
