"""Envío de emails usando la configuración SMTP de configuracion_sistema."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.shared.clients import pb_client


def _get_smtp_config() -> dict:
    rows = pb_client.list_records("configuracion_sistema", filter='modulo="email"')
    cfg = {r["clave"]: r["valor"] for r in rows}
    return cfg


def send_welcome_email(destinatario: str, nombre: str, password_temporal: str, login_url: str) -> Optional[str]:
    """Envía email de bienvenida con credenciales. Retorna None si ok, o mensaje de error."""
    try:
        cfg = _get_smtp_config()
        host = cfg.get("email_smtp_host", "")
        port = int(cfg.get("email_smtp_port", "587"))
        remitente = cfg.get("email_remitente", "")
        password = cfg.get("email_password", "")
        usar_tls = cfg.get("email_usar_tls", "true").lower() == "true"

        if not host or not remitente:
            return "Configuración SMTP incompleta"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Bienvenido a AeroTrack Analytics"
        msg["From"] = remitente
        msg["To"] = destinatario

        body_html = f"""
        <html><body style="font-family:sans-serif;color:#1e293b">
          <h2 style="color:#1B3A6B">Bienvenido a AeroTrack Analytics</h2>
          <p>Hola <strong>{nombre}</strong>,</p>
          <p>Tu cuenta ha sido creada exitosamente. Aquí están tus credenciales:</p>
          <table style="border-collapse:collapse;margin:16px 0">
            <tr><td style="padding:6px 12px;font-weight:600">Email:</td><td style="padding:6px 12px">{destinatario}</td></tr>
            <tr><td style="padding:6px 12px;font-weight:600">Contraseña temporal:</td><td style="padding:6px 12px;font-family:monospace">{password_temporal}</td></tr>
          </table>
          <p>Ingresa al sistema en: <a href="{login_url}">{login_url}</a></p>
          <p style="color:#64748b;font-size:13px">Por seguridad, cambia tu contraseña después del primer inicio de sesión.</p>
        </body></html>
        """
        msg.attach(MIMEText(body_html, "html"))

        smtp = smtplib.SMTP(host, port, timeout=10)
        if usar_tls:
            smtp.starttls()
        if password:
            smtp.login(remitente, password)
        smtp.sendmail(remitente, destinatario, msg.as_string())
        smtp.quit()
        return None
    except Exception as exc:
        return str(exc)
