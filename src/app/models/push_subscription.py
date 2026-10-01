import datetime as dt

from core.db import Base, DateTime, ForeignKey, Mp, String, Text, func, mc


class PushSubscription(Base):
    """A browser (an iPhone's home screen eaty, Chrome…) that let the app send it notifications."""

    id: Mp[int] = mc(primary_key=True)
    user_id: Mp[int] = mc(ForeignKey("app_user.id", ondelete="CASCADE"), index=True)
    endpoint: Mp[str] = mc(Text, unique=True)               # the browser's address at its push service
    p256dh: Mp[str] = mc(String(200))                       # its key to encrypt for
    auth: Mp[str] = mc(String(100))
    created_at: Mp[dt.datetime] = mc(DateTime(timezone=True), server_default=func.now())
