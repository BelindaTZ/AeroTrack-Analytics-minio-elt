"""Módulo de cancelaciones por código FAA (CU-24, CU-25, CU-26)."""

import math
import time
from typing import Any

import pandas as pd
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.shared.analytics import load_agg, get_aerolinas, get_years
from app.shared.deps import render, require_permission
from app.utils.ia_narrativa import generar_narrativa

router = APIRouter()
_perm_ver = require_permission("cancelaciones", "ver")

_page_cache: dict = {}
_PAGE_TTL = 300

_FAA_CODIGOS = {
    "A": "Carrier (Aerolínea)",
    "B": "Weather (Clima)",
    "C": "NAS (Sistema nacional)",
    "D": "Security (Seguridad)",
}
_MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
          "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def _safe(v: Any) -> Any:
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return 0.0
    return v


def _causas_faa_agg(df_canc: pd.DataFrame, df_kpi: pd.DataFrame) -> dict:
    """Distribución de cancelaciones FAA desde agg_cancelaciones_causa + agg_kpi_global_dia."""
    total_vuelos = int(df_kpi["total_vuelos"].sum()) if not df_kpi.empty and "total_vuelos" in df_kpi.columns else 0

    labels, values, descriptions = [], [], []
    if not df_canc.empty and "cancellation_code" in df_canc.columns:
        grp = (
            df_canc[df_canc["cancellation_code"].notna() & (df_canc["cancellation_code"] != "")]
            .groupby("cancellation_code")["total_cancelados"].sum()
            .reset_index()
        )
        for _, row in grp.iterrows():
            code = str(row["cancellation_code"])
            cnt  = int(row["total_cancelados"])
            labels.append(code)
            values.append(cnt)
            descriptions.append(_FAA_CODIGOS.get(code, f"Código {code}"))

    total_cancelados = sum(values)
    tasa = _safe(total_cancelados / total_vuelos) if total_vuelos > 0 else 0.0

    return {
        "labels": labels,
        "counts": values,
        "descriptions": descriptions,
        "total_cancelados": total_cancelados,
        "total_vuelos": total_vuelos,
        "tasa": round(tasa, 4),
    }


def _tendencias_mensuales_agg(df_canc: pd.DataFrame) -> dict:
    """Tendencia mensual de cancelaciones desde agg_cancelaciones_causa."""
    if df_canc.empty or "month" not in df_canc.columns:
        return {"meses": [], "cancelaciones": [], "total": [], "causas": {}}

    grp = df_canc.groupby("month")["total_cancelados"].sum().reset_index().sort_values("month")
    grp["mes_label"] = grp["month"].apply(
        lambda m: _MESES[int(m) - 1] if 1 <= int(m) <= 12 else str(m)
    )

    causas_data: dict = {}
    if "cancellation_code" in df_canc.columns:
        for code in ["A", "B", "C", "D"]:
            sub = df_canc[df_canc["cancellation_code"] == code]
            if len(sub) > 0:
                mes_dict = dict(zip(sub["month"], sub["total_cancelados"]))
                causas_data[code] = [int(mes_dict.get(m, 0)) for m in grp["month"].tolist()]

    return {
        "meses": grp["mes_label"].tolist(),
        "cancelaciones": grp["total_cancelados"].astype(int).tolist(),
        "total": [0] * len(grp),
        "causas": causas_data,
    }


def _desvios_agg(df_dev: pd.DataFrame) -> list[dict]:
    """Top 20 desvíos desde agg_desvios_ruta."""
    if df_dev.empty or "origin" not in df_dev.columns:
        return []
    rows = []
    for _, r in df_dev.head(20).iterrows():
        rows.append({
            "ruta":          f"{r.get('origin','?')}-{r.get('dest','?')}",
            "alt_airport":   r.get("alt_airport", "N/A"),
            "count":         int(r.get("total_desvios", 0)),
            "div_arr_delay": round(float(_safe(r.get("divarrdelay_avg", 0) or 0)), 1),
            "div_distance":  round(float(_safe(r.get("divdistance_avg", 0) or 0)), 1),
        })
    return rows


def _compute_page(filtros: dict) -> dict:
    """Computa datos de cancelaciones desde agregaciones; cacheado 5 min."""
    key = str(sorted(filtros.items()))
    entry = _page_cache.get(key)
    if entry and time.time() < entry["expires"]:
        return entry["data"]

    # airline filter sólo aplica a agg_cancelaciones_causa si tuviera carrier;
    # como no lo tiene, se ignora silenciosamente (filtros year/month sí se aplican)
    df_canc = load_agg("agg_cancelaciones_causa", filtros)
    df_kpi  = load_agg("agg_kpi_global_dia", {k: v for k, v in filtros.items() if k != "airline"})
    df_dev  = load_agg("agg_desvios_ruta")

    data = {
        "causas_data": _causas_faa_agg(df_canc, df_kpi),
        "tendencias":  _tendencias_mensuales_agg(df_canc),
        "desvios":     _desvios_agg(df_dev),
    }
    _page_cache[key] = {"data": data, "expires": time.time() + _PAGE_TTL}
    return data


@router.get("", response_class=HTMLResponse)
def causas(
    request: Request,
    year: str = "", month: str = "", airline: str = "",
):
    user = _perm_ver(request)
    error = None
    causas_data: dict = {"labels": [], "counts": [], "descriptions": [], "total_cancelados": 0, "total_vuelos": 0, "tasa": 0.0}
    tendencias: dict = {"meses": [], "cancelaciones": [], "total": [], "causas": {}}
    desvios: list[dict] = []

    try:
        filtros = {k: v for k, v in {"year": year, "month": month, "airline": airline}.items() if v}
        data = _compute_page(filtros)
        causas_data = data["causas_data"]
        tendencias  = data["tendencias"]
        desvios     = data["desvios"]

    except FileNotFoundError:
        error = "Los datos no están disponibles. Ejecute el pipeline ELT primero."
    except Exception as exc:
        error = f"Error al cargar datos: {exc}"

    return render(request, "cancelaciones/causas.html", {
        "causas_data": causas_data,
        "tendencias":  tendencias,
        "desvios":     desvios,
        "error":       error,
        "years":       get_years(),
        "aerolinas":   get_aerolinas(),
        "filtros":     {"year": year, "month": month, "airline": airline},
    })


@router.get("/narrativa")
def narrativa_json(request: Request, year: str = "", month: str = "", airline: str = ""):
    _perm_ver(request)
    try:
        filtros = {k: v for k, v in {"year": year, "month": month, "airline": airline}.items() if v}
        data = _compute_page(filtros)
        causas_data = data["causas_data"]
        ctx = {
            "Total cancelados": causas_data["total_cancelados"],
            "Tasa cancelación": f"{causas_data['tasa']:.1%}",
            "Principal causa": (causas_data["descriptions"][0] if causas_data["descriptions"] else "N/A"),
            "Total desvíos": len(data["desvios"]),
        }
        return JSONResponse(generar_narrativa(ctx, "Cancelaciones FAA"))
    except Exception:
        return JSONResponse({"texto": "", "proveedor": "", "desde_cache": False})
