import httpx
from app.config import AIRFLOW_URL, AIRFLOW_USER, AIRFLOW_PASSWORD

DAG_ID = "aerotrack_elt_pipeline"
_auth = (AIRFLOW_USER, AIRFLOW_PASSWORD)


async def trigger_dag(conf: dict = None) -> dict:
    url = f"{AIRFLOW_URL}/api/v1/dags/{DAG_ID}/dagRuns"
    async with httpx.AsyncClient() as client:
        resp = client.post(url, json={"conf": conf or {}}, auth=_auth)
        resp.raise_for_status()
        return resp.json()


async def get_dag_runs() -> list:
    url = f"{AIRFLOW_URL}/api/v1/dags/{DAG_ID}/dagRuns"
    async with httpx.AsyncClient() as client:
        resp = client.get(url, auth=_auth)
        resp.raise_for_status()
        return resp.json().get("dag_runs", [])


async def get_task_logs(dag_run_id: str, task_id: str) -> str:
    url = f"{AIRFLOW_URL}/api/v1/dags/{DAG_ID}/dagRuns/{dag_run_id}/taskInstances/{task_id}/logs/1"
    async with httpx.AsyncClient() as client:
        resp = client.get(url, auth=_auth)
        resp.raise_for_status()
        return resp.text
