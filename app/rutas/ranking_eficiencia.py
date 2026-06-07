"""Módulo de análisis de rutas por eficiencia (CU-22, CU-23)."""

import math
import time
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.shared.analytics import load_agg, load_enriched_fact, get_aerolinas, get_years
from app.shared.clients import pb_client
from app.shared.deps import render, require_permission
from app.utils.ia_narrativa import generar_narrativa

router = APIRouter()
_perm_ver = require_permission("rutas", "ver")

_umbral_cache: dict = {"data": None, "expires": 0.0}
_UMBRAL_TTL = 60

_page_cache: dict = {}
_PAGE_TTL = 300


def _get_umbral_ruta() -> float:
    global _umbral_cache
    if _umbral_cache["data"] is not None and time.time() < _umbral_cache["expires"]:
        return _umbral_cache["data"]
    rows = pb_client.list_records("configuracion_sistema", filter='clave="alerta_ruta_ineficiente"')
    result = 0.15
    if rows:
        try:
            result = float(rows[0]["valor"])
        except (ValueError, KeyError):
            pass
    _umbral_cache = {"data": result, "expires": time.time() + _UMBRAL_TTL}
    return result


def _safe(v: Any) -> Any:
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return 0.0
    return v


def _calcular_ranking_agg(df_rutas: pd.DataFrame, umbral: float) -> list[dict]:
    """Ranking de rutas por eficiencia desde agg_rutas_eficiencia."""
    if df_rutas.empty or "origin" not in df_rutas.columns:
        return []

    # Re-agrupa por ruta (sum sobre carriers si hay filtro de aerolínea, avg ponderado si no)
    df = df_rutas.copy()
    df["sum_real"] = df["tiempo_real_avg"] * df["total_vuelos"]
    df["sum_prog"] = df["tiempo_prog_avg"] * df["total_vuelos"]
    df["sum_at"]   = df.get("vuelos_a_tiempo", pd.Series([0] * len(df), index=df.index)) * 1

    grp = df.groupby(["origin", "dest"]).agg(
        total=("total_vuelos", "sum"),
        sum_real=("sum_real", "sum"),
        sum_prog=("sum_prog", "sum"),
        retraso_prom=("retraso_prom", "mean"),
    ).reset_index()
    grp = grp[grp["total"] >= 30].copy()
    grp["eficiencia_media"] = (grp["sum_real"] / grp["sum_prog"].replace(0, float("nan"))).fillna(1.0).round(4)
    grp["ineficiente"] = grp["eficiencia_media"] > (1 + umbral)
    grp["ruta"] = grp["origin"].astype(str) + "-" + grp["dest"].astype(str)
    grp["OriginCode"] = grp["origin"]
    grp["DestCode"]   = grp["dest"]
    grp["origen_ciudad"] = grp["origin"]
    grp["dest_ciudad"]   = grp["dest"]
    grp["retraso_prom"] = grp["retraso_prom"].apply(_safe).round(1)

    return (
        grp.sort_values("eficiencia_media", ascending=True)
        .head(100)
        [["ruta", "OriginCode", "DestCode", "origen_ciudad", "dest_ciudad",
          "total", "eficiencia_media", "ineficiente", "retraso_prom"]]
        .to_dict("records")
    )


def _scatter_eficiencia_agg(df_rutas: pd.DataFrame) -> str:
    """Scatter tiempo real vs programado usando promedios de ruta (desde agg)."""
    if df_rutas.empty or "tiempo_real_avg" not in df_rutas.columns:
        return "{}"

    df = df_rutas.dropna(subset=["tiempo_real_avg", "tiempo_prog_avg"])
    if df.empty:
        return "{}"

    fig = go.Figure()
    fig.add_trace(go.Scattergl(
        x=df["tiempo_prog_avg"].tolist(),
        y=df["tiempo_real_avg"].tolist(),
        mode="markers",
        marker=dict(color="#3b82f6", size=5, opacity=0.6),
        hovertemplate="Prog: %{x:.0f} min<br>Real: %{y:.0f} min<extra></extra>",
    ))
    max_val = float(max(df["tiempo_prog_avg"].max(), df["tiempo_real_avg"].max())) + 20
    fig.add_trace(go.Scatter(
        x=[0, max_val], y=[0, max_val],
        mode="lines", line=dict(color="rgba(255,255,255,0.2)", dash="dash", width=1),
        showlegend=False, hoverinfo="skip",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#94a3b8", size=12),
        margin=dict(l=50, r=20, t=20, b=50),
        height=300,
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="Tiempo programado prom. (min)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="Tiempo real prom. (min)"),
    )
    return fig.to_json()


def _detalle_ruta(df: pd.DataFrame, origen: str, dest: str) -> dict:
    """Detalle de una ruta específica desde fact enriquecido."""
    mask = (df["OriginCode"] == origen) & (df["DestCode"] == dest)
    sub = df[mask].copy()
    if len(sub) == 0:
        return {}

    vuelos_op = sub[sub["Cancelled"] == 0] if "Cancelled" in sub.columns else sub

    eficiencias = []
    if "ActualElapsedTime" in vuelos_op.columns and "CRSElapsedTime" in vuelos_op.columns:
        validos = vuelos_op[vuelos_op["CRSElapsedTime"] > 0]
        eficiencias = (validos["ActualElapsedTime"] / validos["CRSElapsedTime"]).dropna().tolist()

    retrasos = []
    if "ArrDelayMinutes" in vuelos_op.columns:
        retrasos = vuelos_op["ArrDelayMinutes"].dropna().clip(0).tolist()

    monthly_otp: dict = {"meses": [], "otp": []}
    if "Month" in vuelos_op.columns and "ArrDel15" in vuelos_op.columns:
        grp = vuelos_op.groupby("Month").agg(
            t=("pk_vuelo", "count"), ok=("ArrDel15", lambda x: (x == 0).sum())
        ).reset_index()
        grp["otp"] = (grp["ok"] / grp["t"] * 100).round(1)
        meses_names = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        monthly_otp = {
            "meses": [meses_names[int(m)-1] if 1<=int(m)<=12 else str(m) for m in grp["Month"].tolist()],
            "otp": grp["otp"].tolist(),
        }

    return {
        "total": len(sub),
        "total_operados": len(vuelos_op),
        "eficiencias": eficiencias[:2000],
        "retrasos": retrasos[:2000],
        "monthly_otp": monthly_otp,
    }


def _compute_page(filtros: dict) -> dict:
    """Computa ranking y scatter desde agregaciones; cacheado 5 min."""
    key = str(sorted(filtros.items()))
    entry = _page_cache.get(key)
    if entry and time.time() < entry["expires"]:
        return entry["data"]
    umbral = _get_umbral_ruta()
    df_rutas = load_agg("agg_rutas_eficiencia", filtros)
    data = {
        "rows": _calcular_ranking_agg(df_rutas, umbral),
        "grafico_scatter": _scatter_eficiencia_agg(df_rutas),
        "umbral": umbral,
    }
    _page_cache[key] = {"data": data, "expires": time.time() + _PAGE_TTL}
    return data


@router.get("", response_class=HTMLResponse)
def ranking(request: Request, year: str = "", month: str = "", airline: str = ""):
    user = _perm_ver(request)
    error = None
    rows: list[dict] = []
    grafico_scatter = "{}"
    umbral = 0.15

    try:
        filtros = {k: v for k, v in {"year": year, "month": month, "airline": airline}.items() if v}
        data = _compute_page(filtros)
        rows = data["rows"]
        grafico_scatter = data["grafico_scatter"]
        umbral = data["umbral"]

    except FileNotFoundError:
        error = "Los datos no están disponibles. Ejecute el pipeline ELT primero."
    except Exception as exc:
        error = f"Error al cargar datos: {exc}"

    return render(request, "rutas/ranking.html", {
        "rows": rows, "grafico_scatter": grafico_scatter,
        "umbral": umbral,
        "error": error,
        "years": get_years(), "aerolinas": get_aerolinas(),
        "filtros": {"year": year, "month": month, "airline": airline},
    })


@router.get("/narrativa")
def narrativa_json(request: Request, year: str = "", month: str = "", airline: str = ""):
    _perm_ver(request)
    try:
        filtros = {k: v for k, v in {"year": year, "month": month, "airline": airline}.items() if v}
        data = _compute_page(filtros)
        rows = data["rows"]
        total_ineficientes = sum(1 for r in rows if r["ineficiente"])
        ctx = {
            "Rutas analizadas": len(rows),
            "Rutas ineficientes": total_ineficientes,
            "Umbral ineficiencia": f"{data['umbral']:.0%}",
            "Mejor ruta": rows[0]["ruta"] if rows else "N/A",
        }
        return JSONResponse(generar_narrativa(ctx, "Eficiencia de Rutas"))
    except Exception:
        return JSONResponse({"texto": "", "proveedor": "", "desde_cache": False})


@router.get("/{ruta}/detalle", response_class=HTMLResponse)
def detalle_ruta(request: Request, ruta: str, year: str = ""):
    _perm_ver(request)
    error = None
    datos: dict = {}
    origen, dest = "", ""

    if "-" in ruta:
        partes = ruta.split("-", 1)
        origen, dest = partes[0], partes[1]

    try:
        filtros = {"year": year} if year else {}
        df = load_enriched_fact(filtros or None)
        if origen and dest:
            datos = _detalle_ruta(df, origen, dest)
    except Exception as exc:
        error = str(exc)

    return render(request, "rutas/detalle.html", {
        "ruta": ruta, "origen": origen, "dest": dest,
        "datos": datos, "error": error, "year": year, "years": get_years(),
    })
