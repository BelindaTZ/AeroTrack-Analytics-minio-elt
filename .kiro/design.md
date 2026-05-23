# AeroTrack Analytics — Design
## Spec-Driven Development | Fase 2: Diseño del Sistema

---

## Arquitectura General

```
[Navegador] → [FastAPI + Jinja2] → [MinIO SDK] → [Parquet en MinIO]
```

El sistema NO usa base de datos relacional.
Cada operación CRUD lee o escribe directamente sobre los archivos Parquet en MinIO.

---

## Estructura de Archivos

```
C:\proyectos\minio-elt\
└── webapp\
    ├── main.py                  ← Punto de entrada FastAPI
    ├── config.py                ← Configuración MinIO y constantes
    ├── minio_client.py          ← Conexión y operaciones con MinIO
    ├── router_tablas.py         ← Rutas CRUD genéricas para todas las tablas
    ├── requirements_web.txt     ← Dependencias Python
    └── templates\
        ├── base.html            ← Layout principal (sidebar + header)
        ├── dashboard.html       ← Página de inicio con métricas
        ├── tabla_lista.html     ← Listado con paginación y búsqueda
        ├── tabla_detalle.html   ← Vista de un registro
        ├── tabla_form.html      ← Formulario crear/editar
        └── error.html           ← Página de error
```

---

## Endpoints de la API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/` | Dashboard con métricas |
| GET | `/{tabla}` | Listar registros con paginación |
| GET | `/{tabla}/nuevo` | Formulario de creación |
| POST | `/{tabla}/nuevo` | Guardar nuevo registro |
| GET | `/{tabla}/{id}/ver` | Ver detalle de registro |
| GET | `/{tabla}/{id}/editar` | Formulario de edición |
| POST | `/{tabla}/{id}/editar` | Guardar cambios |
| POST | `/{tabla}/{id}/eliminar` | Eliminar registro |

---

## Flujo de Datos CRUD

### Leer (List / Detail)
```
Request → FastAPI → MinIO.get(tabla.parquet) → 
pandas.read_parquet() → Jinja2 template → HTML Response
```

### Crear
```
Form POST → FastAPI → MinIO.get(tabla.parquet) → 
df.append(nuevo_registro) → df.to_parquet() → 
MinIO.put(tabla.parquet) → Redirect lista
```

### Editar
```
Form POST → FastAPI → MinIO.get(tabla.parquet) → 
df.loc[id] = valores_nuevos → df.to_parquet() → 
MinIO.put(tabla.parquet) → Redirect lista
```

### Eliminar
```
POST → FastAPI → MinIO.get(tabla.parquet) → 
df.drop(id) → df.to_parquet() → 
MinIO.put(tabla.parquet) → Redirect lista
```

---

## Configuración MinIO

```python
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS   = "admin"
MINIO_SECRET   = "admin1234"
MINIO_BUCKET   = "aerotrack-dims"
SECURE         = False
```

---

## Tablas disponibles y sus PKs

| Tabla | Clave primaria |
|---|---|
| fact_vuelo | pk_vuelo |
| dim_tiempo | pk_tiempo |
| dim_aerolinea | pk_aerolinea |
| dim_aeropuerto | pk_aeropuerto |
| dim_avion | pk_avion |
| dim_retraso_causa | pk_retraso_causa |
| dim_cancelacion | pk_cancelacion |
| dim_distancia | pk_distancia |
| dim_desvio | pk_desvio |
| dim_horario | pk_horario |
| dim_clasificacion_retraso | pk_clasificacion |
| dim_ruta | pk_ruta |

---

## Diseño Visual

- **Framework CSS:** Bootstrap 5
- **Layout:** Sidebar fijo izquierda + contenido principal derecha
- **Colores:**
  - Primario: `#1B3A6B` (azul marino AeroTrack)
  - Acento: `#E05A4E` (coral para botones de acción)
  - Fondo: `#F4F6F9` (gris claro)
  - Sidebar: `#1B3A6B` con texto blanco
- **Tipografía:** Inter o system-ui
- **Componentes:** Cards para métricas, tablas con hover, badges de estado

---

## Dependencias Python

```
fastapi
uvicorn
jinja2
python-multipart
pandas
pyarrow
minio
```
