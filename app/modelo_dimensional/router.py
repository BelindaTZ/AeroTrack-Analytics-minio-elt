"""CRUD del modelo dimensional con RBAC y auditoría (CU-14, CU-15, CU-16).

IMPORTANTE: las rutas estáticas (/validar) van ANTES que las dinámicas (/{tabla})
para evitar que FastAPI las confunda.
"""

import csv
import io
import json

import pandas as pd
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse

from app.modelo_dimensional.data import service as svc
from app.shared.deps import render, require_permission
from app.shared.templates import TABLAS
from app.shared.utils import audit

router = APIRouter()
_perm_ver = require_permission("modelo_dimensional", "ver")


def _tmpl_error(request, msg: str, status: int = 404):
    return render(request, "error.html", {"mensaje": msg, "codigo": status}, status=status)


# ── Lista de tablas con métricas (CU-14) — /modelo ───────────────────────────
@router.get("", response_class=HTMLResponse)
async def lista_tablas(request: Request):
    _perm_ver(request)
    tablas = svc.listar_tablas_con_metricas()
    return render(request, "modelo_dimensional/lista_tablas.html", {"tablas": tablas})


# ── Validar integridad (CU-16) — /modelo/validar ─────────────────────────────
# Definidas ANTES que /{tabla} para evitar conflicto de rutas


@router.get("/validar", response_class=HTMLResponse)
async def validar_form(request: Request):
    require_permission("modelo_dimensional", "ejecutar")(request)
    return render(request, "modelo_dimensional/validacion.html", {"resultado": None})


@router.post("/validar", response_class=HTMLResponse)
async def validar_ejecutar(request: Request):
    user = require_permission("modelo_dimensional", "ejecutar")(request)
    resultado = svc.validar_integridad()
    audit.registrar(
        user["sub"],
        user["email"],
        "validar",
        "modelo_dimensional",
        detalle=json.dumps({"ok": resultado["ok"], "errores": len(resultado["errores"])}),
    )
    return render(request, "modelo_dimensional/validacion.html", {"resultado": resultado})


@router.get("/validar/export")
async def validar_export(request: Request):
    require_permission("modelo_dimensional", "exportar")(request)
    resultado = svc.validar_integridad()
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["tabla", "columna", "tipo", "descripcion"])
    writer.writeheader()
    for err in resultado["errores"]:
        writer.writerow({k: err.get(k, "") for k in ["tabla", "columna", "tipo", "descripcion"]})
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=validacion_integridad.csv"},
    )


# ── Crear registro — /modelo/{tabla}/nuevo ────────────────────────────────────
# También va ANTES de /{tabla}/{pk_val}/... para que "nuevo" no sea confundido como pk_val


@router.get("/{tabla}/nuevo", response_class=HTMLResponse)
async def nuevo_form(request: Request, tabla: str):
    require_permission("modelo_dimensional", "crear")(request)
    if tabla not in TABLAS:
        return _tmpl_error(request, f"Tabla '{tabla}' no existe.")
    try:
        df = svc._load(tabla)
    except FileNotFoundError:
        return _tmpl_error(request, f"Tabla '{tabla}' no disponible.")
    pk = TABLAS[tabla]["pk"]
    columnas = list(df.columns)
    dtypes = {col: str(df[col].dtype) for col in columnas}
    return render(
        request,
        "modelo_dimensional/form_registro.html",
        {
            "tabla": tabla,
            "tabla_info": TABLAS[tabla],
            "modo": "crear",
            "columnas": columnas,
            "dtypes": dtypes,
            "pk": pk,
            "registro": {},
            "error": None,
        },
    )


@router.post("/{tabla}/nuevo", response_class=HTMLResponse)
async def nuevo_guardar(request: Request, tabla: str):
    user = require_permission("modelo_dimensional", "crear")(request)
    if tabla not in TABLAS:
        return _tmpl_error(request, f"Tabla '{tabla}' no existe.")
    form = await request.form()
    try:
        nuevo = svc.crear_registro(tabla, dict(form))
    except Exception as exc:
        return _tmpl_error(request, str(exc), 500)
    audit.registrar(
        user["sub"],
        user["email"],
        "crear",
        "modelo_dimensional",
        recurso_tipo=tabla,
        recurso_id=str(nuevo.get(TABLAS[tabla]["pk"], "")),
    )
    return RedirectResponse(f"/modelo/{tabla}?msg=created", status_code=303)


# ── Ver, Editar, Eliminar registro ────────────────────────────────────────────


@router.get("/{tabla}/{pk_val}/ver", response_class=HTMLResponse)
async def ver_registro(request: Request, tabla: str, pk_val: str):
    _perm_ver(request)
    if tabla not in TABLAS:
        return _tmpl_error(request, f"Tabla '{tabla}' no existe.")
    try:
        df = svc._load(tabla)
    except FileNotFoundError:
        return _tmpl_error(request, f"Tabla '{tabla}' no disponible.")
    pk = TABLAS[tabla]["pk"]
    df[pk] = df[pk].astype(str)
    row = df[df[pk] == pk_val]
    if row.empty:
        return _tmpl_error(request, f"Registro {pk}={pk_val} no encontrado en '{tabla}'.")
    registro = row.where(pd.notna(row), other=None).iloc[0].to_dict()
    return render(
        request,
        "modelo_dimensional/detalle_registro.html",
        {
            "tabla": tabla,
            "tabla_info": TABLAS[tabla],
            "pk": pk,
            "pk_val": pk_val,
            "registro": registro,
        },
    )


@router.get("/{tabla}/{pk_val}/editar", response_class=HTMLResponse)
async def editar_form(request: Request, tabla: str, pk_val: str):
    require_permission("modelo_dimensional", "editar")(request)
    if tabla not in TABLAS:
        return _tmpl_error(request, f"Tabla '{tabla}' no existe.")
    try:
        df = svc._load(tabla)
    except FileNotFoundError:
        return _tmpl_error(request, f"Tabla '{tabla}' no disponible.")
    pk = TABLAS[tabla]["pk"]
    df[pk] = df[pk].astype(str)
    row = df[df[pk] == pk_val]
    if row.empty:
        return _tmpl_error(request, f"Registro {pk}={pk_val} no encontrado.")
    registro = row.where(pd.notna(row), other=None).iloc[0].to_dict()
    columnas = list(df.columns)
    dtypes = {col: str(df[col].dtype) for col in columnas}
    return render(
        request,
        "modelo_dimensional/form_registro.html",
        {
            "tabla": tabla,
            "tabla_info": TABLAS[tabla],
            "modo": "editar",
            "columnas": columnas,
            "dtypes": dtypes,
            "pk": pk,
            "pk_val": pk_val,
            "registro": registro,
            "error": None,
        },
    )


@router.post("/{tabla}/{pk_val}/editar", response_class=HTMLResponse)
async def editar_guardar(request: Request, tabla: str, pk_val: str):
    user = require_permission("modelo_dimensional", "editar")(request)
    if tabla not in TABLAS:
        return _tmpl_error(request, f"Tabla '{tabla}' no existe.")
    form = await request.form()
    try:
        svc.editar_registro(tabla, pk_val, dict(form))
    except Exception as exc:
        return _tmpl_error(request, str(exc), 500)
    audit.registrar(user["sub"], user["email"], "editar", "modelo_dimensional", recurso_tipo=tabla, recurso_id=pk_val)
    return RedirectResponse(f"/modelo/{tabla}?msg=updated", status_code=303)


@router.post("/{tabla}/{pk_val}/eliminar")
async def eliminar(request: Request, tabla: str, pk_val: str):
    user = require_permission("modelo_dimensional", "eliminar")(request)
    if tabla not in TABLAS:
        return _tmpl_error(request, f"Tabla '{tabla}' no existe.")
    if pk_val in ("0", "0.0"):
        return _tmpl_error(request, "El registro pk=0 es inmutable.", 403)
    try:
        svc.eliminar_registro(tabla, pk_val)
    except Exception as exc:
        return _tmpl_error(request, str(exc), 500)
    audit.registrar(user["sub"], user["email"], "eliminar", "modelo_dimensional", recurso_tipo=tabla, recurso_id=pk_val)
    return RedirectResponse(f"/modelo/{tabla}?msg=deleted", status_code=303)


# ── Lista de registros paginada (CU-15) — /modelo/{tabla} ────────────────────
# Va AL FINAL para no capturar /validar ni /nuevo


@router.get("/{tabla}", response_class=HTMLResponse)
async def lista_registros(request: Request, tabla: str, page: int = 1, q: str = ""):
    _perm_ver(request)
    if tabla not in TABLAS:
        return _tmpl_error(request, f"Tabla '{tabla}' no existe.")
    try:
        df = svc._load(tabla)
    except FileNotFoundError:
        return _tmpl_error(request, f"La tabla '{tabla}' no está disponible en MinIO aún.")
    paginado = svc.paginar(df, page, q)
    return render(
        request,
        "modelo_dimensional/lista_registros.html",
        {
            "tabla": tabla,
            "tabla_info": TABLAS[tabla],
            **paginado,
            "q": q,
        },
    )
