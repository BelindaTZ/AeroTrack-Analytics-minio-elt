"""Dispatcher de webhooks — firma HMAC-SHA256, retry con backoff, asíncrono."""

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.shared.clients import pb_client as pb

log = logging.getLogger(__name__)

_TIMEOUT = 15
_MAX_RETRIES = 3
_BACKOFF = [2, 4, 8]


def _firmar(payload: dict, clave_hmac: str) -> str:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    return hmac.new(clave_hmac.encode(), body, hashlib.sha256).hexdigest()


async def _enviar_webhook(webhook: dict, payload: dict) -> None:
    url = webhook.get("url", "")
    clave_hmac = webhook.get("clave_hmac", "")
    webhook_id = webhook.get("id", "")
    firma = _firmar(payload, clave_hmac)

    for attempt in range(_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-AeroTrack-Signature": firma,
                        "User-Agent": "AeroTrack-Webhook/1.0",
                    },
                )
            if resp.is_success:
                ahora = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                try:
                    pb.update_record(
                        "pb_api_webhooks",
                        webhook_id,
                        {
                            "ultimo_envio": ahora,
                            "ultimo_estado": "exitoso",
                        },
                    )
                except Exception:
                    pass
                log.info(f"Webhook {webhook_id} -> {url} OK (intento {attempt + 1})")
                return

            log.warning(f"Webhook {webhook_id} -> {url} HTTP {resp.status_code} (intento {attempt + 1}/{_MAX_RETRIES})")

        except Exception as exc:
            log.warning(f"Webhook {webhook_id} -> {url} error: {exc} (intento {attempt + 1}/{_MAX_RETRIES})")

        if attempt < _MAX_RETRIES - 1:
            await asyncio.sleep(_BACKOFF[attempt])

    ahora = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    try:
        pb.update_record(
            "pb_api_webhooks",
            webhook_id,
            {
                "ultimo_envio": ahora,
                "ultimo_estado": "fallido",
            },
        )
    except Exception:
        pass
    log.error(f"Webhook {webhook_id} -> {url} FALLIDO tras {_MAX_RETRIES} intentos")


def dispatch_event(evento: str, payload: dict[str, Any]) -> None:
    if evento not in ("pipeline_completado", "alerta_otp", "reporte_generado"):
        log.warning(f"Evento desconocido: {evento}")
        return

    try:
        webhooks = pb.list_records_all("pb_api_webhooks", filter="activo=True")
    except Exception as exc:
        log.error(f"Error cargando webhooks: {exc}")
        return

    suscritos = [w for w in webhooks if evento in (w.get("eventos") or [])]
    if not suscritos:
        log.debug(f"No hay webhooks suscritos a {evento}")
        return

    for wh in suscritos:
        asyncio.create_task(_enviar_webhook(wh, payload))

    log.info(f"Disparados {len(suscritos)} webhook(s) para evento '{evento}'")
