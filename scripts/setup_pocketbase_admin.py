"""
AeroTrack Analytics — Setup colecciones de administración en PocketBase
Versión corregida para PocketBase v0.22.x (usa 'schema' no 'fields')
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

def log(msg, ok=True): print(f"  {'✓' if ok else '✗'} {msg}")

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

def create_col(payload, cols):
    name = payload["name"]
    if name in cols:
        log(f"'{name}' ya existe — omitiendo")
        return cols[name]
    r = S.post(f"{BASE}/api/collections", json=payload)
    if r.status_code in (200, 201):
        cid = r.json()["id"]
        cols[name] = cid
        log(f"'{name}' creada → {cid}")
        return cid
    log(f"Error '{name}': {r.status_code} — {r.text[:120]}", ok=False)
    return None

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

# ── Schemas PocketBase v0.22 (usa 'schema', no 'fields') ──────────────────────

def schema_roles():
    return {
        "name": "roles", "type": "base",
        "schema": [
            {"name": "nombre",      "type": "text",  "required": True,  "options": {}},
            {"name": "descripcion", "type": "text",  "required": False, "options": {}},
            {"name": "es_sistema",  "type": "bool",  "required": False, "options": {}},
            {"name": "activo",      "type": "bool",  "required": False, "options": {}},
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

def schema_config():
    return {
        "name": "configuracion_sistema", "type": "base",
        "schema": [
            {"name": "clave",       "type": "text",   "required": True,  "options": {}},
            {"name": "valor",       "type": "text",   "required": False, "options": {}},
            {"name": "tipo",        "type": "select", "required": False,
             "options": {"maxSelect": 1, "values": ["string","int","float","bool","password","email"]}},
            {"name": "modulo",      "type": "select", "required": False,
             "options": {"maxSelect": 1, "values": ["email","alertas","pipeline","sistema"]}},
            {"name": "descripcion", "type": "text",   "required": False, "options": {}},
            {"name": "editable",    "type": "bool",   "required": False, "options": {}},
            {"name": "sensible",    "type": "bool",   "required": False, "options": {}},
        ]
    }

def schema_app_users(roles_col_id):
    return {
        "name": "app_users", "type": "auth",
        "schema": [
            {"name": "nombre", "type": "text", "required": True,  "options": {}},
            {"name": "rol_id", "type": "relation", "required": True,
             "options": {"collectionId": roles_col_id, "cascadeDelete": False,
                         "maxSelect": 1, "minSelect": None, "displayFields": None}},
            {"name": "activo", "type": "bool", "required": False, "options": {}},
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

ANALISTA = {"modelo_dimensional":["ver"],"dashboard":["ver"],"puntualidad":["ver","exportar"],
            "rutas":["ver","exportar"],"cancelaciones":["ver","exportar"],
            "reportes":["ver","exportar"],"predictivo":["ver","exportar"]}

VIEWER   = {"dashboard":["ver"],"puntualidad":["ver"],"rutas":["ver"],"cancelaciones":["ver"]}

CONFIG = [
    {"clave":"email_smtp_host",       "valor":"smtp.gmail.com","tipo":"string",  "modulo":"email",   "descripcion":"Servidor SMTP",              "editable":True, "sensible":False},
    {"clave":"email_smtp_port",       "valor":"587",           "tipo":"int",     "modulo":"email",   "descripcion":"Puerto SMTP",                "editable":True, "sensible":False},
    {"clave":"email_remitente",       "valor":"",              "tipo":"email",   "modulo":"email",   "descripcion":"Email remitente",            "editable":True, "sensible":False},
    {"clave":"email_password",        "valor":"",              "tipo":"password","modulo":"email",   "descripcion":"Contraseña SMTP",            "editable":True, "sensible":True},
    {"clave":"email_usar_tls",        "valor":"true",          "tipo":"bool",    "modulo":"email",   "descripcion":"Usar TLS",                   "editable":True, "sensible":False},
    {"clave":"email_alertas_activas", "valor":"false",         "tipo":"bool",    "modulo":"email",   "descripcion":"Activar alertas por email",  "editable":True, "sensible":False},
    {"clave":"email_destinatario",    "valor":"",              "tipo":"email",   "modulo":"email",   "descripcion":"Destinatario de alertas",    "editable":True, "sensible":False},
    {"clave":"alerta_otp_umbral_min", "valor":"0.80",          "tipo":"float",   "modulo":"alertas", "descripcion":"OTP mínimo aceptable (0-1)", "editable":True, "sensible":False},
    {"clave":"alerta_cancelacion_max","valor":"0.05",          "tipo":"float",   "modulo":"alertas", "descripcion":"Tasa máx cancelaciones",     "editable":True, "sensible":False},
    {"clave":"alerta_retraso_minutos","valor":"15",            "tipo":"int",     "modulo":"alertas", "descripcion":"Min. retraso para alerta",   "editable":True, "sensible":False},
    {"clave":"alerta_ruta_ineficiente","valor":"0.15",         "tipo":"float",   "modulo":"alertas", "descripcion":"% desviación ruta",          "editable":True, "sensible":False},
    {"clave":"pipeline_batch_size",   "valor":"5000",          "tipo":"int",     "modulo":"pipeline","descripcion":"Tamaño lote carga PocketBase","editable":True, "sensible":False},
    {"clave":"pipeline_max_workers",  "valor":"10",            "tipo":"int",     "modulo":"pipeline","descripcion":"Hilos concurrentes extract",  "editable":True, "sensible":False},
    {"clave":"pipeline_reintentos",   "valor":"3",             "tipo":"int",     "modulo":"pipeline","descripcion":"Reintentos por fallo",        "editable":True, "sensible":False},
]

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "═"*60)
    print("  AeroTrack Analytics — Setup PocketBase Admin v2")
    print("═"*60)

    print("\n[1/8] Autenticando...")
    auth()

    cols = existing_cols()

    # ── roles ──
    print("\n[2/8] Colección 'roles'...")
    create_col(schema_roles(), cols)
    role_ids = {}
    for r in ROLES:
        rid = upsert("roles", r, "nombre", r["nombre"])
        if rid: role_ids[r["nombre"]] = rid; log(f"Rol '{r['nombre']}'")

    # ── modulos ──
    print("\n[3/8] Colección 'modulos'...")
    create_col(schema_modulos(), cols)
    mod_ids = {}
    for m in MODULOS:
        mid = upsert("modulos", m, "clave", m["clave"])
        if mid: mod_ids[m["clave"]] = mid; log(f"Módulo '{m['clave']}'")

    # ── permisos ──
    print("\n[4/8] Colección 'permisos'...")
    create_col(schema_permisos(cols.get("modulos","")), cols)
    perm_ids = {}
    for clave, acciones in PERMISOS_DEF.items():
        mid = mod_ids.get(clave)
        if not mid: continue
        for accion in acciones:
            ex = records("permisos", f'modulo_id="{mid}"&&accion="{accion}"')
            if ex:
                perm_ids[(clave,accion)] = ex[0]["id"]
            else:
                r2 = S.post(f"{BASE}/api/collections/permisos/records",
                            json={"modulo_id":mid,"accion":accion,
                                  "descripcion":f"{accion} en {clave}"})
                if r2.status_code in (200,201):
                    perm_ids[(clave,accion)] = r2.json()["id"]
    log(f"{len(perm_ids)} permisos definidos")

    # ── roles_permisos ──
    print("\n[5/8] Colección 'roles_permisos'...")
    create_col(schema_roles_permisos(cols.get("roles",""), cols.get("permisos","")), cols)

    def asignar(nombre_rol, perms_dict):
        rid = role_ids.get(nombre_rol)
        if not rid: return
        n = 0
        for clave, acciones in perms_dict.items():
            for accion in acciones:
                pid = perm_ids.get((clave,accion))
                if not pid: continue
                ex = records("roles_permisos", f'rol_id="{rid}"&&permiso_id="{pid}"')
                if not ex:
                    S.post(f"{BASE}/api/collections/roles_permisos/records",
                           json={"rol_id":rid,"permiso_id":pid})
                    n += 1
        log(f"Rol '{nombre_rol}': {n} nuevos permisos asignados")

    asignar("administrador", PERMISOS_DEF)
    asignar("analista", ANALISTA)
    asignar("viewer", VIEWER)

    # ── configuracion_sistema ──
    print("\n[6/8] Colección 'configuracion_sistema'...")
    create_col(schema_config(), cols)
    n_cfg = 0
    for cfg in CONFIG:
        r3 = upsert("configuracion_sistema", cfg, "clave", cfg["clave"])
        if r3: n_cfg += 1
    log(f"{n_cfg} configuraciones verificadas")

    # ── app_users ──
    print("\n[7/8] Colección 'app_users'...")
    create_col(schema_app_users(cols.get("roles","")), cols)

    # ── usuario admin ──
    print("\n[8/8] Usuario administrador...")
    admin_rid = role_ids.get("administrador")
    ex_u = records("app_users", f'email="{PB_EMAIL}"')
    if ex_u:
        log(f"Usuario '{PB_EMAIL}' ya existe")
    else:
        ru = S.post(f"{BASE}/api/collections/app_users/records", json={
            "email": PB_EMAIL, "password": PB_PASSWORD,
            "passwordConfirm": PB_PASSWORD,
            "nombre": "Belinda Toaquiza",
            "rol_id": admin_rid, "activo": True, "emailVisibility": True,
        })
        if ru.status_code in (200,201): log(f"Usuario admin creado: {PB_EMAIL}")
        else: log(f"Error usuario: {ru.status_code} — {ru.text[:100]}", ok=False)

    print("\n" + "═"*60)
    print("  Setup completado ✓")
    print(f"  Roles: {len(role_ids)} | Módulos: {len(mod_ids)} | Permisos: {len(perm_ids)}")
    print(f"  Verifica en: {BASE}/_/")
    print("═"*60 + "\n")

if __name__ == "__main__":
    main()
