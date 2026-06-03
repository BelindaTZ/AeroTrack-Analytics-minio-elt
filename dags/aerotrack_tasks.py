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
from datetime import datetime
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
 
    parquet_tmp = Path(tempfile.gettempdir()) / f"vuelos_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
 
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
 