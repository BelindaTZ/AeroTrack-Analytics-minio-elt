"""
Narrativa ejecutiva en español para módulos analíticos.
Patrón: Grok 3 mini (primario) → Gemini 2.0 Flash (fallback en 429/402/503 o timeout >12s)
Caché en memoria TTL 300s, clave = MD5(prompt). Temperatura 0.4.
Contexto = solo KPIs agregados, nunca filas raw.
"""
import hashlib
import logging
import time
from typing import Optional

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


def _cache_key(prompt: str) -> str:
    return hashlib.md5(prompt.encode()).hexdigest()


def _get_cached(key: str) -> Optional[tuple[str, str]]:
    e = _cache.get(key)
    if e and time.time() < e["expires"]:
        return e["text"], e["provider"]
    return None


def _store(key: str, text: str, provider: str) -> None:
    _cache[key] = {"text": text, "provider": provider, "expires": time.time() + _TTL}


def _call_grok(prompt: str, api_key: str) -> str:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "grok-3-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 400,
    }
    r = requests.post(
        "https://api.x.ai/v1/chat/completions",
        json=payload, headers=headers, timeout=_TIMEOUT
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def _call_gemini(prompt: str, api_key: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 400},
    }
    r = requests.post(url, json=payload, timeout=_TIMEOUT)
    r.raise_for_status()
    parts = r.json()["candidates"][0]["content"]["parts"]
    return "".join(p["text"] for p in parts).strip()


def generar_narrativa(contexto: dict, modulo: str) -> dict:
    """
    Genera narrativa ejecutiva en español (≤3 párrafos).
    Returns {"texto": str, "proveedor": str, "desde_cache": bool}
    """
    empty = {"texto": "", "proveedor": "", "desde_cache": False}

    try:
        cfg = _get_ia_config()
    except Exception:
        return empty

    api_key_grok = cfg.get("ia_api_key_grok", "")
    api_key_gemini = cfg.get("ia_api_key_gemini", "")

    if not api_key_grok and not api_key_gemini:
        return empty

    metricas_texto = "\n".join(f"- {k}: {v}" for k, v in contexto.items())
    prompt = (
        f"Eres un analista senior de aviación comercial. "
        f"Genera una narrativa ejecutiva en español (máximo 3 párrafos cortos) "
        f"sobre los siguientes KPIs del módulo {modulo}:\n\n"
        f"{metricas_texto}\n\n"
        f"Destaca tendencias relevantes, valores atípicos y recomendaciones clave. "
        f"Sé conciso y profesional."
    )

    key = _cache_key(prompt)
    cached = _get_cached(key)
    if cached:
        return {"texto": cached[0], "proveedor": cached[1], "desde_cache": True}

    if api_key_grok:
        try:
            texto = _call_grok(prompt, api_key_grok)
            _store(key, texto, "Grok 3 mini")
            return {"texto": texto, "proveedor": "Grok 3 mini", "desde_cache": False}
        except requests.HTTPError as exc:
            if exc.response is None or exc.response.status_code not in (429, 402, 503):
                log.warning("ia_narrativa grok error: %s", exc)
                # fallthrough to Gemini
        except requests.Timeout:
            pass  # fallthrough to Gemini
        except Exception as exc:
            log.warning("ia_narrativa grok unexpected: %s", exc)

    if api_key_gemini:
        try:
            texto = _call_gemini(prompt, api_key_gemini)
            _store(key, texto, "Gemini 2.0 Flash")
            return {"texto": texto, "proveedor": "Gemini 2.0 Flash", "desde_cache": False}
        except Exception as exc:
            log.warning("ia_narrativa gemini error: %s", exc)

    return empty
