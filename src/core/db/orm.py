"""Short names for models and repositories, as in the other services."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    delete,
    func,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Mapped as Mp
from sqlalchemy.orm import mapped_column as mc
from sqlalchemy.orm import relationship

# grams / millilitres / pieces: exact in the database, float in Python
AMOUNT = Numeric(asdecimal=False)

__all__ = [
    "AMOUNT", "Boolean", "CheckConstraint", "Date", "DateTime", "ForeignKey", "Index", "Integer", "JSONB",
    "Mp", "Numeric", "String", "Text", "delete", "func", "insert", "mc", "relationship", "select", "text", "update",
]
