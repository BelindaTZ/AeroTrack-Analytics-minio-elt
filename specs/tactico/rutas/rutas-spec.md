# Especificación Táctica — Rutas

**Módulo:** Rutas
**Prefijo:** RUT
**Código fuente:** `app/rutas/ranking_eficiencia.py`
**Casos de uso cubiertos:** CU-E06 (Evaluar rendimiento de rutas), CU-E07 (Comparar tiempo real vs programado por ruta), CU-O14 (Consultar narrativa IA de un gráfico o KPI)
**Actor:** Analista de Datos/Administrador

---

## Funcionalidad 1: Evaluar rendimiento de rutas (CU-E06)

Ranking de eficiencia de rutas con índice compuesto basado en la diferencia entre tiempo real y programado, complementado con gráfico de dispersión y tabla detallada.

### RF-RUT-001 — Mostrar ranking de eficiencia por ruta
El sistema debe mostrar una tabla con las rutas ordenadas por índice de eficiencia ascendente (menos eficientes primero). Las columnas son: ruta (origen-destino), vuelos, OTP %, tiempo real promedio, tiempo programado promedio, retraso promedio (min), índice de eficiencia (%) e indicador de alerta visual para rutas ineficientes.

### RF-RUT-002 — Mostrar gráfico de dispersión eficiencia vs volumen
El sistema debe mostrar un gráfico de dispersión con el índice de eficiencia en el eje X y el total de vuelos en el eje Y. Cada punto representa una ruta. Las rutas del percentil inferior (menos eficientes) se distinguen visualmente.

### RF-RUT-003 — Calcular índice de eficiencia
El sistema debe calcular el índice de eficiencia de cada ruta como: `((tiempo_real_avg - tiempo_prog_avg) / tiempo_prog_avg) * 100`. Valor positivo = ruta más lenta de lo programado (ineficiente). Valor negativo = ruta más rápida (eficiente).

### RF-RUT-004 — Filtrar por año, aerolínea y mes
El sistema debe ofrecer tres filtros (año, aerolínea, mes) que actualizan el módulo sin recargar la página.

### RF-RUT-005 — Mostrar tabla de resumen por aerolínea en ruta
El sistema debe permitir expandir una fila de ruta para mostrar el desglose por aerolínea que opera esa ruta: OTP %, retraso promedio, índice de eficiencia y vuelos.

### RNF-RUT-001 — Datos cacheados 5 minutos
El sistema debe cachear los datos del módulo durante 5 minutos.

### RNF-RUT-002 — Límite inferior de 10 vuelos por ruta
Las rutas con menos de 10 vuelos no se incluyen en el ranking.

---

## Funcionalidad 2: Comparar tiempo real vs programado por ruta (CU-E07)

Análisis detallado de la brecha entre el tiempo operado y el programado para cada ruta.

### RF-RUT-006 — Mostrar comparación tiempo real vs programado
El sistema debe mostrar un gráfico de barras agrupadas con el tiempo real promedio y el tiempo programado promedio para las rutas de mayor volumen.

### RF-RUT-007 — Calcular brecha de tiempo
El sistema debe calcular la brecha de tiempo como: `tiempo_real_avg - tiempo_prog_avg`. Valor positivo indica que la ruta toma más tiempo del programado (retraso sistemático). Valor negativo indica que se completa antes.

### RF-RUT-008 — Mostrar tabla de rutas con brecha
El sistema debe mostrar una tabla con columnas: ruta, tiempo real (min), tiempo programado (min), brecha (min) y brecha (%). La brecha en minutos es la diferencia absoluta; la brecha porcentual es el índice de eficiencia.

### RF-RUT-009 — Narrativa IA por ruta
Por cada ruta en la tabla, el sistema debe ofrecer la opción de obtener narrativa IA mostrando la eficiencia de la ruta, brecha de tiempo y recomendaciones contextuales.

### RF-RUT-010 — Página de detalle por ruta
El sistema debe mostrar un análisis completo de una ruta específica (en formato ORIGEN-DESTINO): métricas de eficiencia, brecha tiempo real vs programado, desglose por aerolínea y narrativa IA contextualizada. El filtro de año es opcional.

### RNF-RUT-003 — Orden descendente por volumen por defecto
El sistema debe ordenar la tabla de rutas por total de vuelos descendente para mostrar primero las rutas con mayor impacto operacional.

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
1. El Analista accede al módulo de rutas con su sesión activa y filtros opcionales (año, aerolínea, mes).
2. El sistema carga datos desde la tabla de agregación de eficiencia de rutas y aplica los filtros seleccionados.
3. El sistema muestra el ranking de rutas ordenadas por índice de eficiencia ascendente, gráfico de dispersión eficiencia vs volumen y tabla desglosada por aerolínea.
4. El Analista expande una fila de ruta; el sistema muestra el detalle por aerolínea con OTP %, retraso promedio e índice de eficiencia.
5. El Analista hace clic en el botón de narrativa IA de una ruta; el sistema abre un panel emergente con el contexto de eficiencia y brecha de tiempo.

### Manejo de errores
- **Tabla agregada no disponible:** Se muestra mensaje indicando que el pipeline ELT debe ejecutarse primero.
- **Error inesperado en carga de datos:** Se captura la excepción y se muestra el mensaje de error en la interfaz.
- **Sin rutas que cumplan el mínimo de 10 vuelos:** Se muestra un estado vacío indicando que no hay datos suficientes.

---

## Criterios de aceptación

- **CU-E06:** Dado que existen datos en `agg_rutas_eficiencia`, cuando el Analista accede al módulo de rutas, entonces el sistema muestra el ranking de eficiencia con índice compuesto, gráfico de dispersión eficiencia vs volumen y tabla de resumen por aerolínea.
- **CU-E07:** Dado que el Analista visualiza una ruta específica con datos disponibles, entonces el sistema muestra la brecha entre tiempo real promedio y tiempo programado promedio en minutos y porcentaje (índice de eficiencia).

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
