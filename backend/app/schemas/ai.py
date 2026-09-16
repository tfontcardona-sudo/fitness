"""Schemas Pydantic de las salidas de IA — contratos C.2, C.3 y C.4.

Las 3 llamadas orquestadas devuelven JSON validado contra estos modelos:
  ① PlanCoreOutput   — núcleo del plan (nutrición estructural + entrenamiento)
  ② MealsOutput      — banco de comidas según diet_mode (flexible_7 | strict)
  ③ EducationOutput  — píldoras educativas, biomecánica por patrón y FAQ

La validación aritmética de macros (±5%) y los guardrails E.4/F.4 son del
backend (Fase 3); aquí se valida estructura, tipos y cardinalidades.
"""


from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator

# La duración del ciclo y del mesociclo vive en un solo sitio (el módulo que
# además resuelve "qué toca hoy"): si mañana el tope sube de 10, sube aquí.
from app.services.training_cycle import (
    MAX_BLOQUES,
    MAX_DIAS_CICLO,
    MIN_DIAS_CICLO,
    SEMANA,
)

# ============================================================ llamada ① ====


# ⚠️ Las `description` de estos Field son DOCUMENTACIÓN para quien lee el código:
# NO llegan al modelo. `AIClient.generate_json` solo envía `system` y `user`; el
# schema se usa exclusivamente para `model_validate`. Todo tope de longitud que
# deba cumplir la IA hay que escribirlo TAMBIÉN en el prompt (prompts.py /
# generator.py), que es lo único que viaja.

class Macros(BaseModel):
    protein_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)


class MealSlotTarget(BaseModel):
    kcal: float = Field(gt=0)
    protein_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)


class MealSlotDef(BaseModel):
    slot: int = Field(ge=1)
    name: str
    time: str  # "08:00"
    target: MealSlotTarget


class Supplement(BaseModel):
    name: str
    dose: str
    timing: str
    # nota informativa; opcional para no tumbar el plan si la IA la omite
    evidence_note: str = Field(
        default="", description="MÁXIMO 10 palabras. Ej.: 'Evidencia sólida en fuerza'."
    )


class NutritionCore(BaseModel):
    tdee_kcal: float = Field(gt=0)
    target_kcal: float = Field(gt=0)
    rationale: str = Field(
        description=(
            "POR QUÉ de este enfoque, MÁXIMO 2 frases cortas (~35 palabras). "
            "Directo y sin relleno: no repitas las cifras que ya salen en la tabla "
            "ni añadas frases motivacionales."
        )
    )
    macros: Macros
    meals: list[MealSlotDef] = Field(min_length=1)
    supplements: list[Supplement] = Field(default_factory=list)
    flexibility_rules: list[str] = Field(default_factory=list)
    refeed_or_break: str | None = Field(
        default=None,
        description="Una sola línea telegráfica (~15 palabras). null si no aplica.",
    )

    @model_validator(mode="after")
    def slots_unicos_y_ordenados(self) -> "NutritionCore":
        slots = [m.slot for m in self.meals]
        if len(set(slots)) != len(slots):
            raise ValueError("slots de comida duplicados")
        if slots != sorted(slots):
            raise ValueError("los slots deben venir ordenados")
        return self


class WeeklyProgressionWeek(BaseModel):
    # Un "week" es UNA VUELTA AL CICLO (un bloque del mesociclo). Con el ciclo
    # de siempre —7 días— una vuelta es una semana y esto se lee igual que
    # antes; con un ciclo de 10 días, el bloque 2 empieza el día 11.
    week: int = Field(ge=1, le=MAX_BLOQUES)
    intent: str = Field(description="UNA palabra: Base | Progresión | Pico | Deload")
    load_pct: float = Field(gt=0)
    rir_target: str
    volume_note: str = Field(
        description=(
            "TELEGRÁFICO: MÁXIMO 12 palabras, sin frases completas. "
            "Ej.: 'Series ÷2 · carga −30% · lejos del fallo'. "
            "Nada de explicar el porqué ni de motivar: solo la instrucción."
        )
    )


class PlannedExercise(BaseModel):
    exercise_id: int = Field(ge=1)  # SOLO ids de la biblioteca inyectada (F.3)
    sets: int = Field(ge=1, le=10)
    rep_range: str  # "6-8"
    rir: str  # "2" | "1-2"
    tempo: str | None = None
    rest_sec: int = Field(ge=15, le=600)
    start_weight_hint_kg: float | None = Field(default=None, ge=0)
    progression_rule: str = Field(
        description=(
            "Regla de subida en MÁXIMO 12 palabras, con la cifra. "
            "Ej.: 'Completas 4×8 a RIR 2 → +2,5 kg'."
        )
    )
    technique_cue: str = Field(
        description="Una orden accionable de MÁXIMO 10 palabras. Ej.: 'Codos a 45°, baja controlado'."
    )
    biomech_cue: str = Field(
        description="El porqué en MÁXIMO 10 palabras. Ej.: 'Protege el hombro y aísla el pectoral'."
    )
    # Indicaciones PERSONALIZADAS del coach para ESTE cliente (capacidades,
    # limitaciones, adaptación del ejercicio). Las escribe el coach en el editor;
    # el cliente las ve destacadas en su portal y en el PDF.
    coach_notes: str | None = None


class TrainingSession(BaseModel):
    day: str  # "Lunes"… con ciclo semanal; "Día 3" con ciclo rotativo
    # Qué día del CICLO ocupa (1…cycle_days). Es lo que hace que un split de 10
    # días sea posible: sin él, "qué toca hoy" solo se puede resolver por el
    # nombre del día de la semana. Opcional por compatibilidad: en los planes
    # de siempre se deduce del nombre (`training_cycle.indice_de_dia`).
    day_index: int | None = Field(default=None, ge=1, le=MAX_DIAS_CICLO)
    name: str  # "Upper A"
    warmup: str = Field(
        description="MÁXIMO 15 palabras separadas por '·'. Ej.: '5 min bici · movilidad hombro · 2 series ligeras'."
    )
    exercises: list[PlannedExercise] = Field(min_length=1)
    cooldown: str = Field(description="MÁXIMO 12 palabras, separadas por '·'.")


class CardioSession(BaseModel):
    type: Literal["liss", "hiit"]
    minutes: int = Field(ge=5, le=120)
    times_per_week: int = Field(ge=1, le=7)
    notes: str | None = Field(default=None, description="MÁXIMO 12 palabras. null si no aporta.")


class CardioPlan(BaseModel):
    daily_steps: int = Field(ge=0, le=30000)
    sessions: list[CardioSession] = Field(default_factory=list)


class TrainingCore(BaseModel):
    split_name: str
    split_rationale: str = Field(
        description="POR QUÉ esta división, en UNA frase de máximo 20 palabras."
    )
    # Cuántos días dura una vuelta al split (2-10). 7 = la semana de siempre.
    # Ausente = 7, para que los planes ya guardados sigan valiendo tal cual.
    cycle_days: int = Field(default=SEMANA, ge=MIN_DIAS_CICLO, le=MAX_DIAS_CICLO)
    weekly_progression: list[WeeklyProgressionWeek]
    sessions: list[TrainingSession] = Field(min_length=1)
    cardio: CardioPlan
    deload_instructions: str = Field(
        description=(
            "TELEGRÁFICO: MÁXIMO 20 palabras con las cifras concretas. "
            "Ej.: 'Semana 4: series ÷2 · carga −30-35% · RIR 3-4 · sin récords'. "
            "NO expliques para qué sirve un deload ni motives."
        )
    )

    @field_validator("weekly_progression")
    @classmethod
    def bloques_consecutivos(cls, v: list[WeeklyProgressionWeek]) -> list[WeeklyProgressionWeek]:
        """El mesociclo son N bloques CONSECUTIVOS empezando en 1.

        Antes se exigían exactamente 4 ([1,2,3,4]): un mesociclo de 3 o de 5
        bloques no se podía ni generar. Lo que sí se sigue exigiendo es que no
        falte ni se repita ninguno — un plan con los bloques [1,3] deja al
        cliente sin pauta la segunda vuelta, y eso el portal no lo puede
        adivinar."""
        if not v:
            raise ValueError("weekly_progression no puede estar vacía")
        if len(v) > MAX_BLOQUES:
            raise ValueError(f"weekly_progression: máximo {MAX_BLOQUES} bloques")
        if [w.week for w in v] != list(range(1, len(v) + 1)):
            raise ValueError(
                "weekly_progression debe numerar los bloques de forma "
                f"consecutiva desde 1 (recibido: {[w.week for w in v]})")
        return v

    @model_validator(mode="after")
    def dias_dentro_del_ciclo(self) -> "TrainingCore":
        """Ninguna sesión puede caer fuera del ciclo ni compartir día con otra.

        Dos sesiones el mismo día del ciclo es un plan que el portal no sabe
        servir: enseñaría la primera y la otra no existiría para el cliente."""
        vistos: set[int] = set()
        for s in self.sessions:
            if s.day_index is None:
                continue
            if s.day_index > self.cycle_days:
                raise ValueError(
                    f"la sesión '{s.name}' cae en el día {s.day_index}, fuera "
                    f"del ciclo de {self.cycle_days} días")
            if s.day_index in vistos:
                raise ValueError(
                    f"hay dos sesiones en el día {s.day_index} del ciclo")
            vistos.add(s.day_index)
        if len(self.sessions) > self.cycle_days:
            raise ValueError(
                f"{len(self.sessions)} sesiones no caben en un ciclo de "
                f"{self.cycle_days} días")
        return self


class PlanCoreOutput(BaseModel):
    """Salida completa de la llamada ① (se persiste repartida en
    plans.nutrition_json / plans.training_json)."""

    nutrition: NutritionCore
    training: TrainingCore


class NutritionOnlyCoreOutput(BaseModel):
    """Núcleo SOLO-NUTRICIÓN (plan `nutri`): la IA no genera entrenamiento.
    Se persiste en plans.nutrition_json; plans.training_json queda vacío."""

    nutrition: NutritionCore


class TrainingOnlyCoreOutput(BaseModel):
    """Núcleo SOLO-ENTRENAMIENTO (plan `train`): la IA no genera dieta.
    Se persiste en plans.training_json; plans.nutrition_json queda vacío."""

    training: TrainingCore


# ============================================================ llamada ② ====


class Ingredient(BaseModel):
    food: str
    grams: float = Field(gt=0)  # SIEMPRE en crudo (E.3)
    household: str  # medida casera obligatoria
    # §2 (hardening): id del alimento en el catálogo (foods). Cuando la IA lo
    # aporta, el backend FIJA los gramos con el solver (la IA solo selecciona).
    food_id: int | None = None


class OptionMacros(BaseModel):
    kcal: float = Field(gt=0)
    protein_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)


class MealOption(BaseModel):
    key: str | None = None  # "A".."C" o None; el render numera 1/2/3
    title: str
    ingredients: list[Ingredient] = Field(min_length=1)
    prep: str = ""
    prep_minutes: int = Field(default=0, ge=0, le=120)
    macros: OptionMacros
    tags: list[str] = Field(default_factory=list)


# --- Sistema de EQUIVALENCIAS (réplica del ejemplo del coach para comida/cena) ---
class EquivItem(BaseModel):
    """Un alimento intercambiable con su cantidad equivalente en macros."""
    food: str
    amount: str  # "140 g crudo = 380 g cocido", "150 g", "350 ml + 1 huevo entero"


class EquivGroup(BaseModel):
    name: str               # "Hidratos de carbono (refinados / rápidos)"
    note: str = ""          # ración/guía: "1 ración moderada (200 g aprox). Mejor cocida…"
    items: list[EquivItem] = Field(default_factory=list)  # vacío si el grupo es solo guía


class EquivalenceMeal(BaseModel):
    intro: str = ""         # "Equivalencias calculadas para aportar ~108 g de CH del cereal"
    groups: list[EquivGroup] = Field(min_length=1)


class FlexibleSlot(BaseModel):
    slot: int = Field(ge=1)
    fmt: Literal["options", "equivalences"] = "options"
    options: list[MealOption] = Field(default_factory=list)   # 3 si fmt="options"
    equivalences: EquivalenceMeal | None = None               # si fmt="equivalences"
    # Ejemplos concretos para la tabla "dieta semanal" (1 plato corto por día):
    weekly_examples: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _coherencia(self) -> "FlexibleSlot":
        if self.fmt == "equivalences":
            if self.equivalences is None:
                raise ValueError(f"slot {self.slot}: fmt=equivalences requiere 'equivalences'")
        elif not (1 <= len(self.options) <= 4):
            raise ValueError(f"slot {self.slot}: fmt=options requiere 1-4 opciones (objetivo 3)")
        return self


class MealsFlexibleOutput(BaseModel):
    mode: Literal["flexible_7"]
    slots: list[FlexibleSlot] = Field(min_length=1)


DAY_NAMES = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


class StrictDayMeal(BaseModel):
    slot: int = Field(ge=1)
    dish: MealOption  # key = None


class StrictDay(BaseModel):
    day: str  # lunes…domingo (slug sin tildes)
    meals: list[StrictDayMeal] = Field(min_length=1)


class MealsStrictOutput(BaseModel):
    mode: Literal["strict"]
    days: list[StrictDay]
    free_meal_guidelines: str | None = None  # solo si strict_free_meal_enabled

    @field_validator("days")
    @classmethod
    def semana_completa(cls, v: list[StrictDay]) -> list[StrictDay]:
        if [d.day for d in v] != DAY_NAMES:
            raise ValueError(f"days debe ser exactamente {DAY_NAMES} en orden")
        return v

    @model_validator(mode="after")
    def mismos_slots_cada_dia(self) -> "MealsStrictOutput":
        slot_sets = {tuple(sorted(m.slot for m in d.meals)) for d in self.days}
        if len(slot_sets) != 1:
            raise ValueError("todos los días deben cubrir los mismos slots de comida")
        return self


MealsOutput = Annotated[
    Union[MealsFlexibleOutput, MealsStrictOutput], Field(discriminator="mode")
]


# ============================================================ llamada ③ ====


class EducationPill(BaseModel):
    topic: str
    for_client: str  # 4-6 líneas, lenguaje llano


class BiomechPattern(BaseModel):
    pattern: str  # "Empuje horizontal", "Bisagra de cadera"…
    cues: list[str] = Field(min_length=1)
    why: str


class FaqItem(BaseModel):
    q: str
    a: str


class EducationOutput(BaseModel):
    pills: list[EducationPill] = Field(min_length=3, max_length=5)
    biomech_by_pattern: list[BiomechPattern] = Field(min_length=1)
    faq: list[FaqItem] = Field(default_factory=list)


# ---------------------------------- panel de supervisión (hardening §9) ----
class ReviewFindingOut(BaseModel):
    """Hallazgo de un revisor del panel.

    `titulo` y `accion` son lo ÚNICO que el coach ve de un vistazo: el resto es
    detalle plegado. Por eso son obligatoriamente cortos (el contrato de
    longitud viaja en el prompt, que es lo único que llega al modelo).
    """

    severidad: Literal["bloqueante", "mayor", "menor"]
    # Con default "": un revisor antiguo o un fallo de formato no tumba el panel;
    # el frontend deriva el título del `descripcion` si viene vacío.
    titulo: str = ""
    accion: str = ""
    descripcion: str
    cita_anamnesis: str = ""
    donde_en_el_plan: str = ""
    correccion_propuesta: str = ""


class ReviewerOutput(BaseModel):
    """Veredicto estructurado de un revisor IA del panel (§9). Contrato aislado:
    el revisor solo ve anamnesis + plan y devuelve esto."""

    veredicto: Literal["aprobado", "aprobado_con_reservas", "rechazado"]
    puntuacion_rubrica: int = Field(ge=0, le=100)
    hallazgos: list[ReviewFindingOut] = Field(default_factory=list)
