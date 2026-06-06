"""Generación de reportes Excel con openpyxl (CU-28)."""

import io

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from app.shared.analytics import load_enriched_fact


def _estilo_header(ws, fila: int, columnas: list[str]) -> None:
    fill = PatternFill("solid", fgColor="1B3A6B")
    font = Font(bold=True, color="FFFFFF", size=10)
    for i, col in enumerate(columnas, 1):
        cell = ws.cell(row=fila, column=i, value=col)
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="center")


def _autofit(ws) -> None:
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            try:
                val = str(cell.value or "")
                max_len = max(max_len, len(val))
            except Exception:
                pass
        ws.column_dimensions[col_letter].width = min(max_len + 4, 40)


def generar_excel(filtros: dict | None = None) -> bytes:
    """
    Genera un archivo .xlsx con hojas separadas por módulo analítico.
    Retorna el contenido como bytes.
    """
    df = load_enriched_fact(filtros)

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Eliminar hoja por defecto

    # ── Hoja 1: Puntualidad ──
    ws_otp = wb.create_sheet("Puntualidad OTP")
    if "Reporting_Airline" in df.columns and "ArrDel15" in df.columns:
        vuelos_op = df[df["Cancelled"] == 0] if "Cancelled" in df.columns else df
        grp = (
            vuelos_op.groupby("Reporting_Airline")
            .agg(
                total=("pk_vuelo", "count"),
                otp_sum=("ArrDel15", lambda x: (x == 0).sum()),
                retraso_prom=("ArrDelayMinutes", "mean") if "ArrDelayMinutes" in vuelos_op.columns else ("pk_vuelo", lambda x: 0),
            )
            .reset_index()
        )
        grp["otp_pct"] = (grp["otp_sum"] / grp["total"] * 100).round(2)
        headers = ["Aerolínea", "Total vuelos", "OTP (%)", "Retraso prom. (min)"]
        _estilo_header(ws_otp, 1, headers)
        for _, r in grp.iterrows():
            ws_otp.append([
                r["Reporting_Airline"],
                int(r["total"]),
                round(float(r["otp_pct"]), 2),
                round(float(r.get("retraso_prom", 0)), 2),
            ])
        _autofit(ws_otp)

    # ── Hoja 2: Rutas ──
    ws_rutas = wb.create_sheet("Rutas Eficiencia")
    if "OriginCode" in df.columns and "DestCode" in df.columns:
        vuelos_op = df[df["Cancelled"] == 0] if "Cancelled" in df.columns else df
        if "ActualElapsedTime" in vuelos_op.columns and "CRSElapsedTime" in vuelos_op.columns:
            sub = vuelos_op[vuelos_op["CRSElapsedTime"] > 0].copy()
            sub["eficiencia"] = sub["ActualElapsedTime"] / sub["CRSElapsedTime"]
            grp_r = (
                sub.groupby(["OriginCode", "DestCode"])
                .agg(total=("pk_vuelo", "count"), ef_media=("eficiencia", "mean"))
                .reset_index()
            )
            grp_r = grp_r[grp_r["total"] >= 10].sort_values("ef_media")
            headers_r = ["Ruta", "Origen", "Destino", "Vuelos", "Índice eficiencia"]
            _estilo_header(ws_rutas, 1, headers_r)
            for _, r in grp_r.iterrows():
                ws_rutas.append([
                    f"{r['OriginCode']}-{r['DestCode']}",
                    r["OriginCode"],
                    r["DestCode"],
                    int(r["total"]),
                    round(float(r["ef_media"]), 4),
                ])
            _autofit(ws_rutas)

    # ── Hoja 3: Cancelaciones ──
    ws_canc = wb.create_sheet("Cancelaciones")
    if "CancellationCode" in df.columns and "Cancelled" in df.columns:
        cancelados = df[df["Cancelled"] == 1]
        grp_c = cancelados.groupby("CancellationCode").size().reset_index(name="count")
        total_canc = int(cancelados.__len__())
        headers_c = ["Código FAA", "Descripción", "Cancelaciones", "% del total"]
        _estilo_header(ws_canc, 1, headers_c)
        faa_desc = {"A": "Carrier", "B": "Weather", "C": "NAS", "D": "Security"}
        for _, r in grp_c.iterrows():
            code = str(r["CancellationCode"])
            ws_canc.append([
                code,
                faa_desc.get(code, "Otro"),
                int(r["count"]),
                round(int(r["count"]) / total_canc * 100, 2) if total_canc > 0 else 0,
            ])
        _autofit(ws_canc)

    # ── Hoja 4: Resumen ──
    ws_sum = wb.create_sheet("Resumen", 0)
    ws_sum["A1"] = "AeroTrack Analytics — Reporte de Análisis"
    ws_sum["A1"].font = Font(bold=True, size=14, color="1B3A6B")
    ws_sum.append([])
    ws_sum.append(["Métrica", "Valor"])
    ws_sum["A3"].font = Font(bold=True)
    ws_sum["B3"].font = Font(bold=True)
    total_vuelos = len(df)
    cancelados = int(df["Cancelled"].sum()) if "Cancelled" in df.columns else 0
    otp_global = 0.0
    if "ArrDel15" in df.columns:
        vuelos_op = df[df["Cancelled"] == 0] if "Cancelled" in df.columns else df
        otp_global = round(float((vuelos_op["ArrDel15"] == 0).sum() / max(len(vuelos_op), 1) * 100), 2)
    ws_sum.append(["Total vuelos", total_vuelos])
    ws_sum.append(["Total cancelados", cancelados])
    ws_sum.append(["Tasa cancelación (%)", round(cancelados / max(total_vuelos, 1) * 100, 2)])
    ws_sum.append(["OTP global (%)", otp_global])
    _autofit(ws_sum)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
