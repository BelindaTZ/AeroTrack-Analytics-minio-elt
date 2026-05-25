import pandas as pd
from minio import Minio
from io import BytesIO
from app.config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET_DIMS


def _cliente() -> Minio:
    return Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)


def listar_tablas() -> list[str]:
    client = _cliente()
    objetos = client.list_objects(MINIO_BUCKET_DIMS)
    return [obj.object_name for obj in objetos if obj.object_name.endswith(".parquet")]


def leer_tabla(nombre: str) -> pd.DataFrame:
    client = _cliente()
    response = client.get_object(MINIO_BUCKET_DIMS, nombre)
    return pd.read_parquet(BytesIO(response.read()))
