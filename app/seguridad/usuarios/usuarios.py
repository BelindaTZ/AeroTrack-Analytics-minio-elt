"""CRUD de usuarios (CU-04) — solo Administrador."""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.shared.clients import pb_client
from app.shared.utils import audit, email_utils
from app.shared.utils.password_utils import generar_contrasena_temporal
from app.shared.deps import render, require_permission

router = APIRouter()
_perm = require_permission("seguridad", "ver")


@router.get("", response_class=HTMLResponse)
async def lista(request: Request, page: int = 1, q: str = "", rol_id: str = "", activo: str = ""):
    _perm(request)
    filter_parts = []
    if q:
        filter_parts.append(f'(nombre~"{q}"||email~"{q}")')
    if rol_id:
        filter_parts.append(f'rol_id="{rol_id}"')
    if activo in ("true", "false"):
        filter_parts.append(f'activo={activo}')
    filt = "&&".join(filter_parts) if filter_parts else ""
    usuarios = pb_client.list_records("app_users", filter=filt, expand="rol_id",
                                      page=page, per_page=20, sort="-created")
    total_all = len(pb_client.list_records_all("app_users", filter=filt))
    roles = pb_client.list_records("roles")
    return render(request, "usuarios/lista.html", {
        "usuarios": usuarios, "roles": roles,
        "q": q, "filtro_rol": rol_id, "filtro_activo": activo,
        "page": page, "total": total_all, "per_page": 20,
        "total_pages": max(1, -(-total_all // 20)),
    })


@router.post("", response_class=HTMLResponse)
async def crear(
    request: Request,
    nombre: str = Form(...),
    email: str = Form(...),
    rol_id: str = Form(...),
):
    user = require_permission("seguridad", "crear")(request)
    password = generar_contrasena_temporal(nombre)
    try:
        record = pb_client.create_record("app_users", {
            "nombre": nombre, "email": email, "rol_id": rol_id,
            "password": password, "passwordConfirm": password,
            "activo": True, "emailVisibility": True,
        })
    except ValueError as exc:
        roles = pb_client.list_records("roles")
        return render(request, "usuarios/lista.html", {
            "usuarios": pb_client.list_records("app_users", expand="rol_id"),
            "roles": roles, "q": "", "filtro_rol": "", "filtro_activo": "",
            "page": 1, "total": 0, "per_page": 20, "total_pages": 1,
            "error_crear": str(exc),
        })

    audit.registrar(user["sub"], user["email"], "crear", "seguridad",
                    recurso_tipo="usuario", recurso_id=record["id"],
                    detalle=f"email={email} rol={rol_id}")

    login_url = str(request.base_url) + "auth/login"
    err_email = email_utils.send_welcome_email(email, nombre, password, login_url)
    msg = "Usuario creado exitosamente."
    if err_email:
        msg += f" No se pudo enviar el email de bienvenida — verifique la configuración SMTP."

    return RedirectResponse(f"/auth/usuarios?msg={msg}", status_code=303)


@router.get("/{uid}", response_class=HTMLResponse)
async def editar_form(request: Request, uid: str):
    _perm(request)
    record = pb_client.get_record("app_users", uid, expand="rol_id")
    if not record:
        return RedirectResponse("/auth/usuarios", status_code=302)
    roles = pb_client.list_records("roles")
    return render(request, "usuarios/form.html", {"record": record, "roles": roles, "error": None})


@router.post("/{uid}", response_class=HTMLResponse)
async def editar_guardar(
    request: Request,
    uid: str,
    nombre: str = Form(...),
    email: str = Form(...),
    rol_id: str = Form(...),
):
    user = require_permission("seguridad", "editar")(request)
    try:
        pb_client.update_record("app_users", uid, {"nombre": nombre, "email": email, "rol_id": rol_id})
    except ValueError as exc:
        record = pb_client.get_record("app_users", uid, expand="rol_id")
        roles = pb_client.list_records("roles")
        return render(request, "usuarios/form.html", {"record": record, "roles": roles, "error": str(exc)})

    audit.registrar(user["sub"], user["email"], "editar", "seguridad",
                    recurso_tipo="usuario", recurso_id=uid,
                    detalle=f"nombre={nombre} email={email} rol={rol_id}")
    return RedirectResponse("/auth/usuarios?msg=Usuario actualizado.", status_code=303)


@router.post("/{uid}/estado", response_class=HTMLResponse)
async def toggle_estado(request: Request, uid: str):
    user = require_permission("seguridad", "editar")(request)
    if uid == user["sub"]:
        return RedirectResponse("/auth/usuarios?error=No puedes desactivar tu propia cuenta.", status_code=303)
    record = pb_client.get_record("app_users", uid)
    if not record:
        return RedirectResponse("/auth/usuarios", status_code=302)
    nuevo_estado = not record.get("activo", True)
    pb_client.update_record("app_users", uid, {"activo": nuevo_estado})
    audit.registrar(user["sub"], user["email"],
                    "editar", "seguridad", recurso_tipo="usuario", recurso_id=uid,
                    detalle=f"activo={nuevo_estado}")
    return RedirectResponse("/auth/usuarios", status_code=303)


@router.post("/{uid}/reset-password")
async def reset_password(request: Request, uid: str, nombre: str = Form("")):
    user = require_permission("seguridad", "editar")(request)
    record = pb_client.get_record("app_users", uid)
    if not record:
        return RedirectResponse("/auth/usuarios", status_code=302)
    nombre_usuario = nombre or record.get("nombre", "usuario")
    nueva_pass = generar_contrasena_temporal(nombre_usuario)
    pb_client.change_user_password(uid, nueva_pass)
    audit.registrar(user["sub"], user["email"], "editar", "seguridad",
                    recurso_tipo="password_reset", recurso_id=uid)
    return RedirectResponse(f"/auth/usuarios?msg=Contraseña reseteada: {nueva_pass}", status_code=303)
