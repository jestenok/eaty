import posixpath

from app.repositories.timer_sounds import TimerSoundRepository
from app.schemas.timer_sound import TimerSoundFile, TimerSoundOut
from core.error import AppError, NotFoundError
from core.service import BaseService

MAX_BYTES = 2 * 1024 * 1024     # a clip of a few seconds is tens of kilobytes
# by the name, when a phone sends a file without its type (mimetypes doesn't know .m4a on every system)
AUDIO_TYPES = {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".aac": "audio/aac", ".wav": "audio/wav"}


class TimerSoundService(BaseService[TimerSoundRepository]):
    """The user's own sound for timers: one per account, so it rings on every device they sign in on."""

    async def info(self) -> TimerSoundOut | None:
        row = await self.repository.info()
        return None if row is None else TimerSoundOut(**row._asdict())

    async def file(self) -> TimerSoundFile:
        sound = await self.repository.get()
        if sound is None:
            raise NotFoundError("Своего звука нет")
        etag = f'"{int(sound.updated_at.timestamp() * 1000)}-{len(sound.data)}"'
        return TimerSoundFile(content_type=sound.content_type, data=sound.data, etag=etag)

    async def save(self, name: str, content_type: str, data: bytes) -> TimerSoundOut:
        name = posixpath.basename(name.replace("\\", "/")).strip()[:200] or "звук"
        if not content_type.startswith("audio/"):
            content_type = AUDIO_TYPES.get(posixpath.splitext(name)[1].lower(), content_type)
        if not content_type.startswith("audio/"):
            raise AppError("Это не звук: подойдёт mp3, m4a или wav")
        if not data:
            raise AppError("Файл пустой")
        if len(data) > MAX_BYTES:
            raise AppError(f"Файл больше {MAX_BYTES // 1024 // 1024} МБ — нужен короткий звук")
        await self.repository.save(name, content_type[:100], data)
        return await self.info()

    async def remove(self) -> None:
        await self.repository.remove()
