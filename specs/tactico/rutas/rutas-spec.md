# Especificación Táctica — Rutas

**Módulo:** Rutas
**Prefijo:** RUT
**Código fuente:** `app/rutas/ranking_eficiencia.py`
**Casos de uso cubiertos:** CU-E06 (Evaluar rendimiento de rutas), CU-E07 (Comparar tiempo real vs programado por ruta), CU-O14 (Consultar narrativa IA de un gráfico o KPI)
**Actor:** Analista de Datos

---

## Funcionalidad 1: Evaluar rendimiento de rutas (CU-E06)

Ranking de eficiencia de rutas con índice compuesto basado en la diferencia entre tiempo real y programado, complementado con gráfico de dispersión y tabla detallada.

### RF-RUT-001 — Mostrar ranking de eficiencia por ruta
Tabla con las rutas ordenadas por `indice_eficiencia` ascendente (menos eficientes primero). Columnas: Ruta (origen-destino), Vuelos, OTP %, Tiempo real prom., Tiempo programado prom., Retraso prom. (min), Índice eficiencia (%), Indicador de alerta (rojo si ineficiente).

### RF-RUT-002 — Mostrar gráfico de dispersión eficiencia vs volumen
Gráfico de dispersión (Chart.js) con `indice_eficiencia` en eje X y `total_vuelos` en eje Y. Cada punto es una ruta. Se distinguen visualmente las rutas en el percentil inferior (menos eficientes).

### RF-RUT-003 — Calcular índice de eficiencia
`indice_eficiencia = ((tiempo_real_avg - tiempo_prog_avg) / tiempo_prog_avg) * 100`. Valor positivo = ruta más lenta de lo programado (ineficiente). Valor negativo = ruta más rápida (eficiente).

### RF-RUT-004 — Filtrar por año, aerolínea y mes
Tres selectores que recargan el módulo vía fetch. Datos cargados desde `agg_rutas_eficiencia`.

### RF-RUT-005 — Mostrar tabla de resumen por aerolínea en ruta
Expansión de fila de ruta que muestra el desglose por aerolínea que opera esa ruta: OTP %, retraso prom., índice de eficiencia, vuelos.

### RNF-RUT-001 — Datos cacheados 5 minutos
El módulo se cachea en `_page_cache` con `_PAGE_TTL = 300` segundos.

### RNF-RUT-002 — Límite inferior de 10 vuelos por ruta
Las rutas con menos de 10 vuelos no se incluyen en el ranking. Filtro aplicado en la pipeline (`a4 = a4[a4["total_vuelos"] >= 10]`).

---

## Funcionalidad 2: Comparar tiempo real vs programado por ruta (CU-E07)

Análisis detallado de la brecha entre el tiempo operado y el programado para cada ruta, con visualización de desviaciones.

### RF-RUT-006 — Mostrar comparación tiempo real vs programado
Gráfico de barras agrupadas (Chart.js) mostrando tiempo real promedio y tiempo programado promedio para las top N rutas por volumen.

### RF-RUT-007 — Calcular brecha de tiempo
`brecha_min = tiempo_real_avg - tiempo_prog_avg`. Valor positivo = la ruta toma más tiempo del programado (retraso sistemático). Negativo = la ruta se completa antes.

### RF-RUT-008 — Mostrar tabla de rutas con brecha
Tabla detallada con columnas: Ruta, Tiempo real (min), Tiempo programado (min), Brecha (min), Brecha (%). La brecha en minutos es la diferencia absoluta; la brecha en % es el `indice_eficiencia`.

### RF-RUT-009 — Narrativa IA por ruta
Botón por fila que abre popover con narrativa IA mostrando la eficiencia de la ruta, brecha de tiempo y recomendaciones contextuales.

### RF-RUT-010 — Página de detalle por ruta
`GET /rutas/{ruta}/detalle` (donde `{ruta}` es código en formato `AAA-BBB`) muestra análisis completo de una ruta específica: métricas de eficiencia, brecha tiempo real vs programado, desglose por aerolínea, y narrativa IA contextualizada. El parámetro de año es opcional.

### RNF-RUT-003 — Orden descendente por volumen por defecto
La tabla de rutas se ordena por `total_vuelos` descendente para mostrar primero las rutas con mayor impacto operacional.

---

## Reglas de negocio

### RN-RUT-001 — Índice de eficiencia positivo = menos eficiente
Un índice de eficiencia positivo indica que el vuelo tomó más tiempo del programado (menos eficiente). Negativo indica que tomó menos tiempo (más eficiente).

### RN-RUT-002 — Percentil inferior marcado como alerta
Las rutas en el percentil inferior de eficiencia se marcan visualmente en rojo y con indicador de alerta en la tabla. El percentil se calcula sobre el conjunto filtrado.

### RN-RUT-003 — Mínimo 10 vuelos para inclusión
Toda ruta debe tener al menos 10 vuelos en el período para ser considerada en el ranking de eficiencia.

---

## Entradas y salidas

| FUNCIÓN / ENDPOINT | ENTRADAS | SALIDAS |
|---|---|---|
| GET /rutas | Cookie JWT, year, airline, month | Página HTML con ranking de eficiencia, gráfico dispersión, tabla |
| GET /rutas/narrativa | Cookie JWT, ruta, year, airline | JSON con narrativa IA de la ruta (CU-O14) |
| GET /rutas/{ruta}/detalle | Cookie JWT, ruta (ej. ATL-DFW), year, airline | Página HTML con análisis detallado de una ruta específica |

---

## Historias de usuario

- **HU-RUT-01:** Como Analista de Datos quiero ver un ranking de rutas ordenadas por eficiencia para identificar las rutas con peor desempeño operacional.
- **HU-RUT-02:** Como Analista de Datos quiero ver la brecha entre tiempo real y programado por ruta para cuantificar el impacto de retrasos sistemáticos.
- **HU-RUT-03:** Como Analista de Datos quiero ver un gráfico de dispersión eficiencia vs volumen para identificar patrones entre rutas.
- **HU-RUT-04:** Como Analista de Datos quiero filtrar por aerolínea para evaluar solo las rutas de un operador específico.

---

## Objetivo

Evaluar el rendimiento y eficiencia de las rutas operadas mediante un índice compuesto basado en la desviación entre tiempo real y programado, permitiendo identificar rutas ineficientes y cuantificar la brecha operacional.

---

## Escenarios

### Camino feliz
1. El Analista accede a `GET /rutas` con su Cookie JWT y filtros opcionales (año, aerolínea, mes).
2. El sistema carga datos desde `agg_rutas_eficiencia` y aplica los filtros seleccionados.
3. El sistema muestra el ranking de rutas ordenadas por `indice_eficiencia` ascendente (menos eficientes primero), gráfico de dispersión eficiencia vs volumen y tabla desglosada por aerolínea.
4. El Analista expande una fila de ruta; el sistema muestra el detalle por aerolínea con OTP %, retraso promedio e índice de eficiencia.
5. El Analista hace clic en el botón de narrativa IA de una ruta; el sistema abre un popover con el contexto de eficiencia y brecha de tiempo.

### Manejo de errores
- **Tabla agregada no disponible (FileNotFoundError):** Se muestra mensaje indicando que el pipeline ELT debe ejecutarse primero.
- **Error inesperado en carga de datos:** Se captura la excepción y se muestra el mensaje de error en la interfaz.
- **Sin rutas que cumplan el mínimo de 10 vuelos:** Se muestra un estado vacío indicando que no hay datos suficientes.

---

## Criterios de aceptación

- **CU-E06:** Dado que existen datos en `agg_rutas_eficiencia`, cuando el Analista accede al módulo de rutas, entonces el sistema muestra el ranking de eficiencia con índice compuesto, gráfico de dispersión eficiencia vs volumen y tabla de resumen por aerolínea.
- **CU-E07:** Dado que el Analista visualiza una ruta específica con datos disponibles, entonces el sistema muestra la brecha entre tiempo real promedio y tiempo programado promedio en minutos y porcentaje (`indice_eficiencia`).

---

## Dependencias

- **Seguridad:** Autenticación mediante JWT y autorización por permiso `rutas:ver`.
- **Pipeline ELT:** Generación de la tabla agregada `agg_rutas_eficiencia`.

---

## Casos de uso relacionados

- CU-E06 (Evaluar rendimiento de rutas)
- CU-E07 (Comparar tiempo real vs programado por ruta)
- CU-O14 (Consultar narrativa IA de un gráfico o KPI — endpoint `GET /rutas/narrativa`)

---

## Fuera de alcance

- Exportación del ranking de rutas a PDF o CSV.
- Edición de tiempos programados, reales o cualquier dato de origen.
- Análisis de rentabilidad económica o costos operacionales por ruta.
- Comparación histórica de eficiencia entre múltiples períodos en una misma vista.
- Simulación de cambios en tiempos programados para optimizar eficiencia.

---

## Glosario
