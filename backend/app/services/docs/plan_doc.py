"""Documento Word del plan — DOSSIER con el lenguaje visual de la instancia.

Diseño editorial propio (app/branding.py), deliberadamente DISTINTO del plan
de origen del motor: portada de producto (arte negro/dorado con laurel),
títulos a la izquierda, reglas finas doradas en vez de barras rellenas, cajas
marfil sobrias y sin imágenes decorativas. La ESTRUCTURA interna del contenido
es la del motor; ENTRENAMIENTO conserva sus apartados (estructura, progresión,
sesiones, cardio, deload) con el mismo estilo.

La NUTRICIÓN va en formato DOCUMENTO (prosa y listas, sin rejillas): objetivo
con números integrados, cambios de la revisión, tu día, tus comidas (3 opciones
por toma), pautas esenciales y suplementación solo si el plan la define — las
secciones plantilla del plan de origen (alimentos por grupos, plato saludable,
ideas, salsas/yogures/quesos) quedaron fuera a propósito.
"""

from __future__ import annotations

import io
import os
import unicodedata
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

from app import branding
from app.services.docs.word_base import (
    CONTENT_WIDTH_DXA,
    DocBrand,
    clean_table,
    float_image_right,
    info_box,
    init_document,
    open_box,
    section_rule,
    set_page_background,
    setup_reference_pages,
    _hex,
    _keep_lines,
)

ASSETS = Path(__file__).resolve().parent.parent.parent / "assets" / "plan"

# Paleta OSCURA del DOSSIER — identidad Professional (app/branding.py):
# página NEGRA con texto marfil y acentos dorados (lo que el cliente ve es
# absolutamente distinto del plan de origen del motor; la estructura interna
# del contenido es la misma).
PAGE_BG = "0F0E0C"     # fondo de página: negro cálido de la marca
PANEL = "1C1913"       # paneles/cajas y cabeceras de tabla sobre el negro
PANEL_ALT = "17150F"   # zebra de tablas
BORDER = "3A342A"      # bordes sutiles sobre negro
IVORY = "F5F3EE"       # texto principal
SLATE = "4E626C"       # regla de subsecciones (pizarra clara)
GOLD = "E9A90F"        # regla dorada de secciones
GOLD_TEXT = "F7C33A"   # etiquetas doradas sobre paneles
INK = "F5F3EE"         # títulos grandes (marfil sobre negro)

DAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

# Pautas de cierre del documento de nutrición: POCAS y útiles (criterio de la
# casa — las secciones plantilla del plan de origen quedaron fuera del dossier).
PAUTAS_ESENCIALES = [
    "Agua: 2-3 litros al día.",
    "Cocina al vapor, a la plancha, al horno o en freidora de aire — siempre con aceite de oliva virgen extra.",
    "Verdura en las comidas principales y fruta de postre: cuanta más variedad, mejor.",
    "Pésate en ayunas y registra tu día en la app: tu plan se ajusta con tus datos reales, no con sensaciones.",
    "¿Hambre o ansiedad entre horas? Infusiones, gelatinas 0 % o más ración de verdura.",
]


def _goal_label(goal: str | None) -> str:
    return {"fat_loss": "Pérdida de grasa", "muscle_gain": "Ganancia muscular",
            "recomp": "Recomposición"}.get(goal or "", "Plan personalizado")


def _objetivo_pairs(goal: str | None) -> list[tuple[str, str]]:
    """OBJETIVOS como el ejemplo: dos líneas con etiqueta en negrita vino
    ("Antropométrico: …" / "Nutricional: …")."""
    anthro = {
        "fat_loss": "Déficit.",
        "muscle_gain": "Superávit.",
        "recomp": "Mantenimiento / recomposición.",
    }.get(goal or "", "Según objetivo.")
    nutri = {
        "fat_loss": "organizar y planificar la alimentación diaria, manteniendo proteína "
                    "para preservar masa muscular.",
        "muscle_gain": "organizar y planificar la alimentación diaria, aportando energía y "
                       "proteína suficientes para ganar masa muscular.",
        "recomp": "organizar y planificar la alimentación diaria, con proteína alta para "
                  "perder grasa y ganar o mantener músculo.",
    }.get(goal or "", "organizar y planificar la alimentación diaria según tu objetivo.")
    return [("Antropométrico", anthro), ("Nutricional", nutri)]


def _title(doc: Document, text: str, sub: str | None = None) -> None:
    """Cabecera editorial del dossier: título grande a la IZQUIERDA en tinta,
    subtítulo (cliente) en bronce con mayúsculas — nada centrado ni de colores
    de relleno (lenguaje propio de la instancia, distinto del plan de origen)."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(text)
    r.font.size = Pt(25)
    r.font.bold = True
    r.font.color.rgb = _hex(INK)
    if sub:
        ps = doc.add_paragraph()
        ps.alignment = WD_ALIGN_PARAGRAPH.LEFT
        ps.paragraph_format.space_before = Pt(2)
        rs = ps.add_run(sub.upper())
        rs.font.size = Pt(11)
        rs.font.bold = True
        rs.font.color.rgb = _hex(GOLD)
        rPr = rs._r.get_or_add_rPr()
        from docx.oxml.ns import qn as _qn
        sp = rPr.makeelement(_qn("w:spacing"), {_qn("w:val"): "22"})
        rPr.append(sp)


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def _ajuste_text(nutrition: dict, goal: str | None) -> str:
    """Celda 'Ajuste aplicado': el ajuste real sobre el TDEE estimado."""
    tdee = nutrition.get("tdee_kcal") or 0
    target = nutrition.get("target_kcal") or 0
    if not tdee:
        return _goal_label(goal)
    delta = round(target - tdee)
    pct = round(abs(delta) / tdee * 100)
    # La etiqueta la manda el SIGNO del delta real, no el objetivo: si el objetivo
    # es "ganancia" pero las kcal quedaron por debajo del TDEE (tras editar o por
    # el suelo calórico), decir "Superávit +-150" sería falso y contradictorio.
    if delta > 0:
        return f"Superávit +{delta} kcal ({pct}%)"
    if delta == 0:
        return "Mantenimiento ±0 kcal"
    return f"Déficit {delta} kcal ({pct}%)"


def _concise_notas(nutrition: dict, goal: str | None, meals: list[dict]) -> list[str]:
    """NOTAS DEL AJUSTE concisas y computadas (como el ejemplo), NO el rationale
    verboso de la IA."""
    tdee = round(nutrition.get("tdee_kcal") or 0)
    target = round(nutrition.get("target_kcal") or 0)
    out: list = []
    if tdee and target:
        delta = target - tdee
        word = ("Subida progresiva." if delta > 0
                else "Mantenimiento." if delta == 0
                else "Bajada progresiva.")
        out.append(("Calorías totales",
                    f"{delta:+d} kcal sobre el TDEE estimado (≈ {tdee} → {target} kcal). {word}"))
    if meals:
        toma = ", ".join(f"{m.get('name','')} ({m.get('time','')})".strip()
                         for m in meals if m.get("name"))
        if toma:
            out.append(("Estructura", f"{toma}."))
    return out or [nutrition.get("rationale", "")]


def _ingredients_str(opt: dict) -> str:
    out = []
    for ing in opt.get("ingredients", []):
        g = ing.get("grams")
        out.append(f"{ing.get('food','')} {round(g)} g" if g else ing.get("food", ""))
    return ", ".join(out)


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _section(doc: Document, text: str, sub: bool = False) -> None:
    """Rúbrica del dossier oscuro: mayúsculas marfil + regla dorada (secciones)
    o pizarra (subsecciones de comidas/sesiones)."""
    section_rule(doc, text, rule_color=SLATE if sub else GOLD,
                 text_color=IVORY, size=10 if sub else 12)


def _table(doc, headers, rows, brand, **kw):
    """clean_table con el tema oscuro del dossier por defecto."""
    kw.setdefault("header_color", PANEL)
    kw.setdefault("header_text_color", GOLD_TEXT)
    kw.setdefault("body_fills", (PANEL, PANEL_ALT))
    kw.setdefault("border_color", BORDER)
    return clean_table(doc, headers, rows, brand, **kw)


def _box(doc, items, **kw):
    """info_box con el tema oscuro del dossier por defecto."""
    kw.setdefault("fill", PANEL)
    kw.setdefault("label_color", GOLD_TEXT)
    kw.setdefault("border_color", BORDER)
    return info_box(doc, items, **kw)


def _doc_para(doc: Document, size_after: float = 5):
    """Párrafo de DOCUMENTO alineado al ancho de contenido (mismas sangrías que
    reglas y tablas): la nutrición se lee como texto corrido, no como rejilla."""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(size_after)
    sec = doc.sections[0]
    usable_emu = int(sec.page_width) - int(sec.left_margin) - int(sec.right_margin)
    indent_emu = (usable_emu - int(Pt(CONTENT_WIDTH_DXA / 20))) // 2
    if indent_emu > 0:
        pf.left_indent = indent_emu
        pf.right_indent = indent_emu
    _keep_lines(p)
    return p


def _para(doc: Document, item, bullet: bool = False):
    """Línea del dossier: str, o (etiqueta, valor) con la etiqueta en dorado."""
    p = _doc_para(doc)
    if bullet:
        rb = p.add_run("•  ")
        rb.font.bold = True
        rb.font.color.rgb = _hex(GOLD)
    if isinstance(item, (tuple, list)):
        label, value = item
        rl = p.add_run(f"{label}: ")
        rl.font.bold = True
        rl.font.color.rgb = _hex(GOLD_TEXT)
        p.add_run(str(value))
    else:
        p.add_run(str(item))
    return p


def _dossier_cover(doc: Document, cover_path: Path, client_name: str,
                   month_index: int, product_sub: str) -> None:
    """Portada del DOSSIER (Propuesta 1): arte de marca a página completa con el
    nombre del cliente y el mes debajo. La página 1 va SIN cabecera ni pie
    (first-page header vacío) para que el dossier abra limpio; el contenido
    empieza en la página 2 con la cabecera de siempre."""
    from datetime import date as _date

    if not os.path.exists(str(cover_path)):
        return  # sin arte de portada: el documento empieza directo (como antes)
    sec = doc.sections[0]
    sec.different_first_page_header_footer = True
    # Desvincular el header/footer de primera página del principal: si quedan
    # enlazados, Word/LibreOffice pintan el pie normal también en la portada.
    sec.first_page_header.is_linked_to_previous = False
    sec.first_page_footer.is_linked_to_previous = False
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(0)
    try:
        p.add_run().add_picture(str(cover_path), width=Inches(5.55))
    except Exception:
        # Arte ilegible: portada tipográfica mínima en su lugar.
        r = p.add_run(branding.BRAND_WORDMARK)
        r.font.size = Pt(28)
        r.font.bold = True
    np_ = doc.add_paragraph()
    np_.alignment = WD_ALIGN_PARAGRAPH.CENTER
    np_.paragraph_format.space_before = Pt(16)
    np_.paragraph_format.space_after = Pt(0)
    rn = np_.add_run(client_name)
    rn.font.size = Pt(17)
    rn.font.bold = True
    rn.font.color.rgb = _hex(INK)
    hoy = _date.today()
    sp = doc.add_paragraph()
    sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sp.paragraph_format.space_before = Pt(2)
    rs = sp.add_run(f"{product_sub} · Mes {month_index} · {MESES[hoy.month - 1].capitalize()} {hoy.year}")
    rs.font.size = Pt(10.5)
    rs.font.color.rgb = _hex("A9A395")
    doc.add_page_break()


def generate_plan_doc(
    *, brand: DocBrand, client_name: str, month_index: int, goal_type: str | None,
    diet_mode: str | None, nutrition: dict, training: dict, education: dict,
    exercise_names: dict | None = None,
    food_allergies: list[str] | None = None, food_dislikes: list[str] | None = None,
    include_training: bool = False, include_nutrition: bool = True,
    package_tier: str | None = None,
) -> bytes:
    # Por defecto el PLAN es SOLO DIETA (el entrenamiento vive en el tracker del
    # portal). include_nutrition=False es el plan `train`: documento SOLO de
    # entrenamiento (sin un "PLAN NUTRICIONAL" lleno de ceros).
    exercise_names = exercise_names or {}

    # Ninguna toma sin contenido en el PDF: los planes antiguos (guardados antes
    # del relleno automático) reciben aquí sus 3 opciones por defecto escaladas
    # a los macros de la toma — el cliente nunca lee una "toma libre". Sobre una
    # copia: el dict del caller (posible fila de BD en sesión) no se muta.
    import copy as _copy

    from app.services.meal_fallback import ensure_bank_slots

    nutrition = _copy.deepcopy(nutrition)
    if include_nutrition:
        ensure_bank_slots(nutrition, allergies=food_allergies or [],
                          dislikes=food_dislikes or [])

    doc = init_document(brand)
    # Página NEGRA de marca: el dossier entero va en oscuro (blanco y dorado
    # sobre negro), también en el PDF (verificado con LibreOffice).
    set_page_background(doc, PAGE_BG)
    # Calibri (en el contenedor se sustituye por Carlito, idéntico) y texto
    # base MARFIL: todo lo que no fije color hereda el claro sobre negro.
    for _sname in ("Normal", "Heading 1", "Heading 2", "Heading 3"):
        try:
            doc.styles[_sname].font.name = "Calibri"
            doc.styles[_sname].font.color.rgb = _hex(IVORY)
        except Exception:
            pass
    # DOSSIER de marca (Propuesta 1): portada por producto + cabecera con el
    # nombre comercial del plan en todas las páginas de contenido. El tier del
    # cliente decide el producto; sin tier (llamadas antiguas), Génesis por
    # contenido completo o el documento de entrenamiento suelto.
    from datetime import date as _date

    tier = (package_tier or "").strip().lower()
    tier = {"start": "nutri", "pro": "full"}.get(tier, tier)
    if tier not in branding.DOC_PRODUCTS:
        tier = "train" if (include_training and not include_nutrition) else "full"
    product, product_sub, cover_file = branding.DOC_PRODUCTS[tier]

    setup_reference_pages(
        # Logo TRANSPARENTE (blanco+dorado): se integra en la página negra
        # sin tarjeta visible alrededor.
        doc, logo_path=str(ASSETS / "brand_logo_dark.png"),
        right_title=f"{product.upper()} | {client_name}",
        right_sub=str(_date.today().year),
        footer_text=branding.DOC_FOOTER,
    )
    _dossier_cover(doc, ASSETS / cover_file, client_name, month_index, product_sub)

    if include_nutrition:
        # ================== NUTRICIÓN (formato DOCUMENTO) ==================
        # Se lee como un dossier de texto: prosa y listas con reglas doradas,
        # sin rejillas de tablas ni cajas — solo lo esencial.
        _title(doc, "PLAN NUTRICIONAL", client_name)
        macros = nutrition.get("macros", {})
        meals = nutrition.get("meals", [])

        # --- Tu objetivo: números y ajuste integrados en el texto ---
        _section(doc, "Tu objetivo")
        kcal = round(nutrition.get("target_kcal", 0) or 0)
        _para(doc, (
            f"Objetivo: {_goal_label(goal_type).lower()}. Tu plan esta calculado en "
            f"~ {kcal} kcal diarias ({_ajuste_text(nutrition, goal_type)}), repartidas en "
            f"{round(macros.get('protein_g', 0) or 0)} g de proteina, "
            f"{round(macros.get('carbs_g', 0) or 0)} g de hidratos de carbono y "
            f"{round(macros.get('fat_g', 0) or 0)} g de grasas."))
        for nota in _concise_notas(nutrition, goal_type, meals):
            _para(doc, nota)

        # --- Cambios de la última revisión: lista de documento (no tabla) ---
        aa = nutrition.get("applied_adjustments") or {}
        aa_items = aa.get("items") or []
        if aa_items:
            _section(doc, f"Cambios de tu plan · revisión #{aa.get('period_index', '')}")
            for it in aa_items:
                area = (it.get("area") or "").capitalize()
                detail = it.get("detail") or it.get("change") or ""
                reason = (it.get("reason") or "").strip()
                texto = detail + (f" — {reason}" if reason else "")
                _para(doc, (area, texto) if area else texto, bullet=True)

        # --- Tu día: una línea por toma ---
        if meals:
            _section(doc, "Tu día")
            for m in meals:
                nombre = m.get("name") or f"Comida {m.get('slot')}"
                p = _doc_para(doc)
                rt = p.add_run(f"{m.get('time','')}")
                rt.font.bold = True
                rt.font.color.rgb = _hex(GOLD_TEXT)
                rn = p.add_run(f"   {nombre}")
                rn.font.bold = True
                est = _estrategia(m.get("name", ""))
                if est:
                    p.add_run(f" — {est}")

        # --- Tus comidas: las opciones, como texto del documento ---
        bank = nutrition.get("meal_bank") or {}
        # El formato lo decide el banco PERSISTIDO (bank["mode"]); diet_mode del
        # cliente es solo fallback (plan legado sin regenerar).
        diet_mode = bank.get("mode") or diet_mode
        if diet_mode != "strict" and meals:
            _section(doc, "Tus comidas")
            _para(doc, "Cada comida tiene tres opciones equivalentes: elige cada día la "
                       "que mejor te venga — todas cumplen tus números.")
            blocks = {s.get("slot"): s for s in bank.get("slots", [])}
            for m in meals:
                nombre = m.get("name") or "Comida"
                _section(doc, f"{nombre} · {m.get('time','')}", sub=True)
                sb = blocks.get(m.get("slot"), {})
                if sb.get("fmt") == "equivalences" and sb.get("equivalences"):
                    # Planes LEGADO con equivalencias: caja de compatibilidad
                    # (el método de esta marca son opciones cerradas).
                    cell = open_box(doc, PANEL, cant_split=False, border_color=BORDER)
                    _render_equivalences(cell, sb["equivalences"])
                    continue
                opts = sb.get("options", [])[:3]
                for n, opt in enumerate(opts, start=1):
                    p = _doc_para(doc)
                    rl = p.add_run(f"Opción {n} — ")
                    rl.font.bold = True
                    rl.font.color.rgb = _hex(GOLD_TEXT)
                    rtit = p.add_run(f"{opt.get('title','')}. ")
                    rtit.font.bold = True
                    p.add_run(f"{_ingredients_str(opt)}.")
                if not opts:
                    # Toma añadida a mano (sin recetario aún): guía digna.
                    t = m.get("target") or {}
                    detail = ""
                    if t.get("kcal"):
                        detail = (f" (~{round(t['kcal'])} kcal · P {round(t.get('protein_g') or 0)} g · "
                                  f"CH {round(t.get('carbs_g') or 0)} g · G {round(t.get('fat_g') or 0)} g)")
                    _para(doc, "Toma libre: combina alimentos que te gusten hasta cuadrar "
                               f"los macros objetivo de esta comida{detail}.")

        # --- Menú semanal SOLO en modo estricto (es la esencia de ese modo) ---
        if diet_mode == "strict":
            _weekly_section(doc, brand, diet_mode, nutrition, bank)

        # --- Pautas esenciales ---
        _section(doc, "Pautas esenciales")
        for pauta in PAUTAS_ESENCIALES:
            _para(doc, pauta, bullet=True)

        # --- Suplementación: SOLO si el plan la define (sin relleno) ---
        supps = nutrition.get("supplements", [])
        if supps:
            _section(doc, "Suplementación")
            for sup in supps:
                nombre = sup.get("name", "")
                resto = " · ".join(x for x in (sup.get("dose", ""), sup.get("timing", "")) if x)
                _para(doc, (nombre, resto) if resto else nombre, bullet=True)

    if not include_training or not training:
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    # ======================= ENTRENAMIENTO =======================
    if include_nutrition:
        doc.add_page_break()
    _title(doc, "PLAN DE ENTRENAMIENTO", client_name)

    _section(doc, f"Estructura · {training.get('split_name','')}")
    _box(doc, [
        (f"{len(training.get('sessions', []))} días/semana", training.get("split_rationale", "")),
    ])

    prog = training.get("weekly_progression", [])
    if prog:
        _section(doc, "Progresión semanal")
        rows = [[f"Sem {w.get('week')}", w.get("intent", ""), f"{w.get('load_pct','')}%",
                 f"RIR {w.get('rir_target','')}", w.get("volume_note", "")] for w in prog]
        _table(doc, ["Semana", "Enfoque", "Carga", "RIR", "Notas"], rows, brand,
                    header_color=PANEL, header_text_color=GOLD_TEXT,
                    col_widths=[1100, 1800, 1100, 1100, 3926], keep_together=False)

    for sess in training.get("sessions", []):
        _section(doc, f"{sess.get('day','')} · {sess.get('name','')}", sub=True)
        # Calentamiento en caja opaca (legible aunque caiga sobre la banda)
        if sess.get("warmup"):
            _box(doc, [("Calentamiento", sess["warmup"])])
        rows = []
        for ex in sess.get("exercises", []):
            name = exercise_names.get(ex.get("exercise_id"), f"Ejercicio #{ex.get('exercise_id','')}")
            cue = ex.get("technique_cue", "") or ""
            # Indicaciones personalizadas del coach: en la misma celda, en línea
            # aparte y con etiqueta, para que el cliente no se las salte.
            notes = (ex.get("coach_notes") or "").strip()
            if notes:
                cue = f"{cue}\nIndicación para ti: {notes}" if cue else f"Indicación para ti: {notes}"
            rows.append([
                name, f"{ex.get('sets','')}×{ex.get('rep_range','')}", f"RIR {ex.get('rir','')}",
                f"{ex.get('rest_sec','')}s", cue,
            ])
        if rows:
            _table(doc, ["Ejercicio", "Series", "RIR", "Descanso", "Clave técnica"], rows,
                        brand, header_color=PANEL, header_text_color=GOLD_TEXT,
                        col_widths=[2600, 1300, 1100, 1100, 2926], keep_together=False)
        if sess.get("cooldown"):
            _box(doc, [("Vuelta a la calma", sess["cooldown"])])

    cardio = training.get("cardio") or {}
    if cardio.get("daily_steps") or cardio.get("sessions"):
        _section(doc, "Cardio y NEAT")
        items = [("Pasos diarios objetivo", str(cardio.get("daily_steps", "—")))]
        for cs in cardio.get("sessions", []):
            items.append((cs.get("type", "").upper(),
                          f"{cs.get('minutes','')} min × {cs.get('times_per_week','')}/sem"
                          + (f" — {cs.get('notes')}" if cs.get("notes") else "")))
        _box(doc, items)

    if training.get("deload_instructions"):
        _section(doc, "Semana de descarga (deload)")
        _box(doc, [training["deload_instructions"]])

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _render_equivalences(container, eq: dict, image_path: str | None = None) -> None:
    """Renderiza una comida en formato de equivalencias DENTRO de una caja (cell):
    línea intro + un párrafo por grupo con sus alimentos intercambiables. Si se
    pasa image_path, una foto redonda flota a la derecha con el texto alrededor."""
    intro = (eq.get("intro") or "").strip()
    p = container.paragraphs[0]  # reutiliza el primer párrafo (vacío) de la caja
    p.paragraph_format.space_after = Pt(4)
    if image_path and os.path.exists(image_path):
        try:
            float_image_right(p, image_path, Inches(1.5))
        except Exception:
            pass
    # Frase guía sin duplicados: si el intro del plan ya empieza por "Elige una
    # opción..." no se antepone otra vez, y se normaliza el cierre a un solo ":".
    base = "Elige una opción de cada grupo."
    if intro:
        low = intro.lower()
        if low.startswith("elige una opción") or low.startswith("elige una opcion"):
            txt = intro.rstrip(".:") + ":"
        else:
            txt = f"{base} {intro.rstrip('.:')}:"
    else:
        txt = base
    r = p.add_run(txt)
    r.font.italic = True
    r.font.size = Pt(9.5)
    r.font.color.rgb = _hex("A9A395")
    for g in eq.get("groups", []):
        p = container.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        _keep_lines(p)  # un grupo de equivalencias no se parte entre páginas
        rl = p.add_run(f"{g.get('name','')}: ")
        rl.font.bold = True
        rl.font.color.rgb = _hex(GOLD_TEXT)
        note = (g.get("note") or "").strip()
        items = [f"{it.get('food','')} ({it.get('amount','')})"
                 for it in g.get("items", []) if it.get("food")]
        body = note
        if items:
            body = (note + " " if note else "") + " o ".join(items)
        if body and not body.endswith("."):
            body += "."
        p.add_run(body)


def _estrategia(name: str) -> str:
    n = _norm(name)
    if "pre" in n:
        return "Pre-entreno: CH refinados, proteína magra, grasas reducidas."
    if "post" in n:
        return "Post-entreno: recuperación (proteína + CH)."
    if "cena" in n:
        return "Recuperación: integrales, proteína completa, grasas saludables."
    if "desayuno" in n:
        return "Ligero y de fácil digestión."
    if "media" in n or "merienda" in n:
        return "Sustancioso entre comidas principales."
    return "Comida equilibrada."


def _weekly_section(doc: Document, brand: DocBrand, diet_mode: str | None,
                    nutrition: dict, bank: dict) -> None:
    meals = nutrition.get("meals", [])
    if not meals:
        return
    _section(doc, "Ejemplo de dieta semanal")

    headers = ["Toma"] + DAYS
    rows: list[list[str]] = []
    if diet_mode == "strict":
        days = bank.get("days", [])
        by_day = {_norm(d.get("day")): d for d in days}
        order = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
        for m in meals:
            slot = m.get("slot")
            cells = []
            for dslug in order:
                d = by_day.get(dslug)
                title = ""
                if d:
                    for meal in d.get("meals", []):
                        if meal.get("slot") == slot:
                            title = meal.get("dish", {}).get("title", "")
                cells.append(title)
            rows.append([m.get("name", f"Comida {slot}")] + cells)
    else:
        blocks = {s.get("slot"): s for s in bank.get("slots", [])}
        for m in meals:
            sb = blocks.get(m.get("slot"), {})
            wk = [x for x in (sb.get("weekly_examples") or []) if x]
            opts = sb.get("options", [])
            cells = []
            for di in range(7):
                if wk:
                    cells.append(wk[di % len(wk)])
                elif opts:
                    cells.append(opts[di % len(opts)].get("title", ""))
                else:
                    cells.append("")
            rows.append([m.get("name", f"Comida {m.get('slot')}")] + cells)

    if rows:
        # 8 columnas estrechas: fuente 8pt para que los nombres de plato no
        # desborden, y paginación con cabecera repetida (keep_together=False)
        # por si hay muchas tomas.
        _table(doc, headers, rows, brand, header_color=PANEL, header_text_color=GOLD_TEXT,
                    col_widths=[1500] + [1075] * 7, font_pt=8, keep_together=False)
