# Especificación Táctica — Seguridad

**Módulo:** Seguridad
**Prefijo:** SEG
**Código fuente:** `app/seguridad/`
**Casos de uso cubiertos:** CU-T01 (Gestionar usuarios del sistema), CU-T02 (Administrar roles y asignar permisos)
**Actor:** Administrador

---

## Funcionalidad 1: Gestionar usuarios del sistema (CU-T01)

Administración CRUD de usuarios del sistema. El repositorio de usuarios se almacena en la colección `app_users` de PocketBase; las operaciones se delegan a dicho repositorio.

### RF-SEG-001 — Listar usuarios
El sistema debe listar usuarios con paginación de 20 registros por página, ordenados por fecha de creación descendente. Debe soportar filtros combinables: texto libre (busca en nombre y email), rol y estado (activo/inactivo), mostrando el rol expandido de cada usuario.

### RF-SEG-002 — Crear usuario con contraseña temporal
El sistema debe crear un usuario recibiendo nombre, email y rol. El sistema debe generar automáticamente una contraseña temporal, enviarla al nuevo usuario por correo electrónico con el enlace de acceso, y persistir el usuario con estado activo. El envío de correo es transaccional: si falla, la creación del usuario no se bloquea y se muestra advertencia al administrador.

### RF-SEG-003 — Editar datos de usuario
El sistema debe mostrar un formulario precargado con los datos actuales del usuario y permitir actualizar nombre, email y rol. Debe registrar la acción en auditoría.

### RF-SEG-004 — Cambiar estado activo/inactivo
El sistema debe permitir conmutar el estado activo/inactivo de un usuario. Un usuario inactivo no puede iniciar sesión. Debe mostrar confirmación antes de ejecutar el cambio.

### RF-SEG-005 — Protección de auto-desactivación
El sistema debe rechazar explícitamente que un administrador desactive su propia cuenta, retornando el error "No puedes desactivar tu propia cuenta." Esto previene el bloqueo administrativo irreversible.

### RF-SEG-006 — Restablecer contraseña
El sistema debe generar una nueva contraseña temporal para el usuario indicado y mostrarla al administrador en pantalla (única instancia controlada en que se expone una credencial generada, por tratarse de un entorno administrativo).

### RNF-SEG-001 — Sesión JWT inmutable al cambiar email
El token de sesión utiliza el identificador único del usuario (no el email). Cambiar el email del usuario o su contraseña no invalida las sesiones activas.

---

## Funcionalidad 2: Administrar roles y asignar permisos (CU-T02)

CRUD de roles y gestión de la matriz de permisos. Los roles se almacenan en PocketBase colección `roles`; los permisos asignados en `roles_permisos`.

### RF-SEG-007 — Listar roles con conteo de usuarios
El sistema debe mostrar todos los roles ordenados por nombre, cada uno con etiqueta "Sistema"/"Personalizado" según su tipo, y el conteo de usuarios asignados.

### RF-SEG-008 — Crear rol
El sistema debe permitir crear roles personalizados recibiendo nombre y descripción. Solo los roles personalizados pueden crearse desde la interfaz.

### RF-SEG-009 — Editar rol (con protección de sistema)
El sistema debe mostrar un formulario de edición para el rol seleccionado y permitir actualizar nombre y descripción. Los roles de sistema no pueden editarse; el intento redirige con error.

### RF-SEG-010 — Eliminar rol (con protecciones)
El sistema debe bloquear la eliminación de un rol si:
- Es un rol de sistema → "No se puede eliminar un rol del sistema."
- Tiene usuarios asignados → "El rol tiene N usuario(s) asignado(s). Reasígnalos primero."

Al eliminar, el sistema debe realizar la eliminación en cascada de todos los permisos asociados al rol antes de eliminarlo.

### RF-SEG-011 — Gestionar matriz de permisos por rol
El sistema debe mostrar un formulario con todos los módulos del sistema como filas y las 7 acciones disponibles (ver, crear, editar, eliminar, ejecutar, exportar, configurar) como columnas con casillas de verificación, precargado con los permisos actuales del rol.

### RF-SEG-012 — Guardado de permisos como replace completo
El sistema debe eliminar todos los permisos existentes del rol antes de insertar únicamente los seleccionados en el formulario. Esto evita estados inconsistentes por selecciones parciales.

### RF-SEG-013 — Invalidación de caché al guardar permisos
El sistema debe invalidar la caché de permisos del rol modificado tras guardar. La próxima solicitud de cualquier usuario de ese rol forzará una recarga desde el repositorio.

### RNF-SEG-002 — Caché de permisos con TTL 5 minutos
El sistema debe cachear los permisos por rol durante 5 minutos. Cada consulta verifica expiración; si caducó, recarga y actualiza.

### RNF-SEG-003 — Vistas de solo lectura usan el permiso "ver"
Las operaciones de consulta requieren permiso `seguridad:ver`; las operaciones de escritura requieren `crear`, `editar`, `eliminar` o `configurar` según corresponda.

### RNF-SEG-004 — JWT HS256 con TTL y clave secreta configurables
El sistema debe firmar los tokens JWT con el algoritmo HS256, con tiempo de expiración y clave secreta configurables mediante variables de entorno, sin valores por defecto en código — Principio IV de la constitución.

### RNF-SEG-005 — Autorización en capa de aplicación
El sistema debe validar toda autorización en la capa de aplicación, nunca en la base de datos — Principio III de la constitución.

### RNF-SEG-006 — Auditoría de acciones administrativas
El sistema debe registrar en el log de auditoría inmutable toda acción administrativa relevante — Principio V de la constitución.

---

## Reglas de negocio

### RN-SEG-001 — Roles de sistema inmutables
Los roles de sistema no pueden editarse ni eliminarse. Solo los roles personalizados son modificables.

### RN-SEG-002 — No auto-desactivación
Un administrador no puede desactivar su propia cuenta. Esto garantiza que siempre haya al menos un administrador activo.

### RN-SEG-003 — Email único por usuario
El repositorio enforces unicidad de email. El sistema verifica adicionalmente antes de actualizar perfil que el nuevo email no pertenezca a otro usuario.

### RN-SEG-004 — Contraseña temporal en primer acceso
Todo usuario nuevo recibe contraseña temporal. El sistema no provee formulario de cambio obligatorio en primer login; el usuario debe cambiarla voluntariamente desde su perfil.

---

## Historias de usuario

- Como Administrador, quiero crear usuarios con contraseña temporal enviada automáticamente por correo, para que nuevos analistas accedan al sistema desde el primer día sin intervención adicional.
- Como Administrador, quiero configurar los permisos de cada rol en una matriz visual, para controlar el acceso a cada módulo sin modificar código.

---

## Objetivo

Administrar los usuarios del sistema y la matriz de roles y permisos, garantizando el control de acceso basado en roles (RBAC) sobre todos los módulos de la plataforma.

---

## Escenarios

### Camino feliz
1. El Administrador accede a la gestión de usuarios y visualiza la lista paginada con filtros por texto libre, rol y estado activo/inactivo.
2. El Administrador crea un usuario; el sistema genera una contraseña temporal, la asigna en el repositorio y envía un email de bienvenida.
3. El Administrador navega a la gestión de permisos del rol, selecciona las acciones permitidas para cada módulo y guarda.
4. El sistema aplica el reemplazo completo de permisos e invalida la caché del rol modificado.
5. El Administrador conmuta el estado de otro usuario; el sistema registra la operación en auditoría.

### Manejo de errores
- **Auto-desactivación:** Si el Administrador intenta desactivar su propia cuenta, el sistema rechaza con "No puedes desactivar tu propia cuenta."
- **Email duplicado:** Al crear o editar un usuario con un email ya existente, el sistema retorna error de validación antes de persistir.
- **Rol de sistema inmutable:** Intentar editar o eliminar un rol de sistema retorna error y redirige sin modificar datos.
- **Rol con usuarios asignados:** Intentar eliminar un rol con al menos un usuario asignado retorna "El rol tiene N usuario(s) asignado(s). Reasígnalos primero."
- **Error en envío de email:** Si el email de bienvenida no puede enviarse, la creación del usuario no se bloquea pero se muestra una advertencia al Administrador.

---

## Criterios de aceptación

- **CU-T01:** Dado que el Administrador accede a la gestión de usuarios, cuando crea, edita, desactiva o restablece la contraseña de un usuario, entonces el sistema ejecuta la operación en el repositorio y registra la acción en el log de auditoría.
- **CU-T02:** Dado que el Administrador accede a la gestión de roles, cuando crea, edita, elimina o modifica los permisos de un rol, entonces el sistema aplica las reglas de negocio correspondientes (roles de sistema inmutables, reemplazo completo de permisos, protección de roles con usuarios asignados) e invalida la caché del rol modificado.

---

## Dependencias

- **Seguridad:** Autenticación mediante JWT y autorización sobre el propio módulo de seguridad (permisos `seguridad:ver`, `seguridad:crear`, `seguridad:editar`, `seguridad:eliminar`).
- **PocketBase:** Colecciones `app_users` (almacenamiento de usuarios), `roles` (roles del sistema), `roles_permisos` (asignación de permisos por rol) y `auditoria_log` (registro de auditoría).
- **Email:** Servicio de correo electrónico para envío de contraseñas temporales.

---

## Casos de uso relacionados

- CU-T01 (Gestionar usuarios del sistema)
- CU-T02 (Administrar roles y asignar permisos)

---

## Fuera de alcance

- Autenticación con proveedores externos (SSO, OAuth, LDAP).
- Notificaciones push o SMS para recuperación de contraseña.
- Historial de inicios de sesión por usuario.
- Roles jerárquicos o herencia de permisos entre roles.
- Bloqueo automático de cuenta por múltiples intentos fallidos de inicio de sesión.
