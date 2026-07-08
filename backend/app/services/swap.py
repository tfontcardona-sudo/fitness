"""Swap de ejercicios — solo coach, desde el plan publicado (F.5).

Dos operaciones:

1. `propose_alternatives(...)` — dado un ejercicio del plan y el cliente,
   devuelve 2–3 alternativas de la biblioteca con el MISMO patrón de movimiento
   y músculo primario, filtradas por equipamiento, nivel, lesiones y exclusiones
   (filtro determinista de guardrails). No usa IA: es selección + orden por
   similitud de estímulo (mismo patrón > mismos secundarios > equipamiento).

2. `apply_swap(...)` — sustituye el ejercicio en el plan heredando
   series/reps/RIR/descansos, ajustando start_weight_hint proporcionalmente,
   regenerando los cues desde la biblioteca, recalculando el volumen del grupo y
   revalidando guardrails. Registra el motivo en audit_log y, si es permanente,
   lo añade a las exclusiones del cliente. Crea una nueva VERSIÓN del plan
   (borrador) para que el coach la republique.

Mantener esto fuera del router permite testearlo de forma aislada.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, Exercise, Plan
from app.services import guardrails as gr


@dataclass
class Alternative:
    exercise_id: int
    name: str
    movement_pattern: str
    muscle_primary: str
    equipment: list[str]
    similarity: int  # mayor = más parecido


def _client_equipment(client: Client) -> set[str]:
    return set(client.equipment or [])


def _client_excluded(client: Client) -> set[int]:
    return set(client.excluded_exercise_ids or [])


def _client_contraindications(client: Client) -> set[str]:
    # Lesiones (texto libre) → etiquetas de contraindicación articular, para que
    # las alternativas propuestas y el swap nunca ofrezcan un ejercicio que carga
    # una zona lesionada.
    from app.services.injuries import injury_contra_tags
    return injury_contra_tags(client.injuries_notes, client.medical_notes)


def propose_alternatives(
    db: Session, client: Client, current_exercise_id: int, limit: int = 3
) -> list[Alternative]:
    """Alternativas válidas para sustituir un ejercicio (F.5.1)."""
    current = db.get(Exercise, current_exercise_id)
    if current is None:
        return []

    level_max = {"beginner": 1, "intermediate": 2, "advanced": 3}.get(client.level or "intermediate", 2)
    equipment = _client_equipment(client)
    excluded = _client_excluded(client) | {current_exercise_id}
    contra = _client_contraindications(client)

    # Candidatos del mismo patrón de movimiento (requisito duro F.5.1)
    candidates = db.scalars(
        select(Exercise).where(
            Exercise.movement_pattern == current.movement_pattern,
            Exercise.muscle_primary == current.muscle_primary,
            Exercise.archived.is_(False),
        )
    ).all()

    # Filtro determinista de guardrails (equipamiento, nivel, lesiones, exclusiones)
    as_dicts = [{
        "id": e.id, "movement_pattern": e.movement_pattern, "muscle_primary": e.muscle_primary,
        "muscle_secondary": e.muscle_secondary, "equipment": e.equipment,
        "contraindications": e.contraindications, "level_min": e.level_min,
        "archived": e.archived, "canonical_name": e.canonical_name,
    } for e in candidates]

    valid = gr.filter_exercises_for_client(
        as_dicts, client_contraindications=contra, excluded_ids=excluded,
        equipment_available=equipment, level_max=level_max,
        training_place=client.training_place or "gym",
    )

    # Orden por similitud de estímulo: comparte músculos secundarios + equipamiento
    cur_sec = set(current.muscle_secondary or [])
    cur_eq = set(current.equipment or [])
    out: list[Alternative] = []
    for e in valid:
        sec_overlap = len(cur_sec & set(e.get("muscle_secondary") or []))
        eq_overlap = len(cur_eq & set(e.get("equipment") or []))
        out.append(Alternative(
            exercise_id=e["id"], name=e["canonical_name"],
            movement_pattern=e["movement_pattern"], muscle_primary=e["muscle_primary"],
            equipment=e.get("equipment") or [],
            similarity=sec_overlap * 2 + eq_overlap,
        ))
    out.sort(key=lambda a: a.similarity, reverse=True)
    return out[:limit]


@dataclass
class SwapResult:
    new_plan_id: int
    new_version: int
    group_volume_after: float
    guardrail_flags: list[str]


def apply_swap(
    db: Session,
    *,
    client: Client,
    plan: Plan,
    session_index: int,
    old_exercise_id: int,
    new_exercise_id: int,
    permanent: bool,
    reason: str,
) -> SwapResult:
    """Sustituye un ejercicio creando una nueva versión del plan (borrador).

    Hereda series/reps/RIR/descansos, ajusta el peso orientativo
    proporcionalmente (heurística por nivel del ejercicio), regenera cues desde
    la biblioteca y recalcula/valida el volumen. F.5.2–F.5.4.
    """
    from app.services.audit import log_event

    new_ex = db.get(Exercise, new_exercise_id)
    if new_ex is None:
        raise ValueError("Ejercicio de destino no existe")
    # Seguridad: nunca sustituir por un ejercicio que carga una zona lesionada.
    contra = _client_contraindications(client)
    if contra & set(new_ex.contraindications or []):
        zonas = ", ".join(sorted(contra & set(new_ex.contraindications or [])))
        raise ValueError(f"El ejercicio de destino está contraindicado para el cliente ({zonas})")

    training = copy.deepcopy(plan.training_json or {})
    sessions = training.get("sessions", [])
    if session_index >= len(sessions):
        raise ValueError("Sesión fuera de rango")

    exercises = sessions[session_index].get("exercises", [])
    target = next((e for e in exercises if e["exercise_id"] == old_exercise_id), None)
    if target is None:
        raise ValueError("El ejercicio a sustituir no está en esa sesión")

    # Hereda parámetros; sustituye id y cues
    target["exercise_id"] = new_exercise_id
    target["technique_cue"] = (new_ex.technique_notes or "")[:160]
    target["biomech_cue"] = (new_ex.biomechanics_notes or "")[:160]
    # El peso orientativo del ejercicio anterior no es transferible a otro
    # ejercicio (biomecánica distinta): se deja que el coach/cliente lo calibre
    # en la primera sesión en vez de aplicar un factor arbitrario engañoso.
    target["start_weight_hint_kg"] = None

    # Nueva versión (borrador) del plan
    last = db.scalar(
        select(Plan).where(Plan.client_id == client.id, Plan.month_index == plan.month_index)
        .order_by(Plan.version.desc()).limit(1)
    )
    new_plan = Plan(
        client_id=client.id, month_index=plan.month_index, version=last.version + 1,
        status="draft", nutrition_json=plan.nutrition_json, training_json=training,
        education_json=plan.education_json, generated_by="swap",
        goal_type=plan.goal_type or client.goal_type,
    )
    db.add(new_plan)
    db.flush()

    # Recalcula volumen del grupo y valida guardrails
    lib = {e.id: {"canonical_name": e.canonical_name, "muscle_primary": e.muscle_primary,
                  "contraindications": e.contraindications}
           for e in db.scalars(select(Exercise))}
    report = gr.check_training(
        training, training_days_declared=client.training_days or len(sessions),
        session_max_min=client.session_max_min or 90,
        client_contraindications=_client_contraindications(client),
        exercise_lookup=lib,
    )
    new_plan.guardrail_flags = report.as_flags()

    group_volume = sum(
        ex["sets"] for s in sessions for ex in s.get("exercises", [])
        if lib.get(ex["exercise_id"], {}).get("muscle_primary") == new_ex.muscle_primary
    )

    # Exclusión permanente
    if permanent:
        excluded = list(_client_excluded(client))
        if old_exercise_id not in excluded:
            excluded.append(old_exercise_id)
            client.excluded_exercise_ids = excluded

    log_event(db, "plan", new_plan.id, "exercise_swapped", {
        "old_exercise_id": old_exercise_id, "new_exercise_id": new_exercise_id,
        "permanent": permanent, "reason": reason, "from_plan": plan.id,
    })
    db.commit()
    return SwapResult(
        new_plan_id=new_plan.id, new_version=new_plan.version,
        group_volume_after=group_volume, guardrail_flags=new_plan.guardrail_flags or [],
    )
