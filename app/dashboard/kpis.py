"""Dashboard principal de KPIs (CU-17, CU-18)."""

import math
import time
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.shared.analytics import load_enriched_fact, get_aerolinas, get_years
from app.shared.clients import pb_client
from app.shared.deps import render, require_permission
from app.utils.ia_narrativa import generar_narrativa

router = APIRouter()
_perm_ver = require_permission("dashboard", "ver")

_umbrales_cache: dict = {"data": None, "expires": 0.0}
_UMBRALES_TTL = 60

# Caché de resultados computados (KPIs + gráficos) — TTL 5 min, clave = filtros
_page_cache: dict = {}
_PAGE_TTL = 300


def _get_umbrales() -> dict:
    global _umbrales_cache
    if _umbrales_cache["data"] is not None and time.time() < _umbrales_cache["expires"]:
        return _umbrales_cache["data"]
    rows = pb_client.list_records("configuracion_sistema", filter='modulo="alertas"')
    cfg = {r["clave"]: r["valor"] for r in rows}
    result = {
        "otp_min": float(cfg.get("alerta_otp_umbral_min", "0.80")),
        "cancel_max": float(cfg.get("alerta_cancelacion_max", "0.05")),
        "retraso_max": float(cfg.get("alerta_retraso_minutos", "15")),
    }
    _umbrales_cache = {"data": result, "expires": time.time() + _UMBRALES_TTL}
    return result


def _safe(v: Any) -> Any:
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return 0.0
    return v


def _calcular_kpis(df: pd.DataFrame) -> dict:
    total = len(df)
    if total == 0:
        return {
            "total_vuelos": 0, "otp_global": 0.0, "tasa_cancelacion": 0.0,
            "retraso_promedio": 0.0, "top3_aerolineas": [],
        }

    cancelados = int(df["Cancelled"].sum()) if "Cancelled" in df.columns else 0
    tasa_cancel = cancelados / total

    vuelos_op = df[df["Cancelled"] == 0] if "Cancelled" in df.columns else df
    otp = 0.0
    if "ArrDel15" in vuelos_op.columns and len(vuelos_op) > 0:
        otp = float((vuelos_op["ArrDel15"] == 0).sum() / len(vuelos_op))
    elif "ArrDelay" in vuelos_op.columns and len(vuelos_op) > 0:
        otp = float((vuelos_op["ArrDelay"].fillna(0) <= 15).sum() / len(vuelos_op))

    retraso_prom = 0.0
    if "ArrDelayMinutes" in vuelos_op.columns:
        retraso_prom = float(vuelos_op["ArrDelayMinutes"].fillna(0).mean())
    elif "ArrDelay" in vuelos_op.columns:
        retraso_prom = float(vuelos_op["ArrDelay"].fillna(0).clip(lower=0).mean())

    top3: list[dict] = []
    if "Reporting_Airline" in df.columns and "ArrDel15" in df.columns:
        grp = (
            vuelos_op.groupby("Reporting_Airline")
            .agg(total=("pk_vuelo", "count"), otp_sum=("ArrDel15", lambda x: (x == 0).sum()))
            .reset_index()
        )
        grp["otp"] = grp["otp_sum"] / grp["total"]
        top3 = (
            grp.nlargest(3, "total")[["Reporting_Airline", "total", "otp"]]
            .rename(columns={"Reporting_Airline": "aerolinea"})
            .to_dict("records")
        )
        for r in top3:
            r["otp"] = round(_safe(r["otp"]), 4)

    return {
        "total_vuelos": total,
        "otp_global": round(_safe(otp), 4),
        "tasa_cancelacion": round(_safe(tasa_cancel), 4),
        "retraso_promedio": round(_safe(retraso_prom), 2),
        "top3_aerolineas": top3,
    }


def _evaluar_alertas(kpis: dict, umbrales: dict) -> list[dict]:
    alertas = []
    otp = kpis["otp_global"]
    if otp < umbrales["otp_min"]:
        alertas.append({
            "tipo": "critical" if otp < umbrales["otp_min"] * 0.9 else "warning",
            "mensaje": f"OTP global ({otp:.1%}) por debajo del umbral ({umbrales['otp_min']:.1%})",
            "icono": "bi-exclamation-triangle-fill",
        })

    cancel = kpis["tasa_cancelacion"]
    if cancel > umbrales["cancel_max"]:
        alertas.append({
            "tipo": "critical" if cancel > umbrales["cancel_max"] * 1.5 else "warning",
            "mensaje": f"Tasa de cancelación ({cancel:.1%}) supera el umbral ({umbrales['cancel_max']:.1%})",
            "icono": "bi-x-circle-fill",
        })

    retraso = kpis["retraso_promedio"]
    if retraso > umbrales["retraso_max"]:
        alertas.append({
            "tipo": "warning",
            "mensaje": f"Retraso promedio ({retraso:.1f} min) supera el umbral ({umbrales['retraso_max']:.0f} min)",
            "icono": "bi-clock-fill",
        })

    return alertas


def _grafico_otp_por_aerolinea(df: pd.DataFrame) -> str:
    if "Reporting_Airline" not in df.columns or "ArrDel15" not in df.columns:
        return "{}"
    vuelos_op = df[df["Cancelled"] == 0] if "Cancelled" in df.columns else df
    grp = (
        vuelos_op.groupby("Reporting_Airline")
        .agg(total=("pk_vuelo", "count"), otp_sum=("ArrDel15", lambda x: (x == 0).sum()))
        .reset_index()
    )
    grp["otp"] = (grp["otp_sum"] / grp["total"] * 100).round(1)
    grp = grp[grp["total"] >= 100].nlargest(20, "total")

    fig = go.Figure(go.Bar(
        x=grp["Reporting_Airline"].tolist(),
        y=grp["otp"].tolist(),
        marker_color="#3b82f6",
        hovertemplate="%{x}<br>OTP: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#94a3b8", size=12),
        margin=dict(l=40, r=20, t=20, b=60),
        height=280,
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", tickangle=-30),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="OTP %", range=[0, 105]),
    )
    return fig.to_json()


def _grafico_vuelos_por_mes(df: pd.DataFrame) -> str:
    if "Month" not in df.columns:
        return "{}"
    grp = df.groupby("Month").agg(
        total=("pk_vuelo", "count"),
        cancelados=("Cancelled", "sum") if "Cancelled" in df.columns else ("pk_vuelo", lambda x: 0)
    ).reset_index()

    nombres_mes = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                   "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    grp["mes_label"] = grp["Month"].apply(lambda m: nombres_mes[int(m) - 1] if 1 <= int(m) <= 12 else str(m))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Vuelos operados", x=grp["mes_label"].tolist(),
        y=(grp["total"] - grp.get("cancelados", 0)).tolist(),
        marker_color="#3b82f6",
    ))
    fig.add_trace(go.Bar(
        name="Cancelados", x=grp["mes_label"].tolist(),
        y=grp.get("cancelados", pd.Series([0] * len(grp))).tolist(),
        marker_color="#f87171",
    ))
    fig.update_layout(
        barmode="stack",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#94a3b8", size=12),
        margin=dict(l=40, r=20, t=20, b=40),
        height=280,
        legend=dict(orientation="h", y=1.1),
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
    )
    return fig.to_json()


def _compute_page(filtros: dict) -> dict:
    """Computa KPIs y gráficos; resultado cacheado 5 min por combinación de filtros."""
    key = str(sorted(filtros.items()))
    entry = _page_cache.get(key)
    if entry and time.time() < entry["expires"]:
        return entry["data"]
    df = load_enriched_fact(filtros or None)
    kpis = _calcular_kpis(df)
    umbrales = _get_umbrales()
    alertas = _evaluar_alertas(kpis, umbrales)
    data = {
        "kpis": kpis,
        "alertas": alertas,
        "grafico_otp": _grafico_otp_por_aerolinea(df),
        "grafico_meses": _grafico_vuelos_por_mes(df),
        "df": df,
    }
    _page_cache[key] = {"data": data, "expires": time.time() + _PAGE_TTL}
    return data


@router.get("", response_class=HTMLResponse)
def dashboard(
    request: Request,
    year: str = "", month: str = "", airline: str = "",
):
    user = _perm_ver(request)
    error = None
    kpis: dict = {}
    alertas: list[dict] = []
    grafico_otp = "{}"
    grafico_meses = "{}"

    try:
        filtros = {k: v for k, v in {"year": year, "month": month, "airline": airline}.items() if v}
        data = _compute_page(filtros)
        kpis = data["kpis"]
        alertas = data["alertas"]
        grafico_otp = data["grafico_otp"]
        grafico_meses = data["grafico_meses"]

    except FileNotFoundError:
        error = "Los datos del modelo dimensional no están disponibles. Ejecute el pipeline ELT primero."
    except Exception as exc:
        error = f"Error al cargar datos: {exc}"

    return render(request, "dashboard/index.html", {
        "kpis": kpis,
        "alertas": alertas,
        "error": error,
        "grafico_otp": grafico_otp,
        "grafico_meses": grafico_meses,
        "aerolinas": get_aerolinas(),
        "years": get_years(),
        "filtros": {"year": year, "month": month, "airline": airline},
    })


@router.get("/narrativa")
def narrativa_json(
    request: Request,
    year: str = "", month: str = "", airline: str = "",
):
    _perm_ver(request)
    try:
        filtros = {k: v for k, v in {"year": year, "month": month, "airline": airline}.items() if v}
        data = _compute_page(filtros)
        kpis = data["kpis"]
        ctx = {
            "Total vuelos": kpis["total_vuelos"],
            "OTP global": f"{kpis['otp_global']:.1%}",
            "Tasa cancelación": f"{kpis['tasa_cancelacion']:.1%}",
            "Retraso promedio": f"{kpis['retraso_promedio']:.1f} min",
            "Alertas activas": len(data["alertas"]),
        }
        return JSONResponse(generar_narrativa(ctx, "Dashboard KPIs"))
    except Exception:
        return JSONResponse({"texto": "", "proveedor": "", "desde_cache": False})


@router.get("/kpis-json")
def kpis_json(
    request: Request,
    year: str = "", month: str = "", airline: str = "",
):
    _perm_ver(request)
    try:
        filtros = {k: v for k, v in {"year": year, "month": month, "airline": airline}.items() if v}
        df = load_enriched_fact(filtros or None)
        kpis = _calcular_kpis(df)
        umbrales = _get_umbrales()
        alertas = _evaluar_alertas(kpis, umbrales)
        return JSONResponse({"kpis": kpis, "alertas": alertas})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
