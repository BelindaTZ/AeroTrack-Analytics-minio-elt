# Especificación Operativa — Auditoría

**Módulo:** Auditoría
**Prefijo:** AUD
**Código fuente:** `app/auditoria/`
**Casos de uso cubiertos:** CU-O12 (Consultar log de auditoría con filtros), CU-O13 (Exportar log de auditoría)
**Actor:** Administrador

---

## Funcionalidad 1: Consultar log de auditoría (CU-O12)

Visualización del log de auditoría con filtros combinables, paginación de 50 registros y modal de detalle. El log es inmutable: no existen operaciones de edición ni borrado, y la colección de repositorio tiene reglas que impiden su modificación.

### RF-AUD-001 — Listar registros paginados
El sistema debe retornar los registros de auditoría ordenados por fecha de creación descendente (más recientes primero) con paginación de 50 registros por página y navegación anterior/siguiente.

### RF-AUD-002 — Filtros combinables
El sistema debe ofrecer seis filtros combinables: módulo (selector dinámico desde datos reales, 11 valores posibles), acción (selector dinámico, 11 valores posibles), usuario (texto, busca en email e identificador), resultado (selector: exitoso/fallido), desde (fecha, registros desde esa fecha), hasta (fecha, registros hasta esa fecha). Los filtros se aplican con operador AND.

### RF-AUD-003 — Filtros con actualización sin recarga
El sistema debe aplicar los filtros sin recargar la página completa, actualizando la tabla y la paginación en línea. Los selectores de módulo y acción se deben poblar dinámicamente desde los valores distintos presentes en el log.

### RF-AUD-004 — Modal de detalle JSON
El sistema debe mostrar al hacer clic en un registro un panel modal con los datos estructurados del evento (fecha, usuario, módulo, acción, resultado, IP) y el campo de detalle renderizado con sintaxis resaltada como JSON, o como texto plano si no es JSON válido.

### RF-AUD-005 — Conversión de zona horaria
El sistema debe convertir los timestamps UTC a hora local Ecuador (America/Guayaquil, UTC-5, sin horario de verano) para su visualización. El formato de presentación es `YYYY-MM-DD HH:MM:SS`. La conversión se realiza mediante la biblioteca estándar de Python.

---

## Funcionalidad 2: Exportar log de auditoría (CU-O13)

Exportación del log filtrado a CSV con streaming.

### RF-AUD-006 — Exportación CSV con mismos filtros
El sistema debe exportar todos los registros que coincidan con los filtros activos al momento de la exportación (sin paginación) a un archivo CSV descargable.

### RF-AUD-007 — 10 columnas en exportación
El sistema debe generar el archivo CSV con 10 columnas: Fecha, Usuario (ID), Email, Módulo, Acción, Recurso tipo, Recurso ID, Resultado, IP, Detalle. Codificación UTF-8.

### RF-AUD-008 — Botón de exportación en UI
El sistema debe mostrar un botón "Exportar CSV" que refleje los filtros activos en la exportación resultante.

---

### RNF-AUD-001 — Log inmutable (doble capa)
El sistema no debe exponer operaciones de modificación ni borrado sobre el log de auditoría. A nivel de repositorio, la colección prohíbe modificaciones y borrados, permite inserción a cualquier usuario autenticado, y restringe la consulta a usuarios autenticados. Esto impide la alteración de registros incluso a través del acceso directo al repositorio.

### RNF-AUD-002 — La auditoría no bloquea la operación principal
El sistema debe registrar los eventos de auditoría de forma resiliente. Si el repositorio no está disponible o la escritura falla, la operación principal continúa sin interrupción.

### RNF-AUD-003 — Paginación fija de 50 registros
El tamaño de página es fijo en 50 registros y no es configurable por el usuario.

---

### RN-AUD-001 — Los registros son INSERT-only
El sistema solo ejecuta operaciones de inserción en el log de auditoría. No existe funcionalidad de modificación o borrado de registros de auditoría en ninguna parte del sistema.

### RN-AUD-002 — Los campos accion y modulo son tipo select con valores controlados
`accion` acepta: login, logout, login_fallido, crear, editar, eliminar, ejecutar, exportar, configurar, validar, ver_reporte. `modulo` acepta: seguridad, pipeline_elt, modelo_dimensional, dashboard, puntualidad, rutas, cancelaciones, reportes, predictivo, configuracion, monitoreo. No se pueden insertar valores fuera de estos conjuntos.

### RN-AUD-003 — resultado tiene tres valores posibles
exitoso, fallido, parcial. El valor por defecto es "exitoso".

### RN-AUD-004 — Zona horaria fija UTC-5
Todos los timestamps se convierten a America/Guayaquil (UTC-5, sin horario de verano) para visualización.

---

## Entradas y salidas

| CU | Entrada | Salida |
|----|---------|--------|
| CU-O12 | Filtros: modulo, accion, usuario, resultado, desde, hasta, page | HTML con tabla de 50 registros, paginación, filtros y modal de detalle. |
| CU-O13 | Mismos filtros de la consulta activa | CSV streaming con 10 columnas y codificación UTF-8. |

---

## Escenarios

### Camino feliz — Consultar log con filtros
1. El usuario autenticado accede al log de auditoría. Se muestran los últimos 50 registros ordenados por fecha descendente.
2. El usuario selecciona el módulo "seguridad" en el filtro de módulo.
3. La tabla se actualiza sin recargar la página mostrando solo registros del módulo seguridad.
4. El usuario hace clic en un registro; se abre un modal con los datos estructurados y el detalle JSON.

### Camino feliz — Exportar log
1. El usuario aplica filtros: módulo="reportes", resultado="exitoso".
2. Hace clic en "Exportar CSV".
3. El sistema genera un CSV con todos los registros que coinciden con los filtros.
4. El navegador descarga el archivo `auditoria.csv`.

### Manejo de errores
- **Sin registros:** Si ningún registro coincide con los filtros, la tabla muestra mensaje "No hay registros con los filtros actuales" con icono informativo.
- **Error en actualización sin recarga:** Si la consulta falla, los filtros existentes se mantienen y no se actualiza la tabla.
- **Detalle no JSON:** Si el campo `detalle` no es JSON válido, se muestra como texto plano en el modal.

---

## Criterios de aceptación

- **CU-O12:** Dado que el usuario autenticado accede al log de auditoría, cuando aplica filtros combinables (módulo, acción, usuario, resultado, rango de fechas), entonces el sistema muestra los registros coincidentes paginados de 50 en 50, ordenados por fecha descendente, con la opción de ver el detalle completo en un modal.
- **CU-O13:** Dado que el usuario autenticado tiene filtros aplicados en el log, cuando solicita exportar, entonces el sistema genera un archivo CSV con 10 columnas que refleja los mismos filtros y lo sirve como descarga streaming.

---

## Dependencias

- **Seguridad:** Autenticación JWT y autorización con permiso `seguridad:ver` (re-usa el permiso del módulo de seguridad).
- **PocketBase:** Colección `auditoria` con reglas de seguridad: deleteRule=null, updateRule=null, createRule="", listRule="@request.auth.id != ''".
- **Zona horaria:** Conversión UTC → America/Guayaquil (UTC-5) mediante la biblioteca estándar de Python (datetime.timezone), sin dependencia de pytz ni zoneinfo.

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
- Ordenación personalizable (siempre por fecha descendente).
