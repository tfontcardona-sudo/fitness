"""Tests del selector de estructura de comidas (services/meal_structure)."""
from app.services.meal_structure import CANONICAL_MEALS, meal_schedule_from_keys


def test_orders_by_natural_day_regardless_of_input_order():
    sched = meal_schedule_from_keys(["cena", "desayuno", "comida"])
    assert [m["name"] for m in sched] == ["Desayuno", "Comida", "Cena"]
    assert [m["slot"] for m in sched] == [1, 2, 3]
    assert [m["time"] for m in sched] == ["08:00", "14:00", "21:00"]


def test_dedupes_and_ignores_unknown_keys():
    sched = meal_schedule_from_keys(["desayuno", "desayuno", "no_existe", "comida"])
    assert [m["name"] for m in sched] == ["Desayuno", "Comida"]


def test_empty_or_none_yields_empty_schedule():
    assert meal_schedule_from_keys([]) == []
    assert meal_schedule_from_keys(None) == []  # type: ignore[arg-type]


def test_all_six_canonical_meals_roundtrip_in_order():
    keys = [m["key"] for m in CANONICAL_MEALS]
    sched = meal_schedule_from_keys(list(reversed(keys)))
    assert [m["name"] for m in sched] == [m["name"] for m in CANONICAL_MEALS]
    assert len(sched) == 6
    # slots consecutivos 1..N
    assert [m["slot"] for m in sched] == list(range(1, 7))
