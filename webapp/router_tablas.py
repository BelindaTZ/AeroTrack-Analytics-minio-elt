# router_tablas.py — Rutas CRUD genéricas para todas las tablas

import math
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from config import TABLAS, PAGE_SIZE
from minio_client import read_parquet, write_parquet

router = APIRouter()
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ── Helpers ────────────────────────────────────────────────────────────────

def _tmpl(request: Request, name: str, ctx: dict, status: int = 200) -> HTMLResponse:
    """Wrapper para TemplateResponse compatible con Starlette >= 1.0."""
    return templates.TemplateResponse(
        request=request,
        name=name,
        context=ctx,
        status_code=status,
    )


def _error(request: Request, mensaje: str, codigo: int = 404) -> HTMLResponse:
    return _tmpl(request, "error.html",
                 {"tablas": TABLAS, "mensaje": mensaje, "codigo": codigo},
                 status=codigo)


def _tabla_valida(tabla: str, request: Request) -> Optional[HTMLResponse]:
    """Retorna una respuesta de error si la tabla no existe."""
    if tabla not in TABLAS:
        return _error(request, f"La tabla '{tabla}' no existe en el sistema.", 404)
    return None


def _df_to_rows(df: pd.DataFrame) -> list[dict]:
    """Convierte el DataFrame a lista de dicts JSON-serializable."""
    return df.where(pd.notna(df), other=None).to_dict(orient="records")


def _desnormalizar(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte columnas category a object para permitir asignación libre."""
    for col in df.columns:
        if pd.api.types.is_categorical_dtype(df[col]):
            df[col] = df[col].astype(object)
    return df


def _safe_read(tabla: str, request: Request):
    """Lee el Parquet; si falla retorna (None, HTMLResponse de error)."""
    try:
        df = read_parquet(tabla)
        return df, None
    except FileNotFoundError as exc:
        return None, _error(request, str(exc), 404)
    except Exception as exc:
        return None, _error(request, f"Error inesperado: {exc}", 500)


# ── LIST ───────────────────────────────────────────────────────────────────

@router.get("/{tabla}", response_class=HTMLResponse)
async def listar(
    request: Request,
    tabla: str,
    page: int = 1,
    q: str = "",
):
    err = _tabla_valida(tabla, request)
    if err:
        return err

    df, err = _safe_read(tabla, request)
    if err:
        return err

    pk = TABLAS[tabla]["pk"]

    # Búsqueda
    if q:
        mask = df.apply(
            lambda col: col.astype(str).str.contains(q, case=False, na=False)
        ).any(axis=1)
        df = df[mask]

    total = len(df)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    start = (page - 1) * PAGE_SIZE
    df_page = df.iloc[start: start + PAGE_SIZE]

    return _tmpl(request, "tabla_lista.html", {
        "tablas": TABLAS,
        "tabla": tabla,
        "tabla_info": TABLAS[tabla],
        "columnas": list(df_page.columns),
        "rows": _df_to_rows(df_page),
        "pk": pk,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "q": q,
        "page_size": PAGE_SIZE,
    })


# ── DETAIL ─────────────────────────────────────────────────────────────────

@router.get("/{tabla}/{id_val}/ver", response_class=HTMLResponse)
async def ver(request: Request, tabla: str, id_val: str):
    err = _tabla_valida(tabla, request)
    if err:
        return err

    df, err = _safe_read(tabla, request)
    if err:
        return err

    pk = TABLAS[tabla]["pk"]
    df[pk] = df[pk].astype(str)
    row = df[df[pk] == id_val]

    if row.empty:
        return _error(request,
                      f"Registro con {pk}='{id_val}' no encontrado en '{tabla}'.", 404)

    registro = row.where(pd.notna(row), other=None).iloc[0].to_dict()
    return _tmpl(request, "tabla_detalle.html", {
        "tablas": TABLAS,
        "tabla": tabla,
        "tabla_info": TABLAS[tabla],
        "pk": pk,
        "id_val": id_val,
        "registro": registro,
    })


# ── CREATE ─────────────────────────────────────────────────────────────────

@router.get("/{tabla}/nuevo", response_class=HTMLResponse)
async def nuevo_form(request: Request, tabla: str):
    err = _tabla_valida(tabla, request)
    if err:
        return err

    df, err = _safe_read(tabla, request)
    if err:
        return err

    columnas = list(df.columns)
    dtypes = {col: str(df[col].dtype) for col in columnas}
    pk = TABLAS[tabla]["pk"]

    return _tmpl(request, "tabla_form.html", {
        "tablas": TABLAS,
        "tabla": tabla,
        "tabla_info": TABLAS[tabla],
        "modo": "crear",
        "columnas": columnas,
        "dtypes": dtypes,
        "pk": pk,
        "registro": {},
        "error": None,
    })


@router.post("/{tabla}/nuevo", response_class=HTMLResponse)
async def nuevo_guardar(request: Request, tabla: str):
    err = _tabla_valida(tabla, request)
    if err:
        return err

    df, err = _safe_read(tabla, request)
    if err:
        return err

    df = _desnormalizar(df)
    form = await request.form()
    nuevo: dict = {}
    for col in df.columns:
        val = form.get(col, "")
        try:
            dtype = df[col].dtype
            if pd.api.types.is_integer_dtype(dtype):
                nuevo[col] = int(val) if val not in ("", None) else None
            elif pd.api.types.is_float_dtype(dtype):
                nuevo[col] = float(val) if val not in ("", None) else None
            else:
                nuevo[col] = val
        except (ValueError, TypeError):
            nuevo[col] = val

    df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)

    try:
        write_parquet(tabla, df)
    except Exception as exc:
        return _error(request, str(exc), 500)

    return RedirectResponse(f"/{tabla}?msg=created", status_code=303)


# ── EDIT ───────────────────────────────────────────────────────────────────

@router.get("/{tabla}/{id_val}/editar", response_class=HTMLResponse)
async def editar_form(request: Request, tabla: str, id_val: str):
    err = _tabla_valida(tabla, request)
    if err:
        return err

    df, err = _safe_read(tabla, request)
    if err:
        return err

    pk = TABLAS[tabla]["pk"]
    df[pk] = df[pk].astype(str)
    row = df[df[pk] == id_val]

    if row.empty:
        return _error(request, f"Registro con {pk}='{id_val}' no encontrado.", 404)

    registro = row.where(pd.notna(row), other=None).iloc[0].to_dict()
    columnas = list(df.columns)
    dtypes = {col: str(df[col].dtype) for col in columnas}

    return _tmpl(request, "tabla_form.html", {
        "tablas": TABLAS,
        "tabla": tabla,
        "tabla_info": TABLAS[tabla],
        "modo": "editar",
        "columnas": columnas,
        "dtypes": dtypes,
        "pk": pk,
        "id_val": id_val,
        "registro": registro,
        "error": None,
    })


@router.post("/{tabla}/{id_val}/editar", response_class=HTMLResponse)
async def editar_guardar(request: Request, tabla: str, id_val: str):
    err = _tabla_valida(tabla, request)
    if err:
        return err

    df, err = _safe_read(tabla, request)
    if err:
        return err

    df = _desnormalizar(df)
    pk = TABLAS[tabla]["pk"]
    df[pk] = df[pk].astype(str)
    idx = df.index[df[pk] == id_val].tolist()

    if not idx:
        return _error(request, f"Registro con {pk}='{id_val}' no encontrado.", 404)

    form = await request.form()
    for col in df.columns:
        val = form.get(col, "")
        try:
            dtype = df[col].dtype
            if pd.api.types.is_integer_dtype(dtype):
                df.at[idx[0], col] = int(val) if val not in ("", None) else None
            elif pd.api.types.is_float_dtype(dtype):
                df.at[idx[0], col] = float(val) if val not in ("", None) else None
            else:
                df.at[idx[0], col] = val
        except (ValueError, TypeError):
            df.at[idx[0], col] = val

    try:
        write_parquet(tabla, df)
    except Exception as exc:
        return _error(request, str(exc), 500)

    return RedirectResponse(f"/{tabla}?msg=updated", status_code=303)


# ── DELETE ─────────────────────────────────────────────────────────────────

@router.post("/{tabla}/{id_val}/eliminar")
async def eliminar(request: Request, tabla: str, id_val: str):
    err = _tabla_valida(tabla, request)
    if err:
        return err

    df, err = _safe_read(tabla, request)
    if err:
        return err

    df = _desnormalizar(df)
    pk = TABLAS[tabla]["pk"]
    df[pk] = df[pk].astype(str)
    df = df[df[pk] != id_val].reset_index(drop=True)

    try:
        write_parquet(tabla, df)
    except Exception as exc:
        return _error(request, str(exc), 500)

    return RedirectResponse(f"/{tabla}?msg=deleted", status_code=303)
