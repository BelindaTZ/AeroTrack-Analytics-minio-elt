# Checklist de Verificación — Modelo Dimensional Operativo

**Módulo:** Modelo Dimensional  
**Spec de referencia:** `specs/operativo/modelo-dimensional/modelo-dimensional-spec.md`  
**Código verificado:** `app/modelo_dimensional/router.py`, `app/modelo_dimensional/data/service.py`, `app/shared/templates.py`, `app/shared/clients/minio_client.py`  
**Fecha de auditoría:** 2026-06-22

---

## Casos de uso (criterios de aceptación del spec)

### CU-O09 — Ver resumen del modelo dimensional

- [x] **Dado** que el Admin accede al resumen del modelo (`GET /modelo`), **entonces** el sistema muestra las 12 tablas con métricas leídas desde MinIO, indicando aquellas cuyo archivo Parquet no está disponible.
  - `router.py:29-33`: `svc.listar_tablas_con_metricas()` → renderiza `lista_tablas.html`
  - `service.py:40-62`: itera `TABLAS`, llama `stat_parquet()` para cada tabla. Si `stat=None`, `disponible=False`.

### CU-O10 — Explorar y gestionar registros del modelo

- [x] **Dado** que el Admin selecciona una tabla del modelo (`GET /modelo/{tabla}`), **entonces** el sistema permite explorar (paginación, búsqueda textual), crear, editar y eliminar registros con casting automático de tipos y protección del registro sentinel pk=0.
  - Explorar: `router.py:188-203` — `svc.paginar(df, page, q)` con `PAGE_SIZE=50`
  - Crear: `router.py:93-105` — `svc.crear_registro()` con `nuevo_pk = max(pk)+1`
  - Editar: `router.py:154-166` — `svc.editar_registro()`
  - Eliminar: `router.py:169-181` — `svc.eliminar_registro()` con bloqueo pk=0

### CU-O11 — Validar integridad del modelo dimensional

- [x] **Dado** que el Admin ejecuta la validación (`POST /modelo/validar`), **entonces** el sistema verifica las 12 FK de `fact_vuelo`, clasifica cada error en uno de cuatro tipos (`NULL_FK`, `FK_HUERFANA`, `TABLA_FALTANTE`, `FALTA_PK0`) y permite exportar los resultados a CSV.
  - `router.py:45-51`: `svc.validar_integridad()` → renderiza resultado
  - `service.py:143-204`: implementación completa con los 4 tipos de error
  - `router.py:54-68`: `GET /modelo/validar/export` → `StreamingResponse` CSV

---

## Requerimientos funcionales (RF-MOD-0XX)

- [x] **RF-MOD-001** — `GET /modelo` muestra las 12 tablas con count, size_mb, modified y badge de disponibilidad.
  - `service.py:40-62`: itera `TABLAS`, `stat_parquet()`, `_load()` para count, `disponible` = `stat is not None`

- [x] **RF-MOD-002** — Tablas sin Parquet muestran indicador "no disponible".
  - `service.py:52-60`: si `stat=None`, retorna `{"disponible": False, "count": None, "size_mb": None}`

- [x] **RF-MOD-003** — `GET /modelo/{tabla}` lista registros con paginación de 50 por página.
  - `router.py:188-203`, `service.py:65-77`: `PAGE_SIZE=50` en `paginar()`

- [x] **RF-MOD-004** — Parámetro `q` realiza búsqueda case-insensitive en todas las columnas.
  - `service.py:67-69`: `df.apply(lambda col: col.astype(str).str.contains(q, case=False, na=False)).any(axis=1)`

- [x] **RF-MOD-005** — `GET /modelo/{tabla}/{pk_val}/ver` muestra detalle en solo lectura. Retorna 404 si PK no existe.
  - `router.py:110-127`: localiza fila por PK, retorna 404 via `_tmpl_error()` si vacía

- [x] **RF-MOD-006** — `GET/POST /modelo/{tabla}/nuevo` genera formulario dinámico y asigna PK auto-incremental.
  - GET: `router.py:74-90`: `dtypes = {col: str(df[col].dtype) for col in columnas}`
  - POST: `router.py:93-105`, `service.py:89-101`: `nuevo_pk = int(df[pk].max()) + 1 or 1`

- [x] **RF-MOD-007** — `GET/POST /modelo/{tabla}/{pk_val}/editar` con formulario precargado y casting automático.
  - `router.py:130-166`: carga registro actual, aplica `_cast(df[col].dtype, val)` en `editar_registro()`

- [x] **RF-MOD-008** — `POST /modelo/{tabla}/{pk_val}/eliminar` con protección pk=0 → 403.
  - `router.py:174`: `if pk_val in ("0", "0.0"): return _tmpl_error(request, "El registro pk=0 es inmutable.", 403)`

- [x] **RF-MOD-009** — `_cast(dtype, val)` convierte string al tipo nativo de la columna.
  - `service.py:130-140`: `int(float(val))` para int, `float(val)` para float, `None` si vacío

- [x] **RF-MOD-010** — `POST /modelo/validar` ejecuta `validar_integridad()` con los 4 tipos de error.
  - `service.py:143-204`: implementación completa `NULL_FK`, `FK_HUERFANA`, `TABLA_FALTANTE`, `FALTA_PK0`

- [x] **RF-MOD-011** — `GET /modelo/validar` renderiza página con botón de validación.
  - `router.py:39-42`: renderiza `validacion.html` con `{"resultado": None}`

- [x] **RF-MOD-012** — `GET /modelo/validar/export` retorna CSV StreamingResponse con errores.
  - `router.py:54-68`: `csv.DictWriter` con `["tabla", "columna", "tipo", "descripcion"]` → `StreamingResponse`

---

## Requerimientos no funcionales (RNF-MOD-0XX)

- [x] **RNF-MOD-001** — Lectura directa desde MinIO (no desde PocketBase).
  - `service.py:32-33`: `_load(tabla)` llama `read_parquet(MINIO_BUCKET_DIMS, tabla)` exclusivamente

- [x] **RNF-MOD-002** — Modelo dimensional de 12 tablas exactas.
  - `app/shared/templates.py:29-42`: `TABLAS` tiene exactamente 12 entradas

- [x] **RNF-MOD-003** — Auditoría en crear, editar, eliminar y validar.
  - Crear: `router.py:103-104`; Editar: `router.py:164-165`; Eliminar: `router.py:180-181`; Validar: `router.py:49-50`

- [x] **RNF-MOD-004** — PK auto-asignado como `max(pk) + 1` sin base de datos externa.
  - `service.py:92`: `int(df[pk].max()) + 1 if len(df) and df[pk].notna().any() else 1`

- [x] **RNF-MOD-005** — Rutas estáticas antes que dinámicas.
  - `router.py:3-4` y orden en archivo: `/validar`, `/{tabla}/nuevo` definidas antes de `/{tabla}` y `/{tabla}/{pk_val}`

- [x] **RNF-MOD-006** — 12 FK verificadas en `validar_integridad()`.
  - `service.py:13-26`: `FACT_FKS` tiene 12 entradas (incluyendo `fk_aeropuerto_origen` y `fk_aeropuerto_destino` → misma `dim_aeropuerto`)

- [x] **RNF-MOD-007** — Dimensiones opcionales toleran NULL y requieren pk=0.
  - `service.py:29`: `DIMS_OPCIONALES = {"dim_cancelacion", "dim_retraso_causa", "dim_desvio"}`
  - `service.py:158-162`: NULL en FK de opcional no genera error `NULL_FK`
  - `service.py:187-201`: verifica `FALTA_PK0` para cada dim en `DIMS_OPCIONALES`

---

## Reglas de negocio (RN-MOD-0XX)

- [x] **RN-MOD-001** — pk=0 es sentinel inmutable en 3 dimensiones opcionales.
  - `router.py:174`: bloquea con 403 si `pk_val in ("0", "0.0")`
  - `service.py:121-122`: `raise ValueError("El registro pk=0 es inmutable...")`
  - `service.py:196-201`: verifica `FALTA_PK0` si la dimensión no tiene fila con pk=0

- [x] **RN-MOD-002** — Solo las dimensiones opcionales pueden tener FK nulas.
  - `service.py:158-162`: `if nulos and dim_nombre not in DIMS_OPCIONALES: → NULL_FK error`

- [x] **RN-MOD-003** — CRUD opera directamente sobre Parquet en MinIO.
  - `service.py:32-38`: `_load()` = `read_parquet()`, `_save()` = `write_parquet()`. Sin base de datos intermedia.

- [x] **RN-MOD-004** — Tabla fuera del catálogo responde 404.
  - `router.py:77,97,113,...`: `if tabla not in TABLAS: return _tmpl_error(request, ..., 404)`

---

## Verificación cruzada código ↔ spec

| Item | Estado | Nota |
|---|---|---|
| 12 tablas en TABLAS | ✅ Coincide | `app/shared/templates.py:29-42` |
| 12 FKs en FACT_FKS | ✅ Coincide | `service.py:13-26` — dim_aeropuerto aparece 2 veces |
| PAGE_SIZE = 50 | ✅ Coincide | `templates.py:44` |
| 3 dimensiones opcionales | ✅ Coincide | `service.py:29` |
| 4 tipos de error en validar_integridad | ✅ Coincide | `service.py:143-204` |
| PK auto-incremental sin secuencia DB | ✅ Coincide | `service.py:92` |
| Protección pk=0 doble capa | ✅ Coincide | `router.py:174` + `service.py:121` |
| Exportación CSV con campos correctos | ✅ Coincide | `["tabla", "columna", "tipo", "descripcion"]` en `router.py:59` |
| CSV exporta UTF-8 estándar | ✅ Coincide | Spec escenario "Camino feliz" menciona UTF-8; código usa `io.StringIO()` que produce UTF-8 estándar sin BOM |
| Casting con pandas.api.types | ✅ Coincide | Spec RF-MOD-009 menciona "conversión de tipos"; código usa `pandas.api.types` (no DuckDB) |
| Auditoría en exportar errores | ⚠️ No implementado | `GET /modelo/validar/export` no llama `audit.registrar()`. El spec no lo requiere explícitamente para exportar. |
