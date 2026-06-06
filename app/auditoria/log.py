"""Módulo de auditoría — log inmutable (CU-39, CU-40)."""

import csv
import io
import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from app.shared.clients import pb_client
from app.shared.deps import render, require_permission

router = APIRouter()
_perm_ver = require_permission("seguridad", "ver")

_PAGE_SIZE = 50


@router.get("", response_class=HTMLResponse)
def log_auditoria(
    request: Request,
    page: int = 1,
    modulo: str = "",
    accion: str = "",
    usuario: str = "",
    resultado: str = "",
    desde: str = "",
    hasta: str = "",
):
    user = _perm_ver(request)

    filtros_pb = []
    if modulo:
        filtros_pb.append(f'modulo="{modulo}"')
    if accion:
        filtros_pb.append(f'accion="{accion}"')
    if usuario:
        filtros_pb.append(f'(usuario_email~"{usuario}"||usuario_id="{usuario}")')
    if resultado:
        filtros_pb.append(f'resultado="{resultado}"')
    if desde:
        filtros_pb.append(f'created>="{desde} 00:00:00"')
    if hasta:
        filtros_pb.append(f'created<="{hasta} 23:59:59"')

    filter_str = "&&".join(filtros_pb)

    registros = pb_client.list_records(
        "auditoria",
        filter=filter_str,
        sort="-created",
        page=page,
        per_page=_PAGE_SIZE,
    )

    # Contar total para paginación
    total = len(pb_client.list_records_all("auditoria", filter=filter_str)) if filter_str else None

    # Módulos y acciones disponibles para filtros
    modulos_disponibles = _get_distinct("modulo")
    acciones_disponibles = _get_distinct("accion")

    return render(request, "auditoria/index.html", {
        "registros": registros,
        "page": page,
        "page_size": _PAGE_SIZE,
        "total": total,
        "has_next": len(registros) == _PAGE_SIZE,
        "has_prev": page > 1,
        "filtros": {
            "modulo": modulo, "accion": accion, "usuario": usuario,
            "resultado": resultado, "desde": desde, "hasta": hasta,
        },
        "modulos_disponibles": modulos_disponibles,
        "acciones_disponibles": acciones_disponibles,
    })


@router.get("/export")
def export_csv(
    request: Request,
    modulo: str = "",
    accion: str = "",
    usuario: str = "",
    resultado: str = "",
    desde: str = "",
    hasta: str = "",
):
    _perm_ver(request)

    filtros_pb = []
    if modulo:
        filtros_pb.append(f'modulo="{modulo}"')
    if accion:
        filtros_pb.append(f'accion="{accion}"')
    if usuario:
        filtros_pb.append(f'(usuario_email~"{usuario}"||usuario_id="{usuario}")')
    if resultado:
        filtros_pb.append(f'resultado="{resultado}"')
    if desde:
        filtros_pb.append(f'created>="{desde} 00:00:00"')
    if hasta:
        filtros_pb.append(f'created<="{hasta} 23:59:59"')

    filter_str = "&&".join(filtros_pb)
    registros = pb_client.list_records_all("auditoria", filter=filter_str, sort="-created")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Fecha", "Usuario", "Email", "Módulo", "Acción", "Recurso tipo",
                     "Recurso ID", "Resultado", "IP", "Detalle"])
    for r in registros:
        writer.writerow([
            r.get("created", "")[:19],
            r.get("usuario_id", ""),
            r.get("usuario_email", ""),
            r.get("modulo", ""),
            r.get("accion", ""),
            r.get("recurso_tipo", ""),
            r.get("recurso_id", ""),
            r.get("resultado", ""),
            r.get("ip_address", ""),
            r.get("detalle", ""),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=auditoria.csv"},
    )


def _get_distinct(campo: str) -> list[str]:
    try:
        rows = pb_client.list_records_all("auditoria")
        values = sorted({r.get(campo, "") for r in rows if r.get(campo)})
        return values
    except Exception:
        return []
