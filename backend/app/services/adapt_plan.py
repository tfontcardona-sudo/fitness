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

from app.models import Period, Plan
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

    base = db.scalar(
        select(Plan).where(Plan.client_id == client_id, Plan.status == "published")
        .order_by(Plan.version.desc()).limit(1)
    ) or db.scalar(
        select(Plan).where(Plan.client_id == client_id).order_by(Plan.version.desc()).limit(1)
    )
    if not base:
        raise AdaptError("El cliente no tiene un plan base que adaptar.")

    nut = copy.deepcopy(base.nutrition_json or {})
    tr = copy.deepcopy(base.training_json or {})
    edu = copy.deepcopy(base.education_json or {})
    macros = nut.setdefault("macros", {})

    for a in adjustments:
        area = _norm(a.get("area", ""))
        change = a.get("change", "")
        cn = _norm(change)
        mode, val = _parse_change(change)
        if val is None:
            continue
        if "diet" in area or "nutri" in area:
            if "proteina" in cn:
                macros["protein_g"] = _apply(macros.get("protein_g"), mode, val)
            if "hidrato" in cn or "carbo" in cn or re.search(r"\bch\b", cn):
                macros["carbs_g"] = _apply(macros.get("carbs_g"), mode, val)
            if ("kcal" in cn or "calor" in cn) and "manten" not in cn:
                nut["target_kcal"] = _apply(nut.get("target_kcal"), mode, val)
        elif "entren" in area:
            # En entreno solo aplicamos ajustes RELATIVOS de carga (+X kg): un
            # objetivo absoluto no se puede repartir entre todos los ejercicios.
            if mode == "delta" and "kg" in cn:
                for s in tr.get("sessions", []):
                    for ex in s.get("exercises", []):
                        if ex.get("start_weight_hint_kg"):
                            ex["start_weight_hint_kg"] = round(ex["start_weight_hint_kg"] + val, 1)

    if adjustments:
        grid = "\n".join(f"- [{a.get('area')}] {a.get('change')} — {a.get('reason')}" for a in adjustments)
        nut["rationale"] = f"Adaptación a la revisión quincenal #{period.period_index}:\n{grid}"
    else:
        nut["rationale"] = (f"Copia para adaptar a la revisión quincenal #{period.period_index} "
                            "(la revisión no incluía ajustes automáticos: edita manualmente).")
    tr["split_rationale"] = (tr.get("split_rationale", "") or "") + \
        f" · Adaptado a la revisión quincenal #{period.period_index}."

    last = db.scalar(
        select(Plan).where(Plan.client_id == client_id, Plan.month_index == base.month_index)
        .order_by(Plan.version.desc()).limit(1)
    )
    new_version = (last.version if last else 0) + 1
    plan = Plan(
        client_id=client_id, month_index=base.month_index, version=new_version, status="draft",
        nutrition_json=nut, training_json=tr, education_json=edu,
        guardrail_flags=[], generated_by="adaptación quincenal",
    )
    db.add(plan)
    db.flush()
    log_event(db, "plan", plan.id, "plan_adapted",
              {"from_plan": base.id, "period_index": period.period_index})
    db.commit()
    db.refresh(plan)
    return plan
