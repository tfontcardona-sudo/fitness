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


def _plato(opcion: dict) -> str:
    """Nombre del plato + sus ingredientes principales, para el revisor.

    El alérgeno o el alimento incompatible con el patrón casi nunca está en el
    título ("Bowl de la casa"): vive en los ingredientes. Se recortan a los
    primeros para no disparar el coste de la ronda.
    """
    if not isinstance(opcion, dict):
        return ""
    nombre = str(opcion.get("title") or opcion.get("name") or "").strip()
    ings = [str((i or {}).get("food") or "").strip()
            for i in (opcion.get("ingredients") or []) if isinstance(i, dict)]
    ings = [i for i in ings if i][:5]
    if nombre and ings:
        return f"{nombre} ({', '.join(ings)})"
    return nombre or (", ".join(ings) if ings else "")


def _plan_text(nutrition: dict, training: dict | None = None) -> str:
    """Render compacto y legible del plan (nutrición + resumen de entreno)
    para los revisores IA."""
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
    # LOS PLATOS. Sin esto los 8-10 revisores (incluido el clínico CON VETO)
    # juzgaban la dieta viendo solo kcal y macros: ni un alérgeno, ni un
    # alimento fuera del patrón dietético, ni la monotonía del menú. El campo
    # del esquema es `title` (MealOption), no `name` — leerlo mal dejaba la
    # lista vacía y la línea de opciones no se emitía nunca.
    for slot in (bank.get("slots") or [])[:8]:
        opts = [_plato(o) for o in (slot.get("options") or [])]
        opts = [o for o in opts if o]
        if opts:
            lines.append(f"  · Opciones toma {slot.get('slot', '')}: {'; '.join(opts[:4])}.")
        # EQUIVALENCIAS: cuelgan de LA TOMA (`slot.equivalences.groups`), no de
        # la raíz del banco. Se leían de `bank["equivalences"]`, una clave que
        # el esquema no declara y que nadie escribe: era código muerto. Y como
        # el prompt manda COMIDA y CENA en formato equivalencias —sus `options`
        # llegan vacías—, las DOS tomas principales no aportaban una sola línea
        # al texto que ven los 8-10 revisores IA. El coach pagaba la ronda
        # entera por un juicio cualitativo que no veía sus platos de comer y
        # cenar. (Los alérgenos y el patrón dietético SÍ estaban cubiertos: el
        # Revisor 0 determinista recorre las equivalencias por su cuenta.)
        for grupo in ((slot.get("equivalences") or {}).get("groups") or [])[:6]:
            items = [str(i.get("food") or "") for i in (grupo.get("items") or [])]
            items = [i for i in items if i]
            if items:
                lines.append(
                    f"  · Equivalencias toma {slot.get('slot', '')} "
                    f"({grupo.get('name', '')}): {', '.join(items[:8])}.")
    # MENÚ CERRADO (modo strict): el banco no trae `slots` sino `days`.
    dias = bank.get("days") or []
    for dia in dias[:3]:
        platos = [_plato(m.get("dish") or {}) for m in (dia.get("meals") or [])]
        platos = [x for x in platos if x]
        if platos:
            lines.append(f"  · {dia.get('day', 'día')}: {'; '.join(platos[:6])}.")
    if len(dias) > 3:
        lines.append(f"  · (…y {len(dias) - 3} día(s) más con el mismo estilo de menú)")
    # RESUMEN DEL ENTRENO: sin él, los roles que juzgan la coherencia
    # dieta↔entreno opinaban a ciegas (solo veían la dieta).
    if training:
        sesiones = training.get("sessions") or []
        lines.append(
            f"Entrenamiento: {training.get('split_name') or 'split'} · "
            f"{len(sesiones)} sesión(es)/semana.")
        for s in sesiones[:7]:
            ejercicios = s.get("exercises") or []
            series = sum(int(e.get("sets") or 0) for e in ejercicios)
            lines.append(f"- {s.get('day', '')} {s.get('name', '')}: "
                         f"{len(ejercicios)} ejercicios, {series} series.")
        prog = training.get("weekly_progression") or []
        if prog:
            lines.append("Progresión: " + " | ".join(
                f"sem {w.get('week')}: {w.get('intent', '')}" for w in prog[:4]))
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
        # `title`/`action` son lo que el coach ve de un vistazo en el panel; sin
        # serializarlos aquí, el contrato nuevo de los revisores moría en el
        # backend. `correccion_propuesta` viaja con su nombre completo porque el
        # frontend lo usa como acción de reserva en hallazgos antiguos.
        "findings": [{
            "severity": f.severity, "description": f.description,
            "title": f.title, "action": f.action,
            "donde": f.donde_en_el_plan,
            "correccion": f.correccion_propuesta,
            "correccion_propuesta": f.correccion_propuesta,
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
    is_checkin: bool = False, training: dict | None = None,
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
            ai, plan_text=_plan_text(plan, training), anamnesis_text=anamnesis_text,
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
    training: dict | None = None,
) -> tuple[dict, dict | None]:
    """Envoltura BEST-EFFORT para la generación: nunca lanza. Devuelve
    `(nutrition_final, review_summary_or_None)`. Ante cualquier fallo del panel,
    el plan original se devuelve intacto — pero "no revisado" no puede parecer
    "aprobado": el resumen queda en ÁMBAR degradado para que el coach lo sepa."""
    try:
        return review_and_repair(nutrition, client=client, ctx=ctx, ai=ai,
                                 objective_macros=objective_macros,
                                 training=training)
    except Exception:  # noqa: BLE001 — el panel jamás bloquea la generación
        return nutrition, {
            "color": "ambar", "icp": None, "escalated": False, "vetoed": [],
            "iterations": 0, "red_flags": [],
            "degraded_reviewers": ["panel"],
            "findings": [{
                "severity": "mayor",
                "title": "Revisión no ejecutada",
                "description": "El panel de revisión falló al completo: este "
                               "plan NO ha pasado la revisión automática.",
                "action": "Revisar el plan a mano antes de enviarlo",
                "donde": None, "correccion": None, "correccion_propuesta": None,
            }],
            "prompt_version": _prompt_version(),
        }
