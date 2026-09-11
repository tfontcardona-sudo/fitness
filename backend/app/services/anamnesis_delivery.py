"""Entrega de la anamnesis del cliente como documento (PDF/Word).

Mismo patrón que `plan_delivery.py`: un único constructor que decide, por la
marca DEL CLIENTE (`doc_variant`), qué generador llamar — el de DQR o el de
Professional. Nada nuevo se calcula aquí; solo se vuelca lo que YA vive en la
ficha (`Client`), tal cual la pestaña Anamnesis del panel lo muestra.
"""

from __future__ import annotations

import unicodedata

from sqlalchemy.orm import Session

from app.models import Client
from app.services.metrics import age_from_birth
from app.services.plan_delivery import doc_brand, variante_de_documento

DOCX_MEDIA = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def build_anamnesis_pdf(db: Session, client: Client, fmt: str = "pdf") -> tuple[bytes, str, str]:
    """Devuelve (contenido, media_type, filename) de la ficha del cliente.

    fmt="pdf" (por defecto): PDF convertido en el servidor; si la conversión
    fallara, degrada a .docx para no romper nunca la entrega.
    """
    from app.services.docs.pdf_convert import docx_bytes_to_pdf

    comun = dict(
        brand=doc_brand(db, client),
        client_name=client.full_name,
        sex=client.sex,
        age=age_from_birth(client.birth_date) if client.birth_date else None,
        height_cm=client.height_cm,
        start_weight_kg=client.start_weight_kg,
        current_weight_kg=client.current_weight_kg,
        body_fat_pct=client.body_fat_pct,
        goal_type=client.goal_type,
        goal_weight_kg=client.goal_weight_kg,
        goal_deadline=client.goal_deadline,
        level=client.level,
        training_days=client.training_days,
        training_place=client.training_place,
        session_max_min=client.session_max_min,
        daily_activity_level=client.daily_activity_level,
        equipment=client.equipment,
        diet_mode=client.diet_mode,
        diet_pattern=client.diet_pattern,
        meals_per_day=client.meals_per_day,
        food_allergies=client.food_allergies,
        food_dislikes=client.food_dislikes,
        food_likes=client.food_likes,
        injuries_notes=client.injuries_notes,
        medical_notes=client.medical_notes,
        medication_notes=client.medication_notes,
        current_supplements=client.current_supplements,
        sport_history=client.sport_history,
        lifestyle_notes=client.lifestyle_notes,
        generated_on=None,
    )

    variante = variante_de_documento(db, client)
    if variante == "professional":
        from app.services.docs.anamnesis_doc_pf import generate_anamnesis_doc_pf

        data = generate_anamnesis_doc_pf(**comun)
    else:
        from app.services.docs.anamnesis_doc import generate_anamnesis_doc

        data = generate_anamnesis_doc(**comun)

    ascii_name = unicodedata.normalize("NFKD", client.full_name).encode("ascii", "ignore").decode()
    safe = "".join(c if c.isalnum() else "_" for c in ascii_name).strip("_").lower() or "cliente"

    if fmt == "docx":
        return data, DOCX_MEDIA, f"anamnesis_{safe}.docx"

    try:
        pdf = docx_bytes_to_pdf(data)
        return pdf, "application/pdf", f"anamnesis_{safe}.pdf"
    except Exception:  # noqa: BLE001 — degradación controlada, igual que el plan
        return data, DOCX_MEDIA, f"anamnesis_{safe}.docx"
