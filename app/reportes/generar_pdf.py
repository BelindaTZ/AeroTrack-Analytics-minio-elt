"""Generación de reportes PDF con WeasyPrint (CU-27)."""

import io
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

_TZ = timezone(timedelta(hours=-5))  # America/Guayaquil — sin DST

log = logging.getLogger(__name__)

_MESES   = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun",
            "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
_DIAS    = ["", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
_FAA_DESC = {"A": "Aerolínea", "B": "Meteorología", "C": "Sist. Aéreo", "D": "Seguridad"}


def _weasyprint_available() -> bool:
    try:
        import weasyprint  # noqa: F401
        return True
    except (ImportError, OSError):
        return False


# ── SVG chart helpers ────────────────────────────────────────────────────────

def _otp_color(v: float) -> str:
    return "#16a34a" if v >= 80 else "#d97706" if v >= 70 else "#dc2626"


def _svg_line_otp(labels: list, values: list, width: int = 500, height: int = 170) -> str:
    """SVG line chart para tendencia OTP mensual (eje Y fijo en 50–100%)."""
    if not labels or not values or len(labels) < 2:
        return ""
    n = len(labels)
    PL, PR, PT, PB = 42, 18, 14, 36
    W, H = width - PL - PR, height - PT - PB
    y_min, y_max = 50.0, 100.0

    def cx(i: int) -> float:
        return PL + i * W / max(n - 1, 1)

    def cy(v: float) -> float:
        return PT + H - (v - y_min) / (y_max - y_min) * H

    parts: list[str] = []

    # grid lines
    for gv in [60, 70, 80, 90, 100]:
        gy = cy(gv)
        parts.append(
            f'<line x1="{PL}" y1="{gy:.1f}" x2="{width - PR}" y2="{gy:.1f}" '
            f'stroke="#e2e8f0" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{PL - 4}" y="{gy + 3:.1f}" text-anchor="end" '
            f'font-size="8" fill="#94a3b8">{gv}%</text>'
        )

    # umbral 80% en ámbar punteado
    gy80 = cy(80)
    parts.append(
        f'<line x1="{PL}" y1="{gy80:.1f}" x2="{width - PR}" y2="{gy80:.1f}" '
        f'stroke="#d97706" stroke-width="1.2" stroke-dasharray="4,3"/>'
    )

    # área rellena bajo la línea
    path_pts = " ".join(f"{cx(i):.1f},{cy(v):.1f}" for i, v in enumerate(values))
    bot = cy(y_min)
    parts.append(
        f'<polygon points="{cx(0):.1f},{bot} {path_pts} {cx(n - 1):.1f},{bot}" '
        f'fill="rgba(27,58,107,0.09)"/>'
    )
    parts.append(
        f'<polyline points="{path_pts}" fill="none" stroke="#1B3A6B" '
        f'stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>'
    )

    # puntos + etiquetas eje X
    step = max(1, n // 10)
    for i, v in enumerate(values):
        parts.append(
            f'<circle cx="{cx(i):.1f}" cy="{cy(v):.1f}" r="3.5" '
            f'fill="{_otp_color(v)}" stroke="white" stroke-width="1.5"/>'
        )
        if i % step == 0 or i == n - 1:
            parts.append(
                f'<text x="{cx(i):.1f}" y="{height - 5}" text-anchor="middle" '
                f'font-size="8" fill="#64748b">{labels[i]}</text>'
            )

    return (
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'{"".join(parts)}</svg>'
    )


def _svg_hbar(labels: list, values: list, unit: str = "", width: int = 500) -> str:
    """SVG horizontal bar chart para distribución de causas."""
    if not labels or not values:
        return ""
    bar_h, gap = 22, 7
    PL, PR, PT, PB = 130, 60, 8, 8
    n = len(labels)
    height = PT + n * (bar_h + gap) + PB
    max_v = max(values) if max(values) > 0 else 1
    bar_w = width - PL - PR
    COLORS = ["#1B3A6B", "#2563eb", "#0ea5e9", "#06b6d4", "#10b981", "#d97706"]

    parts: list[str] = []
    for i, (lbl, val) in enumerate(zip(labels, values)):
        y = PT + i * (bar_h + gap)
        bw = max(int(val / max_v * bar_w), 3)
        color = COLORS[i % len(COLORS)]
        parts.append(
            f'<text x="{PL - 6}" y="{y + bar_h / 2 + 3:.0f}" text-anchor="end" '
            f'font-size="9.5" fill="#334155">{lbl}</text>'
        )
        parts.append(f'<rect x="{PL}" y="{y}" width="{bw}" height="{bar_h}" fill="{color}" rx="3"/>')
        val_str = f"{val:,.0f}{unit}"
        parts.append(
            f'<text x="{PL + bw + 5}" y="{y + bar_h / 2 + 3:.0f}" '
            f'font-size="9" fill="#64748b">{val_str}</text>'
        )

    return (
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'{"".join(parts)}</svg>'
    )


def _svg_vbar_otp(labels: list, values: list, width: int = 500, height: int = 160) -> str:
    """SVG vertical bar chart para OTP por aerolínea o día de semana."""
    if not labels or not values:
        return ""
    n = len(labels)
    PL, PR, PT, PB = 38, 12, 14, 36
    W, H = width - PL - PR, height - PT - PB
    bar_w = max(W // n - 5, 8)

    def cx(i: int) -> float:
        return PL + (i + 0.5) * W / n

    def cy(v: float) -> float:
        return PT + H - (v / 100.0 * H)

    parts: list[str] = []
    for gv in [60, 70, 80, 90, 100]:
        gy = cy(gv)
        parts.append(
            f'<line x1="{PL}" y1="{gy:.1f}" x2="{width - PR}" y2="{gy:.1f}" '
            f'stroke="#e2e8f0" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{PL - 3}" y="{gy + 3:.1f}" text-anchor="end" '
            f'font-size="7.5" fill="#94a3b8">{gv}%</text>'
        )

    gy80 = cy(80)
    parts.append(
        f'<line x1="{PL}" y1="{gy80:.1f}" x2="{width - PR}" y2="{gy80:.1f}" '
        f'stroke="#d97706" stroke-width="1.2" stroke-dasharray="4,3"/>'
    )

    for i, (lbl, v) in enumerate(zip(labels, values)):
        bh = max(v / 100.0 * H, 2)
        by = PT + H - bh
        bx = cx(i) - bar_w / 2
        parts.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w}" '
            f'height="{bh:.1f}" fill="{_otp_color(v)}" rx="2"/>'
        )
        parts.append(
            f'<text x="{cx(i):.1f}" y="{height - 5}" text-anchor="middle" '
            f'font-size="8" fill="#64748b">{lbl}</text>'
        )
        if bh > 14:
            parts.append(
                f'<text x="{cx(i):.1f}" y="{by - 3:.1f}" text-anchor="middle" '
                f'font-size="7.5" fill="#64748b">{v:.1f}%</text>'
            )

    return (
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'{"".join(parts)}</svg>'
    )


# ── HTML report builder ──────────────────────────────────────────────────────

def _html_reporte(kpis: dict, secciones: list[str], periodo: str, datos: dict | None = None) -> str:
    datos = datos or {}
    now = datetime.now(_TZ).strftime("%d/%m/%Y %H:%M")
    html_sec = ""

    # ── KPIs Operacionales ──────────────────────────────────────────────────
    if "kpis" in secciones:
        otp_v    = kpis.get("otp_global", 0) * 100
        canc_v   = kpis.get("tasa_cancelacion", 0) * 100
        otp_col  = "#16a34a" if otp_v >= 80 else "#d97706" if otp_v >= 70 else "#dc2626"
        canc_col = "#dc2626" if canc_v > 5 else "#d97706" if canc_v > 2 else "#16a34a"
        html_sec += f"""
        <section class="seccion">
          <h2>KPIs Operacionales</h2>
          <div class="kpi-grid">
            <div class="kpi-card">
              <div class="kpi-label">Total Vuelos</div>
              <div class="kpi-val">{kpis.get('total_vuelos', 0):,}</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-label">OTP Global</div>
              <div class="kpi-val" style="color:{otp_col}">{otp_v:.1f}%</div>
              <div class="kpi-sub">Umbral operacional 80%</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-label">Tasa Cancelación</div>
              <div class="kpi-val" style="color:{canc_col}">{canc_v:.1f}%</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-label">Retraso Promedio</div>
              <div class="kpi-val">{kpis.get('retraso_promedio', 0):.1f} min</div>
            </div>
          </div>
        </section>"""

    # ── Tendencia OTP Mensual ───────────────────────────────────────────────
    if "otp_mensual" in secciones and datos.get("otp_mensual"):
        trend  = datos["otp_mensual"]
        labels = [t["mes"] for t in trend]
        values = [t["otp"] for t in trend]
        svg    = _svg_line_otp(labels, values)
        if svg:
            avg_otp = round(sum(values) / len(values), 1) if values else 0
            best    = max(trend, key=lambda t: t["otp"])
            worst   = min(trend, key=lambda t: t["otp"])
            html_sec += f"""
        <section class="seccion">
          <h2>Tendencia OTP Mensual</h2>
          <div style="margin-bottom:8px">{svg}</div>
          <div class="legend-row">
            <span class="legend-item"><span class="leg-dot" style="background:#d97706"></span>Umbral 80%</span>
            <span class="legend-item">Promedio: <strong>{avg_otp}%</strong></span>
            <span class="legend-item">Mejor: <strong>{best['mes']} ({best['otp']:.1f}%)</strong></span>
            <span class="legend-item">Peor: <strong>{worst['mes']} ({worst['otp']:.1f}%)</strong></span>
          </div>
        </section>"""

    # ── Desempeño por Aerolínea ─────────────────────────────────────────────
    if "top_aerolineas" in secciones:
        aerolineas = datos.get("top_aerolineas") or []
        if not aerolineas and kpis.get("top3_aerolineas"):
            aerolineas = [
                {"aerolinea": al["aerolinea"], "total": al["total"],
                 "otp": round(al["otp"] * 100, 1), "retraso": "—"}
                for al in kpis["top3_aerolineas"]
            ]
        if aerolineas:
            labels_al = [al["aerolinea"] for al in aerolineas[:15]]
            values_al = [al["otp"] for al in aerolineas[:15]]
            svg_al    = _svg_vbar_otp(labels_al, values_al)
            rows_al   = "".join(
                f"<tr><td class='center'>{i + 1}</td><td>{al['aerolinea']}</td>"
                f"<td class='right'>{al['total']:,}</td>"
                f"<td class='center' style='color:{_otp_color(al['otp'])};font-weight:700'>"
                f"{al['otp']:.1f}%</td>"
                f"<td class='right'>{al.get('retraso', '—')}</td></tr>"
                for i, al in enumerate(aerolineas)
            )
            html_sec += f"""
        <section class="seccion">
          <h2>Desempeño por Aerolínea</h2>
          {svg_al}
          <table style="margin-top:12px">
            <thead><tr><th>#</th><th>Aerolínea</th><th class="right">Vuelos op.</th>
            <th>OTP</th><th class="right">Retraso prom. (min)</th></tr></thead>
            <tbody>{rows_al}</tbody>
          </table>
        </section>"""

    # ── Causas de Retraso ───────────────────────────────────────────────────
    if "causas_retraso" in secciones and datos.get("causas_retraso"):
        causas    = datos["causas_retraso"]
        labels_c  = [c["label"] for c in causas]
        values_c  = [c["minutos"] for c in causas]
        svg_c     = _svg_hbar(labels_c, values_c, " min")
        rows_caus = "".join(
            f"<tr><td>{c['label']}</td><td class='right'>{c['minutos']:,.0f}</td>"
            f"<td class='center'>{c['pct']:.1f}%</td></tr>"
            for c in causas
        )
        html_sec += f"""
        <section class="seccion">
          <h2>Distribución de Causas de Retraso (minutos totales)</h2>
          <div style="margin-bottom:10px">{svg_c}</div>
          <table>
            <thead><tr><th>Causa</th><th class="right">Minutos totales</th><th>% del total</th></tr></thead>
            <tbody>{rows_caus}</tbody>
          </table>
          <p class="nota">Carrier=problema aerolínea · Weather=clima · NAS=sistema aéreo nacional ·
          Security=seguridad · LateAircraft=avión tardío anterior</p>
        </section>"""

    # ── Rutas con Mayor Problemática ────────────────────────────────────────
    if "peores_rutas" in secciones and datos.get("peores_rutas"):
        peores    = datos["peores_rutas"]
        labels_pr = [r["ruta"] for r in peores[:12]]
        values_pr = [r["otp"] for r in peores[:12]]
        svg_pr    = _svg_vbar_otp(labels_pr, values_pr)
        rows_pr   = "".join(
            f"<tr><td><strong>{r['ruta']}</strong></td>"
            f"<td class='right'>{r['vuelos']:,}</td>"
            f"<td class='center' style='color:{_otp_color(r['otp'])};font-weight:700'>{r['otp']:.1f}%</td>"
            f"<td class='right'>{r['retraso']:.1f} min</td></tr>"
            for r in peores
        )
        html_sec += f"""
        <section class="seccion">
          <h2>Rutas con Mayor Problemática Operacional (menor OTP)</h2>
          {svg_pr}
          <table style="margin-top:12px">
            <thead><tr><th>Ruta</th><th class="right">Vuelos</th>
            <th>OTP</th><th class="right">Retraso prom.</th></tr></thead>
            <tbody>{rows_pr}</tbody>
          </table>
        </section>"""

    # ── OTP por Día de Semana ───────────────────────────────────────────────
    if "dia_semana" in secciones and datos.get("dia_semana"):
        dias_data = datos["dia_semana"]
        labels_d  = [d["dia"] for d in dias_data]
        values_d  = [d["otp"] for d in dias_data]
        svg_d     = _svg_vbar_otp(labels_d, values_d)
        rows_d    = "".join(
            f"<tr><td>{d['dia']}</td>"
            f"<td class='center' style='color:{_otp_color(d['otp'])};font-weight:700'>{d['otp']:.1f}%</td></tr>"
            for d in dias_data
        )
        html_sec += f"""
        <section class="seccion">
          <h2>OTP por Día de Semana</h2>
          {svg_d}
          <table style="margin-top:12px;width:280px">
            <thead><tr><th>Día</th><th>OTP</th></tr></thead>
            <tbody>{rows_d}</tbody>
          </table>
        </section>"""

    # ── Cancelaciones FAA ───────────────────────────────────────────────────
    if "cancelaciones" in secciones and datos.get("cancelaciones"):
        rows_canc = "".join(
            f"<tr><td class='center'><strong>{r['code']}</strong></td><td>{r['desc']}</td>"
            f"<td class='right'>{r['count']:,}</td><td class='center'>{r['pct']:.1f}%</td></tr>"
            for r in datos["cancelaciones"]
        )
        html_sec += f"""
        <section class="seccion">
          <h2>Cancelaciones por Causa FAA</h2>
          <table>
            <thead><tr><th>Código</th><th>Causa</th><th class="right">Total</th><th>% del total</th></tr></thead>
            <tbody>{rows_canc}</tbody>
          </table>
          <p class="nota">A=Aerolínea · B=Meteorología · C=Sistema Aéreo Nacional · D=Seguridad</p>
        </section>"""

    # ── Top Rutas Eficientes ────────────────────────────────────────────────
    if "rutas" in secciones and datos.get("rutas"):
        rows_rut = "".join(
            f"<tr><td class='center'>{i + 1}</td><td><strong>{r['ruta']}</strong></td>"
            f"<td class='right'>{r['vuelos']:,}</td>"
            f"<td class='center' style='color:{'#16a34a' if r['eficiencia'] <= 1.05 else '#d97706' if r['eficiencia'] <= 1.15 else '#dc2626'}'>"
            f"{r['eficiencia']:.3f}</td></tr>"
            for i, r in enumerate(datos["rutas"])
        )
        html_sec += f"""
        <section class="seccion">
          <h2>Top 10 Rutas más Eficientes</h2>
          <table>
            <thead><tr><th>#</th><th>Ruta</th><th class="right">Vuelos</th>
            <th>Índice eficiencia</th></tr></thead>
            <tbody>{rows_rut}</tbody>
          </table>
          <p class="nota">Índice = Tiempo real / Tiempo programado.
          Verde ≤1.05 · Ámbar ≤1.15 · Rojo &gt;1.15 (menos eficiente de lo planificado)</p>
        </section>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:Arial,Helvetica,sans-serif; font-size:10.5pt; color:#1e293b; background:#fff; }}
  .portada {{ padding:42px 48px; background:linear-gradient(135deg,#0f1117 0%,#1B3A6B 100%); color:white; }}
  .portada h1 {{ font-size:24pt; font-weight:700; margin-bottom:4px; }}
  .portada .sub {{ font-size:12pt; opacity:.75; }}
  .portada .meta {{ font-size:9pt; opacity:.5; margin-top:12px; }}
  .contenido {{ padding:22px 44px; }}
  .seccion {{ margin-bottom:26px; page-break-inside:avoid; }}
  h2 {{ font-size:12pt; font-weight:700; color:#1B3A6B;
        border-bottom:2.5px solid #1B3A6B; padding-bottom:5px; margin-bottom:12px; }}
  .kpi-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }}
  .kpi-card {{ background:#f1f5f9; border-radius:7px; padding:12px 14px; text-align:center;
               border-left:3px solid #1B3A6B; }}
  .kpi-label {{ font-size:7.5pt; font-weight:700; color:#64748b; text-transform:uppercase;
                letter-spacing:.4px; margin-bottom:5px; }}
  .kpi-val {{ font-size:17pt; font-weight:700; color:#1e293b; line-height:1.1; }}
  .kpi-sub {{ font-size:7pt; color:#94a3b8; margin-top:3px; }}
  table {{ width:100%; border-collapse:collapse; margin-top:4px; font-size:9.5pt; }}
  th {{ background:#1B3A6B; color:white; padding:6px 9px; text-align:left; font-size:8.5pt; }}
  th.right {{ text-align:right; }}
  td {{ padding:5px 9px; border-bottom:1px solid #e2e8f0; }}
  td.center {{ text-align:center; }}
  td.right {{ text-align:right; }}
  td.otp-cell {{ color:#16a34a; font-weight:700; text-align:center; }}
  tr:nth-child(even) td {{ background:#f8fafc; }}
  .nota {{ font-size:7.5pt; color:#94a3b8; margin-top:6px; font-style:italic; }}
  .legend-row {{ display:flex; gap:18px; flex-wrap:wrap; font-size:8.5pt; color:#64748b; margin-top:4px; }}
  .legend-item {{ display:flex; align-items:center; gap:4px; }}
  .leg-dot {{ width:10px; height:10px; border-radius:50%; display:inline-block; }}
  .footer {{ position:fixed; bottom:12px; right:40px; font-size:7.5pt; color:#94a3b8; }}
  @page {{ margin:14mm 10mm; }}
</style>
</head>
<body>
  <div class="portada">
    <h1>AeroTrack Analytics</h1>
    <div class="sub">Reporte de Análisis Operacional</div>
    <div class="meta">Período: {periodo} &nbsp;·&nbsp; Generado: {now}</div>
  </div>
  <div class="contenido">
    {html_sec}
  </div>
  <div class="footer">AeroTrack Analytics &nbsp;·&nbsp; {now}</div>
</body>
</html>"""


def generar_pdf(
    kpis: dict,
    secciones: list[str],
    periodo: str,
    datos: dict | None = None,
) -> Optional[bytes]:
    """Genera PDF usando WeasyPrint. Retorna bytes o None si no disponible."""
    if not _weasyprint_available():
        return None
    try:
        from weasyprint import HTML as WP_HTML
        html = _html_reporte(kpis, secciones, periodo, datos)
        return WP_HTML(string=html).write_pdf()
    except Exception as exc:
        log.error("generar_pdf error: %s", exc)
        return None


def subir_pdf_minio(pdf_bytes: bytes, nombre: str) -> Optional[str]:
    """Sube el PDF a MinIO aerotrack-exports y retorna URL firmada (1 h)."""
    try:
        from minio import Minio
        from app.config import (MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY,
                                MINIO_BUCKET_EXPORTS, MINIO_PUBLIC_ENDPOINT)

        client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY,
                       secret_key=MINIO_SECRET_KEY, secure=False)
        if not client.bucket_exists(MINIO_BUCKET_EXPORTS):
            client.make_bucket(MINIO_BUCKET_EXPORTS)

        obj_name = f"reportes/{nombre}"
        client.put_object(
            MINIO_BUCKET_EXPORTS, obj_name, io.BytesIO(pdf_bytes),
            length=len(pdf_bytes), content_type="application/pdf",
        )
        sign_client = Minio(MINIO_PUBLIC_ENDPOINT, access_key=MINIO_ACCESS_KEY,
                            secret_key=MINIO_SECRET_KEY, secure=False)
        return sign_client.presigned_get_object(
            MINIO_BUCKET_EXPORTS, obj_name, expires=timedelta(hours=1)
        )
    except Exception as exc:
        log.error("subir_pdf_minio error: %s", exc)
        return None
