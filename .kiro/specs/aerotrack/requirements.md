# Requirements Document

## Introduction

AeroTrack Analytics is a BI platform built on an ELT pipeline that processes 2 million US airline flight records (BTS Carrier On-Time Performance dataset) and exposes tactical and strategic analysis through a FastAPI web application.

All functional requirements below use EARS notation: WHEN [condition] THE SYSTEM SHALL [behavior].

## Actors

- **Administrator**: manages infrastructure, pipeline, users, roles, and system configuration
- **Data Analyst**: consumes tactical and strategic analysis modules
- **System**: automated actions triggered by the DAG, alert evaluation, and audit logging

---

## Requirements

### 1. Seguridad [Entrega 1]

#### 1.1 CU-01: Iniciar sesión

WHEN a user submits valid email and password at /login
THE SYSTEM SHALL validate credentials against the PocketBase `app_users` collection,
generate a signed JWT token, and redirect to the dashboard

WHEN the JWT token is generated successfully
THE SYSTEM SHALL adapt the lateral menu to show only the modules permitted by the user's role

WHEN a user submits incorrect credentials
THE SYSTEM SHALL display a generic error message without revealing which field (email or password) is wrong

WHEN a user account has `activo=false`
THE SYSTEM SHALL reject authentication and display "Cuenta desactivada. Contacte al administrador"

WHEN a valid JWT token expires
THE SYSTEM SHALL redirect the user to /login and clear the session cookie

WHEN a user attempts to access a protected route without a valid JWT
THE SYSTEM SHALL redirect to /login

---

#### 1.2 CU-02: Cerrar sesión

WHEN an authenticated user clicks "Cerrar sesión" in the navbar user menu
THE SYSTEM SHALL invalidate the current JWT token, clear the session cookie,
and redirect to /login with the message "Sesión cerrada correctamente"

---

#### 1.3 CU-03: Ver y editar perfil propio

WHEN an authenticated user accesses "Mi perfil" from the user menu
THE SYSTEM SHALL display name, email, assigned role, account status, and creation date

WHEN a user submits a password change form
THE SYSTEM SHALL require the current password to verify identity before accepting the new password

WHEN a user submits a password change with incorrect current password
THE SYSTEM SHALL reject the change and display "Contraseña actual incorrecta"

WHEN a user submits a password change where new passwords do not match
THE SYSTEM SHALL reject the change and display "Las contraseñas no coinciden"

WHEN a user successfully changes their password
THE SYSTEM SHALL update the password hash in PocketBase without interrupting the active session

WHEN a user is in the profile view
THE SYSTEM SHALL NOT display any option to modify their own role

---

#### 1.4 CU-04: Gestionar usuarios

WHEN an Administrator accesses Administración → Usuarios
THE SYSTEM SHALL display a paginated table of all users with search and filters by role and status

WHEN an Administrator submits a new user form with name, email, temporary password, and role
THE SYSTEM SHALL create the user in PocketBase's `app_users` collection and confirm success

WHEN an Administrator edits an existing user
THE SYSTEM SHALL allow modifying name, email, or role, and persist the changes in PocketBase

WHEN an Administrator clicks the activate/deactivate toggle for a user
THE SYSTEM SHALL show a confirmation modal before changing the `activo` field in PocketBase

WHEN an Administrator resets a user's password
THE SYSTEM SHALL set a temporary password value without requiring the current password

WHEN an Administrator attempts to deactivate their own account
THE SYSTEM SHALL reject the action and display an error message

---

#### 1.5 CU-05: Crear rol

WHEN an Administrator submits a new role with a unique name and description
THE SYSTEM SHALL create the role in PocketBase with no permissions assigned

WHEN a role has `es_sistema=true`
THE SYSTEM SHALL mark it as protected and NOT display it as an editable template

---

#### 1.6 CU-06: Editar rol

WHEN an Administrator submits edits to a non-protected role
THE SYSTEM SHALL update the role's name and/or description in PocketBase

WHEN a role's name or description is updated
THE SYSTEM SHALL NOT alter the permissions or user assignments for that role

---

#### 1.7 CU-07: Eliminar rol

WHEN an Administrator requests deletion of a role that has users assigned
THE SYSTEM SHALL reject the deletion and display how many users must be reassigned first

WHEN an Administrator requests deletion of a role with no users assigned
THE SYSTEM SHALL show a confirmation modal and, upon confirmation,
delete the role and all its records in `roles_permisos`

---

#### 1.8 CU-08: Asignar permisos a un rol

WHEN an Administrator clicks "Gestionar permisos" on a role
THE SYSTEM SHALL display a permission grid with all modules as rows
and available actions as checkboxes (ver, crear, editar, eliminar, ejecutar, exportar, configurar)

WHEN an Administrator saves permission changes
THE SYSTEM SHALL persist the changes in `roles_permisos` and apply them immediately
to all users with that role without requiring a restart

---

#### 1.9 CU-09: Ver matriz de permisos

WHEN an Administrator accesses Administración → Permisos → Vista general
THE SYSTEM SHALL display a cross-reference table with modules as rows and roles as columns,
showing icons for each enabled action per cell

WHEN an Administrator clicks a cell in the permissions matrix
THE SYSTEM SHALL navigate to CU-08 for that specific role

---

### 2. Pipeline ELT [Entrega 1]

#### 2.1 CU-10: Ejecutar pipeline ELT

WHEN an Administrator clicks "Ejecutar ahora" in Pipeline ELT → Panel de control
THE SYSTEM SHALL call the Airflow API to trigger the `aerotrack_elt_pipeline` DAG

WHEN the pipeline execution is triggered successfully
THE SYSTEM SHALL change the displayed status to "En ejecución"
and refresh the status panel every 10 seconds

WHEN the pipeline is already running
THE SYSTEM SHALL display the "Ejecutar ahora" button as disabled with an explanatory tooltip

---

#### 2.2 CU-11: Monitorear estado del DAG

WHEN an Administrator views the Pipeline ELT panel during an active execution
THE SYSTEM SHALL display in real time: the currently running task (extract or transform),
elapsed time, and per-task status (waiting, running, completed, failed) with color coding

THE SYSTEM SHALL refresh the status panel automatically every 10 seconds

---

#### 2.3 CU-12: Consultar historial de ejecuciones

WHEN an Administrator clicks "Historial" in the Pipeline ELT panel
THE SYSTEM SHALL display a table of past executions with:
start date/time, total duration, final status (success/failure), and records processed

WHEN an Administrator clicks any row in the history table
THE SYSTEM SHALL display the per-task detail for that specific execution

---

#### 2.4 CU-13: Ver logs de error y reintentar

WHEN a pipeline task appears in red (failed state)
AND an Administrator clicks "Ver error"
THE SYSTEM SHALL display the error message, full traceback, and the failed task's timestamp

WHEN viewing a failed task's error
THE SYSTEM SHALL offer a download link for the `errors.log` file from the script

WHEN viewing a failed execution
THE SYSTEM SHALL provide a single-click button to retry the full pipeline execution

---

### 3. Modelo Dimensional [Entrega 1]

#### 3.1 CU-14: Ver resumen del modelo dimensional

WHEN an Administrator accesses Modelo Dimensional
THE SYSTEM SHALL display the 12 tables (fact_vuelo + 11 dimensions) as cards,
each showing: table name, record count, Parquet size in MB, and last update date

WHEN a table's Parquet file does not exist in MinIO (pipeline not yet run)
THE SYSTEM SHALL display a card indicating the table is not yet available

WHEN an Administrator clicks a table card
THE SYSTEM SHALL navigate to the record explorer for that table (CU-15)

---

#### 3.2 CU-15: Explorar y gestionar registros

WHEN an Administrator enters a table view
THE SYSTEM SHALL display paginated records (50 per page) with a per-column search field

WHEN an Administrator creates a new record
THE SYSTEM SHALL display a dynamically generated form based on the Parquet schema,
assign an autoincremental primary key, and update the Parquet file in MinIO upon saving

WHEN an Administrator edits a record
THE SYSTEM SHALL display a form pre-filled with current values
where the primary key field is read-only and updates the Parquet file in MinIO upon saving

WHEN an Administrator requests deletion of a record
THE SYSTEM SHALL show a confirmation modal before deleting

WHEN an Administrator confirms deletion of a record
THE SYSTEM SHALL remove the record and update the Parquet file in MinIO

WHEN an Administrator attempts to delete a record with `pk=0`
THE SYSTEM SHALL reject the deletion without showing the confirmation modal

---

#### 3.3 CU-16: Validar integridad del modelo

WHEN an Administrator clicks "Validar integridad"
THE SYSTEM SHALL load all Parquet files from MinIO and verify:
(1) every FK in fact_vuelo points to an existing record in its dimension,
(2) no FK value is NULL,
(3) special rows with pk=0 exist in optional dimensions

WHEN all integrity checks pass
THE SYSTEM SHALL display a report with a green badge indicating no issues found

WHEN integrity violations are detected
THE SYSTEM SHALL display a list of errors with the affected table name and count of affected records

WHEN the integrity report is displayed
THE SYSTEM SHALL provide an option to export the report as CSV

---

### 4. Dashboard [Entrega 2]

#### 4.1 CU-17: Ver dashboard de KPIs con filtros

WHEN a Data Analyst accesses the Dashboard module
THE SYSTEM SHALL display panels with main KPIs:
global OTP, total flights, cancellation rate, and average delay

WHEN a KPI value exceeds its configured threshold
THE SYSTEM SHALL highlight that KPI panel in red

WHEN a Data Analyst applies filters (year, month, airline, route)
THE SYSTEM SHALL update all KPI panels on the page with the filtered data

WHEN KPI data is displayed
THE SYSTEM SHALL correspond to the output of the most recent pipeline execution

---

#### 4.2 CU-18: Detectar y visualizar alertas en KPIs

WHEN the system evaluates KPIs against configured thresholds (set in CU-31)
AND a KPI exceeds its threshold
THE SYSTEM SHALL display a visual alert on the dashboard with a description of the problem
and the affected module

WHEN a Data Analyst clicks on an alert
THE SYSTEM SHALL navigate directly to the detailed analysis view for the affected module

---

### 5. Puntualidad [Entrega 2]

#### 5.1 CU-19: Analizar puntualidad OTP por aerolínea

WHEN a Data Analyst accesses the Puntualidad module
THE SYSTEM SHALL display the OTP index (% on-time flights) per airline as a bar chart

WHEN a Data Analyst selects an airline
THE SYSTEM SHALL display a pie chart breaking down delay causes:
carrier, weather, NAS, security, and late aircraft

WHEN a Data Analyst applies a period filter
THE SYSTEM SHALL update the OTP chart to show how punctuality evolves over the selected period

---

#### 5.2 CU-20: Comparar aerolíneas en rutas compartidas

WHEN a Data Analyst clicks "Comparar aerolíneas" in Puntualidad
THE SYSTEM SHALL display a route selection interface

WHEN a Data Analyst selects a specific route
THE SYSTEM SHALL display a comparative table of all airlines operating that route,
showing OTP, average delay, and delay minutes by cause (carrier, weather, NAS)

WHEN the comparison table is displayed
THE SYSTEM SHALL allow sorting by any column

---

#### 5.3 CU-21: Ver tendencias de puntualidad por período

WHEN a Data Analyst clicks "Tendencias" in the Puntualidad module
THE SYSTEM SHALL display a line chart with OTP month-by-month for the selected period

WHEN viewing the trend chart
THE SYSTEM SHALL allow comparing multiple airlines on the same chart

WHEN a Data Analyst switches to day-of-week view
THE SYSTEM SHALL display which days of the week concentrate the most delays

---

### 6. Rutas [Entrega 2]

#### 6.1 CU-22: Evaluar rendimiento de rutas

WHEN a Data Analyst accesses the Rutas module
THE SYSTEM SHALL display a ranked list of routes ordered by efficiency index
(actual time / scheduled time)

WHEN a route's deviation exceeds the configured threshold
THE SYSTEM SHALL mark that route as flagged

WHEN a Data Analyst clicks on a route
THE SYSTEM SHALL display: actual vs. scheduled time box plot, delay distribution,
operating airlines, and seasonality data

---

#### 6.2 CU-23: Comparar tiempo real vs programado

WHEN a Data Analyst accesses the Tiempo tab within a route detail (CU-22)
THE SYSTEM SHALL display a scatter plot showing the distribution of the difference
between actual flight time and scheduled flight time

WHEN a Data Analyst applies an airline filter in this view
THE SYSTEM SHALL show which carrier best recovers lost time in the air on that specific route

---

### 7. Cancelaciones [Entrega 2]

#### 7.1 CU-24: Analizar cancelaciones por causa FAA

WHEN a Data Analyst accesses the Cancelaciones module
THE SYSTEM SHALL display a pie chart of total cancellations for the period,
broken down by FAA code: A (airline), B (weather), C (NAS), D (security)

WHEN a Data Analyst applies airline and period filters
THE SYSTEM SHALL update the cancellation charts with the filtered data

WHEN the cancellation view is displayed
THE SYSTEM SHALL also show a bar chart of monthly cancellation rate
to identify critical months

---

#### 7.2 CU-25: Analizar impacto operacional de desvíos

WHEN a Data Analyst accesses Cancelaciones → Desvíos tab
THE SYSTEM SHALL display diverted flights with:
alternate airport used, additional delay minutes (DivArrDelay), and extra distance traveled (DivDistance)

WHEN viewing diversion data
THE SYSTEM SHALL display the most frequently used diversion airports
and cumulative impact per airline for the selected period

---

#### 7.3 CU-26: Ver tendencia de cancelaciones mensual

WHEN a Data Analyst accesses Cancelaciones → Tendencias tab
THE SYSTEM SHALL display a bar chart with monthly cancellation rate for the selected year

WHEN the trend chart is displayed
THE SYSTEM SHALL allow overlaying the cause breakdown curve
to identify whether weather, airline, or other factors predominate in specific months

---

### 8. Reportes [Entrega 2]

#### 8.1 CU-27: Exportar análisis a PDF

WHEN a Data Analyst clicks "Exportar PDF" in any analysis module
THE SYSTEM SHALL display a form to select which sections to include and the period

WHEN the Data Analyst confirms the PDF export
THE SYSTEM SHALL generate a PDF with charts and tables from the current analysis view,
upload it to MinIO in the `aerotrack-exports/` path, and provide an immediate download link

---

#### 8.2 CU-28: Exportar análisis a Excel

WHEN a Data Analyst clicks "Exportar Excel" in any analysis module
THE SYSTEM SHALL generate a .xlsx file with separate sheets per module:
puntualidad, rutas, cancelaciones

WHEN the Excel file is generated
THE SYSTEM SHALL use the data currently visible on screen with active filters applied

WHEN the Excel file is ready
THE SYSTEM SHALL offer it for direct download without uploading to MinIO

---

### 9. Configuracion [Entrega 2]

#### 9.1 CU-29: Ver panel de configuración

WHEN an Administrator accesses Administración → Configuración
THE SYSTEM SHALL display configuration grouped by module: Email, Alertas, Pipeline, Sistema

WHEN displaying sensitive configuration values
THE SYSTEM SHALL mask them with •••• characters

WHEN an Administrator clicks any configuration group
THE SYSTEM SHALL open the corresponding edit form (CU-30, CU-31, or CU-32)

---

#### 9.2 CU-30: Configurar y probar servicio de email

WHEN an Administrator saves email settings (SMTP server, port, sender, password, TLS, alerts active, recipient)
THE SYSTEM SHALL persist them in the `configuracion_sistema` PocketBase collection

WHEN an Administrator clicks "Enviar email de prueba"
THE SYSTEM SHALL attempt to connect to the configured SMTP server and send a test email,
then display either a success confirmation or a specific SMTP error message

---

#### 9.3 CU-31: Configurar umbrales de alertas analíticas

WHEN an Administrator saves alert thresholds
(minimum OTP %, maximum cancellation rate %, delay minutes threshold, route deviation %)
THE SYSTEM SHALL persist them in `configuracion_sistema`

WHEN thresholds are saved
THE SYSTEM SHALL apply them immediately to the dashboard KPI evaluation
without requiring any service restart

---

#### 9.4 CU-32: Configurar parámetros del pipeline

WHEN an Administrator saves pipeline parameters
(BATCH_SIZE, max_workers, retry_count)
THE SYSTEM SHALL persist them in `configuracion_sistema`

WHEN the ELT pipeline runs next
THE SYSTEM SHALL use the newly saved parameter values

---

#### 9.5 CU-33: Monitorear métricas de MinIO

WHEN an Administrator accesses Administración → Estado del sistema → MinIO tab
THE SYSTEM SHALL display: total available space, used space,
number of objects per bucket (aerotrack-raw, aerotrack-dims, aerotrack-exports),
and last modification dates per bucket

THE SYSTEM SHALL refresh this information via MinIO API every 30 seconds

---

#### 9.6 CU-34: Ver estado de salud de servicios

WHEN an Administrator accesses Administración → Estado del sistema
THE SYSTEM SHALL display the health status of each service: MinIO, PocketBase, and Airflow,
showing: response status (green/red), latency in ms, and last verification timestamp

WHEN a service does not respond
THE SYSTEM SHALL display specific diagnostic instructions for that service's Docker container

---

### 10. Auditoria [Entrega 2]

#### 10.1 CU-39: Ver log de auditoría del sistema

WHEN an Administrator accesses Administración → Auditoría
THE SYSTEM SHALL display a paginated table of all system events,
ordered from most recent to oldest, with columns:
date/time, user, action, module, affected resource, and result (success/failure)

WHEN an Administrator clicks any row in the audit log
THE SYSTEM SHALL display the full `detalle` field as formatted JSON

---

#### 10.2 CU-40: Filtrar y exportar log de auditoría

WHEN an Administrator applies audit log filters
(module, action, specific user, result, date range)
THE SYSTEM SHALL update the audit table to show only matching events

WHEN an Administrator requests audit export
THE SYSTEM SHALL generate a CSV file of the currently filtered results for external analysis

---

### 11. Predictivo [Entrega 3]

#### 11.1 CU-35: Generar proyección de riesgo operacional

WHEN a Data Analyst selects a target airline, optional route, and projection horizon (3 or 6 months)
AND clicks "Generar proyección"
THE SYSTEM SHALL process historical patterns from the dimensional model
and display a chart with the projected OTP for the selected months including confidence intervals

WHEN the historical data spans less than 12 months
THE SYSTEM SHALL display a warning indicating reduced prediction accuracy

---

#### 11.2 CU-36: Analizar patrones estacionales

WHEN a Data Analyst selects an airline in Predictivo → Estacionalidad
THE SYSTEM SHALL display a heat map with months as columns, days of week as rows,
and color representing the historical average OTP

WHEN viewing the heat map
THE SYSTEM SHALL allow toggling between OTP, cancellation rate, and average delay as the displayed metric

---

#### 11.3 CU-37: Ver recomendaciones automáticas priorizadas

WHEN a projection is generated (CU-35)
THE SYSTEM SHALL automatically display a prioritized recommendations panel:
High, Medium, and Low priority items

WHEN recommendations are displayed
EACH recommendation SHALL include: a description of the concrete action,
the affected module, and a justification based on historical data

WHEN a Data Analyst marks a recommendation as reviewed
THE SYSTEM SHALL persist that status for the current session

---

#### 11.4 CU-38: Exportar informe ejecutivo IA

WHEN a Data Analyst clicks "Generar informe ejecutivo" from the predictive module
THE SYSTEM SHALL generate a structured PDF containing:
executive summary, risk projection chart, seasonal heat map, and prioritized recommendations

WHEN the PDF is generated
THE SYSTEM SHALL upload it to `aerotrack-exports/` in MinIO and provide an immediate download link

WHEN the Administrator configures the maximum projection horizon
THE SYSTEM SHALL use that configured value as the upper limit for the horizon selector in CU-35

---

### 12. Asistente IA [Entrega 3]

#### 12.1 CU-41: Consultar asistente analítico IA

WHEN a Data Analyst types a natural language question in the Asistente IA chat interface
THE SYSTEM SHALL query the relevant Parquet files from the star model to obtain relevant data

WHEN the relevant data is retrieved
THE SYSTEM SHALL pass it as context to the configured LLM
and display the generated response with justification based on real data

WHEN a conversation session is active
THE SYSTEM SHALL maintain the conversation history for the duration of the session

WHEN the AI module generates a response
THE SYSTEM SHALL do so in less than 30 seconds

---

#### 12.2 CU-42: Configurar parámetros del asistente IA

WHEN an Administrator accesses Configuración → IA
THE SYSTEM SHALL display editable parameters:
provider (OpenAI, Anthropic, Gemini, custom), API key (masked field),
specific model, custom endpoint, max tokens, temperature, and timeout

WHEN an Administrator toggles the AI module off
THE SYSTEM SHALL immediately disable the Asistente IA module for all users

WHEN an Administrator saves IA configuration
THE SYSTEM SHALL apply the changes immediately without restarting any service

WHEN the API key is displayed or stored
THE SYSTEM SHALL mask it in the UI with •••• characters

---

## Non-Functional Requirements (ISO 25010)

### 13. Eficiencia de Desempeño

WHEN the dashboard is loaded with current period data
THE SYSTEM SHALL render all KPI panels in less than 5 seconds

WHEN a pipeline ELT execution is triggered
THE SYSTEM SHALL complete extraction of 2M records in less than 40 minutes
using concurrent ThreadPoolExecutor with configurable max_workers (default 10)

WHEN the predictive module generates a 6-month projection
THE SYSTEM SHALL return results in less than 30 seconds

WHEN analytical queries are executed over the 2M-row dataset
THE SYSTEM SHALL use columnar Parquet format and DuckDB to read only required columns
without loading the full Parquet file into RAM

### 14. Fiabilidad

WHEN any write operation fails due to a MinIO connection error
THE SYSTEM SHALL notify the user and preserve the existing Parquet file without corruption

WHEN Airflow does not respond during pipeline monitoring (CU-11)
THE SYSTEM SHALL display the last known status with a notice of possible staleness

WHEN a user performs any write operation (create, edit, delete, configure, pipeline execute)
THE SYSTEM SHALL insert an immutable record in `pb_auditoria` with:
user_id, user_email, action, module, resource, result, and timestamp

WHEN the ELT pipeline fails during PocketBase extraction
THE SYSTEM SHALL automatically retry up to the configured retry_count before marking the task as failed

### 15. Seguridad

WHEN any request arrives at a protected FastAPI endpoint
THE SYSTEM SHALL verify the JWT signature using SECRET_KEY
and check the user's permissions in `roles_permisos` before responding

WHEN a user lacks the required permission for an action
THE SYSTEM SHALL respond with HTTP 403 Forbidden

WHEN a JWT token has expired or been tampered with
THE SYSTEM SHALL respond with HTTP 401 Unauthorized

WHEN credentials or sensitive configuration values are stored
THE SYSTEM SHALL store passwords as bcrypt hashes (PocketBase) and keep all credentials in .env,
never hardcoded in source files

### 16. Mantenibilidad

WHEN a new analytical module is added
THE SYSTEM SHALL require only: creating a module folder, registering it in PocketBase `modulos`,
and assigning permissions from the UI — without modifying existing code

WHEN a system administrator changes the LLM provider (CU-42)
THE SYSTEM SHALL apply the new provider without any code changes or service restarts

### 17. Portabilidad

WHEN the system is deployed on a new machine with Docker Desktop
THE SYSTEM SHALL start all services with a single `docker compose up -d` command

WHEN migrating from MinIO to AWS S3
THE SYSTEM SHALL require only changing the endpoint URLs in `.env` with no code changes

---

## Constraints

| Constraint | Detail |
|---|---|
| PocketBase perPage limit | Maximum 500 records per API request — requires pagination loop |
| Internal communication | All services communicate via Docker `elt-network` — no direct host access |
| No cross-layer FKs | No FK relationships between MinIO (Parquet) and PocketBase — connections are process-based via ELT |
| Audit log immutability | `pb_auditoria` accepts INSERT only — no UPDATE or DELETE operations allowed |
| Credentials isolation | All secrets in `.env` — never committed to git, never hardcoded |
| IAM at application layer | Permissions enforced in FastAPI, not via SQL GRANTs or MinIO policies |
| PocketBase collection creation | Use `"schema"` field (not `"fields"`) when creating collections via API v0.22.4 |
| Setup scripts are one-shot | Scripts 01, 02, and setup_pocketbase_admin run once during initialization only |
| pk=0 rows are immutable | Special rows with pk=0 in optional dimensions cannot be deleted (CU-15) |
