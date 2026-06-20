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

_AIRLINE_NAMES: dict[str, str] = {
    "AA": "American Airlines",
    "DL": "Delta Air Lines",
    "UA": "United Airlines",
    "WN": "Southwest Airlines",
    "B6": "JetBlue Airways",
    "AS": "Alaska Airlines",
    "NK": "Spirit Airlines",
    "F9": "Frontier Airlines",
    "G4": "Allegiant Air",
    "HA": "Hawaiian Airlines",
    "SY": "Sun Country Airlines",
    "VX": "Virgin America",
    "OO": "SkyWest Airlines",
    "MQ": "Envoy Air",
    "YX": "Republic Airways",
    "9E": "Endeavor Air",
    "OH": "PSA Airlines",
    "EV": "ExpressJet Airlines",
    "QX": "Horizon Air",
    "YV": "Mesa Airlines",
    "G7": "GoJet Airlines",
    "ZW": "Air Wisconsin",
    "PT": "Piedmont Airlines",
    "CP": "Compass Airlines",
    "C5": "CommutAir",
    "KS": "Peninsula Airways",
    "EM": "Empire Airlines",
}


def _airline_name(code: str) -> str:
    return _AIRLINE_NAMES.get(code, code)

_umbrales_cache: dict = {"data": None, "expires": 0.0}
_UMBRALES_TTL = 60

_page_cache: dict = {}
_PAGE_TTL = 300


def invalidar_cache_alertas() -> None:
    """Invalida el caché de umbrales y páginas del dashboard. Llamar al guardar configuración de alertas."""
    global _umbrales_cache
    _umbrales_cache = {"data": None, "expires": 0.0}
    _page_cache.clear()


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


_MESES_ES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
             "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]


@router.get("/narrativa")
def narrativa_json(
    request: Request,
    year: str = "", month: str = "", airline: str = "",
    tipo: str = "", id: str = "",
):
    _perm_ver(request)
    try:
        filtros = {k: v for k, v in {"year": year, "month": month, "airline": airline}.items() if v}
        data    = _compute_page(filtros)
        kpis    = data["kpis"]
        df      = load_agg("agg_otp_aerolinea_mes", filtros)  # cached, sin costo extra
        umbrales = _get_umbrales()

        otp_min     = umbrales["otp_min"]
        cancel_max  = umbrales["cancel_max"]
        retraso_max = umbrales["retraso_max"]

        def _otp_estado(v):
            return f"CUMPLE (≥{otp_min:.0%})" if v >= otp_min else f"NO CUMPLE (<{otp_min:.0%})"

        def _cancel_estado(v):
            return f"CUMPLE (≤{cancel_max:.0%})" if v <= cancel_max else f"NO CUMPLE (>{cancel_max:.0%})"

        def _retraso_estado(v):
            return f"CUMPLE (≤{retraso_max:.0f} min)" if v <= retraso_max else f"NO CUMPLE (>{retraso_max:.0f} min)"

        col_total = "total_vuelos_todos" if "total_vuelos_todos" in df.columns else "total_vuelos"

        def _grp_carrier():
            if "carrier" not in df.columns or df.empty:
                return pd.DataFrame()
            agg = {"total": (col_total, "sum"), "op": ("total_vuelos", "sum"), "at": ("vuelos_a_tiempo", "sum")}
            if "total_cancelados" in df.columns:
                agg["cancelados"] = ("total_cancelados", "sum")
            g = df.groupby("carrier").agg(**agg)
            g["otp"] = (g["at"] / g["op"].replace(0, float("nan"))).fillna(0.0)
            if "cancelados" in g.columns:
                g["cancel_rate"] = (g["cancelados"] / g["total"].replace(0, float("nan"))).fillna(0.0)
            if "delay_avg" in df.columns:
                tmp = df.copy()
                tmp["_dw"] = tmp["delay_avg"] * tmp["total_vuelos"]
                g["delay"] = (tmp.groupby("carrier")["_dw"].sum() / g["op"]).fillna(0.0)
            return g

        def _grp_mes():
            if "month" not in df.columns or df.empty:
                return pd.DataFrame()
            agg = {"total": (col_total, "sum"), "op": ("total_vuelos", "sum"), "at": ("vuelos_a_tiempo", "sum")}
            if "total_cancelados" in df.columns:
                agg["cancelados"] = ("total_cancelados", "sum")
            g = df.groupby("month").agg(**agg)
            g["otp"] = (g["at"] / g["op"].replace(0, float("nan"))).fillna(0.0)
            if "delay_avg" in df.columns:
                tmp = df.copy()
                tmp["_dw"] = tmp["delay_avg"] * tmp["total_vuelos"]
                g["delay"] = (tmp.groupby("month")["_dw"].sum() / g["op"]).fillna(0.0)
            return g

        def _mes_nombre(m):
            try:
                return _MESES_ES[int(m) - 1]
            except Exception:
                return str(m)

        # ── contextos por tipo ───────────────────────────────────────────
        if tipo == "otp":
            gc = _grp_carrier()
            ctx = {
                "OTP global": f"{kpis['otp_global']:.1%}",
                "Umbral mínimo": f"{otp_min:.0%}",
                "Estado OTP": _otp_estado(kpis["otp_global"]),
                "Total vuelos operados": f"{kpis['total_vuelos']:,}",
            }
            if not gc.empty and "otp" in gc.columns:
                gc_v = gc[gc["op"] >= 100]
                if not gc_v.empty:
                    mejor = gc_v["otp"].idxmax()
                    peor  = gc_v["otp"].idxmin()
                    ctx["Aerolínea con mejor OTP"] = f"{_airline_name(mejor)} ({gc_v.loc[mejor,'otp']:.1%})"
                    ctx["Aerolínea con peor OTP"]  = f"{_airline_name(peor)} ({gc_v.loc[peor,'otp']:.1%})"
                    bajo = int((gc_v["otp"] < otp_min).sum())
                    ctx["Aerolíneas bajo el umbral"] = f"{bajo} de {len(gc_v)}"
            modulo = "Puntualidad (OTP)"
            focus  = "la puntualidad global y el cumplimiento del umbral OTP"

        elif tipo == "cancelacion":
            gc = _grp_carrier()
            total_canc = int(df["total_cancelados"].sum()) if "total_cancelados" in df.columns else 0
            ctx = {
                "Tasa de cancelación": f"{kpis['tasa_cancelacion']:.1%}",
                "Umbral máximo": f"{cancel_max:.0%}",
                "Estado cancelación": _cancel_estado(kpis["tasa_cancelacion"]),
                "Vuelos cancelados (cantidad)": f"{total_canc:,}",
                "Total vuelos": f"{kpis['total_vuelos']:,}",
            }
            if not gc.empty and "cancel_rate" in gc.columns:
                gc_v = gc[gc["total"] >= 100]
                if not gc_v.empty:
                    peor = gc_v["cancel_rate"].idxmax()
                    ctx["Aerolínea con mayor cancelación"] = f"{_airline_name(peor)} ({gc_v.loc[peor,'cancel_rate']:.1%})"
            modulo = "Cancelaciones"
            focus  = "la tasa de cancelación y su cumplimiento del umbral"

        elif tipo == "retraso":
            gc = _grp_carrier()
            gm = _grp_mes()
            ctx = {
                "Retraso promedio global": f"{kpis['retraso_promedio']:.1f} min",
                "Umbral máximo": f"{retraso_max:.0f} min",
                "Estado retraso": _retraso_estado(kpis["retraso_promedio"]),
                "OTP vinculado": f"{kpis['otp_global']:.1%}",
            }
            if not gc.empty and "delay" in gc.columns:
                gc_v = gc[gc["op"] >= 100].dropna(subset=["delay"])
                if not gc_v.empty:
                    peor = gc_v["delay"].idxmax()
                    ctx["Aerolínea con mayor retraso"] = f"{_airline_name(peor)} ({gc_v.loc[peor,'delay']:.1f} min)"
            if not gm.empty and "delay" in gm.columns:
                gm_v = gm.dropna(subset=["delay"])
                if not gm_v.empty:
                    peor_m = gm_v["delay"].idxmax()
                    ctx["Mes con mayor retraso"] = f"{_mes_nombre(peor_m)} ({gm_v.loc[peor_m,'delay']:.1f} min)"
            modulo = "Retrasos"
            focus  = "el retraso promedio y su impacto en la operación"

        elif tipo == "vuelos":
            gm = _grp_mes()
            gc = _grp_carrier()
            total_canc = int(df["total_cancelados"].sum()) if "total_cancelados" in df.columns else 0
            ctx = {
                "Total vuelos analizados": f"{kpis['total_vuelos']:,}",
                "Vuelos cancelados": f"{total_canc:,}",
            }
            if not gm.empty:
                mes_pico = gm["total"].idxmax()
                mes_bajo = gm["total"].idxmin()
                ctx["Mes con más vuelos"]   = f"{_mes_nombre(mes_pico)} ({int(gm.loc[mes_pico,'total']):,} vuelos)"
                ctx["Mes con menos vuelos"] = f"{_mes_nombre(mes_bajo)} ({int(gm.loc[mes_bajo,'total']):,} vuelos)"
            if not gc.empty:
                lider = gc["total"].idxmax()
                ctx["Aerolínea líder en volumen"] = f"{_airline_name(lider)} ({int(gc.loc[lider,'total']):,} vuelos)"
            modulo = "Volumen de vuelos"
            focus  = "el volumen total de operaciones y su distribución temporal"

        elif tipo == "aerolinea" and id:
            data_al = _compute_page({**filtros, "airline": id})
            k  = data_al["kpis"]
            gc = _grp_carrier()
            nombre_al = _airline_name(id)
            ctx = {
                "Aerolínea analizada": nombre_al,
                "Total vuelos": f"{k['total_vuelos']:,}",
                "OTP": f"{k['otp_global']:.1%}",
                "Estado OTP": _otp_estado(k["otp_global"]),
                "OTP promedio del conjunto": f"{kpis['otp_global']:.1%}",
                "Tasa cancelación": f"{k['tasa_cancelacion']:.1%}",
                "Estado cancelación": _cancel_estado(k["tasa_cancelacion"]),
                "Retraso promedio": f"{k['retraso_promedio']:.1f} min",
                "Estado retraso": _retraso_estado(k["retraso_promedio"]),
            }
            if not gc.empty and id in gc.index:
                por_vol = list(gc.sort_values("total", ascending=False).index)
                por_otp = list(gc[gc["op"] >= 100].sort_values("otp", ascending=False).index)
                if id in por_vol:
                    ctx["Posición en volumen"] = f"#{por_vol.index(id)+1} de {len(por_vol)} aerolíneas"
                if id in por_otp:
                    ctx["Posición en OTP"]     = f"#{por_otp.index(id)+1} de {len(por_otp)} aerolíneas"
            modulo = f"Aerolínea {nombre_al}"
            focus  = f"el desempeño operativo de {nombre_al} respecto al conjunto y sus umbrales"

        elif tipo == "mes" and id and id.isdigit() and 1 <= int(id) <= 12:
            data_mes = _compute_page({**filtros, "month": id})
            k      = data_mes["kpis"]
            nombre = _MESES_ES[int(id) - 1]
            gm     = _grp_mes()
            ctx = {
                "Mes analizado": nombre,
                "Total vuelos": f"{k['total_vuelos']:,}",
                "OTP del mes": f"{k['otp_global']:.1%}",
                "Estado OTP": _otp_estado(k["otp_global"]),
                "OTP promedio anual": f"{kpis['otp_global']:.1%}",
                "Tasa cancelación": f"{k['tasa_cancelacion']:.1%}",
                "Estado cancelación": _cancel_estado(k["tasa_cancelacion"]),
                "Retraso promedio": f"{k['retraso_promedio']:.1f} min",
                "Estado retraso": _retraso_estado(k["retraso_promedio"]),
            }
            if not gm.empty:
                por_vol = list(gm.sort_values("total", ascending=False).index)
                mes_idx = int(id)
                if mes_idx in por_vol:
                    ctx["Posición en volumen"] = f"#{por_vol.index(mes_idx)+1} de {len(por_vol)} meses"
            modulo = f"Mes de {nombre}"
            focus  = f"el desempeño de {nombre} respecto al año y sus umbrales"

        else:
            ctx = {
                "Total vuelos": f"{kpis['total_vuelos']:,}",
                "OTP global": f"{kpis['otp_global']:.1%}",
                "Estado OTP": _otp_estado(kpis["otp_global"]),
                "Tasa cancelación": f"{kpis['tasa_cancelacion']:.1%}",
                "Estado cancelación": _cancel_estado(kpis["tasa_cancelacion"]),
                "Retraso promedio": f"{kpis['retraso_promedio']:.1f} min",
                "Estado retraso": _retraso_estado(kpis["retraso_promedio"]),
                "Alertas activas": str(len(data["alertas"])),
            }
            modulo = "Dashboard KPIs"
            focus  = "el estado general de la operación y los KPIs con alertas activas"

        return JSONResponse(generar_narrativa(ctx, modulo, focus))
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
