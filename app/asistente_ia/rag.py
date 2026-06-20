"""RAG para el asistente analítico IA: extracción de intención y construcción de contexto.

Flujo:
  1. parse_intent(question)       → filtros detectados (airline, year, month, ruta, origen, destino, dow)
  2. _detect_question_type(q)     → tipos de análisis necesarios (delay_cause, cancelacion, dia_semana…)
  3. build_context(filtros, q)    → contexto con selección inteligente de secciones
  4. build_messages(history, ctx) → mensajes para el LLM

Estrategia de contexto:
  - KPIs globales y ranking de aerolíneas: SIEMPRE
  - Secciones adicionales: solo las relevantes al tipo de pregunta detectado
  - Para preguntas genéricas (sin tipo detectado): se cargan todas las secciones
  - Para ruta/aeropuerto específico detectado: se añade detalle desde el fact enriquecido

Fuentes de datos:
  - agg_otp_aerolinea_mes              → rankings aerolíneas, tendencia mensual, OTP global
  - agg_cancelaciones_causa            → desglose FAA A/B/C/D (global)
  - agg_cancelaciones_aerolinea_causa  → cancelaciones cruzadas aerolínea × causa FAA  [NUEVO]
  - agg_cancelaciones_ruta             → rutas por tasa de cancelación
  - agg_causas_retraso_mes             → minutos de retraso por causa y aerolínea
  - agg_rutas_eficiencia               → rutas por retraso y eficiencia
  - agg_desvios_ruta                   → rutas con más desvíos
  - agg_otp_dia_semana                 → OTP por día de la semana (global)
  - agg_otp_aerolinea_dia_semana       → OTP cruzado aerolínea × día de semana  [NUEVO]
  Para ruta/aeropuerto específico: load_enriched_fact filtrado.
  Para aerolínea + filtros adicionales: _seccion_dinamica_aerolinea desde fact enriquecido.
"""

import re
from typing import Optional

import pandas as pd

from app.shared.analytics import load_agg, load_enriched_fact, get_aerolinas


_MESES_ES: dict[str, int] = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MESES_LABEL = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun",
                "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
_DIAS_LABEL  = ["", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

_AIRLINE_CODES: Optional[list[str]] = None


def _get_codes() -> list[str]:
    global _AIRLINE_CODES
    if _AIRLINE_CODES is None:
        _AIRLINE_CODES = get_aerolinas()
    return _AIRLINE_CODES


def _safe(v) -> float:
    try:
        f = float(v)
        return 0.0 if (f != f or f in (float("inf"), float("-inf"))) else f
    except Exception:
        return 0.0


# ── Intent parsing ────────────────────────────────────────────────────────────

def parse_intent(question: str) -> dict:
    """Extrae filtros y palabras clave del intent de la pregunta."""
    q_upper = question.upper()
    q_lower = question.lower()
    filtros: dict = {}

    # Código IATA de aerolínea (2 letras)
    for code in _get_codes():
        if re.search(r'(?<![A-Z])' + re.escape(code) + r'(?![A-Z])', q_upper):
            filtros["airline"] = code
            break

    # Año
    m_year = re.search(r'\b(20\d{2})\b', question)
    if m_year:
        filtros["year"] = m_year.group(1)

    # Mes — con límite de palabra para evitar falsos positivos ("may" en "mayor")
    for mes, num in _MESES_ES.items():
        if re.search(r'\b' + re.escape(mes) + r'\b', q_lower):
            filtros["month"] = str(num)
            break

    # Ruta explícita (XXX-YYY) — solo si los códigos vienen en MAYÚSCULAS en el texto original
    # Primero buscar patrón con guion (más confiable: JFK-LAX)
    m_route = re.search(r'\b([A-Z]{3})-([A-Z]{3})\b', question)
    if m_route:
        filtros["ruta"]    = f"{m_route.group(1)}-{m_route.group(2)}"
        filtros["origen"]  = m_route.group(1)
        filtros["destino"] = m_route.group(2)
    else:
        # Buscar "de XXX a YYY" con mayúsculas originales
        m_route2 = re.search(r'\bde ([A-Z]{3}) a ([A-Z]{3})\b', question)
        if m_route2:
            filtros["ruta"]    = f"{m_route2.group(1)}-{m_route2.group(2)}"
            filtros["origen"]  = m_route2.group(1)
            filtros["destino"] = m_route2.group(2)

    # Código de aeropuerto solo — solo tokens MAYÚSCULAS en el original,
    # excluyendo abreviaturas comunes que no son códigos IATA
    _NO_IATA = {"OTP", "ELT", "KPI", "FAA", "NAS", "USA", "API", "PDF", "CSV", "SQL"}
    if "ruta" not in filtros:
        airport_matches = re.findall(r'\b([A-Z]{3})\b', question)
        airport_matches = [
            a for a in airport_matches
            if a != filtros.get("airline", "") and a not in _NO_IATA
        ]
        if len(airport_matches) == 1:
            filtros["aeropuerto"] = airport_matches[0]
        elif len(airport_matches) >= 2:
            filtros["ruta"]    = f"{airport_matches[0]}-{airport_matches[1]}"
            filtros["origen"]  = airport_matches[0]
            filtros["destino"] = airport_matches[1]

    # Día de la semana
    dias = {"lunes": 1, "martes": 2, "miércoles": 3, "miercoles": 3,
            "jueves": 4, "viernes": 5, "sábado": 6, "sabado": 6, "domingo": 7,
            "monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4,
            "friday": 5, "saturday": 6, "sunday": 7}
    for dia, num in dias.items():
        if dia in q_lower:
            filtros["dow"] = str(num)
            break

    return filtros


# ── Detección de tipo de pregunta ─────────────────────────────────────────────

def _detect_question_type(question: str) -> set:
    q = question.lower()
    tipos: set = set()
    if any(w in q for w in ["causa", "retraso", "demora", "delay", "por qué retrasa", "por que retrasa",
                             "minutos", "tardó", "tardo"]):
        tipos.add("delay_cause")
    if any(w in q for w in ["cancela", "canceló", "cancelo", "cancelación", "cancelacion",
                             "cancelado", "cancelados", "cancelar", "no operó", "no opero"]):
        tipos.add("cancelacion")
    if any(w in q for w in ["día", "dia", "dias", "semana", "lunes", "martes",
                             "miércoles", "miercoles", "jueves", "viernes",
                             "sábado", "sabado", "domingo", "finde", "fin de semana"]):
        tipos.add("dia_semana")
    if any(w in q for w in ["ruta", "origen", "destino", "vuelo entre", "vuelo de"]):
        tipos.add("ruta")
    if any(w in q for w in ["eficiencia", "eficiente", "mejor ruta", "peor ruta"]):
        tipos.add("eficiencia")
    if any(w in q for w in ["desvío", "desvio", "alternativo", "divert"]):
        tipos.add("desvio")
    if any(w in q for w in ["tendencia", "mensual", "por mes", "evolución", "evolucion",
                             "cada mes", "mes a mes"]):
        tipos.add("tendencia")
    if any(w in q for w in ["puntual", "otp", "a tiempo", "ranking", "mejor aerolínea",
                             "mejor aerolinea", "peor aerolínea", "peor aerolinea",
                             "más puntual", "mas puntual", "menos puntual"]):
        tipos.add("ranking_otp")
    return tipos


# ── Secciones de contexto ─────────────────────────────────────────────────────

def _seccion_kpis_globales(df: pd.DataFrame) -> str:
    col_total = "total_vuelos_todos" if "total_vuelos_todos" in df.columns else "total_vuelos"
    total  = int(df[col_total].sum())
    op     = int(df["total_vuelos"].sum())
    at     = int(df["vuelos_a_tiempo"].sum()) if "vuelos_a_tiempo" in df.columns else 0
    canc   = int(df["total_cancelados"].sum()) if "total_cancelados" in df.columns else 0
    otp    = at / op * 100 if op > 0 else 0.0
    t_canc = canc / total * 100 if total > 0 else 0.0
    delay  = 0.0
    if "delay_avg" in df.columns and op > 0:
        delay = _safe((df["delay_avg"] * df["total_vuelos"]).sum() / op)
    return (
        "=== KPIs GLOBALES ===\n"
        f"Total vuelos programados: {total:,}\n"
        f"Vuelos operados: {op:,}\n"
        f"OTP (puntualidad): {otp:.1f}%  ({at:,} vuelos a tiempo)\n"
        f"Tasa cancelación: {t_canc:.1f}%  ({canc:,} vuelos cancelados)\n"
        f"Retraso promedio de llegada: {delay:.1f} min"
    )


def _seccion_ranking_aerolineas(df: pd.DataFrame) -> str:
    if "carrier" not in df.columns:
        return ""
    col_total = "total_vuelos_todos" if "total_vuelos_todos" in df.columns else "total_vuelos"

    grp = df.groupby("carrier").agg(
        total=(col_total, "sum"),
        op=("total_vuelos", "sum"),
        at=("vuelos_a_tiempo", "sum") if "vuelos_a_tiempo" in df.columns else ("total_vuelos", lambda x: 0),
        canc=("total_cancelados", "sum") if "total_cancelados" in df.columns else ("total_vuelos", lambda x: 0),
    ).reset_index()
    grp["otp"]  = (grp["at"]   / grp["op"].replace(0, float("nan")) * 100).fillna(0.0)
    grp["canc_pct"] = (grp["canc"] / grp["total"].replace(0, float("nan")) * 100).fillna(0.0)

    if "delay_avg" in df.columns:
        delay_grp = df.groupby("carrier").apply(
            lambda x: _safe((x["delay_avg"] * x["total_vuelos"]).sum() / x["total_vuelos"].sum())
            if x["total_vuelos"].sum() > 0 else 0.0
        ).rename("delay")
        grp = grp.merge(delay_grp, on="carrier", how="left")
        grp["delay"] = grp["delay"].fillna(0.0)

    grp = grp[grp["op"] >= 100]

    lines = ["=== AEROLÍNEAS — RANKING COMPLETO ==="]

    por_otp = grp.sort_values("otp", ascending=False).reset_index(drop=True)
    lines.append("Por OTP (puntualidad, mayor a menor):")
    for i, row in por_otp.iterrows():
        lines.append(f"  #{i+1} {row['carrier']}: OTP {row['otp']:.1f}%  ({int(row['op']):,} vuelos operados)")

    por_canc = grp.sort_values("canc_pct", ascending=False).reset_index(drop=True)
    lines.append("Por tasa de cancelación (mayor a menor):")
    for i, row in por_canc.iterrows():
        lines.append(
            f"  #{i+1} {row['carrier']}: {row['canc_pct']:.1f}% cancelados"
            f"  ({int(row['canc']):,} de {int(row['total']):,})"
        )

    if "delay" in grp.columns:
        por_delay = grp.sort_values("delay", ascending=False).reset_index(drop=True)
        lines.append("Por retraso promedio (mayor a menor):")
        for i, row in por_delay.iterrows():
            lines.append(f"  #{i+1} {row['carrier']}: {row['delay']:.1f} min retraso")

    return "\n".join(lines)


def _seccion_tendencia_mensual(df: pd.DataFrame) -> str:
    if "month" not in df.columns:
        return ""
    col_total = "total_vuelos_todos" if "total_vuelos_todos" in df.columns else "total_vuelos"
    agg: dict = {"total": (col_total, "sum"), "op": ("total_vuelos", "sum")}
    if "vuelos_a_tiempo" in df.columns:
        agg["at"] = ("vuelos_a_tiempo", "sum")
    if "total_cancelados" in df.columns:
        agg["canc"] = ("total_cancelados", "sum")
    grp = df.groupby("month").agg(**agg).reset_index().sort_values("month")
    lines = ["=== TENDENCIA MENSUAL ==="]
    for _, row in grp.iterrows():
        mes = _MESES_LABEL[int(row["month"])] if 1 <= int(row["month"]) <= 12 else str(int(row["month"]))
        otp_s  = f", OTP {row['at']/row['op']*100:.1f}%" if "at" in row and row["op"] > 0 else ""
        canc_s = f", {int(row['canc']):,} cancelados" if "canc" in row else ""
        lines.append(f"  {mes}: {int(row['total']):,} vuelos{otp_s}{canc_s}")
    return "\n".join(lines)


def _seccion_cancelaciones_causa(df: pd.DataFrame) -> str:
    if df.empty or "cancellation_code" not in df.columns:
        return ""
    codigos = {"A": "Carrier (aerolínea)", "B": "Weather (clima)",
               "C": "NAS (sistema aéreo)", "D": "Security (seguridad)"}
    total_canc = int(df["total_cancelados"].sum()) if "total_cancelados" in df.columns else 0
    grp = df.groupby("cancellation_code")["total_cancelados"].sum().reset_index()
    lines = ["=== CANCELACIONES POR CÓDIGO FAA ===",
             f"Total cancelados: {total_canc:,}"]
    for _, row in grp.sort_values("total_cancelados", ascending=False).iterrows():
        code  = str(row["cancellation_code"])
        label = codigos.get(code, f"Código {code}")
        pct   = row["total_cancelados"] / total_canc * 100 if total_canc > 0 else 0
        lines.append(f"  {code} – {label}: {int(row['total_cancelados']):,} ({pct:.1f}%)")
    return "\n".join(lines)


def _seccion_cancelaciones_ruta(df: pd.DataFrame, top_n: int = 15) -> str:
    if df.empty or "origin" not in df.columns:
        return ""
    has_tasa   = "tasa_cancelacion" in df.columns
    has_retraso = "retraso_prom_min" in df.columns
    df = df.copy()
    df["_ruta"] = df["origin"].astype(str) + "-" + df["dest"].astype(str)
    sort_col = "tasa_cancelacion" if has_tasa else "total_cancelados"
    top = df[df["total_vuelos"] >= 30].sort_values(sort_col, ascending=False).head(top_n)

    lines = [f"=== RUTAS CON MAYOR TASA DE CANCELACIÓN (top {top_n}) ==="]
    for _, row in top.iterrows():
        tasa_s  = f"{row['tasa_cancelacion']*100:.1f}% cancelados" if has_tasa else ""
        canc_s  = f"({int(row['total_cancelados']):,} de {int(row['total_vuelos']):,} vuelos)"
        delay_s = f", retraso prom {row['retraso_prom_min']:.1f} min" if has_retraso else ""
        lines.append(f"  {row['_ruta']}: {tasa_s} {canc_s}{delay_s}")

    bottom = df[df["total_vuelos"] >= 30].sort_values(sort_col, ascending=True).head(5)
    lines.append("Rutas con MENOR tasa de cancelación (top 5):")
    for _, row in bottom.iterrows():
        tasa_s = f"{row['tasa_cancelacion']*100:.1f}% cancelados" if has_tasa else ""
        lines.append(f"  {row['_ruta']}: {tasa_s} ({int(row['total_vuelos']):,} vuelos)")

    return "\n".join(lines)


def _seccion_rutas_eficiencia(df: pd.DataFrame) -> str:
    if df.empty or "origin" not in df.columns or "dest" not in df.columns:
        return ""
    df = df.copy()
    df["_ruta"] = df["origin"].astype(str) + "-" + df["dest"].astype(str)
    has_delay = "retraso_prom" in df.columns
    has_efic  = "eficiencia_media" in df.columns
    has_total = "total_vuelos" in df.columns
    base = df[df["total_vuelos"] >= 30] if has_total else df

    lines = ["=== RUTAS — EFICIENCIA Y RETRASO ==="]
    if has_delay:
        peores = base.sort_values("retraso_prom", ascending=False).head(10)
        lines.append("Rutas con MAYOR retraso (peor rendimiento):")
        for _, row in peores.iterrows():
            efic_s = f", eficiencia {row['eficiencia_media']:.3f}" if has_efic else ""
            vuelos_s = f"  ({int(row['total_vuelos']):,} vuelos)" if has_total else ""
            lines.append(f"  {row['_ruta']}: {_safe(row['retraso_prom']):.1f} min retraso{efic_s}{vuelos_s}")
        mejores = base.sort_values("retraso_prom", ascending=True).head(5)
        lines.append("Rutas con MENOR retraso (más eficientes):")
        for _, row in mejores.iterrows():
            lines.append(f"  {row['_ruta']}: {_safe(row['retraso_prom']):.1f} min retraso")
    elif has_total:
        top = base.sort_values("total_vuelos", ascending=False).head(10)
        lines.append("Rutas más frecuentes:")
        for _, row in top.iterrows():
            lines.append(f"  {row['_ruta']}: {int(row['total_vuelos']):,} vuelos")
    return "\n".join(lines)


def _seccion_desvios_ruta(df: pd.DataFrame) -> str:
    if df.empty or "origin" not in df.columns:
        return ""
    df = df.copy()
    df["_ruta"] = df["origin"].astype(str) + "-" + df["dest"].astype(str)
    has_alt = "alt_airport" in df.columns
    top = df.sort_values("total_desvios", ascending=False).head(10)
    lines = ["=== RUTAS CON MÁS DESVÍOS ==="]
    for _, row in top.iterrows():
        alt_s   = f" → alt. {row['alt_airport']}" if has_alt and row.get("alt_airport") else ""
        delay_s = f", retraso desvío {row['divarrdelay_avg']:.1f} min" if "divarrdelay_avg" in row else ""
        lines.append(f"  {row['_ruta']}{alt_s}: {int(row['total_desvios']):,} desvíos{delay_s}")
    return "\n".join(lines)


def _seccion_causas_retraso(df: pd.DataFrame, airline: str | None = None) -> str:
    causas = {
        "carrierdelay":     "Carrier (aerolínea)",
        "weatherdelay":     "Clima (Weather)",
        "nasdelay":         "NAS (sistema aéreo)",
        "securitydelay":    "Seguridad",
        "lateaircraftdelay":"Late aircraft",
    }
    cols = [c for c in causas if c in df.columns]
    if not cols:
        return ""

    df = df.copy()
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    # Totales globales (o filtrados por aerolínea si hay filtro)
    sub = df[df["carrier"] == airline] if (airline and "carrier" in df.columns) else df
    data: dict[str, float] = {}
    for col, label in causas.items():
        if col in sub.columns:
            v = float(sub[col].sum())
            if v > 0:
                data[label] = v
    if not data:
        return ""
    total = sum(data.values())
    titulo = f"CAUSAS DE RETRASO — {airline}" if airline else "CAUSAS DE RETRASO (minutos totales)"
    lines = [f"=== {titulo} ==="]
    for label, mins in sorted(data.items(), key=lambda x: -x[1]):
        pct = mins / total * 100
        lines.append(f"  {label}: {mins:,.0f} min ({pct:.1f}%)")
    return "\n".join(lines)


def _seccion_otp_dia_semana(df: pd.DataFrame) -> str:
    if df.empty or "day_of_week" not in df.columns or "otp_pct" not in df.columns:
        return ""
    df = df.sort_values("day_of_week")
    lines = ["=== OTP POR DÍA DE LA SEMANA ==="]
    for _, row in df.iterrows():
        dia = _DIAS_LABEL[int(row["day_of_week"])] if 1 <= int(row["day_of_week"]) <= 7 else str(int(row["day_of_week"]))
        lines.append(f"  {dia}: OTP {_safe(row['otp_pct']):.1f}%")
    return "\n".join(lines)


def _seccion_causas_retraso_por_aerolinea(df: pd.DataFrame, airline: str | None = None) -> str:
    """Desglose de minutos de retraso por causa y aerolínea (usa agg_causas_retraso_mes)."""
    causas = {
        "carrierdelay":     "Carrier (aerolínea)",
        "weatherdelay":     "Clima (Weather)",
        "nasdelay":         "NAS (sistema aéreo)",
        "securitydelay":    "Seguridad",
        "lateaircraftdelay":"Late aircraft",
    }
    cols = [c for c in causas if c in df.columns]
    if not cols or "carrier" not in df.columns:
        return ""

    df = df.copy()
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    if airline:
        sub = df[df["carrier"] == airline]
        if sub.empty:
            return ""
        totals = {causas[c]: float(sub[c].sum()) for c in cols if sub[c].sum() > 0}
        if not totals:
            return ""
        grand = sum(totals.values())
        lines = [f"=== CAUSAS DE RETRASO — {airline} (minutos totales) ==="]
        for label, mins in sorted(totals.items(), key=lambda x: -x[1]):
            pct = mins / grand * 100
            lines.append(f"  {label}: {mins:,.0f} min ({pct:.1f}%)")
        return "\n".join(lines)

    # Sin filtro de aerolínea → ranking de aerolíneas por cada causa principal
    grp = df.groupby("carrier")[cols].sum()
    grp = grp[grp.sum(axis=1) > 0]
    if grp.empty:
        return ""
    lines = ["=== CAUSAS DE RETRASO POR AEROLÍNEA (minutos totales) ==="]
    for col, label in causas.items():
        if col not in grp.columns:
            continue
        top = grp[col].sort_values(ascending=False).head(5)
        if top.sum() == 0:
            continue
        lines.append(f"Top aerolíneas — {label}:")
        for carrier, mins in top.items():
            lines.append(f"  {carrier}: {mins:,.0f} min")
    return "\n".join(lines)


def _seccion_cancelaciones_aerolinea_causa(df: pd.DataFrame, airline: str | None = None) -> str:
    """Cancelaciones por aerolínea y código FAA (usa agg_cancelaciones_aerolinea_causa)."""
    if df.empty or "carrier" not in df.columns or "cancellation_code" not in df.columns:
        return ""
    codigos = {"A": "Carrier (aerolínea)", "B": "Weather (clima)",
               "C": "NAS (sistema aéreo)", "D": "Security (seguridad)"}

    if airline:
        sub = df[df["carrier"] == airline]
        if sub.empty:
            return ""
        grp = sub.groupby("cancellation_code")["total_cancelados"].sum()
        total = int(grp.sum())
        if total == 0:
            return ""
        lines = [f"=== CANCELACIONES {airline} POR CÓDIGO FAA ===",
                 f"Total cancelados: {total:,}"]
        for code, cnt in grp.sort_values(ascending=False).items():
            label = codigos.get(str(code), f"Código {code}")
            pct = cnt / total * 100
            lines.append(f"  {code} – {label}: {int(cnt):,} ({pct:.1f}%)")
        return "\n".join(lines)

    # Sin filtro → top aerolíneas por causa de cancelación
    grp = df.groupby(["carrier", "cancellation_code"])["total_cancelados"].sum().reset_index()
    total_global = int(grp["total_cancelados"].sum())
    if total_global == 0:
        return ""
    lines = ["=== CANCELACIONES POR AEROLÍNEA Y CAUSA FAA ==="]
    for code, label in codigos.items():
        sub = grp[grp["cancellation_code"] == code].sort_values("total_cancelados", ascending=False).head(5)
        if sub.empty or sub["total_cancelados"].sum() == 0:
            continue
        lines.append(f"Causa {code} – {label}: top aerolíneas")
        for _, row in sub.iterrows():
            pct = row["total_cancelados"] / total_global * 100
            lines.append(f"  {row['carrier']}: {int(row['total_cancelados']):,} ({pct:.1f}% del total)")
    return "\n".join(lines)


def _seccion_otp_aerolinea_dia_semana(df: pd.DataFrame, airline: str | None = None, dow: str | None = None) -> str:
    """OTP por aerolínea y día de semana (usa agg_otp_aerolinea_dia_semana)."""
    if df.empty or "carrier" not in df.columns or "day_of_week" not in df.columns:
        return ""

    if airline:
        sub = df[df["carrier"] == airline].sort_values("day_of_week")
        if sub.empty:
            return ""
        lines = [f"=== OTP DE {airline} POR DÍA DE LA SEMANA ==="]
        for _, row in sub.iterrows():
            dia = _DIAS_LABEL[int(row["day_of_week"])] if 1 <= int(row["day_of_week"]) <= 7 else str(int(row["day_of_week"]))
            lines.append(f"  {dia}: OTP {_safe(row['otp_pct']):.1f}%  ({int(row['total_vuelos']):,} vuelos)")
        return "\n".join(lines)

    if dow:
        sub = df[df["day_of_week"] == int(dow)].sort_values("otp_pct", ascending=False)
        if sub.empty:
            return ""
        dia = _DIAS_LABEL[int(dow)] if 1 <= int(dow) <= 7 else dow
        lines = [f"=== RANKING AEROLÍNEAS — OTP DEL {dia.upper()} ==="]
        for i, (_, row) in enumerate(sub.iterrows()):
            lines.append(f"  #{i+1} {row['carrier']}: OTP {_safe(row['otp_pct']):.1f}%")
        return "\n".join(lines)

    # Sin filtros → resumen fines de semana vs semana laboral
    df2 = df.copy()
    df2["es_finde"] = df2["day_of_week"].isin([6, 7])
    grp = df2.groupby(["carrier", "es_finde"]).agg(
        total=("total_vuelos", "sum"),
        at=("vuelos_a_tiempo", "sum"),
    ).reset_index()
    grp["otp"] = (grp["at"] / grp["total"].replace(0, float("nan")) * 100).fillna(0.0)
    grp = grp[grp["total"] >= 100]
    finde = grp[grp["es_finde"]].set_index("carrier")["otp"]
    laboral = grp[~grp["es_finde"]].set_index("carrier")["otp"]
    comun = finde.index.intersection(laboral.index)
    if comun.empty:
        return ""
    diff = (finde[comun] - laboral[comun]).sort_values()
    lines = ["=== OTP FINDE vs. SEMANA LABORAL (diferencia OTP%) ==="]
    lines.append("Aerolíneas que mejoran más en fines de semana:")
    for carrier, d in diff.tail(5).sort_values(ascending=False).items():
        lines.append(f"  {carrier}: +{d:.1f}% mejor el finde")
    lines.append("Aerolíneas que empeoran más en fines de semana:")
    for carrier, d in diff.head(5).items():
        lines.append(f"  {carrier}: {d:.1f}% peor el finde")
    return "\n".join(lines)


def _seccion_dinamica_aerolinea(filtros: dict, tipos: set) -> str:
    """Consulta dinámica desde fact_vuelo para preguntas con aerolínea + filtros específicos."""
    airline = filtros.get("airline")
    if not airline:
        return ""
    # Solo aplica cuando hay un filtro adicional (no solo la aerolínea)
    extra = {k: v for k, v in filtros.items() if k != "airline"}
    if not extra:
        return ""
    try:
        df = load_enriched_fact(filtros)
        if df.empty:
            return ""

        lines = [f"=== DETALLE ESPECÍFICO — {airline} ==="]

        # Causas de retraso con filtros aplicados
        causa_cols = {
            "CarrierDelay":      "Carrier",
            "WeatherDelay":      "Clima",
            "NASDelay":          "NAS",
            "SecurityDelay":     "Seguridad",
            "LateAircraftDelay": "Late aircraft",
        }
        avail = {c: l for c, l in causa_cols.items() if c in df.columns}
        if avail and "delay_cause" in tipos:
            op = df[df["Cancelled"] == 0] if "Cancelled" in df.columns else df
            totals = {l: float(pd.to_numeric(op[c], errors="coerce").fillna(0).sum())
                      for c, l in avail.items()}
            grand = sum(totals.values())
            if grand > 0:
                lines.append("Minutos de retraso por causa (con filtros activos):")
                for label, mins in sorted(totals.items(), key=lambda x: -x[1]):
                    if mins > 0:
                        lines.append(f"  {label}: {mins:,.0f} min ({mins/grand*100:.1f}%)")

        # OTP por día de semana con filtros aplicados
        if "dia_semana" in tipos and "DayOfWeek" in df.columns:
            op = df[df["Cancelled"] == 0] if "Cancelled" in df.columns else df
            if "_at" not in op.columns and "ArrDel15" in op.columns:
                op = op.copy()
                op["_at"] = (op["ArrDel15"] == 0).astype(int)
            if "_at" in op.columns:
                dow_grp = op.groupby("DayOfWeek").agg(
                    total=("DayOfWeek", "count"),
                    at=("_at", "sum"),
                ).reset_index()
                dow_grp["otp"] = (dow_grp["at"] / dow_grp["total"].replace(0, float("nan")) * 100).fillna(0.0)
                lines.append("OTP por día de semana (con filtros activos):")
                for _, row in dow_grp.sort_values("DayOfWeek").iterrows():
                    dia = _DIAS_LABEL[int(row["DayOfWeek"])] if 1 <= int(row["DayOfWeek"]) <= 7 else str(int(row["DayOfWeek"]))
                    lines.append(f"  {dia}: OTP {row['otp']:.1f}%  ({int(row['total']):,} vuelos)")

        return "\n".join(lines) if len(lines) > 1 else ""
    except Exception:
        return ""


def _seccion_ruta_especifica(ruta: str) -> str:
    """Carga datos del fact filtrado para una ruta específica (usa caché de memoria)."""
    parts = ruta.split("-")
    if len(parts) != 2:
        return ""
    try:
        df = load_enriched_fact({"ruta": ruta})
        if df.empty:
            return f"=== RUTA {ruta} ===\nNo hay datos para esta ruta."

        total = len(df)
        canc  = int(df["Cancelled"].sum()) if "Cancelled" in df.columns else 0
        t_canc = canc / total * 100 if total > 0 else 0.0

        op    = df[df["Cancelled"] == 0] if "Cancelled" in df.columns else df
        n_op  = len(op)
        at    = int((op["ArrDel15"] == 0).sum()) if "ArrDel15" in op.columns else 0
        otp   = at / n_op * 100 if n_op > 0 else 0.0
        delay = _safe(op["ArrDelayMinutes"].fillna(0).mean()) if "ArrDelayMinutes" in op.columns else 0.0

        lines = [
            f"=== DETALLE RUTA {ruta} ===",
            f"Total vuelos programados: {total:,}",
            f"Vuelos operados: {n_op:,}",
            f"Vuelos cancelados: {canc:,} ({t_canc:.1f}%)",
            f"OTP: {otp:.1f}%  ({at:,} a tiempo de {n_op:,} operados)",
            f"Retraso promedio de llegada: {delay:.1f} min",
        ]

        # Aerolíneas que operan esta ruta
        if "Reporting_Airline" in df.columns:
            al_grp = df.groupby("Reporting_Airline").agg(
                total=("Reporting_Airline", "count"),
                canc=("Cancelled", "sum") if "Cancelled" in df.columns else ("Reporting_Airline", lambda x: 0),
            ).reset_index()
            al_grp["tasa"] = (al_grp["canc"] / al_grp["total"] * 100).fillna(0)
            al_grp = al_grp.sort_values("total", ascending=False).head(5)
            lines.append("Aerolíneas que operan esta ruta:")
            for _, row in al_grp.iterrows():
                lines.append(f"  {row['Reporting_Airline']}: {int(row['total']):,} vuelos, {row['tasa']:.1f}% cancelados")

        # Causas de cancelación
        if "CancellationCode" in df.columns and canc > 0:
            codigos = {"A": "Carrier", "B": "Weather", "C": "NAS", "D": "Security"}
            cod_grp = df[df["Cancelled"] == 1]["CancellationCode"].value_counts()
            lines.append("Causas de cancelación en esta ruta:")
            for code, cnt in cod_grp.items():
                lines.append(f"  {codigos.get(str(code), code)}: {cnt:,}")

        return "\n".join(lines)
    except Exception as exc:
        return f"=== RUTA {ruta} ===\nNo se pudieron cargar datos específicos: {exc}"


def _seccion_aeropuerto(aeropuerto: str, df_rutas: pd.DataFrame, df_canc_ruta: pd.DataFrame) -> str:
    """Resumen de un aeropuerto específico como origen o destino."""
    lines = [f"=== AEROPUERTO {aeropuerto} ==="]
    if not df_rutas.empty and "origin" in df_rutas.columns:
        como_origen = df_rutas[df_rutas["origin"] == aeropuerto]
        como_destino = df_rutas[df_rutas["dest"] == aeropuerto]
        if not como_origen.empty and "retraso_prom" in como_origen.columns:
            delay_orig = _safe(como_origen["retraso_prom"].mean())
            lines.append(f"Retraso prom. como ORIGEN ({len(como_origen)} rutas): {delay_orig:.1f} min")
        if not como_destino.empty and "retraso_prom" in como_destino.columns:
            delay_dest = _safe(como_destino["retraso_prom"].mean())
            lines.append(f"Retraso prom. como DESTINO ({len(como_destino)} rutas): {delay_dest:.1f} min")
    if not df_canc_ruta.empty and "origin" in df_canc_ruta.columns:
        ap_rows = df_canc_ruta[
            (df_canc_ruta["origin"] == aeropuerto) | (df_canc_ruta["dest"] == aeropuerto)
        ]
        if not ap_rows.empty and "tasa_cancelacion" in ap_rows.columns:
            tasa_media = _safe(ap_rows["tasa_cancelacion"].mean()) * 100
            lines.append(f"Tasa media de cancelación en rutas con {aeropuerto}: {tasa_media:.1f}%")
    return "\n".join(lines) if len(lines) > 1 else ""


# ── build_context ─────────────────────────────────────────────────────────────

def build_context(filtros: dict, question: str = "") -> str:
    """
    Construye contexto con selección inteligente de secciones según el tipo de pregunta.
    Para preguntas genéricas (sin tipo detectado) carga todo como antes.
    Para preguntas específicas carga las secciones relevantes + las nuevas tablas cross-dimensionales.
    """
    tipos = _detect_question_type(question)
    airline = filtros.get("airline")
    dow     = filtros.get("dow")

    f_otp    = {k: v for k, v in filtros.items() if k in ("airline", "year", "month")}
    f_mes    = {k: v for k, v in filtros.items() if k in ("year", "month")}
    f_global: dict = {}

    # Cuando la pregunta es genérica (sin tipo detectado) se carga todo
    carga_todo = not tipos

    secciones: list[str] = []
    if filtros:
        secciones.append(f"[Filtros activos: {_describe_filtros(filtros)}]")

    # ── 1. KPIs globales + ranking aerolíneas + tendencia mensual ─────────
    # El ranking siempre se carga. Si el filtro de año/aerolínea deja el df vacío,
    # se carga sin ese filtro para garantizar que siempre haya datos de referencia.
    try:
        df_otp = load_agg("agg_otp_aerolinea_mes", f_otp)

        # Fallback: si el filtro temporal/aerolinea generó vacío, cargar sin filtros
        if df_otp.empty and f_otp:
            df_otp_full = load_agg("agg_otp_aerolinea_mes", {})
            if not df_otp_full.empty:
                year_avail = sorted(df_otp_full["year"].unique().astype(int).tolist()) if "year" in df_otp_full.columns else []
                años_str = ", ".join(str(y) for y in year_avail)
                secciones.append(
                    f"[Nota: no hay datos para los filtros {_describe_filtros(f_otp)}. "
                    f"Se muestran datos globales disponibles (años en el sistema: {años_str}).]"
                )
                df_otp = df_otp_full

        if not df_otp.empty:
            secciones.append(_seccion_kpis_globales(df_otp))
            if carga_todo or "tendencia" in tipos or "ranking_otp" in tipos:
                secciones.append(_seccion_tendencia_mensual(df_otp))

        # Ranking sin filtro de aerolínea para mostrar comparativa completa
        df_universe = load_agg("agg_otp_aerolinea_mes", f_mes) if airline else df_otp
        if df_universe.empty and f_mes:
            df_universe = load_agg("agg_otp_aerolinea_mes", {})
        secciones.append(_seccion_ranking_aerolineas(df_universe))
    except Exception:
        pass

    # ── 2. Cancelaciones por código FAA + desglose por aerolínea ──────────
    if carga_todo or "cancelacion" in tipos:
        try:
            df_causa = load_agg("agg_cancelaciones_causa", f_mes)
            sec = _seccion_cancelaciones_causa(df_causa)
            if sec:
                secciones.append(sec)
        except Exception:
            pass
        # Nueva tabla: cancelaciones aerolínea × causa — solo cuando se pregunta por cancelaciones
        if "cancelacion" in tipos or airline:
            try:
                df_canc_al = load_agg("agg_cancelaciones_aerolinea_causa", f_mes)
                sec = _seccion_cancelaciones_aerolinea_causa(df_canc_al, airline)
                if sec:
                    secciones.append(sec)
            except Exception:
                pass

    # ── 3. Rutas con mayor tasa de cancelación ────────────────────────────
    if carga_todo or "cancelacion" in tipos or "ruta" in tipos:
        try:
            df_canc_ruta = load_agg("agg_cancelaciones_ruta", f_global)
            sec = _seccion_cancelaciones_ruta(df_canc_ruta)
            if sec:
                secciones.append(sec)
        except Exception:
            pass

    # ── 4. Causas de retraso (con desglose por aerolínea si se pide) ─────
    if carga_todo or "delay_cause" in tipos:
        try:
            df_causas_ret = load_agg("agg_causas_retraso_mes", f_mes)
            sec = _seccion_causas_retraso(df_causas_ret, airline)
            if sec:
                secciones.append(sec)
            # Desglose por aerolínea solo cuando la pregunta es sobre causas de retraso
            if "delay_cause" in tipos and not airline:
                sec2 = _seccion_causas_retraso_por_aerolinea(df_causas_ret)
                if sec2:
                    secciones.append(sec2)
        except Exception:
            pass

    # ── 5. Rutas — eficiencia y retraso ───────────────────────────────────
    if carga_todo or "eficiencia" in tipos or "ruta" in tipos:
        try:
            df_rutas = load_agg("agg_rutas_eficiencia", f_mes)
            sec = _seccion_rutas_eficiencia(df_rutas)
            if sec:
                secciones.append(sec)
        except Exception:
            pass

    # ── 6. Desvíos por ruta ───────────────────────────────────────────────
    if carga_todo or "desvio" in tipos:
        try:
            df_dev = load_agg("agg_desvios_ruta", f_global)
            sec = _seccion_desvios_ruta(df_dev)
            if sec:
                secciones.append(sec)
        except Exception:
            pass

    # ── 7. OTP por día de la semana + desglose por aerolínea ──────────────
    if carga_todo or "dia_semana" in tipos or dow:
        try:
            df_dow = load_agg("agg_otp_dia_semana", f_global)
            sec = _seccion_otp_dia_semana(df_dow)
            if sec:
                secciones.append(sec)
        except Exception:
            pass
        # Nueva tabla: OTP aerolínea × día — solo cuando se pregunta por días o aerolínea específica
        if "dia_semana" in tipos or dow or airline:
            try:
                df_al_dow = load_agg("agg_otp_aerolinea_dia_semana", f_global)
                sec = _seccion_otp_aerolinea_dia_semana(df_al_dow, airline, dow)
                if sec:
                    secciones.append(sec)
            except Exception:
                pass

    # ── 8. Detalle dinámico: aerolínea específica + filtros adicionales ────
    if airline:
        extra_tipos = tipos - {"tendencia"}  # tendencia ya cubierta por sección mensual
        sec = _seccion_dinamica_aerolinea(filtros, extra_tipos)
        if sec:
            secciones.append(sec)

    # ── 9. Detalle de ruta específica (si se detectó una ruta) ───────────
    if filtros.get("ruta"):
        secciones.append(_seccion_ruta_especifica(filtros["ruta"]))

    # ── 10. Detalle de aeropuerto específico ──────────────────────────────
    if filtros.get("aeropuerto") and not filtros.get("ruta"):
        try:
            df_rutas_ap = load_agg("agg_rutas_eficiencia", f_mes)
            df_canc_ap  = load_agg("agg_cancelaciones_ruta", f_global)
        except Exception:
            df_rutas_ap = df_canc_ap = pd.DataFrame()
        sec = _seccion_aeropuerto(filtros["aeropuerto"], df_rutas_ap, df_canc_ap)
        if sec:
            secciones.append(sec)

    result = "\n\n".join(s for s in secciones if s and s.strip())
    return result if result else (
        "No hay datos disponibles. Asegúrese de que el pipeline ELT se ha ejecutado."
    )


# ── build_messages ────────────────────────────────────────────────────────────

def build_messages(history: list[dict], context: str, question: str) -> list[dict]:
    system = (
        "Eres AeroTrack, un asistente analítico de datos de aviación de EE. UU. "
        "Respondes siempre en español, de forma concisa y directa.\n\n"
        "REGLAS ABSOLUTAS:\n"
        "1. SOLO puedes citar números y porcentajes que aparezcan LITERALMENTE en el contexto de datos.\n"
        "2. PROHIBIDO calcular, estimar, redondear, inferir o extrapolar cualquier cifra nueva.\n"
        "3. PROHIBIDO inventar causas externas (demanda, infraestructura, clima) "
        "salvo que aparezcan en el contexto.\n"
        "4. Si la pregunta tiene respuesta PARCIAL en el contexto: responde primero con lo que SÍ tienes "
        "(citando valores literales) e indica al final qué dato específico no está disponible. "
        "NUNCA respondas solo 'no tengo ese dato' si puedes dar información parcialmente relevante.\n"
        "5. Cuando afirmes algo, cita el valor exacto del contexto.\n"
        "6. Los rankings del contexto están pre-calculados — úsalos directamente.\n"
        "7. Puedes combinar y sintetizar datos de diferentes secciones del contexto para dar "
        "una respuesta más completa, siempre citando solo valores literales presentes.\n"
        "8. FORMATO DE RESPUESTA: Para rankings, comparativas o tablas de datos usa SIEMPRE tablas "
        "markdown con este formato exacto:\n"
        "| Columna A | Columna B |\n"
        "|-----------|----------|\n"
        "| valor     | valor    |\n"
        "Máximo 15 filas por tabla. Para listas cortas (≤4 items) usa viñetas (- item). "
        "Para análisis narrativo usa párrafos cortos. Combina tabla + párrafo de conclusión cuando sea útil."
    )
    user_with_ctx = (
        f"=== DATOS DEL SISTEMA ===\n{context}\n=== FIN DE DATOS ===\n\n"
        f"Pregunta: {question}"
    )
    messages: list[dict] = [{"role": "system", "content": system}]
    messages.extend(history[-6:])
    messages.append({"role": "user", "content": user_with_ctx})
    return messages


# ── helpers ───────────────────────────────────────────────────────────────────

def _describe_filtros(filtros: dict) -> str:
    partes = []
    if filtros.get("airline"):
        partes.append(f"aerolínea={filtros['airline']}")
    if filtros.get("year"):
        partes.append(f"año={filtros['year']}")
    if filtros.get("month"):
        try:
            partes.append(f"mes={_MESES_LABEL[int(filtros['month'])]}")
        except Exception:
            partes.append(f"mes={filtros['month']}")
    if filtros.get("ruta"):
        partes.append(f"ruta={filtros['ruta']}")
    if filtros.get("aeropuerto"):
        partes.append(f"aeropuerto={filtros['aeropuerto']}")
    if filtros.get("dow"):
        try:
            partes.append(f"día={_DIAS_LABEL[int(filtros['dow'])]}")
        except Exception:
            partes.append(f"día={filtros['dow']}")
    return ", ".join(partes) or "ninguno"
