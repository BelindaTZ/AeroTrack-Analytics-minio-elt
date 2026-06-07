"""Router de reportes — PDF, Excel, CSV, historial (CU-27, CU-28)."""

import io
from datetime import datetime, timedelta, timezone
from typing import Optional

_TZ = timezone(timedelta(hours=-5))  # America/Guayaquil — sin DST

import pandas as pd
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse

from app.dashboard.kpis import _calcular_kpis_agg, _get_umbrales
from app.reportes.generar_excel import generar_excel
from app.reportes.generar_pdf import generar_pdf, subir_pdf_minio, _weasyprint_available
from app.shared.analytics import (
    load_agg, load_enriched_fact,
    get_years, get_aerolinas, get_origins, get_dests,
)
from app.shared.deps import render, require_permission
from app.shared.utils import audit

router = APIRouter()
_perm_ver    = require_permission("reportes", "ver")
_perm_export = require_permission("reportes", "exportar")

_SECCIONES = [
    {"clave": "kpis",          "label": "KPIs operacionales"},
    {"clave": "otp_mensual",   "label": "Tendencia OTP mensual"},
    {"clave": "top_aerolineas","label": "Desempeño por aerolínea"},
    {"clave": "causas_retraso","label": "Causas de retraso"},
    {"clave": "peores_rutas",  "label": "Rutas problemáticas"},
    {"clave": "dia_semana",    "label": "OTP por día de semana"},
    {"clave": "cancelaciones", "label": "Cancelaciones FAA"},
    {"clave": "rutas",         "label": "Top rutas eficientes"},
]

_FAA_DESC = {"A": "Aerolínea (Carrier)", "B": "Meteorología (Weather)",
             "C": "Sistema Aéreo (NAS)", "D": "Seguridad (Security)"}

_FILTRO_KEYS = ["year", "quarter", "month", "dow", "airline", "origin", "dest",
                "cancel_code", "solo_cancelados"]


def _ensure_exports_bucket() -> None:
    try:
        from minio import Minio
        from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration
        from minio.commonconfig import ENABLED
        from app.config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET_EXPORTS

        client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY,
                       secret_key=MINIO_SECRET_KEY, secure=False)
        if not client.bucket_exists(MINIO_BUCKET_EXPORTS):
            client.make_bucket(MINIO_BUCKET_EXPORTS)
            config = LifecycleConfig([
                Rule(ENABLED, rule_id="expire-7d", expiration=Expiration(days=7))
            ])
            client.set_bucket_lifecycle(MINIO_BUCKET_EXPORTS, config)
    except Exception:
        pass


def _subir_export_minio(data: bytes, nombre: str, content_type: str) -> Optional[str]:
    """Sube cualquier export al bucket aerotrack-exports y retorna URL firmada (1 h)."""
    try:
        from minio import Minio
        from app.config import (MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY,
                                MINIO_BUCKET_EXPORTS, MINIO_PUBLIC_ENDPOINT)

        client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY,
                       secret_key=MINIO_SECRET_KEY, secure=False)
        if not client.bucket_exists(MINIO_BUCKET_EXPORTS):
            client.make_bucket(MINIO_BUCKET_EXPORTS)

        obj_name = f"reportes/{nombre}"
        client.put_object(MINIO_BUCKET_EXPORTS, obj_name, io.BytesIO(data),
                          length=len(data), content_type=content_type)
        sign_client = Minio(MINIO_PUBLIC_ENDPOINT, access_key=MINIO_ACCESS_KEY,
                            secret_key=MINIO_SECRET_KEY, secure=False)
        return sign_client.presigned_get_object(
            MINIO_BUCKET_EXPORTS, obj_name, expires=timedelta(hours=1)
        )
    except Exception:
        return None


def _extract_filtros(form) -> dict:
    raw = {k: form.get(k, "") for k in _FILTRO_KEYS}
    return {k: v for k, v in raw.items() if v}


def _datos_para_pdf(df) -> dict:
    """Extrae tablas de cancelaciones y rutas desde el fact enriquecido."""
    datos: dict = {}
    try:
        if "Cancelled" in df.columns and "CancellationCode" in df.columns:
            cancelados = df[df["Cancelled"] == 1]
            total_canc = max(len(cancelados), 1)
            grp = cancelados.groupby("CancellationCode").size().reset_index(name="count")
            datos["cancelaciones"] = [
                {
                    "code": str(r["CancellationCode"]),
                    "desc": _FAA_DESC.get(str(r["CancellationCode"]), "Otro"),
                    "count": int(r["count"]),
                    "pct": round(int(r["count"]) / total_canc * 100, 1),
                }
                for _, r in grp.sort_values("count", ascending=False).iterrows()
            ]
    except Exception:
        pass

    try:
        if "OriginCode" in df.columns and "DestCode" in df.columns:
            vop = df[df["Cancelled"] == 0] if "Cancelled" in df.columns else df
            if "ActualElapsedTime" in vop.columns and "CRSElapsedTime" in vop.columns:
                sub = vop[vop["CRSElapsedTime"] > 0].copy()
                sub["eficiencia"] = sub["ActualElapsedTime"] / sub["CRSElapsedTime"]
                grp_r = sub.groupby(["OriginCode", "DestCode"]).agg(
                    total=("pk_vuelo", "count"), ef_media=("eficiencia", "mean")
                ).reset_index()
                grp_r = grp_r[grp_r["total"] >= 5].nsmallest(10, "ef_media")
                datos["rutas"] = [
                    {
                        "ruta": f"{r['OriginCode']}-{r['DestCode']}",
                        "vuelos": int(r["total"]),
                        "eficiencia": round(float(r["ef_media"]), 3),
                    }
                    for _, r in grp_r.iterrows()
                ]
    except Exception:
        pass

    return datos


_MESES_SHORT  = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun",
                  "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
_DIAS_SHORT   = ["", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
_CAUSA_COLS   = [
    ("carrierdelay",      "Carrier"),
    ("weatherdelay",      "Weather"),
    ("nasdelay",          "NAS"),
    ("securitydelay",     "Security"),
    ("lateaircraftdelay", "LateAircraft"),
]


def _preparar_datos_pdf(filtros: dict) -> dict:
    """Recopila todos los datos necesarios para el PDF desde agg tables + fact."""
    datos: dict = {}

    # ── OTP mensual + top aerolíneas ────────────────────────────────────────
    try:
        df_otp = load_agg("agg_otp_aerolinea_mes", filtros)
        if not df_otp.empty and "month" in df_otp.columns:
            grp = df_otp.groupby("month").agg(
                total=("total_vuelos", "sum"),
                at=("vuelos_a_tiempo", "sum"),
            ).reset_index().sort_values("month")
            grp["otp"] = (grp["at"] / grp["total"].replace(0, pd.NA) * 100).fillna(0.0).round(1)
            datos["otp_mensual"] = [
                {
                    "mes": _MESES_SHORT[int(r["month"])] if 1 <= int(r["month"]) <= 12 else str(r["month"]),
                    "otp": float(r["otp"]),
                }
                for _, r in grp.iterrows()
            ]

        if not df_otp.empty and "carrier" in df_otp.columns:
            grp_al = df_otp.groupby("carrier").agg(
                total=("total_vuelos", "sum"),
                at=("vuelos_a_tiempo", "sum"),
                delay_w=("delay_avg", "mean"),
            ).reset_index()
            grp_al["otp"] = (grp_al["at"] / grp_al["total"].replace(0, pd.NA) * 100).fillna(0.0).round(1)
            grp_al = grp_al[grp_al["total"] >= 50].sort_values("total", ascending=False).head(20)
            datos["top_aerolineas"] = [
                {
                    "aerolinea": str(r["carrier"]),
                    "total":     int(r["total"]),
                    "otp":       float(r["otp"]),
                    "retraso":   f"{float(r.get('delay_w') or 0):.1f}",
                }
                for _, r in grp_al.iterrows()
            ]
    except Exception:
        pass

    # ── Causas de retraso ────────────────────────────────────────────────────
    try:
        df_causas = load_agg("agg_causas_retraso_mes", filtros)
        if not df_causas.empty:
            totales = []
            for col, label in _CAUSA_COLS:
                if col in df_causas.columns:
                    total = float(df_causas[col].fillna(0).sum())
                    if total > 0:
                        totales.append({"label": label, "minutos": total})
            total_all = sum(t["minutos"] for t in totales) or 1
            for t in totales:
                t["pct"] = round(t["minutos"] / total_all * 100, 1)
            datos["causas_retraso"] = sorted(totales, key=lambda x: -x["minutos"])
    except Exception:
        pass

    # ── Peores rutas ─────────────────────────────────────────────────────────
    try:
        df_rutas = load_agg("agg_rutas_eficiencia", filtros)
        if not df_rutas.empty and "otp_pct" in df_rutas.columns and "origin" in df_rutas.columns:
            agg_cols: dict = {"total_vuelos": ("total_vuelos", "sum")}
            if "vuelos_a_tiempo" in df_rutas.columns:
                agg_cols["vuelos_at"] = ("vuelos_a_tiempo", "sum")
            if "retraso_prom" in df_rutas.columns:
                agg_cols["retraso_prom"] = ("retraso_prom", "mean")
            grp_r = df_rutas.groupby(["origin", "dest"]).agg(**agg_cols).reset_index()
            if "vuelos_at" in grp_r.columns:
                grp_r["otp_pct"] = (
                    grp_r["vuelos_at"] / grp_r["total_vuelos"].replace(0, pd.NA) * 100
                ).fillna(0.0).round(1)
            else:
                grp_r["otp_pct"] = 0.0
            grp_r = grp_r[grp_r["total_vuelos"] >= 50].sort_values("otp_pct").head(15)
            datos["peores_rutas"] = [
                {
                    "ruta":    f"{r['origin']}-{r['dest']}",
                    "vuelos":  int(r["total_vuelos"]),
                    "otp":     float(r["otp_pct"]),
                    "retraso": float(r.get("retraso_prom") or 0),
                }
                for _, r in grp_r.iterrows()
            ]
    except Exception:
        pass

    # ── OTP por día de semana ────────────────────────────────────────────────
    try:
        df_dia = load_agg("agg_otp_dia_semana")
        if not df_dia.empty and "otp_pct" in df_dia.columns:
            datos["dia_semana"] = [
                {
                    "dia": _DIAS_SHORT[int(r["day_of_week"])] if 1 <= int(r["day_of_week"]) <= 7 else str(r["day_of_week"]),
                    "otp": float(r["otp_pct"]),
                }
                for _, r in df_dia.sort_values("day_of_week").iterrows()
            ]
    except Exception:
        pass

    # ── Cancelaciones + rutas eficientes (desde fact enriquecido) ────────────
    try:
        df_full = load_enriched_fact(filtros or None)
        datos.update(_datos_para_pdf(df_full))
    except Exception:
        pass

    return datos


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
def index(request: Request):
    user = _perm_ver(request)
    _ensure_exports_bucket()
    return render(request, "reportes/index.html", {
        "secciones":    _SECCIONES,
        "weasyprint_ok": _weasyprint_available(),
        "years":        get_years(),
        "aerolinas":    get_aerolinas(),
        "origins":      get_origins(),
        "dests":        get_dests(),
    })


@router.get("/preview")
def preview(
    request: Request,
    year: str = "", quarter: str = "", month: str = "", dow: str = "",
    airline: str = "", origin: str = "", dest: str = "",
    cancel_code: str = "", solo_cancelados: str = "",
):
    _perm_ver(request)
    filtros = {k: v for k, v in {
        "year": year, "quarter": quarter, "month": month, "dow": dow,
        "airline": airline, "origin": origin, "dest": dest,
        "cancel_code": cancel_code, "solo_cancelados": solo_cancelados,
    }.items() if v}
    try:
        df = load_enriched_fact(filtros or None)
        total = len(df)
        vop = df[df["Cancelled"] == 0] if "Cancelled" in df.columns else df
        cancelados = int(df["Cancelled"].sum()) if "Cancelled" in df.columns else 0
        otp = None
        if "ArrDel15" in vop.columns and len(vop) > 0:
            otp = round(float((vop["ArrDel15"] == 0).sum() / max(len(vop), 1) * 100), 1)
        retraso = None
        if "ArrDelayMinutes" in vop.columns and len(vop) > 0:
            v = vop["ArrDelayMinutes"].mean()
            retraso = round(float(v), 1) if v == v else None  # NaN guard
        aerolinas_n = int(df["Reporting_Airline"].nunique()) if "Reporting_Airline" in df.columns else 0
        rutas_n = 0
        if "OriginCode" in df.columns and "DestCode" in df.columns:
            rutas_n = int(df.groupby(["OriginCode", "DestCode"]).ngroups)
        return JSONResponse({
            "total": total,
            "otp": otp,
            "cancelados": cancelados,
            "cancel_pct": round(cancelados / max(total, 1) * 100, 1),
            "retraso": retraso,
            "aerolinas": aerolinas_n,
            "rutas": rutas_n,
        })
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get("/historial")
def historial(request: Request):
    _perm_ver(request)
    try:
        from minio import Minio
        from app.config import (MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY,
                                MINIO_BUCKET_EXPORTS, MINIO_PUBLIC_ENDPOINT)

        client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY,
                       secret_key=MINIO_SECRET_KEY, secure=False)
        if not client.bucket_exists(MINIO_BUCKET_EXPORTS):
            return JSONResponse({"items": []})

        objects = sorted(
            client.list_objects(MINIO_BUCKET_EXPORTS, prefix="reportes/", recursive=True),
            key=lambda o: o.last_modified,
            reverse=True,
        )[:15]

        sign_client = Minio(MINIO_PUBLIC_ENDPOINT, access_key=MINIO_ACCESS_KEY,
                            secret_key=MINIO_SECRET_KEY, secure=False)
        items = []
        for obj in objects:
            nombre = obj.object_name.split("/", 1)[-1]
            ext = nombre.rsplit(".", 1)[-1] if "." in nombre else "bin"
            try:
                url = sign_client.presigned_get_object(
                    MINIO_BUCKET_EXPORTS, obj.object_name, expires=timedelta(hours=1)
                )
            except Exception:
                url = ""
            items.append({
                "nombre": nombre,
                "url": url,
                "fecha": obj.last_modified.astimezone(_TZ).strftime("%d/%m/%Y %H:%M"),
                "tipo": ext,
                "tamanio_kb": round(obj.size / 1024, 1),
            })
        return JSONResponse({"items": items})
    except Exception as exc:
        return JSONResponse({"items": [], "error": str(exc)})


@router.get("/preview-charts")
def preview_charts(
    request: Request,
    year: str = "", quarter: str = "", month: str = "", dow: str = "",
    airline: str = "", origin: str = "", dest: str = "",
    cancel_code: str = "", solo_cancelados: str = "",
):
    """JSON con datos de charts para la previsualización web (Chart.js)."""
    _perm_ver(request)
    filtros = {k: v for k, v in {
        "year": year, "quarter": quarter, "month": month, "dow": dow,
        "airline": airline, "origin": origin, "dest": dest,
        "cancel_code": cancel_code, "solo_cancelados": solo_cancelados,
    }.items() if v}

    resp: dict = {}

    try:
        df_otp = load_agg("agg_otp_aerolinea_mes", filtros)
        if not df_otp.empty and "month" in df_otp.columns:
            grp = df_otp.groupby("month").agg(
                total=("total_vuelos", "sum"),
                at=("vuelos_a_tiempo", "sum"),
            ).reset_index().sort_values("month")
            grp["otp"] = (grp["at"] / grp["total"].replace(0, pd.NA) * 100).fillna(0.0).round(1)
            resp["otp_mensual"] = {
                "labels": [
                    _MESES_SHORT[int(r["month"])] if 1 <= int(r["month"]) <= 12 else str(r["month"])
                    for _, r in grp.iterrows()
                ],
                "values": [float(r["otp"]) for _, r in grp.iterrows()],
            }
    except Exception:
        pass

    try:
        df_causas = load_agg("agg_causas_retraso_mes", filtros)
        if not df_causas.empty:
            labels, values = [], []
            for col, label in _CAUSA_COLS:
                if col in df_causas.columns:
                    total = float(df_causas[col].fillna(0).sum())
                    if total > 0:
                        labels.append(label)
                        values.append(round(total, 1))
            resp["causas"] = {"labels": labels, "values": values}
    except Exception:
        pass

    try:
        df_rutas = load_agg("agg_rutas_eficiencia", filtros)
        if not df_rutas.empty and "origin" in df_rutas.columns:
            agg_cols: dict = {"total_vuelos": ("total_vuelos", "sum")}
            if "vuelos_a_tiempo" in df_rutas.columns:
                agg_cols["vuelos_at"] = ("vuelos_a_tiempo", "sum")
            grp_r = df_rutas.groupby(["origin", "dest"]).agg(**agg_cols).reset_index()
            if "vuelos_at" in grp_r.columns:
                grp_r["otp_pct"] = (
                    grp_r["vuelos_at"] / grp_r["total_vuelos"].replace(0, pd.NA) * 100
                ).fillna(0.0).round(1)
            else:
                grp_r["otp_pct"] = 0.0
            grp_r = grp_r[grp_r["total_vuelos"] >= 50].sort_values("otp_pct").head(10)
            resp["peores_rutas"] = {
                "labels": [f"{r['origin']}-{r['dest']}" for _, r in grp_r.iterrows()],
                "values": [float(r["otp_pct"]) for _, r in grp_r.iterrows()],
            }
    except Exception:
        pass

    return JSONResponse(resp)


@router.post("/excel")
async def generar_excel_endpoint(request: Request):
    user = _perm_export(request)
    form = await request.form()
    filtros = _extract_filtros(form)
    try:
        excel_bytes = generar_excel(filtros or None)
        nombre = f"aerotrack_reporte_{datetime.now(_TZ).strftime('%Y%m%d_%H%M')}.xlsx"
        audit.registrar(user["sub"], user["email"], "exportar", "reportes",
                        recurso_tipo="excel", recurso_id=nombre)
        # Guardar en MinIO para historial (best-effort)
        try:
            _subir_export_minio(
                excel_bytes, nombre,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception:
            pass
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
        )
    except Exception as exc:
        return RedirectResponse(f"/reportes?error={exc}", status_code=303)


@router.post("/csv")
async def generar_csv_endpoint(request: Request):
    user = _perm_export(request)
    form = await request.form()
    filtros = _extract_filtros(form)
    try:
        df = load_enriched_fact(filtros or None)
        cols_csv = [c for c in [
            "FlightDate", "Reporting_Airline", "OriginCode", "DestCode",
            "Cancelled", "CancellationCode", "Diverted",
            "ArrDel15", "DepDel15", "ArrDelayMinutes", "DepDelayMinutes",
            "ActualElapsedTime", "CRSElapsedTime", "Distance",
        ] if c in df.columns]
        csv_bytes = df[cols_csv].to_csv(index=False).encode("utf-8")
        nombre = f"aerotrack_datos_{datetime.now(_TZ).strftime('%Y%m%d_%H%M')}.csv"
        audit.registrar(user["sub"], user["email"], "exportar", "reportes",
                        recurso_tipo="csv", recurso_id=nombre)
        try:
            _subir_export_minio(csv_bytes, nombre, "text/csv")
        except Exception:
            pass
        return StreamingResponse(
            io.BytesIO(csv_bytes),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
        )
    except Exception as exc:
        return RedirectResponse(f"/reportes?error={exc}", status_code=303)


@router.post("/pdf")
async def generar_pdf_endpoint(request: Request):
    user = _perm_export(request)
    if not _weasyprint_available():
        return JSONResponse({"error": "WeasyPrint no está instalado en este servidor."}, status_code=501)

    form = await request.form()
    filtros  = _extract_filtros(form)
    secciones = list(form.getlist("secciones")) or [s["clave"] for s in _SECCIONES]

    periodo_parts = []
    if filtros.get("year"):    periodo_parts.append(str(filtros["year"]))
    if filtros.get("quarter"): periodo_parts.append(f"Q{filtros['quarter']}")
    if filtros.get("month"):   periodo_parts.append(f"Mes {filtros['month']}")
    if filtros.get("dow"):     periodo_parts.append(f"Día {filtros['dow']}")
    if filtros.get("airline"): periodo_parts.append(filtros["airline"])
    if filtros.get("origin"):  periodo_parts.append(f"Desde {filtros['origin']}")
    if filtros.get("dest"):    periodo_parts.append(f"Hacia {filtros['dest']}")
    periodo = " · ".join(periodo_parts) or "Todos los datos"

    try:
        df_otp = load_agg("agg_otp_aerolinea_mes", filtros)
        kpis = _calcular_kpis_agg(df_otp)
    except Exception as exc:
        return JSONResponse({"error": f"Error al cargar datos: {exc}"}, status_code=500)

    datos = _preparar_datos_pdf(filtros)

    pdf_bytes = generar_pdf(kpis, secciones, periodo, datos)
    if not pdf_bytes:
        return JSONResponse({"error": "Error generando el PDF."}, status_code=500)

    nombre = f"aerotrack_reporte_{datetime.now(_TZ).strftime('%Y%m%d_%H%M')}.pdf"
    url = subir_pdf_minio(pdf_bytes, nombre)

    audit.registrar(user["sub"], user["email"], "exportar", "reportes",
                    recurso_tipo="pdf", recurso_id=nombre)

    if url:
        return JSONResponse({"ok": True, "url": url, "nombre": nombre})
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
