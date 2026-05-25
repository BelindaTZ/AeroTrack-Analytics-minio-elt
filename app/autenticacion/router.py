from fastapi import APIRouter

router = APIRouter()


@router.post("/login")
async def login():
    # CU-01: Autenticación con JWT
    pass


@router.post("/logout")
async def logout():
    # CU-02: Cierre de sesión
    pass


@router.get("/perfil")
async def perfil():
    # CU-03: Ver perfil
    pass
