# config.py — Configuración global de AeroTrack Analytics

import os
from dotenv import load_dotenv

# Carga .env para desarrollo local (no-op en Docker donde los vars vienen de docker-compose)
load_dotenv()

# ── MinIO ──────────────────────────────────────────────────────────────────
# Dentro de Docker: MINIO_URL_DOCKER=minio:9000 (inyectado por docker-compose)
# En local:        MINIO_URL=localhost:9000 (desde .env)
MINIO_ENDPOINT = os.getenv("MINIO_URL_DOCKER", os.getenv("MINIO_URL", "localhost:9000"))
MINIO_ACCESS   = os.getenv("MINIO_ACCESS",  "admin")
MINIO_SECRET   = os.getenv("MINIO_SECRET",  "admin1234")
MINIO_BUCKET   = os.getenv("MINIO_BUCKET_DIMS", "aerotrack-dims")
SECURE         = False

# ── Tablas disponibles con sus PKs ─────────────────────────────────────────
TABLAS: dict[str, dict] = {
    "fact_vuelo": {
        "pk": "pk_vuelo",
        "label": "Vuelos",
        "icon": "bi-airplane",
    },
    "dim_tiempo": {
        "pk": "pk_tiempo",
        "label": "Tiempo",
        "icon": "bi-calendar3",
    },
    "dim_aerolinea": {
        "pk": "pk_aerolinea",
        "label": "Aerolíneas",
        "icon": "bi-building",
    },
    "dim_aeropuerto": {
        "pk": "pk_aeropuerto",
        "label": "Aeropuertos",
        "icon": "bi-geo-alt",
    },
    "dim_avion": {
        "pk": "pk_avion",
        "label": "Aviones",
        "icon": "bi-send",
    },
    "dim_retraso_causa": {
        "pk": "pk_retraso_causa",
        "label": "Causas de Retraso",
        "icon": "bi-exclamation-triangle",
    },
    "dim_cancelacion": {
        "pk": "pk_cancelacion",
        "label": "Cancelaciones",
        "icon": "bi-x-circle",
    },
    "dim_distancia": {
        "pk": "pk_distancia",
        "label": "Distancia",
        "icon": "bi-rulers",
    },
    "dim_desvio": {
        "pk": "pk_desvio",
        "label": "Desvíos",
        "icon": "bi-signpost-split",
    },
    "dim_horario": {
        "pk": "pk_horario",
        "label": "Horarios",
        "icon": "bi-clock",
    },
    "dim_clasificacion_retraso": {
        "pk": "pk_clasificacion",
        "label": "Clasif. Retraso",
        "icon": "bi-bar-chart-steps",
    },
    "dim_ruta": {
        "pk": "pk_ruta",
        "label": "Rutas",
        "icon": "bi-map",
    },
}

PAGE_SIZE = 50
