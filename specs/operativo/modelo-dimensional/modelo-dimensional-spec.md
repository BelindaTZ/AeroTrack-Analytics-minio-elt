# Especificación Operativa — Modelo Dimensional

**Módulo:** Modelo Dimensional
**Prefijo:** MOD
**Código fuente:** `app/modelo_dimensional/router.py`, `app/modelo_dimensional/data/service.py`
**Casos de uso cubiertos:** CU-O09 (Ver resumen del modelo dimensional), CU-O10 (Explorar y gestionar registros del modelo), CU-O11 (Validar integridad del modelo dimensional)
**Actor:** Administrador

---

## Funcionalidad 1: Ver resumen del modelo dimensional (CU-O09)

Vista general del modelo dimensional con métricas por tabla.

### RF-MOD-001 — Listar tablas con métricas
El sistema debe mostrar las 12 tablas del modelo dimensional. Para cada tabla debe presentar: número de filas, tamaño en MB, fecha de última modificación, nombre e indicador de disponibilidad.

### RF-MOD-002 — Indicar tablas no disponibles
El sistema debe mostrar un indicador visual "Ejecuta el pipeline primero" en lugar de métricas cuando una tabla aún no tiene datos disponibles, sin generar error al usuario.

### RNF-MOD-001 — Lectura directa desde MinIO
El sistema debe obtener las métricas consultando los archivos Parquet directamente desde el repositorio de almacenamiento (bucket `aerotrack-dims`), no desde la base de datos operacional. Cada tabla es un archivo Parquet independiente.

### RNF-MOD-002 — 12 tablas del modelo estrella
El modelo dimensional contiene: `fact_vuelo`, `dim_tiempo`, `dim_aerolinea`, `dim_aeropuerto`, `dim_avion`, `dim_retraso_causa`, `dim_cancelacion`, `dim_distancia`, `dim_desvio`, `dim_horario`, `dim_clasificacion_retraso`, `dim_ruta`.

### RNF-MOD-003 — Auditoría en todas las operaciones del modelo
El sistema debe registrar en el log de auditoría toda creación, edición, eliminación y validación de integridad.

---

## Funcionalidad 2: Explorar y gestionar registros del modelo (CU-O10)

CRUD completo sobre cualquier tabla del modelo dimensional. Las operaciones se realizan sobre archivos Parquet en el repositorio de almacenamiento.

### RF-MOD-003 — Listar registros con paginación
El sistema debe listar los registros de una tabla con paginación de 50 registros por página, mostrando todas las columnas con sus valores. Debe soportar navegación entre páginas con cálculo de total de páginas.

### RF-MOD-004 — Búsqueda textual en todas las columnas
El sistema debe permitir búsqueda textual insensible a mayúsculas en todas las columnas del conjunto de datos. Los resultados se filtran antes de paginar.

### RF-MOD-005 — Ver detalle de registro
El sistema debe mostrar todos los campos de un registro individual en vista de solo lectura, localizándolo por su clave primaria. Debe retornar error 404 si la clave primaria no existe.

### RF-MOD-006 — Crear registro con PK auto-incremental
El sistema debe renderizar un formulario dinámico generado a partir del esquema de la tabla (columnas y tipos). Al crear, debe asignar automáticamente la clave primaria como el valor máximo existente más 1 (o 1 si la tabla está vacía), aplicar conversión de tipos según el tipo de dato de cada columna y registrar la acción en auditoría.

### RF-MOD-007 — Editar registro
El sistema debe mostrar un formulario precargado con los valores actuales del registro. Al guardar, debe actualizar todas las columnas excepto la clave primaria, aplicar conversión de tipos y registrar la acción en auditoría.

### RF-MOD-008 — Eliminar registro (con protección pk=0)
El sistema debe eliminar la fila indicada del conjunto de datos y persistir el resultado. Si la clave primaria es 0, el sistema debe retornar error 403 "El registro pk=0 es inmutable" sin modificar los datos. Debe registrar la acción en auditoría.

### RF-MOD-009 — Conversión automática de tipos en formularios
El sistema debe convertir automáticamente los valores ingresados en formularios al tipo de dato nativo de cada columna: entero para columnas de tipo entero, punto flotante para columnas de tipo flotante, y texto para el resto. Los campos vacíos se asignan como nulos.

### RNF-MOD-004 — PK auto-asignado en creación
El sistema debe calcular la nueva clave primaria como el valor máximo existente en la columna PK más 1. Si el conjunto de datos está vacío o la columna PK no tiene valores, asigna 1.

### RNF-MOD-005 — Rutas estáticas con mayor precedencia que rutas dinámicas
El sistema debe garantizar que las rutas estáticas (como `/validar` y `/nuevo`) tengan precedencia sobre los parámetros dinámicos de nombre de tabla, evitando colisiones de enrutamiento.

---

## Funcionalidad 3: Validar integridad del modelo dimensional (CU-O11)

Validación referencial del modelo dimensional.

### RF-MOD-010 — Validar integridad referencial
El sistema debe verificar las 12 claves foráneas definidas en el modelo contra sus tablas de dimensión correspondientes, retornando un resultado con indicador de validez, lista de errores y número de tablas verificadas. El sistema identifica 4 tipos de error:

| Tipo | Descripción |
|------|-------------|
| `NULL_FK` | Valores nulos en clave foránea obligatoria (dimensión no opcional) |
| `FK_HUERFANA` | Valores de clave foránea sin correspondencia en la dimensión |
| `TABLA_FALTANTE` | Archivo Parquet de la dimensión no disponible en el repositorio |
| `FALTA_PK0` | Dimensión opcional sin fila sentinel pk=0 |

### RF-MOD-011 — Mostrar resultados de validación
El sistema debe mostrar el resultado de la validación con un indicador visual de éxito o error (número de errores encontrados), una tabla de errores con columnas `tabla`, `columna`, `tipo` y `descripción`, y opciones para re-validar o exportar los resultados.

### RF-MOD-012 — Exportar errores a CSV
El sistema debe generar un archivo CSV descargable con los errores de validación, con las columnas `tabla, columna, tipo, descripcion` y una fila por cada error. El archivo se genera en memoria como respuesta de streaming.

### RNF-MOD-006 — 12 FK verificadas contra fact_vuelo
El sistema debe verificar las 12 claves foráneas que vinculan `fact_vuelo` con sus 11 dimensiones (la dimensión `dim_aeropuerto` aparece dos veces: origen y destino). Cada clave foránea se verifica individualmente.

### RNF-MOD-007 — Dimensiones opcionales toleran NULL y requieren pk=0
El sistema debe tratar de forma diferenciada las tres dimensiones opcionales (`dim_cancelacion`, `dim_retraso_causa`, `dim_desvio`): los valores nulos en su clave foránea no generan error `NULL_FK`, pero se debe verificar que exista la fila sentinel `pk=0`. Si falta, se reporta `FALTA_PK0`.

---

## Reglas de negocio

### RN-MOD-001 — pk=0 es sentinel inmutable en 3 dimensiones opcionales
Las dimensiones `dim_cancelacion`, `dim_retraso_causa` y `dim_desvio` tienen una fila especial con `pk=0` que representa "sin dato/aplicar". Esta fila no puede eliminarse ni modificarse para cambiar su clave primaria. La regla se aplica en:
- La operación de eliminación → bloquea si `pk_val` es 0
- La capa de enrutamiento → retorna 403 antes de llamar al servicio
- La validación de integridad → reporta `FALTA_PK0` si no existe

### RN-MOD-002 — Las dimensiones opcionales son las únicas que pueden tener FK nulas
Solo las claves foráneas que apuntan a `dim_cancelacion`, `dim_retraso_causa` o `dim_desvio` pueden tener valores nulos en `fact_vuelo`. Cualquier otra clave foránea con nulo se reporta como `NULL_FK` y se considera error de integridad.

### RN-MOD-003 — CRUD opera directamente sobre Parquet en MinIO
Todas las operaciones de gestión leen y escriben archivos Parquet directamente en el repositorio de almacenamiento (bucket `aerotrack-dims`). No hay base de datos intermedia. Cada operación de escritura reemplaza el archivo completo.

### RN-MOD-004 — Tabla fuera del catálogo responde 404
Si una tabla solicitada no existe en el catálogo de 12 tablas del modelo, el sistema responde con error HTTP 404.

---

## Historias de usuario

- Como Administrador, quiero ver las métricas de las 12 tablas del modelo, para confirmar que el pipeline actualizó todos los datos antes de que los analistas los consulten.
- Como Administrador, quiero explorar y corregir registros del modelo dimensional, para resolver inconsistencias puntuales sin re-ejecutar el pipeline completo.
- Como Administrador, quiero validar la integridad referencial del modelo y exportar los errores a CSV, para garantizar que los reportes se basan en datos consistentes.

---

## Objetivo

Proporcionar una interfaz para explorar, gestionar y validar el modelo dimensional de 12 tablas (fact_vuelo + 11 dimensiones), permitiendo operaciones CRUD sobre registros individuales, verificación de integridad referencial y exportación de resultados de validación.

---

## Escenarios

### Camino feliz
1. El Admin accede al resumen del modelo y visualiza las 12 tablas con métricas: cantidad de filas, tamaño en MB y fecha de última modificación.
2. El Admin navega a una tabla del modelo y explora los registros con paginación y búsqueda textual.
3. El Admin edita un registro; el sistema aplica conversión automática de tipos y persiste el archivo en el repositorio.
4. El Admin ejecuta la validación; el sistema verifica las 12 claves foráneas de `fact_vuelo` contra cada dimensión y clasifica cada error en uno de cuatro tipos.
5. Si hay errores, el Admin exporta a CSV con codificación UTF-8.

### Manejo de errores
- **Tabla no disponible:** Si la tabla solicitada no tiene archivo Parquet en el repositorio, el sistema muestra "No disponible aún" en lugar de un error 500.
- **Tabla inexistente:** Si el nombre de tabla no está en el catálogo de 12 tablas, el sistema retorna 404.
- **Eliminar pk=0:** La solicitud de eliminar el registro con clave primaria 0 retorna 403 con "El registro pk=0 es inmutable".
- **Error de conversión de tipo:** La creación o edición con un valor incompatible con el tipo de columna retorna error descriptivo.
- **Error de validación:** Los cuatro tipos de error detectados son: `NULL_FK`, `FK_HUERFANA`, `TABLA_FALTANTE`, `FALTA_PK0`.

---

## Criterios de aceptación

- **CU-O09:** Dado que el Admin accede al resumen del modelo, entonces el sistema muestra las 12 tablas con métricas leídas desde el repositorio, indicando aquellas cuyo archivo no está disponible.
- **CU-O10:** Dado que el Admin selecciona una tabla del modelo, entonces el sistema permite explorar (paginación, búsqueda textual), crear, editar y eliminar registros con conversión automática de tipos y protección del registro sentinel pk=0.
- **CU-O11:** Dado que el Admin ejecuta la validación, entonces el sistema verifica las 12 claves foráneas de `fact_vuelo`, clasifica cada error en uno de cuatro tipos (`NULL_FK`, `FK_HUERFANA`, `TABLA_FALTANTE`, `FALTA_PK0`) y permite exportar los resultados a CSV.

---

## Dependencias

- **Seguridad:** Autenticación JWT y autorización con permisos `modelo_dimensional:ver`, `modelo_dimensional:editar`, `modelo_dimensional:validar`.
- **Pipeline ELT:** Generación de archivos Parquet del modelo dimensional en el bucket `aerotrack-dims` de MinIO.
- **MinIO:** Bucket `aerotrack-dims` con archivos Parquet para cada una de las 12 tablas del modelo.

---

## Casos de uso relacionados

- CU-O09 (Explorar el modelo dimensional)
- CU-O10 (Gestionar registros de tablas)
- CU-O11 (Validar integridad referencial)

---

## Fuera de alcance

- Modificación del esquema de tablas existentes (columnas, tipos, relaciones).
- Creación o eliminación de tablas del modelo dimensional.
- Validación de integridad entre dimensiones (solo se valida fact_vuelo → dimensión).
- Sincronización bidireccional entre MinIO y bases de datos externas.
- Historial de cambios por registro individual.
