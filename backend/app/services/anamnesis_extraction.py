"""Extracción y control de calidad de la anamnesis (hardening §5).

Cuatro piezas:
- `detect_contradictions`: reglas DETERMINISTAS que marcan (no resuelven en
  silencio) contradicciones típicas ("perder grasa" + "ganar 5 kg", "vegano" +
  "como pollo", plazo imposible).
- `COVERAGE_MATRIX`: una fila por cada campo de la anamnesis con DÓNDE influye y
  QUÉ test lo demuestra. Un campo con influencia nula es un fallo silencioso.
- `client_portrait`: retrato del cliente en ≤10 líneas (contexto, barreras,
  motivación) que entra en los prompts de selección y redacción.
- `dual_pass_extract` / `field_confidence`: doble pase de extracción con dos
  callables independientes; discrepancia en campo crítico → revisión; confianza
  <0,85 en campo crítico → no auto-envío.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Callable


def _norm(s: str | None) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii").lower()


# Campos CRÍTICOS: una discrepancia o baja confianza aquí bloquea el auto-envío.
CRITICAL_FIELDS = frozenset({
    "sex", "birth_date", "height_cm", "start_weight_kg", "goal_type",
    "food_allergies", "medical_notes", "medication_notes",
})


@dataclass
class Contradiction:
    code: str
    detail: str
    fields: tuple[str, ...]


def detect_contradictions(profile: dict) -> list[Contradiction]:
    """Contradicciones deterministas de la anamnesis. NO las resuelve: las marca
    para revisión humana (nunca se resuelven en silencio)."""
    out: list[Contradiction] = []
    goal = _norm(profile.get("goal_type"))
    words = _norm(" ".join(str(profile.get(k) or "") for k in
                          ("lifestyle_notes", "goal_in_own_words", "sport_history")))

    # 1) Pérdida de grasa + querer GANAR peso (o al revés) en el texto libre.
    if goal == "fat_loss" and any(t in words for t in ("ganar peso", "ganar masa", "subir de peso", "coger peso")):
        out.append(Contradiction("perder_y_ganar",
                                  "objetivo pérdida de grasa pero pide ganar peso/masa en su texto",
                                  ("goal_type", "lifestyle_notes")))
    if goal == "muscle_gain" and any(t in words for t in ("perder grasa", "adelgazar", "bajar peso", "definir")):
        out.append(Contradiction("ganar_y_definir",
                                  "objetivo ganancia pero pide perder grasa/definir en su texto",
                                  ("goal_type", "lifestyle_notes")))

    # 2) Restricción dietética vs alimentos que dice comer/gustarle.
    diet = _norm(profile.get("diet_pattern"))
    likes = _norm(" ".join(profile.get("food_likes") or []) + " " + words)
    animal = ("pollo", "carne", "pescado", "atun", "huevo", "jamon", "ternera")
    if diet in ("vegano", "vegetariano") and any(a in likes for a in animal):
        hit = next(a for a in animal if a in likes)
        out.append(Contradiction("dieta_vs_alimentos",
                                  f"declara dieta '{diet}' pero menciona '{hit}'",
                                  ("diet_pattern", "food_likes")))

    # 3) Objetivo de peso + plazo físicamente imposible (>1% peso/semana sostenido).
    try:
        w = float(profile.get("start_weight_kg") or 0)
        gw = float(profile.get("goal_weight_kg") or 0)
        from datetime import date
        dl = profile.get("goal_deadline")
        if w and gw and dl:
            deadline = date.fromisoformat(str(dl))
            weeks = max(1, (deadline - date.today()).days / 7)
            rate = abs(gw - w) / w / weeks * 100  # %/semana
            if rate > 1.2:
                out.append(Contradiction("plazo_imposible",
                                          f"cambiar de {w:.0f} a {gw:.0f} kg antes de {dl} exige "
                                          f"~{rate:.1f}%/sem (>1,2% no es seguro/sostenible)",
                                          ("goal_weight_kg", "goal_deadline")))
    except (ValueError, TypeError):
        pass
    return out


# Matriz de cobertura (§5): cada campo → dónde influye → test que lo demuestra.
# Cualquier campo con influencia "" es un fallo silencioso a cerrar.
COVERAGE_MATRIX: dict[str, dict[str, str]] = {
    "sex": {"influye": "BMR, suelos de kcal y de grasa", "test": "test_metrics"},
    "birth_date": {"influye": "edad → BMR; lista roja menor/mayor", "test": "test_safety_gate"},
    "height_cm": {"influye": "BMR, IMC (lista roja)", "test": "test_metrics/test_safety_gate"},
    "start_weight_kg": {"influye": "BMR, TDEE, macros por kg, IMC", "test": "test_metrics"},
    "body_fat_pct": {"influye": "Katch-McArdle; bracket de ajuste (§3)", "test": "test_metrics_hardening"},
    "goal_type": {"influye": "ajuste kcal, proteína/grasa por kg, split", "test": "test_metrics_hardening"},
    "goal_weight_kg": {"influye": "simulación 12 sem, plazo", "test": "test_plan_quality/test_anamnesis"},
    "goal_deadline": {"influye": "contradicción de plazo imposible", "test": "test_anamnesis"},
    "level": {"influye": "bracket de ganancia, volumen, nivel de ejercicios", "test": "test_metrics_hardening"},
    "training_days": {"influye": "actividad, suelo de HC, split", "test": "test_metrics_hardening"},
    "daily_activity_level": {"influye": "NEAT/TDEE", "test": "test_metrics"},
    "session_max_min": {"influye": "duración de sesión (guardrail), TDEE EAT", "test": "test_guardrails"},
    "training_place": {"influye": "filtro de ejercicios por material", "test": "test_guardrails"},
    "equipment": {"influye": "filtro de ejercicios", "test": "test_guardrails"},
    "excluded_exercise_ids": {"influye": "filtro de ejercicios", "test": "test_guardrails"},
    "injuries_notes": {"influye": "contraindicaciones → filtro y guardrail", "test": "test_guardrails"},
    "medical_notes": {"influye": "pautas por patología; lista roja", "test": "test_safety_gate"},
    "medication_notes": {"influye": "lista roja de medicación", "test": "test_safety_gate"},
    "sport_history": {"influye": "retrato del cliente; nivel", "test": "test_anamnesis"},
    "meals_per_day": {"influye": "estructura de comidas; validador nº comidas", "test": "test_deterministic_validator"},
    "meal_schedule": {"influye": "horarios; comida peri-entreno (§6)", "test": "test_diet_training_coherence"},
    "food_allergies": {"influye": "filtro de alimentos y veto de alérgenos", "test": "test_portion_solver/test_deterministic_validator"},
    "food_dislikes": {"influye": "filtro/veto de alimentos odiados", "test": "test_deterministic_validator"},
    "food_likes": {"influye": "selección de alimentos; retrato", "test": "test_anamnesis"},
    "lifestyle_notes": {"influye": "objetivo en palabras; contradicciones; retrato", "test": "test_anamnesis"},
    "current_supplements": {"influye": "suplementación; lista roja (interacción)", "test": "test_safety_gate"},
    "diet_mode": {"influye": "flexible_7 vs strict → banco/validación", "test": "test_deterministic_validator"},
}


def coverage_gaps() -> list[str]:
    """Campos con influencia nula (fallo silencioso). Vacío = todos cubiertos."""
    return [k for k, v in COVERAGE_MATRIX.items() if not v.get("influye")]


def client_portrait(profile: dict, *, max_lines: int = 10) -> str:
    """Retrato del cliente en ≤N líneas: contexto, barreras y motivación, para
    inyectar en los prompts de selección y redacción."""
    lines: list[str] = []
    sex = "Hombre" if profile.get("sex") == "male" else "Mujer" if profile.get("sex") == "female" else "Cliente"
    goal = {"fat_loss": "perder grasa", "muscle_gain": "ganar músculo", "recomp": "recomposición",
            "maintenance": "mantenimiento", "injury_recovery": "recuperar de una lesión"}.get(
                profile.get("goal_type"), "objetivo por definir")
    lines.append(f"{sex}, objetivo: {goal}; nivel {profile.get('level') or '—'}, "
                 f"{profile.get('training_days') or '—'} días/sem.")
    if profile.get("goal_in_own_words") or profile.get("lifestyle_notes"):
        lines.append("En sus palabras: " + str(profile.get("goal_in_own_words")
                     or profile.get("lifestyle_notes"))[:160])
    if profile.get("injuries_notes"):
        lines.append("Lesiones: " + str(profile["injuries_notes"])[:120])
    if profile.get("medical_notes") or profile.get("medication_notes"):
        lines.append("Clínico: " + " · ".join(filter(None, [
            str(profile.get("medical_notes") or "")[:80],
            str(profile.get("medication_notes") or "")[:80]])))
    if profile.get("food_allergies"):
        lines.append("Alergias: " + ", ".join(profile["food_allergies"]))
    if profile.get("food_dislikes"):
        lines.append("No le gusta: " + ", ".join(profile["food_dislikes"][:8]))
    if profile.get("session_max_min"):
        lines.append(f"Dispone de ~{profile['session_max_min']} min por sesión.")
    return "\n".join(lines[:max_lines])


@dataclass
class ExtractionResult:
    data: dict
    confidence: dict[str, float]           # confianza por campo (0-1)
    discrepancies: list[str] = field(default_factory=list)
    needs_review: bool = False


def dual_pass_extract(
    pass_a: Callable[[], dict], pass_b: Callable[[], dict],
    *, critical: frozenset[str] = CRITICAL_FIELDS, min_confidence: float = 0.85,
) -> ExtractionResult:
    """Doble pase de extracción independiente. Compara los dos JSON: discrepancia
    en un campo crítico → revisión. Confianza <min en campo crítico → revisión.
    Cada callable devuelve (data, confidence) o solo data (confianza 1.0)."""
    a = pass_a()
    b = pass_b()
    da, ca = (a if isinstance(a, tuple) else (a, {}))
    db, cb = (b if isinstance(b, tuple) else (b, {}))

    merged: dict = dict(da)
    conf: dict[str, float] = {}
    discrepancies: list[str] = []
    keys = set(da) | set(db)
    for k in keys:
        va, vb = da.get(k), db.get(k)
        agree = va == vb
        base = min(float(ca.get(k, 1.0)), float(cb.get(k, 1.0)))
        conf[k] = base if agree else base * 0.5
        if not agree:
            discrepancies.append(f"{k}: pase A={va!r} vs pase B={vb!r}")

    needs_review = any(
        (k in critical) and (conf.get(k, 1.0) < min_confidence)
        for k in keys
    )
    return ExtractionResult(merged, conf, discrepancies, needs_review)
