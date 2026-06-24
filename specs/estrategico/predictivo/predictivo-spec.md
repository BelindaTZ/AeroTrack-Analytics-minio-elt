# Especificación Estratégica — Predictivo

**Módulo:** Predictivo
**Prefijo:** PRE
**Código fuente:** `app/predictivo/`
**Casos de uso cubiertos:** CU-E14 (Generar proyección de riesgo operacional), CU-E15 (Analizar patrones estacionales), CU-E16 (Ver recomendaciones automáticas priorizadas), CU-E17 (Exportar informe ejecutivo IA), CU-E20 (Detectar anomalías históricas en indicadores de puntualidad y cancelación), CU-E21 (Ver índice de riesgo predictivo por aerolínea), CU-E22 (Simular escenarios "qué pasaría si" sobre la proyección de riesgo operacional)
**Actor:** Analista de Datos/Administrador

---

## Funcionalidad 1: Generar proyección de riesgo OTP con Holt-Winters (CU-E14, CU-E15, CU-E20, CU-E21)

Dashboard predictivo unificado que proyecta el OTP mensual mediante Holt-Winters, analiza estacionalidad en matriz día×mes, detecta anomalías por Z-score, calcula ranking de riesgo compuesto y genera recomendaciones priorizadas.

### RF-PRE-001 — Proyectar OTP con Holt-Winters
El sistema debe proyectar la serie mensual de OTP aplicando el modelo Holt-Winters. Configura tendencia aditiva si hay 6 o más puntos históricos (sin tendencia si hay menos), sin componente estacional. Retorna histórico, proyección, intervalos de confianza al 95%, metadatos del modelo y advertencias. Si el modelo falla, aplica media móvil de 6 meses como fallback. Los valores proyectados se limitan al rango [0, 100].

### RF-PRE-002 — Mostrar dashboard predictivo completo
El sistema debe mostrar el dashboard con: selector de aerolínea, año, métrica del mapa de calor (otp/cancelacion/retraso) y horizonte de proyección (1 a N meses, configurable desde la configuración del sistema, default 6). El dashboard incluye precargados: lista de aerolíneas, años disponibles, mapa de calor, proyección, recomendaciones, anomalías y ranking de riesgo.

### RF-PRE-003 — Analizar patrones estacionales (CU-E15)
El sistema debe retornar una matriz de 7 filas × 12 columnas (día de semana × mes) con los valores de la métrica seleccionada. El mapa de calor se cachea 10 minutos. La interfaz colorea cada celda según umbrales: OTP ≥ 88 verde oscuro, ≥ 80 verde claro, ≥ 70 ámbar, < 70 rojo (con umbrales distintos para cancelación y retraso).

### RF-PRE-004 — Detectar anomalías por Z-score (CU-E20)
El sistema debe detectar anomalías calculando el Z-score del OTP de cada mes-aerolínea contra la media y desviación histórica del mismo mes calendario. Umbral: |z| ≥ 1.5. Retorna hasta 3 anomalías negativas (peor OTP de lo esperado) y 2 positivas (mejor OTP), cada una con un gráfico sparkline SVG inline y descripción.

### RF-PRE-005 — Calcular índice de riesgo compuesto por aerolínea (CU-E21)
El sistema debe calcular un score compuesto por aerolínea como: 0.6 × OTP_score + 0.4 × estabilidad_score. El OTP_score normaliza el OTP medio a [0, 100]; el estabilidad_score normaliza la desviación estándar invertida (menor variabilidad = mayor score). Clasificación: ≥ 70 "estable", ≥ 50 "riesgo", < 50 "crítico". La tendencia se calcula comparando el último tercio vs el primer tercio del período: diff > 1.5 → "up", diff < -1.5 → "down", else → "stable".

### RF-PRE-006 — Generar recomendaciones priorizadas automáticas (CU-E16)
El sistema debe generar recomendaciones con 3 tipos: (1) nivel OTP global — prioridad "alta" si < 75%, "media" si < 82%, "baja" si ≥ 82%; (2) meses más débiles por OTP — prioridad "media"; (3) variabilidad — prioridad "alta" si desviación estándar > 8, "baja" si ≤ 8. Las recomendaciones se ordenan por prioridad (alta → media → baja). Cada una incluye: prioridad, icono, color, título, descripción, justificación, impacto estimado y acción directa.

### RNF-PRE-001 — Proyección calculada en tiempo real
El sistema debe calcular el modelo Holt-Winters en tiempo real por cada solicitud de proyección, sin caché. El tiempo de cómputo debe ser menor a 200ms para series típicas (menos de 120 meses).

### RNF-PRE-002 — Mapa de calor cacheado 10 minutos
El sistema debe cachear el mapa de calor durante 10 minutos para evitar recargas del hecho enriquecido en cada cambio de filtro.

### RNF-PRE-003 — Sin dependencia de Prophet
El módulo usa Holt-Winters de statsmodels, no Prophet. No hay instalación ni dependencia de Prophet en el proyecto.

---

## Funcionalidad 2: Simular escenarios what-if sobre la proyección (CU-E22)

Simulador integrado en el dashboard que permite al analista explorar el impacto de cambios operacionales sobre la proyección OTP.

### RF-PRE-007 — Endpoint backend de simulación what-if
El sistema debe aceptar parámetros de simulación: aerolínea, año, horizonte, buffer de conexión en minutos (0-30, paso 5) y reducción de carga en porcentaje (0-30, paso 5). Internamente ejecuta la proyección Holt-Winters, calcula el delta de mejora con factores empíricos, aplica el delta a la proyección e intervalos de confianza (máximo 100%), y retorna la proyección ajustada junto con los metadatos del escenario. Requiere permiso `predictivo:ver`.

### RF-PRE-008 — UI de simulación en frontend
El sistema debe mostrar dos controles deslizantes (rango 0-30, paso 5): "Buffer de conexión" y "Reducción de carga". Cada cambio debe enviar la solicitud de simulación al backend con los filtros actuales. La respuesta se dibuja como línea diferenciada en el gráfico con etiqueta indicando el delta calculado (ej. "Escenario +2.4pp"). El panel de resultado muestra el delta. Un botón "Resetear" vuelve ambos controles a 0 y elimina la línea del escenario.

### RNF-PRE-004 — What-if sin persistencia
La simulación es volátil. No crea registros en base de datos ni afecta la proyección base. Solo modifica la visualización en la sesión actual.

---

## Funcionalidad 3: Exportar informe ejecutivo PDF (CU-E17)

Genera un informe PDF con 4 secciones: resumen ejecutivo con KPIs, proyección de riesgo OTP, mapa de calor estacional y recomendaciones priorizadas.

### RF-PRE-009 — Generar PDF con la librería de renderizado
El sistema debe generar el informe recibiendo aerolínea, año y horizonte. Requiere permiso `predictivo:exportar`. Genera HTML con gráficos SVG inline, lo convierte a PDF, sube al repositorio de almacenamiento y retorna URL firmada (1 hora). Si la subida falla, retorna error 500. Registra en auditoría la acción de exportación.

### RF-PRE-010 — Contenido del PDF: 4 secciones
El sistema debe incluir en el informe: (1) Resumen Ejecutivo: 4 KPIs (OTP promedio histórico, meses de historial, conteo de recomendaciones, alcance), con advertencia si hay menos de 12 meses. (2) Proyección de Riesgo OTP: gráfico de línea SVG y tabla con mes, OTP proyectado e intervalo al 95%. (3) Mapa de Calor Estacional: SVG mini con días×meses coloreados por umbrales. (4) Recomendaciones Priorizadas: tarjetas con indicador de prioridad, título, descripción y justificación.

### RNF-PRE-005 — Sin librería de PDF no hay informe
La generación del informe depende de la librería de conversión HTML→PDF. Si no está instalada, el endpoint retorna error 500. No hay fallback degradado.

### RNF-PRE-006 — URL firmada con expiración de 1 hora
La URL de descarga se genera con expiración de 1 hora. El archivo en el repositorio no tiene ciclo de vida configurado.

---

## Reglas de negocio

### RN-PRE-001 — Mínimo 3 meses de historial para proyectar
Si el conjunto de datos OTP tiene menos de 3 registros, el sistema retorna error "Datos insuficientes". El dashboard y el endpoint de proyección validan esta condición.

### RN-PRE-002 — Sin tendencia si < 6 períodos
El modelo se configura con tendencia aditiva solo si hay 6 o más puntos históricos. Con menos datos se usa sin tendencia para evitar sobreajuste.

### RN-PRE-003 — IC mínimo 0.98 pp
El intervalo de confianza al 95% se calcula como 1.96 × max(residuo_std, 0.5). El mínimo resultante es 0.98 pp, evitando intervalos irreales con residuos muy pequeños.

### RN-PRE-004 — Proyección clampada a [0, 100]
Todos los valores de proyección e intervalos se limitan al rango [0, 100] para evitar OTP negativos o superiores al 100%.

### RN-PRE-005 — Delta what-if solo aplica a proyección, no a históricos
El escenario what-if modifica únicamente los valores proyectados (proyección, IC sup, IC inf). Los datos históricos permanecen inalterados. No se re-entrena el modelo.

### RN-PRE-006 — Factores what-if fijos
Los factores de mejora son constantes empíricas: 0.7 pp por cada 5 minutos de buffer adicional, 0.3 pp por cada 10% de reducción de carga. No son configurables desde la interfaz.

---

## Entradas y salidas

| FUNCIÓN / ENDPOINT | ENTRADAS | SALIDAS |
|---|---|---|
| GET /predictivo | Cookie JWT, query: airline, year, metric, horizonte | HTML con dashboard completo: mapa calor, proyección, recomendaciones, anomalías, ranking riesgo, what-if |
| POST /predictivo/proyeccion | Cookie JWT, form: airline, year, horizonte | JSON: {historico[], proyeccion[], ic_sup[], ic_inf[], meses_hist[], meses_proy[], metodo, n_meses, ajustado[], precision_estimada, advertencia?} |
| GET /predictivo/estacionalidad | Cookie JWT, query: airline, metric | JSON: {rows[], cols[], matrix[][], metric} |
| GET /predictivo/recomendaciones | Cookie JWT, query: airline, year | JSON: [{prioridad, icono, color, titulo, descripcion, modulo, justificacion, impacto_estimado, accion_directa, revisado}] |
| GET /predictivo/anomalias | Cookie JWT, query: airline, year | JSON: [{tipo, airline, mes, año, valor_esperado, valor_real, z_score, sparkline, descripcion}] |
| GET /predictivo/ranking_riesgo | Cookie JWT, query: year | JSON: [{airline, otp, std, score, nivel, tendencia, tendencia_delta, n_meses}] |
| POST /predictivo/whatif | Cookie JWT, JSON: {aerolinea, anio, horizonte, buffer_minutos, reduccion_carga} | JSON: {proyeccion[], ic_sup[], ic_inf[], meses_hist[], meses_proy[], whatif:{delta, buffer_minutos, reduccion_carga}} |
| POST /predictivo/informe | Cookie JWT, form: airline, year, horizonte | JSON: {url: "URL firmada del repositorio"} |

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
1. El Analista accede al dashboard predictivo. El sistema carga datos desde la tabla de agregación OTP.
2. La página muestra el mapa de calor estacional, gráfico de proyección OTP con intervalos de confianza, tarjetas de recomendaciones priorizadas, lista de anomalías con sparklines y tabla de ranking de riesgo.
3. El Analista cambia el filtro de aerolínea; la página se recarga con nuevos datos.
4. El Analista cambia el horizonte de proyección; el sistema actualiza el gráfico vía AJAX sin recargar la página.
5. Las recomendaciones se muestran ordenadas por prioridad (alta → media → baja).

### Camino feliz — Simulación what-if
1. El Analista ajusta el control "Buffer de conexión" a 15 min y "Reducción de carga" a 10%.
2. El sistema envía la solicitud de simulación con los filtros actuales y parámetros.
3. El backend ejecuta la proyección Holt-Winters, calcula delta = (15/5)×0.7 + (10/10)×0.3 = 2.4 pp, ajusta proyección e IC.
4. El frontend dibuja una nueva línea diferenciada en el gráfico con etiqueta "Escenario +2.4pp".
5. El panel de resultado muestra "+2.4pp OTP proyectado".

### Camino feliz — Exportación PDF
1. El Analista hace clic en "Generar Informe Ejecutivo".
2. Aparece el modal previo con 4 tarjetas animadas (OTP promedio, tendencia, mes crítico, próxima proyección).
3. El Analista hace clic en "Descargar PDF".
4. El sistema genera HTML con SVG inline, lo convierte a PDF y lo sube al repositorio de almacenamiento.
5. Se retorna URL firmada y el PDF se abre en nueva pestaña.

### Manejo de errores
- **Datos insuficientes (< 3 meses):** El dashboard muestra mensaje "Sin datos suficientes. Selecciona una aerolínea con al menos 3 meses de historial." en lugar del gráfico.
- **Error en Holt-Winters (convergencia):** Fallback a media móvil 6 meses. Se registra advertencia en metadatos.
- **Error en repositorio de almacenamiento (informe):** Se retorna error 500 con mensaje descriptivo.
- **Error en what-if (datos vacíos):** Se retorna error 400 "Datos insuficientes."
- **Error en estacionalidad (tabla vacía):** Se retorna JSON con matriz vacía.

---

## Criterios de aceptación

- **CU-E14:** Dado que existen 3 o más meses de datos OTP, cuando el Analista solicita una proyección, entonces el sistema devuelve una serie proyectada con Holt-Winters, intervalos de confianza al 95% y metadatos del modelo.
- **CU-E15:** Dado que el hecho enriquecido tiene datos, cuando el Analista selecciona una métrica en el dashboard, entonces el mapa de calor muestra la matriz 7×12 con colores condicionales.
- **CU-E16:** Dado que hay datos OTP, cuando se carga el dashboard, entonces el sistema muestra recomendaciones ordenadas por prioridad con título, descripción, justificación e impacto estimado.
- **CU-E17:** Dado que la librería de PDF está instalada, cuando el Analista genera un informe, entonces el sistema produce un PDF con 4 secciones (resumen, proyección, mapa de calor, recomendaciones), lo sube al repositorio y retorna URL firmada.
- **CU-E20:** Dado que hay 2 o más años de datos históricos, cuando se cargan anomalías, entonces el sistema retorna hasta 5 eventos con |z| ≥ 1.5, incluyendo sparkline SVG y descripción.
- **CU-E21:** Dado que hay datos de múltiples aerolíneas, cuando se carga el ranking, entonces el sistema retorna lista ordenada por score compuesto con clasificación (estable/riesgo/crítico) y tendencia.
- **CU-E22:** Dado que hay datos OTP suficientes, cuando el Analista ajusta los controles what-if, entonces el sistema retorna una proyección ajustada aplicando el delta calculado a los valores proyectados, sin modificar los históricos.

---

## Dependencias

- **Seguridad:** Autenticación JWT y autorización con permisos `predictivo:ver` (dashboard, proyección, estacionalidad, recomendaciones, anomalías, ranking, what-if) y `predictivo:exportar` (informe PDF).
- **Pipeline ELT:** Tablas de agregación `agg_otp_aerolinea_mes` y demás tablas analíticas en MinIO, más el hecho enriquecido.
- **Statsmodels:** Librería para la proyección Holt-Winters.
- **WeasyPrint:** Librería Python para conversión HTML+CSS → PDF (requisito exclusivo del informe ejecutivo, sin fallback).
- **MinIO:** Bucket `aerotrack-exports` para almacenamiento de PDFs de informe ejecutivo.
- **Configuración:** `configuracion_sistema` módulo `sistema`, clave `horizonte_prediccion_max` (default 6).

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
- Comparación multi-aerolínea en un mismo informe PDF.
- Notificaciones push cuando OTP proyectado cruza umbrales.
- Exportación del ranking de riesgo a PDF independiente.
- Análisis de sensibilidad avanzado (monte carlo, múltiples escenarios simultáneos).
