"""Cliente async para la API REST de Airflow."""

import httpx

from app.config import AIRFLOW_PASSWORD, AIRFLOW_URL, AIRFLOW_USER

DAG_ID = "aerotrack_elt_pipeline"
_AUTH = (AIRFLOW_USER, AIRFLOW_PASSWORD)
_TIMEOUT = 15


async def trigger_dag(conf: dict | None = None) -> dict:
    url = f"{AIRFLOW_URL}/api/v1/dags/{DAG_ID}/dagRuns"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json={"conf": conf or {}}, auth=_AUTH)
        resp.raise_for_status()
        return resp.json()


async def get_dag_runs(limit: int = 20) -> list[dict]:
    url = f"{AIRFLOW_URL}/api/v1/dags/{DAG_ID}/dagRuns"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(url, params={"limit": limit, "order_by": "-execution_date"}, auth=_AUTH)
        resp.raise_for_status()
        return resp.json().get("dag_runs", [])


async def get_task_instances(dag_run_id: str) -> list[dict]:
    url = f"{AIRFLOW_URL}/api/v1/dags/{DAG_ID}/dagRuns/{dag_run_id}/taskInstances"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(url, auth=_AUTH)
        resp.raise_for_status()
        return resp.json().get("task_instances", [])


async def get_task_log(dag_run_id: str, task_id: str, attempt: int = 1) -> str:
    url = f"{AIRFLOW_URL}/api/v1/dags/{DAG_ID}/dagRuns/{dag_run_id}/taskInstances/{task_id}/logs/{attempt}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, auth=_AUTH)
        if not resp.is_success:
            return f"No se pudo obtener el log (status {resp.status_code})."
        return resp.text


async def get_dag_status() -> dict:
    """Retorna el estado del Ultimo dag_run o un dict vacio si no hay ejecuciones."""
    runs = await get_dag_runs(limit=1)
    if not runs:
        return {"state": "no_runs", "dag_run_id": None}
    latest = runs[0]
    tasks = []
    try:
        tasks = await get_task_instances(latest["dag_run_id"])
    except Exception:
        pass
    return {**latest, "task_instances": tasks}


async def get_variable(key: str) -> str | None:
    """Obtiene el valor de una Airflow Variable por su clave."""
    url = f"{AIRFLOW_URL}/api/v1/variables/{key}"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(url, auth=_AUTH)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json().get("value")


async def set_variable(key: str, value: str) -> dict:
    """Crea o actualiza una Airflow Variable. Retorna la respuesta JSON."""
    url = f"{AIRFLOW_URL}/api/v1/variables/{key}"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.patch(url, json={"key": key, "value": value}, auth=_AUTH)
        if resp.status_code == 404:
            resp = await client.post(f"{AIRFLOW_URL}/api/v1/variables", json={"key": key, "value": value}, auth=_AUTH)
        resp.raise_for_status()
        return resp.json()


async def clear_task_instance(dag_id: str, dag_run_id: str, task_id: str) -> dict:
    """Limpia una task instance especifica para que Airflow la reintente."""
    url = f"{AIRFLOW_URL}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/clearTaskInstances"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json={"dry_run": False, "task_ids": [task_id]}, auth=_AUTH)
        resp.raise_for_status()
        return resp.json()
