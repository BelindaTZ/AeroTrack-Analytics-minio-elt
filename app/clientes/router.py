"""Gestión de clientes, suscripciones, demos y entregas (Lote 5)."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.shared.clients import pb_client as pb
from app.shared.deps import render, require_permission
from app.shared.utils import audit

_TZ = timezone(timedelta(hours=-5))

router = APIRouter()
_perm_ver    = require_permission("clientes", "ver")
_perm_crear  = require_permission("clientes", "crear")
_perm_editar = require_permission("clientes", "editar")

_FRECUENCIA_DIAS = {"diaria": 1, "semanal": 7, "mensual": 30}


def _calcular_proxima_entrega(frecuencia: str) -> str:
    dias = _FRECUENCIA_DIAS.get(frecuencia, 30)
    return (datetime.now(_TZ) + timedelta(days=dias)).strftime("%Y-%m-%dT00:00:00.000Z")


@router.get("", response_class=HTMLResponse)
def index(request: Request):
    user = _perm_ver(request)
    try:
        todos = pb.list_records_all("pb_clientes", sort="-created")
    except Exception:
        todos = []
    activos = sum(1 for c in todos if c.get("activo"))
    inactivos = len(todos) - activos
    en_prueba = sum(1 for c in todos if c.get("tipo_servicio") == "basico")
    return render(request, "clientes/index.html", {
        "clientes":  todos,
        "activos":   activos,
        "inactivos": inactivos,
        "en_prueba": en_prueba,
        "total":     len(todos),
    })


@router.post("")
async def crear(request: Request):
    user = _perm_crear(request)
    body = await request.json()
    try:
        record = pb.create_record("pb_clientes", {
            "nombre":         str(body.get("nombre", "")).strip(),
            "iata":           str(body.get("iata", "")).strip().upper()[:2],
            "contacto_email": str(body.get("contacto_email", "")).strip(),
            "tipo_servicio":  str(body.get("tipo_servicio", "basico")),
            "fecha_inicio":   str(body.get("fecha_inicio", "")),
            "activo":         body.get("activo", True),
            "notas":          str(body.get("notas", "")).strip(),
        })
        audit.registrar(user["sub"], user["email"], "crear", "clientes",
                        recurso_tipo="cliente", recurso_id=record.get("id", ""))
        return JSONResponse(record)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@router.get("/{id}", response_class=HTMLResponse)
def detalle(request: Request, id: str):
    user = _perm_ver(request)
    try:
        cliente = pb.get_record("pb_clientes", id)
    except Exception:
        cliente = None
    if not cliente:
        return render(request, "error.html", {"mensaje": "Cliente no encontrado.", "codigo": 404}, status=404)

    suscripciones = pb.list_records_all("pb_suscripciones", filter=f'cliente_id="{id}"')
    historial = []
    for sub in suscripciones:
        h = pb.list_records_all("pb_entregas_historial",
                                filter=f'suscripcion_id="{sub["id"]}"',
                                sort="-created")
        historial.extend(h)
    historial.sort(key=lambda x: x.get("created", ""), reverse=True)

    return render(request, "clientes/detalle.html", {
        "cliente":       cliente,
        "suscripciones": suscripciones,
        "historial":     historial[:50],
    })


@router.post("/{id}")
async def editar(request: Request, id: str):
    user = _perm_editar(request)
    body = await request.json()
    try:
        data = {}
        for campo in ("nombre", "iata", "contacto_email", "tipo_servicio",
                      "fecha_inicio", "notas"):
            if campo in body:
                data[campo] = body[campo]
        if "iata" in data:
            data["iata"] = str(data["iata"]).strip().upper()[:2]
        record = pb.update_record("pb_clientes", id, data)
        audit.registrar(user["sub"], user["email"], "editar", "clientes",
                        recurso_tipo="cliente", recurso_id=id)
        return JSONResponse(record)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@router.post("/{id}/estado")
async def toggle_estado(request: Request, id: str):
    user = _perm_editar(request)
    body = await request.json()
    activo = body.get("activo", True)
    try:
        record = pb.update_record("pb_clientes", id, {"activo": bool(activo)})
        audit.registrar(user["sub"], user["email"], "editar", "clientes",
                        recurso_tipo="cliente_estado", recurso_id=id,
                        detalle=f"activo={activo}")
        return JSONResponse(record)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@router.post("/{id}/suscripcion")
async def crear_suscripcion(request: Request, id: str):
    user = _perm_crear(request)
    body = await request.json()
    frecuencia = str(body.get("frecuencia", "mensual"))
    try:
        record = pb.create_record("pb_suscripciones", {
            "cliente_id":     id,
            "tipo_reporte":   str(body.get("tipo_reporte", "pdf")),
            "frecuencia":     frecuencia,
            "filtros":        body.get("filtros", {}),
            "activa":         body.get("activa", True),
            "proxima_entrega": _calcular_proxima_entrega(frecuencia),
        })
        audit.registrar(user["sub"], user["email"], "crear", "clientes",
                        recurso_tipo="suscripcion", recurso_id=record.get("id", ""))
        return JSONResponse(record)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@router.post("/{id}/demo")
async def generar_demo(request: Request, id: str):
    user = _perm_crear(request)
    body = await request.json()
    dias = int(body.get("dias_expiracion", 7))
    iata_demo = str(body.get("iata_demo", "")).strip().upper()[:2]
    if not iata_demo:
        return JSONResponse({"error": "iata_demo es requerido"}, status_code=400)
    try:
        cliente = pb.get_record("pb_clientes", id)
        if not cliente:
            return JSONResponse({"error": "Cliente no encontrado"}, status_code=404)
        token = secrets.token_hex(32)
        expira = (datetime.now(_TZ) + timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        record = pb.create_record("pb_demo_tokens", {
            "cliente_nombre": cliente.get("nombre", ""),
            "token":          token,
            "iata_demo":      iata_demo,
            "expira_en":      expira,
            "usado":          False,
        })
        audit.registrar(user["sub"], user["email"], "crear", "clientes",
                        recurso_tipo="demo_token", recurso_id=record.get("id", ""),
                        detalle=f"iata={iata_demo},dias={dias}")
        return JSONResponse({
            "token":      token,
            "url_demo":   f"/demo/{token}",
            "expira_en":  expira,
        })
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@router.get("/{id}/historial")
def historial_entregas(request: Request, id: str):
    user = _perm_ver(request)
    try:
        suscripciones = pb.list_records_all("pb_suscripciones", filter=f'cliente_id="{id}"')
        items = []
        for sub in suscripciones:
            h = pb.list_records_all("pb_entregas_historial",
                                    filter=f'suscripcion_id="{sub["id"]}"',
                                    sort="-created")
            for entrega in h:
                entrega["suscripcion_tipo"] = sub.get("tipo_reporte", "")
                items.append(entrega)
        items.sort(key=lambda x: x.get("created", ""), reverse=True)
        return JSONResponse(items[:100])
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get("/demo/{token}")
async def acceso_demo(token: str):
    """Acceso público — redirige a /dashboard con filtro iata si token válido."""
    try:
        records = pb.list_records_all("pb_demo_tokens", filter=f'token="{token}"')
        if not records:
            return RedirectResponse("/auth/login?error=Token+inválido", status_code=302)
        t = records[0]
        if t.get("usado"):
            return RedirectResponse("/auth/login?error=Token+ya+usado", status_code=302)
        expira_str = t.get("expira_en", "")
        if expira_str:
            try:
                expira = datetime.fromisoformat(expira_str.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > expira:
                    return RedirectResponse("/auth/login?error=Token+expirado", status_code=302)
            except ValueError:
                pass
        pb.update_record("pb_demo_tokens", t["id"], {"usado": True})
        iata = t.get("iata_demo", "")
        return RedirectResponse(f"/dashboard?airline={iata}", status_code=302)
    except Exception:
        return RedirectResponse("/auth/login?error=Error+validando+token", status_code=302)
