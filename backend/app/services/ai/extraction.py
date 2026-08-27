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


# Sinónimos frecuentes (ya sin acentos, minúsculas) → enum del sistema.
_ENUM_MAPS: dict[str, dict[str, str]] = {
    "sex": {"male": "male", "female": "female", "hombre": "male", "varon": "male",
            "masculino": "male", "m": "male", "h": "male", "mujer": "female",
            "femenino": "female", "f": "female"},
    "goal_type": {"fat_loss": "fat_loss", "muscle_gain": "muscle_gain",
                  "recomp": "recomp", "maintenance": "maintenance",
                  "perdida de grasa": "fat_loss", "perder grasa": "fat_loss",
                  "definicion": "fat_loss", "adelgazar": "fat_loss",
                  "ganancia muscular": "muscle_gain", "ganar musculo": "muscle_gain",
                  "volumen": "muscle_gain", "hipertrofia": "muscle_gain",
                  "recomposicion": "recomp", "mantenimiento": "maintenance",
                  # recuperación de lesión: objetivo VÁLIDO del sistema que por
                  # la vía PDF era imposible de obtener (sin sinónimos aquí ni
                  # mención en el prompt, auditoría 27-08)
                  "injury_recovery": "injury_recovery",
                  "recuperacion": "injury_recovery",
                  "recuperacion de lesion": "injury_recovery",
                  "rehabilitacion": "injury_recovery"},
    # Patrón alimentario (PDF "Preferencias y aversiones"): gobierna el filtro
    # de alimentos, el banco fallback y el Revisor 0. No se extraía y un vegano
    # de la vía PDF recibía pollo salvo corrección manual (auditoría 27-08).
    "diet_pattern": {"vegano": "vegano", "vegana": "vegano",
                     "vegetariano": "vegetariano", "vegetariana": "vegetariano",
                     "ovolactovegetariano": "vegetariano",
                     "pescetariano": "pescetariano", "pescetariana": "pescetariano",
                     "pescatariano": "pescetariano",
                     "sin cerdo": "sin_cerdo", "sin_cerdo": "sin_cerdo",
                     "no come cerdo": "sin_cerdo",
                     "halal": "halal", "kosher": "kosher"},
    "level": {"beginner": "beginner", "intermediate": "intermediate",
              "advanced": "advanced", "principiante": "beginner",
              "novato": "beginner", "intermedio": "intermediate",
              "avanzado": "advanced"},
    "training_place": {"gym": "gym", "home": "home", "outdoor": "outdoor",
                       "gimnasio": "gym", "casa": "home", "domicilio": "home",
                       "exterior": "outdoor", "aire libre": "outdoor",
                       "calistenia": "outdoor"},
    "diet_mode": {"flexible_7": "flexible_7", "strict": "strict",
                  "flexible": "flexible_7", "estricta": "strict",
                  "estricto": "strict", "cerrada": "strict", "cerrado": "strict"},
    "daily_activity_level": {"sedentary": "sedentary", "light": "light",
                             "active": "active", "very_active": "very_active",
                             "sedentario": "sedentary", "ligera": "light",
                             "ligero": "light", "activa": "active",
                             "activo": "active", "muy activa": "very_active",
                             "muy activo": "very_active"},
}


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
    phone: str | None = Field(None, description="Teléfono/móvil tal y como aparece")
    height_cm: float | None = None
    start_weight_kg: float | None = Field(None, description="Peso actual (kg)")
    body_fat_pct: float | None = None
    # Perímetros iniciales (cm): la línea base corporal que el cliente midió y
    # escribió — sin ella el primer informe no puede enseñar el delta de
    # medidas, justo la prueba de progreso cuando la báscula no se mueve.
    initial_waist_cm: float | None = Field(None, description="Perímetro cintura (cm)")
    initial_hip_cm: float | None = Field(None, description="Perímetro cadera (cm)")
    initial_arm_cm: float | None = Field(None, description="Perímetro brazo relajado (cm)")
    initial_thigh_cm: float | None = Field(None, description="Perímetro muslo (cm)")

    # --- Objetivo (PDF: "Motivo y objetivos") ---
    goal_type: str | None = Field(
        None, description="fat_loss|muscle_gain|recomp|maintenance|injury_recovery")
    goal_weight_kg: float | None = None
    goal_deadline: date | None = Field(
        None, description="Fecha objetivo/plazo que declare el cliente (YYYY-MM-DD)")

    # --- Entrenamiento (PDF: "Experiencia con pesas" / "Entrenamiento actual y preferencias") ---
    level: str | None = Field(None, description="beginner|intermediate|advanced")
    training_days: int | None = Field(None, description="Días que puede entrenar por semana")
    daily_activity_level: str | None = Field(
        None, description="Actividad DIARIA fuera del entreno según el trabajo/estilo de "
        "vida: sedentary (oficina/sentado), light (de pie o caminando a ratos), "
        "active (trabajo físico, muchos pasos), very_active (trabajo físico intenso)")
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
    diet_pattern: str | None = Field(
        None, description="vegano|vegetariano|pescetariano|sin_cerdo|halal|kosher "
        "(PDF 'Patrón alimentario'; omnívoro/ninguno → null)")
    meals_per_day: int | None = None
    meal_schedule: list[MealSlot] = Field(default_factory=list)
    food_likes: list[str] = Field(default_factory=list)
    food_dislikes: list[str] = Field(default_factory=list)
    food_allergies: list[str] = Field(default_factory=list)

    # --- Resúmenes por sección cualitativa (texto libre; cada uno → una columna) ---
    injuries_notes: str | None = Field(
        None,
        description=(
            "PDF 'Historial de lesiones y movilidad': TODAS las lesiones, sin "
            "recorte (seguridad). Una línea densa por lesión: '- [zona, lado] · "
            "[activa/resuelta] · evitar: [movimientos]'. Máx ~20 palabras/línea."
        ),
    )
    medical_notes: str | None = Field(
        None,
        description=(
            "PDF 'Historia clínica' + 'Salud digestiva y hormonal' + 'Salud "
            "femenina'. Cada línea prefijada por tema ('- Clínica: …', "
            "'- Digestivo: …', '- Salud femenina: …', '- Hábitos tóxicos: …', "
            "'- Analítica: …'). Patologías/cirugías/intolerancias SIN recorte; "
            "lo informativo breve. Negaciones agrupadas en una sola línea."
        ),
    )
    medication_notes: str | None = Field(
        None,
        description=(
            "PDF 'Medicación actual' + 'Anticonceptivos hormonales', sin "
            "recorte: '- Nombre — dosis — frecuencia'. null si no toma nada."
        ),
    )
    current_supplements: str | None = Field(
        None,
        description=(
            "PDF 'Suplementación': '- Nombre — dosis — momento', una línea por "
            "suplemento, máximo 6. null si no toma nada."
        ),
    )
    sport_history: str | None = Field(
        None,
        description=(
            "PDF 'Experiencia con pesas' + 'Otros deportes'. MÁXIMO 4 viñetas "
            "cortas: años/nivel con los básicos, métodos que funcionaron o "
            "fallaron, otros deportes con frecuencia, matiz técnico a vigilar."
        ),
    )
    lifestyle_notes: str | None = Field(
        None,
        description=(
            "PDF 'Motivo y objetivos', 'Logística', 'Comida emocional', "
            "'Hidratación', 'Trabajo', 'Sueño', 'Estrés' y auto-evaluación. "
            "MÁXIMO 6 viñetas prefijadas por tema empezando por '- Motivo: …' "
            "('- Trabajo: …', '- Sueño: …', '- Estrés: …', '- Conducta "
            "alimentaria: …'…), 1-2 líneas por tema, ordenadas por impacto en "
            "la adherencia. Temas sin nada relevante se omiten."
        ),
    )

    # --- Normalización de ENUMS (PDFs manuscritos → valores del sistema) ------
    # Un valor fuera de enum ("Hombre", "Gimnasio", "principiante") caía tal
    # cual en la ficha y aguas abajo TODO compara con el enum exacto: un sexo
    # no mapeado activaba la rama femenina de Mifflin (−166 kcal) en silencio.
    # Los sinónimos se mapean (tabla _ENUM_MAPS a nivel de módulo); lo
    # irreconocible queda en None (el coach lo ve VACÍO y lo corrige — nunca
    # un cálculo corrupto).
    @field_validator("sex", "goal_type", "level", "training_place", "diet_mode",
                     "daily_activity_level", "diet_pattern", mode="before")
    @classmethod
    def _normalize_enum(cls, v, info):
        if v is None or not isinstance(v, str):
            return v
        import unicodedata
        key = unicodedata.normalize("NFKD", v.strip().lower())
        key = key.encode("ascii", "ignore").decode("ascii")
        return _ENUM_MAPS.get(info.field_name, {}).get(key)

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
            "Síntesis en 3-5 puntos ('- …') ordenados de más a menos "
            "importante, con SOLO lo que cambia decisiones del plan: cruza "
            "objetivo, lesiones, hábitos, sueño, estrés, conducta alimentaria "
            "y qué ha funcionado o no en el pasado. Sin relleno."
        ),
    )


_EXTRACTION_SYSTEM = """Eres un dietista-entrenador experto leyendo la ficha de \
ANAMNESIS oficial (marca DQ) que un cliente ha rellenado a mano. Tu tarea es EXTRAER \
toda la información del documento de forma fiel y estructurada, sin inventar nada.

REGLA DE ORO: si un dato no aparece, está en blanco o pone "no aplica", déjalo en null \
(o lista/texto vacío). NUNCA inventes datos: un error en peso, lesiones o medicación \
sería grave. El coach revisará todo antes de generar el plan. MAPEAR o INFERIR un valor \
a partir de lo que el cliente escribió NO es inventar; es obligatorio.

LECTURA EXHAUSTIVA, ESCRITURA SELECTIVA: la anamnesis es la BASE de toda la asesoría. \
Lee el documento ENTERO, frase a frase, incluidos márgenes, anotaciones a mano, respuestas \
fuera de su casilla y comentarios sueltos. Pero ESCRIBE selectivo: a las notas va lo que \
tiene señal para dieta, entrenamiento o adherencia — no cada casilla del PDF. \
EXCEPCIÓN SIN RECORTE (seguridad): lesiones, patologías, alergias/intolerancias y \
medicación se recogen SIEMPRE al completo. Y si el cliente escribió algo ambiguo o \
contradictorio, recógelo tal cual en la nota de su sección (el coach decide), nunca lo omitas.

CAMPOS ESTRUCTURADOS OBLIGATORIOS — recórrelos UNO A UNO y rellénalos SIEMPRE que el dato \
aparezca en CUALQUIER parte del documento. NO dejes en null un campo cuyo dato esté presente:
  · birth_date ← "Fecha de nacimiento": convierte DD/MM/AAAA a YYYY-MM-DD (12/03/1990 → 1990-03-12).
  · sex ← "Sexo biológico": Hombre→"male", Mujer→"female" (Otro→null).
  · phone ← "Teléfono": el móvil tal cual (con prefijo si lo escribe).
  · height_cm ← "Altura"; start_weight_kg ← "Peso actual"; goal_weight_kg ← "Peso objetivo".
  · initial_waist_cm / initial_hip_cm / initial_arm_cm / initial_thigh_cm ← "Perímetro \
cintura / cadera / brazo relajado / muslo" (cm) de la antropometría inicial.
  · goal_type ← "Motivo y objetivos" (NO hay casilla: INFIÉRELO del texto): perder grasa/definir/\
adelgazar→"fat_loss"; ganar músculo/volumen→"muscle_gain"; recomposición/tonificar→"recomp"; \
mantener el peso (sin ganar ni perder)→"maintenance"; recuperarse de una lesión/operación y \
volver a entrenar→"injury_recovery".
  · goal_deadline ← si el cliente declara un PLAZO o fecha para su objetivo ("para junio", \
"en 3 meses", "para la boda del 12/09"), conviértelo a YYYY-MM-DD (aprox. si hace falta).
  · level ← "Nivel auto-percibido en sala de pesas": Principiante→"beginner"; Intermedio→\
"intermediate"; Avanzado→"advanced".
  · training_place ← "Dónde entrenas": Gimnasio/gym→"gym"; Casa→"home"; Exterior→"outdoor".
  · training_days ← cuenta los días marcados en "Días que puedes entrenar" (L M X J V S D).
  · daily_activity_level ← deduce la actividad DIARIA por el trabajo/estilo de vida: \
oficina o sentado→"sedentary"; de pie o caminando a ratos (comercio, docencia)→"light"; \
trabajo físico con muchos pasos→"active"; trabajo físico intenso (obra, mensajería, campo)→\
"very_active". Si no hay información suficiente, déjalo en null.
  · session_max_min ← "Duración media de la sesión", en minutos.
  · diet_mode ← bloque de dieta: si menciona equivalencias/flexibilidad→"flexible_7"; si pide \
menú cerrado→"strict". Si no está claro, usa "flexible_7".
  · diet_pattern ← "Patrón alimentario": vegano→"vegano"; vegetariano→"vegetariano"; \
pescetariano→"pescetariano"; sin cerdo→"sin_cerdo"; halal→"halal"; kosher→"kosher"; \
omnívoro/"como de todo"/en blanco→null. Es SEGURIDAD: gobierna qué alimentos puede llevar su plan.
  · Si una respuesta de selección NO encaja en ningún valor del enum, deja el campo en null \
PERO recoge el texto literal en la nota de su sección — que el coach vea que el cliente \
contestó y qué escribió, nunca un campo vacío en silencio.
  · meals_per_day ← "¿Cuántas comidas haces al día?". Si marca "Lo decidís vosotros" \
o deja el bloque en blanco → meals_per_day=null y meal_schedule=[] (DELEGA el número y \
reparto de comidas en el coach; la IA del plan elegirá el óptimo).
  · meal_schedule: de "¿Cuáles?" (desayuno, media mañana, comida, merienda, cena, \
pre-cama…) y del resto del documento, deduce las tomas y sus horas. Cada toma DEBE ser \
un objeto con "slot" (1,2,3…), "name" ("Desayuno","Comida","Merienda","Cena"…) y "time" \
("HH:MM"). Si no hay horas exactas, propón horarios razonables coherentes con el nº de comidas.
  · equipment: SOLO si entrena en casa/exterior, lista el material declarado (mancuernas, barra, \
banco, jaula, gomas, máquinas…). Si entrena en gimnasio, deja la lista vacía.
  · food_likes / food_dislikes / food_allergies: de "Preferencias y aversiones" e "Historia \
clínica" (alergias/intolerancias alimentarias). Listas de alimentos concretos.

RESÚMENES POR SECCIÓN — FORMATO EN PUNTOS: cada campo es una lista de líneas cortas (una \
por dato), empezando CADA línea con "- ". Nada de párrafos largos. Fiel al PDF, en español.
CALIDAD SOBRE CANTIDAD (el coach los lee de un vistazo antes de la asesoría):
  · ORDEN: dentro de cada sección, PRIMERO lo que condiciona el plan (lesiones activas, \
patologías, alergias, medicación con efecto en dieta/entreno), después lo informativo.
  · SIN PAJA: las negaciones y valores sin señal se AGRUPAN en UNA sola línea al final \
("- Sin cirugías, sin medicación, analítica normal"), nunca una línea por cada "no". \
Los ceros sin relevancia clínica (p. ej. "Embarazos: 0") se omiten.
  · SIN DUPLICADOS: cada dato va a UNA sola sección (la más específica); no repitas la \
misma información en dos campos.
  · Línea corta = dato + matiz imprescindible. Nada de frases de relleno ni obviedades.
Lo CLÍNICO Y DE SEGURIDAD (lesiones, patologías, alergias, medicación) se conserva SIEMPRE \
al completo aunque sea largo: ahí la fidelidad manda sobre la brevedad.
  · injuries_notes ← "Historial de lesiones y movilidad": TODAS las lesiones, sin recorte \
(seguridad). Una línea densa por lesión: "- [zona y lado] · [activa/resuelta, desde cuándo] · \
evitar: [movimientos]". Máximo ~20 palabras por línea.
  · medical_notes ← "Historia clínica" + "Salud digestiva y hormonal" + "Salud femenina (si \
aplica)": patologías, antecedentes familiares, cirugías, intolerancias, tabaco/alcohol/otras \
sustancias, analítica reciente; deposiciones/Bristol/síntomas digestivos; y ciclo menstrual/\
embarazos/menopausia si aplica. PREFIJA cada línea con su tema para que se lea por bloques: \
"- Clínica: …", "- Digestivo: …", "- Salud femenina: …", "- Hábitos tóxicos: …", "- Analítica: …".
  · medication_notes ← "Medicación actual" + "Anticonceptivos hormonales", SIN recorte. \
Formato: "- Nombre — dosis — frecuencia" (+ efecto relevante para dieta/entreno si lo hay). \
Sin frases introductorias.
  · current_supplements ← "Suplementación": "- Nombre — dosis — momento", una línea por \
suplemento, máximo 6; sin valoraciones.
  · sport_history ← "Experiencia con pesas" + "Otros deportes" + "Ejercicios favoritos / que \
detesta". MÁXIMO 5 viñetas: años y nivel real con los básicos; qué métodos funcionaron o \
fallaron; otros deportes actuales con frecuencia (condicionan la recuperación); matiz técnico \
a vigilar si lo hay; y SIEMPRE que el cliente los declare, "- Ejercicios: favoritos … / \
detesta …" (el generador los respeta). Líneas cortas tipo "- Pesas: 2 años, técnica básica \
cómoda" / "- Fútbol: 1 vez/semana".
  · lifestyle_notes ← "Motivo y objetivos" (corto/largo plazo, qué funcionó o no, motivación/\
confianza), "Logística y entorno alimentario", "Comida emocional", "Hidratación", "Tu trabajo \
y tu día a día", "Sueño y recuperación", "Estrés y energía" y la auto-evaluación final. \
PREFIJA cada línea con su tema, EMPEZANDO SIEMPRE por el motivo (es lo primero que lee el \
coach): "- Motivo: …", "- Trabajo: …", "- Sueño: …", "- Estrés: …", "- Conducta alimentaria: …", \
"- Logística: …", "- Hidratación: …", "- Horario de entreno: …" (la hora habitual a la que \
entrena condiciona las comidas peri-entreno). MÁXIMO 6 viñetas en total, ordenadas por \
impacto en la adherencia; máximo 1-2 líneas por tema; los temas sin nada relevante se omiten.

SÍNTESIS:
  · deep_analysis: 3-5 líneas en puntos ("- …"), ORDENADAS de más a menos importante, máximo \
~20 palabras por punto. Un punto = UNA decisión de plan (qué respetar, qué priorizar, qué \
vigilar), no un tema: cruza objetivo, lesiones, hábitos, sueño, estrés y conducta alimentaria \
como material, sin obligación de cubrirlos todos. Sin repetir lo que ya está en los campos \
estructurados ni relleno motivacional.

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
        temperature=0,  # §14: extracción determinista (mismos datos → misma lectura)
    )
