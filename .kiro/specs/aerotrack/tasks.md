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

#### Wave 3 — Modelo dimensional (migrar desde webapp/, depende de auth)

- [x] 8. Migrar CRUD del modelo dimensional desde webapp/ a app/modelo_dimensional/
  **Description:** La carpeta webapp/ contiene una implementación funcional del
  CRUD de las 12 tablas dimensionales. MIGRAR (no reescribir desde cero) esa
  lógica a app/modelo_dimensional/ siguiendo la estructura de módulos del proyecto.
  Refactorizar para: usar config.py centralizado, agregar verificación de permisos
  RBAC (modelo_dimensional.ver / .crear / .editar / .eliminar), integrar registro
  en pb_auditoria después de cada operación de escritura.
  NO eliminar webapp/ durante esta tarea — se mantiene hasta visto bueno en Entrega 1.
  **Files:** app/modelo_dimensional/router.py, app/modelo_dimensional/service.py,
  app/templates/modelo_dimensional/
  **Dependencies:** 1, 2
  **Requirements:** CU-14, CU-15, CU-16

  - [x] 8.1 Migrar lógica de listado de tablas con métricas desde webapp/ (nombre, count, tamaño Parquet, última actualización)
  - [x] 8.2 Migrar lógica de exploración paginada (50/página) con búsqueda por columna
  - [x] 8.3 Migrar formularios dinámicos de crear/editar registro basados en schema Parquet
  - [x] 8.4 Migrar lógica de eliminación con modal de confirmación (bloquear pk=0)
  - [x] 8.5 Agregar verificación de permisos RBAC en cada endpoint
  - [x] 8.6 Agregar registro en pb_auditoria en cada operación de escritura (INSERT-only)
  - [x] 8.7 Implementar CU-16: validación de integridad FK + NULLs con exportación CSV del reporte

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

### ⬜ ENTREGA 2 — Nivel Táctico (50%)
> Implementar solo cuando se indique "implementa Entrega 2"
> Prerequisito: Entrega 1 completada y aprobada

#### Wave 1 — Análisis base (sin dependencias entre sí, paralelo)

- [ ] 10. Implementar dashboard de KPIs
  **Description:** Dashboard principal con métricas clave consultando los
  Parquet de MinIO (aerotrack-dims): OTP global, total vuelos, tasa cancelación,
  retraso promedio. Alertas visuales cuando KPIs superan umbrales de
  configuracion_sistema. Filtros por aerolínea, ruta y período.
  **Files:** app/dashboard/kpis.py, app/dashboard/alertas.py,
  app/templates/dashboard/index.html
  **Dependencies:** None
  **Requirements:** CU-17, CU-18

  - [ ] 10.1 Endpoint GET /dashboard/kpis con filtros por año, mes, aerolínea, ruta
  - [ ] 10.2 Calcular OTP global, total vuelos, tasa cancelación y retraso promedio desde fact_vuelo
  - [ ] 10.3 Evaluar KPIs contra umbrales de configuracion_sistema y resaltar en rojo si superan
  - [ ] 10.4 Template con paneles KPI y Chart.js; filtros que actualizan todos los paneles

- [ ] 11. Implementar módulo de puntualidad OTP
  **Description:** Análisis de puntualidad por aerolínea con Chart.js.
  Desglose de causas de retraso (carrier/weather/NAS/security/late aircraft).
  Comparativa entre aerolíneas en rutas compartidas. Tendencias mes a mes.
  **Files:** app/puntualidad/analizar_otp.py, app/templates/puntualidad/
  **Dependencies:** None
  **Requirements:** CU-19, CU-20, CU-21

  - [ ] 11.1 Endpoint GET /puntualidad/otp — OTP por aerolínea como barra Chart.js
  - [ ] 11.2 Vista de desglose de causas de retraso por aerolínea seleccionada (torta)
  - [ ] 11.3 Endpoint comparativa de aerolíneas en ruta compartida (GET /puntualidad/comparar)
  - [ ] 11.4 Endpoint GET /puntualidad/tendencias — línea OTP mes a mes y por día de semana

- [ ] 12. Implementar módulo de rutas
  **Description:** Ranking de rutas por índice de eficiencia (tiempo real /
  programado). Detalle de ruta con distribución de retrasos y estacionalidad.
  Rutas ineficientes marcadas si superan umbral configurado.
  **Files:** app/rutas/ranking_eficiencia.py, app/templates/rutas/
  **Dependencies:** None
  **Requirements:** CU-22, CU-23

  - [ ] 12.1 Endpoint GET /rutas/ranking — lista ordenada por índice de eficiencia
  - [ ] 12.2 Marcar rutas ineficientes si desviación supera umbral de configuracion_sistema
  - [ ] 12.3 Vista de detalle de ruta: box plot tiempo real vs programado, distribución retrasos
  - [ ] 12.4 Endpoint GET /rutas/{ruta}/comparar — scatter plot diferencia tiempo real vs programado

- [ ] 13. Implementar módulo de cancelaciones
  **Description:** Clasificación por código FAA (A/B/C/D) con gráfica de torta.
  Impacto de desvíos con DivArrDelay y DivDistance. Tendencia mensual filtrable.
  **Files:** app/cancelaciones/clasificar_faa.py, app/templates/cancelaciones/
  **Dependencies:** None
  **Requirements:** CU-24, CU-25, CU-26

  - [ ] 13.1 Endpoint GET /cancelaciones/causas — torta por código FAA con filtros
  - [ ] 13.2 Vista de desvíos: aeropuerto alternativo, DivArrDelay, DivDistance
  - [ ] 13.3 Endpoint GET /cancelaciones/tendencias — barra mensual con curva de causas superpuesta

- [ ] 14. Implementar configuración dinámica del sistema
  **Description:** Panel de configuración agrupado por módulo (email, alertas,
  pipeline, ia, sistema). Valores sensibles enmascarados con ••••. Endpoint para
  probar conexión SMTP. Los cambios aplican sin reiniciar servicios.
  **Files:** app/configuracion/panel.py, app/configuracion/email.py,
  app/templates/configuracion/
  **Dependencies:** None
  **Requirements:** CU-29, CU-30, CU-31, CU-32

  - [ ] 14.1 Endpoint GET /configuracion — todos los grupos con valores (sensibles enmascarados)
  - [ ] 14.2 Endpoint PUT /configuracion/{grupo} — guardar grupo de configuración
  - [ ] 14.3 Endpoint POST /configuracion/email/test — enviar email de prueba via SMTP
  - [ ] 14.4 Aplicar umbrales inmediatamente al dashboard al guardar grupo alertas (sin restart)

- [ ] 15. Implementar módulo de auditoría
  **Description:** Vista paginada del log pb_auditoria con filtros por módulo,
  acción, usuario y rango de fechas. Exportar resultado filtrado como CSV.
  **Files:** app/auditoria/log.py, app/templates/auditoria/
  **Dependencies:** None
  **Requirements:** CU-39, CU-40

  - [ ] 15.1 Endpoint GET /auditoria — tabla paginada ordenada por más reciente
  - [ ] 15.2 Filtros por módulo, acción, usuario, resultado y rango de fechas
  - [ ] 15.3 Click en fila muestra detalle JSON del campo detalle
  - [ ] 15.4 Endpoint GET /auditoria/export — CSV del resultado filtrado actual

#### Wave 2 — Exportación y monitoreo (dependen de módulos anteriores)

- [ ] 16. Implementar exportación PDF y Excel
  **Description:** Generar reportes descargables desde cualquier módulo
  analítico. PDF con ReportLab incluyendo gráficas, subido a MinIO aerotrack-exports/.
  Excel con openpyxl con hojas por módulo, descarga directa sin subir a MinIO.
  **Files:** app/reportes/generar_pdf.py, app/reportes/generar_excel.py
  **Dependencies:** 11, 12, 13
  **Requirements:** CU-27, CU-28

  - [ ] 16.1 Endpoint POST /reportes/pdf — generar PDF con ReportLab, subir a MinIO exports, retornar link
  - [ ] 16.2 Endpoint POST /reportes/excel — generar .xlsx con hojas puntualidad/rutas/cancelaciones
  - [ ] 16.3 Formulario de selección de secciones y período antes de exportar PDF

- [ ] 17. Implementar monitoreo de servicios y MinIO
  **Description:** Panel de estado de servicios (MinIO, PocketBase, Airflow)
  con latencia en ms. Métricas de MinIO: espacio usado, objetos por bucket.
  Refresco automático cada 30 segundos.
  **Files:** app/configuracion/monitoreo.py, app/templates/configuracion/monitoreo.html
  **Dependencies:** 14
  **Requirements:** CU-33, CU-34

  - [ ] 17.1 Endpoint GET /configuracion/estado — health check de MinIO, PocketBase, Airflow con latencia
  - [ ] 17.2 Métricas MinIO: espacio total/usado, objetos por bucket, fechas de última modificación
  - [ ] 17.3 Template con estado visual verde/rojo por servicio y refresco automático cada 30s
  - [ ] 17.4 Mostrar instrucciones de diagnóstico si un servicio no responde

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
  Actualizar volume del servicio fastapi de ./webapp a ./app.
  **Files:** docker-compose.yml
  **Dependencies:** None
  **Requirements:** Portabilidad — Instalabilidad (ISO 25010)

  - [ ] 22.1 Confirmar healthchecks y orden de depends_on para todos los servicios
  - [ ] 22.2 Verificar creación automática de buckets aerotrack-raw, aerotrack-dims, aerotrack-exports
  - [ ] 22.3 Actualizar volume fastapi de ./webapp:/app a ./app:/app

- [ ] 23. Generar diagramas finales y actualizar docs/
  **Description:** Actualizar diagrama de componentes y despliegue con el
  sistema completo. Exportar como PNG para incluir en documentación.
  **Files:** docs/diagrama_componentes.puml, docs/diagrama_despliegue.puml
  **Dependencies:** None
  **Requirements:** Mantenibilidad — Comprobabilidad (ISO 25010)

  - [ ] 23.1 Actualizar diagrama de componentes con todos los módulos de E1-E3
  - [ ] 23.2 Actualizar diagrama de despliegue con servicios Docker definitivos

#### Wave 2 — Limpieza final (depende de aprobación Entrega 1)

- [ ] 24. [BLOQUEADO — espera visto bueno del usuario en Entrega 1] Eliminar webapp/ y todas sus referencias
  **Description:** EJECUTAR SOLO cuando el usuario haya dado visto bueno
  explícito de que Entrega 1 funciona correctamente. Eliminar carpeta webapp/
  completa, eliminar referencias en docker-compose.yml (volumes de airflow-*)
  y limpiar la nota de advertencia de la tarea 8 en este archivo.
  **Files:** webapp/ (eliminar), docker-compose.yml, tasks.md
  **Dependencies:** 8, 9
  **Requirements:** Mantenibilidad — Modificabilidad (ISO 25010)

  - [ ] 24.1 Eliminar carpeta webapp/ completa una vez confirmado el visto bueno
  - [ ] 24.2 Eliminar referencias a webapp/ en docker-compose.yml (volumes de airflow-*)
  - [ ] 24.3 Limpiar nota de advertencia y referencias a webapp/ en tarea 8 de este archivo

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
    },
    {
      "wave": "E4-W2",
      "label": "Entrega 4 — Wave 2 — Limpieza final (bloqueada hasta visto bueno E1)",
      "tasks": [24],
      "dependencies": ["E4-W1"]
    }
  ]
}
```

## Notes

- **webapp/** contiene implementación preliminar del CRUD dimensional (solo para demostración visual). NO eliminar hasta visto bueno explícito del usuario en Entrega 1. La tarea 8 migra esa lógica hacia app/modelo_dimensional/.
- **Tarea 24** está bloqueada: solo ejecutar cuando el usuario confirme explícitamente que Entrega 1 funciona.
- Las tareas de cada Entrega son independientes entre entregas. Al indicar "implementa Entrega N", Kiro no debe tocar tareas de otras entregas.
- **docker-compose.yml** monta ./webapp como volumen del servicio fastapi durante E1. Al completar E4 (tarea 22) se cambia a ./app.
- Todas las operaciones de escritura deben registrar en pb_auditoria (INSERT-only, sin UPDATE ni DELETE sobre esa colección).
- Los valores sensibles en configuracion_sistema (flag sensible=true) siempre se enmascaran con •••• en la UI.
