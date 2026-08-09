"""Seed idempotente. Se ejecuta en cada arranque (entrypoint.sh):

1. Biblioteca de 150 ejercicios — solo si la tabla está vacía.
2. brand_config por defecto (H.1) — solo si no existe ninguna fila.
3. Usuarios admin desde ADMIN_x del .env — solo los que falten.

Uso manual: python -m app.seeds.run
"""

import sys

from sqlalchemy import func, select

from app import branding
from app.config import settings
from app.db import SessionLocal
from app.models import BrandConfig, Exercise, Food, User
from app.security import hash_password
from app.seeds.exercises_data import EXERCISES
from app.seeds.foods_data import FOODS
from app.seeds.home_exercises_data import HOME_EXERCISES
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


def seed_home_exercises(db) -> int:
    """Cobertura de casa/exterior (peso corporal y bandas): inserta POR NOMBRE
    los que falten, en cada arranque — la auditoría de perfiles demostró que sin
    esto un cliente de casa sin material se quedaba con 5-11 ejercicios."""
    existing = set(db.scalars(select(Exercise.canonical_name)))
    missing = [d for d in HOME_EXERCISES if d["canonical_name"] not in existing]
    if not missing:
        return 0
    db.add_all(Exercise(**data) for data in missing)
    db.commit()
    return len(missing)


def seed_foods(db) -> int:
    """Base de composición de alimentos (§2): inserta POR NOMBRE los que falten,
    en cada arranque (como la maquinaria) para que producción reciba los nuevos
    en el siguiente deploy sin tocar filas existentes."""
    existing = set(db.scalars(select(Food.canonical_name)))
    missing = [d for d in FOODS if d["canonical_name"] not in existing]
    if not missing:
        return 0
    db.add_all(Food(**data) for data in missing)
    db.commit()
    return len(missing)


def seed_brand(db) -> bool:
    if db.scalar(select(func.count()).select_from(BrandConfig)):
        return False
    db.add(BrandConfig())  # defaults premium de H.1 definidos en el modelo
    db.commit()
    return True


# Teléfono público del negocio: destino del botón "Contacta conmigo" de /planes
# (y de cualquier contacto público futuro). Se rellena solo si el campo está
# VACÍO — lo que el coach escriba en Marca → teléfono de contacto siempre manda.
COACH_WHATSAPP = branding.CONTACT_PHONE


def seed_coach_contact(db) -> bool:
    """Rellena los datos de contacto/tagline de la marca SOLO si están vacíos —
    lo que el coach escriba en la página Marca siempre manda."""
    brand = db.scalar(select(BrandConfig).limit(1))
    if brand is None:
        return False
    changed = False
    if not (brand.contact_phone or "").strip():
        brand.contact_phone = COACH_WHATSAPP
        changed = True
    if not (brand.contact_email or "").strip():
        brand.contact_email = branding.CONTACT_EMAIL
        changed = True
    if not (brand.contact_web or "").strip():
        brand.contact_web = branding.CONTACT_WEB
        changed = True
    if not (brand.tagline or "").strip():
        brand.tagline = branding.BRAND_TAGLINE
        changed = True
    if changed:
        db.commit()
    return changed


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
        n_home = seed_home_exercises(db)
        n_food = seed_foods(db)
        brand = seed_brand(db)
        contacto = seed_coach_contact(db)
        n_admins = seed_admins(db)
        print(
            f"[seed] ejercicios: {n_ex or 'ya existían'} · "
            f"maquinaria nueva: {n_maq} · "
            f"casa/bandas nuevos: {n_home} · "
            f"alimentos nuevos: {n_food} · "
            f"brand: {'creada' if brand else 'ya existía'} · "
            f"whatsapp del coach: {'rellenado' if contacto else 'ya estaba'} · "
            f"admins creados: {n_admins}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
