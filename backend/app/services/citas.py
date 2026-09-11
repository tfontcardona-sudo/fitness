"""La CITA de la revisión: videollamada o visita al centro, en un solo sitio.

DQR revisa por videollamada (asesoría online). Professional revisa EN EL CENTRO
(su cliente entrena allí). El ciclo es el mismo —el cliente propone día y hora,
el coach acepta o cambia, se avisa, se recuerda y se cierra—; lo que cambia es
dónde se ve y qué se le manda al cliente: un enlace de Meet o una dirección.

Dos preguntas que NO hay que confundir, mismo criterio que con la marca:

· `modo_de_marca(db, client)` — qué hace HOY el negocio de ese cliente. Es lo
  que se sella al crear la cita.
· `modo_de_cita(vc)` — lo acordado en ESA cita. Manda sobre todo lo demás: una
  visita confirmada sigue siendo una visita aunque el centro cambie de forma de
  trabajar mañana.

⚠️ Una cita PRESENCIAL no toca Google. Ese es el punto: un gimnasio no tiene por
qué tener una cuenta conectada, y exigirla dejaba el ciclo atascado para
siempre en «pendiente de agendar».
"""
from __future__ import annotations

from sqlalchemy.orm import Session

PRESENCIAL = "presencial"
VIDEOLLAMADA = "videollamada"


def _limpio(valor) -> str:
    v = str(valor or "").strip().lower()
    return PRESENCIAL if v == PRESENCIAL else VIDEOLLAMADA


def modo_de_marca(db: Session, client=None) -> str:
    """El modo de cita del negocio de este cliente (su marca SELLADA)."""
    from app.services.branding import fila_de_marca

    cfg = fila_de_marca(db, client)
    return _limpio(getattr(cfg, "cita_modo", None))


def modo_de_cita(vc) -> str:
    """El modo acordado en esta cita. NULL = videollamada (lo de siempre)."""
    return _limpio(getattr(vc, "modo", None))


def es_presencial(vc) -> bool:
    return modo_de_cita(vc) == PRESENCIAL


def lugar(db: Session, client=None) -> str | None:
    """Dónde es la visita: la dirección del centro de su marca. None si la marca
    no tiene local (y entonces la cita no debería ser presencial)."""
    from app.services.branding import fila_de_marca

    cfg = fila_de_marca(db, client)
    direccion = (getattr(cfg, "contact_address", None) or "").strip()
    return direccion or None


def etiqueta(modo: str, *, mayuscula: bool = False) -> str:
    """Cómo se llama esto delante del cliente."""
    txt = "visita en el centro" if _limpio(modo) == PRESENCIAL else "videollamada"
    return txt[0].upper() + txt[1:] if mayuscula else txt
