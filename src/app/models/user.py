import datetime as dt

from core.db import Base, DateTime, Mp, String, Text, func, mc


class User(Base):
    """Someone with their own plan, pantry and Wolt orders. Recipes and prices are shared.

    The row with login '' holds the data from before accounts existed; the first sign-up
    takes it over (it can't sign in: no password matches an empty hash).
    """

    __tablename__ = "app_user"  # "user" is reserved in Postgres

    id: Mp[int] = mc(primary_key=True)
    login: Mp[str] = mc(String(64), unique=True)            # lowercase
    password_hash: Mp[str] = mc(Text)                       # 'scrypt$n$r$p$salt$hash'
    created_at: Mp[dt.datetime] = mc(DateTime(timezone=True), server_default=func.now())
