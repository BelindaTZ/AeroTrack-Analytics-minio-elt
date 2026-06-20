"""
Registra los módulos de Entrega 3 (predictivo, asistente_ia) en el RBAC
de PocketBase con los campos correctos, crea sus permisos y los asigna
al rol Administrador.

Uso: python seed_rbac_e3.py
"""
import sys

from dotenv import load_dotenv
load_dotenv()

from app.shared.clients import pb_client

# ── Definición de módulos E3 ─────────────────────────────────────────────────
MODULOS_E3 = [
    {
        "clave":         "predictivo",
        "nombre_display": "Predictivo",
        "descripcion":   "Proyecciones OTP, estacionalidad y recomendaciones (CU-35, CU-36, CU-37, CU-38)",
        "orden":         80,
        "acciones":      ["ver", "exportar"],
    },
    {
        "clave":         "asistente_ia",
        "nombre_display": "Asistente IA",
        "descripcion":   "Asistente analítico IA con arquitectura RAG (CU-41, CU-42)",
        "orden":         90,
        "acciones":      ["ver", "ejecutar"],
    },
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _upsert_modulo(modulo_def: dict) -> str:
    """Crea o actualiza el módulo en la colección 'modulos'. Retorna su ID."""
    clave = modulo_def["clave"]
    payload = {
        "clave":         modulo_def["clave"],
        "nombre_display": modulo_def["nombre_display"],
        "descripcion":   modulo_def["descripcion"],
        "orden":         modulo_def["orden"],
    }

    existentes = pb_client.list_records_all("modulos")
    for m in existentes:
        # Buscar por clave (correcto) o por nombre heredado del seed anterior
        if m.get("clave") == clave or m.get("nombre") == clave:
            pb_client.update_record("modulos", m["id"], payload)
            print(f"  actualizado: módulo '{clave}' (id={m['id']})")
            return m["id"]

    rec = pb_client.create_record("modulos", payload)
    print(f"  creado:      módulo '{clave}' (id={rec['id']})")
    return rec["id"]


def _upsert_permisos(modulo_id: str, acciones: list[str]) -> list[str]:
    """Crea los permisos faltantes para el módulo. Retorna lista de IDs."""
    existentes = pb_client.list_records_all("permisos", filter=f'modulo_id="{modulo_id}"')
    existentes_map = {p["accion"]: p["id"] for p in existentes}

    ids: list[str] = []
    for accion in acciones:
        if accion in existentes_map:
            print(f"  ya existe:   permiso '{accion}'")
            ids.append(existentes_map[accion])
        else:
            rec = pb_client.create_record("permisos", {"modulo_id": modulo_id, "accion": accion})
            print(f"  creado:      permiso '{accion}' (id={rec['id']})")
            ids.append(rec["id"])
    return ids


def _get_admin_role_id() -> str:
    """Retorna el ID del rol Administrador (es_sistema=true)."""
    roles = pb_client.list_records_all("roles")
    # Preferir el marcado como sistema con nombre que contenga 'admin'
    for r in roles:
        if r.get("es_sistema") and "admin" in r.get("nombre", "").lower():
            return r["id"]
    # Fallback: cualquiera con es_sistema
    for r in roles:
        if r.get("es_sistema"):
            return r["id"]
    raise RuntimeError("No se encontró el rol Administrador en PocketBase.")


def _assign_permisos_to_role(rol_id: str, permiso_ids: list[str]) -> None:
    """Asigna los permisos al rol si aún no están asignados."""
    existentes = pb_client.list_records_all("roles_permisos", filter=f'rol_id="{rol_id}"')
    ya_asignados = {rp["permiso_id"] for rp in existentes}

    for pid in permiso_ids:
        if pid in ya_asignados:
            print(f"  ya asignado: permiso {pid}")
        else:
            pb_client.create_record("roles_permisos", {"rol_id": rol_id, "permiso_id": pid})
            print(f"  asignado:    permiso {pid}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("── Rol Administrador ──────────────────────────────────────────")
    rol_id = _get_admin_role_id()
    print(f"  encontrado: rol admin (id={rol_id})")

    for mod_def in MODULOS_E3:
        clave = mod_def["clave"]
        print(f"\n── Módulo: {clave} ─────────────────────────────────────────────")
        modulo_id = _upsert_modulo(mod_def)

        print(f"   Permisos:")
        permiso_ids = _upsert_permisos(modulo_id, mod_def["acciones"])

        print(f"   Asignación al Administrador:")
        _assign_permisos_to_role(rol_id, permiso_ids)

    print("\nListo.")
    print("  → El módulo 'asistente_ia' aparece ahora en Roles → Permisos.")
    print("  → Admin tiene: ver + ejecutar en asistente_ia, ver + exportar en predictivo.")
    print("  → Si el servidor está corriendo, reinícialo para limpiar el caché de permisos.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
