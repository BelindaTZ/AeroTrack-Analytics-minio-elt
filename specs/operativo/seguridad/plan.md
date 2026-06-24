# Plan de Implementación — Seguridad Operativa

**Módulo:** Seguridad  
**Paquete:** `app/seguridad/`  
**Prefijos:** `/auth` (auth), `/auth/usuarios` (usuarios), `/auth/roles` (permisos + roles)  
**CUs cubiertos:** CU-O01, CU-O02, CU-O03, CU-O04  
**Fuente:** código leído el 2026-06-22

---

## Routers registrados

| Router | Archivo | Prefix real en main.py |
|---|---|---|
| `auth_router` | `app/seguridad/router.py` | `/auth` |
| `usuarios_router` | `app/seguridad/usuarios/usuarios.py` | `/auth/usuarios` |
| `permisos_router` | `app/seguridad/rbac/permisos.py` | `/auth/roles` |
| `roles_router` | `app/seguridad/rbac/roles_admin.py` | `/auth/roles` |

---

## Endpoints implementados

### app/seguridad/router.py (prefix `/auth`)

| Método | Path | Permiso | Descripción |
|---|---|---|---|
| GET | `/auth/login` | ninguno | Formulario login. Si hay sesión activa redirige a `/pipeline`. Muestra `stats` de login. |
| POST | `/auth/login` | ninguno | Autentica contra PocketBase via `pb_client.auth_user(email, password)`. Si OK: genera JWT, setea cookie `access_token`, redirige a `/pipeline`. Si falla: registra `login_fallido` en auditoría y retorna error. |
| POST | `/auth/logout` | sesión válida | Elimina cookie `access_token`, registra `logout` en auditoría, redirige a `/auth/login?msg=sesion_cerrada`. |
| GET | `/auth/perfil` | `require_user` | Carga `app_users` expandiendo `rol_id`. Renderiza `perfil.html`. |
| POST | `/auth/perfil/datos` | `require_user` | Edita nombre y email. Valida formato (email_validator) y unicidad en PocketBase. Registra `editar` en auditoría. |
| POST | `/auth/perfil/password` | `require_user` | Cambia contraseña: verifica coincidencia nueva/confirmación, verifica contraseña actual via `pb_client.auth_user()`, llama `pb_client.change_user_password()`. Registra `editar` en auditoría. |

### app/seguridad/rbac/permisos.py (prefix `/auth/roles`)

| Método | Path | Permiso | Descripción |
|---|---|---|---|
| GET | `/auth/roles/matriz` | `seguridad:ver` | Matriz de solo lectura: módulos × roles con acciones permitidas. Llama `_permisos_de_rol(rol.id)` para cada rol. |
| GET | `/auth/roles/{rid}/permisos` | `seguridad:ver` | Gestionar permisos de un rol específico. |
| POST | `/auth/roles/{rid}/permisos` | `seguridad:configurar` | Guarda permisos: borra `roles_permisos` existentes del rol e inserta los seleccionados. Invalida caché del rol. Registra `configurar` en auditoría. |

---

## Funciones principales

### app/seguridad/jwt/service.py

```python
def crear_token(data: dict) -> str
    # jose.jwt.encode con SECRET_KEY, algorithm=ALGORITHM
    # Añade exp = now + ACCESS_TOKEN_EXPIRE_MINUTES

def verificar_token(token: str) -> dict
    # jose.jwt.decode — lanza JWTError si inválido o expirado
```

### app/shared/deps.py

```python
def get_current_user(request: Request) -> Optional[dict]
    # Lee cookie access_token, llama verificar_token(), retorna payload o None

def require_user(request: Request) -> dict
    # Si no hay usuario lanza _redirect_to_login (exception handler en main.py)

def require_permission(modulo: str, accion: str) -> Callable
    # Devuelve dependencia que verifica get_current_user + _get_cached_permissions
    # Lanza PermissionError si sin permiso

def _get_cached_permissions(rol_id: str) -> dict[str, list[str]]
    # Cache _perm_cache: {rol_id: {expires, permissions}}
    # TTL 300s (_PERM_TTL)
    # Llama pb_client.get_permissions_for_role(rol_id) si caché expiró

def invalidate_permission_cache(rol_id: Optional[str] = None) -> None
    # Invalida entrada específica o limpia todo el caché
```

### app/seguridad/rbac/permisos.py

```python
def _permisos_de_rol(rid: str) -> dict[str, list[str]]
    # Lee roles_permisos expand=permiso_id,permiso_id.modulo_id
    # Retorna {modulo_clave: [accion, ...]}
```

---

## Implementación del JWT

| Campo | Valor implementado |
|---|---|
| Algoritmo | HS256 (`ALGORITHM = os.getenv("ALGORITHM", "HS256")`) |
| Clave | `SECRET_KEY = os.getenv("SECRET_KEY", "changeme")` |
| Librería | `python-jose` (`from jose import jwt`) |
| Payload | `{sub, email, nombre, rol_id, activo, exp}` |
| `sub` | `record["id"]` (UUID de PocketBase, NO el email) |
| TTL | `ACCESS_TOKEN_EXPIRE_MINUTES` default 60 min |
| Cookie | nombre `access_token`, `httponly=True`, `samesite="lax"`, `max_age=3600` |
| Lectura | `request.cookies.get("access_token")` en `get_current_user()` |

**Nota de seguridad:** `SECRET_KEY` tiene default hardcodeado `"changeme"` — violación del Principio IV documentada en constitution.md como Follow-up TODO #1.

---

## Implementación del RBAC

| Aspecto | Implementación |
|---|---|
| Punto de verificación | `app/shared/deps.py:require_permission()` — dependencia FastAPI |
| Caché | `_perm_cache: dict[str, dict]` en `deps.py:15` — por `rol_id`, TTL 300s |
| Consulta a PocketBase | `pb_client.get_permissions_for_role(rol_id)` si caché expiró |
| Fallo de permiso | Lanza `PermissionError(f"Sin permiso {modulo}.{accion}")` → handler en main.py devuelve 403 |
| Fallo de sesión | Lanza `_redirect_to_login` → handler en main.py redirige a `/auth/login` |
| Invalidación | `invalidate_permission_cache(rol_id)` llamado en `POST /auth/roles/{rid}/permisos` |

---

## Acciones registradas en auditoría

| Acción | Trigger | Módulo | Detalle |
|---|---|---|---|
| `login` | Login exitoso | `seguridad` | IP del cliente |
| `login_fallido` | Credenciales inválidas o cuenta inactiva | `seguridad` | IP + motivo |
| `logout` | POST /auth/logout | `seguridad` | — |
| `editar` | POST /auth/perfil/datos | `seguridad` | `nombre=X, email=Y` |
| `editar` | POST /auth/perfil/password | `seguridad` | recurso_tipo=password |
| `configurar` | POST /auth/roles/{rid}/permisos | `seguridad` | JSON con permisos_count |

---

## Dependencias reales

```python
from jose import jwt, JWTError          # python-jose — JWT HS256
from email_validator import validate_email, EmailNotValidError  # email_validator
from app.shared.clients import pb_client  # PocketBase HTTP client
from app.shared.utils import audit        # INSERT-only en colección auditoria
from app.shared.deps import get_current_user, require_user, require_permission, render
```

---

## Principios de la constitución aplicados

| Principio | Aplicación en este módulo |
|---|---|
| III (RBAC) | `require_permission("seguridad", "ver")` + `require_permission("seguridad", "configurar")` en permisos.py |
| IV (sin secretos hardcodeados) | `SECRET_KEY` tiene default "changeme" — deuda técnica conocida |
| V (auditoría inmutable) | `audit.registrar()` en login, logout, editar perfil, configurar permisos |
| VII (caché TTL) | `_perm_cache` TTL 300s en `deps.py` |
| IX (sin timeouts definidos) | No aplica a este módulo (es web, no pipeline) |
