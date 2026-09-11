"""EL LOGO DE FÁBRICA de cada negocio, si el dueño aún no ha subido el suyo.

Un logo NO se inventa: cuando el dueño manda un archivo de verdad, va aquí,
bajo `assets/brand/`, con el slug de SU marca, y este módulo lo aplica solo al
arrancar — el mismo criterio que `media_legacy.py` para no pedirle al dueño
ni un clic que puede darse él (el logo de Professional venía de un mensaje
suyo con el archivo adjunto; sin este seed habría hecho falta que él mismo
entrara a Recursos → Marca → Logo a subirlo a mano).

NUNCA pisa un logo que el dueño ya subió (`logo_path` con algo dentro): esto
es solo el ARRANQUE de una marca nueva, no una plantilla que se reimponga
sola. En cuanto sube el suyo, este módulo deja de tocar esa marca para
siempre — es la fila, no el fichero, la que decide.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BrandConfig
from app.services.storage import save_brand_logo

log = logging.getLogger("app.media")

_ASSETS = Path(__file__).resolve().parent.parent / "assets" / "brand"

# slug de la marca → fichero de fábrica bajo `assets/brand/`.
_LOGOS_DE_FABRICA: dict[str, str] = {
    "professional-fitness": "logo-professional-fitness.png",
}


def aplicar_logos_de_fabrica(db: Session) -> int:
    """Aplica el logo de fábrica a toda marca que aún no tenga uno subido.

    Devuelve cuántas marcas se han sellado (0 en el caso normal: ya está
    aplicado, o el dueño ya subió el suyo)."""
    aplicados = 0
    try:
        marcas = list(db.scalars(select(BrandConfig)))
    except Exception:  # noqa: BLE001 — sin tabla todavía (base recién creada)
        return 0
    for marca in marcas:
        if getattr(marca, "logo_path", None):
            continue  # ya tiene uno — subido por el dueño o aplicado antes
        fichero = _LOGOS_DE_FABRICA.get(getattr(marca, "slug", None) or "")
        if not fichero:
            continue
        origen = _ASSETS / fichero
        if not origen.is_file():
            continue
        try:
            raw = origen.read_bytes()
            marca.logo_path = save_brand_logo(raw, fichero, marca.slug)
            db.commit()
            aplicados += 1
            log.info("Logo de fábrica aplicado a %s", marca.slug)
        except Exception:  # noqa: BLE001 — un fallo aquí no puede tumbar el arranque
            db.rollback()
            log.warning("No se pudo aplicar el logo de fábrica de %s", marca.slug)
    return aplicados
