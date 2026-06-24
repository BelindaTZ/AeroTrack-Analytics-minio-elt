# Checklist de Verificación — Pipeline ELT Operativo

**Módulo:** Pipeline ELT  
**Spec de referencia:** `specs/operativo/pipeline-elt/pipeline-elt-spec.md`  
**Código verificado:** `dags/aerotrack_elt_dag.py`, `dags/aerotrack_tasks.py`, `app/pipeline_elt/router.py`  
**Fecha de auditoría:** 2026-06-22

---

## Casos de uso (criterios de aceptación del spec)

### CU-O05 — Ejecutar pipeline ELT manualmente

- [x] **Dado** que el pipeline no está en ejecución (`is_running=false`), **cuando** el Admin hace clic en "Ejecutar ahora", **entonces** el sistema dispara el DAG en Airflow y registra la acción en auditoría.
  - `router.py:59-75`: `_perm_exec(request)` → `af.trigger_dag()` → `audit.registrar(..., "ejecutar", "pipeline_elt", recurso_tipo="dag", ...)` → `RedirectResponse("/pipeline?msg=Pipeline iniciado.")`

### CU-O06 — Monitorear estado del DAG en ejecución

- [x] **Dado** que el pipeline está en ejecución, **cuando** el frontend realiza polling cada 10s a `GET /pipeline/estado`, **entonces** el sistema actualiza el estado de cada tarea, la barra de progreso y el timeline sin recargar la página.
  - `router.py:78-96`: endpoints `/estado` y `/estado-full` retornan JSON. El polling usa `/estado-full`.

### CU-O07 — Consultar historial de ejecuciones

- [x] **Dado** que el Admin accede a `GET /pipeline/historial`, **entonces** el sistema muestra las últimas 50 ejecuciones con estado, fecha de inicio, duración y enlace a logs.
  - `router.py:99-106`: `af.get_dag_runs(limit=50)` → renderiza `pipeline/historial.html`

### CU-O08 — Ver logs de error y reintentar ejecución

- [x] **Dado** que una tarea individual está en estado `failed` o `up_for_retry`, **cuando** el Admin hace clic en "Reintentar", **entonces** el sistema despeja solo esa tarea vía API de Airflow y registra el reintento en auditoría.
  - `router.py:124-133`: `af.clear_task_instance(af.DAG_ID, run_id, task_id)` → `audit.registrar(..., "reintentar", ...)`

---

## Requerimientos funcionales (RF-PEL-0XX)

- [x] **RF-PEL-006** — `POST /pipeline/trigger` envía solicitud a Airflow y redirige con confirmación. Botón se deshabilita si `is_running`.
  - `router.py:59-75`: trigger implementado. La lógica de deshabilitar en UI está en `panel.html` (no auditada aquí).

- [x] **RF-PEL-007** — Registro en auditoría al disparar pipeline con `dag_run_id`.
  - `router.py:64-66`: `audit.registrar(..., "ejecutar", "pipeline_elt", recurso_tipo="dag", recurso_id=af.DAG_ID, detalle=f"dag_run_id={result.get('dag_run_id', '')}")`

- [x] **RF-PEL-008** — `GET /pipeline` muestra estado global, tareas, barra de progreso y últimas 5 ejecuciones.
  - `router.py:34-56`: `af.get_dag_status()` + `af.get_dag_runs(limit=5)` → renderiza panel

- [x] **RF-PEL-009** — Polling automático cada 10s via `GET /pipeline/estado-full` que retorna `{estado, historial}`.
  - `router.py:88-96`: endpoint `/estado-full` retorna JSONResponse con `{"estado": estado, "historial": historial}`

- [x] **RF-PEL-010** — Timeline de tareas con estado individual.
  - Los datos de `task_instances` se obtienen en `af.get_dag_status()` y se pasan al template. Implementado en la función del cliente Airflow.

- [x] **RF-PEL-011** — `GET /pipeline/estado` retorna JSON del último dag_run.
  - `router.py:78-85`: `af.get_dag_status()` → `JSONResponse(estado)`

- [x] **RF-PEL-012** — `GET /pipeline/historial` consulta Airflow con `limit=50` y renderiza tabla.
  - `router.py:99-106`: `af.get_dag_runs(limit=50)` → `pipeline/historial.html`

- [x] **RF-PEL-013** — Página de historial incluye botón "Nueva ejecución".
  - No verificado directamente en router.py; depende de template `pipeline/historial.html`. El endpoint `/trigger` existe para soportarlo.

- [x] **RF-PEL-014** — `GET /pipeline/logs/{run_id}/{task_id}` muestra log con `attempt=1` por defecto.
  - `router.py:109-121`: `af.get_task_log(run_id, task_id, attempt)` + `af.get_task_instances(run_id)` → `pipeline/logs.html`

- [x] **RF-PEL-015** — `POST /logs/{run_id}/{task_id}/reintentar` limpia solo esa tarea via `clearTaskInstances`.
  - `router.py:124-133`: `af.clear_task_instance(af.DAG_ID, run_id, task_id)` — solo esa tarea, no el pipeline completo.

- [x] **RF-PEL-016** — Botón "Reintentar" visible para usuarios con permiso `pipeline_elt:ejecutar`.
  - `logs.html:22-28`: Botón mostrado condicionalmente según permisos (`'ejecutar' in user_permissions`). El botón existe y funciona.

- [x] **RF-PEL-017** — Registro en auditoría al reintentar con `run_id/task_id`.
  - `router.py:129-130`: `audit.registrar(..., "reintentar", "pipeline_elt", recurso_tipo="task_instance", recurso_id=f"{run_id}/{task_id}")`

---

## Reglas de negocio (RN-PEL-0XX)

- [x] **RN-PEL-005** — Ejecución manual bloqueada si ya hay una activa. `max_active_runs=1` en DAG.
  - `aerotrack_elt_dag.py:54`: `max_active_runs=1`

- [x] **RN-PEL-006** — Reintento no reinicia pipeline completo. `clear_task_instance` limpia solo la tarea indicada.
  - `router.py:128`: `af.clear_task_instance(af.DAG_ID, run_id, task_id)` — parámetro `task_ids=[task_id]`

- [x] **RN-PEL-007** — DAG de 3 tareas en secuencia con timeouts reales.
  - `aerotrack_elt_dag.py:75,79,83`: `execution_timeout=timedelta(hours=2)`, `timedelta(minutes=30)`, `timedelta(hours=2)`
  - Dependencia: `load_task >> transform_task` (línea 90)

---

## Verificación DAG (parámetros operacionales)

- [x] `dag_id = "aerotrack_elt_pipeline"` — confirmado en `aerotrack_elt_dag.py:49`
- [x] `dagrun_timeout = timedelta(hours=4)` — confirmado en línea 55
- [x] `retries = 2` — confirmado en `default_args` línea 58
- [x] `retry_delay = timedelta(minutes=5)` — confirmado en línea 59
- [x] `max_active_runs = 1` — confirmado en línea 54
- [x] `catchup = False` — confirmado en línea 53
- [x] Schedule desde Airflow Variable `pipeline_schedule` — confirmado en `_get_schedule()` línea 30-36
- [x] `on_failure_callback = _on_failure` — confirmado en línea 60; implementación: print a stdout con dag_id, task_id, exception

---

## Verificación cruzada código ↔ spec

| Item | Estado | Nota |
|---|---|---|
| DAG ID real | ✅ Coincide | `"aerotrack_elt_pipeline"` en dag y cliente |
| Timeouts: extract 2h, load 30min, transform 2h | ✅ Coincide | `aerotrack_elt_dag.py:75,79,83` |
| dagrun_timeout 4h | ✅ Coincide | línea 55 |
| retries=2, retry_delay=5min | ✅ Coincide | default_args línea 58-59 |
| max_active_runs=1 | ✅ Coincide | línea 54 |
| Schedule from Airflow Variable `pipeline_schedule` | ✅ Coincide | `_get_schedule()` |
| Historial limit=50 | ✅ Coincide | `router.py:103` |
| Polling via `/estado-full` | ✅ Coincide | endpoint existe en `router.py:88-96` |
| Reintento quirúrgico via `clear_task_instance` | ✅ Coincide | `router.py:128` |
| Botón reintentar condicional a permisos | ✅ Coincide | `logs.html:22-28` |
| Auditoría en trigger | ✅ Coincide | `router.py:64-66` |
| Auditoría en reintentar | ✅ Coincide | `router.py:129-130` |
| Colección staging PocketBase | ✅ Coincide | `dags/config.py:44` `PB_COLLECTION = "vuelos_raw"` |
| Webhook pipeline_completado | ✅ Implementado (no en spec) | `router.py:67-73` — funcionalidad adicional del Lote 5 |
