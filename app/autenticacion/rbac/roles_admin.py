"""CRUD de roles (CU-05, CU-06, CU-07) — solo Administrador."""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.shared.clients import pb_client
from app.shared.utils import audit
from app.shared.deps import render, require_permission

router = APIRouter()
_perm = require_permission("seguridad", "ver")


@router.get("", response_class=HTMLResponse)
async def lista(request: Request):
    _perm(request)
    roles = pb_client.list_records("roles", sort="nombre")
    for rol in roles:
        rol["_count_usuarios"] = pb_client.list_records_all(
            "app_users", filter=f'rol_id="{rol["id"]}"').__len__()
    return render(request, "roles/lista.html", {"roles": roles})


@router.post("", response_class=HTMLResponse)
async def crear(request: Request, nombre: str = Form(...), descripcion: str = Form("")):
    user = require_permission("seguridad", "crear")(request)
    try:
        record = pb_client.create_record("roles", {"nombre": nombre, "descripcion": descripcion,
                                                    "es_sistema": False, "activo": True})
    except ValueError as exc:
        roles = pb_client.list_records("roles")
        return render(request, "roles/lista.html", {"roles": roles, "error": str(exc)})
    audit.registrar(user["sub"], user["email"], "crear", "seguridad",
                    recurso_tipo="rol", recurso_id=record["id"], detalle=f"nombre={nombre}")
    return RedirectResponse("/auth/roles?msg=Rol creado.", status_code=303)


@router.get("/{rid}", response_class=HTMLResponse)
async def editar_form(request: Request, rid: str):
    _perm(request)
    rol = pb_client.get_record("roles", rid)
    if not rol:
        return RedirectResponse("/auth/roles", status_code=302)
    return render(request, "roles/form.html", {"rol": rol, "error": None})


@router.post("/{rid}", response_class=HTMLResponse)
async def editar_guardar(request: Request, rid: str, nombre: str = Form(...), descripcion: str = Form("")):
    user = require_permission("seguridad", "editar")(request)
    rol = pb_client.get_record("roles", rid)
    if not rol:
        return RedirectResponse("/auth/roles", status_code=302)
    if rol.get("es_sistema"):
        return RedirectResponse("/auth/roles?error=Rol de sistema no editable.", status_code=303)
    try:
        pb_client.update_record("roles", rid, {"nombre": nombre, "descripcion": descripcion})
    except ValueError as exc:
        return render(request, "roles/form.html", {"rol": rol, "error": str(exc)})
    audit.registrar(user["sub"], user["email"], "editar", "seguridad",
                    recurso_tipo="rol", recurso_id=rid, detalle=f"nombre={nombre}")
    return RedirectResponse("/auth/roles?msg=Rol actualizado.", status_code=303)


@router.post("/{rid}/eliminar")
async def eliminar(request: Request, rid: str):
    user = require_permission("seguridad", "eliminar")(request)
    rol = pb_client.get_record("roles", rid)
    if not rol:
        return RedirectResponse("/auth/roles", status_code=302)
    if rol.get("es_sistema"):
        return RedirectResponse("/auth/roles?error=No se puede eliminar un rol del sistema.", status_code=303)
    usuarios = pb_client.list_records_all("app_users", filter=f'rol_id="{rid}"')
    if usuarios:
        return RedirectResponse(
            f"/auth/roles?error=El rol tiene {len(usuarios)} usuario(s) asignado(s). Reasígnalos primero.",
            status_code=303)
    for rp in pb_client.list_records_all("roles_permisos", filter=f'rol_id="{rid}"'):
        pb_client.delete_record("roles_permisos", rp["id"])
    pb_client.delete_record("roles", rid)
    audit.registrar(user["sub"], user["email"], "eliminar", "seguridad",
                    recurso_tipo="rol", recurso_id=rid)
    return RedirectResponse("/auth/roles?msg=Rol eliminado.", status_code=303)
