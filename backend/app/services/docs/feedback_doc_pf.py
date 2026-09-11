"""El INFORME DE REVISIÓN de Professional (Centre Salut & Fitness).

El plan ya tenía su documento propio (`plan_doc_pf`) y el informe quincenal no:
el cliente del centro recibía su plan en negro y dorado y, quince días después,
un informe con la portada, las tarjetas grises y el orden de DQR. Dos marcas en
el mismo buzón.

Y no era solo la piel. El informe de DQR pinta las cabeceras de tabla con el
color primario de la marca y el texto en BLANCO: naranja sobre blanco ya es
justo, pero DORADO sobre blanco da 2,1:1 — en papel, ilegible. Aquí las
cabeceras son negras con el texto en oro, como en el plan.

Qué cambia respecto al de DQR, además de los colores:
· PORTADA negra con el rótulo dorado y las fechas de la quincena (el de DQR
  arranca con una portada clara y centrada).
· «TU QUINCENA EN UNA PÁGINA»: las cifras en fichas, como en su plan — la
  misma pieza en los dos documentos del mismo cliente.
· PRIMERO se lee, después se mira. En DQR el texto («Cómo ha ido») llega tras
  tres páginas de gráficas; aquí va justo después de las cifras, que es lo que
  el cliente del centro abre buscando. Las gráficas van juntas al final, en
  «Tus números».
· «LO QUE CAMBIA» con la cuadrícula de ajustes, en su sitio: pegada a la
  explicación, no al final.
· «CÓMO SEGUIMOS», el ciclo del centro con su cita presencial. No existe en
  DQR, igual que en el plan.

Lo que NO cambia, porque no puede: los NÚMEROS. Vienen calculados de
`services/metrics` y este módulo solo los imprime. Un documento distinto es una
piel distinta, nunca una matemática distinta.
"""

from __future__ import annotations

import io
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

from app.services.docs import charts
from app.services.docs.plan_doc_pf import (
    GRIS,
    NEGRO,
    ORO,
    ORO_PAPEL,
    _barra,
    _caja,
    _fichas,
    _nota,
    _portada_generica,
)
from app.services.docs.word_base import (
    CONTENT_WIDTH_DXA,
    DocBrand,
    _cant_split_rows,
    _hex,
    add_bullets,
    clean_table,
    init_document,
    setup_reference_pages,
    spacer,
)


def _grafica(doc: Document, png: bytes, ancho_in: float = 6.0) -> None:
    doc.add_picture(io.BytesIO(png), width=Inches(ancho_in))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


def _subtitulo(doc: Document, texto: str) -> None:
    """Un rótulo dentro de una sección: versales espaciadas en oro oscuro, no
    un Heading 2 en negrita. Es la voz del resto de documentos de la marca."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(texto.upper())
    r.font.size = Pt(9)
    r.font.bold = True
    r.font.color.rgb = _hex("8A6D14")


def _fmt_delta(value: float | None, unit: str) -> str:
    """Delta con coma decimal y un decimal: "+1,4 kg". Misma regla que el
    informe de DQR — el cliente lee su idioma, no el del código."""
    if value is None:
        return "—"
    if abs(value) < 0.05:
        return "Sin cambios"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f} {unit}".replace(".", ",")


def generate_feedback_doc_pf(
    *,
    brand: DocBrand,
    client_name: str,
    period_index: int,
    metrics: dict,
    weight_points: list[tuple[str, float]],
    goal_kg: float | None,
    e1rm_exercises: list[dict],
    perimeters: dict[str, list[tuple[str, float]]] | None,
    volume_by_group: dict[str, float] | None,
    photo_pairs: list[tuple[str, str]] | None,
    ai_photo_analysis: str | None,
    natural_analysis: str,
    changes_bullets: list[str],
    answers: str | None,
    next_objectives: list[str],
    closing_message: str,
    plan_adjustments: list[dict] | None = None,
    period_label: str | None = None,
    goal_label: str | None = None,
    has_nutrition: bool = True,
) -> bytes:
    """El informe de la revisión de Professional. Misma firma que el de DQR:
    quien lo llama solo elige cuál, nunca prepara datos distintos."""
    doc = init_document(brand)
    pie = brand.name + (f" · {brand.contact_address}" if brand.contact_address else "")
    setup_reference_pages(
        doc,
        logo_path=(brand.logo_path if brand.logo_path and os.path.exists(brand.logo_path)
                   else None),
        right_title=f"REVISIÓN | {client_name}",
        right_sub=period_label or f"Quincena {period_index}",
        footer_text=pie,
    )

    _portada_generica(
        doc, brand, client_name, rotulo="Informe de revisión",
        datos=[("Quincena", period_label or f"Nº {period_index}"),
               ("Objetivo", (goal_label or "").replace("Objetivo: ", "").capitalize()
                or "A definir en el centro"),
               ("Revisión", "nos vemos en el centro")],
    )
    doc.add_page_break()

    # ----------------------------------------- tu quincena en una página ---
    _barra(doc, "Tu quincena en una página")
    _nota(doc, "Las cifras de estos quince días. Lo demás las explica.")
    adh = metrics.get("adherence", {}) or {}
    peso = metrics.get("weight", {}) or {}
    registros_dieta = (int(adh.get("diet_yes") or 0) + int(adh.get("diet_partial") or 0)
                       + int(adh.get("diet_no") or 0))
    # Ausencia de dato no es incumplimiento: a quien no ha contratado dieta —o
    # no tocó el selector— no se le imprime un "0 %" que parece un reproche.
    hay_dieta = bool(has_nutrition) and registros_dieta > 0
    fichas = [("Cambio de peso", _fmt_delta(peso.get("delta_kg"), "kg"))]
    if hay_dieta:
        fichas.append(("Adherencia dieta",
                       f"{round(adh.get('diet_adherence_ratio', 0) * 100)} %"))
    elif has_nutrition:
        fichas.append(("Adherencia dieta", "Sin datos"))
    fichas.append(("Días apuntados",
                   f"{adh.get('days_logged', 0)}/{adh.get('period_days', 0)}"))
    _fichas(doc, fichas)

    # ------------------------------------------------------- cómo ha ido ---
    # Antes que las gráficas, al revés que en DQR: es lo que el cliente del
    # centro abre buscando, y en la sala es de lo que se le habla.
    spacer(doc, 14)
    _barra(doc, "Cómo ha ido")
    if natural_analysis:
        doc.add_paragraph(natural_analysis)

    # ------------------------------------------------------ lo que cambia ---
    if changes_bullets or plan_adjustments:
        spacer(doc, 12)
        _barra(doc, "Lo que cambia y por qué")
        if changes_bullets:
            add_bullets(doc, changes_bullets[:5])
        if plan_adjustments:
            _subtitulo(doc, "Ajustes aplicados")
            filas = [[str(a.get("area", "")), str(a.get("change", "")),
                      str(a.get("reason", ""))] for a in plan_adjustments]
            # Cabecera NEGRA con texto en ORO. La de DQR usa el color primario
            # con texto blanco y, con un dorado, eso no se lee en papel.
            clean_table(
                doc, ["Área", "Cambio", "Por qué"], filas, brand,
                header_color=NEGRO, header_text_color=ORO,
                row_fills=("FFFFFF", GRIS), col_widths=[1800, 3600, 3626],
                cant_split_rows=False, keep_together=False,
            )

    # -------------------------------------------------------- tus números ---
    doc.add_page_break()
    _barra(doc, "Tus números")
    _nota(doc, "Lo mismo de arriba, dibujado. Para ver la tendencia, no el día.")
    acento = "#" + ORO
    if weight_points:
        _subtitulo(doc, "Evolución de peso")
        _grafica(doc, charts.weight_trend_chart(weight_points, goal_kg, acento))
    _subtitulo(doc, "Constancia")
    diet_pct = adh.get("diet_adherence_ratio", 0) * 100 if hay_dieta else None
    train_pct = min(100, adh.get("log_ratio", 0) * 100)
    _grafica(doc, charts.adherence_chart(diet_pct, train_pct, acento), ancho_in=5.5)
    if perimeters:
        _subtitulo(doc, "Medidas")
        _grafica(doc, charts.perimeters_chart(perimeters, acento))
    if volume_by_group:
        _subtitulo(doc, "Trabajo por grupo muscular")
        _grafica(doc, charts.volume_by_group_chart(volume_by_group, acento))
    if e1rm_exercises:
        _subtitulo(doc, "Fuerza")
        _grafica(doc, charts.e1rm_chart(e1rm_exercises, acento))

    # -------------------------------------------------------- cómo te ves ---
    if photo_pairs or ai_photo_analysis:
        doc.add_page_break()
        _barra(doc, "Cómo te ves")
        for antes, ahora in (photo_pairs or []):
            _par_de_fotos(doc, antes, ahora)
        if ai_photo_analysis:
            doc.add_paragraph(ai_photo_analysis)

    # ------------------------------------------- dudas, objetivos y ciclo ---
    if answers:
        spacer(doc, 12)
        _barra(doc, "Lo que preguntaste")
        doc.add_paragraph(answers)

    if next_objectives:
        spacer(doc, 12)
        _barra(doc, "Para estos quince días")
        add_bullets(doc, next_objectives)

    # EL CICLO DEL CENTRO. La pieza que Professional tiene y DQR no, igual que
    # en su plan: aquí la revisión es una VISITA, no una videollamada.
    spacer(doc, 12)
    _barra(doc, "Cómo seguimos")
    _caja(doc, [
        ("1 · Sigues apuntando", "Cada día, en la app: lo que entrenas y cómo te "
                                 "encuentras. Es de donde salen estos números."),
        # La DIRECCIÓN va en el cuerpo, no solo en el pie: citar a alguien en
        # el centro sin decirle dónde es medio recado.
        ("2 · Nos vemos", "A los quince días lo miramos juntos y ajustamos lo que "
                          "haga falta"
                          + (f", en {brand.contact_address}." if brand.contact_address
                             else " en el centro.")),
        ("3 · Sigues", "Con el plan ya ajustado. La cuota se renueva cada mes y "
                       "te avisamos antes: no se te cobra nada solo."),
    ])

    if closing_message:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        r = p.add_run(closing_message)
        r.italic = True
        r.font.color.rgb = _hex("4A4740")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _par_de_fotos(doc: Document, antes: str, ahora: str) -> None:
    """Las dos fotos del mismo ángulo, lado a lado, con su rótulo encima."""
    tabla = doc.add_table(rows=2, cols=2)
    tabla.autofit = True
    cabecera = tabla.rows[0].cells
    for i, rotulo in enumerate(("Quincena anterior", "Ahora")):
        p = cabecera[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(rotulo.upper())
        r.font.size = Pt(8)
        r.font.bold = True
        r.font.color.rgb = RGBColor(0x8A, 0x6D, 0x14)
    # El rótulo no se separa nunca de su foto al paginar.
    _cant_split_rows(tabla)
    celdas = tabla.rows[1].cells
    for i, ruta in enumerate((antes, ahora)):
        p = celdas[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if ruta and os.path.exists(ruta):
            try:
                p.add_run().add_picture(ruta, width=Inches(2.6))
            except Exception:  # noqa: BLE001 — una foto nunca tumba el informe
                p.add_run("(imagen no disponible)")
        else:
            p.add_run("—")


# Silencia los linters sobre nombres importados que este módulo expone por
# comodidad de quien lo lea (la paleta viaja con el documento).
__all__ = ["generate_feedback_doc_pf", "ORO", "ORO_PAPEL", "CONTENT_WIDTH_DXA"]
