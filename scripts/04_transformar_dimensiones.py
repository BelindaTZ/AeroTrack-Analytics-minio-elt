"""
AeroTrack Analytics — Script 04: Transformar → Dimensiones + Hecho
=============================================================================
Qué hace:
  1. Descarga aerotrack-raw/vuelos_raw.parquet desde MinIO
  2. Genera el modelo estrella (10 dimensiones + 1 tabla de hechos)
  3. Sube cada tabla como Parquet a aerotrack-dims/

Usa map() (no merge()) para asignar FKs — NUNCA multiplica filas.
fact_vuelo debe tener exactamente tantas filas como hay en el parquet raw.

Cómo ejecutar:
    python scripts/04_transformar_dimensiones.py
"""

import os
import sys
import tempfile

import pandas as pd
from minio import Minio
from minio.error import S3Error

sys.path.insert(0, os.path.dirname(__file__))
import config

OBJETO_RAW = "vuelos_raw.parquet"


# ── HELPERS ────────────────────────────────────────────────────

def cols_ok(df, columnas):
    return [c for c in columnas if c in df.columns]


def subir(client, df, nombre, bucket_dims):
    tmp = tempfile.mktemp(suffix=".parquet")
    df.to_parquet(tmp, engine="pyarrow", compression="snappy", index=False)
    if not client.bucket_exists(bucket_dims):
        client.make_bucket(bucket_dims)
    client.fput_object(bucket_dims, f"{nombre}.parquet", tmp)
    os.remove(tmp)
    print(f"  ✅ {nombre}: {len(df):,} filas → MinIO/{bucket_dims}/{nombre}.parquet")


def key_str(df, cols):
    return df[cols].astype(str).agg("_|_".join, axis=1)


# ── MAIN ───────────────────────────────────────────────────────

def main():
    MINIO_ENDPOINT = config.MINIO_ENDPOINT
    MINIO_ACCESS   = config.MINIO_ACCESS
    MINIO_SECRET   = config.MINIO_SECRET
    BUCKET_RAW     = config.MINIO_BUCKET_RAW
    BUCKET_DIMS    = config.MINIO_BUCKET_DIMS

    print("=" * 57)
    print("  AeroTrack Analytics — Transformación v2 (con map)")
    print("=" * 57)
    print(f"  MinIO: {MINIO_ENDPOINT} | Raw: {BUCKET_RAW} | Dims: {BUCKET_DIMS}")

    client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS, secret_key=MINIO_SECRET, secure=False)

    # ── Verificar que el parquet raw existe ─────────────────────
    try:
        client.stat_object(BUCKET_RAW, OBJETO_RAW)
    except S3Error:
        print(f"\n❌ No encontrado: s3://{BUCKET_RAW}/{OBJETO_RAW}")
        print("   Ejecuta primero: python scripts/03_extraer_pb_a_minio.py")
        sys.exit(1)

    # ── Descargar parquet desde MinIO ───────────────────────────
    print(f"\n📥 Descargando Parquet desde MinIO...")
    tmp_raw = tempfile.mktemp(suffix=".parquet")
    client.fget_object(BUCKET_RAW, OBJETO_RAW, tmp_raw)
    df = pd.read_parquet(tmp_raw)
    os.remove(tmp_raw)
    print(f"  ✅ {len(df):,} filas × {len(df.columns)} columnas cargadas\n")

    print("🔄 Generando tablas de dimensión...\n")

    # ─────────────────────────────────────────────────────────────
    # DIM_TIEMPO
    # ─────────────────────────────────────────────────────────────
    cols_t = cols_ok(df, [
        "FlightDate","Year","Quarter","Month",
        "DayofMonth","DayOfWeek","DepTimeBlk","ArrTimeBlk"
    ])
    dim_tiempo = (df[cols_t]
                  .drop_duplicates(subset=["FlightDate"])
                  .reset_index(drop=True))
    dim_tiempo.insert(0, "pk_tiempo", range(1, len(dim_tiempo)+1))
    subir(client, dim_tiempo, "dim_tiempo", BUCKET_DIMS)

    # ─────────────────────────────────────────────────────────────
    # DIM_AEROLINEA
    # ─────────────────────────────────────────────────────────────
    cols_a = cols_ok(df, [
        "Reporting_Airline","IATA_CODE_Reporting_Airline","DOT_ID_Reporting_Airline"
    ])
    dim_aerolinea = (df[cols_a]
                     .drop_duplicates(subset=["Reporting_Airline"])
                     .reset_index(drop=True))
    dim_aerolinea.insert(0, "pk_aerolinea", range(1, len(dim_aerolinea)+1))
    subir(client, dim_aerolinea, "dim_aerolinea", BUCKET_DIMS)

    # ─────────────────────────────────────────────────────────────
    # DIM_AEROPUERTO (role-playing: misma tabla para origen y destino)
    # ─────────────────────────────────────────────────────────────
    rename_orig = {
        "OriginAirportID":"AirportID","OriginAirportSeqID":"AirportSeqID",
        "OriginCityMarketID":"CityMarketID","Origin":"AirportCode",
        "OriginCityName":"CityName","OriginState":"State",
        "OriginStateName":"StateName","OriginWac":"Wac"
    }
    rename_dest = {
        "DestAirportID":"AirportID","DestAirportSeqID":"AirportSeqID",
        "DestCityMarketID":"CityMarketID","Dest":"AirportCode",
        "DestCityName":"CityName","DestState":"State",
        "DestStateName":"StateName","DestWac":"Wac"
    }
    cols_orig = cols_ok(df, list(rename_orig.keys()))
    cols_dest = cols_ok(df, list(rename_dest.keys()))

    df_orig = df[cols_orig].rename(columns=rename_orig)
    df_dest = df[cols_dest].rename(columns=rename_dest)
    dim_aeropuerto = (pd.concat([df_orig, df_dest])
                      .drop_duplicates(subset=["AirportCode"])
                      .reset_index(drop=True))
    dim_aeropuerto.insert(0, "pk_aeropuerto", range(1, len(dim_aeropuerto)+1))
    subir(client, dim_aeropuerto, "dim_aeropuerto", BUCKET_DIMS)

    # ─────────────────────────────────────────────────────────────
    # DIM_AVION
    # ─────────────────────────────────────────────────────────────
    cols_av = cols_ok(df, ["Tail_Number","DistanceGroup","Distance"])
    dim_avion = (df[cols_av]
                 .drop_duplicates(subset=["Tail_Number"])
                 .reset_index(drop=True))
    dim_avion.insert(0, "pk_avion", range(1, len(dim_avion)+1))
    subir(client, dim_avion, "dim_avion", BUCKET_DIMS)

    # ─────────────────────────────────────────────────────────────
    # DIM_RETRASO_CAUSA
    # ─────────────────────────────────────────────────────────────
    cols_rc = cols_ok(df, [
        "CarrierDelay","WeatherDelay","NASDelay",
        "SecurityDelay","LateAircraftDelay","TotalAddGTime","LongestAddGTime"
    ])
    dim_retraso = (df[cols_rc].drop_duplicates().reset_index(drop=True))
    dim_retraso.insert(0, "pk_retraso_causa", range(1, len(dim_retraso)+1))
    dim_retraso["descripcion"] = "Retraso registrado"

    fila_sin_retraso = {col: 0 for col in cols_rc}
    fila_sin_retraso.update({"pk_retraso_causa": 0, "descripcion": "Sin retraso"})
    dim_retraso = pd.concat(
        [pd.DataFrame([fila_sin_retraso]), dim_retraso], ignore_index=True
    )
    subir(client, dim_retraso, "dim_retraso_causa", BUCKET_DIMS)

    # ─────────────────────────────────────────────────────────────
    # DIM_CANCELACION
    # ─────────────────────────────────────────────────────────────
    cols_can = cols_ok(df, ["Cancelled","CancellationCode","Diverted","FirstDepTime"])
    dim_cancelacion = (df[cols_can]
                       .drop_duplicates(subset=["Cancelled","CancellationCode","Diverted"])
                       .reset_index(drop=True))
    dim_cancelacion.insert(0, "pk_cancelacion", range(1, len(dim_cancelacion)+1))
    dim_cancelacion["descripcion"] = "Evento registrado"

    fila_normal = {
        "Cancelled": 0, "CancellationCode": "No aplica",
        "Diverted": 0, "FirstDepTime": 0,
        "pk_cancelacion": 0, "descripcion": "Vuelo normal"
    }
    dim_cancelacion = pd.concat(
        [pd.DataFrame([fila_normal]), dim_cancelacion], ignore_index=True
    )
    subir(client, dim_cancelacion, "dim_cancelacion", BUCKET_DIMS)

    # ─────────────────────────────────────────────────────────────
    # DIM_DISTANCIA
    # ─────────────────────────────────────────────────────────────
    cols_dis = cols_ok(df, ["Distance","DistanceGroup","CRSElapsedTime","ActualElapsedTime"])
    dim_distancia = (df[cols_dis]
                     .drop_duplicates(subset=["DistanceGroup"])
                     .reset_index(drop=True))
    dim_distancia.insert(0, "pk_distancia", range(1, len(dim_distancia)+1))
    subir(client, dim_distancia, "dim_distancia", BUCKET_DIMS)

    # ─────────────────────────────────────────────────────────────
    # DIM_DESVIO
    # ─────────────────────────────────────────────────────────────
    cols_dev = cols_ok(df, [
        "DivAirportLandings","DivReachedDest","DivActualElapsedTime",
        "DivArrDelay","DivDistance","Div1Airport","Div1TailNum"
    ])
    dim_desvio = (df[cols_dev]
                  .drop_duplicates(subset=cols_ok(df, ["DivAirportLandings","Div1Airport"]))
                  .reset_index(drop=True))
    dim_desvio.insert(0, "pk_desvio", range(1, len(dim_desvio)+1))
    dim_desvio["descripcion"] = "Desvío registrado"

    fila_sin_desvio = {col: 0 for col in cols_dev}
    fila_sin_desvio.update({
        "Div1Airport": "No aplica", "Div1TailNum": "No aplica",
        "pk_desvio": 0, "descripcion": "Sin desvío"
    })
    dim_desvio = pd.concat(
        [pd.DataFrame([fila_sin_desvio]), dim_desvio], ignore_index=True
    )
    subir(client, dim_desvio, "dim_desvio", BUCKET_DIMS)

    # ─────────────────────────────────────────────────────────────
    # DIM_HORARIO
    # ─────────────────────────────────────────────────────────────
    cols_hor = cols_ok(df, [
        "CRSDepTime","DepTime","DepDelay","DepDelayMinutes",
        "CRSArrTime","ArrTime","ArrDelay","ArrDelayMinutes"
    ])
    dim_horario = (df[cols_hor]
                   .drop_duplicates(subset=["CRSDepTime"])
                   .reset_index(drop=True))
    dim_horario.insert(0, "pk_horario", range(1, len(dim_horario)+1))
    subir(client, dim_horario, "dim_horario", BUCKET_DIMS)

    # ─────────────────────────────────────────────────────────────
    # DIM_CLASIFICACION_RETRASO (junk dimension)
    # ─────────────────────────────────────────────────────────────
    cols_cl = cols_ok(df, [
        "DepDel15","ArrDel15","DepartureDelayGroups","ArrivalDelayGroups"
    ])
    dim_clasificacion = (df[cols_cl].drop_duplicates().reset_index(drop=True))
    dim_clasificacion.insert(0, "pk_clasificacion", range(1, len(dim_clasificacion)+1))
    subir(client, dim_clasificacion, "dim_clasificacion_retraso", BUCKET_DIMS)

    # ─────────────────────────────────────────────────────────────
    # DIM_RUTA
    # ─────────────────────────────────────────────────────────────
    cols_ruta = cols_ok(df, [
        "Origin","Dest","Distance","DistanceGroup",
        "OriginCityName","DestCityName"
    ])
    dim_ruta = (df[cols_ruta]
                .drop_duplicates(subset=["Origin","Dest"])
                .reset_index(drop=True))
    dim_ruta.rename(columns={"Origin":"OriginCode","Dest":"DestCode"}, inplace=True)
    dim_ruta.insert(0, "pk_ruta", range(1, len(dim_ruta)+1))
    subir(client, dim_ruta, "dim_ruta", BUCKET_DIMS)

    # ─────────────────────────────────────────────────────────────
    # FACT_VUELO — usando map() en vez de merge() (nunca multiplica filas)
    # ─────────────────────────────────────────────────────────────
    print("\n🔄 Generando tabla de hechos con map()...\n")

    fact = df.copy()

    lookup_tiempo = dict(zip(dim_tiempo["FlightDate"], dim_tiempo["pk_tiempo"]))
    fact["fk_tiempo"] = df["FlightDate"].map(lookup_tiempo).fillna(0).astype(int)

    lookup_aer = dict(zip(dim_aerolinea["Reporting_Airline"], dim_aerolinea["pk_aerolinea"]))
    fact["fk_aerolinea"] = df["Reporting_Airline"].map(lookup_aer).fillna(0).astype(int)

    lookup_apto = dict(zip(dim_aeropuerto["AirportCode"], dim_aeropuerto["pk_aeropuerto"]))
    if "Origin" in df.columns:
        fact["fk_aeropuerto_origen"] = df["Origin"].map(lookup_apto).fillna(0).astype(int)
    if "Dest" in df.columns:
        fact["fk_aeropuerto_destino"] = df["Dest"].map(lookup_apto).fillna(0).astype(int)

    lookup_av = dict(zip(dim_avion["Tail_Number"], dim_avion["pk_avion"]))
    fact["fk_avion"] = df["Tail_Number"].map(lookup_av).fillna(0).astype(int)

    lookup_ruta = dict(zip(
        dim_ruta["OriginCode"].astype(str) + "_|_" + dim_ruta["DestCode"].astype(str),
        dim_ruta["pk_ruta"]
    ))
    if "Origin" in df.columns and "Dest" in df.columns:
        fact["fk_ruta"] = (
            df["Origin"].astype(str) + "_|_" + df["Dest"].astype(str)
        ).map(lookup_ruta).fillna(0).astype(int)

    lookup_dis = dict(zip(dim_distancia["DistanceGroup"], dim_distancia["pk_distancia"]))
    if "DistanceGroup" in df.columns:
        fact["fk_distancia"] = df["DistanceGroup"].map(lookup_dis).fillna(0).astype(int)

    lookup_hor = dict(zip(dim_horario["CRSDepTime"], dim_horario["pk_horario"]))
    if "CRSDepTime" in df.columns:
        fact["fk_horario"] = df["CRSDepTime"].map(lookup_hor).fillna(0).astype(int)

    lookup_can = dict(zip(
        dim_cancelacion["Cancelled"].astype(str) + "_|_" +
        dim_cancelacion["CancellationCode"].astype(str) + "_|_" +
        dim_cancelacion["Diverted"].astype(str),
        dim_cancelacion["pk_cancelacion"]
    ))
    if all(c in df.columns for c in ["Cancelled","CancellationCode","Diverted"]):
        fact["fk_cancelacion"] = (
            df["Cancelled"].astype(str) + "_|_" +
            df["CancellationCode"].astype(str) + "_|_" +
            df["Diverted"].astype(str)
        ).map(lookup_can).fillna(0).astype(int)

    if cols_cl:
        lookup_cl = dict(zip(
            key_str(dim_clasificacion, cols_cl),
            dim_clasificacion["pk_clasificacion"]
        ))
        fact["fk_clasificacion_retraso"] = (
            key_str(df, cols_cl).map(lookup_cl).fillna(0).astype(int)
        )

    if cols_rc:
        lookup_rc = dict(zip(
            key_str(dim_retraso[cols_rc], cols_rc),
            dim_retraso["pk_retraso_causa"]
        ))
        fact["fk_retraso_causa"] = key_str(df, cols_rc).map(lookup_rc).fillna(0).astype(int)

    cols_desvio_key = cols_ok(df, ["DivAirportLandings","Div1Airport"])
    if cols_desvio_key:
        lookup_dev = dict(zip(
            key_str(dim_desvio[cols_desvio_key], cols_desvio_key),
            dim_desvio["pk_desvio"]
        ))
        fact["fk_desvio"] = key_str(df, cols_desvio_key).map(lookup_dev).fillna(0).astype(int)

    metricas = cols_ok(df, [
        "AirTime","Distance","Flights","ActualElapsedTime",
        "CRSElapsedTime","TaxiIn","TaxiOut"
    ])
    fks = [c for c in fact.columns if c.startswith("fk_")]
    fact_vuelo = fact[fks + metricas].copy()
    fact_vuelo.insert(0, "pk_vuelo", range(1, len(fact_vuelo)+1))

    subir(client, fact_vuelo, "fact_vuelo", BUCKET_DIMS)

    print(f"\n{'='*57}")
    print(f"  ✅ TRANSFORMACIÓN COMPLETA")
    print(f"  fact_vuelo: {len(fact_vuelo):,} filas")
    print(f"  Bucket destino: {BUCKET_DIMS}")
    print(f"  Verifica en: http://localhost:9001")
    print(f"{'='*57}")


if __name__ == "__main__":
    main()
