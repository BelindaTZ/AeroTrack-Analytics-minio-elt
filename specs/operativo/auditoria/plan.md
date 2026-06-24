# Plan de Implementación — Auditoría Operativa

**Módulo:** Auditoría  
**Paquete:** `app/auditoria/`  
**Prefix:** `/auditoria`  
**CUs cubiertos:** CU-O12, CU-O13  
**Fuente:** código leído el 2026-06-22

---

## Archivos del módulo

| Archivo | Propósito |
|---|---|
| `app/auditoria/log.py` | Router con endpoints de consulta y exportación CSV |
| `app/shared/utils/audit.py` | Función `registrar()` INSERT-only (usada por todos los módulos) |

---

## Endpoints implementados (prefix `/auditoria`)

| Método | Path | Permiso | Descripción |
|---|---|---|---|
| GET | `/auditoria` | `seguridad:ver` | Lista paginada de registros con 6 filtros combinables. Retorna HTML. |
| GET | `/auditoria/export` | `seguridad:ver` | Exporta CSV sin paginación con los mismos filtros. Retorna StreamingResponse. |

**Nota:** No existen endpoints PUT, PATCH ni DELETE para `/auditoria`. La colección es de solo lectura desde la API FastAPI (Principio V).

---

## Función audit.registrar()

**Archivo:** `app/shared/utils/audit.py:6`

```python
def registrar(
    usuario_id: str,
    usuario_email: str,
    accion: str,
    modulo: str,
    recurso_tipo: str = "",
    recurso_id: str = "",
    detalle: str = "",
    ip_address: str = "",
    resultado: str = "exitoso",
) -> None:
    """Inserta un registro de auditoría. Nunca lanza excepción al llamador."""
    try:
        pb_client.create_record("auditoria", {...})
    except Exception:
        pass  # El fallo de auditoría no debe interrumpir la operación principal
```

**Mecanismo de inmutabilidad:** `registrar()` solo llama `pb_client.create_record()`. No existe `update_record()` ni `delete_record()` para la colección `auditoria` en ningún archivo del codebase.

**Valores controlados:**
- `accion`: `login`, `logout`, `login_fallido`, `crear`, `editar`, `eliminar`, `ejecutar`, `exportar`, `configurar`, `validar`, `ver_reporte`
- `modulo`: `seguridad`, `pipeline_elt`, `modelo_dimensional`, `dashboard`, `puntualidad`, `rutas`, `cancelaciones`, `reportes`, `predictivo`, `configuracion`, `monitoreo`
- `resultado`: `exitoso` (default), `fallido`, `parcial`

---

## Implementación del router (app/auditoria/log.py)

### GET /auditoria — Consulta paginada

```python
@router.get("", response_class=HTMLResponse)
def log_auditoria(request, page=1, modulo="", accion="", usuario="",
                  resultado="", desde="", hasta=""):
    user = _perm_ver(request)  # require_permission("seguridad", "ver")
    
    # Construcción de filtro PocketBase
    filtros_pb = []
    if modulo:    filtros_pb.append(f'modulo="{modulo}"')
    if accion:    filtros_pb.append(f'accion="{accion}"')
    if usuario:   filtros_pb.append(f'(usuario_email~"{usuario}"||usuario_id="{usuario}")')
    if resultado: filtros_pb.append(f'resultado="{resultado}"')
    if desde:     filtros_pb.append(f'created>="{desde} 00:00:00"')
    if hasta:     filtros_pb.append(f'created<="{hasta} 23:59:59"')
    filter_str = "&&".join(filtros_pb)
    
    # Consulta paginada
    registros = pb_client.list_records("auditoria",
        filter=filter_str, sort="-created", page=page, per_page=_PAGE_SIZE)
    # _PAGE_SIZE = 50 (log.py:36)
    
    # Convertir timestamps a America/Guayaquil
    _localizar_registros(registros)
    
    # Selects dinámicos de módulo y acción
    modulos_disponibles = _get_distinct("modulo")
    acciones_disponibles = _get_distinct("accion")
```

**Filtros implementados (6):**

| Filtro | Parámetro | Tipo PocketBase | Condición |
|---|---|---|---|
| `modulo` | select dinámico | exact match | `modulo="{modulo}"` |
| `accion` | select dinámico | exact match | `accion="{accion}"` |
| `usuario` | texto libre | búsqueda en email o id | `(usuario_email~"{v}"||usuario_id="{v}")` |
| `resultado` | select (exitoso/fallido) | exact match | `resultado="{resultado}"` |
| `desde` | date | >= date 00:00:00 | `created>="{desde} 00:00:00"` |
| `hasta` | date | <= date 23:59:59 | `created<="{hasta} 23:59:59"` |

**Selects dinámicos:** `_get_distinct("modulo")` y `_get_distinct("accion")` leen todos los registros y devuelven los valores únicos ordenados. Sin hardcodeo de listas.

### GET /auditoria/export — Exportación CSV

```python
@router.get("/export")
def export_csv(request, modulo="", accion="", usuario="", resultado="", desde="", hasta=""):
    _perm_ver(request)
    # Misma lógica de filtros que GET /auditoria
    registros = pb_client.list_records_all("auditoria", filter=filter_str, sort="-created")
    # Sin paginación — retorna todos los registros coincidentes
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Fecha", "Usuario", "Email", "Módulo", "Acción", 
                     "Recurso tipo", "Recurso ID", "Resultado", "IP", "Detalle"])
    # 10 columnas
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=auditoria.csv"},
    )
```

**10 columnas en el CSV:**  
`Fecha`, `Usuario` (ID), `Email`, `Módulo`, `Acción`, `Recurso tipo`, `Recurso ID`, `Resultado`, `IP`, `Detalle`

---

## Conversión de zona horaria

**Implementación:** `app/auditoria/log.py:17-28`

```python
_TZ = timezone(timedelta(hours=-5))  # America/Guayaquil — sin DST

def _fmt_local(ts: str) -> str:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00").replace(" ", "T"))
    return dt.astimezone(_TZ).strftime("%Y-%m-%d %H:%M:%S")
```

**Biblioteca:** `datetime` de stdlib — sin pytz ni zoneinfo.  
**Offset:** UTC-5 hardcodeado como `timedelta(hours=-5)` (America/Guayaquil no tiene DST).  
**Formato de salida:** `YYYY-MM-DD HH:MM:SS`  
**Columna agregada:** `fecha_local` en cada registro (no modifica `created`).

---

## Tamaño de página

**`_PAGE_SIZE = 50`** definido en `log.py:36`  
No es configurable por el usuario. Aplicado en `list_records(..., per_page=_PAGE_SIZE)`.

---

## Colección PocketBase: auditoria

**Reglas implementadas a nivel de aplicación:**
- No existe endpoint DELETE ni PUT/PATCH en `app/auditoria/log.py`
- `audit.registrar()` solo llama `pb_client.create_record("auditoria", ...)`

**Reglas a nivel de PocketBase** (mencionadas en spec, verificadas por diseño):
- `deleteRule=null` — no permite borrar registros
- `updateRule=null` — no permite modificar registros
- `createRule=""` — cualquier autenticado puede insertar
- `listRule="@request.auth.id != ''"` — solo autenticados pueden listar

---

## Inmutabilidad: doble capa

| Capa | Mecanismo | Limitación |
|---|---|---|
| API FastAPI | Sin endpoints PUT/PATCH/DELETE en el router | Garantía a nivel de API |
| PocketBase | `deleteRule=null`, `updateRule=null` | Protege contra acceso directo a la API de PocketBase; el admin de PocketBase sigue pudiendo modificar directamente vía consola |

---

## Principios de la constitución aplicados

| Principio | Aplicación en este módulo |
|---|---|
| V (auditoría inmutable) | No hay endpoints de edición/borrado. `registrar()` es INSERT-only. |
| VI (degradación) | `audit.registrar()` silencia excepciones — el fallo de auditoría no interrumpe la operación principal |
| VII (caché TTL) | No aplica directamente en este módulo (los selects dinámicos llaman PocketBase en cada request) |
| VIII (paginación) | `_PAGE_SIZE = 50`. Exportación CSV exenta por ser descargable con autenticación verificada |
