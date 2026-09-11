"""Cambiar UN alimento de una opción del banco de comidas — sin regenerar.

Petición del dueño: cuando una alerta dice "esta opción lleva un alimento que
ahora no tolera/odia", tiene que haber una forma clara y directa de arreglarlo
ahí mismo (sin gastar créditos regenerando el plan entero), y que el cambio
se guarde solo — sin un botón "Guardar" aparte — dejando claro que toca
avisar al cliente del cambio.

Mismo patrón que `services/swap.py` (el swap de EJERCICIOS): crea una nueva
VERSIÓN del plan, revalida con el guardarraíl determinista y solo la activa
si no hay violación; y se registra en `plan_edits` (§13) con su `signal`/
`source="swap"`/`detail`, igual que un cambio de ejercicio.

Los GRAMOS los fija el solver (`portion_solver.snap_option_ingredients`)
contra el objetivo de ESA toma — la IA/el coach solo eligen el alimento, el
backend calcula (principio central del sistema, §3).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, Food, Plan
from app.services import guardrails as gr
from app.services.portion_solver import filter_foods, snap_option_ingredients


def _food_dict(f: Food) -> dict:
    return {
        "id": f.id, "canonical_name": f.canonical_name, "aliases": f.aliases or [],
        "kcal": f.kcal, "protein_g": f.protein_g, "carbs_g": f.carbs_g, "fat_g": f.fat_g,
        "allergens": f.allergens or [], "tags": f.tags or [],
        "unit_grams": f.unit_grams, "min_grams": f.min_grams, "max_grams": f.max_grams,
    }


def search_foods_for_client(db: Session, client: Client, query: str, limit: int = 20) -> list[dict]:
    """Alimentos del catálogo que coinciden con `query`, YA sin los que
    violarían sus alergias/aversiones/patrón — el coach no puede ni ver, y
    menos elegir, algo que reabriría la misma alerta."""
    q = (query or "").strip().lower()
    if len(q) < 2:
        return []
    rows = db.scalars(select(Food).where(Food.archived.is_(False))).all()
    candidatos = [_food_dict(f) for f in rows]
    permitidos = filter_foods(
        candidatos, allergies=client.food_allergies or [],
        dislikes=client.food_dislikes or [],
        diet_pattern=getattr(client, "diet_pattern", None),
    )
    coinciden = [
        f for f in permitidos
        if q in f["canonical_name"].lower() or any(q in a.lower() for a in f["aliases"])
    ]
    coinciden.sort(key=lambda f: (not f["canonical_name"].lower().startswith(q), f["canonical_name"]))
    return coinciden[:limit]


@dataclass
class FoodSwapResult:
    new_plan_id: int
    new_version: int
    retained: bool
    guardrail_flags: list[str]
    option_title: str


def apply_food_swap(
    db: Session, *, client: Client, plan: Plan,
    slot: int, option_index: int, old_food_id: int, new_food_id: int,
) -> FoodSwapResult:
    """Sustituye `old_food_id` por `new_food_id` en una opción del banco
    flexible, creando una nueva versión del plan. Lanza `ValueError` (mensaje
    para el coach) ante cualquier dato que no encaje."""
    nutrition = copy.deepcopy(plan.nutrition_json or {})
    bank = nutrition.get("meal_bank") or {}
    if (bank.get("mode") or "flexible_7") != "flexible_7":
        raise ValueError("El menú cerrado (strict) se edita subiendo el Word, no aquí")

    slots = bank.get("slots") or []
    slot_obj = next((s for s in slots if s.get("slot") == slot), None)
    if slot_obj is None:
        raise ValueError("Esa toma no existe en el banco de comidas")
    options = slot_obj.get("options") or []
    if option_index < 0 or option_index >= len(options):
        raise ValueError("Esa opción no existe")
    option = options[option_index]
    ingredients = option.get("ingredients") or []
    old_ing = next((i for i in ingredients if i.get("food_id") == old_food_id), None)
    if old_ing is None:
        raise ValueError("Ese alimento no está en esta opción")

    new_food = db.get(Food, new_food_id)
    if new_food is None or new_food.archived:
        raise ValueError("El alimento de destino no existe")
    # Nunca fiarse de lo que ya filtró la búsqueda: la ficha pudo cambiar entre
    # medias, o la petición no viene de la búsqueda en absoluto.
    if not filter_foods([_food_dict(new_food)], allergies=client.food_allergies or [],
                        dislikes=client.food_dislikes or [],
                        diet_pattern=getattr(client, "diet_pattern", None)):
        raise ValueError(f"«{new_food.canonical_name}» también choca con su ficha (alergia, "
                         "aversión o patrón): elige otro alimento")

    target = next((m.get("target") for m in (nutrition.get("meals") or []) if m.get("slot") == slot), None)
    if not target:
        raise ValueError("No se encuentra el objetivo de macros de esa toma")

    new_ingredients = [
        {**ing, "food_id": new_food_id} if ing.get("food_id") == old_food_id else ing
        for ing in ingredients
    ]
    food_ids = {i.get("food_id") for i in new_ingredients if i.get("food_id") is not None}
    foods_by_id = {f.id: _food_dict(f) for f in db.scalars(select(Food).where(Food.id.in_(food_ids)))}
    resuelto = snap_option_ingredients(new_ingredients, target, foods_by_id)
    if resuelto is None:
        raise ValueError("No se ha podido recalcular esta opción con ese alimento")
    new_ings, macros = resuelto
    option["ingredients"] = new_ings
    option["macros"] = macros

    old_name = old_ing.get("food") or ""
    title = option.get("title") or ""
    # El título suele nombrar el alimento por su ALIAS coloquial ("avena"), no
    # por el nombre canónico completo del catálogo ("Avena en copos") — probar
    # solo el nombre exacto dejaba el título sin tocar en el caso más común.
    # Se prueba cada candidato de más largo a más corto (evita que un alias
    # corto reemplace solo un trozo de uno más largo que también encaja).
    old_food = db.get(Food, old_food_id)
    candidatos = {old_name} | ({old_food.canonical_name, *(old_food.aliases or [])} if old_food else set())
    for cand in sorted((c for c in candidatos if c), key=len, reverse=True):
        idx = title.lower().find(cand.lower())
        if idx != -1:
            title = title[:idx] + new_food.canonical_name + title[idx + len(cand):]
            option["title"] = title
            break

    # Revalida seguridad alimentaria (Revisor 0): la sustitución ya pasó por
    # `filter_foods`, esto es el mismo criterio COMPLETO (título/preparación
    # incluidos) que usa el resto del sistema, nunca dos varas de medir.
    report = gr.validate_plan_deterministic(
        nutrition, allergies=client.food_allergies or [], dislikes=client.food_dislikes or [],
        diet_pattern=getattr(client, "diet_pattern", None),
    )
    flags = report.as_flags()
    retained = any(str(f).startswith("violation:") for f in flags)
    if retained:
        flags = list(flags) + [
            "retenido: guardado como BORRADOR — revisa y activa tú (el cliente no ha sido avisado)"
        ]

    last = db.scalar(
        select(Plan).where(Plan.client_id == client.id, Plan.month_index == plan.month_index)
        .order_by(Plan.version.desc()).limit(1)
    )
    new_plan = Plan(
        client_id=client.id, month_index=plan.month_index, version=(last.version if last else plan.version) + 1,
        status="draft", nutrition_json=nutrition, training_json=plan.training_json,
        education_json=plan.education_json, generated_by="swap",
        guardrail_flags=flags, goal_type=plan.goal_type or client.goal_type,
    )
    db.add(new_plan)
    db.flush()

    from app.services.audit import log_event

    log_event(db, "plan", new_plan.id, "food_swapped", {
        "slot": slot, "old_food_id": old_food_id, "new_food_id": new_food_id,
        "from_plan": plan.id, "retained": retained,
    })
    # §13: una sustitución de alimento es la señal MÁS explícita que hay de
    # preferencia alimentaria — sin registrarla, el aprendizaje nunca ve que un
    # alimento concreto se cambia una y otra vez.
    try:
        from app.services.continuous_learning import record_edit

        with db.begin_nested():
            record_edit(
                db, plan_id=new_plan.id, category="seleccion_alimentos",
                field_path="nutrition.meal_bank.slots.options",
                note=f"cambio de alimento: {old_name or old_food_id} → {new_food.canonical_name}"
                     f" (toma {slot})",
                signal="nutricion.alimento", source="swap",
                detail=f"{old_name or old_food_id} → {new_food.canonical_name}"[:200],
                commit=False,
            )
    except Exception:  # noqa: BLE001 — el aprendizaje nunca rompe el swap
        pass

    if not retained:
        from app.services.plan_activation import activate_plan

        activate_plan(db, new_plan, notify=False)
    db.commit()
    return FoodSwapResult(
        new_plan_id=new_plan.id, new_version=new_plan.version, retained=retained,
        guardrail_flags=flags, option_title=option.get("title") or "",
    )
