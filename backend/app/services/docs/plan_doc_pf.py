"""El documento de PROFESSIONAL (Centre Salut & Fitness): negro y dorado.

No es el de DQR con otros colores. Los dos negocios funcionan distinto y el
documento lo enseña:

· DQR es una asesoría online que vende meses cerrados: su PDF llega cargado de
  material de consulta (índice, grupos de alimentos, el plato saludable, ideas,
  sección educativa) porque el cliente no tiene a nadie delante.
· Professional es un CENTRO con mostrador y sala. El cliente viene, pregunta y
  se le corrige en persona; lo que necesita por escrito es lo que va a HACER
  esta quincena. Así que el documento es corto, va al grano, y dedica una
  sección entera —que en DQR no existe— a explicar el ciclo del centro: apuntas
  cada día, a los quince días lo revisamos juntos, ajustamos y sigues, con
  renovación mensual.

Qué cambia respecto a DQR, en concreto:
· PORTADA negra con el logo dorado y las tres fechas que importan (DQR no tiene
  portada: arranca en el contenido).
· «TU MES EN UNA PÁGINA»: las cifras en fichas grandes para fotografiarlas.
· La dieta va en ORDEN DEL DÍA (de la primera toma a la última), no en tablas
  de referencia + bloques sueltos.
· Cada sesión es una FICHA con su día, no una barra más.
· «TU SEGUIMIENTO»: el ciclo del centro. No existe en DQR.
· Fuera el índice, los grupos de alimentos, el plato, las ideas, las salsas,
  los yogures, los quesos y la sección educativa.

Lo que NO cambia, porque no puede: los NÚMEROS. Salen del mismo motor
(`metrics`), pasan los mismos guardarraíles y se filtran por las mismas
alergias, aversiones y patrón dietético. Un documento distinto es una piel
distinta, nunca una matemática distinta.

⚠️ Compatibilidad con «Subir Word editado»: las TABLAS de datos conservan las
cabeceras que `word_import` reconoce (son nombres de columna, no estructura) y
las barras que anclan cajas editables se traducen allí con `_ALIAS_BARRA`. Si
renombras una barra de este documento, añade su alias o el coach editará el
Word y sus cambios se perderán en silencio.
"""

from __future__ import annotations

import io
import os
from datetime import date as _date

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

from app.services.docs.word_base import (
    CONTENT_WIDTH_DXA,
    DocBrand,
    clean_table,
    info_box,
    init_document,
    open_box,
    section_bar,
    setup_reference_pages,
    spacer,
    _hex,
    _keep_lines,
    _keep_with_next,
    _no_table_borders,
    _set_cell_margins,
    _shade_cell,
)

# --- Paleta: negro principal, detalles dorados -----------------------------
NEGRO = "111111"       # barras de sección y cabeceras de tabla
CARBON = "0B0B0B"      # la portada
ORO = "C9A227"         # el detalle: texto sobre negro, etiquetas, filetes
ORO_PAPEL = "FBF6E7"   # relleno de las cajas (dorado al 6 %, legible en papel)
GRIS = "F4F3F1"        # zebrado de las tablas
TINTA = "1A1A1A"

DIAS_ORDEN = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]

_OBJETIVO = {
    "fat_loss": "Bajar grasa",
    "muscle_gain": "Ganar músculo",
    "recomp": "Bajar grasa y ganar músculo",
    "maintenance": "Mantener y coger el hábito",
    "injury_recovery": "Volver después de una lesión",
}


def _n(x) -> str:
    """Cifra en español: 2.200, 1,5. El cliente lee su idioma, no el del código."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if abs(v - round(v)) < 0.05:
        return f"{int(round(v)):,}".replace(",", ".")
    return f"{v:.1f}".replace(".", ",")


def _norm(s: str) -> str:
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFKD", str(s).lower())
                   if not unicodedata.combining(c)).strip()


# --- piezas propias de Professional ----------------------------------------

def _portada(doc: Document, brand: DocBrand, client_name: str, month_index: int,
             goal_type: str | None, generated_on: _date | None,
             que_lleva: str) -> None:
    """La portada del PLAN: qué lleva, el objetivo y las fechas del ciclo."""
    hoy = generated_on or _date.today()
    _portada_generica(
        doc, brand, client_name, rotulo=que_lleva,
        datos=[("Objetivo", _OBJETIVO.get(goal_type or "", "A definir en el centro")),
               ("Entregado", hoy.strftime("%d/%m/%Y")),
               ("Mes de trabajo", str(month_index)),
               ("Próxima revisión", "a los 15 días de empezar")],
    )


def _portada_generica(doc: Document, brand: DocBrand, client_name: str, *,
                      rotulo: str, datos: list[tuple[str, str]]) -> None:
    """Bloque negro a toda página: rótulo dorado, nombre y los datos que traiga
    cada documento.

    La comparten el PLAN y el INFORME DE REVISIÓN: son los dos documentos que
    recibe el mismo cliente y tenían que abrir igual — el informe usaba la
    portada clara y centrada de DQR, así que parecían de dos negocios.

    El negro va en una CELDA sombreada, no en el fondo de la página: Word no
    sabe pintar un fondo a sangre que sobreviva a la conversión a PDF, y una
    celda sí. Dentro no hay más que tipografía — en negro, el lujo es el
    espacio."""
    tabla = doc.add_table(rows=1, cols=1)
    tabla.autofit = False
    celda = tabla.rows[0].cells[0]
    celda.width = Pt(CONTENT_WIDTH_DXA / 20)
    _shade_cell(celda, CARBON)
    _set_cell_margins(celda, top=520, bottom=520, left=400, right=400)
    _no_table_borders(tabla)

    def linea(texto: str, *, pt: float, color: str, bold: bool = False,
              espaciado: float = 0, antes: float = 0, primera: bool = False):
        p = celda.paragraphs[0] if primera else celda.add_paragraph()
        p.paragraph_format.space_before = Pt(antes)
        p.paragraph_format.space_after = Pt(0)
        _keep_lines(p)
        r = p.add_run(texto)
        r.font.size = Pt(pt)
        r.font.bold = bold
        r.font.color.rgb = _hex(color)
        if espaciado:
            # Espaciado entre letras: lo que convierte un rótulo en una marca.
            from docx.oxml.ns import qn

            rPr = r._element.get_or_add_rPr()
            sp = rPr.makeelement(qn("w:spacing"), {qn("w:val"): str(int(espaciado * 20))})
            rPr.append(sp)
        return p

    if brand.logo_path and os.path.exists(brand.logo_path):
        p = celda.paragraphs[0]
        p.paragraph_format.space_after = Pt(18)
        try:
            p.add_run().add_picture(brand.logo_path, width=Inches(2.0))
        except Exception:  # noqa: BLE001 — el logo nunca tumba el documento
            linea(brand.name.upper(), pt=17, color=ORO, bold=True, espaciado=4)
    else:
        linea(brand.name.upper(), pt=17, color=ORO, bold=True, espaciado=4, primera=True)

    linea(rotulo.upper(), pt=10, color=ORO, bold=True, espaciado=3, antes=8)
    linea(client_name, pt=30, color="FFFFFF", antes=10)
    linea("—" * 18, pt=9, color=ORO, antes=12)

    for etiqueta, valor in datos:
        p = celda.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(0)
        _keep_lines(p)
        re_ = p.add_run(f"{etiqueta.upper()}   ")
        re_.font.size = Pt(8)
        re_.font.bold = True
        re_.font.color.rgb = _hex(ORO)
        rv = p.add_run(valor)
        rv.font.size = Pt(11)
        rv.font.color.rgb = _hex("FFFFFF")


def _fichas(doc: Document, tarjetas: list[tuple[str, str]]) -> None:
    """Las cifras del mes en fichas grandes: para verlas de un vistazo o
    fotografiarlas. Fondo negro y cifra dorada."""
    if not tarjetas:
        return
    spacer(doc, 8)
    tabla = doc.add_table(rows=1, cols=len(tarjetas))
    tabla.autofit = False
    ancho = CONTENT_WIDTH_DXA // len(tarjetas)
    for i, (etiqueta, valor) in enumerate(tarjetas):
        celda = tabla.rows[0].cells[i]
        celda.width = Pt(ancho / 20)
        _shade_cell(celda, NEGRO)
        _set_cell_margins(celda, top=170, bottom=170, left=60, right=60)
        pv = celda.paragraphs[0]
        pv.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pv.paragraph_format.space_after = Pt(2)
        rv = pv.add_run(valor)
        rv.font.size = Pt(16)
        rv.font.bold = True
        rv.font.color.rgb = _hex(ORO)
        pl = celda.add_paragraph()
        pl.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rl = pl.add_run(etiqueta.upper())
        rl.font.size = Pt(7.5)
        rl.font.bold = True
        rl.font.color.rgb = _hex("D8D5CE")
    _no_table_borders(tabla)


def _barra(doc: Document, texto: str) -> None:
    """Toda barra de Professional es igual: negra con el texto en oro. Sin
    semáforo de colores — un documento serio no necesita cinco."""
    section_bar(doc, texto, NEGRO, text_color=ORO)


def _nota(doc: Document, texto: str) -> None:
    """La línea guía bajo una barra: para qué sirve lo que viene."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(2)
    _keep_with_next(p)
    r = p.add_run(texto)
    r.font.size = Pt(8.5)
    r.font.italic = True
    r.font.color.rgb = _hex("5F5C57")


def _caja(doc: Document, items, *, entera: bool = True) -> None:
    info_box(doc, items, fill=ORO_PAPEL, label_color="8A6D14", cant_split=entera)


def _tabla(doc: Document, headers, rows, brand, anchos=None, **kw):
    return clean_table(doc, headers, rows, brand, col_widths=anchos,
                       header_color=NEGRO, header_text_color=ORO,
                       row_fills=("FFFFFF", GRIS), **kw)


def _ingredientes(opt: dict) -> str:
    partes = []
    for ing in opt.get("ingredients", []):
        g = ing.get("grams")
        casera = (ing.get("household") or "").strip()
        txt = f"{ing.get('food', '')} {int(round(g))} g" if g else str(ing.get("food", ""))
        if casera:
            txt += f" ({casera})"
        partes.append(txt)
    return ", ".join(partes)


def _prep(opt: dict) -> str:
    p = (opt.get("prep") or "").strip()
    m = opt.get("prep_minutes") or 0
    if p and m:
        return f"{p} ({m} min)"
    return p or (f"{m} min" if m else "")


def _macros_linea(macros: dict, kcal) -> str:
    return (f"P {_n(macros.get('protein_g', 0))} g · "
            f"CH {_n(macros.get('carbs_g', 0))} g · "
            f"G {_n(macros.get('fat_g', 0))} g")


def _ajuste(nutrition: dict) -> str:
    tdee = nutrition.get("tdee_kcal") or 0
    target = nutrition.get("target_kcal") or 0
    if not tdee or not target:
        return "—"
    delta = target - tdee
    if abs(delta) < 25:
        return "Mantenimiento"
    signo = "Déficit" if delta < 0 else "Superávit"
    pct = abs(delta) / tdee * 100
    return f"{signo} de {_n(abs(delta))} kcal ({pct:.0f} % de tu gasto)"


def _dur(ex: dict) -> str:
    s = ex.get("rest_sec")
    return f"{s}s" if s else "—"


# --- el documento -----------------------------------------------------------

def generate_plan_doc_pf(
    *, brand: DocBrand, client_name: str, month_index: int, goal_type: str | None,
    diet_mode: str | None, nutrition: dict, training: dict,
    exercise_names: dict | None = None,
    food_allergies: list[str] | None = None, food_dislikes: list[str] | None = None,
    include_training: bool = False, include_nutrition: bool = True,
    diet_pattern: str | None = None,
    generated_on: _date | None = None,
) -> bytes:
    """El plan de Professional en Word (el PDF sale de convertirlo).

    `education` no se recibe a propósito: este documento no lleva sección
    educativa — el centro la da en la sala. Lo demás es el MISMO plan que
    cualquier otra marca, con las mismas cifras y los mismos filtros."""
    import copy as _copy

    from app.services.docs.plan_doc import _food_blocked
    from app.services.meal_fallback import ensure_bank_slots

    exercise_names = exercise_names or {}
    bloqueados = [x for x in (food_allergies or []) + (food_dislikes or []) if x]

    nutrition = _copy.deepcopy(nutrition)
    if include_nutrition:
        ensure_bank_slots(nutrition, allergies=food_allergies or [],
                          dislikes=food_dislikes or [], diet_pattern=diet_pattern)

    doc = init_document(brand)
    que_lleva = ("Dieta y entrenamiento" if (include_nutrition and include_training)
                 else "Tu dieta" if include_nutrition else "Tu entrenamiento")
    pie = brand.name + (f" · {brand.contact_address}" if brand.contact_address else "")
    setup_reference_pages(
        doc, logo_path=(brand.logo_path if brand.logo_path
                        and os.path.exists(brand.logo_path) else None),
        right_title=f"{que_lleva.upper()} | {client_name}",
        right_sub=f"Mes {month_index} · {(generated_on or _date.today()).strftime('%d/%m/%Y')}",
        footer_text=pie,
    )

    _portada(doc, brand, client_name, month_index, goal_type, generated_on, que_lleva)
    doc.add_page_break()

    # ---------------------------------------------- tu mes en una página ---
    _barra(doc, "Tu mes en una página")
    macros = nutrition.get("macros", {}) if include_nutrition else {}
    fichas: list[tuple[str, str]] = []
    if include_nutrition:
        fichas += [
            ("Calorías al día", f"{_n(nutrition.get('target_kcal', 0))}"),
            ("Proteína", f"{_n(macros.get('protein_g', 0))} g"),
            ("Carbohidratos", f"{_n(macros.get('carbs_g', 0))} g"),
            ("Grasas", f"{_n(macros.get('fat_g', 0))} g"),
        ]
    if include_training and training:
        fichas.append(("Días de entreno", str(len(training.get("sessions") or []))))
    _fichas(doc, fichas)

    # El CICLO del centro. Esto es lo que Professional vende y lo que DQR no
    # tiene: pago mensual, seguimiento continuo y revisión cada quincena.
    _barra(doc, "Cómo trabajamos esto")
    _caja(doc, [
        ("1 · Lo sigues", "Come y entrena con lo que tienes aquí. No hace falta "
                          "que sea perfecto: hace falta que sea constante."),
        ("2 · Lo apuntas", "Cada día, en tu portal: peso, cómo te has visto y los "
                           "kilos que has movido. Es lo que nos deja ajustar con datos."),
        ("3 · Lo revisamos", "A los quince días lo miramos juntos, en el centro o "
                             "por videollamada, y te decimos qué cambia y por qué."),
        ("4 · Sigue", "Se ajusta lo que haga falta y arranca la siguiente quincena. "
                      "Mes a mes, sin permanencia."),
    ], entera=True)

    if include_nutrition:
        razon = (nutrition.get("rationale") or "").strip()
        if razon and not _food_blocked(razon, bloqueados, diet_pattern):
            # ⚠️ `word_import` re-lee esta caja: alias «por que lo planteamos asi».
            _barra(doc, "Por qué lo planteamos así")
            _caja(doc, [razon])

        # Tabla del contrato energético. Cabecera IDÉNTICA a la de DQR a
        # propósito: son nombres de columna y es lo que permite que el coach
        # edite el Word y se le aplique (`SIG_ENERGIA`).
        _barra(doc, "Tus cifras del día")
        _nota(doc, "Si cumples las tomas de abajo, el día cuadra solo: los gramos "
                   "de cada comida ya salen de aquí.")
        _tabla(doc, ["Calorías", "Reparto de macros", "Ajuste aplicado"],
               [[f"≈ {_n(nutrition.get('target_kcal', 0))} kcal",
                 _macros_linea(macros, nutrition.get("target_kcal", 0)),
                 _ajuste(nutrition)]],
               brand, anchos=[2400, 4226, 3040])

        _dieta(doc, brand, nutrition, diet_mode, bloqueados, diet_pattern)

    if include_training and training:
        if include_nutrition:
            doc.add_page_break()
        _entreno(doc, brand, training, exercise_names)

    _cierre(doc, brand)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _dieta(doc: Document, brand: DocBrand, nutrition: dict, diet_mode: str | None,
           bloqueados: list[str], diet_pattern: str | None) -> None:
    """La dieta en ORDEN DEL DÍA: de la primera toma a la última, cada una con
    lo que se puede comer. Sin tablas de consulta ni catálogos de alimentos —
    eso se pregunta en el mostrador."""
    from app.services.docs.plan_doc import _food_blocked

    meals = nutrition.get("meals") or []
    bank = nutrition.get("meal_bank") or {}

    if meals:
        # Cabecera `SIG_TOMAS`: la reconoce el importador del Word.
        _barra(doc, "Tu día, toma a toma")
        filas = []
        for m in meals:
            t = m.get("target") or {}
            estrategia = (m.get("strategy") or "").strip()
            if not estrategia and t.get("kcal"):
                estrategia = (f"≈ {_n(t['kcal'])} kcal · P {_n(t.get('protein_g', 0))} g · "
                              f"CH {_n(t.get('carbs_g', 0))} g · G {_n(t.get('fat_g', 0))} g")
            filas.append([m.get("time", ""), m.get("name", ""), estrategia or "—"])
        _tabla(doc, ["Hora", "Toma", "Estrategia"], filas, brand,
               anchos=[1200, 2400, 6066], keep_together=False)

    if _norm(diet_mode or "") == "strict" and bank.get("mode") == "strict":
        _barra(doc, "Tu semana, día a día")
        _nota(doc, "Menú cerrado: esto es lo que toca cada día. Si un día no puedes, "
                   "cámbialo por el mismo día de otra semana, no lo improvises.")
        nombres = {m.get("slot"): m for m in (nutrition.get("meals") or [])}
        for dia in bank.get("days") or []:
            # ⚠️ La barra de cada día la re-lee `word_import` (barras_dias).
            _barra(doc, str(dia.get("day", "")).capitalize())
            celda = open_box(doc, ORO_PAPEL, cant_split=True)
            primero = True
            for plato in dia.get("meals") or []:
                info = nombres.get(plato.get("slot")) or {}
                d = plato.get("dish") or {}
                etiqueta = info.get("name") or f"Toma {plato.get('slot', '')}"
                if info.get("time"):
                    etiqueta += f" · {info['time']}"
                p = celda.paragraphs[0] if primero else celda.add_paragraph()
                primero = False
                p.paragraph_format.space_after = Pt(4)
                _keep_lines(p)
                rl = p.add_run(f"{etiqueta}. ")
                rl.font.bold = True
                rl.font.color.rgb = _hex("8A6D14")
                p.add_run(f"{d.get('title', '')} — {_ingredientes(d)}.")
                prep = _prep(d)
                if prep:
                    pp = celda.add_paragraph()
                    pp.paragraph_format.space_after = Pt(4)
                    _keep_lines(pp)
                    rp = pp.add_run(prep)
                    rp.font.italic = True
                    rp.font.size = Pt(9)
        libre = (bank.get("free_meal_guidelines") or "").strip()
        if libre:
            _barra(doc, "Tu comida libre de la semana")
            _caja(doc, [libre])
        try:
            from app.services.docs.shopping_list import build_shopping_list

            compra = build_shopping_list(bank)
        except Exception:  # noqa: BLE001 — la compra nunca tumba el plan
            compra = {}
        if compra:
            _barra(doc, "Lo que tienes que comprar")
            lineas = []
            for categoria, items in compra.items():
                partes = [(f"{it['food']} {int(it['grams'])} g" if it.get("grams")
                           else f"{it['food']} (al gusto)") for it in items]
                if partes:
                    lineas.append(f"{categoria}: " + " · ".join(partes))
            if lineas:
                # Sin cota: la lista puede no caber en una página y partirla es
                # mejor que perder la mitad de la compra.
                _caja(doc, lineas, entera=False)
    elif meals:
        bloques = {s.get("slot"): s for s in bank.get("slots", [])}
        for m in meals:
            # ⚠️ «Nombre · hora» es la clave con la que `word_import` localiza
            # esta caja (barras_comida). No cambies el formato.
            _barra(doc, f"{m.get('name', 'Comida')} · {m.get('time', '')}")
            sb = bloques.get(m.get("slot"), {})
            equiv = bool(sb.get("fmt") == "equivalences" and sb.get("equivalences"))
            celda = open_box(doc, ORO_PAPEL, cant_split=not equiv)
            if equiv:
                from app.services.docs.plan_doc import _render_equivalences

                _render_equivalences(celda, sb["equivalences"])
                continue
            primero = True
            for n, opt in enumerate(sb.get("options", [])[:4], start=1):
                p = celda.paragraphs[0] if primero else celda.add_paragraph()
                primero = False
                p.paragraph_format.space_after = Pt(4)
                _keep_lines(p)
                rl = p.add_run(f"Opción {n}. ")
                rl.font.bold = True
                rl.font.color.rgb = _hex("8A6D14")
                p.add_run(f"{opt.get('title', '')} — {_ingredientes(opt)}.")
                prep = _prep(opt)
                if prep:
                    pp = celda.add_paragraph()
                    pp.paragraph_format.space_after = Pt(4)
                    _keep_lines(pp)
                    rp = pp.add_run(prep)
                    rp.font.italic = True
                    rp.font.size = Pt(9)
            if primero:
                t = m.get("target") or {}
                detalle = ""
                if t.get("kcal"):
                    detalle = (f" (≈ {_n(t['kcal'])} kcal · P {_n(t.get('protein_g', 0))} g · "
                               f"CH {_n(t.get('carbs_g', 0))} g · G {_n(t.get('fat_g', 0))} g)")
                celda.paragraphs[0].add_run(
                    "Esta toma la montas tú con lo que tengas en casa, cuadrando "
                    f"los macros de arriba{detalle}. Pregúntanos en el centro si dudas.")

    reglas = [r for r in (nutrition.get("flexibility_rules") or []) if str(r).strip()
              and not _food_blocked(str(r), bloqueados, diet_pattern)]
    recarga = (nutrition.get("refeed_or_break") or "").strip()
    if recarga and _food_blocked(recarga, bloqueados, diet_pattern):
        recarga = ""
    if reglas or recarga:
        # ⚠️ alias de `word_import`: «lo que puedes mover» → margen de maniobra.
        _barra(doc, "Lo que puedes mover")
        _nota(doc, "Un plan que no se puede seguir no sirve de nada. Esto es lo que "
                   "puedes cambiar sin salirte del objetivo.")
        lineas: list = [f"• {r}" for r in reglas]
        if recarga:
            lineas.append(("Si necesitas soltar", recarga))
        _caja(doc, lineas)

    supps = nutrition.get("supplements") or []
    if supps:
        # ⚠️ alias de `word_import`: «suplementos» → suplementación recomendada.
        _barra(doc, "Suplementos")
        _nota(doc, "Solo lo que suma en tu caso. Nada de esto sustituye a la comida.")
        _caja(doc, [f"{s.get('name', '')} — {s.get('dose', '')} ({s.get('timing', '')})"
                    for s in supps])


def _entreno(doc: Document, brand: DocBrand, training: dict,
             exercise_names: dict) -> None:
    """El entrenamiento como FICHAS de sesión: una por día, con lo que se hace
    y cómo se hace. Antes, una caja que explica en dos líneas cómo se lee —
    el cliente de un centro de barrio no tiene por qué saber qué es un RIR."""
    _barra(doc, f"Tu rutina · {training.get('split_name', '')}")
    dias = len(training.get("sessions") or [])
    _caja(doc, [(f"{dias} día{'s' if dias != 1 else ''} a la semana",
                 training.get("split_rationale", ""))])

    _barra(doc, "Cómo se lee tu rutina")
    _caja(doc, [
        ("Series", "«4×8-10» son cuatro series de entre ocho y diez repeticiones."),
        ("RIR", "Las repeticiones que te dejas sin hacer. RIR 2 = paras cuando "
                "podrías haber hecho dos más. No es llegar al fallo."),
        ("Descanso", "El tiempo entre serie y serie. Cronométralo: acortarlo "
                     "cambia el entrenamiento."),
        ("Cuándo subir peso", "Lo dice cada ejercicio en su casilla. Si no llegas "
                              "al rango de repeticiones, no subas."),
    ])

    prog = training.get("weekly_progression") or []
    if prog:
        _barra(doc, "Semana a semana")
        _nota(doc, "Las cuatro semanas no se entrenan igual. Esta tabla manda sobre "
                   "cómo te encuentres ese día.")
        filas = [[f"Sem {w.get('week')}", w.get("intent", ""), f"{w.get('load_pct', '')}%",
                  f"RIR {w.get('rir_target', '')}", w.get("volume_note", "")] for w in prog]
        _tabla(doc, ["Semana", "Enfoque", "Carga", "RIR", "Notas"], filas, brand,
               anchos=[1100, 1800, 1100, 1100, 4566], keep_together=False)

    for sess in training.get("sessions") or []:
        _barra(doc, f"{sess.get('day', '')} · {sess.get('name', '')}")
        if sess.get("warmup"):
            _caja(doc, [("Antes de empezar", sess["warmup"])])
        filas = []
        for ex in sess.get("exercises") or []:
            nombre = exercise_names.get(ex.get("exercise_id")) or (
                (ex.get("name") or "").strip() or f"Ejercicio #{ex.get('exercise_id', '')}")
            # MISMAS etiquetas que re-lee `word_import._parse_cue_cell`: la
            # celda concentra todo lo que el cliente necesita del ejercicio.
            partes = []
            if (ex.get("technique_cue") or "").strip():
                partes.append(ex["technique_cue"].strip())
            if (ex.get("biomech_cue") or "").strip():
                partes.append(f"Clave biomecánica: {ex['biomech_cue'].strip()}")
            if str(ex.get("tempo") or "").strip():
                partes.append(f"Tempo: {str(ex['tempo']).strip()}")
            if (ex.get("coach_notes") or "").strip():
                partes.append(f"Indicación para ti: {ex['coach_notes'].strip()}")
            if (ex.get("progression_rule") or "").strip():
                partes.append(f"Cómo progresar: {ex['progression_rule'].strip()}")
            filas.append([nombre, f"{ex.get('sets', '')}×{ex.get('rep_range', '')}",
                          f"RIR {ex.get('rir', '')}", _dur(ex), "\n".join(partes)])
        if filas:
            _tabla(doc, ["Ejercicio", "Series", "RIR", "Descanso", "Clave técnica"],
                   filas, brand, anchos=[2600, 1300, 1100, 1100, 3566],
                   keep_together=False)
        if sess.get("cooldown"):
            _caja(doc, [("Al terminar", sess["cooldown"])])

    cardio = training.get("cardio") or {}
    if cardio.get("daily_steps") or cardio.get("sessions"):
        # ⚠️ alias de `word_import`: «cardio y pasos» → cardio y NEAT.
        _barra(doc, "Cardio y pasos")
        _nota(doc, "Lo que andas a lo largo del día pesa más que el cardio que hagas "
                   "aquí. Los pasos son la parte grande.")
        items = [("Pasos al día",
                  f"{_n(cardio['daily_steps'])} pasos" if cardio.get("daily_steps") else "—")]
        for cs in cardio.get("sessions") or []:
            items.append((str(cs.get("type", "")).upper(),
                          f"{cs.get('minutes', '')} min × {cs.get('times_per_week', '')}/semana"
                          + (f" — {cs['notes']}" if cs.get("notes") else "")))
        _caja(doc, items)

    if (training.get("deload_instructions") or "").strip():
        # ⚠️ alias de `word_import`: «semana suave» → semana de descarga.
        _barra(doc, "Semana suave")
        _nota(doc, "No es perder una semana: es lo que hace que a la siguiente "
                   "vuelvas más fuerte.")
        _caja(doc, [training["deload_instructions"]])


def _cierre(doc: Document, brand: DocBrand) -> None:
    """Dónde estamos y cómo se sigue. En un centro, esto no es un pie de página
    de cortesía: es la dirección a la que el cliente viene."""
    _barra(doc, "Dónde estamos y qué toca ahora")
    items: list = [
        ("Lo siguiente", "Apunta cada día en tu portal. A los quince días te "
                         "escribimos para la revisión."),
    ]
    if brand.contact_address:
        items.append(("El centro", brand.contact_address))
    if brand.contact_phone:
        items.append(("Teléfono", brand.contact_phone))
    if brand.contact_email:
        items.append(("Correo", brand.contact_email))
    items.append(("Dudas", "Pregúntanos en la sala o escríbenos desde tu portal. "
                           "Para eso estamos."))
    _caja(doc, items)
