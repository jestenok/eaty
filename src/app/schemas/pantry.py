from typing import Annotated

from pydantic import BaseModel, Field


class PantryItemOut(BaseModel):
    key: str
    name: str
    base_unit: str
    have: float
    have_text: str
    # «Всегда дома»: pinned products show up on top, and the ones that ran out (or fell below the
    # least to keep) are what to buy
    pinned: bool = False
    min_amount: float | None = None
    min_text: str = ""
    missing: bool = False


class PantryLevelIn(BaseModel):
    amount: float = Field(ge=0)


class PantryPinIn(BaseModel):
    """Keep this product at home; with min_amount it counts as missing below that, not only when it's out."""

    min_amount: float | None = Field(None, gt=0)


class UsedItemOut(BaseModel):
    """A product written off for a cooked meal."""

    key: str
    name: str
    base_unit: str
    amount: float
    amount_text: str


class UsedIn(BaseModel):
    """What a cooked meal really took, in base units; products left out or at 0 aren't written off."""

    amounts: dict[str, Annotated[float, Field(ge=0)]]
