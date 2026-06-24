# Especificación Estratégica — Dashboard

**Módulo:** Dashboard
**Prefijo:** DSH
**Código fuente:** `app/dashboard/kpis.py`
**Casos de uso cubiertos:** CU-E01 (Ver dashboard de KPIs con filtros), CU-E02 (Detectar y visualizar alertas en KPIs), CU-O14 (Consultar narrativa IA de un gráfico o KPI)
**Actor:** Analista de Datos/Administrador

---

## Funcionalidad 1: Visualizar dashboard de KPIs con filtros (CU-E01)

Dashboard consolidado con KPIs principales, gráficos de tendencia y tabla de aerolíneas, cargado desde agregaciones pre-calculadas con filtros por año, mes y aerolínea. Datos cacheados 5 minutos en memoria.

### RF-DSH-001 — Mostrar KPIs globales en tarjetas
El sistema debe mostrar cuatro tarjetas con indicadores globales: total de vuelos, OTP global (%), tasa de cancelación (%) y retraso promedio (min). Cada KPI debe incluir la variación respecto al mismo período del año anterior.

### RF-DSH-002 — Mostrar gráfico de OTP por aerolínea
El sistema debe mostrar un gráfico de barras con el OTP porcentual por aerolínea para las top 25 por volumen. Debe incluir una línea de umbral mínimo configurable (default 80%). Las barras se colorean según si cumplen (verde) o no (rojo) el umbral.

### RF-DSH-003 — Mostrar gráfico de vuelos por mes
El sistema debe mostrar un gráfico de barras con el volumen de vuelos operados por mes, desglosado por aerolínea (apilado). Debe incluir una línea de total de vuelos cancelados.

### RF-DSH-004 — Mostrar tabla de aerolíneas
El sistema debe mostrar una tabla con las aerolíneas activas (top 25 por volumen) incluyendo: OTP %, total de vuelos, retraso promedio y tasa de cancelación. Debe incluir un indicador de alerta visual si algún KPI cruza el umbral configurado.

### RF-DSH-005 — Filtrar dashboard por año, mes y aerolínea
El sistema debe ofrecer tres filtros (año, mes, aerolínea) que actualizan todo el dashboard sin recargar la página.

### RF-DSH-006 — Cargar datos desde agregaciones pre-calculadas
El sistema debe cargar todos los KPIs, gráficos y tablas exclusivamente desde tablas agregadas, nunca del hecho completo. Los datos se cachean 5 minutos.

### RF-DSH-007 — Navegación rápida a módulos de análisis
Cada tarjeta KPI y cada fila de la tabla de aerolíneas debe incluir un enlace que navega al módulo de análisis correspondiente (puntualidad, cancelaciones) con el filtro de aerolínea pre-seleccionado.

### RNF-DSH-001 — Dashboard responsivo
El sistema debe adaptar el diseño a diferentes tamaños de pantalla. En dispositivos móviles los gráficos se apilan verticalmente.

### RNF-DSH-002 — Cache de página con TTL 5 min
El sistema debe cachear el dashboard completo durante 5 minutos. La caché se invalida al cambiar la configuración de alertas.

---

## Funcionalidad 2: Detectar y visualizar alertas en KPIs (CU-E02)

Alertas automáticas que comparan KPIs contra umbrales configurables almacenados en el repositorio de configuración.

### RF-DSH-008 — Configurar umbrales de alerta desde panel de configuración
El sistema debe leer los umbrales de alerta configurables desde el repositorio del sistema:
- OTP mínimo aceptable (default 0.80)
- Tasa de cancelación máxima (default 0.05)
- Retraso promedio máximo en minutos (default 15)

### RF-DSH-009 — Detectar y visualizar alertas en dashboard
El sistema debe comparar automáticamente los KPIs activos contra los umbrales y mostrar:
- Tarjetas KPI con borde de color (verde si cumple, rojo si excede el umbral)
- Tabla de aerolíneas con filas resaltadas donde OTP < umbral, cancelación > umbral, o retraso > umbral
- Indicador de alerta en la tarjeta KPI correspondiente

### RF-DSH-010 — Mostrar alertas por aerolínea en tabla
El sistema debe mostrar indicadores visuales por cada KPI que cruza su umbral en cada fila de la tabla de aerolíneas. Al pasar el cursor debe mostrar información contextual con el nombre del KPI fuera de rango.

### RNF-DSH-003 — Umbrales cacheados 60 segundos
El sistema debe cachear los umbrales durante 60 segundos. Al guardar cambios desde el panel de configuración, la caché se invalida y los nuevos umbrales aplican en la siguiente carga.

### RNF-DSH-004 — Gráficos generados con Plotly
El sistema debe generar los gráficos del dashboard con Plotly, a diferencia de otros módulos que usan Chart.js.

---

## Funcionalidad 3: Narrativa IA por KPI o gráfico del dashboard (CU-O14)

Generación de narrativa textual contextualizada para KPIs y gráficos del dashboard, servida bajo demanda.

### RF-DSH-011 — Endpoint de narrativa IA
El sistema debe generar narrativa IA contextualizada para los datos del dashboard según los filtros activos, retornando la narrativa, el proveedor utilizado y si la respuesta proviene de caché. La narrativa se muestra en panel emergente al interactuar con un elemento del dashboard. Requiere permiso `dashboard:ver`. Se cachea 300 segundos.

---

## Reglas de negocio

### RN-DSH-001 — Variación calculada contra período anterior igual
La variación de cada KPI se calcula restando el valor del período actual menos el valor del mismo período del año anterior. Si no hay datos del año anterior, no se muestra variación.

### RN-DSH-002 — Umbral por defecto aplicado si no hay configuración
Si no existe configuración de umbrales en el repositorio, se usan los valores por defecto: OTP ≥ 80%, cancelación ≤ 5%, retraso ≤ 15 min.

### RN-DSH-003 — Sin alertas no es estado de error
Si no hay alertas activas, el dashboard muestra los indicadores sin resaltados especiales. No se muestra ningún mensaje de "sin alertas" para evitar ruido visual.

---

## Entradas y salidas

| FUNCIÓN / ENDPOINT | ENTRADAS | SALIDAS |
|---|---|---|
| GET /dashboard | Cookie JWT, year, month, airline | Página HTML con KPIs, gráficos, tabla, alertas |
| GET /dashboard/narrativa | Cookie JWT, year, month, airline | JSON con narrativa IA del dashboard |

---

## Historias de usuario

- **HU-DSH-01:** Como Analista de Datos quiero ver los KPIs globales (vuelos, OTP, cancelaciones, retraso) en tarjetas para tener una visión ejecutiva del estado operacional.
- **HU-DSH-02:** Como Analista de Datos quiero filtrar el dashboard por año, mes y aerolínea para analizar períodos específicos.
- **HU-DSH-03:** Como Analista de Datos quiero que el sistema me alerte visualmente cuando un KPI cruza el umbral configurado para poder tomar acciones correctivas.
- **HU-DSH-04:** Como Analista de Datos quiero ver la variación de cada KPI contra el año anterior para identificar tendencias.
- **HU-DSH-05:** Como Analista de Datos quiero hacer clic en una tarjeta KPI para navegar al módulo de análisis detallado correspondiente.

---

## Objetivo

Proporcionar visibilidad ejecutiva de los indicadores clave de desempeño operacional (vuelos, OTP, cancelaciones, retraso promedio) con alertas automáticas cuando los KPIs cruzan umbrales configurables.

---

## Escenarios

### Camino feliz
1. El Analista accede al dashboard con su sesión activa.
2. El sistema carga datos desde las tablas de agregación.
3. El sistema renderiza 4 tarjetas KPI con variación contra el año anterior, gráficos (OTP por aerolínea y vuelos por mes) y tabla de aerolíneas top 25.
4. El Analista selecciona filtros de año, mes y aerolínea; el dashboard se recarga con los nuevos datos.
5. Los KPIs que cruzan umbrales configurados se muestran con borde rojo e indicador de alerta.

### Manejo de errores
- **Tablas agregadas no disponibles:** Se muestra el mensaje "Los datos no están disponibles. Ejecute el pipeline ELT primero."
- **Error inesperado en carga:** Se captura la excepción y se muestra el mensaje de error en la interfaz.
- **Sin datos del año anterior:** La variación del KPI no se muestra.

---

## Criterios de aceptación

- **CU-E01:** Dado que el Analista accede al dashboard, cuando los datos están disponibles en las agregaciones, entonces el sistema muestra los KPIs globales, gráficos y tabla de aerolíneas con filtros por año, mes y aerolínea.
- **CU-E02:** Dado que existen umbrales configurados en el repositorio de configuración, cuando un KPI cruza el umbral, entonces el sistema muestra una alerta visual (borde rojo, indicador) en la tarjeta o fila de tabla correspondiente.
- **CU-O14:** Consultar narrativa IA de un gráfico o KPI.

---

## Dependencias

- **Seguridad:** Autenticación mediante JWT y autorización por permiso `dashboard:ver`.
- **Pipeline ELT:** Generación de las tablas agregadas `agg_otp_aerolinea_mes` y `agg_kpi_global_dia`.
- **Configuración:** Colección `configuracion_sistema` en PocketBase para umbrales de alerta.

---

## Casos de uso relacionados

- CU-E01 (Ver dashboard de KPIs con filtros)
- CU-E02 (Detectar y visualizar alertas en KPIs)
- CU-O14 (Consultar narrativa IA de un gráfico o KPI — endpoint `GET /dashboard/narrativa`)

---

## Fuera de alcance

- Exportación del dashboard a PDF, imagen o CSV.
- Edición de datos de origen desde el dashboard.
- Programación de alertas por email, Slack u otras notificaciones push.
- Personalización de umbrales por usuario (los umbrales son globales y aplican a todos los roles).
- Análisis predictivo o proyecciones desde el dashboard (cubierto en el módulo Predictivo).
