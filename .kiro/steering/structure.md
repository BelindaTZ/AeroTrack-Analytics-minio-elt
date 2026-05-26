# AeroTrack Analytics — Structure

## Estructura de carpetas objetivo

```
minio-elt/                          ← Raíz del proyecto
├── .env                            ← Credenciales (excluido de git)
├── .env.example                    ← Plantilla documentada
├── .gitignore
├── docker-compose.yml              ← Orquesta los 9 servicios
├── Dockerfile                      ← Imagen FastAPI app
├── Dockerfile.setup                ← Imagen one-shot de inicialización
├── requirements.txt                ← Dependencias Python generales
│
├── app/                            ← FastAPI — módulos por paquete CU
│   ├── main.py                     ← Punto de entrada, registro de routers
│   ├── config.py                   ← Detecta Docker/local automáticamente
│   ├── seguridad/                  ← JWT, RBAC, middleware — E1 [CU-01..09]
│   │   ├── router.py
│   │   ├── service.py
│   │   └── templates/
│   ├── pipeline_elt/               ← Trigger DAG, monitor, historial, logs — E1 [CU-10..13]
│   │   ├── router.py
│   │   ├── airflow_client.py
│   │   └── templates/
│   ├── modelo_dimensional/         ← CRUD Parquet en MinIO, validación — E1 [CU-14..16]
│   │   ├── router.py
│   │   ├── service.py
│   │   └── templates/
│   ├── dashboard/                  ← KPIs y alertas — E2 [CU-17..18]
│   ├── puntualidad/                ← OTP, comparativas, tendencias — E2 [CU-19..21]
│   ├── rutas/                      ← Ranking eficiencia — E2 [CU-22..23]
│   ├── cancelaciones/              ← Códigos FAA, desvíos, tendencias — E2 [CU-24..26]
│   ├── reportes/                   ← Exportación PDF/Excel — E2 [CU-27..28]
│   ├── configuracion/              ← Parámetros dinámicos, estado servicios — E2 [CU-29..34]
│   ├── auditoria/                  ← Log inmutable, filtros, CSV — E2 [CU-39..40]
│   ├── predictivo/                 ← Proyecciones riesgo, estacionalidad — E3 [CU-35..38]
│   ├── asistente_ia/               ← Chatbot RAG sobre modelo estrella — E3 [CU-41..42]
│   └── auxiliar/                   ← Paquete «extensible» — sin CUs previstos
│
├── webapp/                         ← CRUD prototipo inicial (presentación)
│   ├── main.py                     ← Prototipo: CRUD genérico de Parquet
│   ├── config.py
│   ├── minio_client.py
│   ├── router_tablas.py
│   ├── requirements_web.txt
│   └── templates/
│       ├── base.html
│       ├── dashboard.html
│       ├── tabla_lista.html
│       ├── tabla_detalle.html
│       ├── tabla_form.html
│       └── error.html
│
├── dags/
│   ├── aerotrack_elt_dag.py        ← DAG principal: extract >> transform
│   ├── aerotrack_tasks.py          ← extract_pipeline(), transform_pipeline()
│   └── config.py                   ← Gemelo de scripts/config.py (Docker-aware)
│
├── scripts/                        ← Setup inicial (one-shot, NO parte del DAG)
│   ├── config.py                   ← Configuración compartida
│   ├── 01_crear_coleccion_pb.py    ← Crea colecciones en PocketBase
│   ├── 02_cargar_csv_a_pb.py       ← Carga CSV → PocketBase
│   ├── 03_extraer_pb_a_minio.py    ← Extract: PocketBase → Parquet → aerotrack-raw
│   ├── 04_transformar_dimensiones.py ← Transform: raw → modelo estrella → aerotrack-dims
│   ├── setup_pocketbase_admin.py   ← Crea usuario admin en PocketBase
│   └── run_setup_inicial.py        ← Orquesta scripts 01, 02 y setup
│
├── data/
│   └── airline_2m.csv              ← Dataset BTS Carrier On-Time Performance (2M vuelos)
│
├── docs/
│   ├── diagrama_componentes.puml   ← Diagrama de componentes PlantUML
│   ├── diagrama_despliegue.puml    ← Diagrama de despliegue PlantUML
│   └── aerotrack_bd_fisica.dbml    ← Modelo físico BD (DBML)
│
└── logs/                           ← Logs de Airflow (montado como volumen)
    └── dag_processor_manager/
```

## Estado de implementación por módulo

| Módulo | Directorio | Entrega | Estado |
|---|---|---|---|
| CRUD Parquet (prototipo) | `webapp/` | — | Implementado (presentación inicial) |
| Autenticación + RBAC | `app/seguridad/` | E1 | Por implementar |
| Pipeline ELT UI | `app/pipeline_elt/` | E1 | Por implementar |
| Modelo Dimensional UI | `app/modelo_dimensional/` | E1 | Por implementar |
| Dashboard KPIs | `app/dashboard/` | E2 | Por implementar |
| Análisis Puntualidad | `app/puntualidad/` | E2 | Por implementar |
| Análisis Rutas | `app/rutas/` | E2 | Por implementar |
| Análisis Cancelaciones | `app/cancelaciones/` | E2 | Por implementar |
| Exportaciones | `app/reportes/` | E2 | Por implementar |
| Configuración Sistema | `app/configuracion/` | E2 | Por implementar |
| Auditoría | `app/auditoria/` | E2 | Por implementar |
| Predictivo | `app/predictivo/` | E3 | Por implementar |
| Asistente IA | `app/asistente_ia/` | E3 | Por implementar |

## Convenciones de código

### Organización de módulos
- Un subdirectorio por paquete del diagrama de casos de uso
- Cada módulo tiene: `router.py` (endpoints), `service.py` (lógica), `templates/` (Jinja2)
- Los módulos no comparten estado mutable entre sí

### config.py centralizado
```python
# Patrón para detectar Docker vs local
import os
IN_DOCKER = os.path.exists("/.dockerenv")

MINIO_ENDPOINT = "minio:9000" if IN_DOCKER else "localhost:9000"
PB_URL = "http://pocketbase:8090" if IN_DOCKER else "http://localhost:8090"
```
Importar siempre las constantes de `config.py` — nunca llamar `os.getenv()` directamente en los módulos.

### Scripts ELT
- **Idempotencia obligatoria:** verificar existencia antes de crear (colecciones, buckets, registros)
- **PocketBase API v0.22.4:** usar `"schema"` (no `"fields"`) al crear colecciones
- **Scripts 01, 02, setup:** solo ejecución manual o vía `aerotrack-setup` container
- **Scripts 03, 04:** invocados por el DAG de Airflow

### Templates Jinja2
- Patrón de diseño visual consistente: sidebar fijo + contenido principal
- Paleta de colores: primario `#1B3A6B`, acento `#E05A4E`, fondo `#F4F6F9`
- Módulos no implementados en la entrega actual: visibles en gris con etiqueta "Próximamente"
- Flujo analítico consistente: filtros → gráfica → exportar

### Seguridad
- Contraseñas con bcrypt (gestionado por PocketBase)
- JWT firmado con `SECRET_KEY` del `.env`
- Variables sensibles NUNCA en código fuente — siempre en `.env`
- Configuraciones sensibles enmascaradas en UI (••••)
- Auditoría: INSERT automático en `pb_auditoria` en toda operación de escritura
