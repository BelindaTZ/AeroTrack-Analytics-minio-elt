# Especificación Estratégica — Asistente IA

**Módulo:** Asistente IA
**Prefijo:** AIA
**Código fuente:** `app/asistente_ia/`
**Casos de uso cubiertos:** CU-E18 (Consultar asistente analítico conversacional con IA), CU-T09 (Configurar parámetros del asistente IA), CU-O14 (Consultar narrativa IA de un gráfico o KPI)
**Actor:** Analista de Datos (CU-E18), Administrador (CU-T09)

---

## Funcionalidad 1: Consultar asistente analítico conversacional con IA (CU-E18)

Chat conversacional que permite al Analista hacer preguntas en lenguaje natural sobre los datos de vuelos. Usa RAG sin embeddings vectoriales, con parseo regex de intención, consultas estructuradas a 10 tablas Parquet y cliente LLM multi-proveedor.

### RF-AIA-001 — Página de chat con sidebar informativo
El sistema debe mostrar la interfaz de chat con: indicador de estado del módulo (activo/inactivo/sin API key), proveedor y modelo configurados, preguntas de ejemplo, historial reciente (últimas 5 conversaciones del usuario desde el repositorio), panel colapsable de fuentes activas con opciones de activación/desactivación, y área principal de chat. Requiere permiso `asistente_ia:ver`.

### RF-AIA-002 — Enviar mensaje y obtener respuesta LLM con RAG
El sistema debe aceptar mensajes de texto de 1 a 800 caracteres con identificador de sesión opcional. El flujo de procesamiento es: (1) extracción de filtros mediante parseo de intención (aerolínea, año, mes, ruta, aeropuerto, día de semana); (2) construcción del contexto seleccionando secciones según el tipo de pregunta detectado y las fuentes activas; (3) ensamblado del mensaje con historial, contexto y pregunta; (4) llamada al proveedor LLM configurado. Retorna respuesta, filtros extraídos e identificador de sesión. Requiere permiso `asistente_ia:ejecutar`.

### RF-AIA-003 — RAG basado en 10 fuentes de datos Parquet
El sistema debe construir el contexto a partir de 10 fuentes de datos, cada una con una clave única que permite su activación/desactivación individual:

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

Las fuentes `cancelaciones_aerolinea` y `otp_aerolinea_dia` fueron añadidas como parte de un gap de auditoría.

### RF-AIA-004 — Parseo de intención por regex (sin NLP)
El sistema debe extraer filtros de la pregunta en 6 pasos secuenciales mediante expresiones regulares, sin modelos de lenguaje: (1) código IATA de aerolínea (2 letras); (2) año (20xx); (3) mes (español/inglés, abreviaciones de 3 letras); (4) ruta explícita (AAA-BBB o "de AAA a BBB"); (5) aeropuerto individual (3 letras mayúsculas, excluyendo palabras reservadas del dominio); (6) día de semana (español/inglés).

### RF-AIA-005 — Selección inteligente de secciones según tipo de pregunta
El sistema debe identificar el tipo de pregunta a partir de palabras clave: "retraso"/"delay" → causas de retraso; "cancelación"/"cancelado" → cancelaciones; "eficiente"/"eficiencia" → eficiencia de rutas; "desvío"/"desviado" → desvíos; días de semana → OTP por día; "ranking"/"top"/"mejor"/"peor" → ranking OTP; "tendencia"/"evolución" → tendencia temporal; "ruta"/"vuelo" → rutas. Si no se detecta ningún tipo, se cargan todas las fuentes activas.

### RF-AIA-006 — System prompt con reglas estrictas de uso de datos
El sistema debe instruir al LLM a: (1) citar solo números que aparezcan literalmente en el contexto; (2) no calcular, estimar, redondear, inferir ni extrapolar cifras; (3) no inventar causas externas; (4) dar respuesta parcial si el contexto no cubre toda la pregunta; (5) usar tablas para rankings y comparativas (máx 15 filas), viñetas para listas cortas (≤ 4 items) y párrafos para análisis narrativo.

### RF-AIA-007 — Soporte multi-proveedor de LLM
El sistema debe leer la configuración del proveedor desde el repositorio de configuración (módulo "ia") con caché de 60s. Los proveedores soportados son: Groq, Anthropic, Gemini, OpenAI y endpoint personalizado. La resolución de API key sigue un orden de fallback por proveedor. Los parámetros de generación (modelo, max_tokens, temperatura, timeout) son configurables.

### RF-AIA-008 — Historial de conversación en memoria para contexto multi-turn
El sistema debe mantener el historial de conversación en memoria con TTL de 30 minutos y límite de 500 sesiones simultáneas, almacenando los últimos 20 mensajes (10 turnos) por sesión. El identificador de sesión se gestiona mediante cookie protegida. Si la cookie no existe, el sistema genera un nuevo identificador.

### RF-AIA-009 — Persistencia de conversaciones en repositorio
El sistema debe persistir cada intercambio (pregunta + respuesta + filtros) en el repositorio de conversaciones. La escritura se realiza de forma resiliente: si falla, la respuesta al usuario no se interrumpe. Los campos almacenados son: identificador de usuario, pregunta, respuesta y fuentes utilizadas.

### RNF-AIA-001 — Escritura resiliente en persistencia
El sistema debe envolver la escritura de conversaciones en manejo de excepciones. La respuesta al usuario nunca falla por un error de persistencia.

### RNF-AIA-002 — Cache de configuración IA 60 segundos
El sistema debe cachear la configuración del módulo IA durante 60 segundos. La función de invalidación de caché se invoca desde el panel de configuración al guardar cambios.

### RNF-AIA-003 — Configuración IA leída desde repositorio de configuración
El sistema debe leer todas las configuraciones del asistente desde el repositorio de configuración del sistema, módulo "ia". Las semillas son gestionadas por el script de inicialización.

### RNF-AIA-004 — Sin dependencia de embeddings vectoriales
El sistema no debe usar embeddings, vectores ni búsqueda semántica. Todo el contexto se genera mediante parseo regex + consultas estructuradas a tablas Parquet + lógica condicional de secciones.

---

## Funcionalidad 2: Configurar fuentes de conocimiento toggleables (CU-T09 — Gap cerrado Lote 4)

Permite activar o desactivar individualmente las 10 fuentes de datos que alimentan el RAG.

### RF-AIA-010 — Colección de fuentes en repositorio
El sistema debe gestionar las fuentes de datos en una colección del repositorio con los campos: clave (única), nombre, descripción, tabla, tipo (agg/fact) y estado activo (default true). El acceso está restringido a usuarios autenticados. Las 10 fuentes se inicializan por el script de configuración.

### RF-AIA-011 — Cache de fuentes activas con TTL 60s
El sistema debe cachear el conjunto de claves de fuentes activas durante 60 segundos. Si la consulta al repositorio falla o retorna conjunto vacío, el sistema usa todas las fuentes disponibles como fallback.

### RF-AIA-012 — Consultar fuentes disponibles
El sistema debe retornar todas las fuentes ordenadas por clave desde el repositorio. Requiere permiso `asistente_ia:ver`. En caso de error de conexión, retorna lista vacía.

### RF-AIA-013 — Activar/desactivar fuente individualmente
El sistema debe aceptar la clave de una fuente, invertir su estado activo en el repositorio e invalidar inmediatamente la caché de fuentes activas. Retorna la clave y el nuevo estado. Requiere permiso `asistente_ia:ejecutar`. Errores: 400 si falta clave, 404 si no se encuentra, 500 en otras excepciones.

### RF-AIA-014 — Secciones de RAG controladas por fuentes activas
El sistema debe verificar para cada bloque del contexto si la clave correspondiente está en el conjunto de fuentes activas. Si una fuente está desactivada, su sección entera se omite del contexto, incluso si la lógica de tipo de pregunta la requeriría.

### RNF-AIA-005 — Toggle invalida caché inmediatamente
El sistema debe invalidar la caché de fuentes activas al momento de procesar un cambio de estado, forzando la próxima consulta RAG a recargar las fuentes desde el repositorio.

### RNF-AIA-006 — Fallback a todas las fuentes si el repositorio no responde
Si la colección de fuentes no existe o hay error de conexión, el sistema debe usar todas las fuentes disponibles, manteniendo el comportamiento equivalente al diseño sin control de fuentes.

---

## Funcionalidad 3: Consultar historial de conversaciones (Gap Lote 4)

Endpoint e interfaz que muestra el historial persistente de conversaciones del usuario autenticado.

### RF-AIA-015 — Endpoint de historial de conversaciones
El sistema debe retornar las últimas 20 conversaciones del usuario autenticado, filtradas por su identificador, ordenadas por fecha descendente. Usa acceso administrativo al repositorio para leer los registros. Requiere permiso `asistente_ia:ver`.

### RF-AIA-016 — Panel de historial en la interfaz de chat
El sistema debe mostrar las últimas 5 conversaciones más recientes del usuario en el panel lateral del chat, presentando los primeros 60 caracteres de la pregunta inicial como elemento navegable. Al seleccionar una entrada del historial, el sistema debe cargar esa pregunta en el campo de entrada y procesarla automáticamente.

### RNF-AIA-007 — Historial limitado a 20 registros por consulta
El sistema debe retornar como máximo 20 registros en la consulta de historial. No hay paginación. La interfaz solo muestra los primeros 5.

---

## Reglas de negocio

### RN-AIA-001 — Respuesta sin datos si no hay contexto
Si no se puede cargar ninguna sección del contexto (todas las fuentes desactivadas o sin datos), el sistema debe retornar el mensaje fijo "No hay datos disponibles. Asegúrese de que el pipeline ELT se ha ejecutado."

### RN-AIA-002 — Prohibición de alucinación numérica
El prompt del sistema prohíbe al LLM calcular, estimar, redondear, inferir o extrapolar cifras no presentes en el contexto. Solo puede citar valores literales.

### RN-AIA-003 — Respuesta parcial preferida sobre "no sé"
Si la pregunta tiene respuesta parcial en el contexto, el LLM debe responder primero con lo que sí tiene (citando valores literales) e indicar al final qué dato específico no está disponible.

### RN-AIA-004 — Historial volátil + persistente
Existen dos capas de historial: (1) en memoria (TTL 30 min, últimos 20 mensajes) para contexto multi-turn del LLM; (2) persistente en repositorio para consulta del usuario. La capa en memoria no se recupera desde el repositorio al iniciar sesión.

### RN-AIA-005 — Máscara de API keys
Las claves de API se almacenan como campos sensibles en la configuración del sistema y se ocultan en la interfaz. No se muestran en logs ni en respuestas de la API.

### RN-AIA-006 — Colección de conversaciones sin regla de borrado
La colección de conversaciones no tiene regla de borrado. Los registros son inmutables (solo inserción). No hay límite de retención.

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

Proporcionar un asistente conversacional basado en IA que permita a los analistas consultar datos operacionales de aviación (OTP, cancelaciones, retrasos, rutas) en lenguaje natural, con respuestas basadas estrictamente en datos reales provenientes de 10 fuentes estructuradas, historial persistente de conversaciones y control granular de fuentes de conocimiento.

---

## Escenarios

### Camino feliz — Consulta conversacional
1. El Analista accede al chat y ve el sidebar con estado del módulo, proveedor/modelo, preguntas de ejemplo e historial reciente.
2. El Analista escribe "¿Cuál fue la aerolínea más puntual en 2022?" y envía el mensaje.
3. El sistema extrae filtros: sin código IATA (consulta global), año=2022.
4. El sistema construye el contexto con datos de KPIs globales, tendencia mensual y ranking de aerolíneas filtrados por año 2022.
5. El sistema envía el contexto al LLM configurado con las reglas estrictas del prompt.
6. El LLM retorna una respuesta citando el ranking exacto del contexto.
7. El mensaje se persiste en el repositorio y el historial en memoria se actualiza.
8. El Analista puede ver la conversación en el historial reciente del panel lateral.

### Camino feliz — Toggle de fuentes
1. El Administrador accede al chat, expande la sección "Fuentes activas" en el panel lateral.
2. Desmarca "Cancelaciones por código FAA".
3. El sistema actualiza el estado de la fuente en el repositorio e invalida la caché RAG.
4. El Analista pregunta "¿Cuáles son las principales causas de cancelación?".
5. El sistema omite la sección de cancelaciones (fuente desactivada).
6. El LLM responde que no hay datos de cancelaciones disponibles en el contexto actual.

### Manejo de errores
- **Módulo deshabilitado:** El sistema retorna 503 con mensaje "El módulo Asistente IA está deshabilitado. Actívelo en Configuración → IA."
- **Sin API key configurada:** El cliente LLM lanza error de configuración, capturado como 503 con mensaje descriptivo.
- **Error de red en LLM:** Capturado como 503.
- **Error inesperado en LLM:** Capturado como 500 con mensaje genérico.
- **Pregunta vacía o > 800 chars:** Error 400 Bad Request.
- **Fallo en persistencia:** Se registra advertencia en el log; la respuesta al usuario no se interrumpe.
- **Fallo en carga de fuentes activas:** El sistema usa todas las fuentes disponibles como comportamiento degradado funcional.

---

## Criterios de aceptación

- **CU-E18:** Dado que el módulo está activo y hay API key configurada, cuando el Analista envía una pregunta, entonces el sistema devuelve una respuesta del LLM basada en el contexto RAG construido desde las fuentes activas, con citas literales de los datos.
- **CU-T09:** Dado que existen fuentes registradas en el repositorio, cuando el Administrador cambia el estado activo de una fuente, entonces el sistema persiste el cambio, invalida la caché RAG, y las próximas consultas excluyen esa fuente del contexto.
- **Historial (Gap Lote 4):** Dado que el usuario ha realizado conversaciones previas, cuando accede al historial, entonces el sistema muestra las últimas 20 conversaciones del usuario ordenadas por fecha descendente.

---

## Dependencias

- **Seguridad:** Autenticación JWT y autorización con permisos `asistente_ia:ver` (chat, historial, fuentes) y `asistente_ia:ejecutar` (chat, toggle fuentes).
- **Pipeline ELT:** Las 10 tablas de datos (9 agregaciones + hecho enriquecido) en MinIO.
- **Configuración:** Colección `configuracion_sistema` módulo "ia" con proveedor, API keys, modelo y parámetros.
- **PocketBase:** Colecciones `conversaciones_asistente` (historial) y `asistente_fuentes` (fuentes toggleables).
- **LLM externo:** Dependencia de API externa (Groq, Anthropic, Gemini u OpenAI) con conexión a internet. Sin LLM local.

---

## Casos de uso relacionados

- CU-E14 (Proyección predictiva OTP): datos de `agg_otp_aerolinea_mes` usados tanto en predictivo como en RAG.
- CU-O14 (Narrativa IA por gráfico o KPI): generación automática de párrafos ejecutivos para cada indicador visualizado.
- CU-T03, CU-T04, CU-T09 (Configuración general del sistema): el panel de configuración permite editar parámetros IA.

---

## Fuera de alcance

- Embeddings vectoriales, búsqueda semántica o RAG con vectores.
- Análisis de sentimiento, resumen automático o generación de narrativa fuera del contexto de datos.
- Chat multi-idioma (solo español, con soporte limitado de términos en inglés para parseo).
- Subida de documentos o archivos como fuente de conocimiento adicional.
- Memoria a largo plazo (el historial en memoria expira a los 30 min y no se recupera desde el repositorio).
- Edición o borrado de conversaciones del historial (solo inserción).
- Exportación del historial de conversaciones.
- Roles de acceso diferenciados dentro del chat.
- Personalización del prompt del sistema por usuario.
- Streaming de respuestas del LLM (la respuesta se recibe completa).
- Modos de chat predefinidos (analítico, resumen, exploratorio).
