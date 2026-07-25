"""Desbloqueo progresivo por segmento (hardening §12).

Hoy no hay datos que respalden el auto-envío, así que TODO empieza en ámbar. Un
segmento simple (adulto sano, sin patología ni medicación, horario estándar, sin
restricciones complejas) pasa a VERDE tras N planes consecutivos con ICP alto y
sin edición material. Se van abriendo segmentos más complejos con el mismo
criterio; si un segmento vuelve a acumular ediciones, revierte a ámbar
automáticamente. Configurable por segmento en BBDD, con contadores y reversión.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SegmentUnlock, utcnow
from app.services.safety_gate import red_flags

# Planes limpios consecutivos para abrir un segmento.
UNLOCK_STREAK = 20


def client_segment(profile: dict) -> str:
    """Clasifica al cliente en un segmento. El más simple ('adulto_sano_estandar')
    es el primero que puede abrirse; el resto son más complejos."""
    if red_flags(profile):
        return "clinico"           # patología/medicación/lista roja → nunca simple
    age = profile.get("age")
    if not isinstance(age, (int, float)) or not (18 <= age <= 65):
        return "edad_fuera"
    if profile.get("diet_pattern") in ("vegano", "vegetariano", "halal", "kosher"):
        return "dieta_compleja"
    if len(profile.get("food_allergies") or []) >= 2:
        return "alergias_multiples"
    if profile.get("shift_work"):
        return "turnos"
    return "adulto_sano_estandar"


def _get(db: Session, segment: str) -> SegmentUnlock:
    row = db.scalar(select(SegmentUnlock).where(SegmentUnlock.segment == segment))
    if row is None:
        row = SegmentUnlock(segment=segment, clean_streak=0, unlocked=False)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def register_plan_outcome(
    db: Session, segment: str, *, clean: bool, commit: bool = True,
) -> SegmentUnlock:
    """Registra el resultado de un plan del segmento. `clean` = ICP alto y sin
    edición material. Racha limpia → desbloquea; una edición → revierte."""
    row = _get(db, segment)
    if clean:
        row.clean_streak += 1
        if row.clean_streak >= UNLOCK_STREAK:
            row.unlocked = True
    else:
        row.clean_streak = 0
        row.unlocked = False   # reversión automática al acumular edición
    row.updated_at = utcnow()
    if commit:
        db.commit()
    return row


def segment_allows_green(db: Session, profile: dict) -> bool:
    """True si el segmento del cliente está desbloqueado (puede ir a verde). Solo
    el segmento simple y los que se hayan abierto; el clínico NUNCA."""
    seg = client_segment(profile)
    if seg == "clinico":
        return False
    return _get(db, seg).unlocked
