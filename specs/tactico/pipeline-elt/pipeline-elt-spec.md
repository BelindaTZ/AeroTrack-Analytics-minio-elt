# Especificación Táctica — Pipeline ELT

**Módulo:** Pipeline ELT
**Prefijo:** PEL
**Código fuente:** `app/configuracion/panel.py` (configuración), `dags/aerotrack_elt_dag.py` (programación), `dags/config.py` (constantes)
**Casos de uso cubiertos:** CU-T06 (Configurar y programar ejecución del pipeline)
**Actor:** Administrador

---

## Funcionalidad 1: Configurar y programar ejecución del pipeline (CU-T06)

Configuración del horario y parámetros del pipeline ELT desde el panel de configuración (`app/configuracion/panel.py`, grupo "pipeline"). El cronograma se sincroniza entre PocketBase y Airflow vía API REST.

### RF-PEL-001 — Seleccionar tipo de programación
El panel de configuración ofrece un selector con opciones: Manual, @daily (Cada día), @hourly (Cada hora), @weekly (Semanal), @monthly (Mensual), @yearly (Anual), o expresión cron personalizada. Las opciones están definidas en `_PRESETS_SCHEDULE` dentro de `app/configuracion/panel.py`.

### RF-PEL-002 — Validar expresión cron con croniter
Al guardar, el valor del horario se valida mediante `_validar_schedule()` que usa `croniter.is_valid()`. Si el valor no es un preset conocido ni una expresión cron válida, retorna mensaje de error descriptivo.

### RF-PEL-003 — Persistir programación en PocketBase
Tras validar, el valor se guarda en la colección `configuracion_sistema` de PocketBase con clave `pipeline_schedule`. La persistencia usa el mecanismo genérico `_save_group()` del panel de configuración.

### RF-PEL-004 — Sincronizar con Airflow vía API REST
Tras guardar en PocketBase, el sistema sincroniza el valor con Airflow mediante `af.set_variable("pipeline_schedule", valor)` que usa la API REST de Airflow (`PATCH /api/v1/variables/` o `POST` si no existe). Esto actualiza la Variable de Airflow que el DAG lee al ser parseado.

### RF-PEL-005 — DAG lee programación desde Airflow Variable
El DAG `aerotrack_elt_pipeline` en `dags/aerotrack_elt_dag.py` lee la Variable `pipeline_schedule` mediante `Variable.get("pipeline_schedule", default_var="manual")`. Si el valor es `"manual"` o vacío, establece `schedule=None` (solo ejecución manual). Si es un preset (`@daily`, `@hourly`, etc.) o expresión cron, lo usa directamente como `schedule` del DAG.

### RF-PEL-006 — Cambio reflejado en hasta ~300s
El DAG se parsea en cada ciclo del scheduler de Airflow (~300s por defecto). Tras actualizar la Variable, el nuevo horario toma efecto en el siguiente ciclo de parseo. No requiere reinicio del scheduler ni reescritura del archivo DAG.

### RF-PEL-007 — Configurar parámetros del pipeline
Además del horario, el panel de configuración expone estos parámetros almacenados en PocketBase (`configuracion_sistema`):
- `pipeline_batch_size` (int, default 5000): tamaño de lote para carga desde PocketBase
- `pipeline_max_workers` (int, default 10): hilos concurrentes para extracción
- `pipeline_reintentos` (int, default 3): reintentos por fallo en tareas

> **Nota:** Los valores de `pipeline_batch_size`, `pipeline_max_workers` y `pipeline_reintentos` están definidos en la semilla de configuración. El DAG actualmente usa constantes internas (`dags/aerotrack_tasks.py`: `PB_PAGE_SIZE=500`, `MAX_WORKERS=10`, `BATCH_SIZE=200`; `dags/config.py`: `BATCH_SIZE=5000`) que no leen estos valores en tiempo de ejecución.

### RNF-PEL-001 — No reescritura del archivo DAG
El cambio de horario se realiza exclusivamente mediante Airflow Variables, no modificando el archivo `dags/aerotrack_elt_dag.py`. Esto evita errores de sintaxis en el DAG y permite cambios sin deploy.

### RNF-PEL-002 — Validación de programación con croniter
Toda expresión cron personalizada es validada con la librería `croniter` antes de persistirse. Valores inválidos son rechazados con mensaje de error.

### RNF-PEL-003 — Timeouts en llamadas a API de Airflow
Las llamadas a la API de Airflow tienen timeout de 15 segundos para operaciones generales y 30 segundos para consulta de logs.

### RNF-PEL-004 — Credenciales de Airflow por entorno
Las URL y credenciales de Airflow (`AIRFLOW_URL`, `AIRFLOW_ADMIN_USER`, `AIRFLOW_ADMIN_PASSWORD`) se configuran exclusivamente mediante variables de entorno, sin valores por defecto en código — Principio IV de la constitución.

---

## Reglas de negocio

### RN-PEL-001 — Horario "manual" no ejecuta pipeline automáticamente
Si `pipeline_schedule` es `"manual"` o vacío, el DAG tiene `schedule=None` y solo se ejecuta mediante trigger manual. No se ejecuta en ningún horario prefijado.

### RN-PEL-002 — Una sola ejecución activa a la vez
El DAG tiene `max_active_runs=1`. Si el pipeline ya está en ejecución, no se inicia una nueva instancia hasta que la actual termine o falle. Esto protege la integridad del proceso ELT secuencial.

### RN-PEL-003 — Tiempo máximo de ejecución: 4 horas
El DAG tiene `dagrun_timeout=timedelta(hours=4)`. Si una ejecución excede este límite, Airflow la marca como fallida automáticamente.

### RN-PEL-004 — Reintentos: 2 por tarea (automático de Airflow)
Cada tarea del DAG tiene `retries=2` con `retry_delay=5min`. Los reintentos son gestionados internamente por Airflow sin intervención del usuario, hasta agotar los intentos.

### RN-PEL-005 — Pipeline secuencial: extract → load → transform
Las 3 tareas se ejecutan en orden estricto: `extract >> load >> transform`. Cada tarea espera la finalización exitosa de la anterior para comenzar.

### RN-PEL-006 — Fallo de sincronización informado explícitamente
Si la sincronización del horario configurado con Airflow falla, el sistema debe informarlo explícitamente al usuario, indicando que PocketBase quedó actualizado pero Airflow no, en lugar de fallar silenciosamente.

---

## Historias de usuario

- Como Administrador, quiero configurar el horario de ejecución del pipeline desde la interfaz web, para automatizar la actualización de datos sin editar archivos de código ni reiniciar servicios.

---

## Objetivo

Configurar la programación horaria y los parámetros de ejecución del pipeline ELT, sincronizando la configuración entre PocketBase y Airflow mediante su API REST.

---

## Escenarios

### Camino feliz
1. El Administrador accede al panel de configuración del pipeline (grupo `pipeline`) y visualiza los valores actuales: horario, `batch_size`, `timeout_mins` y `max_retries`.
2. Selecciona el preset `@daily` en el selector de horario y ajusta `batch_size` a 5000.
3. `POST /configuracion/pipeline` valúa la expresión cron con la biblioteca `croniter`.
4. El sistema persiste los valores en PocketBase (colección `configuracion_sistema`) y sincroniza con Airflow mediante `PATCH /api/v1/dags/aerotrack_elt` con el nuevo `schedule`.
5. En el siguiente ciclo de parseo del scheduler de Airflow (~300s), el DAG adopta el nuevo horario.

### Manejo de errores
- **Expresión cron inválida:** Si `croniter` no puede parsear la expresión, el sistema retorna un mensaje descriptivo y no persiste el cambio.
- **Fallo de sincronización Airflow:** Si PocketBase se actualiza correctamente pero la llamada a la API de Airflow falla, el sistema muestra un mensaje explícito al usuario con el error recibido.
- **Timeout en API de Airflow:** Si la llamada a Airflow excede los 15s, se retorna un error de conexión y la sincronización queda pendiente para el próximo intento.

---

## Criterios de aceptación

- **CU-T06:** Dado que el Administrador configura un horario o parámetro en el panel del pipeline, cuando el valor es válido, entonces el sistema lo persiste en PocketBase, lo sincroniza con Airflow vía API REST e informa al usuario del resultado de cada paso.

---

## Dependencias

- **Seguridad:** Autenticación JWT y autorización con permiso `pipeline_elt:configurar`.
- **Airflow:** API REST (`/api/v1/dags/aerotrack_elt`) y scheduler con ciclo de parseo de ~300s.
- **PocketBase:** Colección `configuracion_sistema` para persistencia de parámetros del pipeline.

---

## Casos de uso relacionados

- CU-T06 (Configurar programación y parámetros del pipeline)

---

## Fuera de alcance

- Modificación directa del archivo DAG desde la interfaz web.
- Configuración de múltiples pipelines independientes.
- Notificaciones por email cuando el pipeline falla.
- Monitoreo en tiempo real de la ejecución (cubierto en la especificación operativa).
- Gestión de conexiones a bases de datos externas.
