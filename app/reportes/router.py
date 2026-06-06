"""Router de reportes — PDF y Excel (CU-27, CU-28)."""

import io
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse

from app.dashboard.kpis import _calcular_kpis, _get_umbrales
from app.reportes.generar_excel import generar_excel
from app.reportes.generar_pdf import generar_pdf, subir_pdf_minio, _weasyprint_available
from app.shared.analytics import load_enriched_fact, get_years, get_aerolinas
from app.shared.deps import render, require_permission
from app.shared.utils import audit

router = APIRouter()
_perm_ver = require_permission("reportes", "ver")
_perm_export = require_permission("reportes", "exportar")

_SECCIONES = [
    {"clave": "kpis",         "label": "KPIs generales"},
    {"clave": "top_aerolineas", "label": "Top aerolíneas"},
]


def _ensure_exports_bucket() -> None:
    """Crea el bucket aerotrack-exports con lifecycle 7 días si no existe."""
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
        pass  # No bloquear si falla


@router.get("", response_class=HTMLResponse)
def index(request: Request):
    user = _perm_ver(request)
    _ensure_exports_bucket()
    return render(request, "reportes/index.html", {
        "secciones": _SECCIONES,
        "weasyprint_ok": _weasyprint_available(),
        "years": get_years(),
        "aerolinas": get_aerolinas(),
    })


@router.post("/excel")
async def generar_excel_endpoint(request: Request):
    user = _perm_export(request)
    form = await request.form()
    year = form.get("year", "")
    month = form.get("month", "")
    airline = form.get("airline", "")

    filtros = {k: v for k, v in {"year": year, "month": month, "airline": airline}.items() if v}
    try:
        excel_bytes = generar_excel(filtros or None)
        nombre = f"aerotrack_reporte_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        audit.registrar(user["sub"], user["email"], "exportar", "reportes",
                        recurso_tipo="excel", recurso_id=nombre)
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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
    year = form.get("year", "")
    month = form.get("month", "")
    airline = form.get("airline", "")
    secciones = list(form.getlist("secciones")) or ["kpis", "top_aerolineas"]

    filtros = {k: v for k, v in {"year": year, "month": month, "airline": airline}.items() if v}
    periodo = " ".join(filter(None, [year, month, airline])) or "Todos los datos"

    try:
        df = load_enriched_fact(filtros or None)
        kpis = _calcular_kpis(df)
    except Exception as exc:
        return JSONResponse({"error": f"Error al cargar datos: {exc}"}, status_code=500)

    pdf_bytes = generar_pdf(kpis, secciones, periodo)
    if not pdf_bytes:
        return JSONResponse({"error": "Error generando el PDF."}, status_code=500)

    nombre = f"aerotrack_reporte_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    url = subir_pdf_minio(pdf_bytes, nombre)

    audit.registrar(user["sub"], user["email"], "exportar", "reportes",
                    recurso_tipo="pdf", recurso_id=nombre)

    if url:
        return JSONResponse({"ok": True, "url": url, "nombre": nombre})
    # Fallback: descarga directa
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
