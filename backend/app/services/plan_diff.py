"""Detección DETERMINISTA de qué cambió en una edición manual del plan.

Al guardar el editor, se compara el plan ANTES y DESPUÉS y se produce una lista
de frases humanas ("Calorías: 2200 → 2000 kcal", "Press banca: 3×8-10 → 4×8-10",
"Añadido Curl femoral"…). Esa lista alimenta el aviso "planificación modificada"
del panel y el mensaje de WhatsApp/email al cliente — sin depender de la IA:
el diff es exacto siempre.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

MAX_ITEMS = 14


def _f(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _num_change(items: list[str], label: str, old, new, unit: str) -> None:
    o, n = _f(old), _f(new)
    if o is None and n is None:
        return
    if o != n:
        fo = "—" if o is None else f"{o:g}"
        fn = "—" if n is None else f"{n:g}"
        items.append(f"{label}: {fo} → {fn} {unit}".strip())


def _nutrition_diff(old: dict, new: dict) -> list[str]:
    items: list[str] = []
    _num_change(items, "Calorías", old.get("target_kcal"), new.get("target_kcal"), "kcal")
    om, nm = old.get("macros") or {}, new.get("macros") or {}
    _num_change(items, "Proteína", om.get("protein_g"), nm.get("protein_g"), "g")
    _num_change(items, "Carbohidratos", om.get("carbs_g"), nm.get("carbs_g"), "g")
    _num_change(items, "Grasas", om.get("fat_g"), nm.get("fat_g"), "g")

    old_meals = [m.get("name") for m in (old.get("meals") or []) if isinstance(m, dict)]
    new_meals = [m.get("name") for m in (new.get("meals") or []) if isinstance(m, dict)]
    if len(old_meals) != len(new_meals):
        items.append(f"Comidas del día: {len(old_meals)} → {len(new_meals)} tomas")
    elif old_meals != new_meals:
        items.append("Cambio en el reparto de comidas del día")
    else:
        # Mismos nombres y totales pero OTRO reparto por comida (mover 30 g de
        # CH de la cena al desayuno): también es un cambio que el cliente nota.
        for om, nm in zip((old.get("meals") or []), (new.get("meals") or [])):
            if not (isinstance(om, dict) and isinstance(nm, dict)):
                continue
            ot, nt = om.get("target") or {}, nm.get("target") or {}
            ok, nk = _f(ot.get("kcal")), _f(nt.get("kcal"))
            if ok is not None and nk is not None and abs(ok - nk) > 10:
                _num_change(items, f"{nm.get('name') or 'Comida'}",
                            round(ok), round(nk), "kcal")

    old_sup = {(s.get("name") or "").strip() for s in (old.get("supplements") or [])
               if isinstance(s, dict) and s.get("name")}
    new_sup = {(s.get("name") or "").strip() for s in (new.get("supplements") or [])
               if isinstance(s, dict) and s.get("name")}
    for name in sorted(new_sup - old_sup):
        items.append(f"Suplemento añadido: {name}")
    for name in sorted(old_sup - new_sup):
        items.append(f"Suplemento quitado: {name}")
    return items


def _ex_desc(e: dict) -> str:
    sets, reps = e.get("sets"), e.get("rep_range") or ""
    return f"{sets}×{reps}" if sets is not None else reps


def _session_diff(items: list[str], old_s: dict, new_s: dict, names: dict[int, str]) -> None:
    label = new_s.get("name") or new_s.get("day") or "Sesión"
    old_ex = {e.get("exercise_id"): e for e in old_s.get("exercises", []) if isinstance(e, dict)}
    new_ex = {e.get("exercise_id"): e for e in new_s.get("exercises", []) if isinstance(e, dict)}

    for eid in new_ex:
        if eid not in old_ex:
            name = names.get(eid, f"ejercicio {eid}")
            items.append(f"{label}: añadido {name} ({_ex_desc(new_ex[eid])})")
    for eid in old_ex:
        if eid not in new_ex:
            items.append(f"{label}: quitado {names.get(eid, f'ejercicio {eid}')}")
    for eid, ne in new_ex.items():
        oe = old_ex.get(eid)
        if oe is None:
            continue
        name = names.get(eid, f"ejercicio {eid}")
        if (oe.get("sets"), oe.get("rep_range")) != (ne.get("sets"), ne.get("rep_range")):
            items.append(f"{name}: {_ex_desc(oe)} → {_ex_desc(ne)}")
        if _f(oe.get("start_weight_hint_kg")) != _f(ne.get("start_weight_hint_kg")):
            _num_change(items, f"{name} · peso", oe.get("start_weight_hint_kg"),
                        ne.get("start_weight_hint_kg"), "kg")
        if _f(oe.get("rest_sec")) != _f(ne.get("rest_sec")):
            _num_change(items, f"{name} · descanso", oe.get("rest_sec"), ne.get("rest_sec"), "s")
        if (oe.get("rir") or "") != (ne.get("rir") or ""):
            items.append(f"{name}: RIR {oe.get('rir') or '—'} → {ne.get('rir') or '—'}")


def _training_diff(db: Session, old: dict, new: dict) -> list[str]:
    items: list[str] = []
    old_sessions = old.get("sessions") or []
    new_sessions = new.get("sessions") or []

    ids: set[int] = set()
    for s in list(old_sessions) + list(new_sessions):
        for e in s.get("exercises", []) if isinstance(s, dict) else []:
            if isinstance(e.get("exercise_id"), int):
                ids.add(e["exercise_id"])
    names: dict[int, str] = {}
    if ids:
        from sqlalchemy import select

        from app.models import Exercise

        names = {ex.id: ex.canonical_name
                 for ex in db.scalars(select(Exercise).where(Exercise.id.in_(ids)))}

    if len(old_sessions) != len(new_sessions):
        items.append(f"Sesiones de entreno: {len(old_sessions)} → {len(new_sessions)}")
    # Emparejado por IDENTIDAD (día + nombre) y solo después por posición:
    # insertar una sesión al principio no desalinea todas las demás (el zip por
    # posición generaba "añadido/quitado X" fantasma en cada sesión posterior).
    def _key(s: dict) -> str:
        return f"{(s.get('day') or '').strip().lower()}|{(s.get('name') or '').strip().lower()}"

    old_by_key: dict[str, dict] = {}
    for s in old_sessions:
        if isinstance(s, dict) and _key(s) not in old_by_key:
            old_by_key[_key(s)] = s
    paired_old: set[int] = set()
    pairs: list[tuple[dict, dict]] = []
    unpaired_new: list[dict] = []
    for s in new_sessions:
        if not isinstance(s, dict):
            continue
        o = old_by_key.get(_key(s))
        if o is not None and id(o) not in paired_old:
            pairs.append((o, s))
            paired_old.add(id(o))
        else:
            unpaired_new.append(s)
    # Los restantes (renombrados/reordenados sin identidad) caen a posición.
    rest_old = [s for s in old_sessions if isinstance(s, dict) and id(s) not in paired_old]
    pairs.extend(zip(rest_old, unpaired_new))
    for old_s, new_s in pairs:
        _session_diff(items, old_s, new_s, names)
    return items


def manual_change_summary(db: Session, *, old_nutrition: dict | None, new_nutrition: dict | None,
                          old_training: dict | None, new_training: dict | None) -> list[str]:
    """Lista de frases con lo que cambió (vacía si nada relevante cambió)."""
    items: list[str] = []
    if isinstance(old_nutrition, dict) and isinstance(new_nutrition, dict):
        items += _nutrition_diff(old_nutrition, new_nutrition)
    if isinstance(old_training, dict) and isinstance(new_training, dict):
        items += _training_diff(db, old_training, new_training)
    if len(items) > MAX_ITEMS:
        items = items[:MAX_ITEMS] + [f"…y {len(items) - MAX_ITEMS} cambios más"]
    return items
