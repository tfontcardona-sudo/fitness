"""Gate de CI del golden set (hardening §14).

Pasa cada perfil por la CAPA DETERMINISTA (energía, macros, validador determinista,
motor quincenal) y exige que:
- el ajuste energético caiga en el bracket/signo esperado,
- los macros respeten los suelos y cuadren 4/4/9,
- un plan mínimo construido con esos macros NO produzca un bloqueante,
- la decisión de check-in coincida con la esperada.

Los rangos son [POR VALIDAR] (David/Toni), pero el gate ya protege de regresiones
en la capa determinista. La CI no debe mergear si un caso produce un bloqueante.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.golden_set import GOLDEN_CHECKIN, GOLDEN_GENERATION, POR_VALIDAR
from app.services.biweekly_engine import CheckinInputs, decide_biweekly
from app.services.guardrails import validate_plan_deterministic
from app.services.metrics import energy_targets, macro_targets


@pytest.mark.parametrize("p", GOLDEN_GENERATION, ids=lambda p: p["id"])
def test_golden_generacion_capa_determinista(p):
    et = energy_targets(
        p["sex"], p["weight"], p["height"], p["age"], p["goal"],
        training_days=p["training_days"], body_fat_pct=p["body_fat"],
        daily_activity=p["activity"], level=p["level"],
    )
    # 1) bracket y signo del ajuste esperados
    assert et.bracket == p["exp_bracket"], f"{p['id']}: {et.bracket}"
    if p["exp_sign"] < 0:
        assert et.adjustment_pct <= 0
    elif p["exp_sign"] > 0:
        assert et.adjustment_pct > 0
    # 2) nunca por debajo del suelo calórico seguro
    assert et.target_kcal >= max(et.bmr, 1400 if p["sex"] == "female" else 1600) - 1

    # 3) reparto de macros: suelos respetados y kcal = 4/4/9 exacto
    mp = macro_targets(p["sex"], p["weight"], p["goal"], et.target_kcal, p["training_days"])
    assert mp.kcal == mp.protein_g * 4 + mp.carbs_g * 4 + mp.fat_g * 9
    assert mp.fat_g >= round(p["weight"] * (0.7 if p["sex"] == "female" else 0.6)) - 1
    assert mp.protein_g > 0 and mp.carbs_g >= 0
    assert mp.fiber_g_min >= 25

    # 4) un plan mínimo COHERENTE con esos macros no produce bloqueante determinista
    plan = {
        "target_kcal": mp.kcal,
        "macros": {"protein_g": mp.protein_g, "carbs_g": mp.carbs_g, "fat_g": mp.fat_g},
        "meals": [{"slot": 1, "target": {"kcal": mp.kcal, "protein_g": mp.protein_g,
                                          "carbs_g": mp.carbs_g, "fat_g": mp.fat_g}}],
        "meal_bank": {"mode": "flexible_7", "slots": []},
    }
    r = validate_plan_deterministic(plan, objective_macros={
        "kcal": mp.kcal, "protein_g": mp.protein_g, "carbs_g": mp.carbs_g, "fat_g": mp.fat_g})
    assert r.ok, f"{p['id']} bloqueado: {r.violations}"


def _points(start_kg: float, weekly_delta: float, n: int = 8):
    d0 = date(2026, 1, 1)
    return [(d0 + timedelta(days=2 * i), round(start_kg + weekly_delta * (2 * i / 7), 2))
            for i in range(n)]


@pytest.mark.parametrize("c", GOLDEN_CHECKIN, ids=lambda c: c["id"])
def test_golden_checkin_decision_determinista(c):
    pts = ([(date(2026, 1, 1), c["weight"])] if c.get("single")
           else _points(c["weight"], c["weekly_delta_kg"]))
    inp = CheckinInputs(
        goal_type=c["goal"], weight_kg=c["weight"], target_rate_pct_week=c["rate"],
        weight_points=pts, adherence_diet_ratio=c["adherence"],
        perimeters_trend=c.get("perimeters"), strength_trend=c.get("strength"),
        fatigue_now=c.get("fatigue_now"), fatigue_prev=c.get("fatigue_prev"),
        single_measurement=c.get("single", False),
    )
    dec = decide_biweekly(inp)
    assert dec.action == c["exp_action"], f"{c['id']}: {dec.action} ({dec.rule})"
    if dec.action == "adjust_kcal":
        assert dec.protein_locked is True  # la proteína nunca se toca


def test_golden_set_marcado_por_validar():
    # Recordatorio explícito en la suite: los rangos aún NO están validados por Toni/David.
    assert POR_VALIDAR is True
