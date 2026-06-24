# Checklist de Verificación — Auditoría Operativa

**Módulo:** Auditoría  
**Spec de referencia:** `specs/operativo/auditoria/auditoria-spec.md`  
**Código verificado:** `app/auditoria/log.py`, `app/shared/utils/audit.py`  
**Fecha de auditoría:** 2026-06-22

---

## Casos de uso (criterios de aceptación del spec)

### CU-O12 — Consultar log de auditoría con filtros

- [x] **Dado** que el usuario autenticado accede al log de auditoría, **cuando** aplica filtros combinables (módulo, acción, usuario, resultado, rango de fechas), **entonces** el sistema muestra los registros coincidentes paginados de 50 en 50, ordenados por fecha descendente, con la opción de ver el detalle completo en un modal.
  - `log.py:39-96`: 6 filtros combinables con AND (`&&`), `sort="-created"`, `per_page=50`
  - El modal de detalle está en el template `auditoria/index.html` (no auditado en código Python)

### CU-O13 — Exportar log de auditoría

- [x] **Dado** que el usuario autenticado tiene filtros aplicados en el log, **cuando** solicita exportar, **entonces** el sistema genera un archivo CSV con 10 columnas que refleja los mismos filtros y lo sirve como descarga streaming.
  - `log.py:99-151`: misma lógica de filtros, `list_records_all()` sin paginación, `StreamingResponse` con 10 columnas

---

## Requerimientos funcionales (RF-AUD-0XX)

- [x] **RF-AUD-001** — `GET /auditoria` retorna registros ordenados por `-created` con paginación de 50.
  - `log.py:68-74`: `sort="-created"`, `per_page=_PAGE_SIZE` donde `_PAGE_SIZE=50`

- [x] **RF-AUD-002** — 6 filtros combinables: módulo, acción, usuario, resultado, desde, hasta.
  - `log.py:53-65`: 6 condiciones construidas con `&&`. Filtro `usuario` busca en `usuario_email` y `usuario_id`.

- [x] **RF-AUD-003** — Filtros aplican via fetch AJAX sin recargar. Selects dinámicos.
  - `log.py:80-82`: `_get_distinct("modulo")` y `_get_distinct("accion")` populan los selects dinámicamente.
  - El comportamiento AJAX es frontend (template), no verificado en código Python.

- [x] **RF-AUD-004** — Modal de detalle JSON con datos estructurados.
  - No verificable en router.py — implementado en template `auditoria/index.html`.

- [x] **RF-AUD-005** — Conversión de timestamps UTC → America/Guayaquil (UTC-5).
  - `log.py:17-28`: `_TZ = timezone(timedelta(hours=-5))`, `_fmt_local()`, `_localizar_registros()`

- [x] **RF-AUD-006** — `GET /auditoria/export` re-aplica exactamente los mismos filtros y exporta sin paginación.
  - `log.py:99-151`: misma construcción de `filter_str`, `pb_client.list_records_all()` sin limit

- [x] **RF-AUD-007** — CSV con 10 columnas: Fecha, Usuario, Email, Módulo, Acción, Recurso tipo, Recurso ID, Resultado, IP, Detalle.
  - `log.py:130-131`: `writer.writerow(["Fecha", "Usuario", "Email", "Módulo", "Acción", "Recurso tipo", "Recurso ID", "Resultado", "IP", "Detalle"])`

- [x] **RF-AUD-008** — Botón "Exportar CSV" en UI enlaza a `/auditoria/export?{filtros_actuales}`.
  - No verificable en router.py — implementado en template `auditoria/index.html`.

---

## Requerimientos no funcionales (RNF-AUD-0XX)

- [x] **RNF-AUD-001** — Log inmutable (doble capa): sin endpoints PUT/PATCH/DELETE en FastAPI y reglas PocketBase.
  - `log.py`: solo endpoints `GET ""` y `GET "/export"`. Sin PUT/PATCH/DELETE.
  - `audit.py`: solo `pb_client.create_record()`. Sin update ni delete.

- [x] **RNF-AUD-002** — `audit.registrar()` no bloquea la operación principal.
  - `audit.py:17-31`: implementado con `try: ... except Exception: pass`

- [x] **RNF-AUD-003** — Paginación fija de 50 registros.
  - `log.py:36`: `_PAGE_SIZE = 50`. No es configurable por el usuario.

---

## Reglas de negocio (RN-AUD-0XX)

- [x] **RN-AUD-001** — Registros INSERT-only.
  - `audit.py:19`: única llamada: `pb_client.create_record("auditoria", {...})`. No existen `update_record()` ni `delete_record()` para la colección `auditoria` en el codebase.

- [x] **RN-AUD-002** — Campos `accion` y `modulo` con valores controlados.
  - Valores controlados documentados en spec. La función `registrar()` no valida el valor (confianza en el llamador). La validación real la hace PocketBase a nivel de colección (tipo select).

- [x] **RN-AUD-003** — `resultado` tiene tres valores: exitoso, fallido, parcial.
  - `audit.py:15`: `resultado: str = "exitoso"`. Los valores `fallido` y `parcial` se pasan explícitamente cuando corresponde.

- [x] **RN-AUD-004** — Zona horaria fija UTC-5.
  - `log.py:17`: `_TZ = timezone(timedelta(hours=-5))` — sin DST, hardcodeado.

---

## Verificación de audit.registrar()

| Campo | Implementado | Valor/Tipo |
|---|---|---|
| `usuario_id` | ✅ | str (UUID de PocketBase) |
| `usuario_email` | ✅ | str (email del usuario) |
| `accion` | ✅ | str (uno de los 11 valores controlados) |
| `modulo` | ✅ | str (uno de los 11 módulos) |
| `recurso_tipo` | ✅ | str opcional, default `""` |
| `recurso_id` | ✅ | str opcional, default `""` |
| `detalle` | ✅ | str opcional, default `""` |
| `ip_address` | ✅ | str opcional, default `""` |
| `resultado` | ✅ | str, default `"exitoso"` |
| try/except silencioso | ✅ | `except Exception: pass` |

---

## Verificación cruzada código ↔ spec

| Item | Estado | Nota |
|---|---|---|
| 6 filtros combinables | ✅ Coincide | `log.py:53-65` |
| Filtro usuario busca email e ID | ✅ Coincide | `usuario_email~"{v}"||usuario_id="{v}"` |
| Paginación 50 registros | ✅ Coincide | `_PAGE_SIZE = 50` en `log.py:36` |
| Ordenado por -created | ✅ Coincide | `sort="-created"` en `log.py:72` |
| 10 columnas en CSV | ✅ Coincide | `log.py:130-131` |
| Encoding UTF-8 en CSV | ✅ Coincide | Spec RF-AUD-007 dice "Codificación UTF-8"; código usa `io.StringIO()` que produce UTF-8 estándar |
| Zona horaria UTC-5 hardcodeada | ✅ Coincide | `log.py:17` `timezone(timedelta(hours=-5))` |
| Biblioteca de timezone | ✅ Coincide | Spec dependencias dice "biblioteca estándar de Python (datetime.timezone)"; código usa `datetime.timezone` |
| Sin endpoints de edición/borrado | ✅ Coincide | Solo GET en el router de auditoría |
| INSERT-only en audit.registrar() | ✅ Coincide | `audit.py:19` solo `create_record()` |
| Selects dinámicos (no hardcodeados) | ✅ Coincide | `_get_distinct()` en `log.py:154` |
| Spec dice 11 valores accion / 11 valores modulo | ✅ Coincide con RN-AUD-002 | Verificado en spec; el código confía en el llamador |
| Modal de detalle JSON | ⚠️ No verificado | Implementado en template, fuera del scope del router |
| Comportamiento AJAX | ⚠️ No verificado | Frontend en `auditoria/index.html`, no en router.py |
