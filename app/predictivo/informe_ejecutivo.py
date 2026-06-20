"""Informe ejecutivo IA en PDF (CU-38). Usa WeasyPrint + Jinja2."""

import io
import math
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from minio import Minio as _Minio
from app.config import (
    MINIO_BUCKET_EXPORTS, MINIO_PUBLIC_ENDPOINT,
    MINIO_ACCESS_KEY, MINIO_SECRET_KEY,
)
from app.predictivo.proyeccion_riesgo import (
    _load_otp_series, _proyectar_otp, _heatmap_data,
    _generar_recomendaciones, _get_horizonte_max, _safe,
    _MESES, _DIAS,
)
from app.shared.clients.minio_client import get_client as _minio
from app.shared.deps import require_permission
from app.shared.utils import audit

router = APIRouter()
_perm_ver = require_permission("predictivo", "ver")

_TZ = timezone(timedelta(hours=-5))  # América/Guayaquil


def _svg_line(labels: list, values: list, width: int = 560, height: int = 180) -> str:
    """Genera SVG inline de línea OTP para el informe PDF."""
    if not values or not any(v is not None for v in values):
        return ""
    n = len(values)
    padl, padr, padt, padb = 44, 16, 16, 32
    w = width - padl - padr
    h = height - padt - padb

    y_min = max(0,   min(v for v in values if v is not None) - 5)
    y_max = min(100, max(v for v in values if v is not None) + 5)
    y_rng = y_max - y_min or 1

    def px(i: int, v: float) -> tuple[float, float]:
        x = padl + (i / max(n - 1, 1)) * w
        y = padt + (1 - (v - y_min) / y_rng) * h
        return x, y

    pts = [(i, v) for i, v in enumerate(values) if v is not None]
    path_d = " ".join(
        f"{'M' if j == 0 else 'L'}{px(i, v)[0]:.1f},{px(i, v)[1]:.1f}"
        for j, (i, v) in enumerate(pts)
    )

    # Y-axis labels (3 ticks)
    y_ticks = [y_min, (y_min + y_max) / 2, y_max]
    tick_svg = "".join(
        f'<text x="{padl - 4:.0f}" y="{padt + (1-(t-y_min)/y_rng)*h:.1f}" '
        f'font-size="9" fill="#64748b" text-anchor="end" dominant-baseline="middle">{t:.0f}%</text>'
        for t in y_ticks
    )

    # X-axis labels (show every other one to avoid crowding)
    step = max(1, n // 8)
    x_tick_svg = "".join(
        f'<text x="{px(i,values[i] or y_min)[0]:.1f}" y="{height - 6}" '
        f'font-size="8" fill="#64748b" text-anchor="middle">{labels[i]}</text>'
        for i in range(0, n, step) if i < len(labels)
    )

    circles = "".join(
        '<circle cx="{:.1f}" cy="{:.1f}" r="3" fill="#3b82f6"/>'.format(px(i, v)[0], px(i, v)[1])
        for i, v in pts
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f'<rect width="{width}" height="{height}" fill="#f8fafc" rx="6"/>'
        f'<line x1="{padl}" y1="{padt}" x2="{padl}" y2="{height-padb}" stroke="#e2e8f0" stroke-width="1"/>'
        f'<line x1="{padl}" y1="{height-padb}" x2="{width-padr}" y2="{height-padb}" stroke="#e2e8f0" stroke-width="1"/>'
        f'{tick_svg}{x_tick_svg}'
        f'<path d="{path_d}" fill="none" stroke="#3b82f6" stroke-width="2" stroke-linejoin="round"/>'
        + circles +
        '</svg>'
    )


def _svg_hmap_mini(matrix: list, rows: list, cols: list, metric: str, width=560, height=160) -> str:
    """Genera miniatura SVG del mapa de calor para el informe."""
    if not matrix:
        return ""
    n_rows, n_cols = len(rows), len(cols)
    cell_w = (width - 40) / n_cols
    cell_h = (height - 20) / n_rows

    def _color(val: float | None, m: str) -> str:
        if val is None:
            return "#f1f5f9"
        if m == "otp":
            if val >= 88: return "#10b981"
            if val >= 80: return "#6ee7b7"
            if val >= 70: return "#fbbf24"
            return "#f87171"
        elif m == "cancelacion":
            if val <= 2: return "#10b981"
            if val <= 5: return "#fbbf24"
            return "#f87171"
        else:
            if val <= 5: return "#10b981"
            if val <= 15: return "#fbbf24"
            return "#f87171"

    cells = []
    for ri, row in enumerate(rows):
        for ci, col in enumerate(cols):
            val = matrix[ri][ci] if ri < len(matrix) and ci < len(matrix[ri]) else None
            x   = 40 + ci * cell_w
            y   = ri * cell_h
            cells.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell_w:.1f}" height="{cell_h:.1f}" '
                f'fill="{_color(val, metric)}" rx="1" opacity="0.85"/>'
            )

    col_labels = "".join(
        f'<text x="{40 + ci * cell_w + cell_w/2:.1f}" y="{height - 4}" '
        f'font-size="7" fill="#64748b" text-anchor="middle">{c}</text>'
        for ci, c in enumerate(cols)
    )
    row_labels = "".join(
        f'<text x="38" y="{ri * cell_h + cell_h/2:.1f}" '
        f'font-size="7" fill="#64748b" text-anchor="end" dominant-baseline="middle">{r}</text>'
        for ri, r in enumerate(rows)
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f'<rect width="{width}" height="{height}" fill="#f8fafc" rx="6"/>'
        f'{"".join(cells)}{row_labels}{col_labels}'
        f'</svg>'
    )


def _html_informe(
    airline: str,
    year: str,
    proy: dict,
    heatmap: dict,
    recs: list,
    ts: str,
) -> str:
    """Genera el HTML completo del informe ejecutivo."""

    scope  = f"Aerolínea: {airline}" if airline else "Todas las aerolíneas"
    period = f"Año: {year}" if year else "Todo el período disponible"
    otp_avg = (
        f"{sum(proy.get('historico', [])) / len(proy.get('historico', [1])):.1f}%"
        if proy.get("historico") else "Sin datos"
    )
    n_meses = proy.get("n_meses", 0)
    adv_txt = (
        '<p style="color:#f59e0b;font-size:11px;margin:4px 0 0 0">'
        '⚠ Menos de 12 meses de datos — precisión de proyección reducida.</p>'
        if proy.get("advertencia") else ""
    )

    # SVGs
    hist_l   = proy.get("meses_hist", [])
    hist_v   = proy.get("historico",  [])
    proy_l   = proy.get("meses_proy", [])
    proy_v   = proy.get("proyeccion", [])
    all_l    = hist_l + proy_l
    all_v    = hist_v + proy_v
    svg_line = _svg_line(all_l, all_v) if all_v else ""
    svg_hmap = _svg_hmap_mini(heatmap.get("matrix", []), heatmap.get("rows", _DIAS),
                               heatmap.get("cols", _MESES), heatmap.get("metric", "otp"))

    # Recomendaciones HTML
    prio_color = {"alta": "#ef4444", "media": "#f59e0b", "baja": "#10b981"}
    recs_html  = "".join(
        f'<div style="padding:10px 0;border-bottom:1px solid #e2e8f0">'
        f'<span style="font-size:10px;font-weight:700;color:{prio_color.get(r["prioridad"],"#64748b")}'
        f';text-transform:uppercase;letter-spacing:.5px">{r["prioridad"]}</span> '
        f'<strong style="font-size:12px;color:#1e293b">{r["titulo"]}</strong>'
        f'<p style="font-size:11px;color:#475569;margin:4px 0 0 0">{r["descripcion"]}</p>'
        f'<p style="font-size:10px;color:#94a3b8;font-style:italic;margin:2px 0 0 0">{r.get("justificacion","")}</p>'
        f'</div>'
        for r in recs
    )

    # Proyección table
    proy_table = ""
    if proy_v and proy_l:
        rows_proy = "".join(
            f'<tr><td style="padding:4px 8px;font-size:11px;color:#475569">{l}</td>'
            f'<td style="padding:4px 8px;font-size:11px;color:#3b82f6;font-weight:700">{v}%</td>'
            f'<td style="padding:4px 8px;font-size:11px;color:#64748b">[{lo}% – {hi}%]</td></tr>'
            for l, v, lo, hi in zip(proy_l, proy_v,
                                     proy.get("ic_inf", []), proy.get("ic_sup", []))
        )
        proy_table = (
            f'<table style="width:100%;border-collapse:collapse;margin-top:8px">'
            f'<tr style="background:#f1f5f9">'
            f'<th style="padding:5px 8px;font-size:10px;color:#475569;text-align:left">Mes</th>'
            f'<th style="padding:5px 8px;font-size:10px;color:#475569;text-align:left">OTP proyectado</th>'
            f'<th style="padding:5px 8px;font-size:10px;color:#475569;text-align:left">Intervalo 95%</th>'
            f'</tr>{rows_proy}</table>'
        )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'Helvetica Neue',Arial,sans-serif; font-size:12px; color:#1e293b; background:#fff; }}
  .page {{ padding:32px 40px; max-width:800px; margin:0 auto; }}
  .header {{ border-bottom:3px solid #3b82f6; padding-bottom:16px; margin-bottom:24px; display:flex; justify-content:space-between; align-items:flex-start; }}
  .brand {{ font-size:20px; font-weight:800; color:#1e293b; letter-spacing:-.3px; }}
  .brand span {{ color:#3b82f6; }}
  .meta {{ font-size:10px; color:#94a3b8; text-align:right; line-height:1.6; }}
  h2 {{ font-size:14px; font-weight:700; color:#1e293b; border-left:3px solid #3b82f6; padding-left:10px; margin:20px 0 12px 0; }}
  .kpi-row {{ display:flex; gap:16px; margin-bottom:20px; }}
  .kpi {{ flex:1; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:12px 16px; }}
  .kpi-label {{ font-size:10px; font-weight:600; color:#64748b; text-transform:uppercase; letter-spacing:.5px; margin-bottom:6px; }}
  .kpi-val {{ font-size:20px; font-weight:700; color:#1e293b; }}
  .footer {{ margin-top:32px; border-top:1px solid #e2e8f0; padding-top:12px; font-size:9px; color:#94a3b8; display:flex; justify-content:space-between; }}
</style>
</head>
<body>
<div class="page">

  <div class="header">
    <div>
      <div class="brand">Aero<span>Track</span> Analytics</div>
      <div style="font-size:11px;color:#64748b;margin-top:2px">Informe Ejecutivo Predictivo IA</div>
    </div>
    <div class="meta">
      Generado: {ts}<br>
      {scope}<br>{period}
    </div>
  </div>

  <h2>1. Resumen Ejecutivo</h2>
  <div class="kpi-row">
    <div class="kpi"><div class="kpi-label">OTP Promedio Histórico</div><div class="kpi-val">{otp_avg}</div></div>
    <div class="kpi"><div class="kpi-label">Meses de Historial</div><div class="kpi-val">{n_meses}</div></div>
    <div class="kpi"><div class="kpi-label">Recomendaciones</div><div class="kpi-val">{len(recs)}</div></div>
    <div class="kpi"><div class="kpi-label">Alcance</div><div class="kpi-val" style="font-size:13px">{airline or "Red completa"}</div></div>
  </div>
  {adv_txt}

  <h2>2. Proyección de Riesgo OTP</h2>
  {"<p style='color:#94a3b8;font-size:11px'>" + proy.get('error','Sin datos suficientes para proyectar.') + "</p>" if not proy_v else ""}
  {svg_line}
  {proy_table}

  <h2>3. Mapa de Calor Estacional</h2>
  {svg_hmap}
  <p style="font-size:10px;color:#94a3b8;margin-top:6px">Métrica: {heatmap.get("metric","otp").upper()} · Filas: día de semana · Columnas: mes</p>

  <h2>4. Recomendaciones Priorizadas</h2>
  {recs_html if recs_html else "<p style='color:#94a3b8;font-size:11px'>Sin datos para generar recomendaciones.</p>"}

  <div class="footer">
    <span>AeroTrack Analytics — Módulo Predictivo IA</span>
    <span>Generado automáticamente · {ts}</span>
  </div>
</div>
</body>
</html>"""


@router.post("/informe")
async def generar_informe(request: Request):
    user = _perm_ver(request)
    form = await request.form()
    airline  = str(form.get("airline", ""))
    year     = str(form.get("year", ""))
    horizonte = int(form.get("horizonte", "6"))
    horizonte = max(1, min(horizonte, _get_horizonte_max()))

    try:
        from weasyprint import HTML as WP_HTML

        df_otp  = _load_otp_series(airline=airline, year=year)
        proy    = _proyectar_otp(df_otp, horizonte) if len(df_otp) >= 3 else {}
        heatmap = _heatmap_data(metric="otp", airline=airline)
        recs    = _generar_recomendaciones(df_otp, airline=airline)

        ts = datetime.now(_TZ).strftime("%Y-%m-%d %H:%M:%S")
        html_str = _html_informe(airline, year, proy, heatmap, recs, ts)

        pdf_bytes = WP_HTML(string=html_str).write_pdf()

        ts_file = datetime.now(_TZ).strftime("%Y%m%d_%H%M%S")
        obj_name = f"reportes/informe_ejecutivo_{ts_file}.pdf"

        client = _minio()
        bucket = MINIO_BUCKET_EXPORTS
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

        client.put_object(
            bucket, obj_name,
            io.BytesIO(pdf_bytes), len(pdf_bytes),
            content_type="application/pdf",
        )

        # Usar endpoint público para que la URL sea accesible desde el navegador
        sign_client = _Minio(
            MINIO_PUBLIC_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False,
        )
        url = sign_client.presigned_get_object(bucket, obj_name, expires=timedelta(hours=1))

        audit.registrar(
            user["sub"], user["email"], "exportar", "predictivo",
            recurso_tipo="informe_ejecutivo", recurso_id=obj_name,
        )

        return JSONResponse({"url": url})

    except Exception as exc:
        return JSONResponse({"error": f"Error al generar el informe: {exc}"}, status_code=500)
