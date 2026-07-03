"""PDF de consentimiento informado RGPD (G.3) — generado y archivado en alta."""

from __future__ import annotations

from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.services.storage import client_dir, storage_root

CONSENT_TEXT = (
    "De conformidad con el Reglamento (UE) 2016/679 (RGPD) y la LOPDGDD 3/2018, "
    "el cliente abajo identificado CONSIENTE de forma explícita el tratamiento de "
    "sus datos personales, incluidos datos de salud (categoría especial del art. 9 "
    "RGPD: peso, medidas corporales, fotografías de progreso, lesiones, patologías "
    "y medicación), con la única finalidad de elaborar y hacer seguimiento de su "
    "planificación personalizada de nutrición y entrenamiento. "
    "Los datos se conservarán mientras dure la relación de asesoría. El cliente "
    "puede ejercer en cualquier momento sus derechos de acceso, rectificación, "
    "supresión, portabilidad, limitación y oposición dirigiéndose al responsable. "
    "Las fotografías de progreso nunca serán públicas ni se cederán a terceros."
)


def generate_consent_pdf(
    client_id: int, client_name: str, client_email: str, brand_name: str, signed_at: datetime
) -> str:
    """Crea el PDF en documents/ y devuelve su ruta relativa al storage."""
    dest = client_dir(client_id, "documents") / "consentimiento_rgpd.pdf"
    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Title"], fontSize=16, spaceAfter=6)
    body = ParagraphStyle("b", parent=styles["BodyText"], fontSize=10.5, leading=15)
    meta = ParagraphStyle("m", parent=styles["BodyText"], fontSize=10, leading=14)

    doc = SimpleDocTemplate(
        str(dest), pagesize=A4,
        leftMargin=22 * mm, rightMargin=22 * mm, topMargin=24 * mm, bottomMargin=20 * mm,
        title="Consentimiento informado RGPD", author=brand_name,
    )
    stamp = signed_at.strftime("%d/%m/%Y %H:%M UTC")
    doc.build([
        Paragraph("Consentimiento informado — protección de datos", title),
        Paragraph(brand_name, styles["Heading3"]),
        Spacer(1, 8),
        Paragraph(f"<b>Cliente:</b> {client_name} &nbsp;&nbsp; <b>Email:</b> {client_email}", meta),
        Paragraph(f"<b>Fecha y hora de aceptación:</b> {stamp}", meta),
        Spacer(1, 12),
        Paragraph(CONSENT_TEXT, body),
        Spacer(1, 14),
        Paragraph(
            "Aceptación registrada electrónicamente mediante casilla de verificación "
            "obligatoria en el formulario de anamnesis del portal del cliente "
            f"(identificador interno de cliente: {client_id}).",
            meta,
        ),
    ])
    return str(dest.relative_to(storage_root()))
