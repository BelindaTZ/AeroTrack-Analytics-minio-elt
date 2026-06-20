"""Panel de configuración dinámica del sistema (CU-29, CU-30, CU-31, CU-32)."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.dashboard.kpis import invalidar_cache_alertas
from app.utils.ia_narrativa import invalidar_cfg_cache as _invalidar_ia_narrativa
from app.rutas.ranking_eficiencia import invalidar_cache_umbral_ruta
from app.shared.clients import pb_client
from app.shared.deps import render, require_permission
from app.shared.utils import audit

router = APIRouter()
_perm_ver = require_permission("configuracion", "ver")
_perm_edit = require_permission("configuracion", "configurar")

_GRUPOS = ["email", "alertas", "pipeline", "ia", "sistema"]

_GRUPO_META = {
    "email":    {"label": "Email / SMTP",           "icon": "bi-envelope-fill",   "color": "#3b82f6"},
    "alertas":  {"label": "Alertas y Umbrales",     "icon": "bi-bell-fill",       "color": "#f59e0b"},
    "pipeline": {"label": "Pipeline ELT",           "icon": "bi-gear-fill",       "color": "#6366f1"},
    "ia":       {"label": "Inteligencia Artificial","icon": "bi-cpu-fill",        "color": "#10b981"},
    "sistema":  {"label": "Sistema General",        "icon": "bi-sliders",         "color": "#94a3b8"},
}


def _get_all_config() -> dict[str, list[dict]]:
    rows = pb_client.list_records_all("configuracion_sistema", sort="clave")
    grupos: dict[str, list[dict]] = {g: [] for g in _GRUPOS}
    for r in rows:
        grupo = r.get("modulo", "sistema")
        if grupo not in grupos:
            grupos[grupo] = []
        entry = {
            "id": r["id"],
            "clave": r["clave"],
            "valor": "••••••••" if r.get("sensible") else r.get("valor", ""),
            "valor_real": r.get("valor", ""),
            "tipo": r.get("tipo", "string"),
            "descripcion": r.get("descripcion", ""),
            "editable": r.get("editable", True),
            "sensible": r.get("sensible", False),
        }
        grupos[grupo].append(entry)
    return grupos


def _save_group(grupo: str, form_data: dict) -> None:
    rows = pb_client.list_records_all("configuracion_sistema", filter=f'modulo="{grupo}"')
    for r in rows:
        clave = r["clave"]
        if clave in form_data and r.get("editable", True):
            nuevo_valor = form_data[clave]
            if nuevo_valor != "••••••••":
                pb_client.update_record("configuracion_sistema", r["id"], {"valor": nuevo_valor})


@router.get("", response_class=HTMLResponse)
def panel(request: Request):
    user = _perm_ver(request)
    config = _get_all_config()
    return render(request, "configuracion/index.html", {
        "grupos": config,
        "grupo_meta": _GRUPO_META,
        "grupos_orden": _GRUPOS,
        "active_grupo": "email",
    })


@router.post("/{grupo}")
async def guardar_grupo(request: Request, grupo: str):
    user = _perm_edit(request)
    if grupo not in _GRUPOS:
        return RedirectResponse("/configuracion?error=Grupo inválido", status_code=303)

    form = await request.form()
    form_data = dict(form)

    try:
        _save_group(grupo, form_data)
        if grupo == "alertas":
            invalidar_cache_alertas()
            invalidar_cache_umbral_ruta()
        elif grupo == "ia":
            _invalidar_ia_narrativa()
            try:
                from app.asistente_ia.llm_client import invalidar_config as _invalidar_llm
                _invalidar_llm()
            except ImportError:
                pass
        audit.registrar(
            user["sub"], user["email"], "editar", "configuracion",
            recurso_tipo="grupo", recurso_id=grupo,
        )
    except Exception as exc:
        return RedirectResponse(f"/configuracion?error={exc}", status_code=303)

    # Auto-test SMTP al guardar grupo email
    if grupo == "email":
        return RedirectResponse(
            f"/configuracion?msg=Configuración de {grupo} guardada.&active={grupo}&test_smtp=1",
            status_code=303
        )
    return RedirectResponse(
        f"/configuracion?msg=Configuración de {grupo} guardada.&active={grupo}",
        status_code=303
    )


@router.post("/email/test")
async def test_smtp(request: Request):
    """Prueba la conexión SMTP (CU-30). Responde JSON para respuesta inline."""
    _perm_ver(request)
    try:
        rows = pb_client.list_records("configuracion_sistema", filter='modulo="email"')
        cfg = {r["clave"]: r["valor"] for r in rows}

        host = cfg.get("email_smtp_host", "")
        port = int(cfg.get("email_smtp_port", "587"))
        remitente = cfg.get("email_remitente", "")
        password = cfg.get("email_password", "")
        destinatario = cfg.get("email_destinatario", remitente)
        usar_tls = cfg.get("email_usar_tls", "true").lower() == "true"

        if not host or not remitente:
            return JSONResponse({"ok": False, "mensaje": "Configuración SMTP incompleta."})

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "AeroTrack Analytics — Prueba SMTP"
        msg["From"] = remitente
        msg["To"] = destinatario or remitente
        msg.attach(MIMEText("<p>Prueba de conexión SMTP exitosa desde AeroTrack Analytics.</p>", "html"))

        smtp = smtplib.SMTP(host, port, timeout=10)
        if usar_tls:
            smtp.starttls()
        if password:
            smtp.login(remitente, password)
        smtp.sendmail(remitente, destinatario or remitente, msg.as_string())
        smtp.quit()

        return JSONResponse({"ok": True, "mensaje": f"Email de prueba enviado a {destinatario or remitente}."})

    except Exception as exc:
        return JSONResponse({"ok": False, "mensaje": f"Error SMTP: {exc}"})
