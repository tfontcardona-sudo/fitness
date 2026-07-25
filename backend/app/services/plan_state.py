"""PlanState — el plan como MODELO de datos único y versionado (hardening §4).

El plan es un modelo; el documento es un render (nunca al revés). PlanState
envuelve nutrición + entrenamiento + educación + metadatos con:

- **Versionado** v1, v2… con historial completo y `revert`.
- **Propagación top-down**: cambian kcal/macros → `reconcile_nutrition` recalcula
  macros, objetivos por comida, gramos del banco y equivalencias (una sola verdad).
- **Propagación bottom-up**: cambian los gramos de un ingrediente → se recalculan
  los macros de la opción desde la composición real (§2) → se recalcula la
  desviación vs. el objetivo de la comida → si se sale de tolerancia, avisa.

No sustituye de golpe a los dicts que ya circulan (migración incremental): es el
contenedor coherente sobre el que se apoyan el generador, el editor y el render.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from app.services.nutrition_scale import kcal_of, reconcile_nutrition

# Tolerancia de desviación de una opción respecto al objetivo de su comida.
OPTION_DEVIATION = 0.05


@dataclass
class PlanVersion:
    version: int
    nutrition: dict
    training: dict | None = None
    education: dict | None = None
    label: str = ""


@dataclass
class PlanState:
    """Estado vivo del plan con historial. `meta` guarda prompt_version,
    telemetría, resultado del panel, ICP y color."""

    current: PlanVersion
    history: list[PlanVersion] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    @classmethod
    def new(cls, nutrition: dict, training: dict | None = None,
            education: dict | None = None, *, weight_kg: float | None = None) -> "PlanState":
        nut = reconcile_nutrition(copy.deepcopy(nutrition), weight_kg)
        v1 = PlanVersion(1, nut, training, education, label="inicial")
        return cls(current=v1, history=[v1])

    def _commit(self, nutrition: dict, label: str) -> "PlanState":
        v = PlanVersion(self.current.version + 1, nutrition,
                        self.current.training, self.current.education, label=label)
        self.history.append(v)
        self.current = v
        return self

    # ---- top-down: cambian los totales ----
    def apply_targets(self, *, target_kcal: float | None = None,
                      macros: dict | None = None, weight_kg: float | None = None) -> "PlanState":
        """Cambia kcal y/o macros y propaga a TODO (macros↔kcal, comidas, banco,
        equivalencias) vía reconcile_nutrition. Crea una versión nueva."""
        nut = copy.deepcopy(self.current.nutrition)
        if macros:
            nut["macros"] = {**(nut.get("macros") or {}), **macros}
        if target_kcal is not None:
            nut["target_kcal"] = target_kcal
        nut = reconcile_nutrition(nut, weight_kg)
        return self._commit(nut, label="ajuste de objetivos")

    # ---- bottom-up: cambian los gramos de un ingrediente ----
    def edit_ingredient_grams(
        self, *, slot: int, option_key: str, food: str, grams: float,
        food_lookup: dict[str, dict] | None = None,
    ) -> tuple["PlanState", list[str]]:
        """Cambia los gramos de un ingrediente y recalcula hacia arriba: macros de
        la opción (desde la composición real si hay `food_lookup`), y desviación
        de la opción vs. el objetivo de su comida. Devuelve (estado, avisos)."""
        nut = copy.deepcopy(self.current.nutrition)
        warnings: list[str] = []
        bank = nut.get("meal_bank") or {}
        slot_block = next((s for s in bank.get("slots") or [] if s.get("slot") == slot), None)
        if not slot_block:
            return self, [f"slot {slot} no existe en el banco"]
        opt = next((o for o in slot_block.get("options") or [] if o.get("key") == option_key), None)
        if not opt:
            return self, [f"opción {option_key} no existe en el slot {slot}"]

        ing = next((i for i in opt.get("ingredients") or [] if i.get("food") == food), None)
        if not ing:
            return self, [f"ingrediente '{food}' no está en la opción"]
        ing["grams"] = grams

        # Recalcular macros de la opción desde la composición real (si se conoce).
        if food_lookup is not None:
            opt["macros"] = _macros_from_ingredients(opt.get("ingredients") or [], food_lookup)

        # Desviación vs el objetivo de la comida.
        meal = next((m for m in nut.get("meals") or []
                     if int(m.get("slot") or 0) == slot and isinstance(m.get("target"), dict)), None)
        if meal and isinstance(opt.get("macros"), dict):
            t = meal["target"]
            for axis in ("kcal", "protein_g", "carbs_g", "fat_g"):
                tv = float(t.get(axis) or 0)
                ov = float(opt["macros"].get(axis) or 0)
                if tv > 0 and abs(ov - tv) / tv > OPTION_DEVIATION:
                    warnings.append(
                        f"slot {slot} '{option_key}': {axis} {ov:.0f} se desvía "
                        f">{OPTION_DEVIATION*100:.0f}% del objetivo {tv:.0f} de la comida"
                    )
        self._commit(nut, label=f"edición de {food} en slot {slot}")
        return self, warnings

    def revert(self, version: int) -> "PlanState":
        """Vuelve a una versión anterior (queda como versión nueva, historial intacto)."""
        target = next((v for v in self.history if v.version == version), None)
        if target is None:
            raise ValueError(f"versión {version} no existe")
        self._commit(copy.deepcopy(target.nutrition), label=f"revertido a v{version}")
        self.current.training = target.training
        self.current.education = target.education
        return self

    def to_persistable(self) -> tuple[dict, dict | None, dict | None]:
        return self.current.nutrition, self.current.training, self.current.education


def _macros_from_ingredients(ingredients: list[dict], food_lookup: dict[str, dict]) -> dict:
    """Suma los macros de una opción desde la composición real de cada alimento
    (por 100 g) × sus gramos. `food_lookup`: {nombre: {kcal,protein_g,carbs_g,fat_g}}."""
    tot = {"kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    for ing in ingredients:
        comp = food_lookup.get(ing.get("food"))
        if not comp:
            continue
        f = float(ing.get("grams") or 0) / 100.0
        for k in ("protein_g", "carbs_g", "fat_g"):
            tot[k] += float(comp.get(k) or 0) * f
    tot = {k: round(v, 1) for k, v in tot.items()}
    tot["kcal"] = kcal_of(tot["protein_g"], tot["carbs_g"], tot["fat_g"])
    return tot
