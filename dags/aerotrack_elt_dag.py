"""
AeroTrack Analytics -- DAG de Airflow: Pipeline ELT
====================================================
Que hace: Orquesta el pipeline ELT con 3 tareas:
    [extract]   ? PocketBase ? Parquet local
    [load]      ? Parquet local ? MinIO (aerotrack-raw)
    [transform] ? aerotrack-raw ? modelo estrella + 7 agregaciones ? aerotrack-dims

El horario se lee de la Airflow Variable `pipeline_schedule`.
  - "manual" o vacio  ? schedule=None (solo manual)
  - preset (@daily, @hourly, @weekly) o expresion cron ? se usa directo

Las funciones importadas usan config.py (tambien en dags/) que
detecta automaticamente si corre en Docker y ajusta las URLs.

UI: http://localhost:8080 ? busca "aerotrack_elt_pipeline"
"""

from __future__ import annotations

from datetime import timedelta

from aerotrack_tasks import extract_pipeline, load_pipeline, transform_pipeline
from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.utils.dates import days_ago


def _get_schedule() -> str | None:
    """Lee pipeline_schedule de Airflow Variables.
    Retorna None para manual, o el valor directo para presets/cron."""
    raw = Variable.get("pipeline_schedule", default_var="manual")
    if not raw or raw.strip() == "" or raw.strip() == "manual":
        return None
    return raw.strip()


def _on_failure(context: dict) -> None:
    ti = context.get("task_instance")
    exception = context.get("exception")
    print("FALLO EN EL PIPELINE")
    print(f"   DAG  : {ti.dag_id}")
    print(f"   Tarea: {ti.task_id}")
    print(f"   Error: {exception}")


@dag(
    dag_id="aerotrack_elt_pipeline",
    description="ELT: PocketBase ? Parquet ? MinIO (aerotrack-raw) ? modelo estrella (aerotrack-dims)",
    schedule=_get_schedule(),
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=4),
    default_args={
        "owner": "aerotrack",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": _on_failure,
    },
    tags=["aerotrack", "elt", "pocketbase", "minio"],
)
def aerotrack_elt():
    """
    Pipeline ELT de AeroTrack Analytics.

    extract ? load ? transform

    Imports resueltos en /opt/airflow/dags/ (en sys.path de Airflow):
      - aerotrack_tasks  ? dags/aerotrack_tasks.py
      - config           ? dags/config.py  (detecta Docker automaticamente)
    """

    @task(task_id="extract", execution_timeout=timedelta(hours=2))
    def extract() -> str:
        return extract_pipeline()

    @task(task_id="load", execution_timeout=timedelta(minutes=30))
    def load(parquet_path: str) -> None:
        load_pipeline(parquet_path)

    @task(task_id="transform", execution_timeout=timedelta(hours=2))
    def transform() -> None:
        transform_pipeline()

    parquet_path = extract()
    load_task = load(parquet_path)
    transform_task = transform()
    load_task >> transform_task


dag_instance = aerotrack_elt()
