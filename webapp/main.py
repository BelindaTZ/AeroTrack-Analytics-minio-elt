# main.py — Punto de entrada de AeroTrack Analytics

from pathlib import Path

import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config import TABLAS
from minio_client import read_parquet
from router_tablas import router

BASE_DIR = Path(__file__).parent

app = FastAPI(title="AeroTrack Analytics", version="1.0.0")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Registrar el router de tablas
app.include_router(router)


# ── Dashboard ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    metricas = {
        "total_vuelos": None,
        "promedio_retraso": None,
        "total_aerolineas": None,
        "total_rutas": None,
    }
    vuelos_recientes = []
    cols_vuelos = []

    try:
        df_vuelos = read_parquet("fact_vuelo")
        metricas["total_vuelos"] = len(df_vuelos)
        for col in ("arr_delay", "dep_delay", "retraso_total", "retraso", "delay"):
            if col in df_vuelos.columns:
                val = df_vuelos[col].dropna()
                if len(val):
                    metricas["promedio_retraso"] = round(float(val.mean()), 1)
                break
        vuelos_recientes = (
            df_vuelos.where(pd.notna(df_vuelos), other=None)
            .head(10)
            .to_dict(orient="records")
        )
        cols_vuelos = list(df_vuelos.columns)
    except Exception:
        pass

    try:
        df_aerolineas = read_parquet("dim_aerolinea")
        metricas["total_aerolineas"] = len(df_aerolineas)
    except Exception:
        pass

    try:
        df_rutas = read_parquet("dim_ruta")
        metricas["total_rutas"] = len(df_rutas)
    except Exception:
        pass

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "tablas": TABLAS,
            "metricas": metricas,
            "vuelos_recientes": vuelos_recientes,
            "cols_vuelos": cols_vuelos,
        },
    )


# ── Manejadores de error globales ──────────────────────────────────────────

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "tablas": TABLAS,
            "mensaje": "La página solicitada no existe.",
            "codigo": 404,
        },
        status_code=404,
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "tablas": TABLAS,
            "mensaje": "Error interno del servidor.",
            "codigo": 500,
        },
        status_code=500,
    )
