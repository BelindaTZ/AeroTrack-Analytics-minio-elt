# -*- coding: utf-8 -*-
"""
AeroTrack Analytics — Configura SMTP de Gmail en PocketBase
Actualiza:
  1. Ajustes SMTP nativos de PocketBase (/api/settings) — necesario para envío real
  2. Registros de configuracion_sistema con los datos del remitente
"""
import sys, os, requests

sys.stdout.reconfigure(encoding="utf-8")

try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from scripts.config import PB_BASE_URL, PB_EMAIL, PB_PASSWORD
except ImportError:
    try:
        from config import PB_BASE_URL, PB_EMAIL, PB_PASSWORD
    except ImportError:
        from dotenv import load_dotenv; load_dotenv()
        PB_BASE_URL = os.getenv("PB_URL", "http://localhost:8090")
        PB_EMAIL    = os.getenv("PB_EMAIL")
        PB_PASSWORD = os.getenv("PB_PASSWORD")

# ── Credenciales Gmail a configurar (desde .env) ──────────────
GMAIL_ADDRESS  = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")
SMTP_HOST      = "smtp.gmail.com"
SMTP_PORT      = 587

BASE = PB_BASE_URL.rstrip("/")
S = requests.Session()
S.headers.update({"Content-Type": "application/json"})


def log(msg, ok=True):
    print(f"  {'OK' if ok else 'ERR'} {msg}")


def auth():
    r = S.post(f"{BASE}/api/admins/auth-with-password",
               json={"identity": PB_EMAIL, "password": PB_PASSWORD})
    if r.status_code != 200:
        r = S.post(f"{BASE}/api/collections/_superusers/auth-with-password",
                   json={"identity": PB_EMAIL, "password": PB_PASSWORD})
    if r.status_code != 200:
        print(f"✗ Auth falló: {r.text}"); sys.exit(1)
    S.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    log(f"Autenticado como: {PB_EMAIL}")


def configure_pb_smtp():
    """Configura SMTP nativo de PocketBase vía /api/settings."""
    payload = {
        "smtp": {
            "enabled": True,
            "host": SMTP_HOST,
            "port": SMTP_PORT,
            "username": GMAIL_ADDRESS,
            "password": GMAIL_APP_PASS,
            "tls": False,        # False = STARTTLS en puerto 587; True = SSL en 465
            "authMethod": "PLAIN",
            "localName": "",
        },
        "meta": {
            "senderName": "AeroTrack Analytics",
            "senderAddress": GMAIL_ADDRESS,
        },
    }
    r = S.patch(f"{BASE}/api/settings", json=payload)
    if r.ok:
        log("SMTP nativo de PocketBase configurado (smtp.gmail.com:587 STARTTLS)")
    else:
        log(f"Error configurando SMTP nativo: {r.status_code} — {r.text[:200]}", ok=False)
    return r.ok


def update_config_record(clave, valor):
    """Actualiza el campo 'valor' de un registro en configuracion_sistema."""
    r = S.get(f"{BASE}/api/collections/configuracion_sistema/records",
              params={"filter": f'clave="{clave}"', "perPage": 1})
    if not r.ok:
        log(f"No se pudo buscar '{clave}': {r.text[:80]}", ok=False)
        return
    items = r.json().get("items", [])
    if not items:
        log(f"Registro '{clave}' no encontrado en configuracion_sistema", ok=False)
        return
    record_id = items[0]["id"]
    rp = S.patch(f"{BASE}/api/collections/configuracion_sistema/records/{record_id}",
                 json={"valor": valor})
    if rp.ok:
        log(f"'{clave}' → '{valor}'")
    else:
        log(f"Error actualizando '{clave}': {rp.text[:80]}", ok=False)


def configure_system_table():
    """Actualiza los registros de email en configuracion_sistema."""
    updates = {
        "email_smtp_host":       SMTP_HOST,
        "email_smtp_port":       str(SMTP_PORT),
        "email_remitente":       GMAIL_ADDRESS,
        "email_password":        GMAIL_APP_PASS,
        "email_usar_tls":        "true",
        "email_alertas_activas": "true",
        "email_destinatario":    GMAIL_ADDRESS,
    }
    for clave, valor in updates.items():
        update_config_record(clave, valor)


def test_smtp():
    """Envía un email de prueba vía la API de PocketBase."""
    r = S.post(f"{BASE}/api/settings/test/email",
               json={"template": "verification", "email": GMAIL_ADDRESS})
    if r.ok:
        log(f"Email de prueba enviado a {GMAIL_ADDRESS} — revisa la bandeja")
    else:
        log(f"Error en email de prueba: {r.status_code} — {r.text[:200]}", ok=False)


def main():
    print("\n" + "="*60)
    print("  AeroTrack — Configurar Gmail SMTP en PocketBase")
    print("="*60)

    print("\n[1/3] Autenticando...")
    auth()

    print("\n[2/3] Configurando SMTP nativo de PocketBase...")
    configure_pb_smtp()

    print("\n[3/3] Actualizando tabla configuracion_sistema...")
    configure_system_table()

    print("\n[Extra] Enviando email de prueba...")
    test_smtp()

    print("\n" + "="*60)
    print("  Configuración completada.")
    print(f"  Gmail:  {GMAIL_ADDRESS}")
    print(f"  SMTP:   {SMTP_HOST}:{SMTP_PORT} (STARTTLS)")
    print(f"  Verifica en: {BASE}/_/ > Settings > Mail settings")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
