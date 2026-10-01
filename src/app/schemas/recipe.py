from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas import BaseOrmModel

Category = Literal["breakfast", "soup", "main", "salad", "snack", "dessert"]
Appliance = Literal["stove", "air_fryer", "none"]
Unit = Literal["g", "ml", "pcs"]


class RecipeShortOut(BaseOrmModel):
    id: int
    slug: str
    title: str
    category: str
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


class IngredientIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    # a product bought in Wolt: goes into the shopping list and the pantry; null for oil, salt, spices
    product_key: str | None = None
    amount: float | None = Field(None, gt=0)    # in the product's base unit
    unit: Unit | None = None
    text_amount: str = Field("", max_length=60)  # '1,5 ст. л.', 'по вкусу'
    note: str = Field("", max_length=100)

    @model_validator(mode="after")
    def has_amount(self) -> "IngredientIn":
        if (self.amount is None) != (self.unit is None):
            raise ValueError("amount и unit указываются вместе")
        if self.product_key and self.amount is None:
            raise ValueError(f"{self.name}: для продукта из магазина нужны amount и unit")
        if self.amount is None and not self.text_amount:
            raise ValueError(f"{self.name}: укажи amount и unit или text_amount")
        return self


class StepIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    timer_seconds: int | None = Field(None, gt=0, le=24 * 3600)
    heat: str = Field("", max_length=50)       # 'средний огонь', '190 °C'


class RecipeIn(BaseModel):
    """A whole recipe for 2 portions; the same shape as RecipeOut, so GET → edit → PUT works."""

    slug: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    title: str = Field(min_length=1, max_length=200)
    category: Category = "main"
    appliance: Appliance = "stove"
    batch_note: str = Field("", max_length=500)
    ingredients: list[IngredientIn] = Field(min_length=1)
    steps: list[StepIn] = Field(min_length=1)
