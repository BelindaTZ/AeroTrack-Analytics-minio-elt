"""Live stats for the login page left panel."""

import asyncio
import io
import logging
import time

import httpx
import pandas as pd
import pyarrow.parquet as pq

from app.config import (
    AIRFLOW_URL,
    MINIO_ACCESS_KEY,
    MINIO_BUCKET_DIMS,
    MINIO_ENDPOINT,
    MINIO_SECRET_KEY,
    PB_URL,
)

_log = logging.getLogger(__name__)
_TIMEOUT = 2.0
_CACHE_TTL = 60
_cache: dict = {"data": None, "ts": 0.0}


def _fmt(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def _fetch_vuelos_sync() -> str:
    from minio import Minio
    try:
        mc = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY,
                   secret_key=MINIO_SECRET_KEY, secure=False)
        resp = mc.get_object(MINIO_BUCKET_DIMS, "fact_vuelo.parquet")
        data = resp.read()
        resp.close()
        resp.release_conn()
        meta = pq.read_metadata(io.BytesIO(data))
        return _fmt(meta.num_rows)
    except Exception as e:
        _log.warning("login_stats fact_vuelo: %s", e)
        return "—"


async def _check_url(client: httpx.AsyncClient, url: str) -> bool:
    try:
        r = await client.get(url)
        return r.status_code < 500
    except Exception:
        return False


async def _fetch_disponibilidad() -> str:
    urls = [
        f"{PB_URL}/api/health",
        f"http://{MINIO_ENDPOINT}/minio/health/live",
        f"{AIRFLOW_URL}/health",
    ]
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        results = await asyncio.gather(*(_check_url(client, u) for u in urls))
    up = 1 + sum(results)  # +1: FastAPI is up if this code runs
    return f"{up * 25}%"


def _fetch_aerolineas_sync() -> str:
    from minio import Minio
    try:
        mc = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY,
                   secret_key=MINIO_SECRET_KEY, secure=False)
        resp = mc.get_object(MINIO_BUCKET_DIMS, "dim_aerolinea.parquet")
        data = resp.read()
        resp.close()
        resp.release_conn()
        df = pd.read_parquet(io.BytesIO(data))
        count = int((df["pk"] != 0).sum()) if "pk" in df.columns else len(df)
        return str(count)
    except Exception:
        return "—"


async def get_login_stats() -> dict:
    now = time.monotonic()
    if _cache["data"] and now - _cache["ts"] < _CACHE_TTL:
        return _cache["data"]

    vuelos, disponibilidad, aerolineas = await asyncio.gather(
        asyncio.to_thread(_fetch_vuelos_sync),
        _fetch_disponibilidad(),
        asyncio.to_thread(_fetch_aerolineas_sync),
    )
    data = {"vuelos": vuelos, "disponibilidad": disponibilidad, "aerolineas": aerolineas}
    _cache["data"] = data
    _cache["ts"] = now
    return data
