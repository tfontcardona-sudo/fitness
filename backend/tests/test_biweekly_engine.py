"""Tests del motor de decisión quincenal (hardening §8). Cada escenario es también
un caso de check-in del golden set (§14)."""
from __future__ import annotations

from datetime import date, timedelta

from app.services.biweekly_engine import CheckinInputs, decide_biweekly


def _points(start_kg: float, weekly_delta: float, n: int = 8) -> list[tuple[date, float]]:
    """n pesajes cada 2 días con una tendencia semanal dada."""
    d0 = date(2026, 1, 1)
    return [(d0 + timedelta(days=2 * i), round(start_kg + weekly_delta * (2 * i / 7), 2))
            for i in range(n)]


def test_un_solo_pesaje_pide_mas_datos():
    inp = CheckinInputs(goal_type="fat_loss", weight_kg=80,
                        target_rate_pct_week=(-0.5, -0.7),
                        weight_points=[(date(2026, 1, 1), 80.0)],
                        single_measurement=True)
    dec = decide_biweekly(inp)
    assert dec.action == "request_data"
    assert dec.kcal_delta_pct == 0.0
    assert dec.rule == "dato_insuficiente"


def test_ciclo_menstrual_no_toca():
    inp = CheckinInputs(goal_type="fat_loss", weight_kg=60,
                        target_rate_pct_week=(-0.5, -0.7),
                        weight_points=_points(60, +0.3),  # subió (agua)
                        adherence_diet_ratio=0.9, menstrual_confound=True)
    dec = decide_biweekly(inp)
    assert dec.action == "request_data"
    assert dec.rule == "posible_ciclo_menstrual"


def test_adherencia_baja_prohibe_tocar_kcal():
    inp = CheckinInputs(goal_type="fat_loss", weight_kg=80,
                        target_rate_pct_week=(-0.5, -0.7),
                        weight_points=_points(80, -0.1),  # casi no baja
                        adherence_diet_ratio=0.5)
    dec = decide_biweekly(inp)
    assert dec.action == "work_adherence"
    assert dec.kcal_delta_pct == 0.0
    assert dec.rule == "adherencia_baja"


def test_fatiga_roja_dos_revisiones_diet_break():
    inp = CheckinInputs(goal_type="fat_loss", weight_kg=80,
                        target_rate_pct_week=(-0.5, -0.7),
                        weight_points=_points(80, -0.5),
                        adherence_diet_ratio=0.9, fatigue_now=4.5, fatigue_prev=4.2)
    dec = decide_biweekly(inp)
    assert dec.action == "diet_break"
    assert dec.rule == "fatiga_roja_2_revisiones"


def test_recomposicion_en_marcha_no_toca():
    inp = CheckinInputs(goal_type="recomp", weight_kg=75,
                        target_rate_pct_week=(0.0, 0.0),
                        weight_points=_points(75, 0.0),  # peso plano
                        adherence_diet_ratio=0.9,
                        perimeters_trend="down", strength_trend="up")
    dec = decide_biweekly(inp)
    assert dec.action == "hold"
    assert dec.rule == "recomposicion_en_marcha"


def test_dentro_del_ritmo_no_se_toca():
    inp = CheckinInputs(goal_type="fat_loss", weight_kg=80,
                        target_rate_pct_week=(-0.5, -0.7),
                        weight_points=_points(80, -0.48),  # ~-0.6 %/sem → dentro
                        adherence_diet_ratio=0.9)
    dec = decide_biweekly(inp)
    assert dec.action == "hold"
    assert dec.rule == "dentro_del_ritmo"


def test_perder_demasiado_lento_aumenta_deficit():
    inp = CheckinInputs(goal_type="fat_loss", weight_kg=80,
                        target_rate_pct_week=(-0.5, -0.7),
                        weight_points=_points(80, -0.05),  # ~-0.06 %/sem → muy lento
                        adherence_diet_ratio=0.95)
    dec = decide_biweekly(inp)
    assert dec.action == "adjust_kcal"
    assert dec.kcal_delta_pct < 0     # más déficit
    assert dec.protein_locked is True
    assert dec.rule == "fuera_del_ritmo"


def test_bajar_demasiado_rapido_reduce_deficit():
    inp = CheckinInputs(goal_type="fat_loss", weight_kg=80,
                        target_rate_pct_week=(-0.5, -0.7),
                        weight_points=_points(80, -1.2),  # ~-1.5 %/sem → muy rápido
                        adherence_diet_ratio=0.95)
    dec = decide_biweekly(inp)
    assert dec.action == "adjust_kcal"
    assert dec.kcal_delta_pct > 0     # se sube kcal (menos déficit)


def test_refeed_tras_muchas_semanas_de_deficit():
    inp = CheckinInputs(goal_type="fat_loss", weight_kg=80,
                        target_rate_pct_week=(-0.5, -0.7),
                        weight_points=_points(80, -0.48),
                        adherence_diet_ratio=0.9, weeks_in_deficit=10)
    dec = decide_biweekly(inp)
    assert dec.action == "hold"
    assert any("refeed" in n or "diet break" in n for n in dec.notes)


def test_ganancia_demasiado_rapida_reduce_superavit():
    inp = CheckinInputs(goal_type="muscle_gain", weight_kg=70,
                        target_rate_pct_week=(0.1, 0.25),
                        weight_points=_points(70, +0.6),  # ~+0.85 %/sem → muy rápido
                        adherence_diet_ratio=0.95)
    dec = decide_biweekly(inp)
    assert dec.action == "adjust_kcal"
    assert dec.kcal_delta_pct < 0     # baja kcal (menos grasa)


def test_cada_decision_guarda_regla_y_datos():
    inp = CheckinInputs(goal_type="fat_loss", weight_kg=80,
                        target_rate_pct_week=(-0.5, -0.7),
                        weight_points=_points(80, -0.48),
                        adherence_diet_ratio=0.9)
    dec = decide_biweekly(inp)
    assert dec.rule
    assert dec.rationale
    assert dec.inputs_snapshot["goal_type"] == "fat_loss"
    assert "actual_rate_pct_week" in dec.inputs_snapshot
