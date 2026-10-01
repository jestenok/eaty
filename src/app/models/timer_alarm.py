import datetime as dt

from core.db import Base, DateTime, ForeignKey, Mp, String, mc


class TimerAlarm(Base):
    """A running timer the server pushes «Готово!» for when it's up: the phone may be locked by then.
    Gone once sent, or when the timer is stopped or paused."""

    user_id: Mp[int] = mc(ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True)
    key: Mp[str] = mc(String(100), primary_key=True)        # the timer's key in the app: recipe:step
    label: Mp[str] = mc(String(200))
    url: Mp[str] = mc(String(500))                          # where the notification opens the app
    fire_at: Mp[dt.datetime] = mc(DateTime(timezone=True), index=True)
