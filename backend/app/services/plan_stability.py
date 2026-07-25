"""Estabilidad y determinismo del plan (hardening §11 + §14).

- `stability_score`: si el mismo cliente produce dos planes distintos, el sistema
  no está decidiendo, está sorteando. Compara dos generaciones (seeds distintas)
  eje a eje y devuelve 0-1 (1 = idénticas). Alimenta el ICP (§11).
- `PROMPT_VERSION` / `MODEL_PINS`: versión de prompts y modelo pinneado por
  versión, para que cada plan guarde con QUÉ se generó (§14). Sin esto no se
  diagnostica nada.
- `PlanTelemetry`: tiempo, coste, iteraciones de reparación y veredictos, por plan.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Versión de los prompts (subir al tocar prompts.py de forma que cambie la salida).
PROMPT_VERSION = "hardening-v2.0"


def _macros_vec(nut: dict) -> tuple[float, float, float, float]:
    m = (nut or {}).get("macros") or {}
    return (
        float((nut or {}).get("target_kcal") or 0),
        float(m.get("protein_g") or 0),
        float(m.get("carbs_g") or 0),
        float(m.get("fat_g") or 0),
    )


def stability_score(nut_a: dict, nut_b: dict) -> float:
    """0-1: cuán parecidas son dos generaciones del MISMO cliente (kcal + macros).
    1 = idénticas; baja con la desviación relativa media por eje."""
    a = _macros_vec(nut_a)
    b = _macros_vec(nut_b)
    devs = []
    for va, vb in zip(a, b):
        base = max(abs(va), abs(vb), 1.0)
        devs.append(abs(va - vb) / base)
    mean_dev = sum(devs) / len(devs)
    return round(max(0.0, 1.0 - mean_dev), 3)


@dataclass
class PlanTelemetry:
    """Telemetría por plan (§14): para diagnosticar y comparar versiones."""

    prompt_version: str = PROMPT_VERSION
    model: str = ""
    generation_ms: int = 0
    cost_usd: float = 0.0
    repair_iterations: int = 0
    panel_color: str = ""
    icp: float = 0.0
    stability: float | None = None
    verdicts: dict = field(default_factory=dict)   # {reviewer: veredicto}

    def to_json(self) -> dict:
        return {
            "prompt_version": self.prompt_version, "model": self.model,
            "generation_ms": self.generation_ms, "cost_usd": round(self.cost_usd, 4),
            "repair_iterations": self.repair_iterations, "panel_color": self.panel_color,
            "icp": self.icp, "stability": self.stability, "verdicts": self.verdicts,
        }
