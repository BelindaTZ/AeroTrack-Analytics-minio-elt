from fastapi import APIRouter

router = APIRouter()


@router.post("/trigger")
async def trigger_dag():
    # CU-10: Disparar ejecución del DAG
    pass


@router.get("/estado")
async def estado_dag():
    # CU-11: Monitorear estado del pipeline
    pass


@router.get("/historial")
async def historial_dag():
    # CU-12: Ver historial de ejecuciones
    pass


@router.get("/logs/{run_id}")
async def logs_dag(run_id: str):
    # CU-13: Ver logs de ejecución
    pass
