"""Extracción de la anamnesis desde CUALQUIER documento con IA (lector universal).

La IA lee el documento —el PDF oficial, el cuestionario de otro profesional, fotos
de una hoja manuscrita, un Word, una hoja de cálculo o unas notas— y extrae:
- Los campos ESTRUCTURADOS que el sistema necesita para calcular y generar
  (sexo, antropometría, objetivo, nivel, entrenamiento, dieta, preferencias).
- Un ANÁLISIS cualitativo en profundidad (lesiones, hábitos, sueño, estrés,
  conducta alimentaria, contexto) que enriquece la planificación.

El coach revisa los campos extraídos antes de generar (seguridad): la IA puede
malinterpretar texto manuscrito o ambiguo, y un error en peso o lesiones sería
grave. Por eso esto solo PRE-RELLENA; la decisión final es del coach.
"""

from __future__ import annotations

from dataclasses import dataclass
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

    # --- Lector universal: qué ES el documento y qué se leyó de él ---------
    # El documento ya no es necesariamente el PDF oficial: puede ser el
    # cuestionario de otro profesional, una foto de una hoja manuscrita, un
    # Word, un Excel o unas notas. Estos campos dejan constancia de qué había
    # y de que se leyó ENTERO — el coach ve el inventario y lo que no cupo en
    # ninguna casilla, en vez de fiarse de un formulario silencioso.
    document_kind: str | None = Field(
        None, description="anamnesis_dq|cuestionario_ajeno|notas|analitica|informe_medico|"
                          "plan_dieta|plan_entreno|mixto|otro")
    source_inventory: list[str] = Field(
        default_factory=list,
        description="Una línea corta por bloque/tema que CONTIENE el documento, en su "
                    "orden (p. ej. '- Datos personales', '- Tabla de perímetros', "
                    "'- Analítica 12/05/2026', '- Texto libre sobre motivación').")
    unmapped_info: list[str] = Field(
        default_factory=list,
        description="Datos RELEVANTES para dieta, entreno o salud que no encajan en "
                    "ningún campo del esquema, cada uno en una línea corta. Vacío si "
                    "no hay nada.")
    confidence: dict[str, float] = Field(
        default_factory=dict,
        description="Confianza 0-1 en los campos críticos que hayas rellenado: sex, "
                    "birth_date, height_cm, start_weight_kg, goal_type, food_allergies, "
                    "medication_notes, medical_notes, injuries_notes. 1 = está escrito "
                    "claro y literal; 0,6 = inferido o manuscrito dudoso.")

    @field_validator("confidence", mode="before")
    @classmethod
    def _confianza_acotada(cls, v):
        if not isinstance(v, dict):
            return {}
        out: dict[str, float] = {}
        for k, val in v.items():
            try:
                f = float(val)
            except (TypeError, ValueError):
                continue
            out[str(k)] = min(1.0, max(0.0, f))
        return out

    @field_validator("source_inventory", "unmapped_info", mode="before")
    @classmethod
    def _listas_de_texto(cls, v):
        """La IA a veces manda un párrafo o un dict en vez de una lista: se
        acepta lo que sea y se normaliza a líneas — una lista rara no puede
        tumbar la extracción entera (gotcha §5.10)."""
        if v is None:
            return []
        if isinstance(v, str):
            return [x.strip(" -•\t") for x in v.splitlines() if x.strip(" -•\t")]
        if isinstance(v, dict):
            return [f"{k}: {val}" for k, val in v.items()]
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return []


_EXTRACTION_SYSTEM = """Eres un dietista-entrenador experto. Te llega UN DOCUMENTO con \
información de un cliente para su asesoría de nutrición y entrenamiento. Tu tarea es EXTRAER \
toda la información del documento de forma fiel y estructurada, sin inventar nada.

EL DOCUMENTO PUEDE TENER CUALQUIER FORMA. No busques casillas: busca INFORMACIÓN. Puede ser \
la ficha de anamnesis oficial (marca DQ, ~10 páginas), el cuestionario de otro profesional con \
otras secciones y otro orden, un formulario web exportado, unas notas escritas a mano y \
fotografiadas con el móvil (varias fotos = un solo documento; léelas en orden), un Word, una \
hoja de cálculo con celdas separadas por tabuladores, una conversación de WhatsApp copiada, o \
un informe médico o una analítica. Mapea cada dato al campo del esquema POR SU SIGNIFICADO, esté \
donde esté y se llame como se llame ("Peso", "Kg actuales", "peso hoy: 82" son lo mismo). \
Ignora la maquetación, los logos y las instrucciones para quien rellena; lee texto impreso, \
manuscrito, tablas, márgenes, casillas marcadas (☑/X/círculos) y anotaciones sueltas.

REGLA DE ORO: si un dato no aparece, está en blanco o pone "no aplica", déjalo en null \
(o lista/texto vacío). NUNCA inventes datos: un error en peso, lesiones o medicación \
sería grave. El coach revisará todo antes de generar el plan. MAPEAR o INFERIR un valor \
a partir de lo que el cliente escribió NO es inventar; es obligatorio. Si un número es \
dudoso (manuscrito ilegible, dos valores distintos), pon el más probable y BAJA su confianza \
en `confidence`; si no puedes decidir, null y cuéntalo en la nota de su sección.

LECTURA EXHAUSTIVA, ESCRITURA SELECTIVA: la anamnesis es la BASE de toda la asesoría. \
Lee el documento ENTERO, frase a frase, incluidos márgenes, anotaciones a mano, respuestas \
fuera de su casilla y comentarios sueltos. Pero ESCRIBE selectivo: a las notas va lo que \
tiene señal para dieta, entrenamiento o adherencia — no cada casilla del documento. \
EXCEPCIÓN SIN RECORTE (seguridad): lesiones, patologías, alergias/intolerancias y \
medicación se recogen SIEMPRE al completo. Y si el cliente escribió algo ambiguo o \
contradictorio, recógelo tal cual en la nota de su sección (el coach decide), nunca lo omitas.

CAMPOS ESTRUCTURADOS OBLIGATORIOS — recórrelos UNO A UNO y rellénalos SIEMPRE que el dato \
aparezca en CUALQUIER parte del documento. NO dejes en null un campo cuyo dato esté presente:
  · birth_date ← fecha de nacimiento: convierte DD/MM/AAAA a YYYY-MM-DD (12/03/1990 → 1990-03-12). \
Si solo hay la EDAD ("34 años"), deja birth_date en null y escribe "- Edad declarada: 34 años" \
en lifestyle_notes (el coach pondrá la fecha).
  · sex ← sexo biológico: Hombre/varón/masculino→"male", Mujer/femenino→"female" (Otro→null).
  · phone ← teléfono/móvil tal cual (con prefijo si lo escribe).
  · height_cm ← altura/talla/estatura (si viene en metros, 1,78 m → 178); start_weight_kg ← \
peso actual; goal_weight_kg ← peso objetivo/deseado.
  · initial_waist_cm / initial_hip_cm / initial_arm_cm / initial_thigh_cm ← perímetros \
(cintura / cadera / brazo relajado / muslo) en cm de la antropometría inicial.
  · goal_type ← objetivo (a menudo NO hay casilla: INFIÉRELO del texto): perder grasa/definir/\
adelgazar→"fat_loss"; ganar músculo/volumen→"muscle_gain"; recomposición/tonificar→"recomp"; \
mantener el peso (sin ganar ni perder)→"maintenance"; recuperarse de una lesión/operación y \
volver a entrenar→"injury_recovery".
  · goal_deadline ← si el cliente declara un PLAZO o fecha para su objetivo ("para junio", \
"en 3 meses", "para la boda del 12/09"), conviértelo a YYYY-MM-DD (aprox. si hace falta).
  · level ← nivel en sala de pesas: Principiante/nunca/menos de 1 año→"beginner"; Intermedio→\
"intermediate"; Avanzado→"advanced".
  · training_place ← dónde entrena: Gimnasio/gym/box→"gym"; Casa/domicilio→"home"; \
Exterior/parque/calistenia→"outdoor".
  · training_days ← días que puede entrenar por semana (cuenta los días marcados L M X J V S D \
o el número que escriba).
  · daily_activity_level ← deduce la actividad DIARIA por el trabajo/estilo de vida: \
oficina o sentado→"sedentary"; de pie o caminando a ratos (comercio, docencia)→"light"; \
trabajo físico con muchos pasos→"active"; trabajo físico intenso (obra, mensajería, campo)→\
"very_active". Si no hay información suficiente, déjalo en null.
  · session_max_min ← duración media/máxima de la sesión, en minutos ("1 h" → 60).
  · diet_mode ← si menciona equivalencias/flexibilidad/opciones→"flexible_7"; si pide \
menú cerrado/dieta pautada día a día→"strict". Si no está claro, usa "flexible_7".
  · diet_pattern ← patrón alimentario: vegano→"vegano"; vegetariano→"vegetariano"; \
pescetariano→"pescetariano"; sin cerdo→"sin_cerdo"; halal→"halal"; kosher→"kosher"; \
omnívoro/"como de todo"/en blanco→null. Es SEGURIDAD: gobierna qué alimentos puede llevar su plan.
  · Si una respuesta de selección NO encaja en ningún valor del enum, deja el campo en null \
PERO recoge el texto literal en la nota de su sección — que el coach vea que el cliente \
contestó y qué escribió, nunca un campo vacío en silencio.
  · meals_per_day ← nº de comidas al día. Si marca "Lo decidís vosotros" o no consta → \
meals_per_day=null y meal_schedule=[] (DELEGA el número y reparto de comidas en el coach).
  · meal_schedule: de las comidas que nombre (desayuno, media mañana, comida, merienda, cena, \
pre-cama…) y del resto del documento, deduce las tomas y sus horas. Cada toma DEBE ser \
un objeto con "slot" (1,2,3…), "name" ("Desayuno","Comida","Merienda","Cena"…) y "time" \
("HH:MM"). Si no hay horas exactas, propón horarios razonables coherentes con el nº de comidas.
  · equipment: SOLO si entrena en casa/exterior, lista el material declarado (mancuernas, barra, \
banco, jaula, gomas, máquinas…). Si entrena en gimnasio, deja la lista vacía.
  · food_likes / food_dislikes / food_allergies: preferencias, aversiones y alergias/\
intolerancias alimentarias, estén en la sección que estén. Listas de alimentos concretos.

RESÚMENES POR SECCIÓN — FORMATO EN PUNTOS: cada campo es una lista de líneas cortas (una \
por dato), empezando CADA línea con "- ". Nada de párrafos largos. Fiel al documento, en español.
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
  · injuries_notes ← lesiones y movilidad (historial, dolores, cirugías ortopédicas, informes \
de fisio): TODAS las lesiones, sin recorte (seguridad). Una línea densa por lesión: "- [zona y \
lado] · [activa/resuelta, desde cuándo] · evitar: [movimientos]". Máximo ~20 palabras por línea.
  · medical_notes ← historia clínica, salud digestiva y hormonal, salud femenina si aplica, \
hábitos tóxicos y ANALÍTICAS: patologías, antecedentes familiares, cirugías, intolerancias, \
tabaco/alcohol/otras sustancias, deposiciones/síntomas digestivos, ciclo menstrual/embarazos/\
menopausia. PREFIJA cada línea con su tema: "- Clínica: …", "- Digestivo: …", "- Salud \
femenina: …", "- Hábitos tóxicos: …". Si el documento trae una ANALÍTICA (o el cliente copia \
valores), vuelca en "- Analítica (fecha): …" los marcadores FUERA DE RANGO con valor, unidad y \
rango de referencia, y agrupa los normales en una sola línea ("resto normal: hemograma, …").
  · medication_notes ← medicación actual y anticonceptivos hormonales, SIN recorte. \
Formato: "- Nombre — dosis — frecuencia" (+ efecto relevante para dieta/entreno si lo hay). \
Sin frases introductorias.
  · current_supplements ← suplementación: "- Nombre — dosis — momento", una línea por \
suplemento, máximo 6; sin valoraciones.
  · sport_history ← experiencia con pesas, otros deportes, ejercicios favoritos / que detesta, \
y si el documento trae una RUTINA o dieta previa, resúmela aquí en 1-2 líneas ("- Rutina \
previa: torso-pierna 4 días, básicos con 60-80 kg"). MÁXIMO 5 viñetas: años y nivel real con \
los básicos; qué métodos funcionaron o fallaron; otros deportes actuales con frecuencia; \
matiz técnico a vigilar; y SIEMPRE que el cliente los declare, "- Ejercicios: favoritos … / \
detesta …" (el generador los respeta).
  · lifestyle_notes ← motivo y objetivos (corto/largo plazo, qué funcionó o no, motivación/\
confianza), logística y entorno alimentario, comida emocional, hidratación, trabajo y día a \
día, sueño y recuperación, estrés y energía, auto-evaluación. PREFIJA cada línea con su tema, \
EMPEZANDO SIEMPRE por el motivo: "- Motivo: …", "- Trabajo: …", "- Sueño: …", "- Estrés: …", \
"- Conducta alimentaria: …", "- Logística: …", "- Hidratación: …", "- Horario de entreno: …" \
(la hora habitual a la que entrena condiciona las comidas peri-entreno). MÁXIMO 6 viñetas en \
total, ordenadas por impacto en la adherencia; máximo 1-2 líneas por tema; los temas sin nada \
relevante se omiten.

SÍNTESIS:
  · deep_analysis: 3-5 líneas en puntos ("- …"), ORDENADAS de más a menos importante, máximo \
~20 palabras por punto. Un punto = UNA decisión de plan (qué respetar, qué priorizar, qué \
vigilar), no un tema: cruza objetivo, lesiones, hábitos, sueño, estrés y conducta alimentaria \
como material, sin obligación de cubrirlos todos. Sin repetir lo que ya está en los campos \
estructurados ni relleno motivacional.

CONSTANCIA DE LA LECTURA (lector universal):
  · document_kind: qué ES el documento (anamnesis_dq | cuestionario_ajeno | notas | analitica \
| informe_medico | plan_dieta | plan_entreno | mixto | otro).
  · source_inventory: una línea corta por bloque o tema que contiene el documento, en su orden \
("- Datos personales", "- Tabla de perímetros", "- Analítica 12/05/2026", "- Texto sobre \
motivación"). Sirve para que el coach compruebe que se leyó ENTERO.
  · unmapped_info: lo relevante para dieta/entreno/salud que NO encaja en ningún campo, una \
línea por dato. Nada se pierde: si dudas de dónde va algo, ponlo aquí.
  · confidence: 0-1 por campo crítico rellenado (sex, birth_date, height_cm, start_weight_kg, \
goal_type, food_allergies, medication_notes, medical_notes, injuries_notes). 1 = literal y \
claro; 0,6 = inferido o manuscrito dudoso. Omite los campos que dejaste en null.

Devuelve SOLO un objeto JSON válido que cumpla el esquema. Sin texto adicional."""


def _user_prompt(documento) -> str:
    """El prompt de usuario describe el documento REAL (ya no «el PDF oficial
    de 10 páginas»): la IA sabe si recibe un PDF, tres fotos o una hoja."""
    que = getattr(documento, "descripcion", None) or "documento"
    nombre = getattr(documento, "nombre", None) or "documento"
    return (
        f"Lee el documento adjunto («{nombre}», {que}) ENTERO y extrae TODA la información "
        "en JSON según el esquema. Puede tener cualquier estructura: recórrelo de principio a "
        "fin y rellena tanto los campos estructurados (antropometría, objetivo, entrenamiento, "
        "dieta) como los resúmenes por sección (clínica, medicación, suplementos, deportes, "
        "lesiones, estilo de vida), el inventario de lo que contiene y lo que no cupo en "
        "ninguna casilla. Lo que no encuentres o esté en blanco, déjalo en null; no inventes datos."
    )


# ------------------------------------------------- segundo pase (§5) -------
# Tras extraer, un SEGUNDO pase relee el MISMO documento (cacheado → ~10 % del
# coste) con otra pregunta: «comprueba estos campos críticos contra el
# documento». Las discrepancias NO se resuelven solas: se enseñan al coach.
# Es el `dual_pass_extract` del hardening §5, que estaba escrito y sin cablear.

CRITICOS_ESCALARES = ("sex", "birth_date", "height_cm", "start_weight_kg", "goal_type")
CRITICOS_LISTA = ("food_allergies",)
CRITICOS_TEXTO = ("medication_notes", "medical_notes", "injuries_notes")


class VerificacionCritica(BaseModel):
    """Lo que el segundo pase VE en el documento para los campos críticos."""

    sex: str | None = None
    birth_date: date | None = None
    height_cm: float | None = None
    start_weight_kg: float | None = None
    goal_type: str | None = None
    food_allergies: list[str] = Field(default_factory=list)
    medication_notes: str | None = None
    medical_notes: str | None = None
    injuries_notes: str | None = None
    omissions: list[str] = Field(
        default_factory=list,
        description="Datos relevantes del documento que FALTAN en la extracción que te enseño")

    _v_enum = field_validator("sex", "goal_type", mode="before")(
        lambda cls, v, info: AnamnesisExtraction._normalize_enum.__func__(cls, v, info))  # type: ignore[attr-defined]

    @field_validator("omissions", "food_allergies", mode="before")
    @classmethod
    def _listas(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [x.strip(" -•") for x in v.splitlines() if x.strip(" -•")]
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return []


_VERIFY_SYSTEM = """Eres el REVISOR de una extracción de datos clínicos y antropométricos. \
Recibes el MISMO documento que leyó un primer extractor y su resultado para los campos \
CRÍTICOS. Tu único trabajo: mirar el documento de nuevo, de forma independiente, y decir qué \
ves TÚ para cada campo crítico —sin dejarte llevar por lo que dice la extracción— y qué datos \
relevantes (clínicos, medicación, lesiones, alergias, antropometría, objetivo) están en el \
documento y FALTAN en la extracción. Mismos formatos: sexo male|female, fecha YYYY-MM-DD, \
altura en cm, peso en kg, objetivo fat_loss|muscle_gain|recomp|maintenance|injury_recovery, \
alergias como lista de alimentos, notas como líneas "- …". Lo que no esté en el documento, \
null o lista vacía. Nunca inventes. Devuelve SOLO el JSON del esquema."""


def _norm_texto(v) -> str:
    import unicodedata

    s = "" if v is None else str(v).strip().lower()
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def _escalar(v):
    if isinstance(v, float):
        return round(v, 1)
    if isinstance(v, date):
        return v.isoformat()
    return v


def comparar_pases(a: dict, b: dict, confianza_a: dict | None = None) -> dict:
    """Compara la extracción (A) con el segundo pase (B) SOLO en lo crítico.
    Escalares: igualdad (números a 1 decimal, fechas como texto). Alergias:
    conjuntos normalizados. Notas clínicas: solo se avisa si un pase ve algo y
    el otro nada (el texto libre nunca coincide letra a letra y compararlo
    daría ruido). Devuelve discrepancias legibles, omisiones, confianza por
    campo y `needs_review`."""
    from app.services.anamnesis_extraction import dual_pass_extract

    ca = {k: float(v) for k, v in (confianza_a or {}).items()}
    sub_a = {k: _escalar(a.get(k)) for k in CRITICOS_ESCALARES}
    sub_b = {k: _escalar(b.get(k)) for k in CRITICOS_ESCALARES}
    res = dual_pass_extract(lambda: (sub_a, ca), lambda: sub_b)
    etiquetas = {"sex": "sexo", "birth_date": "fecha de nacimiento", "height_cm": "altura",
                 "start_weight_kg": "peso actual", "goal_type": "objetivo",
                 "food_allergies": "alergias", "medication_notes": "medicación",
                 "medical_notes": "historia clínica", "injuries_notes": "lesiones"}
    discrepancias: list[str] = []
    desajustados: set[str] = set()
    for k in CRITICOS_ESCALARES:
        va, vb = sub_a.get(k), sub_b.get(k)
        if va != vb:
            # Solo cuenta si el 2º pase VIO algo (un null suyo es «no lo encontré»,
            # que se recoge en omisiones si procede, no una contradicción).
            if vb is None:
                continue
            desajustados.add(k)
            discrepancias.append(
                f"{etiquetas[k]}: la extracción dice «{va if va is not None else '—'}» "
                f"y la relectura ve «{vb}»")
    conf = dict(res.confidence)
    # Dos lecturas INDEPENDIENTES que coinciden en un dato confirman el dato:
    # la confianza sube aunque el extractor la declarara baja (manuscrito
    # dudoso que la relectura leyó igual). `dual_pass_extract` se queda con la
    # mínima por diseño; aquí la coincidencia es información nueva.
    for k in CRITICOS_ESCALARES:
        if sub_a.get(k) is not None and sub_a.get(k) == sub_b.get(k):
            conf[k] = max(conf.get(k, 1.0), 0.9)
    for k in CRITICOS_LISTA:
        sa = {_norm_texto(x) for x in (a.get(k) or []) if _norm_texto(x)}
        sb = {_norm_texto(x) for x in (b.get(k) or []) if _norm_texto(x)}
        if sa != sb and sb:
            solo_b = sorted(sb - sa)
            solo_a = sorted(sa - sb)
            partes = []
            if solo_b:
                partes.append("la relectura añade " + ", ".join(solo_b))
            if solo_a:
                partes.append("la relectura no ve " + ", ".join(solo_a))
            discrepancias.append(f"{etiquetas[k]}: " + "; ".join(partes))
            desajustados.add(k)
            conf[k] = min(ca.get(k, 1.0), 0.5)
        else:
            conf.setdefault(k, ca.get(k, 1.0))
    for k in CRITICOS_TEXTO:
        tiene_a, tiene_b = bool(_norm_texto(a.get(k))), bool(_norm_texto(b.get(k)))
        if tiene_b and not tiene_a:
            discrepancias.append(f"{etiquetas[k]}: la relectura encuentra datos y la "
                                 f"extracción los dejó vacíos: «{str(b.get(k))[:160]}»")
            desajustados.add(k)
            conf[k] = min(ca.get(k, 1.0), 0.5)
        else:
            conf.setdefault(k, ca.get(k, 1.0))
    omisiones = [str(x).strip() for x in (b.get("omissions") or []) if str(x).strip()]
    criticos = set(CRITICOS_ESCALARES) | set(CRITICOS_LISTA) | set(CRITICOS_TEXTO)
    # Campos críticos con la confianza por debajo del umbral §5 (0,85): la
    # relectura no los vio, o el extractor los dio por dudosos. Van con nombre
    # —la UI y el mensaje del endpoint los enseñan— porque una «duda» sin decir
    # en qué campo mandaba al coach a revisar la ficha entera.
    orden = (*CRITICOS_ESCALARES, *CRITICOS_LISTA, *CRITICOS_TEXTO)
    # Un campo ya listado como desajuste no se repite como «confianza baja».
    poca_confianza = [k for k in orden
                      if k not in desajustados and a.get(k) not in (None, [], "")
                      and conf.get(k, 1.0) < 0.85]
    needs_review = bool(discrepancias) or bool(poca_confianza)
    return {"discrepancies": discrepancias, "omissions": omisiones,
            "confidence": conf, "needs_review": needs_review,
            "low_confidence": poca_confianza,
            "low_confidence_labels": [etiquetas[k] for k in poca_confianza]}


def resumen_de_dudas(ver: dict) -> str | None:
    """Frase para el coach con el POR QUÉ de la duda, por motivo: desajustes
    de la relectura, campos con confianza baja y datos echados en falta. None
    si no hay dudas. (Antes se contaban solo los desajustes: con confianza baja
    y cero desajustes salía «no coincide en 0 datos».)"""
    if not ver or not ver.get("needs_review"):
        return None
    partes = []
    disc = ver.get("discrepancies") or []
    if disc:
        partes.append(f"la relectura no coincide en {len(disc)} dato{'s' if len(disc) != 1 else ''}")
    bajos = ver.get("low_confidence_labels") or []
    if bajos:
        partes.append("confianza baja en " + ", ".join(bajos))
    omis = ver.get("omissions") or []
    if omis:
        partes.append(f"{len(omis)} dato{'s' if len(omis) != 1 else ''} que la relectura echa en falta")
    if not partes:
        partes.append("la relectura deja dudas en algún campo crítico")
    return "; ".join(partes)


def verificar_extraccion(documento, extraida: AnamnesisExtraction, ai) -> dict:
    """Segundo pase sobre el MISMO documento. Nunca lanza: si la IA falla, se
    devuelve `{"skipped": motivo}` y la extracción sigue valiendo."""
    from app.config import settings

    a = extraida.model_dump()
    resumen = {k: (a.get(k).isoformat() if isinstance(a.get(k), date) else a.get(k))
               for k in (*CRITICOS_ESCALARES, *CRITICOS_LISTA, *CRITICOS_TEXTO)}
    import json as _json

    user = (
        "Documento adjunto: el mismo que leyó el extractor. Esta fue su extracción de los "
        "campos críticos:\n" + _json.dumps(resumen, ensure_ascii=False) +
        "\n\nRelee el documento y devuelve lo que ves TÚ para esos campos, más `omissions` "
        "con lo relevante que falte. SOLO el JSON."
    )
    try:
        b = ai.read_document_json(
            model=settings.model_heavy, system=_VERIFY_SYSTEM, user=user,
            documento=documento, schema=VerificacionCritica, temperature=0,
            max_tokens=2500,
        )
    except Exception as exc:  # noqa: BLE001 — el 2º pase nunca tumba la lectura
        return {"skipped": f"segundo pase no disponible: {str(exc)[:160]}",
                "discrepancies": [], "omissions": [], "confidence": dict(extraida.confidence),
                "needs_review": False, "low_confidence": [], "low_confidence_labels": []}
    return comparar_pases(a, b.model_dump(), extraida.confidence)


@dataclass
class LecturaAnamnesis:
    """Resultado completo de leer un documento como anamnesis."""

    extraction: AnamnesisExtraction
    verification: dict
    documento: object


def extract_anamnesis_from_document(documento, ai, *, verify: bool | None = None) -> LecturaAnamnesis:
    """Lee un `Documento` de CUALQUIER formato/estructura y devuelve los datos
    extraídos (validados) + la verificación del segundo pase."""
    from app.config import settings

    extraida = ai.read_document_json(
        model=settings.model_heavy,
        system=_EXTRACTION_SYSTEM,
        user=_user_prompt(documento),
        documento=documento,
        schema=AnamnesisExtraction,
        temperature=0,  # §14: extracción determinista (mismos datos → misma lectura)
    )
    hacer = settings.extraction_double_pass if verify is None else verify
    verificacion = (verificar_extraccion(documento, extraida, ai) if hacer
                    else {"skipped": "desactivado", "discrepancies": [], "omissions": [],
                          "confidence": dict(extraida.confidence), "needs_review": False,
                          "low_confidence": [], "low_confidence_labels": []})
    return LecturaAnamnesis(extraida, verificacion, documento)


def extract_anamnesis_from_pdf(pdf_bytes: bytes, ai) -> AnamnesisExtraction:
    """Compatibilidad: lee un PDF con el lector universal (sin segundo pase)."""
    from app.services.document_reader import normalizar

    return extract_anamnesis_from_document(
        normalizar(pdf_bytes, "anamnesis.pdf"), ai, verify=False).extraction
