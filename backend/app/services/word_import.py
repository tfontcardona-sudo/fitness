"""Ida y VUELTA del Word editable del plan.

El coach descarga el "Word editable", lo retoca en Word y lo SUBE de nuevo:
este módulo lee el .docx, detecta qué cambió respecto al plan vigente y
construye los `nutrition_json`/`training_json` candidatos. La APLICACIÓN
real la hace el MISMO `PATCH /api/plans/{id}` de siempre (sanitizado,
reconcile, historial, rev, diff, aprendizaje §13) — aquí solo se lee.

Cómo funciona (100% determinista, 0 créditos de IA):
- El documento lo generamos NOSOTROS (plan_doc.py), así que su estructura es
  conocida: las tablas de datos se reconocen por su fila de cabecera y las
  cajas por el título de sección (barra) que las precede.
- Se re-parsean las partes ESTRUCTURADAS: resumen energético (kcal/macros),
  horas y nombres de las tomas, progresión semanal, tablas de ejercicios de
  cada sesión (series, reps, RIR, descanso, clave técnica, indicaciones y
  regla de progresión), suplementación, deload y pasos diarios.
- Los textos LIBRES (recetas del banco de comidas, tarjetas de plantilla,
  educativo) NO se importan: se editan en el editor web. Si algo no se puede
  aplicar, se devuelve como aviso — nunca se pierde en silencio.
- Los nombres de ejercicio se resuelven contra la biblioteca (canonical_name
  + aliases, normalizados): cambiar el nombre de una fila cambia el ejercicio
  si existe en la biblioteca; si no existe, aviso.
"""
from __future__ import annotations

import copy
import io
import re
import unicodedata

from docx.oxml.ns import qn
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Exercise, Plan

MAX_DOCX_BYTES = 15 * 1024 * 1024


class WordImportError(ValueError):
    """El .docx no se pudo leer o no parece un plan nuestro."""


# ------------------------------------------------------------- utilidades ----

def _norm(s: str | None) -> str:
    s = (s or "").strip().lower()
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def _num(s: str | None) -> float | None:
    """Primer número del texto (acepta coma decimal y separador de miles)."""
    if not s:
        return None
    limpio = s.replace(" ", " ")
    # "1.234,5" → "1234.5"; "2200" → "2200"; "65%" → "65"
    m = re.search(r"-?\d[\d.,]*", limpio)
    if not m:
        return None
    t = m.group(0)
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif t.count(".") > 1:
        t = t.replace(".", "")
    elif "." in t and len(t.split(".")[-1]) == 3:
        t = t.replace(".", "")  # separador de miles ("1.234")
    try:
        return float(t)
    except ValueError:
        return None


def _iter_blocks(doc):
    """Recorre el CUERPO del documento en orden, mezclando párrafos y tablas
    (las cajas del diseño son tablas 1×1, así que el orden real importa)."""
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    body = doc.element.body
    for child in body.iterchildren():
        tag = child.tag.split("}")[-1]
        if tag == "p":
            yield "p", Paragraph(child, doc)
        elif tag == "tbl":
            yield "t", Table(child, doc)


def _cell_text(cell) -> str:
    return "\n".join(p.text for p in cell.paragraphs).strip()


def _header_sig(table) -> tuple[str, ...]:
    try:
        return tuple(_norm(_cell_text(c)) for c in table.rows[0].cells)
    except Exception:  # noqa: BLE001
        return ()


# Firmas de cabecera de las tablas de datos del documento (plan_doc.py).
SIG_ENERGIA = ("calorias", "reparto de macros", "ajuste aplicado")
SIG_TOMAS = ("hora", "toma", "estrategia")
SIG_PROGRESION = ("semana", "enfoque", "carga", "rir", "notas")
SIG_SESION = ("ejercicio", "series", "rir", "descanso", "clave tecnica")


def _es_barra(par) -> bool:
    """¿Este párrafo es una BARRA DE SECCIÓN del documento?

    Se reconoce por el sombreado de párrafo, que es justo lo que la dibuja
    (`word_base.section_bar`). Reconocerla por "tiene texto" hacía que
    cualquier frase suelta bajo la barra la suplantara.
    """
    try:
        if not par.text.strip():
            return False
        pPr = par._p.find(qn("w:pPr"))
        if pPr is None:
            return False
        shd = pPr.find(qn("w:shd"))
        if shd is None:
            return False
        fill = (shd.get(qn("w:fill")) or "").lower()
        return bool(fill) and fill not in ("auto", "ffffff", "none")
    except Exception:  # noqa: BLE001 — un docx raro nunca tumba la importación
        return False


def _exercise_maps(db: Session, training: dict | None):
    """(id→nombre de los ejercicios del plan, nombre normalizado→id de TODA la
    biblioteca, incluidos alias)."""
    ids = set()
    for sess in (training or {}).get("sessions", []):
        for ex in sess.get("exercises", []):
            if ex.get("exercise_id"):
                ids.add(int(ex["exercise_id"]))
    id_a_nombre: dict[int, str] = {}
    nombre_a_id: dict[str, int] = {}
    for e in db.execute(select(Exercise)).scalars():
        if e.id in ids:
            id_a_nombre[e.id] = e.canonical_name
        clave = _norm(e.canonical_name)
        if clave and clave not in nombre_a_id:
            nombre_a_id[clave] = e.id
        for alias in (e.aliases or []):
            ak = _norm(alias)
            if ak and ak not in nombre_a_id:
                nombre_a_id[ak] = e.id
    return id_a_nombre, nombre_a_id


def _parse_cue_cell(text: str) -> dict:
    """Invierte la celda "Clave técnica": técnica + "Indicación para ti:" +
    "Cómo progresar:" (plan_doc concatena las tres en líneas)."""
    tecnica: list[str] = []
    notas = None
    progresion = None
    for ln in (text or "").splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.lower().startswith("indicación para ti:") or s.lower().startswith("indicacion para ti:"):
            notas = s.split(":", 1)[1].strip()
        elif s.lower().startswith("cómo progresar:") or s.lower().startswith("como progresar:"):
            progresion = s.split(":", 1)[1].strip()
        else:
            tecnica.append(s)
    return {"technique_cue": " ".join(tecnica).strip(),
            "coach_notes": notas, "progression_rule": progresion}


# ---------------------------------------------------------------- parseo ----

def parse_word_edits(db: Session, plan: Plan, docx_bytes: bytes) -> dict:
    """Lee el .docx editado y devuelve los JSON candidatos + el resumen de
    cambios detectados + avisos. NO persiste nada."""
    try:
        from docx import Document

        doc = Document(io.BytesIO(docx_bytes))
    except Exception as exc:  # noqa: BLE001
        raise WordImportError(
            "El archivo no se pudo leer como Word (.docx). Sube el documento "
            "descargado con el botón «Word editable» (no un PDF ni un .doc antiguo)."
        ) from exc

    nutrition = copy.deepcopy(plan.nutrition_json) if plan.nutrition_json else None
    training = copy.deepcopy(plan.training_json) if plan.training_json else None
    base_nutrition = copy.deepcopy(plan.nutrition_json) if plan.nutrition_json else None

    avisos: list[str] = []
    frases: list[str] = []      # cambios que plan_diff no sabe describir
    id_a_nombre, nombre_a_id = _exercise_maps(db, training)

    def _nombre_de(ex: dict) -> str:
        eid = ex.get("exercise_id")
        return id_a_nombre.get(eid, f"Ejercicio #{eid}")

    ultima_barra = ""
    energia: dict | None = None
    tomas_rows: list[tuple[str, str]] = []
    vio_algo = False

    for kind, block in _iter_blocks(doc):
        if kind == "p":
            # SOLO las barras de sección cuentan. Antes valía cualquier párrafo
            # con texto, así que la línea guía que se imprime bajo la barra
            # ("Los pasos diarios pesan más que el cardio…") pasaba a ser la
            # referencia y las cajas de Cardio y de la semana de descarga
            # dejaban de importarse EN SILENCIO.
            if _es_barra(block):
                ultima_barra = block.text.strip()
            continue

        sig = _header_sig(block)
        # ---- tabla de RESUMEN ENERGÉTICO -------------------------------
        if sig == SIG_ENERGIA and len(block.rows) >= 2 and nutrition is not None:
            vio_algo = True
            celdas = block.rows[1].cells
            kcal = _num(_cell_text(celdas[0]))
            reparto = _cell_text(celdas[1])
            m = re.search(r"CH\s*([\d.,]+)\s*g.*?P\s*([\d.,]+)\s*g.*?G\s*([\d.,]+)\s*g",
                          reparto, re.IGNORECASE | re.DOTALL)
            if kcal and m:
                energia = {"kcal": kcal, "carbs_g": _num(m.group(1)),
                           "protein_g": _num(m.group(2)), "fat_g": _num(m.group(3))}
            elif kcal:
                energia = {"kcal": kcal}
                if reparto.strip():
                    avisos.append(
                        "No he podido leer el reparto de macros del resumen "
                        "energético: aplico solo las calorías. Escríbelo como "
                        "«CH 000 g · P 000 g · G 000 g», en ese orden."
                    )
            continue

        # ---- tabla de ESTRUCTURA DIARIA (tomas) ------------------------
        if sig == SIG_TOMAS and nutrition is not None:
            vio_algo = True
            for row in block.rows[1:]:
                c = row.cells
                tomas_rows.append((_cell_text(c[0]), _cell_text(c[1])))
            continue

        # ---- tabla de PROGRESIÓN SEMANAL -------------------------------
        if sig == SIG_PROGRESION and training is not None:
            vio_algo = True
            semanas = {int(w.get("week")): w
                       for w in training.get("weekly_progression", []) if w.get("week")}
            for row in block.rows[1:]:
                c = row.cells
                n = _num(_cell_text(c[0]))
                if n is None or int(n) not in semanas:
                    continue
                w = semanas[int(n)]
                intent = _cell_text(c[1]).strip()
                if intent and intent in ("Base", "Progresión", "Pico", "Deload") \
                        and intent != w.get("intent"):
                    frases.append(f"Semana {int(n)}: enfoque {w.get('intent')} → {intent}")
                    w["intent"] = intent
                carga = _num(_cell_text(c[2]))
                if carga and abs(carga - float(w.get("load_pct") or 0)) > 0.01:
                    frases.append(f"Semana {int(n)}: carga {w.get('load_pct')}% → {carga:g}%")
                    w["load_pct"] = carga
                rirt = re.sub(r"(?i)^rir\s*", "", _cell_text(c[3])).strip()
                if rirt and rirt != str(w.get("rir_target") or ""):
                    frases.append(f"Semana {int(n)}: RIR {w.get('rir_target')} → {rirt}")
                    w["rir_target"] = rirt
                nota = _cell_text(c[4]).strip()
                if nota and nota != (w.get("volume_note") or "").strip():
                    frases.append(f"Semana {int(n)}: notas de volumen actualizadas")
                    w["volume_note"] = nota
            continue

        # ---- tabla de SESIÓN de entrenamiento --------------------------
        if sig == SIG_SESION and training is not None:
            vio_algo = True
            _aplicar_sesion(block, ultima_barra, training, id_a_nombre,
                            nombre_a_id, frases, avisos, _nombre_de)
            continue

        # ---- cajas 1×1 (por el título de sección que las precede) ------
        if len(block.rows) == 1 and len(block.rows[0].cells) == 1:
            texto = _cell_text(block.rows[0].cells[0])
            barra = _norm(ultima_barra)
            if barra.startswith("suplementacion recomendada") and nutrition is not None:
                _aplicar_suplementos(texto, nutrition, frases, avisos)
            elif barra.startswith("semana de descarga") and training is not None:
                nuevo = texto.strip()
                if nuevo and nuevo != (training.get("deload_instructions") or "").strip():
                    training["deload_instructions"] = nuevo
                    frases.append("Instrucciones de la semana de descarga actualizadas")
            elif barra.startswith("cardio y neat") and training is not None:
                m = re.search(r"pasos diarios objetivo:\s*([\d.,]+)", texto, re.IGNORECASE)
                pasos = _num(m.group(1)) if m else None
                cardio = training.get("cardio") or {}
                if pasos is not None and int(pasos) != int(cardio.get("daily_steps") or 0):
                    frases.append(f"Pasos diarios: {cardio.get('daily_steps')} → {int(pasos)}")
                    cardio["daily_steps"] = int(pasos)
                    training["cardio"] = cardio
            continue

    if not vio_algo:
        raise WordImportError(
            "No reconozco este documento como el Word del plan: no contiene "
            "ninguna de sus tablas. Descárgalo con «Word editable», edítalo y "
            "vuelve a subir ese mismo archivo."
        )

    # ---- aplicar energía (misma verdad que el editor: rescale) ---------
    # ANTES que las tomas: rescale_nutrition reconstruye los objetivos por
    # comida desde la BASE y pisaría las horas/nombres recién importados.
    _aplicar_energia(energia, nutrition, base_nutrition)

    # ---- aplicar tomas (hora/nombre por posición) ----------------------
    if tomas_rows and nutrition is not None:
        meals = nutrition.get("meals") or []
        if len(tomas_rows) != len(meals):
            avisos.append(
                "El número de tomas del Word no coincide con el del plan: "
                "para añadir o quitar comidas usa el editor web."
            )
        else:
            for (hora, nombre), meal in zip(tomas_rows, meals):
                hora = hora.strip()
                nombre = nombre.strip()
                if hora and hora != (meal.get("time") or "").strip():
                    frases.append(f"{meal.get('name') or 'Comida'}: hora "
                                  f"{meal.get('time')} → {hora}")
                    meal["time"] = hora
                if nombre and nombre != (meal.get("name") or "").strip():
                    frases.append(f"Toma {meal.get('slot')}: renombrada a «{nombre}»")
                    meal["name"] = nombre

    resultado = {
        "nutrition_json": nutrition,
        "training_json": training,
        "warnings": avisos,
        "extra_changes": frases,
    }
    return resultado


def _aplicar_energia(energia: dict | None, nutrition: dict | None,
                     base_nutrition: dict | None) -> None:
    """Aplica kcal/macros del Word con la MISMA verdad que el editor
    (rescale_nutrition desde la base: totales + comidas + banco). El PATCH
    después reconcilia y aplica los topes de seguridad."""
    if not energia or nutrition is None or base_nutrition is None:
        return
    from app.services.nutrition_scale import rescale_nutrition

    macros_actuales = nutrition.get("macros") or {}

    def _valor(clave: str, respaldo) -> float:
        """El 0 del Word MANDA. Con `or` se trataba como ausente y se reponía
        el valor anterior: el coach ponía las grasas a 0 y el plan seguía con
        las de antes, sin un solo aviso."""
        leido = energia.get(clave)
        if leido is None:
            leido = respaldo
        try:
            return float(leido or 0)
        except (TypeError, ValueError):
            return 0.0

    kcal = _valor("kcal", nutrition.get("target_kcal"))
    p = _valor("protein_g", macros_actuales.get("protein_g"))
    c = _valor("carbs_g", macros_actuales.get("carbs_g"))
    g = _valor("fat_g", macros_actuales.get("fat_g"))
    m0 = base_nutrition.get("macros") or {}
    cambia = (abs(kcal - float(base_nutrition.get("target_kcal") or 0)) > 0.5
              or abs(p - float(m0.get("protein_g") or 0)) > 0.5
              or abs(c - float(m0.get("carbs_g") or 0)) > 0.5
              or abs(g - float(m0.get("fat_g") or 0)) > 0.5)
    if cambia:
        rescale_nutrition(nutrition, base_nutrition, kcal, p, c, g)


def _aplicar_sesion(table, barra: str, training: dict, id_a_nombre: dict,
                    nombre_a_id: dict, frases: list, avisos: list, _nombre_de) -> None:
    """Aplica la tabla de UNA sesión: cambios de series/reps/RIR/descanso/
    textos, cambio de ejercicio por nombre, altas y bajas de filas."""
    partes = [x.strip() for x in barra.split("·")]
    dia = partes[0] if partes else ""
    nombre_ses = partes[1] if len(partes) > 1 else ""
    sesion = None
    for s in training.get("sessions", []):
        if _norm(s.get("day")) == _norm(dia) and _norm(s.get("name")) == _norm(nombre_ses):
            sesion = s
            break
    if sesion is None:
        for s in training.get("sessions", []):
            if _norm(s.get("day")) == _norm(dia):
                sesion = s
                break
    if sesion is None:
        avisos.append(f"No encuentro en el plan la sesión «{barra}»: esa tabla no se importó.")
        return

    actuales = sesion.get("exercises") or []
    por_nombre = {}
    for ex in actuales:
        por_nombre.setdefault(_norm(_nombre_de(ex)), []).append(ex)

    etiqueta = sesion.get("name") or sesion.get("day") or "Sesión"
    reclamados: set[int] = set()
    resultado: list[dict] = []

    filas = table.rows[1:]
    for idx, row in enumerate(filas):
        c = row.cells
        nombre = _cell_text(c[0]).strip()
        clave = _norm(nombre)
        objetivo = None
        # 1) "Ejercicio #123" → id directo
        m_id = re.match(r"ejercicio #(\d+)", clave)
        if m_id:
            eid = int(m_id.group(1))
            objetivo = next((ex for ex in actuales
                             if int(ex.get("exercise_id") or 0) == eid
                             and id(ex) not in reclamados), None)
        # 2) nombre igual a un ejercicio de la sesión
        if objetivo is None:
            for ex in por_nombre.get(clave, []):
                if id(ex) not in reclamados:
                    objetivo = ex
                    break
        # 3) nombre nuevo → biblioteca; sustituye al de su posición o se añade
        if objetivo is None:
            eid = nombre_a_id.get(clave)
            if eid is None:
                avisos.append(
                    f"{etiqueta}: el ejercicio «{nombre}» no está en la biblioteca — "
                    "esa fila no se importó (cámbialo desde la web o crea el ejercicio)."
                )
                # conserva el de su posición para no perderlo
                if idx < len(actuales) and id(actuales[idx]) not in reclamados:
                    reclamados.add(id(actuales[idx]))
                    resultado.append(actuales[idx])
                continue
            if idx < len(actuales) and id(actuales[idx]) not in reclamados:
                objetivo = actuales[idx]
                frases.append(f"{etiqueta}: cambiado {_nombre_de(objetivo)} por {nombre}")
                objetivo["exercise_id"] = eid
            else:
                objetivo = {
                    "exercise_id": eid, "sets": 3, "rep_range": "8-10",
                    "rir": "2", "tempo": None, "rest_sec": 90,
                    "start_weight_hint_kg": None, "progression_rule": "",
                    "technique_cue": "", "biomech_cue": "", "coach_notes": None,
                }
                frases.append(f"{etiqueta}: añadido {nombre}")

        reclamados.add(id(objetivo))
        resultado.append(objetivo)

        # ---- campos de la fila ----
        sxr = _cell_text(c[1])
        m = re.search(r"(\d+)\s*[×x]\s*(.+)", sxr)
        if m:
            sets = max(1, min(10, int(m.group(1))))
            rep = m.group(2).strip()[:20]
            if sets != int(objetivo.get("sets") or 0):
                objetivo["sets"] = sets
            if rep and rep != (objetivo.get("rep_range") or ""):
                objetivo["rep_range"] = rep
        rir = re.sub(r"(?i)^rir\s*", "", _cell_text(c[2])).strip()[:10]
        if rir and rir != str(objetivo.get("rir") or ""):
            objetivo["rir"] = rir
        descanso = _num(_cell_text(c[3]))
        if descanso and 15 <= int(descanso) <= 600 \
                and int(descanso) != int(objetivo.get("rest_sec") or 0):
            objetivo["rest_sec"] = int(descanso)
        cue = _parse_cue_cell(_cell_text(c[4]))
        if cue["technique_cue"] and cue["technique_cue"] != (objetivo.get("technique_cue") or "").strip():
            objetivo["technique_cue"] = cue["technique_cue"]
            frases.append(f"{_nombre_de(objetivo)}: clave técnica actualizada")
        if cue["coach_notes"] is not None and cue["coach_notes"] != (objetivo.get("coach_notes") or "").strip():
            objetivo["coach_notes"] = cue["coach_notes"] or None
            frases.append(f"{_nombre_de(objetivo)}: indicación personal actualizada")
        if cue["progression_rule"] is not None and cue["progression_rule"] != (objetivo.get("progression_rule") or "").strip():
            objetivo["progression_rule"] = cue["progression_rule"]
            frases.append(f"{_nombre_de(objetivo)}: regla de progresión actualizada")

    # bajas: ejercicios del plan que ya no aparecen en la tabla
    for ex in actuales:
        if id(ex) not in reclamados:
            frases.append(f"{etiqueta}: quitado {_nombre_de(ex)}")
    if resultado:
        sesion["exercises"] = resultado
    else:
        avisos.append(f"{etiqueta}: la tabla quedó sin ejercicios válidos — no se tocó.")


def _aplicar_suplementos(texto: str, nutrition: dict, frases: list, avisos: list) -> None:
    """Caja "Suplementación recomendada": líneas "Nombre — dosis (momento)"."""
    lineas = [ln.strip() for ln in (texto or "").splitlines() if ln.strip()]
    parseadas = []
    for ln in lineas:
        m = re.match(r"^(.*?)\s+—\s+(.*?)\s*\((.*)\)\s*$", ln)
        if not m:
            avisos.append(
                f"Suplementación: no pude leer la línea «{ln[:60]}» — usa el "
                "formato «Nombre — dosis (momento)». No se cambió nada ahí."
            )
            return
        parseadas.append({"name": m.group(1).strip(), "dose": m.group(2).strip(),
                          "timing": m.group(3).strip()})
    actuales = nutrition.get("supplements") or []
    por_nombre = {_norm(s.get("name")): s for s in actuales}
    nuevos = []
    for p in parseadas:
        previo = por_nombre.get(_norm(p["name"]))
        nuevos.append({**p, "evidence_note": (previo or {}).get("evidence_note", "")})
    viejos_txt = [(s.get("name"), s.get("dose"), s.get("timing")) for s in actuales]
    nuevos_txt = [(s.get("name"), s.get("dose"), s.get("timing")) for s in nuevos]
    if viejos_txt != nuevos_txt:
        nutrition["supplements"] = nuevos
        # plan_diff ya narra añadidos/quitados; esto cubre cambios de dosis.
        frases.append("Suplementación actualizada desde el Word")
