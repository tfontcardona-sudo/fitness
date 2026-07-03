"""Dependencias compartidas de los routers."""


from fastapi import Depends, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Client, User
from app.security import decode_access_token, portal_token_client_id

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Coach autenticado vía JWT Bearer (app de coaches)."""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Autenticación requerida")
    username = decode_access_token(credentials.credentials)
    if not username:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido o expirado")
    user = db.scalar(select(User).where(User.username == username))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no encontrado")
    return user


def get_client_by_token(
    token: str = Path(min_length=10, max_length=255),
    db: Session = Depends(get_db),
) -> Client:
    """Cliente del portal: firma válida + coincidencia exacta en DB (revocable).

    404 genérico en cualquier fallo: no filtra si un token existió o fue revocado.
    """
    client_id = portal_token_client_id(token)
    if client_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontrado")
    client = db.get(Client, client_id)
    if client is None or client.portal_token != token:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontrado")
    return client
