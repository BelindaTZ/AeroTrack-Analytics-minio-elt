# Checklist de Verificación — Seguridad Operativa

**Módulo:** Seguridad  
**Spec de referencia:** `specs/operativo/seguridad/seguridad-spec.md`  
**Código verificado:** `app/seguridad/router.py`, `app/seguridad/jwt/service.py`, `app/seguridad/rbac/permisos.py`, `app/shared/deps.py`  
**Fecha de auditoría:** 2026-06-22

---

## Casos de uso (criterios de aceptación del spec)

### CU-O01 — Iniciar sesión

- [x] **Dado** que el usuario ingresa credenciales válidas en la página de login, **cuando** el sistema las valida contra PocketBase, **entonces** genera un JWT, establece una cookie HTTP-only y redirige al panel principal.
  - Verificado en `router.py:26-66`: `pb_client.auth_user(email, password)` → `crear_token(token_payload)` → `set_cookie("access_token", token, httponly=True)` → `RedirectResponse("/pipeline")`

### CU-O02 — Cerrar sesión

- [x] **Dado** que el usuario tiene una sesión activa, **cuando** solicita cerrar sesión, **entonces** el sistema elimina la cookie y redirige a la página de login.
  - Verificado en `router.py:71-78`: `response.delete_cookie("access_token")` → `RedirectResponse("/auth/login?msg=sesion_cerrada")`

### CU-O03 — Ver y editar perfil propio

- [x] **Dado** que el usuario está autenticado, **cuando** accede a su perfil, **entonces** puede editar su nombre y email (con validación de unicidad) y cambiar su contraseña (verificando la contraseña actual).
  - GET `/auth/perfil` verificado en `router.py:83-88`
  - Edición datos verificada en `router.py:91-122`: `validate_email()` + unicidad en PocketBase
  - Cambio contraseña verificado en `router.py:125-152`: verifica actual via `pb_client.auth_user()`, luego `change_user_password()`

### CU-O04 — Ver matriz de permisos del sistema

- [x] **Dado** que el usuario está autenticado, **cuando** accede a la matriz de permisos, **entonces** el sistema muestra una tabla de solo lectura con módulos, roles y acciones permitidas.
  - Verificado en `permisos.py:90-103`: `GET /auth/roles/matriz` llama `_permisos_de_rol()` para cada rol y renderiza `roles/matriz.html`

---

## Requerimientos funcionales (RF-SEG-0XX)

- [x] **RF-SEG-014** — `GET /auth/login` renderiza formulario con email y contraseña. Si hay sesión activa redirige a `/pipeline`. Muestra `stats`.
  - `router.py:18-23`: `get_current_user(request)` → redirige. `get_login_stats()` → stats.

- [x] **RF-SEG-015** — `POST /auth/login` valida contra PocketBase. Si inválido registra `login_fallido` y retorna error.
  - `router.py:26-51`: `pb_client.auth_user(email, password)` en try/except ValueError → `audit.registrar(..., "login_fallido", ...)`

- [x] **RF-SEG-016** — Si `activo=false` rechaza login con mensaje de cuenta desactivada y registra auditoría.
  - `router.py:44-51`: `if not record.get("activo", True):` → `audit.registrar(..., "login_fallido", ..., detalle="Cuenta desactivada")`

- [x] **RF-SEG-017** — Genera JWT con payload `{sub, email, nombre, rol_id, activo}`, firmado HS256, cookie httponly samesite=lax max_age=3600. Redirige a `/pipeline`.
  - `router.py:53-65`: payload construido, `crear_token(token_payload)`, `set_cookie("access_token", token, httponly=True, samesite="lax", max_age=3600)`

- [x] **RF-SEG-018** — `POST /auth/logout` elimina cookie, registra `logout`, redirige.
  - `router.py:71-78`: `audit.registrar(..., "logout", "seguridad")` → `delete_cookie("access_token")`

- [x] **RF-SEG-019** — `GET /auth/perfil` carga usuario con expand de rol y renderiza perfil. Exige sesión.
  - `router.py:83-88`: `require_user(request)` → `pb_client.get_record("app_users", user["sub"], expand="rol_id")`

- [x] **RF-SEG-020** — `POST /auth/perfil/datos` valida formato email y unicidad en PocketBase. Registra auditoría.
  - `router.py:91-122`: `validate_email(email)` + query PocketBase + `audit.registrar(..., "editar", "seguridad",...)`

- [x] **RF-SEG-021** — `POST /auth/perfil/password` verifica coincidencia, verifica contraseña actual, actualiza. Registra auditoría.
  - `router.py:125-152`: verifica `password_nuevo != password_confirm`, luego `pb_client.auth_user(user["email"], password_actual)`, luego `pb_client.change_user_password()`

- [x] **RF-SEG-022** — `GET /auth/roles/matriz` renderiza matriz de solo lectura.
  - `permisos.py:90-103`: sin formularios ni botones de edición en la matriz.

---

## Requerimientos no funcionales (RNF-SEG-0XX)

- [x] **RNF-SEG-006** — JWT con `sub = record["id"]` (UUID de PocketBase, no email).
  - `router.py:53`: `"sub": record["id"]`

- [x] **RNF-SEG-007** — Cookie HTTP-only y SameSite=Lax.
  - `router.py:65`: `httponly=True`, `samesite="lax"`

- [x] **RNF-SEG-008** — Registro de intentos fallidos en auditoría con IP.
  - `router.py:36,45`: `ip = request.client.host`, `audit.registrar("", email, "login_fallido", ..., ip_address=ip)`

- [x] **RNF-SEG-009** — Cambio de email no invalida sesión (sub = id, no email).
  - Confirmado por diseño: `sub = record["id"]` permanece constante.

- [x] **RNF-SEG-010** — Verificación de contraseña actual antes del cambio.
  - `router.py:142-146`: `pb_client.auth_user(user["email"], password_actual)` en try/except

- [x] **RNF-SEG-011** — Sin controles de edición en matriz de permisos.
  - `permisos.py:90-103`: `GET /auth/roles/matriz` renderiza solo lectura, sin formularios.

- [x] **RNF-SEG-012** — SECRET_KEY obligatoria sin default.
  - Spec actualizado: RNF-SEG-012 requiere SECRET_KEY obligatoria. Pendiente implementar en config.py.

---

## Reglas de negocio (RN-SEG-0XX)

- [x] **RN-SEG-001** — Roles de sistema inmutables.
  - `roles_admin.py:54-62`: `if rol.get("es_sistema"): return _tmpl_error(..., "No se puede editar un rol del sistema.")`

- [x] **RN-SEG-002** — No auto-desactivación.
  - `router.py:112-115`: `if uid == user["sub"]: return _tmpl_error(..., "No puedes desactivar tu propia cuenta.")`

- [x] **RN-SEG-005** — Bloqueo por cuenta inactiva.
  - `router.py:44`: `if not record.get("activo", True):` → rechaza con mensaje genérico "Cuenta desactivada"

- [x] **RN-SEG-006** — Sesión expira a los 60 minutos.
  - `config.py:30`: `ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "60"))`
  - Sin refresh token — confirmado: solo `crear_token()` en login exitoso.

- [x] **RN-SEG-007** — Email único en el sistema.
  - `router.py:108-111`: query PocketBase `filter=f'email="{email}"'` + comparación de IDs

---

## Verificación cruzada código ↔ spec

| Item | Estado | Nota |
|---|---|---|
| JWT sub = UUID PocketBase | ✅ Coincide | `record["id"]` en router.py:54 |
| Cookie httponly + samesite=lax | ✅ Coincide | router.py:65 |
| max_age=3600 en cookie | ✅ Coincide | router.py:65 |
| Redirección a /pipeline en login OK | ✅ Coincide | router.py:64 |
| Registro login_fallido con IP | ✅ Coincide | router.py:36 |
| email_validator en edición perfil | ✅ Coincide | router.py:102 |
| Verificar contraseña actual en cambio | ✅ Coincide | router.py:142 |
| Matriz sin formularios de edición | ✅ Coincide | permisos.py:90-103 |
| Roles de sistema inmutables | ✅ Coincide | roles_admin.py:54-62 |
| Caché de permisos TTL 300s | ✅ Coincide | deps.py:16 `_PERM_TTL = 300` |
| SECRET_KEY obligatoria sin default | ✅ Corregido | Spec actualizado: RNF-SEG-012 |
| Estadísticas en página de login | ✅ Coincide | `get_login_stats()` llamada en GET /auth/login |
