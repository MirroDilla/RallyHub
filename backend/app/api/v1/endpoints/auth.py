import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.ratelimit import get_login_throttle, get_register_throttle
from app.core.tokens import InvalidToken, decode_session_token
from app.db.session import get_db
from app.dependencies.auth import (
    CSRF_COOKIE,
    CSRF_HEADER,
    SESSION_COOKIE,
    AdminUser,
    CurrentUser,
)
from app.dependencies.services import AuthSvc, Pager, page
from app.domain.errors import AuthenticationError, ForbiddenError
from app.models import User
from app.schemas.auth import (
    ChangeEmailRequest,
    ChangePasswordRequest,
    LoginRequest,
    MeRead,
    RegisterRequest,
    UserRead,
)
from app.schemas.common import Message, Page
from app.schemas.common import check_password as _check_password

router = APIRouter(tags=["auth"])
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _set_cookies(resp: Response, settings: Settings, token: str, csrf: str) -> None:
    max_age = settings.access_token_minutes * 60
    common = {"max_age": max_age, "path": "/", "samesite": "lax", "secure": settings.cookie_secure}
    resp.set_cookie(SESSION_COOKIE, token, httponly=True, **common)
    resp.set_cookie(CSRF_COOKIE, csrf, httponly=False, **common)  # lo lee el JS para el header


def _clear_cookies(resp: Response) -> None:
    resp.delete_cookie(SESSION_COOKIE, path="/")
    resp.delete_cookie(CSRF_COOKIE, path="/")


@router.post("/auth/login", response_model=MeRead, summary="Iniciar sesión")
def login(body: LoginRequest, request: Request, resp: Response, svc: AuthSvc,
          settings: SettingsDep):
    """Limita intentos fallidos por (IP, correo): 5 en 15 min por defecto (en memoria, 1 worker)."""
    throttle = get_login_throttle()
    key = f"{request.client.host if request.client else '?'}|{body.email}"
    throttle.check(key)
    try:
        user, token, csrf = svc.login(body.email, body.password)
    except AuthenticationError:
        throttle.register_failure(key)
        raise
    throttle.reset(key)
    _set_cookies(resp, settings, token, csrf)
    return svc.me(user)


@router.post("/auth/register", response_model=MeRead, status_code=status.HTTP_201_CREATED,
             summary="Registro rápido de estudiante (abre sesión)")
def register(body: RegisterRequest, request: Request, resp: Response, svc: AuthSvc,
             settings: SettingsDep):
    """Crea una cuenta de ESTUDIANTE con los datos mínimos e inicia su sesión.

    Se puede desactivar con SELF_REGISTRATION=false. Limita los intentos por IP.
    """
    if not settings.self_registration:
        raise ForbiddenError("El registro rápido está deshabilitado. Pide tu cuenta a la administración.")
    throttle = get_register_throttle()
    key = request.client.host if request.client else "?"
    throttle.check(key)
    throttle.register_failure(key)  # cuenta cada intento, exitoso o no
    user, token, csrf = svc.register(body)
    _set_cookies(resp, settings, token, csrf)
    return svc.me(user)


@router.post("/auth/logout", response_model=Message, summary="Cerrar sesión")
def logout(request: Request, resp: Response, db: Annotated[Session, Depends(get_db)],
           svc: AuthSvc, settings: SettingsDep):
    """Limpia las cookies siempre. Si la sesión es válida (y trae CSRF correcto) invalida el token."""
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        try:
            claims = decode_session_token(settings.secret_key.get_secret_value(), token)
            sent = request.headers.get(CSRF_HEADER, "")
            user = db.get(User, claims.user_id)
            if user and user.token_version == claims.version and hmac.compare_digest(
                    sent, claims.csrf):
                svc.logout(user)
        except InvalidToken:
            pass
    _clear_cookies(resp)
    return Message(detail="Sesión cerrada.")


@router.get("/auth/me", response_model=MeRead, summary="Usuario actual")
def me(user: CurrentUser, svc: AuthSvc):
    return svc.me(user)


@router.post("/auth/change-password", response_model=Message, summary="Cambiar contraseña")
def change_password(body: ChangePasswordRequest, resp: Response, user: CurrentUser, svc: AuthSvc):
    svc.change_password(user, body.current_password, body.new_password)
    _clear_cookies(resp)  # el token anterior queda invalidado; hay que iniciar sesión de nuevo
    return Message(detail="Contraseña actualizada. Inicie sesión nuevamente.")


@router.post("/auth/change-email", response_model=MeRead, summary="Cambiar correo de acceso")
def change_email(body: ChangeEmailRequest, user: CurrentUser, svc: AuthSvc):
    svc.change_email(user, body.current_password, body.new_email)
    return svc.me(user)


class ResetPassword(BaseModel):
    new_password: str


@router.get("/users", response_model=Page[UserRead], summary="Listar usuarios (ADMIN)")
def list_users(actor: AdminUser, svc: AuthSvc, pager: Annotated[Pager, Depends()]):
    items, total = svc.list_users(actor, pager.limit, pager.offset)
    return page(items, total, pager)


@router.post("/users/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT,
             summary="Restablecer contraseña (ADMIN)")
def reset_password(user_id: int, body: ResetPassword, actor: AdminUser, svc: AuthSvc):
    svc.admin_reset_password(actor, user_id, _check_password(body.new_password))
