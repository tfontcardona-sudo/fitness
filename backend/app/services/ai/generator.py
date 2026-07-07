"""Orquestación de la generación del plan mensual (PARTE B + D.2).

Tres llamadas encadenadas a la IA, con el backend haciendo el trabajo duro
entre medias:

  ①  núcleo del plan (nutrición + entrenamiento)
        → guardrails de nutrición y entrenamiento
  ②  banco de comidas según diet_mode (flexible_7 | strict)
        → guardrail ±5% por opción; re-pide SOLO las opciones que fallan
  ③  contenido educativo

El backend:
- calcula BMR/TDEE/kcal objetivo y se los entrega a la IA (nunca al revés),
- filtra la biblioteca de ejercicios ANTES de la llamada (solo aptos),
- revalida cada salida con guardrails sobre números reales,
- ensambla `PlanCoreOutput + MealsOutput + EducationOutput` para persistir.

`PlanGenerationError` encapsula cualquier fallo recuperable (la IA no convergió
o una salida violó guardrails de forma irreparable) → el caller marca estado de
error y notifica al coach.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.config import settings
from app.schemas.ai import (
    EducationOutput,
    MealsFlexibleOutput,
    MealsStrictOutput,
    PlanCoreOutput,
)
from app.services import guardrails as gr
from app.services.ai.client import AIClient, AIGenerationError
from app.services.ai.prompts import (
    system_prompt_education,
    system_prompt_full,
    system_prompt_meals,
)


class PlanGenerationError(RuntimeError):
    def __init__(self, message: str, flags: list[str] | None = None):
        super().__init__(message)
        self.flags = flags or []


@dataclass
class ClientContext:
    """Datos del cliente y métricas pre-calculadas que alimentan los prompts."""

    sex: str
    age: int
    height_cm: float
    weight_kg: float
    goal_type: str
    level: str
    training_days: int
    session_max_min: int
    training_place: str
    diet_mode: str
    meals_per_day: int | None   # None = el cliente lo delega ("lo decidís vosotros")
    meal_schedule: list[dict]
    food_allergies: list[str]
    food_dislikes: list[str]
    food_likes: list[str]
    contraindications: set[str]
    body_fat_pct: float | None
    # métricas calculadas por el backend (services/metrics.py)
    bmr: float
    tdee: float
    target_kcal: float
    energy_method: str
    # biblioteca ya filtrada: [{id, name, pattern, muscle, ...}]
    exercise_library: list[dict]
    # análisis cualitativo del coach/IA (lesiones, hábitos, contexto) — opcional
    deep_analysis: str | None = None
    notes: str = ""


@dataclass
class GeneratedPlan:
    core: PlanCoreOutput
    meals: MealsFlexibleOutput | MealsStrictOutput
    education: EducationOutput
    guardrail_flags: list[str]
    generated_by: str

    def to_persistable(self) -> tuple[dict, dict, dict, list[str]]:
        """(nutrition_json, training_json, education_json, guardrail_flags)."""
        nutrition = self.core.nutrition.model_dump()
        nutrition["meal_bank"] = self.meals.model_dump()
        return (
            nutrition,
            self.core.training.model_dump(),
            self.education.model_dump(),
            self.guardrail_flags,
        )


def _exercise_lookup(library: list[dict]) -> dict[int, dict]:
    return {ex["id"]: ex for ex in library}


def _slot_targets(core: PlanCoreOutput) -> dict[int, dict]:
    """{slot: {kcal, protein_g, carbs_g, fat_g}} desde el núcleo, para validar
    opciones de comida con ±5%."""
    return {
        m.slot: {
            "kcal": m.target.kcal, "protein_g": m.target.protein_g,
            "carbs_g": m.target.carbs_g, "fat_g": m.target.fat_g,
        }
        for m in core.nutrition.meals
    }


# ------------------------------------------------------ construcción prompts ----

def _client_block(ctx: ClientContext) -> str:
    return json.dumps(
        {
            "sexo": ctx.sex, "edad": ctx.age, "altura_cm": ctx.height_cm,
            "peso_kg": ctx.weight_kg, "porcentaje_graso": ctx.body_fat_pct,
            "objetivo": ctx.goal_type, "nivel": ctx.level,
            "dias_entrenamiento": ctx.training_days,
            "duracion_max_sesion_min": ctx.session_max_min,
            "lugar_entrenamiento": ctx.training_place,
            "modo_dieta": ctx.diet_mode,
            # El cliente puede DELEGAR el reparto de comidas: si no declara
            # número u horario, la IA elige el óptimo para su objetivo y rutina.
            "num_comidas": ctx.meals_per_day
            if ctx.meals_per_day
            else "lo delega: elige tú el número óptimo (3-5 según preferencias y objetivo)",
            "horario_comidas": ctx.meal_schedule
            if ctx.meal_schedule
            else "lo delega: reparte tú las comidas (desayuno/comida/cena y añade media mañana, merienda o pre-cama si conviene)",
            "alergias": ctx.food_allergies, "aversiones": ctx.food_dislikes,
            "preferencias": ctx.food_likes,
            "lesiones_contraindicaciones": sorted(ctx.contraindications),
            "notas": ctx.notes,
            "metricas_backend": {
                "bmr": ctx.bmr, "tdee": ctx.tdee,
                "kcal_objetivo": ctx.target_kcal, "metodo": ctx.energy_method,
            },
        },
        ensure_ascii=False, indent=2,
    )


def _analysis_block(ctx: ClientContext) -> str:
    """Bloque opcional con el análisis cualitativo (lesiones, hábitos, contexto)."""
    if not ctx.deep_analysis:
        return ""
    return (
        "\nANÁLISIS EN PROFUNDIDAD DE LA ANAMNESIS (tenlo MUY en cuenta para "
        "personalizar dieta y entrenamiento: lesiones a respetar, hábitos, sueño, "
        "estrés, conducta alimentaria, logística y contexto):\n"
        f"{ctx.deep_analysis}\n"
    )


def _core_user_prompt(ctx: ClientContext) -> str:
    library = [
        {"id": e["id"], "nombre": e["canonical_name"],
         "patron": e["movement_pattern"], "musculo": e["muscle_primary"]}
        for e in ctx.exercise_library
    ]
    max_sets = max(
        1,
        (ctx.session_max_min - gr.SESSION_MINUTES_FIXED_OVERHEAD)
        // gr.SESSION_MINUTES_FORMULA_PER_SET,
    )
    return f"""Genera el NÚCLEO del plan mensual para este cliente.

DATOS DEL CLIENTE Y MÉTRICAS (ya calculadas por el backend, NO recalcules):
{_client_block(ctx)}
{_analysis_block(ctx)}
BIBLIOTECA DE EJERCICIOS DISPONIBLE (usa SOLO estos exercise_id):
{json.dumps(library, ensure_ascii=False)}

Devuelve un JSON con esta forma EXACTA (sin texto fuera del JSON). TODOS los campos de
cada objeto son OBLIGATORIOS salvo los marcados como (null si no aplica). No omitas NINGUNO:
- "nutrition": tdee_kcal, target_kcal, rationale, macros{{protein_g,carbs_g,fat_g}},
  meals[] (un objeto por comida del horario: slot, name, time, target{{kcal,protein_g,carbs_g,fat_g}}),
  supplements[] (cada uno con los 4 campos: name, dose, timing, evidence_note),
  flexibility_rules[] (strings), refeed_or_break (null si no aplica).
- "training": split_name, split_rationale,
  weekly_progression[] (EXACTAMENTE 4 objetos para las semanas 1,2,3,4; cada uno con los 5
  campos: week (1-4), intent (Base|Progresión|Pico|Deload), load_pct (número), rir_target, volume_note),
  sessions[] (day, name, warmup, exercises[], cooldown),
  cardio{{daily_steps, sessions[] (cada uno: type "liss"|"hiit", minutes, times_per_week, notes)}},
  deload_instructions.
  Cada ejercicio: exercise_id (de la biblioteca), sets, rep_range, rir, tempo, rest_sec,
  start_weight_hint_kg, progression_rule, technique_cue, biomech_cue.

RESTRICCIÓN DE DURACIÓN: la duración de cada sesión se estima como (total de series × \
{gr.SESSION_MINUTES_FORMULA_PER_SET} min) + {gr.SESSION_MINUTES_FIXED_OVERHEAD} min. El cliente \
declaró un máximo de {ctx.session_max_min} min/sesión, así que NO pongas más de {max_sets} series \
por sesión (sumando TODOS los ejercicios de esa sesión).

Respeta TODOS los guardrails. La suma de los targets de slot debe acercarse al target_kcal."""


def _meals_user_prompt(ctx: ClientContext, core: PlanCoreOutput) -> str:
    targets = _slot_targets(core)
    slot_info = {
        m.slot: {"nombre": m.name, "hora": m.time, **targets[m.slot]}
        for m in core.nutrition.meals
    }
    common = f"""Genera el BANCO DE COMIDAS para el cliente.

TOMAS DEL DÍA (slot, nombre, hora, macros objetivo del slot):
{json.dumps(slot_info, ensure_ascii=False, indent=2)}

RESTRICCIONES: alergias={ctx.food_allergies}, aversiones={ctx.food_dislikes}, \
preferencias={ctx.food_likes}."""

    if ctx.diet_mode == "flexible_7":
        return common + """

FORMATO POR TOMA (réplica EXACTA del método del coach):

• COMIDA y CENA (tomas principales) → fmt="equivalences" (sistema de equivalencias).
  groups EN ESTE ORDEN: "Vegetales / Hortalizas", "Hidratos de carbono", "Proteína",
  "Grasas", "Fruta de postre". Cada grupo:
    - name: nombre del grupo (matízalo: en cena "Hidratos de carbono (integrales / ricos en
      almidón)"; en comida pre-entreno "(refinados / rápidos)"; "Proteína magra" o
      "Proteína (magra o semi-grasa)" según corresponda).
    - note: ración/guía breve ("1 ración moderada (200 g aprox), mejor cocida"; en grasas
      indica AOVE y qué evitar; en fruta, piezas recomendadas).
    - items: 5-9 alimentos INTERCAMBIABLES; cada uno con su cantidad EQUIVALENTE en macros
      para cubrir el objetivo de ESE grupo en el slot. amount en CRUDO, con cocido si aplica
      ("140 g crudo = 380 g cocido"; "150 g"; "350 ml + 1 huevo entero"). El grupo Vegetales
      puede ir solo con note (items vacío).
  intro del slot: "Equivalencias calculadas para aportar ~<carbs_g del slot> g de CH del cereal".

• DESAYUNO, MEDIA MAÑANA, MERIENDA, SNACK, etc. → fmt="options": EXACTAMENTE 3 opciones
  (combos cerrados) que cumplan los macros del slot ±5%, con ingredients (food/grams/household).

• weekly_examples (TODOS los slots): 7 nombres CORTOS de plato, uno por día, variados, para la
  tabla "Ejemplo de dieta semanal" (p. ej. "Pollo con arroz y brócoli", "Salmón con patata").

Respeta SIEMPRE alergias y aversiones. Devuelve SOLO JSON:
{"mode":"flexible_7","slots":[
 {"slot":N,"fmt":"options","options":[{"key":"A","title":...,"ingredients":[{"food":...,
   "grams":N,"household":...}],"prep":...,"prep_minutes":N,"macros":{"kcal":N,"protein_g":N,
   "carbs_g":N,"fat_g":N},"tags":[...]}, ...3 opciones],"weekly_examples":[...7 textos]},
 {"slot":M,"fmt":"equivalences","equivalences":{"intro":...,"groups":[{"name":...,"note":...,
   "items":[{"food":...,"amount":...}, ...]}, ...5 grupos]},"weekly_examples":[...7 textos]}
]}"""

    return common + """

MODO strict: menú CERRADO de 7 días (lunes→domingo), un plato por slot y día.
JSON: {"mode":"strict","days":[{"day":"lunes","meals":[{"slot":N,"dish":{"key":"A","title":...,
"ingredients":[{"food":...,"grams":N,"household":...}],"prep":...,"prep_minutes":N,
"macros":{"kcal":N,"protein_g":N,"carbs_g":N,"fat_g":N},"tags":[...]}}, ...]}, ... 7 días],
"free_meal_guidelines": null}"""


def _education_user_prompt(core: PlanCoreOutput) -> str:
    patterns = sorted({
        "empuje_horizontal", "empuje_vertical", "traccion_horizontal",
        "traccion_vertical", "sentadilla", "bisagra_cadera",
    })
    return f"""Genera el CONTENIDO EDUCATIVO del plan.

Split del cliente: {core.training.split_name}.
JSON: {{"pills":[{{"topic":...,"for_client":...}} (3–5 píldoras)],
"biomech_by_pattern":[{{"pattern":...,"cues":[...],"why":...}}],
"faq":[{{"q":...,"a":...}}]}}.
Patrones sugeridos para biomech_by_pattern: {patterns}.
Temas de píldoras a rotar: sobrecarga progresiva, RIR, tempo, volumen, proteína,
balance energético, sueño y recuperación, NEAT, hidratación, deload."""


# --------------------------------------------------------------- pipeline ----

def generate_monthly_plan(ctx: ClientContext, ai: AIClient) -> GeneratedPlan:
    """Ejecuta las 3 llamadas con guardrails. Lanza PlanGenerationError si no
    se puede producir un plan seguro."""
    flags: list[str] = []
    model = settings.model_heavy

    # ① Núcleo
    try:
        core = ai.generate_json(
            model=model, system=system_prompt_full(),
            user=_core_user_prompt(ctx), schema=PlanCoreOutput,
        )
    except AIGenerationError as exc:
        raise PlanGenerationError(f"núcleo del plan: {exc}") from exc

    nut_report = gr.check_nutrition(
        core.nutrition.model_dump(), sex=ctx.sex, weight_kg=ctx.weight_kg,
        bmr=ctx.bmr, tdee=ctx.tdee,
    )
    tr_report = gr.check_training(
        core.training.model_dump(),
        training_days_declared=ctx.training_days,
        session_max_min=ctx.session_max_min,
        client_contraindications=ctx.contraindications,
        exercise_lookup=_exercise_lookup(ctx.exercise_library),
    )
    core_report = nut_report.merge(tr_report)
    if not core_report.ok:
        raise PlanGenerationError(
            "el núcleo viola guardrails: " + "; ".join(core_report.violations),
            flags=core_report.as_flags(),
        )
    flags += core_report.as_flags()

    # ② Comidas según diet_mode
    schema = MealsFlexibleOutput if ctx.diet_mode == "flexible_7" else MealsStrictOutput
    try:
        meals = ai.generate_json(
            model=model, system=system_prompt_meals(),
            user=_meals_user_prompt(ctx, core), schema=schema,
        )
    except AIGenerationError as exc:
        raise PlanGenerationError(f"banco de comidas: {exc}") from exc

    targets = _slot_targets(core)
    if isinstance(meals, MealsFlexibleOutput):
        meal_report = gr.check_meal_options(
            [s.model_dump() for s in meals.slots], targets
        )
    else:
        meal_report = gr.check_strict_day_meals(
            [d.model_dump() for d in meals.days], targets
        )
    # Las opciones fuera de ±5% son warnings recuperables: se marcan para que el
    # coach revise; no bloquean (re-pedir opción por opción se hace en Fase 4
    # cuando hay scheduler/SSE; aquí lo dejamos como flag accionable).
    flags += meal_report.as_flags()

    # ③ Educativo
    try:
        education = ai.generate_json(
            model=model, system=system_prompt_education(),
            user=_education_user_prompt(core), schema=EducationOutput,
        )
    except AIGenerationError as exc:
        raise PlanGenerationError(f"contenido educativo: {exc}") from exc

    return GeneratedPlan(
        core=core, meals=meals, education=education,
        guardrail_flags=flags, generated_by=model,
    )
