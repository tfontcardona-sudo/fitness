"""¿Va bien la planificación de este cliente? — progreso hacia SU objetivo.

Petición del dueño: "el programa debe analizar los datos actualizados del
cliente en función de su objetivo, y decir al coach si está o no haciendo
bien la planificación... si no, los puntos/evidencia de por qué no; si sí,
los puntos fuertes a optimizar".

DETERMINISTA, y sobre todo UNA SOLA VERDAD: esto no inventa un segundo
criterio de "¿va bien?" — traduce a lenguaje de coach la MISMA decisión que
ya toma el motor quincenal (`biweekly_engine.decide_biweekly`, hardening §8)
sobre la última revisión cerrada. Si mañana se afina un umbral del motor
(ritmo diana, corte de adherencia…), este veredicto lo hereda solo, en vez de
quedarse con una regla vieja que contradice a la revisión real.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, Period
from app.services.biweekly_engine import decide_biweekly
from app.services.biweekly_period import checkin_inputs_from_period

_GOAL_LABEL = {
    "fat_loss": "perder grasa",
    "muscle_gain": "ganar músculo",
    "recomp": "recomposición (bajar grasa sin perder músculo)",
    "maintenance": "mantenerse",
    "injury_recovery": "volver de su lesión",
}

# Reglas de decide_biweekly que significan "va bien" / "dato insuficiente".
# Todo lo demás (adjust_kcal, work_adherence, diet_break) es "necesita ajuste".
_EN_MARCHA = {"dentro_del_ritmo", "recomposicion_en_marcha", "sin_cambio_neto"}
_SIN_DATO = {"dato_insuficiente", "posible_ciclo_menstrual"}


def _fmt_pct(ratio: float) -> str:
    return f"{ratio * 100:.0f} %"


def _fmt_rate(pct: float) -> str:
    return f"{pct:+.2f} %/semana"


def evaluate_goal_progress(db: Session, client: Client) -> dict | None:
    """Progreso hacia SU objetivo, con la última revisión CERRADA como base.

    `None` si aún no hay ninguna (cliente nuevo o en su primera quincena):
    "no está haciéndolo mal", simplemente no hay con qué juzgar todavía —
    eso también es información, y `None` deja que quien lo muestre lo diga
    así en vez de fabricar un veredicto sobre nada.
    """
    period = db.scalar(
        select(Period).where(
            Period.client_id == client.id,
            Period.status.in_(("closed", "analyzed")),
        ).order_by(Period.period_index.desc()).limit(1)
    )
    if period is None:
        return None

    inputs = checkin_inputs_from_period(db, period, client)
    decision = decide_biweekly(inputs)
    goal_label = _GOAL_LABEL.get(client.goal_type or "", "su objetivo")
    rate = decision.inputs_snapshot.get("actual_rate_pct_week")

    evidence: list[str] = []
    strengths: list[str] = []

    if decision.rule in _SIN_DATO:
        status = "insufficient_data"
        headline = "Datos insuficientes para valorar su progreso"
        evidence.append(decision.rationale)
    elif decision.rule in _EN_MARCHA:
        status = "on_track"
        headline = f"Va bien hacia su objetivo de {goal_label}"
        if rate is not None and client.goal_type not in (None, "maintenance", "recomp", "injury_recovery"):
            strengths.append(f"Ritmo real {_fmt_rate(rate)}: dentro de lo esperado para su objetivo")
        strengths.append(f"Adherencia a la dieta del {_fmt_pct(inputs.adherence_diet_ratio)}")
        if decision.rule == "recomposicion_en_marcha":
            strengths.append("Peso estable con perímetros bajando y fuerza subiendo: recomposición real")
        if inputs.strength_trend == "up":
            strengths.append("Fuerza al alza respecto a su revisión anterior")
        strengths.extend(decision.notes)  # p. ej. "8 semanas en déficit: valora un refeed"
    else:
        status = "needs_attention"
        headline = f"Su plan necesita un ajuste para seguir hacia {goal_label}"
        evidence.append(decision.rationale)
        if decision.rule != "adherencia_baja":
            evidence.append(f"Adherencia a la dieta del {_fmt_pct(inputs.adherence_diet_ratio)}")
        if inputs.strength_trend == "down":
            evidence.append("La fuerza ha bajado respecto a su revisión anterior")

    # Señal secundaria válida en cualquier estado: fatiga alta sostenida no es
    # "el objetivo no avanza", pero SÍ es algo que el coach debe ver.
    if (inputs.fatigue_now or 0) >= 4.0:
        evidence.append(f"Fatiga media alta ({inputs.fatigue_now:.1f}/5) en su última revisión")

    return {
        "status": status,
        "headline": headline,
        "evidence": evidence,
        "strengths": strengths,
        "period_index": period.period_index,
        "rule": decision.rule,
    }
