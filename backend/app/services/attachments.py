"""Adjuntos LEÍDOS: la analítica, el informe médico o de fisio, la dieta o la
rutina anteriores que el cliente o el coach suben junto a la anamnesis.

Hasta ahora un adjunto se guardaba con el prefijo `adjunto_` y NADIE lo leía:
la analítica que el propio cuestionario pide adjuntar no llegaba ni a la ficha,
ni al prompt de generación, ni al panel de supervisión. El criterio del dueño
es que cualquier fuente de información se lea y alimente lo que toque.

Qué hace este módulo:
- `extract_attachment`: la IA lee el adjunto (cualquier formato, vía el lector
  universal) y devuelve un `AttachmentExtraction`: qué es, de cuándo, resumen,
  valores de analítica (con rango y bandera alto/bajo), hallazgos clínicos,
  lesiones, medicación, suplementos, dieta y entreno previos, y ALERTAS que el
  coach debe ver sí o sí. La IA transcribe; no interpreta clínicamente ni
  calcula nada.
- `merge_into_client`: vuelca lo leído en las notas de la ficha de forma
  IDEMPOTENTE: cada adjunto escribe su propio bloque, marcado con
  `[Adjunto: nombre]`, que se sustituye si el mismo adjunto se relee. Nunca
  pisa lo que el coach escribió a mano. La analítica se compacta: fuera de
  rango una línea por marcador; los normales, agrupados.
- Sidecar `_adjunto_<stem>.json` por adjunto y `attachment_context` para que
  la generación del plan y el panel §9 reciban esos hallazgos como contexto.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

MARCA = "[Adjunto: {stem}]"
_RE_BLOQUE = re.compile(r"(?ms)^- \[Adjunto: (?P<stem>[^\]]+)\][^\n]*\n(?:(?!- \[Adjunto: )[^\n]*\n?)*")


def _lista(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [x.strip(" -•\t") for x in v.splitlines() if x.strip(" -•\t")]
    if isinstance(v, dict):
        return [f"{k}: {val}" for k, val in v.items() if str(val).strip()]
    if isinstance(v, list):
        out = []
        for x in v:
            if isinstance(x, dict):
                out.append(_dict_a_linea(x))
            elif str(x).strip():
                out.append(str(x).strip())
        return [x for x in out if x]
    return [str(v)]


def _dict_a_linea(x: dict) -> str:
    """La IA a veces manda objetos donde se pedían líneas («{name, dose,
    timing}»): se leen como «Nombre — dosis (momento)», y cualquier otra forma
    como «clave: valor» — nunca se descarta información por su forma."""
    nombre = x.get("name") or x.get("nombre") or x.get("marker") or x.get("title")
    if nombre:
        dosis = x.get("dose") or x.get("dosis") or x.get("value") or x.get("amount")
        momento = x.get("timing") or x.get("momento") or x.get("frequency") or x.get("frecuencia")
        txt = str(nombre).strip()
        if dosis:
            txt += f" — {str(dosis).strip()}"
        if momento:
            txt += f" ({str(momento).strip()})"
        resto = {k: val for k, val in x.items()
                 if k not in ("name", "nombre", "marker", "title", "dose", "dosis", "value",
                              "amount", "timing", "momento", "frequency", "frecuencia")
                 and str(val).strip()}
        if resto:
            txt += " · " + " · ".join(f"{k}: {val}" for k, val in resto.items())
        return txt
    return " · ".join(f"{k}: {val}" for k, val in x.items() if str(val).strip())


class LabValue(BaseModel):
    marker: str
    value: str
    unit: str | None = None
    reference: str | None = None
    flag: str | None = Field(None, description="alto|bajo|normal|desconocido")

    @field_validator("value", "marker", mode="before")
    @classmethod
    def _texto(cls, v):
        return "" if v is None else str(v).strip()

    @field_validator("flag", mode="before")
    @classmethod
    def _flag(cls, v):
        if v is None:
            return None
        s = unicodedata.normalize("NFKD", str(v).lower()).encode("ascii", "ignore").decode()
        if s.startswith(("alt", "h", "elev", "sup")):
            return "alto"
        if s.startswith(("baj", "l", "dism", "inf")):
            return "bajo"
        if s.startswith(("norm", "ok", "n")):
            return "normal"
        return "desconocido"


class AttachmentExtraction(BaseModel):
    """Lo que la IA lee de un adjunto. Todo opcional: lo que no haya, vacío."""

    document_kind: str | None = Field(
        None, description="analitica|informe_medico|informe_fisio|receta|dieta_previa|"
                          "plan_entreno_previo|cuestionario|otro")
    title: str | None = None
    document_date: str | None = Field(None, description="Fecha del documento (YYYY-MM-DD o texto)")
    summary: list[str] = Field(default_factory=list, description="2-6 líneas: qué es y lo esencial")
    lab_values: list[LabValue] = Field(default_factory=list)
    clinical: list[str] = Field(default_factory=list, description="Diagnósticos, antecedentes, síntomas")
    injuries: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list, description="- Nombre — dosis — frecuencia")
    supplements: list[str] = Field(default_factory=list)
    diet_previous: list[str] = Field(default_factory=list, description="Dieta/pauta anterior, resumida")
    training_previous: list[str] = Field(default_factory=list, description="Rutina anterior, resumida")
    other: list[str] = Field(default_factory=list, description="Lo relevante que no encaja arriba")
    alerts: list[str] = Field(
        default_factory=list,
        description="Lo que el coach debe ver SÍ O SÍ: valores muy fuera de rango, diagnósticos "
                    "que condicionan dieta/entreno, contraindicaciones escritas por un médico")

    _v_listas = field_validator(
        "summary", "clinical", "injuries", "medications", "supplements",
        "diet_previous", "training_previous", "other", "alerts", mode="before")(
        lambda cls, v: _lista(v))

    @field_validator("lab_values", mode="before")
    @classmethod
    def _labs(cls, v):
        if not isinstance(v, list):
            return []
        out = []
        for x in v:
            if isinstance(x, dict) and (x.get("marker") or x.get("name")):
                if "marker" not in x:
                    x = {**x, "marker": x.get("name")}
                out.append(x)
        return out


_SYSTEM = """Eres un dietista-entrenador experto leyendo un DOCUMENTO ADJUNTO de un cliente: \
puede ser una analítica de sangre/orina, un informe médico o de fisioterapia, una receta, una \
dieta o una rutina anteriores, un cuestionario de otro profesional, o cualquier otra cosa. \
Puede venir como PDF, fotos del móvil (varias fotos = un documento), Word, hoja de cálculo o \
texto. TRANSCRIBE lo que hay, fiel y completo, en el esquema. No interpretes clínicamente ni \
calcules nada; no inventes. Lo que no esté, vacío.

- document_kind: qué es. title: cómo se titula o de qué trata. document_date: su fecha.
- summary: 2-6 líneas con lo esencial, empezando por lo que condiciona dieta o entreno.
- lab_values: CADA marcador de una analítica con su valor, unidad, rango de referencia tal \
como lo imprime el laboratorio y flag (alto/bajo/normal según las marcas del informe: *, H, L, \
flechas, negrita; si no hay marca y hay rango, compara tú; si no puedes, desconocido). No te \
dejes ninguno: si el informe trae 40 marcadores, van los 40.
- clinical: diagnósticos, antecedentes, síntomas, recomendaciones escritas por el médico.
- injuries: lesiones, limitaciones de movimiento, indicaciones del fisio ("evitar sentadilla \
profunda 6 semanas").
- medications: "- Nombre — dosis — frecuencia". supplements: igual.
- diet_previous / training_previous: si el documento es una pauta anterior, resúmela en \
líneas cortas (estructura, cifras que declara, alimentos o ejercicios clave).
- other: lo relevante que no encaje arriba. Nada se pierde.
- alerts: SOLO lo que el coach debe ver sí o sí (valores claramente fuera de rango, \
diagnósticos que cambian la pauta, contraindicaciones firmadas por un médico). Sin alarmismo.

Formato: español, líneas cortas que empiezan por "- " en las listas de texto. Devuelve SOLO \
el JSON del esquema."""


def extract_attachment(documento, ai) -> AttachmentExtraction:
    """La IA lee el adjunto (cualquier formato). Lanza AIGenerationError si falla."""
    from app.config import settings

    user = (f"Lee el adjunto («{documento.nombre}», {documento.descripcion}) ENTERO y "
            "transcríbelo en el JSON del esquema. Si es una analítica, todos los marcadores.")
    return ai.read_document_json(
        model=settings.model_heavy, system=_SYSTEM, user=user, documento=documento,
        schema=AttachmentExtraction, temperature=0, max_tokens=6000,
    )


# ---------------------------------------------------------------- sidecar ----

def stem_de(nombre: str) -> str:
    """`adjunto_analitica_ab12cd34.pdf` → `analitica_ab12cd34` (clave estable
    del adjunto: sirve de marca en las notas y de nombre del sidecar)."""
    base = nombre.rsplit("/", 1)[-1]
    if base.startswith("adjunto_"):
        base = base[len("adjunto_"):]
    return base.rsplit(".", 1)[0] if "." in base else base


def sidecar_path(client_id: int, nombre: str) -> Path:
    from app.services.storage import client_dir

    return client_dir(client_id, "documents") / f"_adjunto_{stem_de(nombre)}.json"


def save_sidecar(client_id: int, nombre: str, ext: AttachmentExtraction, avisos: list[str] | None = None) -> None:
    datos = ext.model_dump()
    datos["file"] = nombre
    datos["avisos_lectura"] = list(avisos or [])
    datos["read_at"] = datetime.now(timezone.utc).isoformat()
    sidecar_path(client_id, nombre).write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")


def load_sidecars(client_id: int) -> list[dict]:
    """Todos los adjuntos LEÍDOS del cliente (los sidecars), más reciente primero."""
    from app.services.storage import client_dir

    folder = client_dir(client_id, "documents")
    out: list[dict] = []
    for p in folder.glob("_adjunto_*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            d.setdefault("file", p.name)
            out.append(d)
        except Exception:  # noqa: BLE001 — un sidecar roto no rompe la ficha
            continue
    return sorted(out, key=lambda d: d.get("read_at") or "", reverse=True)


def delete_sidecar(client_id: int, nombre: str) -> None:
    try:
        sidecar_path(client_id, nombre).unlink(missing_ok=True)
    except Exception:  # noqa: BLE001
        pass


# -------------------------------------------------------- fusión en ficha ----

def _linea_lab(lv: LabValue) -> str:
    partes = [lv.marker, lv.value]
    if lv.unit:
        partes[-1] = f"{lv.value} {lv.unit}"
    txt = " ".join(p for p in partes if p)
    extras = []
    if lv.flag in ("alto", "bajo"):
        extras.append(lv.flag.upper())
    if lv.reference:
        extras.append(f"ref {lv.reference}")
    return txt + (f" ({'; '.join(extras)})" if extras else "")


def lineas_de_analitica(ext: AttachmentExtraction) -> list[str]:
    """Compacta la analítica: fuera de rango, una línea por marcador; el resto,
    una sola línea agrupada (que la ficha no sea un volcado de laboratorio)."""
    if not ext.lab_values:
        return []
    fecha = f" ({ext.document_date})" if ext.document_date else ""
    fuera = [lv for lv in ext.lab_values if lv.flag in ("alto", "bajo")]
    dudosos = [lv for lv in ext.lab_values if lv.flag == "desconocido"]
    normales = [lv for lv in ext.lab_values if lv.flag == "normal"]
    out = [f"Analítica{fecha}: {len(ext.lab_values)} marcadores"]
    for lv in fuera:
        out.append("  · " + _linea_lab(lv))
    if dudosos:
        out.append("  · sin rango claro: " + "; ".join(_linea_lab(lv) for lv in dudosos[:12]))
    if normales:
        out.append("  · resto normal: " + ", ".join(lv.marker for lv in normales[:40]))
    return out


def bloques_para_ficha(ext: AttachmentExtraction, stem: str) -> dict[str, list[str]]:
    """Qué líneas van a qué columna de la ficha. La primera línea de cada bloque
    lleva la MARCA del adjunto (idempotencia)."""
    cab = MARCA.format(stem=stem)
    tipo = (ext.document_kind or "adjunto").replace("_", " ")
    fecha = f" · {ext.document_date}" if ext.document_date else ""
    titulo = f" · {ext.title}" if ext.title else ""
    destino: dict[str, list[str]] = {}

    med: list[str] = []
    med += lineas_de_analitica(ext)
    med += ext.clinical
    if ext.alerts:
        med += [f"⚠ {a}" for a in ext.alerts]
    if med:
        destino["medical_notes"] = [f"{cab} {tipo}{fecha}{titulo}"] + med
    if ext.injuries:
        destino["injuries_notes"] = [f"{cab} {tipo}{fecha}"] + ext.injuries
    if ext.medications:
        destino["medication_notes"] = [f"{cab} {tipo}{fecha}"] + ext.medications
    if ext.supplements:
        destino["current_supplements"] = [f"{cab} {tipo}{fecha}"] + ext.supplements
    if ext.training_previous:
        destino["sport_history"] = [f"{cab} rutina previa{fecha}"] + ext.training_previous
    otros = list(ext.diet_previous) + list(ext.other)
    if otros:
        destino["lifestyle_notes"] = [f"{cab} {tipo}{fecha}"] + (
            [f"Dieta previa: {x}" for x in ext.diet_previous] + list(ext.other))
    return destino


def _quitar_bloque(texto: str, stem: str) -> str:
    """Elimina el bloque de ESTE adjunto (si ya estaba) sin tocar el resto."""
    if not texto:
        return ""
    def _keep(m):
        return "" if m.group("stem") == stem else m.group(0)
    nuevo = _RE_BLOQUE.sub(_keep, texto + ("\n" if not texto.endswith("\n") else ""))
    return nuevo.strip("\n")


def _formatea(lineas: list[str]) -> str:
    out = []
    for i, ln in enumerate(lineas):
        ln = ln.rstrip()
        if not ln:
            continue
        if ln.startswith("  ·"):
            out.append(ln)                 # sublínea de la analítica
        elif ln.startswith("- "):
            out.append(ln)
        else:
            out.append("- " + ln)
    return "\n".join(out)


def merge_into_client(client, ext: AttachmentExtraction, nombre: str) -> list[str]:
    """Vuelca el adjunto en las notas de la ficha. Idempotente por adjunto
    (marca); NUNCA borra lo que ya había. Devuelve las columnas tocadas."""
    stem = stem_de(nombre)
    tocadas: list[str] = []
    for campo, lineas in bloques_para_ficha(ext, stem).items():
        actual = _quitar_bloque(getattr(client, campo, None) or "", stem)
        bloque = _formatea(lineas)
        nuevo = (actual + "\n" + bloque).strip("\n") if actual else bloque
        setattr(client, campo, nuevo)
        tocadas.append(campo)
    # Si el adjunto se relee y ya no aporta a una columna, el bloque viejo se va.
    for campo in ("medical_notes", "injuries_notes", "medication_notes",
                  "current_supplements", "sport_history", "lifestyle_notes"):
        if campo in tocadas:
            continue
        actual = getattr(client, campo, None) or ""
        limpio = _quitar_bloque(actual, stem)
        if limpio != actual.strip("\n"):
            setattr(client, campo, limpio or None)
    return tocadas


def remove_from_client(client, nombre: str) -> None:
    """Al borrar un adjunto, su bloque desaparece de la ficha."""
    stem = stem_de(nombre)
    for campo in ("medical_notes", "injuries_notes", "medication_notes",
                  "current_supplements", "sport_history", "lifestyle_notes"):
        actual = getattr(client, campo, None) or ""
        limpio = _quitar_bloque(actual, stem)
        if limpio != actual.strip("\n"):
            setattr(client, campo, limpio or None)


# ----------------------------------------------------- contexto para la IA ----

def attachment_context(client_id: int, *, max_chars: int = 2500) -> str | None:
    """Bloque de texto con los adjuntos LEÍDOS para el prompt de generación y
    el panel de supervisión: resumen, alertas y marcadores fuera de rango.
    None si no hay adjuntos leídos."""
    docs = load_sidecars(client_id)
    if not docs:
        return None
    lineas = ["ADJUNTOS DEL CLIENTE LEÍDOS (analíticas, informes, pautas previas):"]
    for d in docs:
        tipo = (d.get("document_kind") or "adjunto").replace("_", " ")
        fecha = f" ({d['document_date']})" if d.get("document_date") else ""
        lineas.append(f"· {tipo}{fecha}: " + " ".join(d.get("summary") or [])[:300])
        for a in (d.get("alerts") or [])[:5]:
            lineas.append(f"  ⚠ {a}")
        fuera = [lv for lv in (d.get("lab_values") or [])
                 if isinstance(lv, dict) and lv.get("flag") in ("alto", "bajo")]
        if fuera:
            lineas.append("  fuera de rango: " + "; ".join(
                f"{lv.get('marker')} {lv.get('value')} {lv.get('unit') or ''} ({lv.get('flag')})".strip()
                for lv in fuera[:15]))
        for x in (d.get("injuries") or [])[:4]:
            lineas.append(f"  lesión: {x}")
    txt = "\n".join(lineas)
    return txt[:max_chars]


def resumen_para_ui(d: dict) -> dict:
    """Lo que la tarjeta de documentos enseña de un adjunto leído."""
    labs = d.get("lab_values") or []
    fuera = [lv for lv in labs if isinstance(lv, dict) and lv.get("flag") in ("alto", "bajo")]
    return {
        "file": d.get("file"),
        "document_kind": d.get("document_kind"),
        "title": d.get("title"),
        "document_date": d.get("document_date"),
        "read_at": d.get("read_at"),
        "summary": d.get("summary") or [],
        "alerts": d.get("alerts") or [],
        "n_lab_values": len(labs),
        "out_of_range": [f"{lv.get('marker')}: {lv.get('value')} {lv.get('unit') or ''} ({lv.get('flag')})".strip()
                         for lv in fuera],
        "avisos_lectura": d.get("avisos_lectura") or [],
    }
