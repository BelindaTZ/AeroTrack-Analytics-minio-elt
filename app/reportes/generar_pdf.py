"""Generación de reportes PDF con WeasyPrint (CU-27)."""

import io
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

log = logging.getLogger(__name__)


def _weasyprint_available() -> bool:
    """Comprueba en tiempo de ejecución si WeasyPrint está disponible."""
    try:
        import weasyprint  # noqa: F401
        return True
    except (ImportError, OSError):
        return False


# Propiedad pública que el router consulta
_WEASYPRINT_OK = _weasyprint_available()


def _html_reporte(kpis: dict, secciones: list[str], periodo: str) -> str:
    """Genera el HTML del reporte para WeasyPrint."""
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    secciones_html = ""

    if "kpis" in secciones:
        secciones_html += f"""
        <section class="seccion">
          <h2>KPIs Generales</h2>
          <div class="kpi-grid">
            <div class="kpi-card">
              <div class="kpi-label">Total Vuelos</div>
              <div class="kpi-val">{kpis.get('total_vuelos', 0):,}</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-label">OTP Global</div>
              <div class="kpi-val">{kpis.get('otp_global', 0)*100:.1f}%</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-label">Tasa Cancelación</div>
              <div class="kpi-val">{kpis.get('tasa_cancelacion', 0)*100:.1f}%</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-label">Retraso Promedio</div>
              <div class="kpi-val">{kpis.get('retraso_promedio', 0):.1f} min</div>
            </div>
          </div>
        </section>
        """

    if "top_aerolineas" in secciones and kpis.get("top3_aerolineas"):
        rows_html = "".join(
            f"<tr><td>{i+1}</td><td>{al['aerolinea']}</td><td>{al['total']:,}</td><td>{al['otp']*100:.1f}%</td></tr>"
            for i, al in enumerate(kpis["top3_aerolineas"])
        )
        secciones_html += f"""
        <section class="seccion">
          <h2>Top 3 Aerolíneas</h2>
          <table><thead><tr><th>#</th><th>Aerolínea</th><th>Vuelos</th><th>OTP</th></tr></thead>
          <tbody>{rows_html}</tbody></table>
        </section>
        """

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Inter, sans-serif; font-size: 11pt; color: #1e293b; background: #fff; }}
  .portada {{ padding: 48px; background: linear-gradient(135deg, #0f1117 0%, #1B3A6B 100%); color: white; min-height: 200px; }}
  .portada h1 {{ font-size: 26pt; font-weight: 700; margin-bottom: 8px; }}
  .portada .sub {{ font-size: 12pt; opacity: .7; }}
  .portada .meta {{ font-size: 10pt; opacity: .5; margin-top: 16px; }}
  .contenido {{ padding: 32px 48px; }}
  .seccion {{ margin-bottom: 32px; page-break-inside: avoid; }}
  h2 {{ font-size: 14pt; font-weight: 700; color: #1B3A6B; border-bottom: 2px solid #1B3A6B; padding-bottom: 6px; margin-bottom: 16px; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}
  .kpi-card {{ background: #f1f5f9; border-radius: 8px; padding: 14px; text-align: center; }}
  .kpi-label {{ font-size: 9pt; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 6px; }}
  .kpi-val {{ font-size: 18pt; font-weight: 700; color: #1e293b; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #1B3A6B; color: white; padding: 8px 12px; font-size: 10pt; text-align: left; }}
  td {{ padding: 7px 12px; border-bottom: 1px solid #e2e8f0; font-size: 10pt; }}
  tr:nth-child(even) td {{ background: #f8fafc; }}
  .footer {{ position: fixed; bottom: 16px; right: 48px; font-size: 9pt; color: #94a3b8; }}
</style>
</head>
<body>
  <div class="portada">
    <h1>AeroTrack Analytics</h1>
    <div class="sub">Reporte de Análisis Operacional</div>
    <div class="meta">Período: {periodo} · Generado: {now}</div>
  </div>
  <div class="contenido">
    {secciones_html}
  </div>
  <div class="footer">AeroTrack Analytics · Generado el {now}</div>
</body>
</html>"""


def generar_pdf(kpis: dict, secciones: list[str], periodo: str) -> Optional[bytes]:
    """Genera PDF usando WeasyPrint. Retorna bytes o None si no disponible."""
    if not _weasyprint_available():
        return None
    try:
        from weasyprint import HTML as WP_HTML
        html = _html_reporte(kpis, secciones, periodo)
        return WP_HTML(string=html).write_pdf()
    except Exception as exc:
        log.error("generar_pdf error: %s", exc)
        return None


def subir_pdf_minio(pdf_bytes: bytes, nombre: str) -> Optional[str]:
    """Sube el PDF a MinIO aerotrack-exports y retorna URL firmada con expiración 1h."""
    try:
        import io as _io
        from minio import Minio
        from app.config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, \
                               MINIO_BUCKET_EXPORTS, MINIO_PUBLIC_ENDPOINT

        # Cliente interno para operaciones I/O (upload, bucket check)
        client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY,
                       secret_key=MINIO_SECRET_KEY, secure=False)

        if not client.bucket_exists(MINIO_BUCKET_EXPORTS):
            client.make_bucket(MINIO_BUCKET_EXPORTS)

        obj_name = f"reportes/{nombre}"
        buf = _io.BytesIO(pdf_bytes)
        client.put_object(
            MINIO_BUCKET_EXPORTS, obj_name, buf,
            length=len(pdf_bytes), content_type="application/pdf"
        )

        # Cliente público para presigning: presigned_get_object() es puramente local
        # (no hace red), calcula la firma HMAC usando el hostname del cliente.
        # Si usamos el endpoint interno (minio:9000), la firma queda atada a ese host
        # y el browser recibe SignatureDoesNotMatch al acceder por localhost:9000.
        # Con el cliente público la firma se calcula con localhost:9000 y coincide.
        sign_client = Minio(MINIO_PUBLIC_ENDPOINT, access_key=MINIO_ACCESS_KEY,
                            secret_key=MINIO_SECRET_KEY, secure=False)
        url = sign_client.presigned_get_object(
            MINIO_BUCKET_EXPORTS, obj_name,
            expires=timedelta(hours=1)
        )
        return url
    except Exception as exc:
        log.error("subir_pdf_minio error: %s", exc)
        return None
