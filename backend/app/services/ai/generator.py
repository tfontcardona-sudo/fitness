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
    NutritionCore,
    NutritionOnlyCoreOutput,
    PlanCoreOutput,
    TrainingCore,
)
from app.services import guardrails as gr
from app.services.ai.client import AIClient, AIGenerationError
from app.services.ai.prompts import (
    system_prompt_education,
    system_prompt_full,
    system_prompt_meals,
    system_prompt_nutrition_only,
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
    # Objetivo EN PALABRAS DEL CLIENTE ("Motivo y objetivos" de la anamnesis +
    # estilo de vida): la IA debe entender QUÉ pide exactamente y diseñar dieta
    # y entrenamiento para ese fin, no solo para la etiqueta goal_type.
    goal_in_own_words: str | None = None
    # Notas clínicas textuales (lesiones, patologías, medicación, suplementos):
    # condicionan la seguridad del plan y NO se pueden ignorar.
    clinical_notes: str | None = None
    # Historial real de seguimiento (revisiones: peso/adherencia/fuerza) para
    # que la IA entienda el recorrido del cliente, no solo su anamnesis.
    tracking_history: dict | None = None


@dataclass
class GeneratedPlan:
    nutrition: NutritionCore
    meals: MealsFlexibleOutput | MealsStrictOutput
    # training/education son None en el paquete Start (solo-nutrición).
    training: TrainingCore | None
    education: EducationOutput | None
    guardrail_flags: list[str]
    generated_by: str

    def to_persistable(self) -> tuple[dict, dict | None, dict | None, list[str]]:
        """(nutrition_json, training_json, education_json, guardrail_flags).
        training_json/education_json van a None cuando el plan es solo-nutrición."""
        nutrition = self.nutrition.model_dump()
        nutrition["meal_bank"] = self.meals.model_dump()
        return (
            nutrition,
            self.training.model_dump() if self.training is not None else None,
            self.education.model_dump() if self.education is not None else None,
            self.guardrail_flags,
        )


def _exercise_lookup(library: list[dict]) -> dict[int, dict]:
    return {ex["id"]: ex for ex in library}


def _strip_allergens_from_bank(meals, allergies: list[str] | None) -> int:
    """Retira del banco flexible las OPCIONES y ALIMENTOS de equivalencias que
    contengan un alérgeno declarado, siempre que quede una alternativa segura en
    ese slot/grupo. Así un alérgeno no llega al portal ni al PDF (ambos leen el
    banco). Si no queda alternativa segura, se conserva y el flag ⚠ ALÉRGENO
    (violación) queda para que el coach lo resuelva. Devuelve cuántos retiró."""
    if not allergies:
        return 0
    removed = 0
    for s in meals.slots:
        opts = s.options or []
        if opts:
            safe = [o for o in opts if gr.option_allergen(o.model_dump(), allergies) is None]
            if safe and len(safe) < len(opts):
                removed += len(opts) - len(safe)
                s.options = safe
        eq = s.equivalences
        if eq and eq.groups:
            for g in eq.groups:
                items = g.items or []
                if not items:
                    continue
                safe_i = [it for it in items if gr.food_allergen(it.food, allergies) is None]
                if safe_i and len(safe_i) < len(items):
                    removed += len(items) - len(safe_i)
                    g.items = safe_i
    return removed


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
            # Lo que el cliente ESCRIBIÓ sobre su objetivo y su vida: analízalo
            # y diseña el plan para conseguir EXACTAMENTE lo que pide.
            "objetivo_en_palabras_del_cliente": ctx.goal_in_own_words
            or "no declarado: guíate por el objetivo estructurado",
            "alergias": ctx.food_allergies, "aversiones": ctx.food_dislikes,
            "preferencias": ctx.food_likes,
            "lesiones_contraindicaciones": sorted(ctx.contraindications),
            "notas": ctx.notes,
            "historial_seguimiento": ctx.tracking_history
            or "cliente nuevo: sin historial todavía",
            "metricas_backend": {
                "bmr": ctx.bmr, "tdee": ctx.tdee,
                "kcal_objetivo": ctx.target_kcal, "metodo": ctx.energy_method,
            },
        },
        ensure_ascii=False, indent=2,
    )


def _pathology_rules(clinical_notes: str) -> str:
    """Pautas ESPECÍFICAS por patología detectada en las notas clínicas. Reglas
    dietéticas concretas (no consejo médico) que la IA debe aplicar; el criterio
    médico del cliente siempre prevalece."""
    if not clinical_notes:
        return ""
    import unicodedata
    t = unicodedata.normalize("NFKD", clinical_notes).encode("ascii", "ignore").decode("ascii").lower()
    rules: list[str] = []
    if any(k in t for k in ("diabet", "glucemia", "insulina", "metformina", "hba1c", "prediabet", "resistencia a la insulina")):
        rules.append(
            "DIABETES / control glucémico: prioriza carbohidratos de ÍNDICE GLUCÉMICO "
            "BAJO (integrales, legumbres, avena, verduras, fruta entera); REPARTE los "
            "carbohidratos entre las comidas (evita concentrarlos) y acompáñalos "
            "siempre de proteína, grasa y fibra para amortiguar el pico; EVITA azúcares "
            "y refinados de absorción rápida salvo indicación médica expresa; horarios "
            "de comida regulares. No prescribas ayunos prolongados."
        )
    if any(k in t for k in ("hipotiroid", "levotirox", "eutirox", "tiroides", "tirox")):
        rules.append(
            "HIPOTIROIDISMO: el gasto puede ser algo menor y la adherencia cuesta más; "
            "sé CONSERVADOR con el déficit (evita déficits agresivos) y prioriza "
            "proteína alta y comida real; recuerda (nota educativa) tomar la "
            "levotiroxina EN AYUNAS y separada ~30-60 min de café, calcio, hierro y "
            "soja/derivados; asegura micronutrientes (selenio, zinc)."
        )
    if any(k in t for k in ("hipertiroid",)):
        rules.append(
            "HIPERTIROIDISMO: las necesidades energéticas pueden estar elevadas; no "
            "apliques déficits agresivos y asegura suficiente energía y proteína."
        )
    if not rules:
        return ""
    return "\nPAUTAS ESPECÍFICAS POR PATOLOGÍA (aplícalas en la dieta):\n- " + "\n- ".join(rules) + "\n"


def _clinical_block(ctx: ClientContext) -> str:
    """Bloque CLÍNICO obligatorio: lesiones, patologías, medicación y suplementos.
    Es lo que condiciona la SEGURIDAD del plan — la IA no puede ignorarlo."""
    if not ctx.clinical_notes:
        return ""
    return (
        "\n⚠️ SALUD DEL CLIENTE — RESTRICCIONES OBLIGATORIAS (prioridad máxima; "
        "el plan de dieta Y de entrenamiento DEBE adaptarse a esto sin excepción):\n"
        f"{ctx.clinical_notes}\n"
        "REGLAS DURAS: (1) NO incluyas ejercicios que carguen una zona lesionada o "
        "con molestias; sustitúyelos por alternativas seguras del mismo patrón y "
        "explica el motivo en technique_cue/biomech_cue. (2) La dieta debe EXCLUIR "
        "por completo cualquier alimento con alergia o intolerancia declarada y "
        "tener en cuenta patologías (p. ej. tiroides, digestivas) y la medicación. "
        "(3) Si algo limita el volumen o la intensidad, refléjalo en la progresión.\n"
        f"{_pathology_rules(ctx.clinical_notes)}"
    )


def _analysis_block(ctx: ClientContext) -> str:
    """Bloque opcional con el análisis cualitativo (hábitos, contexto)."""
    if not ctx.deep_analysis:
        return ""
    return (
        "\nANÁLISIS EN PROFUNDIDAD DE LA ANAMNESIS (tenlo MUY en cuenta para "
        "personalizar dieta y entrenamiento: hábitos, sueño, estrés, conducta "
        "alimentaria, logística y contexto):\n"
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
{_clinical_block(ctx)}
{_analysis_block(ctx)}
IMPORTANTE: lee "objetivo_en_palabras_del_cliente" y entiende EXACTAMENTE qué
quiere conseguir esta persona (y por qué). El plan de dieta Y el de
entrenamiento deben estar diseñados para ESE fin concreto, no solo para la
etiqueta genérica del objetivo. Refléjalo en rationale y split_rationale.

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
  campos: week (1-4), intent (Base|Progresión|Pico|Deload), load_pct (número), rir_target, volume_note).
  La PERIODIZACIÓN debe seguir la evidencia SEGÚN EL OBJETIVO del cliente (load_pct relativo a
  la semana base = 100): ganancia muscular/recomposición → onda de sobrecarga progresiva
  (100 → 102.5 → 105) con deload real (60-70, volumen −40/50%); pérdida de grasa → misma onda
  conservando intensidad ALTA para retener masa (el volumen puede bajar algo en el déficit);
  recuperación de lesión → progresión suave (100 → 102.5 máx.), RIR alto (3-4) y deload
  temprano; mantenimiento → onda moderada. En volume_note explica QUÉ debe hacer esa semana y
  con qué intención (el cliente lo lee en su portal).
  sessions[] (day, name, warmup, exercises[], cooldown),
  cardio{{daily_steps, sessions[] (cada uno: type "liss"|"hiit", minutes, times_per_week, notes)}},
  deload_instructions.
  Cada ejercicio: exercise_id (de la biblioteca), sets, rep_range, rir, tempo, rest_sec,
  start_weight_hint_kg, progression_rule, technique_cue, biomech_cue.

ENTRENAMIENTO BASADO EN EVIDENCIA (hipertrofia y biomecánica; aplica estos
principios y explícalos en split_rationale, technique_cue y biomech_cue):
- VOLUMEN por grupo muscular: ~10-20 series semanales efectivas como rango
  productivo (Schoenfeld/Krieger); ajusta según nivel (principiante hacia el
  límite bajo, avanzado más alto) y capacidad de recuperación del cliente.
- FRECUENCIA: cada músculo ≥2 veces/semana reparte mejor el volumen que 1
  (mejor calidad de series). Distribuye el split para lograrlo con sus días.
- INTENSIDAD y PROXIMIDAD AL FALLO: la mayoría de series a RIR 1-3 (cerca del
  fallo sin llegar siempre); rango 5-30 reps hipertrofia si se acerca al fallo,
  priorizando 6-12 en básicos y 10-20 en accesorios/aislamientos.
- SELECCIÓN por BIOMECÁNICA y ROM: cubre cada músculo en posiciones de
  estiramiento (evidencia reciente favorece el trabajo en elongación) y
  distintos vectores/curvas de resistencia; elige ejercicios cuyo perfil de
  fuerza case con la función del músculo. Justifícalo en biomech_cue.
- SOBRECARGA PROGRESIVA: progression_rule concreta (añadir reps dentro del
  rango y luego carga; doble progresión). technique_cue con el punto clave de
  ejecución seguro y eficaz.
- SEGÚN OBJETIVO: fuerza/músculo → más carga y básicos pesados; pérdida de
  grasa → mantener intensidad para retener masa, volumen ajustado a la
  recuperación en déficit; lesión → ROM sin dolor y progresión conservadora.
- Respeta descansos por objetivo del ejercicio (2-3 min básicos pesados,
  1-2 min accesorios) en rest_sec.

RESTRICCIÓN DE DURACIÓN: la duración de cada sesión se estima como (total de series × \
{gr.SESSION_MINUTES_FORMULA_PER_SET} min) + {gr.SESSION_MINUTES_FIXED_OVERHEAD} min. El cliente \
declaró un máximo de {ctx.session_max_min} min/sesión, así que NO pongas más de {max_sets} series \
por sesión (sumando TODOS los ejercicios de esa sesión).

DIETA RAZONADA POR EVIDENCIA: en rationale explica de forma breve y directa el
porqué (déficit/superávit sobre el TDEE según objetivo, proteína alta para
preservar/ganar masa, reparto de macros), sin tecnicismos innecesarios.

Respeta TODOS los guardrails. La suma de los targets de slot debe acercarse al target_kcal."""


def _core_user_prompt_nutrition_only(ctx: ClientContext) -> str:
    """Núcleo SOLO-NUTRICIÓN (paquete Start): mismo bloque de datos clínicos y de
    contexto que el completo, pero se pide EXCLUSIVAMENTE la nutrición (sin
    entrenamiento ni biblioteca de ejercicios)."""
    return f"""Genera el NÚCLEO DE NUTRICIÓN del plan mensual para este cliente.

Este cliente tiene un paquete SOLO NUTRICIÓN: NO generes entrenamiento (ni split,
ni sesiones, ni progresión, ni cardio). Céntrate al 100% en la dieta.

DATOS DEL CLIENTE Y MÉTRICAS (ya calculadas por el backend, NO recalcules):
{_client_block(ctx)}
{_clinical_block(ctx)}
{_analysis_block(ctx)}
IMPORTANTE: lee "objetivo_en_palabras_del_cliente" y entiende EXACTAMENTE qué
quiere conseguir esta persona (y por qué). La dieta debe estar diseñada para ESE
fin concreto, no solo para la etiqueta genérica del objetivo. Refléjalo en rationale.

Devuelve un JSON con esta forma EXACTA (sin texto fuera del JSON). TODOS los campos son
OBLIGATORIOS salvo los marcados como (null si no aplica). No omitas NINGUNO:
- "nutrition": tdee_kcal, target_kcal, rationale, macros{{protein_g,carbs_g,fat_g}},
  meals[] (un objeto por comida del horario: slot, name, time, target{{kcal,protein_g,carbs_g,fat_g}}),
  supplements[] (cada uno con los 4 campos: name, dose, timing, evidence_note),
  flexibility_rules[] (strings), refeed_or_break (null si no aplica).

DIETA RAZONADA POR EVIDENCIA: en rationale explica de forma breve y directa el
porqué (déficit/superávit sobre el TDEE según objetivo, proteína alta para
preservar/ganar masa, reparto de macros), sin tecnicismos innecesarios.

Respeta TODOS los guardrails de nutrición. La suma de los targets de slot debe
acercarse al target_kcal."""


def _meals_user_prompt(ctx: ClientContext, core: PlanCoreOutput) -> str:
    targets = _slot_targets(core)
    slot_info = {
        m.slot: {"nombre": m.name, "hora": m.time, **targets[m.slot]}
        for m in core.nutrition.meals
    }
    common = f"""Genera el BANCO DE COMIDAS para el cliente.

TOMAS DEL DÍA (slot, nombre, hora, macros objetivo del slot):
{json.dumps(slot_info, ensure_ascii=False, indent=2)}

PROHIBIDO (NINGÚN plato puede contenerlo — seguridad): \
alergias/intolerancias={ctx.food_allergies}, aversiones={ctx.food_dislikes}. \
PREFERIR / INCLUIR cuando encaje en los macros (alimentos que le gustan): {ctx.food_likes}.\
{(' SALUD A TENER EN CUENTA EN LA DIETA (patologías, medicación, digestivo): ' + ctx.clinical_notes.replace(chr(10), ' ')) if ctx.clinical_notes else ''}"""

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
    - items: alimentos INTERCAMBIABLES, cada uno con su cantidad EQUIVALENTE en macros
      para cubrir el objetivo de ESE grupo en el slot. VARIEDAD AMPLIA — el cliente debe
      poder elegir: Hidratos de carbono 9-12 alimentos; Proteína 7-10; Grasas 4-6; Fruta 4-6.
      amount en CRUDO, con cocido si aplica ("140 g crudo = 380 g cocido"; "150 g";
      "350 ml + 1 huevo entero"). El grupo Vegetales puede ir solo con note (items vacío).
  intro del slot: "Equivalencias calculadas para aportar ~<carbs_g del slot> g de CH del cereal".

• DESAYUNO, MEDIA MAÑANA, MERIENDA, SNACK, etc. → fmt="options": EXACTAMENTE 3 opciones
  (combos cerrados) que cumplan los macros del slot ±5%, con ingredients (food/grams/household).

• OBLIGATORIO: TODAS las tomas del listado deben aparecer en slots CON contenido (opciones o
  equivalencias). Ninguna toma puede quedar vacía o "libre": al cliente siempre se le dan
  opciones concretas, no se le complica la vida.

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

def generate_monthly_plan(
    ctx: ClientContext, ai: AIClient, include_training: bool = True
) -> GeneratedPlan:
    """Ejecuta las llamadas con guardrails y devuelve el plan.

    - include_training=True (Full/Pro): núcleo (nutrición + entrenamiento) →
      comidas → educativo.
    - include_training=False (Start, solo-nutrición): núcleo de nutrición →
      comidas. Sin entrenamiento ni educativo (que trata de entreno).

    Lanza PlanGenerationError si no se puede producir un plan seguro."""
    flags: list[str] = []
    model = settings.model_heavy

    # ① Núcleo
    if include_training:
        try:
            core = ai.generate_json(
                model=model, system=system_prompt_full(),
                user=_core_user_prompt(ctx), schema=PlanCoreOutput,
            )
        except AIGenerationError as exc:
            raise PlanGenerationError(f"núcleo del plan: {exc}") from exc
        training_core: TrainingCore | None = core.training
    else:
        # Solo-nutrición: ni entrenamiento ni biblioteca de ejercicios.
        try:
            core = ai.generate_json(
                model=model, system=system_prompt_nutrition_only(),
                user=_core_user_prompt_nutrition_only(ctx),
                schema=NutritionOnlyCoreOutput,
            )
        except AIGenerationError as exc:
            raise PlanGenerationError(f"núcleo de nutrición: {exc}") from exc
        training_core = None

    # Coherencia numérica ANTES de nada: target_kcal ≡ macros (4/4/9) ≡ suma de
    # los objetivos por comida. Así la IA nunca deja un plan donde un apartado
    # diga X kcal y otro diga otro número, y el banco de comidas (paso ②) se pide
    # contra unos objetivos por slot ya cuadrados. Es idempotente.
    from app.services.nutrition_scale import reconcile_nutrition

    # clamp=False: los guardrails de abajo deben ver los números REALES de la
    # IA y bloquear si son peligrosos (no corregirlos en silencio).
    core.nutrition = NutritionCore.model_validate(
        reconcile_nutrition(core.nutrition.model_dump(), weight_kg=ctx.weight_kg,
                            clamp=False)
    )

    nut_report = gr.check_nutrition(
        core.nutrition.model_dump(), sex=ctx.sex, weight_kg=ctx.weight_kg,
        bmr=ctx.bmr, tdee=ctx.tdee,
    )
    if training_core is not None:
        tr_report = gr.check_training(
            training_core.model_dump(),
            training_days_declared=ctx.training_days,
            session_max_min=ctx.session_max_min,
            client_contraindications=ctx.contraindications,
            exercise_lookup=_exercise_lookup(ctx.exercise_library),
        )
        core_report = nut_report.merge(tr_report)
    else:
        core_report = nut_report
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
            [s.model_dump() for s in meals.slots], targets,
            allergies=ctx.food_allergies, dislikes=ctx.food_dislikes,
        )
    else:
        meal_report = gr.check_strict_day_meals(
            [d.model_dump() for d in meals.days], targets,
            allergies=ctx.food_allergies, dislikes=ctx.food_dislikes,
        )
    # Las opciones fuera de ±5% son warnings recuperables: se marcan para que el
    # coach revise; no bloquean (re-pedir opción por opción se hace en Fase 4
    # cuando hay scheduler/SSE; aquí lo dejamos como flag accionable).
    flags += meal_report.as_flags()

    # SEGURIDAD: retira del banco cualquier opción/alimento con un alérgeno
    # declarado (cuando queda alternativa segura), para que un alérgeno NUNCA
    # llegue al portal ni al PDF por un descuido de la IA. Si un slot quedara sin
    # alternativa segura, se conserva y el flag "⚠ ALÉRGENO" avisa al coach.
    if isinstance(meals, MealsFlexibleOutput):
        removed = _strip_allergens_from_bank(meals, ctx.food_allergies)
        if removed:
            flags.append(f"seguridad: retiradas {removed} opción(es)/alimento(s) con alérgenos del banco")

    # ③ Educativo (solo con entrenamiento: las píldoras y la biomecánica giran
    #    en torno al entreno; en solo-nutrición no aplica).
    education: EducationOutput | None = None
    if include_training:
        try:
            education = ai.generate_json(
                model=model, system=system_prompt_education(),
                user=_education_user_prompt(core), schema=EducationOutput,
            )
        except AIGenerationError as exc:
            raise PlanGenerationError(f"contenido educativo: {exc}") from exc

    return GeneratedPlan(
        nutrition=core.nutrition, meals=meals, training=training_core,
        education=education, guardrail_flags=flags, generated_by=model,
    )
