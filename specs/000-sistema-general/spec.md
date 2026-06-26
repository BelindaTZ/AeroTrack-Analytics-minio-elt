# AeroTrack Analytics — Especificación General del Sistema

## Identificación

| Campo | Valor |
|---|---|
| Sistema | AeroTrack Analytics |
| Versión constitución | 2.2.0 |
| Fecha | 2026-06-22 |
| Código fuente | `app/`, `dags/`, `scripts/` |
| Punto de entrada | `app/main.py` → `uvicorn app.main:app` |

---

## Objetivo

Plataforma web de inteligencia operacional para aerolíneas que ingesta datos de vuelos del BTS/FAA (fuente: `airline_2m.csv`), los procesa mediante un pipeline ELT orquestado por Apache Airflow, los transforma en un modelo dimensional Kimball y los expone a través de módulos de análisis, predicción y asistencia por IA accesibles según el rol del usuario.

---

## Alcance

- **4 entregas** organizadas por nivel de madurez analítica
- **14 módulos** con paquete FastAPI independiente
- **53 casos de uso** catalogados (CU-O, CU-T, CU-E)
- **3 capas de almacenamiento** separadas por principio arquitectónico

---

## Arquitectura de tres capas

```
┌─────────────────────────────────────────────────────────────────────┐
│ CAPA 1 — STAGING                                                    │
│  PocketBase: colección vuelos_raw (datos crudos desde fuente BTS)   │
│  MinIO aerotrack-raw: vuelos_raw.parquet (resultado de extract)     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ Pipeline ELT (Airflow DAG)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ CAPA 2 — ANALÍTICA                                                  │
│  MinIO aerotrack-dims:                                              │
│    fact_vuelo.parquet + 11 dim_*.parquet + 10 agg_*.parquet         │
│  Acceso exclusivo vía read_parquet() / load_agg() / load_enriched_fact() │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ FastAPI (solo lectura)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ CAPA 3 — OPERACIONAL                                                │
│  PocketBase: app_users, roles, permisos, modulos, roles_permisos,   │
│              auditoria, configuracion_sistema,                       │
│              conversaciones_asistente, asistente_fuentes            │
│  FastAPI: RBAC, auditoría, configuración del sistema                │
└─────────────────────────────────────────────────────────────────────┘
```

**Regla de separación:** Ningún módulo analítico lee de `vuelos_raw` ni de `aerotrack-raw`. Todos leen exclusivamente de `aerotrack-dims` (Principio I).

---

## Stack tecnológico

| Componente | Versión | Puerto | Uso |
|---|---|---|---|
| FastAPI + Jinja2 + Bootstrap 5.3.3 | Python 3.12 | 8000 | Web app |
| PocketBase | 0.22.4 | 8090 | RBAC + staging + operacional |
| MinIO | RELEASE.2025-09-07 | 9000 / 9001 | Parquet analítico |
| Apache Airflow | 2.9.3-python3.12 | 8080 | Orquestación ELT |
| PostgreSQL | 15 | interno | Metadatos Airflow (exclusivo) |
| jose (python-jose) | — | — | JWT HS256 |
| pandas + pyarrow | — | — | Lectura/escritura Parquet |
| statsmodels | — | — | Holt-Winters para predicción |

**Detección Docker:** `IN_DOCKER = os.path.exists("/.dockerenv")` en `app/config.py:6`

**Buckets MinIO:**
- `aerotrack-raw` → datos crudos después de extract
- `aerotrack-dims` → modelo dimensional final + agregaciones
- `aerotrack-exports` → archivos exportados (PDF, Excel, CSV)

---

## Dependencias Python

Archivo: `requirements.txt` (sincronizado con `Dockerfile`)

### Core
```
python-dotenv>=1.0.0
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
jinja2>=3.1.0
python-multipart>=0.0.9
```

### Data
```
pandas>=2.0.0
pyarrow>=14.0.0
minio>=7.2.0
```

### HTTP
```
requests>=2.31.0
httpx>=0.27.0
```

### Auth
```
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
```

### Reports
```
plotly>=5.18.0
openpyxl>=3.1.0
weasyprint>=62.0
```

### Utils
```
email-validator>=2.1.0
croniter>=2.0.0
```

### Dev/Test
```
pytest>=8.0.0
ruff>=0.4.0
mypy>=1.10.0
```

**Nota:** `weasyprint` es opcional. Si no está instalado, el endpoint PDF devuelve HTTP 501 y el resto del sistema funciona normalmente.

---

## Variables de entorno

Todas las variables se definen en `.env` (nunca se sube al repositorio). Template: `.env.example`

| Variable | Descripción | Obligatoria |
|---|---|---|
| `PB_URL` | URL PocketBase (host) | Sí |
| `PB_EMAIL` | Email admin PocketBase | Sí |
| `PB_PASSWORD` | Contraseña admin PocketBase | Sí |
| `MINIO_URL` | Endpoint MinIO (host) | Sí |
| `MINIO_ACCESS` | Access key MinIO | Sí |
| `MINIO_SECRET` | Secret key MinIO | Sí |
| `SECRET_KEY` | Clave firma JWT (mín 32 chars) | Sí |
| `ALGORITHM` | Algoritmo JWT (default: HS256) | No |
| `TOKEN_EXPIRE_MINUTES` | TTL token JWT (default: 60) | No |
| `AIRFLOW_ADMIN_USER` | Usuario Airflow | Sí |
| `AIRFLOW_ADMIN_PASSWORD` | Contraseña Airflow | Sí |
| `POSTGRES_USER` | Usuario Postgres (Airflow) | Sí |
| `POSTGRES_PASSWORD` | Contraseña Postgres | Sí |
| `FERNET_KEY` | Clave Fernet (Airflow) | Sí |
| `GROQ_API_KEY` | API key Groq (para IA) | No |
| `GEMINI_API_KEY` | API key Gemini (para IA) | No |
| `GMAIL_ADDRESS` | Gmail para SMTP (setup) | No |
| `GMAIL_APP_PASS` | Gmail app password | No |
| `ADMIN_NAME` | Nombre usuario admin inicial | No |

---

## Servicios Docker (docker-compose.yml)

| Servicio | Imagen | Puerto expuesto | Función |
|---|---|---|---|
| `minio` | quay.io/minio/minio | 9000, 9001 | Object storage S3 |
| `minio-init` | quay.io/minio/mc | — | Crea los 3 buckets al arranque |
| `pocketbase` | ghcr.io/muchobien/pocketbase:0.22.4 | 8090 | Base de datos operacional y staging |
| `aerotrack-setup` | Dockerfile.setup | — | Inicializa colecciones PocketBase |
| `postgres` | postgres:15 | — | Metadatos internos de Airflow |
| `airflow-init` | apache/airflow:2.9.3-python3.12 | — | Migración DB + usuario admin |
| `airflow-webserver` | apache/airflow:2.9.3-python3.12 | 8080 | UI y API REST de Airflow |
| `airflow-scheduler` | apache/airflow:2.9.3-python3.12 | — | Planificación de DAGs |
| `fastapi` | Dockerfile | 8000 | Aplicación web principal |

Todos los servicios comparten la red `elt-network` (bridge). Volúmenes persistentes: `minio-data`, `pocketbase-data`, `postgres-data`.

---

## Actores

| Actor | Descripción | Permisos típicos |
|---|---|---|
| Administrador | Gestiona usuarios, roles, configuración, pipeline | Todos los módulos: ver + crear + editar + eliminar + ejecutar + exportar + configurar |
| Analista | Consulta datos analíticos y genera reportes | dashboard, puntualidad, rutas, cancelaciones, reportes: ver + exportar |
| Usuario de IA | Usa el asistente conversacional | asistente_ia: ver + ejecutar |

---

## Tabla de módulos

| # | Módulo | Paquete | Prefix(es) | Entrega | CUs |
|---|---|---|---|---|---|
| 1 | Seguridad | `app/seguridad/` | `/auth`, `/auth/usuarios`, `/auth/roles` | 1 (Operativo) | CU-O01–O04 |
| 2 | Pipeline ELT | `app/pipeline_elt/` | `/pipeline` | 1 (Operativo) | CU-O05–O08 |
| 3 | Modelo Dimensional | `app/modelo_dimensional/` | `/modelo` | 1 (Operativo) | CU-O09–O11 |
| 4 | Dashboard | `app/dashboard/` | `/dashboard` | 2 (Táctico) | CU-T01–T03 |
| 5 | Puntualidad OTP | `app/puntualidad/` | `/puntualidad` | 2 (Táctico) | CU-T04–T05 |
| 6 | Rutas | `app/rutas/` | `/rutas` | 2 (Táctico) | CU-T06–T08 |
| 7 | Cancelaciones | `app/cancelaciones/` | `/cancelaciones` | 2 (Táctico) | CU-T09–T11 |
| 8 | Configuración | `app/configuracion/` | `/configuracion`, `/configuracion/estado` | 2 (Táctico) | CU-T12–T14 |
| 9 | Auditoría | `app/auditoria/` | `/auditoria` | 2 (Táctico) | CU-O12–O13 |
| 10 | Reportes | `app/reportes/` | `/reportes` | 2 (Táctico) | CU-T15–T18 |
| 11 | Predictivo IA | `app/predictivo/` | `/predictivo` | 3 (Estratégico) | CU-E01–E04 |
| 12 | Asistente IA | `app/asistente_ia/` | `/ia` | 3 (Estratégico) | CU-E05–E07 |
| 13 | Clientes | `app/clientes/` | `/clientes` | 4 (Lote 5) | CU-L01–L04 |
| 14 | Socios API | `app/socios_api/` | `/socios`, `/` (public) | 4 (Lote 5) | CU-L05–L08 |

**Registros de router en `app/main.py`:**

```python
app.include_router(auth_router,          prefix="/auth")
app.include_router(usuarios_router,      prefix="/auth/usuarios")
app.include_router(permisos_router,      prefix="/auth/roles")
app.include_router(roles_router,         prefix="/auth/roles")
app.include_router(pipeline_router,      prefix="/pipeline")
app.include_router(modelo_router,        prefix="/modelo")
app.include_router(dashboard_router,     prefix="/dashboard")
app.include_router(puntualidad_router,   prefix="/puntualidad")
app.include_router(rutas_router,         prefix="/rutas")
app.include_router(cancelaciones_router, prefix="/cancelaciones")
app.include_router(configuracion_router, prefix="/configuracion")
app.include_router(monitoreo_router,     prefix="/configuracion/estado")
app.include_router(auditoria_router,     prefix="/auditoria")
app.include_router(reportes_router,      prefix="/reportes")
app.include_router(predictivo_router,    prefix="/predictivo")
app.include_router(informe_router,       prefix="/predictivo")
app.include_router(ia_router,            prefix="/ia")
app.include_router(clientes_router,      prefix="/clientes")
app.include_router(socios_router,        prefix="/socios")
app.include_router(api_router,           prefix="")
```

---

## Flujo de datos extremo a extremo

```
[Fuente: airline_2m.csv / PocketBase vuelos_raw]
        │
        ▼  DAG: extract (timeout 2h)
[vuelos_raw.parquet — archivo local temporal]
        │
        ▼  DAG: load (timeout 30min)
[MinIO aerotrack-raw / vuelos_raw.parquet]
        │
        ▼  DAG: transform (timeout 2h)
[MinIO aerotrack-dims / fact_vuelo.parquet + 11 dim_*.parquet + 10 agg_*.parquet]
        │
        ▼  FastAPI (lectura vía read_parquet / load_agg / load_enriched_fact)
[Módulos analíticos: dashboard, puntualidad, rutas, cancelaciones, predictivo, IA]
```

---

## Patrones transversales implementados

| Patrón | Implementación | Archivo |
|---|---|---|
| RBAC | `require_permission(modulo, accion)` | `app/shared/deps.py:72` |
| Caché de permisos | `_perm_cache` dict, TTL 300s | `app/shared/deps.py:15` |
| Auditoría INSERT-only | `audit.registrar()` con try/except | `app/shared/utils/audit.py` |
| Caché analítico | `_agg_cache` + `_fact_cache`, TTL 600s | `app/shared/analytics.py` |
| Paginación | `PAGE_SIZE = 50` | `app/shared/templates.py:44` |
| JWT cookie HTTP-only | `access_token`, HS256, TTL 60min | `app/seguridad/jwt/service.py` |
| Degradación resiliente | try/except silencioso en servicios no críticos | Principio VI |
