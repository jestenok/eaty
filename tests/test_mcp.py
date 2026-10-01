"""eaty as an MCP server: Claude registers, the user allows it on the consent page, and Claude
reads the week menu's Wolt order with the token, as that user only.
Needs TEST_DATABASE_URL (see conftest.py); skipped otherwise."""

import base64
import contextlib
import datetime as dt
import hashlib
import secrets
from urllib.parse import parse_qs, urlparse

BASE = "http://localhost:8080"          # PUBLIC_URL's default: the OAuth issuer
MCP_URL = f"{BASE}/mcp"
CALLBACK = "http://localhost:9999/callback"
TODAY = dt.date.today().isoformat()


def site_client(app):
    """The browser: the whole site, not just the API; keeps the session cookie."""
    from httpx import ASGITransport, AsyncClient

    return AsyncClient(transport=ASGITransport(app=app), base_url=BASE)


async def sign_up(browser, login: str) -> None:
    resp = await browser.post("/api/v1/auth/register", json={"login": login, "password": "correct horse"})
    assert resp.status_code == 201, resp.text


def query(url: str) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


async def register_claude(http) -> str:
    resp = await http.post("/register", json={
        "client_name": "Claude", "redirect_uris": [CALLBACK], "token_endpoint_auth_method": "none",
        "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"]})
    assert resp.status_code == 201, resp.text
    return resp.json()["client_id"]


async def consent_url(http, client_id: str) -> tuple[str, str]:
    """/authorize sends the browser to the consent page; returns that URL and the PKCE verifier."""
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    resp = await http.get("/authorize", params={
        "response_type": "code", "client_id": client_id, "redirect_uri": CALLBACK, "code_challenge": challenge,
        "code_challenge_method": "S256", "state": "st4te", "scope": "eaty", "resource": MCP_URL})
    assert resp.status_code == 302, resp.text
    assert resp.headers["location"].startswith(f"{BASE}/oauth/consent?")
    return resp.headers["location"], verifier


async def allow(http, url: str, **form) -> str:
    """Press «Разрешить» on the consent page; returns the code from the redirect back to Claude."""
    resp = await http.post(url.split("?")[0], data={**query(url), "answer": "allow", **form})
    assert resp.status_code == 303, resp.text
    back = query(resp.headers["location"])
    assert resp.headers["location"].startswith(CALLBACK) and back["state"] == "st4te"
    return back["code"]


async def exchange(http, client_id: str, code: str, verifier: str) -> dict:
    resp = await http.post("/token", data={
        "grant_type": "authorization_code", "code": code, "redirect_uri": CALLBACK, "client_id": client_id,
        "code_verifier": verifier, "resource": MCP_URL})
    assert resp.status_code == 200, resp.text
    return resp.json()


async def connect(app, login: str) -> dict:
    """The whole flow for a new user signed in on the site: tokens for Claude."""
    async with site_client(app) as browser:
        await sign_up(browser, login)
        client_id = await register_claude(browser)
        url, verifier = await consent_url(browser, client_id)
        return {"client_id": client_id, **await exchange(browser, client_id, await allow(browser, url), verifier)}


@contextlib.asynccontextmanager
async def mcp_client(app, access_token: str):
    import httpx2
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client

    http = httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app),
                              headers={"Authorization": f"Bearer {access_token}"})
    async with http, Client(streamable_http_client(MCP_URL, http_client=http)) as client:
        yield client


async def test_claude_finds_the_server_and_must_sign_in(app):
    async with site_client(app) as http:
        resource = (await http.get("/.well-known/oauth-protected-resource/mcp")).json()
        assert resource["resource"] == MCP_URL and resource["authorization_servers"] == [BASE]
        server = (await http.get("/.well-known/oauth-authorization-server")).json()
        assert server["authorization_endpoint"] == f"{BASE}/authorize"
        assert server["registration_endpoint"] == f"{BASE}/register"
        assert server["code_challenge_methods_supported"] == ["S256"]

        resp = await http.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert resp.status_code == 401
        assert "resource_metadata" in resp.headers["www-authenticate"]
        bad = await http.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                              headers={"Authorization": "Bearer nope"})
        assert bad.status_code == 401

        # the site and its API work as before, with the API's own 404s
        assert (await http.get("/api/v1/health")).json() == {"ok": True}
        assert (await http.get("/api/v1/nope")).json() == {"detail": "Not Found"}
        assert (await http.get("/")).status_code == 200


async def test_consent_page_signs_in_allows_and_denies(app):
    async with site_client(app) as browser:
        client_id = await register_claude(browser)
        url, verifier = await consent_url(browser, client_id)

        page = await browser.get(url)
        assert page.status_code == 200 and "Claude" in page.text and 'name="password"' in page.text
        assert page.headers["x-frame-options"] == "DENY"

        deny = await browser.post(url.split("?")[0], data={**query(url), "answer": "deny"})
        assert deny.status_code == 303 and query(deny.headers["location"])["error"] == "access_denied"

        await sign_up(browser, "anna")
        await browser.post("/api/v1/auth/logout")
        wrong = await browser.post(url.split("?")[0],
                                   data={**query(url), "answer": "allow", "login": "anna", "password": "wrong horse"})
        assert wrong.status_code == 401 and "Неверный логин или пароль" in wrong.text

        code = await allow(browser, url, login="anna", password="correct horse")
        assert (await browser.get("/api/v1/auth/me")).json()["login"] == "anna"  # signed in on the site too
        assert "Аккаунт eaty: <b>anna</b>" in (await browser.get(url)).text

        tokens = await exchange(browser, client_id, code, verifier)
        assert tokens["token_type"] == "Bearer" and tokens["scope"] == "eaty" and tokens["refresh_token"]
        again = await browser.post("/token", data={
            "grant_type": "authorization_code", "code": code, "redirect_uri": CALLBACK, "client_id": client_id,
            "code_verifier": verifier})
        assert again.status_code == 400  # a code works once


async def test_consent_page_refuses_requests_it_cannot_trust(app):
    async with site_client(app) as browser:
        client_id = await register_claude(browser)
        url, _ = await consent_url(browser, client_id)
        params = query(url)
        for changed in ({"client_id": "nobody"}, {"redirect_uri": "https://evil.example/cb"},
                        {"code_challenge": ""}, {"scope": "admin"}):
            resp = await browser.get("/oauth/consent", params={**params, **changed})
            assert resp.status_code == 400, changed
            assert "evil.example" not in resp.headers.get("location", "")

        url, _ = await consent_url(browser, client_id)
        await sign_up(browser, "anna")
        code = await allow(browser, url)
        wrong_verifier = await browser.post("/token", data={
            "grant_type": "authorization_code", "code": code, "redirect_uri": CALLBACK, "client_id": client_id,
            "code_verifier": secrets.token_urlsafe(48)})
        assert wrong_verifier.status_code == 400


async def test_claude_reads_the_week_order_and_gets_the_prompt(app):
    anna = await connect(app, "anna")
    async with mcp_client(app, anna["access_token"]) as claude:
        assert {t.name for t in (await claude.list_tools()).tools} == {"wolt_order", "menu_status"}
        assert [p.name for p in (await claude.list_prompts()).prompts] == ["wolt_order"]

        nothing = await claude.call_tool("wolt_order", {})
        assert nothing.is_error and "нет меню, которое ждёт заказа" in nothing.content[0].text
        prompt = await claude.get_prompt("wolt_order")
        assert "утвердить меню" in prompt.messages[0].content.text

    async with site_client(app) as browser:
        await browser.post("/api/v1/auth/login", json={"login": "anna", "password": "correct horse"})
        menu = (await browser.post("/api/v1/menus", json={"start": TODAY})).json()
        await browser.put(f"/api/v1/menus/{menu['id']}/status", json={"status": "awaiting_order"})
        expected = (await browser.get(f"/api/v1/menus/{menu['id']}/order")).json()

    async with mcp_client(app, anna["access_token"]) as claude:
        order = await claude.call_tool("wolt_order", {})
        assert not order.is_error
        assert order.structured_content["menu_id"] == menu["id"]
        assert order.structured_content["task"] == expected["task"]
        assert order.structured_content["shopping"]["stores"]

        prompt = (await claude.get_prompt("wolt_order")).messages[0].content.text
        assert prompt.startswith(expected["task"])
        assert "жди моего «да»" in prompt and f"Меню в eaty: №{menu['id']}" in prompt

        status = await claude.call_tool("menu_status", {"menu_id": menu["id"]})
        assert status.structured_content["status"] == "awaiting_order"

    boris = await connect(app, "boris")
    async with mcp_client(app, boris["access_token"]) as claude:
        foreign = await claude.call_tool("menu_status", {"menu_id": menu["id"]})
        assert foreign.is_error and "не найден" in foreign.content[0].text
        assert (await claude.call_tool("wolt_order", {})).is_error  # boris has no menu of his own


async def test_tokens_refresh_and_revoke(app):
    anna = await connect(app, "anna")
    async with site_client(app) as http:
        refresh = {"grant_type": "refresh_token", "refresh_token": anna["refresh_token"], "client_id": anna["client_id"]}
        new = (await http.post("/token", data=refresh)).json()
        assert new["access_token"] != anna["access_token"]
        assert (await http.post("/token", data=refresh)).status_code == 400  # rotated: the old one is used up

        tools = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        old_access = await http.post("/mcp", json=tools, headers={"Authorization": f"Bearer {anna['access_token']}"})
        assert old_access.status_code == 401

        async with mcp_client(app, new["access_token"]) as claude:
            assert (await claude.list_tools()).tools

        # the SDK's revocation form wants client_secret even from a public client: empty then
        revoke = await http.post("/revoke", data={"token": new["refresh_token"], "client_id": anna["client_id"],
                                                  "client_secret": ""})
        assert revoke.status_code == 200
        gone = await http.post("/mcp", json=tools, headers={"Authorization": f"Bearer {new['access_token']}"})
        assert gone.status_code == 401  # revoking the refresh token revokes its access token too



async def test_account_page_lists_claude_and_disconnects_it(app):
    anna = await connect(app, "anna")
    boris = await connect(app, "boris")
    tools = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    async with site_client(app) as http:
        assert (await http.get("/api/v1/claude/connections")).status_code == 401

        await http.post("/api/v1/auth/login", json={"login": "boris", "password": "correct horse"})
        # someone else's Claude is neither seen nor disconnected
        assert [c["client_id"] for c in (await http.get("/api/v1/claude/connections")).json()] == [boris["client_id"]]
        assert (await http.delete(f"/api/v1/claude/connections/{anna['client_id']}")).status_code == 204

        await http.post("/api/v1/auth/login", json={"login": "anna", "password": "correct horse"})
        refresh = {"grant_type": "refresh_token", "refresh_token": anna["refresh_token"], "client_id": anna["client_id"]}
        new = (await http.post("/token", data=refresh)).json()
        listed = (await http.get("/api/v1/claude/connections")).json()
        assert [(c["client_id"], c["name"]) for c in listed] == [(anna["client_id"], "Claude")]  # one, after a refresh too

        assert (await http.delete(f"/api/v1/claude/connections/{anna['client_id']}")).status_code == 204
        assert (await http.get("/api/v1/claude/connections")).json() == []
        gone = await http.post("/mcp", json=tools, headers={"Authorization": f"Bearer {new['access_token']}"})
        assert gone.status_code == 401
        again = {**refresh, "refresh_token": new["refresh_token"]}
        assert (await http.post("/token", data=again)).status_code == 400   # to come back, Claude asks again

    async with mcp_client(app, boris["access_token"]) as claude:
        assert (await claude.list_tools()).tools
