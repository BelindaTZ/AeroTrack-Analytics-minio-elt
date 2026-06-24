# Plan de Implementación — Modelo Dimensional Operativo

**Módulo:** Modelo Dimensional  
**Paquete:** `app/modelo_dimensional/`  
**Prefix:** `/modelo`  
**CUs cubiertos:** CU-O09, CU-O10, CU-O11  
**Fuente:** código leído el 2026-06-22

---

## Archivos del módulo

| Archivo | Propósito |
|---|---|
| `app/modelo_dimensional/router.py` | Endpoints FastAPI (CRUD + validación) |
| `app/modelo_dimensional/data/service.py` | Lógica de negocio: leer/escribir Parquet, validar integridad |
| `app/shared/templates.py` | `TABLAS` (12 tablas con PK e iconos), `PAGE_SIZE = 50` |
| `app/shared/clients/minio_client.py` | `read_parquet()`, `write_parquet()`, `stat_parquet()` |

---

## Endpoints implementados (prefix `/modelo`)

**Nota arquitectural:** Las rutas estáticas (`/validar`, `/{tabla}/nuevo`) se definen antes que las dinámicas (`/{tabla}`, `/{tabla}/{pk_val}`) para evitar que FastAPI las confunda con parámetros de path (documentado en `router.py:3-4`).

| Método | Path | Permiso | Descripción |
|---|---|---|---|
| GET | `/modelo` | `modelo_dimensional:ver` | Lista las 12 tablas con métricas (count, size_mb, modified) desde MinIO |
| GET | `/modelo/validar` | `modelo_dimensional:ejecutar` | Formulario de validación de integridad |
| POST | `/modelo/validar` | `modelo_dimensional:ejecutar` | Ejecuta `validar_integridad()`. Registra auditoría con `{ok, errores_count}`. |
| GET | `/modelo/validar/export` | `modelo_dimensional:exportar` | CSV streaming de errores de integridad |
| GET | `/modelo/{tabla}/nuevo` | `modelo_dimensional:crear` | Formulario dinámico generado desde esquema del Parquet |
| POST | `/modelo/{tabla}/nuevo` | `modelo_dimensional:crear` | Crea registro con PK auto-incremental. Registra auditoría. |
| GET | `/modelo/{tabla}/{pk_val}/ver` | `modelo_dimensional:ver` | Detalle de un registro (solo lectura) |
| GET | `/modelo/{tabla}/{pk_val}/editar` | `modelo_dimensional:editar` | Formulario precargado con valores actuales |
| POST | `/modelo/{tabla}/{pk_val}/editar` | `modelo_dimensional:editar` | Actualiza registro. Registra auditoría. |
| POST | `/modelo/{tabla}/{pk_val}/eliminar` | `modelo_dimensional:eliminar` | Elimina registro. Bloquea pk=0 con 403. Registra auditoría. |
| GET | `/modelo/{tabla}` | `modelo_dimensional:ver` | Lista de registros paginada con búsqueda textual |

---

## Las 12 tablas del modelo (definidas en `app/shared/templates.py:29`)

| Tabla | PK | Label | Opcional (pk=0 sentinel) |
|---|---|---|---|
| `fact_vuelo` | `pk_vuelo` | Vuelos | No |
| `dim_tiempo` | `pk_tiempo` | Tiempo | No |
| `dim_aerolinea` | `pk_aerolinea` | Aerolíneas | No |
| `dim_aeropuerto` | `pk_aeropuerto` | Aeropuertos | No |
| `dim_avion` | `pk_avion` | Aviones | No |
| `dim_retraso_causa` | `pk_retraso_causa` | Causas Retraso | **Sí** |
| `dim_cancelacion` | `pk_cancelacion` | Cancelaciones | **Sí** |
| `dim_distancia` | `pk_distancia` | Distancia | No |
| `dim_desvio` | `pk_desvio` | Desvíos | **Sí** |
| `dim_horario` | `pk_horario` | Horarios | No |
| `dim_clasificacion_retraso` | `pk_clasificacion` | Clasif. Retraso | No |
| `dim_ruta` | `pk_ruta` | Rutas | No |

**Dimensiones opcionales** (permiten NULL en FK de fact_vuelo y requieren pk=0):  
`DIMS_OPCIONALES = {"dim_cancelacion", "dim_retraso_causa", "dim_desvio"}` — `service.py:29`

---

## Implementación de read_parquet() / write_parquet() / stat_parquet()

**Archivo:** `app/shared/clients/minio_client.py`  
**Cliente:** `minio.Minio` con `urllib3.PoolManager(timeout=Timeout(connect=5, read=60))`

```python
def read_parquet(bucket: str, tabla: str) -> pd.DataFrame:
    # client.get_object(bucket, f"{tabla}.parquet")
    # response.read() → io.BytesIO → pd.read_parquet(engine implícito)
    # Si S3Error con code NoSuchKey/NoSuchBucket → FileNotFoundError
    # Si otro error → RuntimeError

def write_parquet(bucket: str, tabla: str, df: pd.DataFrame) -> None:
    # df.to_parquet(buf, index=False, engine="pyarrow") → io.BytesIO
    # client.put_object(bucket, f"{tabla}.parquet", buf, length=...)

def stat_parquet(bucket: str, tabla: str) -> Optional[dict]:
    # client.stat_object(bucket, f"{tabla}.parquet")
    # Retorna {"size_mb": float, "modified": datetime} o None si S3Error
```

**Bucket:** `aerotrack-dims` (`MINIO_BUCKET_DIMS` de `app/config.py:14`)

---

## Implementación de validar_integridad()

**Archivo:** `app/modelo_dimensional/data/service.py:143`

### Las 12 FK verificadas (definidas en `FACT_FKS`, service.py:13)

| FK en fact_vuelo | Dimensión esperada |
|---|---|
| `fk_tiempo` | `dim_tiempo` |
| `fk_aerolinea` | `dim_aerolinea` |
| `fk_aeropuerto_origen` | `dim_aeropuerto` |
| `fk_aeropuerto_destino` | `dim_aeropuerto` |
| `fk_avion` | `dim_avion` |
| `fk_ruta` | `dim_ruta` |
| `fk_distancia` | `dim_distancia` |
| `fk_horario` | `dim_horario` |
| `fk_cancelacion` | `dim_cancelacion` |
| `fk_clasificacion` | `dim_clasificacion_retraso` |
| `fk_retraso_causa` | `dim_retraso_causa` |
| `fk_desvio` | `dim_desvio` |

**`dim_aeropuerto` aparece dos veces** (origen y destino) — ambas FKs verificadas contra la misma tabla.

### Tipos de error detectados

| Tipo | Condición |
|---|---|
| `NULL_FK` | `fact[fk_col].isna().sum() > 0` AND dim NO está en `DIMS_OPCIONALES` |
| `FK_HUERFANA` | `fk_vals[~fk_vals.isin(valid_pks)].empty == False` |
| `TABLA_FALTANTE` | `FileNotFoundError` al cargar la dimensión desde MinIO |
| `FALTA_PK0` | `(dim[dim_pk].astype(str) == "0").any() == False` para dims en `DIMS_OPCIONALES` |

### Retorno

```python
{"ok": bool, "errores": list[dict], "tablas_verificadas": int}
# tablas_verificadas = len(FACT_FKS) = 12
# cada error: {"tabla", "columna"?, "tipo", "descripcion"}
```

---

## Implementación del CRUD sobre Parquet

### PK auto-incremental (service.py:92)

```python
nuevo_pk = int(df[pk].max()) + 1 if len(df) and df[pk].notna().any() else 1
```

No usa secuencias ni base de datos externa. Si el DataFrame está vacío, asigna 1.

### Función _cast() (service.py:130)

```python
def _cast(dtype, val: str):
    if val in ("", None): return None
    if is_integer_dtype(dtype): return int(float(val))
    if is_float_dtype(dtype): return float(val)
    return val   # string para el resto
```

Convierte valores de formulario (string) al dtype nativo de la columna Parquet.

### Protección pk=0 (doble capa)

1. `router.py:174`: `if pk_val in ("0", "0.0"): return _tmpl_error(..., 403)`
2. `service.py:121`: `if pk_val in ("0", "0.0"): raise ValueError(...)`

### Búsqueda textual (service.py:67)

```python
mask = df.apply(lambda col: col.astype(str).str.contains(q, case=False, na=False)).any(axis=1)
```

Busca `q` en todas las columnas del DataFrame, case-insensitive.

---

## Paginación

**PAGE_SIZE = 50** definido en `app/shared/templates.py:44`  
Función `paginar(df, page, q)` en `service.py:65`:  
- Filtra con `q` si existe
- Calcula `total_pages = max(1, ceil(total / PAGE_SIZE))`
- Retorna `{"rows", "total", "total_pages", "page", "page_size", "columnas"}`

---

## Acciones registradas en auditoría

| Acción | Trigger | recurso_tipo | recurso_id |
|---|---|---|---|
| `crear` | POST /{tabla}/nuevo | `tabla` | nuevo PK |
| `editar` | POST /{tabla}/{pk_val}/editar | `tabla` | pk_val |
| `eliminar` | POST /{tabla}/{pk_val}/eliminar | `tabla` | pk_val |
| `validar` | POST /validar | — | — (detalle: `{ok, errores_count}`) |

**Nota:** `GET /modelo/validar/export` requiere permiso `modelo_dimensional:exportar` pero NO registra auditoría. El spec dice que la validación se registra (RF-MOD-011); la exportación no está especificada para auditoría.

---

## Principios de la constitución aplicados

| Principio | Aplicación en este módulo |
|---|---|
| I (separación de capas) | Lee exclusivamente de `aerotrack-dims`, nunca de PocketBase ni `aerotrack-raw` |
| II (modelo Kimball) | 12 tablas exactas en `TABLAS`, `DIMS_OPCIONALES`, `FACT_FKS` |
| V (auditoría) | `audit.registrar()` en crear, editar, eliminar, validar |
| VIII (paginación) | `PAGE_SIZE = 50` en `paginar()` |
| IX (timeouts) | No aplica (módulo web, no pipeline) |
