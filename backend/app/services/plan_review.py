"""Enganche del panel de supervisión a la generación (hardening §9 + §11 + §12).

Tras generar un plan, corre el panel de revisores (revisor 0 determinista + 1–8
IA con contexto AISLADO), calcula el color del semáforo y el ICP, y —si hay
bloqueantes— intenta una REPARACIÓN determinista acotada (reconciliar/clamp a
rangos fisiológicos) antes de volver a evaluar. Nunca degrada el plan: el que se
persiste siempre pasó los guardrails; la reparación solo ajusta números a rango.
Si un bloqueante persiste (típicamente cualitativo, no numérico), se ESCALA: color
rojo para que el coach lo revise (no hay auto-envío).

Todo es best-effort: cualquier fallo del panel (p. ej. la API caída) devuelve el
plan intacto sin anotación, nunca bloquea la generación.
"""
from __future__ import annotations

import copy

from app.services import review_panel as rp
from app.services.nutrition_scale import reconcile_nutrition

# Nº máximo de intentos de reparación (igual que el motor del panel).
MAX_REVIEW_ITERATIONS = rp.MAX_REPAIR_ITERATIONS


def build_profile(client, ctx) -> dict:
    """Perfil que consumen el revisor 0 y la lista roja: métricas + notas clínicas."""
    from app.services.progressive_unlock import profile_from_client

    prof = profile_from_client(client)
    prof.update({
        "bmr": getattr(ctx, "bmr", None),
        "tdee": getattr(ctx, "tdee", None),
        "meals_per_day": getattr(ctx, "meals_per_day", None) or getattr(client, "meals_per_day", None),
        "food_dislikes": getattr(client, "food_dislikes", None) or [],
        "diet_pattern": getattr(client, "diet_pattern", None),
        "goal_type": getattr(client, "goal_type", None),
        "clinical_notes": getattr(ctx, "clinical_notes", None),
    })
    return prof


def _plan_text(nutrition: dict) -> str:
    """Render compacto y legible del plan de nutrición para los revisores IA."""
    m = nutrition.get("macros") or {}
    lines = [
        f"Objetivo calórico: {nutrition.get('target_kcal')} kcal "
        f"(TDEE {nutrition.get('tdee_kcal')}).",
        f"Macros/día: proteína {m.get('protein_g')} g · hidratos {m.get('carbs_g')} g · "
        f"grasa {m.get('fat_g')} g.",
    ]
    if nutrition.get("rationale"):
        lines.append(f"Racional: {nutrition['rationale']}")
    for meal in (nutrition.get("meals") or []):
        t = meal.get("target") or {}
        lines.append(
            f"- {meal.get('name')} ({meal.get('time', '')}): {t.get('kcal')} kcal, "
            f"P{t.get('protein_g')}/C{t.get('carbs_g')}/G{t.get('fat_g')}."
        )
    bank = nutrition.get("meal_bank") or {}
    for slot in (bank.get("slots") or [])[:8]:
        opts = [o.get("name") for o in (slot.get("options") or []) if o.get("name")]
        if opts:
            lines.append(f"  · Opciones {slot.get('name', '')}: {', '.join(opts[:4])}.")
    return "\n".join(lines)


def _anamnesis_text(ctx) -> str:
    """Texto de anamnesis que ve el revisor: el MISMO bloque que vio el generador."""
    from app.services.ai.generator import _client_block, _clinical_block

    parts = []
    try:
        parts.append(_client_block(ctx))
    except Exception:  # noqa: BLE001
        pass
    try:
        clinical = _clinical_block(ctx)
        if clinical:
            parts.append(clinical)
    except Exception:  # noqa: BLE001
        pass
    return "\n\n".join(p for p in parts if p) or "(anamnesis no disponible)"


def summarize(panel: rp.PanelResult, *, iterations: int, escalated: bool) -> dict:
    """Resumen persistible del resultado del panel (lo que verá el coach)."""
    return {
        "color": panel.color,
        "icp": panel.icp,
        "escalated": escalated,
        "vetoed": panel.vetoed,
        "iterations": iterations,
        "red_flags": panel.red_flags,
        # Revisores IA que no llegaron a ejecutarse (API caída): el coach ve
        # que la revisión está DEGRADADA en vez de creerla completa.
        "degraded_reviewers": list(getattr(panel, "degraded_reviewers", []) or []),
        "findings": [{
            "severity": f.severity, "description": f.description,
            "donde": f.donde_en_el_plan, "correccion": f.correccion_propuesta,
        } for f in panel.findings[:20]],
        "prompt_version": _prompt_version(),
    }


def _prompt_version() -> str:
    try:
        from app.services.plan_stability import PROMPT_VERSION
        return PROMPT_VERSION
    except Exception:  # noqa: BLE001
        return ""


def review_and_repair(
    nutrition: dict, *, client, ctx, ai=None, objective_macros: dict | None = None,
    is_checkin: bool = False,
) -> tuple[dict, dict]:
    """Corre el panel con reparación determinista acotada.

    Devuelve `(nutrition_final, review_summary)`. `nutrition_final` siempre es un
    plan válido (el original o su reconciliación a rango). `ai` debe exponer
    `generate_json` (AIClient); si es None, corre solo el revisor 0 (determinista).
    """
    profile = build_profile(client, ctx)
    anamnesis_text = _anamnesis_text(ctx)
    criterios_text = _criterios_text()
    weight_kg = getattr(ctx, "weight_kg", None) or getattr(client, "current_weight_kg", None)

    def reviewer_for(plan: dict):
        if ai is None:
            return None
        return rp.make_ai_reviewer(
            ai, plan_text=_plan_text(plan), anamnesis_text=anamnesis_text,
            criterios_text=criterios_text,
        )

    current = nutrition

    # AHORRO (auditoría de costes): antes los 8-10 roles IA se pagaban ANTES de
    # cualquier reparación, y el caso típico (la IA se desvió en números → el
    # clamp lo arregla) costaba DOS pasadas completas del panel. Ahora:
    # 1) El Revisor 0 (código, coste 0) se consulta primero: si veta, se
    #    repara EN SECO antes de pagar un solo rol — el panel corre ya sobre
    #    el plan reparado y la iteración extra desaparece. Si el Revisor 0
    #    aprueba, no se toca nada (mismo comportamiento de siempre).
    det = rp.deterministic_reviewer(current, profile, objective_macros=objective_macros)
    if det.veredicto == "rechazado":
        repaired = reconcile_nutrition(copy.deepcopy(current), weight_kg, clamp=True)
        if repaired != current:
            current = repaired

    # 2) Las banderas ROJAS del perfil (edad, IMC, patologías) son INVARIANTES
    #    entre iteraciones: con banderas, el panel queda vetado SIEMPRE y
    #    reintentar solo repaga los roles para acabar igual. Una sola pasada
    #    (sus hallazgos siguen siendo útiles para el coach) y escalado.
    try:
        from app.services.safety_gate import red_flags as _red_flags

        max_iter = 1 if _red_flags(profile) else MAX_REVIEW_ITERATIONS
    except Exception:  # noqa: BLE001 — ante la duda, comportamiento clásico
        max_iter = MAX_REVIEW_ITERATIONS

    panel = None
    for i in range(1, max_iter + 1):
        panel = rp.run_panel(current, profile, objective_macros=objective_macros,
                             ai_reviewer=reviewer_for(current), is_checkin=is_checkin)
        if not panel.blocking() and not panel.vetoed:
            return current, summarize(panel, iterations=i, escalated=False)
        # Reparación DETERMINISTA acotada: reconciliar/clamp a rangos fisiológicos.
        repaired = reconcile_nutrition(copy.deepcopy(current), weight_kg, clamp=True)
        if repaired == current or i == max_iter:
            # No hay cambio numérico que reparar (bloqueante cualitativo) o se agotó
            # el margen: se ESCALA (rojo) y se conserva el plan válido actual.
            return current, summarize(panel, iterations=i, escalated=True)
        current = repaired

    return current, summarize(panel, iterations=max_iter, escalated=True)


def _criterios_text() -> str:
    try:
        from app.services.ai.prompts import criterios_reference
        return criterios_reference()
    except Exception:  # noqa: BLE001
        return ""


def review_generated_plan(
    nutrition: dict, *, client, ctx, ai=None, objective_macros: dict | None = None,
) -> tuple[dict, dict | None]:
    """Envoltura BEST-EFFORT para la generación: nunca lanza. Devuelve
    `(nutrition_final, review_summary_or_None)`. Ante cualquier fallo del panel,
    el plan original se devuelve intacto y sin anotación (color None)."""
    try:
        return review_and_repair(nutrition, client=client, ctx=ctx, ai=ai,
                                 objective_macros=objective_macros)
    except Exception:  # noqa: BLE001 — el panel jamás bloquea la generación
        return nutrition, None
