from fastapi import APIRouter, Depends

from api.dependencies import get_current_user
from api.v1.auth import router as api_v1_auth_router
from api.v1.catalog import router as api_v1_catalog_router
from api.v1.claude import router as api_v1_claude_router
from api.v1.health import router as api_v1_health_router
from api.v1.menus import router as api_v1_menus_router
from api.v1.pantry import router as api_v1_pantry_router
from api.v1.plan import router as api_v1_plan_router
from api.v1.products import router as api_v1_products_router
from api.v1.recipes import router as api_v1_recipes_router
from api.v1.shopping import router as api_v1_shopping_router
from api.v1.timer_sound import router as api_v1_timer_sound_router
from api.v1.wolt_orders import router as api_v1_wolt_orders_router

# Everything but signing in and the health check is for signed-in users only.
signed_in = [Depends(get_current_user)]

router = APIRouter()
router.include_router(api_v1_auth_router, prefix="/v1/auth", tags=["Auth"])
router.include_router(api_v1_plan_router, prefix="/v1/plan", tags=["Plan"], dependencies=signed_in)
router.include_router(api_v1_menus_router, prefix="/v1/menus", tags=["Week menus"], dependencies=signed_in)
router.include_router(api_v1_recipes_router, prefix="/v1/recipes", tags=["Recipes"], dependencies=signed_in)
router.include_router(api_v1_products_router, prefix="/v1/products", tags=["Products"], dependencies=signed_in)
router.include_router(api_v1_shopping_router, prefix="/v1/shopping", tags=["Shopping"], dependencies=signed_in)
router.include_router(api_v1_catalog_router, prefix="/v1/catalog", tags=["Catalog"], dependencies=signed_in)
router.include_router(api_v1_pantry_router, prefix="/v1/pantry", tags=["Pantry"], dependencies=signed_in)
router.include_router(api_v1_wolt_orders_router, prefix="/v1/wolt-orders", tags=["Wolt orders"], dependencies=signed_in)
router.include_router(api_v1_claude_router, prefix="/v1/claude", tags=["Claude"], dependencies=signed_in)
router.include_router(api_v1_timer_sound_router, prefix="/v1/timer-sound", tags=["Timer sound"], dependencies=signed_in)
router.include_router(api_v1_health_router, prefix="/v1/health", tags=["Health"])
