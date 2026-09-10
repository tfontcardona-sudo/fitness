"""El gasto REAL de Anthropic (Cost API), no la estimación.

El sistema siempre ha estimado lo que cuesta cada llamada: tokens de la
respuesta × precio de tarifa del modelo. Es una buena aproximación, pero es una
aproximación — y con ella el saldo que ve el coach nunca cuadra del todo con lo
que le factura Anthropic.

Anthropic publica el COSTE por su Cost API de administración:

    GET https://api.anthropic.com/v1/organizations/cost_report

Requiere una clave de ADMINISTRACIÓN (`sk-ant-admin…`, `ANTHROPIC_ADMIN_KEY`),
distinta de la que llama al modelo; sin ella este módulo se apaga solo y el
sistema sigue con la estimación de siempre.

⚠️ Lo que NO existe: Anthropic no publica el SALDO de créditos ni las recargas.
Por eso la recarga la sigue confirmando el coach (un toque, con el importe de la
última ya puesto) y lo que el sistema automatiza es la resta: saldo = lo pagado
− el gasto REAL desde entonces.

Sin SDK a propósito: estos endpoints son solo HTTP crudo (no están en las
librerías), y el proyecto ya usa `httpx` para integraciones así.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.config import settings

log = logging.getLogger("app.ai_cost")

BASE = "https://api.anthropic.com/v1/organizations"
_TIMEOUT = 20.0
# Anthropic recomienda no pasar de una consulta por minuto de forma sostenida.
_MIN_SEGUNDOS_ENTRE_LECTURAS = 60.0
# La ventana diaria admite como mucho 31 buckets por página.
_MAX_DIAS = 31

_ultima_lectura: dict[str, object] = {"at": None, "valor": None}


class CostReportError(RuntimeError):
    """No se pudo leer el informe de coste (sin clave, sin red, credencial mala)."""


def disponible() -> bool:
    """¿Hay clave de administración configurada?"""
    return bool((settings.anthropic_admin_key or "").strip())


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _a_usd(valor) -> float:
    """La Cost API devuelve importes como cadena decimal. Nunca lanza."""
    try:
        return float(valor)
    except (TypeError, ValueError):
        return 0.0


def coste_desde(desde: datetime, *, hasta: datetime | None = None) -> float:
    """Dólares gastados en la organización entre `desde` y ahora.

    Suma todos los tramos de coste de todos los días del rango. Lanza
    `CostReportError` si no hay clave o la consulta falla: quien llama decide si
    se queda con la estimación (que es lo que hacen todos los llamadores).
    """
    if not disponible():
        raise CostReportError("Sin clave de administración de Anthropic")
    fin = hasta or datetime.now(timezone.utc)
    if desde.tzinfo is None:
        desde = desde.replace(tzinfo=timezone.utc)
    # El informe es DIARIO: se pide desde el principio del día de `desde`.
    inicio = desde.astimezone(timezone.utc).replace(hour=0, minute=0, second=0,
                                                    microsecond=0)
    if (fin - inicio) > timedelta(days=_MAX_DIAS):
        inicio = fin - timedelta(days=_MAX_DIAS)

    import httpx

    total = 0.0
    pagina: str | None = None
    cabeceras = {
        "x-api-key": (settings.anthropic_admin_key or "").strip(),
        "anthropic-version": "2023-06-01",
        "User-Agent": "DQR-Asesorias/1.0",
    }
    try:
        with httpx.Client(timeout=_TIMEOUT) as cli:
            for _ in range(10):  # tope de páginas: nunca un bucle infinito
                params: dict[str, str] = {
                    "starting_at": _iso(inicio), "ending_at": _iso(fin)}
                if pagina:
                    params["page"] = pagina
                resp = cli.get(f"{BASE}/cost_report", params=params, headers=cabeceras)
                if resp.status_code in (401, 403):
                    raise CostReportError(
                        "La clave de administración no tiene acceso al informe de coste")
                resp.raise_for_status()
                cuerpo = resp.json()
                for bucket in cuerpo.get("data") or []:
                    for linea in bucket.get("results") or []:
                        total += _a_usd(linea.get("amount"))
                if not cuerpo.get("has_more"):
                    break
                pagina = cuerpo.get("next_page")
                if not pagina:
                    break
    except CostReportError:
        raise
    except Exception as exc:  # noqa: BLE001 — red, JSON raro, 5xx de Anthropic
        raise CostReportError(f"No se pudo leer el informe de coste: {exc}") from exc
    return round(total, 4)


def refrescar_gasto_real(db, *, forzar: bool = False) -> float | None:
    """Pone al día `spent_real_usd` con lo que Anthropic dice que se ha gastado
    DESDE LA ÚLTIMA RECARGA. Devuelve la cifra, o None si no se pudo leer.

    Se estrangula a una lectura por minuto (lo que recomienda Anthropic): la
    página de créditos puede pedirlo en cada carga sin abusar del informe.
    """
    if not disponible():
        return None
    ahora = datetime.now(timezone.utc)
    ultima = _ultima_lectura.get("at")
    if (not forzar and isinstance(ultima, datetime)
            and (ahora - ultima).total_seconds() < _MIN_SEGUNDOS_ENTRE_LECTURAS):
        return _ultima_lectura.get("valor")  # type: ignore[return-value]

    from app.services.ai_credit import get_state

    state = get_state(db)
    desde = state.spent_real_desde or state.updated_at or (ahora - timedelta(days=_MAX_DIAS))
    try:
        total = coste_desde(desde, hasta=ahora)
    except CostReportError as exc:
        log.info("Informe de coste no disponible: %s", exc)
        _ultima_lectura["at"] = ahora
        _ultima_lectura["valor"] = None
        return None
    state.spent_real_usd = total
    state.spent_real_at = ahora
    if state.spent_real_desde is None:
        state.spent_real_desde = desde
    db.commit()
    _ultima_lectura["at"] = ahora
    _ultima_lectura["valor"] = total
    return total


def _reset_estrangulador() -> None:
    """Solo para tests: olvida la última lectura."""
    _ultima_lectura["at"] = None
    _ultima_lectura["valor"] = None
