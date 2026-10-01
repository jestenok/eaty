import datetime as dt
from typing import Any

from core.db import JSONB, Base, DateTime, Integer, Mp, String, Text, func, mc


class WoltSyncLog(Base):
    """One run of «Обновить из Wolt»: what was found and imported, and what the extension
    saw on wolt.com (request paths and field names, no values) — to fix the order parser
    when Wolt changes its format."""

    id: Mp[int] = mc(primary_key=True)
    created_at: Mp[dt.datetime] = mc(DateTime(timezone=True), server_default=func.now())
    source: Mp[str] = mc(String(16), server_default="button")
    orders_found: Mp[int] = mc(Integer, server_default="0")
    orders_imported: Mp[int] = mc(Integer, server_default="0")
    pantry_items: Mp[int] = mc(Integer, server_default="0")
    error: Mp[str | None] = mc(Text)
    details: Mp[dict[str, Any] | None] = mc(JSONB)
