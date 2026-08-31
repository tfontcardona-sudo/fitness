"""Ida y VUELTA del Word editable del plan.

El coach descarga el "Word editable", lo retoca en Word y lo SUBE de nuevo:
este módulo lee el .docx, detecta qué cambió respecto al plan vigente y
construye los `nutrition_json`/`training_json`/`education_json` candidatos.
La APLICACIÓN real la hace el MISMO `PATCH /api/plans/{id}` de siempre
(sanitizado, reconcile, historial, rev, diff, aprendizaje §13) — aquí solo
se lee.

Cómo funciona (100% determinista, 0 créditos de IA):
- El documento lo generamos NOSOTROS (plan_doc.py), así que su estructura es
  conocida: las tablas de datos se reconocen por su fila de cabecera y las
  cajas por el título de sección (barra) que las precede.
- Se re-parsean las partes ESTRUCTURADAS: resumen energético (kcal/macros en
  cualquier orden y con etiquetas naturales), horas/nombres/ESTRATEGIA de
  las tomas, progresión semanal, tablas de ejercicios de cada sesión
  (series, reps, RIR, descanso — también «2 min» —, clave técnica,
  indicaciones y regla de progresión), suplementación, deload, cardio
  (pasos Y sesiones), calentamiento/vuelta a la calma, estructura del split,
  «Por qué este enfoque», «Tu margen de maniobra», la tabla «Cambios de tu
  plan», el educativo (píldoras/técnica/FAQ) y la rejilla semanal flexible.
- Las RECETAS también van y vuelven: las cajas «Opción N. Título — Alimento
  000 g (medida casera), …» del banco flexible y el MENÚ CERRADO por días
  del modo strict se aplican al plan; los macros de cada plato se RECALCULAN
  en el backend desde la base de alimentos (Atwater 4/4/9, half-up) — la IA
  (y el Word) siguen sin calcular nada. Si algún alimento no se reconoce, el
  contenido se aplica igual y se AVISA para revisar macros en el editor.
- Solo quedan fuera las EQUIVALENCIAS de comida/cena (formato libre, se
  editan regenerando o con el swap) y las tarjetas informativas fijas. Si
  algo no se puede aplicar, se devuelve como aviso — nunca en silencio: una
  tabla con la cabecera retocada o una caja ilegible generan aviso.
- Los nombres de ejercicio se resuelven contra la biblioteca (canonical_name
  + aliases, normalizados) y, si no hay coincidencia exacta, por palabras
  clave: un único candidato se acepta (y se dice), varios → aviso con la
  lista; ninguno → aviso.
"""
from __future__ import annotations

import copy
import io
import re
import unicodedata

from docx.oxml.ns import qn
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, Exercise, Food, Plan

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
    limpio = s.replace(" ", " ")
    # "1.234,5" → "1234.5"; "2200" → "2200"; "65%" → "65"
    m = re.search(r"-?\d[\d.,]*", limpio)
    if not m:
        return None
    t = m.group(0)
    if "," in t:
        # "2,150" (millar anglosajón pegado de otra fuente) NO son 2,15 kcal:
        # coma seguida de EXACTAMENTE 3 dígitos por grupo = separador de miles.
        # "120,50" (dos decimales) sigue siendo coma decimal española.
        if re.fullmatch(r"-?\d{1,3}(,\d{3})+", t):
            t = t.replace(",", "")
        else:
            t = t.replace(".", "").replace(",", ".")
    elif t.count(".") > 1:
        t = t.replace(".", "")
    elif "." in t and len(t.split(".")[-1]) == 3:
        t = t.replace(".", "")  # separador de miles ("1.234")
    try:
        return float(t)
    except ValueError:
        return None


def _ws(s) -> str:
    return " ".join(str(s or "").split())


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
SIG_SEMANAL = ("toma", "lun", "mar", "mie", "jue", "vie", "sab", "dom")
SIG_CAMBIOS = ("area", "que cambia", "por que")

_SIGS_CONOCIDAS = (
    ("resumen energético", SIG_ENERGIA), ("estructura diaria", SIG_TOMAS),
    ("progresión semanal", SIG_PROGRESION), ("sesión de entrenamiento", SIG_SESION),
    ("dieta semanal", SIG_SEMANAL), ("cambios de tu plan", SIG_CAMBIOS),
)


def _sig_parecida(sig: tuple[str, ...]) -> str | None:
    """¿Esta cabecera SE PARECE a una tabla nuestra sin serlo? (el coach
    renombró una columna o añadió una). Antes la tabla ENTERA — con todos sus
    cambios de filas — se saltaba sin una palabra."""
    conj = set(sig)
    for nombre, firma in _SIGS_CONOCIDAS:
        if sig == firma:
            continue
        if len(conj & set(firma)) >= max(2, len(firma) - 1):
            return nombre
    return None


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
    """(id→nombre de TODA la biblioteca, nombre normalizado→id de TODA la
    biblioteca, incluidos alias). id→nombre cubría solo los ejercicios del
    plan: al cambiar un ejercicio por otro de la biblioteca, las frases de
    resumen decían «Ejercicio #123» en vez de su nombre."""
    del training  # ya no hace falta acotar: la biblioteca entera es pequeña
    id_a_nombre: dict[int, str] = {}
    nombre_a_id: dict[str, int] = {}
    for e in db.execute(select(Exercise)).scalars():
        id_a_nombre[e.id] = e.canonical_name
        clave = _norm(e.canonical_name)
        if clave and clave not in nombre_a_id:
            nombre_a_id[clave] = e.id
        for alias in (e.aliases or []):
            ak = _norm(alias)
            if ak and ak not in nombre_a_id:
                nombre_a_id[ak] = e.id
    return id_a_nombre, nombre_a_id


_STOPWORDS = {"de", "del", "la", "el", "las", "los", "en", "con", "a", "al",
              "y", "o", "u", "un", "una", "por", "para", "sobre"}


def _fuzzy_exercise(clave: str, nombre_a_id: dict[str, int]) -> dict[int, str]:
    """Candidatos de biblioteca para un nombre SIN coincidencia exacta: mismas
    palabras clave (ignorando artículos) en un sentido u otro, o contención
    directa. Devuelve {id: nombre_normalizado_que_casó} — un único candidato
    se acepta; varios es ambiguo y se avisa."""
    toks = {t for t in clave.split() if t not in _STOPWORDS}
    hits: dict[int, str] = {}
    if not toks:
        return hits
    for k, eid in nombre_a_id.items():
        if eid in hits:
            continue
        kt = {t for t in k.split() if t not in _STOPWORDS}
        if not kt:
            continue
        if toks <= kt or kt <= toks or clave in k or k in clave:
            hits[eid] = k
    return hits


def _parse_rest(text: str | None) -> int | None:
    """Descanso de la fila de sesión → SEGUNDOS. El coach escribe «2 min»,
    «1,5 min» o «1 min 30» con toda naturalidad y antes se descartaba EN
    SILENCIO (solo se aceptaba el número pelado en segundos)."""
    t = _norm(text)
    if not t:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:min\w*|m\b|')", t)
    if m:
        minutos = float(m.group(1).replace(",", "."))
        extra = re.search(r"min\w*\s*(?:y\s*)?(\d+)", t)
        seg = float(extra.group(1)) if extra else 0.0
        return int(round(minutos * 60 + seg))
    n = _num(text)
    return int(n) if n is not None else None


# Etiquetas admitidas en el reparto de macros del resumen energético.
_LABEL_MACRO = {"ch": "carbs_g", "hc": "carbs_g", "c": "carbs_g",
                "p": "protein_g", "g": "fat_g", "gr": "fat_g"}


def _parse_reparto(texto: str) -> dict:
    """Línea de macros del resumen energético, en CUALQUIER orden y con
    etiquetas naturales: «CH/HC/C/carbohidratos/hidratos», «P/prot/proteína»,
    «G/gr/grasa/lípidos». Antes solo se aceptaba «CH … P … G …» exacto y en
    ese orden: reordenar o escribir «Prot» tiraba TODO el reparto a un aviso.
    La 2ª línea de la celda («55% · 25% · 20% de tus calorías») no casa con
    el patrón (no lleva gramos), así que no interfiere."""
    out: dict = {}
    for m in re.finditer(r"([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)\.?\s*:?\s*(\d[\d.,]*)\s*g\b",
                         texto or ""):
        lbl = _norm(m.group(1))
        clave = _LABEL_MACRO.get(lbl)
        if clave is None:
            if lbl.startswith(("carb", "hidrat")):
                clave = "carbs_g"
            elif lbl.startswith("prot"):
                clave = "protein_g"
            elif lbl.startswith(("gras", "lip")):
                clave = "fat_g"
        if clave and clave not in out:
            out[clave] = _num(m.group(2))
    return out


def _food_map(db: Session) -> dict[str, Food]:
    """Nombre normalizado (canónico y alias) → fila de `foods`. Es la base
    para RECALCULAR los macros de un plato editado en el Word: los números
    los pone el backend, nunca el documento."""
    out: dict[str, Food] = {}
    for f in db.execute(select(Food)).scalars():
        k = _norm(f.canonical_name)
        if k and k not in out:
            out[k] = f
        for a in (f.aliases or []):
            ak = _norm(a)
            if ak and ak not in out:
                out[ak] = f
    return out


def _parse_cue_cell(text: str) -> dict:
    """Invierte la celda "Clave técnica": técnica + "Clave biomecánica:" +
    "Tempo:" + "Indicación para ti:" + "Cómo progresar:" (plan_doc concatena
    las líneas etiquetadas bajo la técnica)."""
    tecnica: list[str] = []
    out: dict = {"technique_cue": "", "biomech_cue": None, "tempo": None,
                 "coach_notes": None, "progression_rule": None}
    for ln in (text or "").splitlines():
        s = ln.strip()
        if not s:
            continue
        low = _norm(s)
        if low.startswith("indicacion para ti:"):
            out["coach_notes"] = s.split(":", 1)[1].strip()
        elif low.startswith("como progresar:"):
            out["progression_rule"] = s.split(":", 1)[1].strip()
        elif low.startswith("clave biomecanica:"):
            out["biomech_cue"] = s.split(":", 1)[1].strip()
        elif low.startswith("tempo:"):
            out["tempo"] = s.split(":", 1)[1].strip()
        else:
            tecnica.append(s)
    out["technique_cue"] = " ".join(tecnica).strip()
    return out


def _pares_de_caja(texto: str) -> list[list[str]] | None:
    """Líneas «Etiqueta: valor» de una info_box de pares (educativo). Una
    línea sin «: » continúa el valor anterior. None si el texto no empieza
    con una línea etiquetada (formato irreconocible)."""
    pares: list[list[str]] = []
    for ln in (texto or "").splitlines():
        s = ln.strip()
        if not s:
            continue
        if ": " in s:
            lbl, _, val = s.partition(": ")
            pares.append([lbl.strip(), val.strip()])
        elif s.endswith(":"):
            pares.append([s[:-1].strip(), ""])
        elif pares:
            pares[-1][1] = (pares[-1][1] + "\n" + s).strip()
        else:
            return None
    return pares


# --------------------------------------- recetas (banco flexible y strict) ----

_RE_OPCION = re.compile(r"(?i)^opci\w*\s+(\d+)\s*$")
_RE_INGREDIENTE = re.compile(
    r"^(?P<food>.+?)\s+(?P<g>\d+(?:[.,]\d+)?)\s*g\b\s*(?:\((?P<hh>[^)]*)\))?\s*$",
    re.IGNORECASE)


def _split_ingredientes(s: str) -> list[str]:
    """Separa por comas de PRIMER NIVEL: la medida casera va entre paréntesis
    y puede llevar comas dentro («1 taza, colmada»)."""
    out: list[str] = []
    cur: list[str] = []
    depth = 0
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if cur:
        out.append("".join(cur).strip())
    return [x for x in out if x]


def _parse_ingrediente(txt: str) -> dict:
    """«Avena 60 g (6 cucharadas)» → alimento + gramos + medida casera. Sin
    gramos reconocibles queda solo el alimento (y sus macros no se podrán
    recalcular → aviso aguas arriba)."""
    m = _RE_INGREDIENTE.match(txt.strip())
    if not m:
        return {"food": txt.strip(), "grams": None, "household": ""}
    return {"food": m.group("food").strip(),
            "grams": float(m.group("g").replace(",", ".")),
            "household": (m.group("hh") or "").strip()}


def _parse_lineas_platos(texto: str, acepta_label) -> tuple[list[dict], list[str]]:
    """Invierte una caja de recetas: líneas «Etiqueta. Título — ingredientes.»
    y, debajo de cada una, su párrafo de preparación «texto (X min)».
    `acepta_label` decide si una etiqueta es de plato («Opción N» en flexible,
    la toma del día en strict): una frase de preparación con «. » y «—» dentro
    no debe confundirse con un plato. Devuelve (platos, líneas_sueltas)."""
    platos: list[dict] = []
    sueltas: list[str] = []
    for ln in (texto or "").splitlines():
        s = ln.strip()
        if not s:
            continue
        m = re.match(r"^(?P<label>[^.\n]{1,80}?)\.\s+(?P<titulo>.+?)\s+—\s+"
                     r"(?P<ings>.+?)\.?\s*$", s)
        if m and acepta_label(m.group("label").strip()):
            platos.append({
                "label": m.group("label").strip(),
                "title": m.group("titulo").strip(),
                "ingredients": [_parse_ingrediente(x)
                                for x in _split_ingredientes(m.group("ings"))],
                "prep": "", "prep_minutes": 0,
            })
            continue
        if platos:
            prep = s
            mm = re.search(r"\((\d+)\s*min\)\s*$", prep)
            if mm:
                platos[-1]["prep_minutes"] = int(mm.group(1))
                prep = prep[:mm.start()].strip()
            platos[-1]["prep"] = (platos[-1]["prep"] + " " + prep).strip()
        else:
            sueltas.append(s)
    return platos, sueltas


def _plato_igual(parsed: dict, opt: dict) -> bool:
    """¿El plato del Word es EXACTAMENTE lo que imprimió plan_doc para esta
    opción (título, ingredientes con gramos redondeados y medida casera, y
    preparación)? Si sí, el coach no lo tocó y no hay nada que aplicar."""
    if _ws(parsed["title"]) != _ws(opt.get("title")):
        return False
    if _ws(parsed["prep"]) != _ws(opt.get("prep")):
        return False
    if parsed["prep"] and int(parsed.get("prep_minutes") or 0) != int(opt.get("prep_minutes") or 0):
        return False
    ings = opt.get("ingredients") or []
    if len(parsed["ingredients"]) != len(ings):
        return False
    for pi, oi in zip(parsed["ingredients"], ings):
        og = oi.get("grams")
        impreso = round(og) if og else None
        pg = pi["grams"]
        if _norm(pi["food"]) != _norm(oi.get("food")):
            return False
        if (pg is None) != (impreso is None):
            return False
        if pg is not None and int(round(pg)) != int(impreso):
            return False
        if _norm(pi["household"]) != _norm(oi.get("household")):
            return False
    return True


def _resolver_food(nombre: str, food_map: dict) -> Food | None:
    """Alimento del catálogo por nombre: exacto (canónico/alias) y, si no,
    por palabras clave con la MISMA regla prudente que los ejercicios — solo
    se acepta un candidato ÚNICO («Avena» → «Copos de avena»). Ambiguo o
    desconocido → None (y el aviso de macros lo cubre aguas arriba)."""
    clave = _norm(nombre)
    row = food_map.get(clave)
    if row is not None:
        return row
    toks = {t for t in clave.split() if t not in _STOPWORDS}
    if not toks:
        return None
    hits: dict[int, Food] = {}
    for k, r in food_map.items():
        if r.id in hits:
            continue
        kt = {t for t in k.split() if t not in _STOPWORDS}
        if not kt:
            continue
        if toks <= kt or kt <= toks or clave in k or k in clave:
            hits[r.id] = r
    if len(hits) == 1:
        return next(iter(hits.values()))
    return None


def _macros_recalculados(ingredients: list[dict], food_map: dict) -> dict | None:
    """Macros del plato desde la base de alimentos (por 100 g en crudo) con la
    identidad Atwater kcal = 4·P + 4·CH + 9·G sobre los valores REDONDEADOS
    (half-up), igual que el solver — así el Revisor 0 no veta por céntimos.
    None si algún alimento no se reconoce o no trae gramos."""
    from app.services.nutrition_scale import _rhu, kcal_of

    p = c = f = 0.0
    for ing in ingredients:
        g = ing.get("grams")
        row = _resolver_food(ing.get("food"), food_map)
        if g is None or row is None:
            return None
        p += g * float(row.protein_g) / 100.0
        c += g * float(row.carbs_g) / 100.0
        f += g * float(row.fat_g) / 100.0
    p, c, f = _rhu(p), _rhu(c), _rhu(f)
    return {"kcal": kcal_of(p, c, f), "protein_g": p, "carbs_g": c, "fat_g": f}


def _ingredientes_aplicables(parsed_ings: list[dict], food_map: dict) -> list[dict]:
    """Ingredientes tal y como se guardan en el plan, enlazando `food_id`
    cuando el alimento se reconoce en el catálogo."""
    out = []
    for ing in parsed_ings:
        row = _resolver_food(ing["food"], food_map)
        out.append({"food": ing["food"], "grams": ing["grams"],
                    "household": ing["household"],
                    "food_id": row.id if row else None})
    return out


def _aplicar_plato(destino: dict, pl: dict, macros: dict | None,
                   food_map: dict) -> None:
    """Vuelca un plato parseado sobre una opción/dish del plan (contenido +
    macros recalculados si se pudieron)."""
    destino["title"] = pl["title"]
    destino["ingredients"] = _ingredientes_aplicables(pl["ingredients"], food_map)
    destino["prep"] = pl["prep"]
    destino["prep_minutes"] = pl["prep_minutes"]
    if macros is not None:
        destino["macros"] = macros


# Enfoques canónicos de la progresión semanal + sinónimos que escribe el coach.
_INTENT_MAP = {"base": "Base", "progresion": "Progresión", "pico": "Pico",
               "deload": "Deload", "descarga": "Deload",
               "semana de descarga": "Deload", "intensificacion": "Pico"}


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
    education = copy.deepcopy(plan.education_json) if plan.education_json else None

    avisos: list[str] = []
    frases: list[str] = []      # cambios que plan_diff no sabe describir
    # Restricciones del cliente: el educativo del Word se compara contra las
    # entradas que el documento IMPRIME, y plan_doc filtra por alérgenos y
    # patrón dietético.
    _cli = db.get(Client, plan.client_id) if plan.client_id else None
    bloqueados = list(getattr(_cli, "food_allergies", None) or []) + \
        list(getattr(_cli, "food_dislikes", None) or [])
    patron = getattr(_cli, "diet_pattern", None)
    id_a_nombre, nombre_a_id = _exercise_maps(db, training)
    edu_cambiado = False

    def _nombre_de(ex: dict) -> str:
        eid = ex.get("exercise_id")
        return id_a_nombre.get(eid, f"Ejercicio #{eid}")

    # Barras que anclan cajas de RECETAS, calculadas sobre la nutrición BASE
    # (el documento se imprimió con los nombres/horas de ANTES de esta edición).
    barras_comida: dict[str, tuple[int, str]] = {}   # norm(barra) → (slot, nombre)
    barras_dias: dict[str, str] = {}                  # norm(día) → clave de día
    if base_nutrition:
        for m_ in base_nutrition.get("meals") or []:
            if m_.get("slot") is None:
                continue
            clave = _norm(f"{m_.get('name', 'Comida')} · {m_.get('time', '')}")
            barras_comida[clave] = (m_.get("slot"), m_.get("name") or f"Toma {m_.get('slot')}")
        bank_ = base_nutrition.get("meal_bank") or {}
        if bank_.get("mode") == "strict":
            for d_ in bank_.get("days") or []:
                dk = _norm(str(d_.get("day", "")))
                if dk:
                    barras_dias[dk] = dk

    ultima_barra = ""
    energia: dict | None = None
    caja_free_meal: str | None = None
    tomas_rows: list[tuple[str, str, str]] = []
    cajas_flexibles: list[tuple[int, str, str]] = []   # (slot, nombre toma, texto)
    cajas_strict: list[tuple[str, str]] = []           # (clave de día, texto)
    rejilla_rows: list[tuple[str, list[str]]] = []     # (etiqueta toma, 7 celdas)
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
            macros_leidos = _parse_reparto(reparto)
            if kcal:
                energia = {"kcal": kcal, **macros_leidos}
                if reparto.strip() and not macros_leidos:
                    avisos.append(
                        "No he podido leer el reparto de macros del resumen "
                        "energético: aplico solo las calorías. Escríbelo como "
                        "«CH 000 g · P 000 g · G 000 g»."
                    )
                elif macros_leidos and len(macros_leidos) < 3:
                    faltan = [n for k, n in (("carbs_g", "carbohidratos"),
                                             ("protein_g", "proteína"),
                                             ("fat_g", "grasa")) if k not in macros_leidos]
                    avisos.append(
                        "Del reparto de macros solo he reconocido una parte: "
                        f"{', '.join(faltan)} se mantiene como estaba."
                    )
            continue

        # ---- tabla de ESTRUCTURA DIARIA (tomas) ------------------------
        if sig == SIG_TOMAS and nutrition is not None:
            vio_algo = True
            for row in block.rows[1:]:
                c = row.cells
                tomas_rows.append((_cell_text(c[0]), _cell_text(c[1]),
                                   _cell_text(c[2]) if len(c) > 2 else ""))
            continue

        # ---- tabla de PROGRESIÓN SEMANAL -------------------------------
        if sig == SIG_PROGRESION and training is not None:
            vio_algo = True
            semanas = {int(w.get("week")): w
                       for w in training.get("weekly_progression", []) if w.get("week")}
            for row in block.rows[1:]:
                c = row.cells
                n = _num(_cell_text(c[0]))
                if n is None:
                    if any(_cell_text(x).strip() for x in c):
                        avisos.append("Progresión semanal: una fila sin número de "
                                      "semana legible no se importó.")
                    continue
                if int(n) not in semanas:
                    avisos.append(
                        f"Progresión semanal: la semana {int(n)} no existe en el "
                        "plan — añadir o quitar semanas se hace desde el editor "
                        "web; esa fila no se importó.")
                    continue
                w = semanas[int(n)]
                intent_raw = _cell_text(c[1]).strip()
                if intent_raw:
                    # «pico», «deload», «Descarga»… también valen: antes solo la
                    # grafía exacta con mayúscula/acento se aplicaba y el resto
                    # se descartaba EN SILENCIO.
                    intent = _INTENT_MAP.get(_norm(intent_raw), intent_raw[:40])
                    if intent != w.get("intent"):
                        frases.append(f"Semana {int(n)}: enfoque {w.get('intent')} → {intent}")
                        w["intent"] = intent
                carga_txt = _cell_text(c[2]).strip()
                carga = _num(carga_txt)
                if carga is None and carga_txt:
                    avisos.append(f"Progresión semanal: no entiendo la carga "
                                  f"«{carga_txt[:20]}» de la semana {int(n)} — se "
                                  "mantiene la actual.")
                elif carga is not None and abs(carga - float(w.get("load_pct") or 0)) > 0.01:
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

        # ---- rejilla "Ejemplo de dieta semanal" ------------------------
        if sig == SIG_SEMANAL and nutrition is not None:
            vio_algo = True
            for row in block.rows[1:]:
                c = row.cells
                rejilla_rows.append((_cell_text(c[0]).strip(),
                                     [_cell_text(x).strip() for x in c[1:8]]))
            continue

        # ---- tabla "Cambios de tu plan · revisión #N" ------------------
        if sig == SIG_CAMBIOS and nutrition is not None:
            vio_algo = True
            _aplicar_cambios_plan(block, nutrition, frases, avisos)
            continue

        # ---- ¿tabla NUESTRA con la cabecera retocada? ------------------
        if sig and len(sig) >= 2:
            parecida = _sig_parecida(sig)
            if parecida:
                avisos.append(
                    f"La tabla de {parecida} tiene la cabecera modificada y no "
                    "se pudo importar NINGUNO de sus cambios: restaura la fila "
                    "de cabecera original (o vuelve a descargar el Word).")
                continue

        # ---- cajas 1×1 (por el título de sección que las precede) ------
        if len(block.rows) == 1 and len(block.rows[0].cells) == 1:
            texto = _cell_text(block.rows[0].cells[0])
            barra = _norm(ultima_barra)
            if barra.startswith("suplementacion recomendada") and nutrition is not None:
                _aplicar_suplementos(texto, nutrition, frases, avisos)
            elif barra.startswith("semana de descarga") and training is not None:
                nuevo = texto.strip()
                # Vaciar la caja también cuenta: es la forma natural de QUITAR
                # el deload (antes se exigía texto y el borrado se ignoraba).
                if nuevo != (training.get("deload_instructions") or "").strip():
                    training["deload_instructions"] = nuevo
                    frases.append("Instrucciones de la semana de descarga actualizadas"
                                  if nuevo else "Semana de descarga eliminada")
            elif barra.startswith("cardio y neat") and training is not None:
                _aplicar_cardio(texto, training, frases, avisos)
            elif barra.startswith("tu margen de maniobra") and nutrition is not None:
                _aplicar_margen(texto, nutrition, frases)
            elif barra.startswith("tu comida libre semanal") and nutrition is not None:
                # vive dentro de meal_bank → se aplica DESPUÉS del rescale
                # (que reconstruye el banco desde la base)
                caja_free_meal = texto.strip()
            elif barra.startswith("por que este enfoque") and nutrition is not None:
                nuevo = texto.strip()
                if nuevo and nuevo != (nutrition.get("rationale") or "").strip():
                    nutrition["rationale"] = nuevo
                    frases.append("«Por qué este enfoque» actualizado")
            elif barra.startswith("estructura") and training is not None:
                # info_box: "N días/semana: razón del split" — la etiqueta la
                # calcula el sistema; lo editable es el texto tras los dos puntos.
                valor = texto.split(":", 1)[1].strip() if ":" in texto else texto.strip()
                if valor and valor != (training.get("split_rationale") or "").strip():
                    training["split_rationale"] = valor
                    frases.append("Razón de la estructura (split) actualizada")
            elif barra.startswith("aprende con tu plan") and education is not None:
                # MISMO filtro que plan_doc: no basta con "tiene texto", el
                # documento descarta además las píldoras con un alérgeno o
                # contrarias al patrón dietético. Sin esa segunda mitad, en
                # cuanto el cliente tenía alergias el Word traía 2 píldoras y el
                # plan 3, no cuadraba el recuento y la caja entera se descartaba:
                # el educativo dejaba de importarse justo para esos clientes.
                pills = [p for p in education.get("pills") or []
                         if str(p.get("for_client") or "").strip()
                         and not _edu_bloqueado(
                             (p.get("topic", ""), p.get("for_client", "")),
                             bloqueados, patron)]
                edu_cambiado |= _aplicar_educativo(
                    texto, pills, "topic", "for_client", "píldora", frases, avisos)
            elif barra.startswith("tecnica") and education is not None:
                edu_cambiado |= _aplicar_biomech(texto, education, frases, avisos)
            elif barra.startswith("preguntas frecuentes") and education is not None:
                faq = [f for f in education.get("faq") or []
                       if str(f.get("q") or "").strip()
                       and not _edu_bloqueado((f.get("q", ""), f.get("a", "")),
                                              bloqueados, patron)]
                edu_cambiado |= _aplicar_educativo(
                    texto, faq, "q", "a", "pregunta", frases, avisos)
            elif barra in barras_comida and nutrition is not None:
                slot, nombre_toma = barras_comida[barra]
                cajas_flexibles.append((slot, nombre_toma, texto))
            elif barra in barras_dias and nutrition is not None:
                cajas_strict.append((barras_dias[barra], texto))
            elif training is not None and "·" in ultima_barra:
                # Caja bajo la barra de una SESIÓN: calentamiento o vuelta a la
                # calma (antes se perdían sin aviso).
                _aplicar_caja_sesion(texto, ultima_barra, training, frases)
            continue

    if not vio_algo:
        raise WordImportError(
            "No reconozco este documento como el Word del plan: no contiene "
            "ninguna de sus tablas. Descárgalo con «Word editable», edítalo y "
            "vuelve a subir ese mismo archivo."
        )

    # ---- aplicar energía (misma verdad que el editor: rescale) ---------
    # ANTES que las tomas y las recetas: rescale_nutrition reconstruye los
    # objetivos por comida y el banco desde la BASE y pisaría lo recién
    # importado.
    _aplicar_energia(energia, nutrition, base_nutrition, avisos)

    # ---- aplicar tomas (hora/nombre/estrategia por posición) -----------
    if tomas_rows and nutrition is not None:
        _aplicar_tomas(tomas_rows, nutrition, base_nutrition, frases, avisos)

    # ---- aplicar recetas (SIEMPRE tras el rescale de energía) ----------
    food_map = _food_map(db) if (cajas_flexibles or cajas_strict) else {}
    _aplicar_opciones_flexibles(cajas_flexibles, nutrition, base_nutrition,
                                food_map, frases, avisos)
    _aplicar_menu_strict(cajas_strict, nutrition, base_nutrition,
                         food_map, frases, avisos)
    _aplicar_rejilla_semanal(rejilla_rows, nutrition, base_nutrition,
                             frases, avisos)
    if caja_free_meal and nutrition is not None:
        bank_fm = nutrition.get("meal_bank") or {}
        if caja_free_meal != (bank_fm.get("free_meal_guidelines") or "").strip():
            bank_fm["free_meal_guidelines"] = caja_free_meal
            nutrition["meal_bank"] = bank_fm
            frases.append("Pauta de la comida libre semanal actualizada")

    resultado = {
        "nutrition_json": nutrition,
        "training_json": training,
        "education_json": education if edu_cambiado else None,
        "warnings": avisos,
        "extra_changes": frases,
    }
    return resultado


def _aplicar_energia(energia: dict | None, nutrition: dict | None,
                     base_nutrition: dict | None, avisos: list) -> None:
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
    # Un valor ilegible/absurdo NO reescala el plan entero a la nada: el tope
    # del PATCH solo capa por arriba, así que 2,15 kcal (una coma anglosajona
    # mal leída) destruiría todas las tomas.
    if 0 < kcal < 500:
        avisos.append(
            f"Las calorías leídas del Word ({kcal:g}) no son creíbles — no se "
            "aplicó el resumen energético. Escríbelas como «2.150 kcal».")
        return
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


def _aplicar_tomas(tomas_rows: list, nutrition: dict, base_nutrition: dict | None,
                   frases: list, avisos: list) -> None:
    """Hora, nombre y ESTRATEGIA de cada toma, por posición. La estrategia se
    compara contra lo que el documento IMPRIMIÓ (la guardada o la derivada del
    nombre): solo si el coach la reescribió se aplica."""
    from app.services.docs.plan_doc import _estrategia

    meals = nutrition.get("meals") or []
    base_meals = (base_nutrition or {}).get("meals") or []
    if len(tomas_rows) != len(meals):
        avisos.append(
            "El número de tomas del Word no coincide con el del plan: "
            "para añadir o quitar comidas usa el editor web."
        )
        return
    for i, ((hora, nombre, estrategia), meal) in enumerate(zip(tomas_rows, meals)):
        hora = hora.strip()
        nombre = nombre.strip()
        estrategia = _ws(estrategia)
        if hora and hora != (meal.get("time") or "").strip():
            frases.append(f"{meal.get('name') or 'Comida'}: hora "
                          f"{meal.get('time')} → {hora}")
            meal["time"] = hora
        if nombre and nombre != (meal.get("name") or "").strip():
            frases.append(f"Toma {meal.get('slot')}: renombrada a «{nombre}»")
            meal["name"] = nombre
        base_meal = base_meals[i] if i < len(base_meals) else meal
        impresa = _ws(str(base_meal.get("strategy") or "").strip()
                      or _estrategia(base_meal.get("name", "")))
        if estrategia and estrategia != impresa:
            meal["strategy"] = estrategia
            frases.append(f"{meal.get('name') or 'Comida'}: estrategia actualizada")


def _aplicar_cambios_plan(table, nutrition: dict, frases: list, avisos: list) -> None:
    """Tabla «Cambios de tu plan · revisión #N» (applied_adjustments): texto
    que el cliente lee en su PDF/portal — editable por posición."""
    aa = nutrition.get("applied_adjustments") or {}
    items = aa.get("items") or []
    filas = table.rows[1:]
    if len(filas) != len(items):
        avisos.append(
            "La tabla «Cambios de tu plan» del Word no tiene el mismo número "
            "de filas que el plan: esa tabla no se importó.")
        return
    campo_detalle = "detail" if any("detail" in it for it in items) or not items else "change"
    for row, it in zip(filas, items):
        c = row.cells
        area = _cell_text(c[0]).strip()
        detalle = _cell_text(c[1]).strip()
        razon = _cell_text(c[2]).strip()
        if area and _norm(area) != _norm(it.get("area") or ""):
            it["area"] = area
            frases.append("«Cambios de tu plan»: área actualizada")
        impreso = (it.get("detail") or it.get("change") or "").strip()
        if detalle and detalle != impreso:
            it[campo_detalle] = detalle
            frases.append("«Cambios de tu plan»: detalle actualizado")
        if razon and razon != (it.get("reason") or "").strip():
            it["reason"] = razon
            frases.append("«Cambios de tu plan»: motivo actualizado")


def _aplicar_cardio(texto: str, training: dict, frases: list, avisos: list) -> None:
    """Caja "Cardio y NEAT": pasos diarios + UNA línea por sesión de cardio
    («LISS: 30 min × 3/sem — notas»). Antes solo se leían los pasos y las
    sesiones editadas se perdían sin aviso."""
    cardio = training.get("cardio") or {}
    m = re.search(r"pasos diarios objetivo:\s*([\d.,]+)", texto, re.IGNORECASE)
    if not m:
        # el coach reescribió la etiqueta («9.000 pasos al día»): el número
        # pegado a la palabra "pasos" sigue valiendo
        m = re.search(r"(\d[\d.,]{2,})\s*pasos", texto, re.IGNORECASE)
    pasos = _num(m.group(1)) if m else None
    if pasos is not None and int(pasos) != int(cardio.get("daily_steps") or 0):
        frases.append(f"Pasos diarios: {cardio.get('daily_steps')} → {int(pasos)}")
        cardio["daily_steps"] = int(pasos)
        training["cardio"] = cardio
    elif pasos is None and cardio.get("daily_steps") and "pasos" in _norm(texto):
        avisos.append("Cardio: no pude leer los pasos diarios — escríbelos como "
                      "«Pasos diarios objetivo: 8.000 pasos».")

    sesiones = cardio.get("sessions") or []
    lineas_ses = []
    for ln in (texto or "").splitlines():
        s = ln.strip()
        mm = re.match(r"^(?P<tipo>[^:\n]{1,30}):\s*(?P<min>\d+)\s*min\s*[×xX]\s*"
                      r"(?P<veces>\d+)\s*/sem(?:\s*—\s*(?P<notas>.*))?$", s)
        if mm and "pasos" not in _norm(mm.group("tipo")):
            lineas_ses.append(mm)
    if not lineas_ses:
        return
    if len(lineas_ses) != len(sesiones):
        avisos.append(
            "Cardio: el número de sesiones del Word no coincide con el del "
            "plan — añadir o quitar sesiones de cardio se hace desde el "
            "editor web; esas líneas no se importaron.")
        return
    for mm, ses in zip(lineas_ses, sesiones):
        tipo = mm.group("tipo").strip()
        minutos = int(mm.group("min"))
        veces = int(mm.group("veces"))
        notas = (mm.group("notas") or "").strip()
        if _norm(tipo) != _norm(ses.get("type")):
            frases.append(f"Cardio: {ses.get('type')} → {tipo}")
            ses["type"] = tipo.lower()
        if minutos != int(ses.get("minutes") or 0):
            frases.append(f"Cardio {ses.get('type')}: {ses.get('minutes')} → {minutos} min")
            ses["minutes"] = minutos
        if veces != int(ses.get("times_per_week") or 0):
            frases.append(f"Cardio {ses.get('type')}: {ses.get('times_per_week')} → {veces}/sem")
            ses["times_per_week"] = veces
        if notas != (ses.get("notes") or "").strip():
            ses["notes"] = notas or None
            frases.append(f"Cardio {ses.get('type')}: notas actualizadas")


def _aplicar_margen(texto: str, nutrition: dict, frases: list) -> None:
    """Caja "Tu margen de maniobra": líneas «• regla» + opcional «Recarga o
    descanso: …». Se reemplaza el conjunto si cambió (antes se perdía todo
    sin aviso)."""
    reglas: list[str] = []
    refeed: str | None = None
    for ln in (texto or "").splitlines():
        s = ln.strip()
        if not s:
            continue
        low = _norm(s)
        if low.startswith("recarga o descanso"):
            refeed = s.split(":", 1)[1].strip() if ":" in s else ""
        elif refeed is not None:
            refeed = (refeed + " " + s).strip()
        else:
            reglas.append(s.lstrip("•-– ").strip())
    reglas = [r for r in reglas if r]
    actuales = [str(r).strip() for r in (nutrition.get("flexibility_rules") or [])
                if str(r).strip()]
    if reglas and reglas != actuales:
        nutrition["flexibility_rules"] = reglas
        frases.append("Reglas de flexibilidad actualizadas desde el Word")
    if refeed is not None and refeed != (nutrition.get("refeed_or_break") or "").strip():
        nutrition["refeed_or_break"] = refeed
        frases.append("Recarga/descanso actualizado desde el Word")


def _aplicar_caja_sesion(texto: str, barra: str, training: dict, frases: list) -> None:
    """Cajas bajo la barra de una sesión: «Calentamiento: …» y «Vuelta a la
    calma: …» (info_box de par etiqueta+texto)."""
    sesion, _, _ = _buscar_sesion(training, barra)
    if sesion is None:
        return
    low = _norm(texto)
    etiqueta = sesion.get("name") or sesion.get("day") or "Sesión"
    if low.startswith("calentamiento"):
        valor = texto.split(":", 1)[1].strip() if ":" in texto else ""
        if valor and valor != (sesion.get("warmup") or "").strip():
            sesion["warmup"] = valor
            frases.append(f"{etiqueta}: calentamiento actualizado")
    elif low.startswith("vuelta a la calma"):
        valor = texto.split(":", 1)[1].strip() if ":" in texto else ""
        if valor and valor != (sesion.get("cooldown") or "").strip():
            sesion["cooldown"] = valor
            frases.append(f"{etiqueta}: vuelta a la calma actualizada")


def _edu_bloqueado(item, bloqueados: list[str], patron: str | None) -> bool:
    """¿plan_doc descartaría esta píldora/FAQ? Se delega en SU criterio para que
    el recuento del importador y el del documento no puedan divergir."""
    try:
        from app.services.docs.plan_doc import _blocked_line

        return bool(_blocked_line(item, bloqueados, patron))
    except Exception:  # noqa: BLE001 — ante la duda, se importa (no se pierde)
        return False


def _aplicar_educativo(texto: str, items: list, campo_lbl: str, campo_val: str,
                       nombre: str, frases: list, avisos: list) -> bool:
    """Cajas del educativo con pares «Etiqueta: texto» (píldoras y FAQ),
    aplicadas por posición. Devuelve True si cambió algo."""
    pares = _pares_de_caja(texto)
    if pares is None or len(pares) != len(items):
        avisos.append(
            f"Educativo: la caja de {nombre}s del Word no tiene el mismo "
            f"número de entradas que el plan ({len(items)}) — esa caja no se "
            "importó (añadir/quitar se hace regenerando).")
        return False
    cambio = False
    for (lbl, val), it in zip(pares, items):
        if lbl and lbl != (it.get(campo_lbl) or "").strip():
            it[campo_lbl] = lbl
            cambio = True
        if val and _ws(val) != _ws(it.get(campo_val)):
            it[campo_val] = val
            cambio = True
    if cambio:
        frases.append(f"Educativo: {nombre}s actualizadas desde el Word")
    return cambio


def _aplicar_biomech(texto: str, education: dict, frases: list, avisos: list) -> bool:
    """Caja "Técnica: claves por patrón": pares «Patrón: clave · clave — por
    qué», por posición."""
    items = [b for b in education.get("biomech_by_pattern") or []
             if b.get("pattern")]
    pares = _pares_de_caja(texto)
    if pares is None or len(pares) != len(items):
        avisos.append(
            "Educativo: la caja de técnica por patrón del Word no tiene el "
            f"mismo número de entradas que el plan ({len(items)}) — esa caja "
            "no se importó.")
        return False
    cambio = False
    for (lbl, val), it in zip(pares, items):
        if lbl and lbl != (it.get("pattern") or "").strip():
            it["pattern"] = lbl
            cambio = True
        cues_txt, _, why = val.partition(" — ")
        cues = [c.strip() for c in cues_txt.split("·") if c.strip()]
        why = why.strip()
        impresos = [c.strip() for c in (it.get("cues") or []) if str(c).strip()]
        if cues and cues != impresos:
            it["cues"] = cues
            cambio = True
        if why != (it.get("why") or "").strip():
            it["why"] = why or None
            cambio = True
    if cambio:
        frases.append("Educativo: técnica por patrón actualizada desde el Word")
    return cambio


def _aplicar_opciones_flexibles(cajas: list, nutrition: dict | None,
                                base_nutrition: dict | None, food_map: dict,
                                frases: list, avisos: list) -> None:
    """Cajas de recetas del banco FLEXIBLE («Opción N. Título — ingredientes»).
    Se aplican DESPUÉS del rescale de energía (que reconstruye el banco desde
    la base): la edición explícita del coach manda sobre el reescalado."""
    if not cajas or nutrition is None:
        return
    bank1 = nutrition.get("meal_bank")
    if not isinstance(bank1, dict):
        bank1 = {"mode": "flexible_7", "slots": []}
        nutrition["meal_bank"] = bank1
    if bank1.get("mode") == "strict":
        return  # en strict las recetas van por días, no por tomas
    base_slots = {s.get("slot"): s
                  for s in ((base_nutrition or {}).get("meal_bank") or {}).get("slots", [])}
    new_slots = {s.get("slot"): s for s in bank1.get("slots", [])}
    for slot, nombre_toma, texto in cajas:
        sb0 = base_slots.get(slot)
        sb1 = new_slots.get(slot)
        if (sb0 or {}).get("fmt") == "equivalences":
            # las EQUIVALENCIAS son formato libre: se editan regenerando/swap
            continue
        if not sb1:
            # La toma no tenía recetario (caja "Toma libre"): escribir
            # «Opción N. …» en el Word lo CREA — antes se ignoraba en silencio.
            sb1 = {"slot": slot, "fmt": "options", "options": [],
                   "weekly_examples": []}
            if _parse_lineas_platos(texto, lambda lbl: bool(_RE_OPCION.match(lbl)))[0]:
                bank1.setdefault("slots", []).append(sb1)
                bank1["slots"].sort(key=lambda s: (s.get("slot") is None, s.get("slot")))
                new_slots[slot] = sb1
            else:
                continue
        platos, sueltas = _parse_lineas_platos(
            texto, lambda lbl: bool(_RE_OPCION.match(lbl)))
        for s in sueltas:
            if _norm(s).startswith("toma libre"):
                continue
            avisos.append(
                f"{nombre_toma}: no pude leer la línea «{s[:60]}» — escríbela "
                "como «Opción N. Título — Alimento 000 g (medida), …». No se "
                "cambió nada ahí.")
        opts0 = sb0.get("options") if sb0 else []
        opts1 = sb1.setdefault("options", [])
        for pl in platos:
            n = int(_RE_OPCION.match(pl["label"]).group(1))
            if 1 <= n <= len(opts0 or []) and _plato_igual(pl, opts0[n - 1]):
                continue  # sin cambios: el rescale (si lo hubo) manda
            if n > len(opts1) + 1 or n > 4:
                avisos.append(
                    f"{nombre_toma}: «Opción {n}» no existe en el plan (hay "
                    f"{len(opts1)}) — numera seguido para añadirla (máx. 4).")
                continue
            macros = _macros_recalculados(pl["ingredients"], food_map)
            if n == len(opts1) + 1:
                if macros is None:
                    avisos.append(
                        f"{nombre_toma}: para AÑADIR la opción {n} necesito "
                        "reconocer todos sus alimentos con gramos (no puedo "
                        "calcular sus macros) — revisa los nombres.")
                    continue
                nueva = {"key": None, "title": "", "ingredients": [],
                         "prep": "", "prep_minutes": 0, "macros": macros,
                         "tags": []}
                _aplicar_plato(nueva, pl, macros, food_map)
                opts1.append(nueva)
                frases.append(f"{nombre_toma}: añadida la opción {n} («{pl['title']}»)")
                continue
            _aplicar_plato(opts1[n - 1], pl, macros, food_map)
            if macros is None:
                avisos.append(
                    f"{nombre_toma}: opción {n} aplicada, pero no reconozco "
                    "todos sus alimentos — los macros de esa opción NO se han "
                    "recalculado: revísalos en el editor.")
            frases.append(f"{nombre_toma}: opción {n} actualizada («{pl['title']}»)")


def _aplicar_menu_strict(cajas: list, nutrition: dict | None,
                         base_nutrition: dict | None, food_map: dict,
                         frases: list, avisos: list) -> None:
    """Cajas por DÍA del menú cerrado (strict): líneas «Toma · hora. Título —
    ingredientes.» + preparación. También post-rescale."""
    if not cajas or nutrition is None:
        return
    bank1 = nutrition.get("meal_bank") or {}
    if bank1.get("mode") != "strict":
        return
    bank0 = (base_nutrition or {}).get("meal_bank") or {}
    dias0 = {_norm(str(d.get("day", ""))): d for d in bank0.get("days") or []}
    dias1 = {_norm(str(d.get("day", ""))): d for d in bank1.get("days") or []}
    slot_por_nombre = {_norm(m.get("name")): m.get("slot")
                       for m in (base_nutrition or {}).get("meals") or []
                       if m.get("name")}

    def _slot_de(label: str) -> int | None:
        etiqueta = label.split("·")[0].strip()
        mtoma = re.match(r"(?i)toma\s+(\d+)", etiqueta)
        if mtoma:
            return int(mtoma.group(1))
        return slot_por_nombre.get(_norm(etiqueta))

    for dia_key, texto in cajas:
        d0, d1 = dias0.get(dia_key), dias1.get(dia_key)
        if not d1:
            continue
        dia_lbl = str(d1.get("day", "")).capitalize()
        platos, sueltas = _parse_lineas_platos(
            texto, lambda lbl: _slot_de(lbl) is not None)
        for s in sueltas:
            avisos.append(
                f"Menú de {dia_lbl}: no pude leer la línea «{s[:60]}» — usa el "
                "formato «Toma · hora. Título — Alimento 000 g, …».")
        e0 = {int(m.get("slot") or 0): m for m in (d0 or {}).get("meals") or []}
        e1 = {int(m.get("slot") or 0): m for m in d1.get("meals") or []}
        for pl in platos:
            slot = _slot_de(pl["label"])
            if slot is None or slot not in e1:
                avisos.append(
                    f"Menú de {dia_lbl}: no sé a qué toma corresponde "
                    f"«{pl['label']}» — esa línea no se importó.")
                continue
            dish0 = (e0.get(slot) or {}).get("dish") or {}
            if dish0 and _plato_igual(pl, dish0):
                continue
            macros = _macros_recalculados(pl["ingredients"], food_map)
            dish1 = e1[slot].setdefault("dish", {})
            _aplicar_plato(dish1, pl, macros, food_map)
            if macros is None:
                avisos.append(
                    f"Menú de {dia_lbl}: plato de la toma {slot} aplicado, "
                    "pero no reconozco todos sus alimentos — sus macros NO se "
                    "han recalculado: revísalos en el editor.")
            etiqueta = pl["label"].split("·")[0].strip()
            frases.append(f"Menú de {dia_lbl} · {etiqueta}: plato actualizado "
                          f"(«{pl['title']}»)")


def _aplicar_rejilla_semanal(rejilla_rows: list, nutrition: dict | None,
                             base_nutrition: dict | None,
                             frases: list, avisos: list) -> None:
    """Rejilla "Ejemplo de dieta semanal". En flexible, cada fila editada se
    guarda como los 7 ejemplos semanales de su toma. En strict la rejilla es
    un RESUMEN automático de los días: se avisa para editar las secciones por
    día (si no, dos verdades divergirían)."""
    if not rejilla_rows or nutrition is None:
        return
    bank1 = nutrition.get("meal_bank") or {}
    base = base_nutrition or {}
    bank0 = base.get("meal_bank") or {}
    slot_por_nombre = {_norm(m.get("name")): m.get("slot")
                       for m in base.get("meals") or [] if m.get("name")}
    if (bank0.get("mode") or bank1.get("mode")) == "strict":
        # comparar contra lo impreso para avisar SOLO si el coach la tocó
        impresas = {}
        by_day = {_norm(d.get("day")): d for d in bank0.get("days") or []}
        orden = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
        for m in base.get("meals") or []:
            celdas = []
            for dslug in orden:
                d = by_day.get(dslug)
                title = ""
                for e in (d or {}).get("meals", []):
                    if e.get("slot") == m.get("slot"):
                        title = (e.get("dish") or {}).get("title", "")
                celdas.append(_ws(title))
            impresas[_norm(m.get("name") or "")] = celdas
        for etiqueta, celdas in rejilla_rows:
            if [_ws(c) for c in celdas] != impresas.get(_norm(etiqueta)):
                avisos.append(
                    "En menú cerrado la rejilla semanal es un resumen "
                    "automático: edita las secciones de cada día (Lunes, "
                    "Martes…) — los cambios de la rejilla no se importan.")
                break
        return

    slots1 = {s.get("slot"): s for s in bank1.get("slots", [])}
    slots0 = {s.get("slot"): s for s in bank0.get("slots", [])}
    for etiqueta, celdas in rejilla_rows:
        slot = slot_por_nombre.get(_norm(etiqueta))
        sb1 = slots1.get(slot)
        if slot is None or sb1 is None:
            avisos.append(
                f"Dieta semanal: no sé a qué toma corresponde la fila "
                f"«{etiqueta[:40]}» — esa fila no se importó.")
            continue
        sb0 = slots0.get(slot) or {}
        wk = [x for x in (sb0.get("weekly_examples") or []) if x]
        opts = sb0.get("options") or []
        impresas = []
        for di in range(7):
            if wk:
                impresas.append(_ws(wk[di % len(wk)]))
            elif opts:
                impresas.append(_ws(opts[di % len(opts)].get("title", "")))
            else:
                impresas.append("")
        if [_ws(c) for c in celdas] == impresas:
            continue
        sb1["weekly_examples"] = [c for c in celdas]
        frases.append(f"{etiqueta}: ejemplos de la dieta semanal actualizados")


def _buscar_sesion(training: dict, barra: str):
    """Localiza la sesión de una barra «Día · Nombre». Devuelve (sesión,
    nombre_en_barra, sesiones_del_mismo_día)."""
    partes = [x.strip() for x in barra.split("·")]
    dia = partes[0] if partes else ""
    nombre_ses = partes[1] if len(partes) > 1 else ""
    mismas = [s for s in training.get("sessions", [])
              if _norm(s.get("day")) == _norm(dia)]
    for s in mismas:
        if _norm(s.get("name")) == _norm(nombre_ses):
            return s, nombre_ses, mismas
    return (mismas[0] if mismas else None), nombre_ses, mismas


def _aplicar_sesion(table, barra: str, training: dict, id_a_nombre: dict,
                    nombre_a_id: dict, frases: list, avisos: list, _nombre_de) -> None:
    """Aplica la tabla de UNA sesión: cambios de series/reps/RIR/descanso/
    textos, cambio de ejercicio por nombre, altas y bajas de filas."""
    sesion, nombre_ses, mismas = _buscar_sesion(training, barra)
    if sesion is None:
        avisos.append(f"No encuentro en el plan la sesión «{barra}»: esa tabla no se importó.")
        return
    # Renombrar la sesión en la barra ("Torso" → "Pecho y hombro") también
    # cuenta — solo si el día tiene UNA sesión (con dos sería ambiguo).
    if (nombre_ses and len(mismas) == 1
            and _norm(sesion.get("name")) != _norm(nombre_ses)):
        frases.append(f"Sesión «{sesion.get('name')}» renombrada a «{nombre_ses}»")
        sesion["name"] = nombre_ses

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
                # sin coincidencia exacta: por palabras clave ("press inclinado
                # mancuernas" → "Press banca inclinado con mancuernas")
                candidatos = _fuzzy_exercise(clave, nombre_a_id)
                if len(candidatos) == 1:
                    eid = next(iter(candidatos))
                    frases.append(f"{etiqueta}: «{nombre}» interpretado como "
                                  f"«{id_a_nombre.get(eid, '')}» (biblioteca)")
                elif len(candidatos) > 1:
                    nombres_cand = ", ".join(
                        id_a_nombre.get(e, k) for e, k in list(candidatos.items())[:3])
                    avisos.append(
                        f"{etiqueta}: «{nombre}» es ambiguo en la biblioteca "
                        f"({nombres_cand}…) — esa fila no se importó: escribe "
                        "el nombre exacto.")
                    if idx < len(actuales) and id(actuales[idx]) not in reclamados:
                        reclamados.add(id(actuales[idx]))
                        resultado.append(actuales[idx])
                    continue
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
                frases.append(f"{etiqueta}: cambiado {_nombre_de(objetivo)} por "
                              f"{id_a_nombre.get(eid, nombre)}")
                objetivo["exercise_id"] = eid
            else:
                objetivo = {
                    "exercise_id": eid, "sets": 3, "rep_range": "8-10",
                    "rir": "2", "tempo": None, "rest_sec": 90,
                    "start_weight_hint_kg": None, "progression_rule": "",
                    "technique_cue": "", "biomech_cue": "", "coach_notes": None,
                }
                frases.append(f"{etiqueta}: añadido {id_a_nombre.get(eid, nombre)}")

        reclamados.add(id(objetivo))
        resultado.append(objetivo)

        # ---- campos de la fila ----
        sxr = _cell_text(c[1])
        m = re.search(r"(\d+)\s*[×xX*]\s*(.+)", sxr)
        if m:
            sets_leidos = int(m.group(1))
            sets = max(1, min(10, sets_leidos))
            if sets != sets_leidos:
                avisos.append(f"{etiqueta}: {sets_leidos} series de "
                              f"{_nombre_de(objetivo)} está fuera de rango "
                              f"(1-10) — se aplicó {sets}.")
            rep = m.group(2).strip()[:20]
            if sets != int(objetivo.get("sets") or 0):
                objetivo["sets"] = sets
            if rep and rep != (objetivo.get("rep_range") or ""):
                objetivo["rep_range"] = rep
        elif sxr.strip():
            avisos.append(f"{etiqueta}: no entiendo las series "
                          f"«{sxr.strip()[:20]}» de {_nombre_de(objetivo)} — "
                          "usa «4×8-10».")
        rir = re.sub(r"(?i)^rir\s*", "", _cell_text(c[2])).strip()[:10]
        if rir and rir != str(objetivo.get("rir") or ""):
            objetivo["rir"] = rir
        texto_desc = _cell_text(c[3]).strip()
        descanso = _parse_rest(texto_desc)
        if descanso is not None and 15 <= int(descanso) <= 600:
            if int(descanso) != int(objetivo.get("rest_sec") or 0):
                objetivo["rest_sec"] = int(descanso)
        elif texto_desc:
            avisos.append(f"{etiqueta}: no entiendo el descanso "
                          f"«{texto_desc[:20]}» de {_nombre_de(objetivo)} (usa "
                          "segundos, o «2 min») — se mantiene el actual.")
        cue = _parse_cue_cell(_cell_text(c[4]))
        if cue["technique_cue"] and cue["technique_cue"] != (objetivo.get("technique_cue") or "").strip():
            objetivo["technique_cue"] = cue["technique_cue"]
            frases.append(f"{_nombre_de(objetivo)}: clave técnica actualizada")
        if cue["biomech_cue"] is not None and cue["biomech_cue"] != (objetivo.get("biomech_cue") or "").strip():
            objetivo["biomech_cue"] = cue["biomech_cue"]
            frases.append(f"{_nombre_de(objetivo)}: clave biomecánica actualizada")
        if cue["tempo"] is not None and cue["tempo"] != str(objetivo.get("tempo") or "").strip():
            objetivo["tempo"] = cue["tempo"] or None
            frases.append(f"{_nombre_de(objetivo)}: tempo actualizado")
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
