from typing import Annotated

from fastapi import APIRouter, Header, Query, Request, Response

from api.dependencies import TimerSoundServiceDep
from app.schemas.timer_sound import TimerSoundOut
from app.service.timer_sound import MAX_BYTES

router = APIRouter()


@router.get("", summary="Свой звук таймера: какой он (null — своего нет)", response_model=TimerSoundOut | None)
async def info(service: TimerSoundServiceDep):
    return await service.info()


@router.get("/file", summary="Свой звук таймера, сам файл", response_class=Response,
            responses={200: {"content": {"audio/*": {}}}, 304: {"description": "Не изменился"}})
async def file(service: TimerSoundServiceDep, if_none_match: Annotated[str | None, Header()] = None):
    sound = await service.file()
    # the sound stays in the phone's cache, but a new one comes as soon as it's uploaded
    headers = {"ETag": sound.etag, "Cache-Control": "private, no-cache", "X-Content-Type-Options": "nosniff"}
    if if_none_match == sound.etag:
        return Response(status_code=304, headers=headers)
    return Response(sound.data, media_type=sound.content_type, headers=headers)


@router.put("", summary="Загрузить свой звук таймера: тело запроса — сам файл", response_model=TimerSoundOut,
            openapi_extra={"requestBody": {"required": True, "content": {"audio/*": {"schema": {"type": "string",
                                                                                              "format": "binary"}}}}})
async def upload(service: TimerSoundServiceDep, request: Request, name: Annotated[str, Query(max_length=500)],
                 content_type: Annotated[str, Header()] = ""):
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > MAX_BYTES:   # no need to read the rest of a film
            break
    return await service.save(name, content_type.split(";")[0].strip().lower(), bytes(data))


@router.delete("", status_code=204, summary="Убрать свой звук таймера")
async def remove(service: TimerSoundServiceDep):
    await service.remove()
