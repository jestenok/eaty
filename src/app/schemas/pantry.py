from pydantic import BaseModel, Field


class PantryItemOut(BaseModel):
    key: str
    name: str
    base_unit: str
    have: float
    have_text: str


class PantryLevelIn(BaseModel):
    amount: float = Field(ge=0)
