"""
AeroTrack Analytics — Script 03: Extraer PocketBase → Parquet → MinIO
=======================================================================
Qué hace:
  1. EXTRACT  → Extrae todos los registros de PocketBase con paginación
  2. LOAD     → Convierte los datos a formato Parquet (temporal)
  3. UPLOAD   → Sube el Parquet al bucket 'aerotrack-raw' en MinIO

Cómo ejecutar:
    python scripts/03_extraer_pb_a_minio.py
"""

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from minio import Minio
from minio.error import S3Error

sys.path.insert(0, os.path.dirname(__file__))
import config

PB_BASE_URL     = config.PB_BASE_URL
PB_EMAIL        = config.PB_EMAIL
PB_PASSWORD     = config.PB_PASSWORD
PB_COLLECTION   = config.PB_COLLECTION
MINIO_ENDPOINT  = config.MINIO_ENDPOINT
MINIO_ACCESS    = config.MINIO_ACCESS
MINIO_SECRET    = config.MINIO_SECRET
MINIO_BUCKET    = config.MINIO_BUCKET_RAW
MINIO_OBJETO    = "vuelos_raw.parquet"   # aerotrack-raw/vuelos_raw.parquet

PB_PAGE_SIZE    = 500
PARQUET_LOCAL   = Path(tempfile.gettempdir()) / "vuelos_raw.parquet"


# ── PASO 1: EXTRACT ───────────────────────────────────────────

def autenticar_pb() -> str:
    resp = requests.post(
        f"{PB_BASE_URL}/api/admins/auth-with-password",
        json={"identity": PB_EMAIL, "password": PB_PASSWORD},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def extraer_de_pocketbase() -> pd.DataFrame:
    """Extrae TODOS los registros de PocketBase usando paginación."""
    print("\n[PASO 1] Extrayendo datos de PocketBase...")
    print(f"  URL: {PB_BASE_URL} | Colección: {PB_COLLECTION}")
    token   = autenticar_pb()
    headers = {"Authorization": token}
    url     = f"{PB_BASE_URL}/api/collections/{PB_COLLECTION}/records"

    todos_los_registros = []
    pagina = 1

    while True:
        params = {"page": pagina, "perPage": PB_PAGE_SIZE, "skipTotal": 1}
        resp   = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        items = resp.json().get("items", [])

        if not items:
            break

        todos_los_registros.extend(items)

        if pagina % 20 == 0 or len(items) < PB_PAGE_SIZE:
            print(f"  Página {pagina:,} | Total acumulado: {len(todos_los_registros):,}")

        if len(items) < PB_PAGE_SIZE:
            break

        pagina += 1

        if pagina % 500 == 0:
            print("  Renovando token de autenticación...")
            token   = autenticar_pb()
            headers = {"Authorization": token}

    total = len(todos_los_registros)
    print(f"  ✅ {total:,} registros extraídos")

    if total == 0:
        return pd.DataFrame()

    campos_internos = {"id", "collectionId", "collectionName", "created", "updated"}
    registros_limpios = [
        {k: v for k, v in r.items() if k not in campos_internos}
        for r in todos_los_registros
    ]
    df = pd.DataFrame(registros_limpios)
    print(f"  DataFrame: {df.shape[0]:,} filas × {df.shape[1]} columnas")
    return df


# ── PASO 2: CONVERTIR A PARQUET ───────────────────────────────

def convertir_a_parquet(df: pd.DataFrame) -> Path:
    print(f"\n[PASO 2] Convirtiendo a Parquet...")

    for col in df.select_dtypes(include="object").columns:
        if df[col].nunique() < 500:
            df[col] = df[col].astype("category")

    df.to_parquet(PARQUET_LOCAL, engine="pyarrow", compression="snappy", index=False)

    tamanio_mb = PARQUET_LOCAL.stat().st_size / (1024 * 1024)
    print(f"  ✅ Guardado: {PARQUET_LOCAL} ({tamanio_mb:.1f} MB)")
    return PARQUET_LOCAL


# ── PASO 3: SUBIR A MINIO ─────────────────────────────────────

def subir_a_minio(parquet_path: Path) -> None:
    print(f"\n[PASO 3] Subiendo a MinIO ({MINIO_ENDPOINT})...")

    cliente = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS, secret_key=MINIO_SECRET, secure=False)

    if not cliente.bucket_exists(MINIO_BUCKET):
        cliente.make_bucket(MINIO_BUCKET)
        print(f"  Bucket '{MINIO_BUCKET}' creado")
    else:
        print(f"  Bucket '{MINIO_BUCKET}' ya existe")

    tamanio = parquet_path.stat().st_size
    inicio  = datetime.now()

    cliente.fput_object(
        bucket_name=MINIO_BUCKET,
        object_name=MINIO_OBJETO,
        file_path=str(parquet_path),
        content_type="application/octet-stream",
    )

    duracion   = max((datetime.now() - inicio).seconds, 1)
    vel_mb     = (tamanio / (1024 * 1024)) / duracion

    print(f"  ✅ Subido a: s3://{MINIO_BUCKET}/{MINIO_OBJETO}")
    print(f"  Velocidad: {vel_mb:.1f} MB/s | Consola: http://localhost:9001")


def limpiar_temporal() -> None:
    if PARQUET_LOCAL.exists():
        PARQUET_LOCAL.unlink()


# ── ORQUESTADOR ───────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("  AeroTrack Analytics — Extract → Parquet → MinIO")
    print("=" * 60)
    inicio_total = datetime.now()

    try:
        df = extraer_de_pocketbase()

        if df.empty:
            print("\n⚠️  No hay registros en PocketBase.")
            print("   Ejecuta primero: python scripts/02_cargar_csv_a_pb.py")
            sys.exit(1)

        parquet_path = convertir_a_parquet(df)
        subir_a_minio(parquet_path)

    finally:
        limpiar_temporal()

    duracion_total = (datetime.now() - inicio_total).seconds
    print(f"\n{'=' * 60}")
    print(f"  ✅ PIPELINE COMPLETADO en {duracion_total} segundos")
    print(f"  Próximo paso: configura el DAG en Airflow: http://localhost:8080")
    print("=" * 60)


if __name__ == "__main__":
    main()
