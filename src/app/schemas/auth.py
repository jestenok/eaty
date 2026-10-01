from pydantic import BaseModel, Field, field_validator

from app.schemas import BaseOrmModel


class _Credentials(BaseModel):
    @field_validator("login", mode="before", check_fields=False)
    @classmethod
    def normalize_login(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class SignUpIn(_Credentials):
    login: str = Field(min_length=3, max_length=64, pattern=r"^[\w.@+-]+$")
    password: str = Field(min_length=8, max_length=200)


class SignInIn(_Credentials):
    login: str = Field(max_length=64)
    password: str = Field(max_length=200)


class UserOut(BaseOrmModel):
    id: int
    login: str


class TokenOut(BaseModel):
    """For the Chrome extension: sent as `Authorization: Bearer <token>`."""

    token: str
    user: UserOut
