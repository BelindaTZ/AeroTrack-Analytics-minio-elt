"""Monitoreo de servicios — MinIO, PocketBase, Airflow (CU-33, CU-34)."""

import time

import requests as req_lib
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.config import (
    AIRFLOW_PASSWORD,
    AIRFLOW_URL,
    AIRFLOW_USER,
    MINIO_ACCESS_KEY,
    MINIO_ENDPOINT,
    MINIO_SECRET_KEY,
    PB_URL,
)
from app.shared.deps import render, require_permission

router = APIRouter()
_perm_ver = require_permission("configuracion", "ver")


def _check_pocketbase() -> dict:
    t0 = time.perf_counter()
    try:
        r = req_lib.get(f"{PB_URL}/api/health", timeout=5)
        latencia = round((time.perf_counter() - t0) * 1000, 1)
        ok = r.status_code == 200
        return {
            "nombre": "PocketBase",
            "ok": ok,
            "latencia_ms": latencia,
            "estado": "online" if ok else "degradado",
            "url": f"{PB_URL}/_/",
            "icono": "bi-database-fill",
        }
    except Exception as exc:
        return {
            "nombre": "PocketBase",
            "ok": False,
            "latencia_ms": -1,
            "estado": "offline",
            "error": str(exc),
            "url": f"{PB_URL}/_/",
            "icono": "bi-database-fill",
        }


def _check_minio() -> dict:
    t0 = time.perf_counter()
    try:
        from minio import Minio

        client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)
        buckets = client.list_buckets()
        latencia = round((time.perf_counter() - t0) * 1000, 1)
        bucket_list = [b.name for b in buckets]

        # Métricas por bucket
        metricas = []
        for b in buckets:
            try:
                objetos = list(client.list_objects(b.name))
                size_total = sum(o.size for o in objetos)
                metricas.append(
                    {
                        "bucket": b.name,
                        "objetos": len(objetos),
                        "size_mb": round(size_total / 1_048_576, 2),
                    }
                )
            except Exception:
                metricas.append({"bucket": b.name, "objetos": "?", "size_mb": "?"})

        host, _ = MINIO_ENDPOINT.split(":") if ":" in MINIO_ENDPOINT else (MINIO_ENDPOINT, "9001")
        return {
            "nombre": "MinIO",
            "ok": True,
            "latencia_ms": latencia,
            "estado": "online",
            "buckets": bucket_list,
            "metricas": metricas,
            "url": f"http://{host}:9001",
            "icono": "bi-server",
        }
    except Exception as exc:
        return {
            "nombre": "MinIO",
            "ok": False,
            "latencia_ms": -1,
            "estado": "offline",
            "error": str(exc),
            "url": "#",
            "icono": "bi-server",
        }


def _check_airflow() -> dict:
    t0 = time.perf_counter()
    try:
        r = req_lib.get(
            f"{AIRFLOW_URL}/api/v1/health",
            auth=(AIRFLOW_USER, AIRFLOW_PASSWORD),
            timeout=8,
        )
        latencia = round((time.perf_counter() - t0) * 1000, 1)
        ok = r.status_code == 200
        scheduler_ok = False
        if ok:
            health = r.json()
            scheduler_ok = health.get("scheduler", {}).get("status") == "healthy"
        return {
            "nombre": "Airflow",
            "ok": ok,
            "latencia_ms": latencia,
            "estado": "online" if ok else "degradado",
            "scheduler": "healthy" if scheduler_ok else "unknown",
            "url": f"{AIRFLOW_URL}",
            "icono": "bi-gear-wide-connected",
        }
    except Exception as exc:
        return {
            "nombre": "Airflow",
            "ok": False,
            "latencia_ms": -1,
            "estado": "offline",
            "error": str(exc),
            "url": f"{AIRFLOW_URL}",
            "icono": "bi-gear-wide-connected",
        }


def _get_status() -> dict:
    pb = _check_pocketbase()
    minio = _check_minio()
    af = _check_airflow()
    servicios = [pb, minio, af]
    todos_ok = all(s["ok"] for s in servicios)
    return {"servicios": servicios, "todos_ok": todos_ok}


@router.get("", response_class=HTMLResponse)
def monitoreo(request: Request):
    user = _perm_ver(request)
    status = _get_status()
    return render(request, "configuracion/monitoreo.html", {"status": status})


@router.get("/json")
def estado_json(request: Request):
    """Endpoint AJAX para auto-refresh cada 30s."""
    _perm_ver(request)
    return JSONResponse(_get_status())
