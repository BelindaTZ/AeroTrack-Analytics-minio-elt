"""Endpoints públicos de la API REST — autenticación vía Bearer token o query param."""

import hashlib
import time
from datetime import UTC, datetime

import pandas as pd
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.shared.analytics import load_agg
from app.shared.clients import pb_client as pb

router = APIRouter()


def _validar_api_key(request: Request) -> tuple[dict | None, JSONResponse | None]:
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if not token:
        token = request.query_params.get("api_key", "")
    if not token:
        return None, JSONResponse(
            {"error": "API key requerida. Usa header Authorization: Bearer <key> o query param api_key."},
            status_code=401,
        )

    clave_hash = hashlib.sha256(token.encode()).hexdigest()
    try:
        records = pb.list_records_all("pb_api_claves", filter=f'clave_hash="{clave_hash}"')
    except Exception:
        return None, JSONResponse({"error": "Error validando API key"}, status_code=500)

    if not records:
        return None, JSONResponse({"error": "API key inválida"}, status_code=401)

    record = records[0]
    if not record.get("activa", False):
        return None, JSONResponse({"error": "API key revocada"}, status_code=401)

    expiracion = record.get("expiracion", "")
    if expiracion:
        try:
            exp = datetime.fromisoformat(expiracion.replace("Z", "+00:00"))
            if datetime.now(UTC) > exp:
                return None, JSONResponse({"error": "API key expirada"}, status_code=401)
        except ValueError:
            pass

    limite = record.get("limite_diario", 1000)
    consultas_hoy = record.get("consultas_hoy", 0)
    if consultas_hoy >= limite:
        return None, JSONResponse({"error": "Límite diario de consultas alcanzado"}, status_code=429)

    try:
        pb.update_record(
            "pb_api_claves",
            record["id"],
            {
                "consultas_hoy": consultas_hoy + 1,
                "consultas_total": record.get("consultas_total", 0) + 1,
                "ultima_consulta": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            },
        )
    except Exception:
        pass

    return record, None


def _registrar_llamada(clave_id: str, endpoint: str, metodo: str, codigo: int, tiempo_ms: int, ip: str) -> None:
    try:
        pb.create_record(
            "pb_api_historial",
            {
                "clave_id": clave_id,
                "endpoint": endpoint,
                "metodo": metodo,
                "codigo_respuesta": codigo,
                "tiempo_ms": tiempo_ms,
                "ip_origen": ip,
            },
        )
    except Exception:
        pass


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "")


def _safe_df(df: pd.DataFrame) -> list[dict]:
    if df is None or df.empty:
        return []
    df = df.fillna("").astype(str)
    return df.to_dict(orient="records")


@router.get("/api/v1/otp")
async def api_otp(request: Request, airline: str = "", year: str = "", month: str = ""):
    clave, err = _validar_api_key(request)
    if err:
        return err
    t0 = time.time()
    try:
        df = load_agg(
            "agg_otp_aerolinea_mes",
            {
                k: v
                for k, v in {
                    "airline": airline,
                    "year": year,
                    "month": month,
                }.items()
                if v
            },
        )
        result = _safe_df(df)
        codigo = 200
    except Exception as exc:
        result = {"error": str(exc)}
        codigo = 500
    _registrar_llamada(clave["id"], "/api/v1/otp", "GET", codigo, int((time.time() - t0) * 1000), _client_ip(request))
    return JSONResponse(
        {"ok": codigo == 200, "data": result, "total": len(result) if isinstance(result, list) else 0},
        status_code=codigo,
    )


@router.get("/api/v1/rutas")
async def api_rutas(request: Request, year: str = "", top_n: int = 10):
    clave, err = _validar_api_key(request)
    if err:
        return err
    t0 = time.time()
    try:
        df = load_agg("agg_rutas_eficiencia", {"year": year} if year else None)
        if df is not None and not df.empty:
            df = df.sort_values("total_vuelos", ascending=False).head(top_n)
        result = _safe_df(df)
        codigo = 200
    except Exception as exc:
        result = {"error": str(exc)}
        codigo = 500
    _registrar_llamada(clave["id"], "/api/v1/rutas", "GET", codigo, int((time.time() - t0) * 1000), _client_ip(request))
    return JSONResponse(
        {"ok": codigo == 200, "data": result, "total": len(result) if isinstance(result, list) else 0},
        status_code=codigo,
    )


@router.get("/api/v1/cancelaciones")
async def api_cancelaciones(request: Request, year: str = "", month: str = ""):
    clave, err = _validar_api_key(request)
    if err:
        return err
    t0 = time.time()
    try:
        df = load_agg(
            "agg_cancelaciones_causa",
            {
                k: v
                for k, v in {
                    "year": year,
                    "month": month,
                }.items()
                if v
            },
        )
        result = _safe_df(df)
        codigo = 200
    except Exception as exc:
        result = {"error": str(exc)}
        codigo = 500
    _registrar_llamada(
        clave["id"], "/api/v1/cancelaciones", "GET", codigo, int((time.time() - t0) * 1000), _client_ip(request)
    )
    return JSONResponse(
        {"ok": codigo == 200, "data": result, "total": len(result) if isinstance(result, list) else 0},
        status_code=codigo,
    )


@router.get("/api/v1/kpis")
async def api_kpis(request: Request, year: str = "", month: str = ""):
    clave, err = _validar_api_key(request)
    if err:
        return err
    t0 = time.time()
    try:
        df = load_agg(
            "agg_kpi_global_dia",
            {
                k: v
                for k, v in {
                    "year": year,
                    "month": month,
                }.items()
                if v
            },
        )
        result = _safe_df(df)
        codigo = 200
    except Exception as exc:
        result = {"error": str(exc)}
        codigo = 500
    _registrar_llamada(clave["id"], "/api/v1/kpis", "GET", codigo, int((time.time() - t0) * 1000), _client_ip(request))
    return JSONResponse(
        {"ok": codigo == 200, "data": result, "total": len(result) if isinstance(result, list) else 0},
        status_code=codigo,
    )
