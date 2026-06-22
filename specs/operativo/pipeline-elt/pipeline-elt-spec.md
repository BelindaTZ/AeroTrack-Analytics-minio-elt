# Especificación Operativa — Pipeline ELT

**Módulo:** Pipeline ELT
**Prefijo:** PEL
**Código fuente:** `app/pipeline_elt/router.py`, `app/pipeline_elt/clients/airflow_client.py`, `dags/aerotrack_elt_dag.py`
**Casos de uso cubiertos:** CU-O05 (Ejecutar pipeline ELT manualmente), CU-O06 (Monitorear estado del DAG en ejecución), CU-O07 (Consultar historial de ejecuciones), CU-O08 (Ver logs de error y reintentar ejecución)
**Actor:** Usuario autenticado

---

## Funcionalidad 1: Ejecutar pipeline ELT manualmente (CU-O05)

Trigger manual del DAG de Airflow desde `app/pipeline_elt/router.py` usando el cliente API REST `app/pipeline_elt/clients/airflow_client.py`.

### RF-PEL-021 — Trigger de ejecución manual
`POST /pipeline/trigger` envía una solicitud `POST /api/v1/dags/aerotrack_elt_pipeline/dagRuns` a la API de Airflow. El botón de trigger se deshabilita si el pipeline ya está en ejecución (`is_running`). Redirige a `/pipeline` con mensaje de confirmación.

### RF-PEL-022 — Registrar ejecución en auditoría
Al disparar el pipeline, se registra en auditoría con tipo `ejecutar`, recurso `dag`, detalle incluyendo el `dag_run_id` devuelto por Airflow.

---

## Funcionalidad 2: Monitorear estado del DAG en ejecución (CU-O06)

Seguimiento en tiempo real del estado del pipeline desde la interfaz principal (`GET /pipeline` y endpoints JSON).

### RF-PEL-023 — Mostrar estado actual del pipeline
`GET /pipeline` renderiza el panel principal que muestra: estado global del último `dag_run`, lista de tareas con su estado individual, barra de progreso, y últimas 5 ejecuciones. Los estados posibles del DAG son: `no_runs`, `running`, `queued`, `success`, `failed`.

### RF-PEL-024 — Polling automático cada 10 segundos
El frontend (`panel.html`) implementa un contador regresivo de 10s. Al llegar a 0, solicita `GET /pipeline/estado-full` que retorna JSON con `{estado, historial}`. Actualiza dinámicamente: título del hero, badge de estado, barra de progreso, timeline de tareas, y tabla de historial sin recargar la página.

### RF-PEL-025 — Timeline de tareas con estado individual
Cada tarea (`extract`, `load`, `transform`) se muestra con su estado (`running`, `success`, `failed`, `queued`, `skipped`, `none`) identificado por color y badge. Las tareas en ejecución muestran contador de tiempo transcurrido. Las tareas fallidas muestran enlace directo a logs.

### RF-PEL-026 — Consultar estado como JSON
`GET /pipeline/estado` retorna el último `dag_run` de Airflow con sus `task_instances` como JSON. Usado por el polling del frontend.

---

## Funcionalidad 3: Consultar historial de ejecuciones (CU-O07)

Visualización del historial de ejecuciones desde `app/pipeline_elt/router.py`.

### RF-PEL-027 — Mostrar historial de ejecuciones
`GET /pipeline/historial` consulta la API REST de Airflow (`GET /api/v1/dags/aerotrack_elt_pipeline/dagRuns?limit=50&order_by=-execution_date`) y renderiza una tabla con las últimas 50 ejecuciones, mostrando: Run ID, Estado, Inicio, Fin, y enlace a logs.

### RF-PEL-028 — Nueva ejecución desde historial
La página de historial incluye botón "Nueva ejecución" que postea a `/pipeline/trigger`, permitiendo disparar el pipeline sin volver al panel principal.

---

## Funcionalidad 4: Ver logs de error y reintentar ejecución (CU-O08)

Acceso a logs de tareas y reintento selectivo desde `app/pipeline_elt/router.py`.

### RF-PEL-029 — Ver logs de tarea específica
`GET /pipeline/logs/{run_id}/{task_id}` obtiene el log de una tarea específica (con número de intento por defecto `attempt=1`) desde la API de Airflow (`GET /api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/logs/{attempt}`) y lo muestra en vista con formato monospace. Muestra además navegación entre tareas de la misma ejecución.

### RF-PEL-030 — Reintentar tarea específica (no el pipeline completo)
`POST /pipeline/logs/{run_id}/{task_id}/reintentar` invoca `POST /api/v1/dags/{dag_id}/dagRuns/{run_id}/clearTaskInstances` de la API de Airflow con `{"dry_run": false, "task_ids": [task_id]}`. Solo despeja la tarea indicada, no reinicia el pipeline completo.

### RF-PEL-031 — Botón de reintento condicional al estado
El botón "Reintentar" solo se muestra cuando el estado de la tarea es `failed` o `up_for_retry` (validado en template con `if current_task.state in ('failed', 'up_for_retry')`). Previene reintentos innecesarios sobre tareas en ejecución o exitosas.

### RF-PEL-032 — Registrar reintento en auditoría
Al reintentar una tarea, se registra en auditoría con tipo `reintentar`, recurso `task_instance`, y detalle con `run_id/task_id`.

---

## Reglas de negocio

### RN-PEL-021 — Ejecución manual bloqueada si ya hay una activa
El botón "Ejecutar ahora" se deshabilita mientras el pipeline esté en estado `running` o `queued`. La restricción se aplica tanto en UI como a nivel de Airflow (`max_active_runs=1`).

### RN-PEL-022 — Reintento no reinicia pipeline completo
Al reintentar una tarea vía `clear_task_instance`, solo esa tarea se marca para re-ejecución. Las tareas aguas arriba que ya completaron no se repiten. La tarea reintentada espera a que sus dependencias estén disponibles (si la tarea anterior falló, debe reintentarse primero).

### RN-PEL-023 — DAG de 3 tareas en secuencia estricta
El pipeline ELT tiene 3 tareas: `extract` (PocketBase → Parquet, timeout 2h), `load` (Parquet → MinIO, timeout 30min), `transform` (raw → modelo estrella, timeout 2h). La dependencia es `extract >> load >> transform`, con timeout total del DAG de 4h.

---

## Historias de usuario

- Como Administrador, quiero disparar el pipeline manualmente, para actualizar los datos en momentos específicos según las necesidades del negocio.
- Como Administrador, quiero ver el estado en tiempo real de cada etapa del pipeline, para detectar fallas sin acceder directamente a Airflow.
- Como Administrador, quiero consultar el historial de las últimas 50 ejecuciones, para analizar patrones de fallo y rendimiento.
- Como Administrador, quiero reintentar una tarea fallida sin reiniciar el pipeline completo, para recuperar el proceso rápidamente sin perder el trabajo ya completado.

---

## Objetivo

Ejecutar el pipeline ELT manualmente, monitorear su estado en tiempo real, consultar el historial de ejecuciones y reintentar tareas fallidas sin reiniciar el proceso completo.

---

## Escenarios

### Camino feliz
1. El Admin hace clic en "Ejecutar ahora" en el panel del pipeline.
2. `POST /pipeline/trigger` dispara el DAG `aerotrack_elt` en Airflow y redirige al panel con un mensaje de confirmación.
3. El panel comienza a realizar polling cada 10s vía `GET /pipeline/estado`: las tareas `extract` → `load` → `transform` se marcan secuencialmente como `running` → `success`.
4. Todas las tareas completan exitosamente; el panel muestra estado "success" con la duración total.
5. El Admin consulta `GET /pipeline/historial` y visualiza las últimas 50 ejecuciones en una tabla paginada con estado, fecha de inicio, duración y enlace a logs.

### Manejo de errores
- **Pipeline ya en ejecución:** Si `GET /pipeline/estado` retorna `is_running=true`, el botón "Ejecutar ahora" permanece deshabilitado.
- **Tarea fallida:** El timeline muestra la tarea en rojo con un enlace a la vista de logs.
- **Reintento de tarea:** `POST /pipeline/logs/{run_id}/{task_id}/reintentar` despeja el estado de solo esa tarea mediante `POST /api/v1/dags/aerotrack_elt/clearTaskInstances` y registra el reintento en auditoría.
- **Timeout en consulta de logs:** Si la API de Airflow no responde en 30s, la vista de logs muestra un mensaje de error y permite reintentar la consulta.
- **DAG timeout de 4h:** Si la ejecución excede las 4h, Airflow la marca como `failed` automáticamente.

---

## Criterios de aceptación

- **CU-O05:** Dado que el pipeline no está en ejecución (`is_running=false`), cuando el Admin hace clic en "Ejecutar ahora", entonces el sistema dispara el DAG en Airflow y registra la acción en auditoría.
- **CU-O06:** Dado que el pipeline está en ejecución, cuando el frontend realiza polling cada 10s a `GET /pipeline/estado`, entonces el sistema actualiza el estado de cada tarea, la barra de progreso y el timeline sin recargar la página.
- **CU-O07:** Dado que el Admin accede a `GET /pipeline/historial`, entonces el sistema muestra las últimas 50 ejecuciones con estado, fecha de inicio, duración y enlace a logs.
- **CU-O08:** Dado que una tarea individual está en estado `failed` o `up_for_retry`, cuando el Admin hace clic en "Reintentar", entonces el sistema despeja solo esa tarea vía API de Airflow y registra el reintento en auditoría.

---

## Dependencias

- **Seguridad:** Autenticación JWT y autorización con permisos `pipeline_elt:ejecutar`, `pipeline_elt:ver`, `pipeline_elt:historial`, `pipeline_elt:logs`.
- **Airflow:** API REST para disparo del DAG, consulta de estado, historial de ejecuciones y limpieza de tareas.
- **Pipeline Táctico:** Configuración de programación y parámetros (CU-T06).

---

## Casos de uso relacionados

- CU-O05 (Ejecutar pipeline bajo demanda)
- CU-O06 (Monitorear ejecución en tiempo real)
- CU-O07 (Consultar historial de ejecuciones)
- CU-O08 (Ver logs y reintentar tareas fallidas)

---

## Fuera de alcance

- Reprogramación del horario del pipeline desde este módulo.
- Notificaciones automáticas por email cuando una ejecución falla.
- Cancelación de una ejecución en curso desde la interfaz.
- Comparación de rendimiento entre ejecuciones históricas.
- Edición de parámetros de extracción durante la ejecución.
