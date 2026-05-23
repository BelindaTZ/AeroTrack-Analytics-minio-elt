# minio_client.py — Operaciones de lectura/escritura sobre MinIO + Parquet

import io
import pandas as pd
from minio import Minio
from minio.error import S3Error
from config import MINIO_ENDPOINT, MINIO_ACCESS, MINIO_SECRET, MINIO_BUCKET, SECURE


def get_client() -> Minio:
    """Retorna una instancia del cliente MinIO."""
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS,
        secret_key=MINIO_SECRET,
        secure=SECURE,
    )


def read_parquet(tabla: str) -> pd.DataFrame:
    """
    Descarga el archivo Parquet de MinIO y lo retorna como DataFrame.
    Lanza FileNotFoundError si el objeto no existe en el bucket.
    """
    client = get_client()
    object_name = f"{tabla}.parquet"
    try:
        response = client.get_object(MINIO_BUCKET, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        df = pd.read_parquet(io.BytesIO(data))
        # pyarrow devuelve arrays read-only; copy() los hace escribibles
        return df.copy()
    except S3Error as exc:
        if exc.code in ("NoSuchKey", "NoSuchBucket"):
            raise FileNotFoundError(
                f"El archivo '{object_name}' no existe en el bucket '{MINIO_BUCKET}'."
            ) from exc
        raise RuntimeError(f"Error de MinIO al leer '{object_name}': {exc}") from exc


def write_parquet(tabla: str, df: pd.DataFrame) -> None:
    """
    Serializa el DataFrame a Parquet y lo sube a MinIO.
    """
    client = get_client()
    object_name = f"{tabla}.parquet"
    try:
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=False, engine="pyarrow")
        buffer.seek(0)
        size = buffer.getbuffer().nbytes
        client.put_object(
            MINIO_BUCKET,
            object_name,
            buffer,
            length=size,
            content_type="application/octet-stream",
        )
    except S3Error as exc:
        raise RuntimeError(f"Error de MinIO al escribir '{object_name}': {exc}") from exc
