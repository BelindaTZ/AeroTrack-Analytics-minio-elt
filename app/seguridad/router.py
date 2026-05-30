"""Rutas de autenticación: login, logout, perfil (CU-01, CU-02, CU-03)."""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.seguridad.jwt.service import crear_token
from app.shared.clients import pb_client
from app.shared.utils import audit
from app.shared.deps import get_current_user, render, require_user
from app.utils.login_stats import get_login_stats

router = APIRouter()


# ── Login ─────────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    if get_current_user(request):
        return RedirectResponse("/pipeline", status_code=302)
    stats = await get_login_stats()
    return render(request, "login.html", {"error": None, "current_user": None, "user_permissions": {}, "stats": stats})


@router.post("/login", response_class=HTMLResponse)
async def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    ip = request.client.host if request.client else ""
    try:
        _, record = pb_client.auth_user(email, password)
    except ValueError:
        audit.registrar("", email, "login_fallido", "seguridad",
                        ip_address=ip, resultado="fallido",
                        detalle="Credenciales inválidas")
        stats = await get_login_stats()
        return render(request, "login.html",
                      {"error": "Credenciales incorrectas. Verifique su email y contraseña.",
                       "current_user": None, "user_permissions": {}, "stats": stats})

    if not record.get("activo", True):
        audit.registrar(record["id"], email, "login_fallido", "seguridad",
                        ip_address=ip, resultado="fallido",
                        detalle="Cuenta desactivada")
        stats = await get_login_stats()
        return render(request, "login.html",
                      {"error": "Cuenta desactivada. Contacte al administrador.",
                       "current_user": None, "user_permissions": {}, "stats": stats})

    token_payload = {
        "sub": record["id"],
        "email": record.get("email", email),
        "nombre": record.get("nombre", ""),
        "rol_id": record.get("rol_id", ""),
        "activo": record.get("activo", True),
    }
    token = crear_token(token_payload)

    audit.registrar(record["id"], email, "login", "seguridad", ip_address=ip)

    response = RedirectResponse("/pipeline", status_code=302)
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=3600)
    return response


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(request: Request):
    user = get_current_user(request)
    if user:
        audit.registrar(user["sub"], user["email"], "logout", "seguridad")
    response = RedirectResponse("/auth/login?msg=sesion_cerrada", status_code=302)
    response.delete_cookie("access_token")
    return response


# ── Perfil ────────────────────────────────────────────────────────────────────

@router.get("/perfil", response_class=HTMLResponse)
async def perfil(request: Request):
    user = require_user(request)
    record = pb_client.get_record("app_users", user["sub"], expand="rol_id")
    rol = record.get("expand", {}).get("rol_id", {}) if record else {}
    return render(request, "perfil.html", {"record": record, "rol": rol, "msg": None, "error": None})


@router.post("/perfil/password", response_class=HTMLResponse)
async def cambiar_password(
    request: Request,
    password_actual: str = Form(...),
    password_nuevo: str = Form(...),
    password_confirm: str = Form(...),
):
    user = require_user(request)
    record = pb_client.get_record("app_users", user["sub"], expand="rol_id")
    rol = record.get("expand", {}).get("rol_id", {}) if record else {}

    if password_nuevo != password_confirm:
        return render(request, "perfil.html",
                      {"record": record, "rol": rol,
                       "error": "Las contraseñas no coinciden.", "msg": None})

    # Verificar contraseña actual intentando autenticar
    try:
        pb_client.auth_user(user["email"], password_actual)
    except ValueError:
        return render(request, "perfil.html",
                      {"record": record, "rol": rol,
                       "error": "Contraseña actual incorrecta.", "msg": None})

    pb_client.change_user_password(user["sub"], password_nuevo)
    audit.registrar(user["sub"], user["email"], "editar", "seguridad",
                    recurso_tipo="password", recurso_id=user["sub"])
    return render(request, "perfil.html",
                  {"record": record, "rol": rol,
                   "msg": "Contraseña actualizada correctamente.", "error": None})
