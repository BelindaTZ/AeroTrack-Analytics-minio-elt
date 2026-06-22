# Especificación Táctica — Seguridad

**Módulo:** Seguridad
**Prefijo:** SEG
**Código fuente:** `app/seguridad/`
**Casos de uso cubiertos:** CU-T01 (Gestionar usuarios del sistema), CU-T02 (Administrar roles y asignar permisos)
**Actor:** Administrador

---

## Funcionalidad 1: Gestionar usuarios del sistema (CU-T01)

Administración CRUD de usuarios del sistema desde `app/seguridad/usuarios/usuarios.py`. El repositorio no almacena usuarios en tabla propia; las operaciones se delegan a PocketBase colección `app_users`.

### RF-SEG-001 — Listar usuarios
El sistema lista usuarios en `GET /auth/usuarios` con paginación de 20 registros por página, ordenados por `-created`. Soporta filtros combinables: texto libre (`q`, busca en `nombre` y `email`), `rol_id` y `activo` (true/false). Muestra el rol expandido desde PocketBase.

### RF-SEG-002 — Crear usuario con contraseña temporal
`POST /auth/usuarios` recibe `nombre`, `email`, `rol_id`. El sistema genera una contraseña temporal mediante `generar_contrasena_temporal(nombre)` (formato: `Nombre.Año@3digitos`), la envía por correo vía `email_utils.send_welcome_email()` con el enlace de login, y persiste en PocketBase con `activo=True`. El email de bienvenida es transaccional (no bloquea la creación si falla el envío, muestra advertencia al administrador).

### RF-SEG-003 — Editar datos de usuario
`GET /auth/usuarios/{uid}` muestra formulario precargado. `POST /auth/usuarios/{uid}` actualiza `nombre`, `email` y `rol_id` en PocketBase. Registra auditoría con tipo `editar`.

### RF-SEG-004 — Cambiar estado activo/inactivo
`POST /auth/usuarios/{uid}/estado` conmuta el flag `activo` del usuario. Un usuario inactivo no puede iniciar sesión (validado en login). Muestra modal de confirmación antes de ejecutar.

### RF-SEG-005 — Protección de auto-desactivación
El sistema rechaza explícitamente (`if uid == user["sub"]`) que un administrador se desactive a sí mismo, retornando error "No puedes desactivar tu propia cuenta." Previene el bloqueo administrativo irreversible.

### RF-SEG-006 — Restablecer contraseña
`POST /auth/usuarios/{uid}/reset-password` genera una nueva contraseña temporal, la asigna en PocketBase via `change_user_password()`, y muestra la nueva contraseña al administrador en pantalla (única excepción a no mostrar credenciales, por ser entorno controlado).

### RNF-SEG-001 — Sesión JWT inmutable al cambiar email
El JWT usa `sub = record["id"]` (id de PocketBase) como identificador, no el email. Cambiar el email del usuario o su propia contraseña no invalida las sesiones activas.

---

## Funcionalidad 2: Administrar roles y asignar permisos (CU-T02)

CRUD de roles desde `app/seguridad/rbac/roles_admin.py` y gestión de matriz de permisos desde `app/seguridad/rbac/permisos.py`. Los roles se almacenan en PocketBase colección `roles`; los permisos asignados en `roles_permisos`.

### RF-SEG-007 — Listar roles con conteo de usuarios
`GET /auth/roles` muestra todos los roles ordenados por nombre, cada uno con etiqueta "Sistema"/"Personalizado" según `es_sistema`, y el conteo de usuarios asignados obtenido consultando `app_users` por `rol_id`.

### RF-SEG-008 — Crear rol
`POST /auth/roles` recibe `nombre` y `descripción`. Crea el rol en PocketBase con `es_sistema=False`, `activo=True` (solo roles personalizados pueden crearse).

### RF-SEG-009 — Editar rol (con protección de sistema)
`GET /auth/roles/{rid}` carga formulario. `POST /auth/roles/{rid}` actualiza nombre y descripción. Roles con `es_sistema=True` no pueden editarse (redirección con error).

### RF-SEG-010 — Eliminar rol (con protecciones)
`POST /auth/roles/{rid}/eliminar`. Bloqueado si:
- `es_sistema=True` → "No se puede eliminar un rol del sistema."
- Tiene usuarios asignados → "El rol tiene N usuario(s) asignado(s). Reasígnalos primero."

Al eliminar, realiza cascada manual: borra todos los registros en `roles_permisos` vinculados al rol antes de eliminar el rol.

### RF-SEG-011 — Gestionar matriz de permisos por rol
`GET /auth/roles/{rid}/permisos` muestra formulario con todos los módulos como filas y las 7 acciones disponibles (ver, crear, editar, eliminar, ejecutar, exportar, configurar) como columnas con checkboxes. Muestra permisos actuales precargados.

### RF-SEG-012 — Guardado de permisos como replace completo
`POST /auth/roles/{rid}/permisos`: elimina todos los registros `roles_permisos` existentes para el rol (replace completo), luego inserta solo los seleccionados. Esto evita estados inconsistentes por selecciones parciales.

### RF-SEG-013 — Invalidación de caché al guardar permisos
Tras guardar permisos, invoca `invalidate_permission_cache(rid)` que elimina la entrada del caché en memoria del rol modificado. La próxima solicitud de cualquier usuario de ese rol forzará una recarga desde PocketBase.

### RNF-SEG-002 — Caché de permisos con TTL 5 minutos
Los permisos por rol se cachean en `_perm_cache` (`app/shared/deps.py`) con `_PERM_TTL = 300` segundos. Cada consulta verifica expiración; si caducó, recarga y actualiza.

### RNF-SEG-003 — Vistas de solo lectura usan el permiso "ver"
Las rutas de listado (`GET`) usan `require_permission("seguridad", "ver")`; las rutas de escritura usan `crear`, `editar`, `eliminar` o `configurar` según corresponda.

### RNF-SEG-004 — JWT HS256 con TTL y clave secreta configurables
El JWT usa algoritmo HS256 con TTL configurable vía variable de entorno `TOKEN_EXPIRE_MINUTES` (sin valor por defecto en código) y clave secreta configurable vía `SECRET_KEY` — Principio IV de la constitución.

### RNF-SEG-005 — Autorización en capa de aplicación
Toda autorización se valida en la capa de aplicación (FastAPI), nunca en la base de datos — Principio III de la constitución.

### RNF-SEG-006 — Auditoría de acciones administrativas
Toda acción administrativa relevante debe registrarse en el log de auditoría inmutable — Principio V de la constitución.

---

## Reglas de negocio

### RN-SEG-001 — Roles de sistema inmutables
Los roles con `es_sistema=True` no pueden editarse ni eliminarse. Solo roles personalizados (`es_sistema=False`) son modificables.

### RN-SEG-002 — No auto-desactivación
Un administrador no puede desactivar su propia cuenta. Garantiza que siempre haya al menos un administrador activo.

### RN-SEG-003 — Email único por usuario
PocketBase enforces unicidad de email en colección `app_users`. El sistema verifica adicionalmente antes de actualizar perfil que el nuevo email no pertenezca a otro usuario.

### RN-SEG-004 — Contraseña temporal en primer acceso
Todo usuario nuevo recibe contraseña temporal. El sistema no provee formulario de "cambio obligatorio en primer login"; el usuario debe cambiarla voluntariamente desde su perfil.

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
1. El Administrador accede a `GET /auth/usuarios` y visualiza la lista paginada de usuarios con filtros por texto libre, rol y estado activo/inactivo.
2. El Administrador crea un usuario mediante `POST /auth/usuarios`; el sistema genera una contraseña temporal, la asigna en PocketBase y envía un email de bienvenida.
3. El Administrador navega a `GET /auth/roles/{rid}/permisos`, selecciona las acciones permitidas para cada módulo y guarda mediante `POST /auth/roles/{rid}/permisos`.
4. El sistema aplica el reemplazo completo de permisos (elimina todos los existentes, inserta solo los seleccionados) e invalida la caché del rol modificado.
5. El Administrador intenta desactivar a otro usuario; el sistema conmuta el flag `activo` y registra la operación en auditoría.

### Manejo de errores
- **Auto-desactivación:** Si el Administrador intenta desactivar su propia cuenta (`uid == user["sub"]`), el sistema rechaza con "No puedes desactivar tu propia cuenta."
- **Email duplicado:** Al crear o editar un usuario con un email ya existente en PocketBase, el sistema retorna error de validación antes de persistir.
- **Rol de sistema inmutable:** Intentar editar o eliminar un rol con `es_sistema=True` retorna error y redirige sin modificar datos.
- **Rol con usuarios asignados:** Intentar eliminar un rol que tiene al menos un usuario asignado retorna "El rol tiene N usuario(s) asignado(s). Reasígnalos primero."
- **Error en envío de email:** Si el email de bienvenida no puede enviarse, la creación del usuario no se bloquea pero se muestra una advertencia al Administrador.

---

## Criterios de aceptación

- **CU-T01:** Dado que el Administrador accede a la gestión de usuarios, cuando crea, edita, desactiva o restablece la contraseña de un usuario, entonces el sistema ejecuta la operación en PocketBase y registra la acción en el log de auditoría.
- **CU-T02:** Dado que el Administrador accede a la gestión de roles, cuando crea, edita, elimina o modifica los permisos de un rol, entonces el sistema aplica las reglas de negocio correspondientes (roles de sistema inmutables, reemplazo completo de permisos, protección de roles con usuarios asignados) e invalida la caché del rol modificado.

---

## Dependencias

- **Seguridad:** Autenticación mediante JWT y autorización sobre el propio módulo de seguridad (permisos `seguridad:ver`, `seguridad:crear`, `seguridad:editar`, `seguridad:eliminar`).
- **PocketBase:** Colecciones `app_users` (almacenamiento de usuarios), `roles` (roles del sistema), `roles_permisos` (asignación de permisos por rol) y `auditoria_log` (registro de auditoría).
- **Email:** Servicio de correo electrónico para envío de contraseñas temporales (`email_utils.send_welcome_email`).

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
