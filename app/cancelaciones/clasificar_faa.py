"""Módulo de cancelaciones por código FAA (CU-24, CU-25, CU-26)."""

import math
import time
from typing import Any

import pandas as pd
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.shared.analytics import load_enriched_fact, get_aerolinas, get_years
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


def _causas_faa(df: pd.DataFrame, year: str = "", month: str = "", airline: str = "") -> dict:
    work = df.copy()
    if year and "Year" in work.columns:
        work = work[work["Year"] == int(year)]
    if month and "Month" in work.columns:
        work = work[work["Month"] == int(month)]
    if airline and "Reporting_Airline" in work.columns:
        work = work[work["Reporting_Airline"] == airline]

    cancelados = work[work["Cancelled"] == 1] if "Cancelled" in work.columns else pd.DataFrame()

    labels, values, descriptions = [], [], []
    if "CancellationCode" in cancelados.columns:
        grp = cancelados.groupby("CancellationCode").size().reset_index(name="count")
        grp = grp[grp["CancellationCode"].notna() & (grp["CancellationCode"] != "No aplica")]
        for _, row in grp.iterrows():
            code = str(row["CancellationCode"])
            labels.append(code)
            values.append(int(row["count"]))
            descriptions.append(_FAA_CODIGOS.get(code, f"Código {code}"))

    total = int(cancelados.__len__()) if len(cancelados) > 0 else 0
    total_vuelos = len(work)
    tasa = _safe(total / total_vuelos) if total_vuelos > 0 else 0.0

    return {
        "labels": labels,
        "counts": values,
        "descriptions": descriptions,
        "total_cancelados": total,
        "total_vuelos": total_vuelos,
        "tasa": round(tasa, 4),
    }


def _tendencias_mensuales(df: pd.DataFrame, year: str = "") -> dict:
    work = df.copy()
    if year and "Year" in work.columns:
        work = work[work["Year"] == int(year)]

    if "Month" not in work.columns or "Cancelled" not in work.columns:
        return {"meses": [], "cancelaciones": [], "total": []}

    grp = work.groupby("Month").agg(
        total=("pk_vuelo", "count"),
        cancelados=("Cancelled", "sum"),
    ).reset_index()
    grp["mes_label"] = grp["Month"].apply(
        lambda m: _MESES[int(m) - 1] if 1 <= int(m) <= 12 else str(m)
    )

    causas_data: dict[str, list] = {}
    if "CancellationCode" in work.columns:
        for code in ["A", "B", "C", "D"]:
            sub = work[work["CancellationCode"] == code]
            if len(sub) > 0:
                sub_grp = sub.groupby("Month").size().reset_index(name="count")
                mes_dict = dict(zip(sub_grp["Month"], sub_grp["count"]))
                causas_data[code] = [int(mes_dict.get(m, 0)) for m in grp["Month"]]

    return {
        "meses": grp["mes_label"].tolist(),
        "cancelaciones": grp["cancelados"].astype(int).tolist(),
        "total": grp["total"].astype(int).tolist(),
        "causas": causas_data,
    }


def _desvios(df: pd.DataFrame) -> list[dict]:
    if "Diverted" not in df.columns:
        return []
    desviados = df[df["Diverted"] == 1].copy()
    if len(desviados) == 0:
        return []

    cols_needed = {"OriginCode", "DestCode", "DivArrDelay", "DivDistance", "Div1Airport"}
    present = cols_needed & set(desviados.columns)
    if "OriginCode" not in present:
        return []

    grp_cols = [c for c in ["OriginCode", "DestCode", "Div1Airport"] if c in desviados.columns]
    agg = {
        "count": ("pk_vuelo", "count"),
    }
    if "DivArrDelay" in desviados.columns:
        agg["div_arr_delay"] = ("DivArrDelay", "mean")
    if "DivDistance" in desviados.columns:
        agg["div_distance"] = ("DivDistance", "mean")

    grp = desviados.groupby(grp_cols).agg(**agg).reset_index()
    grp = grp.sort_values("count", ascending=False).head(20)

    rows = []
    for _, r in grp.iterrows():
        row = {
            "ruta": f"{r.get('OriginCode','?')}-{r.get('DestCode','?')}",
            "alt_airport": r.get("Div1Airport", "N/A"),
            "count": int(r["count"]),
            "div_arr_delay": round(_safe(float(r.get("div_arr_delay", 0))), 1),
            "div_distance": round(_safe(float(r.get("div_distance", 0))), 1),
        }
        rows.append(row)
    return rows


def _compute_page(filtros: dict, year: str = "", month: str = "", airline: str = "") -> dict:
    key = str(sorted(filtros.items()))
    entry = _page_cache.get(key)
    if entry and time.time() < entry["expires"]:
        return entry["data"]
    df = load_enriched_fact(filtros or None)
    data = {
        "causas_data": _causas_faa(df, year, month, airline),
        "tendencias": _tendencias_mensuales(df, year),
        "desvios": _desvios(df),
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
    causas_data: dict = {"labels": [], "values": [], "descriptions": [], "total_cancelados": 0, "total_vuelos": 0, "tasa": 0.0}
    tendencias: dict = {"meses": [], "cancelaciones": [], "total": [], "causas": {}}
    desvios: list[dict] = []

    try:
        filtros = {k: v for k, v in {"year": year, "month": month, "airline": airline}.items() if v}
        data = _compute_page(filtros, year, month, airline)
        causas_data = data["causas_data"]
        tendencias = data["tendencias"]
        desvios = data["desvios"]

    except FileNotFoundError:
        error = "Los datos no están disponibles. Ejecute el pipeline ELT primero."
    except Exception as exc:
        error = f"Error al cargar datos: {exc}"

    return render(request, "cancelaciones/causas.html", {
        "causas_data": causas_data,
        "tendencias": tendencias,
        "desvios": desvios,
        "error": error,
        "years": get_years(),
        "aerolinas": get_aerolinas(),
        "filtros": {"year": year, "month": month, "airline": airline},
    })


@router.get("/narrativa")
def narrativa_json(request: Request, year: str = "", month: str = "", airline: str = ""):
    _perm_ver(request)
    try:
        filtros = {k: v for k, v in {"year": year, "month": month, "airline": airline}.items() if v}
        data = _compute_page(filtros, year, month, airline)
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
