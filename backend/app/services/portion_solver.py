"""Solver de porciones (hardening §2).

La IA SELECCIONA alimentos (por nombre/ID); el backend fija las CANTIDADES con un
solver de mínimos cuadrados con restricciones (`scipy.optimize.lsq_linear`), que
minimiza la desviación respecto a los macros objetivo del slot, con cotas
realistas por alimento, y luego redondea a unidades prácticas (5 g, 1 unidad,
1 cucharada) recalculando los totales tras redondear.

Además:
- `filter_foods`: descarta ANTES del solver los alimentos con un alérgeno del
  cliente o que violan una restricción ética/religiosa — un alérgeno no puede ni
  entrar en el contexto del modelo.
- `equivalent_portion`: equivalencias e intercambios por kcal totales + macro
  neta (no por gramos brutos).

Diseño defensivo: el solver JAMÁS lanza; ante datos degenerados devuelve la mejor
aproximación posible (o gramos a cero) y deja que el validador determinista opine.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import lsq_linear

from app.services.guardrails import _DIET_PATTERN_FORBIDDEN, _match_term, _norm_food, _terms_for

# Pesos de cada eje en la función objetivo. La proteína pesa más (es el eje que
# NO se quiere fallar); las kcal se derivan de P/C/F, así que no se optimizan
# aparte (evita doble contar). Grasa e hidratos, peso medio.
_AXIS_WEIGHTS = {"protein_g": 1.6, "carbs_g": 1.0, "fat_g": 1.2}


@dataclass
class SolvedFood:
    food_id: int
    name: str
    grams: float
    macros: dict  # kcal/protein_g/carbs_g/fat_g aportados por esta cantidad


@dataclass
class SolvedPortion:
    items: list[SolvedFood] = field(default_factory=list)
    totals: dict = field(default_factory=lambda: {"kcal": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0})

    def deviation_pct(self, target: dict) -> dict:
        out = {}
        for k in ("kcal", "protein_g", "carbs_g", "fat_g"):
            t = float(target.get(k) or 0)
            out[k] = round((self.totals[k] - t) / t * 100, 1) if t else 0.0
        return out


# ------------------------------------------------------------------ filtro ----

def filter_foods(
    foods: list[dict],
    *,
    allergies: list[str] | None = None,
    diet_pattern: str | None = None,
    dislikes: list[str] | None = None,
) -> list[dict]:
    """Quita los alimentos con un alérgeno del cliente, un alimento odiado o que
    violan la restricción dietética. `foods`: dicts con al menos canonical_name,
    aliases, allergens, tags."""
    forbidden = None
    if diet_pattern:
        forbidden = _DIET_PATTERN_FORBIDDEN.get(_norm_food(diet_pattern).replace(" ", "_"))
    out = []
    for f in foods:
        if f.get("archived"):
            continue
        # Alérgenos declarados en la ficha del alimento
        f_allergens = {_norm_food(a) for a in (f.get("allergens") or [])}
        if any(_norm_food(a) in f_allergens for a in (allergies or [])):
            continue
        name_texts = [_norm_food(f.get("canonical_name"))] + [
            _norm_food(a) for a in (f.get("aliases") or [])
        ]
        # Alérgeno por NOMBRE (defensa extra: sinónimos), alimento odiado, patrón
        if any(_match_term(_terms_for(a), name_texts) for a in (allergies or [])):
            continue
        if any(_match_term(_terms_for(d), name_texts) for d in (dislikes or [])):
            continue
        if forbidden and _match_term(forbidden, name_texts):
            continue
        out.append(f)
    return out


# ------------------------------------------------------------------ solver ----

def _round_practical(grams: float, unit_grams: float | None,
                     min_grams: float | None = None,
                     max_grams: float | None = None) -> float:
    """Redondea a una ración cocinable: a la unidad práctica si la hay
    (1 huevo, 1 rebanada), si no a múltiplos de 5 g.

    Y VUELVE A ACOTAR. El solver respeta `min_grams`/`max_grams`, pero el
    redondeo posterior se los saltaba: 4 rebanadas de 40 g daban 160 g de pan
    integral con un tope de 150. Las cotas del catálogo son el criterio del
    coach sobre lo que es una ración sensata; no puede saltárselas el último
    paso. Se recorta a la unidad práctica que sí cabe."""
    if grams <= 0:
        return 0.0
    from app.services.nutrition_scale import _rhu  # half-up: convención del sistema
    if unit_grams and unit_grams > 0:
        n = max(0, _rhu(grams / unit_grams))
        if max_grams is not None and n * unit_grams > max_grams:
            n = int(max_grams // unit_grams)
        if min_grams is not None and n * unit_grams < min_grams:
            # Redondeo hacia ARRIBA hasta cubrir el suelo (si el suelo no es
            # múltiplo de la unidad, el suelo manda: es el mínimo del catálogo).
            import math
            n = max(n, math.ceil(min_grams / unit_grams))
        return round(max(0, n) * unit_grams, 1)
    g = float(max(0, _rhu(grams / 5.0)) * 5)
    if max_grams is not None:
        g = min(g, float(max_grams))
    if min_grams is not None:
        g = max(g, float(min_grams))
    return g


def solve_portions(foods: list[dict], target: dict) -> SolvedPortion:
    """Fija los gramos de `foods` (dicts con macros por 100 g + cotas) para acercar
    los macros a `target` {protein_g, carbs_g, fat_g[, kcal]}. Mínimos cuadrados
    con cotas (min_grams..max_grams), pesos por eje, y redondeo práctico final."""
    foods = [f for f in foods if f]
    if not foods:
        return SolvedPortion()

    axes = ("protein_g", "carbs_g", "fat_g")
    w = np.array([_AXIS_WEIGHTS[a] for a in axes], dtype=float)
    # A[eje, alimento] = gramos-por-macro por gramo de alimento (÷100), ponderado.
    A = np.array([[float(f.get(a, 0)) / 100.0 for f in foods] for a in axes], dtype=float)
    b = np.array([float(target.get(a) or 0) for a in axes], dtype=float)
    Aw = A * w[:, None]
    bw = b * w

    lo = np.array([float(f.get("min_grams") or 0) for f in foods], dtype=float)
    hi = np.array([float(f.get("max_grams") or 400) for f in foods], dtype=float)
    hi = np.maximum(hi, lo + 1e-6)

    try:
        res = lsq_linear(Aw, bw, bounds=(lo, hi), method="bvls", max_iter=200)
        grams = res.x
    except Exception:  # noqa: BLE001 — solver best-effort, nunca rompe generación
        grams = np.clip((lo + hi) / 2, lo, hi)

    items: list[SolvedFood] = []
    totals = {"kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    for f, g in zip(foods, grams):
        gr = _round_practical(float(g), f.get("unit_grams"),
                              f.get("min_grams"), f.get("max_grams"))
        if gr <= 0:
            continue
        factor = gr / 100.0
        p_g = round(float(f.get("protein_g", 0)) * factor, 1)
        c_g = round(float(f.get("carbs_g", 0)) * factor, 1)
        f_g = round(float(f.get("fat_g", 0)) * factor, 1)
        m = {
            # kcal = 4/4/9 de los macros declarados (una sola verdad): la kcal
            # de etiqueta del catálogo (con fibra) desviaba >2% y disparaba el
            # veto Atwater del Revisor 0 sobre opciones correctas.
            "kcal": round(4 * p_g + 4 * c_g + 9 * f_g),
            "protein_g": p_g,
            "carbs_g": c_g,
            "fat_g": f_g,
        }
        items.append(SolvedFood(
            food_id=f.get("id", 0), name=f.get("canonical_name", "?"), grams=gr, macros=m,
        ))
        for k in totals:
            totals[k] += m[k]
    totals = {k: (round(v) if k == "kcal" else round(v, 1)) for k, v in totals.items()}
    return SolvedPortion(items=items, totals=totals)


# ------------------------------------------------------------ equivalencias ----

def _household_for(name: str, grams: float, unit_grams: float | None) -> str:
    """Medida casera para una cantidad ya resuelta por el solver."""
    if unit_grams and unit_grams > 0:
        n = max(1, round(grams / unit_grams))
        return f"{n} ud ({int(round(grams))} g)"
    return f"{int(round(grams))} g"


def snap_option_ingredients(
    ingredients: list[dict], target: dict, foods_by_id: dict[int, dict],
) -> tuple[list[dict], dict] | None:
    """§2: fija los gramos de una opción cuyos ingredientes referencian el catálogo.

    Devuelve `(ingredientes_nuevos, macros_nuevas)` si TODOS los ingredientes tienen
    un `food_id` resoluble; en otro caso `None` (se conserva la porción de la IA).
    El solver decide los gramos para acercar la opción al `target` del slot; la IA
    solo eligió los alimentos. Nunca lanza.
    """
    if not ingredients:
        return None
    foods = []
    for ing in ingredients:
        fid = ing.get("food_id")
        food = foods_by_id.get(fid) if fid is not None else None
        if not food:
            return None  # un solo ingrediente fuera del catálogo → no tocamos la opción
        foods.append(food)

    solved = solve_portions(foods, target)
    if not solved.items:
        return None

    by_id: dict[int, SolvedFood] = {}
    for it in solved.items:
        by_id.setdefault(it.food_id, it)

    new_ings: list[dict] = []
    for ing, food in zip(ingredients, foods):
        it = by_id.get(food.get("id"))
        if it is None or it.grams <= 0:
            return None  # el solver descartó un alimento → conservamos la opción de la IA
        new_ings.append({
            "food": food.get("canonical_name", ing.get("food")),
            "grams": it.grams,
            "household": _household_for(food.get("canonical_name", ""), it.grams,
                                        food.get("unit_grams")),
            "food_id": food.get("id"),
        })
    macros = {
        "kcal": solved.totals["kcal"],
        "protein_g": solved.totals["protein_g"],
        "carbs_g": solved.totals["carbs_g"],
        "fat_g": solved.totals["fat_g"],
    }
    return new_ings, macros


def snap_meal_bank(meal_bank: dict, slot_targets: dict[int, dict],
                   foods_by_id: dict[int, dict]) -> int:
    """§2: recorre el banco flexible y FIJA los gramos de cada opción cuyos
    ingredientes estén en el catálogo. Best-effort: devuelve cuántas opciones ajustó
    y nunca lanza (la que no encaje se queda como la dejó la IA)."""
    if not meal_bank or not foods_by_id:
        return 0
    snapped = 0
    for slot in (meal_bank.get("slots") or []):
        if slot.get("fmt") not in (None, "options"):
            continue
        target = slot_targets.get(slot.get("slot"))
        if not target:
            continue
        for opt in (slot.get("options") or []):
            try:
                res = snap_option_ingredients(opt.get("ingredients") or [], target, foods_by_id)
            except Exception:  # noqa: BLE001 — el solver nunca rompe la generación
                res = None
            if res is None:
                continue
            new_ings, macros = res
            opt["ingredients"] = new_ings
            opt["macros"] = macros
            snapped += 1
    return snapped


def equivalent_portion(base_food: dict, base_grams: float, alt_food: dict,
                       axis: str = "carbs_g") -> float:
    """Gramos de `alt_food` que igualan el aporte del EJE dominante de `base_food`
    en `base_grams` (equivalencia por macro neta, no por gramos brutos). Redondea
    a ración cocinable."""
    base_axis = float(base_food.get(axis, 0)) / 100.0 * base_grams
    per_g = float(alt_food.get(axis, 0)) / 100.0
    if per_g <= 0:
        return 0.0
    grams = base_axis / per_g
    return _round_practical(grams, alt_food.get("unit_grams"),
                            alt_food.get("min_grams"), alt_food.get("max_grams"))
