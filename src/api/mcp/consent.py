"""The page where the user lets Claude into their eaty (OAuth consent), signing in first if needed.

/authorize (the MCP SDK) sends the browser here with the authorization request in the URL.
Everything in it is checked again, as anyone can open this URL with anything in it.
"""

from dataclasses import dataclass
from html import escape
from urllib.parse import urlparse

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from mcp.server.auth.provider import construct_redirect_uri
from mcp.shared.auth import InvalidRedirectUriError, InvalidScopeError, OAuthClientInformationFull
from pydantic import AnyUrl, ValidationError

from api.dependencies import AuthServiceDep, ConfigDep, OAuthServiceDep, TokenDep
from api.mcp.oauth import CONSENT_PATH
from api.v1.auth import set_session_cookie
from app.schemas.auth import UserOut
from core.error import UnauthorizedError

router = APIRouter()

# Not in a frame (clickjacking), not cached, and the URL with the request isn't sent anywhere.
HEADERS = {"X-Frame-Options": "DENY", "Content-Security-Policy": "frame-ancestors 'none'",
           "Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
FIELDS = ("client_id", "redirect_uri", "explicit", "code_challenge", "state", "scope", "resource")


class BadRequest(Exception):
    """Nowhere safe to send the browser back to: shown on the page instead."""


@dataclass
class Consent:
    client: OAuthClientInformationFull
    redirect_uri: AnyUrl
    explicit: bool
    code_challenge: str
    state: str | None
    scopes: list[str] | None
    resource: str | None
    fields: dict[str, str]          # the request as it came, for the form to send back

    @property
    def app_name(self) -> str:
        return self.client.client_name or "Приложение"

    def back(self, **params: str | None) -> RedirectResponse:
        """To the app's redirect URI with the answer (303: the browser follows with a GET)."""
        return RedirectResponse(construct_redirect_uri(str(self.redirect_uri), **params, state=self.state),
                                status_code=303, headers=HEADERS)


async def read_request(oauth: OAuthServiceDep, data) -> Consent:
    fields = {k: data[k] for k in FIELDS if data.get(k)}
    client = await oauth.get_client(fields.get("client_id", ""))
    if client is None:
        raise BadRequest("Такое приложение не регистрировалось в eaty.")
    try:
        redirect_uri = client.validate_redirect_uri(AnyUrl(fields["redirect_uri"]) if "redirect_uri" in fields else None)
        scopes = client.validate_scope(fields.get("scope"))
    except (InvalidRedirectUriError, InvalidScopeError, ValidationError):
        raise BadRequest("Приложение прислало неверный запрос: адрес возврата или права не те, что оно регистрировало.")
    if not fields.get("code_challenge"):
        raise BadRequest("В запросе нет code_challenge (PKCE).")
    return Consent(client, redirect_uri, fields.get("explicit") == "1", fields["code_challenge"], fields.get("state"),
                   scopes, fields.get("resource"), fields)


async def signed_in(auth: AuthServiceDep, token: str | None) -> UserOut | None:
    try:
        return await auth.user_for_token(token)
    except UnauthorizedError:
        return None


@router.get(CONSENT_PATH, include_in_schema=False)
async def consent_page(request: Request, oauth: OAuthServiceDep, auth: AuthServiceDep, token: TokenDep) -> Response:
    try:
        consent = await read_request(oauth, request.query_params)
    except BadRequest as e:
        return page_response(error_page(str(e)), 400)
    return page_response(consent_form(consent, await signed_in(auth, token)))


@router.post(CONSENT_PATH, include_in_schema=False)
async def consent_answer(request: Request, oauth: OAuthServiceDep, auth: AuthServiceDep, token: TokenDep,
                         config: ConfigDep) -> Response:
    form = await request.form()
    try:
        consent = await read_request(oauth, form)
    except BadRequest as e:
        return page_response(error_page(str(e)), 400)
    if form.get("answer") != "allow":
        return consent.back(error="access_denied", error_description="Пользователь не разрешил доступ")

    user, new_token = await signed_in(auth, token), None
    if user is None:
        try:
            user, new_token = await auth.login(str(form.get("login", "")), str(form.get("password", "")))
        except UnauthorizedError as e:
            return page_response(consent_form(consent, None, error=e.message, login=str(form.get("login", ""))), 401)

    code = await oauth.grant_code(user.id, consent.client, consent.redirect_uri, consent.explicit,
                                  consent.code_challenge, consent.scopes, consent.resource)
    response = consent.back(code=code)
    if new_token:  # signed in on this page: the site is signed in too
        set_session_cookie(request, response, new_token, config.SESSION_DAYS)
    return response


# ---------- HTML ----------

def page_response(body: str, status: int = 200) -> HTMLResponse:
    return HTMLResponse(PAGE.format(body=body), status_code=status, headers=HEADERS)


def consent_form(consent: Consent, user: UserOut | None, error: str = "", login: str = "") -> str:
    host = urlparse(str(consent.redirect_uri)).netloc or str(consent.redirect_uri)
    hidden = "".join(f'<input type="hidden" name="{escape(k)}" value="{escape(v)}">' for k, v in consent.fields.items())
    if user:
        who = f'<p class="small">Аккаунт eaty: <b>{escape(user.login)}</b></p>'
        allow = "Разрешить"
    else:
        who = ('<input name="login" placeholder="Логин" autocomplete="username" required autofocus'
               f' value="{escape(login)}">'
               '<input name="password" type="password" placeholder="Пароль" autocomplete="current-password" required>')
        allow = "Войти и разрешить"
    error_html = f'<p class="error small">{escape(error)}</p>' if error else ""
    return f"""
      <h1 class="brand"><img src="/static/logo.svg" alt="eaty" width="123" height="56"></h1>
      <p><b>{escape(consent.app_name)}</b> просит доступ к твоему eaty: меню на неделю, план,
        что есть дома и заказы Wolt. Так Claude сможет собрать корзину в Wolt по меню.</p>
      <p class="small muted">После ответа вернёмся на {escape(host)}. Отозвать доступ можно
        в настройках коннекторов Claude.</p>
      <form method="post" class="stack">
        {hidden}{who}{error_html}
        <div class="row">
          <button class="primary grow" name="answer" value="allow">{allow}</button>
          <button class="ghost" name="answer" value="deny" formnovalidate>Отказать</button>
        </div>
      </form>"""


def error_page(message: str) -> str:
    return f"""
      <h1 class="brand"><img src="/static/logo.svg" alt="eaty" width="123" height="56"></h1>
      <p>Не получилось подключить приложение.</p>
      <p class="error small">{escape(message)}</p>
      <p class="small muted">Попробуй подключить eaty в Claude заново.</p>"""


PAGE = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Подключить Claude — eaty</title>
  <link rel="icon" href="/favicon.ico" sizes="32x32">
  <link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/static/style.css">
</head>
<body class="signed-out">
  <main class="view"><div class="auth card stack">{body}
  </div></main>
</body>
</html>"""
