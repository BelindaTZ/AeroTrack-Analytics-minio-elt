# Especificación Operativa — Auditoría

**Módulo:** Auditoría
**Prefijo:** AUD
**Código fuente:** `app/auditoria/`
**Casos de uso cubiertos:** CU-O12 (Consultar log de auditoría con filtros), CU-O13 (Exportar log de auditoría)
**Actor:** Usuario autenticado con permiso `seguridad:ver`

---

## Funcionalidad 1: Consultar log de auditoría (CU-O12)

Visualización del log de auditoría con filtros combinables, paginación de 50 registros y modal de detalle. Implementado en `app/auditoria/log.py`. El log es inmutable: no existen endpoints de edición ni borrado en FastAPI, y la colección de PocketBase tiene `deleteRule=null` y `updateRule=null`.

### RF-AUD-001 — Listar registros paginados
`GET /auditoria` retorna los registros ordenados por `-created` (más recientes primero) con paginación de 50 registros por página. Soporta navegación anterior/siguiente.

### RF-AUD-002 — Filtros combinables
Seis filtros: `modulo` (select dinámico desde datos reales, 11 valores posibles), `accion` (select dinámico, 11 valores posibles), `usuario` (texto, busca en `usuario_email` e `usuario_id`), `resultado` (select: exitoso/fallido), `desde` (date, creater >=), `hasta` (date, created <=). Los filtros se combinan con AND en PocketBase.

### RF-AUD-003 — Filtros con actualización AJAX
Los filtros aplican via fetch AJAX sin recargar la página completa. El historial y la paginación se actualizan inline. Los selects de módulo y acción se poblan dinámicamente desde los valores distintos presentes en la colección.

### RF-AUD-004 — Modal de detalle JSON
Cada fila del log es clickeable y abre un modal Bootstrap con: datos estructurados (fecha, usuario, módulo, acción, resultado, IP) y el campo `detalle` renderizado como JSON con sintaxis resaltada (o texto plano si no es JSON válido).

### RF-AUD-005 — Conversión de zona horaria
Los timestamps UTC de PocketBase se convierten a hora local Ecuador (America/Guayaquil, UTC-5, sin DST) para visualización en UI. El formato es `YYYY-MM-DD HH:MM:SS`.

---

## Funcionalidad 2: Exportar log de auditoría (CU-O13)

Exportación del log filtrado a CSV con streaming. Implementado en `app/auditoria/log.py:99`.

### RF-AUD-006 — Exportación CSV con mismos filtros
`GET /auditoria/export` re-aplica exactamente los mismos filtros que la consulta actual y exporta todos los registros coincidentes (sin paginación) a CSV.

### RF-AUD-007 — 10 columnas en exportación
El CSV incluye: Fecha, Usuario (ID), Email, Módulo, Acción, Recurso tipo, Recurso ID, Resultado, IP, Detalle. Encoding UTF-8.

### RF-AUD-008 — Botón de exportación en UI
La UI muestra un botón "Exportar CSV" que enlaza a `/auditoria/export?{filtros_actuales}`. Los filtros aplicados en la consulta se reflejan en la exportación.

---

### RNF-AUD-001 — Log inmutable (doble capa)
No existen endpoints PUT/PATCH/DELETE para la colección `auditoria` en FastAPI. A nivel de PocketBase, la colección tiene `deleteRule=null`, `updateRule=null`, `createRule=""` (cualquier autenticado puede insertar), `listRule="@request.auth.id != ''"`. Esto impide modificación o borrado incluso vía API directa de PocketBase.

### RNF-AUD-002 — La auditoría no bloquea la operación principal
La función `audit.registrar()` envuelve la escritura en try/except. Si PocketBase no está disponible o la escritura falla, la operación principal continúa sin interrupción.

### RNF-AUD-003 — Paginación fija de 50 registros
El tamaño de página es fijo (`_PAGE_SIZE = 50`). No es configurable por el usuario.

---

### RN-AUD-001 — Los registros son INSERT-only
La función `registrar()` en `app/shared/utils/audit.py` solo ejecuta `create_record`. Nunca update ni delete. No existe función de edición o borrado de auditoría en toda la base de código.

### RN-AUD-002 — Los campos accion y modulo son tipo select con valores controlados
`accion` acepta: login, logout, login_fallido, crear, editar, eliminar, ejecutar, exportar, configurar, validar, ver_reporte. `modulo` acepta: seguridad, pipeline_elt, modelo_dimensional, dashboard, puntualidad, rutas, cancelaciones, reportes, predictivo, configuracion, monitoreo. No se pueden insertar valores fuera de estos conjuntos.

### RN-AUD-003 — resultado tiene tres valores posibles
exitoso, fallido, parcial. El default es "exitoso".

### RN-AUD-004 — zona horaria fija UTC-5
Todos los timestamps se convierten a America/Guayaquil (UTC-5, sin horario de verano) para visualización.

---

## Entradas y salidas

| CU | Entrada | Salida |
|----|---------|--------|
| CU-O12 | GET /auditoria?modulo=&accion=&usuario=&resultado=&desde=&hasta=&page= | HTML con tabla de 50 registros, paginación, filtros y modal de detalle. |
| CU-O13 | GET /auditoria/export?{mismos filtros} | CSV streaming con 10 columnas y encoding UTF-8. |

---

## Escenarios

### Camino feliz — Consultar log con filtros
1. El usuario autenticado accede a `GET /auditoria`. Se muestran los últimos 50 registros ordenados por fecha descendente.
2. El usuario selecciona el módulo "seguridad" en el filtro de módulo.
3. AJAX fetch a `GET /auditoria?modulo=seguridad` actualiza la tabla sin recargar la página.
4. El usuario hace clic en un registro; se abre un modal con los datos estructurados y el detalle JSON.

### Camino feliz — Exportar log
1. El usuario aplica filtros: módulo="reportes", resultado="exitoso".
2. Hace clic en "Exportar CSV".
3. `GET /auditoria/export?modulo=reportes&resultado=exitoso` genera un CSV con todos los registros que coinciden.
4. El navegador descarga el archivo `auditoria.csv`.

### Manejo de errores
- **Sin registros:** Si ningún registro coincide con los filtros, la tabla muestra mensaje "No hay registros con los filtros actuales" con icono informativo.
- **Error en fetch AJAX:** Si la consulta AJAX falla, los filtros existentes se mantienen y no se actualiza la tabla (no hay retroalimentación de error al usuario).
- **Detalle no JSON:** Si el campo `detalle` no es JSON válido, se muestra como texto plano en el modal.

---

## Criterios de aceptación

- **CU-O12:** Dado que el usuario autenticado accede al log de auditoría, cuando aplica filtros combinables (módulo, acción, usuario, resultado, rango de fechas), entonces el sistema muestra los registros coincidentes paginados de 50 en 50, ordenados por fecha descendente, con la opción de ver el detalle completo en un modal.
- **CU-O13:** Dado que el usuario autenticado tiene filtros aplicados en el log, cuando solicita exportar, entonces el sistema genera un archivo CSV con 10 columnas que refleja los mismos filtros y lo sirve como descarga streaming.

---

## Dependencias

- **Seguridad:** Autenticación JWT y autorización con permiso `seguridad:ver` (re-usa el permiso del módulo de seguridad).
- **PocketBase:** Colección `auditoria` con reglas de seguridad: deleteRule=null, updateRule=null, createRule="", listRule="@request.auth.id != ''".
- **Zona horaria:** Conversión UTC → America/Guayaquil (UTC-5) hardcodeada en `app/auditoria/log.py:17`.

---

## Casos de uso relacionados

- CU-O12 (Consultar log de auditoría con filtros)
- CU-O13 (Exportar log de auditoría)

---

## Historias de usuario

- Como usuario autenticado, quiero consultar el log de auditoría con filtros por módulo, acción, usuario y rango de fechas, para investigar actividades específicas en el sistema.
- Como usuario autenticado, quiero exportar el log filtrado a CSV, para compartir los registros de actividad con el equipo de auditoría o cumplimiento.
- Como usuario autenticado, quiero ver el detalle completo de cada registro en un modal, para inspeccionar la información adicional sin salir de la vista de lista.

---

## Fuera de alcance

- Edición o borrado de registros de auditoría (inmutable por diseño y por reglas de PocketBase).
- Exportación a formatos diferentes de CSV (PDF, Excel, JSON).
- Alertas automáticas basadas en eventos de auditoría.
- Visualización de estadísticas o gráficos sobre el log (solo tabla plana).
- Suscripción a notificaciones de nuevos eventos de auditoría.
- Filtro por rango de fechas con hora específica (solo fecha completa).
- Ordenación personalizable (siempre por -created).
