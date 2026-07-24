"""Tests de §3 (hardening): energía individualizada, TDEE por componentes y
reparto completo de macros. Todos contra valores calculados a mano."""
from __future__ import annotations

import pytest

from app.services.metrics import (
    energy_targets,
    individualized_energy_adjustment,
    macro_targets,
    tdee_by_components,
)


# --- Ajuste energético individualizado ---------------------------------------

def test_perdida_grasa_alto_vs_bajo_reciben_deficit_distinto():
    """El fallo #3 del audit: el punto medio daba a un 12% y a un 35% el MISMO
    déficit. Ahora un graso alto recibe más déficit que uno bajo."""
    alto = individualized_energy_adjustment("fat_loss", "male", body_fat_pct=30)
    bajo = individualized_energy_adjustment("fat_loss", "male", body_fat_pct=12)
    assert alto.pct < bajo.pct   # alto = déficit MÁS negativo
    assert alto.bracket == "fat_loss/high"
    assert bajo.bracket == "fat_loss/low"
    # punto medio de cada rango (sin adherencia): high=(−0.20,−0.25)→−0.225
    assert alto.pct == pytest.approx(-0.225)
    assert bajo.pct == pytest.approx(-0.125)  # low=(−0.10,−0.15)


def test_umbral_de_grasa_por_sexo():
    # Mujer al 30% es "medium" (umbral alto 32); hombre al 30% es "high" (25).
    assert individualized_energy_adjustment("fat_loss", "female", 30).bracket == "fat_loss/medium"
    assert individualized_energy_adjustment("fat_loss", "male", 30).bracket == "fat_loss/high"


def test_ganancia_novato_vs_avanzado():
    nov = individualized_energy_adjustment("muscle_gain", "male", None, level="beginner")
    adv = individualized_energy_adjustment("muscle_gain", "male", None, level="advanced")
    assert nov.pct > adv.pct    # novato tolera más superávit
    assert nov.pct == pytest.approx(0.135)  # (0.12,0.15) mid
    assert adv.pct == pytest.approx(0.075)  # (0.05,0.10) mid


def test_adherencia_mueve_el_punto_del_rango():
    buena = individualized_energy_adjustment("fat_loss", "male", 30, adherence_ratio=0.9)
    mala = individualized_energy_adjustment("fat_loss", "male", 30, adherence_ratio=0.4)
    assert buena.pct == pytest.approx(-0.25)   # extremo agresivo
    assert mala.pct == pytest.approx(-0.20)    # extremo conservador


def test_recomp_y_mantenimiento():
    assert individualized_energy_adjustment("recomp", "male", 18).pct == pytest.approx(-0.025)
    assert individualized_energy_adjustment("maintenance", "male", 18).pct == 0.0


# --- TDEE por componentes -----------------------------------------------------

def test_tdee_por_componentes_valores_a_mano():
    # BMR 1700, 80 kg, 8000 pasos, 4 sesiones × 60 min, MET 6.
    # NEAT = 8000·80·0.00045 = 288
    # EAT  = 4·60·6·80/60/7 = 4·60·6·80 = 115200 /60 =1920 /7 = 274.285… → 274.3
    # ETA  = 0.10·(1700+288+274.285…) = 226.228… → 226.2
    # total = 1700+288+274.285+226.228 = 2488.514 → 2488.5
    c = tdee_by_components(1700, 80, 8000, 4, 60, met=6)
    assert c.neat == pytest.approx(288.0)
    assert c.eat == pytest.approx(274.3, abs=0.1)
    assert c.eta == pytest.approx(226.2, abs=0.1)
    assert c.total == pytest.approx(2488.5, abs=0.2)


def test_energy_targets_avisa_si_componentes_divergen():
    # Sedentario que entrena 6 días: el factor clásico y los componentes pueden
    # divergir; al menos la estructura de aviso existe y no rompe.
    et = energy_targets("male", 80, 180, 30, "fat_loss", training_days=6,
                        body_fat_pct=20, daily_activity="sedentary", level="intermediate")
    assert et.tdee_components is not None
    assert isinstance(et.warnings, list)


# --- Reparto completo de macros ----------------------------------------------

def test_macro_split_respeta_suelos_de_grasa_y_carbohidratos():
    # Hombre 80 kg, fat_loss, 2000 kcal, entrena 4 días (suelo HC 2 g/kg = 160 g).
    m = macro_targets("male", 80, "fat_loss", 2000, training_days=4)
    # proteína: PROTEIN_RANGE fat_loss (2.0,2.4) mid 2.2 → 80·2.2 = 176
    assert m.protein_g == 176
    # grasa: max(80·0.6=48, 20% de 2000/9=44.4) = 48 g, dentro de 35%
    assert m.fat_g == 48
    # carbs = (2000 - 176·4 - 48·9)/4 = (2000-704-432)/4 = 864/4 = 216 ≥ suelo 160 ✓
    assert m.carbs_g == 216
    assert m.kcal == 2000
    assert not m.notes  # cabía sin subir kcal
    # fibra 14·2000/1000 = 28 (≥25); agua 80·35 = 2800
    assert m.fiber_g_min == 28
    assert m.water_ml == 2800


def test_macro_split_sube_kcal_si_el_suelo_no_cabe():
    """Suelos no caben en las kcal → se SUBEN las kcal (nunca se rompe el suelo)."""
    # Hombre 90 kg, fat_loss, kcal muy bajas 1500, entrena 5 días (suelo HC 3 g/kg=270)
    m = macro_targets("male", 90, "fat_loss", 1500, training_days=5)
    assert m.carbs_g == 270          # suelo respetado, no roto
    assert m.kcal > 1500             # kcal subieron para que quepa
    assert m.kcal == m.protein_g * 4 + m.carbs_g * 4 + m.fat_g * 9
    assert any("suelo" in n for n in m.notes)


def test_macro_split_grasa_minima_en_mujer():
    # Mujer: suelo de grasa 0,7 g/kg (no 0,6).
    m = macro_targets("female", 60, "recomp", 1800, training_days=3)
    assert m.fat_g >= round(60 * 0.7)


def test_macro_split_kcal_siempre_cuadra_4_4_9():
    for sex in ("male", "female"):
        for goal in ("fat_loss", "muscle_gain", "recomp", "maintenance"):
            for days in (2, 4, 6):
                m = macro_targets(sex, 75, goal, 2200, training_days=days)
                assert m.kcal == m.protein_g * 4 + m.carbs_g * 4 + m.fat_g * 9
                assert m.carbs_g >= 0 and m.fat_g > 0 and m.protein_g > 0
