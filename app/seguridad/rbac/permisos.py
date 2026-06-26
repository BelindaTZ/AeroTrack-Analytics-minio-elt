"""Gestión de permisos por rol y vista de matriz (CU-08, CU-09)."""

import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.shared.clients import pb_client
from app.shared.deps import invalidate_permission_cache, render, require_permission
from app.shared.utils import audit

router = APIRouter()
_perm = require_permission("seguridad", "ver")

_TODAS_ACCIONES = ["ver", "crear", "editar", "eliminar", "ejecutar", "exportar", "configurar"]


def _permisos_de_rol(rid: str) -> dict[str, list[str]]:
    """Retorna {modulo_clave: [accion]} para el rol dado."""
    rows = pb_client.list_records_all(
        "roles_permisos", filter=f'rol_id="{rid}"', expand="permiso_id,permiso_id.modulo_id"
    )
    result: dict[str, list[str]] = {}
    for row in rows:
        expanded = row.get("expand", {})
        permiso = expanded.get("permiso_id", {})
        mod_exp = permiso.get("expand", {}).get("modulo_id", {})
        clave = mod_exp.get("clave", "")
        accion = permiso.get("accion", "")
        if clave and accion:
            result.setdefault(clave, []).append(accion)
    return result


@router.get("/{rid}/permisos", response_class=HTMLResponse)
async def gestionar_permisos(request: Request, rid: str):
    _perm(request)
    rol = pb_client.get_record("roles", rid)
    if not rol:
        return RedirectResponse("/auth/roles", status_code=302)
    modulos = pb_client.list_records("modulos", sort="orden")
    permisos_actuales = _permisos_de_rol(rid)
    permisos_disponibles = pb_client.list_records_all("permisos", expand="modulo_id")
    return render(
        request,
        "roles/permisos.html",
        {
            "rol": rol,
            "modulos": modulos,
            "permisos_actuales": permisos_actuales,
            "permisos_disponibles": permisos_disponibles,
            "todas_acciones": _TODAS_ACCIONES,
        },
    )


@router.post("/{rid}/permisos", response_class=HTMLResponse)
async def guardar_permisos(request: Request, rid: str):
    user = require_permission("seguridad", "configurar")(request)
    form = await request.form()

    todos_permisos = pb_client.list_records_all("permisos", expand="modulo_id")
    perm_map: dict[tuple, str] = {}
    for p in todos_permisos:
        mod_exp = p.get("expand", {}).get("modulo_id", {})
        clave = mod_exp.get("clave", "")
        accion = p.get("accion", "")
        if clave and accion:
            perm_map[(clave, accion)] = p["id"]

    seleccionados: set[str] = set()
    for key in form.keys():
        if key.startswith("perm_"):
            parts = key[5:].rsplit("_", 1)
            if len(parts) == 2:
                modulo_clave, accion = parts[0], parts[1]
                pid = perm_map.get((modulo_clave, accion))
                if pid:
                    seleccionados.add(pid)

    existentes = pb_client.list_records_all("roles_permisos", filter=f'rol_id="{rid}"')
    for rp in existentes:
        pb_client.delete_record("roles_permisos", rp["id"])

    for pid in seleccionados:
        pb_client.create_record("roles_permisos", {"rol_id": rid, "permiso_id": pid})

    invalidate_permission_cache(rid)
    audit.registrar(
        user["sub"],
        user["email"],
        "configurar",
        "seguridad",
        recurso_tipo="permisos_rol",
        recurso_id=rid,
        detalle=json.dumps({"permisos_count": len(seleccionados)}),
    )
    return RedirectResponse(f"/auth/roles/{rid}/permisos?msg=Permisos guardados.", status_code=303)


@router.get("/matriz", response_class=HTMLResponse)
async def matriz(request: Request):
    _perm(request)
    roles = pb_client.list_records("roles", sort="nombre")
    modulos = pb_client.list_records("modulos", sort="orden")
    matriz: dict[str, dict] = {}
    for rol in roles:
        matriz[rol["id"]] = _permisos_de_rol(rol["id"])
    return render(
        request,
        "roles/matriz.html",
        {
            "roles": roles,
            "modulos": modulos,
            "matriz": matriz,
            "todas_acciones": _TODAS_ACCIONES,
        },
    )
