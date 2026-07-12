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

# ============================================================ llamada ① ====


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
    evidence_note: str = ""  # nota informativa; opcional para no tumbar el plan si la IA la omite


class NutritionCore(BaseModel):
    tdee_kcal: float = Field(gt=0)
    target_kcal: float = Field(gt=0)
    rationale: str
    macros: Macros
    meals: list[MealSlotDef] = Field(min_length=1)
    supplements: list[Supplement] = Field(default_factory=list)
    flexibility_rules: list[str] = Field(default_factory=list)
    refeed_or_break: str | None = None

    @model_validator(mode="after")
    def slots_unicos_y_ordenados(self) -> "NutritionCore":
        slots = [m.slot for m in self.meals]
        if len(set(slots)) != len(slots):
            raise ValueError("slots de comida duplicados")
        if slots != sorted(slots):
            raise ValueError("los slots deben venir ordenados")
        return self


class WeeklyProgressionWeek(BaseModel):
    week: int = Field(ge=1, le=4)
    intent: str  # Base | Progresión | Pico | Deload
    load_pct: float = Field(gt=0)
    rir_target: str
    volume_note: str


class PlannedExercise(BaseModel):
    exercise_id: int = Field(ge=1)  # SOLO ids de la biblioteca inyectada (F.3)
    sets: int = Field(ge=1, le=10)
    rep_range: str  # "6-8"
    rir: str  # "2" | "1-2"
    tempo: str | None = None
    rest_sec: int = Field(ge=15, le=600)
    start_weight_hint_kg: float | None = Field(default=None, ge=0)
    progression_rule: str
    technique_cue: str
    biomech_cue: str


class TrainingSession(BaseModel):
    day: str  # "Lunes"…
    name: str  # "Upper A"
    warmup: str
    exercises: list[PlannedExercise] = Field(min_length=1)
    cooldown: str


class CardioSession(BaseModel):
    type: Literal["liss", "hiit"]
    minutes: int = Field(ge=5, le=120)
    times_per_week: int = Field(ge=1, le=7)
    notes: str | None = None


class CardioPlan(BaseModel):
    daily_steps: int = Field(ge=0, le=30000)
    sessions: list[CardioSession] = Field(default_factory=list)


class TrainingCore(BaseModel):
    split_name: str
    split_rationale: str
    weekly_progression: list[WeeklyProgressionWeek]
    sessions: list[TrainingSession] = Field(min_length=1)
    cardio: CardioPlan
    deload_instructions: str

    @field_validator("weekly_progression")
    @classmethod
    def cuatro_semanas(cls, v: list[WeeklyProgressionWeek]) -> list[WeeklyProgressionWeek]:
        if [w.week for w in v] != [1, 2, 3, 4]:
            raise ValueError("weekly_progression debe cubrir exactamente las semanas 1-4")
        return v


class PlanCoreOutput(BaseModel):
    """Salida completa de la llamada ① (se persiste repartida en
    plans.nutrition_json / plans.training_json)."""

    nutrition: NutritionCore
    training: TrainingCore


class NutritionOnlyCoreOutput(BaseModel):
    """Núcleo SOLO-NUTRICIÓN (paquete Start): la IA no genera entrenamiento.
    Se persiste en plans.nutrition_json; plans.training_json queda vacío."""

    nutrition: NutritionCore


# ============================================================ llamada ② ====


class Ingredient(BaseModel):
    food: str
    grams: float = Field(gt=0)  # SIEMPRE en crudo (E.3)
    household: str  # medida casera obligatoria


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
