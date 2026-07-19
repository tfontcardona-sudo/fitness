"""Adaptar el plan a la última REVISIÓN QUINCENAL sin volver a llamar a la IA.

Los ajustes (`plan_adjustments`) ya los calculó la IA al generar el feedback. Aquí
se aplican de forma DETERMINISTA sobre el plan publicado vigente (macros de dieta,
cargas de entreno) y se crea una nueva versión en borrador que el coach revisa y
publica. Así "Adaptar plan" funciona siempre (no depende del crédito de la IA).
"""

from __future__ import annotations

import copy
import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, Period, Plan
from app.services.audit import log_event


class AdaptError(RuntimeError):
    """No se puede adaptar (sin revisión analizada o sin plan base)."""


def _norm(s: str) -> str:
    s = (s or "").lower()
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _parse_change(text: str) -> tuple[str | None, float | None]:
    """Interpreta la primera cantidad del cambio.

    Devuelve ('delta', ±n) para un cambio relativo ('+15', 'subir 15', 'bajar 20')
    o ('abs', n) para un objetivo absoluto ('reducir a 150 g', 'hasta 2000 kcal',
    '200 g'). El objetivo 'a/hasta N' tiene prioridad sobre el verbo (así
    'reducir a 150' fija 150, no resta 150). Sin número → (None, None)."""
    t = _norm(text)
    m = re.search(r"([+-]?\d+(?:[.,]\d+)?)", text or "")
    if not m:
        return (None, None)
    val = float(m.group(1).replace(",", "."))
    if m.group(1).startswith(("+", "-")):
        return ("delta", val)
    if re.search(r"\b(a|hasta|hacia)\s+\d", t) or re.search(r"=\s*\d", t):
        return ("abs", abs(val))
    if re.search(r"\b(sub|aument|increment|anad|agreg|suma)", t):
        return ("delta", abs(val))
    if re.search(r"\b(baj|reduc|menos|quit|resta|recort|dismin)", t):
        return ("delta", -abs(val))
    return ("abs", abs(val))  # número suelto ('200 g') → objetivo


def _apply(current: float | None, mode: str, val: float, floor: float = 0.0) -> int:
    """Aplica un delta o un objetivo absoluto y nunca baja del suelo (>=0)."""
    result = val if mode == "abs" else (current or 0) + val
    return int(round(max(floor, result)))


def adapt_plan_from_feedback(db: Session, client_id: int) -> Plan:
    """Crea una nueva versión (borrador) del plan aplicando los ajustes de la
    última revisión quincenal analizada. No llama a la IA."""
    # Solo períodos ANALIZADOS (con feedback): así coincide con la revisión que
    # el coach ve en el banner ("Adaptar a la revisión #N"). Un período cerrado
    # aún sin feedback no tiene ajustes que aplicar.
    period = db.scalar(
        select(Period)
        .where(Period.client_id == client_id, Period.status == "analyzed")
        .order_by(Period.period_index.desc())
        .limit(1)
    )
    if not period:
        raise AdaptError("No hay ninguna revisión quincenal analizada para adaptar el plan.")
    adjustments = (period.ai_analysis_json or {}).get("plan_adjustments") or []

    # Plan base = el último PUBLICADO por (mes, versión) — las versiones se
    # reinician por mes, así que ordenar solo por versión elegiría el mes
    # equivocado cuando conviven planes de varios meses.
    base = db.scalar(
        select(Plan).where(Plan.client_id == client_id, Plan.status == "published")
        .order_by(Plan.month_index.desc(), Plan.version.desc()).limit(1)
    ) or db.scalar(
        select(Plan).where(Plan.client_id == client_id)
        .order_by(Plan.month_index.desc(), Plan.version.desc()).limit(1)
    )
    if not base:
        raise AdaptError("El cliente no tiene un plan base que adaptar.")

    # IDEMPOTENCIA — adaptar dos veces a la misma revisión NO debe acumular
    # los ajustes numéricos (p. ej. proteína 150→165 y luego 165→180):
    # · si el plan vigente YA está adaptado a esta revisión → error claro;
    # · si ya existe un BORRADOR adaptado a esta revisión → se rehace ese
    #   borrador desde el plan publicado (no se crea otra versión más).
    def _adapted_idx(p: Plan) -> int | None:
        return ((p.nutrition_json or {}).get("applied_adjustments") or {}).get("period_index")

    if _adapted_idx(base) == period.period_index:
        raise AdaptError(
            f"El plan vigente ya está adaptado a la revisión #{period.period_index}. "
            "Edítalo directamente si quieres retocarlo."
        )
    existing_draft = next(
        (p for p in db.scalars(
            select(Plan).where(Plan.client_id == client_id, Plan.status == "draft")
            .order_by(Plan.month_index.desc(), Plan.version.desc())
        ) if _adapted_idx(p) == period.period_index),
        None,
    )

    nut = copy.deepcopy(base.nutrition_json or {})
    tr = copy.deepcopy(base.training_json or {})
    edu = copy.deepcopy(base.education_json or {})
    macros = nut.setdefault("macros", {})
    # ¿Qué totales tocan los ajustes? (para la coherencia+reescalado de abajo)
    kcal_touched = protein_touched = carbs_touched = fat_touched = False

    # Registro estructurado de cada ajuste (con antes→después cuando se aplica
    # automáticamente): lo consumen la pestaña Planificación del coach, el
    # desplegable "Novedades de tu plan" del portal y el PDF.
    items: list[dict] = []
    for a in adjustments:
        area = _norm(a.get("area", ""))
        change = a.get("change", "")
        cn = _norm(change)
        mode, val = _parse_change(change)
        is_diet = "diet" in area or "nutri" in area
        entry = {
            "area": "dieta" if is_diet else ("entreno" if "entren" in area else (a.get("area") or "general")),
            "change": change,
            "reason": a.get("reason") or "",
            "applied": False,
            "detail": None,
        }
        details: list[str] = []
        # "Mantener X" no es un cambio numérico: no debe tocar los macros
        # aunque el texto lleve un número ("mantener proteína en 180 g").
        if is_diet and "manten" not in cn:
            # Cada CLÁUSULA se interpreta por separado: así "subir proteína a 180
            # y bajar grasa a 55" aplica 180 a proteína y 55 a grasa (antes el
            # primer número se aplicaba a TODOS los macros nombrados → corrupción).
            clauses = [c for c in re.split(r"\s+y\s+|[,;]|\.", change) if c.strip()] or [change]
            seen: set[str] = set()
            for clause in clauses:
                c_norm = _norm(clause)
                if "manten" in c_norm:
                    continue
                c_mode, c_val = _parse_change(clause)
                if c_val is None:
                    continue
                if "proteina" in c_norm and "protein_g" not in seen:
                    before = macros.get("protein_g")
                    macros["protein_g"] = _apply(before, c_mode, c_val)
                    protein_touched = True; seen.add("protein_g")
                    details.append(f"Proteína: {round(before) if before else '—'} → {macros['protein_g']} g")
                if ("hidrato" in c_norm or "carbo" in c_norm or re.search(r"\bch\b", c_norm)) and "carbs_g" not in seen:
                    before = macros.get("carbs_g")
                    macros["carbs_g"] = _apply(before, c_mode, c_val)
                    carbs_touched = True; seen.add("carbs_g")
                    details.append(f"Carbohidratos: {round(before) if before else '—'} → {macros['carbs_g']} g")
                if ("gras" in c_norm or "lipid" in c_norm) and "fat_g" not in seen:
                    before = macros.get("fat_g")
                    macros["fat_g"] = _apply(before, c_mode, c_val)
                    fat_touched = True; seen.add("fat_g")
                    details.append(f"Grasas: {round(before) if before else '—'} → {macros['fat_g']} g")
                if ("kcal" in c_norm or "calor" in c_norm) and "target_kcal" not in seen:
                    before = nut.get("target_kcal")
                    nut["target_kcal"] = _apply(before, c_mode, c_val)
                    kcal_touched = True; seen.add("target_kcal")
                    details.append(f"Calorías: {round(before) if before else '—'} → {nut['target_kcal']} kcal")
        elif val is not None and "entren" in area:
            # En entreno solo aplicamos ajustes RELATIVOS de carga (+X kg): un
            # objetivo absoluto no se puede repartir entre todos los ejercicios.
            if mode == "delta" and "kg" in cn:
                touched = 0
                for s in tr.get("sessions", []):
                    for ex in s.get("exercises", []):
                        if ex.get("start_weight_hint_kg"):
                            ex["start_weight_hint_kg"] = round(ex["start_weight_hint_kg"] + val, 1)
                            touched += 1
                if touched:
                    details.append(f"Carga inicial: {'+' if val >= 0 else ''}{val:g} kg en {touched} ejercicios")
        if details:
            entry["applied"] = True
            entry["detail"] = " · ".join(details)
        items.append(entry)

    # COHERENCIA + REESCALADO EN BLOQUE: si algún ajuste tocó calorías o
    # macros, todo se mueve junto — kcal⇄macros coherentes (4/4/9; con solo
    # kcal, los TRES macros escalan en proporción al mix del plan) y las
    # COMIDAS y los GRAMOS del banco se reescalan a los totales nuevos (antes
    # el PDF se quedaba con los gramos antiguos).
    if kcal_touched or protein_touched or carbs_touched or fat_touched:
        from app.services.nutrition_scale import (
            kcal_of, macros_scaled_to_kcal, rescale_nutrition,
        )

        K = nut.get("target_kcal") or 0
        P = macros.get("protein_g") or 0
        C = macros.get("carbs_g") or 0
        F = macros.get("fat_g") or 0
        macro_touched = protein_touched or carbs_touched or fat_touched
        if kcal_touched and not macro_touched:
            # Solo kcal → los TRES macros en proporción a la dieta del cliente
            t = macros_scaled_to_kcal(base.nutrition_json or {}, K)
            P, C, F = t["protein_g"], t["carbs_g"], t["fat_g"]
        elif macro_touched and not kcal_touched:
            K = kcal_of(P, C, F)
        elif carbs_touched:
            # El coach fijó los carbohidratos A PROPÓSITO: se RESPETAN y las kcal
            # objetivo se DERIVAN de los macros (4/4/9), en vez de sobrescribir un
            # valor que el coach pidió y dejar el detalle contradiciendo el plan.
            K = kcal_of(P, C, F)
            for it in items:
                if it.get("detail") and "Calorías:" in it["detail"]:
                    it["detail"] = re.sub(
                        r"(Calorías: [^→]*→ )\d+( kcal)",
                        rf"\g<1>{int(round(K))}\g<2>", it["detail"],
                    )
        else:  # tocaron kcal + proteína/grasa: los carbohidratos cuadran las kcal
            C = max(0, round((K - P * 4 - F * 9) / 4))
            # El detalle "Carbohidratos: X → Y" se escribió ANTES de cuadrar:
            # se reescribe con el valor final para que Novedades y PDF cuadren.
            for it in items:
                if it.get("detail") and "Carbohidratos:" in it["detail"]:
                    it["detail"] = re.sub(
                        r"(Carbohidratos: [^→]*→ )\d+( g)",
                        rf"\g<1>{int(round(C))}\g<2>", it["detail"],
                    )
        rescale_nutrition(nut, base.nutrition_json or {}, K, P, C, F)
        items.append({
            "area": "dieta",
            "change": "Comidas y gramos del banco reescalados a los totales nuevos",
            "reason": "Coherencia automática: calorías, macros, raciones y gramos se mueven en bloque.",
            "applied": True,
            "detail": f"Totales finales: {round(K)} kcal · P {round(P)} / C {round(C)} / G {round(F)} g",
        })

    # Coherencia final garantizada: target_kcal ≡ macros (4/4/9) ≡ suma de los
    # objetivos por comida — aunque la revisión no tocara nada de nutrición o el
    # plan base venga de antes de esta invariante. Idempotente.
    from app.services.nutrition_scale import reconcile_nutrition

    _cli = db.get(Client, client_id)
    reconcile_nutrition(
        nut, weight_kg=(_cli.current_weight_kg or _cli.start_weight_kg) if _cli else None
    )
    # Ninguna toma sin contenido tras adaptar: los slots que quedaran vacíos
    # reciben 3 opciones por defecto escaladas a sus macros (nunca "toma libre").
    from app.services.meal_fallback import ensure_bank_slots

    ensure_bank_slots(
        nut,
        allergies=(_cli.food_allergies or []) if _cli else [],
        dislikes=(_cli.food_dislikes or []) if _cli else [],
    )

    # Siempre se sobreescribe (el plan base puede arrastrar el bloque de una
    # adaptación anterior tras el deepcopy).
    if items:
        nut["applied_adjustments"] = {"period_index": period.period_index, "items": items}
    else:
        nut.pop("applied_adjustments", None)

    if adjustments:
        grid = "\n".join(f"- [{a.get('area')}] {a.get('change')} — {a.get('reason')}" for a in adjustments)
        nut["rationale"] = f"Adaptación a la revisión quincenal #{period.period_index}:\n{grid}"
    else:
        nut["rationale"] = (f"Copia para adaptar a la revisión quincenal #{period.period_index} "
                            "(la revisión no incluía ajustes automáticos: edita manualmente).")
    tr["split_rationale"] = (tr.get("split_rationale", "") or "") + \
        f" · Adaptado a la revisión quincenal #{period.period_index}."

    if existing_draft is not None:
        # Rehacer el borrador existente (mismo número de versión): los ajustes
        # se recalculan siempre desde el plan publicado, nunca se acumulan.
        existing_draft.nutrition_json = nut
        existing_draft.training_json = tr
        existing_draft.education_json = edu
        plan = existing_draft
    else:
        last = db.scalar(
            select(Plan).where(Plan.client_id == client_id, Plan.month_index == base.month_index)
            .order_by(Plan.version.desc()).limit(1)
        )
        client = db.get(Client, client_id)
        plan = Plan(
            client_id=client_id, month_index=base.month_index,
            version=(last.version if last else 0) + 1, status="draft",
            nutrition_json=nut, training_json=tr, education_json=edu,
            guardrail_flags=[], generated_by="adaptación quincenal",
            goal_type=(client.goal_type if client else base.goal_type),
        )
        db.add(plan)
    db.flush()
    log_event(db, "plan", plan.id, "plan_adapted",
              {"from_plan": base.id, "period_index": period.period_index,
               "redo": existing_draft is not None})
    # La versión adaptada queda ACTIVA al momento (portal y PDF actualizados);
    # el coach puede retocarla con Editar y enviarla por WhatsApp.
    from app.services.plan_activation import activate_plan

    activate_plan(db, plan)
    db.commit()
    db.refresh(plan)
    return plan
