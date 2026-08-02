"""Historial de versiones del plan + revert (hardening §4, cableado real).

Cada vez que el plan cambia (edición del coach en el editor, adaptación
quincenal, restauración), se guarda ANTES una instantánea completa de su
contenido (nutrición + entreno + educativo) en un sidecar JSON del cliente —
misma convención que el análisis de anamnesis: sin migración Alembic, y los
archivos `_*` no aparecen en la lista de documentos.

El coach puede listar el historial y RESTAURAR cualquier versión: la
restauración también snapshotea el estado actual primero, así nunca se pierde
nada (revert del revert incluido). Tope de versiones por plan para que el
sidecar no crezca sin límite.
"""
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from app.models import Plan
from app.services.storage import client_dir

# Últimas N versiones por plan. Cada edición real del coach genera una; 20
# cubre de sobra un mes de trabajo sobre el mismo plan.
MAX_VERSIONS = 20


def _sidecar(plan: Plan) -> Path:
    return client_dir(plan.client_id, "documents") / f"_plan_{plan.id}_history.json"


def _load(plan: Plan) -> list[dict]:
    p = _sidecar(plan)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []  # sidecar corrupto: el historial empieza de nuevo, nunca rompe la edición


def _summary(nutrition: dict | None) -> dict:
    """Resumen compacto para la lista (sin cargar el snapshot entero en la UI)."""
    nut = nutrition or {}
    macros = nut.get("macros") or {}
    return {
        "target_kcal": nut.get("target_kcal"),
        "protein_g": macros.get("protein_g"),
        "carbs_g": macros.get("carbs_g"),
        "fat_g": macros.get("fat_g"),
        "n_meals": len(nut.get("meals") or []),
    }


def snapshot_plan(plan: Plan, label: str) -> None:
    """Guarda el contenido ACTUAL del plan como una versión del historial.
    Llamar ANTES de mutarlo. Best-effort: un fallo de disco no debe tumbar
    la edición (el historial es una red de seguridad, no el dato primario)."""
    try:
        versions = _load(plan)
        versions.append({
            "at": datetime.now(timezone.utc).isoformat(),
            "label": label,
            "rev": (plan.nutrition_json or {}).get("rev") if isinstance(plan.nutrition_json, dict) else None,
            "summary": _summary(plan.nutrition_json if isinstance(plan.nutrition_json, dict) else None),
            "nutrition_json": copy.deepcopy(plan.nutrition_json),
            "training_json": copy.deepcopy(plan.training_json),
            "education_json": copy.deepcopy(plan.education_json),
        })
        _sidecar(plan).write_text(
            json.dumps(versions[-MAX_VERSIONS:], ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def list_history(plan: Plan) -> list[dict]:
    """Versiones del plan, la más reciente primero, SIN el contenido completo
    (solo metadatos + resumen). El índice devuelto es el que usa el revert."""
    versions = _load(plan)
    out = []
    for i, v in enumerate(versions):
        out.append({
            "index": i,
            "at": v.get("at"),
            "label": v.get("label") or "edición",
            "summary": v.get("summary") or {},
        })
    out.reverse()
    return out


def get_version(plan: Plan, index: int) -> dict | None:
    """Snapshot completo de una versión por su índice (para restaurar)."""
    versions = _load(plan)
    if 0 <= index < len(versions):
        return versions[index]
    return None
