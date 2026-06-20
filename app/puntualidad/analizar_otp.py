"""Módulo de puntualidad OTP (CU-19, CU-20, CU-21)."""

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
_perm_ver = require_permission("puntualidad", "ver")

_MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
          "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

_page_cache: dict = {}
_PAGE_TTL = 300

_CAUSA_LABEL_MAP = {
    "carrierdelay":      "Carrier",
    "weatherdelay":      "Weather",
    "nasdelay":          "NAS",
    "securitydelay":     "Security",
    "lateaircraftdelay": "LateAircraft",
}


def _safe(v: Any) -> Any:
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return 0.0
    return v


def _otp_por_aerolinea_agg(df_otp: pd.DataFrame) -> list[dict]:
    """Tabla OTP por aerolínea desde agg_otp_aerolinea_mes."""
    if "carrier" not in df_otp.columns or df_otp.empty:
        return []
    grp = df_otp.groupby("carrier").agg(
        total=("total_vuelos", "sum"),
        vuelos_at=("vuelos_a_tiempo", "sum"),
    ).reset_index()
    grp["otp"] = (grp["vuelos_at"] / grp["total"].replace(0, float("nan")) * 100).fillna(0.0).round(2)
    grp = grp[grp["total"] >= 50].sort_values("total", ascending=False).head(25)
    return grp[["carrier", "total", "otp"]].rename(columns={"carrier": "aerolinea"}).to_dict("records")


def _causas_retraso_agg(df_causas: pd.DataFrame) -> dict:
    """Distribución de causas de retraso desde agg_causas_retraso_mes."""
    result: dict = {"labels": [], "counts": []}
    if df_causas.empty:
        return result
    for col, label in _CAUSA_LABEL_MAP.items():
        if col in df_causas.columns:
            total = float(df_causas[col].fillna(0).sum())
            if total > 0:
                result["labels"].append(label)
                result["counts"].append(round(_safe(total), 0))
    return result


def _tendencias_otp_mensual_agg(df_otp: pd.DataFrame, airline: str = "") -> dict:
    """Tendencia OTP mensual desde agg_otp_aerolinea_mes."""
    if "month" not in df_otp.columns or df_otp.empty:
        return {"meses": [], "otp": [], "airline": airline}
    grp = df_otp.groupby("month").agg(
        total=("total_vuelos", "sum"),
        vuelos_at=("vuelos_a_tiempo", "sum"),
    ).reset_index().sort_values("month")
    grp["otp"] = (grp["vuelos_at"] / grp["total"].replace(0, float("nan")) * 100).fillna(0.0).round(1)
    meses = [_MESES[int(m) - 1] if 1 <= int(m) <= 12 else str(m) for m in grp["month"].tolist()]
    return {"meses": meses, "otp": grp["otp"].tolist(), "airline": airline}


def _tendencias_dia_semana_agg(df_dia: pd.DataFrame) -> dict:
    """OTP por día de semana desde agg_otp_dia_semana."""
    if "day_of_week" not in df_dia.columns or df_dia.empty:
        return {"dias": [], "otp": []}
    dias_label = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    grp = df_dia.sort_values("day_of_week")
    dias = [dias_label[int(d) - 1] if 1 <= int(d) <= 7 else str(d) for d in grp["day_of_week"].tolist()]
    return {"dias": dias, "otp": grp["otp_pct"].tolist()}


def _compute_page(filtros: dict) -> dict:
    """Computa todos los datos del módulo OTP desde agregaciones; cacheado 5 min."""
    key = str(sorted(filtros.items()))
    entry = _page_cache.get(key)
    if entry and time.time() < entry["expires"]:
        return entry["data"]

    df_otp    = load_agg("agg_otp_aerolinea_mes",  filtros)
    df_causas = load_agg("agg_causas_retraso_mes",  filtros)
    df_dia    = load_agg("agg_otp_dia_semana")          # sin filtros de aerolínea/mes

    data = {
        "datos_otp":     _otp_por_aerolinea_agg(df_otp),
        "causas":        _causas_retraso_agg(df_causas),
        "tendencias":    _tendencias_otp_mensual_agg(df_otp, filtros.get("airline", "")),
        "tendencias_dia":_tendencias_dia_semana_agg(df_dia),
    }
    _page_cache[key] = {"data": data, "expires": time.time() + _PAGE_TTL}
    return data


@router.get("", response_class=HTMLResponse)
def index_otp(request: Request, year: str = "", month: str = "", airline: str = ""):
    user = _perm_ver(request)
    error = None
    datos_otp: list[dict] = []
    causas: dict = {"labels": [], "counts": []}
    tendencias: dict = {"meses": [], "otp": []}
    tendencias_dia: dict = {"dias": [], "otp": []}

    try:
        filtros = {k: v for k, v in {"year": year, "month": month, "airline": airline}.items() if v}
        data = _compute_page(filtros)
        datos_otp      = data["datos_otp"]
        causas         = data["causas"]
        tendencias     = data["tendencias"]
        tendencias_dia = data["tendencias_dia"]

    except FileNotFoundError:
        error = "Los datos no están disponibles. Ejecute el pipeline ELT primero."
    except Exception as exc:
        error = f"Error al cargar datos: {exc}"

    return render(request, "puntualidad/index.html", {
        "datos_otp":      datos_otp,
        "causas":         causas,
        "tendencias":     tendencias,
        "tendencias_dia": tendencias_dia,
        "aerolinas":      get_aerolinas(),
        "years":          get_years(),
        "filtros":        {"year": year, "month": month, "airline": airline},
        "error":          error,
    })


@router.get("/narrativa")
def narrativa_json(
    request: Request,
    year: str = "", month: str = "", airline: str = "",
    tipo: str = "", airline_val: str = "", causa: str = "", mes: str = "", dia: str = "",
):
    _perm_ver(request)
    try:
        from app.shared.airline_names import airline_name
        filtros = {k: v for k, v in {"year": year, "month": month, "airline": airline}.items() if v}
        data = _compute_page(filtros)
        datos_otp     = data["datos_otp"]
        causas        = data["causas"]
        tendencias    = data["tendencias"]
        tendencias_dia = data["tendencias_dia"]

        ctx: dict = {}
        focus = ""

        if tipo == "aerolinea" and airline_val:
            al = next((r for r in datos_otp if r["aerolinea"] == airline_val), None)
            if al:
                otp_prom = sum(r["otp"] for r in datos_otp) / len(datos_otp)
                rank = sorted(datos_otp, key=lambda x: x["otp"], reverse=True)
                pos  = next((i + 1 for i, r in enumerate(rank) if r["aerolinea"] == airline_val), None)
                ctx["Aerolínea"]              = airline_name(airline_val)
                ctx["OTP"]                    = f"{al['otp']:.1f}%"
                ctx["Estado OTP"]             = "CUMPLE (≥80%)" if al["otp"] >= 80 else "NO CUMPLE (<80%)"
                ctx["Vuelos analizados"]      = f"{al['total']:,}"
                ctx["Posición en ranking"]    = f"{pos} de {len(datos_otp)}"
                ctx["OTP promedio del período"] = f"{otp_prom:.1f}%"
                ctx["Diferencia vs promedio"] = f"{al['otp'] - otp_prom:+.1f}%"
                focus = f"el desempeño OTP de {airline_name(airline_val)}"

        elif tipo == "causa" and causa:
            total_c = sum(causas["counts"]) if causas.get("counts") else 0
            idx = causas["labels"].index(causa) if causa in causas.get("labels", []) else -1
            if idx >= 0 and total_c > 0:
                count = causas["counts"][idx]
                pct   = count / total_c * 100
                ctx["Causa de retraso"]         = causa
                ctx["Minutos acumulados"]        = f"{count:,.0f}"
                ctx["Proporción del total"]      = f"{pct:.0f}%"
                ctx["Posición entre causas"]     = f"#{idx + 1} de {len(causas['labels'])}"
                otras = [f"{causas['labels'][j]} ({causas['counts'][j]/total_c*100:.0f}%)"
                         for j in range(min(2, len(causas["labels"]))) if j != idx]
                if otras:
                    ctx["Otras causas principales"] = ", ".join(otras)
                focus = f"la causa '{causa}' como factor de retraso"

        elif tipo == "mes" and mes:
            meses  = tendencias.get("meses", [])
            otps   = tendencias.get("otp", [])
            idx    = meses.index(mes) if mes in meses else -1
            if idx >= 0 and otps:
                otp_mes  = otps[idx]
                otp_prom = sum(otps) / len(otps)
                mejor_m  = meses[otps.index(max(otps))]
                peor_m   = meses[otps.index(min(otps))]
                ctx["Mes"]                  = mes
                ctx["OTP"]                  = f"{otp_mes:.1f}%"
                ctx["Estado OTP"]           = "CUMPLE (≥80%)" if otp_mes >= 80 else "NO CUMPLE (<80%)"
                ctx["OTP promedio anual"]   = f"{otp_prom:.1f}%"
                ctx["Diferencia vs promedio"] = f"{otp_mes - otp_prom:+.1f}%"
                ctx["Mejor mes del período"] = mejor_m
                ctx["Peor mes del período"]  = peor_m
                focus = f"el OTP del mes de {mes} en contexto anual"

        elif tipo == "dia" and dia:
            dias = tendencias_dia.get("dias", [])
            otps = tendencias_dia.get("otp", [])
            idx  = dias.index(dia) if dia in dias else -1
            if idx >= 0 and otps:
                otp_dia  = otps[idx]
                otp_prom = sum(otps) / len(otps)
                mejor_d  = dias[otps.index(max(otps))]
                ctx["Día de semana"]             = dia
                ctx["OTP"]                       = f"{otp_dia:.1f}%"
                ctx["Estado OTP"]                = "CUMPLE (≥80%)" if otp_dia >= 80 else "NO CUMPLE (<80%)"
                ctx["OTP promedio semanal"]      = f"{otp_prom:.1f}%"
                ctx["Diferencia vs promedio"]    = f"{otp_dia - otp_prom:+.1f}%"
                ctx["Día con mejor puntualidad"] = mejor_d
                focus = f"la puntualidad del {dia} como día de operación"

        else:
            if datos_otp:
                otp_prom = sum(r["otp"] for r in datos_otp) / len(datos_otp)
                sorted_al = sorted(datos_otp, key=lambda x: x["otp"])
                ctx["Aerolíneas analizadas"]         = len(datos_otp)
                ctx["OTP promedio"]                  = f"{otp_prom:.1f}%"
                ctx["Estado OTP global"]             = "CUMPLE (≥80%)" if otp_prom >= 80 else "NO CUMPLE (<80%)"
                ctx["Aerolínea con mejor OTP"]       = f"{airline_name(sorted_al[-1]['aerolinea'])} ({sorted_al[-1]['otp']:.1f}%)"
                ctx["Aerolínea con peor OTP"]        = f"{airline_name(sorted_al[0]['aerolinea'])} ({sorted_al[0]['otp']:.1f}%)"
                ctx["Aerolíneas bajo el umbral 80%"] = f"{sum(1 for r in datos_otp if r['otp'] < 80)} de {len(datos_otp)}"
            if causas.get("labels") and causas.get("counts"):
                total_causas = sum(causas["counts"])
                for i, (label, count) in enumerate(zip(causas["labels"][:2], causas["counts"][:2])):
                    pct = count / total_causas * 100 if total_causas > 0 else 0
                    ctx[f"Causa #{i + 1}"] = f"{label} ({pct:.0f}%)"
            focus = "el OTP global del período y las aerolíneas más críticas"

        return JSONResponse(generar_narrativa(ctx, "Puntualidad OTP", focus))
    except Exception:
        return JSONResponse({"texto": "", "proveedor": "", "desde_cache": False})


@router.get("/comparar", response_class=HTMLResponse)
def comparar(request: Request, ruta: str = "", year: str = ""):
    _perm_ver(request)
    error = None
    datos: list[dict] = []

    try:
        if ruta and "-" in ruta:
            partes = ruta.split("-", 1)
            origen, dest = partes[0], partes[1]
            filtros = {"year": year} if year else {}
            df_rutas = load_agg("agg_rutas_eficiencia", filtros)
            if "origin" in df_rutas.columns and "dest" in df_rutas.columns:
                sub = df_rutas[(df_rutas["origin"] == origen) & (df_rutas["dest"] == dest)]
                if len(sub) > 0 and "carrier" in sub.columns:
                    datos = (
                        sub[["carrier", "total_vuelos", "otp_pct", "retraso_prom"]]
                        .rename(columns={
                            "carrier":      "aerolinea",
                            "total_vuelos": "total",
                            "otp_pct":      "otp",
                            "retraso_prom": "retraso",
                        })
                        .sort_values("total", ascending=False)
                        .to_dict("records")
                    )
    except Exception as exc:
        error = str(exc)

    rutas_disponibles: list[str] = []
    try:
        df_r = load_agg("agg_rutas_eficiencia")
        if "origin" in df_r.columns and "dest" in df_r.columns:
            rutas_disponibles = sorted(
                (df_r["origin"].astype(str) + "-" + df_r["dest"].astype(str))
                .dropna().unique().tolist()[:500]
            )
    except Exception:
        pass

    return render(request, "puntualidad/comparar.html", {
        "datos": datos, "ruta": ruta, "year": year,
        "rutas_disponibles": rutas_disponibles, "years": get_years(), "error": error,
    })
