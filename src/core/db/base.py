from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr

from core.utils import camel_to_snake


class Base(DeclarativeBase):
    """Table name from the class name (RecipeStep -> recipe_step), constraint names
    by convention so Alembic can find them again."""

    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    })

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return camel_to_snake(cls.__name__)
