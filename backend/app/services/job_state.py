"""Salud de los AUTOMATISMOS: cuándo corrió cada trabajo y si salió bien.

Los trabajos programados (mantenimiento diario, recordatorios push, resumen del
coach, avisos de videollamada, resumen semanal) son los que abren períodos,
persiguen a los clientes que no registran, cortan las suscripciones de la
oferta ya cobradas y avisan al coach. Si dejan de ejecutarse —el scheduler
apagado, un fallo repetido, el contenedor reiniciándose— hasta ahora NADIE se
enteraba: el error solo iba al log del contenedor y el coach seguía creyendo
que el sistema trabajaba por él.

Aquí se anota el resultado de cada ejecución en un sidecar JSON (sin migración)
y `automatismos_parados()` dice si hace demasiado que no corre lo importante,
para que el panel lo cante como una alerta más.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

_log = logging.getLogger("app.jobs")

# Cada cuánto DEBERÍA correr cada trabajo, y cuánto margen damos antes de
# considerar que algo va mal (el margen cubre un reinicio o un despliegue).
ESPERADO_HORAS = {
    "daily_maintenance": 24,
    "push_reminders": 3,
    "coach_digest": 3,
    "video_call_reminders": 1,
    "weekly_coach_summary": 24 * 7,
}
MARGEN = 1.5   # 24 h → se avisa a las 36 h

# Lo que de verdad hace falta que corra: el resto son recordatorios que pueden
# saltarse una vuelta sin consecuencias.
CRITICOS = ("daily_maintenance",)


def _ruta() -> Path:
    from app.services.storage import storage_root

    d = storage_root() / "brand"
    d.mkdir(parents=True, exist_ok=True)
    return d / "_jobs_state.json"


def _leer() -> dict:
    try:
        p = _ruta()
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — un sidecar roto no puede romper un job
        pass
    return {}


def record_job(nombre: str, *, ok: bool, detalle: str = "") -> None:
    """Anota el resultado de una ejecución. Best-effort: nunca lanza."""
    try:
        datos = _leer()
        ahora = datetime.now(timezone.utc).isoformat()
        entrada = datos.get(nombre) or {}
        entrada["last_run_at"] = ahora
        entrada["last_ok"] = bool(ok)
        entrada["detail"] = (detalle or "")[:300]
        if ok:
            entrada["last_success_at"] = ahora
            entrada["fallos_seguidos"] = 0
        else:
            entrada["fallos_seguidos"] = int(entrada.get("fallos_seguidos") or 0) + 1
        datos[nombre] = entrada
        _ruta().write_text(json.dumps(datos, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        _log.warning("no se pudo anotar el estado del trabajo %s: %s", nombre, exc)


def estado_de_los_trabajos() -> dict:
    """Lo anotado hasta ahora, para enseñarlo tal cual en el panel."""
    return _leer()


def automatismos_parados(ahora: datetime | None = None) -> str | None:
    """Motivo por el que los automatismos NO están funcionando, o None si van.

    Devuelve una frase para el coach, no un código: es lo que verá en el panel.
    """
    from app.config import settings

    if not settings.scheduler_enabled:
        return ("Los automatismos están apagados en el servidor "
                "(SCHEDULER_ENABLED): no se abren períodos ni salen recordatorios.")
    datos = _leer()
    if not datos:
        # Aún no ha corrido nada desde que existe el registro: sin datos no se
        # alarma (un despliegue reciente es lo normal).
        return None
    ahora = ahora or datetime.now(timezone.utc)
    for nombre in CRITICOS:
        e = datos.get(nombre)
        if not e:
            continue
        exito = e.get("last_success_at")
        if not exito:
            return ("El mantenimiento diario no ha llegado a terminar nunca: "
                    "revisa el servidor.")
        try:
            cuando = datetime.fromisoformat(exito)
        except ValueError:
            continue
        if cuando.tzinfo is None:
            cuando = cuando.replace(tzinfo=timezone.utc)
        limite = timedelta(hours=ESPERADO_HORAS[nombre] * MARGEN)
        if ahora - cuando > limite:
            horas = int((ahora - cuando).total_seconds() // 3600)
            return (f"El mantenimiento diario no se ejecuta desde hace {horas} h: "
                    "los períodos y los recordatorios automáticos están parados.")
    return None
