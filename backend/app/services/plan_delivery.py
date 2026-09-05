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


from app.services.branding import fila_de_marca


def doc_brand(db: Session, client=None):
    """La marca de un DOCUMENTO (colores, logo y pie), en un solo sitio.

    Con `client`, la marca SELLADA en su ficha; sin él, la activa. Pásale
    siempre el cliente: su plan y su informe llevan el logo y el pie del
    negocio con el que contrató, no el del switch que el coach tenga puesto.

    Esta función estaba COPIADA en tres módulos (entrega del plan, informe
    quincenal y descarga desde el panel). Con una marca daba igual; con dos,
    arreglar una copia dejaba las otras dos sacando el logo equivocado.
    """
    from app.services.docs.word_base import DocBrand

    cfg = fila_de_marca(db, client)
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
                    tagline=cfg.tagline, contact_email=cfg.contact_email,
                    contact_phone=getattr(cfg, "contact_phone", None),
                    contact_address=getattr(cfg, "contact_address", None),
                    logo_path=logo_abs)


def build_plan_pdf(db: Session, plan: Plan, client: Client,
                   fmt: str = "pdf") -> tuple[bytes, str, str]:
    """Devuelve (contenido, media_type, filename) del plan.

    fmt="pdf" (por defecto): PDF convertido en el servidor (LibreOffice); si la
    conversión fallara, degrada a .docx para no romper nunca la entrega.
    fmt="docx": el Word ORIGINAL editable — para que el coach pueda retocar
    cualquier apartado del documento antes de enviarlo.
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
        brand=doc_brand(db, client),
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
        # Patrón ético/religioso (vegano, halal…): las listas de alimentos y las
        # tarjetas de plantilla del documento también lo respetan.
        diet_pattern=client.diet_pattern,
        # El documento lleva TODO lo que el cliente ha contratado: si tiene
        # dieta, la dieta; si tiene entreno, también el entreno (con su cardio,
        # pasos y deload). Antes el plan con dieta omitía el entrenamiento
        # entero "porque va en el portal" y el cardio/NEAT/deload prescritos no
        # llegaban a NINGÚN sitio (auditoría de calidad).
        include_nutrition=bool(plan.nutrition_json),
        include_training=bool(training),
        # Fecha de GENERACIÓN del plan (el PDF se construye en cada descarga:
        # sin esto, el mismo plan salía fechado el día en que se pulsaba el
        # botón y la fecha no identificaba nada).
        generated_on=(plan.created_at.date() if getattr(plan, "created_at", None) else None),
    )

    ascii_name = unicodedata.normalize("NFKD", client.full_name).encode("ascii", "ignore").decode()
    safe = "".join(c if c.isalnum() else "_" for c in ascii_name).strip("_").lower() or "cliente"

    if fmt == "docx":
        return data, DOCX_MEDIA, f"plan_{safe}_mes{plan.month_index}.docx"

    try:
        pdf = docx_bytes_to_pdf(data)
        return pdf, "application/pdf", f"plan_{safe}_mes{plan.month_index}.pdf"
    except Exception as exc:  # noqa: BLE001 — degradación controlada
        logger.warning("Conversión PDF falló, se entrega .docx: %s", exc)
        return data, DOCX_MEDIA, f"plan_{safe}_mes{plan.month_index}.docx"
