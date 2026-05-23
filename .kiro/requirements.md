# AeroTrack Analytics — Requirements
## Spec-Driven Development | Fase 1: Requisitos

---

## Descripción del Sistema
Web App para gestión y visualización del modelo de datos de AeroTrack Analytics.
Permite realizar operaciones CRUD sobre las tablas de hecho y dimensiones
almacenadas como archivos Parquet en MinIO.

---

## Historias de Usuario

### HU-01 — Dashboard principal
**Como** analista de AeroTrack Analytics,
**quiero** ver un panel principal con métricas clave del sistema,
**para** tener una visión general rápida del estado de los datos.

**Criterios de aceptación (EARS):**
- WHEN el usuario accede a `/`, THEN el sistema muestra total de vuelos, promedio de retraso, total de aerolíneas y total de rutas.
- WHEN los datos están cargados, THEN las métricas se muestran en tarjetas visuales en menos de 3 segundos.

---

### HU-02 — Listar registros de cualquier tabla
**Como** analista,
**quiero** ver los registros de cada tabla (hecho y dimensiones) en una vista paginada,
**para** revisar y auditar los datos almacenados.

**Criterios de aceptación:**
- WHEN el usuario navega a `/{tabla}`, THEN el sistema muestra los primeros 50 registros en una tabla HTML.
- WHEN hay más de 50 registros, THEN el sistema muestra paginación.
- WHERE la tabla no existe en MinIO, THEN el sistema muestra un mensaje de error claro.

---

### HU-03 — Ver detalle de un registro
**Como** analista,
**quiero** ver todos los campos de un registro específico,
**para** analizar su contenido completo.

**Criterios de aceptación:**
- WHEN el usuario hace clic en "Ver" en un registro, THEN el sistema muestra todos sus campos en una vista de detalle.
- WHEN el registro no existe, THEN el sistema redirige al listado con mensaje de error.

---

### HU-04 — Crear nuevo registro
**Como** operador de datos,
**quiero** agregar nuevos registros a cualquier tabla,
**para** mantener los datos actualizados.

**Criterios de aceptación:**
- WHEN el usuario completa el formulario y hace clic en "Guardar", THEN el sistema agrega el registro al Parquet y redirige al listado.
- WHEN un campo requerido está vacío, THEN el sistema muestra un mensaje de validación.
- WHEN el registro se guarda exitosamente, THEN el sistema muestra una notificación de éxito.

---

### HU-05 — Editar un registro existente
**Como** operador de datos,
**quiero** modificar los valores de un registro,
**para** corregir errores o actualizar información.

**Criterios de aceptación:**
- WHEN el usuario hace clic en "Editar", THEN el sistema muestra un formulario pre-llenado con los valores actuales.
- WHEN el usuario guarda los cambios, THEN el sistema actualiza el Parquet y muestra confirmación.

---

### HU-06 — Eliminar un registro
**Como** operador de datos,
**quiero** eliminar registros incorrectos o duplicados,
**para** mantener la calidad de los datos.

**Criterios de aceptación:**
- WHEN el usuario hace clic en "Eliminar", THEN el sistema muestra un diálogo de confirmación.
- WHEN el usuario confirma, THEN el sistema elimina el registro del Parquet.
- WHEN el usuario cancela, THEN el sistema no realiza ninguna acción.

---

### HU-07 — Buscar registros
**Como** analista,
**quiero** filtrar registros por un valor en cualquier columna,
**para** encontrar información específica rápidamente.

**Criterios de aceptación:**
- WHEN el usuario escribe en el campo de búsqueda, THEN el sistema filtra los registros que coincidan.
- WHEN no hay resultados, THEN el sistema muestra "No se encontraron registros".

---

## Tablas del Sistema

| Tabla | Tipo | Descripción |
|---|---|---|
| fact_vuelo | Hecho | Registro de cada vuelo realizado |
| dim_tiempo | Dimensión | Información temporal del vuelo |
| dim_aerolinea | Dimensión | Datos de la aerolínea operadora |
| dim_aeropuerto | Dimensión | Aeropuertos (origen y destino) |
| dim_avion | Dimensión | Avión físico que realizó el vuelo |
| dim_retraso_causa | Dimensión | Causas de retraso en minutos |
| dim_cancelacion | Dimensión | Vuelos cancelados o desviados |
| dim_distancia | Dimensión | Clasificación por distancia |
| dim_desvio | Dimensión | Detalles de vuelos desviados |
| dim_horario | Dimensión | Horarios programados vs reales |
| dim_clasificacion_retraso | Dimensión | Flags e indicadores de retraso |
| dim_ruta | Dimensión | Par origen-destino como entidad |

---

## Restricciones Técnicas
- Backend: Python 3.13 + FastAPI
- Templates: Jinja2 + Bootstrap 5
- Almacenamiento: MinIO (localhost:9000)
- Formato de datos: Apache Parquet (pyarrow)
- Sin base de datos relacional — todo se lee/escribe en Parquet
- Los Parquet están en el bucket `aerotrack-dims`
