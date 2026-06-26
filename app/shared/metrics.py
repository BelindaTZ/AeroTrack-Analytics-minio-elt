"""Métricas centralizadas del sistema AeroTrack.

Todas las métricas OTP, cancelación, retraso, etc. se calculan aquí.
Los módulos (dashboard, puntualidad, reportes, predictivo, IA) consumen
estas funciones en vez de calcular sus propias métricas.

Garantiza consistencia: una sola fuente de verdad para cada KPI.
"""

import math
from typing import Any

import pandas as pd


def safe_float(v: Any) -> Any:
    """Convierte NaN/Inf/strings/None a valor seguro para JSON."""
    if v is None:
        return 0.0
    if isinstance(v, str):
        try:
            v = float(v)
        except (ValueError, TypeError):
            return 0.0
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return 0.0
    return v

# ── Cálculos base ─────────────────────────────────────────────────────────────


def calc_otp(total_vuelos: int, vuelos_a_tiempo: int) -> float:
    """OTP = vuelos a tiempo / vuelos operados * 100."""
    if total_vuelos == 0:
        return 0.0
    return round(vuelos_a_tiempo / total_vuelos * 100, 1)


def calc_tasa_cancelacion(total_vuelos: int, cancelados: int) -> float:
    """Tasa de cancelación = cancelados / total * 100."""
    if total_vuelos == 0:
        return 0.0
    return round(cancelados / total_vuelos * 100, 1)


def calc_retraso_promedio(minutos_totales: int, vuelos: int) -> float:
    """Retraso promedio = minutos totales / vuelos."""
    if vuelos == 0:
        return 0.0
    return round(minutos_totales / vuelos, 1)


def calc_indice_eficiencia(retraso_prom: float, vuelos: int) -> float:
    """Índice de eficiencia: menor retraso + mayor volumen = mejor."""
    if vuelos == 0:
        return 0.0
    # Normalizar retraso (0-100, donde 0 es mejor)
    score_retraso = max(0, 100 - retraso_prom * 2)
    # Factor de volumen (log para suavizar)
    import math

    score_volumen = min(100, math.log1p(vuelos) * 10)
    return round(score_retraso * 0.7 + score_volumen * 0.3, 3)


# ── Métricas desde DataFrames ─────────────────────────────────────────────────


def calc_otp_from_df(df: pd.DataFrame) -> dict:
    """Calcula OTP global desde un DataFrame con columnas de vuelos."""
    col_total = "total_vuelos_todos" if "total_vuelos_todos" in df.columns else "total_vuelos"
    col_at = "vuelos_a_tiempo"

    total = int(df[col_total].sum()) if col_total in df.columns else 0
    a_tiempo = int(df[col_at].sum()) if col_at in df.columns else 0

    return {
        "total_vuelos": total,
        "vuelos_a_tiempo": a_tiempo,
        "otp": calc_otp(total, a_tiempo),
    }


def calc_cancelaciones_from_df(df: pd.DataFrame) -> dict:
    """Calcula métricas de cancelación desde un DataFrame."""
    col_total = "total_vuelos_todos" if "total_vuelos_todos" in df.columns else "total_vuelos"

    total = int(df[col_total].sum()) if col_total in df.columns else 0
    cancelados = int(df["total_cancelados"].sum()) if "total_cancelados" in df.columns else 0

    return {
        "total_vuelos": total,
        "cancelados": cancelados,
        "tasa_cancelacion": calc_tasa_cancelacion(total, cancelados),
    }


def calc_kpi_global(df: pd.DataFrame) -> dict:
    """Calcula KPIs globales desde el fact enriquecido."""
    if df.empty:
        return {
            "total_vuelos": 0,
            "operados": 0,
            "a_tiempo": 0,
            "cancelados": 0,
            "otp": 0.0,
            "tasa_cancelacion": 0.0,
            "retraso_promedio": 0.0,
        }

    total = len(df)
    cancelados = int(df["Cancelled"].sum()) if "Cancelled" in df.columns else 0
    operados = total - cancelados

    a_tiempo = 0
    if "ArrDel15" in df.columns:
        a_tiempo = int((df["ArrDel15"] == 0).sum())

    retraso_prom = 0.0
    if "ArrDelayMinutes" in df.columns:
        retraso_prom = float(df["ArrDelayMinutes"].fillna(0).mean())

    return {
        "total_vuelos": total,
        "operados": operados,
        "a_tiempo": a_tiempo,
        "cancelados": cancelados,
        "otp": calc_otp(operados, a_tiempo),
        "tasa_cancelacion": calc_tasa_cancelacion(total, cancelados),
        "retraso_promedio": round(retraso_prom, 1),
    }


def calc_otp_por_aerolinea(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula OTP agrupado por aerolínea."""
    if df.empty or "Reporting_Airline" not in df.columns:
        return pd.DataFrame()

    grp = (
        df.groupby("Reporting_Airline")
        .agg(
            total=("Reporting_Airline", "count"),
            cancelados=("Cancelled", "sum") if "Cancelled" in df.columns else ("Reporting_Airline", lambda x: 0),
        )
        .reset_index()
    )

    grp["operados"] = grp["total"] - grp["cancelados"]

    if "ArrDel15" in df.columns:
        at = df.groupby("Reporting_Airline")["ArrDel15"].apply(lambda x: (x == 0).sum()).reset_index()
        at.columns = ["Reporting_Airline", "a_tiempo"]
        grp = grp.merge(at, on="Reporting_Airline", how="left")
    else:
        grp["a_tiempo"] = 0

    grp["otp"] = grp.apply(lambda r: calc_otp(int(r["operados"]), int(r["a_tiempo"])), axis=1)
    grp["tasa_cancelacion"] = grp.apply(lambda r: calc_tasa_cancelacion(int(r["total"]), int(r["cancelados"])), axis=1)

    return grp[["Reporting_Airline", "total", "operados", "a_tiempo", "cancelados", "otp", "tasa_cancelacion"]]


def calc_otp_por_ruta(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula OTP agrupado por ruta (origen-destino)."""
    if df.empty or "OriginCode" not in df.columns or "DestCode" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["_ruta"] = df["OriginCode"].astype(str) + "-" + df["DestCode"].astype(str)

    grp = (
        df.groupby("_ruta")
        .agg(
            total=("_ruta", "count"),
            cancelados=("Cancelled", "sum") if "Cancelled" in df.columns else ("_ruta", lambda x: 0),
        )
        .reset_index()
    )

    grp["operados"] = grp["total"] - grp["cancelados"]

    if "ArrDel15" in df.columns:
        at = df.groupby("_ruta")["ArrDel15"].apply(lambda x: (x == 0).sum()).reset_index()
        at.columns = ["_ruta", "a_tiempo"]
        grp = grp.merge(at, on="_ruta", how="left")
    else:
        grp["a_tiempo"] = 0

    grp["otp"] = grp.apply(lambda r: calc_otp(int(r["operados"]), int(r["a_tiempo"])), axis=1)

    return grp[["_ruta", "total", "operados", "a_tiempo", "cancelados", "otp"]]


def calc_tendencia_mensual(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula tendencia OTP mensual."""
    if df.empty or "month" not in df.columns:
        return pd.DataFrame()

    col_total = "total_vuelos_todos" if "total_vuelos_todos" in df.columns else "total_vuelos"
    agg = {"total": (col_total, "sum"), "operados": ("total_vuelos", "sum")}
    if "vuelos_a_tiempo" in df.columns:
        agg["a_tiempo"] = ("vuelos_a_tiempo", "sum")
    if "total_cancelados" in df.columns:
        agg["cancelados"] = ("total_cancelados", "sum")

    grp = df.groupby("month").agg(**agg).reset_index().sort_values("month")
    grp["otp"] = grp.apply(lambda r: calc_otp(int(r["operados"]), int(r["a_tiempo"])), axis=1)

    if "cancelados" in grp.columns:
        grp["tasa_cancelacion"] = grp.apply(
            lambda r: calc_tasa_cancelacion(int(r["total"]), int(r["cancelados"])), axis=1
        )

    return grp


# ── Comparativas ──────────────────────────────────────────────────────────────


def comparar_aerolineas(df: pd.DataFrame, al1: str, al2: str) -> dict:
    """Compara métricas entre dos aerolíneas."""
    if "Reporting_Airline" not in df.columns:
        return {"error": "Columna Reporting_Airline no encontrada"}

    sub1 = df[df["Reporting_Airline"] == al1]
    sub2 = df[df["Reporting_Airline"] == al2]

    kpi1 = calc_kpi_global(sub1) if not sub1.empty else {"otp": 0, "tasa_cancelacion": 0, "retraso_promedio": 0}
    kpi2 = calc_kpi_global(sub2) if not sub2.empty else {"otp": 0, "tasa_cancelacion": 0, "retraso_promedio": 0}

    return {
        al1: kpi1,
        al2: kpi2,
        "diferencia_otp": round(kpi1["otp"] - kpi2["otp"], 1),
        "mejor": al1 if kpi1["otp"] > kpi2["otp"] else al2,
    }


# ── Benchmarks ────────────────────────────────────────────────────────────────

BENCHMARK_OTP = 82.0  # Benchmark OTIF industry standard
UMBRAL_CRITICO = 75.0  # Por debajo de esto es crítico
UMBRAL_VARIABILIDAD = 8.0  # Desviación estándar máxima aceptable


def evaluar_nivel_otp(otp: float) -> dict:
    """Evalúa el nivel del OTP contra benchmarks."""
    if otp >= BENCHMARK_OTP:
        nivel = "excelente"
        color = "#10b981"
        icono = "bi-check-circle-fill"
    elif otp >= UMBRAL_CRITICO:
        nivel = "aceptable"
        color = "#f59e0b"
        icono = "bi-exclamation-circle-fill"
    else:
        nivel = "critico"
        color = "#ef4444"
        icono = "bi-exclamation-triangle-fill"

    return {
        "otp": otp,
        "nivel": nivel,
        "color": color,
        "icono": icono,
        "benchmark": BENCHMARK_OTP,
        "delta_benchmark": round(otp - BENCHMARK_OTP, 1),
    }
