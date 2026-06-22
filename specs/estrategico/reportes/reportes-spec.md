# Especificación Estratégica — Reportes

**Módulo:** Reportes
**Prefijo:** REP
**Código fuente:** `app/reportes/`
**Casos de uso cubiertos:** CU-E11 (Generar reporte ejecutivo PDF por aerolínea y período), CU-E12 (Exportar datos analíticos a Excel con múltiples hojas), CU-E13 (Exportar datos filtrados a CSV)
**Actor:** Analista de Datos

---

## Funcionalidad 1: Generar reporte PDF ejecutivo (CU-E11)

Exporta un reporte analítico en PDF con 8 secciones seleccionables, gráficos SVG inline, KPIs y tablas. Implementado en `app/reportes/generar_pdf.py`. Usa WeasyPrint (HTML+CSS → PDF). Si WeasyPrint no está instalado en el servidor, el PDF se deshabilita con mensaje informativo al usuario.

### RF-REP-001 — Generar PDF con 8 secciones seleccionables
`POST /reportes/pdf` recibe filtros y una lista de secciones (`secciones`). Cada sección equivale a un análisis: `kpis`, `otp_mensual`, `top_aerolineas`, `causas_retraso`, `peores_rutas`, `dia_semana`, `cancelaciones`, `rutas`. Si no se envía la lista, se incluyen todas por defecto.

### RF-REP-002 — Gráficos SVG inline en PDF
El PDF incluye gráficos generados como SVG nativo (sin librería externa): línea para tendencia OTP mensual, barras horizontales para distribución de causas, barras verticales para OTP por aerolínea/día/ruta. Colores condicionales según umbrales: verde ≥80%, ámbar 70–79%, rojo <70%.

### RF-REP-003 — KPIs en portada del PDF
La primera sección muestra 4 KPIs en tarjetas: Total Vuelos, OTP Global (con umbral 80%), Tasa Cancelación y Retraso Promedio. Cada KPI tiene color semáforo según su valor.

### RF-REP-004 — Subida a MinIO + URL firmada
El PDF generado se sube al bucket `aerotrack-exports` (contenedor `reportes/`) y se retorna una URL firmada con validez de 1 hora. Si la subida falla, el PDF se descarga directamente como `StreamingResponse`.

### RF-REP-005 — Filtros disponibles para PDF
Los mismos filtros aplican a todas las exportaciones: año, trimestre, mes, día de semana, aerolínea, aeropuerto origen, aeropuerto destino, código de cancelación FAA (A/B/C/D) y flag solo cancelados.

---

## Funcionalidad 2: Exportar Excel multi-hoja (CU-E12)

Exporta un archivo `.xlsx` con openpyxl que incluye 8 hojas de datos, cada una con gráficos embebidos y formato condicional. Implementado en `app/reportes/generar_excel.py`.

### RF-REP-006 — Excel con 8 hojas y gráficos embebidos
El archivo contiene: Resumen Ejecutivo (portada con métricas globales), Puntualidad OTP por aerolínea (bar chart), Tendencia Mensual (line chart), Causas de Retraso (bar chart + desglose por aerolínea), Rutas con peor OTP (bar chart), OTP por Día de Semana (bar chart), Cancelaciones FAA (pie chart), Rutas Eficientes (tabla con colores condicionales).

### RF-REP-007 — Formato condicional en Excel
Las celdas de OTP se colorean con fondo verde (≥85%), ámbar (70–84%) o rojo (<70%). Las filas pares tienen fondo azul claro alternado. El índice de eficiencia de rutas se colorea: verde ≤1.05, ámbar ≤1.15, rojo >1.15.

### RF-REP-008 — Resumen ejecutivo como primera hoja
La hoja "Resumen Ejecutivo" se inserta al inicio e incluye: título, fecha de generación, filtros aplicados, métricas globales (8 filas) y tabla de contenido con descripción de cada hoja.

---

## Funcionalidad 3: Exportar CSV datos crudos (CU-E13)

Exporta el fact table filtrado como CSV con 14 columnas seleccionadas. Implementado en `app/reportes/router.py:458`.

### RF-REP-009 — CSV con columnas analíticas seleccionadas
`POST /reportes/csv` exporta: FlightDate, Reporting_Airline, OriginCode, DestCode, Cancelled, CancellationCode, Diverted, ArrDel15, DepDel15, ArrDelayMinutes, DepDelayMinutes, ActualElapsedTime, CRSElapsedTime, Distance. Encoding UTF-8.

### RF-REP-010 — Historial de exportaciones en MinIO
Toda exportación (PDF, Excel, CSV) se sube al bucket `aerotrack-exports` con prefijo `reportes/`. El bucket tiene lifecycle de 7 días. El endpoint `GET /reportes/historial` lista las últimas 50 exportaciones con nombre, tipo, fecha, tamaño y URL de descarga firmada (1h).

---

### RNF-REP-001 — WeasyPrint opcional
La generación de PDF depende de WeasyPrint. Si `weasyprint` no está instalado, el endpoint PDF retorna 501 y la UI muestra un mensaje informativo. Excel y CSV no dependen de WeasyPrint.

### RNF-REP-002 — Tiempo de generación
La generación de PDF debe completarse en menos de 30s para conjuntos de datos típicos (<200K registros). La generación de Excel debe completarse en menos de 20s.

### RNF-REP-003 — Exportaciones no bloquean al usuario
Toda exportación se procesa de forma síncrona pero con timeout generoso (30s PDF, 20s Excel). El frontend muestra un indicador de carga durante la generación.

### RNF-REP-004 — Almacenamiento externo
Los archivos generados se almacenan en MinIO bucket `aerotrack-exports` con lifecycle de expiración a 7 días. No se almacenan en el sistema de archivos local ni en PocketBase.

---

### RN-REP-001 — Bucket exports con lifecycle
El bucket `aerotrack-exports` se crea automáticamente al primer acceso (lazy init) con una regla de lifecycle que expira objetos a los 7 días. Esto evita acumulación de archivos temporales.

### RN-REP-002 — URL firmada con expiración de 1 hora
Las URLs de descarga se generan con `presigned_get_object` con expiración de 1 hora. Pasado ese tiempo, el usuario debe regenerar la exportación.

### RN-REP-003 — Cada exportación tiene contenido diferente según el formato
PDF = dashboard analítico con KPIs, gráficos SVG y tablas resumen. Excel = 8 hojas con datos granulares y gráficos openpyxl. CSV = fact table crudo filtrado (14 columnas). No existe un único contenido renderizado a distintos formatos.

---

## Entradas y salidas

| CU | Entrada | Salida |
|----|---------|--------|
| CU-E11 | filtros (año, trimestre, mes, dow, aerolínea, origen, destino, cancel_code, solo_cancelados) + secciones (lista de 8) | PDF con KPIs, gráficos SVG inline y tablas. Retorna JSON con URL firmada o descarga directa. |
| CU-E12 | filtros (mismos que PDF) | .xlsx con 8 hojas + gráficos embebidos openpyxl. StreamingResponse. |
| CU-E13 | filtros (mismos que PDF) | .csv UTF-8 con 14 columnas del fact table. StreamingResponse. |

---

## Escenarios

### Camino feliz — Exportación PDF
1. El Analista accede a `GET /reportes`, selecciona filtros (año, aerolínea, origen) y visualiza la vista previa con métricas y gráficos Chart.js.
2. El Analista selecciona las secciones a incluir (ej: KPIs, OTP mensual, causas) y hace clic en "Generar PDF".
3. `POST /reportes/pdf` procesa los datos desde tablas de agregación (`agg_otp_aerolinea_mes`, `agg_causas_retraso_mes`, `agg_rutas_eficiencia`, `agg_otp_dia_semana`) y fact enriquecido.
4. WeasyPrint convierte el HTML+CSS+SVG a PDF.
5. El PDF se sube a MinIO y se retorna URL firmada al frontend, que muestra enlace de descarga.

### Camino feliz — Exportación Excel
1. El Analista configura los mismos filtros y hace clic en "Descargar Excel".
2. `POST /reportes/excel` carga el fact table y 3 tablas de agregación, genera 8 hojas con openpyxl.
3. Cada hoja incluye gráfico embebido y formato condicional.
4. El archivo se sirve como `StreamingResponse` con `Content-Disposition: attachment`.

### Camino feliz — Exportación CSV
1. El Analista hace clic en "Descargar CSV".
2. `POST /reportes/csv` carga el fact table filtrado, selecciona 14 columnas, serializa a CSV UTF-8.
3. El archivo se sirve como `StreamingResponse`.

### Manejo de errores
- **WeasyPrint no instalado:** `POST /reportes/pdf` retorna 501 con mensaje claro. La UI muestra advertencia preventiva.
- **Error al cargar datos:** Si las tablas de agregación están vacías o el pipeline no se ha ejecutado, retorna error descriptivo (no 500 genérico).
- **Timeout en generación:** Si la consulta a MinIO excede el tiempo esperado, el historial muestra error parcial (no bloquea).
- **Error en subida a MinIO:** La exportación se descarga directamente vía `StreamingResponse` (fallback degradado).

---

## Criterios de aceptación

- **CU-E11:** Dado que el Analista selecciona filtros y secciones en el panel de reportes, cuando genera un PDF, entonces el sistema produce un documento con KPIs, gráficos SVG inline y tablas seleccionadas, lo sube a MinIO y retorna una URL firmada o descarga directa.
- **CU-E12:** Dado que el Analista configura filtros en el panel, cuando solicita exportar a Excel, entonces el sistema genera un archivo .xlsx con 8 hojas, gráficos embebidos y formato condicional, y lo sirve como descarga.
- **CU-E13:** Dado que el Analista configura filtros en el panel, cuando solicita exportar a CSV, entonces el sistema genera un archivo CSV UTF-8 con 14 columnas del fact table filtrado y lo sirve como descarga.

---

## Dependencias

- **Seguridad:** Autenticación JWT y autorización con permisos `reportes:ver` (vista previa) y `reportes:exportar` (exportaciones).
- **Pipeline ELT:** Tablas de agregación (`agg_otp_aerolinea_mes`, `agg_causas_retraso_mes`, `agg_rutas_eficiencia`, `agg_otp_dia_semana`) y fact table enriquecido en MinIO.
- **WeasyPrint:** Librería Python para conversión HTML+CSS → PDF (opcional, graceful degradation).
- **openpyxl:** Librería Python para generación de archivos Excel .xlsx con gráficos.
- **MinIO:** Bucket `aerotrack-exports` para almacenamiento temporal de exportaciones (lifecycle 7 días).
- **Chart.js (CDN):** Librería frontend para gráficos de vista previa en navegador.

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
