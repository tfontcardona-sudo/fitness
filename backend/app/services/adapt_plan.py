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
    # Separador de MILES fuera antes de leer el número: "2.100 kcal" es 2100,
    # no 2.1 (el punto solo es de miles si le siguen exactamente 3 dígitos).
    text = re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", text or "")
    m = re.search(r"([+-]?\d+(?:[.,]\d+)?)", text)
    if not m:
        return (None, None)
    val = float(m.group(1).replace(",", "."))
    # "un 10%" / "10 %" es un cambio RELATIVO: antes se aplicaba como −10 g /
    # −10 kcal (auditoría #11). El signo lo pone el verbo (subir/bajar).
    tail = (text or "")[m.end():m.end() + 3]
    if "%" in tail:
        if re.search(r"\b(baj|reduc|menos|quit|resta|recort|dismin)", t):
            return ("pct", -abs(val))
        return ("pct", abs(val))
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
    """Aplica un delta, un % relativo o un objetivo absoluto (suelo >= 0)."""
    if mode == "pct":
        base_v = float(current or 0)
        return int(max(floor, round(base_v * (1 + val / 100.0))))
    result = val if mode == "abs" else (current or 0) + val
    return int(round(max(floor, result)))


# Reglas del motor quincenal → texto legible: las Novedades del portal y la
# pestaña del coach no pueden hablar en clave interna ("dato_insuficiente").
_RULE_ES = {
    "adherencia_baja": "primero hay que asentar la adherencia",
    "dato_insuficiente": "faltan datos de peso para decidir con garantías",
    "posible_ciclo_menstrual": "el repunte de peso puede ser del ciclo menstrual",
    "fatiga_roja_2_revisiones": "hay señales de fatiga acumulada",
    "recomposicion_en_marcha": "la recomposición va en marcha",
    "dentro_del_ritmo": "el ritmo actual es el buscado",
    "sin_cambio_neto": "no hay cambio neto que corregir",
    "deriva_no_deseada": "el peso deriva sin buscarlo",
    "fuera_del_ritmo": "el ritmo se ha salido del rango buscado",
}


def _regla_legible(decision: dict) -> str:
    rule = str(decision.get("rule") or "")
    return _RULE_ES.get(rule, rule.replace("_", " ")
                        or "la revisión automática lo desaconseja")


def _calibrar_pesos_desde_registros(db: Session, period: Period, tr: dict) -> int:
    """Aprende del feedback REAL de las rutinas: fija la carga de arranque de
    cada ejercicio al último peso que el cliente registró en el período (la
    mejor serie de su último día, redondeada a 0,5 kg). Devuelve cuántos tocó."""
    import math

    from app.models import DailyLog, WorkoutLog

    rows = db.execute(
        select(WorkoutLog.exercise_id, DailyLog.log_date, WorkoutLog.weight_kg)
        .join(DailyLog, WorkoutLog.daily_log_id == DailyLog.id)
        .where(DailyLog.period_id == period.id, WorkoutLog.weight_kg.is_not(None))
    ).all()
    ultimo: dict[int, tuple] = {}
    for ex_id, log_date, w in rows:
        if ex_id is None or w is None:
            continue
        prev = ultimo.get(ex_id)
        if prev is None or log_date > prev[0] or (log_date == prev[0] and float(w) > prev[1]):
            ultimo[ex_id] = (log_date, float(w))
    if not ultimo:
        return 0
    n = 0
    for s in tr.get("sessions", []) or []:
        for ex in s.get("exercises", []) or []:
            reg = ultimo.get(ex.get("exercise_id"))
            if not reg or reg[1] <= 0:
                continue
            nuevo = math.floor(reg[1] * 2 + 0.5) / 2  # a 0,5 kg, half-up
            if ex.get("start_weight_hint_kg") != nuevo:
                ex["start_weight_hint_kg"] = nuevo
                n += 1
    return n


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

    # §8 (hardening): la decisión DETERMINISTA del motor quincenal MANDA sobre
    # las calorías. El texto libre de la IA no puede contradecirla: si la regla
    # dice "no tocar kcal" (hold/adherencia/datos insuficientes) se veta el
    # cambio; si dice "ajustar X%", el número lo pone el motor, no el modelo.
    decision = (period.ai_analysis_json or {}).get("biweekly_decision") or {}
    d_action = decision.get("action")
    d_pct = float(decision.get("kcal_delta_pct") or 0)
    kcal_vetoed = d_action in ("hold", "work_adherence", "request_data")
    kcal_engine = d_action == "adjust_kcal" and abs(d_pct) > 0.01

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
        # En un plan solo-entreno el sello vive en training_json (no hay dieta).
        return (((p.nutrition_json or {}).get("applied_adjustments")
                 or (p.training_json or {}).get("applied_adjustments")
                 or {})).get("period_index")

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
    # Qué incluye el plan base DE VERDAD: un plan solo-entreno no debe salir de
    # aquí con una "dieta" vacía fabricada (antes nutrition_json acababa como
    # {} con macros/rationale y el PDF/portal imprimían una dieta en blanco).
    tiene_dieta = bool(base.nutrition_json)
    tiene_entreno = bool(base.training_json)
    # La adaptación no arrastra el rastro de ediciones del plan base: los
    # cambios manuales pendientes de avisar pertenecen a la versión anterior.
    nut.pop("manual_changes", None)
    macros = nut.setdefault("macros", {}) if tiene_dieta else {}
    # ¿Qué totales tocan los ajustes? (para la coherencia+reescalado de abajo)
    kcal_touched = protein_touched = carbs_touched = fat_touched = False

    # Registro estructurado de cada ajuste (con antes→después cuando se aplica
    # automáticamente): lo consumen la pestaña Planificación del coach, el
    # desplegable "Novedades de tu plan" del portal y el PDF.
    items: list[dict] = []

    # APRENDER DEL FEEDBACK DE LAS RUTINAS: antes de aplicar nada, la carga de
    # arranque de cada ejercicio se calibra con el último peso que el cliente
    # registró en el período — el plan nuevo arranca donde lo dejó, y los
    # ajustes relativos ("+2,5 kg") se aplican sobre esa base real.
    if tiene_entreno:
        try:
            calibrados = _calibrar_pesos_desde_registros(db, period, tr)
        except Exception:  # noqa: BLE001 — la calibración nunca rompe adaptar
            calibrados = 0
        if calibrados:
            items.append({
                "area": "entreno",
                "change": "Cargas de arranque calibradas con tus registros",
                "reason": "El plan nuevo arranca donde lo dejaste: el último "
                          "peso que registraste en cada ejercicio.",
                "applied": True,
                "detail": f"{calibrados} ejercicio(s) puestos al día con tu último peso registrado",
            })
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
        if is_diet and not tiene_dieta:
            entry["detail"] = "No aplicado: este plan no incluye dieta"
        elif is_diet and "manten" not in cn:
            # Cada CLÁUSULA se interpreta por separado: así "subir proteína a 180
            # y bajar grasa a 55" aplica 180 a proteína y 55 a grasa (antes el
            # primer número se aplicaba a TODOS los macros nombrados → corrupción).
            # Los números se NORMALIZAN antes de trocear: "2.100 kcal" lleva un
            # punto de MILES y ",5" una coma decimal — sin esto, el split por
            # [.,] partía "Reducir calorías a 2.100" en "…a 2" + "100 kcal" y
            # fijaba target_kcal=2 (auditoría crítica). El punto solo trocea
            # frases si va seguido de espacio o fin de texto.
            change_norm_num = re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", change)
            change_norm_num = re.sub(r"(?<=\d),(?=\d)", ".", change_norm_num)
            clauses = [c for c in re.split(r"\s+y\s+|[,;]|\.(?=\s|$)", change_norm_num)
                       if c.strip()] or [change_norm_num]
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
                    seen.add("target_kcal")
                    if kcal_vetoed:
                        details.append(
                            "Calorías: no se tocan en esta revisión — "
                            + _regla_legible(decision))
                    elif kcal_engine:
                        details.append(
                            "Calorías: las fija la revisión automática (ver el ajuste de abajo)")
                    else:
                        before = nut.get("target_kcal")
                        nut["target_kcal"] = _apply(before, c_mode, c_val)
                        kcal_touched = True
                        details.append(f"Calorías: {round(before) if before else '—'} → {nut['target_kcal']} kcal")
        elif "entren" in area and not tiene_entreno:
            entry["detail"] = "No aplicado: este plan no incluye entrenamiento"
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

    # Ajuste de calorías del MOTOR (§8): número determinista sobre el plan base,
    # con la proteína bloqueada (los carbohidratos hacen de colchón más abajo).
    if kcal_engine and tiene_dieta:
        before_k = nut.get("target_kcal") or 0
        if before_k:
            import math
            nut["target_kcal"] = int(math.floor(before_k * (1 + d_pct / 100) + 0.5))
            kcal_touched = True
            protein_touched = True  # enruta al cuadre con proteína/grasa fijas
            items.append({
                "area": "dieta",
                "change": f"Calorías {'+' if d_pct > 0 else ''}{d_pct:g}% (revisión automática)",
                "reason": decision.get("rationale")
                or "Revisión automática: reglas fijas sobre tu progreso real.",
                "applied": True,
                "detail": f"Calorías: {round(before_k)} → {nut['target_kcal']} kcal · proteína bloqueada",
            })

    # DIET BREAK (§8): la decisión "diet_break" era solo texto — nadie la
    # aplicaba. Ahora sube las calorías a mantenimiento (TDEE) con la proteína
    # bloqueada; el coach revisa, y a los 7-10 días adapta de nuevo o revierte.
    kcal_salto_por_diseno = False
    if d_action == "diet_break" and tiene_dieta:
        before_k = nut.get("target_kcal") or 0
        tdee_k = float(nut.get("tdee_kcal") or 0)
        razon = (decision.get("rationale")
                 or "Revisión automática: descanso de dieta para recuperar antes de seguir.")
        if before_k and tdee_k:
            import math
            nut["target_kcal"] = int(math.floor(tdee_k + 0.5))
            kcal_touched = True
            protein_touched = True  # enruta al cuadre con proteína/grasa fijas
            # Subir a mantenimiento puede superar el ±15% de recalibración: es
            # un salto POR DISEÑO (el TDEE lo calculó el backend), no un
            # desmadre de la IA — el tope no aplica a este movimiento.
            kcal_salto_por_diseno = True
            items.append({
                "area": "dieta",
                "change": "Diet break: 7-10 días comiendo a mantenimiento",
                "reason": razon,
                "applied": True,
                "detail": f"Calorías: {round(before_k)} → {nut['target_kcal']} kcal (mantenimiento) · proteína bloqueada",
            })
        else:
            items.append({
                "area": "dieta",
                "change": "Diet break: 7-10 días comiendo a mantenimiento",
                "reason": razon,
                "applied": False,
                "detail": "No aplicado automáticamente (el plan no tiene TDEE "
                          "guardado): sube las calorías a mantenimiento a mano.",
            })

    # COHERENCIA + REESCALADO EN BLOQUE: si algún ajuste tocó calorías o
    # macros, todo se mueve junto — kcal⇄macros coherentes (4/4/9; con solo
    # kcal, los TRES macros escalan en proporción al mix del plan) y las
    # COMIDAS y los GRAMOS del banco se reescalan a los totales nuevos (antes
    # el PDF se quedaba con los gramos antiguos).
    if tiene_dieta and (kcal_touched or protein_touched or carbs_touched or fat_touched):
        from app.services.nutrition_scale import (
            kcal_of, macros_scaled_to_kcal, rescale_nutrition,
        )

        K = nut.get("target_kcal") or 0
        P = macros.get("protein_g") or 0
        C = macros.get("carbs_g") or 0
        F = macros.get("fat_g") or 0
        macro_touched = protein_touched or carbs_touched or fat_touched
        if kcal_vetoed and macro_touched and not kcal_engine:
            # El §8 vetó las kcal: un cambio de macros de la IA no puede
            # convertirse en un cambio ENERGÉTICO por la puerta de atrás
            # ("bajar hidratos a 120 g" con hold = −400 kcal reales, auditoría
            # #4). Se respetan los macros pedidos y el resto REBALANCEA hasta
            # las kcal previas: primero los ejes NO tocados (C→G→P), y si se
            # tocaron los tres, escala proporcional.
            K = nut.get("target_kcal") or kcal_of(P, C, F)
            gap = K - kcal_of(P, C, F)
            if abs(gap) > 2:
                buffers = [(name, per) for name, touched, per in (
                    ("carbs_g", carbs_touched, 4), ("fat_g", fat_touched, 9),
                    ("protein_g", protein_touched, 4)) if not touched]
                for name, per in buffers:
                    cur = float(macros.get(name) or 0)
                    move = gap / per
                    new = max(0.0, cur + move)
                    gap -= (new - cur) * per
                    macros[name] = int(round(new))
                    if abs(gap) <= 2:
                        break
                if abs(gap) > 2 and kcal_of(
                        macros.get("protein_g") or 0, macros.get("carbs_g") or 0,
                        macros.get("fat_g") or 0) > 0:
                    r = K / kcal_of(macros.get("protein_g") or 0,
                                    macros.get("carbs_g") or 0,
                                    macros.get("fat_g") or 0)
                    for name in ("protein_g", "carbs_g", "fat_g"):
                        macros[name] = int(round(float(macros.get(name) or 0) * r))
                P = macros.get("protein_g") or 0
                C = macros.get("carbs_g") or 0
                F = macros.get("fat_g") or 0
                items.append({
                    "area": "dieta",
                    "change": "Macros rebalanceados a las calorías previas",
                    "reason": "La revisión automática indica no tocar las "
                              "calorías: el cambio de macros se aplica sin "
                              "alterar la energía total.",
                    "applied": True,
                    "detail": f"Totales mantenidos en {round(K)} kcal",
                })
        elif kcal_touched and not macro_touched:
            # Solo kcal → los TRES macros en proporción a la dieta del cliente
            t = macros_scaled_to_kcal(base.nutrition_json or {}, K)
            P, C, F = t["protein_g"], t["carbs_g"], t["fat_g"]
        elif macro_touched and not kcal_touched:
            K = kcal_of(P, C, F)
        elif carbs_touched and not kcal_engine:
            # El coach fijó los carbohidratos A PROPÓSITO: se RESPETAN y las kcal
            # objetivo se DERIVAN de los macros (4/4/9), en vez de sobrescribir un
            # valor que el coach pidió y dejar el detalle contradiciendo el plan.
            # (Salvo que el MOTOR haya fijado las kcal: entonces mandan las kcal
            # del motor y los carbohidratos vuelven a hacer de colchón.)
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
    _cli = db.get(Client, client_id)
    from app.services.periods import reference_weight_kg

    if tiene_dieta:
        from app.services.nutrition_scale import reconcile_nutrition

        reconcile_nutrition(
            nut, weight_kg=reference_weight_kg(db, _cli) if _cli else None
        )
        # Ninguna toma sin contenido tras adaptar: los slots que quedaran vacíos
        # reciben 3 opciones por defecto escaladas a sus macros (nunca "toma libre").
        from app.services.meal_fallback import ensure_bank_slots

        ensure_bank_slots(
            nut,
            allergies=(_cli.food_allergies or []) if _cli else [],
            dislikes=(_cli.food_dislikes or []) if _cli else [],
            diet_pattern=_cli.diet_pattern if _cli else None,
        )
        # El snapshot de inputs se REFRESCA: la alerta plan_stale_inputs debe
        # comparar contra la ficha con la que se ADAPTÓ, no contra la de la
        # generación original (si no, "ficha cambiada tras generar" no se
        # apagaba nunca en los planes adaptados).
        if _cli is not None:
            nut["gen_inputs"] = {
                "weight_kg": reference_weight_kg(db, _cli),
                "height_cm": _cli.height_cm,
                "level": _cli.level, "training_days": _cli.training_days,
                "training_place": _cli.training_place, "diet_mode": _cli.diet_mode,
                "diet_pattern": _cli.diet_pattern,
            }

    # Los DETALLES que verá el cliente ("Proteína: 150 → X g", "Totales
    # finales…") se reescriben con los valores FINALES tras los topes
    # fisiológicos: si un ajuste de la IA se acotó (p. ej. "proteína a 400 g"
    # clampado a 210), las Novedades y el PDF no pueden prometer un número que
    # el plan real no lleva.
    _fm = (nut.get("macros") or {}) if tiene_dieta else {}
    _finales = (
        ("Proteína", _fm.get("protein_g"), "g"),
        ("Carbohidratos", _fm.get("carbs_g"), "g"),
        ("Grasas", _fm.get("fat_g"), "g"),
        ("Calorías", nut.get("target_kcal"), "kcal"),
    )
    for it in items:
        d = it.get("detail")
        if not d:
            continue
        for _label, _v, _unit in _finales:
            if isinstance(_v, (int, float)):
                d = re.sub(rf"({_label}: [^→·]*→ )\d+( {_unit})",
                           rf"\g<1>{int(round(_v))}\g<2>", d)
        d = re.sub(
            r"(Totales finales: )\d+( kcal · P )\d+( / C )\d+( / G )\d+( g)",
            rf"\g<1>{int(round(nut.get('target_kcal') or 0))}"
            rf"\g<2>{int(round(_fm.get('protein_g') or 0))}"
            rf"\g<3>{int(round(_fm.get('carbs_g') or 0))}"
            rf"\g<4>{int(round(_fm.get('fat_g') or 0))}\g<5>", d)
        it["detail"] = d

    # Siempre se sobreescribe (el plan base puede arrastrar el bloque de una
    # adaptación anterior tras el deepcopy). En un plan solo-entreno el sello
    # vive en training_json — antes se escribía en una nutrición fantasma y
    # ni el coach ni el portal veían las Novedades.
    if items:
        destino = nut if tiene_dieta else tr
        destino["applied_adjustments"] = {"period_index": period.period_index, "items": items}
        (tr if tiene_dieta else nut).pop("applied_adjustments", None)
    else:
        nut.pop("applied_adjustments", None)
        tr.pop("applied_adjustments", None)

    if tiene_dieta:
        # OJO: `rationale` LO LEE EL CLIENTE (sale en el PDF como "Por qué este
        # enfoque"). Aquí se machacaba con texto interno —un volcado con
        # etiquetas de máquina "- [dieta] … — …", que además repite la tabla
        # "Cambios de tu plan" de justo debajo, o directamente una instrucción
        # para el coach ("edita manualmente")— y el argumentario real del plan
        # se perdía para siempre: del mes 2 en adelante ningún cliente volvía a
        # leer por qué su plan es como es.
        # El detalle de la adaptación YA viaja por `applied_adjustments`.
        # Y NO SE ACUMULA: la marca lleva el número de la revisión, así que
        # cada quincena añadía OTRO párrafo idéntico. En el mes 4 el cliente
        # abría "Por qué este enfoque" y encontraba ocho veces la misma frase.
        # Se retira la coletilla de las revisiones anteriores y se pone la de
        # esta — el argumentario original (lo que de verdad explica su plan)
        # queda intacto delante.
        base_rationale = (nut.get("rationale") or "").strip()
        base_rationale = re.sub(
            r"\n*Ajustado tras tu revisión #\d+:[^\n]*", "", base_rationale).strip()
        marca = f"Ajustado tras tu revisión #{period.period_index}"
        nut["rationale"] = (
            f"{base_rationale}\n\n{marca}: mantenemos el enfoque y afinamos "
            "las cifras con lo que has registrado estas dos semanas."
            if base_rationale else
            f"{marca}: afinamos las cifras con lo que has registrado estas "
            "dos semanas."
        )
    if tiene_entreno:
        # Misma regla que el rationale: la coletilla SUSTITUYE a la de la
        # revisión anterior en vez de encadenarse. Esto se imprime en el PDF
        # bajo "Estructura ·", y a la sexta quincena era una ristra de
        # "· Adaptado a la revisión quincenal #1. · … #2. · … #3." que tapaba
        # la razón real del split.
        _split = re.sub(r"\s*·\s*Adaptado a la revisión quincenal #\d+\.", "",
                        tr.get("split_rationale", "") or "").rstrip()
        tr["split_rationale"] = (
            _split + f" · Adaptado a la revisión quincenal #{period.period_index}.")

    if existing_draft is not None:
        # Rehacer el borrador existente (mismo número de versión): los ajustes
        # se recalculan siempre desde el plan publicado, nunca se acumulan.
        existing_draft.nutrition_json = nut if tiene_dieta else None
        existing_draft.training_json = tr if tiene_entreno else None
        existing_draft.education_json = edu or None
        plan = existing_draft
    else:
        # Mes de asesoría: dos revisiones = un mes. La adaptación de la 2ª, 4ª…
        # revisión ABRE mes nuevo (antes se quedaba en el del plan base y el
        # cliente veía "Mes 1" indefinidamente). Nunca retrocede.
        from app.services.periods import current_month_index

        month_index = max(base.month_index, current_month_index(db, client_id))
        last = db.scalar(
            select(Plan).where(Plan.client_id == client_id, Plan.month_index == month_index)
            .order_by(Plan.version.desc()).limit(1)
        )
        client = db.get(Client, client_id)
        plan = Plan(
            client_id=client_id, month_index=month_index,
            version=(last.version if last else 0) + 1, status="draft",
            nutrition_json=(nut if tiene_dieta else None),
            training_json=(tr if tiene_entreno else None),
            education_json=edu or None,
            guardrail_flags=[], generated_by="adaptación quincenal",
            goal_type=(client.goal_type if client else base.goal_type),
        )
        db.add(plan)
    db.flush()
    log_event(db, "plan", plan.id, "plan_adapted",
              {"from_plan": base.id, "period_index": period.period_index,
               "redo": existing_draft is not None})

    # Guardarraíl ANTES de activar (auditoría #4): la adaptación se auto-activaba
    # sin re-validar nutrición — cambios acumulados podían dejar activo un plan
    # bajo el suelo por sexo o con ±% fuera de rango. Mismo patrón que la
    # generación: con violación queda en BORRADOR retenido y el coach decide.
    from app.services.guardrails import check_nutrition

    violations: list[str] = []
    if tiene_dieta:
        try:
            _c = db.get(Client, client_id)
            rep = check_nutrition(
                nut,
                sex=(_c.sex if _c else None) or "male",
                weight_kg=float((_c.current_weight_kg or _c.start_weight_kg or 0) if _c else 0) or 70.0,
                bmr=0.0,  # sin BMR fiable aquí: aplica el suelo por sexo igualmente
                tdee=float(nut.get("tdee_kcal") or 0),
                is_recalibration=True,
                previous_target_kcal=(
                    None if kcal_salto_por_diseno
                    else float((base.nutrition_json or {}).get("target_kcal") or 0) or None),
            )
            violations = [f"violation: {v}" for v in rep.violations]
        except Exception:  # noqa: BLE001 — el chequeo nunca rompe la adaptación
            violations = []
    if violations:
        plan.guardrail_flags = violations + [
            "retenido: adaptación guardada como BORRADOR — revisa y activa tú "
            "(el cliente no ha sido avisado)"
        ]
        db.commit()
        db.refresh(plan)
        return plan

    # La versión adaptada queda ACTIVA al momento (portal y PDF actualizados);
    # el coach puede retocarla con Editar y enviarla por WhatsApp. El AVISO al
    # cliente ("plan nuevo") solo sale si el feedback de esta revisión ya se
    # ENVIÓ: si aún es borrador, avisar aquí filtraba la revisión por la puerta
    # de atrás antes de que el coach la mandara.
    from app.models import FeedbackDoc
    from app.services.plan_activation import activate_plan

    fb = db.scalar(
        select(FeedbackDoc).where(FeedbackDoc.period_id == period.id)
        .order_by(FeedbackDoc.id.desc()).limit(1)
    )
    activate_plan(db, plan, notify=bool(fb and fb.sent_at))
    db.commit()
    db.refresh(plan)
    return plan
