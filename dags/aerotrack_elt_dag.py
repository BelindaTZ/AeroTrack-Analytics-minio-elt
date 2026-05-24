"""
AeroTrack Analytics — DAG de Airflow: Pipeline ELT
====================================================
Qué hace: Orquesta el pipeline ELT diario con exactamente 2 tareas:
    [extract] → PocketBase → Parquet → MinIO (aerotrack-raw)
    [transform] → aerotrack-raw → modelo estrella → aerotrack-dims

Las funciones importadas usan config.py (también en dags/) que
detecta automáticamente si corre en Docker y ajusta las URLs.

UI: http://localhost:8080 → busca "aerotrack_elt_pipeline"
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

# Importar las funciones del pipeline (config.py las hace Docker-aware)
from aerotrack_tasks import extract_pipeline, transform_pipeline


def _on_failure(context: dict) -> None:
    ti        = context.get("task_instance")
    exception = context.get("exception")
    print(f"❌ FALLO EN EL PIPELINE")
    print(f"   DAG  : {ti.dag_id}")
    print(f"   Tarea: {ti.task_id}")
    print(f"   Error: {exception}")


@dag(
    dag_id="aerotrack_elt_pipeline",
    description="ELT: PocketBase → Parquet → MinIO (aerotrack-raw) → modelo estrella (aerotrack-dims)",
    schedule=None,            # Solo ejecución manual; cambia a '@daily' para automatizar
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=4),   # Mata el DagRun completo si supera 4h
    default_args={
        "owner":       "aerotrack",
        "retries":     2,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": _on_failure,
    },
    tags=["aerotrack", "elt", "pocketbase", "minio"],
)
def aerotrack_elt():
    """
    Pipeline ELT de AeroTrack Analytics.

    extract → transform

    Imports resueltos en /opt/airflow/dags/ (en sys.path de Airflow):
      - aerotrack_tasks  → dags/aerotrack_tasks.py
      - config           → dags/config.py  (detecta Docker automáticamente)
    """

    # execution_timeout por tarea sobrescribe default_args
    @task(task_id="extract", execution_timeout=timedelta(hours=2))
    def extract() -> None:
        """Extrae de PocketBase (10 workers), convierte a Parquet y sube a aerotrack-raw."""
        extract_pipeline()

    @task(task_id="transform", execution_timeout=timedelta(hours=1))
    def transform() -> None:
        """Descarga el Parquet crudo y genera el modelo estrella en aerotrack-dims."""
        transform_pipeline()

    extract() >> transform()


dag_instance = aerotrack_elt()
