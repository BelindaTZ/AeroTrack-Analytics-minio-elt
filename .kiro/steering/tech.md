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
Detecta el contexto con `os.path.exists("/.dockerenv")`. Las URLs de MinIO y PocketBase se resuelven automáticamente. Un solo archivo `config.py` es importado por los scripts ELT, el DAG de Airflow y la app FastAPI.

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

## Restricciones y gotchas de Airflow 2.9.3

### Auth backend de la API REST — CRÍTICO
La imagen oficial `apache/airflow:2.9.3` trae por defecto `auth_backends = airflow.api.auth.backend.session` (solo cookies de sesión del navegador). Cualquier cliente programático (FastAPI, curl, scripts) necesita basic auth. La variable **debe** declararse explícitamente:

```yaml
AIRFLOW__API__AUTH_BACKENDS: 'airflow.api.auth.backend.basic_auth,airflow.api.auth.backend.session'
```

Esta variable debe estar en los tres servicios: `airflow-init`, `airflow-webserver` y `airflow-scheduler`. Sin ella, toda llamada a `/api/v1/...` devuelve `403 FORBIDDEN` aunque las credenciales sean correctas y el rol Admin tenga todos los permisos FAB.

### Sincronización de permisos FAB (`AIRFLOW__FAB__UPDATE_FAB_PERMS`)
La clave `[webserver] update_fab_perms` fue deprecada en 2.9.3; se renombró a `[fab] update_fab_perms`. Declarar:

```yaml
AIRFLOW__FAB__UPDATE_FAB_PERMS: 'true'
```

en `airflow-webserver` garantiza que los permisos FAB del rol Admin se sincronicen en cada arranque, evitando errores 403 por permisos desactualizados tras recrear el contenedor.

### `docker-compose restart` NO aplica nuevas variables de entorno
`docker-compose restart` reinicia el proceso dentro del contenedor existente — **no** re-lee `docker-compose.yml`. Si se agrega o modifica una variable `AIRFLOW__*` después de haber levantado los servicios, el contenedor seguirá usando la configuración antigua hasta que sea recreado:

```bash
# correcto — recrea el contenedor con la nueva config
docker-compose up -d --force-recreate airflow-webserver

# incorrecto — el contenedor ignora los cambios nuevos en docker-compose.yml
docker-compose restart airflow-webserver
```

Verificar que una variable está activa dentro del contenedor antes de depurar más:

```bash
docker exec airflow-webserver bash -c "echo \$AIRFLOW__API__AUTH_BACKENDS"
docker exec airflow-webserver airflow config get-value api auth_backends
```

## Restricciones del frontend — auto-refresh

### Evolución del polling en el módulo Pipeline

El módulo Pipeline necesita refrescar datos cada 10 segundos para mostrar el estado del DAG en tiempo real. La solución pasó por tres iteraciones:

#### ❌ Iteración 1 — `location.reload()` (descartada)
`location.reload()` conserva los query params en la URL. Si un POST redirige a `/pipeline?error=<mensaje>`, el error fantasma reaparece en cada ciclo de refresco.

#### ⚠️ Iteración 2 — `window.location.href = '/pipeline'` (descartada)
Descarta los query params correctamente, pero hace una navegación completa: el browser trata la página como nueva y el scroll vuelve al top. Tedioso cuando el usuario está revisando la lista de tareas más abajo en el módulo.

```javascript
// INCORRECTO para UX — pierde posición de scroll
window.location.href = '/pipeline';
```

#### ✅ Iteración 3 — Fetch parcial (implementación actual)
Endpoint dedicado `GET /pipeline/estado-full` devuelve `{estado, historial}` como JSON. El JS actualiza el DOM en lugar de navegar, preservando el scroll.

```javascript
// Cada 10 s: fetch → actualizar DOM en lugar de recargar
fetch('/pipeline/estado-full', { credentials: 'same-origin' })
  .then(r => r.json())
  .then(applyData);
```

**Arquitectura del endpoint:**
- Ruta: `GET /pipeline/estado-full` en `app/pipeline_elt/router.py`
- Devuelve: `{"estado": {..., "task_instances": [...]}, "historial": [...]}`
- Reutiliza `af.get_dag_status()` + `af.get_dag_runs(limit=5)`

**Qué actualiza el JS sin recargar:**
| Sección | Cómo |
|---|---|
| Hero (icono, título, badge, run ID, botón) | Mutación de atributos y `textContent` |
| Barra de progreso (%, animación) | `style.width` + toggle clase `anim` |
| Timeline de tareas | `innerHTML` del `#task-timeline` |
| Tabla "Últimas ejecuciones" | `innerHTML` del `tbody` dentro de `#runs-section` |

**Caso especial — cambio estructural:** si el estado pasa de `no_runs` a cualquier otro (o viceversa), las secciones de progreso y tareas no existen en el DOM porque el template Jinja2 las omite con `{% if state != 'no_runs' %}`. En ese caso el JS cae intencionalmente a `window.location.reload()` para obtener el HTML correcto. Esto solo ocurre cuando el estado cambia de raíz (no durante un pipeline en ejecución).

```javascript
var hasProgressInDOM = !!document.getElementById('pipeline-progress-section');
var needsProgress    = st !== 'no_runs';
if (hasProgressInDOM !== needsProgress) {
  window.location.reload();   // único caso donde se recarga completo
  return;
}
```

**IDs requeridos en el template** (`panel.html`) para que el JS encuentre los contenedores:
- `id="pipeline-progress-section"` — en el div `.pipeline-progress-section`
- `class="task-count-text"` — en el párrafo de conteo de tareas
- `id="task-timeline"` — ya existía en la lista de tareas
- `id="runs-section"` — en el div `.runs-section` del historial

## Botón global "Volver" — patrón de implementación

### Objetivo
Proporcionar un botón de regreso global en todas las páginas secundarias (sub-páginas con breadcrumb padre), sin modificar cada template individualmente.

### Implementación
El botón se inyecta dinámicamente en `aerotrack-ui.js` mediante `initBackButton()`, llamado desde `init()` al cargar el DOM.

**Lógica de detección automática:**
- Busca el elemento `.topbar-breadcrumb` en el topbar
- Si contiene al menos un `<a>`, la página tiene un padre → se muestra el botón
- Si no hay `<a>` (página raíz: Pipeline, Modelo, Usuarios, etc.) → no aparece nada

**Label dinámico:** usa el texto del último `<a>` del breadcrumb (= padre inmediato). Ejemplo: en "Pipeline ELT › Historial › Logs", el botón muestra "← Historial".

**Fallback de navegación:** `history.back()` si hay historial, `location.href` al enlace del padre si el usuario llegó por URL directa.

**Posición:** arriba a la derecha del área de contenido (`#content`), dentro de un `div.at-back-btn-wrap` con `display:flex; justify-content:flex-end`.

**Estilo:** pill suave — fondo `--at-surface`, borde `--at-border`, texto `--at-muted`, ícono flecha en `--at-blue-500`. Hover: borde azul + glow ring.

### Preservación del scroll del sidebar entre navegaciones

El `#sidebar` tiene `overflow-y: auto` y es desplazable cuando hay muchos módulos. Una recarga de página completa resetea `scrollTop = 0`, obligando al usuario a volver a bajar cada vez que navega.

**Solución:** `initSidebarScrollRestore()` en `aerotrack-ui.js`, llamado desde `init()`.

- **Al hacer clic** en cualquier `.nav-item-link[href]` del sidebar, guarda `sidebar.scrollTop` en `sessionStorage` con clave `at_sidebar_scroll`.
- **Al cargar la nueva página**, lee ese valor, lo aplica a `sidebar.scrollTop` y borra la entrada.

No requiere cambios en templates. Funciona automáticamente para todos los módulos presentes y futuros. `sessionStorage` se limpia solo al cerrar el tab.

```javascript
// Patrón — no duplicar, ya está en initSidebarScrollRestore()
sessionStorage.setItem('at_sidebar_scroll', sidebar.scrollTop);  // antes de navegar
sidebar.scrollTop = parseInt(sessionStorage.getItem('at_sidebar_scroll'), 10) || 0;  // al cargar
```

### Cache-busting de archivos estáticos
FastAPI `StaticFiles` sirve los archivos desde disco sin versionar. El navegador los cachea agresivamente. Para forzar recarga al cambiar CSS o JS, se añade un query param de versión en `base.html`:

```html
<link href="/static/css/aerotrack-theme.css?v=3" rel="stylesheet" />
<script src="/static/js/aerotrack-ui.js?v=3"></script>
```

**Regla:** incrementar `v=N` en `base.html` cada vez que se modifique `aerotrack-theme.css` o `aerotrack-ui.js`. Versión actual: `v=4`.

## Convención de layout para formularios de página completa

Los formularios que se renderizan como **página completa** (no modales) deben ocupar el ancho total del área de contenido `#content`. **Nunca** se les aplica `max-width` inline al elemento `.at-card` contenedor.

### Regla
- **Formulario de página completa** → `.at-card` sin `max-width`, campos distribuidos en `row g-3` con `col-sm-6` (o columnas apropiadas según la cantidad de campos).
- **Formulario modal / ventana emergente** → sin restricción de ancho en el card interno; el `modal-dialog` ya gestiona el ancho.

### Motivo
Un `max-width` fijo en un card de página completa deja un espacio vacío visible a la derecha del card, lo que se ve desequilibrado en pantallas medianas y grandes (el sidebar ocupa ~240 px y el resto es espacio aprovechable).

### Archivos de referencia (implementación actual)
| Template | Campos en grid |
|---|---|
| `app/seguridad/templates/roles/form.html` | `col-sm-6` × 2 (Nombre, Descripción) |
| `app/seguridad/templates/usuarios/form.html` | `col-sm-6` × 2 + `col-sm-4` (Nombre, Email, Rol) |
| `app/modelo_dimensional/templates/modelo_dimensional/form_registro.html` | `col-sm-6` dinámico por columnas de tabla |

Los modales (`usuarios/lista.html` → crear usuario, confirm modal en `base.html`) no se ven afectados por esta convención.

## Portabilidad

- **Docker-first:** funciona en Windows, macOS y Linux sin cambios de código
- **MinIO → AWS S3:** cambiar solo las URLs en `.env`
- **PocketBase reemplazable:** cualquier backend con REST API
- **FastAPI desplegable:** Railway, Render, AWS ECS o cualquier runtime de contenedores
- **Múltiples proveedores LLM:** OpenAI, Anthropic, Gemini o endpoint custom (configurado desde UI en CU-42)

---

## Patrones de performance — Entrega 2

Problemas detectados y resueltos durante la Entrega 2 por carga lenta al navegar entre módulos analíticos. Documentados como patrones obligatorios para Entrega 3 y siguientes.

---

### P-01 · Estrategia de caché en 3 capas

Toda página analítica que lea datos de MinIO o PocketBase debe implementar los tres niveles de caché siguientes. El acceso frío a MinIO (2M filas) puede tardar 10+ segundos; con los tres niveles activos, las visitas posteriores son < 200 ms.

#### Capa 1 — Fact table completo (`app/shared/analytics.py`)

`_load_base_fact()` cachea `fact_vuelo` + 8 joins con dimensiones en `_fact_cache` (TTL 10 min). Es el paso más caro (lectura MinIO + merges pandas). El módulo lo llama mediante `load_enriched_fact(filtros)`.

```python
# _fact_cache global en analytics.py
_fact_cache: dict = {"df": None, "expires": 0.0, "bucket": ""}
_FACT_TTL = 600  # 10 min
```

#### Capa 2 — Listas de dimensiones (`app/shared/analytics.py`)

`get_aerolinas()` y `get_years()` se llaman en **cada** módulo para poblar los dropdowns de filtro. Sin caché hacen 2 lecturas MinIO extra por página. Se cachean en `_dim_cache` (TTL 5 min).

```python
_dim_cache: dict = {}
_DIM_TTL = 300  # 5 min, clave = f"aerolinas:{bucket}" | f"years:{bucket}"
```

**Regla:** cualquier función que lea una tabla de dimensión entera para obtener una lista de valores únicos (aerolíneas, años, aeropuertos, etc.) debe seguir este patrón.

#### Capa 3 — Resultados computados por módulo

Aunque el fact esté cacheado, los groupbys + Plotly sobre 2M filas tardan 2–4 s por página. Cada módulo analítico debe cachear sus propios resultados computados en un `_page_cache` local, con clave `str(sorted(filtros.items()))` y TTL 5 min.

```python
# En cada router analítico (dashboard, puntualidad, rutas, cancelaciones, etc.)
_page_cache: dict = {}
_PAGE_TTL = 300

def _compute_page(filtros: dict, ...) -> dict:
    key = str(sorted(filtros.items()))
    entry = _page_cache.get(key)
    if entry and time.time() < entry["expires"]:
        return entry["data"]
    df = load_enriched_fact(filtros or None)
    data = {
        "kpis":   _calcular_kpis(df),
        "charts": _generar_graficos(df),
        # ... resto de computaciones pesadas
    }
    _page_cache[key] = {"data": data, "expires": time.time() + _PAGE_TTL}
    return data

@router.get("", response_class=HTMLResponse)
def mi_modulo(request: Request, year: str = "", ...):
    filtros = {k: v for k, v in {"year": year, ...}.items() if v}
    data = _compute_page(filtros)
    return render(request, "template.html", {**data, ...})
```

**Regla:** el endpoint `/narrativa` del mismo módulo también debe llamar `_compute_page(filtros)` — así reutiliza el resultado cacheado sin recalcular.

#### TTL de configuración (PocketBase)

Las funciones que leen `configuracion_sistema` (umbrales de alertas, umbral de rutas ineficientes, etc.) también deben cachearse. TTL recomendado 60 s — lo suficiente para amortiguar navegación entre módulos sin ocultar cambios de configuración.

```python
_umbrales_cache: dict = {"data": None, "expires": 0.0}
_UMBRALES_TTL = 60

def _get_umbrales() -> dict:
    global _umbrales_cache
    if _umbrales_cache["data"] is not None and time.time() < _umbrales_cache["expires"]:
        return _umbrales_cache["data"]
    # ... leer PocketBase ...
    _umbrales_cache = {"data": result, "expires": time.time() + _UMBRALES_TTL}
    return result
```

---

### P-02 · Narrativa IA asíncrona

**Problema:** `generar_narrativa()` llama a Grok 3 mini / Gemini 2.0 Flash con timeout 12 s. Al llamarse dentro del route principal bloqueaba **toda** la respuesta HTTP hasta que el LLM contestara.

**Solución:** separar la narrativa en un endpoint JSON propio y cargarlo desde el cliente con `fetch` tras renderizar la página.

#### Backend — endpoint `/narrativa`

Cada módulo analítico que use narrativa IA debe exponer:

```python
@router.get("/narrativa")
def narrativa_json(request: Request, year: str = "", month: str = "", airline: str = ""):
    _perm_ver(request)
    try:
        filtros = {k: v for k, v in {"year": year, ...}.items() if v}
        data = _compute_page(filtros)          # reutiliza caché de Capa 3
        ctx = {"KPI 1": data["kpis"]["..."], ...}
        return JSONResponse(generar_narrativa(ctx, "Nombre del módulo"))
    except Exception:
        return JSONResponse({"texto": "", "proveedor": "", "desde_cache": False})
```

El endpoint siempre retorna el mismo shape `{texto, proveedor, desde_cache}`. En caso de error devuelve campos vacíos — el JS simplemente oculta la tarjeta.

`generar_narrativa()` tiene su propio caché TTL 5 min (clave MD5 del prompt), por lo que navegaciones repetidas dentro de la misma sesión devuelven respuesta instantánea.

#### Frontend — div con `data-narrativa-url`

En el template, reemplazar el bloque `{% if narrativa.texto %}` con:

```html
<!-- La URL base; el JS adjunta los query params actuales automáticamente -->
<div id="narrativa-async"
     class="narrativa-card"
     data-narrativa-url="/MI_MODULO/narrativa"
     style="display:none">
</div>
```

`initNarrativaAsync()` en `aerotrack-ui.js` detecta el `id="narrativa-async"`, muestra un skeleton de carga, llama al endpoint pasando los query params actuales de `window.location.search`, y pinta el resultado. Se expone como `AT.initNarrativaAsync()` para que los módulos con live filter puedan rellamarla tras un swap de DOM.

```javascript
// En el callback del live filter, tras el innerHTML swap:
if (window.AT) AT.initNarrativaAsync();
```

**Regla:** nunca llamar `generar_narrativa()` dentro de un route `HTMLResponse`. Siempre en un endpoint separado `GET /modulo/narrativa`.

---

### P-03 · No releer dimensiones que ya están en el fact enriquecido

`load_enriched_fact()` ya hace join con todas las dimensiones. Releer una dimensión directamente desde MinIO en una función analítica duplica la I/O de red sin beneficio.

**Ejemplo real (bug corregido):** `_calcular_ranking()` en `rutas/ranking_eficiencia.py` releía `dim_ruta` para obtener `OriginCityName`/`DestCityName`, cuando esas columnas ya estaban disponibles en el DataFrame enriquecido recibido como argumento.

```python
# ❌ Antes — lectura innecesaria de MinIO
dim_r = read_parquet(MINIO_BUCKET_DIMS, "dim_ruta")
lookup_o = dict(zip(dim_r["OriginCode"], dim_r["OriginCityName"]))

# ✅ Ahora — usa lo que ya trajo load_enriched_fact()
if "OriginCityName" in df.columns:
    city_o = df.drop_duplicates("OriginCode").set_index("OriginCode")["OriginCityName"].to_dict()
```

**Regla:** antes de importar `read_parquet` o `MINIO_BUCKET_DIMS` en un módulo analítico, verificar si las columnas necesarias ya vienen en el `df` recibido de `load_enriched_fact()`.

---

### P-04 · Caché de `_get_ia_config()` en `ia_narrativa.py`

`generar_narrativa()` consulta PocketBase en cada invocación para obtener las claves API de Grok y Gemini. Sin caché esto es un round-trip PocketBase bloqueante antes de cada llamada al LLM.

Caché TTL 2 min en `_cfg_cache`. Los cambios de clave API en la UI de configuración tardan máximo 2 min en reflejarse — comportamiento aceptable.

```python
_cfg_cache: dict = {"data": None, "expires": 0.0}
_CFG_TTL = 120
```

---

### P-05 · Indicador visual de carga en navegación lateral

**Problema:** al hacer clic en un ítem del sidebar el navegador congelaba la UI mientras el servidor procesaba la primera visita (caché frío). Sin feedback visual, parecía que el clic no había funcionado.

**Solución:** `initNavLoadingBar()` en `aerotrack-ui.js` adjunta un listener `click` a todos los `.nav-item-link[href]` del sidebar. Al activarse, inserta un `<div id="at-nav-bar">` fijo en el top de la pantalla con animación CSS `at-page-load` (barra azul que progresa del 0% al 94% en 10 s). La barra desaparece automáticamente cuando el navegador carga la nueva página.

No requiere cambios en los templates. Se inicializa automáticamente desde `init()`.

---

## Bugs conocidos y soluciones — Entrega 2

Errores reales encontrados durante la implementación de la Entrega 2. Documentados para evitar reincidencia.

---

### B-01 · Merge type mismatch int32 vs str en pandas

**Síntoma:** `You are trying to merge on int32 and str columns for key 'fk_aerolinea'`

**Causa:** Parquet con PyArrow puede leer columnas integer como `int32` o incluso como `object`/`str` dependiendo de cómo fueron escritas. Los FKs de `fact_vuelo` y los PKs de las dimensiones no siempre coinciden en dtype tras el ciclo write→read.

**Solución aplicada:** En `app/shared/analytics.py`, antes de cualquier merge:
1. Todas las columnas `fk_*` de `fact_vuelo` se castean a `int64` con `pd.to_numeric(...).fillna(0).astype("int64")`.
2. Cada PK de dimensión se normaliza a `int64` mediante la función helper `_norm_pk()` aplicada sobre cada `_safe_read()`.

**Regla:** Siempre castear FK y PK a `int64` antes de hacer merge; nunca asumir que Parquet preserva el dtype exacto.

---

### B-02 · `dict.values` en Jinja2 resuelve el método Python, no la clave

**Síntoma:** `TypeError: Object of type builtin_function_or_method is not JSON serializable`

**Causa:** En Jinja2, el operador `.` intenta primero `getattr(obj, attr)`. Para un `dict` Python, `causas_data.values` retorna el método `dict.values()` en lugar de la clave `"values"`, porque `getattr(dict, "values")` existe.

**Solución aplicada:** Renombrar la clave conflictiva `"values"` → `"counts"` en:
- `app/puntualidad/analizar_otp.py` → `_causas_retraso()`: `result["counts"]`
- `app/cancelaciones/clasificar_faa.py` → `_causas_faa()`: `"counts": values`
- Templates: `causas.counts`, `causas_data.counts`, `d.causas_counts`, `d.faa_counts`

**Regla:** Nunca usar como clave de dict ninguno de los métodos de Python dict (`keys`, `values`, `items`, `get`, `update`, `pop`, etc.) si ese dict se va a pasar como contexto a Jinja2.

---

### B-03 · Columnas Categorical de Parquet rompen concatenaciones de strings

**Síntoma:** `unsupported operand type(s) for +: 'Categorical' and 'str'`

**Causa:** PyArrow puede leer columnas string de Parquet (con dictionary encoding) como `pd.CategoricalDtype`. Las operaciones de concatenación string (`col + "-" + col2`) fallan sobre Categorical. Afecta a `OriginCode`, `DestCode` y otras columnas de strings leídas desde dimensiones.

**Solución aplicada:**
1. `app/shared/analytics.py`: función `_desnormalizar(df)` que convierte todas las columnas Categorical a su dtype base (`cat.categories.dtype`). Se aplica en `_safe_read()` (todas las dims) y sobre `fact_vuelo` al cargarlo.
2. `app/rutas/ranking_eficiencia.py`: `.astype(str)` explícito sobre `OriginCode` y `DestCode` antes de cualquier concatenación o lookup.
3. `app/puntualidad/analizar_otp.py`: `.astype(str)` al construir la lista de rutas disponibles.

**Regla:** Siempre llamar `_desnormalizar(df)` (o `.astype(str)` puntual) antes de usar columnas string de Parquet en operaciones de concatenación o búsqueda.

---

### B-04 · WeasyPrint requiere librerías de sistema no incluidas en `python:3.13-slim`

**Síntoma:** `OSError: cannot load library 'libgobject-2.0-0'`

**Causa:** WeasyPrint delega el renderizado de texto en Pango/Cairo (librerías nativas de sistema). La imagen `python:3.13-slim` no incluye estas librerías. El `pip install weasyprint` instala solo el código Python pero no las dependencias nativas.

**Solución aplicada:**
1. Agregar al `Dockerfile` antes de pip install:
   ```dockerfile
   RUN apt-get update && apt-get install -y --no-install-recommends \
       libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 \
       libgobject-2.0-0 libglib2.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
       && rm -rf /var/lib/apt/lists/*
   ```
2. `app/reportes/generar_pdf.py`: import lazy de WeasyPrint dentro de `generar_pdf()` (no a nivel de módulo) para evitar que un fallo de import al arrancar deje `_WEASYPRINT_OK = False` permanentemente aunque se instale después.
3. `app/reportes/router.py`: usa `_weasyprint_available()` (función) en vez de `_WEASYPRINT_OK` (constante) para que cada request consulte en tiempo de ejecución.

**Regla:** Las librerías con dependencias de sistema nativas deben importarse de forma lazy (dentro de la función) para permitir degradación graceful y recarga en caliente.

---

### B-05 · Clase CSS `at-input` no existe — usar `form-control-at`

**Síntoma:** Los selects e inputs de los módulos E2 no reciben ningún estilo (aparecen como controles nativos del navegador sin el diseño del sistema).

**Causa:** En los templates de E2 se usó `class="at-input"` pero en `aerotrack-theme.css` la clase correcta es `form-control-at`.

**Solución:** Reemplazar globalmente `class="at-input"` → `class="form-control-at"` en todos los templates de E2.

---

### B-06 · Filtros con botón submit violan el Live Filter Pattern del design.md

**Síntoma:** Los filtros recargan la página completa al hacer clic, en vez de actualizar solo el bloque de resultados.

**Causa:** Se implementaron los filtros con `<button type="submit">` en vez del patrón canónico definido en `.kiro/specs/aerotrack/design.md` (§ "Live Filter Pattern").

**Solución:**
- Eliminar el botón submit de todos los filter forms de módulos analíticos.
- Envolver el contenido dinámico en `<div id="X-results">` hermano del form.
- Adjuntar listener `change` (selects) / `input` + debounce 400ms (texto/fecha) que llama a `fetch` + `box.innerHTML = newBox.innerHTML`.
- Los datos de gráficos Plotly/Chart.js se embedden en `<script id="X-chart-data" type="application/json">` dentro del results div y se re-renderizan tras cada swap.

---

### B-07 · URL firmada de MinIO usa hostname interno de Docker — enlace PDF no abre en el navegador

**Síntoma:** Al generar un PDF desde el módulo Reportes, el enlace "Descargar PDF" aparece pero al hacer clic devuelve error de conexión (ERR_NAME_NOT_RESOLVED o similar).

**Causa:** `presigned_get_object()` genera la URL firmada usando el mismo `MINIO_ENDPOINT` con el que se construyó el cliente Minio. Dentro de Docker, ese endpoint es `minio:9000` (hostname interno de la red Docker `elt-network`). El navegador no puede resolver `minio:9000` porque ese hostname solo existe dentro de la red de contenedores.

```
URL generada (incorrecta para el browser):
http://minio:9000/aerotrack-exports/reportes/aerotrack_reporte_20260604.pdf?X-Amz-Signature=...

URL necesaria (accesible desde el browser):
http://localhost:9000/aerotrack-exports/reportes/aerotrack_reporte_20260604.pdf?X-Amz-Signature=...
```

**Solución aplicada:**
1. `app/config.py`: agregar `MINIO_PUBLIC_ENDPOINT = os.getenv("MINIO_PUBLIC_URL", "localhost:9000")` — endpoint accesible desde el browser (por defecto `localhost:9000`, el puerto API expuesto en docker-compose).
2. `app/reportes/generar_pdf.py` → `subir_pdf_minio()`: usar **dos clientes Minio separados** — uno interno para I/O y otro público solo para presigning:

```python
# Cliente interno → upload y bucket check (resuelve minio:9000 dentro de Docker)
client = Minio(MINIO_ENDPOINT, ...)
client.put_object(...)

# Cliente público → presigning (calcula firma con localhost:9000)
# presigned_get_object() es puramente local: no hace red, solo computa HMAC.
# La firma queda atada al hostname del cliente, así el browser recibe
# una URL con Host=localhost:9000 cuya firma coincide exactamente.
sign_client = Minio(MINIO_PUBLIC_ENDPOINT, ...)
url = sign_client.presigned_get_object(...)
```

**Por qué no funciona reemplazar el string después de firmar:** MinIO incluye el `Host` dentro del canonical request que firma con HMAC-SHA256. Si se firma con `minio:9000` y luego se reemplaza por `localhost:9000`, el browser envía `Host: localhost:9000` al verificar la URL → `SignatureDoesNotMatch`. La firma debe calcularse con el mismo host que recibirá la petición.

**Regla:** Siempre separar el endpoint interno (para I/O server-side: `minio:9000`) del endpoint público (para URLs entregadas al browser: `localhost:9000`). Usar dos clientes Minio distintos: uno para operar, otro para firmar. En producción, `MINIO_PUBLIC_URL` apuntará al dominio/CDN público.

---

### B-08 · Gráficos vacíos por `defer` en librerías de charts (Plotly / Chart.js)

**Síntoma:** Los gráficos de los módulos analíticos (Dashboard, Puntualidad, Rutas, Cancelaciones) aparecen como contenedores vacíos al cargar la página por primera vez. No hay error visible en consola porque el `catch(e){}` silencia la excepción.

**Causa:** Las librerías de charts (Plotly y Chart.js) se cargaban con el atributo `defer` en el bloque `{% block head_extra %}` (dentro del `<head>`). Los scripts `defer` ejecutan **después** de que el parser termina de procesar todo el HTML. Sin embargo, el IIFE en `{% block scripts %}` (al final del `<body>`) es un inline script que ejecuta **durante** el parsing, antes que cualquier script `defer`. Al llamar `Plotly.newPlot()` o `new Chart()`, la librería todavía no existe en `window`, lo que lanza un `ReferenceError` silenciado por el catch.

```
Orden real de ejecución (incorrecto):
1. Parser encuentra <script src="plotly" defer> → descarga en background, no ejecuta
2. Parser llega al IIFE en {% block scripts %} → ejecuta inmediatamente
3. Plotly.newPlot() → ReferenceError (silenciado) → gráfico vacío
4. Parser termina → scripts defer finalmente ejecutan (demasiado tarde)
```

**Solución aplicada:** Mover el tag `<script>` de la librería desde `{% block head_extra %}` al inicio de `{% block scripts %}`, sin `defer`. Al estar en el mismo bloque y antes del IIFE, la librería carga sincrónicamente en orden correcto al final del body.

```html
{# ❌ Antes — defer en head_extra, librería disponible después del IIFE #}
{% block head_extra %}
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js" defer></script>
...
{% endblock %}

{# ✅ Ahora — sincrónico en scripts, disponible antes del IIFE #}
{% block scripts %}
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<script>
(function () {
  function renderCharts() { ... Plotly.newPlot(...) ... }
  renderCharts();
})();
</script>
{% endblock %}
```

**Archivos corregidos:** `dashboard/index.html`, `rutas/ranking.html`, `puntualidad/index.html`, `puntualidad/comparar.html`, `cancelaciones/causas.html`.

**Excepción — `rutas/detalle.html`:** Este template usa `DOMContentLoaded` para envolver el código de charts. Según la spec del W3C, el evento `DOMContentLoaded` no se dispara hasta que todos los scripts `defer` hayan terminado de ejecutar, por lo que `defer` + `DOMContentLoaded` es una combinación válida. No requirió cambio.

**Regla:** Nunca cargar una librería de charts con `defer` en `<head>` si el código que la usa vive en un inline script en `{% block scripts %}`. Elegir una de dos alternativas:
- Mover la librería (sin `defer`) al inicio de `{% block scripts %}`.
- Envolver todo el código de uso en `document.addEventListener('DOMContentLoaded', ...)` (válido porque DOMContentLoaded espera a defer).
