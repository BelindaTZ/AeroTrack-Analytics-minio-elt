# Implementation Plan

## Overview

AeroTrack Analytics — plan de implementación en 4 entregas incrementales.
El sistema ELT procesa 2M registros de vuelos BTS y los expone como análisis
táctico y estratégico a través de una aplicación FastAPI + Jinja2 + Bootstrap 5.

> **Entrega 1 (25%):** Packages seguridad + pipeline_elt + modelo_dimensional
> **Entrega 2 (50%):** Packages dashboard + puntualidad + rutas + cancelaciones + reportes + configuracion + auditoria
> **Entrega 3 (75%):** Packages predictivo + asistente_ia
> **Entrega 4 (100%):** Polish, Kiro-ready docs, README final

## Tasks

---

### 🟢 ENTREGA 1 — Nivel Operativo (25%) ✅ COMPLETADA
> Implementar solo cuando se indique "implementa Entrega 1"
> Al completar: probar login, CRUD modelo dimensional, ejecutar DAG desde web

#### Wave 1 — Infraestructura base (sin dependencias, paralelo)

- [x] 1. Configurar sistema de autenticación JWT con PocketBase
  **Description:** Implementar endpoints FastAPI para login/logout usando
  app_users de PocketBase. Generar y validar JWT firmado con SECRET_KEY.
  Incluir middleware de verificación de token en cada request protegido.
  **Files:** app/seguridad/login.py, app/seguridad/jwt.py,
  app/templates/login.html, app/main.py (rutas auth)
  **Dependencies:** None
  **Requirements:** CU-01, CU-02

  - [x] 1.1 Implementar endpoint POST /auth/login que valide contra PocketBase
  - [x] 1.2 Implementar generación y firma de JWT con expiración configurable
  - [x] 1.3 Crear middleware de verificación JWT para rutas protegidas
  - [x] 1.4 Implementar endpoint POST /auth/logout con invalidación de cookie
  - [x] 1.5 Crear template login.html con Bootstrap 5 y manejo de errores

- [x] 2. Implementar RBAC — verificación de permisos por módulo
  **Description:** Crear el decorador/dependencia FastAPI que verifica que
  el usuario autenticado tenga el permiso requerido (módulo + acción)
  consultando roles_permisos en PocketBase. Retornar HTTP 403 si no tiene acceso.
  **Files:** app/seguridad/roles.py, app/seguridad/permisos.py
  **Dependencies:** None
  **Requirements:** CU-08, CU-09

  - [x] 2.1 Implementar función check_permission(user_id, modulo, accion)
  - [x] 2.2 Crear dependencia FastAPI require_permission() para usar en endpoints
  - [x] 2.3 Cachear permisos del usuario en la sesión para no consultar PocketBase en cada request

- [x] 3. Implementar gestión de usuarios desde la web app
  **Description:** Endpoints y templates para que el Admin pueda crear,
  editar, activar/desactivar y resetear contraseña de usuarios en app_users
  de PocketBase.
  **Files:** app/seguridad/usuarios.py, app/templates/usuarios/
  **Dependencies:** None
  **Requirements:** CU-04

  - [x] 3.1 Endpoint GET /auth/usuarios — listado paginado con filtros
  - [x] 3.2 Endpoint POST /auth/usuarios — crear usuario en PocketBase:
        auto-generar contraseña temporal (4 letras del nombre + 4 dígitos + mayúscula + "!"),
        crear registro en app_users, enviar email de bienvenida con contraseña via SMTP de configuracion_sistema;
        si el envío falla, crear igualmente al usuario y mostrar aviso no bloqueante
  - [x] 3.3 Endpoint PUT /auth/usuarios/{id} — editar nombre, email, rol
  - [x] 3.4 Endpoint PUT /auth/usuarios/{id}/estado — activar/desactivar con modal
  - [x] 3.5 Endpoint POST /auth/usuarios/{id}/reset-password

- [x] 4. Implementar CRUD de roles y permisos
  **Description:** Endpoints para que el Admin gestione roles (crear, editar,
  eliminar con verificación de usuarios asignados) y asigne permisos
  por módulo usando la colección roles_permisos de PocketBase.
  **Files:** app/seguridad/roles_admin.py, app/templates/roles/
  **Dependencies:** None
  **Requirements:** CU-05, CU-06, CU-07, CU-08, CU-09

  - [x] 4.1 Endpoint GET /auth/roles — listado con conteo de usuarios
  - [x] 4.2 Endpoint POST /auth/roles — crear rol nuevo
  - [x] 4.3 Endpoint PUT /auth/roles/{id} — editar (bloqueado si es_sistema=true)
  - [x] 4.4 Endpoint DELETE /auth/roles/{id} — verificar 0 usuarios antes de borrar
  - [x] 4.5 Endpoint GET /auth/roles/{id}/permisos — matriz módulo-acción
  - [x] 4.6 Endpoint PUT /auth/roles/{id}/permisos — guardar cambios en roles_permisos
  - [x] 4.7 Endpoint GET /auth/permisos/matriz — vista de solo lectura rol × módulo

- [x] 5. Implementar perfil de usuario
  **Description:** Página de perfil propio con visualización de datos y
  cambio de contraseña con verificación de la actual.
  **Files:** app/seguridad/perfil.py, app/templates/perfil.html
  **Dependencies:** None
  **Requirements:** CU-03

  - [x] 5.1 Endpoint GET /auth/perfil — mostrar nombre, email, rol, estado, fecha creación
  - [x] 5.2 Endpoint PUT /auth/perfil/password — cambiar contraseña verificando la actual
  - [x] 5.3 Validar que nueva contraseña y confirmación coincidan antes de actualizar

#### Wave 2 — Pipeline ELT en la web app (depende de auth)

- [x] 6. Implementar panel de control del pipeline ELT
  **Description:** Página que muestra el estado actual del DAG consultando
  la API REST de Airflow (:8080/api/v1/). Botón "Ejecutar ahora" que dispara
  el DAG aerotrack_elt_pipeline. Auto-refresh cada 10 segundos del estado.
  Solo accesible con permiso pipeline_elt.ejecutar.
  **Files:** app/pipeline_elt/panel.py, app/templates/pipeline/panel.html
  **Dependencies:** 1, 2
  **Requirements:** CU-10, CU-11

  - [x] 6.1 Función get_dag_status() que consulta Airflow REST API GET /api/v1/dags/aerotrack_elt_pipeline/dagRuns
  - [x] 6.2 Función trigger_dag() que hace POST a Airflow para disparar ejecución
  - [x] 6.3 Template con estado visual por tarea (extract/transform) y auto-refresh cada 10s
  - [x] 6.4 Deshabilitar botón "Ejecutar ahora" si el DAG ya está en ejecución

- [x] 7. Implementar historial y logs del pipeline
  **Description:** Vista de historial de las últimas N ejecuciones del DAG
  con fechas, duración y estado. Vista de log de error con traceback completo
  y botón de reintento.
  **Files:** app/pipeline_elt/historial.py, app/templates/pipeline/historial.html
  **Dependencies:** 6
  **Requirements:** CU-12, CU-13

  - [x] 7.1 Endpoint GET /pipeline/historial — tabla de ejecuciones pasadas
  - [x] 7.2 Endpoint GET /pipeline/logs/{run_id}/{task_id} — traceback completo del error
  - [x] 7.3 Botón de reintento que dispara el pipeline completo desde historial

#### Wave 3 — Modelo dimensional (depende de auth)

- [x] 8. Implementar CRUD del modelo dimensional en app/modelo_dimensional/
  **Description:** Módulo FastAPI con CRUD completo de las 12 tablas del modelo
  estrella (fact_vuelo + 11 dims) almacenadas como Parquet en MinIO bucket
  `aerotrack-dims`. Estructura del módulo:
  - `router.py`: endpoints bajo prefijo `/modelo`; rutas estáticas (`/validar`,
    `/{tabla}/nuevo`) definidas ANTES que las dinámicas (`/{tabla}/{pk}/...`)
    para evitar conflictos de resolución de rutas en FastAPI
  - `data/service.py`: lógica de negocio — read/write Parquet vía
    `shared/clients/minio_client.py`; paginación 50/página; búsqueda
    multi-columna con `df.apply(str.contains)`; auto-incremento de PK;
    `_cast()` para conversión de tipos str→int/float; `_desnormalizar()`
    obligatoria antes de cada escritura (pandas puede retornar columnas
    categóricas al leer Parquet, lo que falla en `concat`)
  - `templates/modelo_dimensional/`: lista_tablas.html (cards con métricas),
    lista_registros.html (live filter 400 ms + paginación),
    form_registro.html (formulario dinámico create/edit por schema Parquet),
    detalle_registro.html (vista solo lectura), validacion.html (reporte
    con exportación CSV)
  **Files:** app/modelo_dimensional/router.py,
  app/modelo_dimensional/data/service.py,
  app/modelo_dimensional/templates/modelo_dimensional/
  **Dependencies:** 1, 2
  **Requirements:** CU-14, CU-15, CU-16

  - [x] 8.1 listar_tablas_con_metricas(): itera TABLAS, llama stat_parquet() en MinIO y carga count; retorna nombre, label, icon, pk, count, size_mb, modified, disponible
  - [x] 8.2 paginar(df, page, q): filtrado multi-columna (q busca en todas las columnas como str, case-insensitive); paginación 50/página con PAGE_SIZE desde shared/templates.py; live filter en lista_registros con fetch+innerHTML (debounce 400 ms, patrón canónico sin FormData)
  - [x] 8.3 crear_registro() y editar_registro(): formulario dinámico generado desde df.columns + dtypes; PK auto-incremental (max+1) en crear; PK read-only en editar; _desnormalizar() antes de concat/write para evitar error con columnas categóricas de Parquet
  - [x] 8.4 eliminar_registro(): bloquea pk_val en ("0", "0.0") en service y en router (HTTP 403 sin mostrar modal); modal de confirmación en template para los demás casos
  - [x] 8.5 RBAC: `_perm_ver = require_permission("modelo_dimensional", "ver")` cacheado a nivel módulo; acciones individuales (crear/editar/eliminar/ejecutar/exportar) verificadas con require_permission() inline en cada endpoint
  - [x] 8.6 Auditoría: audit.registrar(user_id, email, accion, "modelo_dimensional", recurso_tipo=tabla, recurso_id=pk) INSERT en pb_auditoria tras cada operación de escritura (crear, editar, eliminar, validar)
  - [x] 8.7 validar_integridad() (CU-16): verifica 12 FKs de fact_vuelo contra sus dims (FACT_FKS dict), detecta NULLs en FKs obligatorias, verifica fila pk=0 en dims opcionales (dim_cancelacion, dim_retraso_causa, dim_desvio); exportación CSV del reporte en GET /modelo/validar/export

#### Wave 4 — Navegación y layout (depende de auth + módulos)

- [x] 9. Implementar layout base con menú lateral dinámico
  **Description:** Template base Jinja2 con menú lateral que muestra solo
  los módulos a los que el usuario autenticado tiene permiso "ver".
  Los módulos de E2/E3 aparecen en gris con etiqueta "Próximamente".
  **Files:** app/templates/base.html, app/templates/components/sidebar.html
  **Dependencies:** 1, 2
  **Requirements:** CU-01 (post-login redirect)

  - [x] 9.1 Template base con Bootstrap 5 navbar y sidebar
  - [x] 9.2 Lógica de sidebar dinámico basado en permisos del usuario en sesión
  - [x] 9.3 Estilizar módulos pendientes (E2/E3) como deshabilitados con etiqueta "Próximamente"

---

### ✅ ENTREGA 2 — Nivel Táctico (50%) — COMPLETADA
> Implementar solo cuando se indique "implementa Entrega 2"
> Prerequisito: Entrega 1 completada y aprobada

#### Wave 1 — Análisis base (sin dependencias entre sí, paralelo)

- [x] 10. Implementar dashboard de KPIs
  **Description:** Dashboard principal con métricas clave consultando los
  Parquet de MinIO (aerotrack-dims): OTP global, total vuelos, tasa cancelación,
  retraso promedio. Alertas visuales cuando KPIs superan umbrales de
  configuracion_sistema. Filtros por aerolínea, ruta y período.
  Los KPIs se calculan con **pandas** sobre `fact_vuelo.parquet` en MinIO — sin base de datos intermedia.
  Los gráficos interactivos usan **Plotly** (dispersión, barras apiladas); se serializan a JSON en el router
  y se pasan al template Jinja2. Cada módulo incluye una **narrativa ejecutiva en español** renderizada
  en un card debajo del gráfico principal, generada vía `app/utils/ia_narrativa.py`
  (Grok 3 mini → Gemini 2.0 Flash fallback); el card indica qué proveedor respondió y si viene del caché.
  **Files:** app/dashboard/kpis.py, app/dashboard/alertas.py,
  app/templates/dashboard/index.html, app/utils/ia_narrativa.py
  **Dependencies:** None
  **Requirements:** CU-17, CU-18

  - [x] 10.1 Endpoint GET /dashboard/kpis con filtros por año, mes, aerolínea, ruta
  - [x] 10.2 Calcular OTP global, total vuelos, tasa cancelación, retraso promedio y top-3 aerolíneas con pandas sobre fact_vuelo.parquet en MinIO
  - [x] 10.3 Evaluar KPIs contra umbrales de configuracion_sistema; mostrar alerta con severidad (warning/critical) y valor actual vs umbral
  - [x] 10.4 Template con paneles KPI y Plotly; filtros que actualizan todos los paneles automáticamente
  - [x] 10.5 Implementar `app/utils/ia_narrativa.py`: patrón Grok 3 mini (primario) → Gemini 2.0 Flash (fallback en HTTP 429/402/503 o timeout >12s); temperatura 0.4 en ambos; caché en memoria con TTL 300s, clave=MD5(prompt); contexto = solo KPIs agregados (~10-20 métricas), nunca el DataFrame completo ni filas raw

- [x] 11. Implementar módulo de puntualidad OTP
  **Description:** Análisis de puntualidad por aerolínea con Chart.js.
  Desglose de causas de retraso (carrier/weather/NAS/security/late aircraft).
  Comparativa entre aerolíneas en rutas compartidas. Tendencias mes a mes.
  Los datos se agregan con **pandas** sobre Parquet de MinIO. **Chart.js** para series de tiempo
  (OTP mensual, barras de causas de retraso). Incluye card de narrativa ejecutiva vía `ia_narrativa.py`
  con badge de proveedor/caché debajo del gráfico principal.
  **Files:** app/puntualidad/analizar_otp.py, app/templates/puntualidad/
  **Dependencies:** None
  **Requirements:** CU-19, CU-20, CU-21

  - [x] 11.1 Endpoint GET /puntualidad/otp — OTP por aerolínea como barra Chart.js
  - [x] 11.2 Vista de desglose de causas de retraso por aerolínea seleccionada (torta)
  - [x] 11.3 Endpoint comparativa de aerolíneas en ruta compartida (GET /puntualidad/comparar)
  - [x] 11.4 Endpoint GET /puntualidad/tendencias — línea OTP mes a mes y por día de semana

- [x] 12. Implementar módulo de rutas
  **Description:** Ranking de rutas por índice de eficiencia (tiempo real /
  programado). Detalle de ruta con distribución de retrasos y estacionalidad.
  Rutas ineficientes marcadas si superan umbral configurado.
  Los datos de eficiencia se calculan con **pandas** sobre Parquet de MinIO. Los gráficos usan
  **Plotly** (scatter plot tiempo real vs programado; mapa geográfico scattergeo USA). Incluye card de narrativa
  ejecutiva vía `ia_narrativa.py` con badge de proveedor/caché.
  **Files:** app/rutas/ranking_eficiencia.py, app/templates/rutas/
  **Dependencies:** None
  **Requirements:** CU-22, CU-23

  - [x] 12.1 Endpoint GET /rutas — lista ordenada por índice de eficiencia con filtros año y aerolínea
  - [x] 12.2 Marcar rutas ineficientes si desviación supera umbral de configuracion_sistema
  - [x] 12.3 Vista de detalle de ruta: box plot tiempo real vs programado, distribución retrasos
  - [x] 12.4 Endpoint GET /rutas/{ruta}/detalle — scatter plot eficiencia, distribución retrasos, OTP mensual
  - [x] 12.5 Mapa geográfico de rutas USA: `_AIRPORTS` (dict estático ~160 aeropuertos IATA con lat/lon) y
        `_mapa_rutas(rows)` en `ranking_eficiencia.py` generan un Plotly `scattergeo` con arcos verdes
        (eficientes) y rojos (ineficientes), marcadores de aeropuerto y hover con ruta/eficiencia/retraso;
        el card incluye toggle collapse con transición CSS 300 ms y preferencia persistida en
        localStorage ("rutas_mapa_collapsed"); `Plotly.Plots.resize` se llama al expandir para corregir
        dimensiones; `initToggle()` se re-ejecuta tras cada swap del live filter

- [x] 13. Implementar módulo de cancelaciones
  **Description:** Clasificación por código FAA (A/B/C/D) con gráfica de torta.
  Impacto de desvíos con DivArrDelay y DivDistance. Tendencia mensual filtrable.
  Los datos se agregan con **pandas** sobre Parquet de MinIO. **Chart.js** para la tendencia
  mensual de cancelaciones (barras con curva de causas superpuesta). Incluye card de narrativa
  ejecutiva vía `ia_narrativa.py` con badge de proveedor/caché.
  **Files:** app/cancelaciones/clasificar_faa.py, app/templates/cancelaciones/
  **Dependencies:** None
  **Requirements:** CU-24, CU-25, CU-26

  - [x] 13.1 Endpoint GET /cancelaciones/causas — torta por código FAA con filtros
  - [x] 13.2 Vista de desvíos: aeropuerto alternativo, DivArrDelay, DivDistance
  - [x] 13.3 Endpoint GET /cancelaciones/tendencias — barra mensual con curva de causas superpuesta

- [x] 14. Implementar configuración dinámica del sistema
  **Description:** Panel de configuración agrupado por módulo (email, alertas,
  pipeline, ia, sistema). Valores sensibles enmascarados con ••••. Endpoint para
  probar conexión SMTP. Los cambios aplican sin reiniciar servicios.
  **Files:** app/configuracion/panel.py, app/configuracion/email.py,
  app/templates/configuracion/
  **Dependencies:** None
  **Requirements:** CU-29, CU-30, CU-31, CU-32

  - [x] 14.1 Endpoint GET /configuracion — todos los grupos con valores (sensibles enmascarados)
  - [x] 14.2 Endpoint POST /configuracion/{grupo} — guardar grupo de configuración
  - [x] 14.3 Endpoint POST /configuracion/email/test — enviar email de prueba via SMTP (CU-30); inline AJAX
  - [x] 14.4 Al guardar alertas, persistir umbrales; dashboard los lee en cada carga (CU-31)

- [x] 15. Implementar módulo de auditoría
  **Description:** Vista paginada del log pb_auditoria con filtros por módulo,
  acción, usuario y rango de fechas. Exportar resultado filtrado como CSV.
  **Files:** app/auditoria/log.py, app/templates/auditoria/
  **Dependencies:** None
  **Requirements:** CU-39, CU-40

  - [x] 15.1 Endpoint GET /auditoria — tabla paginada ordenada por más reciente
  - [x] 15.2 Filtros por módulo, acción, usuario, resultado y rango de fechas
  - [x] 15.3 Click en fila muestra detalle JSON del campo detalle
  - [x] 15.4 Endpoint GET /auditoria/export — CSV del resultado filtrado actual
  - [x] 15.5 Conversión UTC→Ecuador en `_fmt_local()` (log.py): PocketBase guarda `created` siempre en UTC sin importar `TZ` del contenedor; se convierte con `ZoneInfo("America/Guayaquil")` antes de pasar a template y CSV; el campo `created` original se preserva para `sort` y `filter`

#### Wave 2 — Exportación y monitoreo (dependen de módulos anteriores)

- [x] 16. Implementar exportación PDF, Excel, CSV + filtros avanzados + historial + gráficos
  **Description:** Módulo de reportes completo con 9 filtros de período y operación,
  vista previa dinámica con estadísticas (debounce 500 ms) y gráficos Chart.js interactivos,
  tres formatos de exportación y historial de exportaciones.
  El PDF (WeasyPrint) incluye 8 secciones seleccionables con SVG charts inline (sin matplotlib);
  el Excel (openpyxl) incluye 8 hojas con BarChart/LineChart/PieChart embebidos;
  el CSV exporta el fact table filtrado con columnas clave.
  Los tres formatos se suben a MinIO `aerotrack-exports/reportes/` para el historial.
  El bucket `aerotrack-exports` se crea con lifecycle policy de 7 días.
  **Files:** app/reportes/router.py, app/reportes/generar_pdf.py,
  app/reportes/generar_excel.py, app/reportes/templates/reportes/index.html,
  app/shared/analytics.py (get_origins, get_dests, nuevos filtros),
  dags/aerotrack_tasks.py (fix OTP flag en agregaciones_pipeline, llamada integrada en transform_pipeline — DAG queda en 3 tareas)
  **Dependencies:** 11, 12, 13
  **Requirements:** CU-27, CU-28, CU-43, CU-44, CU-45, CU-46

  - [x] 16.1 Endpoint POST /reportes/pdf — generar PDF con WeasyPrint (8 secciones seleccionables: KPIs operacionales, Tendencia OTP mensual, Desempeño aerolíneas, Causas retraso, Rutas problemáticas, OTP por día, Cancelaciones FAA, Top rutas); SVG charts inline (_svg_line_otp, _svg_hbar, _svg_vbar_otp generados como strings Python); datos pre-computados vía _preparar_datos_pdf() desde 4 agg tables + fact enriquecido; subir a MinIO; retornar enlace firmado 1h
  - [x] 16.2 Endpoint POST /reportes/excel — generar .xlsx con openpyxl: 8 hojas con charts embebidos (Resumen 8 métricas+índice, Puntualidad OTP+BarChart, Tendencia OTP+LineChart, Causas retraso+BarChart, Peores rutas+BarChart, OTP día semana+BarChart, Cancelaciones+PieChart, Rutas eficientes); subir a MinIO + descarga directa
  - [x] 16.3 Formulario de selección de secciones y período antes de exportar PDF
  - [x] 16.4 Verificar/crear bucket aerotrack-exports con lifecycle 7 días al arrancar
  - [x] 16.5 analytics.py: get_origins() y get_dests() desde dim_ruta; nuevos filtros en load_enriched_fact(): quarter, dow, solo_cancelados, cancel_code (conjuntivos con AND lógico)
  - [x] 16.6 Endpoint GET /reportes/preview — estadísticas en tiempo real para los filtros activos: total vuelos, OTP%, cancelados, tasa cancelación%, retraso promedio, aerolíneas únicas, rutas únicas; responde < 500 ms gracias al caché del fact table
  - [x] 16.7 Endpoint POST /reportes/csv — fact table filtrado como CSV (14 columnas clave); subir a MinIO aerotrack-exports/reportes/ + descarga directa; auditoría registrada
  - [x] 16.8 Endpoint GET /reportes/historial — lista últimas 15 exportaciones (PDF/XLSX/CSV) desde MinIO aerotrack-exports/reportes/ con URL firmada 1h, fecha, tipo y tamaño en KB
  - [x] 16.9 generar_excel.py: colores condicionales en OTP (verde ≥85%, ámbar 70-85%, rojo <70%) y en índice eficiencia rutas; hoja Tendencia Mensual (OTP, cancelaciones, retraso por mes); hoja Resumen con filtros aplicados y timestamp; freeze_panes y row striping en todas las hojas
  - [x] 16.10 generar_pdf.py: reescrito con 8 secciones completas y SVG helpers programáticos (_svg_line_otp, _svg_hbar, _svg_vbar_otp) — sin matplotlib (no instalado en Dockerfile); colores dinámicos por umbral OTP (_otp_color); _preparar_datos_pdf(filtros) centraliza la carga desde las 4 agg tables + load_enriched_fact para cancelaciones/rutas
  - [x] 16.14 Timestamps en reportes con zona horaria correcta: `datetime.now(ZoneInfo("America/Guayaquil"))` en generar_pdf.py, generar_excel.py y router.py (nombres de archivo PDF/XLSX/CSV); MinIO `last_modified` convertido con `.astimezone(_TZ)` en historial de exportaciones
  - [x] 16.11 index.html: Chart.js 4.4.4 (CDN en {% block scripts %}); tarjeta "Gráficos del período" con 3 paneles (línea OTP mensual, doughnut causas de retraso, barra horizontal peores rutas); renderCharts()/cargarCharts() en IIFE separado previo al IIFE principal; refresh automático en cada cambio de filtro (debounce 500 ms compartido con preview de stats); limpiarFiltros() también refresca los gráficos
  - [x] 16.12 Endpoint GET /reportes/preview-charts — JSON con otp_mensual {labels,values}, causas {labels,values}, peores_rutas {labels,values}; carga desde agg tables (no fact 2M filas); consumido por Chart.js en index.html con debounce 500 ms
  - [x] 16.13 Fix OTP flag en agregaciones_pipeline() (dags/aerotrack_tasks.py): join de dim_clasificacion_retraso vía fk_clasificacion_retraso y uso de ArrDel15==0 en lugar de ArrDelayMinutes<=15 (dim_horario deduplica por CRSDepTime → ArrDelayMinutes no es confiable por vuelo); requiere re-ejecutar tarea generar_agregaciones en Airflow para regenerar los Parquet de agg

- [x] 17. Implementar monitoreo de servicios y MinIO
  **Description:** Panel de estado de servicios (MinIO, PocketBase, Airflow)
  con latencia en ms. Métricas de MinIO: espacio usado, objetos por bucket.
  Refresco automático cada 30 segundos.
  **Files:** app/configuracion/monitoreo.py, app/templates/configuracion/monitoreo.html
  **Dependencies:** 14
  **Requirements:** CU-33, CU-34

  - [x] 17.1 Endpoint GET /configuracion/estado — health check de MinIO, PocketBase, Airflow con latencia
  - [x] 17.2 Métricas MinIO: espacio total/usado, objetos por bucket, fechas de última modificación
  - [x] 17.3 Template con estado visual verde/rojo por servicio y refresco automático cada 30s
  - [x] 17.4 Mostrar instrucciones de diagnóstico si un servicio no responde

---

### ⬜ ENTREGA 3 — Nivel Estratégico (75%)
> Implementar solo cuando se indique "implementa Entrega 3"
> Prerequisito: Entrega 2 completada y aprobada

#### Wave 1 — Análisis predictivo (sin dependencias entre sí)

- [ ] 18. Implementar módulo predictivo con proyecciones estacionales
  **Description:** Proyecciones de OTP usando statsmodels o Prophet sobre
  datos históricos de dim_tiempo + fact_vuelo. Mapa de calor estacional
  (mes × día de semana). Recomendaciones priorizadas (Alta/Media/Baja).
  Horizonte configurable desde configuracion_sistema.
  **Files:** app/predictivo/proyeccion_riesgo.py, app/predictivo/estacionalidad.py,
  app/predictivo/recomendaciones.py, app/templates/predictivo/
  **Dependencies:** None
  **Requirements:** CU-35, CU-36, CU-37

  - [ ] 18.1 Endpoint POST /predictivo/proyeccion — proyección OTP con intervalos de confianza
  - [ ] 18.2 Advertencia si datos históricos < 12 meses (precisión reducida)
  - [ ] 18.3 Endpoint GET /predictivo/estacionalidad — mapa de calor mes × día de semana
  - [ ] 18.4 Toggle en mapa de calor entre OTP, tasa cancelación y retraso promedio
  - [ ] 18.5 Panel de recomendaciones priorizadas (Alta/Media/Baja) con justificación en datos

- [ ] 19. Implementar asistente analítico IA (chatbot RAG)
  **Description:** Interfaz de chat que responde preguntas en lenguaje natural
  sobre los datos de vuelos. Flujo RAG: consultar Parquet relevante → construir
  contexto → llamar LLM configurado (ia_proveedor + ia_api_key de
  configuracion_sistema) → mostrar respuesta con justificación.
  Historial de conversación por sesión. Registro en pb_auditoria. Target < 30s.
  **Files:** app/asistente_ia/chat.py, app/asistente_ia/rag.py,
  app/asistente_ia/llm_client.py, app/templates/asistente_ia/
  **Dependencies:** None
  **Requirements:** CU-41, CU-42

  - [ ] 19.1 Endpoint POST /ia/chat — consulta RAG sobre Parquet con historial de sesión
  - [ ] 19.2 Módulo rag.py: filtrar Parquet relevante y serializar contexto para LLM
  - [ ] 19.3 Módulo llm_client.py: llamar al proveedor configurado (OpenAI/Anthropic/Gemini/custom)
  - [ ] 19.4 Registrar cada consulta en pb_auditoria con accion="consultar_ia"
  - [ ] 19.5 Deshabilitar módulo si ia.modulo_activo=false en configuracion_sistema

#### Wave 2 — Informe ejecutivo (depende de predictivo)

- [ ] 20. Implementar exportación de informe ejecutivo IA
  **Description:** Generar PDF ejecutivo automatizado con: resumen, proyección
  de riesgo con gráfica, mapa de calor estacional y recomendaciones priorizadas.
  Subir a MinIO aerotrack-exports/ y ofrecer descarga inmediata.
  **Files:** app/predictivo/informe_ejecutivo.py
  **Dependencies:** 18
  **Requirements:** CU-38

  - [ ] 20.1 Endpoint POST /predictivo/informe — generar PDF ejecutivo con ReportLab
  - [ ] 20.2 Incluir gráfica de proyección, mapa de calor y recomendaciones priorizadas
  - [ ] 20.3 Subir PDF a MinIO aerotrack-exports/ y retornar link de descarga inmediata

---

### ⬜ ENTREGA 4 — Pulido y Kiro-ready (100%)
> Implementar solo cuando se indique "implementa Entrega 4"

#### Wave 1 — Documentación y empaquetado final (paralelo)

- [ ] 21. Completar README.md con instrucciones de un solo comando
  **Description:** README con pasos: clonar → copiar .env → docker compose up.
  Descripción de servicios y puertos, cómo ejecutar el setup inicial,
  cómo activar el DAG en Airflow y cómo acceder a la web app.
  **Files:** README.md
  **Dependencies:** None
  **Requirements:** Portabilidad — Instalabilidad (ISO 25010)

  - [ ] 21.1 Sección de requisitos previos (Docker Desktop)
  - [ ] 21.2 Pasos: clonar → .env → docker compose up -d
  - [ ] 21.3 Descripción de servicios con puertos: FastAPI :8000, Airflow :8080, PocketBase :8090, MinIO :9000/:9001
  - [ ] 21.4 Cómo ejecutar setup inicial y activar el DAG

- [ ] 22. Verificar y limpiar docker-compose.yml para entrega
  **Description:** Confirmar que docker compose up -d levanta todo en orden
  correcto con healthchecks. Verificar que minio-init crea los 3 buckets.
  **Files:** docker-compose.yml
  **Dependencies:** None
  **Requirements:** Portabilidad — Instalabilidad (ISO 25010)

  - [ ] 22.1 Confirmar healthchecks y orden de depends_on para todos los servicios
  - [ ] 22.2 Verificar creación automática de buckets aerotrack-raw, aerotrack-dims, aerotrack-exports
  - [ ] 22.3 Verificar que el servicio fastapi monta ./app:/code/app y todos los servicios Airflow solo montan dags, logs, plugins, scripts, data
  - [ ] 22.4 Confirmar que todos los servicios declaran `TZ: America/Guayaquil` en su sección `environment` (minio, pocketbase, airflow-init, airflow-webserver, airflow-scheduler, fastapi) — necesario para que `datetime.now()` en Python use hora Ecuador; no corrige el campo `created` de PocketBase que siempre es UTC

- [ ] 23. Generar diagramas finales y actualizar docs/
  **Description:** Actualizar diagrama de componentes y despliegue con el
  sistema completo. Exportar como PNG para incluir en documentación.
  **Files:** docs/diagrama_componentes.puml, docs/diagrama_despliegue.puml
  **Dependencies:** None
  **Requirements:** Mantenibilidad — Comprobabilidad (ISO 25010)

  - [ ] 23.1 Actualizar diagrama de componentes con todos los módulos de E1-E3
  - [ ] 23.2 Actualizar diagrama de despliegue con servicios Docker definitivos


## Task Dependency Graph

```json
{
  "waves": [
    {
      "wave": "E1-W1",
      "label": "Entrega 1 — Wave 1 — Infraestructura base (paralelo)",
      "tasks": [1, 2, 3, 4, 5],
      "dependencies": []
    },
    {
      "wave": "E1-W2",
      "label": "Entrega 1 — Wave 2 — Pipeline ELT",
      "tasks": [6, 7],
      "dependencies": ["E1-W1"]
    },
    {
      "wave": "E1-W3",
      "label": "Entrega 1 — Wave 3 — Modelo dimensional",
      "tasks": [8],
      "dependencies": ["E1-W1"]
    },
    {
      "wave": "E1-W4",
      "label": "Entrega 1 — Wave 4 — Layout base",
      "tasks": [9],
      "dependencies": ["E1-W1"]
    },
    {
      "wave": "E2-W1",
      "label": "Entrega 2 — Wave 1 — Análisis base (paralelo)",
      "tasks": [10, 11, 12, 13, 14, 15],
      "dependencies": []
    },
    {
      "wave": "E2-W2",
      "label": "Entrega 2 — Wave 2 — Exportación y monitoreo",
      "tasks": [16, 17],
      "dependencies": ["E2-W1"]
    },
    {
      "wave": "E3-W1",
      "label": "Entrega 3 — Wave 1 — Análisis predictivo (paralelo)",
      "tasks": [18, 19],
      "dependencies": []
    },
    {
      "wave": "E3-W2",
      "label": "Entrega 3 — Wave 2 — Informe ejecutivo",
      "tasks": [20],
      "dependencies": ["E3-W1"]
    },
    {
      "wave": "E4-W1",
      "label": "Entrega 4 — Wave 1 — Documentación final (paralelo)",
      "tasks": [21, 22, 23],
      "dependencies": []
    }
  ]
}
```

## Notes

- Las tareas de cada Entrega son independientes entre entregas. Al indicar "implementa Entrega N", Kiro no debe tocar tareas de otras entregas.
- Todas las operaciones de escritura deben registrar en pb_auditoria (INSERT-only, sin UPDATE ni DELETE sobre esa colección).
- Los valores sensibles en configuracion_sistema (flag sensible=true) siempre se enmascaran con •••• en la UI.
