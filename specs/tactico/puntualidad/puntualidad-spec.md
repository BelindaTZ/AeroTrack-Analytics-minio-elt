# Especificación Táctica — Puntualidad OTP

**Módulo:** Puntualidad
**Prefijo:** PUN
**Código fuente:** `app/puntualidad/analizar_otp.py`
**Casos de uso cubiertos:** CU-E03 (Analizar puntualidad OTP por aerolínea), CU-E04 (Comparar aerolíneas en rutas compartidas), CU-E05 (Ver tendencias de puntualidad por período), CU-O14 (Consultar narrativa IA de un gráfico o KPI)
**Actor:** Analista de Datos

---

## Funcionalidad 1: Analizar puntualidad OTP por aerolínea (CU-E03)

Análisis del On-Time Performance (OTP) por aerolínea con causas de retraso, tendencia mensual y desglose por día de semana. Datos desde `agg_otp_aerolinea_mes`, `agg_causas_retraso_mes` y `agg_otp_dia_semana`.

### RF-PUN-001 — Mostrar OTP por aerolínea en gráfico de barras
Gráfico de barras (Chart.js) con OTP % de cada aerolínea (top 25 por volumen). Barras coloreadas: verde (OTP ≥ 80%), ámbar (70-79%), rojo (< 70%). Tooltip muestra retraso promedio en minutos (`retraso_prom`).

### RF-PUN-002 — Mostrar causas de retraso en gráfico de dona
Gráfico de dona (Chart.js) con distribución de minutos de retraso por causa (Carrier, Weather, NAS, Security, LateAircraft). Datos desde `agg_causas_retraso_mes`.

### RF-PUN-003 — Mostrar tendencia OTP mensual en gráfico de línea
Gráfico de línea (Chart.js) con OTP % por mes. Si hay un año específico seleccionado, muestra línea punteada del año anterior (YoY) y badge de tendencia estadística (pendiente de regresión lineal en pp/mes). Tooltip muestra variación en puntos porcentuales vs mes anterior.

### RF-PUN-004 — Mostrar OTP por día de semana en gráfico de barras
Gráfico de barras (Chart.js) con OTP % por día de semana (Lun–Dom). Datos desde `agg_otp_dia_semana` (sin filtro de aerolínea/mes, solo global).

### RF-PUN-005 — Filtrar por año, mes y aerolínea
Tres selectores que recargan todo el módulo vía fetch. Datos cacheados 5 min en `_page_cache`.

### RF-PUN-006 — Narrativa IA por elemento del gráfico
Clic en barra/segmento/punto del gráfico abre popover con narrativa IA generada por `generar_narrativa()`. El popover incluye indicador de proveedor IA y fuente (caché/directo).

### RF-PUN-007 — Calcular retraso promedio por aerolínea
El sistema calcula y expone el retraso promedio en minutos (`retraso_prom`) para cada aerolínea como promedio de `delay_avg` desde `agg_otp_aerolinea_mes`.

### RF-PUN-008 — Calcular variación mes a mes en tendencia
Para la tendencia mensual, el sistema calcula la diferencia en puntos porcentuales entre cada mes y el anterior (`variacion_pp`), mostrada en tooltip del chart.

### RF-PUN-009 — Calcular tendencia estadística (regresión lineal)
El sistema calcula la pendiente de una regresión lineal simple sobre los OTP mensuales. Pendiente positiva = mejora, negativa = deterioro. Se muestra como badge en el título del chart.

### RF-PUN-010 — Mostrar YoY (año anterior) en tendencia mensual
Cuando el filtro de año está activo, el sistema carga los datos del año anterior y superpone una línea punteada gris en el chart de tendencia mensual.

### RNF-PUN-001 — Datos cacheados 5 minutos
Todo el módulo se cachea en `_page_cache` con `_PAGE_TTL = 300` segundos por combinación única de filtros.

### RNF-PUN-002 — Límite de visualización a top 25 aerolíneas
La tabla y gráfico de OTP por aerolínea se limitan a las 25 aerolíneas con mayor volumen de vuelos (mínimo 50 vuelos).

---

## Funcionalidad 2: Comparar aerolíneas en rutas compartidas (CU-E04)

Benchmarking competitivo de aerolíneas que operan una misma ruta, con ranking ordinal, brecha vs líder y narrativa IA.

### RF-PUN-011 — Seleccionar ruta origen-destino a comparar
Selector de ruta con formato `ORIGEN-DESTINO` (códigos IATA de 3 letras) cargado desde `agg_rutas_eficiencia`. Filtro opcional por año.

### RF-PUN-012 — Mostrar tabla comparativa con ranking
Tabla de aerolíneas que operan la ruta seleccionada, ordenada por OTP descendente, con columnas: # (ranking ordinal con badge dorado/plata/bronce), Aerolínea, Vuelos, OTP %, Brecha vs líder (pp), Retraso prom. (min).

### RF-PUN-013 — Calcular ranking ordinal y brecha vs líder
Cada aerolínea recibe una posición ordinal (#1, #2, ...) basada en su OTP. La brecha se calcula como `lider_otp - aerolinea_otp` en puntos porcentuales.

### RF-PUN-014 — Mostrar gráfico comparativo de doble eje
Gráfico de barras (Chart.js) con OTP % (eje izquierdo) y retraso promedio (eje derecho) para cada aerolínea en la ruta.

### RF-PUN-015 — Narrativa IA por aerolínea en la ruta
Botón por fila que abre popover con narrativa IA mostrando OTP, retraso, tiempo real vs programado, índice de eficiencia para esa aerolínea en esa ruta. Datos cargados desde `agg_rutas_eficiencia`.

### RNF-PUN-003 — Datos cacheados 5 min por ruta y año
Los datos comparativos se cargan a través de `load_agg` con caché del módulo compartido (`app/shared/analytics.py`).

---

## Funcionalidad 3: Ver tendencias de puntualidad por período (CU-E05)

Análisis temporal detallado con variación mensual, comparación YoY e indicador de tendencia estadística.

### RF-PUN-016 — Mostrar tendencia OTP mensual con variación
Gráfico de línea con OTP por mes. Tooltip muestra la variación en puntos porcentuales contra el mes anterior.

### RF-PUN-017 — Mostrar comparación YoY (año vs año anterior)
Cuando se selecciona un año específico, el gráfico superpone una línea punteada gris con los valores OTP del año anterior para el mismo conjunto de meses.

### RF-PUN-018 — Mostrar indicador de tendencia estadística
Badge en el título del chart de tendencia mostrando la pendiente de regresión lineal en pp/mes, con flecha verde (↑ mejora) o roja (↓ deterioro).

### RNF-PUN-004 — Regresión lineal solo con 2+ puntos
La tendencia estadística solo se calcula si hay al menos 2 meses con datos. Caso contrario la pendiente es 0.

---

## Reglas de negocio

### RN-PUN-001 — Mínimo 50 vuelos para aparecer en ranking OTP
Las aerolíneas con menos de 50 vuelos totales en el período no aparecen en el ranking de OTP.

### RN-PUN-002 — OTP mínimo operacional 80%
Se considera que una aerolínea CUMPLE el estándar OTP cuando su porcentaje es ≥ 80%. Caso contrario se marca como NO CUMPLE.

### RN-PUN-003 — Aerolínea líder siempre tiene brecha 0
La aerolínea con mayor OTP en la comparación de ruta tiene brecha = 0.0 pp (el badge se muestra verde). Las demás tienen brecha positiva (roja).

### RN-PUN-004 — Variación mes a mes no se calcula para el primer mes
El primer mes del período tiene variación = 0.0 pp por no tener mes anterior de referencia.

---

## Entradas y salidas

| FUNCIÓN / ENDPOINT | ENTRADAS | SALIDAS |
|---|---|---|
| GET /puntualidad | Cookie JWT, year, month, airline | Página HTML con chart OTP, dona causas, línea tendencia, barras día semana |
| GET /puntualidad/narrativa | Cookie JWT, year, month, airline, tipo, airline_val, causa, mes, dia, ruta_tpl, aerolinea_tpl | JSON con narrativa IA del elemento seleccionado |
| GET /puntualidad/comparar | Cookie JWT, ruta, year | Página HTML con tabla ranking y chart comparativo |

---

## Historias de usuario

- **HU-PUN-01:** Como Analista de Datos quiero ver el OTP de cada aerolínea en un gráfico de barras para identificar rápidamente las mejor y peor posicionadas.
- **HU-PUN-02:** Como Analista de Datos quiero ver la distribución de causas de retraso para entender qué factores impactan más la puntualidad.
- **HU-PUN-03:** Como Analista de Datos quiero hacer clic en un elemento del gráfico para obtener una narrativa IA que interprete el dato en contexto.
- **HU-PUN-04:** Como Analista de Datos quiero comparar aerolíneas en una misma ruta con ranking y brecha vs líder para evaluar competitividad.
- **HU-PUN-05:** Como Analista de Datos quiero ver la tendencia OTP mensual con comparación contra el año anterior para identificar mejora o deterioro sostenido.

---

## Objetivo

Analizar el On-Time Performance (OTP) de las aerolíneas con perspectiva comparativa, tendencias temporales, causas de retraso y benchmarking competitivo de aerolíneas en rutas compartidas.

---

## Escenarios

### Camino feliz
1. El Analista accede a `GET /puntualidad` con su Cookie JWT.
2. El sistema carga datos desde `agg_otp_aerolinea_mes`, `agg_causas_retraso_mes` y `agg_otp_dia_semana`.
3. El sistema muestra gráfico de barras OTP por aerolínea (tooltip con retraso promedio), dona de causas de retraso, línea de tendencia mensual (con YoY y badge de tendencia si hay año seleccionado) y barras por día de semana.
4. El Analista hace clic en un elemento del gráfico; el sistema abre un popover con narrativa IA generada por `generar_narrativa()`.
5. El Analista navega a `GET /puntualidad/comparar`, selecciona una ruta y visualiza el ranking ordinal de aerolíneas con brecha vs líder, gráfico de doble eje y botones de narrativa IA por aerolínea.

### Manejo de errores
- **Tablas agregadas no disponibles (FileNotFoundError):** Se muestra "Los datos no están disponibles. Ejecute el pipeline ELT primero."
- **Error en endpoint /narrativa:** El servidor retorna `{"texto": "", "proveedor": "", "desde_cache": false}` y el popover muestra "Sin narrativa disponible."
- **Error de conexión en fetch de narrativa:** El popover muestra "Error al conectar con la IA."
- **Sin datos del año anterior para YoY:** La línea YoY simplemente no se dibuja; no se genera error.
- **Menos de 2 meses con datos:** La tendencia estadística se muestra como 0.0 (no se calcula regresión).

---

## Criterios de aceptación

- **CU-E03:** Dado que existen datos en `agg_otp_aerolinea_mes`, cuando el Analista accede al módulo de puntualidad, entonces el sistema muestra el OTP por aerolínea con retraso promedio, causas de retraso en dona, tendencia mensual con variación pp y desglose por día de semana.
- **CU-E04:** Dado que el Analista selecciona una ruta en la página comparativa, cuando existen datos en `agg_rutas_eficiencia` para esa ruta, entonces el sistema muestra el ranking ordinal de aerolíneas con OTP, brecha vs líder en pp, retraso promedio y botón de narrativa IA por aerolínea.
- **CU-E05:** Dado que el Analista visualiza la tendencia mensual con un año específico seleccionado, cuando existen datos del año anterior en `agg_otp_aerolinea_mes`, entonces el sistema superpone la línea YoY punteada, muestra la variación pp en el tooltip y el badge de tendencia estadística con pendiente de regresión lineal.

---

## Dependencias

- **Seguridad:** Autenticación mediante JWT y autorización por permiso `puntualidad:ver`.
- **Pipeline ELT:** Generación de las tablas agregadas `agg_otp_aerolinea_mes`, `agg_causas_retraso_mes`, `agg_otp_dia_semana` y `agg_rutas_eficiencia`.

---

## Casos de uso relacionados

- CU-E03 (Analizar puntualidad OTP por aerolínea)
- CU-E04 (Comparar aerolíneas en rutas compartidas)
- CU-E05 (Ver tendencias de puntualidad por período)
- CU-O14 (Consultar narrativa IA de un gráfico o KPI — endpoint `GET /puntualidad/narrativa`)

---

## Fuera de alcance

- Exportación de gráficos o tablas a PDF, imagen o CSV.
- Edición de datos de vuelo, causas de retraso o registros de origen.
- Comparación simultánea de más de una ruta en la misma vista comparativa.
- Análisis predictivo de OTP futuro (cubierto en el módulo Predictivo).
- Alertas automáticas por email cuando el OTP de una aerolínea cae por debajo del 80%.

---

## Glosario
