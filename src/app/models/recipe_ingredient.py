from core.db import AMOUNT, Base, CheckConstraint, ForeignKey, Mp, String, Text, mc


class RecipeIngredient(Base):
    id: Mp[int] = mc(primary_key=True)
    recipe_id: Mp[int] = mc(ForeignKey("recipe.id", ondelete="CASCADE"), index=True)
    position: Mp[int]
    name: Mp[str] = mc(Text)
    # null for spices, oil, water: not bought per recipe
    product_key: Mp[str | None] = mc(ForeignKey("product.key"))
    amount: Mp[float | None] = mc(AMOUNT)                   # in the product's base unit
    unit: Mp[str | None] = mc(String(3))
    text_amount: Mp[str] = mc(Text, server_default="")      # '1,5 ст. л.'
    note: Mp[str] = mc(Text, server_default="")

    __table_args__ = (CheckConstraint("unit in ('g', 'ml', 'pcs')", name="unit"),)
