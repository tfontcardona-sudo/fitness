"""Lecciones aprendidas de las EDICIONES del coach (§13 en vivo).

Cada vez que el coach corrige un plan generado, el PATCH ya guarda el cambio
clasificado en `plan_edits` (services/continuous_learning.py). Este módulo
cierra el círculo: destila esas correcciones en LECCIONES cualitativas cortas
y las inyecta en el prompt de generación — cada plan nuevo nace sabiendo lo
que el coach corrigió en los anteriores.

Reglas de seguridad (innegociables):
- Las lecciones son CUALITATIVAS: estilo, selección de alimentos/ejercicios,
  estructura, redacción. NUNCA cifras de kcal/macros — eso lo calcula el
  backend (metrics.py) y la IA no calcula.
- La destilación usa el modelo LIGERO y es best-effort: si falla, se queda la
  versión anterior de las lecciones y no rompe nada.
- El coach puede verlas y regenerarlas desde el panel (transparencia: el
  sistema no aprende "a escondidas").

El resultado vive en un sidecar JSON (storage/brand/_coach_lessons.json), sin
migración, y se refresca solo cuando hay suficientes ediciones nuevas.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Plan, PlanEdit

_log = logging.getLogger("app.coach_lessons")

# Umbral de ediciones NUEVAS desde la última destilación para re-destilar.
REFRESH_MIN_NEW_EDITS = 5
# Mínimo de ediciones totales para que haya algo que aprender.
MIN_EDITS = 5
# Tope de ediciones que se le enseñan al modelo (las más recientes).
MAX_EDITS_FOR_PROMPT = 120
# Tope del bloque inyectado en el prompt de generación.
MAX_BLOCK_CHARS = 1600


class LessonsOutput(BaseModel):
    """Salida estructurada de la destilación."""

    lessons: list[str] = Field(min_length=1, max_length=8)


def _sidecar_path() -> Path:
    from app.services.storage import storage_root

    d = storage_root() / "brand"
    d.mkdir(parents=True, exist_ok=True)
    return d / "_coach_lessons.json"


def load_lessons() -> dict:
    """Contenido actual del sidecar ({} si no existe o está corrupto)."""
    try:
        p = _sidecar_path()
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — un sidecar roto no rompe la generación
        pass
    return {}


def lessons_reference() -> str:
    """Bloque de LECCIONES para el prompt de generación ('' si no hay).
    Se añade al user prompt (no al system): así no invalida la caché del
    system prompt y puede cambiar entre generaciones."""
    data = load_lessons()
    lessons = [x for x in (data.get("lessons") or []) if isinstance(x, str) and x.strip()]
    if not lessons:
        return ""
    body = "\n".join(f"- {x.strip()}" for x in lessons)
    block = (
        "\n\nLECCIONES DEL COACH (aprendidas de sus correcciones a planes "
        "anteriores; aplícalas SIN cambiar ningún número del contrato):\n" + body
    )
    return block[:MAX_BLOCK_CHARS]


def _recent_edits(db: Session) -> list[tuple[PlanEdit, str | None]]:
    filas = db.execute(
        select(PlanEdit, Plan.goal_type)
        .join(Plan, Plan.id == PlanEdit.plan_id)
        .order_by(PlanEdit.id.desc())
        .limit(MAX_EDITS_FOR_PROMPT)
    ).all()
    return [(pe, goal) for pe, goal in filas]


def distill_lessons(db: Session, ai=None) -> dict:
    """Destila las ediciones registradas en 3-8 lecciones cortas (IA ligera)
    y las persiste en el sidecar. Devuelve el sidecar resultante.

    `ai` inyectable (tests). Nunca lanza hacia el caller del scheduler; los
    errores del endpoint del panel sí se propagan para que el coach los vea.
    """
    filas = _recent_edits(db)
    if len(filas) < MIN_EDITS:
        return {"skipped": f"solo {len(filas)} ediciones (mínimo {MIN_EDITS})",
                **load_lessons()}

    # Muestra agrupada por categoría (recorta ruido y tokens).
    por_categoria: dict[str, list[str]] = {}
    max_id = 0
    for pe, goal in filas:
        max_id = max(max_id, pe.id)
        nota = (pe.note or "").strip()
        if not nota:
            continue
        etiqueta = f"[{goal or 'sin objetivo'}] {nota}"
        por_categoria.setdefault(pe.category or "otro", [])
        if len(por_categoria[pe.category or "otro"]) < 15:
            por_categoria[pe.category or "otro"].append(etiqueta)

    lineas = []
    for cat, notas in sorted(por_categoria.items()):
        lineas.append(f"{cat} ({len(notas)} ejemplos):")
        lineas.extend(f"  · {n}" for n in notas)
    corpus = "\n".join(lineas)

    from app.config import settings

    if ai is None:
        from app.services.ai.client import AIClient

        ai = AIClient()
    system = (
        "Eres el asistente de un coach de fitness. Vas a leer CORRECCIONES que "
        "el coach hizo a mano sobre planes generados automáticamente, y debes "
        "destilarlas en LECCIONES generales para que los planes futuros salgan "
        "como a él le gustan.\n"
        "Reglas estrictas:\n"
        "- De 3 a 8 lecciones, en castellano, cada una de UNA frase (≤160 caracteres).\n"
        "- Solo lecciones que GENERALICEN un patrón repetido (≥2 correcciones); "
        "ignora cambios puntuales de un solo cliente.\n"
        "- CUALITATIVAS: preferencias de alimentos/ejercicios, estructura, horarios, "
        "estilo de redacción. PROHIBIDO dictar cifras de kcal, gramos de macros o "
        "porcentajes: esos números los calcula el sistema, no tú.\n"
        "- Nada de datos personales de clientes (sin nombres).\n"
        "Responde SOLO con JSON: {\"lessons\": [\"…\", …]}"
    )
    user = f"CORRECCIONES DEL COACH (agrupadas por tipo):\n{corpus}"
    out = ai.generate_json(model=settings.model_light, system=system, user=user,
                           schema=LessonsOutput, temperature=0, max_tokens=800)

    # Filtro determinista de seguridad: fuera lecciones con cifras de kcal/g
    # (por si el modelo se salta la regla) y tope de longitud.
    import re

    limpias = []
    for lx in out.lessons:
        s = lx.strip()
        if not s:
            continue
        if re.search(r"\d+\s*(kcal|calor[ií]as|g\b|gramos|%)", s, re.IGNORECASE):
            continue
        limpias.append(s[:200])
    if not limpias:
        # El filtro vetó TODO lo devuelto: no se pisa el sidecar (se
        # conservan las lecciones buenas anteriores) ni se avanza
        # last_edit_id — el siguiente refresco lo reintenta.
        return {"skipped": "la IA no produjo lecciones válidas (todas con cifras)",
                **load_lessons()}
    data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_edits": len(filas),
        "last_edit_id": max_id,
        "lessons": limpias,
    }
    _sidecar_path().write_text(json.dumps(data, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    return data


def maybe_refresh(db: Session) -> dict | None:
    """Re-destila SOLO si hay suficientes ediciones nuevas desde la última vez.
    Pensado para el mantenimiento diario: best-effort, nunca lanza."""
    try:
        actual = load_lessons()
        ultimo = int(actual.get("last_edit_id") or 0)
        max_id = int(db.scalar(select(func.max(PlanEdit.id))) or 0)
        nuevas = db.scalar(
            select(func.count()).select_from(PlanEdit).where(PlanEdit.id > ultimo)
        ) or 0
        if max_id <= ultimo or nuevas < REFRESH_MIN_NEW_EDITS:
            return None
        return distill_lessons(db)
    except Exception as exc:  # noqa: BLE001 — el aprendizaje nunca rompe el ciclo
        _log.warning("Refresco de lecciones del coach fallido: %s", exc)
        return None
