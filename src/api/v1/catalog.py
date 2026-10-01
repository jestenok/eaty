from fastapi import APIRouter

from api.dependencies import CatalogJobDep
from app.schemas.shopping import CatalogStatusOut

router = APIRouter()


@router.post("/refresh", status_code=202, summary="Обновить цены из каталога Wolt (в фоне)", response_model=CatalogStatusOut)
async def refresh(job: CatalogJobDep):
    job.start()
    return CatalogStatusOut(running=job.running, last=job.last)


@router.get("/status", summary="Как идёт обновление цен", response_model=CatalogStatusOut)
async def status(job: CatalogJobDep):
    return CatalogStatusOut(running=job.running, last=job.last)
