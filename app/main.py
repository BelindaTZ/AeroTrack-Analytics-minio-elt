from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.seguridad.router import router as auth_router
from app.seguridad.usuarios.usuarios import router as usuarios_router
from app.seguridad.rbac.roles_admin import router as roles_router
from app.seguridad.rbac.permisos import router as permisos_router
from app.pipeline_elt.router import router as pipeline_router
from app.modelo_dimensional.router import router as modelo_router
from app.shared.deps import _redirect_to_login, get_current_user, render

app = FastAPI(title="AeroTrack Analytics", version="1.0.0")

_STATIC = Path(__file__).parent.parent / "static"
_STATIC.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router,     prefix="/auth",          tags=["auth"])
app.include_router(usuarios_router, prefix="/auth/usuarios", tags=["usuarios"])
app.include_router(permisos_router, prefix="/auth/roles",    tags=["permisos"])
app.include_router(roles_router,    prefix="/auth/roles",    tags=["roles"])
app.include_router(pipeline_router, prefix="/pipeline",      tags=["pipeline"])
app.include_router(modelo_router,   prefix="/modelo",        tags=["modelo"])


# ── Root redirect ─────────────────────────────────────────────────────────────
@app.get("/", response_class=RedirectResponse)
async def root(request: Request):
    user = get_current_user(request)
    return RedirectResponse("/pipeline" if user else "/auth/login", status_code=302)


# ── Exception handlers ────────────────────────────────────────────────────────
@app.exception_handler(_redirect_to_login)
async def handle_auth_required(request: Request, exc: _redirect_to_login):
    return RedirectResponse(f"/auth/login", status_code=302)


@app.exception_handler(PermissionError)
async def handle_permission_error(request: Request, exc: PermissionError):
    return render(request, "error.html",
                  {"mensaje": f"Sin permiso para realizar esta acción. {exc}", "codigo": 403},
                  status=403)


@app.exception_handler(404)
async def handle_404(request: Request, exc):
    return render(request, "error.html",
                  {"mensaje": "La página solicitada no existe.", "codigo": 404}, status=404)


@app.exception_handler(500)
async def handle_500(request: Request, exc):
    return render(request, "error.html",
                  {"mensaje": "Error interno del servidor.", "codigo": 500}, status=500)
