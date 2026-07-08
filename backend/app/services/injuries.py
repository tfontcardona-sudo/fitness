"""Traduce las lesiones del cliente (texto libre de la anamnesis) a las
etiquetas de contraindicación articular del catálogo de ejercicios
(`VALID_CONTRA`), para que el filtro determinista y el guardrail de
entrenamiento excluyan de verdad los ejercicios peligrosos por lesión.

Respeta las negaciones y lo ya resuelto igual que el clasificador clínico del
frontend: "Sin lesión de hombro" o "molestia de rodilla ya resuelta" NO generan
contraindicación; "hombro, no resuelta" SÍ.
"""
from __future__ import annotations

import re
import unicodedata

# Etiquetas válidas (deben coincidir con seeds/exercises_data.VALID_CONTRA).
VALID_CONTRA = {"hombro", "codo", "muneca", "lumbar", "rodilla", "cadera", "cuello", "tobillo"}

# Palabras (ya normalizadas: minúsculas y sin acentos) que apuntan a cada zona.
_KEYWORDS: dict[str, tuple[str, ...]] = {
    "hombro": ("hombro", "manguito", "rotador", "subacromial", "supraespinoso",
               "deltoid", "acromio", "escapula", "clavicula"),
    "codo": ("codo", "epicondil", "epitrocle", "epitroclea"),
    "muneca": ("muneca", "carpo", "carpian", "tunel del carpo"),
    "lumbar": ("lumbar", "lumbago", "lumbalg", "espalda baja", "zona baja",
               "hernia", "protrus", "ciatic", "discal", "\bdisco\b", "sacro",
               "espondil", "\bl4\b", "\bl5\b", "\bs1\b", "escoliosis"),
    "rodilla": ("rodilla", "menisco", "cruzado", "\blca\b", "\blcp\b", "\blcl\b",
                "\blcm\b", "rotul", "patel", "condromalac"),
    "cadera": ("cadera", "psoas", "femoroacetabular", "labrum", "coxal",
               "gluteo medio"),
    "cuello": ("cuello", "cervical", "\bc5\b", "\bc6\b", "\bc7\b"),
    "tobillo": ("tobillo", "aquiles", "esguince", "peroneo", "fascit", "fascia plantar"),
}

_BULLET = re.compile(r"^[\s\-•*·]+")
_NEG_START = re.compile(r"^(no|sin|ning[uú]n[oa]?|nunca|jam[aá]s|ausencia)\b", re.I)
_RESOLVED = re.compile(r"\bresuelt[oa]s?\b|\bsuperad[oa]s?\b|\brecuperad[oa]s?\b|\bde la infancia\b", re.I)
_NOT_RESOLVED = re.compile(r"\bno\s+(resuelt|superad|recuperad)", re.I)


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").lower()


def injury_contra_tags(*notes: str | None) -> set[str]:
    """Conjunto de zonas contraindicadas a partir de una o más notas de lesión.

    Procesa línea a línea (la anamnesis viene en puntos). Ignora líneas negadas
    ("Sin…") o ya resueltas (salvo "no resuelta")."""
    tags: set[str] = set()
    for note in notes:
        if not note:
            continue
        for raw in note.splitlines():
            core = _BULLET.sub("", raw).strip()
            if not core:
                continue
            if _NEG_START.match(core):
                continue
            if _RESOLVED.search(core) and not _NOT_RESOLVED.search(core):
                continue
            norm = _norm(core)
            for tag, kws in _KEYWORDS.items():
                for kw in kws:
                    hit = re.search(kw, norm) if "\\b" in kw else (kw in norm)
                    if hit:
                        tags.add(tag)
                        break
    return tags & VALID_CONTRA
