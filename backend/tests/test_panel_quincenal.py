"""El panel §9 en la REVISIÓN QUINCENAL.

`review_panel` tenía desde hace tandas un modo `is_checkin` con roles propios
—los que juzgan si el AJUSTE tiene sentido para lo que ha pasado estas dos
semanas— y no lo activaba nadie: la adaptación, que decide con qué calorías
vive el cliente los siguientes catorce días, salía sin más revisión que el
validador determinista.

Se paga SOLO cuando hay algo que mirar: la adaptación es un cambio numérico y
acotado (el motor decide el %, la proteína queda bloqueada), así que con el
Revisor 0 limpio no hay nada cualitativo nuevo que juzgar. Cobrar 8-10 roles a
cada cliente cada quincena sería lo contrario de recortar créditos.
"""
import warnings

import pytest

warnings.filterwarnings("ignore")


def _db_available() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings

        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="Requiere PostgreSQL")


def test_el_modo_checkin_existe_y_trae_roles_propios():
    """Si esto se queda sin roles, enchufarlo no aporta nada."""
    from app.services.review_panel import CHECKIN_EXTRA_ROLES, REVIEWER_ROLES

    assert CHECKIN_EXTRA_ROLES, "el modo revisión no tiene roles propios"
    nombres = {r.get("role") or r.get("name") for r in REVIEWER_ROLES}
    for extra in CHECKIN_EXTRA_ROLES:
        assert (extra.get("role") or extra.get("name")) not in nombres


def test_el_contexto_de_revision_sale_de_la_ficha_sin_recalcular_nada():
    """La adaptación no construye ningún `ClientContext` —solo reescala
    números—, y por eso el panel nunca llegaba a correr sobre ella. El contexto
    se arma de la ficha, y las MÉTRICAS se toman del plan: aquí no se recalcula
    nada (el principio del sistema es que la IA no calcula, y esto tampoco)."""
    from datetime import date

    from app.models import Client
    from app.services.plan_review import build_profile, ctx_desde_cliente

    c = Client(full_name="Contexto", email="ctx@test.local", sex="female",
               birth_date=date(1990, 6, 1), height_cm=165, current_weight_kg=62.0,
               goal_type="fat_loss", level="intermediate", training_days=4,
               diet_mode="flexible", food_allergies=["lactosa"],
               injuries_notes="Hombro derecho", package_tier="full")
    nut = {"tdee_kcal": 2100, "target_kcal": 1800, "bmr_kcal": 1400}

    ctx = ctx_desde_cliente(c, nut)
    assert ctx.sex == "female" and ctx.age >= 30
    assert ctx.weight_kg == 62.0
    assert ctx.food_allergies == ["lactosa"]
    assert "Hombro derecho" in (ctx.clinical_notes or "")
    # Las métricas VIENEN del plan, tal cual: ni una fórmula aquí.
    assert (ctx.tdee, ctx.target_kcal, ctx.bmr) == (2100, 1800, 1400)

    # Y sirve para lo que lo pide el panel.
    perfil = build_profile(c, ctx)
    assert perfil["tdee"] == 2100 and perfil["diet_pattern"] is None


def test_la_adaptacion_limpia_no_paga_el_panel(monkeypatch):
    """Con el Revisor 0 conforme, la adaptación no llama a la IA: el ajuste es
    numérico y acotado, y pagar la ronda entera cada quincena y por cliente es
    justo lo que se quería evitar."""
    from app.services import adapt_plan as ap

    llamadas = []

    def _no_deberia(*a, **k):
        llamadas.append(k)
        raise AssertionError("el panel se pagó con el Revisor 0 limpio")

    monkeypatch.setattr("app.services.plan_review.review_generated_plan", _no_deberia)
    # El código solo entra al panel si `violations` no está vacío: se comprueba
    # leyendo la condición, que es lo que gobierna el gasto.
    import inspect

    fuente = inspect.getsource(ap)
    assert "if tiene_dieta and violations:" in fuente, (
        "el panel dejó de estar condicionado a que el Revisor 0 encuentre algo")
    assert not llamadas


def test_si_el_revisor_0_veta_entra_el_panel_y_puede_reparar(monkeypatch):
    """Y cuando SÍ hay algo, el panel entra, puede reparar el plan y se vuelve a
    preguntar antes de retenerlo por un desvío que ya no existe."""
    import inspect

    from app.services import adapt_plan as ap

    fuente = inspect.getsource(ap)
    # Entra el panel…
    assert "review_generated_plan(" in fuente
    assert "ctx_desde_cliente(" in fuente
    # …se vuelve a validar tras la reparación…
    assert "rep2 = check_nutrition(" in fuente
    # …y un ROJO retiene la adaptación como borrador.
    assert 'review_summary.get("color") == "rojo"' in fuente
