"""Operaciones MinIO reutilizables para todos los módulos."""

import io
from typing import Optional

import pandas as pd
import urllib3
from minio import Minio
from minio.error import S3Error

from app.config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY

# Timeout para operaciones de red hacia MinIO.
# Sin timeout, response.read() bloquea indefinidamente si MinIO tiene lentitud
# o el objeto fue escrito parcialmente (parquet truncado), dejando la app colgada.
_HTTP_CLIENT = urllib3.PoolManager(
    timeout=urllib3.util.Timeout(connect=5, read=60),
    maxsize=10,
)


def get_client() -> Minio:
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
        http_client=_HTTP_CLIENT,
    )


def read_parquet(bucket: str, tabla: str) -> pd.DataFrame:
    client = get_client()
    obj_name = f"{tabla}.parquet"
    try:
        response = client.get_object(bucket, obj_name)
        data = response.read()
        response.close()
        response.release_conn()
        return pd.read_parquet(io.BytesIO(data)).copy()
    except S3Error as exc:
        if exc.code in ("NoSuchKey", "NoSuchBucket"):
            raise FileNotFoundError(f"'{obj_name}' no existe en bucket '{bucket}'.") from exc
        raise RuntimeError(f"Error MinIO al leer '{obj_name}': {exc}") from exc
    except FileNotFoundError:
        raise
    except Exception as exc:
        # Incluye ReadTimeoutError, ProtocolError, ArrowInvalid (parquet truncado), etc.
        raise RuntimeError(f"Error al leer '{obj_name}' desde '{bucket}': {exc}") from exc


def write_parquet(bucket: str, tabla: str, df: pd.DataFrame) -> None:
    client = get_client()
    obj_name = f"{tabla}.parquet"
    try:
        buf = io.BytesIO()
        df.to_parquet(buf, index=False, engine="pyarrow")
        buf.seek(0)
        client.put_object(bucket, obj_name, buf, length=buf.getbuffer().nbytes,
                          content_type="application/octet-stream")
    except S3Error as exc:
        raise RuntimeError(f"Error MinIO al escribir '{obj_name}': {exc}") from exc


def stat_parquet(bucket: str, tabla: str) -> Optional[dict]:
    """Retorna {size_mb, modified} o None si el objeto no existe."""
    client = get_client()
    obj_name = f"{tabla}.parquet"
    try:
        stat = client.stat_object(bucket, obj_name)
        return {
            "size_mb": round(stat.size / 1_048_576, 2),
            "modified": stat.last_modified,
        }
    except S3Error:
        return None


def list_bucket(bucket: str) -> list[dict]:
    """Lista objetos de un bucket como [{name, size_mb, modified}]."""
    client = get_client()
    try:
        return [
            {"name": obj.object_name, "size_mb": round(obj.size / 1_048_576, 2), "modified": obj.last_modified}
            for obj in client.list_objects(bucket)
        ]
    except S3Error:
        return []
