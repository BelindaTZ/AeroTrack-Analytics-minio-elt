# Especificación Táctica — Puntualidad OTP

**Módulo:** Puntualidad
**Prefijo:** PUN
**Código fuente:** `app/puntualidad/analizar_otp.py`
**Casos de uso cubiertos:** CU-E03 (Analizar puntualidad OTP por aerolínea), CU-E04 (Comparar aerolíneas en rutas compartidas), CU-E05 (Ver tendencias de puntualidad por período), CU-O14 (Consultar narrativa IA de un gráfico o KPI)
**Actor:** Analista de Datos/Administrador

---

## Funcionalidad 1: Analizar puntualidad OTP por aerolínea (CU-E03)

Análisis del On-Time Performance (OTP) por aerolínea con causas de retraso, tendencia mensual y desglose por día de semana.

### RF-PUN-001 — Mostrar OTP por aerolínea en gráfico de barras
El sistema debe mostrar un gráfico de barras con el OTP porcentual de cada aerolínea (top 25 por volumen de vuelos), coloreadas según cumplimiento: verde (OTP ≥ 80%), ámbar (70-79%), rojo (< 70%). Al interactuar con cada barra se debe mostrar el retraso promedio en minutos.

### RF-PUN-002 — Mostrar causas de retraso en gráfico de dona
El sistema debe mostrar un gráfico de dona con la distribución de minutos de retraso por causa: Carrier, Weather, NAS, Security y LateAircraft.

### RF-PUN-003 — Mostrar tendencia OTP mensual en gráfico de línea
El sistema debe mostrar la tendencia de OTP porcentual por mes en un gráfico de línea. Cuando hay un año específico seleccionado, debe superponer la línea del año anterior (comparación interanual) y un indicador de tendencia estadística en pp/mes. Al interactuar con cada punto se debe mostrar la variación en puntos porcentuales respecto al mes anterior.

### RF-PUN-004 — Mostrar OTP por día de semana en gráfico de barras
El sistema debe mostrar el OTP porcentual por día de semana (lunes a domingo) a nivel global, sin filtro de aerolínea ni mes.

### RF-PUN-005 — Filtrar por año, mes y aerolínea
El sistema debe ofrecer tres filtros (año, mes, aerolínea) que actualizan la vista completa sin recargar la página. Los datos se cachean durante 5 minutos.

### RF-PUN-006 — Narrativa IA por elemento del gráfico
Al seleccionar un elemento del gráfico (barra, segmento o punto), el sistema debe mostrar un panel emergente con narrativa generada por IA, incluyendo el indicador del proveedor utilizado y si la respuesta proviene de caché o se generó en tiempo real.

### RF-PUN-007 — Calcular retraso promedio por aerolínea
El sistema debe calcular y exponer el retraso promedio en minutos para cada aerolínea.

### RF-PUN-008 — Calcular variación mes a mes en tendencia
El sistema debe calcular la variación mensual del OTP en puntos porcentuales y mostrarla como información contextual al interactuar con cada punto del gráfico de tendencia.

### RF-PUN-009 — Calcular tendencia estadística (regresión lineal)
El sistema debe calcular la pendiente de una regresión lineal simple sobre los valores OTP mensuales y mostrarla como indicador en el título del gráfico. Pendiente positiva indica mejora; pendiente negativa indica deterioro.

### RF-PUN-010 — Mostrar YoY (año anterior) en tendencia mensual
Cuando el filtro de año está activo, el sistema debe cargar los datos del año anterior y superponerlos como línea de referencia en el gráfico de tendencia mensual.

### RNF-PUN-001 — Datos cacheados 5 minutos
El sistema debe cachear los datos del módulo durante 5 minutos por combinación única de filtros.

### RNF-PUN-002 — Límite de visualización a top 25 aerolíneas
La visualización de OTP por aerolínea se limita a las 25 aerolíneas con mayor volumen de vuelos (mínimo 50 vuelos).

---

## Funcionalidad 2: Comparar aerolíneas en rutas compartidas (CU-E04)

Benchmarking competitivo de aerolíneas que operan una misma ruta, con ranking ordinal, brecha vs líder y narrativa IA.

### RF-PUN-011 — Seleccionar ruta origen-destino a comparar
El sistema debe ofrecer un selector de ruta con formato ORIGEN-DESTINO (códigos IATA de 3 letras) y un filtro opcional por año.

### RF-PUN-012 — Mostrar tabla comparativa con ranking
El sistema debe mostrar una tabla comparativa de aerolíneas que operan la ruta seleccionada, ordenada por OTP descendente, con columnas: posición ordinal (con indicador dorado/plata/bronce para el podio), aerolínea, vuelos, OTP %, brecha vs líder (pp) y retraso promedio (min).

### RF-PUN-013 — Calcular ranking ordinal y brecha vs líder
El sistema debe asignar una posición ordinal a cada aerolínea basada en su OTP. La brecha se calcula como la diferencia en puntos porcentuales entre el OTP del líder y el de cada aerolínea.

### RF-PUN-014 — Mostrar gráfico comparativo de doble eje
El sistema debe mostrar un gráfico comparativo con OTP porcentual y retraso promedio en ejes independientes para cada aerolínea en la ruta.

### RF-PUN-015 — Narrativa IA por aerolínea en la ruta
Por cada aerolínea en la tabla comparativa, el sistema debe ofrecer la opción de obtener narrativa IA que incluya OTP, retraso, tiempo real vs programado e índice de eficiencia para esa aerolínea en esa ruta.

### RNF-PUN-003 — Datos cacheados 5 min por ruta y año
Los datos comparativos se deben cargar con caché compartido de 5 minutos.

---

## Funcionalidad 3: Ver tendencias de puntualidad por período (CU-E05)

Análisis temporal detallado con variación mensual, comparación interanual e indicador de tendencia estadística.

### RF-PUN-016 — Mostrar tendencia OTP mensual con variación
El sistema debe mostrar la tendencia de OTP mensual en un gráfico de línea, mostrando como información contextual la variación en puntos porcentuales respecto al mes anterior.

### RF-PUN-017 — Mostrar comparación YoY (año vs año anterior)
Cuando se selecciona un año específico, el sistema debe superponer los valores OTP del año anterior como línea de referencia para el mismo conjunto de meses.

### RF-PUN-018 — Mostrar indicador de tendencia estadística
El sistema debe mostrar un indicador de tendencia estadística en el gráfico, con la pendiente de regresión lineal en pp/mes y señal visual de mejora (↑) o deterioro (↓).

### RNF-PUN-004 — Regresión lineal solo con 2+ puntos
La tendencia estadística solo se calcula si hay al menos 2 meses con datos. Si no hay suficientes datos, la pendiente se muestra como 0.

---

## Reglas de negocio

### RN-PUN-001 — Mínimo 50 vuelos para aparecer en ranking OTP
Las aerolíneas con menos de 50 vuelos totales en el período no aparecen en el ranking de OTP.

### RN-PUN-002 — OTP mínimo operacional 80%
Se considera que una aerolínea CUMPLE el estándar OTP cuando su porcentaje es ≥ 80%. Caso contrario se marca como NO CUMPLE.

### RN-PUN-003 — Aerolínea líder siempre tiene brecha 0
La aerolínea con mayor OTP en la comparación de ruta tiene brecha = 0.0 pp. Las demás tienen brecha positiva.

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
1. El Analista accede al módulo de puntualidad con su sesión activa.
2. El sistema carga datos desde las tablas de agregación correspondientes.
3. El sistema muestra: gráfico de barras OTP por aerolínea, dona de causas de retraso, gráfico de línea de tendencia mensual (con comparación interanual y badge de tendencia si hay año seleccionado) y barras por día de semana.
4. El Analista hace clic en un elemento del gráfico; el sistema abre un panel emergente con narrativa IA.
5. El Analista navega a la vista comparativa, selecciona una ruta y visualiza el ranking ordinal de aerolíneas con brecha vs líder, gráfico de doble eje y botones de narrativa IA por aerolínea.

### Manejo de errores
- **Tablas agregadas no disponibles:** Se muestra "Los datos no están disponibles. Ejecute el pipeline ELT primero."
- **Error en endpoint de narrativa:** El servidor retorna objeto vacío y el panel emergente muestra "Sin narrativa disponible."
- **Error de conexión en fetch de narrativa:** El panel emergente muestra "Error al conectar con la IA."
- **Sin datos del año anterior para comparación interanual:** La línea de referencia simplemente no se dibuja.
- **Menos de 2 meses con datos:** La tendencia estadística se muestra como 0.0.

---

## Criterios de aceptación

- **CU-E03:** Dado que existen datos en `agg_otp_aerolinea_mes`, cuando el Analista accede al módulo de puntualidad, entonces el sistema muestra el OTP por aerolínea con retraso promedio, causas de retraso en dona, tendencia mensual con variación pp y desglose por día de semana.
- **CU-E04:** Dado que el Analista selecciona una ruta en la página comparativa, cuando existen datos en `agg_rutas_eficiencia` para esa ruta, entonces el sistema muestra el ranking ordinal de aerolíneas con OTP, brecha vs líder en pp, retraso promedio y botón de narrativa IA por aerolínea.
- **CU-E05:** Dado que el Analista visualiza la tendencia mensual con un año específico seleccionado, cuando existen datos del año anterior, entonces el sistema superpone la línea de referencia interanual, muestra la variación pp en la información contextual y el indicador de tendencia estadística con pendiente de regresión lineal.

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
