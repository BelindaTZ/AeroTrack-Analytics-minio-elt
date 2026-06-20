"""Módulo predictivo: proyecciones OTP, estacionalidad y recomendaciones (CU-35, CU-36, CU-37)."""

import math
import time
from typing import Any

import pandas as pd
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.shared.analytics import load_agg, load_enriched_fact, get_aerolinas, get_years
from app.shared.clients import pb_client
from app.shared.deps import render, require_permission

router = APIRouter()
_perm_ver = require_permission("predictivo", "ver")

_MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
          "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
_DIAS  = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

_heatmap_cache: dict = {}
_HEATMAP_TTL = 600


def _safe(v: Any) -> float:
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return 0.0
    return float(v)


def _get_horizonte_max() -> int:
    try:
        rows = pb_client.list_records("configuracion_sistema", filter='modulo="sistema"')
        cfg  = {r["clave"]: r["valor"] for r in rows}
        return int(cfg.get("horizonte_prediccion_max", "6"))
    except Exception:
        return 6


# ── Series OTP mensuales ──────────────────────────────────────────────────────

def _load_otp_series(airline: str = "", year: str = "") -> pd.DataFrame:
    """Carga la serie OTP mensual desde la tabla de agregación."""
    filtros: dict = {}
    if airline:
        filtros["airline"] = airline
    if year:
        filtros["year"] = year

    try:
        df = load_agg("agg_otp_aerolinea_mes", filtros if filtros else None)
    except Exception:
        return pd.DataFrame()
    if df.empty:
        return pd.DataFrame()

    group_cols = ["year", "month"] if "year" in df.columns else ["month"]
    grp = (
        df.groupby(group_cols)
        .agg(total=("total_vuelos", "sum"), a_tiempo=("vuelos_a_tiempo", "sum"))
        .reset_index()
    )
    grp["otp"] = (grp["a_tiempo"] / grp["total"].replace(0, float("nan")) * 100).fillna(0.0)
    grp = grp.sort_values(group_cols)
    return grp


# ── Proyección OTP (statsmodels ExponentialSmoothing) ────────────────────────

def _proyectar_otp(df: pd.DataFrame, horizonte: int) -> dict:
    otp_vals = df["otp"].tolist()
    n_hist   = len(otp_vals)

    if n_hist < 3:
        return {"error": "Se necesitan al menos 3 meses de datos para proyectar."}

    # Etiquetas históricas
    if "year" in df.columns and "month" in df.columns:
        labels_hist = [
            f"{_MESES[int(m)-1]} {int(y)}"
            for y, m in zip(df["year"], df["month"])
        ]
        last_year  = int(df["year"].iloc[-1])
        last_month = int(df["month"].iloc[-1])
    else:
        labels_hist = [_MESES[int(m)-1] for m in df["month"]]
        last_year   = 2022
        last_month  = int(df["month"].iloc[-1])

    # Ajuste del modelo
    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing as ES
        mdl = ES(
            otp_vals,
            trend="add" if n_hist >= 6 else None,
            seasonal=None,
        ).fit(optimized=True, use_brute=False)
        forecast   = list(mdl.forecast(horizonte))
        resid_std  = float(mdl.resid.std()) if hasattr(mdl, "resid") else 2.0
        ic_width   = 1.96 * max(resid_std, 0.5)
    except Exception:
        media    = sum(otp_vals[-min(6, n_hist):]) / min(6, n_hist)
        forecast = [round(media, 1)] * horizonte
        ic_width = 5.0

    fc = [min(100.0, max(0.0, _safe(v))) for v in forecast]
    ic_sup = [round(min(100.0, v + ic_width), 1) for v in fc]
    ic_inf = [round(max(0.0,   v - ic_width), 1) for v in fc]

    # Etiquetas de proyección
    labels_proy = []
    for i in range(1, horizonte + 1):
        m = (last_month + i - 1) % 12 + 1
        y = last_year + (last_month + i - 1) // 12
        labels_proy.append(f"{_MESES[m-1]} {y}")

    return {
        "historico":   [round(_safe(v), 1) for v in otp_vals],
        "proyeccion":  [round(v, 1) for v in fc],
        "ic_sup":      ic_sup,
        "ic_inf":      ic_inf,
        "meses_hist":  labels_hist,
        "meses_proy":  labels_proy,
        "advertencia": n_hist < 12,
        "n_meses":     n_hist,
    }


# ── Mapa de calor estacional ──────────────────────────────────────────────────

def _heatmap_data(metric: str = "otp", airline: str = "") -> dict:
    cache_key = f"{metric}:{airline}"
    entry = _heatmap_cache.get(cache_key)
    if entry and time.time() < entry["expires"]:
        return entry["data"]

    try:
        filtros = {"airline": airline} if airline else {}
        df = load_enriched_fact(filtros if filtros else None)
    except Exception:
        df = pd.DataFrame()

    matrix: list[list] = [[None] * 12 for _ in range(7)]

    if not df.empty and "Month" in df.columns and "DayOfWeek" in df.columns:
        for day in range(1, 8):
            for month in range(1, 13):
                sub = df[(df["DayOfWeek"] == day) & (df["Month"] == month)]
                if sub.empty:
                    continue
                if metric == "otp" and "ArrDel15" in sub.columns:
                    val = float((sub["ArrDel15"] == 0).sum() / len(sub) * 100)
                elif metric == "cancelacion" and "Cancelled" in sub.columns:
                    val = float(sub["Cancelled"].mean() * 100)
                elif metric == "retraso" and "ArrDelayMinutes" in sub.columns:
                    val = float(sub["ArrDelayMinutes"].fillna(0).mean())
                else:
                    val = 0.0
                matrix[day - 1][month - 1] = round(_safe(val), 1)

    result = {"matrix": matrix, "rows": _DIAS, "cols": _MESES, "metric": metric}
    _heatmap_cache[cache_key] = {"data": result, "expires": time.time() + _HEATMAP_TTL}
    return result


# ── Recomendaciones automáticas priorizadas ───────────────────────────────────

def _generar_recomendaciones(df_otp: pd.DataFrame, airline: str = "") -> list[dict]:
    recs: list[dict] = []
    if df_otp.empty or "otp" not in df_otp.columns:
        return recs

    otp_global = float(df_otp["otp"].mean())
    scope      = f"de la aerolínea {airline}" if airline else "de la red"

    # Recomendación 1: nivel OTP global
    if otp_global < 75:
        recs.append({
            "prioridad": "alta", "icono": "bi-exclamation-triangle-fill", "color": "#ef4444",
            "titulo": "OTP crítico — acción inmediata requerida",
            "descripcion": (
                f"El OTP promedio {scope} es {otp_global:.1f}%, por debajo del umbral crítico del 75%. "
                "Se recomienda auditoría de procesos operativos y revisión de turnarounds."
            ),
            "modulo": "Puntualidad", "revisado": False,
            "justificacion": f"OTP promedio de {len(df_otp)} meses: {otp_global:.1f}%.",
        })
    elif otp_global < 82:
        recs.append({
            "prioridad": "media", "icono": "bi-exclamation-circle-fill", "color": "#f59e0b",
            "titulo": "OTP por debajo del benchmark — monitoreo recomendado",
            "descripcion": (
                f"El OTP de {otp_global:.1f}% está por debajo del benchmark del 82%. "
                "Revisar causas de retraso por tipo (carrier / weather / NAS)."
            ),
            "modulo": "Puntualidad", "revisado": False,
            "justificacion": f"Análisis de {len(df_otp)} períodos mensuales.",
        })
    else:
        recs.append({
            "prioridad": "baja", "icono": "bi-check-circle-fill", "color": "#10b981",
            "titulo": "OTP dentro del benchmark — mantener estándares",
            "descripcion": (
                f"El OTP de {otp_global:.1f}% supera el benchmark de 82%. "
                "Continuar monitoreo mensual y revisar rutas con mayor variabilidad."
            ),
            "modulo": "Puntualidad", "revisado": False,
            "justificacion": f"OTP positivo en {len(df_otp)} meses de histórico.",
        })

    # Recomendación 2: meses más débiles (agrupados por mes para evitar duplicados)
    if "month" in df_otp.columns and len(df_otp) >= 3:
        peores_mes = (df_otp.groupby("month")["otp"].mean()
                      .nsmallest(min(2, df_otp["month"].nunique()))
                      .reset_index())
        m_nombres  = [_MESES[int(m) - 1] for m in peores_mes["month"]]
        m_valores  = [f"{v:.1f}%" for v in peores_mes["otp"]]
        desc_meses = ", ".join(f"{n} ({v})" for n, v in zip(m_nombres, m_valores))
        recs.append({
            "prioridad": "media", "icono": "bi-calendar-x-fill", "color": "#f59e0b",
            "titulo": f"Mayor riesgo estacional en {' y '.join(m_nombres)}",
            "descripcion": (
                f"Los meses con menor OTP histórico son {desc_meses}. "
                "Planificar refuerzos operativos y mayor margen de conexión en esos períodos."
            ),
            "modulo": "Predictivo", "revisado": False,
            "justificacion": "Análisis del percentil inferior del histórico mensual.",
        })

    # Recomendación 3: variabilidad
    if len(df_otp) >= 3:
        std_otp = float(df_otp["otp"].std())
        if std_otp > 8:
            recs.append({
                "prioridad": "alta", "icono": "bi-graph-down-arrow", "color": "#ef4444",
                "titulo": "Alta variabilidad operativa — contingencia necesaria",
                "descripcion": (
                    f"La desviación estándar del OTP es {std_otp:.1f} puntos porcentuales, "
                    "indicando alta irregularidad. Implementar protocolos de recuperación y buffers de tiempo."
                ),
                "modulo": "Predictivo", "revisado": False,
                "justificacion": f"σ(OTP) = {std_otp:.1f}%p en el período analizado.",
            })
        else:
            recs.append({
                "prioridad": "baja", "icono": "bi-graph-up-arrow", "color": "#10b981",
                "titulo": "Operación estable — optimizar asignación de capacidad",
                "descripcion": (
                    f"La variabilidad del OTP (σ={std_otp:.1f}%p) es baja, indicando consistencia. "
                    "Oportunidad para optimizar gates y rotaciones de flota."
                ),
                "modulo": "Predictivo", "revisado": False,
                "justificacion": "Baja dispersión en el histórico mensual de OTP.",
            })

    return sorted(recs, key=lambda r: {"alta": 0, "media": 1, "baja": 2}[r["prioridad"]])


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
def predictivo_index(
    request: Request,
    airline: str = "",
    year: str    = "",
    metric: str  = "otp",
    horizonte: int = 6,
):
    _perm_ver(request)
    aerolinas    = get_aerolinas()
    years        = get_years()
    horizonte_max = _get_horizonte_max()
    horizonte    = max(1, min(horizonte, horizonte_max))

    heatmap   = _heatmap_data(metric=metric, airline=airline)
    df_otp    = _load_otp_series(airline=airline, year=year)
    proyeccion: dict = {}
    if not df_otp.empty and len(df_otp) >= 3:
        proyeccion = _proyectar_otp(df_otp, horizonte)
    recs = _generar_recomendaciones(df_otp, airline=airline)

    return render(request, "predictivo/index.html", {
        "aerolinas":     aerolinas,
        "years":         years,
        "airline":       airline,
        "year":          year,
        "metric":        metric,
        "horizonte":     horizonte,
        "horizonte_max": horizonte_max,
        "heatmap":       heatmap,
        "proyeccion":    proyeccion,
        "recomendaciones": recs,
    })


@router.post("/proyeccion")
async def generar_proyeccion(request: Request):
    _perm_ver(request)
    form      = await request.form()
    airline   = str(form.get("airline", ""))
    year      = str(form.get("year", ""))
    horizonte = int(form.get("horizonte", "6"))
    horizonte = max(1, min(horizonte, _get_horizonte_max()))

    df_otp = _load_otp_series(airline=airline, year=year)
    if df_otp.empty or len(df_otp) < 3:
        return JSONResponse({"error": "Datos insuficientes. Se necesitan al menos 3 meses de historial."})

    return JSONResponse(_proyectar_otp(df_otp, horizonte))


@router.get("/estacionalidad")
def estacionalidad(request: Request, airline: str = "", metric: str = "otp"):
    _perm_ver(request)
    return JSONResponse(_heatmap_data(metric=metric, airline=airline))


@router.get("/recomendaciones")
def recomendaciones(request: Request, airline: str = "", year: str = ""):
    _perm_ver(request)
    df_otp = _load_otp_series(airline=airline, year=year)
    return JSONResponse(_generar_recomendaciones(df_otp, airline=airline))
