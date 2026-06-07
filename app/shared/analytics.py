"""Helpers compartidos para cargar fact_vuelo enriquecido con dimensiones."""

import time
from typing import Optional

import pandas as pd

from app.config import MINIO_BUCKET_DIMS
from app.shared.clients.minio_client import read_parquet

# Cache del fact table completo (sin filtros) — TTL 10 minutos
_fact_cache: dict = {"df": None, "expires": 0.0, "bucket": ""}
_FACT_TTL = 600  # segundos

# Cache de agregaciones pre-computadas — TTL 10 minutos
_agg_cache: dict = {}
_AGG_TTL = 600

# Cache de listas de dimensiones (aerolíneas, años) — TTL 5 minutos
_dim_cache: dict = {}
_DIM_TTL = 300


def _desnormalizar(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte columnas Categorical a su dtype base (str→object, int→int64).
    Parquet con dictionary encoding devuelve Categorical, lo que rompe
    concatenaciones de strings y operaciones de merge."""
    for col in df.columns:
        if hasattr(df[col], "cat"):
            base = df[col].cat.categories.dtype
            df[col] = df[col].astype(base)
    return df


def _safe_read(bucket: str, tabla: str, cols: list[str]) -> Optional[pd.DataFrame]:
    try:
        df = read_parquet(bucket, tabla)
        existing = [c for c in cols if c in df.columns]
        return _desnormalizar(df[existing].copy())
    except Exception:
        return None


def _load_base_fact(bucket: str) -> pd.DataFrame:
    """Carga y enriquece fact_vuelo desde MinIO. Resultado cacheado 10 min."""
    global _fact_cache
    if _fact_cache["df"] is not None and bucket == _fact_cache["bucket"] and time.time() < _fact_cache["expires"]:
        return _fact_cache["df"].copy()

    fact = _desnormalizar(read_parquet(bucket, "fact_vuelo").copy())

    # Normalizar todas las columnas FK a int64
    for col in fact.columns:
        if col.startswith("fk_") or col == "pk_vuelo":
            fact[col] = pd.to_numeric(fact[col], errors="coerce").fillna(0).astype("int64")

    def _norm_pk(df: Optional[pd.DataFrame], pk_col: str) -> Optional[pd.DataFrame]:
        if df is not None and pk_col in df.columns:
            df = df.copy()
            df[pk_col] = pd.to_numeric(df[pk_col], errors="coerce").fillna(0).astype("int64")
        return df

    dim_t = _norm_pk(_safe_read(bucket, "dim_tiempo", ["pk_tiempo", "Year", "Month", "DayOfWeek", "FlightDate", "Quarter"]), "pk_tiempo")
    if dim_t is not None and "fk_tiempo" in fact.columns:
        fact = fact.merge(dim_t, left_on="fk_tiempo", right_on="pk_tiempo", how="left")

    dim_al = _norm_pk(_safe_read(bucket, "dim_aerolinea", ["pk_aerolinea", "Reporting_Airline"]), "pk_aerolinea")
    if dim_al is not None and "fk_aerolinea" in fact.columns:
        fact = fact.merge(dim_al, left_on="fk_aerolinea", right_on="pk_aerolinea", how="left")

    dim_r = _norm_pk(_safe_read(bucket, "dim_ruta", ["pk_ruta", "OriginCode", "DestCode", "OriginCityName", "DestCityName", "Distance"]), "pk_ruta")
    if dim_r is not None and "fk_ruta" in fact.columns:
        fact = fact.merge(dim_r, left_on="fk_ruta", right_on="pk_ruta", how="left")

    dim_can = _norm_pk(_safe_read(bucket, "dim_cancelacion", ["pk_cancelacion", "Cancelled", "CancellationCode", "Diverted"]), "pk_cancelacion")
    if dim_can is not None and "fk_cancelacion" in fact.columns:
        fact = fact.merge(dim_can, left_on="fk_cancelacion", right_on="pk_cancelacion", how="left")

    dim_cl = _norm_pk(_safe_read(bucket, "dim_clasificacion_retraso", ["pk_clasificacion", "ArrDel15", "DepDel15"]), "pk_clasificacion")
    if dim_cl is not None and "fk_clasificacion_retraso" in fact.columns:
        fact = fact.merge(dim_cl, left_on="fk_clasificacion_retraso", right_on="pk_clasificacion", how="left")

    dim_hor = _norm_pk(_safe_read(bucket, "dim_horario", ["pk_horario", "ArrDelay", "DepDelay", "ArrDelayMinutes", "DepDelayMinutes"]), "pk_horario")
    if dim_hor is not None and "fk_horario" in fact.columns:
        fact = fact.merge(dim_hor, left_on="fk_horario", right_on="pk_horario", how="left")

    dim_rc = _norm_pk(_safe_read(bucket, "dim_retraso_causa", ["pk_retraso_causa", "CarrierDelay", "WeatherDelay", "NASDelay", "SecurityDelay", "LateAircraftDelay"]), "pk_retraso_causa")
    if dim_rc is not None and "fk_retraso_causa" in fact.columns:
        fact = fact.merge(dim_rc, left_on="fk_retraso_causa", right_on="pk_retraso_causa", how="left")

    dim_dev = _norm_pk(_safe_read(bucket, "dim_desvio", ["pk_desvio", "DivArrDelay", "DivDistance", "Div1Airport"]), "pk_desvio")
    if dim_dev is not None and "fk_desvio" in fact.columns:
        fact = fact.merge(dim_dev, left_on="fk_desvio", right_on="pk_desvio", how="left")

    # Guardar en cache
    _fact_cache["df"] = fact
    _fact_cache["bucket"] = bucket
    _fact_cache["expires"] = time.time() + _FACT_TTL
    return fact.copy()


def load_enriched_fact(
    filtros: Optional[dict] = None,
    bucket: str = MINIO_BUCKET_DIMS,
) -> pd.DataFrame:
    """
    Retorna fact_vuelo enriquecido con dimensiones (de cache TTL 10 min).
    filtros: {year, month, airline, origin, dest, ruta}
    """
    fact = _load_base_fact(bucket)

    if not filtros:
        return fact

    # Aplicar filtros sobre la copia cacheada
    if filtros.get("year") and "Year" in fact.columns:
        fact = fact[fact["Year"] == int(filtros["year"])]
    if filtros.get("month") and "Month" in fact.columns:
        fact = fact[fact["Month"] == int(filtros["month"])]
    if filtros.get("airline") and "Reporting_Airline" in fact.columns:
        fact = fact[fact["Reporting_Airline"] == filtros["airline"]]
    if filtros.get("origin") and "OriginCode" in fact.columns:
        fact = fact[fact["OriginCode"] == filtros["origin"]]
    if filtros.get("dest") and "DestCode" in fact.columns:
        fact = fact[fact["DestCode"] == filtros["dest"]]
    if filtros.get("ruta") and "OriginCode" in fact.columns and "DestCode" in fact.columns:
        parts = filtros["ruta"].split("-")
        if len(parts) == 2:
            fact = fact[(fact["OriginCode"] == parts[0]) & (fact["DestCode"] == parts[1])]
    if filtros.get("quarter") and "Quarter" in fact.columns:
        fact = fact[fact["Quarter"] == int(filtros["quarter"])]
    if filtros.get("dow") and "DayOfWeek" in fact.columns:
        fact = fact[fact["DayOfWeek"] == int(filtros["dow"])]
    if filtros.get("solo_cancelados") and "Cancelled" in fact.columns:
        fact = fact[fact["Cancelled"] == 1]
    if filtros.get("cancel_code") and "CancellationCode" in fact.columns:
        fact = fact[fact["CancellationCode"] == str(filtros["cancel_code"])]

    return fact


def load_agg(
    name: str,
    filtros: Optional[dict] = None,
    bucket: str = MINIO_BUCKET_DIMS,
) -> pd.DataFrame:
    """Lee una tabla de agregación pre-computada desde MinIO con cache TTL 10 min.
    filtros: {year, month, airline} — sólo se aplican si la columna existe en el df.
    """
    key = f"{bucket}:{name}"
    entry = _agg_cache.get(key)
    if entry and time.time() < entry["expires"]:
        df = entry["df"].copy()
    else:
        df = _desnormalizar(read_parquet(bucket, name).copy())
        _agg_cache[key] = {"df": df, "expires": time.time() + _AGG_TTL}
        df = df.copy()

    if not filtros:
        return df

    if filtros.get("year") and "year" in df.columns:
        df = df[df["year"] == int(filtros["year"])]
    if filtros.get("month") and "month" in df.columns:
        df = df[df["month"] == int(filtros["month"])]
    if filtros.get("airline") and "carrier" in df.columns:
        df = df[df["carrier"] == filtros["airline"]]

    return df


def get_aerolinas(bucket: str = MINIO_BUCKET_DIMS) -> list[str]:
    key = f"aerolinas:{bucket}"
    entry = _dim_cache.get(key)
    if entry and time.time() < entry["expires"]:
        return entry["data"]
    try:
        df = read_parquet(bucket, "dim_aerolinea")
        col = "Reporting_Airline"
        if col in df.columns:
            result = sorted(df[col].dropna().unique().tolist())
            _dim_cache[key] = {"data": result, "expires": time.time() + _DIM_TTL}
            return result
    except Exception:
        pass
    return []


def get_origins(bucket: str = MINIO_BUCKET_DIMS) -> list[str]:
    key = f"origins:{bucket}"
    entry = _dim_cache.get(key)
    if entry and time.time() < entry["expires"]:
        return entry["data"]
    try:
        df = read_parquet(bucket, "dim_ruta")
        if "OriginCode" in df.columns:
            result = sorted(df["OriginCode"].dropna().unique().tolist())
            _dim_cache[key] = {"data": result, "expires": time.time() + _DIM_TTL}
            return result
    except Exception:
        pass
    return []


def get_dests(bucket: str = MINIO_BUCKET_DIMS) -> list[str]:
    key = f"dests:{bucket}"
    entry = _dim_cache.get(key)
    if entry and time.time() < entry["expires"]:
        return entry["data"]
    try:
        df = read_parquet(bucket, "dim_ruta")
        if "DestCode" in df.columns:
            result = sorted(df["DestCode"].dropna().unique().tolist())
            _dim_cache[key] = {"data": result, "expires": time.time() + _DIM_TTL}
            return result
    except Exception:
        pass
    return []


def get_years(bucket: str = MINIO_BUCKET_DIMS) -> list[int]:
    key = f"years:{bucket}"
    entry = _dim_cache.get(key)
    if entry and time.time() < entry["expires"]:
        return entry["data"]
    try:
        df = read_parquet(bucket, "dim_tiempo")
        if "Year" in df.columns:
            result = sorted(df["Year"].dropna().unique().astype(int).tolist())
            _dim_cache[key] = {"data": result, "expires": time.time() + _DIM_TTL}
            return result
    except Exception:
        pass
    return []
