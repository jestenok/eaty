import datetime as dt

from core.db import Base, CheckConstraint, DateTime, Integer, Mp, String, Text, func, mc


class PushKey(Base):
    """The app's VAPID key: push services check that pushes to a browser come from whoever it subscribed with.
    One row, made on the first start."""

    id: Mp[int] = mc(Integer, primary_key=True, autoincrement=False)
    private_key: Mp[str] = mc(Text)                         # PEM
    public_key: Mp[str] = mc(String(100))                   # base64url of the raw point, as the browser takes it
    created_at: Mp[dt.datetime] = mc(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (CheckConstraint("id = 1", name="one_row"),)
