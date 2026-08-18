"""Planes contratables y sus capacidades — FUENTE ÚNICA DE VERDAD.

Tres servicios de PAGO ÚNICO con la MISMA maquinaria interna (anamnesis →
plan → portal → seguimiento → informe); solo cambia lo que incluyen:

  - nutri: solo DIETA (70 €).
  - train: solo ENTRENAMIENTO (70 €).
  - full:  las dos cosas + la cuota del gimnasio (130 €).

Todo se entrega por EMAIL en los tres.

Antes estas reglas vivían como comparaciones de cadenas repartidas por routers y
servicios (`package_tier == "start"`, `!= "pro"`…), que es justo donde se cuelan
los fallos al añadir un plan. Aquí se centralizan: el resto del código pregunta
por CAPACIDAD, nunca por el nombre del plan.
"""
from __future__ import annotations

from app import branding

# Planes vigentes, en orden de presentación.
TIERS: tuple[str, ...] = ("train", "nutri", "full")

# Nombres antiguos → nuevos. `start` era solo dieta; `pro` era todo + contacto,
# que ahora es justo `full` (el contacto ya no es un extra).
LEGACY_TIERS = {"start": "nutri", "pro": "full"}

DEFAULT_TIER = "full"

LABELS = branding.TIER_LABELS
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


def label(tier: str | None) -> str:
    return LABELS[normalize(tier)]


def tagline(tier: str | None) -> str:
    return TAGLINES[normalize(tier)]
