"""Emparejado suplementos del plan ⇄ productos de Recursos.

Un producto "cubre" un suplemento si sus nombres se solapan (normalizados, sin
tildes ni mayúsculas): "Creatina monohidrato" ⇄ "ESN Ultrapure Creatine" NO
casan por texto directo, pero "creatina" ⊂ título sí. Se usa en dos sitios:
- el portal, para destacar los productos que salen EN la planificación del
  cliente ("in_plan");
- las alertas del coach, para avisar de suplementos del plan SIN producto
  subido a Recursos (el cliente no los vería en su portal).
"""
from __future__ import annotations

import unicodedata

# Palabras vacías que no aportan al emparejado ("proteína de suero" ⇄ "whey").
_STOP = {"de", "del", "la", "el", "los", "las", "con", "y", "en", "para", "al",
         "monohidrato", "monohidratada", "micronizada", "capsulas", "cápsulas",
         "polvo", "gr", "g", "kg", "mg"}

# Sinónimos habituales castellano ⇄ inglés de suplementos.
_SYNONYMS = {
    "proteina": {"whey", "protein", "iso", "isolate", "caseina", "casein"},
    "creatina": {"creatine", "creapure"},
    "cafeina": {"caffeine"},
    "omega": {"omega3", "omega-3", "fish", "epa", "dha"},
    "magnesio": {"magnesium"},
    "vitamina": {"vitamin", "multivitaminico", "multivitamin"},
    "melatonina": {"melatonin"},
    "electrolitos": {"electrolytes", "hydration"},
    "glutamina": {"glutamine"},
    "citrulina": {"citrulline", "malato"},
    "beta": {"alanina", "alanine"},
    "ashwagandha": {"withania"},
    "colageno": {"collagen"},
    "zinc": {"zma"},
    "hierro": {"iron"},
}


def _norm_tokens(text: str | None) -> set[str]:
    if not text:
        return set()
    s = unicodedata.normalize("NFKD", text.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    tokens = {t for t in "".join(c if c.isalnum() else " " for c in s).split()
              if len(t) >= 3 and t not in _STOP}
    return tokens


def _expand(tokens: set[str]) -> set[str]:
    out = set(tokens)
    for t in tokens:
        for base, syns in _SYNONYMS.items():
            if t == base or t in syns:
                out.add(base)
                out |= syns
    return out


def product_covers(supplement_name: str, product_title: str) -> bool:
    """¿Este producto corresponde a este suplemento del plan?"""
    a = _expand(_norm_tokens(supplement_name))
    b = _expand(_norm_tokens(product_title))
    return bool(a & b)


def plan_supplement_names(nutrition_json: dict | None) -> list[str]:
    """Nombres de los suplementos de la nutrición del plan (si los hay)."""
    if not isinstance(nutrition_json, dict):
        return []
    out = []
    for s in nutrition_json.get("supplements") or []:
        name = (s.get("name") or "").strip() if isinstance(s, dict) else ""
        if name:
            out.append(name)
    return out


def match_products(supplements: list[str], product_titles: list[str]) -> dict:
    """Empareja suplementos y productos.

    Devuelve {"covered_titles": set de títulos de producto que salen en el plan,
    "missing": [suplementos del plan sin producto en Recursos]}."""
    covered_titles: set[str] = set()
    missing: list[str] = []
    for sup in supplements:
        hit = False
        for title in product_titles:
            if product_covers(sup, title):
                covered_titles.add(title)
                hit = True
        if not hit:
            missing.append(sup)
    return {"covered_titles": covered_titles, "missing": missing}
