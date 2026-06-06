# -*- coding: utf-8 -*-
import sys; sys.stdout.reconfigure(encoding="utf-8")
"""
AeroTrack Analytics — Setup colecciones de administración en PocketBase
v3: usa 'schema' (PocketBase 0.22.x), no 'fields'.
Cambios v3:
  - roles/config: campos created_by, updated_by (relation a app_users)
  - config: campo updated_at (date) + 'ia' en select modulo
  - Nueva colección 'auditoria' (creada después de app_users)
  - 8 configuraciones IA en configuracion_sistema
"""
import sys, os, requests

try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from scripts.config import PB_BASE_URL, PB_EMAIL, PB_PASSWORD
except ImportError:
    try:
        from config import PB_BASE_URL, PB_EMAIL, PB_PASSWORD
    except ImportError:
        from dotenv import load_dotenv; load_dotenv()
        PB_BASE_URL = os.getenv("PB_URL", "http://localhost:8090")
        PB_EMAIL    = os.getenv("PB_EMAIL")
        PB_PASSWORD = os.getenv("PB_PASSWORD")

BASE = PB_BASE_URL.rstrip("/")
S = requests.Session()
S.headers.update({"Content-Type": "application/json"})

def log(msg, ok=True): print(f"  {'OK' if ok else 'ERR'} {msg}")

def auth():
    r = S.post(f"{BASE}/api/admins/auth-with-password",
               json={"identity": PB_EMAIL, "password": PB_PASSWORD})
    if r.status_code != 200:
        r = S.post(f"{BASE}/api/collections/_superusers/auth-with-password",
                   json={"identity": PB_EMAIL, "password": PB_PASSWORD})
    if r.status_code != 200:
        print(f"✗ Auth falló: {r.text}"); sys.exit(1)
    S.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    log(f"Autenticado: {PB_EMAIL}")

def existing_cols():
    r = S.get(f"{BASE}/api/collections?perPage=200")
    return {c["name"]: c["id"] for c in r.json().get("items", [])} if r.ok else {}

def get_col(col_name):
    """Retorna el JSON completo de una colección, o None si no existe."""
    r = S.get(f"{BASE}/api/collections/{col_name}")
    return r.json() if r.ok else None

def create_col(payload, cols):
    name = payload["name"]
    if name in cols:
        log(f"'{name}' ya existe — omitiendo creación")
        return cols[name]
    r = S.post(f"{BASE}/api/collections", json=payload)
    if r.status_code in (200, 201):
        cid = r.json()["id"]
        cols[name] = cid
        log(f"'{name}' creada → {cid}")
        return cid
    log(f"Error '{name}': {r.status_code} — {r.text[:120]}", ok=False)
    return None

def add_fields_if_missing(col_name, new_fields):
    """PATCH idempotente: agrega campos faltantes sin tocar los existentes."""
    col = get_col(col_name)
    if not col:
        return
    existing = {f["name"] for f in col.get("schema", [])}
    to_add = [f for f in new_fields if f["name"] not in existing]
    if not to_add:
        return
    updated = {**col, "schema": col.get("schema", []) + to_add}
    r = S.patch(f"{BASE}/api/collections/{col['id']}", json=updated)
    if r.ok:
        log(f"'{col_name}' — campos añadidos: {[f['name'] for f in to_add]}")
    else:
        log(f"Error PATCH '{col_name}': {r.status_code} — {r.text[:120]}", ok=False)

def update_select_values(col_name, field_name, all_values):
    """Agrega valores faltantes al select `field_name` de una colección existente."""
    col = get_col(col_name)
    if not col:
        return
    schema = col.get("schema", [])
    for field in schema:
        if field["name"] == field_name and field["type"] == "select":
            current = field.get("options", {}).get("values", [])
            missing = [v for v in all_values if v not in current]
            if not missing:
                return
            field["options"]["values"] = current + missing
            r = S.patch(f"{BASE}/api/collections/{col['id']}", json={**col, "schema": schema})
            if r.ok:
                log(f"'{col_name}'.{field_name} — valores añadidos: {missing}")
            else:
                log(f"Error select '{col_name}'.{field_name}: {r.text[:100]}", ok=False)
            return

def records(col, f=None):
    url = f"{BASE}/api/collections/{col}/records?perPage=200"
    if f: url += f"&filter={requests.utils.quote(f)}"
    r = S.get(url)
    return r.json().get("items", []) if r.ok else []

def upsert(col, data, ukey, uval):
    ex = records(col, f'{ukey}="{uval}"')
    if ex: return ex[0]["id"]
    r = S.post(f"{BASE}/api/collections/{col}/records", json=data)
    return r.json().get("id") if r.status_code in (200, 201) else None

# ── Helper de campos ──────────────────────────────────────────────────────────

def _rel_field(name, coll_id, required=False):
    """Campo relation si coll_id disponible, text nullable como fallback.
    Nota: si se crea como text (primer run sin app_users), convertir
    manualmente a relation en PocketBase admin UI tras crear app_users."""
    if coll_id:
        return {"name": name, "type": "relation", "required": required,
                "options": {"collectionId": coll_id, "cascadeDelete": False,
                            "maxSelect": 1, "minSelect": None, "displayFields": None}}
    return {"name": name, "type": "text", "required": False, "options": {}}

# ── Schemas PocketBase v0.22 (usa 'schema', no 'fields') ─────────────────────

def schema_roles(app_users_id=""):
    # CAMBIO 1: created_by y updated_by como relation a app_users
    return {
        "name": "roles", "type": "base",
        "schema": [
            {"name": "nombre",      "type": "text",  "required": True,  "options": {}},
            {"name": "descripcion", "type": "text",  "required": False, "options": {}},
            {"name": "es_sistema",  "type": "bool",  "required": False, "options": {}},
            {"name": "activo",      "type": "bool",  "required": False, "options": {}},
            _rel_field("created_by", app_users_id),
            _rel_field("updated_by", app_users_id),
        ]
    }

def schema_modulos():
    return {
        "name": "modulos", "type": "base",
        "schema": [
            {"name": "clave",          "type": "text",   "required": True,  "options": {}},
            {"name": "nombre_display", "type": "text",   "required": True,  "options": {}},
            {"name": "icono",          "type": "text",   "required": False, "options": {}},
            {"name": "orden",          "type": "number", "required": False, "options": {}},
            {"name": "activo",         "type": "bool",   "required": False, "options": {}},
        ]
    }

def schema_permisos(modulos_col_id):
    return {
        "name": "permisos", "type": "base",
        "schema": [
            {"name": "modulo_id", "type": "relation", "required": True,
             "options": {"collectionId": modulos_col_id, "cascadeDelete": False,
                         "maxSelect": 1, "minSelect": None, "displayFields": None}},
            {"name": "accion", "type": "select", "required": True,
             "options": {"maxSelect": 1,
                         "values": ["ver","crear","editar","eliminar","ejecutar","exportar","configurar"]}},
            {"name": "descripcion", "type": "text", "required": False, "options": {}},
        ]
    }

def schema_roles_permisos(roles_col_id, permisos_col_id):
    return {
        "name": "roles_permisos", "type": "base",
        "schema": [
            {"name": "rol_id", "type": "relation", "required": True,
             "options": {"collectionId": roles_col_id, "cascadeDelete": False,
                         "maxSelect": 1, "minSelect": None, "displayFields": None}},
            {"name": "permiso_id", "type": "relation", "required": True,
             "options": {"collectionId": permisos_col_id, "cascadeDelete": False,
                         "maxSelect": 1, "minSelect": None, "displayFields": None}},
        ]
    }

def schema_config(app_users_id=""):
    # CAMBIO 2: created_by, updated_by (relation) y updated_at (date)
    # CAMBIO 5: "ia" incluido en values de modulo
    return {
        "name": "configuracion_sistema", "type": "base",
        "schema": [
            {"name": "clave",       "type": "text",   "required": True,  "options": {}},
            {"name": "valor",       "type": "text",   "required": False, "options": {}},
            {"name": "tipo",        "type": "select", "required": False,
             "options": {"maxSelect": 1,
                         "values": ["string","int","float","bool","password","email"]}},
            {"name": "modulo",      "type": "select", "required": False,
             "options": {"maxSelect": 1,
                         "values": ["email","alertas","pipeline","sistema","ia"]}},
            {"name": "descripcion", "type": "text",   "required": False, "options": {}},
            {"name": "editable",    "type": "bool",   "required": False, "options": {}},
            {"name": "sensible",    "type": "bool",   "required": False, "options": {}},
            _rel_field("created_by", app_users_id),
            _rel_field("updated_by", app_users_id),
            {"name": "updated_at",  "type": "date",   "required": False, "options": {}},
        ]
    }

def schema_app_users(roles_col_id):
    return {
        "name": "app_users", "type": "auth",
        "options": {
            "allowEmailAuth":    True,   # ← necesario para login con email/contraseña
            "allowUsernameAuth": False,
            "allowOAuth2Auth":   False,
            "minPasswordLength": 8,
            "onlyVerified":      False,
            "requireEmail":      False,
        },
        "schema": [
            {"name": "nombre", "type": "text", "required": True,  "options": {}},
            {"name": "rol_id", "type": "relation", "required": True,
             "options": {"collectionId": roles_col_id, "cascadeDelete": False,
                         "maxSelect": 1, "minSelect": None, "displayFields": None}},
            {"name": "activo", "type": "bool", "required": False, "options": {}},
        ]
    }

def schema_auditoria(app_users_id=""):
    # CAMBIO 3: nueva colección de auditoría, siempre creada después de app_users
    return {
        "name": "auditoria", "type": "base",
        "schema": [
            _rel_field("usuario_id", app_users_id),
            {"name": "usuario_email", "type": "text", "required": True,  "options": {}},
            {"name": "accion", "type": "select", "required": True,
             "options": {"maxSelect": 1,
                         "values": ["login","logout","login_fallido","crear","editar",
                                    "eliminar","ejecutar","exportar","configurar",
                                    "validar","ver_reporte"]}},
            {"name": "modulo", "type": "select", "required": True,
             "options": {"maxSelect": 1,
                         "values": ["seguridad","pipeline_elt","modelo_dimensional",
                                    "dashboard","puntualidad","rutas","cancelaciones",
                                    "reportes","predictivo","configuracion","monitoreo"]}},
            {"name": "recurso_tipo", "type": "text",   "required": False, "options": {}},
            {"name": "recurso_id",   "type": "text",   "required": False, "options": {}},
            {"name": "detalle",      "type": "text",   "required": False, "options": {}},
            {"name": "ip_address",   "type": "text",   "required": False, "options": {}},
            {"name": "resultado",    "type": "select", "required": True,
             "options": {"maxSelect": 1,
                         "values": ["exitoso","fallido","parcial"]}},
        ]
    }

# ── Datos semilla ─────────────────────────────────────────────────────────────

ROLES = [
    {"nombre":"administrador","descripcion":"Acceso total al sistema",      "es_sistema":True, "activo":True},
    {"nombre":"analista",     "descripcion":"Acceso a módulos de análisis","es_sistema":True, "activo":True},
    {"nombre":"viewer",       "descripcion":"Solo lectura de análisis",     "es_sistema":False,"activo":True},
]

MODULOS = [
    {"clave":"seguridad",          "nombre_display":"Seguridad",          "icono":"bi-shield-lock",    "orden":1, "activo":True},
    {"clave":"pipeline_elt",       "nombre_display":"Pipeline ELT",       "icono":"bi-gear",           "orden":2, "activo":True},
    {"clave":"modelo_dimensional", "nombre_display":"Modelo Dimensional", "icono":"bi-database",       "orden":3, "activo":True},
    {"clave":"dashboard",          "nombre_display":"Dashboard",          "icono":"bi-bar-chart",      "orden":4, "activo":True},
    {"clave":"puntualidad",        "nombre_display":"Puntualidad",        "icono":"bi-clock",          "orden":5, "activo":True},
    {"clave":"rutas",              "nombre_display":"Rutas",              "icono":"bi-map",            "orden":6, "activo":True},
    {"clave":"cancelaciones",      "nombre_display":"Cancelaciones",      "icono":"bi-x-circle",       "orden":7, "activo":True},
    {"clave":"reportes",           "nombre_display":"Reportes",           "icono":"bi-file-earmark",   "orden":8, "activo":True},
    {"clave":"predictivo",         "nombre_display":"Predictivo",         "icono":"bi-graph-up-arrow", "orden":9, "activo":True},
    {"clave":"configuracion",      "nombre_display":"Configuración",      "icono":"bi-sliders",        "orden":10,"activo":True},
    {"clave":"monitoreo",          "nombre_display":"Monitoreo",          "icono":"bi-activity",       "orden":11,"activo":True},
]

PERMISOS_DEF = {
    "seguridad":          ["ver","crear","editar","eliminar","configurar"],
    "pipeline_elt":       ["ver","ejecutar"],
    "modelo_dimensional": ["ver","crear","editar","eliminar","ejecutar"],
    "dashboard":          ["ver"],
    "puntualidad":        ["ver","exportar"],
    "rutas":              ["ver","exportar"],
    "cancelaciones":      ["ver","exportar"],
    "reportes":           ["ver","exportar"],
    "predictivo":         ["ver","exportar","configurar"],
    "configuracion":      ["ver","configurar"],
    "monitoreo":          ["ver"],
}

ANALISTA = {
    "modelo_dimensional": ["ver"],
    "dashboard":          ["ver"],
    "puntualidad":        ["ver","exportar"],
    "rutas":              ["ver","exportar"],
    "cancelaciones":      ["ver","exportar"],
    "reportes":           ["ver","exportar"],
    "predictivo":         ["ver","exportar"],
}

VIEWER = {
    "dashboard":     ["ver"],
    "puntualidad":   ["ver"],
    "rutas":         ["ver"],
    "cancelaciones": ["ver"],
}

CONFIG = [
    # ── Email ──
    {"clave":"email_smtp_host",        "valor":"smtp.gmail.com","tipo":"string",  "modulo":"email",   "descripcion":"Servidor SMTP",               "editable":True, "sensible":False},
    {"clave":"email_smtp_port",        "valor":"587",           "tipo":"int",     "modulo":"email",   "descripcion":"Puerto SMTP",                 "editable":True, "sensible":False},
    {"clave":"email_remitente",        "valor":"",              "tipo":"email",   "modulo":"email",   "descripcion":"Email remitente",             "editable":True, "sensible":False},
    {"clave":"email_password",         "valor":"",              "tipo":"password","modulo":"email",   "descripcion":"Contraseña SMTP",             "editable":True, "sensible":True},
    {"clave":"email_usar_tls",         "valor":"true",          "tipo":"bool",    "modulo":"email",   "descripcion":"Usar TLS",                    "editable":True, "sensible":False},
    {"clave":"email_alertas_activas",  "valor":"false",         "tipo":"bool",    "modulo":"email",   "descripcion":"Activar alertas por email",   "editable":True, "sensible":False},
    {"clave":"email_destinatario",     "valor":"",              "tipo":"email",   "modulo":"email",   "descripcion":"Destinatario de alertas",     "editable":True, "sensible":False},
    # ── Alertas ──
    {"clave":"alerta_otp_umbral_min",  "valor":"0.80",          "tipo":"float",   "modulo":"alertas", "descripcion":"OTP mínimo aceptable (0-1)", "editable":True, "sensible":False},
    {"clave":"alerta_cancelacion_max", "valor":"0.05",          "tipo":"float",   "modulo":"alertas", "descripcion":"Tasa máx cancelaciones",     "editable":True, "sensible":False},
    {"clave":"alerta_retraso_minutos", "valor":"15",            "tipo":"int",     "modulo":"alertas", "descripcion":"Min. retraso para alerta",   "editable":True, "sensible":False},
    {"clave":"alerta_ruta_ineficiente","valor":"0.15",          "tipo":"float",   "modulo":"alertas", "descripcion":"% desviación ruta",          "editable":True, "sensible":False},
    # ── Pipeline ──
    {"clave":"pipeline_batch_size",    "valor":"5000",          "tipo":"int",     "modulo":"pipeline","descripcion":"Tamaño lote carga PocketBase","editable":True, "sensible":False},
    {"clave":"pipeline_max_workers",   "valor":"10",            "tipo":"int",     "modulo":"pipeline","descripcion":"Hilos concurrentes extract",  "editable":True, "sensible":False},
    {"clave":"pipeline_reintentos",    "valor":"3",             "tipo":"int",     "modulo":"pipeline","descripcion":"Reintentos por fallo",        "editable":True, "sensible":False},
    # ── IA (CAMBIO 4) ──
    {"clave":"ia_proveedor",           "valor":"openai",        "tipo":"string",  "modulo":"ia",      "descripcion":"Proveedor: openai|anthropic|gemini|custom", "editable":True, "sensible":False},
    {"clave":"ia_api_key",             "valor":"",              "tipo":"password","modulo":"ia",      "descripcion":"API Key del proveedor de IA",              "editable":True, "sensible":True},
    {"clave":"ia_modelo",              "valor":"gpt-4o",        "tipo":"string",  "modulo":"ia",      "descripcion":"Modelo a usar (gpt-4o, claude-sonnet-4-5...)","editable":True,"sensible":False},
    {"clave":"ia_endpoint",            "valor":"",              "tipo":"string",  "modulo":"ia",      "descripcion":"Endpoint custom (Ollama, proxy...)",        "editable":True, "sensible":False},
    {"clave":"ia_max_tokens",          "valor":"1000",          "tipo":"int",     "modulo":"ia",      "descripcion":"Tokens máximos por respuesta",             "editable":True, "sensible":False},
    {"clave":"ia_temperatura",         "valor":"0.3",           "tipo":"float",   "modulo":"ia",      "descripcion":"Temperatura 0.0-1.0",                      "editable":True, "sensible":False},
    {"clave":"ia_activa",              "valor":"false",         "tipo":"bool",    "modulo":"ia",      "descripcion":"Habilita el módulo de IA",                 "editable":True, "sensible":False},
    {"clave":"ia_timeout_segundos",    "valor":"30",            "tipo":"int",     "modulo":"ia",      "descripcion":"Timeout por respuesta en segundos",        "editable":True, "sensible":False},
    # ── IA narrativa (Grok primario → Gemini fallback) ──
    {"clave":"ia_api_key_grok",        "valor":"",              "tipo":"password","modulo":"ia",      "descripcion":"API Key xAI (Grok 3 mini) para narrativa",  "editable":True, "sensible":True},
    {"clave":"ia_api_key_gemini",      "valor":"",              "tipo":"password","modulo":"ia",      "descripcion":"API Key Google (Gemini 2.0 Flash) fallback","editable":True, "sensible":True},
]

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "="*60)
    print("  AeroTrack Analytics -- Setup PocketBase Admin v3")
    print("="*60)

    print("\n[1/9] Autenticando...")
    auth()

    cols = existing_cols()

    # Obtener app_users_id si ya existe (ejecuciones posteriores al primer run)
    app_users_id = S.get(f"{BASE}/api/collections/app_users").json().get("id", "")
    if app_users_id:
        log(f"app_users ya existe (id={app_users_id}) — usando relaciones reales")
    else:
        log("app_users no existe aún — created_by/updated_by se crearán como text")

    # ── roles ──────────────────────────────────────────────────────────────────
    print("\n[2/9] Colección 'roles'...")
    create_col(schema_roles(app_users_id), cols)
    # Parchar campos faltantes en colecciones ya existentes (idempotente)
    add_fields_if_missing("roles", [
        _rel_field("created_by", app_users_id),
        _rel_field("updated_by", app_users_id),
    ])
    role_ids = {}
    for r in ROLES:
        rid = upsert("roles", r, "nombre", r["nombre"])
        if rid:
            role_ids[r["nombre"]] = rid
            log(f"Rol '{r['nombre']}'")

    # ── modulos ────────────────────────────────────────────────────────────────
    print("\n[3/9] Colección 'modulos'...")
    create_col(schema_modulos(), cols)
    mod_ids = {}
    for m in MODULOS:
        mid = upsert("modulos", m, "clave", m["clave"])
        if mid:
            mod_ids[m["clave"]] = mid
            log(f"Módulo '{m['clave']}'")

    # ── permisos ───────────────────────────────────────────────────────────────
    print("\n[4/9] Colección 'permisos'...")
    create_col(schema_permisos(cols.get("modulos", "")), cols)
    perm_ids = {}
    for clave, acciones in PERMISOS_DEF.items():
        mid = mod_ids.get(clave)
        if not mid:
            continue
        for accion in acciones:
            ex = records("permisos", f'modulo_id="{mid}"&&accion="{accion}"')
            if ex:
                perm_ids[(clave, accion)] = ex[0]["id"]
            else:
                r2 = S.post(f"{BASE}/api/collections/permisos/records",
                            json={"modulo_id": mid, "accion": accion,
                                  "descripcion": f"{accion} en {clave}"})
                if r2.status_code in (200, 201):
                    perm_ids[(clave, accion)] = r2.json()["id"]
    log(f"{len(perm_ids)} permisos definidos")

    # ── roles_permisos ─────────────────────────────────────────────────────────
    print("\n[5/9] Colección 'roles_permisos'...")
    create_col(schema_roles_permisos(cols.get("roles", ""), cols.get("permisos", "")), cols)

    def asignar(nombre_rol, perms_dict):
        rid = role_ids.get(nombre_rol)
        if not rid:
            return
        n = 0
        for clave, acciones in perms_dict.items():
            for accion in acciones:
                pid = perm_ids.get((clave, accion))
                if not pid:
                    continue
                ex = records("roles_permisos", f'rol_id="{rid}"&&permiso_id="{pid}"')
                if not ex:
                    S.post(f"{BASE}/api/collections/roles_permisos/records",
                           json={"rol_id": rid, "permiso_id": pid})
                    n += 1
        log(f"Rol '{nombre_rol}': {n} nuevos permisos asignados")

    asignar("administrador", PERMISOS_DEF)
    asignar("analista", ANALISTA)
    asignar("viewer", VIEWER)

    # ── configuracion_sistema ──────────────────────────────────────────────────
    print("\n[6/9] Colección 'configuracion_sistema'...")
    create_col(schema_config(app_users_id), cols)
    # Parchar campos faltantes (CAMBIO 2)
    add_fields_if_missing("configuracion_sistema", [
        _rel_field("created_by", app_users_id),
        _rel_field("updated_by", app_users_id),
        {"name": "updated_at", "type": "date", "required": False, "options": {}},
    ])
    # Agregar "ia" al select modulo si todavía no está (CAMBIO 5)
    update_select_values("configuracion_sistema", "modulo",
                         ["email", "alertas", "pipeline", "sistema", "ia"])

    n_cfg = 0
    n_ia  = 0
    for cfg in CONFIG:
        rid = upsert("configuracion_sistema", cfg, "clave", cfg["clave"])
        if rid:
            n_cfg += 1
            if cfg.get("modulo") == "ia":
                n_ia += 1
    log(f"{n_cfg} configuraciones verificadas")
    log(f"{n_ia} configuraciones IA agregadas/verificadas")

    # ── app_users ──────────────────────────────────────────────────────────────
    print("\n[7/9] Colección 'app_users'...")
    create_col(schema_app_users(cols.get("roles", "")), cols)

    # ── usuario administrador ──────────────────────────────────────────────────
    print("\n[8/9] Usuario administrador...")
    admin_rid = role_ids.get("administrador")
    ex_u = records("app_users", f'email="{PB_EMAIL}"')
    if ex_u:
        log(f"Usuario '{PB_EMAIL}' ya existe")
        if not ex_u[0].get("activo"):
            ru = S.patch(f"{BASE}/api/collections/app_users/records/{ex_u[0]['id']}",
                         json={"activo": True})
            if ru.ok:
                log("Usuario activado (estaba inactivo)")
    else:
        ru = S.post(f"{BASE}/api/collections/app_users/records", json={
            "email": PB_EMAIL, "password": PB_PASSWORD,
            "passwordConfirm": PB_PASSWORD,
            "nombre": "Belinda Toaquiza",
            "rol_id": admin_rid, "activo": True, "emailVisibility": True,
        })
        if ru.status_code in (200, 201):
            log(f"Usuario admin creado: {PB_EMAIL}")
        else:
            log(f"Error usuario: {ru.status_code} — {ru.text[:100]}", ok=False)

    # ── auditoria (después de app_users para garantizar el ID) ────────────────
    print("\n[9/9] Colección 'auditoria'...")
    # Refrescar app_users_id: si se acaba de crear, ahora existe
    app_users_id_final = S.get(f"{BASE}/api/collections/app_users").json().get("id", app_users_id)
    create_col(schema_auditoria(app_users_id_final), cols)

    # ── Resumen ────────────────────────────────────────────────────────────────
    cols_final = existing_cols()
    cfg_total  = len(records("configuracion_sistema"))
    print("\n" + "="*60)
    print("  Setup completado OK")
    print(f"  Roles: {len(role_ids)} | Modulos: {len(mod_ids)} | Permisos: {len(perm_ids)}")
    print(f"  Configuraciones totales: {cfg_total} (IA: {n_ia})")
    print(f"  Colecciones en PocketBase: {len(cols_final)}")
    print(f"  Verifica en: {BASE}/_/")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
