# Especificación Operativa — Modelo Dimensional

**Módulo:** Modelo Dimensional
**Prefijo:** MOD
**Código fuente:** `app/modelo_dimensional/router.py`, `app/modelo_dimensional/data/service.py`
**Casos de uso cubiertos:** CU-O09 (Ver resumen del modelo dimensional), CU-O10 (Explorar y gestionar registros del modelo), CU-O11 (Validar integridad del modelo dimensional)
**Actor:** Usuario autenticado

---

## Funcionalidad 1: Ver resumen del modelo dimensional (CU-O09)

Vista general del modelo dimensional desde `app/modelo_dimensional/data/service.py` y `router.py`.

### RF-MOD-001 — Listar tablas con métricas
`GET /modelo` muestra las 12 tablas del modelo dimensional. Para cada tabla consulta MinIO vía `stat_parquet()` para obtener: número de filas, tamaño en MB, y fecha de última modificación. Las tablas se presentan en un bento grid con icono, nombre, recuento, tamaño, y badge de disponibilidad.

### RF-MOD-002 — Indicar tablas no disponibles
Si una tabla no tiene archivo Parquet en MinIO, se muestra con indicador visual "Ejecuta el pipeline primero" en lugar de métricas. Esto ocurre cuando el pipeline ELT aún no ha generado esa tabla.

### RNF-MOD-001 — Lectura directa desde MinIO
Las métricas se obtienen consultando los archivos Parquet directamente desde MinIO (bucket `aerotrack-dims`), no desde PocketBase. Cada tabla es un archivo Parquet independiente.

### RNF-MOD-002 — 12 tablas del modelo estrella
El modelo dimensional contiene: `fact_vuelo`, `dim_tiempo`, `dim_aerolinea`, `dim_aeropuerto`, `dim_avion`, `dim_retraso_causa`, `dim_cancelacion`, `dim_distancia`, `dim_desvio`, `dim_horario`, `dim_clasificacion_retraso`, `dim_ruta`. Definidas en `TABLAS` en `app/shared/templates.py`.

### RNF-MOD-003 — Auditoría en todas las operaciones del modelo
Toda creación, edición, eliminación Y validación de integridad debe registrarse en el log de auditoría inmutable.

---

## Funcionalidad 2: Explorar y gestionar registros del modelo (CU-O10)

CRUD completo sobre cualquier tabla del modelo dimensional desde `app/modelo_dimensional/router.py` y `service.py`. Las operaciones se realizan sobre archivos Parquet en MinIO.

### RF-MOD-003 — Listar registros con paginación
`GET /modelo/{tabla}` lista los registros de una tabla con paginación de 50 registros por página (`PAGE_SIZE = 50`). Muestra todas las columnas del DataFrame con sus valores. Soporta navegación entre páginas con cálculo de total de páginas.

### RF-MOD-004 — Búsqueda textual en todas las columnas
El parámetro `q` en `GET /modelo/{tabla}?q=texto` realiza una búsqueda case-insensitive en **todas** las columnas del DataFrame usando `str.contains(q, case=False, na=False)`. Los resultados se filtran antes de paginar.

### RF-MOD-005 — Ver detalle de registro
`GET /modelo/{tabla}/{pk_val}/ver` carga el DataFrame, localiza la fila por su PK, y muestra todas las columnas en vista de solo lectura tipo ficha (grid de pares clave-valor). Retorna 404 si el PK no existe.

### RF-MOD-006 — Crear registro con PK auto-incremental
`GET /modelo/{tabla}/nuevo` renderiza formulario dinámico generado a partir del esquema del Parquet (columnas y tipos). `POST /modelo/{tabla}/nuevo` asigna PK automático (`max(pk) + 1` o 1 si tabla vacía) y aplica casting de tipos según el dtype de cada columna mediante `_cast()`. Registra auditoría.

### RF-MOD-007 — Editar registro
`GET /modelo/{tabla}/{pk_val}/editar` carga formulario precargado con valores actuales. `POST /modelo/{tabla}/{pk_val}/editar` actualiza todas las columnas excepto PK. Aplica `_cast()` para convertir tipos. Registra auditoría.

### RF-MOD-008 — Eliminar registro (con protección pk=0)
`POST /modelo/{tabla}/{pk_val}/eliminar` elimina la fila del DataFrame y guarda el Parquet. Validación: si `pk_val` es `"0"` o `"0.0"`, retorna error 403 "El registro pk=0 es inmutable" sin modificar datos. Registra auditoría.

### RF-MOD-009 — Casting automático de tipos en formularios
La función `_cast(dtype, val)` en `service.py` convierte valores de string al tipo nativo de la columna: `int` para columnas integer, `float` para float, string para el resto. Si el valor está vacío, asigna `None`.

### RNF-MOD-004 — PK auto-asignado en creación
El nuevo PK se calcula como `max(pk_col) + 1` sobre el DataFrame existente. No usa bases de datos externas ni secuencias. Si el DataFrame está vacío o la columna PK no tiene valores, asigna 1.

### RNF-MOD-005 — Rutas estáticas antes que dinámicas
Para evitar que FastAPI confunda rutas como `/validar` o `/nuevo` con el parámetro `{tabla}`, las rutas estáticas se definen antes que `GET /{tabla}` en el router. Ver comentario en `router.py` línea 3-4.

---

## Funcionalidad 3: Validar integridad del modelo dimensional (CU-O11)

Validación referencial del modelo dimensional desde `app/modelo_dimensional/data/service.py`.

### RF-MOD-010 — Validar integridad referencial
`POST /modelo/validar` ejecuta `validar_integridad()` que verifica las 12 FK definidas en `FACT_FKS` contra sus tablas de dimensión. Retorna objeto con `{ok: bool, errores: list, tablas_verificadas: int}`. Identifica 4 tipos de error:

| Tipo | Descripción |
|------|-------------|
| `NULL_FK` | Valores NULL en FK obligatoria (dimensión no opcional) |
| `FK_HUERFANA` | Valores FK sin correspondencia en dimensión |
| `TABLA_FALTANTE` | Archivo Parquet de dimensión no disponible en MinIO |
| `FALTA_PK0` | Dimensión opcional sin fila sentinel pk=0 |

### RF-MOD-011 — Mostrar resultados de validación
`GET /modelo/validar` renderiza página con botón "Ejecutar validación". Tras ejecutar, muestra badge verde (sin errores) o rojo (N errores encontrados), tabla de errores con columnas `tabla`, `columna`, `tipo` y `descripción`, más botones para re-validar o exportar.

### RF-MOD-012 — Exportar errores a CSV
`GET /modelo/validar/export` ejecuta validación y retorna un archivo CSV descargable con cabeceras `tabla, columna, tipo, descripcion` y una fila por cada error. El contenido se genera en memoria como `StreamingResponse`.

### RNF-MOD-006 — 12 FK verificadas contra fact_vuelo
La validación itera sobre las 12 FK definidas en `FACT_FKS` que vinculan `fact_vuelo` con sus 11 dimensiones (dim_aeropuerto aparece dos veces: origen y destino). Cada FK se verifica individualmente.

### RNF-MOD-007 — Dimensiones opcionales toleran NULL y requieren pk=0
Tres dimensiones son opcionales (`DIMS_OPCIONALES`): `dim_cancelacion`, `dim_retraso_causa`, `dim_desvio`. Para ellas:
- Valores NULL en la FK NO generan error `NULL_FK`.
- Se verifica que exista fila `pk=0` (sentinel). Si falta, se reporta `FALTA_PK0`.

---

## Reglas de negocio

### RN-MOD-001 — pk=0 es sentinel inmutable en 3 dimensiones opcionales
Las dimensiones `dim_cancelacion`, `dim_retraso_causa` y `dim_desvio` tienen una fila especial con `pk=0` que representa "sin dato/aplicar". Esta fila no puede eliminarse ni modificarse para cambiar su PK. La regla se aplica en:
- `eliminar_registro()` → bloquea eliminación si `pk_val in ("0", "0.0")`
- `router.py` → bloquea con 403 antes de llamar al service
- `validar_integridad()` → reporta `FALTA_PK0` si no existe

### RN-MOD-002 — Las dimensiones opcionales son las únicas que pueden tener FK nulas
Solo las FK que apuntan a `dim_cancelacion`, `dim_retraso_causa` o `dim_desvio` pueden tener valores NULL en `fact_vuelo`. Cualquier otra FK con NULL se reporta como `NULL_FK` y se considera error de integridad.

### RN-MOD-003 — CRUD opera directamente sobre Parquet en MinIO
Todas las operaciones CRUD leen y escriben archivos Parquet directamente en MinIO (bucket `aerotrack-dims`). No hay base de datos intermedia. Cada operación de escritura reemplaza el archivo completo mediante `write_parquet()`.

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
1. El Admin accede a `GET /modelo` y visualiza las 12 tablas del modelo con métricas: cantidad de filas, tamaño en MB y fecha de última modificación.
2. El Admin navega a `GET /modelo/{tabla}` y explora los registros con paginación, búsqueda textual y filtros por columna.
3. El Admin edita un registro mediante `POST /modelo/{tabla}/{pk_val}/editar`; el sistema aplica casting automático de tipos según el esquema DuckDB y persiste el archivo Parquet en MinIO.
4. El Admin ejecuta la validación mediante `POST /modelo/validar`; el sistema verifica las 12 claves foráneas de `fact_vuelo` contra cada dimensión y clasifica cada error en uno de cuatro tipos.
5. Si hay errores, el Admin exporta a CSV mediante `GET /modelo/validar/export` con encoding UTF-8 BOM para compatibilidad Excel.

### Manejo de errores
- **Tabla no disponible:** Si `GET /modelo/{tabla}` corresponde a una tabla sin archivo Parquet en MinIO, el sistema muestra "No disponible aún" en lugar de un error 500.
- **Tabla inexistente:** Si el nombre de tabla no está en el catálogo de 12 tablas, `GET /modelo/{tabla_inexistente}` retorna 404.
- **Eliminar pk=0:** `POST /modelo/{tabla}/0/eliminar` retorna 403 con "El registro pk=0 es inmutable".
- **Error de casting:** `POST /modelo/{tabla}/nuevo` con un valor de tipo incorrecto para la columna retorna error de conversión (ej: "El valor 'abc' no es un entero válido para la columna 'anio'").
- **Error de validación:** Los cuatro tipos de error detectados son: `NULL_FK` (FK nula en fact_vuelo), `FK_HUERFANA` (FK sin correspondencia en dimensión), `TABLA_FALTANTE` (Parquet de dimensión no existe), `FALTA_PK0` (dimensión no contiene el registro sentinel pk=0).

---

## Criterios de aceptación

- **CU-O09:** Dado que el Admin accede al resumen del modelo (`GET /modelo`), entonces el sistema muestra las 12 tablas con métricas leídas desde MinIO, indicando aquellas cuyo archivo Parquet no está disponible.
- **CU-O10:** Dado que el Admin selecciona una tabla del modelo (`GET /modelo/{tabla}`), entonces el sistema permite explorar (paginación, búsqueda textual), crear, editar y eliminar registros con casting automático de tipos y protección del registro sentinel pk=0.
- **CU-O11:** Dado que el Admin ejecuta la validación (`POST /modelo/validar`), entonces el sistema verifica las 12 FK de `fact_vuelo`, clasifica cada error en uno de cuatro tipos (`NULL_FK`, `FK_HUERFANA`, `TABLA_FALTANTE`, `FALTA_PK0`) y permite exportar los resultados a CSV.

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
