from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RevalidateStaticMiddleware:
    """The phone must not keep an old app.js after an update: pages and static files
    are always revalidated (cheap, thanks to ETag)."""

    def __init__(self, app: ASGIApp, prefixes: tuple[str, ...] = ("/static/",)):
        self.app = app
        self.prefixes = prefixes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        if scope["type"] != "http" or not (path == "/" or path.startswith(self.prefixes)):
            await self.app(scope, receive, send)
            return

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).append((b"cache-control", b"no-cache"))
            await send(message)

        await self.app(scope, receive, send_with_header)
