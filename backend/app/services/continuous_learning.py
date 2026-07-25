"""Aprendizaje continuo (hardening §13).

Captura las ediciones del coach, las clasifica y, cuando un patrón se repite,
PROPONE una mejora (nunca la aplica sin aprobación). Cada corrección aprobada se
convierte en caso de test permanente (un error solo puede ocurrir una vez).
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import PlanEdit

# Categorías predefinidas del "por qué" de una edición.
EDIT_CATEGORIES = (
    "calculo", "restriccion", "horario", "seleccion_alimentos", "volumen",
    "progresion", "redaccion", "realismo", "criterio_propio", "otro",
)

# A qué acción de mejora mapea cada categoría recurrente.
_IMPROVEMENT_BY_CATEGORY = {
    "calculo": "una regla de cálculo o un guardrail numérico nuevo",
    "restriccion": "un validador de restricción (alérgeno/patrón) más estricto",
    "horario": "una regla de horarios en la coherencia dieta↔entreno",
    "seleccion_alimentos": "un ajuste del filtro/preferencias de alimentos",
    "volumen": "un ajuste del rango de volumen por grupo",
    "progresion": "un ajuste de la plantilla de progresión",
    "redaccion": "un ajuste de prompt de redacción o del editor del panel",
    "realismo": "un cap de porciones/duración en el validador",
    "criterio_propio": "una entrada nueva en CRITERIOS_ASESORIA.md",
    "otro": "revisión manual del patrón",
}

PROPOSAL_THRESHOLD = 3


def record_edit(
    db: Session, *, plan_id: int, category: str, field_path: str | None = None,
    before=None, after=None, note: str | None = None, commit: bool = True,
) -> PlanEdit:
    """Registra una edición del coach. `category` debe estar en EDIT_CATEGORIES."""
    cat = category if category in EDIT_CATEGORIES else "otro"
    edit = PlanEdit(plan_id=plan_id, category=cat, field_path=field_path,
                    before_json=_jsonable(before), after_json=_jsonable(after), note=note)
    db.add(edit)
    if commit:
        db.commit()
    return edit


def _jsonable(v):
    if v is None or isinstance(v, (dict, list, str, int, float, bool)):
        return v if not isinstance(v, (dict, list)) else v
    return str(v)


def classify_edit(field_path: str | None, before=None, after=None) -> str:
    """Heurística determinista para clasificar una edición por su ruta y valores."""
    p = (field_path or "").lower()
    if any(k in p for k in ("kcal", "macro", "protein", "carb", "fat", "target")):
        return "calculo"
    if any(k in p for k in ("time", "horario", "schedule")):
        return "horario"
    if any(k in p for k in ("ingredient", "food", "option", "meal", "dish")):
        return "seleccion_alimentos"
    if any(k in p for k in ("sets", "reps", "volume", "series")):
        return "volumen"
    if any(k in p for k in ("progression", "rir", "tempo", "deload")):
        return "progresion"
    if any(k in p for k in ("rationale", "note", "text", "cue", "why")):
        return "redaccion"
    return "otro"


def classify_change_text(text: str) -> str:
    """Clasifica un cambio por su texto legible (los diff strings de plan_diff,
    p. ej. 'Calorías: 2000 → 2180 kcal'). Acento-insensible."""
    import unicodedata

    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii").lower()
    if any(k in t for k in ("calor", "kcal", "proteina", "hidrato", "grasa", "macro")):
        return "calculo"
    if any(k in t for k in ("rir", "descanso", "progres", "tempo", "deload")):
        return "progresion"
    if any(k in t for k in ("serie", "rep", "peso", "ejercicio", "sesion", "volumen")):
        return "volumen"
    if "suplement" in t:
        return "otro"
    if any(k in t for k in ("comida", "toma", "reparto", "desayuno", "cena", "merienda", "horario")):
        return "horario"
    if any(k in t for k in ("alimento", "ingredient", "opcion")):
        return "seleccion_alimentos"
    return "otro"


def recurring_categories(db: Session, *, min_count: int = PROPOSAL_THRESHOLD) -> dict[str, int]:
    """Categorías de edición que se repiten ≥ min_count (patrones a atender)."""
    rows = db.execute(
        select(PlanEdit.category, func.count()).group_by(PlanEdit.category)
    ).all()
    return {cat: n for cat, n in rows if n >= min_count}


def propose_improvements(db: Session, *, min_count: int = PROPOSAL_THRESHOLD) -> str:
    """Genera el contenido de MEJORAS_PROPUESTAS.md a partir de los patrones
    recurrentes. NADA se aplica sin aprobación explícita del coach."""
    recurring = recurring_categories(db, min_count=min_count)
    lines = [
        "# MEJORAS PROPUESTAS (automático — requiere tu aprobación)",
        "",
        "> Generado desde los patrones de edición del coach (hardening §13). "
        "**Nada se aplica sin tu OK.** Cada mejora aprobada se convierte en un caso "
        "de test permanente.",
        "",
    ]
    if not recurring:
        lines.append("_Sin patrones recurrentes todavía (se necesitan "
                     f"≥{min_count} ediciones de una misma categoría)._")
        return "\n".join(lines) + "\n"
    for cat, n in sorted(recurring.items(), key=lambda x: -x[1]):
        action = _IMPROVEMENT_BY_CATEGORY.get(cat, "revisión manual")
        lines.append(f"- **{cat}** ({n} ediciones): propongo {action}.")
    return "\n".join(lines) + "\n"
