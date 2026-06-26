"""Panel de control del pipeline ELT (CU-10, CU-11, CU-12, CU-13, CU-T06, CU-O08)."""

from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.pipeline_elt.clients import airflow_client as af
from app.shared.clients import pb_client
from app.shared.deps import render, require_permission
from app.shared.utils import audit
from app.socios_api.webhook_dispatcher import dispatch_event

router = APIRouter()
_perm_ver = require_permission("pipeline_elt", "ver")
_perm_exec = require_permission("pipeline_elt", "ejecutar")

_SCHEDULE_LABELS = {
    "manual": "Manual",
    "@daily": "Cada dia",
    "@hourly": "Cada hora",
    "@weekly": "Semanal",
    "@monthly": "Mensual",
    "@yearly": "Anual",
}


def _get_schedule_label(valor: str) -> str:
    if not valor or valor == "manual":
        return "Manual"
    return _SCHEDULE_LABELS.get(valor, valor)


@router.get("", response_class=HTMLResponse)
async def panel(request: Request):
    user = _perm_ver(request)
    try:
        estado = await af.get_dag_status()
        historial = await af.get_dag_runs(limit=5)
    except Exception as exc:
        estado = {"state": "error", "error": str(exc)}
        historial = []
    schedule_val = "manual"
    try:
        rows = pb_client.list_records("configuracion_sistema", filter='clave="pipeline_schedule"')
        if rows:
            schedule_val = rows[0].get("valor", "manual")
    except Exception:
        pass
    return render(
        request,
        "pipeline/panel.html",
        {
            "estado": estado,
            "historial": historial,
            "dag_id": af.DAG_ID,
            "schedule_val": schedule_val,
            "schedule_label": _get_schedule_label(schedule_val),
        },
    )


@router.post("/trigger")
async def trigger(request: Request):
    user = _perm_exec(request)
    try:
        result = await af.trigger_dag()
        audit.registrar(
            user["sub"],
            user["email"],
            "ejecutar",
            "pipeline_elt",
            recurso_tipo="dag",
            recurso_id=af.DAG_ID,
            detalle=f"dag_run_id={result.get('dag_run_id', '')}",
        )
        dispatch_event(
            "pipeline_completado",
            {
                "dag_id": af.DAG_ID,
                "dag_run_id": result.get("dag_run_id", ""),
                "estado": "iniciado",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
    except Exception as exc:
        return RedirectResponse(f"/pipeline?error={exc}", status_code=303)
    return RedirectResponse("/pipeline?msg=Pipeline iniciado.", status_code=303)


@router.get("/estado")
async def estado_json(request: Request):
    _perm_ver(request)
    try:
        estado = await af.get_dag_status()
        return JSONResponse(estado)
    except Exception as exc:
        return JSONResponse({"state": "error", "error": str(exc)})


@router.get("/estado-full")
async def estado_full(request: Request):
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
    return render(
        request,
        "pipeline/logs.html",
        {
            "run_id": run_id,
            "task_id": task_id,
            "log_text": log_text,
            "tasks": tasks,
        },
    )


@router.post("/logs/{run_id}/{task_id}/reintentar")
async def reintentar_tarea(request: Request, run_id: str, task_id: str):
    user = _perm_exec(request)
    try:
        await af.clear_task_instance(af.DAG_ID, run_id, task_id)
        audit.registrar(
            user["sub"],
            user["email"],
            "reintentar",
            "pipeline_elt",
            recurso_tipo="task_instance",
            recurso_id=f"{run_id}/{task_id}",
        )
    except Exception as exc:
        return RedirectResponse(f"/pipeline/logs/{run_id}/{task_id}?error={exc}", status_code=303)
    return RedirectResponse(f"/pipeline/logs/{run_id}/{task_id}?msg=Tarea+reintentada.", status_code=303)
