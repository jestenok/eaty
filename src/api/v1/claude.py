from fastapi import APIRouter

from api.dependencies import CurrentUserDep, OAuthServiceDep
from app.schemas.oauth import ClaudeConnectionOut

router = APIRouter()


@router.get("/connections", summary="Какие Claude подключены к eaty (MCP)", response_model=list[ClaudeConnectionOut])
async def connections(service: OAuthServiceDep, user: CurrentUserDep):
    return await service.connections(user.id)


@router.delete("/connections/{client_id}", status_code=204, summary="Отключить Claude от eaty")
async def disconnect(service: OAuthServiceDep, user: CurrentUserDep, client_id: str):
    await service.disconnect(user.id, client_id)
