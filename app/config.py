import os

IN_DOCKER = os.path.exists("/.dockerenv")

MINIO_ENDPOINT = "minio:9000" if IN_DOCKER else "localhost:9000"
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
MINIO_BUCKET_RAW = "aerotrack-raw"
MINIO_BUCKET_DIMS = "aerotrack-dims"

PB_URL = "http://pocketbase:8090" if IN_DOCKER else "http://localhost:8090"

AIRFLOW_URL = "http://airflow-webserver:8080" if IN_DOCKER else "http://localhost:8080"
AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")

SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
