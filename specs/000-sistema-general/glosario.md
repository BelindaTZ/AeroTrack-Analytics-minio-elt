# AeroTrack Analytics — Glosario Técnico

Definiciones de términos técnicos del sistema. Cada término incluye dónde aparece en el código real.

---

## OTP — On-Time Performance

**Definición:** Métrica de puntualidad aeroportuaria. Un vuelo es puntual (OTP=1) si llega con 15 minutos o menos de retraso. Se expresa como porcentaje de vuelos puntuales sobre el total.

**En el código:** Tabla de agregación `agg_otp_aerolinea_mes.parquet` en bucket `aerotrack-dims`. Columnas relevantes: `carrier`, `year`, `month`. Cargada via `load_agg("agg_otp_aerolinea_mes", filtros)` en `app/shared/analytics.py:142`.

---

## BTS — Bureau of Transportation Statistics

**Definición:** Agencia del Departamento de Transporte de EE.UU. que publica los datos de vuelos comerciales domésticos. Fuente del dataset de entrenamiento `airline_2m.csv` (~2 millones de registros).

**En el código:** No aparece como colección ni constante. Referenciado en comentarios de `dags/aerotrack_tasks.py`. El archivo `data/airline_2m.csv` es la materialización local de esta fuente.

---

## FAA — Federal Aviation Administration

**Definición:** Agencia federal de aviación de EE.UU. Establece los códigos de cancelación de vuelos (A=Carrier, B=Weather, C=NAS, D=Security) usados en el dataset BTS.

**En el código:** Módulo `app/cancelaciones/clasificar_faa.py`. Campo `CancellationCode` en `dim_cancelacion.parquet`. Filtro `cancel_code` en `load_enriched_fact()` (`app/shared/analytics.py:137`).

---

## IATA — International Air Transport Association

**Definición:** Asociación internacional que asigna códigos de 2 letras a aerolíneas (ej: AA=American, DL=Delta) y códigos de 3 letras a aeropuertos (ej: JFK, LAX).

**En el código:** Columna `Reporting_Airline` en `dim_aerolinea.parquet` (códigos IATA de aerolínea). Columnas `OriginCode`, `DestCode` en `dim_ruta.parquet` (códigos IATA de aeropuerto). Cargadas via `get_aerolinas()` y `get_origins()` en `app/shared/analytics.py`.

---

## Parquet

**Definición:** Formato de almacenamiento columnar binario optimizado para análisis. Soporta compresión y tipos de datos tipados. Usado en AeroTrack para todas las tablas del modelo dimensional y datos de staging.

**En el código:** Toda lectura: `read_parquet(bucket, tabla)` en `app/shared/clients/minio_client.py:32` usando `pandas.read_parquet()` + `pyarrow`. Toda escritura: `write_parquet(bucket, tabla, df)` en `app/shared/clients/minio_client.py:52` usando `df.to_parquet(engine="pyarrow")`. Archivos nombrados `{tabla}.parquet` en MinIO.

---

## fact_vuelo

**Definición:** Tabla de hechos central del modelo dimensional Kimball. Contiene un registro por vuelo individual con claves foráneas (FK) hacia las 11 dimensiones. No contiene atributos descriptivos — solo métricas y FKs.

**En el código:** Archivo `fact_vuelo.parquet` en bucket `aerotrack-dims`. PK: `pk_vuelo`. FKs: 12 columnas `fk_*` definidas en `FACT_FKS` en `app/modelo_dimensional/data/service.py:13`. Cargada via `read_parquet(MINIO_BUCKET_DIMS, "fact_vuelo")` o `load_enriched_fact()`.

---

## agg_* — Tablas de agregación

**Definición:** 10 tablas Parquet pre-calculadas por el pipeline (tarea `transform`) que resumen `fact_vuelo` a nivel mensual, por aerolínea, ruta, etc. Son recalculables: si se corrompen, re-ejecutar `transform` las regenera. **Nunca son fuente de verdad** (Principio II).

**Tablas en aerotrack-dims:**

| Tabla | Descripción |
|---|---|
| `agg_otp_aerolinea_mes` | OTP por aerolínea y mes |
| `agg_causas_retraso_mes` | Causas de retraso por mes |
| `agg_rutas_eficiencia` | Eficiencia operacional por ruta |
| `agg_cancelaciones_causa` | Cancelaciones por código FAA |
| `agg_cancelaciones_aerolinea_causa` | Cancelaciones cruzadas aerolínea × causa |
| `agg_cancelaciones_ruta` | Cancelaciones por ruta |
| `agg_desvios_ruta` | Desvíos por ruta |
| `agg_otp_dia_semana` | OTP por día de la semana |
| `agg_otp_aerolinea_dia_semana` | OTP por aerolínea × día de semana |
| `agg_kpi_global_dia` | KPIs globales diarios |

**En el código:** Cargadas via `load_agg(name, filtros)` en `app/shared/analytics.py:142`. Caché en memoria TTL 600s (`_agg_cache`).

---

## vuelos_raw

**Definición:** Colección de staging en PocketBase donde se almacenan los registros de vuelos crudos antes de la transformación al modelo dimensional.

**En el código:** Nombre de colección PocketBase definido en `dags/config.py:44` como `PB_COLLECTION = os.getenv("PB_COLLECTION", "vuelos_raw")`. La tarea `extract` en `dags/aerotrack_tasks.py` lee de esta colección. También existe como archivo en MinIO: `aerotrack-raw/vuelos_raw.parquet`.

---

## dim_* — Dimensiones del modelo Kimball

**Definición:** 11 tablas de dimensión desnormalizadas que describen los atributos de los vuelos. Cada fila tiene una PK (`pk_*`) referenciada como FK en `fact_vuelo`.

**Catálogo completo (definido en `app/shared/templates.py:29`):**

| Tabla | PK | Descripción |
|---|---|---|
| `dim_tiempo` | `pk_tiempo` | Fecha, año, mes, día semana, quarter |
| `dim_aerolinea` | `pk_aerolinea` | Código IATA de aerolínea |
| `dim_aeropuerto` | `pk_aeropuerto` | Códigos IATA de aeropuerto (origen y destino) |
| `dim_avion` | `pk_avion` | Matrícula y tipo de aeronave |
| `dim_retraso_causa` | `pk_retraso_causa` | Minutos de retraso por causa (opcional, pk=0 sentinel) |
| `dim_cancelacion` | `pk_cancelacion` | Código de cancelación FAA (opcional, pk=0 sentinel) |
| `dim_distancia` | `pk_distancia` | Distancia en millas del vuelo |
| `dim_desvio` | `pk_desvio` | Datos de desvío de ruta (opcional, pk=0 sentinel) |
| `dim_horario` | `pk_horario` | Minutos de retraso de llegada y salida |
| `dim_clasificacion_retraso` | `pk_clasificacion` | Flag ArrDel15 y DepDel15 |
| `dim_ruta` | `pk_ruta` | Origen, destino, distancia de la ruta |

**En el código:** Definidas en `TABLAS` en `app/shared/templates.py:29`. Las 3 opcionales (`dim_retraso_causa`, `dim_cancelacion`, `dim_desvio`) están en `DIMS_OPCIONALES` en `app/modelo_dimensional/data/service.py:29`.

---

## RAG — Retrieval-Augmented Generation

**Definición:** Patrón de IA que complementa las capacidades de un LLM inyectando contexto recuperado dinámicamente en el prompt. En AeroTrack, el contexto es una selección de KPIs y métricas cargadas desde las tablas de agregación de MinIO, no vectores embeddings.

**En el código:** Implementado en `app/asistente_ia/rag.py`. La función `build_context()` carga KPIs de las fuentes activas (controladas por `asistente_fuentes` en PocketBase) y los inyecta como texto plano en el prompt. No usa base de datos vectorial — usa parseo regex de intención + consultas estructuradas a tablas Parquet.

---

## Holt-Winters

**Definición:** Algoritmo de suavizamiento exponencial triple (tendencia + estacionalidad) para predicción de series temporales. Usado en el módulo Predictivo para proyectar OTP mensual por aerolínea.

**En el código:** `statsmodels.tsa.holtwinters.ExponentialSmoothing` en `app/predictivo/proyeccion_riesgo.py`. Parámetros: `trend="add"`, `seasonal="add"`. La proyección incluye intervalos de confianza calculados a partir de la desviación estándar de los residuales.

**Nota:** La spec menciona Prophet, pero el código implementa Holt-Winters con `statsmodels`. Discrepancia documentada en `CLAUDE.md`.

---

## Z-score

**Definición:** Métrica de desviación estándar normalizada. Indica cuántas desviaciones estándar se aleja un valor de la media. Usada en el módulo Predictivo para caracterizar la volatilidad del OTP de una aerolínea.

**En el código:** Calculada implícitamente en `app/predictivo/proyeccion_riesgo.py:258` mediante `std_otp` (desviación estándar del OTP histórico). No hay función `zscore` explícita — se usa la desviación estándar directamente para generar la narrativa.

---

## RBAC — Role-Based Access Control

**Definición:** Modelo de control de acceso donde los permisos se asignan a roles, y los usuarios pertenecen a un rol. En AeroTrack: colecciones `roles`, `permisos`, `modulos`, `roles_permisos` en PocketBase.

**En el código:** Implementado en `app/shared/deps.py`. Función clave: `require_permission(modulo, accion)` en línea 72. Permisos cacheados por `rol_id` con TTL 300s en `_perm_cache` (línea 15). `invalidate_permission_cache(rol_id)` en línea 28 se llama al guardar cambios de permisos. PocketBase almacena los datos pero no los impone (Principio III).

---

## JWT — JSON Web Token

**Definición:** Estándar para transmitir información de identidad de forma compacta y auto-contenida entre cliente y servidor. Firmado con clave secreta (HS256 en AeroTrack).

**En el código:** Algoritmo HS256, biblioteca `python-jose`. Generación: `crear_token(data)` en `app/seguridad/jwt/service.py:10`. Verificación: `verificar_token(token)` en línea 16. Payload: `{sub (PocketBase record.id), email, nombre, rol_id, activo, exp}`. Almacenado en cookie `access_token` con flags `httponly=True`, `samesite="lax"`, `max_age=3600`. TTL configurado por `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60, en `app/config.py:30`).

---

## staging

**Definición:** Capa intermedia de datos crudos antes de la transformación al modelo analítico. En AeroTrack comprende dos repositorios: la colección PocketBase `vuelos_raw` (datos operacionales) y el archivo `aerotrack-raw/vuelos_raw.parquet` (volcado de la extracción).

**En el código:** PocketBase collection: `vuelos_raw` (referenciada en `dags/config.py:44`). MinIO bucket: `aerotrack-raw` (variable `MINIO_BUCKET_RAW`, `app/config.py:13`). Ningún módulo analítico lee de estas fuentes (Principio I).

---

## load_agg()

**Definición:** Función que lee una tabla de agregación pre-calculada desde MinIO `aerotrack-dims` y aplica filtros opcionales por año, mes y aerolínea. Incluye caché en memoria TTL 600s.

**Firma:** `load_agg(name: str, filtros: Optional[dict] = None, bucket: str = MINIO_BUCKET_DIMS) -> pd.DataFrame`

**En el código:** `app/shared/analytics.py:142`. Caché `_agg_cache` keyed por `"{bucket}:{name}"`. Filtros soportados: `year`, `month`, `airline`. Usada por: dashboard, puntualidad, rutas, cancelaciones, reportes, predictivo, asistente IA, socios API.

---

## load_enriched_fact()

**Definición:** Función que carga `fact_vuelo` enriquecido con joins LEFT de 8 dimensiones (tiempo, aerolínea, ruta, cancelación, clasificación, horario, retraso_causa, desvío). El resultado se cachea TTL 600s. Aplica filtros sobre la copia cacheada sin re-leer MinIO.

**Firma:** `load_enriched_fact(filtros: Optional[dict] = None, bucket: str = MINIO_BUCKET_DIMS) -> pd.DataFrame`

**Filtros soportados:** `year`, `month`, `airline`, `origin`, `dest`, `ruta`, `quarter`, `dow`, `solo_cancelados`, `cancel_code`

**En el código:** `app/shared/analytics.py:102`. Llama a `_load_base_fact()` (línea 44) que realiza los merges. Caché `_fact_cache` TTL 600s. Usada por: reportes, rutas, predictivo, asistente IA.

---

## audit.registrar()

**Definición:** Función INSERT-only que escribe un registro en la colección `auditoria` de PocketBase. Nunca lanza excepción al llamador (principio de no-bloqueo).

**Firma:**
```python
audit.registrar(
    usuario_id: str,
    usuario_email: str,
    accion: str,        # login|logout|login_fallido|crear|editar|eliminar|ejecutar|exportar|configurar|validar|ver_reporte
    modulo: str,        # seguridad|pipeline_elt|modelo_dimensional|dashboard|puntualidad|rutas|cancelaciones|reportes|predictivo|configuracion|monitoreo
    recurso_tipo: str = "",
    recurso_id: str = "",
    detalle: str = "",
    ip_address: str = "",
    resultado: str = "exitoso",  # exitoso|fallido|parcial
) -> None
```

**En el código:** `app/shared/utils/audit.py:6`. Implementado con `try/except: pass` — el fallo de auditoría nunca interrumpe la operación principal (Principio VI + Principio V).

---

## horizonte_prediccion_max

**Definición:** Parámetro de configuración que limita el número máximo de meses hacia adelante que el módulo Predictivo puede proyectar. Previene proyecciones estadísticamente no fiables a largo plazo.

**En el código:** Leído desde `configuracion_sistema` en PocketBase, clave `"horizonte_prediccion_max"`, módulo `"ia"`. Función `_get_horizonte_max()` en `app/predictivo/proyeccion_riesgo.py:32`. Default: `6` meses. Aplicado en endpoints `POST /predictivo` (línea 496) y `POST /predictivo/whatif` (línea 531).
