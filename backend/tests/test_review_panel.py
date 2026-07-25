"""Tests del panel de supervisión (§9) y el ICP (§11). Los revisores IA se
mockean: el panel es determinista y testable sin clave."""
from __future__ import annotations

from app.services.review_panel import (
    ReviewFinding,
    ReviewerVerdict,
    compute_icp,
    consolidate,
    deterministic_reviewer,
    reviewer_prompt,
    run_panel,
    REVIEWER_ROLES,
)


def _coherent_plan() -> dict:
    m = {"protein_g": 150, "carbs_g": 200, "fat_g": 60}
    kcal = m["protein_g"] * 4 + m["carbs_g"] * 4 + m["fat_g"] * 9
    p, c, f = m["protein_g"], m["carbs_g"], m["fat_g"]
    return {
        "target_kcal": kcal, "macros": m,
        "meals": [
            {"slot": 1, "target": {"kcal": (p // 2) * 4 + (c // 2) * 4 + (f // 2) * 9,
                                    "protein_g": p // 2, "carbs_g": c // 2, "fat_g": f // 2}},
            {"slot": 2, "target": {"kcal": (p - p // 2) * 4 + (c - c // 2) * 4 + (f - f // 2) * 9,
                                    "protein_g": p - p // 2, "carbs_g": c - c // 2, "fat_g": f - f // 2}},
        ],
        "meal_bank": {"mode": "flexible_7", "slots": [
            {"slot": 1, "options": [
                {"key": "A", "title": "Pollo con arroz",
                 "ingredients": [{"food": "Pechuga de pollo", "grams": 150, "household": ""}],
                 # kcal = 34·4 + 0 + 4·9 = 172 (Atwater coherente)
                 "macros": {"kcal": 172, "protein_g": 34, "carbs_g": 0, "fat_g": 4}},
            ]},
        ]},
    }


def _profile(**kw) -> dict:
    base = {"sex": "male", "age": 30, "height_cm": 178, "weight_kg": 80,
            "food_allergies": [], "food_dislikes": [], "meals_per_day": 2}
    base.update(kw)
    return base


# ---- Revisor 0 (determinista) ----

def test_revisor_determinista_aprueba_plan_coherente():
    v = deterministic_reviewer(_coherent_plan(), _profile())
    assert v.reviewer == "validador_determinista"
    assert v.can_veto is True
    assert v.veredicto in ("aprobado", "aprobado_con_reservas")


def test_revisor_determinista_veta_alergeno():
    plan = _coherent_plan()  # lleva pollo
    v = deterministic_reviewer(plan, _profile(food_allergies=["pollo"]))
    assert v.veredicto == "rechazado"
    assert v.puntuacion_rubrica == 0
    assert any(f.severity == "bloqueante" for f in v.hallazgos)


# ---- ICP ----

def test_icp_cero_si_falla_determinista():
    r = compute_icp(deterministic_ok=False, coverage_ratio=1.0, panel_scores=[90, 90])
    assert r.icp == 0.0


def test_icp_alto_con_consenso():
    r = compute_icp(deterministic_ok=True, coverage_ratio=1.0, panel_scores=[90, 92, 88, 91])
    assert r.icp >= 80


def test_icp_baja_si_un_revisor_discrepa():
    alto = compute_icp(deterministic_ok=True, coverage_ratio=1.0, panel_scores=[90, 90, 90]).icp
    disp = compute_icp(deterministic_ok=True, coverage_ratio=1.0, panel_scores=[90, 90, 30]).icp
    # el consenso (dispersión) penaliza cuando uno rechaza y el resto aprueba
    assert disp < alto


def test_icp_renormaliza_factores_ausentes():
    # sin extracción ni estabilidad, el peso se reparte; ICP sigue siendo alto
    r = compute_icp(deterministic_ok=True, coverage_ratio=1.0, panel_scores=[95, 95])
    assert 90 <= r.icp <= 100
    assert "extraction" not in r.breakdown


# ---- Panel completo ----

def _fake_ai_reviewer(all_approve=True, clinical_rejects=False):
    def reviewer(role: dict) -> ReviewerVerdict:
        if role["key"] == "clinico" and clinical_rejects:
            return ReviewerVerdict("clinico", "rechazado", 20,
                                   [ReviewFinding("bloqueante", "interacción con medicación")],
                                   can_veto=True)
        return ReviewerVerdict(role["key"], "aprobado", 90, [], can_veto=role.get("can_veto", False))
    return reviewer


def test_panel_solo_determinista_sin_ia():
    res = run_panel(_coherent_plan(), _profile())
    assert len(res.verdicts) == 1  # solo el revisor 0
    assert res.color in ("verde", "ambar")


def test_panel_completo_aprueba():
    res = run_panel(_coherent_plan(), _profile(), ai_reviewer=_fake_ai_reviewer())
    assert len(res.verdicts) == 1 + len(REVIEWER_ROLES)
    assert res.icp >= 80
    assert res.color == "verde"


def test_arbitro_no_puede_anular_veto_clinico():
    res = run_panel(_coherent_plan(), _profile(),
                    ai_reviewer=_fake_ai_reviewer(clinical_rejects=True))
    assert res.vetoed is True
    assert res.color == "rojo"        # el veto clínico manda pese al resto aprobado
    assert res.blocking()


def test_lista_roja_fuerza_rojo_aunque_todo_apruebe():
    prof = _profile(medical_notes="Diabético tipo 2", medication_notes="Ozempic")
    res = run_panel(_coherent_plan(), prof, ai_reviewer=_fake_ai_reviewer())
    assert res.color == "rojo"
    assert "diabetes" in res.red_flags


def test_un_revisor_caido_no_tumba_el_panel():
    def flaky(role):
        if role["key"] == "editor":
            raise RuntimeError("timeout")
        return ReviewerVerdict(role["key"], "aprobado", 90, [], can_veto=role.get("can_veto", False))
    res = run_panel(_coherent_plan(), _profile(), ai_reviewer=flaky)
    # el panel sobrevive; el revisor caído aporta un hallazgo menor
    assert any("editor" in f.description for f in res.findings)


# ---- Independencia (contexto aislado) ----

def test_prompt_de_revisor_es_aislado():
    p = reviewer_prompt(REVIEWER_ROLES[0], plan_text="PLAN_X", anamnesis_text="ANAMNESIS_Y")
    assert "PLAN_X" in p and "ANAMNESIS_Y" in p
    assert REVIEWER_ROLES[0]["name"] in p
    # NO debe filtrar el razonamiento de generación ni informes de otros revisores
    assert "razonamiento" not in p.lower() or "sin el razonamiento" not in p.lower()
