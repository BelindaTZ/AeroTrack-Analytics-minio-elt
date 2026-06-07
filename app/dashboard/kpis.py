"""Dashboard principal de KPIs (CU-17, CU-18)."""

import math
import time
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.shared.analytics import load_agg, get_aerolinas, get_years
from app.shared.clients import pb_client
from app.shared.deps import render, require_permission
from app.utils.ia_narrativa import generar_narrativa

router = APIRouter()
_perm_ver = require_permission("dashboard", "ver")

_umbrales_cache: dict = {"data": None, "expires": 0.0}
_UMBRALES_TTL = 60

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


def _calcular_kpis_agg(df_otp: pd.DataFrame) -> dict:
    """Calcula KPIs globales desde agg_otp_aerolinea_mes (ya filtrado)."""
    if df_otp.empty:
        return {
            "total_vuelos": 0, "otp_global": 0.0, "tasa_cancelacion": 0.0,
            "retraso_promedio": 0.0, "top3_aerolineas": [],
        }

    col_total = "total_vuelos_todos" if "total_vuelos_todos" in df_otp.columns else "total_vuelos"
    total = int(df_otp[col_total].sum())

    total_cancelados = int(df_otp["total_cancelados"].sum()) if "total_cancelados" in df_otp.columns else 0
    tasa_cancel = total_cancelados / total if total > 0 else 0.0

    vuelos_op = int(df_otp["total_vuelos"].sum())
    vuelos_at = int(df_otp["vuelos_a_tiempo"].sum()) if "vuelos_a_tiempo" in df_otp.columns else 0
    otp = vuelos_at / vuelos_op if vuelos_op > 0 else 0.0

    retraso_prom = 0.0
    if "delay_avg" in df_otp.columns and vuelos_op > 0:
        retraso_prom = float((df_otp["delay_avg"] * df_otp["total_vuelos"]).sum()) / vuelos_op

    top3: list[dict] = []
    if "carrier" in df_otp.columns:
        grp = df_otp.groupby("carrier").agg(
            total=("total_vuelos", "sum"),
            vuelos_at=("vuelos_a_tiempo", "sum"),
        ).reset_index()
        grp["otp"] = (grp["vuelos_at"] / grp["total"].replace(0, float("nan"))).fillna(0.0).round(4)
        top3 = (
            grp.nlargest(3, "total")[["carrier", "total", "otp"]]
            .rename(columns={"carrier": "aerolinea"})
            .to_dict("records")
        )

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


def _grafico_otp_por_aerolinea_agg(df_otp: pd.DataFrame) -> str:
    """Bar chart OTP por aerolínea desde agg_otp_aerolinea_mes."""
    if "carrier" not in df_otp.columns or df_otp.empty:
        return "{}"
    grp = df_otp.groupby("carrier").agg(
        total=("total_vuelos", "sum"),
        vuelos_at=("vuelos_a_tiempo", "sum"),
    ).reset_index()
    grp["otp"] = (grp["vuelos_at"] / grp["total"].replace(0, float("nan")) * 100).fillna(0.0).round(1)
    grp = grp[grp["total"] >= 100].nlargest(20, "total")
    if grp.empty:
        return "{}"

    fig = go.Figure(go.Bar(
        x=grp["carrier"].tolist(),
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


def _grafico_vuelos_por_mes_agg(df_otp: pd.DataFrame) -> str:
    """Bar chart vuelos por mes desde agg_otp_aerolinea_mes."""
    if "month" not in df_otp.columns or df_otp.empty:
        return "{}"
    col_total = "total_vuelos_todos" if "total_vuelos_todos" in df_otp.columns else "total_vuelos"
    col_canc = "total_cancelados"

    grp = df_otp.groupby("month").agg(
        total=(col_total, "sum"),
        cancelados=(col_canc, "sum") if col_canc in df_otp.columns else (col_total, lambda x: 0),
    ).reset_index().sort_values("month")

    nombres_mes = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                   "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    grp["mes_label"] = grp["month"].apply(lambda m: nombres_mes[int(m) - 1] if 1 <= int(m) <= 12 else str(m))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Vuelos operados", x=grp["mes_label"].tolist(),
        y=(grp["total"] - grp["cancelados"]).tolist(),
        marker_color="#3b82f6",
    ))
    fig.add_trace(go.Bar(
        name="Cancelados", x=grp["mes_label"].tolist(),
        y=grp["cancelados"].tolist(),
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
    """Computa KPIs y gráficos desde agregaciones; resultado cacheado 5 min."""
    key = str(sorted(filtros.items()))
    entry = _page_cache.get(key)
    if entry and time.time() < entry["expires"]:
        return entry["data"]

    df_otp = load_agg("agg_otp_aerolinea_mes", filtros)
    kpis = _calcular_kpis_agg(df_otp)
    umbrales = _get_umbrales()
    alertas = _evaluar_alertas(kpis, umbrales)
    data = {
        "kpis": kpis,
        "alertas": alertas,
        "grafico_otp": _grafico_otp_por_aerolinea_agg(df_otp),
        "grafico_meses": _grafico_vuelos_por_mes_agg(df_otp),
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
        data = _compute_page(filtros)
        return JSONResponse({"kpis": data["kpis"], "alertas": data["alertas"]})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
