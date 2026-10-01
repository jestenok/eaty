from pydantic import BaseModel, Field


class PushKeyOut(BaseModel):
    """The app's VAPID public key: the browser subscribes with it (applicationServerKey)."""

    public_key: str


class PushKeysIn(BaseModel):
    p256dh: str = Field(max_length=200)
    auth: str = Field(max_length=100)


class PushSubscriptionIn(BaseModel):
    """PushSubscription.toJSON() from the browser."""

    endpoint: str = Field(max_length=2000)
    keys: PushKeysIn


class TimerAlarmIn(BaseModel):
    """A running timer: push «Готово!» in `seconds`, unless it's stopped or paused before."""

    label: str = Field(max_length=200)
    seconds: float = Field(ge=0, le=24 * 3600)
    url: str = Field("/", max_length=500, pattern=r"^/([^/].*)?$")   # in the app: where the notification opens it
