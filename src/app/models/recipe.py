from core.db import ARRAY, Base, CheckConstraint, Integer, Mp, String, Text, mc, relationship


class Recipe(Base):
    id: Mp[int] = mc(primary_key=True)
    slug: Mp[str] = mc(String(64), unique=True)
    title: Mp[str] = mc(Text)
    portions: Mp[int] = mc(Integer, server_default="2")
    category: Mp[str] = mc(String(16), server_default="main")    # breakfast | soup | main | salad | snack | dessert
    appliance: Mp[str] = mc(String(16), server_default="stove")   # stove | air_fryer | none
    batch_note: Mp[str] = mc(Text, server_default="")             # what to do when cooking it x2
    # meals it fits when a week menu is put together: breakfast | lunch | dinner
    meals: Mp[list[str]] = mc(ARRAY(String(16)), server_default="{lunch,dinner}")

    # selectin: a recipe is always shown with its ingredients and steps, and lazy loading
    # in an async session would raise MissingGreenlet
    ingredients: Mp[list["RecipeIngredient"]] = relationship(
        order_by="RecipeIngredient.position", cascade="all, delete-orphan", lazy="selectin")
    steps: Mp[list["RecipeStep"]] = relationship(
        order_by="RecipeStep.position", cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        CheckConstraint("appliance in ('stove', 'air_fryer', 'none')", name="appliance"),
        CheckConstraint("category in ('breakfast', 'soup', 'main', 'salad', 'snack', 'dessert')", name="category"),
        # an empty list: not picked into week menus on its own (side salads, desserts)
        CheckConstraint("meals <@ array['breakfast', 'lunch', 'dinner']::varchar[]", name="meals"),
    )
