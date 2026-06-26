from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.asistente_ia.router import router as ia_router
from app.auditoria.log import router as auditoria_router
from app.cancelaciones.clasificar_faa import router as cancelaciones_router

# Lote 5
from app.clientes.router import router as clientes_router
from app.configuracion.monitoreo import router as monitoreo_router
from app.configuracion.panel import router as configuracion_router

# Entrega 2
from app.dashboard.kpis import router as dashboard_router
from app.modelo_dimensional.router import router as modelo_router
from app.pipeline_elt.router import router as pipeline_router
from app.predictivo.informe_ejecutivo import router as informe_router

# Entrega 3
from app.predictivo.proyeccion_riesgo import router as predictivo_router
from app.puntualidad.analizar_otp import router as puntualidad_router
from app.reportes.router import router as reportes_router
from app.rutas.ranking_eficiencia import router as rutas_router
from app.seguridad.rbac.permisos import router as permisos_router
from app.seguridad.rbac.roles_admin import router as roles_router
from app.seguridad.router import router as auth_router
from app.seguridad.usuarios.usuarios import router as usuarios_router
from app.shared.deps import _redirect_to_login, get_current_user, render
from app.socios_api.api import router as api_router
from app.socios_api.router import router as socios_router

app = FastAPI(title="AeroTrack Analytics", version="1.0.0")

_STATIC = Path(__file__).parent.parent / "static"
_STATIC.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(usuarios_router, prefix="/auth/usuarios", tags=["usuarios"])
app.include_router(permisos_router, prefix="/auth/roles", tags=["permisos"])
app.include_router(roles_router, prefix="/auth/roles", tags=["roles"])
app.include_router(pipeline_router, prefix="/pipeline", tags=["pipeline"])
app.include_router(modelo_router, prefix="/modelo", tags=["modelo"])

# Entrega 2
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
app.include_router(puntualidad_router, prefix="/puntualidad", tags=["puntualidad"])
app.include_router(rutas_router, prefix="/rutas", tags=["rutas"])
app.include_router(cancelaciones_router, prefix="/cancelaciones", tags=["cancelaciones"])
app.include_router(configuracion_router, prefix="/configuracion", tags=["configuracion"])
app.include_router(monitoreo_router, prefix="/configuracion/estado", tags=["monitoreo"])
app.include_router(auditoria_router, prefix="/auditoria", tags=["auditoria"])
app.include_router(reportes_router, prefix="/reportes", tags=["reportes"])

# Entrega 3
app.include_router(predictivo_router, prefix="/predictivo", tags=["predictivo"])
app.include_router(informe_router, prefix="/predictivo", tags=["predictivo"])
app.include_router(ia_router, prefix="/ia", tags=["asistente_ia"])

# Lote 5
app.include_router(clientes_router, prefix="/clientes", tags=["clientes"])
app.include_router(socios_router, prefix="/socios", tags=["socios_api"])
app.include_router(api_router, prefix="", tags=["api_publica"])


# ── Health check (para docker-compose healthcheck) ─────────────────────────────
@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}


# ── Root redirect ─────────────────────────────────────────────────────────────
@app.get("/", response_class=RedirectResponse)
async def root(request: Request):
    user = get_current_user(request)
    return RedirectResponse("/dashboard" if user else "/auth/login", status_code=302)


# ── Exception handlers ────────────────────────────────────────────────────────
@app.exception_handler(_redirect_to_login)
async def handle_auth_required(request: Request, exc: _redirect_to_login):
    return RedirectResponse("/auth/login", status_code=302)


@app.exception_handler(PermissionError)
async def handle_permission_error(request: Request, exc: PermissionError):
    return render(
        request, "error.html", {"mensaje": f"Sin permiso para realizar esta acción. {exc}", "codigo": 403}, status=403
    )


@app.exception_handler(404)
async def handle_404(request: Request, exc):
    return render(request, "error.html", {"mensaje": "La página solicitada no existe.", "codigo": 404}, status=404)


@app.exception_handler(500)
async def handle_500(request: Request, exc):
    return render(request, "error.html", {"mensaje": "Error interno del servidor.", "codigo": 500}, status=500)
