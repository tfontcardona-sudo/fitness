"""Extracción de la anamnesis desde el PDF con IA (lectura nativa).

La IA lee el PDF oficial rellenado por el cliente y extrae:
- Los campos ESTRUCTURADOS que el sistema necesita para calcular y generar
  (sexo, antropometría, objetivo, nivel, entrenamiento, dieta, preferencias).
- Un ANÁLISIS cualitativo en profundidad (lesiones, hábitos, sueño, estrés,
  conducta alimentaria, contexto) que enriquece la planificación.

El coach revisa los campos extraídos antes de generar (seguridad): la IA puede
malinterpretar texto manuscrito o ambiguo, y un error en peso o lesiones sería
grave. Por eso esto solo PRE-RELLENA; la decisión final es del coach.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator


class MealSlot(BaseModel):
    """Toma de comida. Los campos son opcionales en la extracción porque la IA a
    veces omite slot/name; se autocompletan en AnamnesisExtraction para no
    descartar toda la lectura por un detalle de formato."""

    slot: int | None = None
    name: str | None = None
    time: str | None = None  # "HH:MM"


class AnamnesisExtraction(BaseModel):
    """Datos extraídos del PDF oficial de anamnesis (DQ). Campos opcionales: si
    la IA no los encuentra, los deja en null (o lista/texto vacío) y el coach
    los completa.

    El esquema refleja las secciones del PDF: los campos ESTRUCTURADOS que el
    backend necesita para calcular y filtrar, más un resumen por SECCIÓN
    cualitativa (cada uno mapea a una columna de la ficha del cliente) y una
    síntesis final (deep_analysis) para personalizar el plan.
    """

    # --- Datos personales y antropometría (PDF: "Datos personales" / "Antropometría inicial") ---
    sex: str | None = Field(None, description="male|female (mapea Hombre→male, Mujer→female)")
    birth_date: date | None = Field(None, description="Fecha de nacimiento YYYY-MM-DD")
    height_cm: float | None = None
    start_weight_kg: float | None = Field(None, description="Peso actual (kg)")
    body_fat_pct: float | None = None

    # --- Objetivo (PDF: "Motivo y objetivos") ---
    goal_type: str | None = Field(None, description="fat_loss|muscle_gain|recomp")
    goal_weight_kg: float | None = None

    # --- Entrenamiento (PDF: "Experiencia con pesas" / "Entrenamiento actual y preferencias") ---
    level: str | None = Field(None, description="beginner|intermediate|advanced")
    training_days: int | None = Field(None, description="Días que puede entrenar por semana")
    session_max_min: int | None = Field(None, description="Duración media/máxima de sesión en minutos")
    training_place: str | None = Field(None, description="gym|home|outdoor")
    equipment: list[str] = Field(
        default_factory=list,
        description=(
            "Material disponible SOLO si entrena en casa/exterior (mancuernas, "
            "barra, banco, jaula, gomas…). Vacío si entrena en gimnasio."
        ),
    )

    # --- Dieta (PDF: "Hábitos dietéticos" / "Preferencias y aversiones") ---
    diet_mode: str | None = Field(None, description="flexible_7|strict")
    meals_per_day: int | None = None
    meal_schedule: list[MealSlot] = Field(default_factory=list)
    food_likes: list[str] = Field(default_factory=list)
    food_dislikes: list[str] = Field(default_factory=list)
    food_allergies: list[str] = Field(default_factory=list)

    # --- Resúmenes por sección cualitativa (texto libre; cada uno → una columna) ---
    injuries_notes: str | None = Field(
        None,
        description=(
            "PDF 'Historial de lesiones y movilidad': resume TODAS las lesiones/"
            "molestias con zona, lado, si está resuelto y qué movimientos evitar. "
            "Crítico para la seguridad del entrenamiento."
        ),
    )
    medical_notes: str | None = Field(
        None,
        description=(
            "PDF 'Historia clínica' + 'Salud digestiva y hormonal' + 'Salud "
            "femenina': patologías, antecedentes familiares, cirugías, "
            "intolerancias, tabaco/alcohol/otras sustancias, analítica reciente, "
            "salud digestiva (deposiciones, Bristol, síntomas) y, si aplica, "
            "ciclo menstrual/embarazos/menopausia. Resume lo relevante."
        ),
    )
    medication_notes: str | None = Field(
        None,
        description=(
            "PDF 'Medicación actual' + 'Anticonceptivos hormonales': nombre, "
            "dosis y frecuencia. null si no toma nada."
        ),
    )
    current_supplements: str | None = Field(
        None,
        description=(
            "PDF 'Suplementación': suplementos actuales con dosis y momento del "
            "día. null si no toma nada."
        ),
    )
    sport_history: str | None = Field(
        None,
        description=(
            "PDF 'Experiencia con pesas' + 'Otros deportes': años entrenando, "
            "nivel/técnica de los básicos, métodos/rutinas seguidas, y otros "
            "deportes recreativos con su frecuencia semanal."
        ),
    )
    lifestyle_notes: str | None = Field(
        None,
        description=(
            "PDF 'Motivo y objetivos' (corto/largo plazo, qué funcionó o no, "
            "motivación), 'Logística y entorno alimentario', 'Comida emocional', "
            "'Hidratación', 'Tu trabajo y tu día a día', 'Sueño y recuperación', "
            "'Estrés y energía' y la auto-evaluación final. Resume hábitos, "
            "sueño, estrés, conducta alimentaria, logística y contexto."
        ),
    )

    @field_validator("meal_schedule")
    @classmethod
    def _normalize_meal_schedule(cls, v: list[MealSlot]) -> list[MealSlot]:
        """Autocompleta slot (1,2,3…) y name si la IA los omitió, para que la
        ficha quede usable y no se pierda la extracción entera."""
        _default_names = {1: "Desayuno", 2: "Comida", 3: "Merienda", 4: "Cena"}
        out: list[MealSlot] = []
        for i, m in enumerate(v, start=1):
            slot = m.slot if m.slot is not None else i
            name = m.name or _default_names.get(slot, f"Toma {slot}")
            out.append(MealSlot(slot=slot, name=name, time=m.time or ""))
        return out

    # --- Síntesis final para personalizar el plan ---
    deep_analysis: str | None = Field(
        None,
        description=(
            "Síntesis ejecutiva (4-8 frases) con lo MÁS relevante para "
            "personalizar el plan: cruza objetivo, lesiones, hábitos, sueño, "
            "estrés, conducta alimentaria y qué ha funcionado o no en el pasado."
        ),
    )


_EXTRACTION_SYSTEM = """Eres un dietista-entrenador experto leyendo la ficha de \
ANAMNESIS oficial (marca DQ) que un cliente ha rellenado a mano. Tu tarea es EXTRAER \
toda la información del documento de forma fiel y estructurada, sin inventar nada.

REGLA DE ORO: si un dato no aparece, está en blanco o pone "no aplica", déjalo en null \
(o lista/texto vacío). NUNCA inventes datos: un error en peso, lesiones o medicación \
sería grave. El coach revisará todo antes de generar el plan. MAPEAR o INFERIR un valor \
a partir de lo que el cliente escribió NO es inventar; es obligatorio.

CAMPOS ESTRUCTURADOS OBLIGATORIOS — recórrelos UNO A UNO y rellénalos SIEMPRE que el dato \
aparezca en CUALQUIER parte del documento. NO dejes en null un campo cuyo dato esté presente:
  · birth_date ← "Fecha de nacimiento": convierte DD/MM/AAAA a YYYY-MM-DD (12/03/1990 → 1990-03-12).
  · sex ← "Sexo biológico": Hombre→"male", Mujer→"female" (Otro→null).
  · height_cm ← "Altura"; start_weight_kg ← "Peso actual"; goal_weight_kg ← "Peso objetivo".
  · goal_type ← "Motivo y objetivos" (NO hay casilla: INFIÉRELO del texto): perder grasa/definir/\
adelgazar→"fat_loss"; ganar músculo/volumen→"muscle_gain"; recomposición/mantener/tonificar→"recomp".
  · level ← "Nivel auto-percibido en sala de pesas": Principiante→"beginner"; Intermedio→\
"intermediate"; Avanzado→"advanced".
  · training_place ← "Dónde entrenas": Gimnasio/gym→"gym"; Casa→"home"; Exterior→"outdoor".
  · training_days ← cuenta los días marcados en "Días que puedes entrenar" (L M X J V S D).
  · session_max_min ← "Duración media de la sesión", en minutos.
  · diet_mode ← bloque de dieta: si menciona equivalencias/flexibilidad→"flexible_7"; si pide \
menú cerrado→"strict". Si no está claro, usa "flexible_7".
  · meals_per_day ← "¿Cuántas comidas haces al día?".
  · meal_schedule: deduce las tomas y sus horas. Cada toma DEBE ser un objeto con \
"slot" (1,2,3…), "name" ("Desayuno","Comida","Merienda","Cena"…) y "time" ("HH:MM"). \
Si no hay horas exactas, propón horarios razonables coherentes con el nº de comidas.
  · equipment: SOLO si entrena en casa/exterior, lista el material declarado (mancuernas, barra, \
banco, jaula, gomas, máquinas…). Si entrena en gimnasio, deja la lista vacía.
  · food_likes / food_dislikes / food_allergies: de "Preferencias y aversiones" e "Historia \
clínica" (alergias/intolerancias alimentarias). Listas de alimentos concretos.

RESÚMENES POR SECCIÓN — FORMATO EN PUNTOS: cada campo es una lista de líneas cortas (una \
por dato), empezando CADA línea con "- ". Nada de párrafos largos. Fiel al PDF, en español:
  · injuries_notes ← "Historial de lesiones y movilidad": cada lesión marcada con zona, lado, \
si está resuelta y qué movimientos dan molestia. Crítico para la seguridad.
  · medical_notes ← "Historia clínica" + "Salud digestiva y hormonal" + "Salud femenina (si \
aplica)": patologías, antecedentes familiares, cirugías, intolerancias, tabaco/alcohol/otras \
sustancias, analítica reciente; deposiciones/Bristol/síntomas digestivos; y ciclo menstrual/\
embarazos/menopausia si aplica.
  · medication_notes ← "Medicación actual" + "Anticonceptivos hormonales": nombre, dosis, frecuencia.
  · current_supplements ← "Suplementación": suplementos actuales con dosis y momento del día.
  · sport_history ← "Experiencia con pesas" + "Otros deportes": años entrenando, comodidad con \
la técnica de los básicos, métodos/rutinas previas, y otros deportes recreativos y su frecuencia.
  · lifestyle_notes ← "Motivo y objetivos" (corto/largo plazo, qué funcionó o no, motivación/\
confianza), "Logística y entorno alimentario", "Comida emocional", "Hidratación", "Tu trabajo \
y tu día a día", "Sueño y recuperación", "Estrés y energía" y la auto-evaluación final.

SÍNTESIS:
  · deep_analysis: 4-8 frases con lo MÁS relevante para personalizar el plan, cruzando objetivo, \
lesiones, hábitos, sueño, estrés y conducta alimentaria. Concreto y accionable.

Devuelve SOLO un objeto JSON válido que cumpla el esquema. Sin texto adicional."""

_EXTRACTION_USER = """Lee la ficha de anamnesis adjunta (PDF oficial DQ, ~10 páginas) y \
extrae TODA la información en JSON según el esquema. Recorre el documento sección por \
sección y rellena tanto los campos estructurados (antropometría, objetivo, entrenamiento, \
dieta) como los resúmenes por sección (clínica, medicación, suplementos, deportes, lesiones, \
estilo de vida). Lo que no encuentres o esté en blanco, déjalo en null; no inventes datos."""


def extract_anamnesis_from_pdf(pdf_bytes: bytes, ai) -> AnamnesisExtraction:
    """Lee el PDF con la IA y devuelve los datos extraídos validados."""
    from app.config import settings

    return ai.read_pdf_json(
        model=settings.model_heavy,
        system=_EXTRACTION_SYSTEM,
        user=_EXTRACTION_USER,
        pdf_bytes=pdf_bytes,
        schema=AnamnesisExtraction,
    )
