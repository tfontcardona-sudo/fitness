"""Entrega del plan al cliente: PDF generado bajo demanda.

Un único constructor del documento para las dos puertas de salida:
- descarga del coach (`GET /api/plans/{id}/document`),
- enlace público tokenizado del cliente (`GET /api/p/{token}/plan.pdf`), pensado
  para mandarse por WhatsApp con un clic desde la ficha del cliente.
"""

from __future__ import annotations

import logging
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, Exercise, Plan

logger = logging.getLogger("app.plan_delivery")

DOCX_MEDIA = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def doc_brand(db: Session):
    """DocBrand desde la configuración de marca (con logo si existe)."""
    from app.models import BrandConfig
    from app.services.docs.word_base import DocBrand

    cfg = db.scalar(select(BrandConfig).limit(1))
    if cfg is None:
        return DocBrand(name="Tu asesoría", color_primary="#E8833A",
                        color_secondary="#2E5E8C", font_family="Inter")
    logo_abs = None
    if cfg.logo_path:
        from app.services.storage import abs_path

        try:
            logo_abs = str(abs_path(cfg.logo_path))
        except Exception:
            logo_abs = None
    return DocBrand(name=cfg.name, color_primary=cfg.color_primary,
                    color_secondary=cfg.color_secondary, font_family=cfg.font_family,
                    logo_path=logo_abs)


def build_plan_pdf(db: Session, plan: Plan, client: Client) -> tuple[bytes, str, str]:
    """Devuelve (contenido, media_type, filename) del plan.

    PDF convertido en el servidor (LibreOffice); si la conversión fallara,
    degrada a .docx para no romper nunca la entrega.
    """
    from app.services.docs.pdf_convert import docx_bytes_to_pdf
    from app.services.docs.plan_doc import generate_plan_doc

    training = plan.training_json or {}
    ex_ids = {
        ex.get("exercise_id")
        for sess in training.get("sessions", [])
        for ex in sess.get("exercises", [])
        if ex.get("exercise_id") is not None
    }
    exercise_names: dict[int, str] = {}
    if ex_ids:
        for ex in db.scalars(select(Exercise).where(Exercise.id.in_(ex_ids))):
            exercise_names[ex.id] = ex.canonical_name

    data = generate_plan_doc(
        brand=doc_brand(db),
        client_name=client.full_name,
        month_index=plan.month_index,
        goal_type=client.goal_type,
        diet_mode=client.diet_mode,
        nutrition=plan.nutrition_json or {},
        training=training,
        education=plan.education_json or {},
        exercise_names=exercise_names,
        food_allergies=client.food_allergies,
        food_dislikes=client.food_dislikes,
    )

    ascii_name = unicodedata.normalize("NFKD", client.full_name).encode("ascii", "ignore").decode()
    safe = "".join(c if c.isalnum() else "_" for c in ascii_name).strip("_").lower() or "cliente"

    try:
        pdf = docx_bytes_to_pdf(data)
        return pdf, "application/pdf", f"plan_{safe}_mes{plan.month_index}.pdf"
    except Exception as exc:  # noqa: BLE001 — degradación controlada
        logger.warning("Conversión PDF falló, se entrega .docx: %s", exc)
        return data, DOCX_MEDIA, f"plan_{safe}_mes{plan.month_index}.docx"
