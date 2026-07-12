"""Estructura de comidas del día (canónica) para el selector de la planificación.

El cliente declara sus comidas en la anamnesis, pero el coach puede rehacer la
estructura desde la planificación eligiendo entre estas 6 tomas canónicas. Al
cambiarla se regenera el plan con ese reparto y toda la info se adapta.
"""
from __future__ import annotations

# Orden fijo del día. `key` es estable (para el selector); `name` y `time` son el
# valor por defecto que se le entrega a la IA (que reparte los macros entre ellas).
CANONICAL_MEALS: list[dict] = [
    {"key": "desayuno", "name": "Desayuno", "time": "08:00"},
    {"key": "media_manana", "name": "Media mañana", "time": "11:00"},
    {"key": "comida", "name": "Comida", "time": "14:00"},
    {"key": "snack", "name": "Snack", "time": "17:00"},
    {"key": "cena", "name": "Cena", "time": "21:00"},
    {"key": "precama", "name": "Pre-cama", "time": "23:00"},
]

_BY_KEY = {m["key"]: m for m in CANONICAL_MEALS}
_ORDER = {m["key"]: i for i, m in enumerate(CANONICAL_MEALS)}


def meal_schedule_from_keys(keys: list[str]) -> list[dict]:
    """Convierte una lista de claves canónicas en un meal_schedule ordenado:
    [{slot, name, time}], slots 1..N en el orden natural del día. Ignora claves
    desconocidas y duplicados."""
    seen: set[str] = set()
    chosen = []
    for k in keys or []:
        if k in _BY_KEY and k not in seen:
            seen.add(k)
            chosen.append(_BY_KEY[k])
    chosen.sort(key=lambda m: _ORDER[m["key"]])
    return [{"slot": i + 1, "name": m["name"], "time": m["time"]} for i, m in enumerate(chosen)]
