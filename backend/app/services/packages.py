"""Planes contratables y sus capacidades — FUENTE ÚNICA DE VERDAD.

Tres planes con la MISMA maquinaria interna (anamnesis → plan → portal →
seguimiento → revisión); solo cambian los servicios incluidos:

  - nutri: solo NUTRICIÓN.
  - train: solo ENTRENAMIENTO.
  - full:  las dos cosas (y la videollamada de revisión).

El contacto diario por WhatsApp está en los TRES: es el canal con el cliente,
no un extra de gama alta.

Antes estas reglas vivían como comparaciones de cadenas repartidas por routers y
servicios (`package_tier == "start"`, `!= "pro"`…), que es justo donde se cuelan
los fallos al añadir un plan. Aquí se centralizan: el resto del código pregunta
por CAPACIDAD, nunca por el nombre del plan.
"""
from __future__ import annotations

# Planes vigentes, en orden de presentación.
TIERS: tuple[str, ...] = ("train", "nutri", "full")

# Nombres antiguos → nuevos. `start` era solo dieta; `pro` era todo + contacto,
# que ahora es justo `full` (el contacto ya no es un extra).
LEGACY_TIERS = {"start": "nutri", "pro": "full"}

DEFAULT_TIER = "full"

LABELS = {"nutri": "DQR Nutri", "train": "DQR Train", "full": "DQR Full"}
TAGLINES = {
    "nutri": "solo nutrición",
    "train": "solo entrenamiento",
    "full": "nutrición + entrenamiento",
}


def normalize(tier: str | None) -> str:
    """Nombre de plan vigente. Traduce los antiguos y cae al de por defecto."""
    t = (tier or "").strip().lower()
    t = LEGACY_TIERS.get(t, t)
    return t if t in TIERS else DEFAULT_TIER


def has_nutrition(tier: str | None) -> bool:
    """¿El plan incluye dieta? (nutri y full)."""
    return normalize(tier) in ("nutri", "full")


def has_training(tier: str | None) -> bool:
    """¿El plan incluye entrenamiento? (train y full)."""
    return normalize(tier) in ("train", "full")


def has_direct_contact(tier: str | None) -> bool:
    """WhatsApp diario: incluido en TODOS los planes."""
    normalize(tier)  # valida
    return True


def has_video_call(tier: str | None) -> bool:
    """Videollamada de revisión (Google Meet): solo en el pack completo."""
    return normalize(tier) == "full"


def label(tier: str | None) -> str:
    return LABELS[normalize(tier)]


def tagline(tier: str | None) -> str:
    return TAGLINES[normalize(tier)]
