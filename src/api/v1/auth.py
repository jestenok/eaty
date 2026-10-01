from fastapi import APIRouter, Request, Response

from api.dependencies import SESSION_COOKIE, AuthServiceDep, ConfigDep, CurrentUserDep, TokenDep
from app.schemas.auth import SignInIn, SignUpIn, TokenOut, UserOut

router = APIRouter()


def set_session_cookie(request: Request, response: Response, token: str, days: int) -> None:
    """HttpOnly: scripts on the page can't read it; Lax: other sites can't send requests with it.
    Secure when the app is reached over HTTPS (directly or through a proxy such as Tailscale)."""
    https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie(SESSION_COOKIE, token, max_age=days * 86400, path="/", httponly=True, samesite="lax", secure=https)


@router.post("/register", status_code=201, summary="Регистрация (и сразу вход)", response_model=UserOut)
async def register(service: AuthServiceDep, config: ConfigDep, request: Request, response: Response, dto: SignUpIn):
    user, token = await service.register(dto.login, dto.password)
    set_session_cookie(request, response, token, config.SESSION_DAYS)
    return user


@router.post("/login", summary="Вход в браузере (cookie)", response_model=UserOut)
async def login(service: AuthServiceDep, config: ConfigDep, request: Request, response: Response, dto: SignInIn):
    user, token = await service.login(dto.login, dto.password)
    set_session_cookie(request, response, token, config.SESSION_DAYS)
    return user


@router.post("/token", summary="Вход для расширения Chrome (токен в ответе)", response_model=TokenOut)
async def token(service: AuthServiceDep, dto: SignInIn):
    user, token = await service.login(dto.login, dto.password)
    return TokenOut(token=token, user=user)


@router.post("/extension-token", summary="Вход для расширения Chrome с открытого сайта, без пароля",
             response_model=TokenOut)
async def extension_token(service: AuthServiceDep, user: CurrentUserDep):
    """The extension's script on the app's page asks with the page's cookie, so the extension
    signs in as whoever is signed in there. The SameSite=Lax cookie doesn't go with POSTs from
    other sites, and without CORS their pages can't read the answer."""
    return TokenOut(token=await service.sign_in_again(user.id), user=user)


@router.post("/logout", status_code=204, summary="Выйти")
async def logout(service: AuthServiceDep, response: Response, token: TokenDep):
    await service.logout(token)
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", summary="Кто вошёл", response_model=UserOut)
async def me(user: CurrentUserDep):
    return user
