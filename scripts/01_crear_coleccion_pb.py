"""
AeroTrack Analytics — Script 01: Crear colección en PocketBase
===============================================================
Qué hace: Se conecta a la API de administración de PocketBase y crea
          la colección con el esquema adecuado para nuestro dataset.
          Si la colección ya existe, no hace nada.

Cómo ejecutar:
    python scripts/01_crear_coleccion_pb.py
"""

import sys
import os

import requests

sys.path.insert(0, os.path.dirname(__file__))
import config

PB_URL          = config.PB_BASE_URL
PB_EMAIL        = config.PB_EMAIL
PB_PASSWORD     = config.PB_PASSWORD
COLLECTION_NAME = config.PB_COLLECTION

SCHEMA = [
    # ── TIEMPO ─────────────────────────────────────────────
    {"name": "FlightDate",   "type": "text",   "required": False},
    {"name": "Year",         "type": "number", "required": False},
    {"name": "Quarter",      "type": "number", "required": False},
    {"name": "Month",        "type": "number", "required": False},
    {"name": "DayofMonth",   "type": "number", "required": False},
    {"name": "DayOfWeek",    "type": "number", "required": False},
    {"name": "DepTimeBlk",   "type": "text",   "required": False},
    {"name": "ArrTimeBlk",   "type": "text",   "required": False},

    # ── AEROLÍNEA ───────────────────────────────────────────
    {"name": "Reporting_Airline",              "type": "text",   "required": False},
    {"name": "IATA_CODE_Reporting_Airline",    "type": "text",   "required": False},
    {"name": "DOT_ID_Reporting_Airline",       "type": "number", "required": False},
    {"name": "Flight_Number_Reporting_Airline","type": "number", "required": False},

    # ── AEROPUERTO ORIGEN ───────────────────────────────────
    {"name": "OriginAirportID",    "type": "number", "required": False},
    {"name": "OriginAirportSeqID", "type": "number", "required": False},
    {"name": "OriginCityMarketID", "type": "number", "required": False},
    {"name": "Origin",             "type": "text",   "required": False},
    {"name": "OriginCityName",     "type": "text",   "required": False},
    {"name": "OriginState",        "type": "text",   "required": False},
    {"name": "OriginStateName",    "type": "text",   "required": False},
    {"name": "OriginWac",          "type": "number", "required": False},

    # ── AEROPUERTO DESTINO ──────────────────────────────────
    {"name": "DestAirportID",    "type": "number", "required": False},
    {"name": "DestAirportSeqID", "type": "number", "required": False},
    {"name": "DestCityMarketID", "type": "number", "required": False},
    {"name": "Dest",             "type": "text",   "required": False},
    {"name": "DestCityName",     "type": "text",   "required": False},
    {"name": "DestState",        "type": "text",   "required": False},
    {"name": "DestStateName",    "type": "text",   "required": False},
    {"name": "DestWac",          "type": "number", "required": False},

    # ── AVIÓN ───────────────────────────────────────────────
    {"name": "Tail_Number", "type": "text", "required": False},

    # ── HORARIO ─────────────────────────────────────────────
    {"name": "CRSDepTime",      "type": "number", "required": False},
    {"name": "DepTime",         "type": "number", "required": False},
    {"name": "DepDelay",        "type": "number", "required": False},
    {"name": "DepDelayMinutes", "type": "number", "required": False},
    {"name": "CRSArrTime",      "type": "number", "required": False},
    {"name": "ArrTime",         "type": "number", "required": False},
    {"name": "ArrDelay",        "type": "number", "required": False},
    {"name": "ArrDelayMinutes", "type": "number", "required": False},

    # ── JUNK DIMENSION (clasificación de retraso) ───────────
    {"name": "DepDel15",              "type": "number", "required": False},
    {"name": "ArrDel15",              "type": "number", "required": False},
    {"name": "DepartureDelayGroups",  "type": "number", "required": False},
    {"name": "ArrivalDelayGroups",    "type": "number", "required": False},

    # ── MEDIDAS DEL VUELO ───────────────────────────────────
    {"name": "TaxiOut",           "type": "number", "required": False},
    {"name": "TaxiIn",            "type": "number", "required": False},
    {"name": "AirTime",           "type": "number", "required": False},
    {"name": "Flights",           "type": "number", "required": False},
    {"name": "Distance",          "type": "number", "required": False},
    {"name": "DistanceGroup",     "type": "number", "required": False},
    {"name": "CRSElapsedTime",    "type": "number", "required": False},
    {"name": "ActualElapsedTime", "type": "number", "required": False},

    # ── CANCELACIÓN ─────────────────────────────────────────
    {"name": "Cancelled",       "type": "number", "required": False},
    {"name": "CancellationCode","type": "text",   "required": False},
    {"name": "Diverted",        "type": "number", "required": False},
    {"name": "FirstDepTime",    "type": "number", "required": False},

    # ── CAUSA DE RETRASO ────────────────────────────────────
    {"name": "CarrierDelay",      "type": "number", "required": False},
    {"name": "WeatherDelay",      "type": "number", "required": False},
    {"name": "NASDelay",          "type": "number", "required": False},
    {"name": "SecurityDelay",     "type": "number", "required": False},
    {"name": "LateAircraftDelay", "type": "number", "required": False},
    {"name": "TotalAddGTime",     "type": "number", "required": False},
    {"name": "LongestAddGTime",   "type": "number", "required": False},

    # ── DESVÍO ──────────────────────────────────────────────
    {"name": "DivAirportLandings",   "type": "number", "required": False},
    {"name": "DivReachedDest",       "type": "number", "required": False},
    {"name": "DivActualElapsedTime", "type": "number", "required": False},
    {"name": "DivArrDelay",          "type": "number", "required": False},
    {"name": "DivDistance",          "type": "number", "required": False},
    {"name": "Div1Airport",          "type": "text",   "required": False},
    {"name": "Div1TailNum",          "type": "text",   "required": False},
]


def autenticar_admin() -> str:
    url = f"{PB_URL}/api/admins/auth-with-password"
    try:
        resp = requests.post(url, json={"identity": PB_EMAIL, "password": PB_PASSWORD}, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        print(f"❌ No se pudo conectar a PocketBase en {PB_URL}")
        print("   Verifica que el contenedor Docker esté corriendo.")
        sys.exit(1)
    print("✅ Autenticado en PocketBase como administrador")
    return resp.json()["token"]


def coleccion_existe(token: str) -> bool:
    headers = {"Authorization": token}
    resp = requests.get(f"{PB_URL}/api/collections/{COLLECTION_NAME}", headers=headers)
    return resp.status_code == 200


def crear_coleccion(token: str) -> None:
    headers = {"Authorization": token}
    payload = {"name": COLLECTION_NAME, "type": "base", "schema": SCHEMA}
    resp = requests.post(f"{PB_URL}/api/collections", headers=headers, json=payload, timeout=15)

    if resp.status_code == 200:
        print(f"✅ Colección '{COLLECTION_NAME}' creada con {len(SCHEMA)} campos")
        print(f"   Verifica en: {PB_URL}/_/#/collections")
    else:
        print(f"❌ Error al crear la colección: {resp.status_code}")
        print(f"   Respuesta: {resp.text}")
        sys.exit(1)


def main():
    print("=" * 55)
    print("  AeroTrack Analytics — Crear colección PocketBase")
    print("=" * 55)
    print(f"  URL: {PB_URL} | Colección: {COLLECTION_NAME}")

    token = autenticar_admin()

    if coleccion_existe(token):
        print(f"⚠️  La colección '{COLLECTION_NAME}' ya existe — no se sobrescribe.")
        print(f"   Si quieres recrearla, bórrala desde {PB_URL}/_/")
        return

    crear_coleccion(token)
    print("\n✅ Script completado. Ejecuta 02_cargar_csv_a_pb.py para cargar datos.")


if __name__ == "__main__":
    main()
