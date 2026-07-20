"""Seed idempotente. Se ejecuta en cada arranque (entrypoint.sh):

1. Biblioteca de 150 ejercicios — solo si la tabla está vacía.
2. brand_config por defecto (H.1) — solo si no existe ninguna fila.
3. Usuarios admin desde ADMIN_x del .env — solo los que falten.

Uso manual: python -m app.seeds.run
"""

import sys

from sqlalchemy import func, select

from app.config import settings
from app.db import SessionLocal
from app.models import BrandConfig, Exercise, User
from app.security import hash_password
from app.seeds.exercises_data import EXERCISES
from app.seeds.machines_data import MACHINE_EXERCISES


def seed_exercises(db) -> int:
    count = db.scalar(select(func.count()).select_from(Exercise))
    if count:
        return 0
    db.add_all(Exercise(**data) for data in EXERCISES)
    db.commit()
    return len(EXERCISES)


def seed_machines(db) -> int:
    """Maquinaria del gimnasio del coach: inserta POR NOMBRE las que falten.

    A diferencia de la biblioteca base (solo con tabla vacía), esto corre en
    cada arranque y añade las máquinas nuevas sin tocar filas existentes —
    así producción las recibe en el siguiente deploy."""
    existing = set(db.scalars(select(Exercise.canonical_name)))
    missing = [d for d in MACHINE_EXERCISES if d["canonical_name"] not in existing]
    if not missing:
        return 0
    db.add_all(Exercise(**data) for data in missing)
    db.commit()
    return len(missing)


def seed_brand(db) -> bool:
    if db.scalar(select(func.count()).select_from(BrandConfig)):
        return False
    db.add(BrandConfig())  # defaults premium de H.1 definidos en el modelo
    db.commit()
    return True


def seed_admins(db) -> int:
    created = 0
    for username, password in (
        (settings.admin_1_user, settings.admin_1_pass),
        (settings.admin_2_user, settings.admin_2_pass),
    ):
        if not username or not password:
            continue
        exists = db.scalar(select(func.count()).where(User.username == username))
        if exists:
            continue
        db.add(User(username=username, password_hash=hash_password(password)))
        created += 1
    db.commit()
    return created


def main() -> None:
    db = SessionLocal()
    try:
        n_ex = seed_exercises(db)
        n_maq = seed_machines(db)
        brand = seed_brand(db)
        n_admins = seed_admins(db)
        print(
            f"[seed] ejercicios: {n_ex or 'ya existían'} · "
            f"maquinaria nueva: {n_maq} · "
            f"brand: {'creada' if brand else 'ya existía'} · "
            f"admins creados: {n_admins}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
