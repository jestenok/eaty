"""eaty as an MCP server for the user's own Claude (claude.ai, Claude Desktop, Claude Code).

Claude connects to {PUBLIC_URL}/mcp and signs in as an eaty user with OAuth (the consent page
is api/mcp/consent.py). It then sees what the week menu needs from Wolt and gets a prompt to
fill the Wolt carts in the user's browser, on the user's own Claude plan.
"""

import datetime as dt
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from starlette.applications import Starlette
from starlette.routing import Route

from api.dependencies import menu_service_factory, oauth_service_factory
from api.mcp.oauth import EatyOAuthProvider
from app.schemas.menu import MenuOrderOut, MenuOut
from app.service.menus import MenuService
from app.service.oauth import SCOPE
from config import AppConfig
from core.db import Database
from core.error import AppError

MCP_PATH = "/mcp"

INSTRUCTIONS = """eaty plans the user's week of meals and works out which groceries to buy in Wolt.
To order them: call wolt_order, put the items into the Wolt carts in the user's browser (one order per
store), and stop before paying: show the carts, the totals with delivery and any substitutions, and
wait for the user's explicit yes. After the payment, menu_status shows whether the order reached eaty.
Texts from eaty are in Russian; answer the user in their language."""

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)

WOLT_TIPS = """Как класть в корзину Wolt:
- Клади товары по одному и жди, пока корзина обновится (в шапке сменится «Открыть заказ … ₾»),
  только потом следующий: быстрые добавления и перезагрузка страницы теряют товары.
- Не открывай wolt.com в двух вкладках, пока собираешь корзину.
- Если у тебя нет браузера с моим аккаунтом Wolt (например, Claude в Chrome), скажи об этом и дай мне
  этот список: я закажу сам по ссылкам.
- После оплаты проверь инструментом menu_status, что заказ дошёл до eaty."""


def build_mcp(config: AppConfig, database: Database) -> MCPServer:
    public_url = config.PUBLIC_URL.rstrip("/")
    menus = menu_service_factory(config)

    server = MCPServer(
        name="eaty",
        title="eaty",
        version=config.RELEASE_VERSION,
        website_url=public_url,
        instructions=INSTRUCTIONS,
        auth_server_provider=EatyOAuthProvider(database, oauth_service_factory(config), public_url),
        auth=AuthSettings(
            issuer_url=public_url,
            resource_server_url=public_url + MCP_PATH,
            required_scopes=[SCOPE],
            client_registration_options=ClientRegistrationOptions(enabled=True, valid_scopes=[SCOPE],
                                                                  default_scopes=[SCOPE]),
            revocation_options=RevocationOptions(enabled=True),
            # eaty issues tokens for this one server only, so there is no other audience to refuse
            validate_token_resource=False,
        ),
    )

    @asynccontextmanager
    async def user_menus() -> AsyncIterator[MenuService]:
        """The menus of the user the token belongs to, on the call's own transaction."""
        token = get_access_token()
        if token is None or token.subject is None:  # the SDK lets no request without a token through
            raise ToolError("Нужно подключить eaty заново: нет входа")
        try:
            async with database.transaction() as session:
                yield menus(session, int(token.subject))
        except AppError as e:
            raise ToolError(e.message) from e

    async def awaiting_order(service: MenuService, menu_id: int | None) -> MenuOrderOut | None:
        """What to order for the menu, or, without `menu_id`, for the earliest menu awaiting order."""
        if menu_id is None:
            waiting = await service.active(dt.date.today(), "awaiting_order")
            if not waiting:
                return None
            menu_id = waiting[0].id
        return await service.order(menu_id, dt.date.today())

    @server.tool(title="Что заказать в Wolt", annotations=READ_ONLY)
    async def wolt_order(menu_id: int | None = None) -> MenuOrderOut:
        """What to put into the Wolt carts for the user's week menu that awaits ordering: stores (one Wolt
        order each) with item links and how many to add (`packs`; for `by_weight` items, weight steps),
        items to find by search (`not_found`), and `task`, the same as instructions in Russian.
        Without `menu_id`, the earliest menu awaiting order."""
        async with user_menus() as service:
            order = await awaiting_order(service, menu_id)
        if order is None:
            raise ToolError(f"В eaty нет меню, которое ждёт заказа. Попроси пользователя утвердить меню на неделю: "
                            f"{public_url}/#/week")
        return order

    @server.tool(title="Статус меню", annotations=READ_ONLY)
    async def menu_status(menu_id: int) -> MenuOut:
        """A week menu: its status (draft, awaiting_order, ordered), meals, and the Wolt orders that came
        back through the eaty Chrome extension. Becomes `ordered` once nothing is left to buy."""
        async with user_menus() as service:
            return await service.get(menu_id)

    @server.prompt(name="wolt_order", title="Собрать корзину в Wolt")
    async def wolt_order_prompt() -> str:
        """Fill the Wolt carts for the week menu that awaits ordering, and wait for a yes before paying."""
        async with user_menus() as service:
            order = await awaiting_order(service, None)
        if order is None:
            return (f"Помоги заказать продукты в Wolt по меню eaty. Сейчас в eaty нет меню, которое ждёт заказа: "
                    f"подскажи мне утвердить меню на неделю ({public_url}/#/week), а потом позвать тебя снова.")
        if not order.shopping.stores and not order.shopping.not_found:
            return order.task
        return f"{order.task}\n\n{WOLT_TIPS}\n\nМеню в eaty: №{order.menu_id}."

    return server


def mcp_routes(mcp_app: Starlette) -> list[Route]:
    """The MCP SDK's app as routes of our own app, each behind the SDK's middleware (the bearer
    token check): /mcp, and the OAuth endpoints it serves at the root (/.well-known/…, /authorize,
    /token, /register, /revoke). Not a mount at "/": that would swallow every route added later,
    and the API's own 404s."""
    return [Route(r.path, r.endpoint, methods=r.methods, name=r.name, middleware=mcp_app.user_middleware)
            for r in mcp_app.routes]
