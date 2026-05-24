"""
AeroTrack Analytics — Script 03: Extraer PocketBase → Parquet → MinIO
=======================================================================
Qué hace:
  1. EXTRACT  → Extrae todos los registros de PocketBase en PARALELO
               (10 workers simultáneos, ~10× más rápido que secuencial)
  2. LOAD     → Convierte los datos a formato Parquet (temporal)
  3. UPLOAD   → Sube el Parquet al bucket 'aerotrack-raw' en MinIO

Rendimiento esperado con 2M registros / 4000 páginas:
  Secuencial (1 worker):  ~60-90 minutos
  Concurrente (10 workers): ~6-10 minutos

Cómo ejecutar:
    python scripts/03_extraer_pb_a_minio.py
"""

import os
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from minio import Minio

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
MINIO_OBJETO    = "vuelos_raw.parquet"

PB_PAGE_SIZE    = 500
MAX_WORKERS     = 10
MAX_REINTENTOS  = 3
PARQUET_LOCAL   = Path(tempfile.gettempdir()) / "vuelos_raw.parquet"
_CAMPOS_INTERNOS = {"id", "collectionId", "collectionName", "created", "updated"}


# ── AUTENTICACIÓN ─────────────────────────────────────────────

def autenticar_pb() -> str:
    resp = requests.post(
        f"{PB_BASE_URL}/api/admins/auth-with-password",
        json={"identity": PB_EMAIL, "password": PB_PASSWORD},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["token"]


# ── WORKER: descarga una página ───────────────────────────────

def _fetch_pagina(args: tuple) -> tuple[int, list]:
    """Descarga una sola página de PocketBase con reintentos."""
    num_pagina, url, headers, page_size = args
    for intento in range(MAX_REINTENTOS):
        try:
            resp = requests.get(
                url,
                headers=headers,
                params={"page": num_pagina, "perPage": page_size, "skipTotal": 1},
                timeout=30,
            )
            resp.raise_for_status()
            return num_pagina, resp.json().get("items", [])
        except Exception:
            if intento == MAX_REINTENTOS - 1:
                raise
            time.sleep(1 * (intento + 1))
    return num_pagina, []


# ── PASO 1: EXTRACT (concurrente) ─────────────────────────────

def extraer_de_pocketbase() -> pd.DataFrame:
    """Extrae TODOS los registros con 10 workers en paralelo."""
    print(f"\n[PASO 1] Extrayendo datos de PocketBase (concurrente, {MAX_WORKERS} workers)...")
    print(f"  URL: {PB_BASE_URL} | Colección: {PB_COLLECTION}")

    token   = autenticar_pb()
    headers = {"Authorization": token}
    url     = f"{PB_BASE_URL}/api/collections/{PB_COLLECTION}/records"

    # Primera solicitud: obtiene totalItems y totalPages (sin skipTotal para el COUNT)
    resp = requests.get(url, headers=headers, params={"page": 1, "perPage": PB_PAGE_SIZE}, timeout=30)
    resp.raise_for_status()
    data         = resp.json()
    total_items  = data.get("totalItems", 0)
    total_pages  = data.get("totalPages", 1)
    primera_pag  = data.get("items", [])

    if total_items == 0:
        print("  ⚠️  Colección vacía.")
        return pd.DataFrame()

    print(f"  {total_items:,} registros | {total_pages:,} páginas | {MAX_WORKERS} workers → ~{total_pages // MAX_WORKERS} rondas")

    # Resultado de página 1 ya disponible; descargar 2..N concurrentemente
    resultados: dict[int, list] = {1: primera_pag}
    completadas   = 1
    registros_ok  = len(primera_pag)
    lock          = threading.Lock()

    args_lista = [(p, url, headers, PB_PAGE_SIZE) for p in range(2, total_pages + 1)]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futuros = {executor.submit(_fetch_pagina, a): a[0] for a in args_lista}
        for futuro in as_completed(futuros):
            num_pag, items = futuro.result()
            resultados[num_pag] = items       # seguro: cada clave es única
            with lock:
                completadas  += 1
                registros_ok += len(items)
                if completadas % 100 == 0 or completadas == total_pages:
                    print(
                        f"  Páginas completadas: {completadas:,}/{total_pages:,} "
                        f"| Registros: {registros_ok:,}/{total_items:,}",
                        flush=True,
                    )

    # Reensamblar en orden de página para garantizar secuencia correcta
    todos_los_registros = []
    for p in sorted(resultados.keys()):
        todos_los_registros.extend(resultados[p])

    total = len(todos_los_registros)
    print(f"  ✅ {total:,} registros extraídos")

    registros_limpios = [
        {k: v for k, v in r.items() if k not in _CAMPOS_INTERNOS}
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

    duracion = max((datetime.now() - inicio).seconds, 1)
    vel_mb   = (tamanio / (1024 * 1024)) / duracion
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
