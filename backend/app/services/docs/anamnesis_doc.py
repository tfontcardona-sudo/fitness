"""Documento de la anamnesis (ficha estructurada) — DQR.

Petición del dueño: la ficha del cliente tiene que poder VERSE y DESCARGARSE
como documento, no solo consultarse en la pestaña Anamnesis del panel. Este
generador vuelca los mismos datos que ya viven en la ficha (nada nuevo, nada
calculado): antropometría, objetivo, entrenamiento, alimentación y salud.

Mismo patrón que plan_doc/feedback_doc: un DocBrand, portada + secciones con
`add_section_heading`, tablas limpias para los datos tabulares y viñetas para
las notas de texto libre. La seguridad alimentaria (alergias) se destaca en
rojo, igual que en el resto del sistema — no es un dato más de la lista.
"""

from __future__ import annotations

import io
from datetime import date

from docx import Document
from docx.shared import Pt

from app.services.docs.word_base import (
    DocBrand,
    add_bullets,
    add_cards_row,
    add_cover,
    add_section_heading,
    clean_table,
    init_document,
    setup_branded_pages,
    _hex,
)

_GOAL_LABEL = {
    "fat_loss": "Pérdida de grasa", "muscle_gain": "Ganancia muscular",
    "recomp": "Recomposición", "maintenance": "Mantenimiento",
    "injury_recovery": "Recuperación de lesión",
}
_LEVEL_LABEL = {"beginner": "Principiante", "intermediate": "Intermedio", "advanced": "Avanzado"}
_PLACE_LABEL = {"gym": "Gimnasio", "home": "Casa", "outdoor": "Exterior"}
_ACTIVITY_LABEL = {
    "sedentary": "Sedentaria (oficina)", "light": "Ligera (de pie a ratos)",
    "active": "Activa (trabajo físico)", "very_active": "Muy activa (físico intenso)",
}
_DIET_LABEL = {"flexible_7": "Flexible (7 opciones)", "strict": "Estricta"}
_DIET_PATTERN_LABEL = {
    "vegano": "Vegano", "vegetariano": "Vegetariano", "pescetariano": "Pescetariano",
    "sin_cerdo": "Sin cerdo", "halal": "Halal", "kosher": "Kosher",
}
_SEX_LABEL = {"male": "Hombre", "female": "Mujer"}


def _f1(v: float | None, unit: str = "") -> str:
    return "—" if v is None else f"{v:.1f}{unit}".replace(".0", "").replace(".", ",")


def _fecha(v: str | None) -> str:
    if not v:
        return "—"
    try:
        y, m, d = v.split("-")
        return f"{d}/{m}/{y}"
    except Exception:  # noqa: BLE001 — un formato inesperado no rompe el documento
        return v


def generate_anamnesis_doc(
    *,
    brand: DocBrand,
    client_name: str,
    sex: str | None,
    age: int | None,
    height_cm: float | None,
    start_weight_kg: float | None,
    current_weight_kg: float | None,
    body_fat_pct: float | None,
    goal_type: str | None,
    goal_weight_kg: float | None,
    goal_deadline: str | None,
    level: str | None,
    training_days: int | None,
    training_place: str | None,
    session_max_min: int | None,
    daily_activity_level: str | None,
    equipment: list[str] | None,
    diet_mode: str | None,
    diet_pattern: str | None,
    meals_per_day: int | None,
    food_allergies: list[str] | None,
    food_dislikes: list[str] | None,
    food_likes: list[str] | None,
    injuries_notes: str | None,
    medical_notes: str | None,
    medication_notes: str | None,
    current_supplements: str | None,
    sport_history: str | None,
    lifestyle_notes: str | None,
    generated_on: date | None = None,
) -> bytes:
    doc = init_document(brand)
    setup_branded_pages(doc, banner_path=None,
                        footer_text=brand.name + (f" · {brand.tagline}" if brand.tagline else ""))

    add_cover(doc, brand, client_name, subtitle="Ficha de anamnesis",
              goal=_GOAL_LABEL.get(goal_type or "", "Datos de la asesoría"))

    # 1) Datos personales — cards de un vistazo
    add_section_heading(doc, brand, "Datos personales")
    add_cards_row(doc, brand, [
        ("Sexo", _SEX_LABEL.get(sex or "", "—")),
        ("Edad", f"{age} años" if age else "—"),
        ("Altura", _f1(height_cm, " cm")),
        ("Peso inicial", _f1(start_weight_kg, " kg")),
    ])
    if current_weight_kg is not None or body_fat_pct is not None:
        doc.add_paragraph()
        add_cards_row(doc, brand, [
            ("Peso actual", _f1(current_weight_kg, " kg")),
            ("% graso", _f1(body_fat_pct, " %")),
        ])

    # 2) Objetivo
    doc.add_page_break()
    add_section_heading(doc, brand, "Objetivo")
    clean_table(doc, ["Dato", "Valor"], [
        ["Objetivo", _GOAL_LABEL.get(goal_type or "", "—")],
        ["Peso objetivo", _f1(goal_weight_kg, " kg")],
        ["Fecha límite", _fecha(goal_deadline)],
        ["Nivel", _LEVEL_LABEL.get(level or "", "—")],
    ], brand, col_widths=[3200, 6466])

    # 3) Entrenamiento
    add_section_heading(doc, brand, "Entrenamiento")
    clean_table(doc, ["Dato", "Valor"], [
        ["Días de entreno/semana", str(training_days) if training_days else "—"],
        ["Lugar", _PLACE_LABEL.get(training_place or "", "—")],
        ["Duración máx. por sesión", f"{session_max_min} min" if session_max_min else "—"],
        ["Actividad diaria (fuera del gimnasio)", _ACTIVITY_LABEL.get(daily_activity_level or "", "—")],
        ["Equipamiento declarado", ", ".join(equipment) if equipment else "Ninguno / no aplica"],
    ], brand, col_widths=[3800, 5866])

    # 4) Alimentación — alergias en rojo: es seguridad, no una preferencia más
    doc.add_page_break()
    add_section_heading(doc, brand, "Alimentación")
    clean_table(doc, ["Dato", "Valor"], [
        ["Modo de dieta", _DIET_LABEL.get(diet_mode or "", "—")],
        ["Patrón dietético", _DIET_PATTERN_LABEL.get(diet_pattern or "", "Sin restricción declarada")],
        ["Comidas al día", str(meals_per_day) if meals_per_day else "—"],
    ], brand, col_widths=[3800, 5866])
    doc.add_paragraph()
    p = doc.add_paragraph()
    run = p.add_run(
        "⚠ Alergias / intolerancias: " + (", ".join(food_allergies) if food_allergies else "Ninguna declarada")
    )
    run.font.bold = True
    run.font.color.rgb = _hex("#B3261E" if food_allergies else "#6B6B76")
    if food_dislikes:
        doc.add_paragraph("No le gustan: " + ", ".join(food_dislikes))
    if food_likes:
        doc.add_paragraph("Preferencias / le gustan: " + ", ".join(food_likes))

    # 5) Salud — lo crítico (lesiones, medicación) siempre visible
    doc.add_page_break()
    add_section_heading(doc, brand, "Salud")
    if injuries_notes:
        doc.add_heading("Lesiones", level=2)
        add_bullets(doc, [l for l in injuries_notes.splitlines() if l.strip()] or [injuries_notes])
    else:
        doc.add_paragraph("Sin lesiones declaradas.")
    if medical_notes:
        doc.add_heading("Patologías y salud", level=2)
        add_bullets(doc, [l for l in medical_notes.splitlines() if l.strip()] or [medical_notes])
    if medication_notes:
        doc.add_heading("Medicación", level=2)
        add_bullets(doc, [l for l in medication_notes.splitlines() if l.strip()] or [medication_notes])
    if current_supplements:
        doc.add_heading("Suplementación actual", level=2)
        doc.add_paragraph(current_supplements)

    # 6) Experiencia y estilo de vida
    if sport_history or lifestyle_notes:
        doc.add_page_break()
        add_section_heading(doc, brand, "Experiencia y estilo de vida")
        if sport_history:
            doc.add_heading("Historial deportivo", level=2)
            doc.add_paragraph(sport_history)
        if lifestyle_notes:
            doc.add_heading("Hábitos y estilo de vida", level=2)
            add_bullets(doc, [l for l in lifestyle_notes.splitlines() if l.strip()] or [lifestyle_notes])

    if generated_on:
        p = doc.add_paragraph()
        run = p.add_run(f"Ficha generada el {generated_on.strftime('%d/%m/%Y')}")
        run.font.size = Pt(8.5)
        run.font.color.rgb = _hex("#6B6B76")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
