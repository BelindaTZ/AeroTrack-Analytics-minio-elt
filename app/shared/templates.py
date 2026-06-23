"""Instancia compartida de Jinja2Templates y registro de módulos del sidebar."""

from pathlib import Path
from fastapi.templating import Jinja2Templates
from jinja2 import FileSystemLoader

_BASE = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(_BASE / "shared" / "templates"))
templates.env.auto_reload = True  # recarga templates sin reiniciar el servidor
templates.env.loader = FileSystemLoader([
    str(_BASE / "shared" / "templates"),
    str(_BASE / "seguridad" / "templates"),
    str(_BASE / "pipeline_elt" / "templates"),
    str(_BASE / "modelo_dimensional" / "templates"),
    str(_BASE / "dashboard" / "templates"),
    str(_BASE / "puntualidad" / "templates"),
    str(_BASE / "rutas" / "templates"),
    str(_BASE / "cancelaciones" / "templates"),
    str(_BASE / "configuracion" / "templates"),
    str(_BASE / "auditoria" / "templates"),
    str(_BASE / "reportes" / "templates"),
    str(_BASE / "predictivo" / "templates"),
    str(_BASE / "asistente_ia" / "templates"),
    str(_BASE / "clientes" / "templates"),
    str(_BASE / "socios_api" / "templates"),
])

# Tablas del modelo dimensional con sus PKs e iconos
TABLAS: dict[str, dict] = {
    "fact_vuelo":               {"pk": "pk_vuelo",              "label": "Vuelos",           "icon": "bi-airplane"},
    "dim_tiempo":               {"pk": "pk_tiempo",             "label": "Tiempo",           "icon": "bi-calendar3"},
    "dim_aerolinea":            {"pk": "pk_aerolinea",          "label": "Aerolíneas",       "icon": "bi-building"},
    "dim_aeropuerto":           {"pk": "pk_aeropuerto",         "label": "Aeropuertos",      "icon": "bi-geo-alt"},
    "dim_avion":                {"pk": "pk_avion",              "label": "Aviones",          "icon": "bi-send"},
    "dim_retraso_causa":        {"pk": "pk_retraso_causa",      "label": "Causas Retraso",   "icon": "bi-exclamation-triangle"},
    "dim_cancelacion":          {"pk": "pk_cancelacion",        "label": "Cancelaciones",    "icon": "bi-x-circle"},
    "dim_distancia":            {"pk": "pk_distancia",          "label": "Distancia",        "icon": "bi-rulers"},
    "dim_desvio":               {"pk": "pk_desvio",             "label": "Desvíos",          "icon": "bi-signpost-split"},
    "dim_horario":              {"pk": "pk_horario",            "label": "Horarios",         "icon": "bi-clock"},
    "dim_clasificacion_retraso":{"pk": "pk_clasificacion",      "label": "Clasif. Retraso",  "icon": "bi-bar-chart-steps"},
    "dim_ruta":                 {"pk": "pk_ruta",               "label": "Rutas",            "icon": "bi-map"},
}

PAGE_SIZE = 50

# Módulos visibles en el sidebar con su entrega y URL
MODULOS_SIDEBAR = [
    {"clave": "pipeline_elt",       "label": "Pipeline ELT",       "icon": "bi-gear-fill",          "url": "/pipeline",         "entrega": 1},
    {"clave": "modelo_dimensional", "label": "Modelo Dimensional", "icon": "bi-database-fill",      "url": "/modelo",           "entrega": 1},
    {"clave": "dashboard",          "label": "Dashboard",          "icon": "bi-bar-chart-fill",     "url": "/dashboard",        "entrega": 2},
    {"clave": "puntualidad",        "label": "Puntualidad OTP",    "icon": "bi-clock-history",      "url": "/puntualidad",      "entrega": 2},
    {"clave": "rutas",              "label": "Rutas",              "icon": "bi-map-fill",           "url": "/rutas",            "entrega": 2},
    {"clave": "cancelaciones",      "label": "Cancelaciones",      "icon": "bi-x-circle-fill",      "url": "/cancelaciones",    "entrega": 2},
    {"clave": "reportes",           "label": "Reportes",           "icon": "bi-file-earmark-pdf",   "url": "/reportes",         "entrega": 2},
    {"clave": "predictivo",         "label": "Predictivo IA",      "icon": "bi-graph-up-arrow",     "url": "/predictivo",       "entrega": 3},
    {"clave": "asistente_ia",       "label": "Asistente IA",       "icon": "bi-cpu-fill",           "url": "/ia",               "entrega": 3},
    {"clave": "clientes",      "label": "Clientes",      "icon": "bi-people-fill",        "url": "/clientes",       "entrega": 4},
    {"clave": "socios_api",    "label": "Socios API",    "icon": "bi-link-45deg",         "url": "/socios",         "entrega": 4},
]

# Menú de administración (requiere permiso seguridad.ver)
MODULOS_ADMIN = [
    {"label": "Usuarios",      "icon": "bi-people-fill",     "url": "/auth/usuarios"},
    {"label": "Roles",         "icon": "bi-shield-lock-fill","url": "/auth/roles"},
    {"label": "Permisos",      "icon": "bi-key-fill",        "url": "/auth/roles/matriz"},
    {"label": "Configuración", "icon": "bi-sliders",         "url": "/configuracion"},
    {"label": "Auditoría",     "icon": "bi-journal-text",    "url": "/auditoria"},
]
