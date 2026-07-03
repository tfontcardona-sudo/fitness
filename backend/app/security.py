"""Seguridad: contraseñas (bcrypt), JWT de coaches y tokens de portal.

Diseño del token de portal (G.4 — "firmado, revocable/regenerable"):
- token = URLSafeSerializer(PORTAL_TOKEN_SECRET).dumps({"c": client_id, "n": nonce})
- La firma garantiza integridad (no se pueden fabricar tokens).
- La revocación se consigue comparando contra `clients.portal_token` en DB:
  regenerar = guardar un token nuevo → el anterior deja de coincidir y muere.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from itsdangerous import BadSignature, URLSafeSerializer

from app.config import settings

JWT_ALGORITHM = "HS256"

_portal_serializer = URLSafeSerializer(settings.portal_token_secret, salt="portal")


# ----------------------------------------------------------- contraseñas ----
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# ------------------------------------------------------------ JWT coaches ----
def create_access_token(username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Devuelve el username o None si el token es inválido/expirado."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
        return str(payload["sub"])
    except (jwt.PyJWTError, KeyError):
        return None


# -------------------------------------------------------- tokens de portal ----
def new_portal_token(client_id: int) -> str:
    return _portal_serializer.dumps({"c": client_id, "n": secrets.token_hex(8)})


def portal_token_client_id(token: str) -> int | None:
    """Verifica la FIRMA y devuelve el client_id embebido (o None).

    La validez final exige además que el token coincida con el guardado en DB
    (ver deps.get_client_by_token) — así un token regenerado revoca el anterior.
    """
    try:
        data = _portal_serializer.loads(token)
        return int(data["c"])
    except (BadSignature, KeyError, TypeError, ValueError):
        return None
