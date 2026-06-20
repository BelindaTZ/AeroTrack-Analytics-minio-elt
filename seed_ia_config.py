"""
Inserta (o actualiza) los 3 registros de configuración IA en PocketBase.
Uso: python seed_ia_config.py
"""
import os
import sys

# Necesita variables del .env cargadas antes de importar los clientes
from dotenv import load_dotenv
load_dotenv()

from app.shared.clients import pb_client

REGISTROS_IA = [
    {
        "modulo": "ia",
        "clave": "ia_activa",
        "valor": "true",
        "tipo": "bool",
        "editable": True,
        "sensible": False,
        "descripcion": "Activar narrativa ejecutiva con IA",
    },
    {
        "modulo": "ia",
        "clave": "ia_api_key_groq",
        "valor": os.getenv("GROQ_API_KEY", ""),
        "tipo": "password",
        "editable": True,
        "sensible": True,
        "descripcion": "API Key de Groq (llama-3.1-8b-instant) — proveedor primario",
    },
    {
        "modulo": "ia",
        "clave": "ia_api_key_gemini",
        "valor": os.getenv("GEMINI_API_KEY", ""),
        "tipo": "password",
        "editable": True,
        "sensible": True,
        "descripcion": "API Key de Gemini 2.0 Flash (Google) — fallback",
    },
]


def main() -> None:
    existentes = pb_client.list_records("configuracion_sistema", filter='modulo="ia"')
    existentes_map = {r["clave"]: r for r in existentes}

    for reg in REGISTROS_IA:
        clave = reg["clave"]
        if clave in existentes_map:
            rid = existentes_map[clave]["id"]
            pb_client.update_record("configuracion_sistema", rid, reg)
            print(f"  actualizado: {clave}")
        else:
            pb_client.create_record("configuracion_sistema", reg)
            print(f"  creado:      {clave}")

    print("\nListo. Recarga el dashboard para ver la narrativa IA.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
