# AeroTrack Analytics — Reglas y Principios del Sistema

Fuente: `.specify/memory/constitution.md` v2.2.0 (ratificada 2026-06-21, última enmienda 2026-06-22).
Los principios se transcriben textualmente agrupados por área temática.

---

## A. Arquitectura de Datos

### I. Separación de capas de almacenamiento

El dato crudo atraviesa dos capas de staging antes de llegar al modelo
analítico: PocketBase (`vuelos_raw`) y `aerotrack-raw` en MinIO
(`vuelos_raw.parquet`, resultado de la extracción). Ningún módulo
analítico lee de ninguna de las dos; todos leen exclusivamente de
`aerotrack-dims` (modelo dimensional final).

### II. Modelo dimensional Kimball

`fact_vuelo` atómica + 11 dimensiones desnormalizadas. Solo las 3
dimensiones opcionales (`dim_retraso_causa`, `dim_cancelacion`,
`dim_desvio`) tienen fila sentinel pk=0 ("Sin retraso"/"Vuelo
normal"/"Sin desvío"). Las 8 dimensiones restantes exigen FK válida; un
vuelo sin match recibe FK=0, detectable como huérfana en
`validar_integridad()`. El pipeline mantiene 10 tablas de agregación
derivadas y recalculables, nunca fuente de verdad.

---

## B. Seguridad y Configuración

### III. RBAC en la capa de aplicación

Toda regla de autorización se implementa como dependencia FastAPI
(`require_permission(modulo, accion)`), con caché de permisos por rol
(TTL 300s). PocketBase almacena los datos de roles pero no impone
restricciones nativas; el cumplimiento ocurre exclusivamente en
`deps.py`.

### IV. Configuración por entorno sin secretos hardcodeados

`os.path.exists("/.dockerenv")` distingue contexto Docker de local. Está
prohibido que cualquier valor sensible (contraseñas, claves JWT,
credenciales de PocketBase, claves de cifrado) tenga un default
hardcodeado en código — debe fallar al arrancar si `.env` no lo provee.
Solo parámetros NO sensibles (timeouts, TTLs de caché, tamaños de
página) pueden tener default hardcodeado como valor de respaldo.

### V. Auditoría inmutable a nivel de aplicación

Todo evento administrativo relevante se registra vía INSERT-only en la
colección `auditoria`; el router expone solo lectura (lista filtrada +
exportación CSV). Esta garantía de inmutabilidad opera a nivel de la API
de la aplicación — no existe Row-Level Security en PocketBase, por lo
que el acceso administrativo directo a PocketBase queda fuera del
alcance de este principio y debe restringirse por infraestructura.

---

## C. Resiliencia y Rendimiento

### VI. Degradación de servicios no críticos

Los subsistemas no críticos (auditoría, narrativa IA, health checks,
lectura de Parquet) nunca propagan una excepción al usuario: retornan
resultado vacío, `None`, o estado degradado. Solo el núcleo del negocio
(autenticación, permisos, datos analíticos solicitados explícitamente)
puede propagar errores. La narrativa IA implementa además un fallback
explícito entre dos proveedores de lenguaje configurables.

### VII. Caché en memoria con TTL explícito

Toda consulta a MinIO o PocketBase con resultado reutilizable se cachea
en memoria con TTL explícito, proporcional a la frecuencia de cambio del
dato: 600s para el modelo dimensional y agregaciones, 300s para permisos
y narrativas IA, 120s para configuración IA, 60s para estadísticas de la
página de login. Ningún caché carece de expiración.

### VIII. Paginación obligatoria en listados

Todo listado retornado al cliente HTTP aplica paginación o límite
explícito (ej. 50 registros en auditoría, 200 por lote en extracción,
máximo 10 pares de mensajes en historial de chat IA). La exportación sin
límite solo se permite en formato descargable (CSV) con autenticación
verificada.

### IX. Pipeline ELT con timeouts y reintentos en múltiples niveles

El DAG declara timeout de 4 horas a nivel de ejecución completa y
timeouts por tarea (extract 2h, load 30min, transform 2h), con política
de reintento automático (2 intentos, espera 5 minutos) y callback de
fallo con logging. Ninguna tarea del pipeline corre sin timeout
definido.

---

## D. Inteligencia Artificial Responsable

### X. Contexto de IA limitado a KPIs agregados

Todo prompt enviado a un modelo de lenguaje contiene exclusivamente KPIs
o métricas pre-calculadas. Está prohibido enviar filas individuales de
`fact_vuelo` o datos de staging a cualquier proveedor de IA, interno o
externo.

### XI. Asistente IA visible solo con permiso verificado

El botón flotante del asistente conversacional (FAB y módulo `/ia`) se
renderiza en `base.html` únicamente cuando el usuario posee el permiso
`asistente_ia.ejecutar`: `{% if 'ejecutar' in user_permissions.get('asistente_ia', []) %}`.
El endpoint `/ia/chat` aplica la misma verificación como segunda línea
de defensa. La interfaz nunca presenta un control al que el usuario no
puede acceder — visibilidad y autorización son coherentes.

---

## E. Frontend y Sistema de Diseño

### XII. Design tokens centralizados

Todo valor visual (color, sombra, radio, duración de animación) se
declara como variable CSS `--at-*` en `aerotrack-theme.css` y se
referencia con `var(--at-*)`. Prohibido hardcodear valores hexadecimales
o RGBA directamente en templates de módulo; una nueva variante de color
requiere un nuevo token, no un valor inline.

### XIII. JavaScript Vanilla sin frameworks

El frontend usa exclusivamente Vanilla JS, expuesto globalmente como
`window.AT` (`aerotrack-ui.js`). Prohibido introducir React, Vue,
Angular o jQuery como dependencia de runtime. La interactividad de
módulo se implementa vía la API `AT.*` o como IIFE local en el bloque de
scripts del template.

### XIV. Librerías de gráficos: versión única y criterio documentado

Chart.js se fija en una sola versión en todos los templates (objetivo:
unificar a 4.4.4, eliminando 4.4.2). Plotly.js 2.27.0 se usa para
visualizaciones que requieren interactividad geoespacial, zoom o
intervalos de confianza; Chart.js para barras, líneas y donuts simples.
Ningún módulo elige librería sin seguir este criterio.

### XV. Serialización segura backend → frontend

Toda transferencia de datos Python → JavaScript usa el filtro `| tojson`.
El filtro `| safe` solo se permite en dos casos: (1) JSON pre-serializado
con `json.dumps()` en el router, cuando llega como string y no como
objeto; (2) SVG generado íntegramente por el servidor sin interpolación
de input de usuario. Todo uso nuevo de `| safe` requiere un comentario
inline que justifique el caso.

### XVI. Dependencias externas como deuda técnica documentada

El sistema depende actualmente de 6 orígenes CDN externos (Google Fonts,
jsdelivr, cdn.plot.ly) sin SRI ni fallback local — esto es una brecha
conocida, no una decisión aceptada permanentemente. Meta de madurez:
antes de una entrega a producción, las librerías de producción se sirven
desde `/static/vendor/` con `integrity` SRI en cada `<script>`/`<link>`;
el CDN directo queda limitado a desarrollo.

### XIX. Estructura de página y vocabulario de componentes UI

Toda página de módulo sigue una estructura de cuatro capas:

1. **`page-heading`**: `<div class="page-heading">` con `<h1>` que contiene
   `<span class="heading-icon {color}">` y un párrafo de subtítulo descriptivo.
2. **Métricas KPI**: cuando el módulo expone indicadores de resumen, se
   presentan en `<div class="kpi-grid">` con tarjetas `.kpi-card.{color}`.
   El color semántico es invariable: `green` = positivo/activo, `amber` =
   advertencia/intermedio, `red` = crítico/inactivo, `blue` = neutro/informacional.
3. **Listados tabulares**: siempre envueltos en la jerarquía
   `at-table-wrapper > at-table-header > at-table-scroll > at-table`.
   El `at-table-header` empareja el título de sección con la acción primaria
   (botón o formulario inline).
4. **Estado vacío**: `<div class="at-card at-empty">` con ícono Bootstrap Icons
   de clase `at-empty-icon`, `<strong>` para el título y `<p>` opcional.

Reglas adicionales de vocabulario: (a) las tarjetas de contenido usan
`at-card` con padding 20px 24px; (b) los estados de entidades usan siempre
`at-badge at-badge-{estado}` con `badge-dot` previo al texto; (c) valores
numéricos, IDs, timestamps y códigos usan `font-family:'JetBrains Mono',monospace`
o la clase `at-code`; (d) los modales de creación siguen Bootstrap con
`modal-body` en flex-column gap:12px; (e) las llamadas asíncronas usan
`fetch` con `credentials:'same-origin'` y body en JSON, nunca `FormData`.

---

## F. Stack Tecnológico

### XVII. Stack tecnológico estandarizado

FastAPI + Jinja2 + Bootstrap 5.3.3, PocketBase 0.22.4, MinIO, Apache
Airflow 2.9.3 con TaskFlow API, PostgreSQL 15 (uso exclusivo: metadatos
de Airflow). **Python 3.12 unificado en todo el stack** (FastAPI y
Airflow) — decisión cerrada por recomendación del profesor del curso por
motivos de compatibilidad. No se permite divergencia de versión de
Python entre los dos entornos del proyecto.

---

## G. Conformidad con Normas de Calidad

### XVIII. Adherencia al modelo de calidad ISO/IEC 25010:2023

El sistema se evalúa y se diseña conforme al modelo de calidad de
producto de la norma ISO/IEC 25010 en su revisión 2023 (9
características). Cada principio de esta constitución existe para
sostener al menos una de estas características; ningún cambio futuro a
esta constitución puede dejar una característica sin principio que la
respalde, sin que quede documentado explícitamente como deuda técnica
aceptada.

Trazabilidad característica → principio:

| Característica ISO/IEC 25010:2023 | Principio(s) que la sostienen |
|---|---|
| Adecuación Funcional | Restricciones de Calidad (spec previa por CU) |
| Eficiencia de Desempeño | VII (caché TTL), VIII (paginación), XVI (meta CDN/SRI) |
| Compatibilidad | XVII (stack y Python unificados), XIV (versión única de librerías de gráficos) |
| Capacidad de Interacción (ex-Usabilidad) | XI (asistente IA con permiso), XII (design tokens), XIII (Vanilla JS consistente), XIX (estructura y vocabulario de componentes) |
| Fiabilidad | VI (degradación de servicios no críticos), IX (timeouts/reintentos del pipeline) |
| Seguridad | III (RBAC), IV (sin secretos hardcodeados), V (auditoría inmutable), X (contexto IA solo KPIs), XV (serialización segura) |
| Mantenibilidad | XII (tokens centralizados), XIV (versión única Chart.js), II (modelo dimensional documentado) |
| Flexibilidad (ex-Portabilidad) | IV (config por entorno), I (separación de capas) |
| Seguridad de Funcionamiento (Safety) | II (validar_integridad() detecta FK huérfanas), X (contexto IA solo KPIs reales), VI (datos analíticos del núcleo nunca degradan silenciosamente) |

---

## Reglas transversales de aplicación universal

Estas reglas aparecen en múltiples spec.md bajo el patrón `RN-XXX-001` y se aplican a todos los módulos:

### RN-TRX-001 — Auditoría obligatoria en toda operación administrativa

Toda operación de creación, edición, eliminación, ejecución, exportación o configuración debe registrarse llamando a `audit.registrar()` en `app/shared/utils/audit.py`. La llamada va dentro de un `try/except` implícito (la función nunca lanza). No se puede omitir la auditoría en operaciones que modifican estado.

Módulos donde aplica: seguridad, pipeline_elt, modelo_dimensional, configuracion, reportes, predictivo, asistente_ia, clientes, socios_api.

### RN-TRX-002 — RBAC obligatorio en todo endpoint no público

Todo endpoint FastAPI que devuelva datos o ejecute operaciones debe invocar `require_permission(modulo, accion)` como primera instrucción. El único endpoint sin verificación de permisos es `GET /auth/login` y `POST /auth/login`.

### RN-TRX-003 — Serialización segura de datos Python → JavaScript

Toda variable Python que se pase a un template Jinja2 para uso en JavaScript debe usar `| tojson`. El uso de `| safe` directo sin `json.dumps()` previo está prohibido salvo los dos casos documentados en el Principio XV.

### RN-TRX-004 — Los datos analíticos se leen exclusivamente de aerotrack-dims

Ningún módulo de análisis (dashboard, puntualidad, rutas, cancelaciones, reportes, predictivo, asistente IA) lee de PocketBase ni de `aerotrack-raw`. Toda consulta usa `read_parquet()`, `load_agg()` o `load_enriched_fact()` sobre el bucket `aerotrack-dims`.

### RN-TRX-005 — Paginación en todo listado HTML

Todo endpoint que retorna una lista de registros HTML aplica `PAGE_SIZE = 50` (definido en `app/shared/templates.py:44`). Los endpoints JSON para APIs públicas o exportaciones CSV quedan exentos de este límite con autenticación verificada.
