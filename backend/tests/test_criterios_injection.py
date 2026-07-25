"""Test de inyección del criterio del coach en la generación (hardening §7)."""
from __future__ import annotations

from app.services.ai.prompts import (
    criterios_reference,
    system_prompt_full,
    system_prompt_nutrition_only,
)


def test_criterios_reference_omite_pendientes():
    ref = criterios_reference()
    # Existe el archivo → hay contenido; y NUNCA filtra los huecos [PENDIENTE TONI].
    assert "[PENDIENTE TONI]" not in ref
    if ref:
        assert "CRITERIO DEL COACH" in ref


def test_system_prompt_incluye_criterio_si_existe():
    ref = criterios_reference()
    full = system_prompt_full()
    only = system_prompt_nutrition_only()
    # Siempre incluye base + metodología
    assert "nutrición" in full.lower()
    if ref:
        assert "CRITERIO DEL COACH" in full
        assert "CRITERIO DEL COACH" in only


def test_system_prompt_no_rompe_sin_criterio(monkeypatch):
    # Si el archivo no existe, el prompt se ensambla igual (sin bloque de criterio).
    monkeypatch.setattr("app.services.ai.prompts.criterios_reference", lambda: "")
    full = system_prompt_full()
    assert full and "CRITERIO DEL COACH" not in full
