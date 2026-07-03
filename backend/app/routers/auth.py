"""Autenticación de coaches (JWT)."""


from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas.entities import LoginIn, TokenOut
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=TokenOut)
@limiter.limit("5/minute")
def login(request: Request, body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    """Login de los admins seedados desde el .env. 5 intentos/minuto por IP."""
    user = db.scalar(select(User).where(User.username == body.username))
    if not user or not verify_password(body.password, user.password_hash):
        # Mensaje único: no revela si el usuario existe
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales incorrectas")
    return TokenOut(access_token=create_access_token(user.username))


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return {"id": user.id, "username": user.username}
