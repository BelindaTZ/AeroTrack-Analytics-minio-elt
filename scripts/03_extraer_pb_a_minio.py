"""
AeroTrack Analytics — Script 03: Extraer PocketBase → Parquet → MinIO
=======================================================================
Qué hace:
  1. EXTRACT  → Extrae todos los registros de PocketBase en PARALELO
               (workers simultáneos, ~10× más rápido que secuencial)
               *** Escritura incremental por lotes → sin OOM Kill ***
  2. LOAD     → Convierte los datos a formato Parquet (por lotes a disco)
  3. UPLOAD   → Sube el Parquet al bucket 'aerotrack-raw' en MinIO
 
Rendimiento esperado con 2M registros / 4000 páginas:
  Secuencial (1 worker):  ~60-90 minutos
  Concurrente (6 workers): ~8-12 minutos
 
Cambio clave v2:
  - Se eliminaron las 3 copias simultáneas del dataset en RAM
  - Ahora escribe a Parquet por lotes (BATCH_SIZE páginas a la vez)
  - Pico de memoria: ~200-400 MB en lugar de 3-4 GB
  - Elimina el error: return code -9 (OOM Kill)
 
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
import pyarrow as pa
import pyarrow.parquet as pq
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
BATCH_SIZE      = 200   # páginas acumuladas antes de escribir a disco (~100k registros)
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
 
 
# ── HELPERS ───────────────────────────────────────────────────
 
def _limpiar_registros(items: list) -> list:
    """Elimina campos internos de PocketBase."""
    return [
        {k: v for k, v in r.items() if k not in _CAMPOS_INTERNOS}
        for r in items
    ]
 
 
def _escribir_batch(items: list, writer_ref: list) -> None:
    """
    Convierte un lote de registros a DataFrame y lo escribe en el
    ParquetWriter existente (o lo crea si es el primer batch).
    writer_ref es una lista de 1 elemento para permitir mutación.
    """
    df_batch = pd.DataFrame(_limpiar_registros(items))
 
    # Optimizar columnas de baja cardinalidad
    for col in df_batch.select_dtypes(include="object").columns:
        if df_batch[col].nunique() < 500:
            df_batch[col] = df_batch[col].astype("category")
 
    table = pa.Table.from_pandas(df_batch, preserve_index=False)
 
    if writer_ref[0] is None:
        writer_ref[0] = pq.ParquetWriter(
            PARQUET_LOCAL, table.schema, compression="snappy"
        )
 
    writer_ref[0].write_table(table)
 
 
# ── PASO 1: EXTRACT + WRITE INCREMENTAL ───────────────────────
 
def extraer_de_pocketbase() -> Path:
    """
    Extrae TODOS los registros con MAX_WORKERS en paralelo y los escribe
    a Parquet de forma incremental (por lotes) para evitar el OOM Kill.
    """
    print(f"\n[PASO 1] Extrayendo datos de PocketBase (concurrente, {MAX_WORKERS} workers)...")
    print(f"  URL: {PB_BASE_URL} | Colección: {PB_COLLECTION}")
 
    token   = autenticar_pb()
    headers = {"Authorization": token}
    url     = f"{PB_BASE_URL}/api/collections/{PB_COLLECTION}/records"
 
    # Primera solicitud: obtiene totalItems y totalPages
    resp = requests.get(
        url, headers=headers,
        params={"page": 1, "perPage": PB_PAGE_SIZE},
        timeout=30,
    )
    resp.raise_for_status()
    data        = resp.json()
    total_items = data.get("totalItems", 0)
    total_pages = data.get("totalPages", 1)
    primera_pag = data.get("items", [])
 
    if total_items == 0:
        print("  ⚠️  Colección vacía.")
        return PARQUET_LOCAL
 
    print(
        f"  {total_items:,} registros | {total_pages:,} páginas | "
        f"{MAX_WORKERS} workers | lotes de {BATCH_SIZE} páginas (~{BATCH_SIZE * PB_PAGE_SIZE:,} registros)"
    )
 
    # writer_ref[0] se inicializa con el primer batch (necesitamos el schema)
    writer_ref   = [None]
    buffer       = list(primera_pag)   # buffer en RAM (se vacía cada BATCH_SIZE páginas)
    completadas  = 1
    registros_ok = len(primera_pag)
    batches_escritos = 0
    lock         = threading.Lock()
 
    args_lista = [(p, url, headers, PB_PAGE_SIZE) for p in range(2, total_pages + 1)]
 
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futuros = {executor.submit(_fetch_pagina, a): a[0] for a in args_lista}
 
        for futuro in as_completed(futuros):
            num_pag, items = futuro.result()
 
            with lock:
                buffer.extend(items)
                completadas  += 1
                registros_ok += len(items)
 
                # Cada BATCH_SIZE páginas → escribir a disco y liberar RAM
                if len(buffer) >= BATCH_SIZE * PB_PAGE_SIZE:
                    _escribir_batch(buffer, writer_ref)
                    buffer.clear()
                    batches_escritos += 1
                    print(
                        f"  📦 Batch {batches_escritos} escrito | "
                        f"Páginas: {completadas:,}/{total_pages:,} | "
                        f"Registros: {registros_ok:,}/{total_items:,}",
                        flush=True,
                    )
 
                elif completadas % 100 == 0:
                    print(
                        f"  Páginas: {completadas:,}/{total_pages:,} | "
                        f"Registros: {registros_ok:,}/{total_items:,}",
                        flush=True,
                    )
 
    # Escribir lo que quedó en el buffer (último lote parcial)
    if buffer:
        _escribir_batch(buffer, writer_ref)
        buffer.clear()
        batches_escritos += 1
        print(f"  📦 Batch final ({batches_escritos}) escrito", flush=True)
 
    if writer_ref[0]:
        writer_ref[0].close()
 
    tamanio_mb = PARQUET_LOCAL.stat().st_size / (1024 * 1024)
    print(f"\n  ✅ {registros_ok:,} registros extraídos y guardados en Parquet")
    print(f"  Archivo: {PARQUET_LOCAL} ({tamanio_mb:.1f} MB) | {batches_escritos} batches escritos")
    return PARQUET_LOCAL
 
 
# ── PASO 2: SUBIR A MINIO ─────────────────────────────────────
 
def subir_a_minio(parquet_path: Path) -> None:
    print(f"\n[PASO 2] Subiendo a MinIO ({MINIO_ENDPOINT})...")
 
    cliente = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS,
        secret_key=MINIO_SECRET,
        secure=False,
    )
 
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
    print("  AeroTrack Analytics — Extract → Parquet → MinIO  v2")
    print("=" * 60)
    inicio_total = datetime.now()
 
    try:
        parquet_path = extraer_de_pocketbase()
 
        if not parquet_path.exists() or parquet_path.stat().st_size == 0:
            print("\n⚠️  No hay registros en PocketBase.")
            print("   Ejecuta primero: python scripts/02_cargar_csv_a_pb.py")
            sys.exit(1)
 
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
