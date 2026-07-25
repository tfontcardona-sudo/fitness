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


def profile_from_client(client) -> dict:
    """Construye el `profile` que consumen `client_segment`/`red_flags` a partir de
    un modelo Client. Centraliza el mapeo para que la clasificación sea idéntica
    en la activación (§12) y en el semáforo de envío."""
    from app.services.metrics import age_from_birth

    age = age_from_birth(client.birth_date) if getattr(client, "birth_date", None) else None
    return {
        "sex": getattr(client, "sex", None),
        "age": age,
        "height_cm": getattr(client, "height_cm", None),
        "weight_kg": getattr(client, "current_weight_kg", None) or getattr(client, "start_weight_kg", None),
        "medical_notes": getattr(client, "medical_notes", None),
        "medication_notes": getattr(client, "medication_notes", None),
        "injuries_notes": getattr(client, "injuries_notes", None),
        "lifestyle_notes": getattr(client, "lifestyle_notes", None),
        "current_supplements": getattr(client, "current_supplements", None),
        "food_allergies": getattr(client, "food_allergies", None) or [],
        # `diet_pattern`/`shift_work` no son campos propios de la anamnesis actual;
        # se dejan como huecos [PENDIENTE TONI] y no fuerzan un segmento simple.
        "diet_pattern": None,
        "shift_work": None,
    }


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
        # flush (no commit): así el llamador conserva su transacción. `activate_plan`
        # registra el resultado SIN cerrar su commit; un commit aquí persistiría una
        # activación a medias.
        db.flush()
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


def plan_is_clean(db: Session, plan) -> bool:
    """¿El plan salió "limpio"? Señal DETERMINISTA disponible hoy: sin violaciones
    de guardrail y sin ninguna edición material del coach registrada (§13). El ICP
    del panel (§9/§11) endurecerá esta señal cuando los revisores IA estén enchufados.
    """
    from app.models import PlanEdit

    flags = plan.guardrail_flags or []
    if any(str(f).startswith("violation:") for f in flags):
        return False
    edited = db.scalar(select(PlanEdit.id).where(PlanEdit.plan_id == plan.id).limit(1))
    return edited is None


def register_plan_activation(db: Session, plan, client, *, commit: bool = False) -> SegmentUnlock | None:
    """Registra el resultado del plan recién activado en el segmento del cliente
    (§12). Best-effort: nunca debe tumbar la activación."""
    if client is None:
        return None
    segment = client_segment(profile_from_client(client))
    return register_plan_outcome(db, segment, clean=plan_is_clean(db, plan), commit=commit)


def segment_allows_green(db: Session, profile: dict) -> bool:
    """True si el segmento del cliente está desbloqueado (puede ir a verde). Solo
    el segmento simple y los que se hayan abierto; el clínico NUNCA."""
    seg = client_segment(profile)
    if seg == "clinico":
        return False
    return _get(db, seg).unlocked
