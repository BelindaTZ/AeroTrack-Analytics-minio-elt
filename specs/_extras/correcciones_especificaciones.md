# Correcciones — Especificaciones Operativas (secciones 3.1, 3.2, 3.3)

---

## Auditoría Lote 2 — Gaps detectados y corregidos

### Estado antes de la corrección

| CU | Módulo | Estado | Problema |
|----|--------|--------|----------|
| CU-E03 | Puntualidad | ⚠️ Parcial | `retraso_prom` calculado en `agg_otp_aerolinea_mes` (columna `delay_avg`) pero no expuesto en la UI ni en tooltips del chart |
| CU-E04 | Puntualidad | ⚠️ Parcial | Tabla comparativa sin ranking ordinal, brecha vs líder, ni botón de narrativa IA por aerolínea |
| CU-E05 | Puntualidad | ⚠️ Parcial | Tendencia mensual sin línea YoY del año anterior, sin variación pp mes a mes en tooltip, sin indicador de tendencia estadística (slope) |
| CU-E08/E10 | Cancelaciones | ✅ Completo (backend) | Filtro de aerolínea existe en UI pero no opera porque `agg_cancelaciones_causa` no tiene columna `carrier` |
| CU-E09 | Cancelaciones | ⚠️ Parcial | Tabla de desvíos estática, sin gráfico de barras, sin filtros año/mes funcionales porque `agg_desvios_ruta` no tenía columnas `year`/`month` |

### Correcciones aplicadas

#### Gap 1 (CU-E03) — retraso_prom en UI de puntualidad
- **`app/puntualidad/analizar_otp.py`** `_otp_por_aerolinea_agg()`: Agregado `delay_avg` al groupby, calculado `retraso_prom` como promedio de `delay_avg`, incluido en el dict de retorno.
- **`app/puntualidad/templates/puntualidad/index.html`**: Añadido `otp_retrasos` al JSON de datos Chart.js y callback `afterLabel` en tooltip para mostrar "Retraso prom: X min".

#### Gap 2 (CU-E04) — Ranking, brecha vs líder y narrativa IA en comparar rutas
- **`app/puntualidad/analizar_otp.py`** endpoint `/comparar`: Datos ahora ordenados por OTP descendente. Añadidos campos `ranking` (posición 1..N) y `brecha` (diferencia en pp con el líder) a cada registro.
- **`app/puntualidad/analizar_otp.py`** endpoint `/narrativa`: Añadido handler `ruta_aerolinea` que carga `agg_rutas_eficiencia`, filtra por ruta+aerolínea y genera contexto con OTP, retraso, tiempos, índice de eficiencia.
- **`app/puntualidad/templates/puntualidad/comparar.html`**: Añadidas columnas # (ranking con badge dorado/plata/bronce), Brecha vs líder (pp), botón de narrativa IA por fila. Añadido popover IA con estilos skeleton, funciones `_iaFetch`, `_iaPos`, `_iaQs`, `rutaSel()`.

#### Gap 3 (CU-E05) — YoY, variación pp y tendencia estadística
- **`app/puntualidad/analizar_otp.py`** `_tendencias_otp_mensual_agg()`: Acepta parámetro `year`. Calcula variación pp mes a mes. Calcula pendiente de regresión lineal simple (tendencia). Si hay año específico, carga datos del año anterior y devuelve `yoy_otp`.
- **`app/puntualidad/analizar_otp.py`** `_compute_page()`: Pasa `year` a `_tendencias_otp_mensual_agg`.
- **`app/puntualidad/templates/puntualidad/index.html`**: Añadidos datos `tend_yoy`, `tend_varpp`, `tend_slope` al JSON. Chart de tendencia ahora muestra línea punteada del año anterior cuando disponible. Tooltip muestra variación pp vs mes anterior. Badge de tendencia (↑/↓ + slope pp/mes) en el título del chart.

#### Gap 4 (CU-E08/E10) — Filtro de aerolínea funcional en cancelaciones
- **`dags/aerotrack_tasks.py`**: Nueva tabla `agg_cancelaciones_causa_aerolinea` que agrupa por `CancellationCode` + `Reporting_Airline` + `Year` + `Month`. Renombrados contadores de 7→8 tablas.
- **`app/cancelaciones/clasificar_faa.py`** `_compute_page()`: Si el filtro incluye `airline`, carga desde `agg_cancelaciones_causa_aerolinea`; si no, desde `agg_cancelaciones_causa` (comportamiento anterior).

#### Gap 5 (CU-E09) — Gráfico de desvíos + filtros año/mes funcionales
- **`dags/aerotrack_tasks.py`**: `agg_desvios_ruta` ahora incluye `Year` y `Month` en el GROUP BY y renombra como `year`/`month` (int). Las agregaciones se reagrupan por ruta en el backend para mantener el top 20.
- **`app/cancelaciones/clasificar_faa.py`** `_desvios_agg()`: Ahora acepta DataFrame con year/month, reagrupa por ruta para consolidar. `_compute_page()` pasa filtros year/month a `load_agg("agg_desvios_ruta", ...)`.
- **`app/cancelaciones/templates/cancelaciones/causas.html`**: Añadido chart de barras horizontal (Chart.js) con desvíos y retraso promedio, datos `dev_labels`/`dev_counts`/`dev_delays` en JSON, y event handler para narrativa IA por ruta.

### Estado después de la corrección

| CU | Módulo | Estado | Estado anterior |
|----|--------|--------|-----------------|
| CU-E03 | Puntualidad | ✅ Completo | ⚠️ Parcial |
| CU-E04 | Puntualidad | ✅ Completo | ⚠️ Parcial |
| CU-E05 | Puntualidad | ✅ Completo | ⚠️ Parcial |
| CU-E06 | Rutas | ✅ Completo | ✅ Completo |
| CU-E07 | Rutas | ✅ Completo | ✅ Completo |
| CU-E08 | Cancelaciones | ✅ Completo | ✅ Completo |
| CU-E09 | Cancelaciones | ✅ Completo | ⚠️ Parcial |
| CU-E10 | Cancelaciones | ✅ Completo | ✅ Completo |

---

# Correcciones — Especificaciones Operativas (secciones 3.1, 3.2, 3.3)

Copia y pega estos bloques reemplazando los originales del documento.

---

## 3.1 Módulo: Seguridad

### 3.1.5 Requisitos no funcionales

• RNF-SEG-001: El JWT debe usar algoritmo HS256 con tiempo de vida configurable por variable de entorno (por defecto 60 minutos, configurable vía TOKEN_EXPIRE_MINUTES) y clave secreta configurable vía SECRET_KEY (Principio IV de la constitución).
• RNF-SEG-002: Toda autorización se valida en la capa de aplicación (FastAPI), nunca en la base de datos (Principio III).
• RNF-SEG-003: La caché de permisos por rol debe expirar en un máximo de 5 minutos.
• RNF-SEG-004: Toda acción administrativa relevante (login, login fallido, logout, CRUD de usuarios/roles, cambios de permisos, cambios de perfil) debe registrarse en el log de auditoría inmutable (Principio V).
• RNF-SEG-005: El JWT usa el id de PocketBase (record["id"]) como sub, no el email, por lo que cambiar el email del perfil no invalida la sesión activa.

### 3.1.6 Reglas de negocio

• RN-SEG-001: Un usuario no puede desactivar su propia cuenta.
• RN-SEG-002: Una cuenta inactiva no puede iniciar sesión aunque sus credenciales sean correctas.
• RN-SEG-003: Los roles marcados como es_sistema=True no pueden editarse ni eliminarse.
• RN-SEG-004: No se puede eliminar un rol con al menos un usuario asignado.
• RN-SEG-005: Guardar los permisos de un rol reemplaza la totalidad de sus permisos previos; no es una operación incremental.

### 3.1.7 Entradas y salidas

| FUNCIÓN / ENDPOINT | ENTRADAS | SALIDAS |
|---|---|---|
| GET /auth/login | — | Formulario de inicio de sesión |
| POST /auth/login | email, password | Cookie access_token + redirect a /pipeline, o error en pantalla |
| POST /auth/logout | Cookie JWT | Cookie eliminada + redirect a login |
| GET /auth/perfil | Cookie JWT | Datos del usuario y su rol expandido |
| POST /auth/perfil/datos | nombre, email | Perfil actualizado o error de validación/duplicado |
| POST /auth/perfil/password | password_actual, password_nuevo, password_confirm | Contraseña actualizada o error |
| GET /auth/usuarios | Cookie JWT, page, q (filtro), rol_id, activo | Lista paginada (20/pág) con filtros |
| POST /auth/usuarios | nombre, email, rol_id | Usuario creado + email de bienvenida |
| GET /auth/usuarios/{uid} | Cookie JWT, uid | Formulario de edición precargado |
| POST /auth/usuarios/{uid} | nombre, email, rol_id | Usuario actualizado o error |
| POST /auth/usuarios/{uid}/estado | Cookie JWT, uid | Estado activo/inactivo conmutado (auto-desactivación bloqueada) |
| POST /auth/usuarios/{uid}/reset-password | Cookie JWT, uid | Nueva contraseña temporal generada |
| GET /auth/roles | Cookie JWT | Lista de roles con conteo de usuarios |
| POST /auth/roles | nombre, descripcion | Rol creado (es_sistema=False) |
| GET /auth/roles/{rid} | Cookie JWT, rid | Formulario de edición |
| POST /auth/roles/{rid} | nombre, descripcion | Rol actualizado (roles de sistema bloqueados) |
| POST /auth/roles/{rid}/eliminar | Cookie JWT, rid | Rol eliminado (roles de sistema y con usuarios bloqueados) |
| GET /auth/roles/{rid}/permisos | Cookie JWT, rid | Formulario de matriz permisos × módulo |
| POST /auth/roles/{rid}/permisos | Checkboxes por módulo×acción | Permisos guardados (replace completo), caché invalidada |
| GET /auth/roles/matriz | Cookie JWT | Tabla roles × módulos × acciones (solo lectura) |

---

## 3.2 Módulo: Pipeline ELT

### 3.2.4 Requisitos funcionales

Funcionalidad 1: Configurar y programar ejecución del pipeline (CU-T06)
• RF-PEL-001: El sistema debe permitir al Administrador definir el horario de ejecución del pipeline mediante presets (Manual, Diario, Cada hora, Semanal, Mensual, Anual) o una expresión cron personalizada, validada con croniter antes de guardar.
• RF-PEL-002: El sistema debe sincronizar el horario configurado con una Variable de Airflow (pipeline_schedule), sin modificar el archivo del DAG.
• RF-PEL-003: El sistema debe permitir configurar el tamaño de lote, número de procesos paralelos y reintentos de extracción (valores almacenados en PocketBase; el DAG actualmente usa constantes internas: MAX_WORKERS=10, BATCH_SIZE=200 páginas, retries=2 por tarea).
• RF-PEL-004: El sistema debe informar al Administrador que el cambio de horario puede tardar hasta el siguiente ciclo de refresco del scheduler de Airflow (~300 s).

Funcionalidad 2: Ejecutar pipeline ELT manualmente (CU-O05)
• RF-PEL-005: El sistema debe permitir disparar manualmente la ejecución completa del pipeline desde la interfaz web.

Funcionalidad 3: Monitorear estado del DAG en ejecución (CU-O06)
• RF-PEL-006: El sistema debe mostrar en tiempo real el estado de cada etapa del pipeline en ejecución, actualizando automáticamente cada 10 segundos.

Funcionalidad 4: Consultar historial de ejecuciones (CU-O07)
• RF-PEL-007: El sistema debe mostrar el historial de las últimas 50 ejecuciones, con fecha, duración y estado final.

Funcionalidad 5: Ver logs de error y reintentar ejecución (CU-O08)
• RF-PEL-008: El sistema debe mostrar el log detallado de una tarea específica de un run.
• RF-PEL-009: El sistema debe permitir reintentar una tarea fallida sin reiniciar el pipeline completo, mostrando el botón de reintento solo cuando el estado de la tarea sea "failed" o "up_for_retry".

### 3.2.5 Requisitos no funcionales

• RNF-PEL-001: Las llamadas a la API de Airflow deben tener timeout de 15 segundos para operaciones generales y 30 segundos para consulta de logs.
• RNF-PEL-002: El pipeline no debe permitir ejecuciones concurrentes (max_active_runs=1).
• RNF-PEL-003: Toda ejecución manual, cambio de horario y reintento de tarea debe registrarse en el log de auditoría inmutable.
• RNF-PEL-004: Las URL y credenciales de Airflow se configuran mediante variables de entorno con valores por defecto para desarrollo local (AIRFLOW_URL, AIRFLOW_ADMIN_USER, AIRFLOW_ADMIN_PASSWORD).

### 3.2.7 Entradas y salidas

| FUNCIÓN / ENDPOINT | ENTRADAS | SALIDAS |
|---|---|---|
| GET /pipeline | Cookie JWT | Panel con estado, tareas, progreso, últimas 5 ejecuciones |
| POST /pipeline/trigger | Cookie JWT (permiso ejecutar) | Redirect con mensaje de inicio o error |
| GET /pipeline/estado | Cookie JWT | JSON: estado, dag_run_id, task_instances |
| GET /pipeline/estado-full | Cookie JWT | JSON: estado + historial (5 últimas ejecuciones) |
| GET /pipeline/historial | Cookie JWT | Lista de últimas 50 ejecuciones |
| GET /pipeline/logs/{run_id}/{task_id} | run_id, task_id, attempt | Texto del log + lista de tareas |
| POST /pipeline/logs/{run_id}/{task_id}/reintentar | run_id, task_id | Tarea reencolada en Airflow, o error |
| POST /configuracion/pipeline | pipeline_schedule, batch_size, max_workers, reintentos | Configuración guardada en PocketBase + Variable de Airflow sincronizada |

---

## 3.3 Módulo: Modelo Dimensional

### 3.3.4 Requisitos funcionales

Funcionalidad 1: Ver resumen del modelo dimensional (CU-O09)
• RF-MOD-001: El sistema debe mostrar las 12 tablas del modelo con su número de filas, tamaño en MB, fecha de última modificación e indicador de disponibilidad.
• RF-MOD-002: Si una tabla no tiene archivo Parquet en MinIO, el sistema debe mostrar un indicador visual "Ejecuta el pipeline primero" en lugar de métricas.

Funcionalidad 2: Explorar y gestionar registros del modelo (CU-O10)
• RF-MOD-003: El sistema debe permitir explorar cualquiera de las 12 tablas con paginación de 50 registros por página.
• RF-MOD-004: El sistema debe permitir búsqueda textual sobre todas las columnas de la tabla seleccionada.
• RF-MOD-005: El sistema debe permitir ver el detalle completo de un registro individual por su PK.
• RF-MOD-006: El sistema debe permitir crear registros con PK auto-incremental y casting automático de tipos según la columna.
• RF-MOD-007: El sistema debe permitir editar registros existentes con casting automático de tipos.
• RF-MOD-008: El sistema debe permitir eliminar registros, bloqueando la eliminación del registro sentinel pk=0 en las dimensiones opcionales.

Funcionalidad 3: Validar integridad del modelo dimensional (CU-O11)
• RF-MOD-009: El sistema debe ejecutar la validación de las 12 claves foráneas de fact_vuelo contra sus dimensiones correspondientes mediante POST.
• RF-MOD-010: El sistema debe clasificar cada error de validación en uno de cuatro tipos: NULL_FK (FK nula en dimensión obligatoria), FK_HUERFANA (FK sin correspondencia), TABLA_FALTANTE (dimensión no disponible), o FALTA_PK0 (fila sentinel pk=0 faltante en dimensión opcional).
• RF-MOD-011: El sistema debe mostrar los resultados de validación con indicador visual (verde/rojo) y tabla detallada de errores.
• RF-MOD-012: El sistema debe permitir exportar el resultado de la validación a un archivo CSV.

### 3.3.5 Requisitos no funcionales

• RNF-MOD-001: Toda lectura y escritura del modelo se realiza sobre archivos Parquet en MinIO, sin updates parciales (se reescribe el archivo completo).
• RNF-MOD-002: Toda creación, edición, eliminación y validación debe registrarse en el log de auditoría inmutable.
• RNF-MOD-003: Las rutas estáticas (/validar, /nuevo) deben definirse antes que las dinámicas (/{tabla}) en el router para evitar conflictos de ruta en FastAPI.

### 3.3.6 Reglas de negocio

• RN-MOD-001: El registro con pk=0 en las dimensiones opcionales (dim_cancelacion, dim_retraso_causa, dim_desvio) es inmutable y no puede eliminarse.
• RN-MOD-002: El PK de un registro nuevo se autogenera como el máximo PK existente más uno (o 1 si la tabla está vacía).
• RN-MOD-003: Si una tabla solicitada no existe en el catálogo de tablas del modelo, el sistema responde con error 404.
• RN-MOD-004: Si el archivo Parquet de una tabla aún no existe en MinIO, el sistema lo indica como "no disponible aún" en vez de fallar de forma genérica.

### 3.3.7 Entradas y salidas

| FUNCIÓN / ENDPOINT | ENTRADAS | SALIDAS |
|---|---|---|
| GET /modelo | Cookie JWT | Resumen de las 12 tablas con métricas y disponibilidad |
| GET /modelo/{tabla} | tabla, page, q (búsqueda) | Listado paginado (50/pág) con resultados de búsqueda |
| GET /modelo/{tabla}/{pk_val}/ver | Cookie JWT, tabla, pk_val | Detalle completo del registro (solo lectura) |
| GET /modelo/{tabla}/nuevo | Cookie JWT, tabla | Formulario dinámico según esquema Parquet |
| POST /modelo/{tabla}/nuevo | Columnas de la tabla (Form) | Registro creado con PK autogenerado o error |
| GET /modelo/{tabla}/{pk_val}/editar | Cookie JWT, tabla, pk_val | Formulario precargado con valores actuales |
| POST /modelo/{tabla}/{pk_val}/editar | Columnas modificadas | Registro actualizado o error |
| POST /modelo/{tabla}/{pk_val}/eliminar | Cookie JWT, tabla, pk_val | Registro eliminado, o rechazo si pk=0 (403) |
| GET /modelo/validar | Cookie JWT (permiso ejecutar) | Página con botón "Ejecutar validación" |
| POST /modelo/validar | Cookie JWT (permiso ejecutar) | Resultado de validación con errores detallados |
| GET /modelo/validar/export | Cookie JWT (permiso exportar) | Archivo CSV descargable con errores |
