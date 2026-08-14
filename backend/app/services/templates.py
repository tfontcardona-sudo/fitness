"""Pool de rutinas/planificaciones (plantillas) — lógica compartida.

Tres caminos alimentan el pool y los tres acaban en el MISMO shape que
`plans.training_json` (ejercicios resueltos a `exercise_id` de la biblioteca):

  1. SEMBRADAS de fábrica (`seeds/templates_data.py`): 20 rutinas por carpeta,
     escritas con nombres EXACTOS de la biblioteca y resueltas aquí.
  2. SUBIDAS (PDF/Word externos): la IA extrae la rutina y MAPEA cada ejercicio
     al nombre más cercano de la biblioteca (lista cerrada en el prompt, como en
     la generación de planes: la IA nunca inventa ejercicios); el backend
     resuelve nombre→id de forma determinista.
  3. CREADAS/EDITADAS a mano en el editor (ya llegan con exercise_id).

"Usar con un cliente" copia la plantilla como Plan BORRADOR (el coach revisa y
publica: mismo patrón de seguridad que la generación con IA). El documento de
una plantilla se renderiza con el dossier de la marca (mismo motor que los
planes de clientes) — así cualquier plan externo subido queda re-maquetado al
diseño de Professional.
"""
from __future__ import annotations

import difflib
import unicodedata

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Exercise, PlanTemplate

# Carpetas del pool — lo más recurrente en un gimnasio. El frontend las lee de
# GET /api/templates/categories (una sola verdad).
CATEGORIES: list[dict] = [
    {"key": "ganancia_muscular", "label": "Ganancia muscular",
     "blurb": "Hipertrofia: volumen, priorización de grupos y progresión."},
    {"key": "perdida_grasa", "label": "Pérdida de grasa y cintura",
     "blurb": "Déficit bien entrenado: fuerza + NEAT sin perder músculo."},
    {"key": "fuerza", "label": "Fuerza y rendimiento",
     "blurb": "Básicos, rendimiento deportivo y oposiciones."},
    {"key": "salud_espalda", "label": "Salud, espalda y molestias",
     "blurb": "Casos con molestias comunes: conservador y progresivo."},
    {"key": "principiantes", "label": "Primeros pasos y vuelta al gym",
     "blurb": "Empezar de cero o volver tras un parón, sin agobios."},
    {"key": "mantenimiento", "label": "Mantenimiento y tono",
     "blurb": "Mantener resultados, salud general y mínimo efectivo."},
]
CATEGORY_KEYS = {c["key"] for c in CATEGORIES}

# Objetivo interno aproximado por carpeta (pre-rellena la ficha al usarla).
CATEGORY_GOAL = {
    "ganancia_muscular": "muscle_gain", "perdida_grasa": "fat_loss",
    "fuerza": "muscle_gain", "salud_espalda": "maintenance",
    "principiantes": "maintenance", "mantenimiento": "maintenance",
}

_DEFAULT_PROGRESSION = [
    {"week": 1, "intent": "Adaptación", "load_pct": 100, "rir_target": "2-3",
     "volume_note": "Aprende los pesos de referencia."},
    {"week": 2, "intent": "Progresión", "load_pct": 102.5, "rir_target": "2",
     "volume_note": "Sube carga si cierras todas las series."},
    {"week": 3, "intent": "Carga", "load_pct": 105, "rir_target": "1-2",
     "volume_note": "Semana fuerte: prioriza técnica."},
    {"week": 4, "intent": "Descarga", "load_pct": 90, "rir_target": "3-4",
     "volume_note": "Mitad de series: recupera para el mes siguiente."},
]


class TemplateError(ValueError):
    """Plantilla inválida (ejercicios sin resolver, estructura incoherente…)."""


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def _library_index(db: Session) -> tuple[dict[str, int], list[str], dict[str, str]]:
    """Índices nombre→id (canónicos y alias, normalizados) + lista de canónicos."""
    by_name: dict[str, int] = {}
    canon_by_norm: dict[str, str] = {}
    canonicals: list[str] = []
    for ex in db.scalars(select(Exercise)):
        n = _norm(ex.canonical_name)
        by_name[n] = ex.id
        canon_by_norm[n] = ex.canonical_name
        canonicals.append(n)
        for a in ex.aliases or []:
            by_name.setdefault(_norm(a), ex.id)
    return by_name, canonicals, canon_by_norm


def resolve_training(db: Session, routine: dict) -> dict:
    """Convierte una rutina con ejercicios POR NOMBRE al shape de
    `plans.training_json` (exercise_id resueltos). Lanza TemplateError con la
    lista de nombres irresolubles — nunca inventa un ejercicio."""
    by_name, canonicals, _ = _library_index(db)
    unresolved: list[str] = []
    sessions_out = []
    for sess in routine.get("sessions", []):
        exs = []
        for ex in sess.get("exercises", []):
            if ex.get("exercise_id"):
                exs.append(ex)
                continue
            name = ex.get("name") or ""
            key = _norm(name)
            ex_id = by_name.get(key)
            if ex_id is None:
                # Tolerancia mínima a variaciones tipográficas (0.9): un nombre
                # realmente distinto NO se sustituye en silencio.
                close = difflib.get_close_matches(key, canonicals, n=1, cutoff=0.9)
                ex_id = by_name.get(close[0]) if close else None
            if ex_id is None:
                unresolved.append(name)
                continue
            exs.append({
                "exercise_id": ex_id,
                "sets": int(ex.get("sets") or 3),
                "rep_range": str(ex.get("rep_range") or "8-10"),
                "rir": str(ex.get("rir") or "2"),
                "rest_sec": int(ex.get("rest_sec") or 120),
                "technique_cue": ex.get("technique_cue") or "",
            })
        if not exs:
            raise TemplateError(
                f"La sesión «{sess.get('name') or sess.get('day')}» queda sin ejercicios reconocibles")
        sessions_out.append({
            "day": sess.get("day") or "Lunes",
            "name": sess.get("name") or "Sesión",
            "warmup": sess.get("warmup") or "5-10 minutos de cardio suave y movilidad general.",
            "exercises": exs,
            "cooldown": sess.get("cooldown") or "Estiramiento global 5 minutos.",
        })
    if unresolved:
        raise TemplateError(
            "Ejercicios fuera de la biblioteca: " + ", ".join(sorted(set(unresolved))))
    if not sessions_out:
        raise TemplateError("La rutina no tiene sesiones")
    return {
        "split_name": routine.get("split_name") or "Rutina",
        "split_rationale": routine.get("split_rationale") or "",
        "sessions": sessions_out,
        "weekly_progression": routine.get("weekly_progression") or _DEFAULT_PROGRESSION,
        "cardio": routine.get("cardio") or {"daily_steps": 8000, "sessions": []},
        "deload_instructions": routine.get("deload_instructions")
        or "Semana 4: misma rutina con la mitad de series y RIR 3-4.",
    }


def template_document(db: Session, tpl: PlanTemplate, fmt: str = "pdf") -> tuple[bytes, str, str]:
    """Renderiza la plantilla con el dossier de la MARCA (mismo motor que los
    planes de clientes): cualquier plan externo subido sale re-maquetado."""
    from app.services.docs.pdf_convert import docx_bytes_to_pdf
    from app.services.docs.plan_doc import generate_plan_doc
    from app.services.plan_delivery import DOCX_MEDIA, doc_brand

    training = tpl.training_json or {}
    ex_ids = {e.get("exercise_id") for s in training.get("sessions", [])
              for e in s.get("exercises", []) if e.get("exercise_id")}
    names: dict[int, str] = {}
    if ex_ids:
        for ex in db.scalars(select(Exercise).where(Exercise.id.in_(ex_ids))):
            names[ex.id] = ex.canonical_name

    has_nutrition = bool(tpl.nutrition_json)
    data = generate_plan_doc(
        brand=doc_brand(db),
        client_name=tpl.title,
        month_index=1,
        goal_type=tpl.goal_type,
        diet_mode=None,
        nutrition=tpl.nutrition_json or {},
        training=training,
        education={},
        exercise_names=names,
        include_nutrition=has_nutrition,
        include_training=bool(training) and not has_nutrition,
        package_tier="full" if has_nutrition else "train",
    )
    ascii_t = unicodedata.normalize("NFKD", tpl.title).encode("ascii", "ignore").decode()
    safe = "".join(c if c.isalnum() else "_" for c in ascii_t).strip("_").lower() or "rutina"
    if fmt == "docx":
        return data, DOCX_MEDIA, f"rutina_{safe}.docx"
    try:
        pdf = docx_bytes_to_pdf(data)
        return pdf, "application/pdf", f"rutina_{safe}.pdf"
    except Exception:
        return data, DOCX_MEDIA, f"rutina_{safe}.docx"


# ----------------------------------------------------- importación con IA ----
class _ImpExercise(BaseModel):
    name: str  # EXACTO de la lista de la biblioteca inyectada en el prompt
    sets: int = Field(default=3, ge=1, le=10)
    rep_range: str = "8-10"
    rir: str = "2"
    rest_sec: int = Field(default=120, ge=15, le=600)
    technique_cue: str = ""


class _ImpSession(BaseModel):
    day: str = "Lunes"
    name: str = "Sesión"
    warmup: str = ""
    exercises: list[_ImpExercise] = Field(min_length=1)
    cooldown: str = ""


class TemplateImport(BaseModel):
    """Rutina extraída de un documento externo (solo ENTRENAMIENTO: la dieta de
    un documento ajeno no se importa — la nutrición la calcula el sistema con la
    anamnesis de cada cliente)."""

    title: str
    case_note: str | None = None
    level: str | None = None            # beginner|intermediate|advanced
    days_per_week: int | None = Field(default=None, ge=1, le=7)
    training_place: str | None = None   # gym|home
    split_name: str | None = None
    split_rationale: str | None = None
    sessions: list[_ImpSession] = Field(min_length=1)
    deload_instructions: str | None = None


_IMPORT_SYSTEM = """Eres el asistente del preparador de un centro de fitness. Te llega un \
documento EXTERNO con una rutina/planificación de entrenamiento y debes extraerla a JSON \
para incorporarla a la biblioteca del centro, que la re-maquetará con su propio diseño.

REGLAS:
- Extrae SOLO el entrenamiento (sesiones, ejercicios, series, repeticiones, RIR/intensidad, \
descansos). Si el documento trae dieta, IGNÓRALA (la nutrición se genera aparte para cada \
cliente).
- Cada ejercicio debe mapearse al nombre MÁS CERCANO de la BIBLIOTECA que se te da (lista \
cerrada, cópialo EXACTO, tildes incluidas). Nunca inventes nombres fuera de la lista; si un \
ejercicio no tiene equivalente razonable, OMÍTELO.
- Si el documento no da algún dato (RIR, descanso…), usa valores prudentes por defecto \
(RIR "2", 120 s) en vez de inventar precisión.
- Textos en castellano, tono profesional, sin emojis.
- "title": nombre corto de la rutina. "case_note": para quién es (si el documento lo dice)."""


def _import_user_prompt(db: Session, extra: str = "") -> str:
    _, _, canon_by_norm = _library_index(db)
    nombres = sorted(canon_by_norm.values())
    return (
        "BIBLIOTECA DE EJERCICIOS (usa estos nombres EXACTOS):\n- "
        + "\n- ".join(nombres)
        + "\n\nExtrae la rutina del documento a JSON según el esquema." + extra
    )


def import_template_from_file(
    db: Session, *, filename: str, raw: bytes, category: str, ai=None,
) -> PlanTemplate:
    """PDF/Word externo → plantilla del pool (la IA extrae y mapea; el backend
    resuelve nombre→id de forma determinista). Devuelve la fila SIN commitear."""
    from app.config import settings
    from app.services.ai.client import AIClient

    ai = ai or AIClient()
    lower = (filename or "").lower()
    if lower.endswith(".pdf"):
        imp = ai.read_pdf_json(
            model=settings.model_heavy, system=_IMPORT_SYSTEM,
            user=_import_user_prompt(db), pdf_bytes=raw, schema=TemplateImport,
        )
    elif lower.endswith(".docx"):
        import io

        from docx import Document

        doc = Document(io.BytesIO(raw))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(c.text.strip() for c in row.cells))
        text = "\n".join(parts)[:60000]
        imp = ai.generate_json(
            model=settings.model_heavy, system=_IMPORT_SYSTEM,
            user=_import_user_prompt(db, f"\n\nDOCUMENTO (texto extraído):\n{text}"),
            schema=TemplateImport,
        )
    else:
        raise TemplateError("Formato no soportado: sube un PDF o un Word (.docx)")

    routine = imp.model_dump()
    training = resolve_training(db, routine)
    return PlanTemplate(
        category=category,
        title=imp.title.strip()[:160] or "Rutina importada",
        case_note=imp.case_note,
        goal_type=CATEGORY_GOAL.get(category),
        level=imp.level if imp.level in ("beginner", "intermediate", "advanced") else None,
        days_per_week=imp.days_per_week or len(training["sessions"]),
        training_place=imp.training_place if imp.training_place in ("gym", "home") else "gym",
        training_json=training,
        source="upload",
    )


def seed_plan_templates(db: Session) -> int:
    """Siembra el pool de fábrica (insert-por-título dentro de cada carpeta, como
    la biblioteca de ejercicios: re-ejecutar no duplica ni pisa ediciones)."""
    try:
        from app.seeds.templates_data import TEMPLATES
    except Exception:
        return 0
    existing = {(t.category, t.title) for t in db.scalars(
        select(PlanTemplate).where(PlanTemplate.source == "seed"))}
    added = 0
    for entry in TEMPLATES:
        key = (entry["category"], entry["title"])
        if key in existing:
            continue
        try:
            training = resolve_training(db, entry)
        except TemplateError:
            # Un nombre irresoluble NO tumba el arranque: se omite esa plantilla.
            continue
        db.add(PlanTemplate(
            category=entry["category"], title=entry["title"],
            case_note=entry.get("case"), goal_type=CATEGORY_GOAL.get(entry["category"]),
            level=entry.get("level"), days_per_week=entry.get("days_per_week"),
            training_place=entry.get("place") or "gym",
            training_json=training, source="seed",
        ))
        added += 1
    if added:
        db.commit()
    return added
