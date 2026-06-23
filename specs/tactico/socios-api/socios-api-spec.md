# Módulo: Socios API

**Prefijo:** SOC · **Paquete técnico:** `app/socios_api/` · **Entrega:** Entrega 4

## Objetivo

Exponer los resultados analíticos de AeroTrack como servicio programático documentado y seguro para socios tecnológicos externos, con gestión de claves de acceso y webhooks de notificación.

## Actores

- **Administrador** — gestiona claves API, webhooks e historial de uso.
- **Socio tecnológico** — consume los endpoints públicos de la API REST con autenticación por API key (Bearer token o query param).

## Requisitos funcionales

### Funcionalidad 1: Gestionar claves de acceso programático (CU-T12)

- **RF-SOC-001**: El sistema debe permitir crear claves API vía `POST /socios/claves` con nombre del socio, límite diario de consultas (default 1000) y fecha de expiración opcional. La clave se genera como `at_{token_hex(32)}`, se almacena únicamente su hash SHA256, y se devuelve en texto plano una sola vez.
- **RF-SOC-002**: El sistema debe listar las claves activas vía `GET /socios` con métricas: consultas del día, consultas totales, última fecha de consulta, expiración y webhooks asociados.
- **RF-SOC-003**: El sistema debe permitir revocar una clave inmediatamente vía `POST /socios/claves/{id}/revocar`; las peticiones con esa clave son rechazadas con 401.
- **RF-SOC-004**: El sistema debe validar cada petición a los endpoints públicos verificando: existencia de la clave, estado activo, no expiración y límite diario no superado.

### Funcionalidad 2: Configurar webhooks de notificación (CU-T13)

- **RF-SOC-005**: El sistema debe permitir configurar webhooks vía `POST /socios/webhooks` con nombre, clave API asociada, URL de destino, eventos suscritos (`pipeline_completado`, `alerta_otp`, `reporte_generado`) y clave HMAC para firma de payloads.
- **RF-SOC-006**: El sistema debe permitir activar/desactivar un webhook vía `POST /socios/webhooks/{id}/toggle`.
- **RF-SOC-007**: El sistema debe disparar los webhooks activos cuando ocurra el evento correspondiente, enviando payload JSON firmado con HMAC-SHA256 en header `X-AeroTrack-Signature`, con reintentos hasta 3 veces con backoff (2s, 4s, 8s).

### Funcionalidad 3: Endpoints públicos de consulta para socios (CU-O17)

- **RF-SOC-008**: `GET /api/v1/otp` — retorna OTP por aerolínea y período desde `agg_otp_aerolinea_mes`. Parámetros: `airline`, `year`, `month` (opcionales).
- **RF-SOC-009**: `GET /api/v1/rutas` — retorna ranking de eficiencia de rutas desde `agg_rutas_eficiencia`. Parámetros: `year`, `top_n` (default 10).
- **RF-SOC-010**: `GET /api/v1/cancelaciones` — retorna resumen de cancelaciones por código FAA desde `agg_cancelaciones_causa`. Parámetros: `year`, `month` (opcionales).
- **RF-SOC-011**: `GET /api/v1/kpis` — retorna KPIs globales del período desde `agg_kpi_global_dia`. Parámetros: `year`, `month` (opcionales).

### Funcionalidad 4: Ver historial de uso de la API (CU-O18)

- **RF-SOC-012**: El sistema debe registrar cada llamada a los endpoints públicos en `pb_api_historial`: clave usada, endpoint, método, código de respuesta, tiempo de respuesta en ms e IP de origen.
- **RF-SOC-013**: El sistema debe mostrar el historial de llamadas vía `GET /socios/historial` con filtros por socio, endpoint y rango de fechas.
- **RF-SOC-014**: `GET /socios/historial/json` retorna el historial filtrado como JSON para actualización dinámica sin recargar la página (live filter vía fetch).

## Requisitos no funcionales

- **RNF-SOC-001**: La autenticación por API key se valida mediante header `Authorization: Bearer {key}` o query param `api_key`; nunca en el body.
- **RNF-SOC-002**: Los endpoints públicos retornan únicamente datos de tablas de agregación pre-calculadas; no exponen el fact table completo.
- **RNF-SOC-003**: El payload de cada webhook se firma con HMAC-SHA256 usando la `clave_hmac` del socio; header `X-AeroTrack-Signature`.
- **RNF-SOC-004**: Toda gestión de claves y webhooks (crear, revocar, configurar) se audita con módulo `socios_api`.
- **RNF-SOC-005**: El RBAC interno se valida en FastAPI con `require_permission("socios_api", *)`: `ver`, `crear`, `configurar`, `eliminar`.
- **RNF-SOC-006**: Los endpoints públicos (`/api/v1/*`) no requieren cookie JWT; solo autenticación por API key.

## Reglas de negocio

- **RN-SOC-001**: Una clave revocada no puede reactivarse; debe crearse una nueva.
- **RN-SOC-002**: Si una clave supera su límite diario de consultas, las peticiones adicionales retornan 429 Too Many Requests.
- **RN-SOC-003**: Los webhooks solo se disparan para socios con clave activa, no expirada y con el webhook en estado activo.
- **RN-SOC-004**: Los endpoints públicos de la API de socios no requieren sesión web; solo autenticación por API key.

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /socios` | Cookie JWT admin | HTML con lista de claves y webhooks |
| `POST /socios/claves` | `{nombre, limite_diario, expiracion}` | JSON con clave plana (una sola vez) + advertencia |
| `POST /socios/claves/{id}/revocar` | Cookie JWT admin | `{"ok": true}` |
| `POST /socios/webhooks` | `{nombre, clave_id, url, eventos[], clave_hmac}` | JSON del webhook creado |
| `POST /socios/webhooks/{id}/toggle` | `{activo: bool}` | JSON del webhook actualizado |
| `GET /socios/historial` | Cookie JWT admin, filtros | HTML con tabla de llamadas |
| `GET /api/v1/otp` | `api_key` o Bearer, `airline`,`year`,`month` | `{"ok":true, "data":[...], "total":N}` |
| `GET /api/v1/rutas` | `api_key` o Bearer, `year`, `top_n` | `{"ok":true, "data":[...], "total":N}` |
| `GET /api/v1/cancelaciones` | `api_key` o Bearer, `year`, `month` | `{"ok":true, "data":[...], "total":N}` |
| `GET /api/v1/kpis` | `api_key` o Bearer, `year`, `month` | `{"ok":true, "data":[...], "total":N}` |

## Escenarios

### Camino feliz — Integración de socio

El Administrador accede a `GET /socios`, crea una clave para "AeroData Partners" con límite 1000 consultas/día. El sistema genera `at_{hex}`, guarda el hash SHA256, y devuelve la clave plana con advertencia. El Administrador configura un webhook para `pipeline_completado` apuntando a `https://socio.com/webhook` con clave HMAC. El socio usa la clave en `GET /api/v1/otp?airline=AA&year=2025`, recibe JSON con los datos de OTP. El sistema incrementa `consultas_hoy` y registra la llamada en `pb_api_historial`. Al completarse el pipeline, `dispatch_event("pipeline_completado", payload)` envía el payload firmado al webhook del socio con 3 reintentos si es necesario.

### Manejo de errores

- **Clave inválida**: `GET /api/v1/otp` sin clave o con clave incorrecta → 401 `"API key inválida"`.
- **Clave revocada**: 401 `"API key revocada"`.
- **Clave expirada**: 401 `"API key expirada"`.
- **Límite superado**: 429 `"Límite diario de consultas alcanzado"`.
- **Webhook falla 3 veces**: se registra `ultimo_estado=fallido` en `pb_api_webhooks`; no bloquea otras operaciones.
- **Evento inválido**: `dispatch_event("invalido", ...)` loguea warning y no dispara nada.
- **Sin webhooks suscritos**: `dispatch_event` loguea debug y retorna sin error.

## Criterios de aceptación

1. Dado que el Administrador crea una clave API, cuando el socio la usa en `GET /api/v1/otp`, entonces el sistema valida existencia, estado activo, no expiración y límite, retorna los datos solicitados y registra la llamada en el historial.
2. Dado que una clave supera su límite diario de 1000 consultas, cuando el socio hace la petición 1001, entonces el sistema retorna 429.
3. Dado que se configura un webhook para `pipeline_completado`, cuando el pipeline termina exitosamente (`POST /pipeline/trigger`), entonces el sistema envía un payload JSON firmado con HMAC-SHA256 a la URL del socio.
4. Dado que el Administrador consulta `GET /socios/historial?endpoint=otp`, entonces el sistema muestra solo las llamadas al endpoint `/api/v1/otp`.
5. Dado que el Administrador revoca una clave vía `POST /socios/claves/{id}/revocar`, cuando el socio intenta usarla, entonces el sistema retorna 401.

## Dependencias

- **Pipeline ELT** — las tablas de agregación (`agg_otp_aerolinea_mes`, `agg_rutas_eficiencia`, `agg_cancelaciones_causa`, `agg_kpi_global_dia`) son la fuente de datos de los endpoints públicos.
- **Seguridad** — RBAC interno para gestión de claves y webhooks con permiso `socios_api.*`.
- **Auditoría** — registro de creación y revocación de claves, configuración de webhooks.
- **httpx** — librería HTTP asíncrona para envío de webhooks.

## Casos de uso relacionados

CU-T12 · CU-T13 · CU-O17 · CU-O18

## Historias de usuario

- Como **Administrador**, quiero gestionar claves API por socio con límites de uso configurables, para controlar el acceso programático al sistema sin exponer credenciales internas.
- Como **Administrador**, quiero configurar webhooks por evento para cada socio, para que sus sistemas reciban notificaciones automáticas sin necesitar polling.
- Como **Socio tecnológico**, quiero consumir los KPIs de puntualidad y eficiencia vía API REST autenticada, para integrarlos en mis propios sistemas operacionales.
- Como **Administrador**, quiero consultar el historial de uso de la API por socio, para auditar el consumo y detectar abusos.

## Fuera de alcance

- Portal de developer self-service para que el socio gestione sus propias claves.
- Documentación Swagger/OpenAPI pública en esta versión.
- Rate limiting por IP además del límite por clave.
- SDK cliente en otros lenguajes.
- Monetización o cobro por uso de API.
- Soporte de OAuth2 o JWT para socios (solo API key en esta entrega).
