from app.schemas import BaseOrmModel


class RecipeShortOut(BaseOrmModel):
    id: int
    slug: str
    title: str
    appliance: str


class IngredientOut(BaseOrmModel):
    name: str
    product_key: str | None
    amount: float | None
    unit: str | None
    text_amount: str
    note: str
    have: float | None = None   # at home, in the product's base unit


class StepOut(BaseOrmModel):
    position: int
    text: str
    timer_seconds: int | None
    heat: str


class RecipeOut(RecipeShortOut):
    portions: int
    batch_note: str
    ingredients: list[IngredientOut]
    steps: list[StepOut]
