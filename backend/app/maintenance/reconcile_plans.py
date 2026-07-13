"""Uniformiza la coherencia numérica de TODOS los planes ya guardados.

Los planes creados antes de la invariante de coherencia (target_kcal ≡ macros
4/4/9 ≡ suma de los objetivos por comida) pueden arrastrar números descuadrados
—un apartado dice X kcal y otro dice otro número—. Este comando los recuadra en
bloque, una sola vez. Es IDEMPOTENTE: sobre planes ya coherentes no cambia nada,
así que se puede ejecutar tantas veces como se quiera.

Uso:
    python -m app.maintenance.reconcile_plans            # aplica los cambios
    python -m app.maintenance.reconcile_plans --dry-run  # solo informa
"""
from __future__ import annotations

import sys

from app.db import SessionLocal
from app.models import Client, Plan
from app.services.nutrition_scale import kcal_of, reconcile_nutrition


def _is_coherent(nut: dict) -> bool:
    m = nut.get("macros") or {}
    p, c, f = m.get("protein_g") or 0, m.get("carbs_g") or 0, m.get("fat_g") or 0
    if round(nut.get("target_kcal") or 0) != kcal_of(p, c, f):
        return False
    meals = [x for x in (nut.get("meals") or []) if x.get("target")]
    if not meals:
        return True
    if sum(x["target"].get("kcal") or 0 for x in meals) != nut["target_kcal"]:
        return False
    for axis, total in (("protein_g", p), ("carbs_g", c), ("fat_g", f)):
        if sum(x["target"].get(axis) or 0 for x in meals) != total:
            return False
    return True


def main(dry_run: bool = False) -> int:
    """Reconcilia la nutrición de todos los planes. Devuelve cuántos cambió."""
    db = SessionLocal()
    changed = 0
    try:
        weights: dict[int, float | None] = {}
        for plan in db.query(Plan).all():
            nut = plan.nutrition_json
            if not isinstance(nut, dict) or not nut:
                continue
            if _is_coherent(nut):
                continue
            if plan.client_id not in weights:
                cli = db.get(Client, plan.client_id)
                weights[plan.client_id] = (
                    (cli.current_weight_kg or cli.start_weight_kg) if cli else None
                )
            if not dry_run:
                # Copia mutada para que SQLAlchemy detecte el cambio del JSON.
                import copy

                fixed = reconcile_nutrition(copy.deepcopy(nut), weight_kg=weights[plan.client_id])
                plan.nutrition_json = fixed
            changed += 1
            print(f"  plan #{plan.id} (cliente {plan.client_id}) recuadrado")
        if not dry_run:
            db.commit()
        verb = "se recuadrarían" if dry_run else "recuadrados"
        print(f"[reconcile_plans] {verb} {changed} plan(es).")
        return changed
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(0 if main(dry_run="--dry-run" in sys.argv) >= 0 else 1)
