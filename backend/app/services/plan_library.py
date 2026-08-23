"""Biblioteca de planificaciones — copiar, guardar como modelo y empezar desde ahí.

Petición del dueño: poder coger la planificación de un cliente (o un MODELO
guardado, p. ej. "Planificación base") y usarla como punto de partida para
otro cliente, SIN gastar créditos y sin empezar de cero.

El principio de seguridad se mantiene intacto: **los números nunca se copian a
ciegas**. Al pegar un plan en otro cliente, el backend recalcula el contrato
calórico del DESTINO (`metrics.energy_targets` + `macro_targets`, con su peso
de referencia) y reescala comidas y banco desde la base copiada
(`rescale_nutrition` + `reconcile_nutrition`, las mismas funciones del editor
y del Word). Lo que viaja de un cliente a otro es la ESTRUCTURA (comidas,
recetas, sesiones, textos); las cifras son siempre las del destino. Cero
llamadas a la IA en todo el módulo.

La copia queda SIEMPRE en borrador y no se activa al editar (misma excepción
que la base sin IA): el coach la adapta y pulsa Activar cuando esté lista.
"""

import copy as _copy
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, Plan, PlanTemplate
from app.services.audit import log_event
from app.services.metrics import _rhu, age_from_birth, energy_targets
from app.services.metrics import macro_targets as _macro_targets
from app.services.nutrition_scale import reconcile_nutrition, rescale_nutrition
from app.services.periods import current_month_index, reference_weight_kg


class PlanLibraryError(Exception):
    """Error accionable de la biblioteca (mensaje listo para el coach)."""


# ------------------------------------------------------------- resumen ----

_GOAL_LABEL = {
    "fat_loss": "pérdida de grasa", "muscle_gain": "ganancia muscular",
    "recomp": "recomposición", "maintenance": "mantenimiento",
    "injury_recovery": "recuperación de lesión",
}


def resumen_plan(nutrition: dict | None, training: dict | None,
                 goal_type: str | None = None) -> str:
    """Una LÍNEA que dice de qué va el plan, para elegir en el pool sin abrir
    nada: "2.200 kcal · P165 C210 G68 · 5 comidas · Torso/Pierna · 4 días"."""
    partes: list[str] = []
    if goal_type and goal_type in _GOAL_LABEL:
        partes.append(_GOAL_LABEL[goal_type])
    if nutrition:
        kcal = nutrition.get("target_kcal")
        if kcal:
            partes.append(f"{_rhu(float(kcal)):,} kcal".replace(",", "."))
        m = nutrition.get("macros") or {}
        if m.get("protein_g"):
            partes.append(
                f"P{_rhu(float(m.get('protein_g') or 0))} "
                f"C{_rhu(float(m.get('carbs_g') or 0))} "
                f"G{_rhu(float(m.get('fat_g') or 0))}"
            )
        meals = nutrition.get("meals") or []
        if meals:
            partes.append(f"{len(meals)} comidas")
    if training:
        if training.get("split_name"):
            partes.append(str(training["split_name"]))
        sesiones = training.get("sessions") or []
        if sesiones:
            partes.append(f"{len(sesiones)} día{'s' if len(sesiones) != 1 else ''}")
    return " · ".join(partes) or "plan vacío"


# ---------------------------------------------------------------- copia ----

def _contrato_del_destino(db: Session, client: Client):
    """Cifras deterministas del cliente DESTINO. Si su anamnesis está coja se
    dice QUÉ falta, igual que al generar."""
    from app.routers.clients import _REQUIRED_FIELDS

    faltan = [label for field, label in _REQUIRED_FIELDS.items()
              if getattr(client, field, None) in (None, "", [])]
    if faltan:
        raise PlanLibraryError(
            "Su anamnesis está incompleta para calcular sus cifras: falta "
            + ", ".join(faltan) + "."
        )
    weight = reference_weight_kg(db, client)
    if not weight:
        raise PlanLibraryError("Sin peso de referencia: rellena su peso en la ficha.")
    age = age_from_birth(client.birth_date, date.today())
    et = energy_targets(
        sex=client.sex, weight_kg=weight, height_cm=client.height_cm, age=age,
        goal_type=client.goal_type, training_days=client.training_days,
        body_fat_pct=client.body_fat_pct, daily_activity=client.daily_activity_level,
        level=client.level, session_min=client.session_max_min,
    )
    mp = _macro_targets(client.sex, weight, client.goal_type, et.target_kcal,
                        client.training_days, tdee=et.tdee)
    return weight, et, mp


def _avisos_de_seguridad(nutrition: dict | None, training: dict | None,
                         client: Client, db: Session) -> list[str]:
    """Choques del plan copiado con la ficha del DESTINO: alérgenos, aversiones,
    patrón dietético y ejercicios fuera de su biblioteca. MISMO criterio que el
    Revisor 0 y que la alerta viva del panel — no una tercera fórmula."""
    from app.services.guardrails import (
        _DIET_PATTERN_FORBIDDEN, _all_option_texts, _iter_options,
        _match_term, _norm_food, option_allergen,
    )

    avisos: list[str] = []
    if nutrition:
        forbidden_pat = (_DIET_PATTERN_FORBIDDEN.get(
            _norm_food(client.diet_pattern).replace(" ", "_"))
            if getattr(client, "diet_pattern", None) else None)
        vistos: set[str] = set()
        for slot, opt in _iter_options(nutrition):
            titulo = opt.get("title") or opt.get("key") or "?"
            if client.food_allergies:
                f = option_allergen(opt, client.food_allergies)
                if f and f"a:{slot}:{f}" not in vistos:
                    vistos.add(f"a:{slot}:{f}")
                    avisos.append(f"⚠ ALÉRGENO para este cliente: «{titulo}» "
                                  f"(toma {slot}, contiene {f}). Cámbialo antes de activar.")
            if client.food_dislikes:
                f = option_allergen(opt, client.food_dislikes)
                if f and f"d:{slot}:{f}" not in vistos:
                    vistos.add(f"d:{slot}:{f}")
                    avisos.append(f"No lo tolera/odia: «{titulo}» (toma {slot}, {f}).")
            if forbidden_pat:
                f = _match_term(forbidden_pat, _all_option_texts(opt))
                if f and f"p:{slot}:{f}" not in vistos:
                    vistos.add(f"p:{slot}:{f}")
                    avisos.append(f"Choca con su patrón «{client.diet_pattern}»: "
                                  f"«{titulo}» (toma {slot}, {f}).")
    if training:
        sesiones = training.get("sessions") or []
        dias = client.training_days
        if dias and len(sesiones) > dias:
            avisos.append(
                f"El plan trae {len(sesiones)} días y este cliente entrena "
                f"{dias}: quita días desde el editor (botón «Quitar día»)."
            )
        # Ejercicios que el filtro del destino NO permitiría (material de casa,
        # contraindicaciones): se avisan por nombre, el coach los cambia.
        from app.models import Exercise

        ids_plan = {int(ex["exercise_id"]) for s in sesiones
                    for ex in (s.get("exercises") or []) if ex.get("exercise_id")}
        if ids_plan:
            permitidos = _biblioteca_permitida(db, client)
            if permitidos is not None:
                filas = list(db.scalars(select(Exercise).where(Exercise.id.in_(ids_plan))))
                for e in filas:
                    if e.id not in permitidos:
                        avisos.append(f"«{e.canonical_name}» no encaja con su ficha "
                                      "(material/limitaciones): cámbialo en el editor.")
    return avisos


def _biblioteca_permitida(db: Session, client: Client) -> set[int] | None:
    """Ids de ejercicio que el filtro determinista permite al cliente, o None
    si no se pudo calcular (nunca rompe la copia: solo deja de avisar).

    MISMO filtro que la generación (guardrails.filter_exercises_for_client con
    las mismas reglas: gym sin restricción de material, lesiones → etiquetas).
    """
    try:
        from app.models import Exercise
        from app.services.guardrails import filter_exercises_for_client
        from app.services.injuries import injury_contra_tags

        all_ex = db.scalars(select(Exercise)).all()
        ex_dicts = [{
            "id": e.id, "canonical_name": e.canonical_name, "name": e.canonical_name,
            "movement_pattern": e.movement_pattern,
            "muscle_primary": e.muscle_primary,
            "muscle_secondary": e.muscle_secondary or [],
            "equipment": e.equipment or [], "level_min": e.level_min,
            "contraindications": e.contraindications or [], "archived": e.archived,
        } for e in all_ex]
        level_map = {"beginner": 1, "intermediate": 2, "advanced": 3}
        equip = set() if client.training_place == "gym" else set(client.equipment or [])
        contra = injury_contra_tags(client.injuries_notes, client.medical_notes)
        library = filter_exercises_for_client(
            ex_dicts, client_contraindications=contra,
            excluded_ids=set(client.excluded_exercise_ids or []),
            equipment_available=equip,
            level_max=level_map.get(client.level, 2),
            training_place=client.training_place,
        )
        return {e["id"] for e in library}
    except Exception:  # noqa: BLE001 — el aviso es best-effort
        return None


def copiar_a_cliente(db: Session, client: Client, *, nutrition: dict | None,
                     training: dict | None, education: dict | None,
                     origen: str) -> tuple[Plan, list[str]]:
    """Crea un BORRADOR para `client` a partir de los JSON de otro plan.

    Estructura del origen + cifras del destino: se recalcula el contrato
    calórico del cliente y se reescala todo desde la base copiada. 0 créditos.
    Devuelve (plan, avisos) — los avisos van también en guardrail_flags para
    que se vean en el panel hasta que se corrijan.
    """
    from app.services import packages as pkgs

    nutrition = _copy.deepcopy(nutrition) if nutrition else None
    training = _copy.deepcopy(training) if training else None
    education = _copy.deepcopy(education) if education else None

    avisos: list[str] = []

    # El paquete del DESTINO manda: pegar entreno a un cliente Start (solo
    # nutrición) publicaría en su portal algo que no ha contratado.
    if training and not pkgs.has_training(client.package_tier):
        training = None
        avisos.append("Este cliente no tiene entrenamiento contratado: "
                      "se copia solo la dieta.")
    if nutrition and not pkgs.has_nutrition(client.package_tier):
        nutrition = None
        avisos.append("Este cliente no tiene nutrición contratada: "
                      "se copia solo el entrenamiento.")
    if not nutrition and not training:
        raise PlanLibraryError(
            "No queda nada que copiar: el plan de origen no encaja con lo que "
            "este cliente tiene contratado."
        )

    weight, et, mp = _contrato_del_destino(db, client)

    if nutrition:
        # Lo que pertenecía al CICLO del cliente de origen no viaja: sus
        # ajustes de revisión, su contador de ediciones y su snapshot.
        for clave in ("applied_adjustments", "rev", "gen_inputs"):
            nutrition.pop(clave, None)
        base = _copy.deepcopy(nutrition)  # la base ORIGINAL, antes de mutar
        # mp.kcal, no et.target_kcal: el plan guarda el invariante del sistema
        # (kcal ≡ 4/4/9 de sus macros), igual que la generación y el editor.
        rescale_nutrition(nutrition, base, float(mp.kcal),
                          float(mp.protein_g), float(mp.carbs_g), float(mp.fat_g))
        reconcile_nutrition(nutrition, weight_kg=weight)
        # TDEE autoritativo del backend (como en la generación): sin él, el
        # déficit/superávit mostrado sería el del cliente de ORIGEN.
        nutrition["tdee_kcal"] = et.tdee
        nutrition["gen_inputs"] = {
            "weight_kg": weight, "height_cm": client.height_cm,
            "level": client.level, "training_days": client.training_days,
            "training_place": client.training_place, "diet_mode": client.diet_mode,
            "diet_pattern": client.diet_pattern,
        }

    # La mitad que FALTA se completa con la base del sistema (0 créditos):
    # copiar un "sistema de entrenamiento" a un cliente con dieta contratada
    # no puede dejarle la dieta vacía — y al revés igual.
    nutrition, training, extra = _completar_mitad_faltante(
        db, client, nutrition, training, et, mp)
    avisos += extra

    avisos += _avisos_de_seguridad(nutrition, training, client, db)

    flags = [f"copiado de {origen} — revísalo y actívalo"] + list(avisos)
    month_index = current_month_index(db, client.id)
    last = db.scalar(
        select(Plan).where(Plan.client_id == client.id,
                           Plan.month_index == month_index)
        .order_by(Plan.version.desc()).limit(1)
    )
    plan = Plan(
        client_id=client.id, month_index=month_index,
        version=(last.version + 1) if last else 1, status="draft",
        nutrition_json=nutrition, training_json=training,
        education_json=education, guardrail_flags=flags,
        generated_by="library", review_json=None, goal_type=client.goal_type,
    )
    db.add(plan)
    db.flush()
    log_event(db, "plan", plan.id, "plan_copied", {
        "client_id": client.id, "origen": origen, "avisos": len(avisos),
    })
    return plan, avisos


def _completar_mitad_faltante(db: Session, client: Client,
                              nutrition: dict | None, training: dict | None,
                              et, mp):
    """Si el origen no traía dieta (o entreno) y el destino SÍ la tiene
    contratada, se prepara la base determinista del sistema (plan_scaffold,
    la misma del botón "A mano"). Best-effort: si la ficha no da, se avisa y
    la copia sigue — nunca se rompe por esto."""
    from app.services import packages as pkgs
    from app.services import plan_scaffold

    avisos: list[str] = []

    if nutrition is None and pkgs.has_nutrition(client.package_tier):
        try:
            nutrition = plan_scaffold.build_nutrition(client, et, mp)
            if client.diet_mode == "strict":
                bank, extra = plan_scaffold.build_strict_menu(
                    nutrition, allergies=client.food_allergies or [],
                    dislikes=client.food_dislikes or [],
                    diet_pattern=client.diet_pattern)
                nutrition["meal_bank"] = bank
                avisos += list(extra)
            else:
                from app.services.meal_fallback import ensure_bank_slots

                ensure_bank_slots(
                    nutrition, allergies=client.food_allergies or [],
                    dislikes=client.food_dislikes or [],
                    diet_pattern=client.diet_pattern)
            nutrition["gen_inputs"] = {
                "weight_kg": reference_weight_kg(db, client),
                "height_cm": client.height_cm, "level": client.level,
                "training_days": client.training_days,
                "training_place": client.training_place,
                "diet_mode": client.diet_mode, "diet_pattern": client.diet_pattern,
            }
            avisos.append("El origen no traía dieta: se ha preparado la base "
                          "del sistema (revísala).")
        except Exception:  # noqa: BLE001
            nutrition = None
            avisos.append("El origen no traía dieta y la base no se pudo "
                          "montar con su ficha: añádela a mano o genera.")

    if training is None and pkgs.has_training(client.package_tier):
        try:
            from app.models import Exercise

            permitidos = _biblioteca_permitida(db, client)
            all_ex = db.scalars(select(Exercise)).all()
            library = [{
                "id": e.id, "canonical_name": e.canonical_name,
                "name": e.canonical_name, "movement_pattern": e.movement_pattern,
                "muscle_primary": e.muscle_primary,
                "muscle_secondary": e.muscle_secondary or [],
                "equipment": e.equipment or [], "level_min": e.level_min,
                "contraindications": e.contraindications or [],
                "archived": e.archived,
            } for e in all_ex if permitidos is None or e.id in permitidos]
            training = plan_scaffold.build_training(client, library)
            avisos.append("El origen no traía entrenamiento: se ha preparado "
                          "la base del sistema (revísala).")
        except Exception:  # noqa: BLE001
            training = None
            avisos.append("El origen no traía entrenamiento y la base no se "
                          "pudo montar: añádelo a mano o genera.")

    return nutrition, training, avisos


# -------------------------------------------------------------- modelos ----

def guardar_modelo(db: Session, plan: Plan, titulo: str) -> PlanTemplate:
    """Congela un plan como MODELO reutilizable. Sin datos personales: el
    título lo pone el coach (si quiere nombrar al cliente, es su decisión)."""
    titulo = (titulo or "").strip()
    if not titulo:
        raise PlanLibraryError("Ponle un título al modelo (p. ej. «Planificación base»).")
    nutrition = _copy.deepcopy(plan.nutrition_json) if plan.nutrition_json else None
    if nutrition:
        # El modelo tampoco arrastra el ciclo de nadie.
        for clave in ("applied_adjustments", "rev", "gen_inputs"):
            nutrition.pop(clave, None)
    tpl = PlanTemplate(
        title=titulo[:120],
        summary=resumen_plan(nutrition, plan.training_json, plan.goal_type),
        nutrition_json=nutrition,
        training_json=_copy.deepcopy(plan.training_json) if plan.training_json else None,
        education_json=_copy.deepcopy(plan.education_json) if plan.education_json else None,
    )
    db.add(tpl)
    db.flush()
    log_event(db, "plan_template", tpl.id, "template_saved",
              {"title": tpl.title, "from_plan": plan.id})
    return tpl


def pool_de_planes(db: Session) -> list[dict]:
    """El plan VIGENTE de cada cliente (o su último borrador si no hay activo),
    con su resumen: es la lista de "copiar de este cliente"."""
    filas = list(db.execute(
        select(Plan, Client.full_name)
        .join(Client, Client.id == Plan.client_id)
        .where(Plan.status.in_(("published", "draft")))
        .order_by(Plan.client_id, Plan.id.desc())
    ))
    mejores: dict[int, tuple[Plan, str]] = {}
    for plan, nombre in filas:
        actual = mejores.get(plan.client_id)
        # Preferencia: publicado > borrador; a igualdad, el más nuevo (la
        # consulta ya viene de nuevo a viejo).
        if actual is None or (plan.status == "published" and actual[0].status != "published"):
            mejores[plan.client_id] = (plan, nombre)
    out = []
    for plan, nombre in mejores.values():
        out.append({
            "plan_id": plan.id, "client_id": plan.client_id, "client_name": nombre,
            "status": plan.status,
            "summary": resumen_plan(plan.nutrition_json, plan.training_json,
                                    plan.goal_type),
            "updated_at": (plan.published_at or plan.created_at).isoformat()
            if (plan.published_at or plan.created_at) else None,
        })
    out.sort(key=lambda x: x["client_name"].lower())
    return out
