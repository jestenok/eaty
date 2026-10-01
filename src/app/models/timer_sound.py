import datetime as dt

from core.db import Base, DateTime, ForeignKey, LargeBinary, Mp, String, func, mc


class TimerSound(Base):
    """The user's own sound for a timer that rings, uploaded on the account page."""

    user_id: Mp[int] = mc(ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True)
    name: Mp[str] = mc(String(200))                         # the file's name, to show
    content_type: Mp[str] = mc(String(100))                 # audio/…
    data: Mp[bytes] = mc(LargeBinary)
    updated_at: Mp[dt.datetime] = mc(DateTime(timezone=True), server_default=func.now())
