import datetime as dt

from core.db import Base, DateTime, ForeignKey, Mp, String, func, mc


class LoginSession(Base):
    """A sign-in: the browser keeps its token in a cookie, the Chrome extension in its
    storage. Only a hash of the token is stored, so a database dump can't sign anyone in."""

    token_hash: Mp[str] = mc(String(64), primary_key=True)  # sha256, hex
    user_id: Mp[int] = mc(ForeignKey("app_user.id", ondelete="CASCADE"), index=True)
    created_at: Mp[dt.datetime] = mc(DateTime(timezone=True), server_default=func.now())
    expires_at: Mp[dt.datetime] = mc(DateTime(timezone=True))
