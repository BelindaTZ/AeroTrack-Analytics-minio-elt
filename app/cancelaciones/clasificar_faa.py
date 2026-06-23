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

    # total_cancelados_faa: solo vuelos con código FAA (para el desglose del gráfico)
    # total_cancelados_all: todos los cancelados desde agg_kpi_global_dia (consistente con Dashboard)
    total_cancelados_faa = sum(values)
    total_cancelados_all = (int(df_kpi["total_cancelados"].sum())
                            if not df_kpi.empty and "total_cancelados" in df_kpi.columns
                            else total_cancelados_faa)
    tasa = _safe(total_cancelados_all / total_vuelos) if total_vuelos > 0 else 0.0

    return {
        "labels": labels,
        "counts": values,
        "descriptions": descriptions,
        "total_cancelados": total_cancelados_all,
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
    grp_cols = [c for c in ["origin", "dest", "alt_airport"] if c in df_dev.columns]
    if not grp_cols:
        return []
    grp = df_dev.groupby(grp_cols).agg(
        total_desvios=("total_desvios", "sum"),
        divarrdelay_avg=("divarrdelay_avg", "mean"),
        divdistance_avg=("divdistance_avg", "mean"),
    ).reset_index().sort_values("total_desvios", ascending=False).head(20)
    rows = []
    for _, r in grp.iterrows():
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

    has_airline = "airline" in filtros and filtros["airline"]
    if has_airline:
        df_canc = load_agg("agg_cancelaciones_aerolinea_causa", filtros)
    else:
        df_canc = load_agg("agg_cancelaciones_causa", filtros)
    df_kpi  = load_agg("agg_kpi_global_dia", {k: v for k, v in filtros.items() if k != "airline"})
    filtros_dev = {k: v for k, v in filtros.items() if k != "airline"}
    df_dev  = load_agg("agg_desvios_ruta", filtros_dev if any(k in filtros_dev for k in ["year", "month"]) else None)

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
def narrativa_json(
    request: Request,
    year: str = "", month: str = "", airline: str = "",
    tipo: str = "", code: str = "", mes: str = "", ruta: str = "",
):
    _perm_ver(request)
    try:
        filtros = {k: v for k, v in {"year": year, "month": month, "airline": airline}.items() if v}
        data = _compute_page(filtros)
        causas_data = data["causas_data"]
        tendencias  = data["tendencias"]
        desvios     = data["desvios"]

        tasa_pct   = causas_data["tasa"] * 100
        umbral_pct = 5.0
        total_c    = sum(causas_data["counts"]) if causas_data["counts"] else 0
        ctx: dict = {}
        focus = ""

        if tipo == "causa_faa" and code:
            idx = causas_data["labels"].index(code) if code in causas_data.get("labels", []) else -1
            if idx >= 0 and total_c > 0:
                count = causas_data["counts"][idx]
                desc  = causas_data["descriptions"][idx]
                pct   = count / total_c * 100
                ctx["Código FAA"]             = code
                ctx["Descripción"]            = desc
                ctx["Cancelaciones"]          = f"{count:,}"
                ctx["Proporción del total"]   = f"{pct:.0f}%"
                ctx["Tasa cancelación global"] = f"{tasa_pct:.2f}%"
                ctx["Estado tasa global"]     = "CUMPLE (≤5%)" if tasa_pct <= umbral_pct else "NO CUMPLE (>5%)"
                otras = [f"{causas_data['labels'][j]} ({causas_data['counts'][j]/total_c*100:.0f}%)"
                         for j in range(len(causas_data["labels"])) if j != idx]
                if otras:
                    ctx["Otras causas"] = ", ".join(otras[:2])
                focus = f"las cancelaciones por código FAA {code} ({desc})"

        elif tipo == "mes" and mes:
            meses = tendencias.get("meses", [])
            cancs = tendencias.get("cancelaciones", [])
            idx   = meses.index(mes) if mes in meses else -1
            if idx >= 0 and cancs:
                count    = cancs[idx]
                promedio = sum(cancs) / len(cancs)
                peak_mes = meses[cancs.index(max(cancs))]
                ctx["Mes"]                      = mes
                ctx["Cancelaciones en el mes"]  = f"{count:,}"
                ctx["Promedio mensual"]          = f"{promedio:,.0f}"
                ctx["Diferencia vs promedio"]   = f"{count - promedio:+,.0f}"
                ctx["Mes con más cancelaciones"] = peak_mes
                ctx["Tasa cancelación global"]  = f"{tasa_pct:.2f}%"
                focus = f"las cancelaciones del mes de {mes} vs el promedio del período"

        elif tipo == "desvio" and ruta:
            d = next((x for x in desvios if x["ruta"] == ruta), None)
            if d:
                ctx["Ruta desviada"]             = ruta
                ctx["Total desvíos"]             = f"{d['count']:,}"
                ctx["Aeropuerto alternativo"]    = d["alt_airport"]
                ctx["Retraso llegada prom."]     = f"{d['div_arr_delay']:.1f} min"
                ctx["Distancia adicional prom."] = f"{d['div_distance']:.1f} mi"
                focus = f"el impacto de los desvíos en la ruta {ruta}"

        elif tipo == "tasa":
            ctx["Tasa de cancelación"] = f"{tasa_pct:.2f}%"
            ctx["Estado"]              = "CUMPLE (≤5%)" if tasa_pct <= umbral_pct else "NO CUMPLE (>5%)"
            ctx["Total cancelados"]    = f"{causas_data['total_cancelados']:,}"
            ctx["Total vuelos"]        = f"{causas_data['total_vuelos']:,}"
            if causas_data["labels"] and total_c > 0:
                dom_idx = causas_data["counts"].index(max(causas_data["counts"]))
                ctx["Causa dominante"] = (
                    f"{causas_data['descriptions'][dom_idx]} "
                    f"({causas_data['counts'][dom_idx]/total_c*100:.0f}%)"
                )
            focus = "la tasa de cancelación comparada con el umbral operacional del 5%"

        else:
            ctx["Total vuelos"]            = f"{causas_data['total_vuelos']:,}"
            ctx["Total cancelados"]        = f"{causas_data['total_cancelados']:,}"
            ctx["Tasa de cancelación"]     = f"{tasa_pct:.2f}%"
            ctx["Estado tasa cancelación"] = "CUMPLE (≤5%)" if tasa_pct <= umbral_pct else "NO CUMPLE (>5%)"
            if causas_data["labels"] and total_c > 0:
                for i, (label, desc, count) in enumerate(
                    zip(causas_data["labels"][:3], causas_data["descriptions"][:3], causas_data["counts"][:3])
                ):
                    ctx[f"Causa FAA {label}"] = f"{desc}: {count:,} ({count/total_c*100:.0f}%)"
            if tendencias.get("meses") and tendencias.get("cancelaciones"):
                peak_idx = tendencias["cancelaciones"].index(max(tendencias["cancelaciones"]))
                ctx["Mes con más cancelaciones"] = (
                    f"{tendencias['meses'][peak_idx]} ({tendencias['cancelaciones'][peak_idx]:,})"
                )
            focus = "la tasa de cancelación vs umbral 5% y la causa FAA dominante"

        return JSONResponse(generar_narrativa(ctx, "Cancelaciones FAA", focus))
    except Exception:
        return JSONResponse({"texto": "", "proveedor": "", "desde_cache": False})
