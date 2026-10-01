from app.models import WoltSyncLog
from core.repository import UserScopedRepository


class WoltSyncLogRepository(UserScopedRepository[WoltSyncLog]):
    model = WoltSyncLog

    async def latest(self, limit: int) -> list[WoltSyncLog]:
        return await self.find(order_by=[WoltSyncLog.created_at.desc(), WoltSyncLog.id.desc()], limit=limit)
