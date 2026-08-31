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

<<<<<<< HEAD
# Lo que de verdad hace falta que corra: si esto se para, el ciclo entero se
# detiene (no se abren períodos, no hay transiciones de estado).
CRITICOS = ("daily_maintenance",)

# Nombre legible de cada trabajo y qué se pierde si deja de correr. Los no
# críticos pueden saltarse UNA vuelta sin consecuencias — por eso su margen es
# más ancho—, pero llevar días muertos no es saltarse una vuelta: un
# `push_reminders` caído tres días deja a TODOS los clientes sin un solo aviso
# durante media quincena, y nada lo decía porque solo se vigilaba el
# mantenimiento diario.
QUE_SE_PIERDE = {
    "daily_maintenance": ("el mantenimiento diario",
                          "los períodos y los recordatorios automáticos están parados"),
    "push_reminders": ("los recordatorios del portal",
                       "los clientes no reciben ningún aviso de registro"),
    "coach_digest": ("el resumen de avisos al móvil",
                     "no te llega nada al móvil aunque haya avisos"),
    "video_call_reminders": ("los recordatorios de videollamada",
                             "ni tú ni el cliente recibís el aviso de la cita"),
    "weekly_coach_summary": ("el resumen semanal del lunes",
                             "no sale el repaso de la semana"),
}
# Un trabajo NO crítico se avisa cuando lleva muerto varias vueltas, no una.
MARGEN_NO_CRITICO = 6
=======
# Lo que de verdad hace falta que corra: si esto se para, se avisa enseguida.
CRITICOS = ("daily_maintenance",)

# El resto SÍ puede saltarse una vuelta sin consecuencias (por eso no están en
# CRITICOS), pero "saltarse una vuelta" no es lo mismo que llevar días muerto:
# los recordatorios del cliente, el resumen del coach y los avisos de
# videollamada podían fallar indefinidamente sin que nadie se enterara. Con este
# margen mucho más ancho, una vuelta perdida no molesta y una parada real canta.
MARGEN_SECUNDARIOS = 8   # push cada 3 h → se avisa a las 24 h

# Nombres legibles para el aviso del panel (el coach no sabe qué es "coach_digest").
NOMBRES = {
    "daily_maintenance": "el mantenimiento diario",
    "push_reminders": "los recordatorios del cliente",
    "coach_digest": "tu resumen de pendientes",
    "video_call_reminders": "los avisos de videollamada",
    "weekly_coach_summary": "el resumen semanal",
}

# Entradas del sidecar que NO son trabajos programados: `record_job` se reutiliza
# para guardar la huella del resumen del coach (dedup), y sin excluirla se
# vigilaría como si fuera un automatismo parado.
NO_SON_TRABAJOS = ("coach_digest_huella",)
>>>>>>> origin/claude/tanda3-pendiente-de-tanda1


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

<<<<<<< HEAD
    def _horas_sin_exito(e: dict) -> int | None:
        exito = e.get("last_success_at")
=======
    def _horas_sin_exito(entrada: dict) -> float | None:
        """Horas desde el último final BUENO, o None si no se puede saber."""
        exito = entrada.get("last_success_at")
>>>>>>> origin/claude/tanda3-pendiente-de-tanda1
        if not exito:
            return None
        try:
            cuando = datetime.fromisoformat(exito)
        except ValueError:
            return None
        if cuando.tzinfo is None:
            cuando = cuando.replace(tzinfo=timezone.utc)
<<<<<<< HEAD
        return int((ahora - cuando).total_seconds() // 3600)

    # Los CRÍTICOS primero: si el mantenimiento diario está parado, eso es lo
    # que hay que contar, no que además falte un recordatorio.
    for nombre in list(CRITICOS) + [n for n in ESPERADO_HORAS if n not in CRITICOS]:
        e = datos.get(nombre)
        if not e:
            continue
        critico = nombre in CRITICOS
        etiqueta, consecuencia = QUE_SE_PIERDE.get(
            nombre, (f"el trabajo «{nombre}»", "algo automático no se está haciendo"))
        horas = _horas_sin_exito(e)
        margen = MARGEN if critico else MARGEN_NO_CRITICO
        limite_h = ESPERADO_HORAS[nombre] * margen

=======
        return (ahora - cuando).total_seconds() / 3600

    # 1) Los críticos, primero: si el mantenimiento diario se para, todo lo demás
    #    da igual. La ANTIGÜEDAD se mira ANTES que el "terminó con errores": si
    #    no, un trabajo que falló y además dejó de ejecutarse se quedaba
    #    eternamente en "terminó con errores" —que suena a que sigue corriendo—
    #    y el aviso no escalaba nunca a "lleva N horas sin ejecutarse".
    for nombre in CRITICOS:
        e = datos.get(nombre)
        if not e:
            continue
        horas = _horas_sin_exito(e)
        limite = ESPERADO_HORAS[nombre] * MARGEN
        if horas is None:
            return ("El mantenimiento diario no ha llegado a terminar nunca: "
                    "revisa el servidor.")
        if horas > limite:
            extra = ""
            if e.get("last_ok") is False:
                detalle = str(e.get("detail") or "")[:160]
                extra = f" Además, el último intento terminó con errores. {detalle}"
            return (f"El mantenimiento diario no se ejecuta desde hace {int(horas)} h: "
                    f"los períodos y los recordatorios automáticos están parados.{extra}")
>>>>>>> origin/claude/tanda3-pendiente-de-tanda1
        # La última ejecución terminó MAL (reventó entera, o se dejó clientes
        # por el camino): eso hay que decirlo hoy, no dentro de 36 h. Un fallo
        # por cliente suele ser determinista —sus datos—, así que ese cliente
        # se queda sin recordatorios ni transiciones día tras día.
        if e.get("last_ok") is False:
            detalle = str(e.get("detail") or "")[:160]
<<<<<<< HEAD
            # CUÁNTO lleva roto. Antes esta rama devolvía siempre la misma
            # frase suave y el aviso no escalaba nunca: un trabajo que llevaba
            # días fallando se leía igual que uno que falló una vez.
            desde = ""
            if horas is not None and horas > limite_h:
                desde = f" Lleva {horas} h sin completarse."
            elif horas is None:
                desde = " No ha llegado a completarse nunca."
            return (f"Falla {etiqueta}: {consecuencia}.{desde} {detalle}").strip()

        if horas is None:
            if critico:
                return (f"No ha llegado a terminar nunca {etiqueta}: "
                        "revisa el servidor.")
            continue
        if horas > limite_h:
            return (f"No se ejecuta {etiqueta} desde hace {horas} h: "
                    f"{consecuencia}.")
=======
            return ("El mantenimiento diario terminó con errores: hay clientes "
                    f"sin atender (sin recordatorios ni cambios de estado). {detalle}")

    # 2) Los secundarios: no se alarma por una vuelta perdida, pero llevar días
    #    muerto sí se canta. Antes NADIE los vigilaba: los recordatorios del
    #    cliente, el resumen del coach o los avisos de videollamada podían estar
    #    caídos indefinidamente y el panel seguía diciendo que todo iba bien.
    for nombre, esperado in ESPERADO_HORAS.items():
        if nombre in CRITICOS or nombre in NO_SON_TRABAJOS:
            continue
        e = datos.get(nombre)
        if not e:
            continue  # nunca ha corrido: puede que no aplique todavía
        horas = _horas_sin_exito(e)
        if horas is None or horas <= esperado * MARGEN_SECUNDARIOS:
            continue
        que = NOMBRES.get(nombre, nombre)
        return (f"Hace {int(horas)} h que no funciona {que}: "
                "revisa el servidor (los automatismos están a medias).")
>>>>>>> origin/claude/tanda3-pendiente-de-tanda1
    return None
