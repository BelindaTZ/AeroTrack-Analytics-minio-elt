"""Generación y verificación de JWT."""

from datetime import datetime, timedelta, timezone

from jose import jwt

from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES


def crear_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verificar_token(token: str) -> dict:
    """Decodifica y verifica el JWT. Lanza JWTError si es inválido o expirado."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
