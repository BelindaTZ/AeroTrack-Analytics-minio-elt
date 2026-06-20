"""Módulo de análisis de rutas por eficiencia (CU-22, CU-23)."""

import math
import time
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.shared.analytics import load_agg, load_enriched_fact, get_aerolinas, get_years
from app.shared.clients import pb_client
from app.shared.deps import render, require_permission
from app.utils.ia_narrativa import generar_narrativa

router = APIRouter()
_perm_ver = require_permission("rutas", "ver")

# lat, lon de aeropuertos IATA USA más comunes en el dataset DOT/BTS
_AIRPORTS: dict[str, tuple[float, float]] = {
    "ATL": (33.6407, -84.4277), "LAX": (33.9425, -118.4081), "ORD": (41.9742, -87.9073),
    "DFW": (32.8998, -97.0403), "DEN": (39.8561, -104.6737), "JFK": (40.6413, -73.7781),
    "SFO": (37.6213, -122.379),  "SEA": (47.4502, -122.3088), "LAS": (36.0840, -115.1537),
    "MCO": (28.4312, -81.3081),  "MIA": (25.7959, -80.2870),  "CLT": (35.2140, -80.9431),
    "EWR": (40.6895, -74.1745),  "PHX": (33.4373, -112.0078), "IAH": (29.9902, -95.3368),
    "BOS": (42.3656, -71.0096),  "MSP": (44.8848, -93.2223),  "DTW": (42.2162, -83.3554),
    "FLL": (26.0742, -80.1506),  "PHL": (39.8744, -75.2424),  "LGA": (40.7771, -73.8740),
    "BWI": (39.1754, -76.6683),  "DCA": (38.8512, -77.0402),  "IAD": (38.9531, -77.4565),
    "MDW": (41.7868, -87.7522),  "SLC": (40.7899, -111.9791), "SAN": (32.7338, -117.1933),
    "TPA": (27.9772, -82.5311),  "HNL": (21.3245, -157.9251), "AUS": (30.1975, -97.6664),
    "BNA": (36.1245, -86.6782),  "STL": (38.7487, -90.3700),  "OAK": (37.7213, -122.2208),
    "RDU": (35.8776, -78.7875),  "PDX": (45.5898, -122.5951), "SMF": (38.6954, -121.5908),
    "MCI": (39.2976, -94.7139),  "CLE": (41.4117, -81.8498),  "MKE": (42.9472, -87.8966),
    "HOU": (29.6454, -95.2789),  "PIT": (40.4915, -80.2329),  "CVG": (39.0488, -84.6678),
    "CMH": (39.9980, -82.8919),  "IND": (39.7173, -86.2944),  "SJC": (37.3626, -121.929),
    "ABQ": (35.0402, -106.609),  "OGG": (20.8986, -156.4305), "SAT": (29.5337, -98.4698),
    "RSW": (26.5362, -81.7552),  "JAX": (30.4941, -81.6879),  "BUF": (42.9405, -78.7322),
    "MEM": (35.0424, -89.9767),  "MSY": (29.9934, -90.2580),  "SNA": (33.6757, -117.8682),
    "BUR": (34.2007, -118.3585), "ONT": (34.0560, -117.6012), "BOI": (43.5644, -116.2228),
    "GEG": (47.6199, -117.5338), "RNO": (39.4991, -119.7681), "SDF": (38.1744, -85.7360),
    "GSO": (36.0978, -79.9373),  "TUL": (36.1984, -95.8881),  "OKC": (35.3931, -97.6007),
    "ELP": (31.8072, -106.3779), "FAT": (36.7762, -119.7182), "LIT": (34.7294, -92.2243),
    "MHT": (42.9326, -71.4357),  "ORF": (36.8976, -76.0132),  "RIC": (37.5052, -77.3197),
    "ANC": (61.1744, -149.9964), "FAI": (64.8151, -147.8562), "JNU": (58.3549, -134.5763),
    "KOA": (19.7388, -156.0456), "LIH": (21.9760, -159.3390), "ITO": (19.7204, -155.0485),
    "DSM": (41.5340, -93.6631),  "GRR": (42.8808, -85.5228),  "FSD": (43.5820, -96.7419),
    "BZN": (45.7774, -111.1533), "JAC": (43.6073, -110.7377), "MSO": (46.9163, -114.0906),
    "ROC": (43.1189, -77.6724),  "SYR": (43.1112, -76.1063),  "BHM": (33.5629, -86.7535),
    "CHA": (35.0353, -85.2038),  "TYS": (35.8110, -83.9940),  "HSV": (34.6372, -86.7751),
    "MOB": (30.6913, -88.2428),  "PNS": (30.4734, -87.1866),  "GPT": (30.4073, -89.0701),
    "BTR": (30.5332, -91.1496),  "SHV": (32.4466, -93.8256),  "JAN": (32.3112, -90.0759),
    "XNA": (36.2819, -94.3068),  "CHS": (32.8986, -80.0405),  "SAV": (32.1276, -81.2021),
    "AVL": (35.4362, -82.5418),  "MYR": (33.6797, -78.9283),  "CAE": (33.9389, -81.1195),
    "SRQ": (27.3953, -82.5544),  "TLH": (30.3965, -84.3503),  "GNV": (29.6901, -82.2717),
    "DAB": (29.1799, -81.0581),  "MLB": (28.1028, -80.6453),  "PIE": (27.9102, -82.6874),
    "PBI": (26.6832, -80.0956),  "EYW": (24.5561, -81.7596),  "MDT": (40.1935, -76.7634),
    "ABE": (40.6521, -75.4408),  "AVP": (41.3385, -75.7234),  "PHF": (37.1319, -76.4930),
    "CHO": (38.1386, -78.4529),  "ROA": (37.3255, -79.9754),  "GSP": (34.8957, -82.2189),
    "AGS": (33.3699, -81.9645),  "RDM": (44.2541, -121.150),  "EUG": (44.1246, -123.2119),
    "MFR": (42.3742, -122.8735), "SBA": (34.4262, -119.8403), "SBP": (35.2368, -120.6424),
    "MRY": (36.5870, -121.8429), "LGB": (33.8177, -118.1516), "TWF": (42.4818, -114.4877),
    "LWS": (46.3745, -117.0153), "PIH": (42.9098, -112.5958), "IDA": (43.5146, -112.0702),
    "CPR": (42.9080, -106.4644), "RAP": (44.0453, -103.0574), "BIS": (46.7727, -100.7466),
    "FAR": (46.9207, -96.8158),  "GFK": (47.9493, -97.1762),  "MOT": (48.2594, -101.2797),
    "MSN": (43.1399, -89.3375),  "GRB": (44.4851, -88.1297),  "ATW": (44.2571, -88.5191),
    "RST": (43.9088, -92.5001),  "DLH": (46.8421, -92.1936),  "BJI": (47.5077, -94.9328),
    "EVV": (38.0369, -87.5324),  "FWA": (40.9785, -85.1951),  "SBN": (41.7087, -86.3173),
    "CMI": (40.0399, -88.2782),  "PIA": (40.6643, -89.6930),  "BMI": (40.4771, -88.9159),
    "CID": (41.8847, -91.7108),  "OMA": (41.3032, -95.8941),  "LNK": (40.8510, -96.7592),
    "SUX": (42.4026, -96.3844),  "SGF": (37.2457, -93.3886),  "JLN": (37.1518, -94.4983),
    "ICT": (37.6499, -97.4331),  "FSM": (35.3361, -94.3674),  "TXK": (33.4537, -93.9910),
    "MLU": (32.5109, -92.0376),  "LFT": (30.2053, -91.9876),  "LCH": (30.1261, -93.2233),
    "CRP": (27.7704, -97.5011),  "MFE": (26.1758, -98.2386),  "LRD": (27.5438, -99.4616),
    "MAF": (31.9425, -102.2019), "ABI": (32.4113, -99.6819),  "DAL": (32.8471, -96.8517),
    "GGG": (32.3840, -94.7115),  "TYR": (32.3541, -95.4024),  "ACT": (31.6113, -97.2302),
    "AMA": (35.2194, -101.7059), "LBB": (33.6636, -101.8229), "SPS": (33.9888, -98.4919),
    "ROW": (33.3016, -104.5306), "TUS": (32.1161, -110.9410), "FLG": (35.1385, -111.6703),
    "YUM": (32.6566, -114.6060), "ELY": (39.2997, -114.8421), "BDL": (41.9389, -72.6831),
    "HPN": (41.0670, -73.7076),  "ALB": (42.7483, -73.8017),  "SWF": (41.5041, -74.1048),
    "ERI": (42.0831, -80.1739),  "TOL": (41.5868, -83.8078),  "CAK": (40.9161, -81.4422),
    "DAY": (39.9024, -84.2194),  "CKB": (39.2966, -80.2280),  "CRW": (38.3731, -81.5932),
    "TRI": (36.4752, -82.4074),  "PVD": (41.7268, -71.4283),  "BGR": (44.8074, -68.8281),
    "PWM": (43.6462, -70.3094),  "BTV": (44.4720, -73.1533),  "MHK": (39.1410, -96.6708),
    "HRL": (26.2285, -97.6544),  "SAF": (35.6171, -106.0888), "FLO": (34.1854, -79.7239),
    "ILM": (34.2706, -77.9026),  "OAJ": (34.8292, -77.6121),  "DHN": (31.3213, -85.4496),
    "MGM": (32.3006, -86.3940),  "VLD": (30.7825, -83.2767),  "MCN": (32.6928, -83.6492),
    "SBY": (38.3405, -75.5103),  "LYH": (37.3267, -79.2004),  "HTS": (38.3667, -82.5578),
    "PGD": (26.9200, -81.9905),  "ECP": (30.3571, -85.7954),  "VPS": (30.4833, -86.5254),
    "MEI": (32.3326, -88.7515),  "GRK": (31.0672, -97.8287),  "SJT": (31.3577, -100.4963),
    "BPT": (30.0706, -94.0207),  "CLL": (30.5886, -96.3636),  "VCT": (28.8526, -97.0099),
    "HIB": (47.3866, -92.8390),  "INL": (48.5662, -93.4031),  "BRD": (46.3983, -94.1381),
    "AXN": (45.8663, -95.3947),  "CWA": (44.7776, -89.6668),  "LSE": (43.8789, -91.2567),
    "MBS": (43.5329, -84.0799),  "LAN": (42.7787, -84.5874),  "FNT": (42.9658, -83.7436),
    "AZO": (42.2350, -85.5522),  "IMT": (45.8181, -88.1145),  "MKG": (43.1696, -86.2382),
    "TVC": (44.7414, -85.5822),  "ESC": (45.7227, -87.0936),  "MQT": (46.3536, -87.5954),
    "PLN": (45.5708, -84.7967),  "CIU": (46.2508, -84.4728),  "ISN": (48.1779, -103.6419),
    "DIK": (46.7974, -102.8019), "GCC": (44.3489, -105.5396), "SHR": (44.7692, -106.9802),
    "RKS": (41.5942, -109.0658), "CYS": (41.1558, -104.8119), "LAR": (41.3121, -105.675),
    "CDC": (37.7010, -113.0987), "SGU": (37.0363, -113.5103), "VEL": (40.4408, -109.5099),
    "BKG": (36.6819, -93.2003),  "XWA": (48.2594, -101.2797), "DBQ": (42.4020, -90.7095),
    "ALO": (42.5571, -92.4003),  "COU": (38.8181, -92.2196),  "SWO": (36.1771, -97.0860),
    "LAW": (34.5677, -98.4166),  "MLC": (34.8824, -95.7833),  "HHH": (32.2244, -80.6975),
    "SSI": (31.1515, -81.3913),  "ABY": (31.5355, -84.1945),  "CSG": (32.5164, -84.9389),
    "GTF": (47.4820, -111.3707), "HLN": (46.6068, -111.9833), "BIL": (45.8077, -108.5428),
    "CDV": (60.4919, -145.4778), "SIT": (57.0471, -135.3615), "KTN": (55.3556, -131.7137),
    "BET": (60.7798, -161.8380), "OME": (64.5122, -165.4451), "OTZ": (66.8847, -162.5985),
    "ADQ": (57.7500, -152.4938), "DLG": (59.0445, -158.5067), "SCC": (70.1947, -148.4651),
}

_umbral_cache: dict = {"data": None, "expires": 0.0}
_UMBRAL_TTL = 60

_page_cache: dict = {}
_PAGE_TTL = 300


def _get_umbral_ruta() -> float:
    global _umbral_cache
    if _umbral_cache["data"] is not None and time.time() < _umbral_cache["expires"]:
        return _umbral_cache["data"]
    rows = pb_client.list_records("configuracion_sistema", filter='clave="alerta_ruta_ineficiente"')
    result = 0.15
    if rows:
        try:
            result = float(rows[0]["valor"])
        except (ValueError, KeyError):
            pass
    _umbral_cache = {"data": result, "expires": time.time() + _UMBRAL_TTL}
    return result


def invalidar_cache_umbral_ruta() -> None:
    global _umbral_cache
    _umbral_cache = {"data": None, "expires": 0.0}
    _page_cache.clear()


def _safe(v: Any) -> Any:
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return 0.0
    return v


def _mapa_rutas(rows: list[dict]) -> str:
    """Genera figura Plotly geo con arcos entre aeropuertos, coloreados por eficiencia."""
    if not rows:
        return "{}"

    lats_ok: list = []
    lons_ok: list = []
    txt_ok:  list = []
    lats_bad: list = []
    lons_bad: list = []
    txt_bad:  list = []
    ap_seen: dict[str, tuple[float, float]] = {}

    for r in rows:
        orig = str(r.get("OriginCode") or r.get("origin") or "")
        dest = str(r.get("DestCode")   or r.get("dest")   or "")
        if orig not in _AIRPORTS or dest not in _AIRPORTS:
            continue
        lat0, lon0 = _AIRPORTS[orig]
        lat1, lon1 = _AIRPORTS[dest]
        ap_seen[orig] = (lat0, lon0)
        ap_seen[dest] = (lat1, lon1)
        hover = (
            f"<b>{r['ruta']}</b><br>"
            f"Eficiencia: {r['eficiencia_media']:.3f}<br>"
            f"Retraso prom.: {r['retraso_prom']:.1f} min"
        )
        if r["ineficiente"]:
            lats_bad += [lat0, lat1, None]
            lons_bad += [lon0, lon1, None]
            txt_bad  += [hover, hover, None]
        else:
            lats_ok += [lat0, lat1, None]
            lons_ok += [lon0, lon1, None]
            txt_ok  += [hover, hover, None]

    if not ap_seen:
        return "{}"

    traces: list = []
    if lats_ok:
        traces.append(go.Scattergeo(
            lat=lats_ok, lon=lons_ok, mode="lines",
            line=dict(width=0.9, color="rgba(16,185,129,0.45)"),
            hoverinfo="text", text=txt_ok,
            name="Eficiente", showlegend=True,
        ))
    if lats_bad:
        traces.append(go.Scattergeo(
            lat=lats_bad, lon=lons_bad, mode="lines",
            line=dict(width=1.4, color="rgba(239,68,68,0.55)"),
            hoverinfo="text", text=txt_bad,
            name="Ineficiente", showlegend=True,
        ))
    # Marcadores de aeropuertos
    traces.append(go.Scattergeo(
        lat=[c[0] for c in ap_seen.values()],
        lon=[c[1] for c in ap_seen.values()],
        mode="markers",
        marker=dict(size=3.5, color="#94a3b8", opacity=0.75),
        hoverinfo="text",
        hovertext=list(ap_seen.keys()),
        name="Aeropuertos", showlegend=False,
    ))

    fig = go.Figure(data=traces)
    fig.update_geos(
        scope="usa",
        showland=True,       landcolor="rgba(22,27,40,1)",
        showocean=True,      oceancolor="rgba(10,13,20,1)",
        showlakes=True,      lakecolor="rgba(10,13,20,1)",
        showcoastlines=True, coastlinecolor="rgba(100,116,139,0.35)",
        showsubunits=True,   subunitcolor="rgba(100,116,139,0.12)",
        showcountries=True,  countrycolor="rgba(100,116,139,0.3)",
        bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        height=400,
        legend=dict(
            orientation="h", yanchor="bottom", y=0.02,
            xanchor="right", x=0.98,
            font=dict(color="#94a3b8", size=11),
            bgcolor="rgba(15,17,23,0.65)",
            bordercolor="rgba(100,116,139,0.2)", borderwidth=1,
        ),
        font=dict(family="Inter, sans-serif", color="#94a3b8"),
    )
    return fig.to_json()


def _calcular_ranking_agg(df_rutas: pd.DataFrame, umbral: float) -> list[dict]:
    """Ranking de rutas por eficiencia desde agg_rutas_eficiencia."""
    if df_rutas.empty or "origin" not in df_rutas.columns:
        return []

    # Re-agrupa por ruta (sum sobre carriers si hay filtro de aerolínea, avg ponderado si no)
    df = df_rutas.copy()
    df["sum_real"] = df["tiempo_real_avg"] * df["total_vuelos"]
    df["sum_prog"] = df["tiempo_prog_avg"] * df["total_vuelos"]
    df["sum_at"]   = df.get("vuelos_a_tiempo", pd.Series([0] * len(df), index=df.index)) * 1

    grp = df.groupby(["origin", "dest"]).agg(
        total=("total_vuelos", "sum"),
        sum_real=("sum_real", "sum"),
        sum_prog=("sum_prog", "sum"),
        retraso_prom=("retraso_prom", "mean"),
    ).reset_index()
    grp = grp[grp["total"] >= 30].copy()
    grp["eficiencia_media"] = (grp["sum_real"] / grp["sum_prog"].replace(0, float("nan"))).fillna(1.0).round(4)
    grp["ineficiente"] = grp["eficiencia_media"] > (1 + umbral)
    grp["ruta"] = grp["origin"].astype(str) + "-" + grp["dest"].astype(str)
    grp["OriginCode"] = grp["origin"]
    grp["DestCode"]   = grp["dest"]
    grp["origen_ciudad"] = grp["origin"]
    grp["dest_ciudad"]   = grp["dest"]
    grp["retraso_prom"] = grp["retraso_prom"].apply(_safe).round(1)

    return (
        grp.sort_values("eficiencia_media", ascending=True)
        .head(100)
        [["ruta", "OriginCode", "DestCode", "origen_ciudad", "dest_ciudad",
          "total", "eficiencia_media", "ineficiente", "retraso_prom"]]
        .to_dict("records")
    )


def _scatter_eficiencia_agg(df_rutas: pd.DataFrame) -> str:
    """Scatter tiempo real vs programado usando promedios de ruta (desde agg)."""
    if df_rutas.empty or "tiempo_real_avg" not in df_rutas.columns:
        return "{}"

    df = df_rutas.dropna(subset=["tiempo_real_avg", "tiempo_prog_avg"])
    if df.empty:
        return "{}"

    fig = go.Figure()
    fig.add_trace(go.Scattergl(
        x=df["tiempo_prog_avg"].tolist(),
        y=df["tiempo_real_avg"].tolist(),
        mode="markers",
        marker=dict(color="#3b82f6", size=5, opacity=0.6),
        hovertemplate="Prog: %{x:.0f} min<br>Real: %{y:.0f} min<extra></extra>",
        showlegend=False,
    ))
    max_val = float(max(df["tiempo_prog_avg"].max(), df["tiempo_real_avg"].max())) + 20
    fig.add_trace(go.Scatter(
        x=[0, max_val], y=[0, max_val],
        mode="lines", line=dict(color="rgba(255,255,255,0.2)", dash="dash", width=1),
        showlegend=False, hoverinfo="skip",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#94a3b8", size=12),
        margin=dict(l=50, r=20, t=20, b=50),
        height=300,
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="Tiempo programado prom. (min)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="Tiempo real prom. (min)"),
    )
    return fig.to_json()


def _detalle_ruta(df: pd.DataFrame, origen: str, dest: str) -> dict:
    """Detalle de una ruta específica desde fact enriquecido."""
    mask = (df["OriginCode"] == origen) & (df["DestCode"] == dest)
    sub = df[mask].copy()
    if len(sub) == 0:
        return {}

    vuelos_op = sub[sub["Cancelled"] == 0] if "Cancelled" in sub.columns else sub

    eficiencias = []
    if "ActualElapsedTime" in vuelos_op.columns and "CRSElapsedTime" in vuelos_op.columns:
        validos = vuelos_op[vuelos_op["CRSElapsedTime"] > 0]
        eficiencias = (validos["ActualElapsedTime"] / validos["CRSElapsedTime"]).dropna().tolist()

    retrasos = []
    if "ArrDelayMinutes" in vuelos_op.columns:
        retrasos = vuelos_op["ArrDelayMinutes"].dropna().clip(0).tolist()

    monthly_otp: dict = {"meses": [], "otp": []}
    if "Month" in vuelos_op.columns and "ArrDel15" in vuelos_op.columns:
        grp = vuelos_op.groupby("Month").agg(
            t=("pk_vuelo", "count"), ok=("ArrDel15", lambda x: (x == 0).sum())
        ).reset_index()
        grp["otp"] = (grp["ok"] / grp["t"] * 100).round(1)
        meses_names = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        monthly_otp = {
            "meses": [meses_names[int(m)-1] if 1<=int(m)<=12 else str(m) for m in grp["Month"].tolist()],
            "otp": grp["otp"].tolist(),
        }

    return {
        "total": len(sub),
        "total_operados": len(vuelos_op),
        "eficiencias": eficiencias[:2000],
        "retrasos": retrasos[:2000],
        "monthly_otp": monthly_otp,
    }


def _compute_page(filtros: dict) -> dict:
    """Computa ranking y scatter desde agregaciones; cacheado 5 min."""
    key = str(sorted(filtros.items()))
    entry = _page_cache.get(key)
    if entry and time.time() < entry["expires"]:
        return entry["data"]
    umbral = _get_umbral_ruta()
    df_rutas = load_agg("agg_rutas_eficiencia", filtros)
    rows = _calcular_ranking_agg(df_rutas, umbral)
    data = {
        "rows": rows,
        "grafico_scatter": _scatter_eficiencia_agg(df_rutas),
        "grafico_mapa": _mapa_rutas(rows),
        "umbral": umbral,
    }
    _page_cache[key] = {"data": data, "expires": time.time() + _PAGE_TTL}
    return data


@router.get("", response_class=HTMLResponse)
def ranking(request: Request, year: str = "", month: str = "", airline: str = ""):
    user = _perm_ver(request)
    error = None
    rows: list[dict] = []
    grafico_scatter = "{}"
    grafico_mapa = "{}"
    umbral = 0.15

    try:
        filtros = {k: v for k, v in {"year": year, "month": month, "airline": airline}.items() if v}
        data = _compute_page(filtros)
        rows = data["rows"]
        grafico_scatter = data["grafico_scatter"]
        grafico_mapa = data["grafico_mapa"]
        umbral = data["umbral"]

    except FileNotFoundError:
        error = "Los datos no están disponibles. Ejecute el pipeline ELT primero."
    except Exception as exc:
        error = f"Error al cargar datos: {exc}"

    return render(request, "rutas/ranking.html", {
        "rows": rows, "grafico_scatter": grafico_scatter,
        "grafico_mapa": grafico_mapa,
        "umbral": umbral,
        "error": error,
        "years": get_years(), "aerolinas": get_aerolinas(),
        "filtros": {"year": year, "month": month, "airline": airline},
    })


@router.get("/narrativa")
def narrativa_json(
    request: Request,
    year: str = "", month: str = "", airline: str = "",
    tipo: str = "", ruta_val: str = "",
):
    _perm_ver(request)
    try:
        filtros = {k: v for k, v in {"year": year, "month": month, "airline": airline}.items() if v}
        data = _compute_page(filtros)
        rows   = data["rows"]
        umbral = data["umbral"]

        total        = len(rows)
        ineficientes = [r for r in rows if r["ineficiente"]]
        pct_inef     = len(ineficientes) / total * 100 if total > 0 else 0
        ctx: dict = {}
        focus = ""

        if tipo == "ruta" and ruta_val:
            row = next((r for r in rows if r["ruta"] == ruta_val), None)
            if row:
                rank = next((i + 1 for i, r in enumerate(rows) if r["ruta"] == ruta_val), None)
                eficientes = [r for r in rows if not r["ineficiente"]]
                mejor_global = min((r for r in rows), key=lambda r: r["eficiencia_media"]) if rows else None
                ctx["Ruta"]                  = ruta_val
                ctx["Índice de eficiencia"]  = f"{row['eficiencia_media']:.3f}"
                ctx["Estado eficiencia"]     = (
                    f"INEFICIENTE (índice > {1 + umbral:.2f})" if row["ineficiente"]
                    else f"EFICIENTE (índice ≤ {1 + umbral:.2f})"
                )
                ctx["Retraso promedio"]      = f"{row['retraso_prom']:.1f} min"
                ctx["Vuelos operados"]       = f"{row['total']:,}"
                ctx["Posición en ranking"]   = f"#{rank} de {total}"
                ctx["% rutas ineficientes global"] = f"{pct_inef:.0f}%"
                if mejor_global and mejor_global["ruta"] != ruta_val:
                    ctx["Ruta más eficiente del período"] = (
                        f"{mejor_global['ruta']} (índice {mejor_global['eficiencia_media']:.3f})"
                    )
                focus = f"la eficiencia operacional de la ruta {ruta_val}"
        else:
            ctx["Rutas analizadas"]         = total
            ctx["Rutas ineficientes"]       = f"{len(ineficientes)} de {total} ({pct_inef:.0f}%)"
            ctx["Umbral de ineficiencia"]   = f"índice > {1 + umbral:.2f}"
            ctx["Estado eficiencia global"] = (
                "CUMPLE: mayoría eficiente" if pct_inef <= 30 else "NO CUMPLE: alta proporción ineficiente"
            )
            if ineficientes:
                peor = max(ineficientes, key=lambda r: r["eficiencia_media"])
                ctx["Ruta más ineficiente"] = (
                    f"{peor['ruta']} (índice {peor['eficiencia_media']:.3f}, "
                    f"retraso {peor['retraso_prom']:.1f} min)"
                )
            eficientes = [r for r in rows if not r["ineficiente"]]
            if eficientes:
                mejor = min(eficientes, key=lambda r: r["eficiencia_media"])
                ctx["Ruta más eficiente"] = f"{mejor['ruta']} (índice {mejor['eficiencia_media']:.3f})"
            if rows:
                ctx["Retraso promedio global"] = f"{sum(r['retraso_prom'] for r in rows)/len(rows):.1f} min"
            focus = "el porcentaje de rutas ineficientes y la ruta con peor eficiencia"

        return JSONResponse(generar_narrativa(ctx, "Eficiencia de Rutas", focus))
    except Exception:
        return JSONResponse({"texto": "", "proveedor": "", "desde_cache": False})


@router.get("/{ruta}/detalle", response_class=HTMLResponse)
def detalle_ruta(request: Request, ruta: str, year: str = ""):
    _perm_ver(request)
    error = None
    datos: dict = {}
    origen, dest = "", ""

    if "-" in ruta:
        partes = ruta.split("-", 1)
        origen, dest = partes[0], partes[1]

    try:
        filtros = {"year": year} if year else {}
        df = load_enriched_fact(filtros or None)
        if origen and dest:
            datos = _detalle_ruta(df, origen, dest)
    except Exception as exc:
        error = str(exc)

    return render(request, "rutas/detalle.html", {
        "ruta": ruta, "origen": origen, "dest": dest,
        "datos": datos, "error": error, "year": year, "years": get_years(),
    })
