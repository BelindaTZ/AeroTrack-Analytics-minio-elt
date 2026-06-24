# Especificación Operativa — Pipeline ELT

**Módulo:** Pipeline ELT
**Prefijo:** PEL
**Código fuente:** `app/pipeline_elt/router.py`, `app/pipeline_elt/clients/airflow_client.py`, `dags/aerotrack_elt_dag.py`
**Casos de uso cubiertos:** CU-O05 (Ejecutar pipeline ELT manualmente), CU-O06 (Monitorear estado del DAG en ejecución), CU-O07 (Consultar historial de ejecuciones), CU-O08 (Ver logs de error y reintentar ejecución)
**Actor:** Administrador

---
## Funcionalidad 1: Configurar y programar ejecución del pipeline (CU-T06)

- RF-PEL-001: El sistema debe permitir al Administrador definir el horario de ejecución del pipeline mediante presets (Manual, Diario, Cada hora, Semanal, Mensual, Anual) o una expresión cron personalizada, validada con croniter antes de guardar.

- RF-PEL-002: El sistema debe sincronizar el horario configurado con una Variable de Airflow (pipeline_schedule), sin modificar el archivo del DAG.

- RF-PEL-003: El sistema debe permitir configurar el tamaño de lote, número de procesos paralelos y reintentos de extracción (valores almacenados en PocketBase; el DAG actualmente usa constantes internas: MAX_WORKERS=10, BATCH_SIZE=200 páginas, retries=2 por tarea).

- RF-PEL-004: El sistema debe informar al Administrador que el cambio de horario puede tardar hasta el siguiente ciclo de refresco del scheduler de Airflow (~300 s).
---

## Funcionalidad 2: Ejecutar pipeline ELT manualmente (CU-O05)

Trigger manual del DAG de Airflow desde la interfaz web.

### RF-PEL-021 — Trigger de ejecución manual
El sistema debe permitir disparar el pipeline ELT manualmente. La opción de ejecución debe deshabilitarse si el pipeline ya está activo. Al completarse el disparo, el sistema redirige al panel con un mensaje de confirmación.

### RF-PEL-022 — Registrar ejecución en auditoría
El sistema debe registrar en auditoría cada disparo del pipeline, incluyendo el identificador de ejecución generado por el orquestador.

---

## Funcionalidad 3: Monitorear estado del DAG en ejecución (CU-O06)

Seguimiento en tiempo real del estado del pipeline desde la interfaz principal.

### RF-PEL-023 — Mostrar estado actual del pipeline
El sistema debe mostrar el panel principal con el estado global de la última ejecución del pipeline, la lista de tareas con su estado individual, una barra de progreso y las últimas 5 ejecuciones. Los estados posibles son: sin ejecuciones, en ejecución, en cola, exitoso, fallido.

### RF-PEL-024 — Polling automático cada 10 segundos
El sistema debe actualizar automáticamente la vista cada 10 segundos, obteniendo el estado actual del pipeline y actualizando dinámicamente el estado general, la barra de progreso, el listado de tareas y el historial, sin recargar la página completa.

### RF-PEL-025 — Timeline de tareas con estado individual
El sistema debe mostrar cada tarea del pipeline con su estado actual (en ejecución, exitoso, fallido, en cola, omitido, sin datos), identificado visualmente por color e indicador. Las tareas en ejecución deben mostrar el tiempo transcurrido. Las tareas fallidas deben incluir enlace directo a sus logs.

### RF-PEL-026 — Consultar estado como JSON
El sistema debe exponer el estado actual del pipeline en formato JSON, incluyendo el estado de la última ejecución y el estado de cada tarea individual. Este endpoint es consumido por la actualización automática de la interfaz.

---

## Funcionalidad 4: Consultar historial de ejecuciones (CU-O07)

Visualización del historial de ejecuciones del pipeline.

### RF-PEL-027 — Mostrar historial de ejecuciones
El sistema debe mostrar las últimas 50 ejecuciones del pipeline en una tabla con: identificador de ejecución, estado, fecha de inicio, fecha de fin y enlace a los logs correspondientes.

### RF-PEL-028 — Nueva ejecución desde historial
El sistema debe ofrecer la opción de iniciar una nueva ejecución desde la página de historial, sin necesidad de regresar al panel principal.

---

## Funcionalidad 5: Ver logs de error y reintentar ejecución (CU-O08)

Acceso a logs de tareas y reintento selectivo.

### RF-PEL-029 — Ver logs de tarea específica
El sistema debe mostrar los logs de una tarea específica de una ejecución determinada, con formato de texto monoespaciado y navegación entre las tareas de la misma ejecución.

### RF-PEL-030 — Reintentar tarea específica (no el pipeline completo)
El sistema debe permitir reintentar una tarea fallida de forma individual, sin reiniciar el pipeline completo. Solo limpia el estado de la tarea indicada, sin afectar las demás tareas.

### RF-PEL-031 — Botón de reintento condicional al estado
El sistema debe mostrar la opción de reintento únicamente cuando la tarea está en estado fallido o pendiente de reintento. No debe mostrarse para tareas en ejecución o completadas exitosamente.

### RF-PEL-032 — Registrar reintento en auditoría
El sistema debe registrar en auditoría cada reintento de tarea, incluyendo el identificador de ejecución y el identificador de la tarea reintentada.

---

## Reglas de negocio

### RN-PEL-021 — Ejecución manual bloqueada si ya hay una activa
La opción de ejecución manual se deshabilita mientras el pipeline esté en estado activo o en cola. La restricción se aplica tanto en la interfaz como en el orquestador, que admite como máximo una ejecución simultánea.

### RN-PEL-022 — Reintento no reinicia pipeline completo
Al reintentar una tarea individualmente, solo esa tarea se marca para re-ejecución. Las tareas aguas arriba que ya completaron no se repiten. La tarea reintentada espera a que sus dependencias estén disponibles.

### RN-PEL-023 — DAG de 3 tareas en secuencia estricta
El pipeline ELT tiene 3 tareas ejecutadas en orden estricto: extracción (timeout 2h), carga (timeout 30min) y transformación con agregaciones (timeout 2h). La tarea de transformación incluye la construcción del modelo estrella (fact_vuelo + 11 dimensiones) y la generación de las tablas de indicadores precalculados como paso final. Cada tarea espera la finalización exitosa de la anterior. El timeout total del pipeline es de 4h.

---

## Historias de usuario

- Como Administrador, quiero disparar el pipeline manualmente, para actualizar los datos en momentos específicos según las necesidades del negocio.
- Como Administrador, quiero ver el estado en tiempo real de cada etapa del pipeline, para detectar fallas sin acceder directamente al orquestador.
- Como Administrador, quiero consultar el historial de las últimas 50 ejecuciones, para analizar patrones de fallo y rendimiento.
- Como Administrador, quiero reintentar una tarea fallida sin reiniciar el pipeline completo, para recuperar el proceso rápidamente sin perder el trabajo ya completado.

---

## Objetivo

Ejecutar el pipeline ELT manualmente, monitorear su estado en tiempo real, consultar el historial de ejecuciones y reintentar tareas fallidas sin reiniciar el proceso completo.

---

## Escenarios

### Camino feliz
1. El Admin hace clic en "Ejecutar ahora" en el panel del pipeline.
2. El sistema dispara el DAG en Airflow y redirige al panel con un mensaje de confirmación.
3. El panel comienza a realizar polling cada 10s: las tareas de extracción → carga → transformación se marcan secuencialmente como en ejecución → exitoso.
4. Todas las tareas completan exitosamente; el panel muestra estado "success" con la duración total.
5. El Admin consulta el historial y visualiza las últimas 50 ejecuciones en una tabla con estado, fecha de inicio, duración y enlace a logs.

### Manejo de errores
- **Pipeline ya en ejecución:** Si el pipeline está activo, la opción "Ejecutar ahora" permanece deshabilitada.
- **Tarea fallida:** El timeline muestra la tarea en rojo con un enlace a la vista de logs.
- **Reintento de tarea:** El sistema limpia el estado de solo esa tarea y registra el reintento en auditoría.
- **Timeout en consulta de logs:** Si el orquestador no responde en 30s, la vista de logs muestra un mensaje de error y permite reintentar la consulta.
- **Timeout del DAG de 4h:** Si la ejecución excede las 4h, el orquestador la marca como fallida automáticamente.

---

## Criterios de aceptación

- **CU-O05:** Dado que el pipeline no está en ejecución, cuando el Admin hace clic en "Ejecutar ahora", entonces el sistema dispara el DAG en Airflow y registra la acción en auditoría.
- **CU-O06:** Dado que el pipeline está en ejecución, cuando el sistema actualiza el estado cada 10 segundos, entonces actualiza el estado de cada tarea, la barra de progreso y el timeline sin recargar la página.
- **CU-O07:** Dado que el Admin accede al historial de ejecuciones, entonces el sistema muestra las últimas 50 ejecuciones con estado, fecha de inicio, duración y enlace a logs.
- **CU-O08:** Dado que una tarea individual está en estado fallido o pendiente de reintento, cuando el Admin hace clic en "Reintentar", entonces el sistema reintenta solo esa tarea y registra el reintento en auditoría.

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
