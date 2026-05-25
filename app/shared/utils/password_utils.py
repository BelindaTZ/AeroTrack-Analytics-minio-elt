"""Utilidades de contraseña reutilizables."""

import random
import string
import unicodedata


def generar_contrasena_temporal(nombre: str) -> str:
    """Genera contraseña temporal: 4 letras del nombre + 4 dígitos + 1 mayúscula + '!'.
    Ejemplo: nombre='Belinda' → 'beli4829R!'
    """
    # Normalizar: minúsculas, sin tildes, solo letras ASCII
    nfkd = unicodedata.normalize("NFKD", nombre.strip().lower())
    ascii_nombre = "".join(c for c in nfkd if not unicodedata.combining(c) and c.isalpha())
    prefijo = (ascii_nombre + "xxxx")[:4]
    digitos = "".join(random.choices(string.digits, k=4))
    mayuscula = random.choice(string.ascii_uppercase)
    return f"{prefijo}{digitos}{mayuscula}!"
