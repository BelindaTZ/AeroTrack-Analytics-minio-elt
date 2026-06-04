# AeroTrack Analytics — Product

## Propósito del producto

AeroTrack Analytics es un sistema de inteligencia de negocios estratégico para el análisis operacional de aerolíneas de EE.UU. Procesa 2 millones de registros del dataset Carrier On-Time Performance (BTS/FAA) mediante un pipeline ELT automatizado para generar análisis de puntualidad, cancelaciones, rutas y predicciones de riesgo operacional.

El sistema transforma datos crudos en información accionable organizada en tres niveles:
- **Operativo (E1):** infraestructura, pipeline y modelo de datos
- **Táctico (E2):** dashboards de KPIs, análisis y exportaciones
- **Estratégico (E3):** proyecciones predictivas y asistente IA

## Usuarios objetivo

| Actor | Rol | Alcance funcional |
|---|---|---|
| **Administrador** | Gestiona la infraestructura y el pipeline | Usuarios, roles, permisos, pipeline ELT, modelo dimensional, configuración, auditoría |
| **Analista de Datos** | Consume el análisis generado | Dashboard, puntualidad, rutas, cancelaciones, reportes, módulo predictivo, asistente IA |

## Funcionalidades clave por entrega

### Entrega 1 — Nivel Operativo
- Autenticación JWT + RBAC dinámico por módulo y acción (CU-01 a CU-09)
- Pipeline ELT automatizado con Airflow: PocketBase → MinIO (Parquet) (CU-10 a CU-13)
- CRUD del modelo dimensional estrella (12 tablas) con validación de integridad (CU-14 a CU-16)

### Entrega 2 — Nivel Táctico
- Dashboard de KPIs con alertas configurables por umbral (CU-17 a CU-18)
- Análisis de puntualidad OTP, rutas y cancelaciones por código FAA (CU-19 a CU-26)
- Exportación a PDF y Excel | Configuración dinámica del sistema (CU-27 a CU-34)
- Log de auditoría inmutable con filtrado y exportación CSV (CU-39 a CU-40)

### Entrega 3 — Nivel Estratégico
- Proyecciones de riesgo operacional con intervalos de confianza (CU-35 a CU-38)
- Asistente analítico IA con RAG sobre el modelo estrella (LLM configurable) (CU-41 a CU-42)

## Objetivos de negocio

| ID | Objetivo |
|---|---|
| OE-01 | Reducir el índice de retrasos identificando causas por aerolínea y ruta |
| OE-02 | Optimizar el rendimiento de rutas ineficientes comparando tiempo real vs. programado |
| OE-03 | Gestionar el pipeline ELT de forma automatizada y auditable |
| OE-04 | Minimizar la exposición a cancelaciones y desvíos detectando patrones FAA |
| OE-05 | Anticipar disrupciones operacionales con inteligencia predictiva |

## Métricas de éxito

| Métrica | Objetivo |
|---|---|
| Tiempo de carga del dashboard | < 5 segundos |
| Duración del pipeline ELT (2M registros, 10 workers) | < 40 minutos |
| Tiempo de respuesta del módulo predictivo (6 meses) | < 30 segundos |
| Disponibilidad de servicios críticos | `restart: unless-stopped` en FastAPI, Airflow webserver y scheduler |

## Alcance y límites

**Dentro del alcance:**
- Análisis de vuelos domésticos de EE.UU. (dataset BTS Carrier On-Time Performance)
- Usuarios internos del sistema (Administrador y Analista de Datos)
- Despliegue local con Docker Desktop

**Fuera del alcance:**
- Integración con sistemas de reservas o GDS
- Datos en tiempo real (el pipeline procesa snapshots estáticos)
- Despliegue en producción cloud (migratable vía variables .env)

