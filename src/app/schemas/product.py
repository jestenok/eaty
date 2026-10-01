import re

from pydantic import BaseModel, Field, field_validator

from app.schemas import BaseOrmModel
from app.schemas.recipe import Unit


class ProductOut(BaseOrmModel):
    key: str
    name: str
    base_unit: str
    venue_slug: str
    search_q: str
    match_re: str
    exclude_re: str


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    base_unit: Unit                                         # recipes and the pantry count it in this unit
    venue_slug: str = Field(min_length=1, max_length=100)   # the Wolt store it's bought in
    search_q: str = Field(min_length=1, max_length=100)     # query for the Wolt catalog search
    match_re: str = Field(min_length=1, max_length=500)     # item names that count as this product
    exclude_re: str = Field("", max_length=500)

    @field_validator("match_re", "exclude_re")
    @classmethod
    def compiles(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(f"неправильное регулярное выражение: {exc}") from exc
        return value
