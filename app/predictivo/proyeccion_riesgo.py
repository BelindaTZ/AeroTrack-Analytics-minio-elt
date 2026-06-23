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
        metodo     = "Holt-Winters (Suavizamiento Exponencial)"
        fitted     = [round(min(100.0, max(0.0, _safe(v))), 1) for v in mdl.fittedvalues]
        mae_val    = float(pd.Series([abs(r - f) for r, f in zip(otp_vals, fitted)]).mean())
        precision_estimada = round(100.0 - mae_val, 1) if mae_val < 100 else None
    except Exception:
        media    = sum(otp_vals[-min(6, n_hist):]) / min(6, n_hist)
        forecast = [round(media, 1)] * horizonte
        ic_width = 5.0
        metodo   = "Media móvil (6 meses)"
        fitted   = []
        precision_estimada = None

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
        "historico":          [round(_safe(v), 1) for v in otp_vals],
        "proyeccion":         [round(v, 1) for v in fc],
        "ic_sup":             ic_sup,
        "ic_inf":             ic_inf,
        "meses_hist":         labels_hist,
        "meses_proy":         labels_proy,
        "advertencia":        n_hist < 12,
        "n_meses":            n_hist,
        "metodo":             metodo,
        "ajustado":           fitted,
        "precision_estimada": precision_estimada,
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
            "impacto_estimado": f"+{82 - otp_global:.1f}pp para alcanzar benchmark del 82%",
            "accion_directa": "Auditar causas de retraso por tipo (carrier/weather/NAS) e implementar plan de recuperación de turnarounds.",
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
            "impacto_estimado": f"+{82 - otp_global:.1f}pp para alcanzar benchmark del 82%",
            "accion_directa": "Revisar causas de retraso por tipo (carrier/weather/NAS) y programar auditoría en los próximos 30 días.",
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
            "impacto_estimado": f"OTP {otp_global:.1f}% — {otp_global - 82:.1f}pp sobre benchmark",
            "accion_directa": "Documentar buenas prácticas actuales y evaluar optimización de gates y rotaciones de flota.",
        })

    # Recomendación 2: meses más débiles (agrupados por mes para evitar duplicados)
    if "month" in df_otp.columns and len(df_otp) >= 3:
        por_mes    = df_otp.groupby("month")["otp"].mean()
        peores_mes = por_mes.nsmallest(min(2, df_otp["month"].nunique())).reset_index()
        m_nombres  = [_MESES[int(m) - 1] for m in peores_mes["month"]]
        m_valores  = [f"{v:.1f}%" for v in peores_mes["otp"]]
        desc_meses = ", ".join(f"{n} ({v})" for n, v in zip(m_nombres, m_valores))
        n_meses_riesgo = len(peores_mes)
        pct_riesgo = round(n_meses_riesgo / max(por_mes.count(), 1) * 100)
        recs.append({
            "prioridad": "media", "icono": "bi-calendar-x-fill", "color": "#f59e0b",
            "titulo": f"Mayor riesgo estacional en {' y '.join(m_nombres)}",
            "descripcion": (
                f"Los meses con menor OTP histórico son {desc_meses}. "
                "Planificar refuerzos operativos y mayor margen de conexión en esos períodos."
            ),
            "modulo": "Predictivo", "revisado": False,
            "justificacion": "Análisis del percentil inferior del histórico mensual.",
            "impacto_estimado": f"Meses de riesgo representan ~{pct_riesgo}% del historial analizado",
            "accion_directa": f"Planificar refuerzos operativos en {' y '.join(m_nombres)}: ampliar buffers de conexión y revisar asignación de gates.",
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
                "impacto_estimado": f"Dispersión ±{std_otp:.1f}pp — objetivo: reducir a <8pp",
                "accion_directa": "Implementar buffers de conexión en rutas críticas y protocolos de recuperación para reducir variabilidad operativa.",
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
                "impacto_estimado": f"Dispersión ±{std_otp:.1f}pp — operación consistente",
                "accion_directa": "Aprovechar la estabilidad para optimizar rotaciones de flota y asignación de gates en horarios de alta demanda.",
            })

    return sorted(recs, key=lambda r: {"alta": 0, "media": 1, "baja": 2}[r["prioridad"]])


# ── Detección de anomalías ────────────────────────────────────────────────────

def _sparkline_svg(vals: list[float], pos: int, tipo: str) -> str:
    """Genera SVG inline de sparkline con punto resaltado en la posición del período anómalo."""
    if len(vals) < 2:
        return ""
    w, h = 96, 32
    vmin, vmax = min(vals), max(vals)
    vrange = max(vmax - vmin, 1.0)
    pad = 4

    def cx(i: int) -> float:
        return round(pad + i / (len(vals) - 1) * (w - 2 * pad), 1)

    def cy(v: float) -> float:
        return round(h - pad - (v - vmin) / vrange * (h - 2 * pad), 1)

    points = " ".join(f"{cx(i)},{cy(v)}" for i, v in enumerate(vals))
    dx, dy = cx(pos), cy(vals[pos])
    color  = "#ef4444" if tipo == "bajo" else "#10b981"
    return (
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block;flex-shrink:0">'
        f'<polyline points="{points}" stroke="rgba(148,163,184,.45)" stroke-width="1.5" '
        f'fill="none" stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{dx}" cy="{dy}" r="3.5" fill="{color}" stroke="rgba(0,0,0,.25)" stroke-width="1"/>'
        f'</svg>'
    )


def _detectar_anomalias(df: pd.DataFrame, airline: str = "") -> list[dict]:
    """Detecta períodos atípicos comparando cada mes con su promedio histórico para ese mes."""
    if df.empty or "otp" not in df.columns or len(df) < 6:
        return []

    if "month" not in df.columns:
        return []

    # Estadísticas por posición de mes (media y std de todos los años para ese mes)
    stats = df.groupby("month")["otp"].agg(["mean", "std"]).reset_index()
    stats.columns = ["month", "mean_m", "std_m"]
    df_m = df.merge(stats, on="month", how="left")

    anomalias = []
    for _, row in df_m.iterrows():
        std_m = row["std_m"]
        if pd.isna(std_m) or std_m < 0.1:
            continue
        z = (row["otp"] - row["mean_m"]) / std_m
        if abs(z) < 1.5:
            continue

        mes_label = _MESES[int(row["month"]) - 1]
        if "year" in row and not pd.isna(row["year"]):
            periodo = f"{mes_label} {int(row['year'])}"
            yr = int(row["year"])
        else:
            periodo = mes_label
            yr = -1

        # Sparkline: OTP de ese mes a través de todos los años disponibles
        mes_rows = df_m[df_m["month"] == int(row["month"])].sort_values("year") if "year" in df_m.columns else df_m[df_m["month"] == int(row["month"])]
        spark_vals = [round(float(v), 1) for v in mes_rows["otp"].tolist()]
        spark_pos  = 0
        if "year" in mes_rows.columns:
            for i, yr_val in enumerate(mes_rows["year"].tolist()):
                if int(yr_val) == yr:
                    spark_pos = i
                    break

        delta = round(row["otp"] - row["mean_m"], 1)
        tipo  = "bajo" if z < 0 else "alto"
        anomalias.append({
            "periodo":      periodo,
            "otp":          round(row["otp"], 1),
            "promedio_mes": round(row["mean_m"], 1),
            "delta":        delta,
            "z":            round(float(z), 2),
            "tipo":         tipo,
            "sparkline":    _sparkline_svg(spark_vals, spark_pos, tipo),
        })

    # Mostrar las 3 más negativas + 2 más positivas (eventos malos y sorprendentemente buenos)
    negativas = sorted([a for a in anomalias if a["z"] < 0], key=lambda a: a["z"])
    positivas = sorted([a for a in anomalias if a["z"] > 0], key=lambda a: a["z"], reverse=True)
    seleccion = negativas[:3] + positivas[:2]
    seleccion.sort(key=lambda a: a["z"])  # negativos primero, luego positivos
    return seleccion


# ── Índice de riesgo compuesto por aerolínea ─────────────────────────────────

def _calcular_ranking_riesgo(year: str = "") -> list[dict]:
    """Score compuesto 0-100 por aerolínea: OTP (60%) + estabilidad (40%)."""
    filtros: dict = {"year": year} if year else {}
    try:
        df = load_agg("agg_otp_aerolinea_mes", filtros if filtros else None)
    except Exception:
        return []
    if df.empty:
        return []

    carrier_col = next((c for c in ["carrier", "Reporting_Airline"] if c in df.columns), None)
    if not carrier_col:
        return []

    df = df.copy()
    df["otp_row"] = (
        df["vuelos_a_tiempo"] / df["total_vuelos"].replace(0, float("nan")) * 100
    ).fillna(0.0)

    agg = (
        df.groupby(carrier_col)
        .agg(total=("total_vuelos", "sum"), a_tiempo=("vuelos_a_tiempo", "sum"),
             n_meses=(carrier_col, "count"))
        .reset_index()
    )
    agg["otp_mean"] = (
        agg["a_tiempo"] / agg["total"].replace(0, float("nan")) * 100
    ).fillna(0.0)

    std_df = df.groupby(carrier_col)["otp_row"].std().reset_index()
    std_df.columns = [carrier_col, "otp_std"]
    agg = agg.merge(std_df, on=carrier_col, how="left")
    agg["otp_std"] = agg["otp_std"].fillna(0.0)

    # Tendencia: promedio últimos 2 períodos vs 2 anteriores
    tendencia_map:       dict = {}
    tendencia_delta_map: dict = {}
    if "year" in df.columns and "month" in df.columns:
        df_s = df.sort_values(["year", "month"])
        for airline, grp in df_s.groupby(carrier_col):
            vals = grp["otp_row"].tolist()
            if len(vals) >= 4:
                diff = sum(vals[-2:]) / 2 - sum(vals[-4:-2]) / 2
                tendencia_map[airline]       = "up" if diff > 1.5 else ("down" if diff < -1.5 else "stable")
                tendencia_delta_map[airline] = round(diff, 1)
            else:
                tendencia_map[airline]       = "stable"
                tendencia_delta_map[airline] = 0.0

    otp_min, otp_max = float(agg["otp_mean"].min()), float(agg["otp_mean"].max())
    std_min, std_max = float(agg["otp_std"].min()), float(agg["otp_std"].max())

    def _norm(val: float, lo: float, hi: float, invert: bool = False) -> float:
        if hi == lo:
            return 50.0
        n = (val - lo) / (hi - lo) * 100.0
        return round(100.0 - n if invert else n, 1)

    result = []
    for _, row in agg.iterrows():
        airline   = str(row[carrier_col])
        otp_score = _norm(float(row["otp_mean"]), otp_min, otp_max)
        std_score = _norm(float(row["otp_std"]), std_min, std_max, invert=True)
        score     = round(0.6 * otp_score + 0.4 * std_score, 1)
        nivel     = "estable" if score >= 70 else ("riesgo" if score >= 50 else "critico")
        result.append({
            "airline":          airline,
            "otp":              round(float(row["otp_mean"]), 1),
            "std":              round(float(row["otp_std"]), 1),
            "score":            score,
            "nivel":            nivel,
            "tendencia":        tendencia_map.get(airline, "stable"),
            "tendencia_delta":  tendencia_delta_map.get(airline, 0.0),
            "n_meses":          int(row["n_meses"]),
        })

    return sorted(result, key=lambda r: r["score"], reverse=True)


def _simular_whatif(
    df_otp: pd.DataFrame,
    horizonte: int,
    buffer_minutos: int,
    reduccion_carga: int,
) -> dict:
    """Proyecta OTP ajustando por escenario what-if (buffer/reducción de carga).
    Computa la proyección base y aplica el delta a los valores proyectados."""
    base = _proyectar_otp(df_otp, horizonte)
    if "error" in base:
        return base

    BUFFER_FACTOR = 0.7   # pp por cada 5 min de buffer
    VOL_FACTOR    = 0.3   # pp por cada 10% de reducción de carga
    delta = (buffer_minutos / 5) * BUFFER_FACTOR + (reduccion_carga / 10) * VOL_FACTOR

    if delta > 0:
        for key in ("proyeccion", "ic_sup", "ic_inf"):
            if key in base and isinstance(base[key], list):
                base[key] = [min(100.0, round(v + delta, 1)) for v in base[key]]

    base["whatif"] = {
        "delta": round(delta, 2),
        "buffer_minutos": buffer_minutos,
        "reduccion_carga": reduccion_carga,
    }
    return base


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
    recs           = _generar_recomendaciones(df_otp, airline=airline)
    anomalias      = _detectar_anomalias(df_otp, airline=airline)
    ranking_riesgo = _calcular_ranking_riesgo(year=year)

    return render(request, "predictivo/index.html", {
        "aerolinas":       aerolinas,
        "years":           years,
        "airline":         airline,
        "year":            year,
        "metric":          metric,
        "horizonte":       horizonte,
        "horizonte_max":   horizonte_max,
        "heatmap":         heatmap,
        "proyeccion":      proyeccion,
        "recomendaciones": recs,
        "anomalias":       anomalias,
        "ranking_riesgo":  ranking_riesgo,
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


@router.post("/whatif")
async def whatif(request: Request):
    _perm_ver(request)
    body       = await request.json()
    airline    = str(body.get("aerolinea", ""))
    year       = str(body.get("anio", ""))
    horizonte  = int(body.get("horizonte", 6))
    buffer_min = max(0, min(30, int(body.get("buffer_minutos", 0))))
    reduccion  = max(0, min(30, int(body.get("reduccion_carga", 0))))
    horizonte  = max(1, min(horizonte, _get_horizonte_max()))

    df_otp = _load_otp_series(airline=airline, year=year)
    if df_otp.empty or len(df_otp) < 3:
        return JSONResponse({"error": "Datos insuficientes."}, status_code=400)

    return JSONResponse(_simular_whatif(df_otp, horizonte, buffer_min, reduccion))


@router.get("/estacionalidad")
def estacionalidad(request: Request, airline: str = "", metric: str = "otp"):
    _perm_ver(request)
    return JSONResponse(_heatmap_data(metric=metric, airline=airline))


@router.get("/recomendaciones")
def recomendaciones(request: Request, airline: str = "", year: str = ""):
    _perm_ver(request)
    df_otp = _load_otp_series(airline=airline, year=year)
    return JSONResponse(_generar_recomendaciones(df_otp, airline=airline))


@router.get("/anomalias")
def anomalias_endpoint(request: Request, airline: str = "", year: str = ""):
    _perm_ver(request)
    df_otp = _load_otp_series(airline=airline, year=year)
    return JSONResponse(_detectar_anomalias(df_otp, airline=airline))


@router.get("/ranking_riesgo")
def ranking_riesgo_endpoint(request: Request, year: str = ""):
    _perm_ver(request)
    return JSONResponse(_calcular_ranking_riesgo(year=year))
