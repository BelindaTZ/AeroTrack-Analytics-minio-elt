# AeroTrack Analytics — Tech Stack

## Stack principal

| Capa | Tecnología | Versión | Rol |
|---|---|---|---|
| Backend | Python + FastAPI | 3.13 / latest | API REST + renderizado server-side |
| Frontend | Bootstrap 5 + Chart.js | 5.x / latest | Templates Jinja2, visualizaciones |
| Orquestación | Apache Airflow (TaskFlow API) | 2.9.3 | DAG `aerotrack_elt_pipeline` |
| Almacenamiento analítico | MinIO (S3-compatible) + Apache Parquet | latest | Modelo estrella en Parquet |
| Almacenamiento operativo | PocketBase | 0.22.4 | Datos fuente, usuarios, roles, config, auditoría |
| Metadatos Airflow | PostgreSQL | 15 | Base de datos interna de Airflow |
| Contenedores | Docker Desktop + docker-compose | 3.8 | Todo el stack |
| Red interna | `elt-network` (bridge) | — | Comunicación entre contenedores |

## Servicios Docker (9 en total)

| Servicio | Container | Puerto | `restart` |
|---|---|---|---|
| MinIO | `minio` | 9000 (API), 9001 (UI) | implícito |
| MinIO Init | `minio-init` | — | `no` (one-shot) |
| PocketBase | `pocketbase` | 8090 | implícito |
| AeroTrack Setup | `aerotrack-setup` | — | `no` (one-shot) |
| PostgreSQL | `postgres-airflow` | — | implícito |
| Airflow Init | `airflow-init` | — | `no` (one-shot) |
| Airflow Webserver | `airflow-webserver` | 8080 | `unless-stopped` |
| Airflow Scheduler | `airflow-scheduler` | — | `unless-stopped` |
| FastAPI App | `fastapi-app` | 8000 | `unless-stopped` |

## Buckets MinIO

| Bucket | Variable | Contenido |
|---|---|---|
| `aerotrack-raw` | `MINIO_BUCKET_RAW` | Parquet crudo extraído de PocketBase |
| `aerotrack-dims` | `MINIO_BUCKET_DIMS` | Modelo estrella (fact_vuelo + 11 dims) |
| `aerotrack-exports` | `MINIO_BUCKET_EXPORTS` | Reportes PDF y Excel generados |

## Modelo de datos — Estrella de Kimball

```
fact_vuelo (PK: pk_vuelo)
├── dim_tiempo          (pk_tiempo)
├── dim_aerolinea       (pk_aerolinea)
├── dim_aeropuerto      (pk_aeropuerto)
├── dim_avion           (pk_avion)
├── dim_retraso_causa   (pk_retraso_causa)
├── dim_cancelacion     (pk_cancelacion)
├── dim_distancia       (pk_distancia)
├── dim_desvio          (pk_desvio)
├── dim_horario         (pk_horario)
├── dim_clasificacion_retraso (pk_clasificacion)
└── dim_ruta            (pk_ruta)
```

Filas especiales con `pk=0` en dimensiones opcionales (desviado, causa de retraso): no eliminables.

## Colecciones PocketBase

| Colección | Propósito |
|---|---|
| `app_users` | Usuarios del sistema (Admin, Analista) |
| `roles` | Definición de roles (es_sistema=true protegidos) |
| `modulos` | Módulos del sistema registrados |
| `roles_permisos` | RBAC: matriz rol × módulo × acción |
| `configuracion_sistema` | Parámetros dinámicos (email SMTP, umbrales, pipeline) |
| `pb_auditoria` | Log de auditoría inmutable (INSERT-only) |

## Decisiones arquitectónicas clave

### RBAC en FastAPI (no SQL GRANTs)
MinIO no es BD relacional y PocketBase solo permite permisos por colección completa. El RBAC se implementa en capa de aplicación: cada endpoint FastAPI verifica el JWT y consulta `roles_permisos` antes de responder. Sin permiso → HTTP 403. Los permisos son configurables desde la UI (CU-08) sin tocar código.

### Parquet sobre SQL para el modelo dimensional
Formato columnar con compresión 5-10x respecto al CSV de 2M filas. Compatible con Spark, Pandas, DuckDB y toda plataforma de BI. Las consultas analíticas con DuckDB leen solo las columnas necesarias sin cargar el Parquet completo en RAM.

### config.py autodiscoverable (Docker vs local)
Detecta el contexto con `os.path.exists("/.dockerenv")`. Las URLs de MinIO y PocketBase se resuelven automáticamente. Un solo archivo `config.py` es importado por los scripts ELT, el DAG de Airflow y la webapp FastAPI.

### Configuración dinámica en PocketBase
Los parámetros del sistema (umbrales de alertas, BATCH_SIZE, max_workers, SMTP, config IA) se almacenan en la colección `configuracion_sistema` de PocketBase, NO en `.env`. El `.env` es exclusivamente para credenciales de infraestructura que no deben persistir en BD.

### Auditoría inmutable
La colección `pb_auditoria` es INSERT-only: ningún endpoint acepta UPDATE o DELETE sobre ella. Registra: `user_id`, `user_email`, `accion`, `modulo`, `recurso`, `resultado`, `timestamp`.

### Extracción concurrente de PocketBase
`ThreadPoolExecutor(max_workers=10)` para superar el límite de 500 registros por página de la API PocketBase v0.22.4. Configurable vía `max_workers` en `configuracion_sistema`.

### DAG solo orquesta scripts 03 y 04
Los scripts 01, 02 y `setup_pocketbase_admin.py` son inicialización manual (ejecutados por `aerotrack-setup` container one-shot). El DAG `aerotrack_elt_pipeline` únicamente orquesta extracción (`03_extraer_pb_a_minio.py`) y transformación (`04_transformar_dimensiones.py`).

## Variables de entorno (.env)

Todas las credenciales en `.env` (excluido del repositorio con `.gitignore`). El archivo `.env.example` documenta todas las variables sin valores.

| Variable | Descripción |
|---|---|
| `MINIO_ACCESS` | Usuario root de MinIO |
| `MINIO_SECRET` | Contraseña root de MinIO |
| `MINIO_BUCKET_RAW` | Nombre del bucket raw |
| `MINIO_BUCKET_DIMS` | Nombre del bucket del modelo dimensional |
| `MINIO_BUCKET_EXPORTS` | Nombre del bucket de exportaciones |
| `SECRET_KEY` | Clave para firma de JWT |
| `PB_EMAIL` / `PB_PASSWORD` | Credenciales admin de PocketBase |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | Credenciales de PostgreSQL para Airflow |
| `AIRFLOW_ADMIN_USER` / `AIRFLOW_ADMIN_PASSWORD` | Usuario admin de Airflow |
| `FERNET_KEY` | Clave de cifrado interno de Airflow |

## Restricciones de la API PocketBase v0.22.4

- Máximo `perPage: 500` registros por petición
- Crear colecciones usa el campo `"schema"` (NO `"fields"`)
- Los scripts de setup deben ser idempotentes (verificar existencia antes de crear)
- Autenticación: endpoint `/api/admins/auth-with-password` para el admin

## Portabilidad

- **Docker-first:** funciona en Windows, macOS y Linux sin cambios de código
- **MinIO → AWS S3:** cambiar solo las URLs en `.env`
- **PocketBase reemplazable:** cualquier backend con REST API
- **FastAPI desplegable:** Railway, Render, AWS ECS o cualquier runtime de contenedores
- **Múltiples proveedores LLM:** OpenAI, Anthropic, Gemini o endpoint custom (configurado desde UI en CU-42)
