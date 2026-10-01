import datetime as dt

from pydantic import BaseModel


class TimerSoundOut(BaseModel):
    """The user's own timer sound: what it is, the sound itself is at /timer-sound/file."""

    name: str
    content_type: str
    size: int                       # bytes
    updated_at: dt.datetime


class TimerSoundFile(BaseModel):
    content_type: str
    data: bytes
    etag: str
