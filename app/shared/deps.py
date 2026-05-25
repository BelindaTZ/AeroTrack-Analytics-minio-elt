"""Dependencias FastAPI reutilizables: autenticación JWT y verificación RBAC."""

import time
from typing import Optional

from fastapi import Request
from fastapi.responses import RedirectResponse
from jose import JWTError

from app.autenticacion.jwt.service import verificar_token
from app.shared.clients import pb_client
from app.shared.templates import templates, MODULOS_SIDEBAR, MODULOS_ADMIN

# Cache de permisos por rol: {rol_id: {expires, permissions: {modulo: [accion]}}}
_perm_cache: dict[str, dict] = {}
_PERM_TTL = 300  # 5 minutos


def _get_cached_permissions(rol_id: str) -> dict[str, list[str]]:
    entry = _perm_cache.get(rol_id)
    if entry and time.time() < entry["expires"]:
        return entry["permissions"]
    perms = pb_client.get_permissions_for_role(rol_id)
    _perm_cache[rol_id] = {"expires": time.time() + _PERM_TTL, "permissions": perms}
    return perms


def invalidate_permission_cache(rol_id: Optional[str] = None) -> None:
    """Invalida el caché de permisos (llamar al guardar cambios de permisos)."""
    if rol_id:
        _perm_cache.pop(rol_id, None)
    else:
        _perm_cache.clear()


def get_current_user(request: Request) -> Optional[dict]:
    """Decodifica el JWT de la cookie. Retorna el payload del usuario o None."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = verificar_token(token)
        return payload
    except JWTError:
        return None


def require_user(request: Request) -> dict:
    """Dependencia: redirige a /auth/login si no hay sesión válida."""
    user = get_current_user(request)
    if not user:
        raise _redirect_to_login()
    return user


class _redirect_to_login(Exception):
    pass


def user_permissions(request: Request) -> dict[str, list[str]]:
    """Retorna las permisos del usuario autenticado ({modulo: [acciones]})."""
    user = get_current_user(request)
    if not user:
        return {}
    return _get_cached_permissions(user.get("rol_id", ""))


def has_permission(permissions: dict[str, list[str]], modulo: str, accion: str) -> bool:
    return accion in permissions.get(modulo, [])


def require_permission(modulo: str, accion: str):
    """Devuelve una dependencia FastAPI que verifica un permiso específico."""
    def _check(request: Request):
        user = get_current_user(request)
        if not user:
            raise _redirect_to_login()
        perms = _get_cached_permissions(user.get("rol_id", ""))
        if not has_permission(perms, modulo, accion):
            raise PermissionError(f"Sin permiso {modulo}.{accion}")
        return user
    return _check


def render(request: Request, template: str, ctx: dict, status: int = 200):
    """Helper para renderizar templates inyectando sidebar y usuario."""
    user = get_current_user(request)
    perms = _get_cached_permissions(user["rol_id"]) if user else {}

    ctx.setdefault("current_user", user)
    ctx.setdefault("user_permissions", perms)
    ctx.setdefault("modulos_sidebar", MODULOS_SIDEBAR)
    ctx.setdefault("modulos_admin", MODULOS_ADMIN if has_permission(perms, "seguridad", "ver") else [])

    return templates.TemplateResponse(request=request, name=template, context=ctx, status_code=status)
