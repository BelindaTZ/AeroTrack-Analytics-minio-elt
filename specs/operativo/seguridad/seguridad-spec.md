# Especificación Operativa — Seguridad

**Módulo:** Seguridad
**Prefijo:** SEG
**Código fuente:** `app/seguridad/`
**Casos de uso cubiertos:** CU-O01 (Iniciar sesión), CU-O02 (Cerrar sesión), CU-O03 (Ver y editar perfil propio), CU-O04 (Ver matriz de permisos del sistema)
**Actor:** Usuario autenticado

---

## Funcionalidad 1: Iniciar sesión (CU-O01) y Cerrar sesión (CU-O02)

Autenticación basada en JWT almacenado en cookie HTTP-only, implementada en `app/seguridad/router.py` y `app/seguridad/jwt/service.py`.

### RF-SEG-021 — Mostrar formulario de inicio de sesión
`GET /auth/login` renderiza formulario con campos de email y contraseña. Si el usuario ya tiene sesión activa, redirige a `/pipeline`. Muestra estadísticas de login en la vista.

### RF-SEG-022 — Autenticar credenciales
`POST /auth/login` valida email/contraseña contra PocketBase vía `pb_client.auth_user(email, password)`. Si las credenciales son inválidas, registra auditoría `login_fallido` y retorna error "Credenciales incorrectas".

### RF-SEG-023 — Validar cuenta activa al iniciar sesión
Si el usuario existe pero su flag `activo` es `false`, se rechaza el login con mensaje "Cuenta desactivada. Contacte al administrador." y se registra en auditoría.

### RF-SEG-024 — Crear JWT y cookie de sesión
Tras autenticación exitosa, genera un JWT con payload `{sub, email, nombre, rol_id, activo}` firmado con HS256. Lo almacena en cookie `access_token` con flags `httponly=True`, `samesite="lax"`, `max_age=3600` (1 hora, configurable vía `TOKEN_EXPIRE_MINUTES`). Redirige a `/pipeline`.

### RF-SEG-025 — Cerrar sesión
`POST /auth/logout` elimina la cookie `access_token`, registra auditoría `logout` y redirige a `/auth/login?msg=sesion_cerrada`.

### RNF-SEG-021 — JWT con sub = id de PocketBase
El campo `sub` del JWT es el `id` de PocketBase (`record["id"]`), no el email. Esto asegura que cambiar el email no invalida la sesión.

### RNF-SEG-022 — Cookie HTTP-only y SameSite=Lax
La cookie de sesión no es accesible desde JavaScript (`httponly`) y se envía solo en navegación de mismo sitio (`samesite=lax`), mitigando XSS y CSRF.

### RNF-SEG-023 — Registro de intentos fallidos en auditoría
Cada intento de login fallido (credenciales inválidas o cuenta desactivada) se registra en auditoría con IP, timestamp, y resultado.

---

## Funcionalidad 2: Ver y editar perfil propio (CU-O03)

Gestión de datos personales y contraseña desde `app/seguridad/router.py` (rutas `/perfil`).

### RF-SEG-026 — Ver perfil propio
`GET /auth/perfil` carga los datos del usuario desde PocketBase expandiendo el rol, y renderiza vista con nombre, email, rol, estado y fecha de creación. Exige sesión activa (`require_user`).

### RF-SEG-027 — Editar datos personales (nombre y email)
`POST /auth/perfil/datos` permite al usuario cambiar su `nombre` y `email`. Valida:
1. Formato de email mediante librería `email_validator`.
2. Unicidad: consulta PocketBase para verificar que ningún otro usuario tenga ese email (`existentes[0]["id"] != user["sub"]`).
Registra auditoría con tipo `editar`.

### RF-SEG-028 — Cambiar contraseña
`POST /auth/perfil/password` recibe `password_actual`, `password_nuevo`, `password_confirm`. Verifica:
1. Coincidencia entre nuevo password y confirmación.
2. Contraseña actual correcta mediante `pb_client.auth_user(user["email"], password_actual)`.
3. Si OK, actualiza vía `pb_client.change_user_password()`.
Registra auditoría con tipo `editar`.

### RNF-SEG-024 — Cambio de email no invalida sesión
Al usar `sub = record["id"]` en el JWT, modificar el email no requiere regenerar el token. La sesión continúa activa tras el cambio.

### RNF-SEG-025 — Verificación de contraseña actual antes del cambio
El sistema exige la contraseña actual como paso de verificación, previniendo cambios no autorizados si la sesión queda abierta.

---

## Funcionalidad 3: Ver matriz de permisos del sistema (CU-O04)

Visualización de solo lectura de la matriz de permisos desde `app/seguridad/rbac/permisos.py`.

### RF-SEG-029 — Mostrar matriz de permisos
`GET /auth/roles/matriz` renderiza matriz de solo lectura con módulos como filas, roles como columnas, y en cada celda las acciones permitidas representadas como badges de colores. Usa helper `_permisos_de_rol()` para cada rol.

### RNF-SEG-026 — Sin controles de edición en matriz pública
La vista de matriz no incluye formularios ni botones de guardado. Para editar permisos, el administrador debe usar la interfaz de gestión por rol (`/auth/roles/{rid}/permisos`).

---

## Reglas de negocio

### RN-SEG-021 — Bloqueo por cuenta inactiva
Un usuario con `activo=false` no puede autenticarse bajo ninguna circunstancia. No se notifica el motivo específico al usuario (se muestra "Cuenta desactivada").

### RN-SEG-022 — Sesión expira a los 60 minutos
El token JWT expira según `TOKEN_EXPIRE_MINUTES` (por defecto 60). No existe mecanismo de refresh token; al expirar, el usuario debe volver a iniciar sesión.

### RN-SEG-023 — El email es único en el sistema
Tanto en creación como en edición de perfil, el sistema verifica que el email no esté siendo usado por otro usuario. La validación es doble: frontend PocketBase y verificación explícita en el backend.

---

## Historias de usuario

- Como usuario autenticado, quiero iniciar sesión con email y contraseña, para acceder a las funciones del sistema según mi rol.
- Como usuario autenticado, quiero cerrar sesión de forma segura, para proteger mi cuenta al terminar mi trabajo.
- Como usuario autenticado, quiero editar mi nombre y correo, y cambiar mi contraseña verificando la actual, para mantener mis datos actualizados sin depender de un Administrador.
- Como Administrador, quiero consultar la matriz completa de permisos en modo lectura, para auditar qué puede hacer cada rol en el sistema.

---

## Objetivo

Gestionar la autenticación de usuarios (inicio y cierre de sesión), la edición del perfil propio y la consulta de la matriz de permisos del sistema, garantizando un acceso seguro y controlado a los módulos de la plataforma.

---

## Escenarios

### Camino feliz
1. El usuario accede a `GET /auth/login`, visualiza el formulario e ingresa su email y contraseña.
2. `POST /auth/login` valúa las credenciales contra PocketBase: si coinciden, genera un JWT de 1h (`max_age=3600`), establece una cookie HTTP-only y redirige a `/pipeline`.
3. El usuario navega a `GET /auth/perfil`, visualiza sus datos actuales; edita su nombre y email y los guarda mediante `POST /auth/perfil/datos`.
4. El usuario cambia su contraseña mediante `POST /auth/perfil/password`, proporcionando la contraseña actual y la nueva.
5. El usuario cierra sesión mediante `POST /auth/logout`; el sistema elimina la cookie y redirige a `/auth/login`.

### Manejo de errores
- **Credenciales inválidas:** `POST /auth/login` con email/contraseña incorrectos retorna "Credenciales incorrectas" y registra un evento `login_fallido` en auditoría.
- **Cuenta desactivada:** `POST /auth/login` con `activo=false` retorna "Cuenta desactivada. Contacte al administrador."
- **Email duplicado en perfil:** `POST /auth/perfil/datos` con un email ya existente retorna error de validación y no actualiza el registro.
- **Contraseña actual incorrecta:** `POST /auth/perfil/password` con contraseña actual errónea retorna error sin revelar si la cuenta existe.

---

## Criterios de aceptación

- **CU-O01:** Dado que el usuario ingresa credenciales válidas en la página de login, cuando el sistema las valida contra PocketBase, entonces genera un JWT, establece una cookie HTTP-only y redirige al panel principal.
- **CU-O02:** Dado que el usuario tiene una sesión activa, cuando solicita cerrar sesión, entonces el sistema elimina la cookie y redirige a la página de login.
- **CU-O03:** Dado que el usuario está autenticado, cuando accede a su perfil, entonces puede editar su nombre y email (con validación de unicidad) y cambiar su contraseña (verificando la contraseña actual).
- **CU-O04:** Dado que el usuario está autenticado, cuando accede a la matriz de permisos, entonces el sistema muestra una tabla de solo lectura con módulos, roles y acciones permitidas.

---

## Dependencias

- **Seguridad:** Autenticación mediante JWT y autorización sobre los recursos del módulo operativo de seguridad.
- **PocketBase:** Colecciones `app_users` (validación de credenciales, actualización de perfil), `roles` (información del rol del usuario), `roles_permisos` (matriz de permisos) y `auditoria_log` (registro de eventos de login y perfil).
- **Email:** Servicio de correo electrónico para envío de notificaciones de cambio de contraseña.

---

## Casos de uso relacionados

- CU-O01 (Iniciar sesión en el sistema)
- CU-O02 (Cerrar sesión)
- CU-O03 (Editar perfil de usuario)
- CU-O04 (Consultar matriz de permisos)

---

## Fuera de alcance

- Autenticación biométrica o por tokens de hardware.
- Recuperación de contraseña por correo electrónico (solo el administrador puede restablecer contraseñas).
- Historial de cambios de perfil por usuario.
- Personalización de la vista de matriz de permisos.
- Bloqueo temporal de cuenta por múltiples intentos fallidos.
