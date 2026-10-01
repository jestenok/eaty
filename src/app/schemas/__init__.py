from pydantic import BaseModel, ConfigDict


class BaseOrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


__all__ = ["BaseOrmModel"]
