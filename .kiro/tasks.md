# AeroTrack Analytics — Tasks
## Spec-Driven Development | Fase 3: Plan de Implementación

---

## TASK-01 — Estructura del proyecto y dependencias

**Prioridad:** Alta | **Referencia:** design.md → Estructura de Archivos

- [ ] Crear carpeta `webapp/` en la raíz del proyecto
- [ ] Crear `webapp/requirements_web.txt` con las dependencias:
  `fastapi`, `uvicorn`, `jinja2`, `python-multipart`, `pandas`, `pyarrow`, `minio`
- [ ] Crear carpeta `webapp/templates/`

---

## TASK-02 — Configuración y cliente MinIO

**Prioridad:** Alta | **Referencia:** design.md → Configuración MinIO

- [ ] Crear `webapp/config.py` con:
  - Constantes MinIO (`MINIO_ENDPOINT`, `MINIO_ACCESS`, `MINIO_SECRET`, `MINIO_BUCKET`, `SECURE=False`)
  - Diccionario `TABLAS` con las 12 tablas y sus PKs
  - Lista de tablas disponibles para la navegación del sidebar
- [ ] Crear `webapp/minio_client.py` con funciones:
  - `get_client()` → retorna instancia MinIO
  - `read_parquet(tabla)` → descarga y retorna DataFrame
  - `write_parquet(tabla, df)` → sube DataFrame como Parquet a MinIO
  - Manejo de errores cuando el archivo no existe en el bucket

---

## TASK-03 — Templates HTML base

**Prioridad:** Alta | **Referencia:** design.md → Diseño Visual

- [ ] Crear `webapp/templates/base.html`:
  - Layout con Bootstrap 5 (CDN)
  - Sidebar fijo izquierdo con las 12 tablas listadas, color `#1B3A6B`
  - Header con nombre "AeroTrack Analytics" y logo/ícono de avión
  - Área de contenido principal con fondo `#F4F6F9`
  - Bloque para mensajes flash (éxito/error)
  - Tipografía Inter (Google Fonts)
- [ ] Crear `webapp/templates/error.html`:
  - Muestra mensaje de error descriptivo
  - Botón para regresar al listado o dashboard

---

## TASK-04 — Template Dashboard

**Prioridad:** Alta | **Referencia:** requirements.md → HU-01

- [ ] Crear `webapp/templates/dashboard.html`:
  - 4 tarjetas de métricas: total vuelos, promedio de retraso, total aerolíneas, total rutas
  - Colores de tarjeta acorde a la paleta (`#1B3A6B`, `#E05A4E`)
  - Tabla de últimos registros de `fact_vuelo` (top 10)
  - Badges o indicadores visuales de estado del sistema (tablas cargadas)

---

## TASK-05 — Template Listado con paginación y búsqueda

**Prioridad:** Alta | **Referencia:** requirements.md → HU-02, HU-07

- [ ] Crear `webapp/templates/tabla_lista.html`:
  - Tabla HTML responsiva con todos los campos de la tabla activa
  - Campo de búsqueda en tiempo real (filtro client-side con JavaScript básico)
  - Paginación (50 registros por página)
  - Columna de acciones: botones Ver, Editar, Eliminar por fila
  - Botón "Nuevo registro" en la cabecera
  - Mensaje "No se encontraron registros" cuando aplica

---

## TASK-06 — Template Detalle y Formulario

**Prioridad:** Alta | **Referencia:** requirements.md → HU-03, HU-04, HU-05

- [ ] Crear `webapp/templates/tabla_detalle.html`:
  - Muestra todos los campos del registro en formato clave-valor (lista descriptiva)
  - Botones: Editar y Regresar al listado
- [ ] Crear `webapp/templates/tabla_form.html`:
  - Formulario dinámico generado a partir de los campos del DataFrame
  - Diferencia modo "Crear" vs "Editar" (título y pre-llenado de campos)
  - Validación HTML5 en campos requeridos
  - Botones: Guardar y Cancelar

---

## TASK-07 — Router CRUD genérico

**Prioridad:** Alta | **Referencia:** design.md → Endpoints de la API, Flujo de Datos CRUD

- [ ] Crear `webapp/router_tablas.py` con los 8 endpoints para cada tabla:
  - `GET /{tabla}` → leer Parquet, paginar, pasar a template lista
  - `GET /{tabla}/nuevo` → mostrar formulario vacío
  - `POST /{tabla}/nuevo` → agregar fila al DataFrame, subir Parquet, redirigir
  - `GET /{tabla}/{id}/ver` → buscar fila por PK, mostrar detalle
  - `GET /{tabla}/{id}/editar` → buscar fila por PK, mostrar formulario pre-llenado
  - `POST /{tabla}/{id}/editar` → actualizar fila, subir Parquet, redirigir
  - `POST /{tabla}/{id}/eliminar` → eliminar fila, subir Parquet, redirigir
- [ ] Validar que `{tabla}` exista en el diccionario `TABLAS`; si no, devolver error 404
- [ ] Manejar excepciones de MinIO con mensajes claros al usuario

---

## TASK-08 — Punto de entrada principal

**Prioridad:** Alta | **Referencia:** design.md → Endpoints de la API

- [ ] Crear `webapp/main.py`:
  - Instanciar la app FastAPI con título "AeroTrack Analytics"
  - Montar `Jinja2Templates` apuntando a `templates/`
  - Registrar `router_tablas`
  - `GET /` → calcular métricas del dashboard leyendo `fact_vuelo`, `dim_aerolinea` y `dim_ruta`, renderizar `dashboard.html`
  - Manejo global de errores 404 y 500

---

## TASK-09 — Verificación y pruebas manuales

**Prioridad:** Media | **Referencia:** requirements.md → Todos los HU

- [ ] Instalar dependencias: `pip install -r webapp/requirements_web.txt`
- [ ] Iniciar el servidor: `uvicorn webapp.main:app --reload --port 8000`
- [ ] Verificar dashboard carga métricas desde MinIO (HU-01)
- [ ] Verificar listado con paginación y búsqueda para al menos 3 tablas (HU-02, HU-07)
- [ ] Verificar flujo completo Crear → Ver → Editar → Eliminar en `dim_aerolinea` (HU-03 a HU-06)
- [ ] Verificar mensaje de error cuando una tabla no existe en el bucket (HU-02)

---

## Orden de ejecución recomendado

```
TASK-01 → TASK-02 → TASK-03 → TASK-04 → TASK-05
       → TASK-06 → TASK-07 → TASK-08 → TASK-09
```
