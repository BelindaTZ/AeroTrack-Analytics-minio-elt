# Consideraciones de Implementación

Guía para replicar AeroTrack Analytics desde cero.

---

## 1. Orden de implementación (dependency chain)

```
1. Seguridad (JWT + RBAC)          ← base de todo
2. Pipeline ELT (Airflow DAG)      ← provee datos
3. Modelo Dimensional (CRUD)       ← valida esquema
4. Dashboard (KPIs)                ← primer módulo analítico
5. Módulos de análisis             ← consumen agg tables
6. Predictivo + Asistente IA       ← capa inteligencia
7. Clientes + Socios API           ← capa negocio
```

**Regla:** Cada módulo solo lee de `aerotrack-dims` (nunca de `vuelos_raw`).

---

## 2. Convenciones de código

### Nombres de archivo
- `app/{modulo}/router.py` → endpoints FastAPI
- `app/{modulo}/templates/{modulo}/` → templates Jinja2
- `app/shared/` → código compartido (analytics, clients, deps, templates)
- `dags/aerotrack_tasks.py` → funciones del pipeline ELT

### Variables MAYÚSCULAS dentro de funciones
El proyecto usa MAYÚSCULAS para constantes dentro de funciones (convención, no error de linting):
```python
def extract_pipeline():
    PB_BASE_URL = config.PB_BASE_URL  # ← correcto en este proyecto
    pb_page_size = 500                 # ← variables locales en snake_case
```

### Imports condicionales
```python
# Patrón para dependencias opcionales (ej: weasyprint)
try:
    from weasyprint import HTML as WP_HTML
    _WEASYPRINT_OK = True
except ImportError:
    _WEASYPRINT_OK = False
```

### Detección de Docker
```python
IN_DOCKER = os.path.exists("/.dockerenv")
# Usado en TODOS los config.py para switching de URLs
```

---

## 3. Patrón de configuración (3 config.py)

Hay 3 archivos de configuración que leen el mismo `.env`:

| Archivo | Consumidor | Ubicación |
|---|---|---|
| `app/config.py` | FastAPI web app | `app/config.py` |
| `dags/config.py` | Airflow DAG tasks | `dags/config.py` |
| `scripts/config.py` | Setup scripts | `scripts/config.py` |

**Regla:** Todos usan `load_dotenv()` + `os.getenv()` con fallbacks vacíos (sin defaults hardcodeados).

---

## 4. Patrón de routers FastAPI

```python
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.shared.deps import require_permission, render

router = APIRouter()

# Dependencia de permiso (se ejecuta antes del handler)
_perm_ver = require_permission("modulo", "ver")

@router.get("", response_class=HTMLResponse)
def index(request: Request):
    _perm_ver(request)  # Lanza PermissionError si no tiene permiso
    return render(request, "modulo/index.html", {"datos": datos})
```

---

## 5. Patrón de caching

| Capa | TTL | Variable |
|---|---|---|
| Fact table | 600s (10min) | `_fact_cache` en `analytics.py` |
| Agregaciones | 600s (10min) | `_agg_cache` en `analytics.py` |
| Dimensiones | 300s (5min) | `_dim_cache` en `analytics.py` |
| Permisos | 300s (5min) | `_perm_cache` en `deps.py` |
| Fuentes IA | 60s | `_SOURCE_CACHE` en `rag.py` |
| Config IA | 60s | `llm_client.py` |

**Invalidación:** `invalidate_permission_cache()` se llama al cambiar permisos.

---

## 6. Modelo dimensional (Kimball)

### Estructura de archivos en MinIO
```
aerotrack-dims/
├── fact_vuelo.parquet
├── dim_tiempo.parquet
├── dim_aerolinea.parquet
├── dim_avion.parquet
├── dim_ruta.parquet
├── dim_aeropuerto.parquet
├── dim_cancelacion.parquet
├── dim_retraso_causa.parquet
├── dim_clasificacion_retraso.parquet
├── dim_horario.parquet
├── dim_distancia.parquet
├── dim_desvio.parquet
├── agg_otp_aerolinea_mes.parquet
├── agg_cancelaciones_causa.parquet
├── agg_cancelaciones_aerolinea_causa.parquet
├── agg_cancelaciones_ruta.parquet
├── agg_kpi_global_dia.parquet
├── agg_rutas_eficiencia.parquet
├── agg_causas_retraso_mes.parquet
├── agg_otp_dia_semana.parquet
├── agg_otp_aerolinea_dia_semana.parquet
└── agg_desvios_ruta.parquet
```

### Columnas FK en fact_vuelo
Todas las FK usan `int64` y se normalizan con:
```python
for col in fact.columns:
    if col.startswith("fk_") or col == "pk_vuelo":
        fact[col] = pd.to_numeric(fact[col], errors="coerce").fillna(0).astype("int64")
```

---

## 7. RAG (Asistente IA)

### Flujo
```
Pregunta usuario
    ↓
parse_intent() → filtros (airline, year, month, ruta, dow)
    ↓
_detect_question_type() → tipos (delay_cause, cancelacion, etc.)
    ↓
build_context() → selecciona secciones relevantes desde Parquet
    ↓
build_messages() → construye prompts para LLM
    ↓
llm_client.py → envía a Groq/Anthropic/Gemini/OpenAI
```

### Fuentes de datos (10 tablas)
Cada fuente se puede activar/desactivar desde PocketBase (`asistente_fuentes`).

### System prompt (obligatorio)
- Solo citar valores LITERALMENTE del contexto
- PROHIBIDO calcular, estimar o extrapolar
- Responder en español
- Formato markdown con tablas para rankings

---

## 8. Seguridad

### JWT
- Algoritmo: HS256
- Payload: `{sub: uuid, email, nombre, rol_id, activo, exp}`
- Cookie: HTTP-only, SameSite=Lax, MaxAge=3600
- SECRET_KEY: obligatoria sin default (error en Docker si falta)

### RBAC
- 13 módulos con permisos: ver, crear, editar, eliminar, ejecutar, exportar, configurar
- 3 roles predefinidos: administrador, analista, viewer
- Cache de permisos: 300s por rol

### Auditoría
- INSERT-only (PocketBase rules + FastAPI)
- Timezone: UTC-5 (America/Guayaquil) fijo
- Acciones controladas: login, login_fallido, logout, editar, configurar, exportar

---

## 9. Docker

### Health checks
| Servicio | Comando | Intervalo |
|---|---|---|
| minio | `curl -f http://localhost:9000/minio/health/live` | 15s |
| pocketbase | `wget --spider -q http://localhost:8090/api/health` | 15s |
| postgres | `pg_isready -U airflow` | 10s |
| airflow-webserver | `curl -f http://localhost:8080/health` | 30s |
| fastapi | `curl -f http://localhost:8000/health` | 30s |

### Volúmenes persistentes
- `minio-data` → datos Parquet
- `pocketbase-data` → usuarios, config, auditoría
- `postgres-data` → metadatos Airflow

---

## 10. CI/CD

### GitHub Actions (`.github/workflows/ci.yml`)
```yaml
jobs:
  lint:     ruff check + ruff format --check
  test:     pytest tests/
  docker:   docker build (después de lint + test)
```

### Comandos de verificación
```bash
ruff check app/ dags/           # Linting
ruff format --check app/ dags/  # Formato
python -m pytest tests/ -v      # Tests
```
