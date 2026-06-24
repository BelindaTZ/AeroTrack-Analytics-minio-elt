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

- **RF-SOC-008**: El sistema debe exponer un endpoint público de consulta de OTP por aerolínea y período, retornando los datos de la tabla de agregación correspondiente. Parámetros: aerolínea, año y mes (opcionales).
- **RF-SOC-009**: El sistema debe exponer un endpoint público de consulta de ranking de eficiencia de rutas, retornando los datos de la tabla de agregación correspondiente. Parámetros: año y cantidad de rutas a mostrar (valor predeterminado: 10).
- **RF-SOC-010**: El sistema debe exponer un endpoint público de consulta de cancelaciones por código FAA, retornando los datos de la tabla de agregación correspondiente. Parámetros: año y mes (opcionales).
- **RF-SOC-011**: El sistema debe exponer un endpoint público de consulta de KPIs globales del período, retornando los datos de la tabla de agregación correspondiente. Parámetros: año y mes (opcionales).

### Funcionalidad 4: Ver historial de uso de la API (CU-O18)

- **RF-SOC-012**: El sistema debe registrar cada llamada a los endpoints públicos en el registro de auditoría de la API: clave utilizada, endpoint, método, código de respuesta, tiempo de respuesta en milisegundos e IP de origen.
- **RF-SOC-013**: El sistema debe mostrar el historial de llamadas vía `GET /socios/historial` con filtros por socio, endpoint y rango de fechas.
- **RF-SOC-014**: El sistema debe exponer un endpoint de historial de uso en formato JSON que permita la actualización dinámica de la tabla sin recargar la página, aplicando los mismos filtros que la vista HTML.

## Requisitos no funcionales

- **RNF-SOC-001**: La autenticación por API key se valida mediante header `Authorization: Bearer {key}` o query param `api_key`; nunca en el body.
- **RNF-SOC-002**: Los endpoints públicos retornan únicamente datos de tablas de agregación pre-calculadas; no exponen el fact table completo.
- **RNF-SOC-003**: El payload de cada webhook se firma con HMAC-SHA256 usando la `clave_hmac` del socio; header `X-AeroTrack-Signature`.
- **RNF-SOC-004**: Toda gestión de claves y webhooks (crear, revocar, configurar) se audita con módulo `socios_api`.
- **RNF-SOC-005**: El RBAC interno debe validarse en cada endpoint de gestión, exigiendo los permisos del módulo correspondiente: ver, crear, configurar, eliminar.
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

El Administrador accede al panel de socios, crea una clave para "AeroData Partners" con límite 1000 consultas/día. El sistema genera una clave única, almacena únicamente su hash y devuelve la clave en texto plano con advertencia de uso único. El Administrador configura un webhook para el evento de pipeline completado apuntando a una URL de destino del socio con clave HMAC. El socio usa la clave para consultar datos de OTP por aerolínea y período, recibiendo el JSON con la información solicitada. El sistema incrementa el contador de consultas y registra la llamada en el registro de auditoría de la API. Al completarse el pipeline, el sistema notifica a los webhooks suscritos con payload firmado, realizando hasta 3 reintentos si es necesario.

### Manejo de errores

- **Clave inválida**: Consulta sin clave o con clave incorrecta → 401 "API key inválida".
- **Clave revocada**: 401 "API key revocada".
- **Clave expirada**: 401 "API key expirada".
- **Límite superado**: 429 "Límite diario de consultas alcanzado".
- **Webhook falla 3 veces**: se registra el estado fallido en la configuración del webhook; no bloquea otras operaciones.
- **Evento inválido**: el sistema registra advertencia y no dispara notificaciones.
- **Sin webhooks suscritos**: el sistema registra depuración y retorna sin error.

## Criterios de aceptación

1. Dado que el Administrador crea una clave API, cuando el socio la usa en un endpoint público de consulta, entonces el sistema valida existencia, estado activo, no expiración y límite, retorna los datos solicitados y registra la llamada en el historial.
2. Dado que una clave supera su límite diario de 1000 consultas, cuando el socio realiza la petición adicional, entonces el sistema retorna 429.
3. Dado que se configura un webhook para el evento de pipeline completado, cuando el pipeline termina exitosamente, entonces el sistema envía un payload JSON firmado con HMAC-SHA256 a la URL del socio.
4. Dado que el Administrador consulta el historial filtrado por endpoint de OTP, entonces el sistema muestra solo las llamadas a ese endpoint.
5. Dado que el Administrador revoca una clave, cuando el socio intenta usarla, entonces el sistema retorna 401.

## Dependencias

- **Pipeline ELT** — las tablas de agregación de datos analíticos son la fuente de datos de los endpoints públicos.
- **Seguridad** — RBAC interno para gestión de claves y webhooks con permisos del módulo `socios_api`.
- **Auditoría** — registro de creación y revocación de claves, configuración de webhooks.
- **HTTP** — cliente HTTP asíncrona para envío de webhooks con reintentos.

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
