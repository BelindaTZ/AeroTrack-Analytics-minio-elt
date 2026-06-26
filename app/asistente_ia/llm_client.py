"""Cliente LLM genérico para el asistente analítico IA (CU-42).
Soporta OpenAI, Anthropic, Gemini y endpoint custom compatible con OpenAI.
Configuración dinámica desde PocketBase (grupo 'ia').
"""

import logging
import time

import requests

from app.shared.clients import pb_client

log = logging.getLogger(__name__)

_cfg_cache: dict = {"data": None, "expires": 0.0}
_CFG_TTL = 60  # segundos — config cambia poco


def get_ia_config() -> dict:
    """Lee configuración IA de PocketBase (cacheada 60 s)."""
    global _cfg_cache
    if _cfg_cache["data"] is not None and time.time() < _cfg_cache["expires"]:
        return _cfg_cache["data"]
    rows = pb_client.list_records("configuracion_sistema", filter='modulo="ia"')
    cfg = {r["clave"]: r["valor"] for r in rows}
    _cfg_cache = {"data": cfg, "expires": time.time() + _CFG_TTL}
    return cfg


def invalidar_config() -> None:
    global _cfg_cache
    _cfg_cache = {"data": None, "expires": 0.0}


def modulo_activo() -> bool:
    """Retorna True si el módulo asistente_ia está habilitado."""
    cfg = get_ia_config()
    return cfg.get("modulo_activo", "true").lower() == "true"


def resolver_api_key(cfg: dict, proveedor: str) -> str:
    """Resuelve la API key correcta según el proveedor.
    Groq y Gemini pueden usar sus claves específicas (ia_api_key_groq / ia_api_key_gemini)
    cuando ia_api_key genérica está vacía, reutilizando las claves de narrativa IA.
    """
    generic = cfg.get("ia_api_key", "")
    if proveedor == "groq":
        return generic or cfg.get("ia_api_key_groq", "")
    if proveedor == "gemini":
        return generic or cfg.get("ia_api_key_gemini", "")
    return generic


def call_llm(messages: list[dict], extra_timeout: int | None = None) -> str:
    """
    Llama al LLM configurado.
    messages: lista de {"role": "system"|"user"|"assistant", "content": str}
    Retorna el texto de respuesta.
    Lanza ValueError si falta API key, RuntimeError en error de red.
    """
    cfg = get_ia_config()
    proveedor = cfg.get("ia_proveedor", "groq").lower()
    api_key = resolver_api_key(cfg, proveedor)
    modelo = cfg.get("ia_modelo", "llama-3.1-8b-instant")
    endpoint_cus = cfg.get("ia_endpoint_custom", "").rstrip("/")
    max_tokens = int(cfg.get("ia_max_tokens", "2048"))
    temperatura = float(cfg.get("ia_temperatura", "0.3"))
    timeout = extra_timeout or int(cfg.get("ia_timeout_segundos", cfg.get("ia_timeout", "30")))

    if not api_key:
        raise ValueError("API key no configurada. Vaya a Configuración → IA para ingresar las credenciales.")

    if proveedor == "groq":
        base = endpoint_cus or "https://api.groq.com/openai"
        return _call_openai_compat(base, api_key, modelo, messages, max_tokens, temperatura, timeout)
    elif proveedor == "anthropic":
        return _call_anthropic(api_key, modelo, messages, max_tokens, temperatura, timeout)
    elif proveedor == "gemini":
        return _call_gemini(api_key, modelo, messages, max_tokens, temperatura, timeout)
    elif proveedor == "custom" and endpoint_cus:
        return _call_openai_compat(endpoint_cus, api_key, modelo, messages, max_tokens, temperatura, timeout)
    else:
        base = endpoint_cus or "https://api.openai.com"
        return _call_openai_compat(base, api_key, modelo, messages, max_tokens, temperatura, timeout)


# ── Manejo de errores amigables ───────────────────────────────────────────────


def _friendly_error(exc: requests.RequestException, proveedor: str) -> RuntimeError:
    """Convierte excepciones de requests en mensajes comprensibles para el usuario."""
    if isinstance(exc, requests.exceptions.Timeout):
        return RuntimeError(
            f"La consulta al asistente tardó demasiado ({proveedor}). "
            "Intenta de nuevo o formula una pregunta más corta."
        )
    if isinstance(exc, requests.exceptions.ConnectionError):
        return RuntimeError(
            f"No se pudo conectar con el servicio de IA ({proveedor}). "
            "Verifica la conexión a internet o inténtalo más tarde."
        )
    if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None:
        status = exc.response.status_code
        if status == 429:
            return RuntimeError(
                f"El servicio {proveedor} superó el límite de solicitudes por minuto. "
                "Espera unos segundos e intenta de nuevo."
            )
        if status in (401, 403):
            return RuntimeError(
                f"La API key de {proveedor} es inválida o no tiene permisos. "
                "Verifica la configuración en Configuración → IA."
            )
        if status == 404:
            return RuntimeError(
                f"El modelo configurado no existe en {proveedor}. Verifica el nombre del modelo en Configuración → IA."
            )
        if status == 400:
            return RuntimeError(
                f"La solicitud fue rechazada por {proveedor} (parámetros inválidos). "
                "Revisa la configuración de temperatura o tokens máximos."
            )
        if status >= 500:
            return RuntimeError(
                f"El servicio {proveedor} está experimentando problemas internos (código {status}). "
                "Intenta de nuevo en unos minutos."
            )
        return RuntimeError(f"Error al contactar {proveedor} (código HTTP {status}). Intenta de nuevo.")
    return RuntimeError(
        f"Error inesperado al contactar el servicio de IA ({proveedor}). Intenta de nuevo o revisa la configuración."
    )


# ── Implementaciones por proveedor ────────────────────────────────────────────


def _call_openai_compat(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    max_tokens: int,
    temp: float,
    timeout: int,
) -> str:
    proveedor = "Groq" if "groq.com" in base_url else "OpenAI/custom"
    url = f"{base_url}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temp}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except requests.RequestException as exc:
        raise _friendly_error(exc, proveedor) from exc


def _call_anthropic(
    api_key: str,
    model: str,
    messages: list[dict],
    max_tokens: int,
    temp: float,
    timeout: int,
) -> str:
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    chat_msgs = [m for m in messages if m["role"] != "system"]
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    payload: dict = {
        "model": model or "claude-haiku-4-5-20251001",
        "messages": chat_msgs,
        "max_tokens": max_tokens,
        "temperature": temp,
    }
    if system:
        payload["system"] = system
    try:
        r = requests.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()["content"][0]["text"].strip()
    except requests.RequestException as exc:
        raise _friendly_error(exc, "Anthropic") from exc


def _call_gemini(
    api_key: str,
    model: str,
    messages: list[dict],
    max_tokens: int,
    temp: float,
    timeout: int,
) -> str:
    mdl_name = model or "gemini-2.0-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{mdl_name}:generateContent?key={api_key}"
    contents = []
    for m in messages:
        if m["role"] == "system":
            continue
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    payload = {
        "contents": contents,
        "generationConfig": {"temperature": temp, "maxOutputTokens": max_tokens},
    }
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        parts = r.json()["candidates"][0]["content"]["parts"]
        return "".join(p["text"] for p in parts).strip()
    except requests.RequestException as exc:
        raise _friendly_error(exc, "Gemini") from exc
