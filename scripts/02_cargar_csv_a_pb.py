"""
AeroTrack Analytics — Script 02: Cargar CSV a PocketBase
=========================================================
Qué hace:
  1. AUTO-DETECCIÓN: si ya hay datos en PocketBase, no recarga (usa --force para recargar).
  2. CARGA EN LOTES: lee el CSV en chunks de 50.000 filas, divide en sub-lotes de
     BATCH_SIZE (5.000) y los inserta con 8 hilos concurrentes.
  3. REINTENTOS: cada sub-lote reintenta 3 veces antes de registrar el error en errors.log.

Cómo ejecutar:
    python scripts/02_cargar_csv_a_pb.py            # Carga normal (salta si ya hay datos)
    python scripts/02_cargar_csv_a_pb.py --force    # Borra todo y recarga desde cero
"""

import logging
import math
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import pandas as pd
import requests

# ── Config ───────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
import config

PB_BASE_URL   = config.PB_BASE_URL
PB_EMAIL      = config.PB_EMAIL
PB_PASSWORD   = config.PB_PASSWORD
PB_COLLECTION = config.PB_COLLECTION
BATCH_SIZE    = config.BATCH_SIZE
CSV_FILE_PATH = config.CSV_FILE_PATH

CHUNK_SIZE     = 50_000   # Filas que pandas lee por iteración
NUM_HILOS      = 8
MAX_REINTENTOS = 3

COLUMNAS = [
    "FlightDate", "Year", "Quarter", "Month", "DayofMonth", "DayOfWeek",
    "DepTimeBlk", "ArrTimeBlk", "Reporting_Airline",
    "IATA_CODE_Reporting_Airline", "DOT_ID_Reporting_Airline",
    "Flight_Number_Reporting_Airline", "OriginAirportID", "OriginAirportSeqID",
    "OriginCityMarketID", "Origin", "OriginCityName", "OriginState",
    "OriginStateName", "OriginWac", "DestAirportID", "DestAirportSeqID",
    "DestCityMarketID", "Dest", "DestCityName", "DestState", "DestStateName",
    "DestWac", "Tail_Number", "CRSDepTime", "DepTime", "DepDelay",
    "DepDelayMinutes", "CRSArrTime", "ArrTime", "ArrDelay", "ArrDelayMinutes",
    "DepDel15", "ArrDel15", "DepartureDelayGroups", "ArrivalDelayGroups",
    "TaxiOut", "TaxiIn", "AirTime", "Flights", "Distance", "DistanceGroup",
    "CRSElapsedTime", "ActualElapsedTime", "Cancelled", "CancellationCode",
    "Diverted", "FirstDepTime", "CarrierDelay", "WeatherDelay", "NASDelay",
    "SecurityDelay", "LateAircraftDelay", "TotalAddGTime", "LongestAddGTime",
    "DivAirportLandings", "DivReachedDest", "DivActualElapsedTime",
    "DivArrDelay", "DivDistance", "Div1Airport", "Div1TailNum",
]

# Thread-local: cada hilo tiene su propia Session HTTP
_thread_local = threading.local()


def _get_session() -> requests.Session:
    if not hasattr(_thread_local, "session"):
        _thread_local.session = requests.Session()
    return _thread_local.session


# ── Autenticación ─────────────────────────────────────────────

def autenticar() -> str:
    resp = requests.post(
        f"{PB_BASE_URL}/api/admins/auth-with-password",
        json={"identity": PB_EMAIL, "password": PB_PASSWORD},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["token"]


# ── Auto-detección ────────────────────────────────────────────

def contar_registros(token: str) -> int:
    headers = {"Authorization": token}
    resp = requests.get(
        f"{PB_BASE_URL}/api/collections/{PB_COLLECTION}/records",
        headers=headers,
        params={"perPage": 1},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("totalItems", 0)


def forzar_reinicio(token: str) -> None:
    """Elimina la colección y la recrea vacía (mucho más rápido que borrar fila a fila)."""
    headers = {"Authorization": token}
    print("  Obteniendo esquema actual de la colección...")
    resp = requests.get(
        f"{PB_BASE_URL}/api/collections/{PB_COLLECTION}", headers=headers, timeout=15
    )
    resp.raise_for_status()
    col_data   = resp.json()
    col_id     = col_data["id"]
    col_schema = col_data.get("schema", [])

    requests.delete(
        f"{PB_BASE_URL}/api/collections/{col_id}", headers=headers, timeout=30
    ).raise_for_status()
    print("  ✅ Colección eliminada")

    requests.post(
        f"{PB_BASE_URL}/api/collections",
        headers=headers,
        json={"name": PB_COLLECTION, "type": "base", "schema": col_schema},
        timeout=30,
    ).raise_for_status()
    print(f"  ✅ Colección '{PB_COLLECTION}' recreada vacía")


# ── Limpieza de registros ─────────────────────────────────────

def limpiar_registro(fila: dict) -> dict:
    limpio = {}
    for clave, valor in fila.items():
        if isinstance(valor, float):
            if math.isnan(valor):
                limpio[clave] = None
            elif valor == int(valor):
                limpio[clave] = int(valor)
            else:
                limpio[clave] = valor
        elif isinstance(valor, str) and valor.strip() == "":
            limpio[clave] = None
        else:
            limpio[clave] = valor
    return limpio


# ── Inserción individual (ejecutada en hilo) ──────────────────

def _insertar_registro(args: tuple) -> bool:
    registro, headers = args
    url     = f"{PB_BASE_URL}/api/collections/{PB_COLLECTION}/records"
    session = _get_session()
    try:
        resp = session.post(url, json=registro, headers=headers, timeout=15)
        return resp.status_code == 200
    except Exception:
        return False


# ── Procesamiento de un sub-lote con reintentos ───────────────

def procesar_sublote(
    registros: list,
    headers: dict,
    num_lote: int,
    total_lotes: int,
    error_logger: logging.Logger,
) -> tuple[int, int]:
    """Inserta un sub-lote con reintentos. Devuelve (exitosos, fallidos)."""
    args_list = [(r, headers) for r in registros]

    for intento in range(1, MAX_REINTENTOS + 1):
        exitosos = fallidos = 0

        with ThreadPoolExecutor(max_workers=NUM_HILOS) as executor:
            futuros = {executor.submit(_insertar_registro, a): i for i, a in enumerate(args_list)}
            for futuro in as_completed(futuros):
                if futuro.result():
                    exitosos += 1
                else:
                    fallidos += 1

        if fallidos == 0:
            return exitosos, 0

        if intento < MAX_REINTENTOS:
            print(
                f"\n  ⚠️  Lote {num_lote}/{total_lotes}: {fallidos} errores "
                f"— reintento {intento}/{MAX_REINTENTOS - 1}...",
                flush=True,
            )
            time.sleep(2 * intento)
        else:
            error_logger.error(
                "Lote %d/%d: %d registros fallaron tras %d intentos",
                num_lote, total_lotes, fallidos, MAX_REINTENTOS,
            )

    return exitosos, fallidos


# ── Main ──────────────────────────────────────────────────────

def main() -> None:
    print("=" * 62)
    print("  AeroTrack Analytics — Carga de CSV a PocketBase")
    print("=" * 62)

    usar_force = "--force" in sys.argv

    # 1. Autenticar
    print("\n[1/5] Autenticando en PocketBase...")
    try:
        token = autenticar()
    except Exception as e:
        print(f"❌ No se pudo conectar a PocketBase en {PB_BASE_URL}")
        print(f"   Error: {e}")
        sys.exit(1)
    headers = {"Authorization": token}
    print(f"  ✅ Autenticado  ({PB_BASE_URL})")

    # 2. Auto-detección
    print("\n[2/5] Verificando registros existentes en PocketBase...")
    total_existente = contar_registros(token)

    if total_existente > 0 and not usar_force:
        print(
            f"  Ya existen {total_existente:,} registros en PocketBase. "
            f"Saltando carga."
        )
        print("  Usa --force para borrar todo y recargar.")
        sys.exit(0)

    if total_existente > 0 and usar_force:
        print(f"  --force: se borrarán {total_existente:,} registros existentes...")
        forzar_reinicio(token)
        token   = autenticar()   # Token nuevo tras recrear colección
        headers = {"Authorization": token}

    # 3. Contar filas del CSV para calcular total de lotes
    print(f"\n[3/5] Contando filas en CSV: {CSV_FILE_PATH}")
    with open(CSV_FILE_PATH, "rb") as f:
        total_csv_rows = sum(1 for _ in f) - 1  # -1 por cabecera
    total_lotes = math.ceil(total_csv_rows / BATCH_SIZE)
    print(f"  {total_csv_rows:,} filas → {total_lotes:,} lotes de {BATCH_SIZE:,}")

    # 4. Configurar logger de errores
    logging.basicConfig(
        filename="errors.log",
        filemode="a",
        level=logging.ERROR,
        format="%(asctime)s %(message)s",
    )
    error_logger = logging.getLogger("carga_errors")

    # 5. Carga en chunks + sub-lotes con concurrencia
    print(f"\n[4/5] Cargando con {NUM_HILOS} hilos concurrentes...")
    inicio          = datetime.now()
    total_exitosos  = 0
    total_fallidos  = 0
    num_lote        = 0
    filas_enviadas  = 0

    for chunk in pd.read_csv(
        CSV_FILE_PATH,
        encoding="latin1",
        usecols=lambda col: col in set(COLUMNAS),
        low_memory=False,
        chunksize=CHUNK_SIZE,
    ):
        registros_chunk = [limpiar_registro(r) for r in chunk.to_dict(orient="records")]

        for i in range(0, len(registros_chunk), BATCH_SIZE):
            sublote   = registros_chunk[i : i + BATCH_SIZE]
            num_lote += 1
            filas_enviadas += len(sublote)

            print(
                f"  Lote {num_lote}/{total_lotes} — "
                f"{filas_enviadas:,}/{total_csv_rows:,} filas",
                end="\r",
                flush=True,
            )

            ex, fa = procesar_sublote(sublote, headers, num_lote, total_lotes, error_logger)
            total_exitosos += ex
            total_fallidos += fa

            # Renovar token cada 100 lotes (~8-10 min de trabajo)
            if num_lote % 100 == 0:
                token   = autenticar()
                headers = {"Authorization": token}

    # 6. Resumen
    duracion  = max((datetime.now() - inicio).seconds, 1)
    velocidad = total_exitosos / duracion

    print(f"\n\n{'=' * 62}")
    print(f"  RESUMEN DE CARGA")
    print(f"{'=' * 62}")
    print(f"  ✅ Exitosos  : {total_exitosos:,}")
    print(f"  ❌ Fallidos  : {total_fallidos:,}")
    print(f"  ⏱  Duración  : {duracion} segundos")
    print(f"  ⚡ Velocidad : {velocidad:.0f} registros/segundo")

    if total_fallidos:
        print(f"\n  ⚠️  {total_fallidos:,} registros no se pudieron insertar.")
        print("     Revisa errors.log para ver qué lotes fallaron.")

    print(f"\n✅ Script completado. Ejecuta 03_extraer_pb_a_minio.py")


if __name__ == "__main__":
    main()
