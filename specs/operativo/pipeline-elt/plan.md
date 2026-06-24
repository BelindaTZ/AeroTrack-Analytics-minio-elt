# Plan de Implementación — Pipeline ELT Operativo

**Módulo:** Pipeline ELT  
**Paquete:** `app/pipeline_elt/`, `dags/`  
**Prefix:** `/pipeline`  
**CUs cubiertos:** CU-O05, CU-O06, CU-O07, CU-O08  
**Fuente:** código leído el 2026-06-22

---

## Archivos DAG

| Archivo | Propósito |
|---|---|
| `dags/aerotrack_elt_dag.py` | Definición del DAG con TaskFlow API, parámetros y dependencias |
| `dags/aerotrack_tasks.py` | Implementación de las 3 funciones del pipeline (extract, load, transform) |
| `dags/config.py` | Configuración para el entorno Airflow (detección Docker, URLs, colección PocketBase) |

---

## DAG: aerotrack_elt_pipeline

**DAG ID:** `aerotrack_elt_pipeline`  
**Archivo:** `dags/aerotrack_elt_dag.py`

### Parámetros operacionales

| Parámetro | Valor implementado | Archivo / línea |
|---|---|---|
| `dag_id` | `"aerotrack_elt_pipeline"` | `aerotrack_elt_dag.py:49` |
| `max_active_runs` | `1` | `aerotrack_elt_dag.py:54` |
| `dagrun_timeout` | `timedelta(hours=4)` | `aerotrack_elt_dag.py:55` |
| `retries` (default_args) | `2` | `aerotrack_elt_dag.py:58` |
| `retry_delay` | `timedelta(minutes=5)` | `aerotrack_elt_dag.py:59` |
| `catchup` | `False` | `aerotrack_elt_dag.py:53` |
| `on_failure_callback` | `_on_failure` (print a stdout) | `aerotrack_elt_dag.py:60` |

### Tareas (@task decoradas con TaskFlow API)

| task_id | Función | Timeout | Qué hace |
|---|---|---|---|
| `extract` | `extract_pipeline()` en `aerotrack_tasks.py` | 2 horas | Lee todos los registros de PocketBase colección `vuelos_raw` y escribe `vuelos_raw_{timestamp}.parquet` en `/tmp`. Retorna la ruta local del archivo. Usa escritura incremental por lotes para evitar OOM. |
| `load` | `load_pipeline(parquet_path)` en `aerotrack_tasks.py` | 30 minutos | Sube el Parquet local a MinIO `aerotrack-raw/vuelos_raw.parquet`. Elimina el archivo local. |
| `transform` | `transform_pipeline()` en `aerotrack_tasks.py` | 2 horas | Descarga `vuelos_raw.parquet` desde `aerotrack-raw`, genera el modelo estrella (`fact_vuelo` + 11 `dim_*`) y 10 tablas `agg_*`, sube todo a `aerotrack-dims`. |

### Dependencias de tareas

```python
parquet_path = extract()      # extract retorna str (ruta local)
load_task = load(parquet_path) # load recibe la ruta
transform_task = transform()   # transform es independiente de load en parámetros
load_task >> transform_task    # pero transform espera que load termine
```

Flujo efectivo: `extract → load → transform` (secuencial).

### Lectura y sincronización del schedule

```python
def _get_schedule() -> str | None:
    raw = Variable.get("pipeline_schedule", default_var="manual")
    if not raw or raw.strip() == "" or raw.strip() == "manual":
        return None      # → schedule=None → solo ejecución manual
    return raw.strip()   # → preset (@daily, @hourly) o expresión cron
```

**Airflow Variable:** `pipeline_schedule`  
**Comportamiento si Variable no existe:** default `"manual"` → `schedule=None` (solo manual)  
**FastAPI lee el schedule desde PocketBase:** `configuracion_sistema` con `clave="pipeline_schedule"` (en `app/pipeline_elt/router.py:44-49`) para mostrarlo en UI, pero el DAG lo lee de Airflow Variables al inicializarse.

### Staging en PocketBase

- **Colección fuente:** `vuelos_raw` (definida en `dags/config.py:44` como `PB_COLLECTION`)
- La tarea `extract` lee todos los registros de esta colección y los convierte a Parquet
- No hay escritura a PocketBase desde el DAG (solo lectura en extract)

---

## Endpoints FastAPI de monitoreo (prefix `/pipeline`)

| Método | Path | Permiso | Retorna | Descripción |
|---|---|---|---|---|
| GET | `/pipeline` | `pipeline_elt:ver` | HTML | Panel principal: estado actual + historial últimas 5 ejecuciones + schedule label |
| POST | `/pipeline/trigger` | `pipeline_elt:ejecutar` | Redirect | Dispara el DAG vía `af.trigger_dag()`. Registra auditoría. Despacha webhook `pipeline_completado`. |
| GET | `/pipeline/estado` | `pipeline_elt:ver` | JSON | Último dag_run con task_instances |
| GET | `/pipeline/estado-full` | `pipeline_elt:ver` | JSON | `{estado, historial}` — usado por polling cada 10s del frontend |
| GET | `/pipeline/historial` | `pipeline_elt:ver` | HTML | Últimas 50 ejecuciones desde Airflow API |
| GET | `/pipeline/logs/{run_id}/{task_id}` | `pipeline_elt:ver` | HTML | Log de una tarea (attempt=1 por defecto) + lista de tareas de la ejecución |
| POST | `/pipeline/logs/{run_id}/{task_id}/reintentar` | `pipeline_elt:ejecutar` | Redirect | Clear task instance. Registra auditoría. |

---

## Mecanismo de reintento quirúrgico

```python
# app/pipeline_elt/router.py:124-133
@router.post("/logs/{run_id}/{task_id}/reintentar")
async def reintentar_tarea(request, run_id, task_id):
    user = _perm_exec(request)
    await af.clear_task_instance(af.DAG_ID, run_id, task_id)
    audit.registrar(user["sub"], user["email"], "reintentar", "pipeline_elt",
                    recurso_tipo="task_instance", recurso_id=f"{run_id}/{task_id}")
```

**API Airflow llamada:** `POST /api/v1/dags/{dag_id}/dagRuns/{run_id}/clearTaskInstances`  
**Payload:** `{"dry_run": false, "task_ids": [task_id]}`  
**Efecto:** Solo esa tarea se marca para re-ejecución; las tareas aguas arriba que ya completaron no se repiten.

---

## Cliente Airflow (app/pipeline_elt/clients/airflow_client.py)

Funciones invocadas en `router.py`:

| Función | Descripción |
|---|---|
| `af.DAG_ID` | Constante `"aerotrack_elt_pipeline"` |
| `af.get_dag_status()` | Último dag_run con task_instances (estado de cada tarea) |
| `af.get_dag_runs(limit=N)` | Historial de N últimas ejecuciones |
| `af.trigger_dag()` | POST a Airflow API para crear nuevo dag_run. Retorna `{dag_run_id, ...}` |
| `af.get_task_log(run_id, task_id, attempt)` | Log de texto de la tarea |
| `af.get_task_instances(run_id)` | Lista de tareas de una ejecución |
| `af.clear_task_instance(dag_id, run_id, task_id)` | Limpia (reintenta) una tarea específica |

---

## Acciones registradas en auditoría

| Acción | Trigger | Módulo | recurso_tipo | Detalle |
|---|---|---|---|---|
| `ejecutar` | POST /pipeline/trigger | `pipeline_elt` | `dag` | `dag_run_id=...` |
| `reintentar` | POST /logs/{run_id}/{task_id}/reintentar | `pipeline_elt` | `task_instance` | `{run_id}/{task_id}` |

---

## Webhook a socios API

En `POST /pipeline/trigger`, tras el dispatch exitoso:
```python
dispatch_event("pipeline_completado", {
    "dag_id": af.DAG_ID,
    "dag_run_id": result.get("dag_run_id", ""),
    "estado": "iniciado",
    "timestamp": datetime.now(timezone.utc).isoformat(),
})
```
Dispatcha evento a los socios suscritos a `pipeline_completado`. Implementado en `app/socios_api/webhook_dispatcher.py`.

---

## Principios de la constitución aplicados

| Principio | Aplicación en este módulo |
|---|---|
| I (separación de capas) | extract lee de PocketBase/staging; transform escribe en aerotrack-dims; FastAPI nunca lee de aerotrack-raw |
| V (auditoría) | `audit.registrar()` en trigger y reintentar |
| VI (degradación) | try/except en `panel()` — si Airflow no responde, muestra `estado={"state": "error"}` sin romper la página |
| IX (timeouts y reintentos) | `dagrun_timeout=4h`, `extract 2h`, `load 30min`, `transform 2h`, `retries=2`, `retry_delay=5min` |
| VIII (paginación) | `limit=50` en historial, `limit=5` en panel |
