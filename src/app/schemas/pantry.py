from typing import Annotated

from pydantic import BaseModel, Field


class PantryItemOut(BaseModel):
    key: str
    name: str
    base_unit: str
    have: float
    have_text: str


class PantryLevelIn(BaseModel):
    amount: float = Field(ge=0)


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
