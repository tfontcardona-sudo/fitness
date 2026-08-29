"""Salud de los AUTOMATISMOS: que se note cuando dejan de correr.

Los trabajos programados abren períodos, persiguen a quien no registra, cortan
las suscripciones de la oferta ya cobradas y avisan al coach. Si se paran, el
coach tiene que enterarse por el panel, no por el log del contenedor.
"""
import warnings
from datetime import datetime, timedelta, timezone

import pytest

warnings.filterwarnings("ignore")


@pytest.fixture()
def sidecar(tmp_path, monkeypatch):
    """Aísla el sidecar de estado en un directorio temporal."""
    from app.config import settings
    from app.services import job_state

    monkeypatch.setattr(settings, "storage_path", str(tmp_path))
    monkeypatch.setattr(settings, "scheduler_enabled", True)
    return job_state


def test_se_anota_cada_ejecucion_con_su_resultado(sidecar):
    sidecar.record_job("daily_maintenance", ok=True, detalle="3 períodos abiertos")
    estado = sidecar.estado_de_los_trabajos()["daily_maintenance"]
    assert estado["last_ok"] is True
    assert estado["fallos_seguidos"] == 0
    assert "períodos" in estado["detail"]

    sidecar.record_job("daily_maintenance", ok=False, detalle="OperationalError: x")
    estado = sidecar.estado_de_los_trabajos()["daily_maintenance"]
    assert estado["last_ok"] is False and estado["fallos_seguidos"] == 1
    # El último ÉXITO se conserva: es lo que decide si hay que alarmar.
    assert estado["last_success_at"]


def test_sin_datos_todavia_no_se_alarma(sidecar):
    """Un despliegue recién hecho no puede pintar una alerta roja."""
    assert sidecar.automatismos_parados() is None


def test_si_el_mantenimiento_lleva_dias_sin_correr_se_avisa(sidecar):
    sidecar.record_job("daily_maintenance", ok=True, detalle="ok")
    assert sidecar.automatismos_parados() is None

    # Se falsea el último éxito a hace tres días.
    import json

    ruta = sidecar._ruta()
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    hace3 = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    datos["daily_maintenance"]["last_success_at"] = hace3
    ruta.write_text(json.dumps(datos), encoding="utf-8")

    motivo = sidecar.automatismos_parados()
    assert motivo and "no se ejecuta" in motivo
    assert "72 h" in motivo or "71 h" in motivo


def test_el_scheduler_apagado_se_canta(sidecar, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "scheduler_enabled", False)
    motivo = sidecar.automatismos_parados()
    assert motivo and "apagados" in motivo


def test_un_fallo_al_anotar_no_rompe_el_trabajo(monkeypatch):
    """El registro es best-effort: si el disco falla, el job sigue su curso."""
    from app.services import job_state

    monkeypatch.setattr(job_state, "_ruta", lambda: (_ for _ in ()).throw(OSError("disco")))
    job_state.record_job("daily_maintenance", ok=True)   # no debe lanzar
