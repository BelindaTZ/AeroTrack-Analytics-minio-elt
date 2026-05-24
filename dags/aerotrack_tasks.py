"""
AeroTrack Analytics — Funciones del pipeline para el DAG de Airflow
====================================================================
Este módulo expone las dos funciones principales del pipeline ELT:
  - extract_pipeline(): PocketBase → Parquet → MinIO (aerotrack-raw)
  - transform_pipeline(): aerotrack-raw → modelo estrella → aerotrack-dims

Al estar en dags/, Airflow lo importa directamente sin necesidad de
montar el directorio scripts/. Las URLs/credenciales las gestiona
config.py (también en dags/) que detecta automáticamente el contexto Docker.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path


# ═══════════════════════════════════════════════════════════════
# EXTRACT: PocketBase → Parquet → MinIO
# (equivalente a scripts/03_extraer_pb_a_minio.py)
# ═══════════════════════════════════════════════════════════════

def extract_pipeline() -> None:
    """Extrae todos los registros de PocketBase, los convierte a Parquet
    y los sube a MinIO en aerotrack-raw/vuelos_raw.parquet."""
    import requests
    import pandas as pd
    from minio import Minio

    # config.py está en dags/ → Airflow lo encuentra en sys.path
    import config

    PB_BASE_URL   = config.PB_BASE_URL
    PB_EMAIL      = config.PB_EMAIL
    PB_PASSWORD   = config.PB_PASSWORD
    PB_COLLECTION = config.PB_COLLECTION
    MINIO_ENDPOINT = config.MINIO_ENDPOINT
    MINIO_ACCESS   = config.MINIO_ACCESS
    MINIO_SECRET   = config.MINIO_SECRET
    BUCKET_RAW     = config.MINIO_BUCKET_RAW
    OBJETO_RAW     = "vuelos_raw.parquet"
    PB_PAGE_SIZE   = 500

    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed

    MAX_WORKERS    = 10
    MAX_REINTENTOS = 3
    CAMPOS_INTERNOS = {"id", "collectionId", "collectionName", "created", "updated"}

    print(f"[EXTRACT] PocketBase: {PB_BASE_URL} | Colección: {PB_COLLECTION} | {MAX_WORKERS} workers")

    # 1. Autenticar
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

    # 2. Primera solicitud: obtiene totalItems y totalPages
    resp = requests.get(url, headers=headers, params={"page": 1, "perPage": PB_PAGE_SIZE}, timeout=30)
    resp.raise_for_status()
    data         = resp.json()
    total_items  = data.get("totalItems", 0)
    total_pages  = data.get("totalPages", 1)
    primera_pag  = data.get("items", [])

    if total_items == 0:
        raise RuntimeError("No hay registros en PocketBase. Ejecuta primero el setup inicial.")

    print(f"[EXTRACT] {total_items:,} registros | {total_pages:,} páginas → ~{total_pages // MAX_WORKERS} rondas")

    # 3. Worker que descarga una página con reintentos
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

    # 4. Descargar páginas 2..N concurrentemente (página 1 ya disponible)
    resultados: dict = {1: primera_pag}
    completadas  = 1
    registros_ok = len(primera_pag)
    lock         = threading.Lock()

    args_lista = [(p, url, headers, PB_PAGE_SIZE) for p in range(2, total_pages + 1)]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futuros = {executor.submit(fetch_pagina, a): a[0] for a in args_lista}
        for futuro in as_completed(futuros):
            num_pag, items = futuro.result()
            resultados[num_pag] = items
            with lock:
                completadas  += 1
                registros_ok += len(items)
                if completadas % 100 == 0 or completadas == total_pages:
                    print(
                        f"[EXTRACT] Páginas completadas: {completadas:,}/{total_pages:,} "
                        f"| Registros: {registros_ok:,}/{total_items:,}",
                        flush=True,
                    )

    # 5. Reensamblar en orden y limpiar campos internos
    todos_raw = []
    for p in sorted(resultados.keys()):
        todos_raw.extend(resultados[p])

    todos = [{k: v for k, v in r.items() if k not in CAMPOS_INTERNOS} for r in todos_raw]

    print(f"[EXTRACT] ✅ {len(todos):,} registros extraídos")

    # 3. Convertir a DataFrame y optimizar
    df = pd.DataFrame(todos)
    for col in df.select_dtypes(include="object").columns:
        if df[col].nunique() < 500:
            df[col] = df[col].astype("category")

    # 4. Guardar Parquet temporal y subir a MinIO
    parquet_tmp = Path(tempfile.gettempdir()) / f"vuelos_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
    df.to_parquet(parquet_tmp, engine="pyarrow", compression="snappy", index=False)

    tam_mb = parquet_tmp.stat().st_size / (1024 * 1024)
    print(f"[EXTRACT] Parquet local: {parquet_tmp} ({tam_mb:.1f} MB)")

    cliente = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS, secret_key=MINIO_SECRET, secure=False)
    if not cliente.bucket_exists(BUCKET_RAW):
        cliente.make_bucket(BUCKET_RAW)
        print(f"[EXTRACT] Bucket '{BUCKET_RAW}' creado")

    cliente.fput_object(BUCKET_RAW, OBJETO_RAW, str(parquet_tmp), content_type="application/octet-stream")
    parquet_tmp.unlink()

    print(f"[EXTRACT] ✅ Subido a s3://{BUCKET_RAW}/{OBJETO_RAW}")


# ═══════════════════════════════════════════════════════════════
# TRANSFORM: aerotrack-raw → modelo estrella → aerotrack-dims
# (equivalente a scripts/04_transformar_dimensiones.py)
# ═══════════════════════════════════════════════════════════════

def transform_pipeline() -> None:
    """Descarga vuelos_raw.parquet desde MinIO, genera el modelo
    estrella (10 dims + fact_vuelo) y sube cada tabla a aerotrack-dims."""
    import os as _os
    import pandas as pd
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

    # Verificar que el parquet raw existe
    try:
        client.stat_object(BUCKET_RAW, OBJETO_RAW)
    except S3Error:
        raise RuntimeError(
            f"No encontrado: s3://{BUCKET_RAW}/{OBJETO_RAW}. "
            "Ejecuta primero la tarea extract."
        )

    # ── Helpers locales ─────────────────────────────────────────
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
        return df[cols].astype(str).agg("_|_".join, axis=1)

    # ── Descargar parquet raw ────────────────────────────────────
    tmp_raw = tempfile.mktemp(suffix=".parquet")
    client.fget_object(BUCKET_RAW, OBJETO_RAW, tmp_raw)
    df = pd.read_parquet(tmp_raw)
    _os.remove(tmp_raw)
    print(f"[TRANSFORM] ✅ {len(df):,} filas × {len(df.columns)} columnas cargadas")

    # ── Dimensiones ──────────────────────────────────────────────
    cols_t = cols_ok(df, ["FlightDate","Year","Quarter","Month","DayofMonth","DayOfWeek","DepTimeBlk","ArrTimeBlk"])
    dim_tiempo = df[cols_t].drop_duplicates(subset=["FlightDate"]).reset_index(drop=True)
    dim_tiempo.insert(0, "pk_tiempo", range(1, len(dim_tiempo)+1))
    subir(dim_tiempo, "dim_tiempo")

    cols_a = cols_ok(df, ["Reporting_Airline","IATA_CODE_Reporting_Airline","DOT_ID_Reporting_Airline"])
    dim_aerolinea = df[cols_a].drop_duplicates(subset=["Reporting_Airline"]).reset_index(drop=True)
    dim_aerolinea.insert(0, "pk_aerolinea", range(1, len(dim_aerolinea)+1))
    subir(dim_aerolinea, "dim_aerolinea")

    rename_orig = {"OriginAirportID":"AirportID","OriginAirportSeqID":"AirportSeqID","OriginCityMarketID":"CityMarketID","Origin":"AirportCode","OriginCityName":"CityName","OriginState":"State","OriginStateName":"StateName","OriginWac":"Wac"}
    rename_dest = {"DestAirportID":"AirportID","DestAirportSeqID":"AirportSeqID","DestCityMarketID":"CityMarketID","Dest":"AirportCode","DestCityName":"CityName","DestState":"State","DestStateName":"StateName","DestWac":"Wac"}
    df_orig = df[cols_ok(df, list(rename_orig.keys()))].rename(columns=rename_orig)
    df_dest = df[cols_ok(df, list(rename_dest.keys()))].rename(columns=rename_dest)
    dim_aeropuerto = pd.concat([df_orig, df_dest]).drop_duplicates(subset=["AirportCode"]).reset_index(drop=True)
    dim_aeropuerto.insert(0, "pk_aeropuerto", range(1, len(dim_aeropuerto)+1))
    subir(dim_aeropuerto, "dim_aeropuerto")

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

    cols_dev = cols_ok(df, ["DivAirportLandings","DivReachedDest","DivActualElapsedTime","DivArrDelay","DivDistance","Div1Airport","Div1TailNum"])
    dim_desvio = df[cols_dev].drop_duplicates(subset=cols_ok(df, ["DivAirportLandings","Div1Airport"])).reset_index(drop=True)
    dim_desvio.insert(0, "pk_desvio", range(1, len(dim_desvio)+1))
    dim_desvio["descripcion"] = "Desvío registrado"
    fila_sin_dev = {col: 0 for col in cols_dev}
    fila_sin_dev.update({"Div1Airport":"No aplica","Div1TailNum":"No aplica","pk_desvio":0,"descripcion":"Sin desvío"})
    dim_desvio = pd.concat([pd.DataFrame([fila_sin_dev]), dim_desvio], ignore_index=True)
    subir(dim_desvio, "dim_desvio")

    cols_hor = cols_ok(df, ["CRSDepTime","DepTime","DepDelay","DepDelayMinutes","CRSArrTime","ArrTime","ArrDelay","ArrDelayMinutes"])
    dim_horario = df[cols_hor].drop_duplicates(subset=["CRSDepTime"]).reset_index(drop=True)
    dim_horario.insert(0, "pk_horario", range(1, len(dim_horario)+1))
    subir(dim_horario, "dim_horario")

    cols_cl = cols_ok(df, ["DepDel15","ArrDel15","DepartureDelayGroups","ArrivalDelayGroups"])
    dim_clasificacion = df[cols_cl].drop_duplicates().reset_index(drop=True)
    dim_clasificacion.insert(0, "pk_clasificacion", range(1, len(dim_clasificacion)+1))
    subir(dim_clasificacion, "dim_clasificacion_retraso")

    cols_ruta = cols_ok(df, ["Origin","Dest","Distance","DistanceGroup","OriginCityName","DestCityName"])
    dim_ruta = df[cols_ruta].drop_duplicates(subset=["Origin","Dest"]).reset_index(drop=True)
    dim_ruta.rename(columns={"Origin":"OriginCode","Dest":"DestCode"}, inplace=True)
    dim_ruta.insert(0, "pk_ruta", range(1, len(dim_ruta)+1))
    subir(dim_ruta, "dim_ruta")

    # ── Fact table con map() ─────────────────────────────────────
    print("\n[TRANSFORM] Generando fact_vuelo con map()...")
    fact = df.copy()

    fact["fk_tiempo"]   = df["FlightDate"].map(dict(zip(dim_tiempo["FlightDate"], dim_tiempo["pk_tiempo"]))).fillna(0).astype(int)
    fact["fk_aerolinea"] = df["Reporting_Airline"].map(dict(zip(dim_aerolinea["Reporting_Airline"], dim_aerolinea["pk_aerolinea"]))).fillna(0).astype(int)

    lookup_apto = dict(zip(dim_aeropuerto["AirportCode"], dim_aeropuerto["pk_aeropuerto"]))
    if "Origin" in df.columns:
        fact["fk_aeropuerto_origen"]  = df["Origin"].map(lookup_apto).fillna(0).astype(int)
    if "Dest" in df.columns:
        fact["fk_aeropuerto_destino"] = df["Dest"].map(lookup_apto).fillna(0).astype(int)

    fact["fk_avion"] = df["Tail_Number"].map(dict(zip(dim_avion["Tail_Number"], dim_avion["pk_avion"]))).fillna(0).astype(int)

    lookup_ruta = dict(zip(dim_ruta["OriginCode"].astype(str)+"_|_"+dim_ruta["DestCode"].astype(str), dim_ruta["pk_ruta"]))
    if "Origin" in df.columns and "Dest" in df.columns:
        fact["fk_ruta"] = (df["Origin"].astype(str)+"_|_"+df["Dest"].astype(str)).map(lookup_ruta).fillna(0).astype(int)

    if "DistanceGroup" in df.columns:
        fact["fk_distancia"] = df["DistanceGroup"].map(dict(zip(dim_distancia["DistanceGroup"], dim_distancia["pk_distancia"]))).fillna(0).astype(int)
    if "CRSDepTime" in df.columns:
        fact["fk_horario"] = df["CRSDepTime"].map(dict(zip(dim_horario["CRSDepTime"], dim_horario["pk_horario"]))).fillna(0).astype(int)

    lookup_can = dict(zip(dim_cancelacion["Cancelled"].astype(str)+"_|_"+dim_cancelacion["CancellationCode"].astype(str)+"_|_"+dim_cancelacion["Diverted"].astype(str), dim_cancelacion["pk_cancelacion"]))
    if all(c in df.columns for c in ["Cancelled","CancellationCode","Diverted"]):
        fact["fk_cancelacion"] = (df["Cancelled"].astype(str)+"_|_"+df["CancellationCode"].astype(str)+"_|_"+df["Diverted"].astype(str)).map(lookup_can).fillna(0).astype(int)

    if cols_cl:
        fact["fk_clasificacion_retraso"] = key_str(df, cols_cl).map(dict(zip(key_str(dim_clasificacion, cols_cl), dim_clasificacion["pk_clasificacion"]))).fillna(0).astype(int)
    if cols_rc:
        fact["fk_retraso_causa"] = key_str(df, cols_rc).map(dict(zip(key_str(dim_retraso[cols_rc], cols_rc), dim_retraso["pk_retraso_causa"]))).fillna(0).astype(int)

    cols_dev_key = cols_ok(df, ["DivAirportLandings","Div1Airport"])
    if cols_dev_key:
        fact["fk_desvio"] = key_str(df, cols_dev_key).map(dict(zip(key_str(dim_desvio[cols_dev_key], cols_dev_key), dim_desvio["pk_desvio"]))).fillna(0).astype(int)

    metricas = cols_ok(df, ["AirTime","Distance","Flights","ActualElapsedTime","CRSElapsedTime","TaxiIn","TaxiOut"])
    fks = [c for c in fact.columns if c.startswith("fk_")]
    fact_vuelo = fact[fks + metricas].copy()
    fact_vuelo.insert(0, "pk_vuelo", range(1, len(fact_vuelo)+1))
    subir(fact_vuelo, "fact_vuelo")

    print(f"\n[TRANSFORM] ✅ TRANSFORMACIÓN COMPLETA — fact_vuelo: {len(fact_vuelo):,} filas")
