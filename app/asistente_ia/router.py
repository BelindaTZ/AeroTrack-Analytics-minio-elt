"""Asistente analítico IA — endpoints (CU-41).
Flujo RAG: pregunta → parse intent → query Parquet → build context → LLM → respuesta.
Historial de conversación por sesión (en memoria, cookie session_id).
"""

import logging
import secrets
import time
import uuid
from typing import Optional

log = logging.getLogger(__name__)

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.asistente_ia.llm_client import call_llm, get_ia_config, modulo_activo, resolver_api_key
from app.asistente_ia.rag import parse_intent, build_context, build_messages
from app.shared.deps import render, require_permission
from app.shared.utils import audit

router = APIRouter()
_perm_ver  = require_permission("asistente_ia", "ver")
_perm_exec = require_permission("asistente_ia", "ejecutar")

# Historial en memoria: {session_id: {"history": [...], "expires": float}}
_sessions: dict[str, dict] = {}
_SESSION_TTL = 1800  # 30 minutos


def _get_session(session_id: str) -> list[dict]:
    entry = _sessions.get(session_id)
    if entry and time.time() < entry["expires"]:
        return entry["history"]
    return []


def _save_session(session_id: str, history: list[dict]) -> None:
    _sessions[session_id] = {"history": history, "expires": time.time() + _SESSION_TTL}
    # Limpiar sesiones expiradas (cada 100 requests)
    if len(_sessions) > 500:
        now = time.time()
        expired = [k for k, v in _sessions.items() if v["expires"] < now]
        for k in expired:
            _sessions.pop(k, None)


def _ensure_session(request: Request) -> str:
    return request.cookies.get("chat_session") or secrets.token_hex(16)


@router.get("", response_class=HTMLResponse)
def chat_page(request: Request):
    _perm_ver(request)
    activo    = modulo_activo()
    cfg       = get_ia_config()
    proveedor = cfg.get("ia_proveedor", "groq")
    modelo    = cfg.get("ia_modelo", "")
    tiene_key = bool(resolver_api_key(cfg, proveedor.lower()))

    session_id = _ensure_session(request)
    history    = _get_session(session_id)

    response = render(request, "asistente_ia/chat.html", {
        "activo":     activo,
        "proveedor":  proveedor,
        "modelo":     modelo,
        "tiene_key":  tiene_key,
        "session_id": session_id,
        "history":    history,
    })
    response.set_cookie("chat_session", session_id, httponly=True, max_age=_SESSION_TTL)
    return response


@router.post("/chat")
async def chat_message(request: Request):
    user = _perm_exec(request)

    if not modulo_activo():
        return JSONResponse(
            {"error": "El módulo Asistente IA está deshabilitado. Actívelo en Configuración → IA."},
            status_code=503,
        )

    body = await request.json()
    question   = str(body.get("mensaje", "")).strip()
    session_id = str(body.get("session_id", _ensure_session(request)))

    if not question:
        return JSONResponse({"error": "La pregunta no puede estar vacía."}, status_code=400)

    if len(question) > 800:
        return JSONResponse({"error": "La pregunta es demasiado larga (máx. 800 caracteres)."}, status_code=400)

    history = _get_session(session_id)

    # RAG
    filtros = parse_intent(question)
    context = build_context(filtros, question)
    messages = build_messages(history, context, question)

    try:
        respuesta = call_llm(messages)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=503)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=503)
    except Exception as exc:
        log.exception("Error inesperado en call_llm")
        return JSONResponse(
            {"error": "Ocurrió un error inesperado al procesar tu consulta. Intenta de nuevo."},
            status_code=500,
        )

    # Actualizar historial (sin el mensaje con contexto expandido)
    new_history = history + [
        {"role": "user",      "content": question},
        {"role": "assistant", "content": respuesta},
    ]
    # Mantener solo las últimas 20 interacciones (10 pares)
    _save_session(session_id, new_history[-20:])

    audit.registrar(
        user["sub"], user["email"], "consultar_ia", "asistente_ia",
        recurso_tipo="chat", recurso_id=session_id[:8],
    )

    return JSONResponse({
        "respuesta":  respuesta,
        "filtros":    filtros,
        "session_id": session_id,
    })


@router.post("/reset")
async def reset_session(request: Request):
    _perm_ver(request)
    session_id = _ensure_session(request)
    _sessions.pop(session_id, None)
    new_id = secrets.token_hex(16)
    response = JSONResponse({"session_id": new_id})
    response.set_cookie("chat_session", new_id, httponly=True, max_age=_SESSION_TTL)
    return response
