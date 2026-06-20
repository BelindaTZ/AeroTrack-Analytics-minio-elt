"""
Inserta (o actualiza) los registros de configuración del Asistente IA y
registra los módulos predictivo + asistente_ia en PocketBase para el RBAC.

Uso: python seed_asistente_config.py
"""
import os
import sys

from dotenv import load_dotenv
load_dotenv()

from app.shared.clients import pb_client

# Configuración del asistente IA (grupo "ia")
IA_CONFIG = [
    {
        "modulo": "ia",
        "clave": "modulo_activo",
        "valor": "true",
        "tipo": "bool",
        "editable": True,
        "sensible": False,
        "descripcion": "Activar módulo Asistente IA (chat RAG)",
    },
    {
        "modulo": "ia",
        "clave": "ia_proveedor",
        "valor": "openai",
        "tipo": "string",
        "editable": True,
        "sensible": False,
        "descripcion": "Proveedor LLM: openai | anthropic | gemini | custom",
    },
    {
        "modulo": "ia",
        "clave": "ia_api_key",
        "valor": "",
        "tipo": "password",
        "editable": True,
        "sensible": True,
        "descripcion": "API key del proveedor LLM (asistente chat)",
    },
    {
        "modulo": "ia",
        "clave": "ia_modelo",
        "valor": "gpt-4o-mini",
        "tipo": "string",
        "editable": True,
        "sensible": False,
        "descripcion": "Modelo específico (ej: gpt-4o-mini, claude-haiku-4-5-20251001, gemini-2.0-flash)",
    },
    {
        "modulo": "ia",
        "clave": "ia_endpoint_custom",
        "valor": "",
        "tipo": "string",
        "editable": True,
        "sensible": False,
        "descripcion": "Endpoint custom compatible con OpenAI (dejar vacío para usar el proveedor estándar)",
    },
    {
        "modulo": "ia",
        "clave": "ia_max_tokens",
        "valor": "2048",
        "tipo": "number",
        "editable": True,
        "sensible": False,
        "descripcion": "Máximo de tokens en la respuesta del asistente",
    },
    {
        "modulo": "ia",
        "clave": "ia_temperatura",
        "valor": "0.3",
        "tipo": "number",
        "editable": True,
        "sensible": False,
        "descripcion": "Temperatura del LLM (0.0 = determinista, 1.0 = creativo)",
    },
    {
        "modulo": "ia",
        "clave": "ia_timeout",
        "valor": "30",
        "tipo": "number",
        "editable": True,
        "sensible": False,
        "descripcion": "Timeout en segundos para la llamada al LLM",
    },
    # Horizonte máximo de predicción (grupo sistema)
    {
        "modulo": "sistema",
        "clave": "horizonte_prediccion_max",
        "valor": "6",
        "tipo": "number",
        "editable": True,
        "sensible": False,
        "descripcion": "Horizonte máximo de proyección predictiva (meses)",
    },
]

# Módulos E3 para RBAC
MODULOS_E3 = [
    {"nombre": "predictivo",   "descripcion": "Módulo predictivo: proyecciones OTP, estacionalidad y recomendaciones"},
    {"nombre": "asistente_ia", "descripcion": "Asistente analítico IA con arquitectura RAG"},
]


def seed_config() -> None:
    existentes = pb_client.list_records_all("configuracion_sistema")
    existentes_map = {r["clave"]: r for r in existentes}

    for reg in IA_CONFIG:
        clave = reg["clave"]
        if clave in existentes_map:
            rid = existentes_map[clave]["id"]
            pb_client.update_record("configuracion_sistema", rid, reg)
            print(f"  actualizado: {clave}")
        else:
            pb_client.create_record("configuracion_sistema", reg)
            print(f"  creado:      {clave}")


def seed_modulos() -> None:
    existentes = pb_client.list_records_all("modulos")
    existentes_nombres = {r["nombre"] for r in existentes}

    for mod in MODULOS_E3:
        if mod["nombre"] in existentes_nombres:
            print(f"  ya existe:   módulo '{mod['nombre']}'")
        else:
            pb_client.create_record("modulos", mod)
            print(f"  creado:      módulo '{mod['nombre']}'")


def main() -> None:
    print("── Configuración IA Asistente ─────────────────────────────────")
    seed_config()

    print("\n── Módulos E3 para RBAC ───────────────────────────────────────")
    seed_modulos()

    print(
        "\nListo. Asigna permisos a los roles desde Administración → Roles → Gestionar permisos."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
