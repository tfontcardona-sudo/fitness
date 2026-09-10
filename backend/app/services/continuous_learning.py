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


# De dónde viene una edición. Cambiar lo que acabas de COPIAR de otro cliente y
# corregir lo que escribió la IA son cosas distintas: mezclarlas en la misma
# bolsa es lo que hacía que el sistema "aprendiera" ruido.
EDIT_SOURCES = (
    "edicion",     # el editor del panel sobre un plan vivo (corrección a la IA)
    "copia",       # lo que se cambia de un plan copiado de otro cliente
    "modelo",      # lo que se cambia de un modelo de plan aplicado
    "documento",   # correcciones a la transcripción de un plan ajeno
    "word",        # el Word editado que vuelve
    "swap",        # cambio de ejercicio
    "revision",    # corrección de los ajustes que propuso la revisión quincenal
)


def record_edit(
    db: Session, *, plan_id: int, category: str, field_path: str | None = None,
    before=None, after=None, note: str | None = None, commit: bool = True,
    signal: str | None = None, source: str | None = None,
    detail: str | None = None,
) -> PlanEdit:
    """Registra una edición del coach. `category` debe estar en EDIT_CATEGORIES.

    `signal`/`detail` se DERIVAN solos de la frase del cambio si no se pasan:
    la señal es el campo normalizado por el que se cuentan los patrones y el
    detalle es la sustitución en limpio ("pollo → pavo"). Todo determinista, sin
    una sola llamada a la IA."""
    cat = category if category in EDIT_CATEGORIES else "otro"
    texto = note or ""
    if signal is None:
        signal = derivar_signal(texto, field_path)
    if detail is None:
        par = derivar_sustitucion(texto)
        detail = f"{par[0]} → {par[1]}" if par else None
    edit = PlanEdit(plan_id=plan_id, category=cat, field_path=field_path,
                    before_json=_jsonable(before), after_json=_jsonable(after),
                    note=note, signal=signal,
                    source=(source if source in EDIT_SOURCES else "edicion"),
                    detail=(detail or None))
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


# ---------------------------------------------------------------- señales ----
# El campo NORMALIZADO de cada edición. La categoría dice "corrige el cálculo";
# la señal dice cuál: las kcal, la proteína o el reparto de una toma concreta.
# De aquí sale todo lo que el sistema aprende de sí mismo, y se calcula sin IA.

SIGNAL_LABELS: dict[str, str] = {
    "nutricion.kcal": "las calorías del día",
    "nutricion.proteina": "la proteína",
    "nutricion.hidratos": "los hidratos",
    "nutricion.grasa": "la grasa",
    "nutricion.reparto": "el reparto entre tomas",
    "nutricion.horario": "las horas de las tomas",
    "nutricion.alimentos": "los alimentos de las opciones",
    "nutricion.suplementos": "la suplementación",
    "nutricion.flexibilidad": "las reglas de flexibilidad",
    "nutricion.argumentario": "el porqué del enfoque",
    "entreno.ejercicio": "qué ejercicio va en cada sitio",
    "entreno.series": "las series",
    "entreno.repeticiones": "las repeticiones",
    "entreno.rir": "el RIR",
    "entreno.descanso": "el descanso entre series",
    "entreno.progresion": "la progresión semanal",
    "entreno.deload": "la semana de descarga",
    "entreno.cardio": "el cardio y los pasos",
    "entreno.estructura": "el reparto de días y sesiones",
    "entreno.tecnica": "las claves técnicas",
    "otro": "otras cosas",
}

# (señal, palabras que la delatan). El ORDEN manda: lo más específico primero,
# porque "series" aparece también en frases de repeticiones.
_SIGNAL_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("nutricion.proteina", ("proteina", "protein_g")),
    ("nutricion.hidratos", ("hidrato", "carbs_g", "carbohidrato")),
    ("nutricion.grasa", ("grasa", "fat_g")),
    ("nutricion.kcal", ("caloria", "kcal", "target_kcal", "energia")),
    ("nutricion.suplementos", ("suplement",)),
    ("nutricion.flexibilidad", ("flexibilidad", "margen de maniobra", "recarga",
                                "comida libre", "refeed")),
    ("nutricion.argumentario", ("rationale", "porque este enfoque", "argumentario")),
    ("nutricion.horario", ("hora de", "horario", "a las ", "meal.time", "time")),
    ("nutricion.alimentos", ("alimento", "ingredient", "opcion", "plato", "receta",
                             "menu", "banco")),
    ("nutricion.reparto", ("reparto", "toma", "comida", "desayuno", "almuerzo",
                           "cena", "merienda", "snack")),
    ("entreno.descanso", ("descanso", "rest_sec", "rest")),
    ("entreno.rir", ("rir",)),
    ("entreno.repeticiones", ("repetic", "reps")),
    ("entreno.series", ("serie", "sets")),
    ("entreno.progresion", ("progres", "semana ", "weekly_progression")),
    ("entreno.deload", ("deload", "descarga")),
    ("entreno.cardio", ("cardio", "pasos", "neat")),
    ("entreno.tecnica", ("tecnica", "cue", "biomecanic", "tempo")),
    ("entreno.estructura", ("split", "sesion", "dia de entreno", "estructura",
                            "calentamiento", "vuelta a la calma")),
    ("entreno.ejercicio", ("ejercicio", "exercise")),
)


def _sin_acentos(texto: str) -> str:
    import unicodedata

    return (unicodedata.normalize("NFKD", texto or "")
            .encode("ascii", "ignore").decode("ascii").lower())


def derivar_signal(texto: str, field_path: str | None = None) -> str:
    """Campo normalizado al que se refiere una edición.

    Mira primero la RUTA (cuando el editor la da, es exacta) y después la frase
    del cambio. Lo que no encaja en ninguna regla queda como "otro": preferimos
    un cubo honesto a colgarle al coach un patrón que no es suyo."""
    base = _sin_acentos(f"{field_path or ''} {texto or ''}")
    for signal, claves in _SIGNAL_RULES:
        if any(k in base for k in claves):
            # Cambiar "Tostada → Tortilla" en el desayuno habla del ALIMENTO, no
            # de cuánto va en esa toma: si la frase es una sustitución de texto,
            # el reparto no es la señal correcta.
            if signal == "nutricion.reparto" and derivar_sustitucion(texto):
                return "nutricion.alimentos"
            return signal
    return "otro"


def etiqueta_de_signal(signal: str) -> str:
    """La señal en cristiano, para enseñársela al coach."""
    return SIGNAL_LABELS.get(signal or "", SIGNAL_LABELS["otro"])


def derivar_sustitucion(texto: str) -> tuple[str, str] | None:
    """('pollo', 'pavo') de una frase de cambio, o None si no es una sustitución.

    Las frases del diff vienen como «Ejercicio 2: Sentadilla → Prensa» o
    «Calorías: 2000 → 2180 kcal». Solo interesan las de TEXTO: un cambio de
    cifra no es una preferencia, es un ajuste, y meterlo aquí llenaría los
    patrones de "siempre cambias 2000 por 2180"."""
    import re

    if not texto:
        return None
    m = re.search(r"([^:→\n]{2,60}?)\s*(?:→|->)\s*([^→\n]{2,60})", texto)
    if not m:
        return None
    izq, der = m.group(1).strip(" .;,"), m.group(2).strip(" .;,")
    # El lado izquierdo suele traer pegada la etiqueta ("Ejercicio 2: Sentadilla").
    if ":" in izq:
        izq = izq.rsplit(":", 1)[-1].strip()
    if not izq or not der:
        return None
    # Cifras fuera: cambiar 2000 kcal por 2180 no es "preferir" nada.
    def _es_cifra(x: str) -> bool:
        return bool(re.fullmatch(r"[\d\s.,]+(?:\s*[a-zA-Z%º°]{1,6})?", x.strip()))

    if _es_cifra(izq) or _es_cifra(der):
        return None
    if _sin_acentos(izq) == _sin_acentos(der):
        return None
    return izq[:90], der[:90]
