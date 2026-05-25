from fastapi import APIRouter

router = APIRouter()


@router.get("/tablas")
async def listar_tablas():
    # CU-14: Listar tablas del modelo dimensional en MinIO
    pass


@router.get("/tablas/{nombre}")
async def ver_tabla(nombre: str):
    # CU-15: Ver datos de tabla Parquet
    pass


@router.post("/tablas/{nombre}/validar")
async def validar_tabla(nombre: str):
    # CU-16: Validar integridad del modelo dimensional
    pass
