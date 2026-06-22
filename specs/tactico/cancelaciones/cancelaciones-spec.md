# Especificación Táctica — Cancelaciones

**Módulo:** Cancelaciones
**Prefijo:** CAN
**Código fuente:** `app/cancelaciones/clasificar_faa.py`
**Casos de uso cubiertos:** CU-E08 (Analizar cancelaciones por causa FAA), CU-E09 (Analizar impacto operacional de desvíos), CU-E10 (Tendencia de cancelaciones)
**Actor:** Analista de Datos

---

## Funcionalidad 1: Analizar cancelaciones por causa FAA (CU-E08)

Análisis de cancelaciones clasificadas por código oficial FAA (A: Carrier, B: Weather, C: NAS, D: Security) con filtro por aerolínea.

### RF-CAN-001 — Mostrar KPIs de cancelaciones en tarjetas
Cuatro tarjetas con indicadores clave: Total cancelados, Tasa cancelación (%), Total vuelos, Causas FAA distintas. Cada tarjeta tiene botón de narrativa IA.

### RF-CAN-002 — Mostrar distribución por código FAA en gráfico de dona
Gráfico de dona (Chart.js) con desglose por código FAA (A/B/C/D), colores: azul, ámbar, verde, rojo. Clic en segmento abre narrativa IA.

### RF-CAN-003 — Mostrar flujo Sankey de cancelaciones
Diagrama Sankey (Plotly) mostrando el flujo desde Total vuelos → Operados / Cancelados → Desglose por código FAA. Se oculta si no hay cancelaciones.

### RF-CAN-004 — Filtrar por año, mes y aerolínea
Tres selectores que recargan el módulo vía fetch. El filtro de aerolínea utiliza `agg_cancelaciones_causa_aerolinea` (que incluye columna `carrier`), no `agg_cancelaciones_causa` (que no la tiene).

### RF-CAN-005 — Mostrar tasa de cancelación con umbral 5%
La tasa de cancelación se compara contra el umbral del 5%. Si excede, se muestra en rojo; si cumple, en verde. El indicador "Estado tasa global" aparece en la narrativa IA.

### RNF-CAN-001 — Tabla de agregación específica con aerolínea
La tabla `agg_cancelaciones_causa_aerolinea` agrupa por `cancellation_code` + `carrier` + `year` + `month` para permitir filtrado por aerolínea. Cuando no hay filtro de aerolínea, se usa `agg_cancelaciones_causa` (más ligera).

### RNF-CAN-002 — Datos cacheados 5 minutos
Módulo cacheado en `_page_cache` con `_PAGE_TTL = 300` segundos.

### RNF-CAN-003 — Códigos FAA definidos en constante
Los 4 códigos FAA con sus descripciones están definidos en `_FAA_CODIGOS` dentro del módulo: A=Carrier, B=Weather, C=NAS, D=Security.

---

## Funcionalidad 2: Analizar impacto operacional de desvíos (CU-E09)

Análisis de desvíos a aeropuertos alternativos, cuantificando tiempo adicional y distancia extra por ruta.

### RF-CAN-006 — Mostrar top 20 rutas con más desvíos
Tabla con las 20 rutas con mayor número de desvíos. Columnas: Ruta (origen-destino), Aeropuerto alternativo, Desvíos, Retraso llegada prom. (min), Distancia desvío prom. (mi).

### RF-CAN-007 — Mostrar gráfico de desvíos por ruta
Gráfico de barras horizontal (Chart.js) con las rutas en eje Y y desvíos en eje X. Incluye serie secundaria de retraso promedio por desvío (eje superior). Clic en barra abre narrativa IA.

### RF-CAN-008 — Filtrar desvíos por año y mes
Los datos de desvíos se filtran por año y mes usando las columnas `year`/`month` de `agg_desvios_ruta`. Los registros se reagrupan por ruta para mantener el top 20 consolidado.

### RF-CAN-009 — Narrativa IA por ruta desviada
Botón por fila y clic en barra abren popover con narrativa IA mostrando: ruta, desvíos totales, aeropuerto alternativo, retraso promedio, distancia adicional.

### RNF-CAN-004 — Columnas year/month agregadas en pipeline
La tabla `agg_desvios_ruta` incluye `year` y `month` en el GROUP BY de la pipeline para permitir filtrado temporal. Sin filtro se muestran todos los desvíos del histórico.

### RNF-CAN-005 — Retorno agregado por ruta
Los datos de `agg_desvios_ruta` se reagrupan por ruta (origin + dest + alt_airport) en `_desvios_agg()` para consolidar múltiples períodos en una sola fila.

---

## Funcionalidad 3: Ver tendencia de cancelaciones por período (CU-E10)

Tendencia mensual de cancelaciones con desglose por código FAA.

### RF-CAN-010 — Mostrar tendencia mensual de cancelaciones
Gráfico de barras (Chart.js) con cancelaciones totales por mes, superponiendo líneas por código FAA (A=azul, B=ámbar, C=verde, D=rojo).

### RF-CAN-011 — Narrativa IA por mes
Clic en barra del mes abre popover con narrativa IA mostrando: cancelaciones del mes, promedio mensual, diferencia vs promedio, mes pico, tasa de cancelación global.

### RF-CAN-012 — Datos por código FAA en tendencia
El sistema desglosa cada mes en sus 4 componentes FAA, mostrando líneas individuales para identificar cambios estacionales o eventos específicos.

### RNF-CAN-006 — Códigos sin datos se omiten en la leyenda
Los códigos FAA que no tienen registros en un período no generan líneas en el gráfico de tendencia.

---

## Reglas de negocio

### RN-CAN-001 — Tasa de cancelación máxima aceptable 5%
Se considera que la operación cumple el estándar cuando la tasa de cancelación es ≤ 5%. Caso contrario se marca como NO CUMPLE.

### RN-CAN-002 — Código FAA A es "Carrier" (responsabilidad de la aerolínea)
El código A agrupa cancelaciones por causas imputables a la aerolínea (tripulación, mantenimiento, etc.). Es el único código sobre el cual la aerolínea tiene control directo.

### RN-CAN-003 — Desvíos no se contabilizan como cancelaciones
Un vuelo desviado (Diverted=1) no es un vuelo cancelado. Ambos indicadores se reportan por separado en el módulo.

---

## Entradas y salidas

| FUNCIÓN / ENDPOINT | ENTRADAS | SALIDAS |
|---|---|---|
| GET /cancelaciones | Cookie JWT, year, month, airline | Página HTML con KPIs, dona FAA, Sankey, tendencia mensual, tabla + chart desvíos |
| GET /cancelaciones/narrativa | Cookie JWT, year, month, airline, tipo, code, mes, ruta | JSON con narrativa IA del elemento seleccionado |

---

## Historias de usuario

- **HU-CAN-01:** Como Analista de Datos quiero ver la distribución de cancelaciones por código FAA para identificar la causa dominante.
- **HU-CAN-02:** Como Analista de Datos quiero filtrar cancelaciones por aerolínea para analizar el desempeño de un operador específico.
- **HU-CAN-03:** Como Analista de Datos quiero ver la tendencia mensual de cancelaciones con desglose por causa para identificar patrones estacionales.
- **HU-CAN-04:** Como Analista de Datos quiero ver el impacto de desvíos por ruta en un gráfico para identificar las rutas más problemáticas.
- **HU-CAN-05:** Como Analista de Datos quiero hacer clic en una ruta desviada para obtener una narrativa IA que interprete el impacto operacional.

---

## Objetivo

Analizar las cancelaciones clasificadas por código oficial FAA (A/B/C/D) y el impacto operacional de los desvíos a aeropuertos alternativos, con tendencia mensual, filtro por aerolínea y narrativa IA.

---

## Escenarios

### Camino feliz
1. El Analista accede a `GET /cancelaciones` con su Cookie JWT y filtros opcionales (año, mes, aerolínea).
2. Si hay filtro de aerolínea, el sistema carga `agg_cancelaciones_causa_aerolinea`; si no, carga `agg_cancelaciones_causa`. También carga `agg_kpi_global_dia` y `agg_desvios_ruta` con filtros de año/mes.
3. El sistema muestra 4 tarjetas KPI, gráfico de dona por código FAA, diagrama Sankey de flujo, tendencia mensual con líneas por código FAA, y tabla + gráfico de barras horizontal de desvíos top 20.
4. El Analista selecciona una aerolínea en el filtro; el sistema recarga usando la tabla con desglose por aerolínea.
5. El Analista hace clic en un segmento de la dona, barra de tendencia o barra de desvíos; el sistema abre un popover con narrativa IA.

### Manejo de errores
- **Tablas agregadas no disponibles (FileNotFoundError):** Se muestra "Los datos no están disponibles. Ejecute el pipeline ELT primero."
- **Error en endpoint /narrativa:** El servidor retorna objeto vacío y el popover muestra "Sin narrativa disponible."
- **Error de conexión en fetch de narrativa:** El popover muestra "Error al conectar con la IA."
- **Sin cancelaciones en el período:** El diagrama Sankey se oculta automáticamente; la dona y la tendencia muestran estado vacío.
- **Sin desvíos en el período:** La sección de desvíos (tabla y chart) no se renderiza.

---

## Criterios de aceptación

- **CU-E08:** Dado que existen datos en `agg_cancelaciones_causa` (o `agg_cancelaciones_causa_aerolinea` con filtro), cuando el Analista accede al módulo de cancelaciones, entonces el sistema muestra la distribución por código FAA con KPIs, dona, Sankey y permite filtrar por aerolínea.
- **CU-E09:** Dado que existen datos en `agg_desvios_ruta`, cuando el Analista visualiza la sección de desvíos, entonces el sistema muestra el top 20 de rutas con más desvíos en tabla y gráfico de barras horizontal, filtrable por año y mes.
- **CU-E10:** Dado que existen datos de tendencia mensual en `agg_cancelaciones_causa`, cuando el Analista visualiza el gráfico de tendencia, entonces el sistema muestra las cancelaciones totales por mes con líneas desglosadas por código FAA (A/B/C/D).

---

## Dependencias

- **Seguridad:** Autenticación mediante JWT y autorización por permiso `cancelaciones:ver`.
- **Pipeline ELT:** Generación de las tablas agregadas `agg_cancelaciones_causa`, `agg_cancelaciones_causa_aerolinea`, `agg_kpi_global_dia` y `agg_desvios_ruta`.

---

## Casos de uso relacionados

- CU-E08 (Analizar cancelaciones por causa FAA)
- CU-E09 (Analizar impacto operacional de desvíos)
- CU-E10 (Tendencia de cancelaciones)

---

## Fuera de alcance

- Exportación del análisis de cancelaciones a PDF o CSV.
- Edición de códigos FAA, registros de cancelaciones o datos de desvíos.
- Notificaciones automáticas cuando la tasa de cancelación supera el 5%.
- Clasificación manual de causas de cancelación fuera de los 4 códigos FAA estándar.
- Análisis de cancelaciones por ruta específica (cubierto parcialmente en el asistente IA vía `agg_cancelaciones_ruta`).

---

## Glosario

- **FAA:** Federal Aviation Administration — entidad reguladora de la aviación en EE.UU.
- **Código FAA A:** Cancelación por causa imputable a la aerolínea (Carrier).
- **Código FAA B:** Cancelación por condiciones climáticas (Weather).
- **Código FAA C:** Cancelación por el sistema nacional de aviación (NAS).
- **Código FAA D:** Cancelación por razones de seguridad (Security).
- **Desvío:** Vuelo que aterriza en un aeropuerto diferente al programado (Diverted).
- **Tasa de cancelación:** Porcentaje de vuelos cancelados sobre el total de vuelos programados.
