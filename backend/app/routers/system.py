"""EL INTERRUPTOR GLOBAL de mantenimiento — ver `services/mantenimiento.py`.

GET da el estado actual (para pintar el aviso en Recursos); POST lo cambia.
Las rutas PÚBLICAS (portal, pagos, landing) NO pasan por aquí: ellas llevan su
propia `dependencies=[Depends(no_en_mantenimiento)]` que responde 503 sola.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.services import mantenimiento

router = APIRouter(prefix="/api/system", tags=["system"], dependencies=[Depends(get_current_user)])


class MantenimientoOut(BaseModel):
    activo: bool
    mensaje: str


class MantenimientoIn(BaseModel):
    activo: bool
    mensaje: str | None = Field(default=None, max_length=300)


@router.get("/mantenimiento", response_model=MantenimientoOut)
def leer_mantenimiento(db: Session = Depends(get_db)) -> MantenimientoOut:
    return MantenimientoOut(**mantenimiento.estado(db))


@router.post("/mantenimiento", response_model=MantenimientoOut)
def cambiar_mantenimiento(body: MantenimientoIn, db: Session = Depends(get_db)) -> MantenimientoOut:
    if body.activo:
        mantenimiento.activar(db, body.mensaje)
    else:
        mantenimiento.desactivar(db)
    return MantenimientoOut(**mantenimiento.estado(db))
