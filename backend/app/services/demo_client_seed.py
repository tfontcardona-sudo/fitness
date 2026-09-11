"""EL CLIENTE DE DEMOSTRACIÓN de Professional.

El dueño pidió ver con sus propios ojos que la anamnesis, la planificación y
el portal de Professional no se parecen a los de DQR — no una captura que le
enseñe yo, sino un caso real que pueda abrir él mismo en producción. Este
módulo siembra ESE cliente, con una anamnesis completa (como la rellenaría
alguien en el cuestionario corto del centro) y un plan generado con la IA
real, publicado y con su período de seguimiento ya abierto.

Mismo criterio que `default_brand_logos.py`/`media_legacy.py`: va en el
arranque de la app, no en una migración de Alembic, porque esto no es
estructura — es un caso de ejemplo, con una llamada real a la API de
Anthropic de por medio (una migración corre en una transacción y no es sitio
para eso). Y es IDEMPOTENTE: si el cliente demo ya existe, no hace nada — ni
una llamada a la IA de más en el despliegue siguiente.

⚠️ SOLO EN PRODUCCIÓN (`settings.is_production`): en dev y en la suite de
tests esto NO debe llamar NUNCA a la API real de Anthropic sin que nadie lo
haya pedido — la suite usa un AIClient falso a propósito (§7 de CLAUDE.md).
Y corre en un HILO aparte: generar un plan de verdad pasa por el panel de
revisión (8-10 roles) y puede tardar; el resto de la cartera no tiene por qué
esperar a que termine para que el servidor empiece a responder.
"""
from __future__ import annotations

import logging
import threading
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import BrandConfig, Client
from app.security import hash_password, new_portal_token

logger = logging.getLogger("app.demo_seed")

# Un email de negocio, no el de una persona real: nunca se le manda correo
# (el acceso se deja ya sellado con la contraseña de abajo), así que no
# importa que no exista un buzón detrás.
DEMO_EMAIL = "marta.demo@centre-salut-fitness.com"
# Fija y conocida a propósito: como no se envía por email, es la única forma
# de que el dueño pueda entrar de verdad al portal de este cliente a mirarlo.
DEMO_PASSWORD = "CentreDemo26"


def _ya_existe(db: Session) -> bool:
    return db.scalar(select(Client.id).where(Client.email == DEMO_EMAIL)) is not None


def _crear_cliente_demo(db: Session) -> Client | None:
    brand = db.scalar(select(BrandConfig).where(BrandConfig.slug == "professional-fitness"))
    if brand is None:
        return None  # esta base aún no tiene la marca Professional (no debería pasar en prod)

    client = Client(
        brand_id=brand.id,
        full_name="Marta Puig Serra",
        email=DEMO_EMAIL,
        package_tier="full",  # el único que vende Professional: Pack Premium
        billing_period="1m",  # cuota mensual, sin programa cerrado ni oferta
        level="intermediate",
        status="onboarding",
        portal_token="pendiente",  # se firma abajo con el id real
        # --- Lo que saldría del cuestionario corto del centro ---
        sex="female",
        birth_date=date(1992, 3, 20),
        height_cm=165,
        start_weight_kg=71.5,
        current_weight_kg=71.5,
        body_fat_pct=28.5,
        goal_type="fat_loss",
        goal_weight_kg=64,
        training_days=3,
        daily_activity_level="light",
        session_max_min=60,
        training_place="gym",
        equipment=[],
        injuries_notes=(
            "Molestia leve en la rodilla derecha al hacer sentadilla profunda; "
            "sin diagnóstico médico, evitar cargas altas ahí."
        ),
        medical_notes="Tensión un poco alta, en revisión con su médico de cabecera.",
        current_supplements="Proteína de suero después de entrenar.",
        sport_history=(
            "Ha hecho running suelto y alguna clase de zumba en el pasado.\n"
            "- Ejercicios (favoritos / que detesta): le gusta el remo y la polea; "
            "evita las zancadas por la rodilla."
        ),
        meals_per_day=4,
        food_allergies=[],
        food_dislikes=["pescado azul"],
        food_likes=[],
        lifestyle_notes=(
            "[Zonas a priorizar] Piernas y glúteos\n"
            "[Horarios de comida] Come fuera de casa entre semana; cena tarde "
            "los días que cierra la tienda."
        ),
        diet_mode="flexible_7",
        payment_status="paid",
        paid_at=datetime.now(timezone.utc),
        consent_signed_at=datetime.now(timezone.utc),
        portal_access_sent_at=datetime.now(timezone.utc),
    )
    db.add(client)
    db.flush()  # asigna el id real
    client.portal_token = new_portal_token(client.id)
    client.portal_password_hash = hash_password(DEMO_PASSWORD)
    db.commit()
    db.refresh(client)
    return client


def _generar_plan_demo(db: Session, client_id: int) -> None:
    # Mismo camino que pulsa el coach en el panel — núcleo + comidas + panel de
    # revisión con la IA real, y activación automática si no hay violaciones.
    from app.routers.clients import generate_client_plan

    generate_client_plan(client_id=client_id, month_index=None, body=None, db=db)


def _seed_sync() -> None:
    from app.db import SessionLocal

    with SessionLocal() as db:
        try:
            if _ya_existe(db):
                return
            client = _crear_cliente_demo(db)
            if client is None:
                logger.warning(
                    "Cliente demo de Professional omitido: la marca "
                    "'professional-fitness' no existe en esta base."
                )
                return
            logger.info(
                "Cliente demo de Professional creado (id=%s); generando su "
                "plan con IA…", client.id,
            )
            _generar_plan_demo(db, client.id)
            logger.info(
                "Cliente demo de Professional listo (id=%s): anamnesis, plan "
                "y seguimiento ya abiertos.", client.id,
            )
        except Exception:  # noqa: BLE001 — nunca puede tumbar el arranque
            logger.exception("No se pudo sembrar el cliente demo de Professional")


def seed_demo_professional_client() -> None:
    """Lanza la siembra en segundo plano. Solo en PRODUCCIÓN y solo una vez
    (comprueba antes de nada si el cliente demo ya existe)."""
    if not settings.is_production:
        return
    threading.Thread(target=_seed_sync, name="demo-seed-professional", daemon=True).start()
