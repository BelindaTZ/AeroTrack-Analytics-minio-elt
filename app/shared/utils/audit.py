"""Registro de auditoría en la colección `auditoria` de PocketBase (INSERT-only)."""

from app.shared.clients import pb_client


def registrar(
    usuario_id: str,
    usuario_email: str,
    accion: str,
    modulo: str,
    recurso_tipo: str = "",
    recurso_id: str = "",
    detalle: str = "",
    ip_address: str = "",
    resultado: str = "exitoso",
) -> None:
    """Inserta un registro de auditoría. Nunca lanza excepción al llamador."""
    try:
        pb_client.create_record("auditoria", {
            "usuario_id": usuario_id,
            "usuario_email": usuario_email,
            "accion": accion,
            "modulo": modulo,
            "recurso_tipo": recurso_tipo,
            "recurso_id": recurso_id,
            "detalle": detalle,
            "ip_address": ip_address,
            "resultado": resultado,
        })
    except Exception:
        pass  # El fallo de auditoría no debe interrumpir la operación principal
