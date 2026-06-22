<!--
SYNC IMPACT REPORT
==================
Generated: 2026-06-21
Skill: speckit-constitution

Version change: 2.0.0 → 2.1.0
Bump type: MINOR — Principio XVII reescrito: unificación de Python a 3.12 en todo
           el stack (FastAPI + Airflow), decisión cerrada por recomendación del
           profesor del curso. Tabla ISO actualizada al modelo 2023 (9 características,
           añadiendo Capacidad de Interacción y Seguridad de Funcionamiento).

Modified principles:
  XVII. Stack tecnológico estandarizado — texto anterior especificaba Python 3.13
        para FastAPI / Python 3.12 para Airflow como "intencional"; nuevo texto
        establece Python 3.12 unificado como decisión cerrada.

Added: Sección G reordenada antes de Gobernanza (corrección de orden lógico).
       Tabla ISO actualizada a revisión 2023 (9 características).

Removed: N/A

Templates reviewed:
  ✅ .specify/templates/plan-template.md   — "Constitution Check" section genérica;
     sin referencias hardcoded a principios — sin cambios requeridos.
  ✅ .specify/templates/spec-template.md  — sin referencias a principios
     específicos; estructura genérica — sin cambios requeridos.
  ✅ .specify/templates/tasks-template.md — sin referencias a principios
     específicos; categorías genéricas — sin cambios requeridos.

Deferred items: NINGUNO.

Follow-up TODOs (heredados de v2.0.0, sin cambio de estado):
  1. [SEGURIDAD] Eliminar defaults hardcodeados en app/config.py (líneas 11, 12, 28)
     y dags/config.py — deben lanzar excepción al arrancar si .env no los provee. Ver Principio IV.
  2. [SEGURIDAD] Confirmar Fernet key hardcodeada en docker-compose.yml línea 136. Ver Principio IV.
  3. [FRONTEND] Unificar Chart.js a versión 4.4.4. Ver Principio XIV.
  4. [FRONTEND] Documentar cada uso de | safe con comentario inline. Ver Principio XV.
  5. [INFRAESTRUCTURA] Migrar librerías CDN a /static/vendor/ con SRI antes de producción. Ver Principio XVI.
-->

# AeroTrack Analytics — Constitución del Proyecto

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

## D. Inteligencia Artificial Responsable

### X. Contexto de IA limitado a KPIs agregados

Todo prompt enviado a un modelo de lenguaje contiene exclusivamente KPIs
o métricas pre-calculadas. Está prohibido enviar filas individuales de
`fact_vuelo` o datos de staging a cualquier proveedor de IA, interno o
externo.

### XI. Asistente IA global con verificación de permiso en backend

El asistente conversacional está disponible visualmente en todas las
páginas autenticadas para facilitar el descubrimiento, pero el acceso
real se decide en el endpoint `/ia/chat` mediante `asistente_ia.ejecutar`,
que responde 403 si el usuario no tiene el permiso. La visibilidad del
botón no es una garantía de autorización; la garantía vive en el
backend.

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

## F. Stack Tecnológico

### XVII. Stack tecnológico estandarizado

FastAPI + Jinja2 + Bootstrap 5.3.3, PocketBase 0.22.4, MinIO, Apache
Airflow 2.9.3 con TaskFlow API, PostgreSQL 15 (uso exclusivo: metadatos
de Airflow). **Python 3.12 unificado en todo el stack** (FastAPI y
Airflow) — decisión cerrada por recomendación del profesor del curso por
motivos de compatibilidad. No se permite divergencia de versión de
Python entre los dos entornos del proyecto.

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
| Capacidad de Interacción (ex-Usabilidad) | XII (design tokens), XIII (Vanilla JS consistente), XI (asistente IA global) |
| Fiabilidad | VI (degradación de servicios no críticos), IX (timeouts/reintentos del pipeline) |
| Seguridad | III (RBAC), IV (sin secretos hardcodeados), V (auditoría inmutable), X (contexto IA solo KPIs), XV (serialización segura) |
| Mantenibilidad | XII (tokens centralizados), XIV (versión única Chart.js), II (modelo dimensional documentado) |
| Flexibilidad (ex-Portabilidad) | IV (config por entorno), I (separación de capas) |
| Seguridad de Funcionamiento (Safety) | II (`validar_integridad()` detecta FK huérfanas antes de que lleguen al cliente), X (contexto IA solo KPIs reales, sin alucinación), VI (datos analíticos del núcleo nunca degradan silenciosamente) — protege contra que AeroTrack entregue inteligencia operacional incorrecta a una aerolínea cliente, lo cual podría derivar en decisiones reales sobre tripulación, rutas o capacidad con impacto en la seguridad operacional |

## Restricciones de Calidad

- Todo caso de uso del catálogo de 53 CUs debe tener especificación
  formal antes de implementarse.
- Toda funcionalidad nueva declara explícitamente sus dependencias con
  otros módulos y su criterio de aceptación verificable.
- Las narrativas IA se presentan siempre en un modal por gráfico/KPI,
  nunca como bloque a nivel de módulo completo.

## Flujo de Desarrollo

`speckit-constitution` (este archivo) → `speckit-specify` →
`speckit-clarify` → `speckit-plan` → `speckit-tasks` →
`speckit-implement` → `speckit-checklist`/`speckit-analyze`.
Especificaciones organizadas en `specs/` por nivel organizacional
(`estrategico/`, `tactico/`, `operativo/`), replicando el mapa OE/OT/OO.

## Gobernanza

Esta constitución prevalece sobre cualquier práctica informal. Toda
modificación se documenta con justificación y fecha de enmienda.
Mientras `.kiro/` esté activo, `steering/tech.md` y `steering/structure.md`
deben reflejar la misma versión.

**Versión**: 2.1.0 | **Ratificada**: 2026-06-21 | **Última enmienda**: 2026-06-21
