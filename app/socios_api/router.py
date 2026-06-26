"""Administración de socios API: claves, webhooks e historial."""

import hashlib
import secrets
from datetime import timedelta, timezone

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.shared.clients import pb_client as pb
from app.shared.deps import render, require_permission
from app.shared.utils import audit

_TZ = timezone(timedelta(hours=-5))

router = APIRouter()
_perm_ver = require_permission("socios_api", "ver")
_perm_crear = require_permission("socios_api", "crear")
_perm_config = require_permission("socios_api", "configurar")
_perm_eliminar = require_permission("socios_api", "eliminar")

_EVENTOS_VALIDOS = ["pipeline_completado", "alerta_otp", "reporte_generado"]


@router.get("", response_class=HTMLResponse)
def index(request: Request):
    user = _perm_ver(request)
    try:
        claves = pb.list_records_all("pb_api_claves", sort="-created")
    except Exception:
        claves = []
    webhooks_por_clave = {}
    for c in claves:
        try:
            wh = pb.list_records_all("pb_api_webhooks", filter=f'clave_id="{c["id"]}"')
        except Exception:
            wh = []
        webhooks_por_clave[c["id"]] = wh
    return render(
        request,
        "socios_api/index.html",
        {
            "claves": claves,
            "webhooks_por_clave": webhooks_por_clave,
            "eventos_disponibles": _EVENTOS_VALIDOS,
        },
    )


@router.post("/claves")
async def crear_clave(request: Request):
    user = _perm_crear(request)
    body = await request.json()
    nombre = str(body.get("nombre", "")).strip()
    if not nombre:
        return JSONResponse({"error": "nombre requerido"}, status_code=400)

    clave_plana = f"at_{secrets.token_hex(32)}"
    clave_hash = hashlib.sha256(clave_plana.encode()).hexdigest()

    try:
        record = pb.create_record(
            "pb_api_claves",
            {
                "nombre": nombre,
                "clave_hash": clave_hash,
                "permisos": body.get("permisos", []),
                "limite_diario": int(body.get("limite_diario", 1000)),
                "consultas_hoy": 0,
                "consultas_total": 0,
                "activa": True,
                "expiracion": body.get("expiracion", ""),
            },
        )
        audit.registrar(
            user["sub"], user["email"], "crear", "socios_api", recurso_tipo="api_clave", recurso_id=record.get("id", "")
        )
        return JSONResponse(
            {
                **record,
                "clave_plana": clave_plana,
                "advertencia": "Guarda esta clave en un lugar seguro. No se mostrará nuevamente.",
            }
        )
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@router.post("/claves/{id}/revocar")
async def revocar_clave(request: Request, id: str):
    user = _perm_eliminar(request)
    try:
        pb.update_record("pb_api_claves", id, {"activa": False})
        audit.registrar(
            user["sub"],
            user["email"],
            "eliminar",
            "socios_api",
            recurso_tipo="api_clave",
            recurso_id=id,
            detalle="revocada",
        )
        return JSONResponse({"ok": True})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@router.post("/webhooks")
async def crear_webhook(request: Request):
    user = _perm_config(request)
    body = await request.json()
    clave_id = str(body.get("clave_id", "")).strip()
    if not clave_id:
        return JSONResponse({"error": "clave_id requerido"}, status_code=400)

    eventos = body.get("eventos", [])
    if not eventos:
        return JSONResponse({"error": "Al menos un evento requerido"}, status_code=400)
    invalidos = [e for e in eventos if e not in _EVENTOS_VALIDOS]
    if invalidos:
        return JSONResponse({"error": f"Eventos inválidos: {invalidos}"}, status_code=400)

    try:
        record = pb.create_record(
            "pb_api_webhooks",
            {
                "nombre": str(body.get("nombre", "")).strip(),
                "clave_id": clave_id,
                "url": str(body.get("url", "")).strip(),
                "eventos": eventos,
                "clave_hmac": str(body.get("clave_hmac", "")).strip(),
                "activo": True,
                "ultimo_estado": "pendiente",
            },
        )
        audit.registrar(
            user["sub"],
            user["email"],
            "configurar",
            "socios_api",
            recurso_tipo="webhook",
            recurso_id=record.get("id", ""),
        )
        return JSONResponse(record)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@router.post("/webhooks/{id}/toggle")
async def toggle_webhook(request: Request, id: str):
    user = _perm_config(request)
    body = await request.json()
    activo = body.get("activo", True)
    try:
        record = pb.update_record("pb_api_webhooks", id, {"activo": bool(activo)})
        return JSONResponse(record)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@router.get("/historial", response_class=HTMLResponse)
def historial(request: Request, socio: str = "", endpoint: str = "", desde: str = "", hasta: str = ""):
    user = _perm_ver(request)
    try:
        todos = pb.list_records_all("pb_api_historial", sort="-created")
    except Exception:
        todos = []

    if socio:
        todos = [r for r in todos if r.get("clave_id") == socio]
    if endpoint:
        todos = [r for r in todos if endpoint.lower() in (r.get("endpoint") or "").lower()]
    if desde:
        todos = [r for r in todos if (r.get("created") or "") >= desde]
    if hasta:
        todos = [r for r in todos if (r.get("created") or "") <= hasta]

    try:
        claves_map = {c["id"]: c["nombre"] for c in pb.list_records_all("pb_api_claves")}
    except Exception:
        claves_map = {}
    for r in todos:
        r["socio_nombre"] = claves_map.get(r.get("clave_id", ""), r.get("clave_id", ""))

    return render(
        request,
        "socios_api/historial.html",
        {
            "historial": todos[:200],
            "claves": list(claves_map.items()),
            "filtro_socio": socio,
            "filtro_endpoint": endpoint,
            "filtro_desde": desde,
            "filtro_hasta": hasta,
        },
    )


@router.get("/historial/json")
def historial_json(request: Request, socio: str = "", endpoint: str = "", desde: str = "", hasta: str = ""):
    _perm_ver(request)
    try:
        todos = pb.list_records_all("pb_api_historial", sort="-created")
    except Exception:
        todos = []
    if socio:
        todos = [r for r in todos if r.get("clave_id") == socio]
    if endpoint:
        todos = [r for r in todos if endpoint.lower() in (r.get("endpoint") or "").lower()]
    return JSONResponse(todos[:200])
