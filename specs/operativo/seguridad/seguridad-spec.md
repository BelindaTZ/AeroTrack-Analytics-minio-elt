# Especificación Operativa — Seguridad

**Módulo:** Seguridad
**Prefijo:** SEG
**Código fuente:** `app/seguridad/`
**Casos de uso cubiertos:** CU-O01 (Iniciar sesión), CU-O02 (Cerrar sesión), CU-O03 (Ver y editar perfil propio), CU-O04 (Ver matriz de permisos del sistema)
**Actor:** Administrador/Analista de Datos

---

## Funcionalidad 1: Iniciar sesión (CU-O01) y Cerrar sesión (CU-O02)

Autenticación basada en JWT almacenado en cookie HTTP-only.

### RF-SEG-014 — Mostrar formulario de inicio de sesión
El sistema debe mostrar un formulario de inicio de sesión con campos de email y contraseña. Si el usuario ya posee una sesión activa, debe redirigir al panel principal. La vista incluye estadísticas de accesos recientes.

### RF-SEG-015 — Autenticar credenciales
El sistema debe validar las credenciales del usuario (email y contraseña) contra el repositorio de usuarios. Si las credenciales son inválidas, debe registrar el evento en auditoría como intento de login fallido y retornar el mensaje "Credenciales incorrectas".

### RF-SEG-016 — Validar cuenta activa al iniciar sesión
El sistema debe rechazar el inicio de sesión de usuarios con cuenta desactivada, mostrando el mensaje "Cuenta desactivada. Contacte al administrador." y registrando el evento en auditoría.

### RF-SEG-017 — Crear JWT y cookie de sesión
El sistema debe generar un token de sesión firmado tras una autenticación exitosa, conteniendo el identificador único del usuario, email, nombre, rol y estado. El token debe almacenarse en una cookie protegida contra acceso desde JavaScript y con restricciones de envío entre sitios, con vigencia de 1 hora (configurable). Tras el login exitoso, el sistema debe redirigir al panel principal.

### RF-SEG-018 — Cerrar sesión
El sistema debe eliminar la cookie de sesión al cerrar sesión, registrar el evento de logout en auditoría y redirigir a la página de inicio de sesión.

### RNF-SEG-007 — Identificador de sesión basado en ID de usuario
El token de sesión debe utilizar el identificador único del usuario (no el email) como sujeto del token. Esto garantiza que modificar el email no invalida las sesiones activas.

### RNF-SEG-008 — Cookie HTTP-only y SameSite=Lax
El sistema debe emitir la cookie de sesión con protección contra acceso desde JavaScript y restricciones de envío en solicitudes entre sitios, mitigando ataques XSS y CSRF.

### RNF-SEG-009 — Registro de intentos fallidos en auditoría
El sistema debe registrar en auditoría todo intento de inicio de sesión fallido (credenciales inválidas o cuenta desactivada), incluyendo la dirección IP, marca temporal y resultado.

---

## Funcionalidad 2: Ver y editar perfil propio (CU-O03)

Gestión de datos personales y contraseña del usuario autenticado.

### RF-SEG-019 — Ver perfil propio
El sistema debe mostrar al usuario autenticado su información de perfil: nombre, email, rol asignado, estado de cuenta y fecha de creación. Requiere sesión activa.

### RF-SEG-020 — Editar datos personales (nombre y email)
El sistema debe permitir al usuario cambiar su nombre y email. La validación incluye: (1) formato de email válido; (2) unicidad del email, verificando que ningún otro usuario en el sistema lo tenga registrado. El sistema debe registrar la acción en auditoría.

### RF-SEG-021 — Cambiar contraseña
El sistema debe permitir al usuario cambiar su contraseña verificando: (1) coincidencia entre la nueva contraseña y su confirmación; (2) corrección de la contraseña actual. Si ambas verificaciones son exitosas, actualiza la contraseña y registra la acción en auditoría.

### RNF-SEG-010 — Cambio de email no invalida sesión
Al utilizar el identificador único del usuario en el token de sesión, modificar el email no requiere regenerar el token. La sesión continúa activa tras el cambio.

### RNF-SEG-011 — Verificación de contraseña actual antes del cambio
El sistema debe exigir la contraseña actual como paso de verificación, previniendo cambios no autorizados si la sesión queda abierta.

---

## Funcionalidad 3: Ver matriz de permisos del sistema (CU-O04)

Visualización de solo lectura de la matriz de permisos del sistema.

### RF-SEG-022 — Mostrar matriz de permisos
El sistema debe mostrar una matriz de permisos de solo lectura, con los módulos del sistema como filas, los roles como columnas, y en cada celda las acciones permitidas representadas visualmente mediante indicadores de color.

### RNF-SEG-012 — Sin controles de edición en matriz pública
La vista de matriz no debe incluir formularios ni controles de edición. La modificación de permisos se realiza exclusivamente desde la interfaz de gestión por rol.

---

## Reglas de negocio

### RN-SEG-005 — Bloqueo por cuenta inactiva
Un usuario con cuenta desactivada no puede autenticarse bajo ninguna circunstancia. El sistema muestra el mensaje "Cuenta desactivada. Contacte al administrador." sin revelar el motivo técnico específico.

### RN-SEG-006 — Sesión expira a los 60 minutos
El token de sesión tiene vigencia de 60 minutos (configurable). No existe mecanismo de renovación automática; al expirar, el usuario debe iniciar sesión nuevamente.

### RN-SEG-007 — El email es único en el sistema
Tanto en creación como en edición de perfil, el sistema verifica que el email no esté siendo usado por otro usuario. La validación se aplica en la capa de aplicación.

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
1. El usuario accede a la página de inicio de sesión, visualiza el formulario e ingresa su email y contraseña.
2. El sistema valida las credenciales; si coinciden, genera un token de sesión de 1h, establece una cookie protegida y redirige al panel principal.
3. El usuario navega a su perfil, visualiza sus datos actuales; edita su nombre y email y los guarda.
4. El usuario cambia su contraseña proporcionando la contraseña actual y la nueva.
5. El usuario cierra sesión; el sistema elimina la cookie y redirige a la página de inicio de sesión.

### Manejo de errores
- **Credenciales inválidas:** El intento de login con email/contraseña incorrectos retorna "Credenciales incorrectas" y registra un evento de login fallido en auditoría.
- **Cuenta desactivada:** El intento de login con cuenta desactivada retorna "Cuenta desactivada. Contacte al administrador."
- **Email duplicado en perfil:** La edición de perfil con un email ya existente retorna error de validación y no actualiza el registro.
- **Contraseña actual incorrecta:** El cambio de contraseña con contraseña actual errónea retorna error sin revelar si la cuenta existe.

---

## Criterios de aceptación

- **CU-O01:** Dado que el usuario ingresa credenciales válidas en la página de login, cuando el sistema las valida, entonces genera un token de sesión, establece una cookie protegida y redirige al panel principal.
- **CU-O02:** Dado que el usuario tiene una sesión activa, cuando solicita cerrar sesión, entonces el sistema elimina la cookie y redirige a la página de login.
- **CU-O03:** Dado que el usuario está autenticado, cuando accede a su perfil, entonces puede editar su nombre y email (con validación de unicidad) y cambiar su contraseña (verificando la contraseña actual).
- **CU-O04:** Dado que el usuario está autenticado, cuando accede a la matriz de permisos, entonces el sistema muestra una tabla de solo lectura con módulos, roles y acciones permitidas.

---

## Dependencias

- **Seguridad:** Autenticación mediante JWT y autorización sobre los recursos del módulo operativo de seguridad.
- **PocketBase:** Colecciones `app_users` (validación de credenciales, actualización de perfil), `roles` (información del rol del usuario), `roles_permisos` (matriz de permisos), `modulos` (catálogo de módulos del sistema para la matriz de permisos) y `auditoria` (registro de eventos de login y perfil).
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

---

## Requerimientos de configuración

### RNF-SEG-013 — SECRET_KEY obligatoria sin valor por defecto
El sistema debe requerir que la variable de entorno `SECRET_KEY` esté definida en el archivo `.env` antes del arranque. Si la variable no está presente o tiene el valor por defecto `"changeme"`, el sistema debe lanzar una excepción y detener el inicio. Esta restricción garantiza que ningún secreto quede hardcodeado en el código fuente.
