from sqlalchemy import Row, func, select

from app.models import TimerSound
from core.repository import UserScopedRepository


class TimerSoundRepository(UserScopedRepository[TimerSound]):
    model = TimerSound

    async def info(self) -> Row | None:
        """name, content_type, size, updated_at: what the sound is, without loading the sound itself."""
        query = select(TimerSound.name, TimerSound.content_type, func.length(TimerSound.data).label("size"),
                       TimerSound.updated_at).where(self.mine)
        return (await self.session.execute(query)).one_or_none()

    async def save(self, name: str, content_type: str, data: bytes) -> None:
        await self.upsert(dict(name=name, content_type=content_type, data=data, updated_at=func.now()), conflict=())

    async def remove(self) -> None:
        await self.delete_where()
