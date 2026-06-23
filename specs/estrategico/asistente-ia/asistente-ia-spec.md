# Especificación Estratégica — Asistente IA

**Módulo:** Asistente IA
**Prefijo:** AIA
**Código fuente:** `app/asistente_ia/`
**Casos de uso cubiertos:** CU-E18 (Consultar asistente analítico conversacional con IA), CU-T09 (Configurar parámetros del asistente IA)
**Actor:** Analista de Datos (CU-E18), Administrador (CU-T09)

---

## Funcionalidad 1: Consultar asistente analítico conversacional con IA (CU-E18)

Chat conversacional en `GET /ia` que permite al Analista hacer preguntas en lenguaje natural sobre los datos de vuelos. Usa RAG (sin embeddings vectoriales) con parseo regex de intención, consultas estructuradas a 10 tablas Parquet, y LLM multi-proveedor. Implementado en `app/asistente_ia/`.

### RF-AIA-001 — Página de chat con sidebar informativo
`GET /ia` renderiza `asistente_ia/chat.html` con: indicador de estado del módulo (activo/inactivo/sin API key), proveedor y modelo configurados, preguntas de ejemplo, historial reciente (últimas 5 conversaciones del usuario desde PocketBase), panel colapsable de fuentes activas toggleables, y área principal de chat. Permiso requerido: `asistente_ia:ver`.

### RF-AIA-002 — Enviar mensaje y obtener respuesta LLM con RAG
`POST /ia/chat` acepta JSON: `{mensaje (1-800 chars obligatorio), session_id (opcional)}`. El flujo RAG: (1) `parse_intent(question)` extrae filtros vía regex (aerolínea, año, mes, ruta origen-destino, aeropuerto, día de semana); (2) `build_context(filtros, question)` selecciona secciones según tipo de pregunta detectado y fuentes activas; (3) `build_messages(history, context, question)` arma system prompt + historial + contexto + pregunta; (4) `call_llm(messages)` envía al proveedor configurado. Retorna JSON: `{respuesta, filtros, session_id}`. Permiso requerido: `asistente_ia:ejecutar`.

### RF-AIA-003 — RAG basado en 10 fuentes de datos Parquet
El contexto se construye a partir de 10 tablas de datos, cada una con una clave única que permite su activación/desactivación individual:

| Clave | Tabla | Tipo | Contenido |
|-------|-------|------|-----------|
| `otp_global` | `agg_otp_aerolinea_mes` | agg | KPIs globales, ranking aerolíneas, tendencia mensual OTP |
| `cancelaciones` | `agg_cancelaciones_causa` | agg | Cancelaciones por código FAA (A/B/C/D) |
| `cancelaciones_aerolinea` | `agg_cancelaciones_aerolinea_causa` | agg | Cancelaciones cruzadas aerolínea × causa FAA |
| `cancelaciones_ruta` | `agg_cancelaciones_ruta` | agg | Rutas con mayor tasa de cancelación |
| `causas_retraso` | `agg_causas_retraso_mes` | agg | Minutos de retraso por causa (carrier, weather, NAS, security, late aircraft) |
| `rutas_eficiencia` | `agg_rutas_eficiencia` | agg | Rutas más y menos eficientes (retraso promedio, eficiencia media) |
| `desvios` | `agg_desvios_ruta` | agg | Rutas con más desvíos |
| `otp_dia_semana` | `agg_otp_dia_semana` | agg | OTP por día de la semana (global) |
| `otp_aerolinea_dia` | `agg_otp_aerolinea_dia_semana` | agg | OTP por aerolínea y día de la semana |
| `detalle_vuelos` | `fact_vuelo` (enriquecido) | fact | Detalle dinámico de vuelos individuales con 8 dimensiones |

Las fuentes `cancelaciones_aerolinea` y `otp_aerolinea_dia` fueron añadidas como parte de un gap de auditoría (no estaban en el diseño original).

### RF-AIA-004 — Parseo de intención por regex (sin NLP)
`parse_intent()` extrae filtros de la pregunta en 6 pasos secuenciales, todos sobre texto plano sin modelos de lenguaje: (1) código IATA de aerolínea (2 letras, con negative lookbehind/lookahead); (2) año (20dd con word boundary); (3) mes (español/inglés, abreviaciones 3 letras); (4) ruta explícita (AAA-BBB o "de AAA a BBB"); (5) aeropuerto individual (3 letras mayúsculas, excluyendo palabras reservadas OTP/ELT/KPI/FAA/NAS/USA/API/PDF/CSV/SQL); (6) día de semana (español/inglés, substring simple).

### RF-AIA-005 — Selección inteligente de secciones según tipo de pregunta
`_detect_question_type(question)` identifica palabras clave: "retraso"/"delay" → `delay_cause`; "cancelación"/"cancelado" → `cancelacion`; "eficiente"/"eficiencia" → `eficiencia`; "desvío"/"desviado" → `desvio`; "día"/"semana"/"lunes"/"martes"... → `dia_semana`; "ranking"/"top"/"mejor"/"peor" → `ranking_otp`; "tendencia"/"evolución" → `tendencia`; "ruta"/"vuelo" → `ruta`. Si no se detecta ningún tipo, `carga_todo = True` y se cargan todas las fuentes activas.

### RF-AIA-006 — System prompt con reglas estrictas de uso de datos
El system prompt instruye al LLM a: (1) citar solo números que aparezcan literalmente en el contexto; (2) prohibido calcular, estimar, redondear, inferir o extrapolar cifras; (3) prohibido inventar causas externas; (4) respuesta parcial si el contexto no cubre toda la pregunta; (5) usar tablas markdown para rankings y comparativas (máx 15 filas), viñetas para listas cortas (≤4 items), párrafos para análisis narrativo.

### RF-AIA-007 — Soporte multi-proveedor de LLM
`call_llm()` lee la configuración desde `configuracion_sistema` módulo "ia" con cache de 60s. Proveedores soportados: Groq (OpenAI-compat, endpoint `https://api.groq.com/openai`), Anthropic (`https://api.anthropic.com/v1/messages`), Gemini (`https://generativelanguage.googleapis.com`), OpenAI (OpenAI-compat), y custom endpoint. La API key se resuelve con fallbacks: `ia_api_key` primaria, luego `ia_api_key_groq` para Groq o `ia_api_key_gemini` para Gemini. Parámetros: modelo (por defecto `llama-3.1-8b-instant` para Groq, `claude-haiku-4-5-20251001` para Anthropic, `gemini-2.0-flash` para Gemini), max_tokens (default 2048), temperatura (default 0.3), timeout (default 30s).

### RF-AIA-008 — Historial de conversación en memoria para contexto multi-turn
El historial se mantiene en `_sessions` (dict en memoria, TTL 30 min, limpieza al superar 500 entradas). Se almacenan los últimos 20 mensajes (10 turnos) por sesión. El session_id se gestiona mediante cookie `chat_session` (httponly). Si la cookie no existe, se genera un nuevo token con `secrets.token_hex(16)`.

### RF-AIA-009 — Persistencia de conversaciones en PocketBase (Gap cerrado Lote 4 — sin CU catalogado)
Cada intercambio (pregunta + respuesta + filtros) se persiste en la colección `conversaciones_asistente` de PocketBase mediante `_persist_conversacion()` que envuelve el `create_record` en try/except. Si la persistencia falla, la respuesta al usuario no se interrumpe (resiliente). Campos: `usuario_id` (relation → app_users), `pregunta` (text), `respuesta` (text), `fuentes` (json). No hay cascade delete.

### RNF-AIA-001 — Escritura resiliente en persistencia
`_persist_conversacion()` usa try/except que captura toda excepción y solo registra un warning en el log. La respuesta al usuario nunca falla por un error de persistencia.

### RNF-AIA-002 — Cache de configuración IA 60 segundos
`get_ia_config()` cachea la configuración del módulo "ia" en `_cfg_cache` con TTL 60s. La función `invalidar_config()` limpia la caché (llamada desde el panel de configuración al guardar cambios).

### RNF-AIA-003 — Configuración IA leída desde configuracion_sistema
Las configuraciones del asistente se almacenan en `configuracion_sistema` con `modulo="ia"`. Claves: `ia_proveedor`, `ia_api_key`, `ia_modelo`, `ia_endpoint`, `ia_max_tokens`, `ia_temperatura`, `ia_activa`, `ia_timeout_segundos`, `ia_api_key_grok`, `ia_api_key_gemini`. Semillas gestionadas por `setup_pocketbase_admin.py`.

### RNF-AIA-004 — Sin dependencia de embeddings vectoriales
El RAG no usa embeddings, vectores, ni búsqueda semántica. Todo el contexto se genera mediante parseo regex + consultas estructuradas a tablas Parquet + lógica condicional de secciones.

---

## Funcionalidad 2: Configurar fuentes de conocimiento toggleables (CU-T09 — Gap cerrado Lote 4)

Permite al usuario activar o desactivar individualmente las 10 fuentes de datos que alimentan el RAG. Implementado como colección `asistente_fuentes` en PocketBase, cache con invalidation, y endpoints REST en `router.py`.

### RF-AIA-010 — Colección asistente_fuentes en PocketBase
Colección con schema: `clave` (text, required, única), `nombre` (text, required), `descripcion` (text, opcional), `tabla` (text, required), `tipo` (select: agg/fact), `activa` (bool, default true). Reglas: `listRule: @request.auth.id != ''`, `createRule: ""`. 10 registros semilla cargados por `setup_pocketbase_admin.py` step 11/11.

### RF-AIA-011 — Cache de fuentes activas con TTL 60s
`_get_activas()` en `rag.py` consulta `asistente_fuentes` con filtro `activa=True` y cachea el conjunto de claves activas durante 60 segundos en `_SOURCE_CACHE` (variable global). Si la consulta falla o retorna conjunto vacío, se usa `_ALL_SOURCES` (todas las 10 fuentes). Si no hay datos en caché y la consulta a PocketBase falla, se retorna también `_ALL_SOURCES`.

### RF-AIA-012 — Endpoint GET /ia/fuentes
Retorna todas las fuentes ordenadas por clave desde `asistente_fuentes`. Permiso: `asistente_ia:ver`. En caso de error de conexión a PocketBase, retorna lista vacía.

### RF-AIA-013 — Endpoint POST /ia/fuentes/toggle
Acepta JSON `{clave}`. Busca la fuente por clave en `asistente_fuentes`, niega el valor actual de `activa`, actualiza el registro y además invalida el cache de `_get_activas()` seteando `_SOURCE_CACHE["data"] = None`. Retorna `{clave, activa}`. Permiso: `asistente_ia:ejecutar`. Errores: 400 si falta clave, 404 si no se encuentra, 500 en otras excepciones.

### RF-AIA-014 — Secciones de RAG controladas por fuentes activas
Cada bloque de `build_context()` verifica si la clave correspondiente está en el conjunto `activas` obtenido de `_get_activas()`. Las 10 secciones (detalladas en RF-AIA-003) están mapeadas a sus claves respectivas. Si una fuente está desactivada, su sección entera se omite del contexto, incluso si `carga_todo = True`. Para la sección 10 (detalle de aeropuerto), se verifica que al menos una de las dos fuentes necesarias esté activa.

### RNF-AIA-005 — Toggle invalida caché inmediatamente
`POST /ia/fuentes/toggle` invalida `_SOURCE_CACHE["data"]` a None, forzando la próxima consulta RAG a recargar las fuentes activas desde PocketBase.

### RNF-AIA-006 — Fallback a todas las fuentes si PocketBase no responde
Si `asistente_fuentes` no existe o hay error de conexión, `_get_activas()` retorna `_ALL_SOURCES` (comportamiento igual al diseño original sin toggle).

---

## Funcionalidad 3: Consultar historial de conversaciones (implementación sin CU catalogado — Gap Lote 4)

Endpoint y UI que muestra el historial persistente de conversaciones del usuario autenticado, permitiendo re-enviar preguntas anteriores.

### RF-AIA-015 — Endpoint GET /ia/historial
Retorna las últimas 20 conversaciones del usuario autenticado (JWT), filtradas por `usuario_id="{user["sub"]}"` en la colección `conversaciones_asistente`, ordenadas por `-created` (más recientes primero). Usa el token de administrador de PocketBase para leer los registros. Permiso: `asistente_ia:ver`.

### RF-AIA-016 — Sidebar de historial en chat.html
El template `chat.html` muestra las últimas 5 conversaciones del usuario en un panel "Historial reciente" dentro del sidebar. Cada entrada muestra los primeros 60 caracteres de la pregunta como texto clickeable. Al hacer clic, la función `setQuestion()` rellena el input y envía el mensaje automáticamente.

### RNF-AIA-007 — Historial limitado a 20 registros por consulta
El endpoint `GET /ia/historial` retorna máximo 20 registros (slice `[:20]`). No hay paginación implementada. La UI solo muestra los primeros 5.

---

## Reglas de negocio

### RN-AIA-001 — Respuesta sin datos si no hay contexto
Si `build_context()` no puede cargar ninguna sección (porque todas las fuentes están desactivadas o no hay datos), retorna el mensaje fijo "No hay datos disponibles. Asegúrese de que el pipeline ELT se ha ejecutado."

### RN-AIA-002 — Prohibición de alucinación numérica
El system prompt prohíbe explícitamente al LLM calcular, estimar, redondear, inferir o extrapolar cifras no presentes en el contexto. Solo puede citar valores literales.

### RN-AIA-003 — Respuesta parcial preferida sobre "no sé"
Si la pregunta tiene respuesta parcial en el contexto, el LLM debe responder primero con lo que SÍ tiene (citando valores literales) e indicar al final qué dato específico no está disponible.

### RN-AIA-004 — Historial volátil + persistente
Existen dos capas de historial: (1) en memoria (`_sessions`, TTL 30 min, últimos 20 mensajes) para contexto multi-turn del LLM; (2) persistente en PocketBase (`conversaciones_asistente`) para consulta del usuario. La capa en memoria no se recupera desde PocketBase al iniciar sesión.

### RN-AIA-005 — Máscara de API keys
Las claves API (`ia_api_key`, `ia_api_key_grok`, `ia_api_key_gemini`) se almacenan con `sensible=True` en `configuracion_sistema` y se ocultan en la UI. No se muestran en logs ni en respuestas de API.

### RN-AIA-006 — Colección conversaciones sin deleteRule
La colección `conversaciones_asistente` no tiene regla de borrado. Los registros son inmutables (append-only). No hay límite de retención.

---

## Entradas y salidas

| FUNCIÓN / ENDPOINT | ENTRADAS | SALIDAS |
|---|---|---|
| GET /ia | Cookie JWT | HTML: panel de chat + sidebar (estado, info, ejemplos, historial, fuentes) |
| POST /ia/chat | Cookie JWT, JSON: {mensaje, session_id?} | JSON: {respuesta, filtros{}, session_id} |
| POST /ia/reset | Cookie JWT, cookie session_id | JSON: {session_id: nuevo token} |
| GET /ia/historial | Cookie JWT | JSON: [{id, usuario_id, pregunta, respuesta, fuentes, created}] (máx 20) |
| GET /ia/fuentes | Cookie JWT | JSON: [{id, clave, nombre, descripcion, tabla, tipo, activa}] |
| POST /ia/fuentes/toggle | Cookie JWT, JSON: {clave} | JSON: {clave, activa} |

---

## Historias de usuario

- **HU-AIA-01:** Como Analista de Datos quiero hacer preguntas en lenguaje natural sobre los datos de vuelos para obtener respuestas rápidas sin escribir consultas técnicas.
- **HU-AIA-02:** Como Analista de Datos quiero que el asistente solo use datos reales del sistema y no invente cifras para confiar en las respuestas.
- **HU-AIA-03:** Como Analista de Datos quiero ver el historial de mis conversaciones anteriores para retomar análisis previos.
- **HU-AIA-04:** Como Analista de Datos quiero hacer clic en una pregunta anterior para re-enviarla al asistente y obtener una respuesta actualizada.
- **HU-AIA-05:** Como Administrador quiero activar/desactivar fuentes de datos específicas del asistente IA para controlar qué información está disponible para los analistas.

---

## Objetivo

Proporcionar un asistente conversacional basado en IA que permita a los analistas consultar datos operacionales de aviación (OTP, cancelaciones, retrasos, rutas) en lenguaje natural, con respuestas basadas estrictamente en datos reales provenientes de 10 fuentes estructuradas, historial persistente de conversaciones, y control granular de fuentes de conocimiento.

---

## Escenarios

### Camino feliz — Consulta conversacional
1. El Analista accede a `GET /ia` y ve el sidebar con estado del módulo, proveedor/modelo, preguntas de ejemplo e historial reciente.
2. El Analista escribe "¿Cuál fue la aerolínea más puntual en 2022?" y hace clic en enviar.
3. `POST /ia/chat` ejecuta `parse_intent()` que detecta `airline` (ningún código IATA match → consulta global), `year=2022`.
4. `build_context()` carga `agg_otp_aerolinea_mes` con filtro year=2022, genera secciones de KPIs globales, tendencia mensual y ranking de aerolíneas.
5. `call_llm()` envía el contexto al LLM configurado (Groq/Anthropic/Gemini/OpenAI) con system prompt de reglas estrictas.
6. El LLM retorna una respuesta que cita el ranking exacto del contexto, por ejemplo: "La aerolínea más puntual en 2022 fue Delta Air Lines (DL) con un OTP de 83.2%".
7. El mensaje se persiste en `conversaciones_asistente` y el historial en memoria se actualiza.
8. El Analista puede ver la conversación en el historial reciente del sidebar.

### Camino feliz — Toggle de fuentes
1. El Administrador accede al chat, expande la sección "Fuentes activas" en el sidebar.
2. Desmarca "Cancelaciones por código FAA".
3. `POST /ia/fuentes/toggle` con clave `cancelaciones` → PocketBase actualiza `activa=False`, cache RAG invalidado.
4. El Analista pregunta "¿Cuáles son las principales causas de cancelación?"
5. `build_context()` salta la sección de cancelaciones (fuente desactivada, aunque el tipo de pregunta lo requiera).
6. El LLM responde que no hay datos de cancelaciones disponibles en el contexto actual.

### Manejo de errores
- **Módulo deshabilitado (`ia_activa=false`):** `POST /ia/chat` retorna 503 con mensaje "El módulo Asistente IA está deshabilitado. Actívelo en Configuración → IA."
- **Sin API key configurada:** El LLM client lanza `ValueError`, capturado como 503 con mensaje descriptivo.
- **Error de red en LLM:** `RuntimeError` capturado como 503.
- **Error inesperado en LLM:** Capturado como 500 con mensaje genérico "Ocurrió un error inesperado al procesar tu consulta."
- **Pregunta vacía (>800 chars):** 400 Bad Request.
- **Fallo en persistencia PocketBase:** Se registra warning en log, la respuesta al usuario no se interrumpe.
- **Fallo en carga de fuentes activas:** `_get_activas()` retorna `_ALL_SOURCES` (todas las fuentes), comportamiento degradado pero funcional.

---

## Criterios de aceptación

- **CU-E18:** Dado que el módulo está activo y hay API key configurada, cuando el Analista envía una pregunta, entonces el sistema devuelve una respuesta del LLM basada en el contexto RAG construido desde las fuentes activas, con citas literales de los datos.
- **CU-T09:** Dado que existen fuentes registradas en `asistente_fuentes`, cuando el Administrador cambia el estado activa de una fuente, entonces el sistema persiste el cambio en PocketBase, invalida el cache RAG, y las próximas consultas excluyen esa fuente del contexto.
- **Historial (Gap Lote 4):** Dado que el usuario ha realizado conversaciones previas, cuando accede al historial, entonces el sistema muestra las últimas 20 conversaciones del usuario ordenadas por fecha descendente.

---

## Dependencias

- **Seguridad:** Autenticación JWT y autorización con permisos `asistente_ia:ver` (chat, historial, fuentes) y `asistente_ia:ejecutar` (chat, toggle fuentes).
- **Pipeline ELT:** Las 10 tablas de datos (9 agregaciones + fact enriquecido) en MinIO.
- **Configuración:** Colección `configuracion_sistema` módulo "ia" con proveedor, API keys, modelo, parámetros.
- **PocketBase:** Colecciones `conversaciones_asistente` (historial) y `asistente_fuentes` (fuentes toggleables).
- **LLM externo:** Dependencia de API externa (Groq, Anthropic, Gemini u OpenAI) con conexión a internet. Sin LLM local.
- **Multi-provider support:** `app/asistente_ia/llm_client.py` abstrae 4 proveedores: Groq, Anthropic, Gemini, OpenAI/Custom.

---

## Casos de uso relacionados

- CU-E14 (Proyección predictiva OTP): datos de `agg_otp_aerolinea_mes` usados tanto en predictivo como en RAG.
- CU-T03, CU-T04, CU-T09 (Configuración general del sistema): el panel de configuración permite editar parámetros IA (proveedor, API keys, modelo, etc.).

---

## Fuera de alcance

- Embeddings vectoriales, búsqueda semántica o RAG con vectores (el sistema usa parseo regex + consultas estructuradas).
- Análisis de sentimiento, resumen automático o generación de narrativa fuera del contexto de datos.
- Chat multi-idioma (solo español, con soporte limitado de términos en inglés para parseo).
- Subida de documentos o archivos como fuente de conocimiento adicional.
- Memoria a largo plazo (el historial en memoria expira a los 30 min y no se recupera desde PocketBase).
- Edición o borrado de conversaciones del historial (append-only).
- Exportación del historial de conversaciones.
- Roles de acceso diferenciados dentro del chat (todos los usuarios autenticados con permiso `ejecutar` tienen las mismas capacidades).
- Personalización del system prompt por usuario.
- Streaming de respuestas del LLM (la respuesta se recibe completa).
- Modos de chat predefinidos (analítico, resumen, exploratorio).
