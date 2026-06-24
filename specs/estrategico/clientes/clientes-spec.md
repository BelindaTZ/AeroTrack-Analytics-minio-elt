# Módulo: Clientes

**Prefijo:** CLI · **Paquete técnico:** `app/clientes/` · **Entrega:** Entrega 4

## Objetivo

Administrar la cartera de clientes aerolínea de AeroTrack, gestionar suscripciones de entrega automática de reportes y generar tokens de demostración para captación comercial.

## Actores

- **Administrador** — gestiona clientes, suscripciones, tokens demo e historial de entregas.

## Requisitos funcionales

### Funcionalidad 1: Ver panel de captación y gestionar clientes aerolínea (CU-E19, CU-T10)

- **RF-CLI-001**: El sistema debe mostrar un panel con métricas globales de la cartera: total de clientes, activos, inactivos y en plan básico/prueba.
- **RF-CLI-002**: El sistema debe permitir listar clientes con paginación por orden de creación.
- **RF-CLI-003**: El sistema debe permitir crear un cliente con los siguientes datos: nombre, código IATA (2 letras, único), email de contacto, tipo de servicio (básico/profesional/enterprise), fecha de inicio y notas opcionales.
- **RF-CLI-004**: El sistema debe permitir editar los datos de un cliente existente.
- **RF-CLI-005**: El sistema debe permitir activar o desactivar un cliente; un cliente inactivo no recibe entregas automáticas de reportes.

### Funcionalidad 2: Configurar suscripciones de reporte por cliente (CU-T11)

- **RF-CLI-006**: El sistema debe permitir crear suscripciones definiendo: tipo de reporte (PDF/Excel/CSV), frecuencia (diaria/semanal/mensual), filtros opcionales y estado activo.
- **RF-CLI-007**: El sistema debe calcular y mostrar la próxima fecha de entrega según la frecuencia configurada (1 día, 7 días o 30 días desde la creación).

### Funcionalidad 3: Generar enlace de demo y ver historial de entregas (CU-O15, CU-O16)

- **RF-CLI-008**: El sistema debe generar un token de demostración con días de expiración configurables y código IATA de la aerolínea a mostrar.
- **RF-CLI-009**: El sistema debe exponer un acceso público sin autenticación que valida el token de demostración, verifica su expiración, lo marca como usado y redirige al dashboard filtrado por la aerolínea correspondiente.
- **RF-CLI-010**: El sistema debe mostrar el historial de entregas por cliente con fecha, tipo de reporte, estado (exitoso/fallido) y enlace de descarga.

## Requisitos no funcionales

- **RNF-CLI-001**: El sistema debe registrar en auditoría toda acción de creación, edición y eliminación de clientes, con módulo identificador `clientes`.
- **RNF-CLI-002**: El sistema debe expirar automáticamente los tokens de demostración y rechazar el acceso redirigiendo al inicio de sesión si están vencidos o ya fueron utilizados.
- **RNF-CLI-003**: El sistema debe validar el control de acceso basado en roles para cada operación, exigiendo los permisos correspondientes: ver, crear, editar, eliminar y exportar.
- **RNF-CLI-004**: El sistema debe ser resiliente en operaciones de auditoría — si el servicio de persistencia no responde, la operación principal no debe interrumpirse.

## Reglas de negocio

- **RN-CLI-001**: Un cliente con estado inactivo no puede recibir entregas automáticas aunque tenga suscripciones activas.
- **RN-CLI-002**: El código IATA de un cliente debe ser único en el sistema.
- **RN-CLI-003**: Un token de demo vencido no puede reactivarse; debe generarse uno nuevo.
- **RN-CLI-004**: Un token de demostración se marca como utilizado tras el primer acceso y no puede reutilizarse.

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /clientes` | Cookie JWT | HTML con métricas y lista de clientes |
| `POST /clientes` | `{nombre, iata, contacto_email, tipo_servicio, fecha_inicio, notas}` | JSON del cliente creado o error |
| `GET /clientes/{id}` | Cookie JWT, id | HTML con detalle del cliente |
| `POST /clientes/{id}` | `{nombre, iata, contacto_email, ...}` | JSON del cliente actualizado |
| `POST /clientes/{id}/estado` | `{activo: bool}` | JSON del cliente con nuevo estado |
| `POST /clientes/{id}/suscripcion` | `{tipo_reporte, frecuencia, filtros, activa}` | JSON de suscripción con próxima entrega |
| `POST /clientes/{id}/demo` | `{dias_expiracion, iata_demo}` | JSON con token, URL demo y expiración |
| `GET /clientes/{id}/historial` | Cookie JWT, id | JSON array de entregas históricas |
| `GET /demo/{token}` | token público | Redirect a `/dashboard?airline={iata}` o a `/auth/login` con error |

## Escenarios

### Camino feliz

El Administrador accede al panel de clientes y ve las métricas de la cartera (total: 12, activos: 9, inactivos: 3, prueba: 4). Crea un nuevo cliente con nombre "AeroLatina", IATA "AL", email "contacto@aerolatina.com", servicio "profesional". El sistema lo registra y lo muestra en la lista con estado activo. El Administrador abre el detalle, configura una suscripción mensual de PDF. El sistema calcula próxima entrega a 30 días. Genera un token de demo de 7 días para IATA "AL". Copia la URL y se la envía al prospecto. El prospecto accede al enlace de demo y es redirigido al dashboard filtrado por "AL".

### Manejo de errores

- **IATA duplicado**: `POST /clientes` retorna 400 con mensaje de error; el cliente no se crea.
- **Cliente no encontrado**: `GET /clientes/{id}` retorna template de error 404.
- **Token inválido**: `GET /demo/{token_invalido}` redirige a `/auth/login?error=Token+inválido`.
- **Token expirado**: `GET /demo/{token_expirado}` redirige a `/auth/login?error=Token+expirado`.
- **Token ya usado**: `GET /demo/{token_usado}` redirige a `/auth/login?error=Token+ya+usado`.

## Criterios de aceptación

1. Dado que el Administrador crea un cliente con código IATA único, cuando guarda, entonces el sistema registra el cliente y lo muestra en la lista con estado activo.
2. Dado que un cliente tiene suscripción activa con frecuencia mensual, cuando se crea la suscripción, entonces el sistema calcula la próxima fecha de entrega a 30 días.
3. Dado que el Administrador genera un token de demo con 7 días de expiración, cuando el prospecto accede a la URL dentro del plazo, entonces visualiza el dashboard filtrado por su aerolínea y el token se marca como usado.
4. Dado que un token de demo está expirado, cuando se accede a su URL, entonces el sistema redirige a inicio de sesión con mensaje de error.
5. Dado que el Administrador solicita el historial de entregas de un cliente, entonces el sistema retorna los registros ordenados por fecha descendente.

## Dependencias

- **Seguridad** — RBAC con permisos del módulo `clientes` y autenticación JWT.
- **Persistencia** — Servicio de almacenamiento para clientes, suscripciones, tokens de demo y historial de entregas.
- **Dashboard** — La demo redirige al dashboard en modo de solo lectura filtrado por la aerolínea del token.

## Casos de uso relacionados

CU-E19 · CU-T10 · CU-T11 · CU-O15 · CU-O16

## Historias de usuario

- Como **Administrador**, quiero ver un panel con métricas de mi cartera de clientes, para tener visibilidad ejecutiva del estado comercial del servicio.
- Como **Administrador**, quiero gestionar los datos de cada aerolínea cliente, para mantener actualizada la información de contacto y tipo de servicio contratado.
- Como **Administrador**, quiero configurar suscripciones de reporte automático por cliente, para que cada aerolínea reciba sus análisis sin intervención manual.
- Como **Administrador**, quiero generar un enlace de demo con expiración, para que un cliente potencial explore el sistema sin necesitar una cuenta permanente.
- Como **Administrador**, quiero consultar el historial de entregas por cliente, para verificar que todos los reportes se entregaron correctamente.

## Fuera de alcance

- Portal de autoservicio para que el cliente acceda directamente al sistema.
- Facturación o cobro automático.
- Integración con CRM externo.
- Personalización de plantillas de email por cliente.
- Múltiples contactos por cliente en esta versión.
