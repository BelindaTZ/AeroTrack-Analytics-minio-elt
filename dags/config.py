"""
AeroTrack Analytics — Configuración centralizada del pipeline ELT
=================================================================
Detecta si el proceso corre dentro de Docker y selecciona
automáticamente las URLs correctas (nombres de servicio vs localhost).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Carga .env desde la raíz del proyecto (no-op si no existe, p.ej. en Docker)
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

IN_DOCKER = os.path.exists("/.dockerenv")

# ── URLs según contexto ───────────────────────────────────────
MINIO_ENDPOINT = os.getenv("MINIO_URL_DOCKER", "minio:9000") if IN_DOCKER else os.getenv("MINIO_URL", "localhost:9000")
PB_BASE_URL = (
    os.getenv("PB_URL_DOCKER", "http://pocketbase:8090") if IN_DOCKER else os.getenv("PB_URL", "http://localhost:8090")
)
CSV_FILE_PATH = (
    os.getenv("CSV_PATH_DOCKER", "/opt/airflow/data/airline_2m.csv")
    if IN_DOCKER
    else os.getenv("CSV_PATH_LOCAL", "./data/airline_2m.csv")
)

# ── Credenciales MinIO ────────────────────────────────────────
MINIO_ACCESS = os.getenv("MINIO_ACCESS", "admin")
MINIO_SECRET = os.getenv("MINIO_SECRET", "admin1234")
MINIO_BUCKET_RAW = os.getenv("MINIO_BUCKET_RAW", "aerotrack-raw")
MINIO_BUCKET_DIMS = os.getenv("MINIO_BUCKET_DIMS", "aerotrack-dims")
MINIO_BUCKET_EXPORTS = os.getenv("MINIO_BUCKET_EXPORTS", "aerotrack-exports")

# ── Credenciales PocketBase ───────────────────────────────────
PB_EMAIL = os.getenv("PB_EMAIL", "")
PB_PASSWORD = os.getenv("PB_PASSWORD", "")
PB_COLLECTION = os.getenv("PB_COLLECTION", "vuelos_raw")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5000"))

# ── Seguridad JWT ─────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "60"))
