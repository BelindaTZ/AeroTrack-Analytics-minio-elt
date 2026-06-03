"""Panel de control del pipeline ELT (CU-10, CU-11, CU-12, CU-13)."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.pipeline_elt.clients import airflow_client as af
from app.shared.utils import audit
from app.shared.deps import render, require_permission

router = APIRouter()
_perm_ver = require_permission("pipeline_elt", "ver")
_perm_exec = require_permission("pipeline_elt", "ejecutar")


@router.get("", response_class=HTMLResponse)
async def panel(request: Request):
    user = _perm_ver(request)
    try:
        estado = await af.get_dag_status()
        historial = await af.get_dag_runs(limit=5)
    except Exception as exc:
        estado = {"state": "error", "error": str(exc)}
        historial = []
    return render(request, "pipeline/panel.html", {
        "estado": estado,
        "historial": historial,
        "dag_id": af.DAG_ID,
    })


@router.post("/trigger")
async def trigger(request: Request):
    user = _perm_exec(request)
    try:
        result = await af.trigger_dag()
        audit.registrar(user["sub"], user["email"], "ejecutar", "pipeline_elt",
                        recurso_tipo="dag", recurso_id=af.DAG_ID,
                        detalle=f"dag_run_id={result.get('dag_run_id', '')}")
    except Exception as exc:
        return RedirectResponse(f"/pipeline?error={exc}", status_code=303)
    return RedirectResponse("/pipeline?msg=Pipeline iniciado.", status_code=303)


@router.get("/estado")
async def estado_json(request: Request):
    """Endpoint AJAX para auto-refresh del estado (cada 10s desde el template)."""
    _perm_ver(request)
    try:
        estado = await af.get_dag_status()
        return JSONResponse(estado)
    except Exception as exc:
        return JSONResponse({"state": "error", "error": str(exc)})


@router.get("/estado-full")
async def estado_full(request: Request):
    """Endpoint AJAX para polling sin recarga de página (estado + historial)."""
    _perm_ver(request)
    try:
        estado = await af.get_dag_status()
        historial = await af.get_dag_runs(limit=5)
        return JSONResponse({"estado": estado, "historial": historial})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get("/historial", response_class=HTMLResponse)
async def historial(request: Request):
    _perm_ver(request)
    try:
        runs = await af.get_dag_runs(limit=50)
    except Exception:
        runs = []
    return render(request, "pipeline/historial.html", {"runs": runs, "dag_id": af.DAG_ID})


@router.get("/logs/{run_id}/{task_id}", response_class=HTMLResponse)
async def logs(request: Request, run_id: str, task_id: str, attempt: int = 1):
    _perm_ver(request)
    try:
        log_text = await af.get_task_log(run_id, task_id, attempt)
        tasks = await af.get_task_instances(run_id)
    except Exception as exc:
        log_text = str(exc)
        tasks = []
    return render(request, "pipeline/logs.html", {
        "run_id": run_id, "task_id": task_id,
        "log_text": log_text, "tasks": tasks,
    })
