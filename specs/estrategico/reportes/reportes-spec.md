# Especificación Estratégica — Reportes

**Módulo:** Reportes
**Prefijo:** REP
**Código fuente:** `app/reportes/`
**Casos de uso cubiertos:** CU-E11 (Generar reporte ejecutivo PDF por aerolínea y período), CU-E12 (Exportar datos analíticos a Excel con múltiples hojas), CU-E13 (Exportar datos filtrados a CSV)
**Actor:** Analista de Datos/Administrador

---

## Funcionalidad 1: Generar reporte PDF ejecutivo (CU-E11)

Exporta un reporte analítico en PDF con hasta 8 secciones seleccionables, gráficos SVG inline, KPIs y tablas. Si la librería de generación de PDF no está instalada en el servidor, el PDF se deshabilita con mensaje informativo al usuario.

### RF-REP-001 — Generar PDF con 8 secciones seleccionables
El sistema debe generar un PDF recibiendo filtros y una lista de secciones seleccionables. Cada sección equivale a un análisis: resumen de KPIs, OTP mensual, top aerolíneas, causas de retraso, peores rutas, día de semana, cancelaciones y rutas. Si no se envía la lista, se incluyen todas las secciones por defecto.

### RF-REP-002 — Gráficos SVG inline en PDF
El sistema debe incluir en el PDF gráficos generados como SVG nativo: línea para tendencia OTP mensual, barras horizontales para distribución de causas, barras verticales para OTP por aerolínea, día y ruta. Los colores deben seguir los umbrales de cumplimiento: verde ≥ 80%, ámbar 70–79%, rojo < 70%.

### RF-REP-003 — KPIs en portada del PDF
El sistema debe mostrar en la primera sección del PDF cuatro KPIs en tarjetas: Total Vuelos, OTP Global (con umbral 80%), Tasa Cancelación y Retraso Promedio. Cada KPI debe tener color indicativo según su valor.

### RF-REP-004 — Subida a MinIO + URL firmada
El sistema debe subir el PDF generado al repositorio de almacenamiento y retornar una URL firmada con validez de 1 hora. Si la subida falla, el PDF se sirve directamente como respuesta de streaming.

### RF-REP-005 — Filtros disponibles para PDF
El sistema debe aplicar los mismos filtros para todas las exportaciones: año, trimestre, mes, día de semana, aerolínea, aeropuerto origen, aeropuerto destino, código de cancelación FAA (A/B/C/D) y flag de solo cancelados.

---

## Funcionalidad 2: Exportar Excel multi-hoja (CU-E12)

Exporta un archivo `.xlsx` con 8 hojas de datos, cada una con gráficos embebidos y formato condicional.

### RF-REP-006 — Excel con 8 hojas y gráficos embebidos
El sistema debe generar un archivo Excel con 8 hojas: Resumen Ejecutivo (portada con métricas globales), Puntualidad OTP por aerolínea (gráfico de barras), Tendencia Mensual (gráfico de línea), Causas de Retraso (gráfico de barras + desglose por aerolínea), Rutas con peor OTP (gráfico de barras), OTP por Día de Semana (gráfico de barras), Cancelaciones FAA (gráfico circular), Rutas Eficientes (tabla con colores condicionales).

### RF-REP-007 — Formato condicional en Excel
El sistema debe colorear las celdas de OTP con fondo verde (≥ 85%), ámbar (70–84%) o rojo (< 70%). Las filas pares deben tener fondo azul claro alternado. El índice de eficiencia de rutas debe colorearse: verde ≤ 1.05, ámbar ≤ 1.15, rojo > 1.15.

### RF-REP-008 — Resumen ejecutivo como primera hoja
El sistema debe insertar al inicio la hoja "Resumen Ejecutivo" con: título, fecha de generación, filtros aplicados, métricas globales y tabla de contenido con descripción de cada hoja.

---

## Funcionalidad 3: Exportar CSV datos crudos (CU-E13)

Exporta el hecho filtrado como CSV con 14 columnas seleccionadas.

### RF-REP-009 — CSV con columnas analíticas seleccionadas
El sistema debe exportar las siguientes 14 columnas del hecho: FlightDate, Reporting_Airline, OriginCode, DestCode, Cancelled, CancellationCode, Diverted, ArrDel15, DepDel15, ArrDelayMinutes, DepDelayMinutes, ActualElapsedTime, CRSElapsedTime, Distance. Codificación UTF-8.

### RF-REP-010 — Historial de exportaciones en MinIO
El sistema debe subir toda exportación (PDF, Excel, CSV) al repositorio de almacenamiento con ciclo de vida de 7 días. El historial debe listar las últimas 50 exportaciones con nombre, tipo, fecha, tamaño y URL de descarga firmada (1h).

---

### RNF-REP-001 — Librería de PDF opcional
El sistema debe manejar de forma degradada la ausencia de la librería de generación de PDF: el endpoint retorna error 501 y la interfaz muestra un mensaje informativo. Las exportaciones a Excel y CSV no dependen de esta librería.

### RNF-REP-002 — Tiempo de generación
El sistema debe completar la generación de PDF en menos de 30s para conjuntos de datos típicos (menos de 200K registros). La generación de Excel debe completarse en menos de 20s.

### RNF-REP-003 — Exportaciones no bloquean al usuario
El sistema debe mostrar un indicador de carga durante la generación de exportaciones. El procesamiento es síncrono con timeout generoso.

### RNF-REP-004 — Almacenamiento externo
El sistema debe almacenar los archivos generados en el repositorio de almacenamiento (bucket `aerotrack-exports`) con ciclo de vida de 7 días. No se almacenan en el sistema de archivos local ni en la base de datos.

---

### RN-REP-001 — Bucket exports con lifecycle
El sistema debe crear el bucket de exportaciones automáticamente al primer acceso con una regla de ciclo de vida que expira objetos a los 7 días, evitando acumulación de archivos temporales.

### RN-REP-002 — URL firmada con expiración de 1 hora
Las URLs de descarga se generan con expiración de 1 hora. Pasado ese tiempo, el usuario debe regenerar la exportación.

### RN-REP-003 — Cada exportación tiene contenido diferente según el formato
PDF = dashboard analítico con KPIs, gráficos SVG y tablas resumen. Excel = 8 hojas con datos granulares y gráficos embebidos. CSV = hecho filtrado (14 columnas). No existe un único contenido renderizado a distintos formatos.

---

## Entradas y salidas

| CU | Entrada | Salida |
|----|---------|--------|
| CU-E11 | filtros (año, trimestre, mes, dow, aerolínea, origen, destino, cancel_code, solo_cancelados) + secciones (lista de 8) | PDF con KPIs, gráficos SVG inline y tablas. Retorna JSON con URL firmada o descarga directa. |
| CU-E12 | filtros (mismos que PDF) | .xlsx con 8 hojas + gráficos embebidos. StreamingResponse. |
| CU-E13 | filtros (mismos que PDF) | .csv UTF-8 con 14 columnas del hecho. StreamingResponse. |

---

## Escenarios

### Camino feliz — Exportación PDF
1. El Analista accede al panel de reportes, selecciona filtros y visualiza la vista previa.
2. El Analista selecciona las secciones a incluir y hace clic en "Generar PDF".
3. El sistema procesa los datos desde las tablas de agregación y el hecho enriquecido.
4. La librería de PDF convierte el HTML+CSS+SVG a PDF.
5. El PDF se sube al repositorio de almacenamiento y se retorna la URL firmada para descarga.

### Camino feliz — Exportación Excel
1. El Analista configura los mismos filtros y hace clic en "Descargar Excel".
2. El sistema carga el hecho y las tablas de agregación, genera 8 hojas con gráficos embebidos y formato condicional.
3. El archivo se sirve como respuesta de streaming.

### Camino feliz — Exportación CSV
1. El Analista hace clic en "Descargar CSV".
2. El sistema carga el hecho filtrado, selecciona las 14 columnas y serializa a CSV UTF-8.
3. El archivo se sirve como respuesta de streaming.

### Manejo de errores
- **Librería de PDF no instalada:** El endpoint retorna 501 con mensaje claro. La interfaz muestra advertencia preventiva.
- **Error al cargar datos:** Si las tablas de agregación están vacías o el pipeline no se ha ejecutado, retorna error descriptivo.
- **Timeout en generación:** Si la consulta al repositorio de almacenamiento excede el tiempo esperado, el historial muestra error parcial.
- **Error en subida al repositorio:** La exportación se descarga directamente vía streaming como fallback.

---

## Criterios de aceptación

- **CU-E11:** Dado que el Analista selecciona filtros y secciones en el panel de reportes, cuando genera un PDF, entonces el sistema produce un documento con KPIs, gráficos SVG inline y tablas seleccionadas, lo sube al repositorio de almacenamiento y retorna una URL firmada o descarga directa.
- **CU-E12:** Dado que el Analista configura filtros en el panel, cuando solicita exportar a Excel, entonces el sistema genera un archivo .xlsx con 8 hojas, gráficos embebidos y formato condicional, y lo sirve como descarga.
- **CU-E13:** Dado que el Analista configura filtros en el panel, cuando solicita exportar a CSV, entonces el sistema genera un archivo CSV UTF-8 con 14 columnas del hecho filtrado y lo sirve como descarga.

---

## Dependencias

- **Seguridad:** Autenticación JWT y autorización con permisos `reportes:ver` (vista previa) y `reportes:exportar` (exportaciones).
- **Pipeline ELT:** Tablas de agregación (`agg_otp_aerolinea_mes`, `agg_causas_retraso_mes`, `agg_rutas_eficiencia`, `agg_otp_dia_semana`) y hecho enriquecido en MinIO.
- **WeasyPrint:** Librería Python para conversión HTML+CSS → PDF (opcional, degradación controlada).
- **openpyxl:** Librería Python para generación de archivos Excel .xlsx con gráficos.
- **MinIO:** Bucket `aerotrack-exports` para almacenamiento temporal de exportaciones (lifecycle 7 días).

---

## Casos de uso relacionados

- CU-E11 (Generar reporte ejecutivo PDF por aerolínea y período)
- CU-E12 (Exportar datos analíticos a Excel con múltiples hojas)
- CU-E13 (Exportar datos filtrados a CSV)

---

## Historias de usuario

- Como Analista de Datos, quiero generar un reporte PDF con KPIs y gráficos seleccionables, para compartir el análisis operacional con el equipo directivo sin necesidad de acceso al sistema.
- Como Analista de Datos, quiero exportar los datos a Excel con múltiples hojas y gráficos, para realizar análisis complementarios en herramientas de escritorio.
- Como Analista de Datos, quiero descargar los datos crudos en CSV, para importarlos a herramientas de BI externas o realizar validaciones ad-hoc.
- Como Analista de Datos, quiero ver una vista previa de los datos antes de exportar, para confirmar que los filtros seleccionados producen el resultado esperado.
- Como Analista de Datos, quiero consultar el historial de exportaciones recientes, para re-descargar un archivo sin tener que regenerarlo.

---

## Fuera de alcance

- Exportación a otros formatos (Word, PowerPoint, JSON, Parquet).
- Programación de exportaciones automáticas recurrentes.
- Envío de exportaciones por email.
- Personalización de columnas en CSV (siempre las mismas 14).
- Edición del contenido del PDF (solo selección de secciones predefinidas).
- Almacenamiento permanente de exportaciones (lifecycle forzado a 7 días).
- Comparación multi-período en un mismo reporte.
