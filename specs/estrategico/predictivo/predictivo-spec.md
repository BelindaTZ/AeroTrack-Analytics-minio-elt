# Especificación Estratégica — Predictivo

**Módulo:** Predictivo
**Prefijo:** PRE
**Código fuente:** `app/predictivo/`
**Casos de uso cubiertos:** CU-E14 (Generar proyección de riesgo operacional), CU-E15 (Analizar patrones estacionales), CU-E16 (Ver recomendaciones automáticas priorizadas), CU-E17 (Exportar informe ejecutivo IA), CU-E20 (Detectar anomalías históricas en indicadores de puntualidad y cancelación), CU-E21 (Ver índice de riesgo predictivo por aerolínea), CU-E22 (Simular escenarios "qué pasaría si" sobre la proyección de riesgo operacional)
**Actor:** Analista de Datos

---

## Funcionalidad 1: Generar proyección de riesgo OTP con Holt-Winters (CU-E14, CU-E15, CU-E20, CU-E21)

Dashboard predictivo unificado en `GET /predictivo` que proyecta el OTP mensual mediante Holt-Winters (`statsmodels.tsa.holtwinters.ExponentialSmoothing`), analiza estacionalidad en matriz día×mes, detecta anomalías por Z-score, calcula ranking de riesgo compuesto y genera recomendaciones priorizadas. Implementado en `app/predictivo/proyeccion_riesgo.py`.

### RF-PRE-001 — Proyectar OTP con Holt-Winters
`POST /predictivo/proyeccion` recibe filtros `airline`, `year`, `horizonte` (form-urlencoded). Carga la serie mensual de OTP desde `agg_otp_aerolinea_mes`. Ajusta `ExponentialSmoothing` con `trend="add"` si hay ≥6 puntos históricos (sin tendencia si hay menos), `seasonal=None` siempre. Retorna JSON con `historico`, `proyeccion`, `ic_sup`, `ic_inf` (IC 95% = 1.96 × max(resid_std, 0.5)), `meses_hist`, `meses_proy`, `metodo`, `n_meses`, `ajustado`, `precision_estimada`. Fallback a media móvil 6 meses si Holt-Winters falla. Valores clampados a [0, 100].

### RF-PRE-002 — Mostrar dashboard predictivo completo
`GET /predictivo` renderiza `predictivo/index.html` con: selector de aerolínea (dropdown con todas), año, métrica de mapa de calor (otp/cancelacion/retraso), horizonte de proyección (1–N, configurable vía `horizonte_prediccion_max` en `configuracion_sistema` módulo sistema, default 6). El template recibe todos los datos precargados: `aerolinas`, `years`, `heatmap`, `proyeccion`, `recomendaciones`, `anomalias`, `ranking_riesgo`.

### RF-PRE-003 — Analizar patrones estacionales (CU-E15)
`GET /predictivo/estacionalidad` retorna JSON con matriz 7×12 (día de semana × mes) con valores de la métrica seleccionada (otp/cancelacion/retraso). Implementado en `_heatmap_data()` que carga desde la enriched fact table. Cacheado 10 minutos en `_heatmap_cache` TTL 600s. El frontend renderiza una tabla HTML con colores condicionales: OTP ≥88 verde, ≥80 verde claro, ≥70 ámbar, <70 rojo (para cancelación y retraso se usan umbrales distintos).

### RF-PRE-004 — Detectar anomalías por Z-score (CU-E20)
`GET /predictivo/anomalias` retorna anomalías detectadas vía `_detectar_anomalias()`. Para cada mes-aerolínea, calcula el Z-score del OTP contra la media y desviación histórica del mismo mes calendario. Umbral: |z| ≥ 1.5. Retorna hasta 3 anomalías negativas (peor OTP de lo esperado) y 2 positivas (mejor OTP), cada una con sparkline SVG inline generado por `_sparkline_svg()`.

### RF-PRE-005 — Calcular índice de riesgo compuesto por aerolínea (CU-E21)
`GET /predictivo/ranking_riesgo` retorna ranking de aerolíneas con score compuesto = 0.6 × OTP_score + 0.4 × estabilidad_score. OTP_score normaliza OTP medio a [0,100]; estabilidad_score normaliza desviación estándar (invertida: menor std = mayor score). Clasificación: ≥70 "estable", ≥50 "riesgo", <50 "crítico". Tendencia calculada comparando último tercio vs primer tercio del período: diff > 1.5 → "up", diff < −1.5 → "down", else → "stable".

### RF-PRE-006 — Generar recomendaciones priorizadas automáticas (CU-E16)
El dashboard incluye recomendaciones generadas por `_generar_recomendaciones()` con 3 tipos: (1) nivel OTP global — "alta" si <75%, "media" si <82%, "baja" si ≥82%; (2) meses más débiles por OTP — prioridad "media"; (3) variabilidad — "alta" si desv. estándar > 8, "baja" si ≤ 8. Ordenadas por prioridad (alta → media → baja). Cada recomendación incluye: prioridad, icono, color, título, descripción, justificación, impacto estimado, acción directa.

### RNF-PRE-001 — Proyección cacheable por request
Cada `POST /predictivo/proyeccion` computa Holt-Winters en tiempo real (sin cache). El modelo se re-entrena con cada llamada usando `fit(optimized=True, use_brute=False)`. El tiempo de cómputo es < 200ms para series típicas (< 120 meses).

### RNF-PRE-002 — Mapa de calor cacheado 10 minutos
`_heatmap_data` se cachea en `_heatmap_cache` con TTL 600s para evitar recarga de la enriched fact table en cada cambio de filtro.

### RNF-PRE-003 — Sin dependencia de Prophet
A diferencia de la especificación original, el módulo usa `statsmodels` (Holt-Winters) en lugar de Prophet. No hay instalación ni dependencia de Prophet en el proyecto.

---

## Funcionalidad 2: Simular escenarios what-if sobre la proyección (CU-E22)

Simulador integrado en el dashboard que permite al analista explorar el impacto de cambios operacionales (buffer de conexión, reducción de carga) sobre la proyección OTP. Implementado como endpoint backend `POST /predictivo/whatif` en `proyeccion_riesgo.py:540`. Gap CU-E22 cerrado en Lote 4.

### RF-PRE-007 — Endpoint backend de simulación what-if
`POST /predictivo/whatif` acepta JSON: `{aerolinea, anio, horizonte, buffer_minutos (0-30, step 5), reduccion_carga (0-30, step 5)}`. Internamente ejecuta `_simular_whatif()` que: (1) corre `_proyectar_otp()` con Holt-Winters real sobre la serie OTP filtrada; (2) calcula delta = (buffer_min/5) × 0.7 + (reducción/10) × 0.3 usando factores empíricos; (3) aplica delta a proyección, ic_sup e ic_inf (cap 100); (4) retorna la proyección ajustada + metadato `whatif.delta`. Permiso requerido: `predictivo:ver`.

### RF-PRE-008 — UI de simulación en frontend
Dos sliders tipo range (min 0, max 30, step 5): "Buffer de conexión" (`sl-buffer`) y "Reducción de carga" (`sl-vol`). Cada cambio envía petición POST a `/predictivo/whatif` con filtros actuales del dashboard (aerolínea, año, horizonte). La respuesta se dibuja como línea púrpura punteada en el gráfico Chart.js con etiqueta "Escenario +X.Xpp". Panel de resultado muestra el delta calculado. Botón "Resetear" vuelve ambos sliders a 0 y elimina la línea what-if del gráfico.

### RNF-PRE-004 — What-if sin persistencia
La simulación what-if es volátil (no se persiste). No crea registros en base de datos ni afecta la proyección base del dashboard. Solo modifica la visualización en sesión actual.

---

## Funcionalidad 3: Exportar informe ejecutivo PDF (CU-E17)

Genera un informe PDF con WeasyPrint que incluye 4 secciones: resumen ejecutivo con KPIs, proyección de riesgo OTP con gráfico SVG y tabla, mapa de calor estacional SVG mini, y recomendaciones priorizadas. Implementado en `app/predictivo/informe_ejecutivo.py`.

### RF-PRE-009 — Generar PDF con WeasyPrint
`POST /predictivo/informe` recibe form-data con filtros `airline`, `year`, `horizonte`. Permiso requerido: `predictivo:exportar` (`_perm_export`). Genera HTML con gráficos SVG inline y CSS embebido, lo convierte a PDF vía WeasyPrint, sube a MinIO bucket `aerotrack-exports` con nombre `reportes/informe_ejecutivo_{YYYYMMDD_HHMMSS}.pdf`, retorna URL firmada (1 hora). Si la subida falla, retorna error 500. Auditoría: registra acción "exportar" en módulo "predictivo", recurso_tipo "informe_ejecutivo".

### RF-PRE-010 — Contenido del PDF: 4 secciones
(1) Resumen Ejecutivo: marca "AeroTrack Analytics", 4 KPIs (OTP promedio histórico, meses de historial, conteo de recomendaciones, alcance), advertencia si <12 meses. (2) Proyección de Riesgo OTP: gráfico de línea SVG + tabla con mes, OTP proyectado, intervalo 95%. (3) Mapa de Calor Estacional: SVG mini heatmap con días×meses coloreados por umbrales. (4) Recomendaciones Priorizadas: tarjetas con badge de prioridad, título, descripción, justificación.

### RNF-PRE-005 — Sin WeasyPrint no hay PDF
La generación de PDF depende de WeasyPrint. Si `weasyprint` no está instalado, el endpoint retorna error 500. No hay fallback degradado (a diferencia del módulo Reportes). Este gap está documentado.

### RNF-PRE-006 — URL firmada con expiración de 1 hora
La URL de descarga se genera con `presigned_get_object` y expira en 1 hora. El archivo en MinIO no tiene lifecycle configurado (a diferencia del bucket de reportes).

---

## Reglas de negocio

### RN-PRE-001 — Mínimo 3 meses de historial para proyectar
Si el DataFrame OTP tiene menos de 3 filas, `_proyectar_otp()` retorna error "Datos insuficientes". El endpoint `/predictivo/proyeccion` y la página principal validan esta condición.

### RN-PRE-002 — Sin tendencia si < 6 períodos
Holt-Winters se configura con `trend="add"` solo si hay ≥6 puntos históricos. Con menos datos, se usa sin tendencia para evitar sobreajuste.

### RN-PRE-003 — IC mínimo 0.98 pp
El intervalo de confianza al 95% se calcula como 1.96 × max(resid_std, 0.5). El mínimo es 0.98 pp, evitando intervalos irreales con residuos muy pequeños.

### RN-PRE-004 — Proyección clampada a [0, 100]
Todos los valores de proyección e intervalos se clampan al rango [0, 100] mediante `min(100, max(0, v))` para evitar OTP negativos o superiores al 100%.

### RN-PRE-005 — Delta what-if solo aplica a proyección, no a históricos
El escenario what-if modifica únicamente los valores proyectados (proyección, IC sup, IC inf). Los datos históricos permanecen inalterados. No se re-entrena el modelo con datos históricos ajustados.

### RN-PRE-006 — Factores what-if fijos
Los factores de mejora son constantes empíricas: 0.7 pp por cada 5 min de buffer adicional, 0.3 pp por cada 10% de reducción de carga. No son configurables desde la UI.

---

## Entradas y salidas

| FUNCIÓN / ENDPOINT | ENTRADAS | SALIDAS |
|---|---|---|
| GET /predictivo | Cookie JWT, query: airline, year, metric, horizonte | HTML con dashboard completo: mapa calor, proyección Chart.js, recomendaciones, anomalías, ranking riesgo, what-if |
| POST /predictivo/proyeccion | Cookie JWT, form: airline, year, horizonte | JSON: {historico[], proyeccion[], ic_sup[], ic_inf[], meses_hist[], meses_proy[], metodo, n_meses, ajustado[], precision_estimada, advertencia?} |
| GET /predictivo/estacionalidad | Cookie JWT, query: airline, metric | JSON: {rows[], cols[], matrix[][], metric} |
| GET /predictivo/recomendaciones | Cookie JWT, query: airline, year | JSON: [{prioridad, icono, color, titulo, descripcion, modulo, justificacion, impacto_estimado, accion_directa, revisado}] |
| GET /predictivo/anomalias | Cookie JWT, query: airline, year | JSON: [{tipo, airline, mes, año, valor_esperado, valor_real, z_score, sparkline, descripcion}] |
| GET /predictivo/ranking_riesgo | Cookie JWT, query: year | JSON: [{airline, otp, std, score, nivel, tendencia, tendencia_delta, n_meses}] |
| POST /predictivo/whatif | Cookie JWT, JSON: {aerolinea, anio, horizonte, buffer_minutos, reduccion_carga} | JSON: {proyeccion[], ic_sup[], ic_inf[], meses_hist[], meses_proy[], whatif:{delta, buffer_minutos, reduccion_carga}} |
| POST /predictivo/informe | Cookie JWT, form: airline, year, horizonte | JSON: {url: "presigned MinIO URL"} |

---

## Historias de usuario

- **HU-PRE-01:** Como Analista de Datos quiero ver la proyección OTP a futuro con intervalo de confianza para anticipar riesgos operacionales.
- **HU-PRE-02:** Como Analista de Datos quiero analizar la estacionalidad del OTP por día de semana y mes para identificar patrones periódicos.
- **HU-PRE-03:** Como Analista de Datos quiero que el sistema me recomiende acciones priorizadas basadas en los datos para saber dónde enfocar esfuerzos.
- **HU-PRE-04:** Como Analista de Datos quiero detectar automáticamente meses con OTP anómalo para investigar causas subyacentes.
- **HU-PRE-05:** Como Analista de Datos quiero ver un ranking de aerolíneas por riesgo operacional para priorizar intervenciones.
- **HU-PRE-06:** Como Analista de Datos quiero simular el impacto de cambios operacionales (buffer, reducción de carga) en la proyección OTP para evaluar decisiones antes de implementarlas.
- **HU-PRE-07:** Como Analista de Datos quiero exportar un informe PDF ejecutivo con los análisis predictivos para compartir con la dirección.

---

## Objetivo

Proporcionar capacidades de análisis predictivo sobre el desempeño operacional (OTP), permitiendo al Analista de Datos proyectar riesgos futuros, simular escenarios correctivos, detectar anomalías históricas y generar reportes ejecutivos, todo basado en el modelo Holt-Winters sobre datos históricos agregados por aerolínea y mes.

---

## Escenarios

### Camino feliz — Dashboard completo
1. El Analista accede a `GET /predictivo`. El sistema carga datos desde `agg_otp_aerolinea_mes`.
2. La página renderiza el mapa de calor estacional, gráfico Chart.js con proyección OTP + IC, tarjetas de recomendaciones priorizadas, lista de anomalías con sparklines, y tabla de ranking de riesgo.
3. El Analista cambia el filtro de aerolínea; la página se recarga con nuevos datos.
4. El Analista cambia el horizonte de proyección; `fetchProyeccion()` envía POST a `/predictivo/proyeccion` y actualiza el gráfico vía AJAX sin recargar la página.
5. Las tarjetas de recomendaciones se muestran ordenadas por prioridad (alta → media → baja).

### Camino feliz — Simulación what-if
1. El Analista ajusta el slider "Buffer de conexión" a 15 min y "Reducción de carga" a 10%.
2. La función `updateWhatIf()` envía POST a `/predictivo/whatif` con los filtros actuales y parámetros de simulación.
3. El backend ejecuta `_simular_whatif()`: corre Holt-Winters, calcula delta = (15/5)×0.7 + (10/10)×0.3 = 2.4 pp, ajusta proyección e IC.
4. El frontend dibuja una nueva línea púrpura punteada en el chart con etiqueta "Escenario +2.4pp".
5. El panel de resultado muestra "+2.4pp OTP proyectado".

### Camino feliz — Exportación PDF
1. El Analista hace clic en "Generar Informe Ejecutivo".
2. Aparece el modal Briefing con 4 tarjetas animadas (OTP promedio, tendencia, mes crítico, próxima proyección).
3. El Analista hace clic en "Descargar PDF".
4. `POST /predictivo/informe` genera HTML con SVG inline, WeasyPrint lo convierte a PDF, se sube a MinIO.
5. Se retorna URL firmada y el PDF se abre en nueva pestaña.

### Manejo de errores
- **Datos insuficientes (< 3 meses):** El dashboard muestra mensaje "Sin datos suficientes. Selecciona una aerolínea con al menos 3 meses de historial." en lugar del gráfico.
- **Error en Holt-Winters (convergencia):** Fallback a media móvil 6 meses. Se registra advertencia en metadatos.
- **Error en MinIO (informe):** Se retorna JSON con error 500 y mensaje descriptivo.
- **Error en what-if (datos vacíos):** Se retorna JSON con error 400 "Datos insuficientes.".
- **Error en heatmap/estacionalidad (tabla vacía):** Se retorna JSON con matriz vacía (no bloquea).

---

## Criterios de aceptación

- **CU-E14:** Dado que existen ≥3 meses de datos OTP en `agg_otp_aerolinea_mes`, cuando el Analista solicita una proyección, entonces el sistema devuelve una serie proyectada con Holt-Winters, intervalos de confianza al 95%, y metadatos del modelo.
- **CU-E15:** Dado que la enriched fact table tiene datos, cuando el Analista selecciona una métrica en el dashboard, entonces el mapa de calor muestra la matriz 7×12 con colores condicionales.
- **CU-E16:** Dado que hay datos OTP, cuando se carga el dashboard, entonces el sistema muestra recomendaciones ordenadas por prioridad con título, descripción, justificación e impacto estimado.
- **CU-E17:** Dado que WeasyPrint está instalado, cuando el Analista genera un informe, entonces el sistema produce un PDF con 4 secciones (resumen, proyección, heatmap, recomendaciones), lo sube a MinIO y retorna URL firmada.
- **CU-E20:** Dado que hay ≥2 años de datos históricos, cuando se cargan anomalías, entonces el sistema retorna hasta 5 eventos con |z| ≥ 1.5, incluyendo sparkline SVG y descripción.
- **CU-E21:** Dado que hay datos de múltiples aerolíneas, cuando se carga el ranking, entonces el sistema retorna lista ordenada por score compuesto con clasificación (estable/riesgo/crítico) y tendencia.
- **CU-E22:** Dado que hay datos OTP suficientes, cuando el Analista ajusta los sliders what-if, entonces el sistema retorna una proyección ajustada aplicando el delta calculado a los valores proyectados, sin modificar los históricos.

---

## Dependencias

- **Seguridad:** Autenticación JWT y autorización con permisos `predictivo:ver` (dashboard, proyección, estacionalidad, recomendaciones, anomalías, ranking, what-if) y `predictivo:exportar` (informe PDF).
- **Pipeline ELT:** Tablas de agregación `agg_otp_aerolinea_mes`, `agg_cancelaciones_causa`, `agg_cancelaciones_aerolinea_causa`, `agg_cancelaciones_ruta`, `agg_causas_retraso_mes`, `agg_rutas_eficiencia`, `agg_desvios_ruta`, `agg_otp_dia_semana`, `agg_otp_aerolinea_dia_semana` y enriched fact table en MinIO.
- **Statsmodels:** Librería `statsmodels.tsa.holtwinters.ExponentialSmoothing` para la proyección Holt-Winters.
- **WeasyPrint:** Librería Python para conversión HTML+CSS → PDF (requisito exclusivo de informe ejecutivo, no hay fallback).
- **MinIO:** Bucket `aerotrack-exports` para almacenamiento de PDFs de informe ejecutivo.
- **Configuración:** `configuracion_sistema` módulo `sistema`, clave `horizonte_prediccion_max` (default 6).
- **Chart.js (CDN):** Librería frontend para gráfico de proyección en navegador.

---

## Casos de uso relacionados

- CU-E01, CU-E02 (Dashboard — KPIs globales, alertas): el predictivo usa las mismas tablas agregadas.
- CU-E11 (Reportes — PDF multi-sección): patrón de exportación similar pero con alcance predictivo.
- CU-E22 (Simular escenarios): extensión directa de CU-E14.

---

## Fuera de alcance

- Uso de Prophet (se usa Holt-Winters de statsmodels).
- Re-entrenamiento del modelo con escenarios what-if (el delta se aplica post-proyección).
- Persistencia de simulaciones what-if en base de datos.
- Programación de exportaciones automáticas de informes.
- Envío de informes por email.
- Personalización de factores what-if (0.7 y 0.3 son constantes).
- Comparación multi-aerolínea en un mismo informe PDF (el informe aplica a una aerolínea o todas).
- Notificaciones push cuando OTP proyectado cruza umbrales.
- Exportación del ranking de riesgo a PDF independiente.
- Análisis de sensibilidad avanzado (monte carlo, múltiples escenarios simultáneos).
