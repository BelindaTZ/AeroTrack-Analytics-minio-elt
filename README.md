# AeroTrack Analytics

Sistema de Business Intelligence sobre datos de vuelos BTS Carrier On-Time Performance (2M registros). Pipeline ELT con Airflow → MinIO (Parquet) + PocketBase. Interfaz web FastAPI + Jinja2 + Bootstrap 5.

---

## Requisitos previos

- Docker Desktop (Windows/Mac/Linux)
- Git

---

## Levantar el sistema

```bash
git clone <repo>
cd minio-elt
cp .env.example .env          # ajustar variables si es necesario
docker compose up -d
```

Servicios disponibles:

| Servicio    | URL                        | Credenciales por defecto |
|-------------|----------------------------|--------------------------|
| FastAPI app | http://localhost:8000      | —                        |
| Airflow     | http://localhost:8080      | admin / admin1234        |
| PocketBase  | http://localhost:8090/_/   | ver `.env`               |
| MinIO       | http://localhost:9001      | admin / admin1234        |

---

## Setup inicial (primera vez)

```bash
# Desde el host (no dentro de Docker)
pip install -r scripts/requirements-setup.txt
python scripts/run_setup_inicial.py
```

Crea colecciones en PocketBase, carga el CSV de vuelos y configura roles/permisos.

---

## Desarrollo — recarga de cambios

| Tipo de archivo | Recarga automática | Comando manual |
|---|---|---|
| `app/**/*.py` | Sí — Watchfiles detecta y recarga uvicorn automáticamente | — |
| `app/**/*.html` (templates) | **No** — Watchfiles ignora `.html` | `docker restart fastapi-app` |
| `static/css/*.css`, `static/js/*.js` | No aplica — servidos estáticos, basta con recargar el navegador | — |

---

## Ejecutar el pipeline ELT

1. Ir a Airflow → DAGs → `aerotrack_elt_pipeline`
2. Activar el DAG (toggle ON)
3. Disparar manualmente o esperar el schedule
4. También se puede disparar desde la web app en `/pipeline`

---

## Dependencias del Dockerfile — notas importantes

El `Dockerfile` instala todas las dependencias de Python con `pip`. Si se reimplementa desde cero, verificar que estén presentes:

### Dependencias core (siempre necesarias)

```
fastapi, uvicorn[standard], jinja2, python-multipart
pandas, pyarrow, minio
requests, httpx
python-jose[cryptography], passlib[bcrypt]
python-dotenv
```

### Dependencias de Entrega 2 (añadidas al build)

```
plotly>=5.18.0      ← gráficos interactivos (dashboard, rutas)
openpyxl>=3.1.0     ← exportación Excel (.xlsx)
```

> **Importante:** Si `plotly` u `openpyxl` no están en el Dockerfile, FastAPI crashea al arrancar con `ModuleNotFoundError` porque los imports son a nivel de módulo en `app/dashboard/kpis.py` y `app/reportes/generar_excel.py`. El contenedor entra en bucle de reinicios.

### WeasyPrint (generación de PDF) — opcional

WeasyPrint requiere librerías nativas del sistema (`libpango`, `libcairo2`, `libgdk-pixbuf2.0`). El build de la imagen slim **falla** si se intenta instalar las dependencias de sistema con `apt-get` sin acceso a red durante el build.

**Estado actual:** WeasyPrint **no está instalado**. El módulo `app/reportes/generar_pdf.py` detecta su ausencia con:

```python
try:
    from weasyprint import HTML as WP_HTML
    _WEASYPRINT_OK = True
except ImportError:
    _WEASYPRINT_OK = False
```

- Si `_WEASYPRINT_OK = False`: el endpoint PDF devuelve HTTP 501 y la UI muestra un aviso.
- El resto del sistema (Excel, dashboard, análisis) funciona con normalidad.

Para activar PDF en una imagen con acceso a red al momento del build:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 libcairo2 \
    libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir weasyprint>=62.0
```

---

## Estructura del proyecto

```
app/
├── seguridad/          # JWT, RBAC, usuarios, roles (E1)
├── pipeline_elt/       # Panel + logs del DAG Airflow (E1)
├── modelo_dimensional/ # CRUD Parquet estrella (E1)
├── dashboard/          # KPIs globales + alertas (E2)
├── puntualidad/        # OTP por aerolínea/ruta (E2)
├── rutas/              # Ranking eficiencia de rutas (E2)
├── cancelaciones/      # Clasificación FAA A/B/C/D (E2)
├── configuracion/      # Panel config + monitoreo servicios (E2)
├── auditoria/          # Log inmutable pb_auditoria (E2)
├── reportes/           # PDF (WeasyPrint) + Excel (openpyxl) (E2)
├── shared/
│   ├── analytics.py    # load_enriched_fact() — joins fact+dims
│   ├── clients/        # minio_client, pb_client
│   ├── deps.py         # require_permission(), render()
│   └── templates/      # base.html, error.html
└── utils/
    └── ia_narrativa.py # Grok 3 mini → Gemini 2.0 Flash fallback

dags/                   # DAG aerotrack_elt_pipeline
scripts/                # Setup inicial one-shot
```

---

## Variables de entorno relevantes (`.env`)

| Variable              | Descripción                            |
|-----------------------|----------------------------------------|
| `MINIO_URL`           | Endpoint MinIO (host)                  |
| `MINIO_URL_DOCKER`    | Endpoint MinIO (dentro de Docker)      |
| `MINIO_ACCESS`        | Access key MinIO                       |
| `MINIO_SECRET`        | Secret key MinIO                       |
| `PB_URL`              | URL PocketBase (host)                  |
| `PB_URL_DOCKER`       | URL PocketBase (dentro de Docker)      |
| `PB_EMAIL`            | Email admin PocketBase                 |
| `PB_PASSWORD`         | Contraseña admin PocketBase            |
| `SECRET_KEY`          | Clave firma JWT                        |
| `AIRFLOW_ADMIN_USER`  | Usuario Airflow                        |
| `AIRFLOW_ADMIN_PASSWORD` | Contraseña Airflow                  |

---

## Notas de UI / Frontend

### Botón de regreso generado por JavaScript

El archivo `static/js/aerotrack-ui.js` contiene `initBackButton()`, que genera automáticamente un botón de regreso leyendo el último enlace del breadcrumb (`.topbar-breadcrumb a`). Este botón se inyecta **dentro del `.page-heading`**, alineado horizontalmente con el `<h1>` del módulo mediante la clase `.page-heading-meta` (flex row con `justify-content: space-between`).

**Consideración:** Si el template ya incluye un `.page-heading-meta` en el HTML (páginas que tienen acciones propias junto al título, como detalle de registro o matriz de permisos), el JS detecta esto y **no inyecta** el botón automático para evitar duplicados.

```html
<!-- Heading con acciones propias — JS no toca este bloque -->
<div class="page-heading">
  <div class="page-heading-meta">
    <h1>Título del módulo</h1>
    <a href="..." class="btn-at-ghost">← Volver</a>
  </div>
</div>

<!-- Heading sin acciones — JS inyecta el botón inline con el h1 -->
<div class="page-heading">
  <h1>Título del módulo</h1>
</div>
```

Los botones **Guardar / Cancelar** de los formularios deben permanecer en el pie del formulario (dentro del `<form>`, no en el heading).

---

### Tablas anchas con scroll horizontal

Las tablas que pueden tener muchas columnas (ej. matriz de permisos) requieren dos cosas para que el scroll horizontal funcione correctamente:

1. **`min-width`** explícito en la tabla para que pueda sobrepasar el ancho del contenedor.
2. El contenedor scroll debe ser **el wrapper externo** (no un `div` interno anidado). Si hay un `div.at-table-scroll` dentro de un wrapper con `border-radius`, se debe sobrescribir el scroll del div interno y delegarlo al wrapper:

```css
/* En el <style> del template, no en el CSS global */
.mi-tabla-wrap {
  overflow-x: auto;
}
.mi-tabla-wrap .at-table-scroll {
  overflow: visible;
  min-width: max-content;
}
.mi-tabla {
  min-width: 830px; /* ajustar según columnas */
}
```

> **Por qué:** `overflow: hidden` en el wrapper externo bloquea visualmente la tabla antes de que `.at-table-scroll` pueda crear su contexto de scroll. El wrapper externo debe ser el punto de scroll para que el `border-radius` y el scroll coexistan.
