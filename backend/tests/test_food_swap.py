"""Cambiar UN alimento de una opción del banco — sin regenerar el plan.

Escenario real (la alerta "plan_dislike_conflict" de la ficha): el cliente ya
no tolera/odia un alimento que su plan activo lleva en una toma. El coach debe
poder arreglarlo AHÍ MISMO — el backend fija los gramos con el solver
(`portion_solver.snap_option_ingredients`), revalida con el Revisor 0
determinista y activa la nueva versión sola si no hay violación.

Requiere PostgreSQL (usa el catálogo de alimentos YA sembrado por
`app.seeds.foods_data`: "Avena en copos", "Clara de huevo", "Quinoa",
"Plátano" — reutilizarlos evita chocar con la restricción UNIQUE de
`foods.canonical_name`).
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest


def _db() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings
        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db(), reason="Requiere PostgreSQL")


def _mk_client(db, **over):
    from app.models import Client
    base = dict(
        full_name="Swap Client", email=f"swap-{uuid.uuid4().hex[:8]}@x.com",
        portal_token=f"tok-{uuid.uuid4().hex}",
        sex="female", birth_date=date(1992, 3, 4),
        height_cm=165, current_weight_kg=62.0,
        goal_type="fat_loss", level="intermediate", training_days=4, status="active",
        diet_mode="flexible_7", food_dislikes=["avena"],
    )
    base.update(over)
    c = Client(**base)
    db.add(c)
    db.flush()
    return c


def _food_id(db, canonical_name: str) -> int:
    from sqlalchemy import select

    from app.models import Food
    f = db.scalar(select(Food).where(Food.canonical_name == canonical_name))
    assert f is not None, f"seed food no encontrado: {canonical_name}"
    return f.id


def _mk_plan_with_option(db, client_id, *, avena_id: int, clara_id: int) -> "Plan":  # noqa: F821
    """Un plan mínimo pero AUTOCONSISTENTE (Atwater exacto) con una sola toma,
    una sola opción (avena + clara), tal y como la alerta del ejemplo real."""
    from app.models import Plan
    nutrition = {
        "target_kcal": 555,
        "macros": {"protein_g": 45, "carbs_g": 60, "fat_g": 15},
        "meals": [
            {"slot": 1, "name": "Desayuno",
             "target": {"kcal": 555, "protein_g": 45, "carbs_g": 60, "fat_g": 15}},
        ],
        "meal_bank": {
            "mode": "flexible_7",
            "slots": [
                {
                    "slot": 1,
                    "options": [
                        {
                            "title": "Tortilla de claras con avena y plátano",
                            "ingredients": [
                                {"food": "Avena en copos", "food_id": avena_id,
                                 "grams": 80, "household": "8 cucharadas"},
                                {"food": "Clara de huevo", "food_id": clara_id,
                                 "grams": 150, "household": "5 claras"},
                            ],
                            "macros": {"kcal": 359, "protein_g": 27.3,
                                       "carbs_g": 49.05, "fat_g": 5.9},
                        },
                    ],
                },
            ],
        },
    }
    pl = Plan(client_id=client_id, month_index=1, version=1, status="draft",
              nutrition_json=nutrition, generated_by="ia", goal_type="fat_loss")
    db.add(pl)
    db.flush()
    return pl


def test_swap_sustituye_el_alimento_recalcula_gramos_y_activa():
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import Plan, PlanEdit
    from app.services.food_swap import apply_food_swap

    with SessionLocal() as db:
        c = _mk_client(db)
        avena_id = _food_id(db, "Avena en copos")
        clara_id = _food_id(db, "Clara de huevo")
        quinoa_id = _food_id(db, "Quinoa")
        plan = _mk_plan_with_option(db, c.id, avena_id=avena_id, clara_id=clara_id)
        db.commit()

        result = apply_food_swap(
            db, client=c, plan=plan, slot=1, option_index=0,
            old_food_id=avena_id, new_food_id=quinoa_id,
        )

        assert not result.retained
        assert result.guardrail_flags == [] or all(
            not f.startswith("violation:") for f in result.guardrail_flags
        )
        assert "quinoa" in result.option_title.lower()
        assert "avena" not in result.option_title.lower()

        new_plan = db.get(Plan, result.new_plan_id)
        assert new_plan.status == "published"
        assert new_plan.generated_by == "swap"
        opt = new_plan.nutrition_json["meal_bank"]["slots"][0]["options"][0]
        ids = {i["food_id"] for i in opt["ingredients"]}
        assert avena_id not in ids
        assert quinoa_id in ids
        # El solver fija los gramos — no se conservan los de la IA (80/150).
        quinoa_ing = next(i for i in opt["ingredients"] if i["food_id"] == quinoa_id)
        assert 0 < quinoa_ing["grams"] <= 120  # tope del catálogo (mn=40, mx=120)

        # El plan ORIGINAL sigue intacto (nueva versión, no mutación in-place).
        assert plan.nutrition_json["meal_bank"]["slots"][0]["options"][0]["ingredients"][0]["food_id"] == avena_id

        # §13: el swap deja rastro para el aprendizaje.
        edit = db.scalar(
            select(PlanEdit).where(PlanEdit.plan_id == new_plan.id)
            .order_by(PlanEdit.id.desc()).limit(1)
        )
        assert edit is not None
        assert edit.source == "swap"
        assert edit.category == "seleccion_alimentos"
        assert edit.signal == "nutricion.alimento"
        assert "Avena en copos" in edit.detail and "Quinoa" in edit.detail
        db.rollback()


def test_swap_rechaza_alimento_que_tambien_choca():
    from app.db import SessionLocal
    from app.services.food_swap import apply_food_swap

    with SessionLocal() as db:
        c = _mk_client(db, food_dislikes=["avena", "platano"])
        avena_id = _food_id(db, "Avena en copos")
        clara_id = _food_id(db, "Clara de huevo")
        platano_id = _food_id(db, "Plátano")
        plan = _mk_plan_with_option(db, c.id, avena_id=avena_id, clara_id=clara_id)
        db.commit()

        with pytest.raises(ValueError, match="también choca"):
            apply_food_swap(
                db, client=c, plan=plan, slot=1, option_index=0,
                old_food_id=avena_id, new_food_id=platano_id,
            )
        db.rollback()


def test_swap_rechaza_menu_strict():
    from app.db import SessionLocal
    from app.models import Plan
    from app.services.food_swap import apply_food_swap

    with SessionLocal() as db:
        c = _mk_client(db)
        avena_id = _food_id(db, "Avena en copos")
        quinoa_id = _food_id(db, "Quinoa")
        plan = Plan(client_id=c.id, month_index=1, version=1, status="draft",
                    nutrition_json={"meal_bank": {"mode": "strict", "days": []}},
                    generated_by="ia")
        db.add(plan)
        db.flush()
        db.commit()

        with pytest.raises(ValueError, match="Word"):
            apply_food_swap(
                db, client=c, plan=plan, slot=1, option_index=0,
                old_food_id=avena_id, new_food_id=quinoa_id,
            )
        db.rollback()


def test_swap_rechaza_toma_opcion_o_alimento_inexistente():
    from app.db import SessionLocal
    from app.services.food_swap import apply_food_swap

    with SessionLocal() as db:
        c = _mk_client(db)
        avena_id = _food_id(db, "Avena en copos")
        clara_id = _food_id(db, "Clara de huevo")
        quinoa_id = _food_id(db, "Quinoa")
        plan = _mk_plan_with_option(db, c.id, avena_id=avena_id, clara_id=clara_id)
        db.commit()

        with pytest.raises(ValueError, match="toma"):
            apply_food_swap(db, client=c, plan=plan, slot=99, option_index=0,
                            old_food_id=avena_id, new_food_id=quinoa_id)
        with pytest.raises(ValueError, match="opción"):
            apply_food_swap(db, client=c, plan=plan, slot=1, option_index=5,
                            old_food_id=avena_id, new_food_id=quinoa_id)
        with pytest.raises(ValueError, match="no está en esta opción"):
            apply_food_swap(db, client=c, plan=plan, slot=1, option_index=0,
                            old_food_id=quinoa_id, new_food_id=avena_id)
        db.rollback()


def test_search_foods_for_client_filtra_lo_que_choca():
    from app.db import SessionLocal
    from app.services.food_swap import search_foods_for_client

    with SessionLocal() as db:
        c = _mk_client(db, food_dislikes=["avena"])
        sin_avena = search_foods_for_client(db, c, "avena")
        assert all("avena" not in f["canonical_name"].lower() for f in sin_avena)

        con_quinoa = search_foods_for_client(db, c, "quin")
        assert any(f["canonical_name"] == "Quinoa" for f in con_quinoa)
        db.rollback()


def test_router_foods_swap_traduce_value_error_a_400():
    from fastapi import HTTPException

    from app.db import SessionLocal
    from app.routers.plans import FoodSwapIn, foods_swap

    with SessionLocal() as db:
        c = _mk_client(db)
        avena_id = _food_id(db, "Avena en copos")
        clara_id = _food_id(db, "Clara de huevo")
        quinoa_id = _food_id(db, "Quinoa")
        plan = _mk_plan_with_option(db, c.id, avena_id=avena_id, clara_id=clara_id)
        db.commit()

        body = FoodSwapIn(slot=99, option_index=0, old_food_id=avena_id, new_food_id=quinoa_id)
        with pytest.raises(HTTPException) as exc_info:
            foods_swap(c.id, plan.id, body, db)
        assert exc_info.value.status_code == 400
        db.rollback()
