"""Lecciones aprendidas de las EDICIONES del coach (§13 en vivo).

Cada vez que el coach corrige un plan generado, el PATCH ya guarda el cambio
clasificado en `plan_edits` (services/continuous_learning.py). Este módulo
cierra el círculo: destila esas correcciones en LECCIONES cualitativas cortas
y las inyecta en el prompt de generación — cada plan nuevo nace sabiendo lo
que el coach corrigió en los anteriores.

Reglas de seguridad (innegociables):
- Las lecciones son CUALITATIVAS: estilo, selección de alimentos/ejercicios,
  estructura, redacción. NUNCA cifras de kcal/macros — eso lo calcula el
  backend (metrics.py) y la IA no calcula.
- La destilación usa el modelo LIGERO y es best-effort: si falla, se queda la
  versión anterior de las lecciones y no rompe nada.
- El coach puede verlas y regenerarlas desde el panel (transparencia: el
  sistema no aprende "a escondidas").

El resultado vive en un sidecar JSON (storage/brand/_coach_lessons.json), sin
migración, y se refresca solo cuando hay suficientes ediciones nuevas.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Plan, PlanEdit

_log = logging.getLogger("app.coach_lessons")

# Umbral de ediciones NUEVAS desde la última destilación para re-destilar.
REFRESH_MIN_NEW_EDITS = 5
# Mínimo de ediciones totales para que haya algo que aprender.
MIN_EDITS = 5
# Tope de ediciones que se le enseñan al modelo (las más recientes).
MAX_EDITS_FOR_PROMPT = 120
# Tope del bloque inyectado en el prompt de generación.
MAX_BLOCK_CHARS = 1600


class LessonsOutput(BaseModel):
    """Salida estructurada de la destilación."""

    lessons: list[str] = Field(min_length=1, max_length=8)


def _sidecar_path() -> Path:
    from app.services.storage import storage_root

    d = storage_root() / "brand"
    d.mkdir(parents=True, exist_ok=True)
    return d / "_coach_lessons.json"


def load_lessons() -> dict:
    """Contenido actual del sidecar ({} si no existe o está corrupto)."""
    try:
        p = _sidecar_path()
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — un sidecar roto no rompe la generación
        pass
    return {}


def lessons_reference() -> str:
    """Bloque de LECCIONES para el prompt de generación ('' si no hay).
    Se añade al user prompt (no al system): así no invalida la caché del
    system prompt y puede cambiar entre generaciones."""
    data = load_lessons()
    lessons = [x for x in (data.get("lessons") or []) if isinstance(x, str) and x.strip()]
    if not lessons:
        return ""
    body = "\n".join(f"- {x.strip()}" for x in lessons)
    block = (
        "\n\nLECCIONES DEL COACH (aprendidas de sus correcciones a planes "
        "anteriores; aplícalas SIN cambiar ningún número del contrato):\n" + body
    )
    return block[:MAX_BLOCK_CHARS]


def _recent_edits(db: Session) -> list[tuple[PlanEdit, str | None]]:
    filas = db.execute(
        select(PlanEdit, Plan.goal_type)
        .join(Plan, Plan.id == PlanEdit.plan_id)
        .order_by(PlanEdit.id.desc())
        .limit(MAX_EDITS_FOR_PROMPT)
    ).all()
    return [(pe, goal) for pe, goal in filas]


def distill_lessons(db: Session, ai=None) -> dict:
    """Destila las ediciones registradas en 3-8 lecciones cortas (IA ligera)
    y las persiste en el sidecar. Devuelve el sidecar resultante.

    `ai` inyectable (tests). Nunca lanza hacia el caller del scheduler; los
    errores del endpoint del panel sí se propagan para que el coach los vea.
    """
    filas = _recent_edits(db)
    if len(filas) < MIN_EDITS:
        return {"skipped": f"solo {len(filas)} ediciones (mínimo {MIN_EDITS})",
                **load_lessons()}

    # Muestra agrupada por categoría (recorta ruido y tokens).
    por_categoria: dict[str, list[str]] = {}
    max_id = 0
    for pe, goal in filas:
        max_id = max(max_id, pe.id)
        nota = (pe.note or "").strip()
        if not nota:
            continue
        etiqueta = f"[{goal or 'sin objetivo'}] {nota}"
        por_categoria.setdefault(pe.category or "otro", [])
        if len(por_categoria[pe.category or "otro"]) < 15:
            por_categoria[pe.category or "otro"].append(etiqueta)

    lineas = []
    for cat, notas in sorted(por_categoria.items()):
        lineas.append(f"{cat} ({len(notas)} ejemplos):")
        lineas.extend(f"  · {n}" for n in notas)
    corpus = "\n".join(lineas)

    from app.config import settings

    if ai is None:
        from app.services.ai.client import AIClient

        ai = AIClient()
    system = (
        "Eres el asistente de un coach de fitness. Vas a leer CORRECCIONES que "
        "el coach hizo a mano sobre planes generados automáticamente, y debes "
        "destilarlas en LECCIONES generales para que los planes futuros salgan "
        "como a él le gustan.\n"
        "Reglas estrictas:\n"
        "- De 3 a 8 lecciones, en castellano, cada una de UNA frase (≤160 caracteres).\n"
        "- Solo lecciones que GENERALICEN un patrón repetido (≥2 correcciones); "
        "ignora cambios puntuales de un solo cliente.\n"
        "- CUALITATIVAS: preferencias de alimentos/ejercicios, estructura, horarios, "
        "estilo de redacción. PROHIBIDO dictar cifras de kcal, gramos de macros o "
        "porcentajes: esos números los calcula el sistema, no tú.\n"
        "- Nada de datos personales de clientes (sin nombres).\n"
        "Responde SOLO con JSON: {\"lessons\": [\"…\", …]}"
    )
    user = f"CORRECCIONES DEL COACH (agrupadas por tipo):\n{corpus}"
    out = ai.generate_json(model=settings.model_light, system=system, user=user,
                           schema=LessonsOutput, temperature=0, max_tokens=800)

    # Filtro determinista de seguridad: fuera lecciones con cifras de kcal/g
    # (por si el modelo se salta la regla) y tope de longitud.
    import re

    limpias = []
    for lx in out.lessons:
        s = lx.strip()
        if not s:
            continue
        if re.search(r"\d+\s*(kcal|calor[ií]as|g\b|gramos|%)", s, re.IGNORECASE):
            continue
        limpias.append(s[:200])
    if not limpias:
        # El filtro vetó TODO lo devuelto: no se pisa el sidecar (se
        # conservan las lecciones buenas anteriores) ni se avanza
        # last_edit_id — el siguiente refresco lo reintenta.
        return {"skipped": "la IA no produjo lecciones válidas (todas con cifras)",
                **load_lessons()}
    data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_edits": len(filas),
        "last_edit_id": max_id,
        "lessons": limpias,
    }
    _sidecar_path().write_text(json.dumps(data, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    return data


# ----------------------------------------------------------- vetos a la IA ----
# Memoria de VETOS del sistema a la IA (guardrails/Revisor 0/contrato): lo que
# el validador tuvo que frenar o corregir en generaciones anteriores se
# recuerda y, si se REPITE, se inyecta en el prompt para que la IA no tropiece
# dos veces con la misma piedra. Cualitativo: el texto del veto, nunca cifras
# nuevas (los números siguen viniendo del contrato del backend).

MAX_VETOS = 12
_VETOS_BLOCK_CHARS = 900


def _vetos_path() -> Path:
    from app.services.storage import storage_root

    d = storage_root() / "brand"
    d.mkdir(parents=True, exist_ok=True)
    return d / "_ai_vetos.json"


def _sin_cifras(texto: str) -> str:
    """Deja el TIPO de error sin un solo dato del cliente.

    Los vetos vienen con números suyos ("kcal objetivo 1450 por debajo del
    mínimo 1600", "proteína 120 g < mínimo 144 g"). Como estas advertencias se
    inyectan en la generación de TODOS los clientes, no pueden llevar cifras:
    ni las de otro cliente ni ninguna, porque los números los pone el backend
    y la IA no calcula. Se queda la forma del problema, que es lo útil.
    """
    import re as _re

    t = (texto or "")
    # Familias que por naturaleza llevan datos del cliente (su alergia, el
    # alimento concreto): se reducen a la LECCIÓN, sin el dato.
    bajo = t.lower()
    if "alérgeno" in bajo or "alergeno" in bajo:
        return "violation: se coló un alimento con un alérgeno declarado"
    if "aversión" in bajo or "aversion" in bajo or "no tolera" in bajo:
        return "violation: se coló un alimento que el cliente rechaza"
    # El texto REAL del guardrail es «restricción 'vegano' violada: slot 2 …»:
    # no lleva la palabra "patrón" por ninguna parte, así que esta rama no se
    # activaba NUNCA y la frase caía al limpiador genérico, que se lleva los
    # nombres entrecomillados y las cifras y deja un muñón —"restricción
    # violada: slot ' contiene '"— inyectado en la generación de todos los
    # demás clientes.
    if ("patrón" in bajo or "patron dietético" in bajo
            or "restricción" in bajo or "restriccion" in bajo):
        return "violation: se coló un alimento fuera del patrón dietético"
    if "contraindic" in bajo:
        return "violation: se coló un ejercicio contraindicado"
    # Fuera nombres entrecomillados (alimentos, ejercicios) y cifras.
    t = _re.sub(r"[«\"'][^»\"']*[»\"']", "", t)
    t = _re.sub(r"\d+(?:[.,]\d+)?\s*(?:%|g/kg|kcal|g|kg|min|h)?", "", t)
    # Paréntesis que se quedan sin contenido útil tras quitar las cifras
    # ("(max BMR/)", "(objetivo del backend: )").
    t = _re.sub(r"\([^)]*[:/·,;-]\s*\)", "", t)
    t = _re.sub(r"\(\s*\)", "", t)
    t = _re.sub(r"\([^)\d]*\)", "", t)   # "(opción del slot )" y similares
    t = _re.sub(r"\s{2,}", " ", t)
    t = _re.sub(r"\s+([,.;:])", r"\1", t)
    return t.strip(" ·-,;:").strip()


def record_ai_vetos(flags: list[str]) -> None:
    """Anota los vetos/correcciones de una generación (best-effort, nunca lanza).

    Se guarda el TIPO de veto, nunca las cifras del cliente: estas advertencias
    acaban en el prompt de otras generaciones."""
    try:
        # `seguridad:` y `cuadre:` TAMBIÉN son vetos. Desde que se repara ANTES
        # de juzgar, los dos tropiezos más repetidos de la IA —colar un alérgeno
        # en el banco y no dar en el objetivo de la toma— ya no llegan a
        # `check_meal_options`, así que dejaron de emitir `violation:` y la
        # memoria dejó de aprenderlos: el prompt no advertía de ellos, el modelo
        # los repetía y el backend seguía pagando por arreglarlos.
        interesantes = [
            _sin_cifras(f) for f in (flags or [])
            if isinstance(f, str) and f.startswith(
                ("violation:", "contrato:", "núcleo:", "seguridad:", "cuadre:"))
        ]
        interesantes = [f for f in interesantes if len(f) > 12]
        if not interesantes:
            return
        p = _vetos_path()
        data = {}
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                data = {}
        conteo: dict[str, int] = dict(data.get("conteo") or {})
        for f in interesantes:
            clave = f.strip()[:180]
            conteo[clave] = int(conteo.get(clave) or 0) + 1
        top = dict(sorted(conteo.items(), key=lambda kv: -kv[1])[:60])
        p.write_text(json.dumps({
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "conteo": top,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:  # noqa: BLE001 — la memoria de vetos nunca rompe nada
        pass


def vetos_reference() -> str:
    """Bloque para el prompt con los tropiezos REPETIDOS ('' si no hay)."""
    try:
        p = _vetos_path()
        if not p.exists():
            return ""
        conteo = (json.loads(p.read_text(encoding="utf-8")) or {}).get("conteo") or {}
        # SANEAR TAMBIÉN AL LEER. El filtro se aplicaba solo al escribir, así
        # que cualquier clave que ya estuviera en el sidecar —guardada antes
        # de que el filtro existiera, o metida a mano— viajaba tal cual al
        # prompt de TODOS los clientes, con las cifras y los alimentos de uno
        # solo. El fichero es de larga vida: la memoria de vetos se acumula
        # durante meses, y el saneado de entrada no lo alcanza nunca.
        # Re-agrupa, además, las claves que colapsan en la misma lección.
        limpio: dict[str, int] = {}
        for clave, veces in conteo.items():
            if not isinstance(clave, str):
                continue
            k = _sin_cifras(clave).strip()[:180]
            if len(k) <= 12:
                continue
            limpio[k] = limpio.get(k, 0) + int(veces or 0)
        repetidos = sorted(
            ((k, v) for k, v in limpio.items() if v >= 2),
            key=lambda kv: -kv[1],
        )
        if not repetidos:
            return ""
        body = "\n".join(f"- {k}" for k, _ in repetidos[:MAX_VETOS])
        block = (
            "\n\nERRORES QUE EL VALIDADOR YA TUVO QUE FRENAR EN PLANES "
            "ANTERIORES (no los repitas):\n" + body
        )
        return block[:_VETOS_BLOCK_CHARS]
    except Exception:  # noqa: BLE001
        return ""


def maybe_refresh(db: Session) -> dict | None:
    """Re-destila SOLO si hay suficientes ediciones nuevas desde la última vez.
    Pensado para el mantenimiento diario: best-effort, nunca lanza."""
    try:
        actual = load_lessons()
        ultimo = int(actual.get("last_edit_id") or 0)
        max_id = int(db.scalar(select(func.max(PlanEdit.id))) or 0)
        nuevas = db.scalar(
            select(func.count()).select_from(PlanEdit).where(PlanEdit.id > ultimo)
        ) or 0
        if max_id <= ultimo or nuevas < REFRESH_MIN_NEW_EDITS:
            return None
        return distill_lessons(db)
    except Exception as exc:  # noqa: BLE001 — el aprendizaje nunca rompe el ciclo
        _log.warning("Refresco de lecciones del coach fallido: %s", exc)
        return None
