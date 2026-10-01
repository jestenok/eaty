from fastapi import APIRouter

from api.v1.catalog import router as api_v1_catalog_router
from api.v1.health import router as api_v1_health_router
from api.v1.pantry import router as api_v1_pantry_router
from api.v1.plan import router as api_v1_plan_router
from api.v1.recipes import router as api_v1_recipes_router
from api.v1.shopping import router as api_v1_shopping_router
from api.v1.wolt_orders import router as api_v1_wolt_orders_router

router = APIRouter()
router.include_router(api_v1_plan_router, prefix="/v1/plan", tags=["Plan"])
router.include_router(api_v1_recipes_router, prefix="/v1/recipes", tags=["Recipes"])
router.include_router(api_v1_shopping_router, prefix="/v1/shopping", tags=["Shopping"])
router.include_router(api_v1_catalog_router, prefix="/v1/catalog", tags=["Catalog"])
router.include_router(api_v1_pantry_router, prefix="/v1/pantry", tags=["Pantry"])
router.include_router(api_v1_wolt_orders_router, prefix="/v1/wolt-orders", tags=["Wolt orders"])
router.include_router(api_v1_health_router, prefix="/v1/health", tags=["Health"])
