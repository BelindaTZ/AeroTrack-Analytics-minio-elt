# Especificación Estratégica — Dashboard

**Módulo:** Dashboard
**Prefijo:** DSH
**Código fuente:** `app/dashboard/kpis.py`
**Casos de uso cubiertos:** CU-E01 (Ver dashboard de KPIs con filtros), CU-E02 (Detectar y visualizar alertas en KPIs)
**Actor:** Analista de Datos

---

## Funcionalidad 1: Visualizar dashboard de KPIs con filtros (CU-E01)

Dashboard consolidado con KPIs principales, gráficos de tendencia y tabla de aerolíneas, cargado desde agregaciones pre-calculadas con filtros por año, mes y aerolínea. Cacheado 5 min en memoria (`_page_cache`).

### RF-DSH-001 — Mostrar KPIs globales en tarjetas
El dashboard muestra 4 tarjetas con indicadores globales: total de vuelos, OTP global (%), tasa de cancelación (%), retraso promedio (min). Cada KPI incluye variación vs período anterior (año anterior), obtenida mediante segunda carga de `agg_otp_aerolinea_mes` con year-1.

### RF-DSH-002 — Mostrar gráfico de OTP por aerolínea
Gráfico de barras (Plotly, `plotly.graph_objects`) mostrando OTP % por aerolínea para las top 25 por volumen. Incluye línea de umbral OTP mínimo configurable (por defecto 80%). Las barras se colorean según cumplan (verde) o no (rojo) el umbral.

### RF-DSH-003 — Mostrar gráfico de vuelos por mes
Gráfico de barras (Plotly) mostrando volumen de vuelos operados por mes, desglosado por aerolínea (stacked). Incluye línea de total cancelados.

### RF-DSH-004 — Mostrar tabla de aerolíneas
Tabla con las aerolíneas activas (top 25 por volumen) mostrando: OTP %, total vuelos, retraso promedio, tasa de cancelación. Incluye indicador de alerta (icono) si algún KPI cruza el umbral configurado.

### RF-DSH-005 — Filtrar dashboard por año, mes y aerolínea
Tres selectores (año, mes, aerolínea) que recargan todo el dashboard vía fetch con reemplazo de contenido HTML y Chart.js/Plotly mediante `renderCharts()`.

### RF-DSH-006 — Cargar datos desde agregaciones pre-calculadas
Todos los KPIs, gráficos y tablas se cargan desde tablas agregadas (`agg_otp_aerolinea_mes`, `agg_kpi_global_dia`), nunca del fact table completo. Los datos se cachean 5 minutos en `_page_cache`.

### RF-DSH-007 — Navegación rápida a módulos de análisis
Cada tarjeta KPI y cada fila de la tabla de aerolíneas incluye un enlace que navega al módulo de análisis correspondiente (puntualidad, cancelaciones) con el filtro de aerolínea pre-seleccionado.

### RNF-DSH-001 — Dashboard responsivo
El diseño se adapta a diferentes tamaños de pantalla usando CSS Grid con `auto-fit` y `minmax`. En móvil los gráficos se apilan verticalmente.

### RNF-DSH-002 — Cache de página con TTL 5 min
El dashboard completo se cachea en `_page_cache` con `_PAGE_TTL = 300` segundos. La caché se invalida al cambiar la configuración de alertas.

---

## Funcionalidad 2: Detectar y visualizar alertas en KPIs (CU-E02)

Alertas automáticas que comparan KPIs contra umbrales configurables, almacenados en PocketBase colección `configuracion_sistema`.

### RF-DSH-008 — Configurar umbrales de alerta desde panel de configuración
Tres umbrales configurables almacenados en `configuracion_sistema` con clave `alerta_*`:
- `alerta_otp_umbral_min` (float, default 0.80): OTP mínimo aceptable (80%)
- `alerta_cancelacion_max` (float, default 0.05): tasa de cancelación máxima (5%)
- `alerta_retraso_minutos` (float, default 15): retraso promedio máximo en minutos

### RF-DSH-009 — Detectar y visualizar alertas en dashboard
El sistema compara automáticamente los KPIs activos contra los umbrales y muestra:
- Tarjetas KPI con borde de color (verde si cumple, rojo si excede el umbral)
- Tabla de aerolíneas con filas resaltadas donde OTP < umbral, cancelación > umbral, o retraso > umbral
- Badge "Alerta" en la tarjeta KPI correspondiente

### RF-DSH-010 — Mostrar alertas por aerolínea en tabla
Cada fila de la tabla de aerolíneas muestra indicadores visuales (iconos rojos/verdes) por cada KPI que cruza su umbral. Al pasar el mouse muestra tooltip con el nombre del KPI fuera de rango.

### RNF-DSH-003 — Umbrales cacheados 60 segundos
Los umbrales se cargan desde PocketBase con `_UMBRALES_TTL = 60` segundos. Al guardar cambios desde el panel de configuración se invoca `invalidar_cache_alertas()` que limpia ambas cachés.

### RNF-DSH-004 — Gráficos generados con Plotly
Los gráficos del dashboard usan `plotly.graph_objects` (no Chart.js), a diferencia del resto del sistema. Se renderizan como HTML estático embebido con `plotly.js`.

---

## Reglas de negocio

### RN-DSH-001 — Variación calculada contra período anterior igual
La variación de cada KPI (flecha arriba/abajo) se calcula restando el valor del período actual menos el valor del mismo período en el año anterior. Si no hay datos del año anterior, no se muestra variación.

### RN-DSH-002 — Umbral por defecto aplicado si no hay configuración
Si no existe configuración de umbrales en PocketBase, se usan los valores por defecto: OTP ≥ 80%, cancelación ≤ 5%, retraso ≤ 15 min.

### RN-DSH-003 — Sin alertas no es estado de error
Si no hay alertas activas, el dashboard muestra los indicadores sin resaltados especiales. No se muestra ningún mensaje de "sin alertas" para evitar ruido visual.

---

## Entradas y salidas

| FUNCIÓN / ENDPOINT | ENTRADAS | SALIDAS |
|---|---|---|
| GET /dashboard | Cookie JWT, year, month, airline | Página HTML con KPIs, gráficos Plotly, tabla, alertas |
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
1. El Analista accede a `GET /dashboard` con su Cookie JWT.
2. El sistema carga datos desde las tablas agregadas `agg_otp_aerolinea_mes` y `agg_kpi_global_dia`.
3. El sistema renderiza 4 tarjetas KPI con variación contra el año anterior, gráficos Plotly (OTP por aerolínea y vuelos por mes) y tabla de aerolíneas top 25.
4. El Analista selecciona filtros de año, mes y aerolínea; el dashboard se recarga vía fetch con reemplazo de contenido HTML.
5. Los KPIs que cruzan umbrales configurados se muestran con borde rojo y badge "Alerta".

### Manejo de errores
- **Tablas agregadas no disponibles (FileNotFoundError):** Se muestra el mensaje "Los datos no están disponibles. Ejecute el pipeline ELT primero."
- **Error inesperado en carga:** Se captura la excepción y se muestra "Error al cargar datos: {mensaje}" en la interfaz.
- **Sin datos del año anterior:** La variación del KPI no se muestra (no se genera error).

---

## Criterios de aceptación

- **CU-E01:** Dado que el Analista accede al dashboard, cuando los datos están disponibles en las agregaciones, entonces el sistema muestra los KPIs globales, gráficos Plotly y tabla de aerolíneas con filtros por año, mes y aerolínea.
- **CU-E02:** Dado que existen umbrales configurados en `configuracion_sistema` de PocketBase, cuando un KPI cruza el umbral, entonces el sistema muestra una alerta visual (borde rojo, badge) en la tarjeta o fila de tabla correspondiente.

---

## Dependencias

- **Seguridad:** Autenticación mediante JWT y autorización por permiso `dashboard:ver`.
- **Pipeline ELT:** Generación de las tablas agregadas `agg_otp_aerolinea_mes` y `agg_kpi_global_dia`.
- **Configuración:** Colección `configuracion_sistema` en PocketBase para umbrales de alerta.

---

## Casos de uso relacionados

- CU-E01 (Ver dashboard de KPIs con filtros)
- CU-E02 (Detectar y visualizar alertas en KPIs)

---

## Fuera de alcance

- Exportación del dashboard a PDF, imagen o CSV.
- Edición de datos de origen desde el dashboard.
- Programación de alertas por email, Slack u otras notificaciones push.
- Personalización de umbrales por usuario (los umbrales son全局es y aplican a todos los roles).
- Análisis predictivo o proyecciones desde el dashboard (cubierto en el módulo Predictivo).
