# Especificación Táctica — Cancelaciones

**Módulo:** Cancelaciones
**Prefijo:** CAN
**Código fuente:** `app/cancelaciones/clasificar_faa.py`
**Casos de uso cubiertos:** CU-E08 (Analizar cancelaciones por causa FAA), CU-E09 (Analizar impacto operacional de desvíos), CU-E10 (Tendencia de cancelaciones), CU-O14 (Consultar narrativa IA de un gráfico o KPI)
**Actor:** Analista de Datos/Administrador

---

## Funcionalidad 1: Analizar cancelaciones por causa FAA (CU-E08)

Análisis de cancelaciones clasificadas por código oficial FAA (A: Carrier, B: Weather, C: NAS, D: Security) con filtro por aerolínea.

### RF-CAN-001 — Mostrar KPIs de cancelaciones en tarjetas
El sistema debe mostrar cuatro tarjetas con indicadores clave: total de vuelos cancelados, tasa de cancelación (%), total de vuelos y cantidad de causas FAA distintas. Cada tarjeta debe incluir la opción de obtener narrativa IA.

### RF-CAN-002 — Mostrar distribución por código FAA en gráfico de dona
El sistema debe mostrar un gráfico de dona con el desglose de cancelaciones por código FAA (A: azul, B: ámbar, C: verde, D: rojo). Al seleccionar un segmento se debe abrir la narrativa IA correspondiente.

### RF-CAN-003 — Mostrar flujo Sankey de cancelaciones
El sistema debe mostrar un diagrama de flujo que presente la trayectoria desde el total de vuelos hacia operados y cancelados, y de ahí al desglose por código FAA. El diagrama se oculta si no hay cancelaciones en el período.

### RF-CAN-004 — Filtrar por año, mes y aerolínea
El sistema debe ofrecer tres filtros (año, mes, aerolínea) que actualizan el módulo sin recargar la página. Cuando se aplica filtro de aerolínea, el sistema debe utilizar la tabla de agregación con desglose por aerolínea; sin filtro, usa la tabla general de cancelaciones.

### RF-CAN-005 — Mostrar tasa de cancelación con umbral 5%
El sistema debe comparar la tasa de cancelación contra el umbral del 5%. Si excede, se muestra en rojo; si cumple, en verde.

### RNF-CAN-001 — Tabla de agregación específica con aerolínea
El sistema debe seleccionar la tabla de agregación adecuada según la presencia de filtro de aerolínea: la tabla con desglose por aerolínea cuando hay filtro activo, o la tabla general cuando no hay filtro.

### RNF-CAN-002 — Datos cacheados 5 minutos
El sistema debe cachear los datos del módulo durante 5 minutos.

### RNF-CAN-003 — Códigos FAA definidos en el dominio
Los 4 códigos FAA con sus descripciones son parte del dominio del módulo: A=Carrier, B=Weather, C=NAS, D=Security.

---

## Funcionalidad 2: Analizar impacto operacional de desvíos (CU-E09)

Análisis de desvíos a aeropuertos alternativos, cuantificando tiempo adicional y distancia extra por ruta.

### RF-CAN-006 — Mostrar top 20 rutas con más desvíos
El sistema debe mostrar las 20 rutas con mayor número de desvíos en una tabla con columnas: ruta (origen-destino), aeropuerto alternativo, desvíos, retraso de llegada promedio (min) y distancia de desvío promedio (mi).

### RF-CAN-007 — Mostrar gráfico de desvíos por ruta
El sistema debe mostrar un gráfico de barras horizontal con las rutas en el eje vertical y el número de desvíos en el horizontal, incluyendo una serie secundaria de retraso promedio por desvío. Al seleccionar una barra se debe abrir la narrativa IA correspondiente.

### RF-CAN-008 — Filtrar desvíos por año y mes
El sistema debe filtrar los datos de desvíos por año y mes, reagrupando por ruta para mantener el top 20 consolidado.

### RF-CAN-009 — Narrativa IA por ruta desviada
Por cada fila de la tabla y barra del gráfico, el sistema debe ofrecer la opción de obtener narrativa IA mostrando: ruta, total de desvíos, aeropuerto alternativo, retraso promedio y distancia adicional.

### RNF-CAN-004 — Columnas de período en tabla de desvíos
La tabla de desvíos incluye columnas de año y mes para permitir filtrado temporal. Sin filtro se muestran todos los desvíos del histórico.

### RNF-CAN-005 — Agregación por ruta en desvíos
El sistema debe reagrupar los datos de desvíos por ruta (origen + destino + aeropuerto alternativo) para consolidar múltiples períodos en una sola fila.

---

## Funcionalidad 3: Ver tendencia de cancelaciones por período (CU-E10)

Tendencia mensual de cancelaciones con desglose por código FAA.

### RF-CAN-010 — Mostrar tendencia mensual de cancelaciones
El sistema debe mostrar un gráfico de barras con las cancelaciones totales por mes, superponiendo líneas individuales por código FAA (A: azul, B: ámbar, C: verde, D: rojo).

### RF-CAN-011 — Narrativa IA por mes
Al seleccionar una barra del mes, el sistema debe mostrar narrativa IA con: cancelaciones del mes, promedio mensual, diferencia vs promedio, mes pico y tasa de cancelación global.

### RF-CAN-012 — Datos por código FAA en tendencia
El sistema debe desglosar cada mes en sus 4 componentes FAA, mostrando líneas individuales para identificar cambios estacionales o eventos específicos.

### RNF-CAN-006 — Códigos sin datos se omiten en la leyenda
Los códigos FAA que no tienen registros en un período no generan líneas en el gráfico de tendencia.

---

## Reglas de negocio

### RN-CAN-001 — Tasa de cancelación máxima aceptable 5%
Se considera que la operación cumple el estándar cuando la tasa de cancelación es ≤ 5%. Caso contrario se marca como NO CUMPLE.

### RN-CAN-002 — Código FAA A es "Carrier" (responsabilidad de la aerolínea)
El código A agrupa cancelaciones por causas imputables a la aerolínea (tripulación, mantenimiento, etc.). Es el único código sobre el cual la aerolínea tiene control directo.

### RN-CAN-003 — Desvíos no se contabilizan como cancelaciones
Un vuelo desviado no es un vuelo cancelado. Ambos indicadores se reportan por separado en el módulo.

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
1. El Analista accede al módulo de cancelaciones con su sesión activa y filtros opcionales (año, mes, aerolínea).
2. Si hay filtro de aerolínea, el sistema carga la tabla con desglose por aerolínea; si no, carga la tabla general.
3. El sistema muestra 4 tarjetas KPI, gráfico de dona por código FAA, diagrama de flujo, tendencia mensual con líneas por código FAA, y tabla + gráfico de desvíos top 20.
4. El Analista selecciona una aerolínea en el filtro; el sistema recarga usando la tabla con desglose por aerolínea.
5. El Analista hace clic en un segmento de la dona, barra de tendencia o barra de desvíos; el sistema abre un panel emergente con narrativa IA.

### Manejo de errores
- **Tablas agregadas no disponibles:** Se muestra "Los datos no están disponibles. Ejecute el pipeline ELT primero."
- **Error en endpoint de narrativa:** El servidor retorna objeto vacío y el panel emergente muestra "Sin narrativa disponible."
- **Error de conexión en fetch de narrativa:** El panel emergente muestra "Error al conectar con la IA."
- **Sin cancelaciones en el período:** El diagrama de flujo se oculta automáticamente; la dona y la tendencia muestran estado vacío.
- **Sin desvíos en el período:** La sección de desvíos (tabla y gráfico) no se renderiza.

---

## Criterios de aceptación

- **CU-E08:** Dado que existen datos en `agg_cancelaciones_causa` (o con filtro de aerolínea), cuando el Analista accede al módulo de cancelaciones, entonces el sistema muestra la distribución por código FAA con KPIs, dona, diagrama de flujo y permite filtrar por aerolínea.
- **CU-E09:** Dado que existen datos en `agg_desvios_ruta`, cuando el Analista visualiza la sección de desvíos, entonces el sistema muestra el top 20 de rutas con más desvíos en tabla y gráfico de barras horizontal, filtrable por año y mes.
- **CU-E10:** Dado que existen datos de tendencia mensual en `agg_cancelaciones_causa`, cuando el Analista visualiza el gráfico de tendencia, entonces el sistema muestra las cancelaciones totales por mes con líneas desglosadas por código FAA (A/B/C/D).

---

## Dependencias

- **Seguridad:** Autenticación mediante JWT y autorización por permiso `cancelaciones:ver`.
- **Pipeline ELT:** Generación de las tablas agregadas `agg_cancelaciones_causa`, `agg_cancelaciones_aerolinea_causa`, `agg_kpi_global_dia` y `agg_desvios_ruta`.

---

## Casos de uso relacionados

- CU-E08 (Analizar cancelaciones por causa FAA)
- CU-E09 (Analizar impacto operacional de desvíos)
- CU-E10 (Tendencia de cancelaciones)
- CU-O14 (Consultar narrativa IA de un gráfico o KPI — endpoint `GET /cancelaciones/narrativa`)

---

## Fuera de alcance

- Exportación del análisis de cancelaciones a PDF o CSV.
- Edición de códigos FAA, registros de cancelaciones o datos de desvíos.
- Notificaciones automáticas cuando la tasa de cancelación supera el 5%.
- Clasificación manual de causas de cancelación fuera de los 4 códigos FAA estándar.
- Análisis de cancelaciones por ruta específica (cubierto parcialmente en el asistente IA).

---

## Glosario

- **FAA:** Federal Aviation Administration — entidad reguladora de la aviación en EE.UU.
- **Código FAA A:** Cancelación por causa imputable a la aerolínea (Carrier).
- **Código FAA B:** Cancelación por condiciones climáticas (Weather).
- **Código FAA C:** Cancelación por el sistema nacional de aviación (NAS).
- **Código FAA D:** Cancelación por razones de seguridad (Security).
- **Desvío:** Vuelo que aterriza en un aeropuerto diferente al programado (Diverted).
- **Tasa de cancelación:** Porcentaje de vuelos cancelados sobre el total de vuelos programados.
