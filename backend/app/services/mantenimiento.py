"""EL INTERRUPTOR GLOBAL: pausar todo el acceso público de un toque.

Una sola fila (`SystemState`, mismo patrón que `AiCreditState`) con un booleano
y un mensaje. Cuando está activo, el acceso PÚBLICO —portales de cliente
(`/api/p/*`), pagos y compras (`/api/pay/*`), y la landing/catálogo/registro
(`/api/public/*`: `/dq`, `/planes`, `/oferta`)— responde 503 en vez de
ejecutar nada (ver los `dependencies=[Depends(no_en_mantenimiento)]` en
`main.py` y `stripe_router.py`). El panel del coach y el webhook de Stripe
NUNCA pasan por aquí: el coach tiene que poder trabajar y volver a activarlo,
y los cobros/bajas ya en marcha no pueden perderse por estar en pausa.

Caché en memoria de unos segundos (mismo patrón que `branding.py`): se
consulta en CADA petición pública, así que sin caché cada `GET` del portal
(que ya se refresca solo) sería una consulta extra a la base de datos para
leer un booleano que casi nunca cambia.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SystemState

MENSAJE_POR_DEFECTO = (
    "El sistema no está disponible en este momento. Vuelve a intentarlo más tarde."
)

_TTL_S = 5.0
_cache: dict = {"at": 0.0, "activo": False, "mensaje": MENSAJE_POR_DEFECTO}


def _fila(db: Session) -> SystemState:
    """Fila única get-or-create (mismo patrón que `AiCreditState`/`BrandConfig`)."""
    estado = db.scalar(select(SystemState).limit(1))
    if not estado:
        estado = SystemState(maintenance_enabled=False)
        db.add(estado)
        db.commit()
        db.refresh(estado)
    return estado


def invalidar() -> None:
    """Fuerza la próxima lectura a ir a la base — la llama `activar`/`desactivar`
    para que el cambio se note YA, no al cabo de `_TTL_S` segundos."""
    _cache["at"] = 0.0


def estado(db: Session) -> dict:
    """`{"activo": bool, "mensaje": str}` — lo que mira cada petición pública."""
    if time.monotonic() - _cache["at"] < _TTL_S:
        return {"activo": _cache["activo"], "mensaje": _cache["mensaje"]}
    fila = _fila(db)
    mensaje = fila.maintenance_message or MENSAJE_POR_DEFECTO
    _cache.update({"at": time.monotonic(), "activo": bool(fila.maintenance_enabled), "mensaje": mensaje})
    return {"activo": _cache["activo"], "mensaje": mensaje}


def activar(db: Session, mensaje: str | None = None) -> SystemState:
    fila = _fila(db)
    fila.maintenance_enabled = True
    fila.maintenance_message = (mensaje or "").strip() or None
    fila.maintenance_enabled_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(fila)
    invalidar()
    return fila


def desactivar(db: Session) -> SystemState:
    fila = _fila(db)
    fila.maintenance_enabled = False
    db.commit()
    db.refresh(fila)
    invalidar()
    return fila
