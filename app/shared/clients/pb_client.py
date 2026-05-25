"""Cliente HTTP para la API REST de PocketBase.

Todas las operaciones usan requests síncronos (FastAPI los ejecuta en threads).
El token de administrador se cachea para evitar re-autenticar en cada request.
"""

import time
from typing import Any, Optional

import requests

from app.config import PB_URL, PB_EMAIL, PB_PASSWORD

_admin_cache: dict = {"token": "", "expires": 0.0}


def _get_admin_token() -> str:
    """Obtiene (o reutiliza) el token de administrador de PocketBase."""
    if time.time() < _admin_cache["expires"]:
        return _admin_cache["token"]
    for endpoint in ("/api/admins/auth-with-password", "/api/collections/_superusers/auth-with-password"):
        r = requests.post(f"{PB_URL}{endpoint}", json={"identity": PB_EMAIL, "password": PB_PASSWORD}, timeout=10)
        if r.status_code == 200:
            token = r.json()["token"]
            _admin_cache.update({"token": token, "expires": time.time() + 3600})
            return token
    raise RuntimeError("No se pudo autenticar como administrador en PocketBase")


def auth_user(email: str, password: str) -> tuple[str, dict]:
    """Autentica un usuario en la colección app_users.
    Retorna (pb_token, record_dict) o lanza ValueError si falla.
    """
    r = requests.post(
        f"{PB_URL}/api/collections/app_users/auth-with-password",
        json={"identity": email, "password": password},
        timeout=10,
    )
    if r.status_code != 200:
        raise ValueError("Credenciales inválidas")
    data = r.json()
    return data["token"], data["record"]


def list_records(collection: str, filter: str = "", expand: str = "",
                 page: int = 1, per_page: int = 200, sort: str = "") -> list[dict]:
    """Lista registros de una colección con paginación y filtro."""
    token = _get_admin_token()
    params: dict[str, Any] = {"page": page, "perPage": per_page}
    if filter:
        params["filter"] = filter
    if expand:
        params["expand"] = expand
    if sort:
        params["sort"] = sort
    r = requests.get(
        f"{PB_URL}/api/collections/{collection}/records",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=10,
    )
    if not r.ok:
        return []
    return r.json().get("items", [])


def list_records_all(collection: str, filter: str = "", expand: str = "", sort: str = "") -> list[dict]:
    """Descarga todos los registros paginando hasta 500/página."""
    token = _get_admin_token()
    result: list[dict] = []
    page = 1
    while True:
        params: dict[str, Any] = {"page": page, "perPage": 500}
        if filter:
            params["filter"] = filter
        if expand:
            params["expand"] = expand
        if sort:
            params["sort"] = sort
        r = requests.get(
            f"{PB_URL}/api/collections/{collection}/records",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=15,
        )
        if not r.ok:
            break
        data = r.json()
        items = data.get("items", [])
        result.extend(items)
        if len(result) >= data.get("totalItems", 0):
            break
        page += 1
    return result


def get_record(collection: str, record_id: str, expand: str = "") -> Optional[dict]:
    token = _get_admin_token()
    params = {"expand": expand} if expand else {}
    r = requests.get(
        f"{PB_URL}/api/collections/{collection}/records/{record_id}",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=10,
    )
    return r.json() if r.ok else None


def create_record(collection: str, data: dict) -> dict:
    token = _get_admin_token()
    r = requests.post(
        f"{PB_URL}/api/collections/{collection}/records",
        headers={"Authorization": f"Bearer {token}"},
        json=data,
        timeout=10,
    )
    if not r.ok:
        raise ValueError(r.json().get("message", f"Error creando en {collection}"))
    return r.json()


def update_record(collection: str, record_id: str, data: dict) -> dict:
    token = _get_admin_token()
    r = requests.patch(
        f"{PB_URL}/api/collections/{collection}/records/{record_id}",
        headers={"Authorization": f"Bearer {token}"},
        json=data,
        timeout=10,
    )
    if not r.ok:
        raise ValueError(r.json().get("message", f"Error actualizando {record_id} en {collection}"))
    return r.json()


def delete_record(collection: str, record_id: str) -> None:
    token = _get_admin_token()
    r = requests.delete(
        f"{PB_URL}/api/collections/{collection}/records/{record_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if not r.ok:
        raise ValueError(r.json().get("message", f"Error eliminando {record_id} en {collection}"))


def change_user_password(user_id: str, new_password: str) -> None:
    """Cambia la contraseña de un usuario en app_users."""
    update_record("app_users", user_id, {
        "password": new_password,
        "passwordConfirm": new_password,
    })


def get_permissions_for_role(rol_id: str) -> dict[str, list[str]]:
    """Retorna {modulo_clave: [accion, ...]} para el rol dado."""
    rows = list_records_all(
        "roles_permisos",
        filter=f'rol_id="{rol_id}"',
        expand="permiso_id,permiso_id.modulo_id",
    )
    perms: dict[str, list[str]] = {}
    for row in rows:
        expanded = row.get("expand", {})
        permiso = expanded.get("permiso_id", {})
        modulo_expanded = permiso.get("expand", {}).get("modulo_id", {})
        modulo_clave = modulo_expanded.get("clave", "")
        accion = permiso.get("accion", "")
        if modulo_clave and accion:
            perms.setdefault(modulo_clave, []).append(accion)
    return perms
