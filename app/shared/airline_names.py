"""Diccionario IATA → nombre completo de aerolíneas del dataset BTS/DOT."""

_NAMES: dict[str, str] = {
    "AA": "American Airlines",
    "DL": "Delta Air Lines",
    "UA": "United Airlines",
    "WN": "Southwest Airlines",
    "B6": "JetBlue Airways",
    "AS": "Alaska Airlines",
    "NK": "Spirit Airlines",
    "F9": "Frontier Airlines",
    "G4": "Allegiant Air",
    "HA": "Hawaiian Airlines",
    "SY": "Sun Country Airlines",
    "VX": "Virgin America",
    "OO": "SkyWest Airlines",
    "MQ": "Envoy Air",
    "YX": "Republic Airways",
    "9E": "Endeavor Air",
    "OH": "PSA Airlines",
    "EV": "ExpressJet Airlines",
    "QX": "Horizon Air",
    "YV": "Mesa Airlines",
    "G7": "GoJet Airlines",
    "ZW": "Air Wisconsin",
    "PT": "Piedmont Airlines",
    "CP": "Compass Airlines",
    "C5": "CommutAir",
    "KS": "Peninsula Airways",
    "EM": "Empire Airlines",
}


def airline_name(code: str) -> str:
    """Devuelve el nombre completo; si no existe, retorna el código."""
    return _NAMES.get(str(code), str(code))
