

===== FILE: backend/app/services/__init__.py =====



===== FILE: backend/app/services/adapt_plan.py =====

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

from app.models import Period, Plan
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
    m = re.search(r"([+-]?\d+(?:[.,]\d+)?)", text or "")
    if not m:
        return (None, None)
    val = float(m.group(1).replace(",", "."))
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
    """Aplica un delta o un objetivo absoluto y nunca baja del suelo (>=0)."""
    result = val if mode == "abs" else (current or 0) + val
    return int(round(max(floor, result)))


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

    base = db.scalar(
        select(Plan).where(Plan.client_id == client_id, Plan.status == "published")
        .order_by(Plan.version.desc()).limit(1)
    ) or db.scalar(
        select(Plan).where(Plan.client_id == client_id).order_by(Plan.version.desc()).limit(1)
    )
    if not base:
        raise AdaptError("El cliente no tiene un plan base que adaptar.")

    nut = copy.deepcopy(base.nutrition_json or {})
    tr = copy.deepcopy(base.training_json or {})
    edu = copy.deepcopy(base.education_json or {})
    macros = nut.setdefault("macros", {})

    for a in adjustments:
        area = _norm(a.get("area", ""))
        change = a.get("change", "")
        cn = _norm(change)
        mode, val = _parse_change(change)
        if val is None:
            continue
        if "diet" in area or "nutri" in area:
            if "proteina" in cn:
                macros["protein_g"] = _apply(macros.get("protein_g"), mode, val)
            if "hidrato" in cn or "carbo" in cn or re.search(r"\bch\b", cn):
                macros["carbs_g"] = _apply(macros.get("carbs_g"), mode, val)
            if ("kcal" in cn or "calor" in cn) and "manten" not in cn:
                nut["target_kcal"] = _apply(nut.get("target_kcal"), mode, val)
        elif "entren" in area:
            # En entreno solo aplicamos ajustes RELATIVOS de carga (+X kg): un
            # objetivo absoluto no se puede repartir entre todos los ejercicios.
            if mode == "delta" and "kg" in cn:
                for s in tr.get("sessions", []):
                    for ex in s.get("exercises", []):
                        if ex.get("start_weight_hint_kg"):
                            ex["start_weight_hint_kg"] = round(ex["start_weight_hint_kg"] + val, 1)

    if adjustments:
        grid = "\n".join(f"- [{a.get('area')}] {a.get('change')} — {a.get('reason')}" for a in adjustments)
        nut["rationale"] = f"Adaptación a la revisión quincenal #{period.period_index}:\n{grid}"
    else:
        nut["rationale"] = (f"Copia para adaptar a la revisión quincenal #{period.period_index} "
                            "(la revisión no incluía ajustes automáticos: edita manualmente).")
    tr["split_rationale"] = (tr.get("split_rationale", "") or "") + \
        f" · Adaptado a la revisión quincenal #{period.period_index}."

    last = db.scalar(
        select(Plan).where(Plan.client_id == client_id, Plan.month_index == base.month_index)
        .order_by(Plan.version.desc()).limit(1)
    )
    new_version = (last.version if last else 0) + 1
    plan = Plan(
        client_id=client_id, month_index=base.month_index, version=new_version, status="draft",
        nutrition_json=nut, training_json=tr, education_json=edu,
        guardrail_flags=[], generated_by="adaptación quincenal",
    )
    db.add(plan)
    db.flush()
    log_event(db, "plan", plan.id, "plan_adapted",
              {"from_plan": base.id, "period_index": period.period_index})
    db.commit()
    db.refresh(plan)
    return plan


===== FILE: backend/app/services/ai/__init__.py =====



===== FILE: backend/app/services/ai/client.py =====

"""Cliente de IA — capa fina sobre la API de Anthropic (PARTE D).

Responsabilidades:
- Llamar al modelo (HEAVY para generación/visión, LIGHT para parseo/matching).
- Forzar salida JSON, parsearla de forma robusta (tolera ```json ... ``` por si
  el modelo se desvía) y validarla contra un schema Pydantic.
- Retry 1 con el error de validación inyectado ("tu JSON falló en X, corrígelo").
- Segundo fallo → AIGenerationError, que el orquestador traduce a estado de
  error recuperable + notificación al coach.

Parámetros fijos (D.2): temperatura 0.3, max_tokens generoso.

El cliente NO conoce el dominio (nutrición/entrenamiento): solo recibe system
prompt, user prompt y schema. El conocimiento experto vive en prompts.py y la
orquestación en generator.py.
"""

from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.config import settings

TEMPERATURE = 0.3
# Generoso: el banco de comidas (4 slots × 7 opciones con ingredientes/macros) y el
# núcleo del plan son salidas grandes; 8000 truncaba el JSON → fallo de parseo.
MAX_TOKENS = 16000

T = TypeVar("T", bound=BaseModel)

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class AIGenerationError(RuntimeError):
    """La IA no produjo JSON válido conforme al schema tras el reintento."""

    def __init__(self, message: str, last_error: str | None = None):
        super().__init__(message)
        self.last_error = last_error


def _translate_api_error(exc: Exception) -> "AIGenerationError | None":
    """Traduce un error de la API de Anthropic (sin crédito, rate limit, clave
    inválida, etc.) a AIGenerationError con mensaje legible, para que el endpoint
    devuelva un 502 claro en vez de un 500 opaco. Devuelve None si no es un error
    de la API (en ese caso, se deja propagar)."""
    try:
        from anthropic import APIError
    except Exception:
        return None
    if isinstance(exc, APIError):
        msg = getattr(exc, "message", None) or str(exc)
        return AIGenerationError(f"La API de Anthropic devolvió un error: {msg}")
    return None


def _extract_json(text: str) -> str:
    """Aísla el JSON aunque venga envuelto en markdown o con texto alrededor."""
    text = text.strip()
    fenced = _JSON_FENCE.search(text)
    if fenced:
        return fenced.group(1).strip()
    # Primer { hasta el último } — defensa ante preámbulos accidentales.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


class AIClient:
    """Wrapper con reintento y validación. Inyectable/mockeable en tests."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.anthropic_api_key
        self._client = None  # perezoso: no instanciar SDK si se usa un mock

    def _anthropic(self):
        if self._client is None:
            from anthropic import Anthropic

            self._client = Anthropic(api_key=self._api_key)
        return self._client

    def _raw_call(self, *, model: str, system: str, user: str) -> str:
        """Una llamada cruda al modelo. Sobrescribible en tests."""
        try:
            resp = self._anthropic().messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as exc:
            translated = _translate_api_error(exc)
            if translated:
                raise translated from exc
            raise
        return "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )

    def _raw_call_with_pdf(
        self, *, model: str, system: str, user: str, pdf_bytes: bytes
    ) -> str:
        """Una llamada al modelo incluyendo un PDF como documento adjunto.

        Usa el bloque `document` de la API de Anthropic (lectura nativa de PDF).
        Sobrescribible en tests.
        """
        import base64

        b64 = base64.standard_b64encode(pdf_bytes).decode("ascii")
        try:
            resp = self._anthropic().messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": user},
                    ],
                }],
            )
        except Exception as exc:
            translated = _translate_api_error(exc)
            if translated:
                raise translated from exc
            raise
        return "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )

    def read_pdf_json(
        self, *, model: str, system: str, user: str, pdf_bytes: bytes, schema: type[T]
    ) -> T:
        """Lee un PDF, extrae datos y los valida contra el esquema. Reintenta una vez."""
        last_error: str | None = None
        attempt_user = user
        for _ in range(2):
            raw = self._raw_call_with_pdf(
                model=model, system=system, user=attempt_user, pdf_bytes=pdf_bytes
            )
            try:
                data = json.loads(_extract_json(raw))
            except json.JSONDecodeError as exc:
                last_error = f"JSON mal formado: {exc}"
            else:
                try:
                    return schema.model_validate(data)
                except ValidationError as exc:
                    last_error = _summarize_validation_error(exc)
            attempt_user = (
                f"{user}\n\n--- CORRECCIÓN REQUERIDA ---\n"
                f"Tu respuesta anterior falló la validación: {last_error}\n"
                "Devuelve de nuevo SOLO el JSON corregido, sin texto adicional."
            )
        raise AIGenerationError(
            "La IA no extrajo un JSON válido del PDF tras el reintento", last_error
        )

    def generate_json(
        self, *, model: str, system: str, user: str, schema: type[T]
    ) -> T:
        """Genera, parsea y valida. Reintenta UNA vez con el error inyectado."""
        last_error: str | None = None
        attempt_user = user

        for attempt in range(2):
            raw = self._raw_call(model=model, system=system, user=attempt_user)
            try:
                data = json.loads(_extract_json(raw))
            except json.JSONDecodeError as exc:
                last_error = f"JSON mal formado: {exc}"
            else:
                try:
                    return schema.model_validate(data)
                except ValidationError as exc:
                    last_error = _summarize_validation_error(exc)

            # Preparar reintento con el error concreto inyectado.
            attempt_user = (
                f"{user}\n\n--- CORRECCIÓN REQUERIDA ---\n"
                f"Tu respuesta anterior falló la validación: {last_error}\n"
                "Devuelve de nuevo SOLO el JSON corregido, sin texto adicional."
            )

        raise AIGenerationError(
            "La IA no devolvió un JSON válido tras el reintento", last_error
        )


def _summarize_validation_error(exc: ValidationError) -> str:
    """Resumen compacto y accionable de los errores de Pydantic para el reintento."""
    parts = []
    for err in exc.errors()[:6]:
        loc = ".".join(str(p) for p in err["loc"])
        parts.append(f"{loc}: {err['msg']}")
    return " | ".join(parts)


===== FILE: backend/app/services/ai/extraction.py =====

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


===== FILE: backend/app/services/ai/feedback.py =====

"""Análisis de feedback con IA (parte cualitativa del informe quincenal).

El backend calcula TODAS las métricas (peso, adherencia, e1RM, perímetros) en
services/metrics.py y se las entrega ya hechas. La IA SOLO redacta el análisis
en lenguaje natural y las recomendaciones, NUNCA recalcula números.

Salida validada contra `FeedbackAIOutput`. Campos con defaults: si la IA omite
alguno, no se descarta todo el informe (el coach revisa antes de enviarlo).
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from app.config import settings


class PlanAdjustment(BaseModel):
    """Una fila de la CUADRÍCULA DE CAMBIOS del informe: qué se cambia y por qué."""

    area: str = Field(description='Área: "Dieta" | "Entrenamiento" | "Cardio/NEAT" | "Hábitos"')
    change: str = Field(description="El cambio CONCRETO (p. ej. 'Subir CH +30 g en comida y cena').")
    reason: str = Field(description="Por qué, basado en los datos registrados por el cliente.")


class FeedbackAIOutput(BaseModel):
    """Texto cualitativo del feedback. El backend aporta los números."""

    natural_analysis: str = Field(
        default="",
        description="Resumen BREVE de cómo ha ido el período (peso, adherencia, "
        "energía, fuerza), cercano y honesto. MÁXIMO 3-4 frases cortas — el detalle "
        "va en changes_bullets y next_objectives, no repitas.",
    )
    changes_bullets: list[str] = Field(
        default_factory=list,
        description="Qué se va a cambiar en el plan y por qué. Máximo 5 bullets.",
    )
    plan_adjustments: list[PlanAdjustment] = Field(
        default_factory=list,
        description="CUADRÍCULA DE CAMBIOS: 2-6 ajustes concretos (área, cambio, porqué) "
        "que se aplicarán al plan de dieta y entrenamiento, deducidos de los datos "
        "registrados (entrenos, diario, revisión quincenal).",
    )
    answers: str | None = Field(
        default=None,
        description="Respuesta a las dudas que dejó el cliente al cerrar (si las hay).",
    )
    next_objectives: list[str] = Field(
        default_factory=list,
        description="2-4 objetivos concretos para las próximas 2 semanas.",
    )
    closing_message: str = Field(
        default="",
        description="Mensaje de cierre breve y motivador.",
    )
    ai_photo_analysis: str | None = Field(
        default=None,
        description="Análisis de la evolución visible en las fotos (solo si hay fotos).",
    )


_SYSTEM = """Eres el dietista-entrenador (marca DQ) redactando el FEEDBACK quincenal \
para tu cliente, en castellano, con tono cercano, honesto y motivador (sin adular).

REGLA CRÍTICA: NO calcules ni inventes números. El backend ya te entrega las métricas \
(cambio de peso, ritmo semanal, adherencia, energía/sueño, progresión de fuerza). \
Úsalas tal cual; tu trabajo es INTERPRETARLAS y dar recomendaciones accionables.

- natural_analysis: resumen BREVE (MÁXIMO 3-4 frases cortas) de cómo ha ido el período \
(peso, adherencia, energía, fuerza). Reconoce lo bueno y señala lo mejorable. NO te \
extiendas: el detalle va en changes_bullets y next_objectives, no lo repitas aquí.
- changes_bullets: máximo 5 cambios concretos para el plan y POR QUÉ (p. ej. "subo 100 \
kcal porque el ritmo de bajada es muy agresivo").
- plan_adjustments: la CUADRÍCULA DE CAMBIOS del informe (2-6 filas). Cada fila = {area, \
change, reason}. Basa cada ajuste en los DATOS REGISTRADOS por el cliente (series de \
entreno y su progresión, peso/sueño/pasos/saciedad/agua del diario, sensaciones y \
adherencia de la revisión quincenal). Cubre dieta Y entrenamiento cuando proceda.
- answers: responde a las dudas del cliente si las dejó; si no, déjalo en null.
- next_objectives: 2-4 objetivos claros y medibles para las próximas 2 semanas.
- closing_message: 1-2 frases de cierre motivadoras.
- ai_photo_analysis: SOLO si te indican que hay fotos; describe la evolución visible \
de forma prudente. Si no hay fotos, déjalo en null.

Devuelve SOLO un objeto JSON válido conforme al esquema. Sin texto adicional."""


def _user_prompt(payload: dict) -> str:
    return (
        "Redacta el feedback del período con estos DATOS YA CALCULADOS por el backend "
        "(no recalcules). Devuelve el JSON del esquema.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def generate_feedback_analysis(payload: dict, ai) -> FeedbackAIOutput:
    """Pide a la IA la parte cualitativa del feedback a partir de las métricas."""
    return ai.generate_json(
        model=settings.model_heavy,
        system=_SYSTEM,
        user=_user_prompt(payload),
        schema=FeedbackAIOutput,
    )


===== FILE: backend/app/services/ai/generator.py =====

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
    meals_per_day: int
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
            "modo_dieta": ctx.diet_mode, "num_comidas": ctx.meals_per_day,
            "horario_comidas": ctx.meal_schedule,
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


===== FILE: backend/app/services/ai/prompts.py =====

"""Prompts de IA embebidos (PARTE D).

Toda la metodología de las PARTES E (nutrición) y F (entrenamiento) se embebe
LITERALMENTE como contexto experto en el system prompt, junto con los
guardrails como instrucciones explícitas (la validación dura la hace el
backend en services/guardrails.py; aquí se le pide a la IA que los respete de
entrada para minimizar reintentos).

Estas constantes son la ÚNICA fuente de verdad de los prompts. No se generan
ni se improvisan en runtime: se formatean con datos del cliente y nada más.
"""

from __future__ import annotations

# ============================================================ D.1 base ====

SYSTEM_BASE = """Eres un experto en nutrición deportiva y ciencias del entrenamiento de fuerza. \
Trabajas con evidencia científica actual, personalización extrema y lenguaje profesional pero \
cercano. Tus planes los seguirán personas reales: prioriza adherencia, claridad y seguridad por \
encima de la perfección teórica. Respondes EXCLUSIVAMENTE con JSON válido conforme al schema \
indicado, sin markdown ni texto fuera del JSON."""


METHODOLOGY_NUTRITION = """\
=== METODOLOGÍA DE NUTRICIÓN (conocimiento experto) ===

ENERGÍA
- BMR: Mifflin-St Jeor; si hay % graso, Katch-McArdle (370 + 21.6 × masa magra kg).
- TDEE: BMR × factor de actividad (1.2 / 1.375 / 1.55 / 1.725 / 1.9) según días de entrenamiento.
- Pérdida de grasa: déficit 15–25% del TDEE (mayor a mayor % graso; conservador en magros/novatos).
  Ganancia: superávit 5–12% (menor en avanzados). Recomposición: mantenimiento ±5% con proteína alta.
- Las calorías SIEMPRE con justificación: TDEE estimado + ajuste + por qué.
  IMPORTANTE: el backend ya te entrega BMR, TDEE y kcal objetivo calculados. NO recalcules:
  parte de esos números y justifícalos. Tú afinas dentro de los límites, no inventas la base.

MACROS Y DISTRIBUCIÓN
- Proteína 1.6–2.2 g/kg (hasta 2.6 en déficit agresivo y sujeto magro); grasas mínimo 0.6–0.8 g/kg;
  carbohidratos el resto, priorizados peri-entrenamiento.
- Reparto de proteína en tomas de 0.3–0.5 g/kg según número de comidas declarado.
- Fibra orientativa 25–40 g/día; agua 30–40 ml/kg como guía.

FORMATO DEL PLAN (clave: facilidad de seguimiento)
- Macros = contrato; menú = plantilla. El banco de opciones por slot debe cumplir los macros del slot.
- Doble medida SIEMPRE: gramos + medida casera. Conversiones estándar: cucharada sopera ≈ 15 ml
  (aceite 10 g); cucharadita ≈ 5 ml; taza ≈ 250 ml; puñado de arroz/pasta crudos ≈ 60–80 g;
  palma de la mano ≈ 100–120 g de carne/pescado; huevo M ≈ 55 g; rebanada de pan ≈ 40 g;
  pieza mediana de fruta ≈ 150 g. Úsalas para los campos `household`.
- TODOS los pesos en CRUDO (estándar profesional).
- Suplementación solo con evidencia (creatina 5 g/día, cafeína 3–6 mg/kg pre-entreno si tolera,
  proteína en polvo como conveniencia, vitamina D, omega-3). NUNCA sustancias farmacológicas.
- Reglas de flexibilidad explícitas: comidas sociales (1–2/semana con pautas), alcohol, viajes,
  qué hacer si falla una comida (compensación simple, nunca castigo).
- Déficit >8 semanas consecutivas → considerar refeed semanal o diet break de 1 semana.
- Respeta SIEMPRE alergias, aversiones, preferencias y horarios de la anamnesis.

GUARDRAILS DE NUTRICIÓN (obligatorios — el backend los revalida):
- kcal objetivo ≥ max(BMR, 1400 mujer / 1600 hombre).
- Ajuste máximo ±15% kcal por recalibración.
- Proteína mínima 1.4 g/kg; grasas mínimas 0.5 g/kg.
- Déficit máximo 30% del TDEE; superávit máximo 15% del TDEE.
- Cada opción de comida debe cumplir los macros de su slot con ±5% de tolerancia."""


METHODOLOGY_TRAINING = """\
=== METODOLOGÍA DE ENTRENAMIENTO (conocimiento experto) ===

PROGRAMACIÓN Y SOBRECARGA PROGRESIVA
- División según días: 2→Full Body / 3→FB o U-L+FB / 4→Upper-Lower / 5→U-L+PPL o especialización /
  6→PPL×2. Siempre justificada.
- Sobrecarga progresiva EXPLÍCITA: tabla de progresión semanal (semana 1 base, 2–3 progresión de
  carga y/o volumen, semana 4 deload con volumen −40–50% e intensidad −10–20%). Cada ejercicio
  lleva su `progression_rule` en lenguaje claro ("cuando completes 4×8 con RIR 2, sube 2.5 kg").
- Doble progresión por defecto; lineal simple en principiantes los 2 primeros meses.
- RIR: compuestos pesados 2–3, secundarios 1–2, aislamiento 0–2. Tempo solo cuando aporte.
  Descansos: compuestos 2–3 min, aislamiento 60–90 s.
- Volumen semanal (series efectivas/grupo): principiante 8–12, intermedio 10–18, avanzado 14–22.
- Cardio sin interferir con la recuperación: pasos diarios objetivo + LISS/HIIT según objetivo.
- En recalibraciones: ajusta cargas desde los e1RM reales que te entrega el backend.

BIOMECÁNICA Y EDUCACIÓN
- Cada ejercicio lleva `technique_cue` (1 línea accionable) y `biomech_cue` (por qué, 1 línea
  accesible). La sección educativa incluye píldoras de ciencia y cues por patrón de movimiento.
- Objetivo: que el cliente entienda QUÉ hace y POR QUÉ.

BIBLIOTECA DE EJERCICIOS
- SOLO seleccionas ejercicios de la biblioteca que se te entrega (ya filtrada por equipamiento,
  nivel, lesiones y exclusiones). Usa exclusivamente los `exercise_id` proporcionados.

GUARDRAILS DE ENTRENAMIENTO (obligatorios — el backend los revalida):
- Máximo 25 series por grupo muscular y semana.
- Incremento de carga máximo +10% por ejercicio y recalibración.
- Nunca uses ejercicios contraindicados para las lesiones declaradas.
- Nunca excedas los días ni la duración de sesión declarados (estimación: series × 3 min + 10)."""


# Solo nutrición + guardrails de comida para la llamada ② (ahorra contexto).
METHODOLOGY_NUTRITION_BRIEF = """\
=== REGLAS DE COMIDAS ===
- TODOS los pesos en CRUDO. Doble medida siempre: gramos + medida casera (`household`).
- Conversiones: cucharada ≈ 15 ml (aceite 10 g); cucharadita ≈ 5 ml; taza ≈ 250 ml;
  puñado de arroz/pasta crudos ≈ 60–80 g; palma ≈ 100–120 g; huevo M ≈ 55 g; rebanada ≈ 40 g;
  fruta mediana ≈ 150 g.
- Cada opción/plato cumple los macros de su slot con ±5%.
- Respeta alergias, aversiones, preferencias y horarios de la anamnesis.
- Lenguaje de preparación directo, 2–3 pasos máximo por opción."""


def system_prompt_full() -> str:
    """System prompt para la llamada ① (núcleo): base + metodología completa."""
    return "\n\n".join([SYSTEM_BASE, METHODOLOGY_NUTRITION, METHODOLOGY_TRAINING])


def system_prompt_meals() -> str:
    """System prompt para la llamada ② (comidas): base + reglas de comida."""
    return "\n\n".join([SYSTEM_BASE, METHODOLOGY_NUTRITION_BRIEF])


def system_prompt_education() -> str:
    """System prompt para la llamada ③ (educativo)."""
    return (
        SYSTEM_BASE
        + "\n\nGeneras contenido educativo claro y basado en evidencia, sin citas "
        "académicas pero sin afirmaciones pseudocientíficas. Tono profesional y cercano."
    )


SYSTEM_PHOTO_ANALYSIS = (
    SYSTEM_BASE
    + "\n\nAnalizas fotografías de progreso físico con lenguaje PRUDENTE y accesible. "
    "Describe cambios visibles por zona corporal y su coherencia con el peso y perímetros "
    "aportados. NUNCA inventes porcentajes de grasa corporal ni hagas promesas. El texto "
    "será revisado y editado por el coach antes de enviarse al cliente. Responde en JSON "
    'con la forma {"analysis": "texto en español, 4–8 frases"}.'
)


===== FILE: backend/app/services/audit.py =====

"""Registro de auditoría (audit_log) — toda acción relevante deja traza."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AuditLog


def log_event(
    db: Session,
    entity: str,
    entity_id: int | None,
    event: str,
    detail: dict | None = None,
) -> None:
    """Añade la entrada al UoW actual; el commit lo hace el caller."""
    db.add(AuditLog(entity=entity, entity_id=entity_id, event=event, detail_json=detail))


===== FILE: backend/app/services/consent_pdf.py =====

"""PDF de consentimiento informado RGPD (G.3) — generado y archivado en alta."""

from __future__ import annotations

from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.services.storage import client_dir, storage_root

CONSENT_TEXT = (
    "De conformidad con el Reglamento (UE) 2016/679 (RGPD) y la LOPDGDD 3/2018, "
    "el cliente abajo identificado CONSIENTE de forma explícita el tratamiento de "
    "sus datos personales, incluidos datos de salud (categoría especial del art. 9 "
    "RGPD: peso, medidas corporales, fotografías de progreso, lesiones, patologías "
    "y medicación), con la única finalidad de elaborar y hacer seguimiento de su "
    "planificación personalizada de nutrición y entrenamiento. "
    "Los datos se conservarán mientras dure la relación de asesoría. El cliente "
    "puede ejercer en cualquier momento sus derechos de acceso, rectificación, "
    "supresión, portabilidad, limitación y oposición dirigiéndose al responsable. "
    "Las fotografías de progreso nunca serán públicas ni se cederán a terceros."
)


def generate_consent_pdf(
    client_id: int, client_name: str, client_email: str, brand_name: str, signed_at: datetime
) -> str:
    """Crea el PDF en documents/ y devuelve su ruta relativa al storage."""
    dest = client_dir(client_id, "documents") / "consentimiento_rgpd.pdf"
    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Title"], fontSize=16, spaceAfter=6)
    body = ParagraphStyle("b", parent=styles["BodyText"], fontSize=10.5, leading=15)
    meta = ParagraphStyle("m", parent=styles["BodyText"], fontSize=10, leading=14)

    doc = SimpleDocTemplate(
        str(dest), pagesize=A4,
        leftMargin=22 * mm, rightMargin=22 * mm, topMargin=24 * mm, bottomMargin=20 * mm,
        title="Consentimiento informado RGPD", author=brand_name,
    )
    stamp = signed_at.strftime("%d/%m/%Y %H:%M UTC")
    doc.build([
        Paragraph("Consentimiento informado — protección de datos", title),
        Paragraph(brand_name, styles["Heading3"]),
        Spacer(1, 8),
        Paragraph(f"<b>Cliente:</b> {client_name} &nbsp;&nbsp; <b>Email:</b> {client_email}", meta),
        Paragraph(f"<b>Fecha y hora de aceptación:</b> {stamp}", meta),
        Spacer(1, 12),
        Paragraph(CONSENT_TEXT, body),
        Spacer(1, 14),
        Paragraph(
            "Aceptación registrada electrónicamente mediante casilla de verificación "
            "obligatoria en el formulario de anamnesis del portal del cliente "
            f"(identificador interno de cliente: {client_id}).",
            meta,
        ),
    ])
    return str(dest.relative_to(storage_root()))


===== FILE: backend/app/services/docs/__init__.py =====



===== FILE: backend/app/services/docs/charts.py =====

"""Generación de gráficas matplotlib con colores de marca (H.4).

Cada función devuelve PNG en bytes (BytesIO), listo para incrustar en el
documento Word. Usa el backend 'Agg' (sin display) y un estilo limpio acorde
al tema claro de los documentos. El color de acento es el de la marca.

Los datos vienen ya calculados por services/metrics.py (la IA nunca calcula):
estas funciones solo dibujan.
"""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

# Estilo base para documentos (tema claro, premium)
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "font.size": 11,
    "axes.edgecolor": "#D8D8DE",
    "axes.linewidth": 0.8,
    "axes.grid": True,
    "grid.color": "#EEEEF2",
    "grid.linewidth": 0.8,
    "axes.axisbelow": True,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": "#6B6B76",
    "ytick.color": "#6B6B76",
    "text.color": "#1A1A24",
    "axes.labelcolor": "#1A1A24",
})


def _fig_to_png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def weight_trend_chart(
    points: list[tuple[str, float]], goal_kg: float | None, accent: str
) -> bytes:
    """Peso a lo largo del período con línea de tendencia y objetivo."""
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    labels = [p[0] for p in points]
    values = [p[1] for p in points]
    xs = list(range(len(values)))

    ax.plot(xs, values, color=accent, linewidth=2.4, marker="o",
            markersize=5, markerfacecolor="white", markeredgecolor=accent,
            markeredgewidth=1.8, zorder=3, label="Peso")

    # Tendencia (regresión lineal simple) si hay ≥2 puntos
    if len(values) >= 2:
        n = len(values)
        mx = sum(xs) / n
        my = sum(values) / n
        denom = sum((x - mx) ** 2 for x in xs)
        if denom:
            slope = sum((x - mx) * (y - my) for x, y in zip(xs, values)) / denom
            intercept = my - slope * mx
            trend = [slope * x + intercept for x in xs]
            ax.plot(xs, trend, color="#9A9AA6", linewidth=1.4, linestyle="--",
                    zorder=2, label="Tendencia")

    if goal_kg is not None:
        ax.axhline(goal_kg, color=accent, linewidth=1.2, linestyle=":",
                   alpha=0.6, zorder=1)
        ax.text(xs[-1], goal_kg, "  objetivo", va="center", fontsize=9,
                color=accent, alpha=0.8)

    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("kg")
    ax.legend(frameon=False, fontsize=9, loc="best")
    return _fig_to_png(fig)


def adherence_chart(diet_pct: float, training_pct: float, accent: str) -> bytes:
    """Barras horizontales de adherencia a dieta y entrenamiento (0–100%)."""
    fig, ax = plt.subplots(figsize=(6.4, 2.0))
    cats = ["Entrenamiento", "Dieta"]
    vals = [training_pct, diet_pct]
    bars = ax.barh(cats, vals, color=[accent, "#8B9DF7"], height=0.55, zorder=3)
    ax.set_xlim(0, 100)
    ax.set_xlabel("% de adherencia")
    for bar, v in zip(bars, vals):
        ax.text(min(v + 2, 96), bar.get_y() + bar.get_height() / 2,
                f"{v:.0f}%", va="center", fontsize=10, fontweight="bold",
                color="#1A1A24")
    ax.grid(axis="y", visible=False)
    return _fig_to_png(fig)


def e1rm_chart(exercises: list[dict], accent: str) -> bytes:
    """Barras de e1RM por ejercicio (3–5 principales) con valor encima.

    `exercises`: [{name, e1rm_kg, delta_kg}] ya ordenados.
    """
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    names = [e["name"] for e in exercises]
    vals = [e["e1rm_kg"] for e in exercises]
    bars = ax.bar(names, vals, color=accent, width=0.6, zorder=3)
    ax.set_ylabel("e1RM (kg)")
    for bar, e in zip(bars, exercises):
        label = f"{e['e1rm_kg']:.0f}"
        if e.get("delta_kg"):
            sign = "+" if e["delta_kg"] > 0 else ""
            label += f"\n{sign}{e['delta_kg']:.1f}"
        ax.text(bar.get_x() + bar.get_width() / 2, e["e1rm_kg"],
                label, ha="center", va="bottom", fontsize=9,
                color="#1A1A24", fontweight="bold")
    ax.margins(y=0.18)
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right", fontsize=9)
    return _fig_to_png(fig)


def perimeters_chart(
    perimeters: dict[str, list[tuple[str, float]]], accent: str
) -> bytes:
    """Evolución de perímetros (cintura, cadera…) a lo largo de los cierres."""
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    palette = [accent, "#8B9DF7", "#F7C96E", "#C99EF7"]
    for i, (name, series) in enumerate(perimeters.items()):
        xs = list(range(len(series)))
        ys = [v for _, v in series]
        ax.plot(xs, ys, marker="o", markersize=4, linewidth=2,
                color=palette[i % len(palette)], label=name, zorder=3)
    ax.set_ylabel("cm")
    if perimeters:
        any_series = next(iter(perimeters.values()))
        ax.set_xticks(list(range(len(any_series))))
        ax.set_xticklabels([lbl for lbl, _ in any_series], fontsize=9)
    ax.legend(frameon=False, fontsize=9, ncol=2, loc="best")
    return _fig_to_png(fig)


def volume_by_group_chart(volume: dict[str, float], accent: str) -> bytes:
    """Barras horizontales de series semanales por grupo muscular."""
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    items = sorted(volume.items(), key=lambda x: x[1])
    names = [k for k, _ in items]
    vals = [v for _, v in items]
    ax.barh(names, vals, color=accent, height=0.6, zorder=3)
    ax.set_xlabel("series / semana")
    ax.axvline(25, color="#F77E7E", linewidth=1.2, linestyle="--", alpha=0.7)
    ax.text(25, -0.6, "máx 25", color="#F77E7E", fontsize=8, ha="center")
    return _fig_to_png(fig)


===== FILE: backend/app/services/docs/feedback_doc.py =====

"""Documento de feedback quincenal/mensual con gráficas (H.4).

Estructura: resumen del período en datos (peso+tendencia, adherencia,
perímetros, volumen) → progresión de fuerza (e1RM) → composición física (fotos
lado a lado + análisis IA) → análisis en lenguaje natural → "qué ha cambiado y
por qué" (máx 5 bullets) → respuesta a dudas + objetivos + cierre.

Las gráficas (services/docs/charts) usan datos ya calculados por
services/metrics. Las imágenes se incrustan desde BytesIO.
"""

from __future__ import annotations

import io
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

from app.services.docs import charts
from app.services.docs.word_base import (
    DocBrand,
    add_bullets,
    add_cards_row,
    add_cover,
    add_section_heading,
    clean_table,
    init_document,
)


def _add_chart(doc: Document, png: bytes, width_in: float = 6.0) -> None:
    doc.add_picture(io.BytesIO(png), width=Inches(width_in))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


def generate_feedback_doc(
    *,
    brand: DocBrand,
    client_name: str,
    period_index: int,
    metrics: dict,
    weight_points: list[tuple[str, float]],
    goal_kg: float | None,
    e1rm_exercises: list[dict],
    perimeters: dict[str, list[tuple[str, float]]] | None,
    volume_by_group: dict[str, float] | None,
    photo_pairs: list[tuple[str, str]] | None,
    ai_photo_analysis: str | None,
    natural_analysis: str,
    changes_bullets: list[str],
    answers: str | None,
    next_objectives: list[str],
    closing_message: str,
    plan_adjustments: list[dict] | None = None,
) -> bytes:
    doc = init_document(brand)
    accent = brand.color_primary

    add_cover(doc, brand, client_name,
              subtitle=f"Informe de progreso · Período {period_index}",
              goal="Tu evolución en datos")

    # 1) Resumen del período en datos
    add_section_heading(doc, brand, "Tu período en datos")
    adh = metrics.get("adherence", {})
    weight = metrics.get("weight", {})
    add_cards_row(doc, brand, [
        ("Cambio de peso", _fmt_delta(weight.get("delta_kg"), "kg")),
        ("Adherencia dieta", f"{round(adh.get('diet_adherence_ratio', 0) * 100)}%"),
        ("Días registrados", f"{adh.get('days_logged', 0)}/{adh.get('period_days', 0)}"),
    ])
    doc.add_paragraph()

    if weight_points:
        doc.add_heading("Evolución de peso", level=2)
        _add_chart(doc, charts.weight_trend_chart(weight_points, goal_kg, accent))

    doc.add_heading("Adherencia", level=2)
    diet_pct = adh.get("diet_adherence_ratio", 0) * 100
    train_pct = min(100, adh.get("log_ratio", 0) * 100)
    _add_chart(doc, charts.adherence_chart(diet_pct, train_pct, accent), width_in=5.5)

    if perimeters:
        doc.add_heading("Perímetros", level=2)
        _add_chart(doc, charts.perimeters_chart(perimeters, accent))

    if volume_by_group:
        doc.add_heading("Volumen por grupo muscular", level=2)
        _add_chart(doc, charts.volume_by_group_chart(volume_by_group, accent))

    # 2) Progresión de fuerza
    if e1rm_exercises:
        doc.add_page_break()
        add_section_heading(doc, brand, "Progresión de fuerza")
        doc.add_paragraph(
            "Fuerza estimada (1RM por Epley) de tus ejercicios principales."
        )
        _add_chart(doc, charts.e1rm_chart(e1rm_exercises, accent))

    # 3) Composición física
    if (photo_pairs or ai_photo_analysis):
        doc.add_page_break()
        add_section_heading(doc, brand, "Composición física")
        if photo_pairs:
            for before, after in photo_pairs:
                _add_photo_pair(doc, before, after)
        if ai_photo_analysis:
            doc.add_paragraph(ai_photo_analysis)

    # 4) Análisis en lenguaje natural
    doc.add_page_break()
    add_section_heading(doc, brand, "Cómo ha ido")
    doc.add_paragraph(natural_analysis)

    # 5) Qué ha cambiado y por qué (máx 5 bullets)
    if changes_bullets:
        doc.add_heading("Qué ha cambiado en tu plan y por qué", level=2)
        add_bullets(doc, changes_bullets[:5])

    # 5b) CUADRÍCULA DE CAMBIOS — tabla de ajustes aplicados al plan
    if plan_adjustments:
        doc.add_heading("Cuadrícula de cambios aplicados", level=2)
        rows = [
            [str(a.get("area", "")), str(a.get("change", "")), str(a.get("reason", ""))]
            for a in plan_adjustments
        ]
        clean_table(
            doc, ["Área", "Cambio", "Por qué"], rows, brand,
            header_color=brand.color_primary, header_text_color="FFFFFF",
            col_widths=[1800, 3600, 3626],
        )

    # 6) Dudas + objetivos + cierre
    if answers:
        doc.add_heading("Tus dudas", level=2)
        doc.add_paragraph(answers)

    if next_objectives:
        doc.add_heading("Objetivos para las próximas 2 semanas", level=2)
        add_bullets(doc, next_objectives)

    p = doc.add_paragraph()
    p.add_run(closing_message).italic = True

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _add_photo_pair(doc: Document, before_path: str, after_path: str) -> None:
    """Dos fotos lado a lado (antes/después) emparejadas por ángulo."""
    table = doc.add_table(rows=2, cols=2)
    table.autofit = True
    headers = table.rows[0].cells
    for i, label in enumerate(("Período anterior", "Período actual")):
        p = headers[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(label)
        run.font.size = Pt(9)
        run.font.color.rgb = run.font.color.rgb  # mantiene color por defecto
    cells = table.rows[1].cells
    for i, path in enumerate((before_path, after_path)):
        p = cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if path and os.path.exists(path):
            try:
                run = p.add_run()
                run.add_picture(path, width=Inches(2.6))
            except Exception:
                p.add_run("(imagen no disponible)")
        else:
            p.add_run("—")


def _fmt_delta(value: float | None, unit: str) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value} {unit}"


===== FILE: backend/app/services/docs/pdf_convert.py =====

"""Conversión determinista de .docx → PDF con LibreOffice headless.

Los planes se generan con python-docx y se entregan como PDF convertido EN EL
SERVIDOR con LibreOffice, no como .docx. Así el documento que recibe el coach/
cliente es exactamente el que se verifica (mismo motor de render), sin depender
de la versión de Word de cada cual ni de sus sustituciones de fuente/layout.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile


def _soffice_bin() -> str:
    for name in ("soffice", "libreoffice"):
        path = shutil.which(name)
        if path:
            return path
    return "/usr/bin/soffice"


def docx_bytes_to_pdf(docx_bytes: bytes, timeout: int = 120) -> bytes:
    """Convierte un .docx (bytes) a PDF (bytes). Lanza RuntimeError si falla."""
    with tempfile.TemporaryDirectory() as tmp:
        docx_path = os.path.join(tmp, "plan.docx")
        with open(docx_path, "wb") as fh:
            fh.write(docx_bytes)
        # Perfil de usuario propio por conversión → evita bloqueos con concurrencia.
        profile = "file://" + os.path.join(tmp, "lo_profile")
        env = dict(os.environ, HOME=tmp)
        try:
            proc = subprocess.run(
                [_soffice_bin(), "--headless", "--norestore", "--nologo", "--nofirststartwizard",
                 f"-env:UserInstallation={profile}", "--convert-to", "pdf:writer_pdf_Export",
                 "--outdir", tmp, docx_path],
                check=True, capture_output=True, timeout=timeout, env=env,
            )
        except subprocess.CalledProcessError as exc:  # pragma: no cover
            raise RuntimeError(
                f"LibreOffice falló al convertir a PDF: {exc.stderr.decode('utf-8', 'ignore')[:400]}"
            ) from exc
        except FileNotFoundError as exc:  # soffice no instalado
            raise RuntimeError("LibreOffice (soffice) no está disponible en el servidor") from exc
        pdf_path = os.path.join(tmp, "plan.pdf")
        if not os.path.exists(pdf_path):
            raise RuntimeError(
                f"LibreOffice no produjo PDF. stdout={proc.stdout.decode('utf-8', 'ignore')[:300]}"
            )
        with open(pdf_path, "rb") as fh:
            return fh.read()


===== FILE: backend/app/services/docs/plan_doc.py =====

"""Documento Word del plan — diseño de marca DQ (réplica del ejemplo del coach).

Un único documento con la estética del plan oficial: portada con logo, banda de
comida en la cabecera, barras de sección de color, tablas con cabecera de color,
cajas crema. Incluye NUTRICIÓN (objetivos, resumen energético, estructura diaria,
alimentos por grupos, plato saludable, comidas, dieta semanal, ideas, recomenda-
ciones, suplementación) y, a continuación, ENTRENAMIENTO en el mismo estilo.

El contenido cambia según el cliente (datos ya calculados); el diseño es fijo.
Secciones genéricas (alimentos por grupos, plato, ideas, recomendaciones) son
plantilla, filtrando alimentos por alergias/aversiones.
"""

from __future__ import annotations

import io
import os
import unicodedata
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

from app.services.docs.word_base import (
    DocBrand,
    branded_cover,
    clean_table,
    float_image_right,
    info_box,
    init_document,
    open_box,
    section_bar,
    setup_branded_pages,
    _hex,
)

ASSETS = Path(__file__).resolve().parent.parent.parent / "assets" / "plan"

# Paleta EXACTA extraída del PDF de ejemplo del coach
WINE = "8B1A2B"
BLUE = "4A7BA8"
GOLD = "C9A961"   # barra de "Estructura diaria"
CREAM = "F5F0E8"  # relleno de cajas y zebra de tablas
# Colores de las 4 columnas de "Alimentos por grupos" (verbatim del ejemplo)
FG_GREEN = "2E7D32"
FG_YELLOW = "F1C232"
FG_WINE = "8B1A2B"
FG_ORANGE = "E69138"

DAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

# --- Contenido de plantilla (genérico, VERBATIM del ejemplo del coach) ---
# Estructurado como [(etiqueta, [alimentos…])] para poder filtrar alergias/
# aversiones SIN romper etiquetas ni alimentos contiguos.
FOOD_GROUPS = {
    "VEGETALES": [
        ("", ["Acelga", "ajo", "alcachofas", "apio", "berenjena", "brócoli", "calabacín",
              "pepino", "pimiento", "puerro", "rábano", "remolacha", "zanahoria", "coliflor",
              "endivia", "escarola", "espárragos", "espinacas", "judías verdes", "calabaza",
              "nabo", "cebolla", "col lombarda", "coles de Bruselas"]),
    ],
    "CARBOHIDRATOS": [
        ("Féculas y tubérculos", ["patata", "boniato", "yuca"]),
        ("Pseudocereales", ["amaranto", "quinoa", "trigo sarraceno"]),
        ("Cereales", ["cebada", "maíz", "arroz integral", "kamut", "centeno", "sorgo",
                      "teff", "mijo", "avena", "bulgur", "espelta"]),
    ],
    "PROTEÍNAS": [
        ("Proteína animal", ["carne", "pescado", "huevo"]),
        ("Legumbres y derivados", ["cacahuete", "azukis", "edamame", "garbanzos", "habas",
                                   "lentejas", "guisantes", "soja", "tempeh", "tofu",
                                   "seitán", "heura"]),
        ("Lácteos", ["leche", "cuajada", "kéfir", "yogurt"]),
    ],
    "LÍPIDOS": [
        ("", ["Aguacate", "aceite de oliva", "aceitunas"]),
        ("Frutos secos", ["almendras", "anacardos", "nueces", "avellanas", "castañas",
                          "pistachos", "cacahuete*"]),
        ("Semillas", ["chía", "calabaza", "lino", "girasol", "sésamo"]),
    ],
}
FOOD_GROUP_FOOTNOTE = {"LÍPIDOS": "*El cacahuete es una legumbre."}
FOOD_GROUP_COLORS = [FG_GREEN, FG_YELLOW, FG_WINE, FG_ORANGE]

PLATO_TEXT = [
    "El plato saludable es una herramienta muy útil para crear platos equilibrados de forma "
    "rápida y sencilla. Para que tus platos sean equilibrados debes añadir siempre:",
    "• Vegetales y frutas: la mayor parte del plato (la mitad) debe estar cubierta de "
    "vegetales — ¡cuanta más variedad, mejor! La fruta de postre es siempre una buena opción.",
    "• Granos integrales (hidratos de carbono): un cuarto del plato debe estar compuesto por "
    "granos integrales, féculas y tubérculos.",
    "• Proteína: otro cuarto del plato debe estar compuesto por alimentos ricos en proteína "
    "animal y/o vegetal. Es importante limitar el consumo de carne roja y procesada.",
    "Bebida: el agua es la bebida por excelencia. Acompaña el plato con grasas saludables "
    "como aceite de oliva virgen extra, aguacate o frutos secos.",
]

IDEAS_RAPIDAS = [
    "Pan integral con queso cottage y aguacate.",
    "Pan integral con queso cottage y pavo, jamón o huevo.",
    "Pan integral con crema de cacahuete, rodajas de plátano, canela y semillas de sésamo.",
    "Pan integral con aguacate y jamón o huevo.",
    "Pan integral con hummus y rodajas de tomate.",
    "Pan integral con queso fresco y huevo.",
    "Pan integral con aguacate y plátano.",
    "Yogur con copos de avena (o cornflakes sin azúcar) y fruta o frutos secos.",
    "Tortitas de arroz con crema de cacahuete 100% y rodajas de plátano.",
    "Bowl de queso fresco batido 0% con frutos rojos y canela.",
]

SALSAS_TEXT = [
    "Tomate triturado natural (sin azúcar añadido), mostaza Dijon, vinagre balsámico/de "
    "manzana/de Módena, salsa de soja baja en sodio, salsa tamari, salsa Sriracha (con "
    "moderación), salsa de yogur natural con limón y especias, salsa romesco casera, pesto "
    "casero (con moderación por las grasas), guacamole casero, hummus, salsa tahini, mayonesa "
    "light o de aguacate (con moderación), mojo verde/rojo, chimichurri, tzatziki.",
]

YOGURES_TEXT = [
    ("Mejor opción", "yogur natural sin azúcar, yogur griego natural, yogur skyr (alto en "
     "proteína), yogur proteico tipo Hacendado/Pascual sin azúcar, kéfir natural."),
    ("Evitar", "yogures de sabores, edulcorados con azúcar añadido, con frutas en almíbar o "
     "con cereales tipo «de postre»."),
]

QUESOS_TEXT = [
    ("Diarios", "queso fresco batido 0%, queso cottage, requesón, queso de Burgos light, "
     "queso fresco bajo en grasa, queso havarti light, queso de untar 0%."),
    ("Ocasionales (1-2 veces/semana)", "mozzarella de búfala, queso feta, queso de cabra "
     "fresco, parmesano rallado (en pequeñas cantidades para dar sabor)."),
    ("Evitar/limitar", "quesos curados muy grasos, quesos azules, quesos cremosos tipo "
     "brie/camembert en grandes cantidades."),
]

RECOMENDACIONES = [
    ("Agua", "2-3 L al día."),
    ("Días de descanso", "realizar cardio y tomar batido post entreno (opciones del post entreno)."),
    ("Cocciones recomendadas", "vapor, plancha, horno, freidora de aire. Aceite de oliva virgen extra siempre."),
    ("Saciedad extra", "proteína de soja aislada o caseína; espesantes como goma guar, arábiga o xantana."),
    ("Ansiedad", "gelatinas 0%, infusiones o aumentar ración de verdura."),
    ("Frutos secos", "sin sal, ni fritos ni tostados. Sus cremas 100% son válidas."),
]

SUPLEMENTACION_DEFAULT = [
    "Multivitamínico",
    "Omega 3",
    "Creatina monohidrato Creapure (incluida en intra y post entreno)",
    "Vitamina C 1000 mg después de entrenar",
    "Bisglicinato de magnesio 400 mg después de entrenar",
]


def _goal_label(goal: str | None) -> str:
    return {"fat_loss": "Pérdida de grasa", "muscle_gain": "Ganancia muscular",
            "recomp": "Recomposición"}.get(goal or "", "Plan personalizado")


def _objetivo_pairs(goal: str | None) -> list[tuple[str, str]]:
    """OBJETIVOS como el ejemplo: dos líneas con etiqueta en negrita vino
    ("Antropométrico: …" / "Nutricional: …")."""
    anthro = {
        "fat_loss": "Déficit.",
        "muscle_gain": "Superávit.",
        "recomp": "Mantenimiento / recomposición.",
    }.get(goal or "", "Según objetivo.")
    nutri = {
        "fat_loss": "organizar y planificar la alimentación diaria, manteniendo proteína "
                    "para preservar masa muscular.",
        "muscle_gain": "organizar y planificar la alimentación diaria, aportando energía y "
                       "proteína suficientes para ganar masa muscular.",
        "recomp": "organizar y planificar la alimentación diaria, con proteína alta para "
                  "perder grasa y ganar o mantener músculo.",
    }.get(goal or "", "organizar y planificar la alimentación diaria según tu objetivo.")
    return [("Antropométrico", anthro), ("Nutricional", nutri)]


def _title(doc: Document, text: str, sub: str | None = None) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    r = p.add_run(text)
    r.font.size = Pt(24)
    r.font.bold = True
    r.font.color.rgb = _hex(WINE)
    if sub:
        ps = doc.add_paragraph()
        ps.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rs = ps.add_run(sub)
        rs.font.size = Pt(16)
        rs.font.bold = True
        rs.font.color.rgb = _hex("#1A1A1A")


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def _food_blocked(food: str, blocked: set[str]) -> bool:
    """¿Este alimento concreto choca con una alergia/aversión? Compara por
    palabra normalizada (sin tildes/may.), no por substring frágil."""
    nf = _norm(food).rstrip("*")
    return any(b and (b == nf or b in nf.split() or nf in b) for b in blocked)


def _food_group_text(column: str, blocked: set[str]) -> str:
    """Construye el texto de una columna de 'Alimentos por grupos' a partir de la
    estructura [(etiqueta, [alimentos])], quitando SOLO los alimentos bloqueados
    y conservando etiquetas y alimentos contiguos (arregla el bug del filtro)."""
    chunks: list[str] = []
    for label, foods in FOOD_GROUPS[column]:
        kept = [f for f in foods if not _food_blocked(f, blocked)]
        if not kept:
            continue
        body = ", ".join(kept)
        chunks.append(f"{label}: {body}" if label else body)
    text = ". ".join(chunks)
    if text and not text.endswith("."):
        text += "."
    foot = FOOD_GROUP_FOOTNOTE.get(column)
    if foot:
        text = f"{text} {foot}"
    return text or "—"


def _ajuste_text(nutrition: dict, goal: str | None) -> str:
    """Celda 'Ajuste aplicado': el ajuste real sobre el TDEE estimado."""
    tdee = nutrition.get("tdee_kcal") or 0
    target = nutrition.get("target_kcal") or 0
    delta = round(target - tdee)
    if not tdee:
        return _goal_label(goal)
    pct = round(abs(delta) / tdee * 100)
    if goal == "muscle_gain" or delta > 0:
        return f"Superávit +{delta} kcal ({pct}%)"
    if goal == "recomp" or delta == 0:
        return "Mantenimiento ±0 kcal"
    return f"Déficit {delta} kcal ({pct}%)"


def _concise_notas(nutrition: dict, goal: str | None, meals: list[dict]) -> list[str]:
    """NOTAS DEL AJUSTE concisas y computadas (como el ejemplo), NO el rationale
    verboso de la IA."""
    tdee = round(nutrition.get("tdee_kcal") or 0)
    target = round(nutrition.get("target_kcal") or 0)
    out: list = []
    if tdee and target:
        delta = target - tdee
        word = ("Subida progresiva." if (goal == "muscle_gain" or delta > 0)
                else "Mantenimiento." if (goal == "recomp" or delta == 0)
                else "Bajada progresiva.")
        out.append(("Calorías totales",
                    f"{delta:+d} kcal sobre el TDEE estimado (≈ {tdee} → {target} kcal). {word}"))
    if meals:
        toma = ", ".join(f"{m.get('name','')} ({m.get('time','')})".strip()
                         for m in meals if m.get("name"))
        if toma:
            out.append(("Estructura", f"{toma}."))
    return out or [nutrition.get("rationale", "")]


def _ingredients_str(opt: dict) -> str:
    out = []
    for ing in opt.get("ingredients", []):
        g = ing.get("grams")
        out.append(f"{ing.get('food','')} {round(g)} g" if g else ing.get("food", ""))
    return ", ".join(out)


def generate_plan_doc(
    *, brand: DocBrand, client_name: str, month_index: int, goal_type: str | None,
    diet_mode: str | None, nutrition: dict, training: dict, education: dict,
    exercise_names: dict | None = None,
    food_allergies: list[str] | None = None, food_dislikes: list[str] | None = None,
    include_training: bool = False,
) -> bytes:
    # El PLAN es SOLO DIETA: el entrenamiento vive en el tracker del portal.
    # include_training queda como opción por si alguna vez se quiere el doc completo.
    exercise_names = exercise_names or {}
    blocked = {_norm(x) for x in (food_allergies or []) + (food_dislikes or []) if x}

    doc = init_document(brand)
    # El ejemplo usa Calibri (en el contenedor se sustituye por Carlito, idéntico).
    for _sname in ("Normal", "Heading 1", "Heading 2", "Heading 3"):
        try:
            doc.styles[_sname].font.name = "Calibri"
        except Exception:
            pass
    setup_branded_pages(doc, banner_path=str(ASSETS / "header_banner.png"),
                        footer_text="David Quiceno · Dietista & Entrenador Personal")
    branded_cover(doc, str(ASSETS / "cover.png"))

    # ======================= NUTRICIÓN =======================
    _title(doc, "PLAN NUTRICIONAL", client_name)
    macros = nutrition.get("macros", {})

    section_bar(doc, "Objetivos", WINE)
    info_box(doc, _objetivo_pairs(goal_type), fill=CREAM, label_color=WINE)

    section_bar(doc, "Resumen energético diario", BLUE)
    clean_table(
        doc, ["Calorías", "Reparto de macros", "Ajuste aplicado"],
        [[f"≈ {round(nutrition.get('target_kcal', 0))} kcal",
          f"CH {round(macros.get('carbs_g', 0))} g · P {round(macros.get('protein_g', 0))} g · "
          f"G {round(macros.get('fat_g', 0))} g",
          _ajuste_text(nutrition, goal_type)]],
        brand, header_color=WINE, header_text_color="FFFFFF",
        col_widths=[2400, 4226, 2400],
    )

    meals = nutrition.get("meals", [])
    section_bar(doc, "Notas del ajuste", BLUE)
    info_box(doc, _concise_notas(nutrition, goal_type, meals))

    if meals:
        section_bar(doc, "Estructura diaria", GOLD)
        rows = [[m.get("time", ""), m.get("name", f"Comida {m.get('slot')}"),
                 _estrategia(m.get("name", ""))] for m in meals]
        clean_table(doc, ["Hora", "Toma", "Estrategia"], rows, brand,
                    header_color=WINE, header_text_color="FFFFFF",
                    col_widths=[1500, 3000, 4526])

    # Alimentos por grupos (plantilla, filtrada con precisión por alergias)
    section_bar(doc, "Alimentos por grupos", WINE)
    names = list(FOOD_GROUPS.keys())
    clean_table(
        doc, names, [[_food_group_text(n, blocked) for n in names]],
        brand, header_colors=FOOD_GROUP_COLORS, header_text_color="FFFFFF",
    )

    # El plato saludable (plantilla + foto)
    section_bar(doc, "El plato saludable", BLUE)
    info_box(doc, PLATO_TEXT, fill=CREAM, label_color=WINE)
    plate = ASSETS / "plate.png"
    if plate.exists():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        try:
            p.add_run().add_picture(str(plate), width=Inches(2.6))
        except Exception:
            pass

    # Comidas detalladas (flexible) — como el ejemplo: comida/cena con sistema de
    # equivalencias por grupos; el resto, 3 opciones numeradas en prosa (sin kcal).
    # Comidas detalladas: cada comida = barra + CAJA CREMA con el contenido dentro
    # (como el ejemplo). Comida/cena en equivalencias; resto, 3 opciones numeradas.
    bank = nutrition.get("meal_bank") or {}
    if diet_mode != "strict" and meals:
        blocks = {s.get("slot"): s for s in bank.get("slots", [])}
        for m in meals:
            section_bar(doc, f"{m.get('name','Comida')} · {m.get('time','')}", WINE, size=10)
            sb = blocks.get(m.get("slot"), {})
            cell = open_box(doc, CREAM)
            if sb.get("fmt") == "equivalences" and sb.get("equivalences"):
                # foto redonda flotante en la cena (como el ejemplo del coach)
                img = str(ASSETS / "food_round.png") if "cena" in _norm(m.get("name", "")) else None
                _render_equivalences(cell, sb["equivalences"], image_path=img)
            else:
                first = True
                for n, opt in enumerate(sb.get("options", [])[:3], start=1):
                    p = cell.paragraphs[0] if first else cell.add_paragraph()
                    first = False
                    p.paragraph_format.space_after = Pt(4)
                    rl = p.add_run(f"Opción {n}. ")
                    rl.font.bold = True
                    rl.font.color.rgb = _hex(WINE)
                    p.add_run(f"{opt.get('title','')} — {_ingredients_str(opt)}.")

    # Ejemplo de dieta semanal
    _weekly_section(doc, brand, diet_mode, nutrition, bank)

    # Ideas rápidas
    section_bar(doc, "Ideas rápidas de desayunos, snacks y meriendas", WINE)
    info_box(doc, [f"• {x}" for x in IDEAS_RAPIDAS], fill=CREAM)

    # Salsas recomendables
    section_bar(doc, "Salsas recomendables", BLUE)
    info_box(doc, SALSAS_TEXT, fill=CREAM)

    # Yogures recomendables
    section_bar(doc, "Yogures recomendables", BLUE)
    info_box(doc, YOGURES_TEXT, fill=CREAM)

    # Quesos recomendables
    section_bar(doc, "Quesos recomendables", BLUE)
    info_box(doc, QUESOS_TEXT, fill=CREAM)

    # Recomendaciones generales
    section_bar(doc, "Recomendaciones generales", WINE)
    info_box(doc, RECOMENDACIONES, fill=CREAM)

    # Suplementación
    section_bar(doc, "Suplementación recomendada", BLUE)
    supps = nutrition.get("supplements", [])
    if supps:
        items = [f"{s.get('name','')} — {s.get('dose','')} ({s.get('timing','')})" for s in supps]
    else:
        items = SUPLEMENTACION_DEFAULT
    info_box(doc, items, fill=CREAM)

    if not include_training or not training:
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    # ======================= ENTRENAMIENTO =======================
    doc.add_page_break()
    _title(doc, "PLAN DE ENTRENAMIENTO", client_name)

    section_bar(doc, f"Estructura · {training.get('split_name','')}", BLUE)
    info_box(doc, [
        (f"{len(training.get('sessions', []))} días/semana", training.get("split_rationale", "")),
    ])

    prog = training.get("weekly_progression", [])
    if prog:
        section_bar(doc, "Progresión semanal", WINE)
        rows = [[f"Sem {w.get('week')}", w.get("intent", ""), f"{w.get('load_pct','')}%",
                 f"RIR {w.get('rir_target','')}", w.get("volume_note", "")] for w in prog]
        clean_table(doc, ["Semana", "Enfoque", "Carga", "RIR", "Notas"], rows, brand,
                    header_color=WINE, header_text_color="FFFFFF",
                    col_widths=[1100, 1800, 1100, 1100, 3926])

    for sess in training.get("sessions", []):
        section_bar(doc, f"{sess.get('day','')} · {sess.get('name','')}", WINE, size=10)
        # Calentamiento en caja opaca (legible aunque caiga sobre la banda)
        if sess.get("warmup"):
            info_box(doc, [("Calentamiento", sess["warmup"])])
        rows = []
        for ex in sess.get("exercises", []):
            name = exercise_names.get(ex.get("exercise_id"), f"Ejercicio #{ex.get('exercise_id','')}")
            rows.append([
                name, f"{ex.get('sets','')}×{ex.get('rep_range','')}", f"RIR {ex.get('rir','')}",
                f"{ex.get('rest_sec','')}s", ex.get("technique_cue", "") or "",
            ])
        if rows:
            clean_table(doc, ["Ejercicio", "Series", "RIR", "Descanso", "Clave técnica"], rows,
                        brand, header_color=WINE, header_text_color="FFFFFF",
                        col_widths=[2600, 1300, 1100, 1100, 2926])
        if sess.get("cooldown"):
            info_box(doc, [("Vuelta a la calma", sess["cooldown"])])

    cardio = training.get("cardio") or {}
    if cardio.get("daily_steps") or cardio.get("sessions"):
        section_bar(doc, "Cardio y NEAT", BLUE)
        items = [("Pasos diarios objetivo", str(cardio.get("daily_steps", "—")))]
        for cs in cardio.get("sessions", []):
            items.append((cs.get("type", "").upper(),
                          f"{cs.get('minutes','')} min × {cs.get('times_per_week','')}/sem"
                          + (f" — {cs.get('notes')}" if cs.get("notes") else "")))
        info_box(doc, items)

    if training.get("deload_instructions"):
        section_bar(doc, "Semana de descarga (deload)", BLUE)
        info_box(doc, [training["deload_instructions"]])

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _render_equivalences(container, eq: dict, image_path: str | None = None) -> None:
    """Renderiza una comida en formato de equivalencias DENTRO de una caja (cell):
    línea intro + un párrafo por grupo con sus alimentos intercambiables. Si se
    pasa image_path, una foto redonda flota a la derecha con el texto alrededor."""
    intro = (eq.get("intro") or "").strip()
    p = container.paragraphs[0]  # reutiliza el primer párrafo (vacío) de la caja
    p.paragraph_format.space_after = Pt(4)
    if image_path and os.path.exists(image_path):
        try:
            float_image_right(p, image_path, Inches(1.5))
        except Exception:
            pass
    txt = "Elige una opción de cada grupo." + (f" {intro}:" if intro else "")
    r = p.add_run(txt)
    r.font.italic = True
    r.font.size = Pt(9.5)
    r.font.color.rgb = _hex("#5A5A5A")
    for g in eq.get("groups", []):
        p = container.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        rl = p.add_run(f"{g.get('name','')}: ")
        rl.font.bold = True
        rl.font.color.rgb = _hex(WINE)
        note = (g.get("note") or "").strip()
        items = [f"{it.get('food','')} ({it.get('amount','')})"
                 for it in g.get("items", []) if it.get("food")]
        body = note
        if items:
            body = (note + " " if note else "") + " o ".join(items)
        if body and not body.endswith("."):
            body += "."
        p.add_run(body)


def _estrategia(name: str) -> str:
    n = _norm(name)
    if "pre" in n:
        return "Pre-entreno: CH refinados, proteína magra, grasas reducidas."
    if "post" in n:
        return "Post-entreno: recuperación (proteína + CH)."
    if "cena" in n:
        return "Recuperación: integrales, proteína completa, grasas saludables."
    if "desayuno" in n:
        return "Ligero y de fácil digestión."
    if "media" in n or "merienda" in n:
        return "Sustancioso entre comidas principales."
    return "Comida equilibrada."


def _weekly_section(doc: Document, brand: DocBrand, diet_mode: str | None,
                    nutrition: dict, bank: dict) -> None:
    meals = nutrition.get("meals", [])
    if not meals:
        return
    section_bar(doc, "Ejemplo de dieta semanal", WINE)

    headers = ["Toma"] + DAYS
    rows: list[list[str]] = []
    if diet_mode == "strict":
        days = bank.get("days", [])
        by_day = {_norm(d.get("day")): d for d in days}
        order = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
        for m in meals:
            slot = m.get("slot")
            cells = []
            for dslug in order:
                d = by_day.get(dslug)
                title = ""
                if d:
                    for meal in d.get("meals", []):
                        if meal.get("slot") == slot:
                            title = meal.get("dish", {}).get("title", "")
                cells.append(title)
            rows.append([m.get("name", f"Comida {slot}")] + cells)
    else:
        blocks = {s.get("slot"): s for s in bank.get("slots", [])}
        for m in meals:
            sb = blocks.get(m.get("slot"), {})
            wk = [x for x in (sb.get("weekly_examples") or []) if x]
            opts = sb.get("options", [])
            cells = []
            for di in range(7):
                if wk:
                    cells.append(wk[di % len(wk)])
                elif opts:
                    cells.append(opts[di % len(opts)].get("title", ""))
                else:
                    cells.append("")
            rows.append([m.get("name", f"Comida {m.get('slot')}")] + cells)

    if rows:
        clean_table(doc, headers, rows, brand, header_color=WINE, header_text_color="FFFFFF",
                    col_widths=[1500] + [1075] * 7)


===== FILE: backend/app/services/docs/shopping_list.py =====

"""Lista de la compra semanal (modo strict).

Deriva por agregación aritmética la lista de la compra exacta a partir del
menú cerrado de 7 días: suma los gramos de cada ingrediente a lo largo de toda
la semana y los agrupa por categoría. Es aritmética pura (testable) y debe
cuadrar con el menú (test de agregación, PARTE B).

El agrupado por categoría usa un diccionario de palabras clave; lo desconocido
cae en "Otros" para no perder nada.
"""

from __future__ import annotations

from collections import defaultdict

# Categorización por palabras clave (es de cara al cliente, en castellano).
CATEGORIES: dict[str, list[str]] = {
    "Proteínas": [
        "pollo", "pavo", "ternera", "cerdo", "huevo", "atún", "salmón", "merluza",
        "pescado", "gambas", "lomo", "jamón", "queso", "yogur", "skyr", "requesón",
        "tofu", "seitán", "proteína", "clara",
    ],
    "Verduras y hortalizas": [
        "lechuga", "tomate", "cebolla", "pimiento", "calabacín", "berenjena",
        "brócoli", "espinaca", "zanahoria", "pepino", "champiñón", "ajo", "espárrago",
        "judía", "col", "coliflor", "canónigos", "rúcula", "verdura", "ensalada",
    ],
    "Frutas": [
        "manzana", "plátano", "fresa", "naranja", "kiwi", "arándano", "pera", "uva",
        "melón", "sandía", "mango", "piña", "frambuesa", "fruta", "aguacate", "limón",
    ],
    "Hidratos": [
        "arroz", "pasta", "pan", "patata", "avena", "quinoa", "couscous", "legumbre",
        "lenteja", "garbanzo", "tortita", "cereal", "boniato", "harina",
    ],
    "Grasas y otros": [
        "aceite", "oliva", "almendra", "nuez", "cacahuete", "semilla", "mantequilla",
        "chocolate", "coco", "tahini", "crema",
    ],
}


def _categorize(food: str) -> str:
    f = food.lower()
    for cat, keywords in CATEGORIES.items():
        if any(k in f for k in keywords):
            return cat
    return "Otros"


def build_shopping_list(strict_menu: dict) -> dict[str, list[dict]]:
    """Agrega ingredientes de un menú strict (MealsStrictOutput serializado).

    Devuelve {categoría: [{food, grams, mentions}]} ordenado, donde `grams` es
    la suma semanal y `mentions` cuántas veces aparece (para detectar staples).
    """
    totals: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    non_gram: dict[str, int] = defaultdict(int)  # ingredientes "al gusto" sin gramos

    for day in strict_menu.get("days", []):
        for meal in day.get("meals", []):
            dish = meal.get("dish", {})
            for ing in dish.get("ingredients", []):
                food = ing.get("food", "").strip()
                if not food:
                    continue
                grams = ing.get("grams")
                if grams:
                    totals[food] += float(grams)
                    counts[food] += 1
                else:
                    non_gram[food] += 1

    by_cat: dict[str, list[dict]] = defaultdict(list)
    for food, grams in totals.items():
        by_cat[_categorize(food)].append({
            "food": food, "grams": round(grams), "mentions": counts[food],
        })
    for food, n in non_gram.items():
        if food not in totals:
            by_cat[_categorize(food)].append({
                "food": food, "grams": None, "mentions": n,
            })

    # Ordena categorías por el orden canónico y los ítems por gramos desc.
    order = list(CATEGORIES.keys()) + ["Otros"]
    out: dict[str, list[dict]] = {}
    for cat in order:
        if cat in by_cat:
            out[cat] = sorted(by_cat[cat], key=lambda x: (x["grams"] is None, -(x["grams"] or 0)))
    return out


def shopping_list_total_grams(shopping: dict[str, list[dict]]) -> float:
    """Suma total de gramos (para el test de agregación: debe cuadrar con el menú)."""
    return sum(
        item["grams"] for items in shopping.values() for item in items if item["grams"]
    )


===== FILE: backend/app/services/docs/word_base.py =====

"""Helpers de generación Word con python-docx, tema claro con marca (H.3).

Centraliza el estilo (tipografía, colores de marca, espaciados) y las
primitivas de maquetación (portada, cabeceras de sección, cards de resumen,
tablas limpias con ancho explícito). Las reglas de oro de tablas (ancho en DXA,
sin viñetas unicode, padding de celda, sombreado CLEAR) siguen las del skill de
docx, aplicadas al equivalente de python-docx.

Tanto el documento de plan como el de feedback construyen sobre estas piezas
para garantizar un aspecto coherente y profesional.
"""

from __future__ import annotations

from dataclasses import dataclass

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

# Ancho de contenido en EMU/twips para A4 con márgenes de 2 cm
CONTENT_WIDTH_DXA = 9026  # A4 menos márgenes


@dataclass
class DocBrand:
    name: str
    color_primary: str   # "#6EE7B7"
    color_secondary: str
    font_family: str
    tagline: str | None = None
    contact_email: str | None = None
    logo_path: str | None = None  # ruta absoluta a imagen, opcional


def _hex(color: str) -> RGBColor:
    return RGBColor.from_string(color.lstrip("#").upper())


def _shade_cell(cell, hex_color: str) -> None:
    """Sombreado de celda (equivale a ShadingType.CLEAR del skill).

    shd debe ir al inicio de tcPr (antes de tcMar/tcW) según el esquema OOXML.
    """
    tcPr = cell._tc.get_or_add_tcPr()
    # Quita un shd previo si existiera (evita duplicados en zebra+header)
    for old in tcPr.findall(qn("w:shd")):
        tcPr.remove(old)
    shd = tcPr.makeelement(qn("w:shd"), {
        qn("w:val"): "clear", qn("w:color"): "auto",
        qn("w:fill"): hex_color.lstrip("#").upper(),
    })
    # shd va después de tcW/gridSpan si existen, antes de tcMar
    tcW = tcPr.findall(qn("w:tcW"))
    if tcW:
        tcW[-1].addnext(shd)
    else:
        tcPr.insert(0, shd)


def _set_cell_margins(cell, top=60, bottom=60, left=110, right=110) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    m = tcPr.makeelement(qn("w:tcMar"), {})
    # El esquema de tcMar exige el orden: top, left (start), bottom, right (end)
    for side, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        node = m.makeelement(qn(f"w:{side}"), {qn("w:w"): str(val), qn("w:type"): "dxa"})
        m.append(node)
    tcPr.append(m)


def float_image_right(paragraph, image_path: str, width) -> None:
    """Inserta una imagen FLOTANTE a la derecha con el texto fluyendo alrededor
    (como las fotos del ejemplo del coach, superpuestas entre las palabras)."""
    from docx.oxml import OxmlElement

    def _wp(tag):
        return qn("wp:" + tag)

    run = paragraph.add_run()
    run.add_picture(image_path, width=width)  # inline de partida
    drawing = run._r.find(qn("w:drawing"))
    inline = drawing.find(_wp("inline"))
    extent = inline.find(_wp("extent"))
    cx, cy = extent.get("cx"), extent.get("cy")
    docPr = inline.find(_wp("docPr"))
    cNv = inline.find(_wp("cNvGraphicFramePr"))
    graphic = inline.find(qn("a:graphic"))

    anchor = OxmlElement("wp:anchor")
    for k, v in {"distT": "0", "distB": "0", "distL": "114300", "distR": "114300",
                 "simplePos": "0", "relativeHeight": "2", "behindDoc": "0", "locked": "0",
                 "layoutInCell": "1", "allowOverlap": "1"}.items():
        anchor.set(k, v)
    sp = OxmlElement("wp:simplePos"); sp.set("x", "0"); sp.set("y", "0"); anchor.append(sp)
    ph = OxmlElement("wp:positionH"); ph.set("relativeFrom", "column")
    al = OxmlElement("wp:align"); al.text = "right"; ph.append(al); anchor.append(ph)
    pv = OxmlElement("wp:positionV"); pv.set("relativeFrom", "paragraph")
    off = OxmlElement("wp:posOffset"); off.text = "0"; pv.append(off); anchor.append(pv)
    ext = OxmlElement("wp:extent"); ext.set("cx", cx); ext.set("cy", cy); anchor.append(ext)
    ee = OxmlElement("wp:effectExtent")
    for k in ("l", "t", "r", "b"):
        ee.set(k, "0")
    anchor.append(ee)
    wrap = OxmlElement("wp:wrapSquare"); wrap.set("wrapText", "bothSides"); anchor.append(wrap)
    anchor.append(docPr); anchor.append(cNv); anchor.append(graphic)
    drawing.remove(inline)
    drawing.append(anchor)


def _header_bg_image(paragraph, image_path: str, width) -> None:
    """Imagen de cabecera como FONDO flotante (detrás del texto, anclada al borde
    superior de la página), para que el contenido se superponga encima (como el
    ejemplo: título y cajas sobre la banda de comida)."""
    from docx.oxml import OxmlElement

    def _wp(tag):
        return qn("wp:" + tag)

    run = paragraph.add_run()
    run.add_picture(image_path, width=width)
    drawing = run._r.find(qn("w:drawing"))
    inline = drawing.find(_wp("inline"))
    extent = inline.find(_wp("extent"))
    cx, cy = extent.get("cx"), extent.get("cy")
    docPr = inline.find(_wp("docPr"))
    cNv = inline.find(_wp("cNvGraphicFramePr"))
    graphic = inline.find(qn("a:graphic"))

    anchor = OxmlElement("wp:anchor")
    for k, v in {"distT": "0", "distB": "0", "distL": "0", "distR": "0", "simplePos": "0",
                 "relativeHeight": "0", "behindDoc": "1", "locked": "0", "layoutInCell": "1",
                 "allowOverlap": "1"}.items():
        anchor.set(k, v)
    sp = OxmlElement("wp:simplePos"); sp.set("x", "0"); sp.set("y", "0"); anchor.append(sp)
    ph = OxmlElement("wp:positionH"); ph.set("relativeFrom", "page")
    al = OxmlElement("wp:align"); al.text = "center"; ph.append(al); anchor.append(ph)
    pv = OxmlElement("wp:positionV"); pv.set("relativeFrom", "page")
    off = OxmlElement("wp:posOffset"); off.text = "0"; pv.append(off); anchor.append(pv)
    ext = OxmlElement("wp:extent"); ext.set("cx", cx); ext.set("cy", cy); anchor.append(ext)
    ee = OxmlElement("wp:effectExtent")
    for k in ("l", "t", "r", "b"):
        ee.set(k, "0")
    anchor.append(ee)
    anchor.append(OxmlElement("wp:wrapNone"))
    anchor.append(docPr); anchor.append(cNv); anchor.append(graphic)
    drawing.remove(inline); drawing.append(anchor)


def _cant_split_rows(table) -> None:
    """Evita que una fila se parta entre páginas (texto/celdas cortados)."""
    for row in table.rows:
        trPr = row._tr.get_or_add_trPr()
        if trPr.find(qn("w:cantSplit")) is None:
            trPr.append(trPr.makeelement(qn("w:cantSplit"), {}))


def _keep_with_next(paragraph) -> None:
    """La barra/encabezado se queda con el contenido que le sigue (no se orfana)."""
    pPr = paragraph._p.get_or_add_pPr()
    if pPr.find(qn("w:keepNext")) is None:
        pPr.append(pPr.makeelement(qn("w:keepNext"), {}))


def _keep_rows_together(table) -> None:
    """Mantiene TODAS las filas juntas (la tabla no se corta entre páginas)."""
    rows = table.rows
    for row in list(rows)[:-1]:
        for cell in row.cells:
            for p in cell.paragraphs:
                _keep_with_next(p)


def open_box(doc: Document, fill: str = "F5F0E8"):
    """Crea una caja (cell) a todo el ancho con relleno y devuelve la celda para
    rellenarla con párrafos. Sin bordes, no se parte entre páginas."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    cell = table.rows[0].cells[0]
    cell.width = Pt(CONTENT_WIDTH_DXA / 20)
    _shade_cell(cell, fill)
    _set_cell_margins(cell, top=140, bottom=140, left=160, right=160)
    _no_table_borders(table)
    _cant_split_rows(table)
    return cell


def init_document(brand: DocBrand) -> Document:
    """Documento con estilos base de marca (tipografía y headings)."""
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = brand.font_family
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = _hex("#1A1A24")

    for level, size in (("Heading 1", 20), ("Heading 2", 14), ("Heading 3", 11.5)):
        st = doc.styles[level]
        st.font.name = brand.font_family
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = _hex("#1A1A24")

    # Márgenes de 2 cm
    for section in doc.sections:
        section.top_margin = section.bottom_margin = Pt(56)
        section.left_margin = section.right_margin = Pt(56)

    # El zoom por defecto de python-docx (val="bestFit") sin percent falla la
    # validación OOXML estricta; fijamos percent=100.
    zoom = doc.settings.element.find(qn("w:zoom"))
    if zoom is not None:
        zoom.set(qn("w:percent"), "100")
    return doc


def add_cover(doc: Document, brand: DocBrand, client_name: str, subtitle: str,
              goal: str) -> None:
    """Portada: marca, nombre del cliente, mes/objetivo."""
    import os

    from docx.shared import Inches

    if brand.logo_path and os.path.exists(brand.logo_path):
        try:
            doc.add_picture(brand.logo_path, width=Inches(1.4))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        except Exception:
            pass

    for _ in range(3):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(brand.name)
    run.font.size = Pt(15)
    run.font.bold = True
    run.font.color.rgb = _hex(brand.color_primary)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(client_name)
    run.font.size = Pt(30)
    run.font.bold = True

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(subtitle)
    run.font.size = Pt(13)
    run.font.color.rgb = _hex("#6B6B76")

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(goal)
    run.font.size = Pt(12)
    run.font.color.rgb = _hex(brand.color_secondary)

    doc.add_page_break()


def add_section_heading(doc: Document, brand: DocBrand, text: str) -> None:
    """Encabezado de sección con regla inferior de color de marca."""
    h = doc.add_heading(text, level=1)
    # Regla inferior (border en el párrafo, no tabla — regla del skill)
    pPr = h._p.get_or_add_pPr()
    borders = pPr.makeelement(qn("w:pBdr"), {})
    bottom = borders.makeelement(qn("w:bottom"), {
        qn("w:val"): "single", qn("w:sz"): "12",
        qn("w:space"): "4", qn("w:color"): brand.color_primary.lstrip("#").upper(),
    })
    borders.append(bottom)
    pPr.append(borders)


def add_cards_row(doc: Document, brand: DocBrand, cards: list[tuple[str, str]]) -> None:
    """Fila de 'cards' visuales (label, value) para el resumen ejecutivo."""
    n = len(cards)
    table = doc.add_table(rows=1, cols=n)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    col_w = CONTENT_WIDTH_DXA // n
    for i, (label, value) in enumerate(cards):
        cell = table.rows[0].cells[i]
        cell.width = Pt(col_w / 20)
        _shade_cell(cell, "F4F4F7")
        _set_cell_margins(cell, top=120, bottom=120)
        cell.paragraphs[0].text = ""
        pv = cell.paragraphs[0]
        pv.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rv = pv.add_run(value)
        rv.font.size = Pt(17)
        rv.font.bold = True
        rv.font.color.rgb = _hex(brand.color_primary)
        pl = cell.add_paragraph()
        pl.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rl = pl.add_run(label)
        rl.font.size = Pt(8.5)
        rl.font.color.rgb = _hex("#6B6B76")
    _no_table_borders(table)


def clean_table(doc: Document, headers: list[str], rows: list[list[str]],
                brand: DocBrand, col_widths: list[int] | None = None,
                header_color: str | None = None, header_colors: list[str] | None = None,
                header_text_color: str = "0A0A0F"):
    """Tabla limpia con cabecera de color, ancho explícito y padding (skill).

    header_color: color único de la cabecera (por defecto el de marca).
    header_colors: color por columna (p. ej. los 4 grupos de alimentos)."""
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    if col_widths is None:
        col_widths = [CONTENT_WIDTH_DXA // len(headers)] * len(headers)
    base_hdr = (header_color or brand.color_primary)

    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].width = Pt(col_widths[i] / 20)
        _shade_cell(hdr[i], (header_colors[i] if header_colors else base_hdr).lstrip("#"))
        _set_cell_margins(hdr[i])
        p = hdr[i].paragraphs[0]
        run = p.add_run(h)
        run.font.bold = True
        run.font.size = Pt(9.5)
        run.font.color.rgb = _hex(header_text_color)

    for r_idx, row in enumerate(rows):
        cells = table.add_row().cells
        for i, val in enumerate(row):
            cells[i].width = Pt(col_widths[i] / 20)
            _set_cell_margins(cells[i])
            # SIEMPRE relleno opaco (blanco/crema) para que el texto sea legible
            # aunque la fila quede sobre la banda de comida de la cabecera.
            _shade_cell(cells[i], "F5F0E8" if r_idx % 2 == 1 else "FFFFFF")
            p = cells[i].paragraphs[0]
            run = p.add_run(str(val))
            run.font.size = Pt(9.5)
    _thin_borders(table)
    _cant_split_rows(table)
    _keep_rows_together(table)  # la tabla no se parte entre páginas
    return table


def add_bullets(doc: Document, items: list[str]) -> None:
    """Lista con viñetas usando el estilo nativo (nunca viñetas unicode, skill)."""
    for it in items:
        doc.add_paragraph(it, style="List Bullet")


def section_bar(doc: Document, text: str, color: str, text_color: str = "FFFFFF",
                size: float = 11) -> None:
    """Barra de sección a todo el ancho con fondo de color y texto centrado."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    cell = table.rows[0].cells[0]
    cell.width = Pt(CONTENT_WIDTH_DXA / 20)
    _shade_cell(cell, color)
    _set_cell_margins(cell, top=80, bottom=80, left=120, right=120)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text.upper())
    r.font.bold = True
    r.font.size = Pt(size)
    r.font.color.rgb = _hex(text_color)
    _no_table_borders(table)
    _cant_split_rows(table)
    _keep_with_next(p)  # la barra no se queda sola al pie de página


def info_box(doc: Document, items, fill: str = "F5F0E8", label_color: str = "8B1A2B") -> None:
    """Recuadro con fondo crema. items: str (línea) o (label, valor)."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    cell = table.rows[0].cells[0]
    cell.width = Pt(CONTENT_WIDTH_DXA / 20)
    _shade_cell(cell, fill)
    _set_cell_margins(cell, top=140, bottom=140, left=160, right=160)
    first = True
    for item in items:
        p = cell.paragraphs[0] if first else cell.add_paragraph()
        first = False
        p.paragraph_format.space_after = Pt(3)
        if isinstance(item, (tuple, list)):
            label, value = item
            rl = p.add_run(f"{label}: ")
            rl.font.bold = True
            rl.font.color.rgb = _hex(label_color)
            rl.font.size = Pt(10)
            rv = p.add_run(value)
            rv.font.size = Pt(10)
        else:
            r = p.add_run(str(item))
            r.font.size = Pt(10)
    _no_table_borders(table)
    _cant_split_rows(table)


def setup_branded_pages(doc: Document, banner_path: str | None = None,
                        footer_text: str | None = None) -> None:
    """Cabecera con banda de marca (en páginas de contenido, no en portada) + pie."""
    import os

    from docx.shared import Inches

    section = doc.sections[0]
    section.different_first_page_header_footer = True
    if banner_path and os.path.exists(banner_path):
        # Banda de comida TRANSLÚCIDA a sangre completa como FONDO; el título y las
        # cajas se superponen encima y se leen (la banda está atenuada como el
        # ejemplo del coach). El contenido empieza arriba, sobre la banda.
        section.top_margin = Inches(1.45)
        section.header_distance = Inches(0.0)
        hp = section.header.paragraphs[0]
        hp.paragraph_format.space_before = Pt(0)
        hp.paragraph_format.space_after = Pt(0)
        try:
            _header_bg_image(hp, banner_path, Inches(8.8))  # banda full-bleed, detrás
        except Exception:
            pass
    if footer_text:
        from docx.enum.text import WD_TAB_ALIGNMENT
        from docx.oxml import OxmlElement

        fp = section.footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        # tab a la derecha (ancho de contenido) para empujar el nº de página
        fp.paragraph_format.tab_stops.add_tab_stop(
            Pt(CONTENT_WIDTH_DXA / 20), WD_TAB_ALIGNMENT.RIGHT
        )
        r = fp.add_run(footer_text)
        r.font.size = Pt(8)
        r.font.color.rgb = _hex("#9A9AA6")
        fp.add_run("\t")
        # campo PAGE (Word/LibreOffice lo numeran solos)
        pr = fp.add_run()
        pr.font.size = Pt(8)
        pr.font.color.rgb = _hex("#9A9AA6")
        beg = OxmlElement("w:fldChar"); beg.set(qn("w:fldCharType"), "begin")
        ins = OxmlElement("w:instrText"); ins.set(qn("xml:space"), "preserve"); ins.text = "PAGE"
        end = OxmlElement("w:fldChar"); end.set(qn("w:fldCharType"), "end")
        pr._r.append(beg); pr._r.append(ins); pr._r.append(end)


def branded_cover(doc: Document, cover_path: str | None) -> None:
    """Portada con la imagen de marca centrada."""
    import os

    from docx.shared import Inches

    for _ in range(5):
        doc.add_paragraph()
    if cover_path and os.path.exists(cover_path):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        try:
            p.add_run().add_picture(cover_path, width=Inches(4.8))
        except Exception:
            pass
    doc.add_page_break()


def _thin_borders(table) -> None:
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = tblPr.makeelement(qn("w:tblBorders"), {})
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = borders.makeelement(qn(f"w:{edge}"), {
            qn("w:val"): "single", qn("w:sz"): "4",
            qn("w:space"): "0", qn("w:color"): "E0E0E6",
        })
        borders.append(e)
    _insert_tbl_borders(tblPr, borders)


def _no_table_borders(table) -> None:
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = tblPr.makeelement(qn("w:tblBorders"), {})
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = borders.makeelement(qn(f"w:{edge}"), {qn("w:val"): "none"})
        borders.append(e)
    _insert_tbl_borders(tblPr, borders)


def _insert_tbl_borders(tblPr, borders) -> None:
    """Inserta tblBorders en la posición correcta del esquema OOXML.

    El orden en tblPr es estricto: ...tblW, jc, tblCellSpacing, tblInd,
    tblBorders, shd, ... Insertamos tblBorders justo después de tblInd/jc/tblW
    (lo que exista) y antes de cualquier shd.
    """
    after = ("w:tblInd", "w:tblCellSpacing", "w:jc", "w:tblW", "w:tblStyle")
    anchor = None
    for tag in after:
        found = tblPr.findall(qn(tag))
        if found:
            anchor = found[-1]
            break
    if anchor is not None:
        anchor.addnext(borders)
    else:
        tblPr.insert(0, borders)


===== FILE: backend/app/services/email_service.py =====

"""Servicio de envío de email (G.5).

- Envía vía SMTP usando smtplib (síncrono; el scheduler corre en su propio
  hilo y los endpoints que envían lo hacen de forma puntual).
- Respeta el toggle GLOBAL (settings.emails_enabled) y POR CLIENTE
  (client.emails_enabled): si cualquiera está desactivado, no envía pero
  registra el intento con status "disabled".
- Toda salida (enviada, fallida o desactivada) deja traza en email_log.
- En desarrollo, docker-compose.dev.yml apunta SMTP a Mailpit, así que los
  emails se ven en http://localhost:8025 sin configurar un SMTP real.

El servicio NO decide CUÁNDO enviar (eso es la máquina de estados / scheduler /
endpoints); solo CÓMO enviar y registrar.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import BrandConfig, Client, EmailLog
from app.services.email_templates import Brand


def brand_from_config(db: Session) -> Brand:
    cfg = db.scalar(select(BrandConfig).limit(1))
    if cfg is None:
        return Brand(name="Tu asesoría", color_primary="#6EE7B7", color_bg="#0A0A0F")
    logo_url = None
    if cfg.logo_path:
        logo_url = f"{settings.public_base_url}/storage/{cfg.logo_path}"
    return Brand(
        name=cfg.name,
        color_primary=cfg.color_primary,
        color_bg=cfg.color_bg,
        contact_email=cfg.contact_email or None,
        logo_url=logo_url,
    )


class EmailService:
    """Envío + registro. Inyectable: en tests se sustituye `_transport`."""

    def __init__(self, db: Session):
        self.db = db

    # -- transporte (sobrescribible en tests) --
    def _transport(self, msg: EmailMessage) -> None:
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as s:
                self._auth_and_send(s, msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
                try:
                    s.starttls()
                except smtplib.SMTPNotSupportedError:
                    pass  # Mailpit y algunos relays no usan TLS
                self._auth_and_send(s, msg)

    def _auth_and_send(self, s: smtplib.SMTP, msg: EmailMessage) -> None:
        if settings.smtp_user:
            s.login(settings.smtp_user, settings.smtp_pass)
        s.send_message(msg)

    def _log(self, client_id: int | None, kind: str, subject: str, status: str) -> None:
        self.db.add(EmailLog(client_id=client_id, kind=kind, subject=subject, status=status))

    def send(
        self, *, to: str, subject: str, html: str, kind: str,
        client: Client | None = None,
    ) -> str:
        """Envía un email y registra el resultado. Devuelve el status final.

        No hace commit: el caller controla la transacción (así el envío y los
        cambios de estado que lo motivan se confirman juntos o no).
        """
        client_id = client.id if client else None

        # Toggle global o por cliente desactivado → no enviar, pero registrar.
        if not settings.emails_enabled or (client is not None and not client.emails_enabled):
            self._log(client_id, kind, subject, "disabled")
            return "disabled"

        msg = EmailMessage()
        msg["From"] = settings.smtp_from or settings.smtp_user or "no-reply@fitness.local"
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(
            "Este email requiere un cliente compatible con HTML. "
            "Abre tu portal para ver el contenido."
        )
        msg.add_alternative(html, subtype="html")

        try:
            self._transport(msg)
            self._log(client_id, kind, subject, "sent")
            return "sent"
        except Exception:
            self._log(client_id, kind, subject, "failed")
            return "failed"


===== FILE: backend/app/services/email_templates.py =====

"""Plantillas HTML de email con marca (G.5).

Cada plantilla es una función que recibe los datos y la marca, y devuelve
(asunto, html). El diseño es sobrio, mobile-first y aplica los colores de
brand_config. Todo el texto de cara al cliente va en castellano.

Las plantillas se mantienen como HTML inline (sin dependencias de assets
externos salvo el logo si existe) para máxima compatibilidad con clientes de
correo. El logo se referencia por URL pública si está disponible.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Brand:
    name: str
    color_primary: str
    color_bg: str
    contact_email: str | None = None
    logo_url: str | None = None


def _shell(brand: Brand, title: str, body_html: str, cta_url: str | None = None,
           cta_label: str | None = None) -> str:
    """Envoltorio común: cabecera con marca, cuerpo, CTA opcional y pie."""
    logo = (
        f'<img src="{brand.logo_url}" alt="{brand.name}" '
        f'style="max-height:48px;margin-bottom:8px">'
        if brand.logo_url else
        f'<div style="font-size:20px;font-weight:700;color:{brand.color_primary}">'
        f'{brand.name}</div>'
    )
    cta = ""
    if cta_url and cta_label:
        cta = (
            f'<table role="presentation" cellpadding="0" cellspacing="0" '
            f'style="margin:24px 0"><tr><td style="border-radius:10px;'
            f'background:{brand.color_primary}">'
            f'<a href="{cta_url}" style="display:inline-block;padding:13px 26px;'
            f'font-weight:600;color:#0A0A0F;text-decoration:none;border-radius:10px">'
            f'{cta_label}</a></td></tr></table>'
        )
    footer_contact = (
        f'<br>¿Dudas? Escríbenos a <a href="mailto:{brand.contact_email}" '
        f'style="color:{brand.color_primary}">{brand.contact_email}</a>.'
        if brand.contact_email else ""
    )
    return f"""\
<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f7;font-family:Inter,Arial,sans-serif">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f7;padding:24px 12px">
<tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background:#ffffff;border-radius:16px;overflow:hidden">
<tr><td style="padding:28px 28px 0">{logo}</td></tr>
<tr><td style="padding:8px 28px 28px;color:#1a1a24;font-size:15px;line-height:1.6">
<h1 style="font-size:19px;margin:12px 0 4px;color:#1a1a24">{title}</h1>
{body_html}
{cta}
<p style="font-size:13px;color:#8a8a94;margin-top:24px">
Este mensaje es parte de tu asesoría personalizada con {brand.name}.{footer_contact}
</p>
</td></tr></table></td></tr></table></body></html>"""


# ---------------------------------------------------------- al cliente ----

def plan_published(brand: Brand, first_name: str, portal_url: str, is_new_month: bool) -> tuple[str, str]:
    if is_new_month:
        subject = f"Tu nuevo plan del mes ya está listo · {brand.name}"
        intro = (
            f"Hola {first_name}, hemos preparado tu plan para el nuevo mes a partir de "
            "tus resultados y tu feedback. Encontrarás los ajustes en tu portal."
        )
    else:
        subject = f"¡Bienvenido/a! Tu plan ya está disponible · {brand.name}"
        intro = (
            f"Hola {first_name}, tu planificación personalizada de nutrición y "
            "entrenamiento ya está lista. Entra en tu portal para verla y registrar "
            "tu día a día."
        )
    body = f"<p>{intro}</p><p>En la vista <strong>HOY</strong> verás qué comer y qué entrenar cada día, en menos de 30 segundos.</p>"
    return subject, _shell(brand, "Tu plan está listo", body, portal_url, "Abrir mi portal")


def reminder_no_logs(brand: Brand, first_name: str, portal_url: str, days_left: int) -> tuple[str, str]:
    subject = f"Un recordatorio rápido de tu seguimiento · {brand.name}"
    body = (
        f"<p>Hola {first_name}, hemos visto que llevas unos días sin registrar tu "
        f"seguimiento. Quedan <strong>{days_left} días</strong> para cerrar este "
        "período.</p><p>Registrar tu peso, entrenos y adherencia nos permite ajustar "
        "tu plan con precisión. ¡Solo te lleva un minuto al día!</p>"
    )
    return subject, _shell(brand, "¿Cómo va tu seguimiento?", body, portal_url, "Registrar ahora")


def closing_due(brand: Brand, first_name: str, portal_url: str, period_index: int) -> tuple[str, str]:
    subject = f"Es momento de cerrar tu período · {brand.name}"
    body = (
        f"<p>Hola {first_name}, tu período actual ha llegado a su fin. Para preparar "
        "tu siguiente fase necesitamos que completes el <strong>cierre</strong>: peso "
        "final, medidas opcionales, alguna foto y cómo te ha ido.</p>"
        "<p>Con esa información ajustaremos tu plan para que sigas progresando.</p>"
    )
    return subject, _shell(brand, "Cierra tu período", body, f"{portal_url}/cierre", "Completar cierre")


def feedback_ready(brand: Brand, first_name: str, portal_url: str) -> tuple[str, str]:
    subject = f"Tu informe de progreso está listo · {brand.name}"
    body = (
        f"<p>Hola {first_name}, ya tienes tu informe de seguimiento con tus gráficas "
        "de progreso, evolución de fuerza y los cambios que hemos hecho en tu plan "
        "(y por qué).</p>"
    )
    return subject, _shell(brand, "Tu progreso, en detalle", body, f"{portal_url}/feedback", "Ver mi informe")


def plan_republished(brand: Brand, first_name: str, portal_url: str, change_summary: str) -> tuple[str, str]:
    subject = f"Tu planificación se ha actualizado · {brand.name}"
    body = (
        f"<p>Hola {first_name}, hemos actualizado tu planificación:</p>"
        f"<p style='background:#f4f4f7;border-radius:10px;padding:12px 14px'>{change_summary}</p>"
        "<p>Ya puedes ver los cambios en tu portal.</p>"
    )
    return subject, _shell(brand, "Plan actualizado", body, portal_url, "Ver cambios")


# ------------------------------------------------------------ al coach ----

def coach_change_request(brand: Brand, client_name: str, message: str, dashboard_url: str) -> tuple[str, str]:
    subject = f"[Acción] {client_name} ha solicitado un ajuste"
    body = (
        f"<p>El cliente <strong>{client_name}</strong> ha enviado una solicitud de "
        f"ajuste:</p><p style='background:#f4f4f7;border-radius:10px;padding:12px 14px'>"
        f"{message}</p><p>Revísala y republica el plan cuando lo resuelvas.</p>"
    )
    return subject, _shell(brand, "Solicitud de ajuste", body, dashboard_url, "Abrir panel")


def coach_at_risk(brand: Brand, client_name: str, reason: str, dashboard_url: str) -> tuple[str, str]:
    subject = f"[Aviso] {client_name} está en riesgo de abandono"
    body = (
        f"<p>El cliente <strong>{client_name}</strong> ha pasado a estado "
        f"<strong>at_risk</strong>:</p>"
        f"<p style='background:#fff4f4;border-radius:10px;padding:12px 14px'>{reason}</p>"
        "<p>Quizá convenga un contacto personal para recuperar la adherencia.</p>"
    )
    return subject, _shell(brand, "Cliente en riesgo", body, dashboard_url, "Abrir panel")


===== FILE: backend/app/services/feedback_service.py =====

"""Orquestación del FEEDBACK quincenal del coach (cierre → informe).

A partir de un período CERRADO por el cliente:
1. reúne los registros diarios + datos de cierre + período anterior,
2. calcula TODAS las métricas con services/metrics (la IA nunca calcula),
3. pide a la IA SOLO la parte cualitativa (análisis y recomendaciones),
4. genera el documento Word con gráficas y lo persiste como FeedbackDoc,
5. marca el período como `analyzed` y guarda métricas/análisis.

Devuelve el FeedbackDoc creado. Reutilizable con un AIClient inyectado (tests).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BrandConfig, Client, DailyLog, Exercise, FeedbackDoc, Period, WorkoutLog
from app.services import metrics as M
from app.services.audit import log_event
from app.services.docs.feedback_doc import generate_feedback_doc
from app.services.docs.word_base import DocBrand
from app.services.storage import abs_path, client_dir, storage_root


class FeedbackError(RuntimeError):
    """No se pudo generar el feedback (datos insuficientes o fallo de IA)."""


def _doc_brand(db: Session) -> DocBrand:
    cfg = db.scalar(select(BrandConfig).limit(1))
    if cfg is None:
        return DocBrand(name="Tu asesoría", color_primary="#6EE7B7",
                        color_secondary="#8B9DF7", font_family="Inter")
    logo_abs = None
    if cfg.logo_path:
        try:
            logo_abs = str(abs_path(cfg.logo_path))
        except Exception:
            logo_abs = None
    return DocBrand(
        name=cfg.name, color_primary=cfg.color_primary,
        color_secondary=cfg.color_secondary, font_family=cfg.font_family,
        tagline=cfg.tagline, contact_email=cfg.contact_email, logo_path=logo_abs,
    )


def _prev_period(db: Session, period: Period) -> Period | None:
    return db.scalar(
        select(Period).where(
            Period.client_id == period.client_id,
            Period.period_index < period.period_index,
        ).order_by(Period.period_index.desc()).limit(1)
    )


def _perimeters(prev: Period | None, cur: Period) -> dict[str, list[tuple[str, float]]] | None:
    """Series de perímetros: período anterior (si hay) → actual."""
    fields = [("Cintura", "closing_waist_cm"), ("Cadera", "closing_hip_cm"),
              ("Brazo", "closing_arm_cm"), ("Muslo", "closing_thigh_cm")]
    out: dict[str, list[tuple[str, float]]] = {}
    for label, attr in fields:
        cur_v = getattr(cur, attr, None)
        if cur_v is None:
            continue
        series: list[tuple[str, float]] = []
        prev_v = getattr(prev, attr, None) if prev else None
        if prev_v is not None:
            series.append(("Anterior", prev_v))
        series.append(("Actual", cur_v))
        out[label] = series
    return out or None


def _photo_pairs(db: Session, prev: Period | None, cur: Period) -> list[tuple[str, str]] | None:
    """Empareja fotos por ángulo: período anterior vs actual."""
    from app.models import ProgressPhoto

    if not prev:
        return None
    def by_kind(pid: int) -> dict[str, str]:
        rows = db.scalars(select(ProgressPhoto).where(ProgressPhoto.period_id == pid))
        d: dict[str, str] = {}
        for ph in rows:
            try:
                p = abs_path(ph.file_path)
                if p.exists():
                    d[ph.kind] = str(p)
            except Exception:
                pass
        return d
    before, after = by_kind(prev.id), by_kind(cur.id)
    pairs = [(before[k], after[k]) for k in after if k in before]
    return pairs or None


def _workout_sets_for_logs(db: Session, log_ids: list[int]) -> list[dict]:
    if not log_ids:
        return []
    return [
        {"exercise_id": wl.exercise_id, "weight_kg": wl.weight_kg, "reps": wl.reps, "daily_log_id": wl.daily_log_id}
        for wl in db.scalars(select(WorkoutLog).where(WorkoutLog.daily_log_id.in_(log_ids)))
    ]


def compute_period_summary(db: Session, period_id: int) -> dict:
    """Resumen de métricas del período SIN IA, a partir de lo que el cliente
    registró: cambio de peso corporal, adherencia, fuerza ganada (e1RM vs período
    anterior) y distancia al objetivo. Para el botón de feedback rápido del coach."""
    period = db.get(Period, period_id)
    if not period:
        raise FeedbackError("Período no encontrado")
    client = db.get(Client, period.client_id)

    logs = list(db.scalars(
        select(DailyLog).where(DailyLog.period_id == period_id).order_by(DailyLog.log_date)
    ))
    period_days = (period.ends_on - period.starts_on).days + 1

    raw_points = [(dl.log_date, dl.weight_kg) for dl in logs if dl.weight_kg is not None]
    if period.closing_weight_kg is not None:
        raw_points.append((period.ends_on, period.closing_weight_kg))
    wt = M.weight_trend(raw_points)

    adh = M.adherence_summary([{
        "diet_adherence": dl.diet_adherence, "sleep_hours": dl.sleep_hours,
        "energy_1_5": dl.energy_1_5, "mood_1_5": dl.mood_1_5, "fatigue_1_5": dl.fatigue_1_5,
    } for dl in logs], period_days)

    # Fuerza: mejor e1RM por ejercicio este período vs el período anterior
    sets = _workout_sets_for_logs(db, [dl.id for dl in logs])
    progress = M.exercise_e1rm_progress(sets)[:6]
    prev = _prev_period(db, period)
    prev_best: dict[int, float] = {}
    if prev:
        prev_logs = list(db.scalars(select(DailyLog.id).where(DailyLog.period_id == prev.id)))
        for p in M.exercise_e1rm_progress(_workout_sets_for_logs(db, list(prev_logs))):
            prev_best[p.exercise_id] = p.best_e1rm_kg
    ex_ids = {p.exercise_id for p in progress}
    ex_info = {e.id: e for e in db.scalars(select(Exercise).where(Exercise.id.in_(ex_ids)))} if ex_ids else {}
    strength = [{
        "name": ex_info[p.exercise_id].canonical_name if p.exercise_id in ex_info else f"#{p.exercise_id}",
        "e1rm_kg": p.best_e1rm_kg,
        "delta_kg": round(p.best_e1rm_kg - prev_best[p.exercise_id], 1) if p.exercise_id in prev_best else None,
    } for p in progress]

    current = period.closing_weight_kg if period.closing_weight_kg is not None else (
        wt.end_kg if wt.end_kg is not None else client.start_weight_kg
    )
    goal = client.goal_weight_kg
    distance = round(current - goal, 1) if (current is not None and goal is not None) else None

    return {
        "period_index": period.period_index,
        "status": period.status,
        "weight": {
            "start_kg": wt.start_kg, "end_kg": wt.end_kg,
            "delta_kg": wt.delta_kg, "weekly_rate_kg": wt.weekly_rate_kg,
        },
        "body_weight_now_kg": current,
        "goal_weight_kg": goal,
        "distance_to_goal_kg": distance,
        "adherence": {
            "diet_pct": round(adh.diet_adherence_ratio * 100),
            "log_pct": round(min(1.0, adh.log_ratio) * 100),
            "days_logged": adh.days_logged, "period_days": adh.period_days,
        },
        "strength": strength,
    }


def _gather_doc_inputs(db: Session, period: Period, client: Client) -> dict:
    """Reúne TODO lo calculado que necesita el documento de feedback (sin IA).
    Reutilizado por la generación y por la edición/regeneración."""
    logs = list(db.scalars(
        select(DailyLog).where(DailyLog.period_id == period.id).order_by(DailyLog.log_date)
    ))
    period_days = (period.ends_on - period.starts_on).days + 1

    raw_points = [(dl.log_date, dl.weight_kg) for dl in logs if dl.weight_kg is not None]
    if period.closing_weight_kg is not None:
        raw_points.append((period.ends_on, period.closing_weight_kg))
    weight_points = [(f"{d.day}/{d.month}", w) for d, w in sorted(raw_points)]
    wt = M.weight_trend(raw_points)

    adh = M.adherence_summary([{
        "diet_adherence": dl.diet_adherence, "sleep_hours": dl.sleep_hours,
        "energy_1_5": dl.energy_1_5, "mood_1_5": dl.mood_1_5, "fatigue_1_5": dl.fatigue_1_5,
    } for dl in logs], period_days)

    sets = _workout_sets_for_logs(db, [dl.id for dl in logs])
    progress = M.exercise_e1rm_progress(sets)[:5]
    ex_ids = {p.exercise_id for p in progress} | {s["exercise_id"] for s in sets}
    ex_info = {e.id: e for e in db.scalars(select(Exercise).where(Exercise.id.in_(ex_ids)))} if ex_ids else {}
    e1rm_exercises = [{
        "name": ex_info[p.exercise_id].canonical_name if p.exercise_id in ex_info else f"#{p.exercise_id}",
        "e1rm_kg": p.best_e1rm_kg,
    } for p in progress]

    weeks = max(1.0, period_days / 7)
    vol_counts: dict[str, float] = {}
    for s in sets:
        info = ex_info.get(s["exercise_id"])
        group = info.muscle_primary if info else "otros"
        vol_counts[group] = vol_counts.get(group, 0) + 1
    volume_by_group = {g: round(c / weeks, 1) for g, c in vol_counts.items()} or None

    prev = _prev_period(db, period)
    pm = M.PeriodMetrics(weight=wt, adherence=adh, exercise_progress=progress)
    return {
        "weight_points": weight_points, "e1rm_exercises": e1rm_exercises,
        "perimeters": _perimeters(prev, period),
        "volume_by_group": volume_by_group,
        "photo_pairs": _photo_pairs(db, prev, period),
        "metrics_json": pm.to_json(),
    }


def _write_feedback_doc(db: Session, client: Client, period: Period, inputs: dict, ai_out) -> str:
    """Genera el .docx con las gráficas + el texto (de la IA o editado) y lo guarda."""
    docx = generate_feedback_doc(
        brand=_doc_brand(db), client_name=client.full_name, period_index=period.period_index,
        metrics=inputs["metrics_json"], weight_points=inputs["weight_points"],
        goal_kg=client.goal_weight_kg, e1rm_exercises=inputs["e1rm_exercises"],
        perimeters=inputs["perimeters"], volume_by_group=inputs["volume_by_group"],
        photo_pairs=inputs["photo_pairs"],
        ai_photo_analysis=ai_out.ai_photo_analysis if inputs["photo_pairs"] else None,
        natural_analysis=ai_out.natural_analysis, changes_bullets=ai_out.changes_bullets,
        answers=ai_out.answers, next_objectives=ai_out.next_objectives,
        closing_message=ai_out.closing_message,
        plan_adjustments=[
            {"area": a.area, "change": a.change, "reason": a.reason}
            for a in getattr(ai_out, "plan_adjustments", []) or []
        ],
    )
    folder = client_dir(client.id, "feedback")
    fname = f"feedback_p{period.period_index}.docx"
    (folder / fname).write_bytes(docx)
    return str((folder / fname).relative_to(storage_root()))


def build_period_feedback(db: Session, period_id: int, ai=None) -> FeedbackDoc:
    """Genera y persiste el feedback (borrador) de un período cerrado."""
    from app.services.ai.client import AIClient, AIGenerationError
    from app.services.ai.feedback import generate_feedback_analysis

    ai = ai or AIClient()
    period = db.get(Period, period_id)
    if not period:
        raise FeedbackError("Período no encontrado")
    if period.status == "open":
        raise FeedbackError("El período aún no está cerrado por el cliente")
    client = db.get(Client, period.client_id)

    inputs = _gather_doc_inputs(db, period, client)
    logs_q = list(db.scalars(
        select(DailyLog).where(DailyLog.period_id == period.id).order_by(DailyLog.log_date)
    ))
    payload = {
        "objetivo": client.goal_type, "peso_objetivo_kg": client.goal_weight_kg,
        "periodo_index": period.period_index, "metricas": inputs["metrics_json"],
        # Registro DIARIO crudo del cliente (para que la IA lo interprete)
        "registro_diario": [{
            "fecha": dl.log_date.isoformat(), "peso": dl.weight_kg, "sueno_h": dl.sleep_hours,
            "pasos": dl.steps, "saciedad_1_10": dl.satiety_1_10, "agua_l": dl.water_liters,
            "adherencia_dieta": dl.diet_adherence, "notas": dl.free_notes,
        } for dl in logs_q],
        # REVISIÓN QUINCENAL completa
        "revision_quincenal": {
            "peso_kg": period.closing_weight_kg,
            "medidas_cm": {"cintura": period.closing_waist_cm, "cadera": period.closing_hip_cm,
                           "brazo": period.closing_arm_cm, "muslo": period.closing_thigh_cm},
            "sensaciones_1_5": period.closing_feelings_json,
            "adherencia_dieta_0_10": period.adherence_diet_0_10,
            "adherencia_entreno_0_10": period.adherence_training_0_10,
            "comidas_libres": period.free_meals_count,
            "cambios_importantes": period.closing_changes,
            "lo_mas_dificil": period.closing_hardest,
            "objetivo_proximo": period.closing_next_goal,
            "dudas": period.closing_questions,
            "valoracion_1_5": period.closing_rating,
        },
        "hay_fotos": bool(inputs["photo_pairs"]),
    }
    try:
        ai_out = generate_feedback_analysis(payload, ai)
    except AIGenerationError as exc:
        raise FeedbackError(f"La IA no devolvió un feedback válido: {exc}") from exc

    docx_rel = _write_feedback_doc(db, client, period, inputs, ai_out)
    fb = FeedbackDoc(period_id=period.id, kind="biweekly",
                     content_json={**ai_out.model_dump(), "metrics": inputs["metrics_json"],
                                   "weight_points": inputs["weight_points"],
                                   "goal_weight_kg": client.goal_weight_kg},
                     docx_path=docx_rel)
    db.add(fb)
    period.status = "analyzed"
    period.metrics_json = inputs["metrics_json"]
    period.ai_analysis_json = ai_out.model_dump()
    period.ai_photo_analysis = ai_out.ai_photo_analysis
    db.flush()
    log_event(db, "period", period.id, "feedback_generated", {"feedback_id": fb.id})
    db.commit()
    db.refresh(fb)
    return fb


_TEXT_FIELDS = ("natural_analysis", "changes_bullets", "plan_adjustments", "answers",
                "next_objectives", "closing_message", "ai_photo_analysis")


def update_feedback_text(db: Session, feedback_id: int, text: dict) -> FeedbackDoc:
    """Edición MANUAL del feedback por el coach: actualiza el texto, **regenera el
    Word** y refresca lo que verá el cliente. No recalcula métricas ni llama a la IA."""
    from app.services.ai.feedback import FeedbackAIOutput

    fb = db.get(FeedbackDoc, feedback_id)
    if not fb:
        raise FeedbackError("Feedback no encontrado")
    period = db.get(Period, fb.period_id)
    client = db.get(Client, period.client_id)

    current = dict(fb.content_json or {})
    metrics = current.get("metrics")
    merged = {k: current.get(k) for k in _TEXT_FIELDS}
    for k, v in (text or {}).items():
        if k in merged:
            merged[k] = v
    ai_out = FeedbackAIOutput.model_validate(merged)

    inputs = _gather_doc_inputs(db, period, client)
    fb.docx_path = _write_feedback_doc(db, client, period, inputs, ai_out)
    fb.content_json = {**ai_out.model_dump(), "metrics": metrics or inputs["metrics_json"],
                       "weight_points": inputs["weight_points"],
                       "goal_weight_kg": client.goal_weight_kg}
    period.ai_analysis_json = ai_out.model_dump()
    db.flush()
    log_event(db, "period", period.id, "feedback_edited", {"feedback_id": fb.id})
    db.commit()
    db.refresh(fb)
    return fb


===== FILE: backend/app/services/guardrails.py =====

"""Guardrails — validación de seguridad de TODA salida de IA (E.4 + F.4).

Capa independiente de la validación de forma (Pydantic en schemas/ai.py).
Pydantic garantiza que el JSON tiene la *estructura* correcta; los guardrails
garantizan que los *valores* son seguros y coherentes con la metodología.

Cada función devuelve `GuardrailReport`:
- `violations`: problemas que BLOQUEAN la publicación (kcal por debajo del
  mínimo fisiológico, proteína insuficiente, volumen excesivo, ejercicio
  contraindicado…). Si hay alguna, el plan no se publica tal cual.
- `warnings`: avisos no bloqueantes que se registran en plans.guardrail_flags
  y se muestran al coach para revisión.

Diseño: los guardrails NO modifican la salida; informan. El servicio de IA
decide reintentar (con el error inyectado) o escalar al coach.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --- Constantes E.4 (nutrición) ---
KCAL_FLOOR_FEMALE = 1400
KCAL_FLOOR_MALE = 1600
RECAL_KCAL_ADJUST_MAX = 0.15   # ±15% kcal por recalibración
PROTEIN_MIN_G_PER_KG = 1.4
FAT_MIN_G_PER_KG = 0.5
DEFICIT_MAX_PCT = 0.30         # 30% TDEE
SURPLUS_MAX_PCT = 0.15         # 15% TDEE
MEAL_OPTION_TOLERANCE = 0.05   # ±5% macros del slot

# --- Constantes F.4 (entrenamiento) ---
SETS_MAX_PER_GROUP_WEEK = 25
LOAD_INCREMENT_MAX_PCT = 0.10  # +10% por ejercicio y recalibración
SESSION_MINUTES_FORMULA_PER_SET = 3
SESSION_MINUTES_FIXED_OVERHEAD = 10
# La duración es una ESTIMACIÓN heurística y la logística no es seguridad: un
# exceso leve sobre el máximo declarado es aviso (el coach recorta), no bloqueo.
# Solo bloquea un exceso holgado (> tolerancia).
SESSION_MINUTES_TOLERANCE = 0.20

KCAL_PER_G = {"protein_g": 4, "carbs_g": 4, "fat_g": 9}


@dataclass
class GuardrailReport:
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations

    def merge(self, other: "GuardrailReport") -> "GuardrailReport":
        return GuardrailReport(
            violations=self.violations + other.violations,
            warnings=self.warnings + other.warnings,
        )

    def as_flags(self) -> list[str]:
        """Para persistir en plans.guardrail_flags (prefijo legible)."""
        return [f"violation:{v}" for v in self.violations] + [
            f"warning:{w}" for w in self.warnings
        ]


# =================================================================== E.4 ====

def check_nutrition(
    nutrition: dict,
    *,
    sex: str,
    weight_kg: float,
    bmr: float,
    tdee: float,
    is_recalibration: bool = False,
    previous_target_kcal: float | None = None,
) -> GuardrailReport:
    """Valida el bloque de nutrición de la salida de IA contra E.4.

    `nutrition` es el dict `nutrition` de PlanCoreOutput (ya validado en forma).
    """
    r = GuardrailReport()
    target = float(nutrition["target_kcal"])
    macros = nutrition["macros"]
    protein = float(macros["protein_g"])
    fat = float(macros["fat_g"])

    # Suelo calórico: max(BMR, suelo por sexo)
    floor = max(bmr, KCAL_FLOOR_MALE if sex == "male" else KCAL_FLOOR_FEMALE)
    if target < floor:
        r.violations.append(
            f"kcal objetivo {target:.0f} por debajo del mínimo {floor:.0f} "
            f"(max BMR/{'1600' if sex == 'male' else '1400'})"
        )

    # Déficit / superávit máximos respecto al TDEE
    if tdee > 0:
        delta_pct = (target - tdee) / tdee
        if delta_pct < -DEFICIT_MAX_PCT:
            r.violations.append(
                f"déficit {abs(delta_pct) * 100:.0f}% supera el máximo "
                f"{DEFICIT_MAX_PCT * 100:.0f}% del TDEE"
            )
        if delta_pct > SURPLUS_MAX_PCT:
            r.violations.append(
                f"superávit {delta_pct * 100:.0f}% supera el máximo "
                f"{SURPLUS_MAX_PCT * 100:.0f}% del TDEE"
            )

    # Mínimos de proteína y grasa por kg
    if weight_kg > 0:
        if protein < PROTEIN_MIN_G_PER_KG * weight_kg - 0.5:
            r.violations.append(
                f"proteína {protein:.0f} g < mínimo "
                f"{PROTEIN_MIN_G_PER_KG * weight_kg:.0f} g ({PROTEIN_MIN_G_PER_KG} g/kg)"
            )
        if fat < FAT_MIN_G_PER_KG * weight_kg - 0.5:
            r.violations.append(
                f"grasa {fat:.0f} g < mínimo "
                f"{FAT_MIN_G_PER_KG * weight_kg:.0f} g ({FAT_MIN_G_PER_KG} g/kg)"
            )

    # Coherencia kcal ↔ macros (no debe desviarse mucho de target)
    macro_kcal = sum(float(macros[k]) * v for k, v in KCAL_PER_G.items())
    if target > 0 and abs(macro_kcal - target) / target > 0.10:
        r.warnings.append(
            f"suma de macros ({macro_kcal:.0f} kcal) se desvía >10% del "
            f"objetivo ({target:.0f} kcal)"
        )

    # Límite de ajuste en recalibración (±15%)
    if is_recalibration and previous_target_kcal:
        change = abs(target - previous_target_kcal) / previous_target_kcal
        if change > RECAL_KCAL_ADJUST_MAX:
            r.violations.append(
                f"ajuste de {change * 100:.0f}% supera el máximo "
                f"{RECAL_KCAL_ADJUST_MAX * 100:.0f}% por recalibración"
            )

    # Slots de comida: cada target de slot dentro de ±5% no aplica aquí
    # (se valida por opción en check_meal_options). Aquí: suma de slots ≈ target.
    meals = nutrition.get("meals", [])
    if meals:
        slot_sum = sum(float(m["target"]["kcal"]) for m in meals)
        if target > 0 and abs(slot_sum - target) / target > 0.10:
            r.warnings.append(
                f"suma de slots ({slot_sum:.0f} kcal) se desvía >10% del "
                f"objetivo diario ({target:.0f} kcal)"
            )
    return r


def check_meal_options(slots: list[dict], day_targets: dict[int, dict]) -> GuardrailReport:
    """Valida que cada opción de comida cumple los macros de su slot ±5% (E.4).

    `slots`: lista de FlexibleSlot serializados (slot + options[]).
    `day_targets`: {slot: {kcal, protein_g, carbs_g, fat_g}} del plan núcleo.
    Devuelve violación por cada opción concreta fuera de tolerancia, indicando
    slot y key para que el servicio de IA re-pida SOLO esa opción.
    """
    r = GuardrailReport()
    for slot_block in slots:
        slot = slot_block["slot"]
        target = day_targets.get(slot)
        if not target:
            r.warnings.append(f"slot {slot} sin target de referencia")
            continue
        for opt in slot_block["options"]:
            _check_single_option(r, slot, opt, target)
    return r


def check_strict_day_meals(days: list[dict], day_targets: dict[int, dict]) -> GuardrailReport:
    """Igual que check_meal_options pero para el modo strict (un plato/slot/día)."""
    r = GuardrailReport()
    for day_block in days:
        day_name = day_block.get("day", "?")
        for meal in day_block["meals"]:
            slot = meal["slot"]
            target = day_targets.get(slot)
            if not target:
                r.warnings.append(f"slot {slot} sin target de referencia")
                continue
            _check_single_option(r, slot, meal["dish"], target, label=f"{day_name}/")
    return r


def _check_single_option(
    r: GuardrailReport, slot: int, opt: dict, target: dict, label: str = ""
) -> None:
    macros = opt["macros"]
    key = opt.get("key", opt.get("title", "?"))
    for macro in ("kcal", "protein_g", "carbs_g", "fat_g"):
        tgt = float(target[macro])
        val = float(macros[macro])
        if tgt <= 0:
            continue
        if abs(val - tgt) / tgt > MEAL_OPTION_TOLERANCE:
            r.violations.append(
                f"opción {label}slot {slot} '{key}': {macro} {val:.0f} fuera de "
                f"±{MEAL_OPTION_TOLERANCE * 100:.0f}% del objetivo {tgt:.0f}"
            )


# =================================================================== F.4 ====

def check_training(
    training: dict,
    *,
    training_days_declared: int,
    session_max_min: int,
    client_contraindications: set[str],
    exercise_lookup: dict[int, dict],
    is_recalibration: bool = False,
    previous_weights: dict[int, float] | None = None,
) -> GuardrailReport:
    """Valida el bloque de entrenamiento contra F.4.

    `exercise_lookup`: {exercise_id: {contraindications, muscle_primary, name}}
    para cruzar contraindicaciones y contar volumen por grupo.
    `previous_weights`: {exercise_id: start_weight_hint_kg} del plan anterior,
    para el límite de +10% por recalibración.
    """
    r = GuardrailReport()
    sessions = training.get("sessions", [])

    # 1) Nunca exceder días declarados
    if len(sessions) > training_days_declared:
        r.violations.append(
            f"{len(sessions)} sesiones > {training_days_declared} días declarados"
        )

    weekly_sets_by_group: dict[str, float] = {}

    for sess in sessions:
        session_sets = 0
        for ex in sess.get("exercises", []):
            ex_id = ex["exercise_id"]
            sets = int(ex["sets"])
            session_sets += sets
            info = exercise_lookup.get(ex_id)

            if info is None:
                r.violations.append(
                    f"exercise_id {ex_id} no existe en la biblioteca"
                )
                continue

            # 2) Contraindicaciones (doble verificación post-IA)
            contra = set(info.get("contraindications") or [])
            clash = contra & client_contraindications
            if clash:
                r.violations.append(
                    f"'{info.get('canonical_name', ex_id)}' contraindicado para "
                    f"lesión(es): {', '.join(sorted(clash))}"
                )

            # Volumen por grupo (primario cuenta completo)
            group = info.get("muscle_primary", "desconocido")
            weekly_sets_by_group[group] = weekly_sets_by_group.get(group, 0) + sets

            # 3) Incremento de carga máx +10% por recalibración
            if is_recalibration and previous_weights:
                prev = previous_weights.get(ex_id)
                new = ex.get("start_weight_hint_kg")
                if prev and new and prev > 0:
                    inc = (new - prev) / prev
                    if inc > LOAD_INCREMENT_MAX_PCT:
                        r.violations.append(
                            f"'{info.get('canonical_name', ex_id)}': subida de "
                            f"{inc * 100:.0f}% supera el máximo "
                            f"{LOAD_INCREMENT_MAX_PCT * 100:.0f}%"
                        )

        # 4) Duración estimada de la sesión: series×3min + 10. Exceso leve = aviso;
        # exceso holgado (> tolerancia) = violación que bloquea.
        est_min = session_sets * SESSION_MINUTES_FORMULA_PER_SET + SESSION_MINUTES_FIXED_OVERHEAD
        if est_min > session_max_min * (1 + SESSION_MINUTES_TOLERANCE):
            r.violations.append(
                f"sesión '{sess.get('name', '?')}' ~{est_min} min supera el "
                f"máximo declarado {session_max_min} min"
            )
        elif est_min > session_max_min:
            r.warnings.append(
                f"sesión '{sess.get('name', '?')}' ~{est_min} min supera "
                f"ligeramente el máximo declarado {session_max_min} min; revisa y recorta series si quieres"
            )

    # 5) Volumen semanal máximo por grupo
    for group, total in weekly_sets_by_group.items():
        if total > SETS_MAX_PER_GROUP_WEEK:
            r.violations.append(
                f"grupo '{group}': {total:.0f} series/semana supera el máximo "
                f"{SETS_MAX_PER_GROUP_WEEK}"
            )
    return r


def filter_exercises_for_client(
    exercises: list[dict],
    *,
    client_contraindications: set[str],
    excluded_ids: set[int],
    equipment_available: set[str],
    level_max: int,
    training_place: str,
) -> list[dict]:
    """Filtro determinista PREVIO a la IA (F.3 / D.2): la IA solo ve ejercicios
    aptos. Reduce contexto y previene contraindicaciones de raíz.

    En 'home'/'outdoor' no se exige equipamiento de gimnasio; en 'gym' se
    requiere que el cliente disponga de TODO el equipamiento del ejercicio.
    """
    out = []
    for ex in exercises:
        if ex.get("archived"):
            continue
        if ex["id"] in excluded_ids:
            continue
        if ex.get("level_min", 1) > level_max:
            continue
        contra = set(ex.get("contraindications") or [])
        if contra & client_contraindications:
            continue
        needed = set(ex.get("equipment") or [])
        if training_place == "gym":
            # En gimnasio se asume equipamiento estándar; solo se exige que el
            # cliente no haya excluido el equipamiento explícitamente.
            if needed and equipment_available and not needed <= equipment_available:
                # permite peso corporal siempre
                if needed != {"peso_corporal"}:
                    continue
        else:
            # casa/exterior: solo lo que el cliente declaró tener (o peso corporal)
            if needed and not needed <= (equipment_available | {"peso_corporal"}):
                continue
        out.append(ex)
    return out


===== FILE: backend/app/services/jobs.py =====

"""Jobs del scheduler (G.1/G.2/G.5) — la capa con efectos.

`run_daily_maintenance(db, today)` es el job diario idempotente:
- Para cada cliente con período activo, calcula los hechos desde la DB.
- Llama a la máquina de estados (función pura) para decidir transiciones.
- Persiste cambios de estado, registra en audit_log y dispara los emails que
  correspondan (recordatorio al cliente, alerta at_risk al coach).

Idempotencia: un email de un `kind` concreto no se reenvía si ya se registró
para ese cliente hoy (se consulta email_log por kind + fecha). Así, ejecutar el
job dos veces el mismo día no duplica nada.

Se ejecuta vía APScheduler (scheduler.py) una vez al día, y también puede
invocarse manualmente para pruebas o backfill.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Client, DailyLog, EmailLog, Period
from app.services import email_templates as tpl
from app.services.audit import log_event
from app.services.email_service import EmailService, brand_from_config
from app.services.state_machine import (
    ClientFacts,
    can_transition,
    evaluate_transition,
)


def _already_sent_today(db: Session, client_id: int, kind: str, today: date) -> bool:
    start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    n = db.scalar(
        select(func.count())
        .select_from(EmailLog)
        .where(
            EmailLog.client_id == client_id,
            EmailLog.kind == kind,
            EmailLog.sent_at >= start,
        )
    )
    return bool(n)


def _active_period(db: Session, client_id: int) -> Period | None:
    """Período más reciente del cliente que no esté analizado."""
    return db.scalar(
        select(Period)
        .where(Period.client_id == client_id, Period.status != "analyzed")
        .order_by(Period.period_index.desc())
        .limit(1)
    )


def _facts_for(db: Session, client: Client) -> ClientFacts:
    period = _active_period(db, client.id)
    if period is None:
        return ClientFacts(status=client.status)

    days_logged = db.scalar(
        select(func.count())
        .select_from(DailyLog)
        .where(DailyLog.period_id == period.id)
    ) or 0

    last_log_date = db.scalar(
        select(func.max(DailyLog.log_date)).where(DailyLog.period_id == period.id)
    )
    last_activity = last_log_date or period.starts_on

    return ClientFacts(
        status=client.status,
        has_active_period=True,
        period_start=period.starts_on,
        period_end=period.ends_on,
        period_closed=period.status in ("closed", "analyzed"),
        days_logged_in_period=int(days_logged),
        last_activity_date=last_activity,
    )


def run_daily_maintenance(db: Session, today: date | None = None) -> dict:
    """Job diario. Devuelve un resumen de lo actuado (útil para logs/tests)."""
    today = today or date.today()
    summary = {"evaluated": 0, "transitions": 0, "reminders": 0, "at_risk_alerts": 0}

    clients = db.scalars(
        select(Client).where(Client.status.notin_(["inactive"]))
    ).all()
    if not clients:
        return summary

    emailer = EmailService(db)
    brand = brand_from_config(db)
    base = settings.public_base_url

    for client in clients:
        summary["evaluated"] += 1
        facts = _facts_for(db, client)
        decision = evaluate_transition(facts, today)

        # 1) Recordatorio día 12 (no cambia estado)
        if decision.send_reminder and not _already_sent_today(db, client.id, "reminder_no_logs", today):
            period = _active_period(db, client.id)
            days_left = max(0, (period.ends_on - today).days) if period else 0
            subject, html = tpl.reminder_no_logs(
                brand, client.full_name.split()[0],
                f"{base}/p/{client.portal_token}", days_left,
            )
            emailer.send(to=client.email, subject=subject, html=html,
                         kind="reminder_no_logs", client=client)
            summary["reminders"] += 1

        # 2) Cambio de estado
        if decision.new_status and decision.new_status != client.status:
            if can_transition(client.status, decision.new_status):
                old = client.status
                client.status = decision.new_status
                log_event(db, "client", client.id, "status_changed",
                          {"from": old, "to": decision.new_status, "reason": decision.reason})
                summary["transitions"] += 1

                # 3) Alerta al coach si pasa a at_risk
                if decision.notify_coach_at_risk and not _already_sent_today(
                    db, client.id, "coach_at_risk", today
                ):
                    coach_to = settings.smtp_from or settings.smtp_user
                    if coach_to:
                        subject, html = tpl.coach_at_risk(
                            brand, client.full_name, decision.reason, f"{base}/clients/{client.id}",
                        )
                        emailer.send(to=coach_to, subject=subject, html=html,
                                     kind="coach_at_risk", client=client)
                        summary["at_risk_alerts"] += 1

    db.commit()
    return summary


===== FILE: backend/app/services/metrics.py =====

"""Servicio de métricas — TODA la aritmética del sistema vive aquí.

Principio rector (PARTE D.2): **la IA nunca calcula**. El backend computa
energía, medias, tendencias, adherencias y e1RM, y se los entrega ya hechos.
Esto garantiza reproducibilidad, testabilidad y que los guardrails operen
sobre números fiables, no sobre lo que la IA "creía" haber calculado.

Unidades: kg, cm, kcal, gramos. Pesos de comida siempre en crudo (E.3).
"""

from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

# ----------------------------------------------------------------- energía ----

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

# Ajuste calórico por objetivo (fracción del TDEE). El signo lo aplica el caller.
GOAL_ADJUSTMENT = {
    "fat_loss": (0.15, 0.25),   # déficit 15–25%
    "muscle_gain": (0.05, 0.12),  # superávit 5–12%
    "recomp": (0.0, 0.05),       # mantenimiento ±5%
}


def mifflin_st_jeor(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    """BMR (kcal/día). Mifflin-St Jeor — el estándar cuando no hay % graso."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return round(base + (5 if sex == "male" else -161), 1)


def katch_mcardle(weight_kg: float, body_fat_pct: float) -> float:
    """BMR vía masa magra (kcal/día). Preferible si hay % graso fiable."""
    lean = weight_kg * (1 - body_fat_pct / 100)
    return round(370 + 21.6 * lean, 1)


def bmr(
    sex: str, weight_kg: float, height_cm: float, age: int,
    body_fat_pct: float | None = None,
) -> float:
    """BMR usando Katch-McArdle si hay % graso, Mifflin-St Jeor si no (E.1)."""
    if body_fat_pct is not None and 3 <= body_fat_pct <= 60:
        return katch_mcardle(weight_kg, body_fat_pct)
    return mifflin_st_jeor(sex, weight_kg, height_cm, age)


def activity_factor_for_days(training_days: int) -> float:
    """Mapea días de entrenamiento/semana a factor de actividad (E.1)."""
    if training_days <= 1:
        return ACTIVITY_FACTORS["sedentary"]
    if training_days <= 2:
        return ACTIVITY_FACTORS["light"]
    if training_days <= 4:
        return ACTIVITY_FACTORS["moderate"]
    if training_days <= 5:
        return ACTIVITY_FACTORS["active"]
    return ACTIVITY_FACTORS["very_active"]


def tdee(bmr_value: float, training_days: int) -> float:
    return round(bmr_value * activity_factor_for_days(training_days), 1)


def age_from_birth(birth: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


@dataclass
class EnergyTargets:
    bmr: float
    tdee: float
    target_kcal: float
    method: str           # "mifflin" | "katch"
    adjustment_pct: float  # negativo = déficit, positivo = superávit


def energy_targets(
    sex: str, weight_kg: float, height_cm: float, age: int, goal_type: str,
    training_days: int, body_fat_pct: float | None = None,
) -> EnergyTargets:
    """Objetivo calórico de referencia que el backend entrega a la IA.

    La IA puede afinar dentro de los guardrails, pero parte de esta base
    objetiva en lugar de inventarla.
    """
    use_katch = body_fat_pct is not None and 3 <= body_fat_pct <= 60
    b = bmr(sex, weight_kg, height_cm, age, body_fat_pct)
    t = tdee(b, training_days)
    lo, hi = GOAL_ADJUSTMENT.get(goal_type, (0.0, 0.05))
    mid = (lo + hi) / 2
    if goal_type == "fat_loss":
        target = t * (1 - mid)
        adj = -mid
    elif goal_type == "muscle_gain":
        target = t * (1 + mid)
        adj = mid
    else:  # recomp
        target = t
        adj = 0.0
    return EnergyTargets(
        bmr=b, tdee=t, target_kcal=round(target, 1),
        method="katch" if use_katch else "mifflin",
        adjustment_pct=round(adj, 4),
    )


def protein_target_g(weight_kg: float, goal_type: str) -> tuple[float, float]:
    """Rango de proteína recomendado (g/día) según objetivo (E.2)."""
    if goal_type == "fat_loss":
        lo, hi = 2.0, 2.4
    elif goal_type == "muscle_gain":
        lo, hi = 1.6, 2.2
    else:
        lo, hi = 1.8, 2.2
    return round(weight_kg * lo, 1), round(weight_kg * hi, 1)


# ------------------------------------------------------------------- e1RM ----

def epley_1rm(weight_kg: float, reps: int) -> float:
    """1RM estimado (Epley). reps=1 → el propio peso."""
    if reps <= 0:
        return 0.0
    if reps == 1:
        return round(weight_kg, 2)
    return round(weight_kg * (1 + reps / 30), 2)


# ------------------------------------------------- agregados de un período ----

@dataclass
class WeightTrend:
    start_kg: float | None = None
    end_kg: float | None = None
    delta_kg: float | None = None
    weekly_rate_kg: float | None = None  # ritmo semanal (negativo = bajada)
    mean_kg: float | None = None
    n_measurements: int = 0


def weight_trend(points: list[tuple[date, float]]) -> WeightTrend:
    """Tendencia de peso a partir de (fecha, kg). Robusta a huecos.

    El ritmo semanal usa una regresión lineal simple por mínimos cuadrados
    sobre los días transcurridos: más estable que (fin - inicio) ante ruido.
    """
    pts = sorted((d, w) for d, w in points if w is not None)
    if not pts:
        return WeightTrend()
    weights = [w for _, w in pts]
    if len(pts) == 1:
        return WeightTrend(
            start_kg=weights[0], end_kg=weights[0], delta_kg=0.0,
            weekly_rate_kg=0.0, mean_kg=round(weights[0], 2), n_measurements=1,
        )
    day0 = pts[0][0]
    xs = [(d - day0).days for d, _ in pts]
    slope = _least_squares_slope(xs, weights)  # kg/día
    return WeightTrend(
        start_kg=round(weights[0], 2),
        end_kg=round(weights[-1], 2),
        delta_kg=round(weights[-1] - weights[0], 2),
        weekly_rate_kg=round(slope * 7, 3) if slope is not None else None,
        mean_kg=round(statistics.fmean(weights), 2),
        n_measurements=len(pts),
    )


def _least_squares_slope(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom


@dataclass
class AdherenceSummary:
    days_logged: int = 0
    period_days: int = 0
    log_ratio: float = 0.0          # días registrados / días del período
    diet_yes: int = 0
    diet_partial: int = 0
    diet_no: int = 0
    diet_adherence_ratio: float = 0.0  # (yes + 0.5·partial) / registros de dieta
    mean_sleep_h: float | None = None
    mean_energy: float | None = None
    mean_mood: float | None = None
    mean_fatigue: float | None = None


def adherence_summary(
    logs: list[dict], period_days: int,
) -> AdherenceSummary:
    """Resume la adherencia y el bienestar del período.

    `logs`: lista de dicts con claves opcionales diet_adherence, sleep_hours,
    energy_1_5, mood_1_5, fatigue_1_5. Tolera campos ausentes/None.
    """
    s = AdherenceSummary(days_logged=len(logs), period_days=period_days)
    if period_days > 0:
        s.log_ratio = round(len(logs) / period_days, 3)

    diet = [g.get("diet_adherence") for g in logs if g.get("diet_adherence")]
    s.diet_yes = diet.count("yes")
    s.diet_partial = diet.count("partial")
    s.diet_no = diet.count("no")
    if diet:
        s.diet_adherence_ratio = round((s.diet_yes + 0.5 * s.diet_partial) / len(diet), 3)

    s.mean_sleep_h = _mean_of(logs, "sleep_hours")
    s.mean_energy = _mean_of(logs, "energy_1_5")
    s.mean_mood = _mean_of(logs, "mood_1_5")
    s.mean_fatigue = _mean_of(logs, "fatigue_1_5")
    return s


def _mean_of(rows: list[dict], key: str) -> float | None:
    vals = [r[key] for r in rows if r.get(key) is not None]
    return round(statistics.fmean(vals), 2) if vals else None


@dataclass
class ExerciseProgress:
    exercise_id: int
    best_e1rm_kg: float
    best_set: tuple[float, int]  # (peso, reps) que produjo el mejor e1RM
    sessions: int


def exercise_e1rm_progress(sets: list[dict]) -> list[ExerciseProgress]:
    """Mejor e1RM por ejercicio dentro del período.

    `sets`: dicts con exercise_id, weight_kg, reps. Ignora sets sin peso/reps.
    El feedback grafica 3–5 ejercicios; esto da el dato a graficar (H.4).
    """
    by_ex: dict[int, list[dict]] = {}
    for st in sets:
        if st.get("weight_kg") and st.get("reps"):
            by_ex.setdefault(st["exercise_id"], []).append(st)

    out: list[ExerciseProgress] = []
    for ex_id, ex_sets in by_ex.items():
        best = max(ex_sets, key=lambda s: epley_1rm(s["weight_kg"], s["reps"]))
        out.append(ExerciseProgress(
            exercise_id=ex_id,
            best_e1rm_kg=epley_1rm(best["weight_kg"], best["reps"]),
            best_set=(best["weight_kg"], best["reps"]),
            sessions=len({s.get("daily_log_id") for s in ex_sets}),
        ))
    out.sort(key=lambda p: p.best_e1rm_kg, reverse=True)
    return out


def option_choice_stats(chosen: list[dict]) -> dict[int, dict[str, int]]:
    """Frecuencia de elección de opciones por slot (para regeneración mensual).

    `chosen`: lista de chosen_options_json, p.ej. [{"1":"A","2":"C"}, ...].
    Devuelve {slot: {opcion: veces}} para conservar las 4–5 más usadas (C.3).
    """
    counters: dict[int, Counter] = {}
    for day in chosen:
        if not day:
            continue
        for slot_str, opt in day.items():
            try:
                slot = int(slot_str)
            except (ValueError, TypeError):
                continue
            counters.setdefault(slot, Counter())[opt] += 1
    return {slot: dict(c.most_common()) for slot, c in counters.items()}


# ------------------------------------------------- ensamblado para la IA ----

@dataclass
class PeriodMetrics:
    """Paquete completo que el backend persiste en periods.metrics_json y
    entrega a la IA en recalibración/análisis. La IA solo lee, nunca recalcula."""

    weight: WeightTrend
    adherence: AdherenceSummary
    exercise_progress: list[ExerciseProgress] = field(default_factory=list)
    option_stats: dict[int, dict[str, int]] = field(default_factory=dict)

    def to_json(self) -> dict:
        return {
            "weight": {
                "start_kg": self.weight.start_kg, "end_kg": self.weight.end_kg,
                "delta_kg": self.weight.delta_kg,
                "weekly_rate_kg": self.weight.weekly_rate_kg,
                "mean_kg": self.weight.mean_kg,
                "n_measurements": self.weight.n_measurements,
            },
            "adherence": {
                "days_logged": self.adherence.days_logged,
                "period_days": self.adherence.period_days,
                "log_ratio": self.adherence.log_ratio,
                "diet_yes": self.adherence.diet_yes,
                "diet_partial": self.adherence.diet_partial,
                "diet_no": self.adherence.diet_no,
                "diet_adherence_ratio": self.adherence.diet_adherence_ratio,
                "mean_sleep_h": self.adherence.mean_sleep_h,
                "mean_energy": self.adherence.mean_energy,
                "mean_mood": self.adherence.mean_mood,
                "mean_fatigue": self.adherence.mean_fatigue,
            },
            "exercise_progress": [
                {
                    "exercise_id": p.exercise_id, "best_e1rm_kg": p.best_e1rm_kg,
                    "best_weight_kg": p.best_set[0], "best_reps": p.best_set[1],
                    "sessions": p.sessions,
                }
                for p in self.exercise_progress
            ],
            "option_stats": {str(k): v for k, v in self.option_stats.items()},
        }


===== FILE: backend/app/services/portal.py =====

"""Lógica de presentación del portal del cliente (G.4).

Resuelve "el plan y período vigentes" de un cliente y arma la vista HOY a
partir del plan publicado y los registros del día. Mantener esto fuera del
router permite testearlo y reutilizarlo (p. ej. el documento Word offline de
seguimiento de la Fase 7 parte de la misma estructura día a día).

La vista HOY mapea el día de la semana actual a la sesión de entrenamiento
correspondiente del plan y a las comidas del día (banco flexible: las 7
opciones por slot; estricto: el plato del día).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BrandConfig, Client, DailyLog, Exercise, Period, Plan

DAY_LABELS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DAY_SLUGS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


def active_period(db: Session, client_id: int) -> Period | None:
    """Período más reciente no analizado (el que el cliente está viviendo)."""
    return db.scalar(
        select(Period)
        .where(Period.client_id == client_id, Period.status != "analyzed")
        .order_by(Period.period_index.desc())
        .limit(1)
    )


def published_plan_for_period(db: Session, period: Period) -> Plan | None:
    return db.get(Plan, period.plan_id)


def latest_published_plan(db: Session, client_id: int) -> Plan | None:
    return db.scalar(
        select(Plan)
        .where(Plan.client_id == client_id, Plan.status == "published")
        .order_by(Plan.month_index.desc(), Plan.version.desc())
        .limit(1)
    )


def period_info(period: Period | None, today: date) -> dict | None:
    if period is None:
        return None
    days_total = (period.ends_on - period.starts_on).days + 1
    days_elapsed = max(0, min(days_total, (today - period.starts_on).days + 1))
    days_left = max(0, (period.ends_on - today).days)
    # Cierre disponible desde el día 14 del período (G.4)
    can_close = days_elapsed >= 14 and period.status == "open"
    return {
        "period_id": period.id,
        "period_index": period.period_index,
        "starts_on": period.starts_on,
        "ends_on": period.ends_on,
        "days_total": days_total,
        "days_elapsed": days_elapsed,
        "days_left": days_left,
        "can_close": can_close,
        "status": period.status,
    }


def brand_payload(db: Session) -> dict:
    cfg = db.scalar(select(BrandConfig).limit(1))
    if cfg is None:
        return {
            "name": "Tu asesoría", "color_primary": "#6EE7B7",
            "color_secondary": "#8B9DF7", "color_bg": "#0A0A0F",
            "font_family": "Inter", "portal_theme": "dark", "logo_path": None,
        }
    return {
        "name": cfg.name, "color_primary": cfg.color_primary,
        "color_secondary": cfg.color_secondary, "color_bg": cfg.color_bg,
        "font_family": cfg.font_family, "portal_theme": cfg.portal_theme,
        "logo_path": cfg.logo_path,
    }


def _meals_for_today(plan: Plan, client: Client, chosen: dict | None) -> list[dict]:
    """Comidas del día desde el plan. Flexible: 7 opciones/slot. Estricto: plato del día."""
    nutrition = plan.nutrition_json or {}
    meal_defs = nutrition.get("meals", [])  # slots con name/time/target
    bank = nutrition.get("meal_bank") or {}
    mode = client.diet_mode
    chosen = chosen or {}

    slots_out: list[dict] = []
    for mdef in meal_defs:
        slot = mdef["slot"]
        entry = {
            "slot": slot,
            "name": mdef.get("name", f"Comida {slot}"),
            "time": mdef.get("time", ""),
            "target": mdef.get("target", {}),
            "options": [],
            "chosen_key": chosen.get(str(slot)),
        }
        if mode == "flexible_7":
            for s in bank.get("slots", []):
                if s["slot"] == slot:
                    entry["options"] = [
                        {"key": o.get("key"), "title": o["title"], "macros": o["macros"],
                         "prep_minutes": o.get("prep_minutes"), "tags": o.get("tags", [])}
                        for o in s.get("options", [])
                    ]
                    entry["equivalences"] = s.get("equivalences")
        elif mode == "strict":
            # plato del día = el del weekday actual en el menú cerrado
            today_idx = date.today().weekday()
            slug = DAY_SLUGS[today_idx]
            for d in bank.get("days", []):
                if d["day"] == slug:
                    for meal in d["meals"]:
                        if meal["slot"] == slot:
                            dish = meal["dish"]
                            entry["options"] = [{
                                "key": dish.get("key", "A"), "title": dish["title"],
                                "macros": dish["macros"], "prep_minutes": dish.get("prep_minutes"),
                                "tags": dish.get("tags", []),
                            }]
        slots_out.append(entry)
    return slots_out


def _resolve_session(db: Session, sess: dict) -> dict:
    """Convierte una sesión del plan (con exercise_id) en una sesión con nombres
    de ejercicio y vídeo resueltos desde la biblioteca."""
    ex_ids = [e["exercise_id"] for e in sess.get("exercises", [])]
    lib = {
        ex.id: ex
        for ex in db.scalars(select(Exercise).where(Exercise.id.in_(ex_ids)))
    } if ex_ids else {}
    exercises = []
    for e in sess.get("exercises", []):
        ex = lib.get(e["exercise_id"])
        exercises.append({
            "exercise_id": e["exercise_id"],
            "name": ex.canonical_name if ex else f"Ejercicio {e['exercise_id']}",
            "sets": e["sets"], "rep_range": e["rep_range"], "rir": e.get("rir", ""),
            "rest_sec": e.get("rest_sec", 90),
            "start_weight_hint_kg": e.get("start_weight_hint_kg"),
            "technique_cue": e.get("technique_cue"),
            "video_url": ex.video_url if ex and ex.video_url else None,
        })
    return {
        "day": sess.get("day", ""), "name": sess.get("name", ""),
        "warmup": sess.get("warmup"), "exercises": exercises,
        "cooldown": sess.get("cooldown"),
    }


def _session_for_today(db: Session, plan: Plan, today: date) -> dict | None:
    """Sesión de entrenamiento que toca hoy según el día de la semana.

    Mapea el weekday actual al `day` de las sesiones del plan (que vienen como
    "Lunes", "Martes"…). Si hoy no hay sesión, es día de descanso → None.
    """
    training = plan.training_json or {}
    today_label = DAY_LABELS[today.weekday()].lower()
    for sess in training.get("sessions", []):
        if sess.get("day", "").strip().lower() == today_label:
            return _resolve_session(db, sess)
    return None


def build_training_sessions(db: Session, client: Client) -> list[dict]:
    """TODAS las sesiones del plan vigente, con nombres de ejercicio resueltos.

    Para el selector de sesión del portal (el cliente registra la que ha hecho,
    no solo la del día)."""
    period = active_period(db, client.id)
    plan = published_plan_for_period(db, period) if period else latest_published_plan(db, client.id)
    if plan is None:
        return []
    training = plan.training_json or {}
    return [_resolve_session(db, s) for s in training.get("sessions", [])]


def build_today_view(db: Session, client: Client, today: date) -> dict:
    period = active_period(db, client.id)
    plan = published_plan_for_period(db, period) if period else latest_published_plan(db, client.id)

    meals: list[dict] = []
    session = None
    already_logged = False

    if plan is not None:
        chosen = None
        if period is not None:
            log = db.scalar(
                select(DailyLog).where(
                    DailyLog.period_id == period.id, DailyLog.log_date == today
                )
            )
            if log is not None:
                already_logged = True
                chosen = log.chosen_options_json
        meals = _meals_for_today(plan, client, chosen)
        session = _session_for_today(db, plan, today)

    return {
        "date": today,
        "day_label": DAY_LABELS[today.weekday()],
        "period": period_info(period, today),
        "meals": meals,
        "session": session,
        "already_logged": already_logged,
    }


===== FILE: backend/app/services/scheduler.py =====

"""Scheduler de tareas programadas (APScheduler).

Un único job diario que ejecuta el mantenimiento de la máquina de estados y los
recordatorios. Corre en un BackgroundScheduler (hilo aparte) con la zona horaria
de settings.tz (Europe/Madrid por defecto).

El job abre su PROPIA sesión de base de datos (no comparte la de los requests).
`misfire_grace_time` y `coalesce` evitan ejecuciones acumuladas si el proceso
estuvo caído; `max_instances=1` impide solapamiento. Como el job es idempotente
(jobs.run_daily_maintenance), reejecutar el mismo día es seguro.

El arranque/parada se engancha al lifespan de FastAPI (main.py).
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.db import SessionLocal
from app.services.jobs import run_daily_maintenance

logger = logging.getLogger("scheduler")

DAILY_HOUR = 6   # 06:00 hora local: tras el cierre natural del día anterior
DAILY_MINUTE = 30

_scheduler: BackgroundScheduler | None = None


def _daily_job() -> None:
    db = SessionLocal()
    try:
        summary = run_daily_maintenance(db)
        logger.info("mantenimiento diario: %s", summary)
    except Exception:  # nunca tumbar el scheduler por un fallo puntual
        logger.exception("fallo en el mantenimiento diario")
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    sched = BackgroundScheduler(timezone=settings.tz)
    sched.add_job(
        _daily_job,
        trigger=CronTrigger(hour=DAILY_HOUR, minute=DAILY_MINUTE),
        id="daily_maintenance",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )
    sched.start()
    logger.info("scheduler iniciado (job diario %02d:%02d %s)", DAILY_HOUR, DAILY_MINUTE, settings.tz)
    _scheduler = sched
    return sched


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


===== FILE: backend/app/services/state_machine.py =====

"""Máquina de estados del cliente (G.2).

    onboarding → active → awaiting_feedback
              → (at_risk si +4 días sin cerrar tras fin de período
                 o <30% de registros a día 10)
              → review_pending → active …
    inactive (manual o >30 días sin actividad)

Diseño en dos capas:

1. `evaluate_transition(...)` — FUNCIÓN PURA: dado el estado actual y unos
   hechos (fechas, conteo de registros, si el período está cerrado…), decide
   el nuevo estado y el motivo. Sin DB, sin emails: 100% testable.

2. `apply_daily_transitions(db, ...)` — capa con efectos: lee los clientes,
   calcula los hechos desde la DB, llama a la función pura y, si hay cambio,
   persiste el estado, registra en audit_log y dispara el email/alerta que
   corresponda. Idempotente: ejecutarla dos veces el mismo día no duplica
   transiciones ni emails (los emails de aviso se controlan por kind+día).

Las transiciones que dependen de eventos (publicar plan → active; enviar
feedback → review_pending→active) las disparan los endpoints/pipeline, no el
scheduler; aquí vive solo lo que depende del paso del tiempo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

# Umbrales de G.2
AT_RISK_DAYS_AFTER_PERIOD_END = 4   # +4 días sin cerrar tras fin de período
LOG_RATIO_CHECK_DAY = 10            # a día 10 del período
LOG_RATIO_MIN = 0.30               # <30% de registros → at_risk
INACTIVE_DAYS = 30                 # >30 días sin actividad → inactive
REMINDER_DAY = 12                  # recordatorio si no registra (día 12)


@dataclass
class ClientFacts:
    """Hechos observables de un cliente, calculados desde la DB."""

    status: str
    has_active_period: bool = False
    period_start: date | None = None
    period_end: date | None = None
    period_closed: bool = False
    days_logged_in_period: int = 0
    last_activity_date: date | None = None  # último log o cierre


@dataclass
class TransitionDecision:
    new_status: str | None      # None = sin cambio
    reason: str = ""
    # Señales para la capa de efectos (no cambian estado pero disparan email):
    send_reminder: bool = False
    notify_coach_at_risk: bool = False


def _period_day(today: date, start: date) -> int:
    """Día del período (1-indexado). Día de inicio = día 1."""
    return (today - start).days + 1


def evaluate_transition(facts: ClientFacts, today: date) -> TransitionDecision:
    """Decide la transición por paso del tiempo. Función pura.

    Orden de prioridad: inactividad > at_risk > recordatorio. Estados terminales
    o gestionados por eventos (onboarding, review_pending) no transicionan aquí.
    """
    status = facts.status

    # inactive: cualquier estado activo con >30 días sin actividad
    if status in ("active", "awaiting_feedback", "at_risk"):
        if facts.last_activity_date is not None:
            idle = (today - facts.last_activity_date).days
            if idle > INACTIVE_DAYS:
                return TransitionDecision("inactive", f"{idle} días sin actividad")

    # onboarding no transiciona por tiempo (espera a publicar plan → evento)
    if status == "onboarding":
        return TransitionDecision(None)

    if status in ("active", "awaiting_feedback"):
        # ¿Período terminado y sin cerrar +4 días? → at_risk
        if facts.period_end is not None and not facts.period_closed:
            days_past_end = (today - facts.period_end).days
            if days_past_end >= AT_RISK_DAYS_AFTER_PERIOD_END:
                return TransitionDecision(
                    "at_risk",
                    f"{days_past_end} días sin cerrar el período",
                    notify_coach_at_risk=True,
                )

        # ¿Baja adherencia a día 10? → at_risk
        if facts.period_start is not None and not facts.period_closed:
            day = _period_day(today, facts.period_start)
            if day >= LOG_RATIO_CHECK_DAY:
                expected = day
                ratio = facts.days_logged_in_period / expected if expected else 0
                if ratio < LOG_RATIO_MIN:
                    return TransitionDecision(
                        "at_risk",
                        f"adherencia {ratio * 100:.0f}% (<{LOG_RATIO_MIN * 100:.0f}%) a día {day}",
                        notify_coach_at_risk=True,
                    )

        # Recordatorio día 12 si aún no ha registrado nada hoy/poco (no cambia estado)
        if (
            status == "active"
            and facts.period_start is not None
            and not facts.period_closed
            and _period_day(today, facts.period_start) == REMINDER_DAY
            and facts.days_logged_in_period < REMINDER_DAY // 2
        ):
            return TransitionDecision(None, "recordatorio día 12", send_reminder=True)

    return TransitionDecision(None)


# valid transitions for event-driven changes (validación defensiva)
VALID_TRANSITIONS = {
    "onboarding": {"active", "inactive"},
    "active": {"awaiting_feedback", "at_risk", "inactive"},
    "awaiting_feedback": {"review_pending", "at_risk", "active", "inactive"},
    "at_risk": {"review_pending", "active", "inactive"},
    "review_pending": {"active", "inactive"},
    "inactive": {"active"},  # reactivación manual
}


def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in VALID_TRANSITIONS.get(from_status, set())


===== FILE: backend/app/services/storage.py =====

"""Almacenamiento de archivos (PARTE I).

Estructura: {STORAGE_PATH}/clients/{id}/photos|documents|uploads/ y /brand/.
Fotos: validación de formato/tamaño y eliminación de EXIF (la geolocalización
de una foto corporal es dato sensible — se re-codifica la imagen sin metadatos).
"""

from __future__ import annotations

import io
import secrets
import shutil
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.config import settings

MAX_PHOTO_MB = 10
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
_EXT = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


def storage_root() -> Path:
    root = Path(settings.storage_path)
    root.mkdir(parents=True, exist_ok=True)
    return root


def brand_dir() -> Path:
    p = storage_root() / "brand"
    p.mkdir(parents=True, exist_ok=True)
    return p


def client_dir(client_id: int, sub: str | None = None) -> Path:
    p = storage_root() / "clients" / str(client_id)
    if sub:
        p = p / sub
    p.mkdir(parents=True, exist_ok=True)
    return p


class PhotoValidationError(ValueError):
    """Formato no soportado, archivo corrupto o demasiado grande."""


def save_photo(client_id: int, raw: bytes, sub: str = "photos") -> str:
    """Valida, elimina EXIF re-codificando y guarda. Devuelve la ruta relativa."""
    if len(raw) > MAX_PHOTO_MB * 1024 * 1024:
        raise PhotoValidationError(f"La foto supera {MAX_PHOTO_MB} MB")
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise PhotoValidationError("El archivo no es una imagen válida") from exc
    if img.format not in ALLOWED_FORMATS:
        raise PhotoValidationError("Formato no soportado (usa JPG, PNG o WebP)")

    fmt = img.format
    clean = Image.new(img.mode, img.size)
    clean.putdata(list(img.getdata()))  # píxeles sí, metadatos no
    if fmt == "JPEG" and clean.mode not in ("RGB", "L"):
        clean = clean.convert("RGB")

    name = f"{secrets.token_hex(12)}.{_EXT[fmt]}"
    dest = client_dir(client_id, sub) / name
    params = {"quality": 92} if fmt == "JPEG" else {}
    clean.save(dest, format=fmt, **params)
    return str(dest.relative_to(storage_root()))


MAX_DOC_MB = 25
_DOC_EXT = {"application/pdf": "pdf"}


class DocumentValidationError(ValueError):
    """Documento no soportado o demasiado grande."""


def save_document(client_id: int, raw: bytes, original_name: str) -> str:
    """Guarda un documento (PDF) del cliente. Devuelve la ruta relativa.

    Conserva un nombre legible (saneado) para que el coach lo reconozca, con un
    sufijo aleatorio que evita colisiones. Solo acepta PDF (la anamnesis oficial).
    """
    if len(raw) > MAX_DOC_MB * 1024 * 1024:
        raise DocumentValidationError(f"El documento supera {MAX_DOC_MB} MB")
    if raw[:5] != b"%PDF-":
        raise DocumentValidationError("El archivo no es un PDF válido")

    import re

    stem = re.sub(r"[^A-Za-z0-9._-]", "_", (original_name or "documento").rsplit(".", 1)[0])[:60]
    stem = stem.strip("_") or "documento"
    name = f"{stem}_{secrets.token_hex(4)}.pdf"
    dest = client_dir(client_id, "documents") / name
    dest.write_bytes(raw)
    return str(dest.relative_to(storage_root()))


def list_documents(client_id: int) -> list[dict]:
    """Lista la anamnesis subida del cliente (solo el PDF, más reciente primero).

    Se excluyen los archivos internos (sidecar `_anamnesis_analysis.json` y
    cualquier `_*`) y todo lo que no sea PDF: la web solo debe mostrar la
    anamnesis, y solo hay una por cliente (cada subida reemplaza la anterior).
    """
    folder = storage_root() / "clients" / str(client_id) / "documents"
    if not folder.exists():
        return []
    items = []
    for f in folder.iterdir():
        if f.is_file() and f.suffix.lower() == ".pdf" and not f.name.startswith("_"):
            st = f.stat()
            items.append({
                "name": f.name,
                "size_kb": round(st.st_size / 1024),
                "uploaded_at": st.st_mtime,
                "rel_path": str(f.relative_to(storage_root())),
            })
    return sorted(items, key=lambda x: x["uploaded_at"], reverse=True)


def save_brand_logo(raw: bytes, filename_hint: str) -> str:
    if len(raw) > 5 * 1024 * 1024:
        raise PhotoValidationError("El logo supera 5 MB")
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise PhotoValidationError("El archivo no es una imagen válida") from exc
    if img.format not in ALLOWED_FORMATS:
        raise PhotoValidationError("Formato no soportado (usa JPG, PNG o WebP)")
    dest = brand_dir() / f"logo.{_EXT[img.format]}"
    img.save(dest, format=img.format)
    return str(dest.relative_to(storage_root()))


def abs_path(rel: str) -> Path:
    """Ruta absoluta segura dentro del storage (evita path traversal)."""
    p = (storage_root() / rel).resolve()
    if not str(p).startswith(str(storage_root().resolve())):
        raise PhotoValidationError("Ruta fuera del almacenamiento")
    return p


def delete_client_tree(client_id: int) -> None:
    """Supresión RGPD: borra todos los archivos del cliente."""
    p = storage_root() / "clients" / str(client_id)
    if p.exists():
        shutil.rmtree(p)


===== FILE: backend/app/services/swap.py =====

"""Swap de ejercicios — solo coach, desde el plan publicado (F.5).

Dos operaciones:

1. `propose_alternatives(...)` — dado un ejercicio del plan y el cliente,
   devuelve 2–3 alternativas de la biblioteca con el MISMO patrón de movimiento
   y músculo primario, filtradas por equipamiento, nivel, lesiones y exclusiones
   (filtro determinista de guardrails). No usa IA: es selección + orden por
   similitud de estímulo (mismo patrón > mismos secundarios > equipamiento).

2. `apply_swap(...)` — sustituye el ejercicio en el plan heredando
   series/reps/RIR/descansos, ajustando start_weight_hint proporcionalmente,
   regenerando los cues desde la biblioteca, recalculando el volumen del grupo y
   revalidando guardrails. Registra el motivo en audit_log y, si es permanente,
   lo añade a las exclusiones del cliente. Crea una nueva VERSIÓN del plan
   (borrador) para que el coach la republique.

Mantener esto fuera del router permite testearlo de forma aislada.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, Exercise, Plan
from app.services import guardrails as gr


@dataclass
class Alternative:
    exercise_id: int
    name: str
    movement_pattern: str
    muscle_primary: str
    equipment: list[str]
    similarity: int  # mayor = más parecido


def _client_equipment(client: Client) -> set[str]:
    return set(client.equipment or [])


def _client_excluded(client: Client) -> set[int]:
    return set(client.excluded_exercise_ids or [])


def _client_contraindications(client: Client) -> set[str]:
    # La anamnesis guarda lesiones como texto libre (injuries_notes); no hay un
    # conjunto estructurado de contraindicaciones articulares por cliente. El
    # filtro por patrón/músculo/equipamiento/nivel ya acota fuerte; aquí
    # devolvemos vacío y dejamos que el coach valide el caso clínico.
    return set()


def propose_alternatives(
    db: Session, client: Client, current_exercise_id: int, limit: int = 3
) -> list[Alternative]:
    """Alternativas válidas para sustituir un ejercicio (F.5.1)."""
    current = db.get(Exercise, current_exercise_id)
    if current is None:
        return []

    level_max = {"beginner": 1, "intermediate": 2, "advanced": 3}.get(client.level or "intermediate", 2)
    equipment = _client_equipment(client)
    excluded = _client_excluded(client) | {current_exercise_id}
    contra = _client_contraindications(client)

    # Candidatos del mismo patrón de movimiento (requisito duro F.5.1)
    candidates = db.scalars(
        select(Exercise).where(
            Exercise.movement_pattern == current.movement_pattern,
            Exercise.muscle_primary == current.muscle_primary,
            Exercise.archived.is_(False),
        )
    ).all()

    # Filtro determinista de guardrails (equipamiento, nivel, lesiones, exclusiones)
    as_dicts = [{
        "id": e.id, "movement_pattern": e.movement_pattern, "muscle_primary": e.muscle_primary,
        "muscle_secondary": e.muscle_secondary, "equipment": e.equipment,
        "contraindications": e.contraindications, "level_min": e.level_min,
        "archived": e.archived, "canonical_name": e.canonical_name,
    } for e in candidates]

    valid = gr.filter_exercises_for_client(
        as_dicts, client_contraindications=contra, excluded_ids=excluded,
        equipment_available=equipment, level_max=level_max,
        training_place=client.training_place or "gym",
    )

    # Orden por similitud de estímulo: comparte músculos secundarios + equipamiento
    cur_sec = set(current.muscle_secondary or [])
    cur_eq = set(current.equipment or [])
    out: list[Alternative] = []
    for e in valid:
        sec_overlap = len(cur_sec & set(e.get("muscle_secondary") or []))
        eq_overlap = len(cur_eq & set(e.get("equipment") or []))
        out.append(Alternative(
            exercise_id=e["id"], name=e["canonical_name"],
            movement_pattern=e["movement_pattern"], muscle_primary=e["muscle_primary"],
            equipment=e.get("equipment") or [],
            similarity=sec_overlap * 2 + eq_overlap,
        ))
    out.sort(key=lambda a: a.similarity, reverse=True)
    return out[:limit]


@dataclass
class SwapResult:
    new_plan_id: int
    new_version: int
    group_volume_after: float
    guardrail_flags: list[str]


def apply_swap(
    db: Session,
    *,
    client: Client,
    plan: Plan,
    session_index: int,
    old_exercise_id: int,
    new_exercise_id: int,
    permanent: bool,
    reason: str,
) -> SwapResult:
    """Sustituye un ejercicio creando una nueva versión del plan (borrador).

    Hereda series/reps/RIR/descansos, ajusta el peso orientativo
    proporcionalmente (heurística por nivel del ejercicio), regenera cues desde
    la biblioteca y recalcula/valida el volumen. F.5.2–F.5.4.
    """
    from app.services.audit import log_event

    new_ex = db.get(Exercise, new_exercise_id)
    if new_ex is None:
        raise ValueError("Ejercicio de destino no existe")

    training = copy.deepcopy(plan.training_json or {})
    sessions = training.get("sessions", [])
    if session_index >= len(sessions):
        raise ValueError("Sesión fuera de rango")

    exercises = sessions[session_index].get("exercises", [])
    target = next((e for e in exercises if e["exercise_id"] == old_exercise_id), None)
    if target is None:
        raise ValueError("El ejercicio a sustituir no está en esa sesión")

    # Hereda parámetros; sustituye id y cues
    target["exercise_id"] = new_exercise_id
    target["technique_cue"] = (new_ex.technique_notes or "")[:160]
    target["biomech_cue"] = (new_ex.biomechanics_notes or "")[:160]
    # Ajuste proporcional del peso orientativo por nivel del ejercicio
    old_ex = db.get(Exercise, old_exercise_id)
    if target.get("start_weight_hint_kg") and old_ex:
        factor = 1.0
        if old_ex.level_min and new_ex.level_min:
            factor = old_ex.level_min / max(1, new_ex.level_min)
        target["start_weight_hint_kg"] = round(target["start_weight_hint_kg"] * factor, 1)

    # Nueva versión (borrador) del plan
    last = db.scalar(
        select(Plan).where(Plan.client_id == client.id, Plan.month_index == plan.month_index)
        .order_by(Plan.version.desc()).limit(1)
    )
    new_plan = Plan(
        client_id=client.id, month_index=plan.month_index, version=last.version + 1,
        status="draft", nutrition_json=plan.nutrition_json, training_json=training,
        education_json=plan.education_json, generated_by="swap",
    )
    db.add(new_plan)
    db.flush()

    # Recalcula volumen del grupo y valida guardrails
    lib = {e.id: {"canonical_name": e.canonical_name, "muscle_primary": e.muscle_primary,
                  "contraindications": e.contraindications}
           for e in db.scalars(select(Exercise))}
    report = gr.check_training(
        training, training_days_declared=client.training_days or len(sessions),
        session_max_min=client.session_max_min or 90,
        client_contraindications=_client_contraindications(client),
        exercise_lookup=lib,
    )
    new_plan.guardrail_flags = report.as_flags()

    group_volume = sum(
        ex["sets"] for s in sessions for ex in s.get("exercises", [])
        if lib.get(ex["exercise_id"], {}).get("muscle_primary") == new_ex.muscle_primary
    )

    # Exclusión permanente
    if permanent:
        excluded = list(_client_excluded(client))
        if old_exercise_id not in excluded:
            excluded.append(old_exercise_id)
            client.excluded_exercise_ids = excluded

    log_event(db, "plan", new_plan.id, "exercise_swapped", {
        "old_exercise_id": old_exercise_id, "new_exercise_id": new_exercise_id,
        "permanent": permanent, "reason": reason, "from_plan": plan.id,
    })
    db.commit()
    return SwapResult(
        new_plan_id=new_plan.id, new_version=new_plan.version,
        group_volume_after=group_volume, guardrail_flags=new_plan.guardrail_flags or [],
    )
