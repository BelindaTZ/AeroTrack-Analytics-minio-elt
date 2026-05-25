from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.autenticacion.router import router as autenticacion_router
from app.pipeline_elt.router import router as pipeline_elt_router
from app.modelo_dimensional.router import router as modelo_dimensional_router

app = FastAPI(title="AeroTrack Analytics", version="1.0.0")

app.include_router(autenticacion_router, prefix="/auth", tags=["autenticacion"])
app.include_router(pipeline_elt_router, prefix="/pipeline", tags=["pipeline_elt"])
app.include_router(modelo_dimensional_router, prefix="/modelo", tags=["modelo_dimensional"])


@app.get("/")
async def root():
    return {"message": "AeroTrack Analytics API", "version": "1.0.0"}
