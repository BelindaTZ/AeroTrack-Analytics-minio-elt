"""Módulo de análisis de rutas por eficiencia (CU-22, CU-23)."""

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


def _calcular_ranking(df: pd.DataFrame, umbral: float) -> list[dict]:
    """Calcula ranking de rutas por índice de eficiencia."""
    needed = {"OriginCode", "DestCode", "ActualElapsedTime", "CRSElapsedTime"}
    if not needed.issubset(df.columns):
        return []

    vuelos_op = df[df["Cancelled"] == 0] if "Cancelled" in df.columns else df
    vuelos_op = vuelos_op[
        vuelos_op["ActualElapsedTime"].notna() &
        vuelos_op["CRSElapsedTime"].notna() &
        (vuelos_op["CRSElapsedTime"] > 0)
    ].copy()

    if len(vuelos_op) == 0:
        return []

    vuelos_op["eficiencia"] = vuelos_op["ActualElapsedTime"] / vuelos_op["CRSElapsedTime"]

    grp = vuelos_op.groupby(["OriginCode", "DestCode"]).agg(
        total=("pk_vuelo", "count"),
        eficiencia_media=("eficiencia", "mean"),
        eficiencia_std=("eficiencia", "std"),
        retraso_prom=("ArrDelayMinutes", "mean") if "ArrDelayMinutes" in vuelos_op.columns else ("pk_vuelo", lambda x: 0.0),
        distancia_media=("Distance", "mean") if "Distance" in vuelos_op.columns else ("pk_vuelo", lambda x: 0.0),
    ).reset_index()

    grp = grp[grp["total"] >= 30].copy()
    # Desnormalizar Categorical antes de operar con strings
    grp["OriginCode"] = grp["OriginCode"].astype(str)
    grp["DestCode"]   = grp["DestCode"].astype(str)
    grp["eficiencia_media"] = grp["eficiencia_media"].apply(_safe).round(4)
    grp["ineficiente"] = grp["eficiencia_media"] > (1 + umbral)
    grp["ruta"] = grp["OriginCode"] + "-" + grp["DestCode"]

    # Usar nombres de ciudad ya presentes en el fact enriquecido (evita re-lectura de MinIO)
    if "OriginCityName" in df.columns and "DestCityName" in df.columns:
        city_o = df.drop_duplicates("OriginCode").set_index("OriginCode")["OriginCityName"].to_dict()
        city_d = df.drop_duplicates("DestCode").set_index("DestCode")["DestCityName"].to_dict()
        grp["origen_ciudad"] = grp["OriginCode"].map(city_o).fillna(grp["OriginCode"])
        grp["dest_ciudad"]   = grp["DestCode"].map(city_d).fillna(grp["DestCode"])
    else:
        grp["origen_ciudad"] = grp["OriginCode"]
        grp["dest_ciudad"]   = grp["DestCode"]

    return (
        grp.sort_values("eficiencia_media", ascending=True)
        .head(100)
        [["ruta", "OriginCode", "DestCode", "origen_ciudad", "dest_ciudad",
          "total", "eficiencia_media", "ineficiente", "retraso_prom", "distancia_media"]]
        .to_dict("records")
    )


def _scatter_eficiencia(df: pd.DataFrame) -> str:
    """Scatter plot tiempo real vs programado."""
    needed = {"ActualElapsedTime", "CRSElapsedTime"}
    if not needed.issubset(df.columns):
        return "{}"
    vuelos_op = df[df["Cancelled"] == 0] if "Cancelled" in df.columns else df
    sample = vuelos_op[
        vuelos_op["ActualElapsedTime"].notna() & vuelos_op["CRSElapsedTime"].notna()
    ].sample(min(3000, len(vuelos_op)), random_state=42)

    fig = go.Figure()
    fig.add_trace(go.Scattergl(
        x=sample["CRSElapsedTime"].tolist(),
        y=sample["ActualElapsedTime"].tolist(),
        mode="markers",
        marker=dict(color="#3b82f6", size=4, opacity=0.5),
        hovertemplate="Prog: %{x} min<br>Real: %{y} min<extra></extra>",
    ))
    max_val = max(float(sample["CRSElapsedTime"].max()), float(sample["ActualElapsedTime"].max())) + 20
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
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="Tiempo programado (min)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="Tiempo real (min)"),
    )
    return fig.to_json()


def _detalle_ruta(df: pd.DataFrame, origen: str, dest: str) -> dict:
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
    key = str(sorted(filtros.items()))
    entry = _page_cache.get(key)
    if entry and time.time() < entry["expires"]:
        return entry["data"]
    umbral = _get_umbral_ruta()
    df = load_enriched_fact(filtros or None)
    data = {
        "rows": _calcular_ranking(df, umbral),
        "grafico_scatter": _scatter_eficiencia(df),
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
            "Mejor ruta OTP": rows[0]["ruta"] if rows else "N/A",
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
        filtros = {}
        if year:
            filtros["year"] = year
        df = load_enriched_fact(filtros or None)
        if origen and dest:
            datos = _detalle_ruta(df, origen, dest)
    except Exception as exc:
        error = str(exc)

    return render(request, "rutas/detalle.html", {
        "ruta": ruta, "origen": origen, "dest": dest,
        "datos": datos, "error": error, "year": year, "years": get_years(),
    })
