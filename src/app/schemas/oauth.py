import datetime as dt

from pydantic import BaseModel


class ClaudeConnectionOut(BaseModel):
    """An app (Claude) the user let into their eaty and that can still come in."""

    client_id: str
    name: str                       # as the app named itself when it registered: "Claude", "Claude Code"…
    signed_in_at: dt.datetime       # when it last got tokens: on "Allow" or on its daily refresh
