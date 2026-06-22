"""
AeroTrack Analytics — Funciones del pipeline para el DAG de Airflow
====================================================================
Este módulo expone las tres funciones del pipeline ELT:
  - extract_pipeline(): PocketBase → Parquet local
  - load_pipeline():    Parquet local → MinIO (aerotrack-raw)
  - transform_pipeline(): aerotrack-raw → modelo estrella → aerotrack-dims

Al estar en dags/, Airflow lo importa directamente sin necesidad de
montar el directorio scripts/. Las URLs/credenciales las gestiona
config.py (también en dags/) que detecta automáticamente el contexto Docker.

CAMBIO v2 — extract_pipeline():
  - Escritura incremental a Parquet por lotes (BATCH_SIZE páginas)
  - Pico de memoria: ~200-400 MB en lugar de 3-4 GB
  - Elimina el error: return code -9 (OOM Kill)

CAMBIO v3 — separación E / L / T:
  - extract_pipeline() devuelve la ruta del Parquet local (str)
  - load_pipeline(parquet_path) sube ese archivo a MinIO y lo elimina
"""
 
from __future__ import annotations
 
import os
import tempfile
from datetime import datetime, timedelta, timezone

_TZ = timezone(timedelta(hours=-5))  # America/Guayaquil — sin DST
from pathlib import Path
 
 
# ═══════════════════════════════════════════════════════════════
# EXTRACT: PocketBase → Parquet → MinIO
# ═══════════════════════════════════════════════════════════════
 
def extract_pipeline() -> str:
    """Extrae todos los registros de PocketBase y los convierte a Parquet
    de forma incremental (sin OOM Kill). Devuelve la ruta del archivo
    local para que la tarea load lo suba a MinIO."""
 
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed
 
    import pyarrow as pa
    import pyarrow.parquet as pq
    import requests

    import config

    PB_BASE_URL     = config.PB_BASE_URL
    PB_EMAIL        = config.PB_EMAIL
    PB_PASSWORD     = config.PB_PASSWORD
    PB_COLLECTION   = config.PB_COLLECTION
 
    PB_PAGE_SIZE    = 500
    MAX_WORKERS     = 10
    MAX_REINTENTOS  = 3
    BATCH_SIZE      = 200   # páginas por lote → ~100k registros por escritura a disco
    CAMPOS_INTERNOS = {"id", "collectionId", "collectionName", "created", "updated"}
 
    parquet_tmp = Path(tempfile.gettempdir()) / f"vuelos_raw_{datetime.now(_TZ).strftime('%Y%m%d_%H%M%S')}.parquet"
 
    print(f"[EXTRACT] PocketBase: {PB_BASE_URL} | Colección: {PB_COLLECTION} | {MAX_WORKERS} workers")
 
    # ── 1. Autenticar ─────────────────────────────────────────
    def autenticar():
        resp = requests.post(
            f"{PB_BASE_URL}/api/admins/auth-with-password",
            json={"identity": PB_EMAIL, "password": PB_PASSWORD},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["token"]
 
    token   = autenticar()
    headers = {"Authorization": token}
    url     = f"{PB_BASE_URL}/api/collections/{PB_COLLECTION}/records"
 
    # ── 2. Primera solicitud: totalItems y totalPages ─────────
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
        raise RuntimeError("No hay registros en PocketBase. Ejecuta primero el setup inicial.")
 
    print(
        f"[EXTRACT] {total_items:,} registros | {total_pages:,} páginas | "
        f"lotes de {BATCH_SIZE} páginas (~{BATCH_SIZE * PB_PAGE_SIZE:,} registros)"
    )
 
    # ── 3. Worker que descarga una página con reintentos ──────
    def fetch_pagina(args):
        num_pagina, _url, _headers, page_size = args
        for intento in range(MAX_REINTENTOS):
            try:
                r = requests.get(
                    _url,
                    headers=_headers,
                    params={"page": num_pagina, "perPage": page_size, "skipTotal": 1},
                    timeout=30,
                )
                r.raise_for_status()
                return num_pagina, r.json().get("items", [])
            except Exception:
                if intento == MAX_REINTENTOS - 1:
                    raise
                time.sleep(1 * (intento + 1))
        return num_pagina, []
 
    # ── 4. Helper: limpiar y escribir un lote a Parquet ───────
    def limpiar(items):
        return [
            {k: v for k, v in r.items() if k not in CAMPOS_INTERNOS}
            for r in items
        ]
 
    def escribir_batch(items, writer_ref):
        """Escribe un lote en el ParquetWriter. Lo crea si es el primero."""
        import pandas as pd
 
        df_batch = pd.DataFrame(limpiar(items))
        for col in df_batch.select_dtypes(include="object").columns:
            if df_batch[col].nunique() < 500:
                df_batch[col] = df_batch[col].astype("category")
 
        table = pa.Table.from_pandas(df_batch, preserve_index=False)
 
        if writer_ref[0] is None:
            writer_ref[0] = pq.ParquetWriter(
                parquet_tmp, table.schema, compression="snappy"
            )
        writer_ref[0].write_table(table)
 
    # ── 5. Descargar páginas concurrentemente + escritura incremental ──
    # writer_ref es lista de 1 elemento para permitir mutación en closure
    writer_ref      = [None]
    buffer          = list(primera_pag)   # buffer en RAM (se vacía cada BATCH_SIZE páginas)
    completadas     = 1
    registros_ok    = len(primera_pag)
    batches_escritos = 0
    lock            = threading.Lock()
 
    args_lista = [(p, url, headers, PB_PAGE_SIZE) for p in range(2, total_pages + 1)]
 
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futuros = {executor.submit(fetch_pagina, a): a[0] for a in args_lista}
 
        for futuro in as_completed(futuros):
            num_pag, items = futuro.result()
 
            with lock:
                buffer.extend(items)
                completadas  += 1
                registros_ok += len(items)
 
                # Cada BATCH_SIZE páginas → escribir a disco y liberar RAM
                if len(buffer) >= BATCH_SIZE * PB_PAGE_SIZE:
                    escribir_batch(buffer, writer_ref)
                    buffer.clear()
                    batches_escritos += 1
                    print(
                        f"[EXTRACT] 📦 Batch {batches_escritos} escrito | "
                        f"Páginas: {completadas:,}/{total_pages:,} | "
                        f"Registros: {registros_ok:,}/{total_items:,}",
                        flush=True,
                    )
 
                elif completadas % 100 == 0 or completadas == total_pages:
                    print(
                        f"[EXTRACT] Páginas: {completadas:,}/{total_pages:,} | "
                        f"Registros: {registros_ok:,}/{total_items:,}",
                        flush=True,
                    )
 
    # Escribir el último lote parcial
    if buffer:
        escribir_batch(buffer, writer_ref)
        buffer.clear()
        batches_escritos += 1
        print(f"[EXTRACT] 📦 Batch final ({batches_escritos}) escrito", flush=True)
 
    if writer_ref[0]:
        writer_ref[0].close()

    tam_mb = parquet_tmp.stat().st_size / (1024 * 1024)
    print(f"[EXTRACT] ✅ {registros_ok:,} registros extraídos → {parquet_tmp} ({tam_mb:.1f} MB)")
    return str(parquet_tmp)
 
 
# ═══════════════════════════════════════════════════════════════
# LOAD: Parquet local → MinIO (aerotrack-raw)
# ═══════════════════════════════════════════════════════════════

def load_pipeline(parquet_path: str) -> None:
    """Sube el Parquet extraído a MinIO (aerotrack-raw/vuelos_raw.parquet)
    y elimina el archivo local temporal."""
    from minio import Minio

    import config

    MINIO_ENDPOINT = config.MINIO_ENDPOINT
    MINIO_ACCESS   = config.MINIO_ACCESS
    MINIO_SECRET   = config.MINIO_SECRET
    BUCKET_RAW     = config.MINIO_BUCKET_RAW
    OBJETO_RAW     = "vuelos_raw.parquet"

    parquet_tmp = Path(parquet_path)
    tam_mb = parquet_tmp.stat().st_size / (1024 * 1024)
    print(f"[LOAD] Archivo local: {parquet_tmp} ({tam_mb:.1f} MB)")

    cliente = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS, secret_key=MINIO_SECRET, secure=False)
    if not cliente.bucket_exists(BUCKET_RAW):
        cliente.make_bucket(BUCKET_RAW)
        print(f"[LOAD] Bucket '{BUCKET_RAW}' creado")

    cliente.fput_object(BUCKET_RAW, OBJETO_RAW, str(parquet_tmp), content_type="application/octet-stream")
    parquet_tmp.unlink()

    print(f"[LOAD] ✅ Subido a s3://{BUCKET_RAW}/{OBJETO_RAW}")


# ═══════════════════════════════════════════════════════════════
# TRANSFORM: aerotrack-raw → modelo estrella → aerotrack-dims
# ═══════════════════════════════════════════════════════════════

def transform_pipeline() -> None:
    """Descarga vuelos_raw.parquet desde MinIO, genera el modelo
    estrella (10 dims + fact_vuelo) y sube cada tabla a aerotrack-dims.

    Estrategia de tres pasadas para minimizar pico de RAM:
      PASS 1a (~39 cols) — dims simples: tiempo, aerolinea, avion,
                           retraso, cancelacion, distancia, horario, clasificacion
      PASS 1b (~25 cols) — dims espaciales: aeropuerto, ruta, desvio
      PASS 2  (~30 cols) — fact table: FK sources + métricas
    Pico: max(39, 25, 30) = 39 cols en lugar de 62 (reducción ~37%)
    """
    import os as _os
    import gc
    import pandas as pd
    import pyarrow.parquet as pq
    from minio import Minio
    from minio.error import S3Error

    import config

    MINIO_ENDPOINT = config.MINIO_ENDPOINT
    MINIO_ACCESS   = config.MINIO_ACCESS
    MINIO_SECRET   = config.MINIO_SECRET
    BUCKET_RAW     = config.MINIO_BUCKET_RAW
    BUCKET_DIMS    = config.MINIO_BUCKET_DIMS
    OBJETO_RAW     = "vuelos_raw.parquet"

    print(f"[TRANSFORM] MinIO: {MINIO_ENDPOINT} | {BUCKET_RAW} → {BUCKET_DIMS}")

    client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS, secret_key=MINIO_SECRET, secure=False)

    try:
        client.stat_object(BUCKET_RAW, OBJETO_RAW)
    except S3Error:
        raise RuntimeError(
            f"No encontrado: s3://{BUCKET_RAW}/{OBJETO_RAW}. "
            "Ejecuta primero la tarea extract."
        )

    # ── Helpers ──────────────────────────────────────────────────
    def cols_ok(df, columnas):
        return [c for c in columnas if c in df.columns]

    def subir(df, nombre):
        tmp = tempfile.mktemp(suffix=".parquet")
        df.to_parquet(tmp, engine="pyarrow", compression="snappy", index=False)
        if not client.bucket_exists(BUCKET_DIMS):
            client.make_bucket(BUCKET_DIMS)
        client.fput_object(BUCKET_DIMS, f"{nombre}.parquet", tmp)
        _os.remove(tmp)
        print(f"  ✅ {nombre}: {len(df):,} filas → s3://{BUCKET_DIMS}/{nombre}.parquet")

    def key_str(df, cols):
        result = df[cols[0]].astype(str)
        for col in cols[1:]:
            result = result + "_|_" + df[col].astype(str)
        return result

    # ── Manifiestos de columnas ───────────────────────────────────
    DIM_COLS_A = [
        "FlightDate","Year","Quarter","Month","DayofMonth","DayOfWeek","DepTimeBlk","ArrTimeBlk",
        "Reporting_Airline","IATA_CODE_Reporting_Airline","DOT_ID_Reporting_Airline",
        "Tail_Number","DistanceGroup","Distance",
        "CarrierDelay","WeatherDelay","NASDelay","SecurityDelay","LateAircraftDelay","TotalAddGTime","LongestAddGTime",
        "Cancelled","CancellationCode","Diverted","FirstDepTime",
        "CRSElapsedTime","ActualElapsedTime",
        "CRSDepTime","DepTime","DepDelay","DepDelayMinutes","CRSArrTime","ArrTime","ArrDelay","ArrDelayMinutes",
        "DepDel15","ArrDel15","DepartureDelayGroups","ArrivalDelayGroups",
    ]

    DIM_COLS_B = [
        "OriginAirportID","OriginAirportSeqID","OriginCityMarketID","Origin","OriginCityName","OriginState","OriginStateName","OriginWac",
        "DestAirportID","DestAirportSeqID","DestCityMarketID","Dest","DestCityName","DestState","DestStateName","DestWac",
        "Distance","DistanceGroup",
        "DivAirportLandings","DivReachedDest","DivActualElapsedTime","DivArrDelay","DivDistance","Div1Airport","Div1TailNum",
    ]

    FACT_COLS = [
        "FlightDate","Reporting_Airline","Origin","Dest","Tail_Number",
        "DistanceGroup","CRSDepTime",
        "Cancelled","CancellationCode","Diverted",
        "DepDel15","ArrDel15","DepartureDelayGroups","ArrivalDelayGroups",
        "CarrierDelay","WeatherDelay","NASDelay","SecurityDelay","LateAircraftDelay","TotalAddGTime","LongestAddGTime",
        "DivAirportLandings","Div1Airport",
        "AirTime","Distance","Flights","ActualElapsedTime","CRSElapsedTime","TaxiIn","TaxiOut",
    ]
    METRICAS = ["AirTime","Distance","Flights","ActualElapsedTime","CRSElapsedTime","TaxiIn","TaxiOut"]

    # ── Descargar parquet raw ─────────────────────────────────────
    tmp_raw = tempfile.mktemp(suffix=".parquet")
    client.fget_object(BUCKET_RAW, OBJETO_RAW, tmp_raw)

    avail = set(pq.read_schema(tmp_raw).names)

    def pick(cols):
        seen, result = set(), []
        for c in cols:
            if c in avail and c not in seen:
                seen.add(c); result.append(c)
        return result

    # ════════════════════════════════════════════════════════════
    # PASS 1a — dims simples (tiempo, aerolinea, avion, retraso,
    #            cancelacion, distancia, horario, clasificacion)
    # ════════════════════════════════════════════════════════════
    cols_a = pick(DIM_COLS_A)
    print(f"\n[TRANSFORM] PASS 1a — {len(cols_a)}/{len(avail)} columnas (dims simples)")
    df = pd.read_parquet(tmp_raw, columns=cols_a)
    print(f"  {len(df):,} filas × {len(df.columns)} cols")

    cols_t = cols_ok(df, ["FlightDate","Year","Quarter","Month","DayofMonth","DayOfWeek","DepTimeBlk","ArrTimeBlk"])
    dim_tiempo = df[cols_t].drop_duplicates(subset=["FlightDate"]).reset_index(drop=True)
    dim_tiempo.insert(0, "pk_tiempo", range(1, len(dim_tiempo)+1))
    subir(dim_tiempo, "dim_tiempo")

    cols_al = cols_ok(df, ["Reporting_Airline","IATA_CODE_Reporting_Airline","DOT_ID_Reporting_Airline"])
    dim_aerolinea = df[cols_al].drop_duplicates(subset=["Reporting_Airline"]).reset_index(drop=True)
    dim_aerolinea.insert(0, "pk_aerolinea", range(1, len(dim_aerolinea)+1))
    subir(dim_aerolinea, "dim_aerolinea")

    cols_av = cols_ok(df, ["Tail_Number","DistanceGroup","Distance"])
    dim_avion = df[cols_av].drop_duplicates(subset=["Tail_Number"]).reset_index(drop=True)
    dim_avion.insert(0, "pk_avion", range(1, len(dim_avion)+1))
    subir(dim_avion, "dim_avion")

    cols_rc = cols_ok(df, ["CarrierDelay","WeatherDelay","NASDelay","SecurityDelay","LateAircraftDelay","TotalAddGTime","LongestAddGTime"])
    dim_retraso = df[cols_rc].drop_duplicates().reset_index(drop=True)
    dim_retraso.insert(0, "pk_retraso_causa", range(1, len(dim_retraso)+1))
    dim_retraso["descripcion"] = "Retraso registrado"
    fila_sin = {col: 0 for col in cols_rc}
    fila_sin.update({"pk_retraso_causa": 0, "descripcion": "Sin retraso"})
    dim_retraso = pd.concat([pd.DataFrame([fila_sin]), dim_retraso], ignore_index=True)
    subir(dim_retraso, "dim_retraso_causa")

    cols_can = cols_ok(df, ["Cancelled","CancellationCode","Diverted","FirstDepTime"])
    dim_cancelacion = df[cols_can].drop_duplicates(subset=["Cancelled","CancellationCode","Diverted"]).reset_index(drop=True)
    dim_cancelacion.insert(0, "pk_cancelacion", range(1, len(dim_cancelacion)+1))
    dim_cancelacion["descripcion"] = "Evento registrado"
    fila_normal = {"Cancelled":0,"CancellationCode":"No aplica","Diverted":0,"FirstDepTime":0,"pk_cancelacion":0,"descripcion":"Vuelo normal"}
    dim_cancelacion = pd.concat([pd.DataFrame([fila_normal]), dim_cancelacion], ignore_index=True)
    subir(dim_cancelacion, "dim_cancelacion")

    cols_dis = cols_ok(df, ["Distance","DistanceGroup","CRSElapsedTime","ActualElapsedTime"])
    dim_distancia = df[cols_dis].drop_duplicates(subset=["DistanceGroup"]).reset_index(drop=True)
    dim_distancia.insert(0, "pk_distancia", range(1, len(dim_distancia)+1))
    subir(dim_distancia, "dim_distancia")

    cols_hor = cols_ok(df, ["CRSDepTime","DepTime","DepDelay","DepDelayMinutes","CRSArrTime","ArrTime","ArrDelay","ArrDelayMinutes"])
    dim_horario = df[cols_hor].drop_duplicates(subset=["CRSDepTime"]).reset_index(drop=True)
    dim_horario.insert(0, "pk_horario", range(1, len(dim_horario)+1))
    subir(dim_horario, "dim_horario")

    cols_cl = cols_ok(df, ["DepDel15","ArrDel15","DepartureDelayGroups","ArrivalDelayGroups"])
    dim_clasificacion = df[cols_cl].drop_duplicates().reset_index(drop=True)
    dim_clasificacion.insert(0, "pk_clasificacion", range(1, len(dim_clasificacion)+1))
    subir(dim_clasificacion, "dim_clasificacion_retraso")

    # Lookups PASS 1a
    lookup_tiempo    = dict(zip(dim_tiempo["FlightDate"],           dim_tiempo["pk_tiempo"]))
    del dim_tiempo
    lookup_aerolinea = dict(zip(dim_aerolinea["Reporting_Airline"], dim_aerolinea["pk_aerolinea"]))
    del dim_aerolinea
    lookup_avion     = dict(zip(dim_avion["Tail_Number"],           dim_avion["pk_avion"]))
    del dim_avion
    lookup_distancia = dict(zip(dim_distancia["DistanceGroup"],     dim_distancia["pk_distancia"]))
    del dim_distancia
    lookup_horario   = dict(zip(dim_horario["CRSDepTime"],          dim_horario["pk_horario"]))
    del dim_horario
    lookup_can       = dict(zip(
        dim_cancelacion["Cancelled"].astype(str) + "_|_" + dim_cancelacion["CancellationCode"].astype(str) + "_|_" + dim_cancelacion["Diverted"].astype(str),
        dim_cancelacion["pk_cancelacion"]
    ))
    del dim_cancelacion
    lookup_cl        = dict(zip(key_str(dim_clasificacion, cols_cl), dim_clasificacion["pk_clasificacion"])) if cols_cl else {}
    del dim_clasificacion
    lookup_rc        = dict(zip(key_str(dim_retraso[cols_rc], cols_rc), dim_retraso["pk_retraso_causa"])) if cols_rc else {}
    del dim_retraso

    del df
    gc.collect()
    print("[TRANSFORM] PASS 1a completo — RAM liberada.", flush=True)

    # ════════════════════════════════════════════════════════════
    # PASS 1b — dims espaciales (aeropuerto, ruta, desvio)
    # ════════════════════════════════════════════════════════════
    cols_b = pick(DIM_COLS_B)
    print(f"\n[TRANSFORM] PASS 1b — {len(cols_b)}/{len(avail)} columnas (aeropuerto/ruta/desvío)")
    df = pd.read_parquet(tmp_raw, columns=cols_b)
    print(f"  {len(df):,} filas × {len(df.columns)} cols")

    rename_orig = {"OriginAirportID":"AirportID","OriginAirportSeqID":"AirportSeqID","OriginCityMarketID":"CityMarketID","Origin":"AirportCode","OriginCityName":"CityName","OriginState":"State","OriginStateName":"StateName","OriginWac":"Wac"}
    rename_dest = {"DestAirportID":"AirportID","DestAirportSeqID":"AirportSeqID","DestCityMarketID":"CityMarketID","Dest":"AirportCode","DestCityName":"CityName","DestState":"State","DestStateName":"StateName","DestWac":"Wac"}
    df_orig = df[cols_ok(df, list(rename_orig.keys()))].rename(columns=rename_orig)
    df_dest = df[cols_ok(df, list(rename_dest.keys()))].rename(columns=rename_dest)
    dim_aeropuerto = pd.concat([df_orig, df_dest]).drop_duplicates(subset=["AirportCode"]).reset_index(drop=True)
    dim_aeropuerto.insert(0, "pk_aeropuerto", range(1, len(dim_aeropuerto)+1))
    subir(dim_aeropuerto, "dim_aeropuerto")

    cols_ruta = cols_ok(df, ["Origin","Dest","Distance","DistanceGroup","OriginCityName","DestCityName"])
    dim_ruta = df[cols_ruta].drop_duplicates(subset=["Origin","Dest"]).reset_index(drop=True)
    dim_ruta.rename(columns={"Origin":"OriginCode","Dest":"DestCode"}, inplace=True)
    dim_ruta.insert(0, "pk_ruta", range(1, len(dim_ruta)+1))
    subir(dim_ruta, "dim_ruta")

    cols_dev = cols_ok(df, ["DivAirportLandings","DivReachedDest","DivActualElapsedTime","DivArrDelay","DivDistance","Div1Airport","Div1TailNum"])
    dim_desvio = df[cols_dev].drop_duplicates(subset=cols_ok(df, ["DivAirportLandings","Div1Airport"])).reset_index(drop=True)
    dim_desvio.insert(0, "pk_desvio", range(1, len(dim_desvio)+1))
    dim_desvio["descripcion"] = "Desvío registrado"
    fila_sin_dev = {col: 0 for col in cols_dev}
    fila_sin_dev.update({"Div1Airport":"No aplica","Div1TailNum":"No aplica","pk_desvio":0,"descripcion":"Sin desvío"})
    dim_desvio = pd.concat([pd.DataFrame([fila_sin_dev]), dim_desvio], ignore_index=True)
    subir(dim_desvio, "dim_desvio")

    # Lookups PASS 1b
    lookup_apto   = dict(zip(dim_aeropuerto["AirportCode"], dim_aeropuerto["pk_aeropuerto"]))
    del dim_aeropuerto
    lookup_ruta   = dict(zip(
        dim_ruta["OriginCode"].astype(str) + "_|_" + dim_ruta["DestCode"].astype(str),
        dim_ruta["pk_ruta"]
    ))
    del dim_ruta
    cols_dev_key  = cols_ok(dim_desvio, ["DivAirportLandings", "Div1Airport"])
    lookup_desvio = dict(zip(key_str(dim_desvio[cols_dev_key], cols_dev_key), dim_desvio["pk_desvio"])) if cols_dev_key else {}
    del dim_desvio

    del df
    gc.collect()
    print("[TRANSFORM] PASS 1b completo — RAM liberada.", flush=True)

    # ════════════════════════════════════════════════════════════
    # PASS 2 — Fact table
    # ════════════════════════════════════════════════════════════
    fact_cols = pick(FACT_COLS)
    print(f"\n[TRANSFORM] PASS 2 — {len(fact_cols)}/{len(avail)} columnas (fact_vuelo)", flush=True)
    fact = pd.read_parquet(tmp_raw, columns=fact_cols)
    _os.remove(tmp_raw)
    print(f"  {len(fact):,} filas × {len(fact.columns)} cols", flush=True)

    cat_cols = [c for c in fact.select_dtypes(include="category").columns]
    if cat_cols:
        fact[cat_cols] = fact[cat_cols].astype(object)
        gc.collect()

    fact["fk_tiempo"]    = fact["FlightDate"].map(lookup_tiempo).fillna(0).astype("int32")
    del lookup_tiempo
    fact["fk_aerolinea"] = fact["Reporting_Airline"].map(lookup_aerolinea).fillna(0).astype("int32")
    del lookup_aerolinea
    print("  ✓ fk_tiempo, fk_aerolinea", flush=True)

    if "Origin" in fact.columns:
        fact["fk_aeropuerto_origen"]  = fact["Origin"].map(lookup_apto).fillna(0).astype("int32")
    if "Dest" in fact.columns:
        fact["fk_aeropuerto_destino"] = fact["Dest"].map(lookup_apto).fillna(0).astype("int32")
    del lookup_apto

    fact["fk_avion"] = fact["Tail_Number"].map(lookup_avion).fillna(0).astype("int32")
    del lookup_avion
    print("  ✓ fk_aeropuerto_origen/destino, fk_avion", flush=True)

    if "Origin" in fact.columns and "Dest" in fact.columns:
        fact["fk_ruta"] = (fact["Origin"].astype(str) + "_|_" + fact["Dest"].astype(str)).map(lookup_ruta).fillna(0).astype("int32")
    del lookup_ruta

    if "DistanceGroup" in fact.columns:
        fact["fk_distancia"] = fact["DistanceGroup"].map(lookup_distancia).fillna(0).astype("int32")
    del lookup_distancia

    if "CRSDepTime" in fact.columns:
        fact["fk_horario"] = fact["CRSDepTime"].map(lookup_horario).fillna(0).astype("int32")
    del lookup_horario
    print("  ✓ fk_ruta, fk_distancia, fk_horario", flush=True)

    if all(c in fact.columns for c in ["Cancelled", "CancellationCode", "Diverted"]):
        fact["fk_cancelacion"] = (
            fact["Cancelled"].astype(str) + "_|_" + fact["CancellationCode"].astype(str) + "_|_" + fact["Diverted"].astype(str)
        ).map(lookup_can).fillna(0).astype("int32")
    del lookup_can
    print("  ✓ fk_cancelacion", flush=True)

    if lookup_cl:
        cols_cl_f = [c for c in cols_cl if c in fact.columns]
        if cols_cl_f:
            fact["fk_clasificacion_retraso"] = key_str(fact, cols_cl_f).map(lookup_cl).fillna(0).astype("int32")
    del lookup_cl

    if lookup_rc:
        cols_rc_f = [c for c in cols_rc if c in fact.columns]
        if cols_rc_f:
            fact["fk_retraso_causa"] = key_str(fact, cols_rc_f).map(lookup_rc).fillna(0).astype("int32")
    del lookup_rc
    print("  ✓ fk_clasificacion_retraso, fk_retraso_causa", flush=True)

    if lookup_desvio:
        cols_dev_f = [c for c in cols_dev_key if c in fact.columns]
        if cols_dev_f:
            fact["fk_desvio"] = key_str(fact, cols_dev_f).map(lookup_desvio).fillna(0).astype("int32")
    del lookup_desvio
    gc.collect()
    print("  ✓ fk_desvio — todos los FKs asignados", flush=True)

    fks        = [c for c in fact.columns if c.startswith("fk_")]
    metricas_f = [c for c in METRICAS if c in fact.columns]
    fact.drop(columns=[c for c in fact.columns if c not in set(fks + metricas_f)], inplace=True)
    gc.collect()
    fact.insert(0, "pk_vuelo", range(1, len(fact)+1))
    print(f"  fact_vuelo: {len(fact):,} filas × {len(fact.columns)} cols — Subiendo a MinIO...", flush=True)
    subir(fact, "fact_vuelo")

    print(f"\n[TRANSFORM] ✅ TRANSFORMACIÓN COMPLETA — fact_vuelo: {len(fact):,} filas")

    agregaciones_pipeline()


# ═══════════════════════════════════════════════════════════════
# AGREGACIONES: fact_vuelo + dims → 8 tablas pre-calculadas
# ═══════════════════════════════════════════════════════════════

def agregaciones_pipeline() -> None:
    """Lee fact_vuelo + dimensiones desde aerotrack-dims, genera 8 tablas
    de agregación pre-calculadas y las sube al mismo bucket.

    Tablas generadas (requeridas):
      agg_otp_aerolinea_mes           — OTP por aerolínea / año / mes
      agg_cancelaciones_causa         — Cancelaciones por código FAA / año / mes
      agg_cancelaciones_causa_aerolinea — Cancelaciones por código FAA / aerolínea / año / mes
      agg_kpi_global_dia              — KPIs globales por día
      agg_rutas_eficiencia            — Eficiencia por ruta / aerolínea

    Tablas adicionales (eliminan el full-fact en las páginas secundarias):
      agg_causas_retraso_mes          — Minutos de retraso por causa / aerolínea / mes
      agg_otp_dia_semana              — OTP por día de la semana
      agg_desvios_ruta                — Desvíos agregados por ruta / aeropuerto alternativo
      agg_cancelaciones_ruta          — Tasa de cancelación y retraso por ruta (para asistente IA)
    """
    import gc
    import io
    import os as _os
    import tempfile

    import pandas as pd
    import pyarrow.parquet as pq
    from minio import Minio

    import config

    MINIO_ENDPOINT = config.MINIO_ENDPOINT
    MINIO_ACCESS   = config.MINIO_ACCESS
    MINIO_SECRET   = config.MINIO_SECRET
    BUCKET_DIMS    = config.MINIO_BUCKET_DIMS

    client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS, secret_key=MINIO_SECRET, secure=False)

    def read_dim(name: str, cols: list) -> pd.DataFrame:
        try:
            resp = client.get_object(BUCKET_DIMS, f"{name}.parquet")
            buf  = io.BytesIO(resp.read())
            resp.close()
            pf   = pq.ParquetFile(buf)
            ok   = [c for c in cols if c in pf.schema_arrow.names]
            df   = pf.read(columns=ok).to_pandas()
            for col in df.columns:
                if hasattr(df[col], "cat"):
                    df[col] = df[col].astype(df[col].cat.categories.dtype)
            return df
        except Exception as exc:
            print(f"  ⚠ {name}.parquet no disponible: {exc}")
            return pd.DataFrame()

    def subir(df: pd.DataFrame, name: str) -> None:
        tmp = tempfile.mktemp(suffix=".parquet")
        df.to_parquet(tmp, engine="pyarrow", compression="snappy", index=False)
        client.fput_object(BUCKET_DIMS, f"{name}.parquet", tmp)
        _os.remove(tmp)
        print(f"  ✅ {name}: {len(df):,} filas → s3://{BUCKET_DIMS}/{name}.parquet")

    def norm_pk(df: pd.DataFrame, pk: str) -> None:
        if pk in df.columns:
            df[pk] = pd.to_numeric(df[pk], errors="coerce").fillna(0).astype("int64")

    print(f"\n[AGG] Leyendo modelo dimensional desde s3://{BUCKET_DIMS}/")

    # ── fact_vuelo ───────────────────────────────────────────────
    fact = read_dim("fact_vuelo", [
        "pk_vuelo", "fk_tiempo", "fk_aerolinea", "fk_ruta",
        "fk_horario", "fk_cancelacion", "fk_clasificacion_retraso",
        "fk_retraso_causa", "fk_desvio",
        "ActualElapsedTime", "CRSElapsedTime",
    ])
    if fact.empty:
        raise RuntimeError("fact_vuelo.parquet no encontrado. Ejecuta la tarea transform primero.")
    for col in [c for c in fact.columns if c.startswith("fk_") or c == "pk_vuelo"]:
        fact[col] = pd.to_numeric(fact[col], errors="coerce").fillna(0).astype("int64")
    print(f"  fact_vuelo: {len(fact):,} filas")

    # ── Dimensiones ──────────────────────────────────────────────
    dim_t    = read_dim("dim_tiempo",             ["pk_tiempo",        "Year", "Month", "DayofMonth", "DayOfWeek"])
    dim_al   = read_dim("dim_aerolinea",          ["pk_aerolinea",     "Reporting_Airline"])
    dim_hor  = read_dim("dim_horario",            ["pk_horario",       "ArrDelayMinutes"])
    dim_can  = read_dim("dim_cancelacion",        ["pk_cancelacion",   "Cancelled", "CancellationCode", "Diverted"])
    dim_ruta = read_dim("dim_ruta",               ["pk_ruta",          "OriginCode", "DestCode"])
    dim_rc   = read_dim("dim_retraso_causa",      ["pk_retraso_causa", "CarrierDelay", "WeatherDelay",
                                                   "NASDelay", "SecurityDelay", "LateAircraftDelay"])
    dim_dev  = read_dim("dim_desvio",             ["pk_desvio",        "Div1Airport", "DivArrDelay", "DivDistance"])
    dim_cl   = read_dim("dim_clasificacion_retraso", ["pk_clasificacion", "ArrDel15"])

    for df_d, pk in [
        (dim_t,    "pk_tiempo"),     (dim_al,   "pk_aerolinea"),
        (dim_hor,  "pk_horario"),    (dim_can,  "pk_cancelacion"),
        (dim_ruta, "pk_ruta"),       (dim_rc,   "pk_retraso_causa"),
        (dim_dev,  "pk_desvio"),     (dim_cl,   "pk_clasificacion"),
    ]:
        norm_pk(df_d, pk)

    # ── Mini-fact enriquecido ─────────────────────────────────────
    f = fact.copy()
    if not dim_t.empty    and "fk_tiempo"                 in f.columns: f = f.merge(dim_t,    left_on="fk_tiempo",                 right_on="pk_tiempo",        how="left")
    if not dim_al.empty   and "fk_aerolinea"              in f.columns: f = f.merge(dim_al,   left_on="fk_aerolinea",              right_on="pk_aerolinea",     how="left")
    if not dim_hor.empty  and "fk_horario"                in f.columns: f = f.merge(dim_hor,  left_on="fk_horario",                right_on="pk_horario",       how="left")
    if not dim_can.empty  and "fk_cancelacion"            in f.columns: f = f.merge(dim_can,  left_on="fk_cancelacion",            right_on="pk_cancelacion",   how="left")
    if not dim_ruta.empty and "fk_ruta"                   in f.columns: f = f.merge(dim_ruta, left_on="fk_ruta",                   right_on="pk_ruta",          how="left")
    if not dim_rc.empty   and "fk_retraso_causa"          in f.columns: f = f.merge(dim_rc,   left_on="fk_retraso_causa",          right_on="pk_retraso_causa", how="left")
    if not dim_dev.empty  and "fk_desvio"                 in f.columns: f = f.merge(dim_dev,  left_on="fk_desvio",                 right_on="pk_desvio",        how="left")
    if not dim_cl.empty   and "fk_clasificacion_retraso"  in f.columns: f = f.merge(dim_cl,   left_on="fk_clasificacion_retraso",  right_on="pk_clasificacion", how="left")

    del fact, dim_t, dim_al, dim_hor, dim_can, dim_ruta, dim_rc, dim_dev, dim_cl
    gc.collect()
    print(f"  Mini-fact: {len(f):,} filas × {len(f.columns)} cols")

    # Defaults seguros para columnas que pueden faltar
    for col, default in [
        ("Cancelled", 0), ("Diverted", 0), ("ArrDelayMinutes", 0.0),
        ("Year", 0), ("Month", 0), ("DayofMonth", 0), ("DayOfWeek", 0),
        ("Reporting_Airline", ""), ("CancellationCode", ""),
        ("OriginCode", ""), ("DestCode", ""), ("Div1Airport", ""),
    ]:
        if col not in f.columns:
            f[col] = default
    f["Cancelled"]         = f["Cancelled"].fillna(0).astype(int)
    f["Diverted"]          = f["Diverted"].fillna(0).astype(int)
    f["ArrDelayMinutes"]   = pd.to_numeric(f["ArrDelayMinutes"],   errors="coerce").fillna(0.0)
    f["ActualElapsedTime"] = pd.to_numeric(f["ActualElapsedTime"], errors="coerce")
    f["CRSElapsedTime"]    = pd.to_numeric(f["CRSElapsedTime"],    errors="coerce")
    f["_at"] = (f["ArrDel15"] == 0).astype(int)   # usa BTS ArrDel15; ArrDelayMinutes no es confiable (dim_horario deduplica por CRSDepTime)

    # ════════════════════════════════════════════════════════════
    # 1. agg_otp_aerolinea_mes
    # GROUP BY carrier / year / month
    # ════════════════════════════════════════════════════════════
    print("\n[AGG] 1/7 — agg_otp_aerolinea_mes")
    G1 = ["Reporting_Airline", "Year", "Month"]
    if all(c in f.columns for c in G1):
        tot1 = f.groupby(G1).agg(
            total_vuelos_todos=("pk_vuelo",  "count"),
            total_cancelados  =("Cancelled", "sum"),
        ).reset_index()
        op1 = f[f["Cancelled"] == 0]
        op1_agg = op1.groupby(G1).agg(
            total_vuelos   =("pk_vuelo",       "count"),
            vuelos_a_tiempo=("_at",            "sum"),
            delay_sum      =("ArrDelayMinutes", "sum"),
        ).reset_index()
        a1 = op1_agg.merge(tot1, on=G1, how="left")
        d1 = a1["total_vuelos"].replace(0, float("nan"))
        a1["otp_pct"]   = (a1["vuelos_a_tiempo"] / d1 * 100).fillna(0.0).round(2)
        a1["delay_avg"] = (a1["delay_sum"]        / d1      ).fillna(0.0).round(2)
        a1.drop(columns=["delay_sum"], inplace=True)
        a1.rename(columns={"Reporting_Airline": "carrier", "Year": "year", "Month": "month"}, inplace=True)
        a1[["year", "month"]] = a1[["year", "month"]].astype(int)
        subir(a1, "agg_otp_aerolinea_mes")

    # ════════════════════════════════════════════════════════════
    # 2. agg_cancelaciones_causa
    # GROUP BY cancellation_code / year / month
    # ════════════════════════════════════════════════════════════
    print("\n[AGG] 2/7 — agg_cancelaciones_causa")
    canc2 = f[f["Cancelled"] == 1].copy()
    if len(canc2) > 0 and "CancellationCode" in canc2.columns:
        total_canc = len(canc2)
        a2 = canc2.groupby(["CancellationCode", "Year", "Month"]).size().reset_index(name="total_cancelados")
        a2["pct_del_total"] = (a2["total_cancelados"] / total_canc * 100).round(2)
        a2.rename(columns={"CancellationCode": "cancellation_code", "Year": "year", "Month": "month"}, inplace=True)
        a2[["year", "month"]] = a2[["year", "month"]].astype(int)
        subir(a2, "agg_cancelaciones_causa")

    # ════════════════════════════════════════════════════════════
    # 2b. agg_cancelaciones_causa_aerolinea
    # GROUP BY cancellation_code / carrier / year / month
    # ════════════════════════════════════════════════════════════
    print("\n[AGG] 2b/8 — agg_cancelaciones_causa_aerolinea")
    if len(canc2) > 0 and "CancellationCode" in canc2.columns and "Reporting_Airline" in canc2.columns:
        a2b = canc2.groupby(["CancellationCode", "Reporting_Airline", "Year", "Month"]).size().reset_index(name="total_cancelados")
        a2b.rename(columns={"CancellationCode": "cancellation_code", "Reporting_Airline": "carrier", "Year": "year", "Month": "month"}, inplace=True)
        a2b[["year", "month"]] = a2b[["year", "month"]].astype(int)
        subir(a2b, "agg_cancelaciones_causa_aerolinea")

    # ════════════════════════════════════════════════════════════
    # 3. agg_kpi_global_dia
    # GROUP BY year / month / day_of_month
    # ════════════════════════════════════════════════════════════
    print("\n[AGG] 3/7 — agg_kpi_global_dia")
    G3 = ["Year", "Month", "DayofMonth"]
    if all(c in f.columns for c in G3):
        tot3 = f.groupby(G3).agg(
            total_vuelos    =("pk_vuelo",  "count"),
            total_cancelados=("Cancelled", "sum"),
            total_desviados =("Diverted",  "sum"),
        ).reset_index()
        op3 = f[f["Cancelled"] == 0]
        op3_agg = op3.groupby(G3).agg(
            vuelos_operados =("pk_vuelo",       "count"),
            vuelos_a_tiempo =("_at",            "sum"),
            sum_arr_delay   =("ArrDelayMinutes", "sum"),
        ).reset_index()
        a3 = tot3.merge(op3_agg, on=G3, how="left")
        d3 = a3["vuelos_operados"].replace(0, float("nan"))
        a3["otp_pct"]          = (a3["vuelos_a_tiempo"] / d3 * 100).fillna(0.0).round(2)
        a3["retraso_promedio"] = (a3["sum_arr_delay"]    / d3      ).fillna(0.0).round(2)
        a3.rename(columns={"Year": "year", "Month": "month", "DayofMonth": "day_of_month"}, inplace=True)
        a3[["year", "month", "day_of_month"]] = a3[["year", "month", "day_of_month"]].astype(int)
        subir(a3, "agg_kpi_global_dia")

    # ════════════════════════════════════════════════════════════
    # 4. agg_rutas_eficiencia
    # GROUP BY origin / dest / carrier
    # ════════════════════════════════════════════════════════════
    print("\n[AGG] 4/7 — agg_rutas_eficiencia")
    G4 = [c for c in ["OriginCode", "DestCode", "Reporting_Airline", "Year"] if c in f.columns]
    op4 = f[
        (f["Cancelled"] == 0) &
        f["ActualElapsedTime"].notna() &
        f["CRSElapsedTime"].notna() &
        (f["CRSElapsedTime"] > 0)
    ].copy()
    if G4 and len(op4) > 0:
        a4 = op4.groupby(G4).agg(
            total_vuelos   =("pk_vuelo",          "count"),
            vuelos_a_tiempo=("_at",               "sum"),
            tiempo_real_avg=("ActualElapsedTime",  "mean"),
            tiempo_prog_avg=("CRSElapsedTime",     "mean"),
            retraso_prom   =("ArrDelayMinutes",    "mean"),
        ).reset_index()
        a4 = a4[a4["total_vuelos"] >= 10].copy()
        d4 = a4["total_vuelos"].replace(0, float("nan"))
        a4["otp_pct"]           = (a4["vuelos_a_tiempo"] / d4 * 100).fillna(0.0).round(2)
        a4["indice_eficiencia"] = ((a4["tiempo_real_avg"] - a4["tiempo_prog_avg"]) / a4["tiempo_prog_avg"] * 100).round(2)
        a4["tiempo_real_avg"]   = a4["tiempo_real_avg"].round(2)
        a4["tiempo_prog_avg"]   = a4["tiempo_prog_avg"].round(2)
        a4["retraso_prom"]      = a4["retraso_prom"].fillna(0.0).round(2)
        ren4 = {}
        if "OriginCode"        in a4.columns: ren4["OriginCode"]        = "origin"
        if "DestCode"          in a4.columns: ren4["DestCode"]          = "dest"
        if "Reporting_Airline" in a4.columns: ren4["Reporting_Airline"] = "carrier"
        if "Year"              in a4.columns: ren4["Year"]              = "year"
        a4.rename(columns=ren4, inplace=True)
        if "year" in a4.columns:
            a4["year"] = a4["year"].astype(int)
        subir(a4, "agg_rutas_eficiencia")

    # ════════════════════════════════════════════════════════════
    # 5. agg_causas_retraso_mes  (elimina full-fact en puntualidad)
    # GROUP BY carrier / year / month — SUMA de minutos por causa
    # ════════════════════════════════════════════════════════════
    print("\n[AGG] 5/7 — agg_causas_retraso_mes")
    CAUSA_COLS = ["CarrierDelay", "WeatherDelay", "NASDelay", "SecurityDelay", "LateAircraftDelay"]
    G5 = ["Reporting_Airline", "Year", "Month"]
    avail5 = [c for c in CAUSA_COLS if c in f.columns]
    if avail5 and all(c in f.columns for c in G5):
        f5 = f.copy()
        for c in avail5:
            f5[c] = pd.to_numeric(f5[c], errors="coerce").fillna(0.0)
        a5_spec = {c.lower(): (c, "sum") for c in avail5}
        a5 = f5.groupby(G5).agg(**a5_spec).reset_index()
        a5.rename(columns={"Reporting_Airline": "carrier", "Year": "year", "Month": "month"}, inplace=True)
        a5[["year", "month"]] = a5[["year", "month"]].astype(int)
        subir(a5, "agg_causas_retraso_mes")

    # ════════════════════════════════════════════════════════════
    # 6. agg_otp_dia_semana  (elimina full-fact en puntualidad)
    # GROUP BY day_of_week
    # ════════════════════════════════════════════════════════════
    print("\n[AGG] 6/7 — agg_otp_dia_semana")
    if "DayOfWeek" in f.columns:
        op6 = f[f["Cancelled"] == 0]
        a6 = op6.groupby("DayOfWeek").agg(
            total_vuelos   =("pk_vuelo", "count"),
            vuelos_a_tiempo=("_at",      "sum"),
        ).reset_index()
        d6 = a6["total_vuelos"].replace(0, float("nan"))
        a6["otp_pct"] = (a6["vuelos_a_tiempo"] / d6 * 100).fillna(0.0).round(2)
        a6.rename(columns={"DayOfWeek": "day_of_week"}, inplace=True)
        a6["day_of_week"] = a6["day_of_week"].astype(int)
        subir(a6, "agg_otp_dia_semana")

    # ════════════════════════════════════════════════════════════
    # 7. agg_desvios_ruta  (elimina full-fact en cancelaciones)
    # GROUP BY origin / dest / alt_airport
    # ════════════════════════════════════════════════════════════
    print("\n[AGG] 7/7 — agg_desvios_ruta")
    dev7 = f[f["Diverted"] == 1].copy()
    G7 = [c for c in ["OriginCode", "DestCode", "Div1Airport", "Year", "Month"] if c in dev7.columns]
    if G7 and len(dev7) > 0:
        a7_spec: dict = {"total_desvios": ("pk_vuelo", "count")}
        for cd in ["DivArrDelay", "DivDistance"]:
            if cd in dev7.columns:
                dev7[cd] = pd.to_numeric(dev7[cd], errors="coerce")
                a7_spec[f"{cd.lower()}_avg"] = (cd, "mean")
        a7 = dev7.groupby(G7).agg(**a7_spec).reset_index()
        ren7 = {}
        if "OriginCode"  in a7.columns: ren7["OriginCode"]  = "origin"
        if "DestCode"    in a7.columns: ren7["DestCode"]    = "dest"
        if "Div1Airport" in a7.columns: ren7["Div1Airport"] = "alt_airport"
        if "Year"        in a7.columns: ren7["Year"]        = "year"
        if "Month"       in a7.columns: ren7["Month"]       = "month"
        a7.rename(columns=ren7, inplace=True)
        for ca in ["divarrdelay_avg", "divdistance_avg"]:
            if ca in a7.columns:
                a7[ca] = a7[ca].fillna(0.0).round(1)
        for c7 in ["year", "month"]:
            if c7 in a7.columns:
                a7[c7] = a7[c7].astype(int)
        a7 = a7.sort_values("total_desvios", ascending=False)
        subir(a7, "agg_desvios_ruta")

    # ════════════════════════════════════════════════════════════
    # 8. agg_cancelaciones_ruta  (para el asistente IA)
    # GROUP BY origin / dest — tasa de cancelación por ruta
    # ════════════════════════════════════════════════════════════
    print("\n[AGG] 8/8 — agg_cancelaciones_ruta")
    G8 = [c for c in ["OriginCode", "DestCode"] if c in f.columns]
    if len(G8) == 2 and "Cancelled" in f.columns:
        a8_spec: dict = {
            "total_vuelos":     ("pk_vuelo", "count"),
            "total_cancelados": ("Cancelled", "sum"),
        }
        if "ArrDelayMinutes" in f.columns:
            op8 = f[f["Cancelled"] == 0]
            delay8 = op8.groupby(G8)["ArrDelayMinutes"].mean().rename("retraso_prom_min").reset_index()
        else:
            delay8 = None

        a8 = f.groupby(G8).agg(**a8_spec).reset_index()
        a8.rename(columns={"OriginCode": "origin", "DestCode": "dest"}, inplace=True)
        a8["total_cancelados"] = a8["total_cancelados"].fillna(0).astype(int)
        a8["tasa_cancelacion"] = (
            a8["total_cancelados"] / a8["total_vuelos"].replace(0, float("nan"))
        ).fillna(0.0).round(4)

        if delay8 is not None:
            delay8.rename(columns={"OriginCode": "origin", "DestCode": "dest"}, inplace=True)
            a8 = a8.merge(delay8, on=["origin", "dest"], how="left")
            a8["retraso_prom_min"] = a8["retraso_prom_min"].fillna(0.0).round(1)

        a8 = a8[a8["total_vuelos"] >= 30].sort_values("tasa_cancelacion", ascending=False)
        subir(a8, "agg_cancelaciones_ruta")

    # ════════════════════════════════════════════════════════════
    # 9. agg_cancelaciones_aerolinea_causa
    # GROUP BY carrier / cancellation_code / year / month
    # ════════════════════════════════════════════════════════════
    print("\n[AGG] 9/10 — agg_cancelaciones_aerolinea_causa")
    canc9 = f[f["Cancelled"] == 1].copy()
    G9 = ["Reporting_Airline", "CancellationCode", "Year", "Month"]
    if all(c in canc9.columns for c in G9) and len(canc9) > 0:
        a9 = canc9.groupby(G9).size().reset_index(name="total_cancelados")
        tot9 = a9.groupby(["Reporting_Airline", "Year", "Month"])["total_cancelados"].transform("sum")
        a9["pct_del_carrier"] = (a9["total_cancelados"] / tot9.replace(0, float("nan")) * 100).fillna(0.0).round(2)
        a9.rename(columns={
            "Reporting_Airline": "carrier",
            "CancellationCode":  "cancellation_code",
            "Year":              "year",
            "Month":             "month",
        }, inplace=True)
        a9[["year", "month"]] = a9[["year", "month"]].astype(int)
        subir(a9, "agg_cancelaciones_aerolinea_causa")

    # ════════════════════════════════════════════════════════════
    # 10. agg_otp_aerolinea_dia_semana
    # GROUP BY carrier / day_of_week
    # ════════════════════════════════════════════════════════════
    print("\n[AGG] 10/10 — agg_otp_aerolinea_dia_semana")
    G10 = ["Reporting_Airline", "DayOfWeek"]
    if all(c in f.columns for c in G10):
        op10 = f[f["Cancelled"] == 0]
        a10 = op10.groupby(G10).agg(
            total_vuelos   =("pk_vuelo", "count"),
            vuelos_a_tiempo=("_at",      "sum"),
        ).reset_index()
        a10["otp_pct"] = (
            a10["vuelos_a_tiempo"] / a10["total_vuelos"].replace(0, float("nan")) * 100
        ).fillna(0.0).round(2)
        a10.rename(columns={"Reporting_Airline": "carrier", "DayOfWeek": "day_of_week"}, inplace=True)
        a10["day_of_week"] = a10["day_of_week"].astype(int)
        subir(a10, "agg_otp_aerolinea_dia_semana")

    del f
    gc.collect()
    print(f"\n[AGG] ✅ 10 agregaciones generadas en s3://{BUCKET_DIMS}/")
 