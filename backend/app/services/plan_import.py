"""Importar una PLANIFICACIÓN desde CUALQUIER documento ajeno.

El Word de ida y vuelta solo entiende el documento que generamos nosotros (y
rechaza todo lo demás, con razón: es determinista). Pero al coach le llegan
planes hechos fuera: una dieta en Excel, la rutina que traía el cliente de otro
entrenador en PDF, una foto de una hoja con las comidas, un Word de otra
época. Este módulo los convierte en un BORRADOR del sistema por el mismo
camino que «copiar de la biblioteca»:

1. La IA TRANSCRIBE el documento (`PlanDocumentExtraction`): comidas y
   alimentos con sus cantidades tal cual, ejercicios con sus series/repes/RIR/
   descansos, suplementos, reglas, progresión. No calcula ni completa.
2. El backend construye los JSON del plan con SUS reglas:
   · kcal y macros salen del CONTRATO del cliente (`metrics`), nunca del
     documento — si el documento declara otras cifras, se avisa.
   · los ejercicios se resuelven contra la BIBLIOTECA (canónico + alias +
     palabras clave, un único candidato); lo que no está, se avisa y no entra.
   · los alimentos se resuelven contra la BASE (`foods`) y los macros de cada
     plato se RECALCULAN (Atwater 4/4/9, half-up); sin gramos → se conserva la
     cantidad escrita y se avisa para completarla en el editor.
3. `copiar_a_cliente` crea el borrador: reescala al contrato, completa la mitad
   que falte con la base del sistema, pasa los avisos de seguridad (alérgenos,
   patrón dietético, lesiones) y lo deja como «copiado de …, revísalo».

La IA no calcula; el coach confirma antes de que exista el borrador.
"""
from __future__ import annotations

import copy as _copy
import re
import unicodedata
from types import SimpleNamespace

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, Exercise


# ------------------------------------------------------------- esquema IA ----

def _lista(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [x.strip(" -•\t") for x in v.splitlines() if x.strip(" -•\t")]
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, dict):
        return [f"{k}: {val}" for k, val in v.items()]
    return [str(v)]


def _num(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"-?\d+(?:[.,]\d+)?", str(v))
    return float(m.group(0).replace(",", ".")) if m else None


class DocFood(BaseModel):
    food: str
    amount: str | None = Field(None, description="Cantidad TAL CUAL está escrita ('120 g', '1 taza', '2 huevos')")
    grams: float | None = Field(None, description="Gramos SOLO si el documento los da en gramos")
    household: str | None = Field(None, description="Medida casera si la hay")

    _v_g = field_validator("grams", mode="before")(lambda cls, v: _num(v))


class DocMeal(BaseModel):
    name: str
    time: str | None = None
    day: str | None = Field(None, description="Solo en menús cerrados por día (lunes…domingo)")
    foods: list[DocFood] = Field(default_factory=list)
    notes: str | None = None


class DocSupplement(BaseModel):
    name: str
    dose: str | None = None
    timing: str | None = None


class DocNutrition(BaseModel):
    declared_kcal: float | None = None
    declared_protein_g: float | None = None
    declared_carbs_g: float | None = None
    declared_fat_g: float | None = None
    meals: list[DocMeal] = Field(default_factory=list)
    supplements: list[DocSupplement] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list, description="Reglas, equivalencias, consejos tal cual")
    notes: list[str] = Field(default_factory=list)

    _v_n = field_validator("declared_kcal", "declared_protein_g", "declared_carbs_g",
                           "declared_fat_g", mode="before")(lambda cls, v: _num(v))
    _v_l = field_validator("rules", "notes", mode="before")(lambda cls, v: _lista(v))


class DocExercise(BaseModel):
    name: str
    sets: int | None = None
    reps: str | None = None
    rir: str | None = None
    rest_sec: int | None = None
    tempo: str | None = None
    weight_hint_kg: float | None = None
    notes: str | None = None

    @field_validator("sets", mode="before")
    @classmethod
    def _entero(cls, v):
        n = _num(v)
        return int(round(n)) if n is not None else None

    @field_validator("rest_sec", mode="before")
    @classmethod
    def _descanso(cls, v):
        """«2 min», «90 s», «1'30», 2 (minutos) → segundos. Misma regla que el
        Word de ida y vuelta: sin unidad y por debajo de 15, son minutos."""
        if v is None:
            return None
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            n = float(v)
            return int(round(n * 60 if n < 15 else n))
        from app.services.word_import import _parse_rest

        return _parse_rest(str(v))

    @field_validator("reps", "rir", "tempo", mode="before")
    @classmethod
    def _txt(cls, v):
        return None if v is None else str(v).strip() or None

    _v_w = field_validator("weight_hint_kg", mode="before")(lambda cls, v: _num(v))


class DocSession(BaseModel):
    day: str | None = None
    name: str | None = None
    exercises: list[DocExercise] = Field(default_factory=list)
    warmup: str | None = None
    cooldown: str | None = None


class DocCardioSession(BaseModel):
    type: str | None = None
    minutes: int | None = None
    times_per_week: int | None = None

    @field_validator("minutes", "times_per_week", mode="before")
    @classmethod
    def _entero(cls, v):
        n = _num(v)
        return int(round(n)) if n is not None else None


class DocCardio(BaseModel):
    daily_steps: int | None = None
    sessions: list[DocCardioSession] = Field(default_factory=list)

    @field_validator("daily_steps", mode="before")
    @classmethod
    def _entero(cls, v):
        n = _num(v)
        return int(round(n)) if n is not None else None


class DocTraining(BaseModel):
    split_name: str | None = None
    sessions: list[DocSession] = Field(default_factory=list)
    progression: list[str] = Field(default_factory=list)
    cardio: DocCardio | None = None
    deload: str | None = None

    _v_l = field_validator("progression", mode="before")(lambda cls, v: _lista(v))


class PlanDocumentExtraction(BaseModel):
    document_kind: str | None = Field(None, description="plan_dieta|plan_entreno|plan_completo|otro")
    nutrition: DocNutrition | None = None
    training: DocTraining | None = None
    inventory: list[str] = Field(default_factory=list, description="Qué contiene el documento, bloque a bloque")
    unmapped: list[str] = Field(default_factory=list, description="Lo relevante que no cupo en el esquema")
    warnings: list[str] = Field(default_factory=list, description="Dudas de lectura (ilegible, ambiguo)")

    _v_l = field_validator("inventory", "unmapped", "warnings", mode="before")(lambda cls, v: _lista(v))


_SYSTEM = """Eres un dietista-entrenador experto TRANSCRIBIENDO una planificación ajena (dieta y/o \
entrenamiento) para importarla en un sistema. El documento puede tener cualquier forma: PDF de \
otro entrenador, Excel con las comidas, foto de una hoja escrita, Word, texto. TRANSCRIBE lo que \
hay, fiel y completo. NO calcules, NO completes lo que falte, NO inventes cantidades.

DIETA (nutrition):
- declared_*: kcal y macros SOLO si el documento los declara (tal cual). No los calcules.
- meals: cada comida con su nombre, hora si consta, y sus alimentos: `food` (nombre limpio, \
sin cantidades), `amount` (la cantidad TAL CUAL está escrita: "120 g", "1 taza", "2 huevos"), \
`grams` SOLO si está en gramos, `household` si hay medida casera. Si hay VARIAS OPCIONES para \
una comida, crea una comida por opción con el mismo nombre y "(opción 2)". Si es un MENÚ POR \
DÍAS (lunes…domingo), rellena `day` en cada comida.
- supplements: nombre, dosis y momento tal cual. rules: reglas, equivalencias, consejos.
ENTRENAMIENTO (training):
- sessions: cada sesión con su día si consta (lunes…domingo o "Día 1"), nombre, y sus \
ejercicios: `name` (el nombre del ejercicio tal cual, sin series), `sets`, `reps` (texto: \
"8-12", "AMRAP"), `rir` (texto: "2", "1-2"), `rest_sec` (en segundos: "2 min" → 120), `tempo`, \
`weight_hint_kg` si consta, `notes` (técnica, sustituciones). Calentamiento y vuelta a la \
calma si constan.
- progression: cómo dice progresar. cardio: pasos diarios y sesiones si constan. deload: si consta.
CONSTANCIA: inventory (qué contiene el documento, bloque a bloque), unmapped (lo relevante que \
no cabe en el esquema), warnings (lo ilegible o ambiguo). Devuelve SOLO el JSON del esquema."""


def extract_plan_from_document(documento, ai) -> PlanDocumentExtraction:
    from app.config import settings

    user = (f"Transcribe la planificación del documento adjunto («{documento.nombre}», "
            f"{documento.descripcion}) ENTERA en el JSON del esquema. Todas las comidas y todos "
            "los ejercicios, con sus cantidades tal cual. No calcules nada.")
    return ai.read_document_json(
        model=settings.model_heavy, system=_SYSTEM, user=user, documento=documento,
        schema=PlanDocumentExtraction, temperature=0, max_tokens=12000,
    )


# ------------------------------------------------------------- utilidades ----

def _norm(s: str | None) -> str:
    s = (s or "").strip().lower()
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


_DIAS = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
_DIA_SINONIMOS = {
    "lunes": "lunes", "monday": "lunes", "l": "lunes", "lun": "lunes",
    "martes": "martes", "tuesday": "martes", "m": "martes", "mar": "martes",
    "miercoles": "miercoles", "wednesday": "miercoles", "x": "miercoles", "mie": "miercoles", "mier": "miercoles",
    "jueves": "jueves", "thursday": "jueves", "j": "jueves", "jue": "jueves",
    "viernes": "viernes", "friday": "viernes", "v": "viernes", "vie": "viernes",
    "sabado": "sabado", "saturday": "sabado", "s": "sabado", "sab": "sabado",
    "domingo": "domingo", "sunday": "domingo", "d": "domingo", "dom": "domingo",
}
_REPARTO = {
    1: ("lunes",), 2: ("lunes", "jueves"), 3: ("lunes", "miercoles", "viernes"),
    4: ("lunes", "martes", "jueves", "viernes"), 5: ("lunes", "martes", "miercoles", "jueves", "viernes"),
    6: ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado"),
    7: _DIAS,
}
_NOMBRE_DIA = {"lunes": "Lunes", "martes": "Martes", "miercoles": "Miércoles", "jueves": "Jueves",
               "viernes": "Viernes", "sabado": "Sábado", "domingo": "Domingo"}


def _dia_slug(texto: str | None) -> str | None:
    t = _norm(texto)
    if not t:
        return None
    for tok in re.split(r"[\s,;:/().-]+", t):
        if tok in _DIA_SINONIMOS:
            return _DIA_SINONIMOS[tok]
    for d in _DIAS:
        if d in t:
            return d
    return None


def _dia_sesion(texto: str | None, indice: int, total: int) -> str:
    slug = _dia_slug(texto)
    if slug is None:
        reparto = _REPARTO.get(max(1, min(7, total)), _DIAS)
        slug = reparto[min(indice, len(reparto) - 1)]
    return _NOMBRE_DIA[slug]


def resolver_ejercicio(nombre: str, nombre_a_id: dict[str, int],
                       id_a_nombre: dict[int, str]) -> tuple[int | None, str | None]:
    """(id, aviso). Exacto por canónico/alias; si no, palabras clave con un
    ÚNICO candidato (se acepta y se dice); varios → ambiguo; ninguno → None."""
    from app.services.word_import import _fuzzy_exercise

    clave = _norm(nombre)
    if not clave:
        return None, None
    eid = nombre_a_id.get(clave)
    if eid is not None:
        return eid, None
    hits = _fuzzy_exercise(clave, nombre_a_id)
    if len(hits) == 1:
        eid = next(iter(hits))
        return eid, f"«{nombre}» se ha tomado como «{id_a_nombre.get(eid, eid)}»"
    if len(hits) > 1:
        nombres = sorted({id_a_nombre.get(i, str(i)) for i in hits})[:4]
        return None, f"«{nombre}» es ambiguo en la biblioteca ({', '.join(nombres)}): elígelo en el editor"
    return None, f"«{nombre}» no está en la biblioteca: añádelo en Recursos o cámbialo en el editor"


_RE_GRAMOS = re.compile(r"(?P<n>\d+(?:[.,]\d+)?)\s*(?P<u>g|gr|grs|gramos|ml|mililitros)\b", re.I)


def _gramos_de(f: DocFood) -> float | None:
    if f.grams and f.grams > 0:
        return float(f.grams)
    for txt in (f.amount, f.household):
        m = _RE_GRAMOS.search(txt or "")
        if m:
            return float(m.group("n").replace(",", "."))
    return None


_HORA_POR_NOMBRE = (
    ("desayun", "08:00"), ("media manana", "11:00"), ("almuerzo", "11:00"),
    ("tentempie", "11:00"), ("comida", "14:00"), ("mediodia", "14:00"),
    ("merienda", "17:30"), ("pre entreno", "17:30"), ("post entreno", "19:30"),
    ("cena", "21:00"), ("recena", "23:00"), ("antes de dormir", "23:00"),
    ("pre cama", "23:00"),
)
_HORAS_REPARTO = {
    1: ("14:00",), 2: ("14:00", "21:00"), 3: ("08:00", "14:00", "21:00"),
    4: ("08:00", "14:00", "17:30", "21:00"), 5: ("08:00", "11:00", "14:00", "17:30", "21:00"),
    6: ("08:00", "11:00", "14:00", "17:30", "21:00", "23:00"),
}


def _hora_de_toma(nombre: str, hora: str | None, indice: int, total: int) -> str:
    """La hora que trae el documento («8:00» → «08:00»); si no trae, la
    habitual para ESE nombre de toma (cena a las 21:00, no a la hora que le
    toque por posición); y si el nombre no dice nada, un reparto por número."""
    m = re.match(r"^\s*(\d{1,2})[:.h](\d{2})?", hora or "")
    if m:
        h, mi = int(m.group(1)), int(m.group(2) or 0)
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return f"{h:02d}:{mi:02d}"
    n = _norm(nombre)
    for clave, h in _HORA_POR_NOMBRE:
        if clave in n:
            return h
    reparto = _HORAS_REPARTO.get(max(1, min(6, total)), _HORAS_REPARTO[4])
    return reparto[min(indice, len(reparto) - 1)]


# ------------------------------------------------------------ construir ----

# Opciones por toma que admite el contrato (`FlexibleSlot`): el banco generado
# usa 3, pero si el documento trae 4 no hay motivo para tirar la cuarta.
MAX_OPCIONES = 4


def _semana_completa(dias: dict[str, list[dict]], avisos: list[str]) -> dict[str, list[dict]]:
    """Un menú CERRADO tiene que cubrir los 7 días: si el documento solo trae
    unos cuantos, el portal se quedaba sin comidas el resto de la semana (y el
    banco ni siquiera cumplía el contrato del sistema). Los días que faltan se
    completan ROTANDO los que hay, y se dice cuáles son copia."""
    presentes = [d for d in _DIAS if d in dias]
    if not presentes or len(presentes) == 7:
        return dias
    copiados = []
    i = 0
    for d in _DIAS:
        if d in dias:
            continue
        origen = presentes[i % len(presentes)]
        i += 1
        dias[d] = [{"slot": m["slot"], "dish": _copy.deepcopy(m["dish"])} for m in dias[origen]]
        copiados.append(f"{d} (como {origen})")
    avisos.append("El menú del documento solo cubría "
                  f"{len(presentes)} de los 7 días: los demás se han completado repitiendo los "
                  "que hay — " + ", ".join(copiados) + ". Cámbialos en el editor si hace falta.")
    return dias


_PROGRESION_DEFECTO = [
    {"week": 1, "intent": "Base", "load_pct": 100.0, "rir_target": "2",
     "volume_note": "Asienta técnica y cargas de referencia."},
    {"week": 2, "intent": "Progresión", "load_pct": 102.5, "rir_target": "1-2",
     "volume_note": "Sube peso o repeticiones donde el RIR lo permita."},
    {"week": 3, "intent": "Pico", "load_pct": 105.0, "rir_target": "1",
     "volume_note": "Semana más exigente del ciclo."},
    {"week": 4, "intent": "Deload", "load_pct": 60.0, "rir_target": "3-4",
     "volume_note": "Mitad de series: recuperar para el siguiente ciclo."},
]


def _cue(text: str | None, default: str) -> str:
    t = (text or "").strip().split("\n")[0]
    return (t[:110] or default)


def build_training(db: Session, client: Client, doc: DocTraining, avisos: list[str],
                   resumen: dict) -> dict | None:
    from app.services.word_import import _exercise_maps

    id_a_nombre, nombre_a_id = _exercise_maps(db, None)
    lib = {e.id: e for e in db.scalars(select(Exercise))}
    sesiones = []
    sin_lib: list[str] = []
    tomados: list[str] = []
    n = len([s for s in doc.sessions if s.exercises]) or len(doc.sessions)
    for i, ds in enumerate(doc.sessions):
        exs = []
        for de in ds.exercises:
            eid, aviso = resolver_ejercicio(de.name, nombre_a_id, id_a_nombre)
            if eid is None:
                if aviso:
                    sin_lib.append(aviso)
                continue
            if aviso:
                tomados.append(aviso)
            ex = lib.get(eid)
            exs.append({
                "exercise_id": eid,
                "sets": max(1, min(10, de.sets or 3)),
                "rep_range": de.reps or "8-12",
                "rir": de.rir or "2",
                "tempo": de.tempo,
                "rest_sec": max(15, min(600, de.rest_sec or 90)),
                "start_weight_hint_kg": de.weight_hint_kg if (de.weight_hint_kg or 0) >= 0 else None,
                "progression_rule": ("Doble progresión: cuando completes todas las series en el "
                                     "tope del rango con el RIR indicado, sube el peso la siguiente sesión."),
                "technique_cue": _cue(getattr(ex, "technique_notes", None),
                                      "Técnica controlada y rango completo."),
                "biomech_cue": _cue(getattr(ex, "biomechanics_notes", None),
                                    "Controla la fase excéntrica (2-3 s)."),
                "coach_notes": (de.notes or None),
            })
        if not exs:
            if ds.exercises:
                avisos.append(f"La sesión «{ds.name or i + 1}» se queda fuera: ninguno de sus "
                              "ejercicios está en la biblioteca.")
            continue
        sesiones.append({
            "day": _dia_sesion(ds.day, len(sesiones), n),
            "name": (ds.name or f"Sesión {len(sesiones) + 1}")[:60],
            "warmup": (ds.warmup or "5-8 min de cardio suave + 2 series de aproximación en los básicos del día.")[:300],
            "exercises": exs,
            "cooldown": (ds.cooldown or "3-5 min de vuelta a la calma y estiramientos suaves.")[:200],
        })
    resumen["sesiones"] = len(sesiones)
    resumen["ejercicios_reconocidos"] = sum(len(s["exercises"]) for s in sesiones)
    resumen["ejercicios_sin_biblioteca"] = sin_lib
    resumen["ejercicios_asimilados"] = tomados
    cardio_doc = doc.cardio or DocCardio()
    avisos.extend(sin_lib[:12])
    if len(sin_lib) > 12:
        avisos.append(f"… y {len(sin_lib) - 12} ejercicios más sin biblioteca.")
    avisos.extend(tomados[:8])
    if not sesiones:
        return None
    pasos = {"sedentary": 7000, "light": 8000, "active": 9000,
             "very_active": 10000}.get(client.daily_activity_level or "", 8000)
    cardio_ses = []
    for cs in cardio_doc.sessions:
        tipo = "hiit" if "hiit" in _norm(cs.type) or "interval" in _norm(cs.type) else "liss"
        if cs.minutes:
            cardio_ses.append({"type": tipo, "minutes": max(5, min(120, cs.minutes)),
                               "times_per_week": max(1, min(7, cs.times_per_week or 2)),
                               "notes": None})
    progresion_txt = " ".join(doc.progression)[:400]
    # Lo que el sistema NO puede representar tal cual se dice, no se traga en
    # silencio: el coach tiene que saber qué se ha sustituido por lo estándar.
    if doc.progression:
        avisos.append("La progresión que describe el documento no encaja en el esquema de 4 "
                      "semanas del sistema: queda la estándar (y su texto, en el porqué de la "
                      "rutina). Ajústala en el editor si hace falta.")
    sin_minutos = [cs for cs in cardio_doc.sessions if not cs.minutes]
    if sin_minutos:
        avisos.append(f"{len(sin_minutos)} sesión(es) de cardio del documento no dicen cuántos "
                      "minutos duran: no se han importado.")
    if doc.deload is None:
        avisos.append("El documento no pauta descarga: se ha puesto la del sistema (semana 4).")
    training = {
        "split_name": (doc.split_name or f"Rutina de {len(sesiones)} días")[:80],
        "split_rationale": ("Rutina importada de un documento externo y adaptada al sistema: "
                            + (progresion_txt or "progresión por doble progresión semana a semana."))[:600],
        "weekly_progression": _PROGRESION_DEFECTO,
        "sessions": sesiones,
        "cardio": {"daily_steps": max(0, min(30000, cardio_doc.daily_steps or pasos)),
                   "sessions": cardio_ses},
        "deload_instructions": (doc.deload or
                                "Semana 4: mitad de series con el mismo peso; técnica perfecta.")[:400],
    }
    try:
        from app.schemas.ai import TrainingCore

        training = TrainingCore.model_validate(training).model_dump()
    except ValidationError as exc:
        avisos.append("El entrenamiento importado no pasó el contrato del sistema: "
                      + str(exc).splitlines()[0][:160])
        return None
    # MISMO Revisor determinista que el entreno generado: volumen por grupo,
    # patrones, duración de sesión y ejercicios contraindicados por sus
    # lesiones. Sus violaciones se devuelven con el prefijo que RETIENE el
    # borrador (nada llega al cliente sin que el coach las resuelva).
    try:
        from app.services import injuries
        from app.services.guardrails import check_training

        rep = check_training(
            training,
            exercise_lookup={e.id: {"muscle_primary": e.muscle_primary,
                                    "muscle_secondary": list(e.muscle_secondary or []),
                                    "movement_pattern": e.movement_pattern,
                                    "contraindications": list(e.contraindications or [])}
                             for e in lib.values()},
            client_contraindications=injuries.injury_contra_tags(
                client.injuries_notes, client.medical_notes),
            training_days_declared=client.training_days,
            session_max_min=client.session_max_min,
        )
        resumen["violaciones_entreno"] = list(rep.violations)
        avisos.extend(f"violation: {v}" for v in rep.violations)
        avisos.extend(rep.warnings[:6])
    except Exception:  # noqa: BLE001 — el chequeo nunca tumba la importación
        pass
    if any(e.get("start_weight_hint_kg") for s_ in training["sessions"] for e in s_["exercises"]):
        avisos.append("Las cargas iniciales vienen del documento, no del historial de fuerza de "
                      "este cliente: compruébalas antes de activar.")
    return training


def _opcion_desde(dm: DocMeal, target: dict, food_map: dict, avisos: list[str],
                  resumen: dict, letra: str = "A", foods_by_id: dict | None = None) -> dict | None:
    from app.services.word_import import _ingredientes_aplicables, _macros_recalculados

    parsed = []
    for f in dm.foods:
        if not (f.food or "").strip():
            continue
        g = _gramos_de(f)
        casera = (f.household or "").strip() or ((f.amount or "").strip() if g is None else
                                                 (f.amount or "").strip())
        parsed.append({"food": f.food.strip(), "grams": g, "household": casera})
    if not parsed:
        return None
    ings = _ingredientes_aplicables(parsed, food_map)
    sin_base = [i["food"] for i in ings if i.get("food_id") is None]
    sin_gramos = [i["food"] for i in ings if not i.get("grams")]
    resumen.setdefault("alimentos_sin_base", []).extend(sin_base)
    resumen.setdefault("alimentos_sin_gramos", []).extend(sin_gramos)
    resumen["alimentos_reconocidos"] = resumen.get("alimentos_reconocidos", 0) + (len(ings) - len(sin_base))
    macros = _macros_recalculados(parsed, food_map) if not sin_base and not sin_gramos else None
    ajustada = False
    if macros is None and not sin_base and foods_by_id:
        # Faltan GRAMOS pero todos los alimentos están en la base: los pone el
        # BACKEND con el solver de porciones, que es el camino oficial del
        # sistema (la IA elige alimentos, el backend fija los gramos). Antes se
        # copiaba el objetivo de la toma como si fueran los macros del plato:
        # números que no salían de ningún alimento y que además arrastraban el
        # reescalado de las opciones buenas de esa misma toma.
        from app.services.portion_solver import snap_option_ingredients

        try:
            snap = snap_option_ingredients(ings, target, foods_by_id)
        except Exception:  # noqa: BLE001 — el solver nunca tumba la importación
            snap = None
        if snap is not None:
            ings, macros = snap[0], snap[1]
            ajustada = True
    if macros is None:
        # No se puede saber qué lleva el plato (algún alimento no está en la
        # base): NO se inventan sus macros ni entra en el banco — la toma se
        # queda libre para el banco de reserva del sistema, que sí es seguro.
        # Se avisa con nombre y apellidos para que el coach lo añada o lo
        # escriba en el editor.
        resumen.setdefault("platos_descartados", []).append(
            f"{dm.name or 'plato'} ({', '.join(sin_base[:3])})")
        return None
    titulo = (dm.name or ", ".join(i["food"] for i in ings[:3]))[:80]
    if ajustada:
        resumen.setdefault("platos_ajustados", []).append(titulo)
    return {
        "key": letra, "title": titulo, "ingredients": ings,
        "prep": (dm.notes or "")[:400], "prep_minutes": 0, "macros": macros,
        "tags": ["importado"] + (["gramos_del_sistema"] if ajustada else []),
    }


def build_nutrition(db: Session, client: Client, doc: DocNutrition, avisos: list[str],
                    resumen: dict) -> dict | None:
    from app.services.plan_library import _contrato_del_destino
    from app.services.plan_scaffold import build_nutrition as scaffold_nutrition
    from app.services.word_import import _food_map

    weight, et, mp = _contrato_del_destino(db, client)
    resumen["kcal_contrato"] = float(mp.kcal)
    resumen["kcal_documento"] = doc.declared_kcal
    if doc.declared_kcal and abs(float(doc.declared_kcal) - float(mp.kcal)) > 25:
        avisos.append(
            f"El documento declara {doc.declared_kcal:.0f} kcal; las cifras de este cliente salen "
            f"de su ficha ({mp.kcal:.0f} kcal) y el borrador usa las suyas. Si quieres respetar el "
            "documento, ajusta las kcal en el editor.")

    sueltas = [m for m in doc.meals if not _dia_slug(m.day)]
    por_dia = [m for m in doc.meals if _dia_slug(m.day)]
    # Tomas: las del documento (nombres/horas) si las hay; si no, las del cliente.
    nombres_vistos: list[tuple[str, str | None]] = []
    for m in (sueltas or por_dia):
        base = re.sub(r"\s*\(opci[oó]n\s*\d+\)\s*$", "", m.name or "", flags=re.I).strip() or "Comida"
        if not any(_norm(base) == _norm(n) for n, _t in nombres_vistos):
            nombres_vistos.append((base, m.time))
    if nombres_vistos:
        schedule = [{"slot": i + 1, "name": n[:40], "time": _hora_de_toma(n, t, i, len(nombres_vistos))}
                    for i, (n, t) in enumerate(nombres_vistos[:6])]
        pseudo = SimpleNamespace(meal_schedule=schedule, meals_per_day=len(schedule))
    else:
        pseudo = SimpleNamespace(meal_schedule=client.meal_schedule, meals_per_day=client.meals_per_day)
    nut = scaffold_nutrition(pseudo, et, mp)
    nut["supplements"] = [{"name": s.name[:60], "dose": (s.dose or "según etiqueta")[:60],
                           "timing": (s.timing or "según indicación")[:60],
                           "evidence_note": ""} for s in doc.supplements[:8] if s.name]
    nut["flexibility_rules"] = [r[:200] for r in doc.rules[:8]]

    food_map = _food_map(db)
    slot_de_nombre = {_norm(m["name"]): m["slot"] for m in nut["meals"]}

    def _slot_para(nombre: str, orden: int) -> int:
        base = re.sub(r"\s*\(opci[oó]n\s*\d+\)\s*$", "", nombre or "", flags=re.I).strip()
        return slot_de_nombre.get(_norm(base)) or nut["meals"][min(orden, len(nut["meals"]) - 1)]["slot"]

    targets = {m["slot"]: m["target"] for m in nut["meals"]}
    foods_by_id = {f.id: {"id": f.id, "canonical_name": f.canonical_name,
                          "protein_g": float(f.protein_g), "carbs_g": float(f.carbs_g),
                          "fat_g": float(f.fat_g),
                          "unit_grams": getattr(f, "unit_grams", None),
                          "min_grams": getattr(f, "min_grams", None) or 0,
                          "max_grams": getattr(f, "max_grams", None) or 400}
                   for f in {x.id: x for x in food_map.values()}.values()}
    # El modo lo decide la MAYORÍA de lo que trae el documento, no la simple
    # presencia de comidas por día: un documento mixto (un menú por días + unas
    # opciones sueltas) descartaba en silencio TODA una de las dos listas.
    modo = "strict" if len(por_dia) > len(sueltas) else "flexible_7"
    total_doc = len(doc.meals)
    if modo == "flexible_7":
        # En flexible entran TODAS: las sueltas y las que traían día (como una
        # opción más de su toma).
        entradas = list(sueltas) + list(por_dia)
        opciones: dict[int, list[dict]] = {m["slot"]: [] for m in nut["meals"]}
        recortadas: list[str] = []
        for orden, dm in enumerate(entradas):
            slot = _slot_para(dm.name, orden)
            if len(opciones[slot]) >= MAX_OPCIONES:
                recortadas.append(dm.name or f"comida {orden + 1}")
                continue
            letra = "ABCD"[len(opciones[slot])]
            op = _opcion_desde(dm, targets[slot], food_map, avisos, resumen, letra, foods_by_id)
            if op:
                opciones[slot].append(op)
        if recortadas:
            avisos.append(
                f"Cada toma admite {MAX_OPCIONES} opciones: se han dejado fuera "
                + ", ".join(f"«{n}»" for n in recortadas[:6])
                + (" …" if len(recortadas) > 6 else "") + ". Añádelas en el editor si las quieres.")
        nut["meal_bank"] = {"mode": "flexible_7", "slots": [
            {"slot": m["slot"], "fmt": "options", "options": opciones[m["slot"]],
             "weekly_examples": []} for m in nut["meals"]]}
        resumen["comidas"] = sum(len(v) for v in opciones.values())
    else:
        dias: dict[str, list[dict]] = {}
        for orden, dm in enumerate(por_dia):
            slug = _dia_slug(dm.day) or "lunes"
            usados = {x["slot"] for x in dias.get(slug, [])}
            slot = _slot_para(dm.name, len(dias.get(slug, [])))
            if slot in usados:
                # Dos platos para la misma toma del mismo día: el segundo
                # SOBRESCRIBÍA al primero en silencio. Se queda el primero y
                # se avisa del otro.
                avisos.append(f"«{dm.name or 'comida'}» del {slug} repite la toma de otro plato: "
                              "se ha quedado el primero, revísalo en el editor.")
                continue
            op = _opcion_desde(dm, targets[slot], food_map, avisos, resumen, "A", foods_by_id)
            if op:
                op["key"] = None
                dias.setdefault(slug, []).append({"slot": slot, "dish": op})
        if sueltas:
            avisos.append(
                f"El documento es un menú por días y {len(sueltas)} comida(s) no decían de qué "
                "día son: no se han importado. Añádelas en el editor.")
        dias = _semana_completa(dias, avisos)
        nut["meal_bank"] = {"mode": "strict", "days": [
            {"day": d, "meals": sorted(dias[d], key=lambda x: x["slot"])}
            for d in _DIAS if d in dias]}
        resumen["comidas"] = sum(len(v) for v in dias.values())
    # Nada se pierde en silencio: si el documento traía más comidas de las que
    # han entrado, se dice cuántas y por qué.
    if resumen.get("platos_descartados"):
        pl = resumen["platos_descartados"]
        avisos.append(
            f"{len(pl)} plato(s) no han entrado porque algún alimento suyo no está en la base "
            "(sus macros no se pueden calcular y el sistema no los inventa): "
            + ", ".join(pl[:6]) + (" …" if len(pl) > 6 else "")
            + ". Añade esos alimentos en Recursos y vuelve a importar, o escríbelos en el editor.")
    if resumen.get("platos_ajustados"):
        avisos.append(
            f"{len(resumen['platos_ajustados'])} plato(s) venían sin gramos: los ha fijado el "
            "sistema para cuadrar con el objetivo de su toma (los alimentos son los del documento).")
    if total_doc and resumen.get("comidas", 0) < total_doc:
        avisos.append(f"El documento trae {total_doc} comidas y se han importado "
                      f"{resumen.get('comidas', 0)}: revisa los avisos de arriba.")
    if resumen.get("alimentos_sin_base"):
        unicos = sorted(set(resumen["alimentos_sin_base"]))
        avisos.append("Alimentos sin ficha en la base (sus macros no se recalculan; revísalos "
                      "en el editor): " + ", ".join(unicos[:12]) + (" …" if len(unicos) > 12 else ""))
    if resumen.get("alimentos_sin_gramos"):
        unicos = sorted(set(resumen["alimentos_sin_gramos"]))
        avisos.append("Cantidades sin gramos (se conserva lo escrito; complétalas en el editor): "
                      + ", ".join(unicos[:12]) + (" …" if len(unicos) > 12 else ""))
    if not doc.meals:
        avisos.append("El documento no trae comidas reconocibles: la dieta queda con los objetivos "
                      "del cliente y sin recetas (complétala o genera con IA).")
    return nut


def build_plan_candidates(db: Session, client: Client, ext: PlanDocumentExtraction,
                          nombre_doc: str) -> dict:
    """Los JSON candidatos + avisos + resumen. NO persiste nada."""
    from app.services import packages as pkgs

    avisos: list[str] = list(ext.warnings)
    resumen: dict = {}
    nutrition = training = None
    tiene_dieta = bool(ext.nutrition and (ext.nutrition.meals or ext.nutrition.declared_kcal
                                          or ext.nutrition.supplements))
    tiene_entreno = bool(ext.training and ext.training.sessions)
    if tiene_dieta:
        if pkgs.has_nutrition(client.package_tier):
            nutrition = build_nutrition(db, client, ext.nutrition, avisos, resumen)
        else:
            avisos.append("Este cliente no tiene nutrición contratada: la dieta del documento se ignora.")
    if tiene_entreno:
        if pkgs.has_training(client.package_tier):
            training = build_training(db, client, ext.training, avisos, resumen)
        else:
            avisos.append("Este cliente no tiene entrenamiento contratado: la rutina del documento se ignora.")
    if not nutrition and not training:
        raise ValueError(
            "No se ha reconocido en el documento ni una dieta con comidas ni una rutina con "
            "ejercicios de la biblioteca. Revisa los avisos.")
    return {
        "nutrition_json": nutrition, "training_json": training,
        "avisos": avisos, "resumen": resumen,
        "inventory": list(ext.inventory), "unmapped": list(ext.unmapped),
        "document_kind": ext.document_kind, "document": nombre_doc,
    }
