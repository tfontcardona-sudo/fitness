"""Créditos de la API de Anthropic — contabilidad local (fila única).

Anthropic NO expone el SALDO de créditos por API (sí el COSTE: ver
`services/ai_cost_report.py`), así que el saldo se lleva en local: el coach
confirma de un toque lo que ha pagado al recargar y el sistema resta lo
gastado desde entonces — el gasto REAL de Anthropic si hay clave de
administración, o la estimación por tokens (respuesta × precio de tarifa) si
no la hay.

Y cuando el crédito se acaba de verdad no hay que adivinarlo: la propia API lo
dice («credit balance is too low»). Ese error sella `sin_credito_desde`, que
enciende el aviso del panel y se apaga SOLO en cuanto una llamada vuelve a
funcionar.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AiCreditState

RECHARGE_URL = "https://console.anthropic.com/settings/billing"

# ------------------------------------------------------- en qué se gasta ----
# PARA QUÉ era cada llamada. Sin esto el coach ve "este mes 14 $" y no puede
# hacer nada con ese dato: si se le fue en generar planes, en leer anamnesis o
# en el panel de revisión son tres conclusiones distintas.
PURPOSES: dict[str, str] = {
    "plan": "Generar la planificación",
    "comidas": "Elegir las comidas",
    "educativo": "Contenido educativo",
    "anamnesis": "Leer la anamnesis",
    "adjunto": "Leer un adjunto",
    "documento": "Leer un plan de fuera",
    "revision": "Panel de revisión",
    "feedback": "Informe quincenal",
    "objetivo": "Análisis de objetivo",
    "lecciones": "Aprender de tus correcciones",
    "whatsapp": "Mensajes de WhatsApp",
    "otro": "Otras llamadas",
}


def etiqueta_de_proposito(clave: str | None) -> str:
    return PURPOSES.get(clave or "otro", PURPOSES["otro"])


# El propósito viaja por CONTEXTO, no por parámetro: `generate_json` se llama
# desde decenas de sitios y encadenar un argumento por todos ellos era la forma
# segura de que a alguno se le olvidara y el apunte saliera sin etiqueta.
_PROPOSITO: "ContextVar[tuple[str, int | None]]" = ContextVar(
    "proposito_ia", default=("otro", None))


@contextmanager
def proposito(clave: str, client_id: int | None = None):
    """Marca para qué son las llamadas a la IA de este bloque (y de quién).

    ⚠️ Los `contextvars` NO cruzan a los hilos de un ThreadPoolExecutor por su
    cuenta: donde se paraleliza (el panel de revisión) hay que arrancar cada
    tarea con `contextvars.copy_context().run(...)`, que es lo que hace que el
    apunte de cada revisor salga etiquetado."""
    _, cliente_actual = _PROPOSITO.get()
    # El CLIENTE se hereda: el endpoint lo fija una vez ("esto es de Mario") y
    # los bloques de dentro solo afinan el propósito ("ahora las comidas") sin
    # tener que volver a pasarlo — que es como se perdía.
    token = _PROPOSITO.set((clave if clave in PURPOSES else "otro",
                            client_id if client_id is not None else cliente_actual))
    try:
        yield
    finally:
        _PROPOSITO.reset(token)


def proposito_actual() -> tuple[str, int | None]:
    return _PROPOSITO.get()

# Precio oficial (USD por millón de tokens: entrada, salida) por familia.
_PRICES: tuple[tuple[str, tuple[float, float]], ...] = (
    ("haiku", (1.00, 5.00)),
    ("sonnet", (3.00, 15.00)),
    ("opus", (5.00, 25.00)),
)
_DEFAULT = (5.00, 25.00)


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Coste de una llamada según la familia del modelo (entrada + salida)."""
    model_l = (model or "").lower()
    price_in, price_out = _DEFAULT
    for family, prices in _PRICES:
        if family in model_l:
            price_in, price_out = prices
            break
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


def get_state(db: Session) -> AiCreditState:
    """Fila única get-or-create (mismo patrón que BrandConfig)."""
    state = db.scalar(select(AiCreditState).limit(1))
    if not state:
        state = AiCreditState(spent_usd=0.0)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def gasto_desde_la_recarga(state: AiCreditState) -> tuple[float, bool]:
    """Lo gastado desde la última recarga, y si es la cifra REAL de Anthropic.

    Con clave de administración el informe de coste manda: es lo que Anthropic
    factura. Sin ella, la estimación por tokens de siempre."""
    real = state.spent_real_usd
    if real is not None and state.spent_real_at is not None:
        return round(float(real), 4), True
    return round(float(state.spent_usd or 0.0), 4), False


def remaining_usd(state: AiCreditState) -> float | None:
    """Saldo restante; None mientras el coach no confirme una recarga."""
    if state.balance_usd is None:
        return None
    gasto, _ = gasto_desde_la_recarga(state)
    return round(state.balance_usd - gasto, 2)


def record_usage(model: str, input_tokens: int, output_tokens: int,
                 purpose: str | None = None, client_id: int | None = None) -> None:
    """Acumula el coste de una llamada y deja su rastro para el consumo en vivo.
    Sesión propia y a prueba de fallos: la contabilidad JAMÁS puede romper una
    generación de plan."""
    try:
        cost = estimate_cost_usd(model, input_tokens, output_tokens)
        if cost <= 0:
            return
        from app.db import SessionLocal
        from app.models import AiUsageEvent

        from sqlalchemy import update

        with SessionLocal() as db:
            state = get_state(db)   # get-or-create de la fila única
            # SUMA EN LA BASE, no leer-modificar-escribir. Los 8-10 revisores
            # del panel corren EN PARALELO, cada uno con su sesión: con el
            # patrón anterior todos leían el mismo saldo y el último en
            # escribir se llevaba por delante lo que habían sumado los otros.
            # El gasto anotado salía por debajo del real y el coach veía un
            # saldo optimista justo en la operación que más créditos consume.
            db.execute(
                update(AiCreditState)
                .where(AiCreditState.id == state.id)
                .values(spent_usd=func.coalesce(AiCreditState.spent_usd, 0.0) + cost)
            )
            ctx_purpose, ctx_client = proposito_actual()
            db.add(AiUsageEvent(
                model=model or "?", input_tokens=input_tokens or 0,
                output_tokens=output_tokens or 0, cost_usd=cost,
                purpose=(purpose or ctx_purpose or "otro"),
                client_id=(client_id if client_id is not None else ctx_client),
            ))
            db.commit()
    except Exception:  # noqa: BLE001 — contabilidad best-effort
        pass



# ------------------------------------------------------ crédito agotado ----
# El sistema no adivina cuándo se acaba el crédito: lo dice la API.


def es_error_de_credito(mensaje: str | None) -> bool:
    """¿Este error de la API es «te has quedado sin crédito»?

    Se exige la frase completa de saldo bajo: «billing» a secas sale también en
    errores que no son de saldo, y encender el cartel rojo por uno de esos
    dejaría al coach recargando un crédito que no le falta."""
    texto = (mensaje or "").lower()
    return "credit balance is too low" in texto or "insufficient credit" in texto


# Espejo en memoria de "¿está encendido el cartel?". Sin él, `marcar_con_credito`
# abriría una sesión de base de datos en CADA llamada buena a la IA (y el panel
# de revisión hace 8-10 seguidas) solo para comprobar algo que casi siempre es
# «no hay nada que apagar». None = aún no se ha mirado.
_cartel_encendido: bool | None = None


def marcar_sin_credito(mensaje: str) -> None:
    """Sella el momento en que la API dijo que no queda crédito.

    Best-effort y con sesión propia, como el resto de la contabilidad: esto se
    llama desde dentro del manejador de un error que ya va camino del coach."""
    global _cartel_encendido
    try:
        from app.db import SessionLocal
        from app.models import utcnow

        with SessionLocal() as db:
            state = get_state(db)
            primera_vez = state.sin_credito_desde is None
            if primera_vez:
                state.sin_credito_desde = utcnow()
            state.ultimo_error = (mensaje or "")[:300]
            db.commit()
            if primera_vez:
                # Solo la PRIMERA vez: si no, cada acción de IA que falle
                # mientras no hay crédito manda su propio aviso al móvil.
                try:
                    from app.services.push import notify_coach_sin_creditos

                    notify_coach_sin_creditos(db, motivo=mensaje or "")
                except Exception:  # noqa: BLE001
                    pass
        _cartel_encendido = True
    except Exception:  # noqa: BLE001
        pass


def marcar_con_credito() -> None:
    """Una llamada que FUNCIONA es la prueba de que ya hay crédito: apaga el
    cartel sin que nadie tenga que pulsar nada."""
    global _cartel_encendido
    if _cartel_encendido is False:
        return  # nada que apagar, y sin tocar la base
    try:
        from app.db import SessionLocal

        with SessionLocal() as db:
            state = get_state(db)
            if state.sin_credito_desde is None and not state.ultimo_error:
                _cartel_encendido = False
                return
            state.sin_credito_desde = None
            state.ultimo_error = None
            db.commit()
        _cartel_encendido = False
    except Exception:  # noqa: BLE001
        pass


def sin_credito(state: AiCreditState) -> bool:
    global _cartel_encendido
    _cartel_encendido = state.sin_credito_desde is not None
    return _cartel_encendido

# ------------------------------------------------------- consumo en vivo ----

# Ventana para estimar el coste medio por plan (y con él, los planes restantes).
USAGE_WINDOW_DAYS = 30


def usage_summary(db: Session) -> dict:
    """Consumo REAL en vivo: gasto de hoy, de la ventana, nº de llamadas, última
    llamada y coste medio por plan (gasto de la ventana ÷ planes generados con IA
    en la ventana). Nunca lanza: ante cualquier fallo devuelve ceros."""
    from datetime import timedelta

    from sqlalchemy import func

    from app.models import AiUsageEvent, Plan
    from app.services.portal import today_local

    out = {
        "spent_today_usd": 0.0, "spent_window_usd": 0.0, "calls_window": 0,
        "last_call_at": None, "avg_cost_per_plan_usd": None,
        "window_days": USAGE_WINDOW_DAYS,
    }
    try:
        since = _utcnow() - timedelta(days=USAGE_WINDOW_DAYS)
        # Día de negocio (Europe/Madrid), igual que el resto del sistema.
        start_today = _start_of_local_day(today_local())

        row = db.execute(
            select(func.coalesce(func.sum(AiUsageEvent.cost_usd), 0.0),
                   func.count(AiUsageEvent.id),
                   func.max(AiUsageEvent.created_at))
            .where(AiUsageEvent.created_at >= since)
        ).one()
        out["spent_window_usd"] = round(float(row[0] or 0.0), 4)
        out["calls_window"] = int(row[1] or 0)
        out["last_call_at"] = row[2]

        out["spent_today_usd"] = round(float(db.scalar(
            select(func.coalesce(func.sum(AiUsageEvent.cost_usd), 0.0))
            .where(AiUsageEvent.created_at >= start_today)
        ) or 0.0), 4)

        # Planes generados con IA en la misma ventana → gasto POR PLAN GENERADO.
        # "coach" (manual) y "scaffold" (base sin IA del avanzado) NO cuentan:
        # cuestan 0 y meterlos en el denominador falsearía la cifra.
        #
        # OJO CON EL NOMBRE: el numerador es TODO el gasto de la ventana —
        # también la lectura de anamnesis, el panel de revisión, los feedbacks y
        # los borradores de WhatsApp—, así que esto NO es lo que cuesta generar
        # un plan: es más. La consecuencia es que `plans_left` sale CORTO, que
        # es el lado seguro para un presupuesto; separar el gasto por tipo de
        # llamada pediría anotar el motivo en `ai_usage_events` (no lo lleva).
        plans = int(db.scalar(
            select(func.count(Plan.id))
            .where(Plan.created_at >= since, Plan.generated_by.isnot(None),
                   Plan.generated_by.notin_(("coach", "scaffold", "library")))
        ) or 0)
        if plans > 0 and out["spent_window_usd"] > 0:
            out["avg_cost_per_plan_usd"] = round(out["spent_window_usd"] / plans, 4)
    except Exception:  # noqa: BLE001 — el resumen nunca rompe el endpoint
        pass
    return out


def _utcnow():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


def _start_of_local_day(local_date):
    """Medianoche de la fecha de negocio (Europe/Madrid), con huso."""
    from datetime import datetime, time
    from zoneinfo import ZoneInfo

    return datetime.combine(local_date, time.min, tzinfo=ZoneInfo("Europe/Madrid"))


def plans_left(remaining: float | None, avg_cost_per_plan: float | None) -> int | None:
    """Planes que aún se pueden generar con el saldo restante (estimación).
    None si falta el saldo o aún no hay histórico para estimar el coste medio."""
    if remaining is None or not avg_cost_per_plan or avg_cost_per_plan <= 0:
        return None
    return max(0, int(remaining // avg_cost_per_plan))


# ------------------------------------------------------------- historial ----

def desglose(db: Session, *, days: int = 30) -> list[dict]:
    """EN QUÉ se fue el dinero en la ventana: una línea por propósito, con su
    gasto, sus llamadas y su peso sobre el total. Ordenado de más a menos caro,
    que es como se lee para decidir dónde recortar."""
    from datetime import timedelta

    from app.models import AiUsageEvent

    try:
        since = _utcnow() - timedelta(days=max(1, days))
        filas = db.execute(
            select(AiUsageEvent.purpose,
                   func.coalesce(func.sum(AiUsageEvent.cost_usd), 0.0),
                   func.count(AiUsageEvent.id))
            .where(AiUsageEvent.created_at >= since)
            .group_by(AiUsageEvent.purpose)
        ).all()
    except Exception:  # noqa: BLE001 — el historial nunca tumba la pantalla
        return []
    total = sum(float(c or 0.0) for _, c, _ in filas) or 0.0
    out = [{
        "purpose": (p or "otro"),
        "label": etiqueta_de_proposito(p),
        "cost_usd": round(float(c or 0.0), 4),
        "calls": int(n or 0),
        "share": round(100.0 * float(c or 0.0) / total, 1) if total else 0.0,
    } for p, c, n in filas]
    out.sort(key=lambda x: -x["cost_usd"])
    return out


def movimientos(db: Session, *, limit: int = 60) -> list[dict]:
    """Las últimas llamadas, una a una: cuándo, para qué, de quién y cuánto.
    El «extracto» de los créditos — el equivalente al feed de cobros, pero del
    dinero que SALE."""
    from app.models import AiUsageEvent, Client

    try:
        filas = db.execute(
            select(AiUsageEvent, Client.full_name)
            .outerjoin(Client, Client.id == AiUsageEvent.client_id)
            .order_by(AiUsageEvent.created_at.desc())
            .limit(max(1, min(limit, 200)))
        ).all()
    except Exception:  # noqa: BLE001
        return []
    return [{
        "id": ev.id,
        "at": ev.created_at,
        "purpose": ev.purpose or "otro",
        "label": etiqueta_de_proposito(ev.purpose),
        "client_id": ev.client_id,
        # El nombre puede faltar (baja RGPD): el apunte contable sobrevive sin él.
        "client_name": nombre,
        "model": ev.model,
        "cost_usd": round(float(ev.cost_usd or 0.0), 4),
        "input_tokens": ev.input_tokens or 0,
        "output_tokens": ev.output_tokens or 0,
    } for ev, nombre in filas]


def ultima_recarga_usd(db: Session) -> float | None:
    """Lo que se pagó la última vez. Es lo que se propone la siguiente: casi
    siempre se recarga lo mismo, y así confirmar es UN toque en vez de teclear
    una cifra que hay que ir a buscar al recibo."""
    from app.models import AiCreditTopUp

    try:
        fila = db.scalars(
            select(AiCreditTopUp).order_by(AiCreditTopUp.created_at.desc()).limit(1)
        ).first()
    except Exception:  # noqa: BLE001
        return None
    return round(float(fila.amount_usd), 2) if fila else None


def recargas(db: Session, *, limit: int = 24) -> list[dict]:
    """Lo que el coach ha ido pagando de créditos."""
    from app.models import AiCreditTopUp

    try:
        filas = db.scalars(
            select(AiCreditTopUp).order_by(AiCreditTopUp.created_at.desc())
            .limit(max(1, min(limit, 100)))
        ).all()
    except Exception:  # noqa: BLE001
        return []
    return [{"id": r.id, "at": r.created_at, "amount_usd": round(r.amount_usd, 2),
             "balance_before_usd": (round(r.balance_before_usd, 2)
                                    if r.balance_before_usd is not None else None),
             "note": r.note} for r in filas]


def anotar_recarga(db: Session, amount_usd: float, *, note: str | None = None) -> dict:
    """Suma una recarga al saldo. Es la cuenta que el coach hacía a mano.

    Anthropic NO expone el saldo por API, así que el sistema no puede leerlo
    solo. Lo que sí puede es llevar el libro: se apunta lo PAGADO (la cifra del
    recibo, que es la única que el coach tiene delante) y el saldo pasa a ser
    «lo que quedaba + lo que acabas de meter». Antes había que teclear la suma,
    y una resta mal hecha dejaba el aviso de saldo bajo mintiendo durante
    semanas.
    """
    from app.models import AiCreditTopUp, utcnow

    state = get_state(db)
    antes = remaining_usd(state)
    base = antes if antes is not None else 0.0
    state.balance_usd = round(base + float(amount_usd), 4)
    # El gasto vuelve a cero porque el saldo nuevo YA lo tiene descontado: el
    # historial de llamadas (ai_usage_events) conserva el detalle intacto.
    state.spent_usd = 0.0
    ahora = utcnow()
    state.updated_at = ahora
    # El informe de coste vuelve a contar DESDE AQUÍ; si no, la próxima lectura
    # traería el gasto del ciclo anterior y se descontaría dos veces.
    state.spent_real_usd = 0.0 if state.spent_real_at is not None else None
    state.spent_real_desde = ahora
    state.spent_real_at = ahora if state.spent_real_at is not None else None
    # Recargar es exactamente la prueba de que vuelve a haber crédito.
    state.sin_credito_desde = None
    state.ultimo_error = None
    db.add(AiCreditTopUp(amount_usd=float(amount_usd), balance_before_usd=antes,
                         note=(note or None)))
    db.commit()
    db.refresh(state)
    global _cartel_encendido
    _cartel_encendido = False
    return {"balance_usd": state.balance_usd, "added_usd": float(amount_usd),
            "balance_before_usd": antes}
