## Goal
- Cerrar 4 gaps de Lote 4 (Predictivo y Asistente IA) en orden: Gap 1 → Gap 2 → Gap 3 → Gap 4

## Constraints & Preferences
- Mostrar diff o archivo completo antes de aplicar, esperar confirmación
- Auditar toda escritura, RBAC en FastAPI, sin secretos hardcodeados
- Un entregable a la vez en el orden indicado

## Progress
### Done
- Auditoría técnica de Lote 4 completa: Predictivo 6/7 ✅, 1 ⚠️; Asistente IA 1/3 ✅, 2 ⚠️
- Gap 1: `informe_ejecutivo.py` ahora usa `_perm_export = require_permission("predictivo", "exportar")` en `POST /informe` (líneas 26-27)
- Gap 2 (CU-O14 — historial persistente):
  - Collection `conversaciones_asistente` añadida a `setup_pocketbase_admin.py` (schema, step 10/10)
  - `_persist_conversacion()` en `router.py:49` — escribe cada exchange en PocketBase con try/except (resiliente)
  - `GET /historial` en `router.py:173` — últimas 20 conversaciones del usuario JWT, vía admin admin
  - Sidebar en `chat.html` — muestra historial reciente (últimos 5), click para re-enviar pregunta
- Gap 3 (CU-E22 — simulador what-if backend):
  - `_simular_whatif()` en `proyeccion_riesgo.py:456` — corre Holt-Winters base + aplica delta de escenario a proyección e IC
  - `POST /predictivo/whatif` en `proyeccion_riesgo.py:510` — acepta JSON {aerolinea, anio, horizonte, buffer_minutos, reduccion_carga}, retorna proyección ajustada + metadatos whatif.delta
  - Frontend `updateWhatIf()` ahora llama al backend en vez de calcular localmente con constantes hardcodeadas
- Gap 4 (CU-T09 — fuentes de conocimiento toggleables):
  - Collection `asistente_fuentes` añadida a `setup_pocketbase_admin.py` (schema, seed 10 fuentes, step 11/11)
  - `_get_activas()` en `rag.py` — cachea 60s las fuentes activas desde PocketBase, fallback a todas
  - `build_context()` modificado — cada sección verifica `"clave" in activas` antes de cargar
  - `GET /ia/fuentes` + `POST /ia/fuentes/toggle` en `router.py` — toggle con invalidación de cache
  - Sidebar en `chat.html` — collapsible "Fuentes activas" con checkboxes toggleables
  - Setup script refactorizado: `schema_conversaciones_asistente` movida antes de `main()`, migración auditoria corregida

### In Progress
- (none)

### Blocked
- (none)

## Key Decisions
- Gap 1: patrón idéntico a `reportes/router.py` donde exportación usa `_perm_export`
- Gap 2: escritura resiliente — si falla persistencia no interrumpe respuesta al usuario
- Gap 2: se mantiene historial en memoria para contexto RAG (multi-turn); la DB es capa adicional permanente
- Gap 3: what-if corre Holt-Winters real y ajusta solo valores proyectados (no re-entrena sobre datos históricos modificados)
- Gap 4: RAG dinámico con cache de 60s; toggle invalida cache mutando `_SOURCE_CACHE["data"] = None`
- Gap 4: fallback a todas las fuentes si PocketBase no responde (resiliente)
- Gaps en orden secuencial: 1→2→3→4

## Next Steps
- (todos los gaps de Lote 4 completados)

## Critical Context
- `statsmodels` (Holt-Winters) usado en predictivo, no Prophet como menciona spec — gap documentado en auditoría
- RAG sin embeddings vectoriales, usa parseo regex + consultas estructuradas a 10 tablas Parquet
- Historial actual es volátil (`_sessions` dict en memoria, TTL 30 min)
- Permisos RBAC existentes: predictivo=[ver, exportar], asistente_ia=[ver, ejecutar]
- Config IA en configuracion_sistema modulo="ia" (proveedor, modelo, API keys, max_tokens)
- 4 gaps detectados en auditoría: permiso exportar, historial persistente, what-if backend, fuentes knowledge base

## Relevant Files
- app/predictivo/informe_ejecutivo.py: Gap 1 — permiso cambiado a exportar
- app/predictivo/proyeccion_riesgo.py: Gap 3 — _simular_whatif(), POST /whatif
- app/asistente_ia/router.py: Gap 2 — persistencia historial, endpoint GET /historial; Gap 4 — fuentes toggle
- app/asistente_ia/rag.py: 10 fuentes Parquet hardcodeadas, parseo regex de intención; Gap 4 — _get_activas(), build_context dinámico
- app/asistente_ia/llm_client.py: multi-proveedor (Groq, Anthropic, Gemini, OpenAI)
- scripts/setup_pocketbase_admin.py: Gap 2 y 4 — nuevas colecciones + seed data + refactor
- app/predictivo/templates/predictivo/index.html: Gap 3 — what-if llama backend
- app/asistente_ia/templates/asistente_ia/chat.html: Gap 2 — historial en UI; Gap 4 — fuentes toggle
- app/reportes/router.py: patrón de exportación usado como referencia para Gap 1
- app/shared/deps.py: require_permission, render, invalidate_permission_cache
