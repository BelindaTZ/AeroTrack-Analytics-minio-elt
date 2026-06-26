import os
import sys

from dotenv import load_dotenv

load_dotenv()

IN_DOCKER = os.path.exists("/.dockerenv")

# ── MinIO ─────────────────────────────────────────────────────────────────────
MINIO_ENDPOINT = os.getenv("MINIO_URL_DOCKER") if IN_DOCKER else os.getenv("MINIO_URL", "localhost:9000")
MINIO_PUBLIC_ENDPOINT = os.getenv("MINIO_PUBLIC_URL", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET", "admin1234")
MINIO_BUCKET_RAW = os.getenv("MINIO_BUCKET_RAW", "aerotrack-raw")
MINIO_BUCKET_DIMS = os.getenv("MINIO_BUCKET_DIMS", "aerotrack-dims")
MINIO_BUCKET_EXPORTS = os.getenv("MINIO_BUCKET_EXPORTS", "aerotrack-exports")

# ── PocketBase ────────────────────────────────────────────────────────────────
PB_URL = os.getenv("PB_URL_DOCKER") if IN_DOCKER else os.getenv("PB_URL", "http://localhost:8090")
PB_EMAIL = os.getenv("PB_EMAIL", "")
PB_PASSWORD = os.getenv("PB_PASSWORD", "")

# ── Airflow ───────────────────────────────────────────────────────────────────
AIRFLOW_URL = "http://airflow-webserver:8080" if IN_DOCKER else os.getenv("AIRFLOW_URL", "http://localhost:8080")
AIRFLOW_USER = os.getenv("AIRFLOW_ADMIN_USER", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_ADMIN_PASSWORD", "admin1234")

# ── JWT (RNF-SEG-012: SECRET_KEY obligatoria) ────────────────────────────────
_SECRET_KEY_RAW = os.getenv("SECRET_KEY", "")
if not _SECRET_KEY_RAW or _SECRET_KEY_RAW == "changeme":
    print(
        "\n[SECURITY] SECRET_KEY no está definida o usa el valor por defecto 'changeme'.\n"
        "           Define SECRET_KEY en tu archivo .env con una cadena aleatoria de al menos 32 caracteres.\n"
        '           Ejemplo: SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")\n',
        file=sys.stderr,
    )
    if not IN_DOCKER:
        _SECRET_KEY_RAW = "changeme"
    else:
        raise RuntimeError("SECRET_KEY obligatoria en producción. Define SECRET_KEY en .env con un valor seguro.")

SECRET_KEY = _SECRET_KEY_RAW
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "60"))
