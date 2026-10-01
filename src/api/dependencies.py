"""Composition root: how repositories and services are built for a request.

Chain: request -> unit of work (session) -> signed-in user -> repositories -> services -> handler.
FastAPI caches dependencies per request, so every repository and service of one
request shares the same session and transaction. Repositories of a user's own data are
built for the signed-in user, so asking for one requires signing in. Tests swap any link
with `app.dependency_overrides`.
"""

import datetime as dt
import random
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.wolt_catalog import WoltCatalogClient
from app.repositories.login_sessions import LoginSessionRepository
from app.repositories.meal_plans import MealPlanRepository
from app.repositories.oauth import OAuthClientRepository, OAuthCodeRepository, OAuthTokenRepository
from app.repositories.pantry_entries import PantryEntryRepository
from app.repositories.pantry_pins import PantryPinRepository
from app.repositories.products import ProductRepository
from app.repositories.recipes import RecipeRepository
from app.repositories.timer_sounds import TimerSoundRepository
from app.repositories.users import UserRepository
from app.repositories.week_menus import WeekMenuRepository
from app.repositories.wolt_items import WoltItemRepository
from app.repositories.wolt_orders import WoltOrderRepository
from app.repositories.wolt_sync_logs import WoltSyncLogRepository
from app.schemas.auth import UserOut
from app.service.auth import AuthService
from app.service.catalog import CatalogRefreshJob, CatalogService
from app.service.menus import MenuService
from app.service.oauth import OAuthService
from app.service.orders import OrderService
from app.service.pantry import PantryService
from app.service.plan import PlanService
from app.service.products import ProductService
from app.service.recipes import RecipeService
from app.service.shopping import ShoppingService
from app.service.timer_sound import TimerSoundService
from config import AppConfig
from core.fastapi.dependencies import SessionDep


# ---------- app-level singletons (created in lifespan) ----------

def get_config(request: Request) -> AppConfig:
    return request.app.state.config


def get_catalog_job(request: Request) -> CatalogRefreshJob:
    return request.app.state.catalog_job


ConfigDep = Annotated[AppConfig, Depends(get_config)]
CatalogJobDep = Annotated[CatalogRefreshJob, Depends(get_catalog_job)]


# ---------- shared repositories ----------

def get_product_repository(session: SessionDep) -> ProductRepository:
    return ProductRepository(session)


def get_recipe_repository(session: SessionDep) -> RecipeRepository:
    return RecipeRepository(session)


def get_wolt_item_repository(session: SessionDep) -> WoltItemRepository:
    return WoltItemRepository(session)


def get_user_repository(session: SessionDep) -> UserRepository:
    return UserRepository(session)


def get_login_session_repository(session: SessionDep) -> LoginSessionRepository:
    return LoginSessionRepository(session)


ProductRepositoryDep = Annotated[ProductRepository, Depends(get_product_repository)]
RecipeRepositoryDep = Annotated[RecipeRepository, Depends(get_recipe_repository)]
WoltItemRepositoryDep = Annotated[WoltItemRepository, Depends(get_wolt_item_repository)]
UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
LoginSessionRepositoryDep = Annotated[LoginSessionRepository, Depends(get_login_session_repository)]


# ---------- who is signed in ----------

SESSION_COOKIE = "eaty_session"


def get_token(request: Request) -> str | None:
    """The sign-in token: `Authorization: Bearer` from the Chrome extension, or the browser's cookie."""
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() == "bearer" and token.strip():
        return token.strip()
    return request.cookies.get(SESSION_COOKIE)


TokenDep = Annotated[str | None, Depends(get_token)]


def get_auth_service(users: UserRepositoryDep, logins: LoginSessionRepositoryDep, session: SessionDep,
                     config: ConfigDep) -> AuthService:
    return AuthService(users, logins, plans_of=lambda user_id: MealPlanRepository(session, user_id),
                       session_days=config.SESSION_DAYS)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_current_user(auth: AuthServiceDep, token: TokenDep) -> UserOut:
    """The signed-in user, or 401."""
    return await auth.user_for_token(token)


CurrentUserDep = Annotated[UserOut, Depends(get_current_user)]


# ---------- repositories of the signed-in user's own data ----------

def get_meal_plan_repository(session: SessionDep, user: CurrentUserDep) -> MealPlanRepository:
    return MealPlanRepository(session, user.id)


def get_pantry_entry_repository(session: SessionDep, user: CurrentUserDep) -> PantryEntryRepository:
    return PantryEntryRepository(session, user.id)


def get_pantry_pin_repository(session: SessionDep, user: CurrentUserDep) -> PantryPinRepository:
    return PantryPinRepository(session, user.id)


def get_wolt_order_repository(session: SessionDep, user: CurrentUserDep) -> WoltOrderRepository:
    return WoltOrderRepository(session, user.id)


def get_wolt_sync_log_repository(session: SessionDep, user: CurrentUserDep) -> WoltSyncLogRepository:
    return WoltSyncLogRepository(session, user.id)


def get_week_menu_repository(session: SessionDep, user: CurrentUserDep) -> WeekMenuRepository:
    return WeekMenuRepository(session, user.id)


def get_timer_sound_repository(session: SessionDep, user: CurrentUserDep) -> TimerSoundRepository:
    return TimerSoundRepository(session, user.id)


MealPlanRepositoryDep = Annotated[MealPlanRepository, Depends(get_meal_plan_repository)]
PantryEntryRepositoryDep = Annotated[PantryEntryRepository, Depends(get_pantry_entry_repository)]
PantryPinRepositoryDep = Annotated[PantryPinRepository, Depends(get_pantry_pin_repository)]
WoltOrderRepositoryDep = Annotated[WoltOrderRepository, Depends(get_wolt_order_repository)]
WoltSyncLogRepositoryDep = Annotated[WoltSyncLogRepository, Depends(get_wolt_sync_log_repository)]
WeekMenuRepositoryDep = Annotated[WeekMenuRepository, Depends(get_week_menu_repository)]
TimerSoundRepositoryDep = Annotated[TimerSoundRepository, Depends(get_timer_sound_repository)]


# ---------- services ----------

def get_pantry_service(entries: PantryEntryRepositoryDep, products: ProductRepositoryDep,
                       recipes: RecipeRepositoryDep, pins: PantryPinRepositoryDep) -> PantryService:
    return PantryService(entries, products, recipes, pins)


PantryServiceDep = Annotated[PantryService, Depends(get_pantry_service)]


def get_recipe_service(recipes: RecipeRepositoryDep, products: ProductRepositoryDep,
                       pantry: PantryServiceDep) -> RecipeService:
    return RecipeService(recipes, products, pantry)


def get_product_service(products: ProductRepositoryDep) -> ProductService:
    return ProductService(products)


def get_plan_service(plans: MealPlanRepositoryDep, recipes: RecipeRepositoryDep, pantry: PantryServiceDep) -> PlanService:
    return PlanService(plans, recipes, pantry)


def get_shopping_service(plans: MealPlanRepositoryDep, products: ProductRepositoryDep, items: WoltItemRepositoryDep,
                         pantry: PantryServiceDep, config: ConfigDep) -> ShoppingService:
    return ShoppingService(plans, products, items, pantry, city=config.WOLT_CITY)


ShoppingServiceDep = Annotated[ShoppingService, Depends(get_shopping_service)]


def get_menu_service(menus: WeekMenuRepositoryDep, plans: MealPlanRepositoryDep, recipes: RecipeRepositoryDep,
                     orders: WoltOrderRepositoryDep, shopping: ShoppingServiceDep,
                     pantry: PantryServiceDep) -> MenuService:
    return MenuService(menus, plans, recipes, orders, shopping, pantry, rng=random.Random())


MenuServiceDep = Annotated[MenuService, Depends(get_menu_service)]


def get_order_service(orders: WoltOrderRepositoryDep, items: WoltItemRepositoryDep, products: ProductRepositoryDep,
                      entries: PantryEntryRepositoryDep, sync_logs: WoltSyncLogRepositoryDep, menus: MenuServiceDep,
                      config: ConfigDep) -> OrderService:
    return OrderService(orders, items, products, entries, sync_logs, menus,
                        grocery_re=config.GROCERY_VENUES_RE, max_age_days=config.ORDERS_MAX_AGE_DAYS)


RecipeServiceDep = Annotated[RecipeService, Depends(get_recipe_service)]
ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]
PlanServiceDep = Annotated[PlanService, Depends(get_plan_service)]
OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]


def get_oauth_service(session: SessionDep, config: ConfigDep) -> OAuthService:
    return oauth_service_factory(config)(session)


OAuthServiceDep = Annotated[OAuthService, Depends(get_oauth_service)]


def get_timer_sound_service(sounds: TimerSoundRepositoryDep) -> TimerSoundService:
    return TimerSoundService(sounds)


TimerSoundServiceDep = Annotated[TimerSoundService, Depends(get_timer_sound_service)]


# ---------- background work (no request, so no Depends) ----------

def catalog_service_factory(client: WoltCatalogClient):
    """For the catalog refresh job: a service on the job's own transaction."""
    def build(session: AsyncSession) -> CatalogService:
        return CatalogService(WoltItemRepository(session), ProductRepository(session), client)
    return build


def oauth_service_factory(config: AppConfig):
    """For the MCP SDK's OAuth endpoints, which call us outside any request: a service on the
    call's own transaction."""
    def build(session: AsyncSession) -> OAuthService:
        return OAuthService(OAuthClientRepository(session), OAuthCodeRepository(session), OAuthTokenRepository(session),
                            access_lifetime=dt.timedelta(hours=config.MCP_ACCESS_TOKEN_HOURS),
                            refresh_lifetime=dt.timedelta(days=config.SESSION_DAYS))
    return build


def menu_service_factory(config: AppConfig):
    """For MCP tools: the menus of the user the access token belongs to, on the tool call's own
    transaction. The same chain as get_menu_service."""
    def build(session: AsyncSession, user_id: int) -> MenuService:
        plans = MealPlanRepository(session, user_id)
        products, recipes = ProductRepository(session), RecipeRepository(session)
        pantry = PantryService(PantryEntryRepository(session, user_id), products, recipes,
                               PantryPinRepository(session, user_id))
        shopping = ShoppingService(plans, products, WoltItemRepository(session), pantry, city=config.WOLT_CITY)
        return MenuService(WeekMenuRepository(session, user_id), plans, recipes, WoltOrderRepository(session, user_id),
                           shopping, pantry, rng=random.Random())
    return build
