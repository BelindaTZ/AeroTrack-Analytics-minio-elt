"""
Narrativa ejecutiva en español para módulos analíticos.
Patrón: Groq llama-3.1-8b-instant (primario) → Gemini 2.5 Flash (fallback en 429/402/503 o timeout >12s)
Caché en memoria TTL 300s, clave = MD5(prompt). Temperatura 0.4.
Contexto = solo KPIs agregados, nunca filas raw.
"""

import hashlib
import logging
import time

import requests

from app.shared.clients import pb_client

log = logging.getLogger(__name__)

_cache: dict[str, dict] = {}
_TTL = 300
_TIMEOUT = 12

_cfg_cache: dict = {"data": None, "expires": 0.0}
_CFG_TTL = 120


def _get_ia_config() -> dict:
    global _cfg_cache
    if _cfg_cache["data"] is not None and time.time() < _cfg_cache["expires"]:
        return _cfg_cache["data"]
    rows = pb_client.list_records("configuracion_sistema", filter='modulo="ia"')
    result = {r["clave"]: r["valor"] for r in rows}
    _cfg_cache = {"data": result, "expires": time.time() + _CFG_TTL}
    return result


def invalidar_cfg_cache() -> None:
    global _cfg_cache
    _cfg_cache = {"data": None, "expires": 0.0}


def _cache_key(prompt: str) -> str:
    return hashlib.md5(prompt.encode()).hexdigest()


def _get_cached(key: str) -> tuple[str, str] | None:
    e = _cache.get(key)
    if e and time.time() < e["expires"]:
        return e["text"], e["provider"]
    return None


def _store(key: str, text: str, provider: str) -> None:
    _cache[key] = {"text": text, "provider": provider, "expires": time.time() + _TTL}


def _call_groq(prompt: str, api_key: str) -> str:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.15,
        "max_tokens": 180,
    }
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=_TIMEOUT
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def _call_gemini(prompt: str, api_key: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.15, "maxOutputTokens": 180},
    }
    r = requests.post(url, json=payload, timeout=_TIMEOUT)
    r.raise_for_status()
    parts = r.json()["candidates"][0]["content"]["parts"]
    return "".join(p["text"] for p in parts).strip()


def generar_narrativa(contexto: dict, modulo: str, focus: str = "") -> dict:
    """
    Genera narrativa ejecutiva en español (2 oraciones).
    Returns {"texto": str, "proveedor": str, "desde_cache": bool}
    focus: describe qué debe protagonizar el análisis (ej. "el volumen de vuelos").
    """
    empty = {"texto": "", "proveedor": "", "desde_cache": False}

    try:
        cfg = _get_ia_config()
    except Exception:
        return empty

    api_key_groq = cfg.get("ia_api_key_groq", "")
    api_key_gemini = cfg.get("ia_api_key_gemini", "")

    if cfg.get("ia_activa", "false").lower() != "true":
        return empty

    if not api_key_groq and not api_key_gemini:
        return empty

    metricas_texto = "\n".join(f"- {k}: {v}" for k, v in contexto.items())
    tema = focus if focus else "el KPI más crítico según su Estado"
    prompt = (
        f"Eres un analista de aviación. Datos del módulo '{modulo}':\n{metricas_texto}\n\n"
        f"REGLAS ABSOLUTAS:\n"
        f"- SOLO puedes mencionar números que aparezcan LITERALMENTE en los datos anteriores.\n"
        f"- PROHIBIDO calcular, estimar, redondear o inferir cualquier cifra nueva.\n"
        f"- Los campos 'Estado *' ya indican CUMPLE/NO CUMPLE — úsalos tal cual, sin recomputar.\n\n"
        f"Escribe exactamente 2 oraciones en español centradas en {tema}: "
        f"la primera interpreta el dato principal citando su valor exacto; "
        f"la segunda da una recomendación operativa específica basada solo en los datos. "
        f"Sin introducción, sin markdown, texto plano."
    )

    key = _cache_key(prompt)
    cached = _get_cached(key)
    if cached:
        return {"texto": cached[0], "proveedor": cached[1], "desde_cache": True}

    if api_key_groq:
        try:
            texto = _call_groq(prompt, api_key_groq)
            _store(key, texto, "Groq llama-3.1")
            return {"texto": texto, "proveedor": "Groq llama-3.1", "desde_cache": False}
        except requests.HTTPError as exc:
            if exc.response is None or exc.response.status_code not in (429, 402, 503):
                log.warning("ia_narrativa groq error: %s", exc)
        except requests.Timeout:
            pass
        except Exception as exc:
            log.warning("ia_narrativa groq unexpected: %s", exc)

    if api_key_gemini:
        try:
            texto = _call_gemini(prompt, api_key_gemini)
            _store(key, texto, "Gemini 2.5 Flash")
            return {"texto": texto, "proveedor": "Gemini 2.5 Flash", "desde_cache": False}
        except Exception as exc:
            log.warning("ia_narrativa gemini error: %s", exc)

    return empty
