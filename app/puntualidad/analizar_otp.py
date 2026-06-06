"""Módulo de puntualidad OTP (CU-19, CU-20, CU-21)."""

import math
import time
from typing import Any

import pandas as pd
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.shared.analytics import load_enriched_fact, get_aerolinas, get_years
from app.shared.deps import render, require_permission
from app.utils.ia_narrativa import generar_narrativa

router = APIRouter()
_perm_ver = require_permission("puntualidad", "ver")

_MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
          "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

_page_cache: dict = {}
_PAGE_TTL = 300


def _safe(v: Any) -> Any:
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return 0.0
    return v


def _otp_por_aerolinea(df: pd.DataFrame) -> list[dict]:
    if "Reporting_Airline" not in df.columns or "ArrDel15" not in df.columns:
        return []
    vuelos_op = df[df["Cancelled"] == 0] if "Cancelled" in df.columns else df
    grp = (
        vuelos_op.groupby("Reporting_Airline")
        .agg(total=("pk_vuelo", "count"), otp_sum=("ArrDel15", lambda x: (x == 0).sum()))
        .reset_index()
    )
    grp["otp"] = (grp["otp_sum"] / grp["total"] * 100).round(2)
    grp = grp[grp["total"] >= 50].sort_values("total", ascending=False).head(25)
    return grp[["Reporting_Airline", "total", "otp"]].rename(
        columns={"Reporting_Airline": "aerolinea"}
    ).to_dict("records")


def _causas_retraso(df: pd.DataFrame, airline: str = "") -> dict:
    causas_cols = ["CarrierDelay", "WeatherDelay", "NASDelay", "SecurityDelay", "LateAircraftDelay"]
    result = {"labels": [], "counts": []}
    work = df.copy()
    if airline and "Reporting_Airline" in work.columns:
        work = work[work["Reporting_Airline"] == airline]

    for col in causas_cols:
        if col in work.columns:
            total = float(work[col].fillna(0).sum())
            if total > 0:
                result["labels"].append(col.replace("Delay", "").replace("LateAircraft", "LateAircraft"))
                result["counts"].append(round(_safe(total), 0))
    return result


def _tendencias_otp_mensual(df: pd.DataFrame, airline: str = "") -> dict:
    if "Month" not in df.columns or "ArrDel15" not in df.columns:
        return {"meses": [], "otp": [], "airline": airline}
    work = df.copy()
    if airline and "Reporting_Airline" in work.columns:
        work = work[work["Reporting_Airline"] == airline]
    vuelos_op = work[work["Cancelled"] == 0] if "Cancelled" in work.columns else work

    grp = (
        vuelos_op.groupby("Month")
        .agg(total=("pk_vuelo", "count"), otp_sum=("ArrDel15", lambda x: (x == 0).sum()))
        .reset_index()
    )
    grp["otp"] = (grp["otp_sum"] / grp["total"] * 100).round(1)
    meses = [_MESES[int(m) - 1] for m in grp["Month"].tolist()]
    return {"meses": meses, "otp": grp["otp"].tolist(), "airline": airline}


def _tendencias_dia_semana(df: pd.DataFrame) -> dict:
    if "DayOfWeek" not in df.columns or "ArrDel15" not in df.columns:
        return {"dias": [], "otp": []}
    vuelos_op = df[df["Cancelled"] == 0] if "Cancelled" in df.columns else df
    dias_label = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    grp = (
        vuelos_op.groupby("DayOfWeek")
        .agg(total=("pk_vuelo", "count"), otp_sum=("ArrDel15", lambda x: (x == 0).sum()))
        .reset_index()
    )
    grp["otp"] = (grp["otp_sum"] / grp["total"] * 100).round(1)
    dias = [dias_label[int(d) - 1] if 1 <= int(d) <= 7 else str(d) for d in grp["DayOfWeek"].tolist()]
    return {"dias": dias, "otp": grp["otp"].tolist()}


def _comparar_aerolineas(df: pd.DataFrame, ruta: str) -> list[dict]:
    """Compara OTP de aerolíneas en la misma ruta."""
    if not ruta or "Reporting_Airline" not in df.columns:
        return []
    parts = ruta.split("-")
    if len(parts) != 2:
        return []
    origen, dest = parts
    mask = (df["OriginCode"] == origen) & (df["DestCode"] == dest)
    sub = df[mask & (df["Cancelled"] == 0)] if "Cancelled" in df.columns else df[mask]
    if len(sub) == 0:
        return []
    grp = (
        sub.groupby("Reporting_Airline")
        .agg(total=("pk_vuelo", "count"),
             otp_sum=("ArrDel15", lambda x: (x == 0).sum()) if "ArrDel15" in sub.columns else ("pk_vuelo", "count"),
             retraso=("ArrDelayMinutes", "mean") if "ArrDelayMinutes" in sub.columns else ("pk_vuelo", lambda x: 0.0))
        .reset_index()
    )
    if "ArrDel15" in sub.columns:
        grp["otp"] = (grp["otp_sum"] / grp["total"] * 100).round(1)
    else:
        grp["otp"] = 0.0
    return grp[["Reporting_Airline", "total", "otp", "retraso"]].rename(
        columns={"Reporting_Airline": "aerolinea"}
    ).to_dict("records")


def _compute_page(filtros: dict, airline: str = "") -> dict:
    key = str(sorted(filtros.items()))
    entry = _page_cache.get(key)
    if entry and time.time() < entry["expires"]:
        return entry["data"]
    df = load_enriched_fact(filtros or None)
    data = {
        "datos_otp": _otp_por_aerolinea(df),
        "causas": _causas_retraso(df, airline),
        "tendencias": _tendencias_otp_mensual(df, airline),
        "tendencias_dia": _tendencias_dia_semana(df),
    }
    _page_cache[key] = {"data": data, "expires": time.time() + _PAGE_TTL}
    return data


@router.get("", response_class=HTMLResponse)
def index_otp(request: Request, year: str = "", month: str = "", airline: str = ""):
    user = _perm_ver(request)
    error = None
    datos_otp: list[dict] = []
    causas: dict = {"labels": [], "values": []}
    tendencias: dict = {"meses": [], "otp": []}
    tendencias_dia: dict = {"dias": [], "otp": []}

    try:
        filtros = {k: v for k, v in {"year": year, "month": month, "airline": airline}.items() if v}
        data = _compute_page(filtros, airline)
        datos_otp = data["datos_otp"]
        causas = data["causas"]
        tendencias = data["tendencias"]
        tendencias_dia = data["tendencias_dia"]

    except FileNotFoundError:
        error = "Los datos no están disponibles. Ejecute el pipeline ELT primero."
    except Exception as exc:
        error = f"Error al cargar datos: {exc}"

    return render(request, "puntualidad/index.html", {
        "datos_otp": datos_otp,
        "causas": causas,
        "tendencias": tendencias,
        "tendencias_dia": tendencias_dia,
        "aerolinas": get_aerolinas(),
        "years": get_years(),
        "filtros": {"year": year, "month": month, "airline": airline},
        "error": error,
    })


@router.get("/narrativa")
def narrativa_json(request: Request, year: str = "", month: str = "", airline: str = ""):
    _perm_ver(request)
    try:
        filtros = {k: v for k, v in {"year": year, "month": month, "airline": airline}.items() if v}
        data = _compute_page(filtros, airline)
        datos_otp = data["datos_otp"]
        causas = data["causas"]
        otp_prom = sum(r["otp"] for r in datos_otp) / len(datos_otp) if datos_otp else 0
        ctx = {
            "Aerolíneas analizadas": len(datos_otp),
            "OTP promedio": f"{otp_prom:.1f}%",
            "Principales causas": ", ".join(causas["labels"][:3]) if causas["labels"] else "N/A",
        }
        return JSONResponse(generar_narrativa(ctx, "Puntualidad OTP"))
    except Exception:
        return JSONResponse({"texto": "", "proveedor": "", "desde_cache": False})


@router.get("/comparar", response_class=HTMLResponse)
def comparar(request: Request, ruta: str = "", year: str = ""):
    _perm_ver(request)
    error = None
    datos: list[dict] = []

    try:
        filtros = {k: v for k, v in {"year": year}.items() if v}
        df = load_enriched_fact(filtros or None)
        if ruta:
            datos = _comparar_aerolineas(df, ruta)
    except Exception as exc:
        error = str(exc)

    rutas_disponibles: list[str] = []
    try:
        from app.shared.clients.minio_client import read_parquet
        from app.config import MINIO_BUCKET_DIMS
        from app.shared.analytics import _desnormalizar
        dim_r = _desnormalizar(read_parquet(MINIO_BUCKET_DIMS, "dim_ruta"))
        if "OriginCode" in dim_r.columns and "DestCode" in dim_r.columns:
            rutas_disponibles = (
                (dim_r["OriginCode"].astype(str) + "-" + dim_r["DestCode"].astype(str))
                .dropna().unique().tolist()
            )
            rutas_disponibles = sorted(rutas_disponibles[:500])
    except Exception:
        pass

    years = get_years()
    return render(request, "puntualidad/comparar.html", {
        "datos": datos, "ruta": ruta, "year": year,
        "rutas_disponibles": rutas_disponibles, "years": years, "error": error,
    })
