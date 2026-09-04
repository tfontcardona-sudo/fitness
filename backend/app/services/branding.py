"""LA MARCA: una sola puerta para saber bajo qué identidad se está trabajando.

El sistema puede llevar más de un negocio con la MISMA maquinaria: mismo motor
de cálculo, mismos guardarraíles, mismo ciclo quincenal, mismo portal. Lo que
cambia de una marca a otra es lo que se VE y lo que se VENDE — nombre, colores,
logo, nombres de los servicios, tarifas, precios de Stripe, la anamnesis y el
pie del documento del cliente.

Dos preguntas distintas, y confundirlas es el fallo que este módulo evita:

· `marca_activa()` — la del ESCAPARATE: el panel del coach, la landing, la
  página de planes y las altas nuevas. Es la que cambia el switch.
· `marca_de_cliente()` — la del cliente CONCRETO, sellada en su ficha el día
  que entró. Su portal, sus documentos, sus emails y sus precios de renovación
  salen de aquí. Que el coach cambie el switch no puede cambiarle la marca a
  quien ya está pagando.

Todo lo que sale de aquí son DATOS COPIADOS (`Marca`), no filas del ORM: una
fila cacheada entre sesiones se queda detached y revienta al leerla. Y hay
caché porque `label()` se llama en bucles por cliente; el switch la invalida.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BrandConfig

# Los valores de DQR, que son los que había clavados en el código antes de que
# la marca fuera un dato. Sirven de RESERVA para que nada se caiga si la base
# aún no tiene perfil (tests sin migrar, arranque a medias).
DEFAULTS = {
    "slug": "dqr",
    "name": "DQR Assessories",
    "service_labels": {"train": "DQR Train", "nutri": "DQR Nutri", "full": "DQR Full"},
    "service_taglines": {"train": "solo entrenamiento", "nutri": "solo nutrición",
                         "full": "nutrición + entrenamiento"},
    "prices": {
        "train": {"1m": 6900, "3m": 17700, "6m": 32400},
        "nutri": {"1m": 7900, "3m": 20100, "6m": 37200},
        "full": {"1m": 12900, "3m": 33000, "6m": 60000},
        "oferta": {"monthly_cents": 12000, "first_month_cents": 100, "charges": 3},
        "oferta2": {"monthly_cents": 12050, "charges": 2},
    },
    "stripe_prefix": "dqr",
    "page_title": "DQ · Asesorías Fitness",
    "app_name": "DQR · Assessories",
    "app_short_name": "DQR",
    "anamnesis_variant": "dq",
}

_TTL_S = 30.0
_lock = threading.Lock()
_cache: dict = {"at": 0.0, "por_id": {}, "activa": None}


@dataclass(frozen=True)
class Marca:
    """Copia inmutable del perfil de marca. Nunca una fila viva del ORM."""

    id: int | None
    slug: str
    name: str
    tagline: str | None = None
    color_primary: str = "#E8833A"
    color_secondary: str = "#2E5E8C"
    color_bg: str = "#0B111C"
    font_family: str = "Inter"
    logo_path: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    contact_web: str | None = None
    service_labels: dict = field(default_factory=dict)
    service_taglines: dict = field(default_factory=dict)
    prices: dict = field(default_factory=dict)
    stripe_prefix: str = "dqr"
    page_title: str = ""
    app_name: str = ""
    app_short_name: str = ""
    anamnesis_variant: str = "dq"
    activa: bool = False

    # --- lo que pregunta el resto del sistema -------------------------------
    def label(self, tier: str) -> str:
        """Nombre comercial del servicio ("DQR Full", "Professional Full")."""
        return (self.service_labels or {}).get(tier) or DEFAULTS["service_labels"].get(tier, tier)

    def tagline_de(self, tier: str) -> str:
        return (self.service_taglines or {}).get(tier) or \
            DEFAULTS["service_taglines"].get(tier, "")

    def importe(self, tier: str, period: str) -> int | None:
        """Céntimos de un plan × duración según ESTA marca. None si no lo vende."""
        v = ((self.prices or {}).get(tier) or {}).get(period)
        return int(v) if isinstance(v, (int, float)) and v > 0 else None

    def oferta(self, clave: str = "oferta") -> dict:
        return dict((self.prices or {}).get(clave) or DEFAULTS["prices"].get(clave) or {})

    def lookup_key(self, tier: str, period: str) -> str:
        """Clave del precio en Stripe. El PREFIJO por marca es lo que impide que
        dos marcas se pisen los precios (y, con ellos, las suscripciones vivas)."""
        return f"{self.stripe_prefix or 'dqr'}_{tier}_{period}"


def _marca_de_fila(fila: BrandConfig) -> Marca:
    return Marca(
        id=fila.id,
        slug=getattr(fila, "slug", None) or DEFAULTS["slug"],
        name=fila.name or DEFAULTS["name"],
        tagline=fila.tagline,
        color_primary=fila.color_primary,
        color_secondary=fila.color_secondary,
        color_bg=fila.color_bg,
        font_family=fila.font_family,
        logo_path=fila.logo_path,
        contact_email=fila.contact_email,
        contact_phone=fila.contact_phone,
        contact_web=fila.contact_web,
        service_labels=dict(getattr(fila, "service_labels", None) or DEFAULTS["service_labels"]),
        service_taglines=dict(getattr(fila, "service_taglines", None)
                              or DEFAULTS["service_taglines"]),
        prices=dict(getattr(fila, "prices", None) or DEFAULTS["prices"]),
        stripe_prefix=getattr(fila, "stripe_prefix", None) or DEFAULTS["stripe_prefix"],
        page_title=getattr(fila, "page_title", None) or fila.name or DEFAULTS["page_title"],
        app_name=getattr(fila, "app_name", None) or fila.name or DEFAULTS["app_name"],
        app_short_name=getattr(fila, "app_short_name", None) or DEFAULTS["app_short_name"],
        anamnesis_variant=getattr(fila, "anamnesis_variant", None) or DEFAULTS["anamnesis_variant"],
        activa=bool(getattr(fila, "activa", False)),
    )


def marca_por_defecto() -> Marca:
    """La reserva: lo que había clavado en el código. Nunca lanza."""
    return Marca(id=None, slug=DEFAULTS["slug"], name=DEFAULTS["name"],
                 service_labels=dict(DEFAULTS["service_labels"]),
                 service_taglines=dict(DEFAULTS["service_taglines"]),
                 prices=dict(DEFAULTS["prices"]),
                 stripe_prefix=DEFAULTS["stripe_prefix"],
                 page_title=DEFAULTS["page_title"], app_name=DEFAULTS["app_name"],
                 app_short_name=DEFAULTS["app_short_name"],
                 anamnesis_variant=DEFAULTS["anamnesis_variant"], activa=True)


def invalidar() -> None:
    """El switch (y cualquier edición de la marca) tira la caché: el cambio se
    ve al instante, no dentro de medio minuto."""
    with _lock:
        _cache.update({"at": 0.0, "por_id": {}, "activa": None})


def _refrescar(db: Session) -> None:
    filas = db.scalars(select(BrandConfig).order_by(BrandConfig.id)).all()
    por_id = {f.id: _marca_de_fila(f) for f in filas}
    activa = next((m for m in por_id.values() if m.activa), None)
    if activa is None and por_id:
        activa = next(iter(por_id.values()))          # base antigua: la primera
    with _lock:
        _cache.update({"at": time.monotonic(), "por_id": por_id, "activa": activa})


def _vigente() -> bool:
    return bool(_cache["por_id"]) and (time.monotonic() - _cache["at"]) < _TTL_S


def _con_sesion(db: Session | None):
    """Ejecuta con la sesión dada o con una propia (call sites sin `db`)."""
    if db is not None:
        return db, False
    from app.db import SessionLocal

    return SessionLocal(), True


def marcas(db: Session | None = None) -> list[Marca]:
    """Todos los perfiles, en orden. Para el selector del panel."""
    ses, propia = _con_sesion(db)
    try:
        _refrescar(ses)
    except Exception:  # noqa: BLE001 — sin base, la reserva
        return [marca_por_defecto()]
    finally:
        if propia:
            ses.close()
    return list(_cache["por_id"].values())


def marca_activa(db: Session | None = None) -> Marca:
    """La marca del ESCAPARATE: panel, landing, /planes y altas nuevas."""
    if _vigente() and _cache["activa"] is not None:
        return _cache["activa"]
    ses, propia = _con_sesion(db)
    try:
        _refrescar(ses)
    except Exception:  # noqa: BLE001 — la marca nunca puede tumbar una pantalla
        return marca_por_defecto()
    finally:
        if propia:
            ses.close()
    return _cache["activa"] or marca_por_defecto()


def marca_por_id(brand_id: int | None, db: Session | None = None) -> Marca:
    if brand_id is None:
        return marca_activa(db)
    if _vigente() and brand_id in _cache["por_id"]:
        return _cache["por_id"][brand_id]
    ses, propia = _con_sesion(db)
    try:
        _refrescar(ses)
    except Exception:  # noqa: BLE001
        return marca_por_defecto()
    finally:
        if propia:
            ses.close()
    return _cache["por_id"].get(brand_id) or marca_activa(db)


def marca_de_cliente(client, db: Session | None = None) -> Marca:
    """La marca SELLADA en la ficha del cliente. Un cliente que entró por una
    marca la conserva aunque el coach cambie el switch: su portal, sus
    documentos y sus precios de renovación son los de su marca."""
    return marca_por_id(getattr(client, "brand_id", None), db)


def fila_de_marca(db: Session, client=None) -> BrandConfig | None:
    """La FILA de marca (ORM) para quien necesita el objeto entero: el
    generador de documentos, los emails, el portal.

    Con `client`, la marca SELLADA en su ficha; sin él, la ACTIVA. Antes esto
    era `select(BrandConfig).limit(1)` en nueve sitios: con un solo perfil daba
    igual, pero con dos devuelve una marca CUALQUIERA — el documento de un
    cliente podía salir con el logo del otro negocio.
    """
    bid = getattr(client, "brand_id", None) if client is not None else None
    if bid is not None:
        fila = db.get(BrandConfig, bid)
        if fila is not None:
            return fila
    return (db.scalar(select(BrandConfig).where(BrandConfig.activa.is_(True)).limit(1))
            or db.scalar(select(BrandConfig).order_by(BrandConfig.id).limit(1)))
