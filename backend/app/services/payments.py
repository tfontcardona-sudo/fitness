"""Libro de caja de la asesoría: anotar, consultar y sincronizar movimientos.

Incluye los cobros de Stripe y los que el coach registra a mano (efectivo,
transferencia, Bizum): el total del mes tiene que contar TODO el dinero.

El coach necesita ver EN LA WEB quién pagó, cuánto y cuándo, y enterarse de cada
cobro como en la app del banco. Este módulo es la única puerta a la tabla
`payments`:

- `record_payment` anota un movimiento (cobro, cobro fallido o devolución) de
  forma IDEMPOTENTE y sin poder romper nunca al que la llama: el dinero ya entró
  en Stripe, así que un fallo contable jamás puede tumbar el webhook.
- `summary` / `list_payments` alimentan el feed y su cabecera.
- `mark_seen` sella lo leído (`seen_at`) — el "no leído" del feed.
- `sync_from_stripe` rellena el histórico ANTERIOR a esta tabla y repesca lo que
  un webhook perdido no trajo: la red de seguridad de todo el sistema.

Reglas del dinero (aprendidas de la auditoría):
- Los importes se guardan en CÉNTIMOS enteros, como los da Stripe, con su moneda.
  Nunca se deducen de la tabla de precios del código: un cupón, un prorrateo o un
  reprecio histórico harían mentir a la cifra.
- La fecha es la de STRIPE (`created`/`status_transitions.paid_at`), no la de
  recepción del webhook: una reentrega tardía no puede falsear el día del cobro.
- Los pagos en modo PRUEBA (`livemode=False`) se anotan pero NO suman en los
  totales: no son dinero real.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Client, Payment

_log = logging.getLogger("app.payments")

# Tipos de movimiento y estados (String + Literal en Pydantic, como el resto).
# "subscription"/"canceled": la BAJA de la suscripción de la oferta — no mueve
# dinero (importe 0, fuera de los totales) pero es un hecho de Stripe que el
# coach debe ver en el feed, no solo en un push que se esfuma.
# "manual": cobro fuera de Stripe que anota el coach (efectivo, transferencia…).
KINDS = ("checkout", "invoice", "refund", "subscription", "manual")
STATUSES = ("paid", "failed", "refunded", "canceled")

# Tope del histórico que trae la sincronización manual con Stripe.
SYNC_DEFAULT_DAYS = 365
SYNC_MAX_OBJECTS = 2000  # freno duro: ninguna cuenta de un coach tiene más

# Lo que la sincronización trae del PASADO se da por visto (rellenar el
# histórico no puede encender 200 notificaciones). Pero un cobro RECIENTE que
# aparece por sincronización es justo lo contrario: significa que su webhook se
# perdió, y el coach todavía no se ha enterado — ese llega SIN LEER.
SYNC_SEEN_OLDER_THAN_H = 24


def _tz() -> ZoneInfo:
    try:
        return ZoneInfo(settings.tz)
    except Exception:  # noqa: BLE001 — zona mal escrita en el .env
        return ZoneInfo("UTC")


def ts_to_dt(value) -> datetime | None:
    """Marca de tiempo UNIX de Stripe → datetime con zona (UTC)."""
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def describe(tier: str | None, billing_period: str | None, *,
             kind: str = "checkout", billing_reason: str | None = None) -> str:
    """Texto corto del movimiento para el feed: "DQR Full · 3 meses"."""
    from app.services import packages as pkgs
    from app.services.stripe_service import PERIOD_LABEL

    plan = pkgs.label(tier) if tier else "Asesoría"
    if billing_period == "oferta":
        # Programa cerrado de 3 pagos (1 € + 120 + 120): se dice cuál es el 1º;
        # los otros dos llegan como facturas mensuales de 120 €.
        if billing_reason == "subscription_create":
            return f"{plan} · oferta (pago 1 de 3 · 1 €)"
        return (f"{plan} · oferta (pago 2 o 3 de 3)" if kind == "invoice"
                else f"{plan} · oferta")
    if billing_period == "oferta2":
        # La misma oferta en 2 pagos de 120,50 €: se dice cuál de los dos es.
        if billing_reason == "subscription_create":
            return f"{plan} · oferta (pago 1 de 2)"
        return (f"{plan} · oferta (pago 2 de 2)" if kind == "invoice"
                else f"{plan} · oferta 2 pagos")
    periodo = PERIOD_LABEL.get(billing_period or "", "")
    return f"{plan} · {periodo}" if periodo else plan


def record_payment(
    db: Session,
    *,
    object_id: str,
    kind: str,
    status: str,
    amount_cents: int,
    currency: str = "eur",
    livemode: bool = True,
    client: Client | None = None,
    customer_name: str | None = None,
    customer_email: str | None = None,
    tier: str | None = None,
    billing_period: str | None = None,
    description: str | None = None,
    paid_at: datetime | None = None,
    event_id: str | None = None,
    seen: bool = False,
    fee_cents: int | None = None,
    payment_intent: str | None = None,
) -> Payment | None:
    """Anota un movimiento en el libro. Devuelve la fila creada, o None si ya
    estaba anotada (idempotente por objeto+estado) o si algo falló.

    NUNCA lanza: el cobro ya ocurrió en Stripe y la contabilidad no puede
    impedir que el webhook siga marcando al cliente como pagado.
    """
    if not object_id or status not in STATUSES:
        return None
    try:
        ya = db.scalar(
            select(Payment).where(
                Payment.stripe_object_id == object_id, Payment.status == status
            ).limit(1)
        )
        if ya is not None:
            return None
        pago = Payment(
            stripe_object_id=object_id,
            stripe_event_id=event_id,
            kind=kind if kind in KINDS else "checkout",
            status=status,
            amount_cents=int(amount_cents or 0),
            fee_cents=int(fee_cents) if fee_cents is not None else None,
            payment_intent=payment_intent or None,
            currency=(currency or "eur").lower(),
            livemode=bool(livemode),
            client_id=client.id if client is not None else None,
            # Copia del pagador: el libro debe seguir diciendo QUIÉN pagó aunque
            # la ficha se borre (RGPD) o el pago sea huérfano.
            customer_name=(customer_name or (client.full_name if client else None)),
            customer_email=(customer_email or (client.email if client else None)),
            tier=tier or (client.package_tier if client else None),
            billing_period=billing_period or (client.billing_period if client else None),
            description=description,
            paid_at=paid_at or datetime.now(timezone.utc),
            seen_at=datetime.now(timezone.utc) if seen else None,
        )
        # Savepoint: si otra entrega simultánea del mismo evento se adelanta, el
        # UNIQUE salta aquí y NO invalida la transacción del webhook.
        with db.begin_nested():
            db.add(pago)
            db.flush()
        return pago
    except SQLAlchemyError as exc:
        _log.warning("Movimiento %s/%s no anotado: %s", object_id, status, exc)
        return None
    except Exception as exc:  # noqa: BLE001 — la contabilidad nunca rompe el cobro
        _log.warning("Movimiento %s/%s no anotado (inesperado): %s", object_id, status, exc)
        return None


def record_refunds_of_charge(db: Session, charge: dict, *,
                             client: Client | None = None,
                             event_id: str | None = None,
                             seen: bool = False,
                             seen_by_age: bool = False) -> int:
    """Anota las DEVOLUCIONES de un cobro. Devuelve cuántas se anotaron nuevas.

    Va por REEMBOLSO (re_…), no por cargo: `charge.amount_refunded` es el
    ACUMULADO y Stripe dispara `charge.refunded` en CADA devolución, así que
    con el id del cargo como clave la segunda devolución parcial se descartaba
    entera por idempotencia y el libro se quedaba corto (30 € devueltos de 80 €
    reales). Con el id de cada reembolso, cada una es su propio movimiento.

    Reserva: si el evento no trae la lista de reembolsos (según la versión de
    API anclada al endpoint del webhook), se anota una única fila con el id del
    cargo y el acumulado, y si esa fila ya existía con MENOS importe se
    actualiza — así el total devuelto nunca se queda por debajo del real.
    """
    facturado = charge.get("billing_details") or {}
    email = (facturado.get("email") or charge.get("receipt_email") or "").strip().lower() or None
    pi = charge.get("payment_intent")
    comun = dict(
        kind="refund", status="refunded", currency=charge.get("currency") or "eur",
        livemode=bool(charge.get("livemode", True)), client=client,
        customer_name=facturado.get("name"), customer_email=email,
        description="Devolución", event_id=event_id, seen=seen,
        payment_intent=(pi.get("id") if isinstance(pi, dict) else pi) or None,
    )
    # ¿Existe ya una fila AGREGADA por el id del cargo? (la escribió un webhook
    # cuya carga no traía la lista de reembolsos). Si existe, la sincronización
    # NO puede además insertar filas re_… del mismo cargo: el mismo dinero
    # devuelto restaría dos veces. En ese caso se mantiene la semántica
    # agregada y solo se pone al día el importe acumulado.
    cargo_id = charge.get("id") or ""
    agregada = db.scalar(
        select(Payment).where(Payment.stripe_object_id == cargo_id,
                              Payment.status == "refunded").limit(1)
    ) if cargo_id else None

    reembolsos = [r for r in ((charge.get("refunds") or {}).get("data") or [])
                  if r.get("id") and (r.get("amount") or 0) > 0]
    if reembolsos and agregada is None:
        nuevas = 0
        for r in reembolsos:
            cuando = ts_to_dt(r.get("created") or charge.get("created"))
            if seen_by_age:
                # Por la FECHA DEL REEMBOLSO, no la del cargo: una devolución
                # de ayer sobre un cobro de hace meses quedaba "vista" y el
                # badge no avisaba al coach (auditoría).
                comun["seen"] = _visto_por_antiguedad(cuando)
            if record_payment(db, object_id=r["id"], amount_cents=r.get("amount") or 0,
                              paid_at=cuando, **comun) is not None:
                nuevas += 1
        return nuevas

    total = charge.get("amount_refunded") or 0
    if total <= 0:
        return 0
    if agregada is not None:
        # Si han devuelto MÁS desde entonces, se pone al día el importe.
        if total > agregada.amount_cents:
            agregada.amount_cents = total
            return 1
        return 0
    pago = record_payment(db, object_id=cargo_id, amount_cents=total,
                          paid_at=ts_to_dt(charge.get("created")), **comun)
    return 1 if pago is not None else 0


# ------------------------------------------------------------ consultas ----

def unseen_count(db: Session) -> int:
    """Movimientos sin leer (el badge de la barra)."""
    return int(db.scalar(
        select(func.count(Payment.id)).where(Payment.seen_at.is_(None))
    ) or 0)


def _month_bounds(now_local: datetime) -> tuple[datetime, datetime]:
    """(inicio de ESTE mes, inicio del SIGUIENTE) en UTC, con el mes natural de
    la zona horaria del coach — no la del servidor."""
    start = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    nxt = (start + timedelta(days=32)).replace(day=1)
    return start.astimezone(timezone.utc), nxt.astimezone(timezone.utc)


def _neto_cents(db: Session, desde: datetime, hasta: datetime) -> tuple[int, int]:
    """(cobrado − devuelto, nº de cobros) entre dos fechas. Solo dinero REAL:
    los movimientos en modo prueba de Stripe no suman."""
    filas = db.execute(
        select(Payment.status, func.coalesce(func.sum(Payment.amount_cents), 0),
               func.count(Payment.id))
        .where(Payment.paid_at >= desde, Payment.paid_at < hasta,
               Payment.livemode.is_(True), Payment.status.in_(("paid", "refunded")))
        .group_by(Payment.status)
    ).all()
    total = 0
    cobros = 0
    for status, suma, n in filas:
        if status == "paid":
            total += int(suma or 0)
            cobros += int(n or 0)
        else:
            total -= int(suma or 0)
    return total, cobros


def summary(db: Session) -> dict:
    """Cabecera del feed: ingresos del mes, del anterior, sin leer y avisos."""
    ahora_local = datetime.now(timezone.utc).astimezone(_tz())
    mes_ini, mes_fin = _month_bounds(ahora_local)
    prev_ini, _ = _month_bounds((mes_ini.astimezone(_tz()) - timedelta(days=1)))

    mes_total, mes_cobros = _neto_cents(db, mes_ini, mes_fin)
    prev_total, _prev_cobros = _neto_cents(db, prev_ini, mes_ini)

    ultimo = db.scalar(
        select(Payment).where(Payment.status == "paid")
        .order_by(Payment.paid_at.desc()).limit(1)
    )
    # Movimientos de PRUEBA (clave sk_test_): se ven en el feed pero no suman.
    pruebas = int(db.scalar(
        select(func.count(Payment.id)).where(Payment.livemode.is_(False))
    ) or 0)
    # Cobros que Stripe no pudo pasar: lo que el coach tiene que perseguir.
    # Solo dinero REAL: un impago o un huérfano de una prueba con sk_test_
    # no puede encender avisos rojos en el panel (auditoría).
    fallidos = int(db.scalar(
        select(func.count(Payment.id)).where(
            Payment.status == "failed", Payment.paid_at >= mes_ini,
            Payment.livemode.is_(True))
    ) or 0)
    huerfanos = int(db.scalar(
        select(func.count(Payment.id)).where(
            Payment.client_id.is_(None), Payment.status == "paid",
            Payment.livemode.is_(True), Payment.anonymized_at.is_(None))
    ) or 0)
    # Comisiones de Stripe del mes (solo cobros con fee consultado): permiten
    # enseñar el NETO real que llega al banco, no solo el bruto cobrado.
    mes_fees = int(db.scalar(
        select(func.coalesce(func.sum(Payment.fee_cents), 0)).where(
            Payment.paid_at >= mes_ini, Payment.paid_at < mes_fin,
            Payment.livemode.is_(True), Payment.status == "paid")
    ) or 0)
    return {
        "unseen": unseen_count(db),
        "month_total_cents": mes_total,
        "month_fee_cents": mes_fees,
        "month_count": mes_cobros,
        "prev_month_total_cents": prev_total,
        "failed_month": fallidos,
        "orphan_count": huerfanos,
        "test_count": pruebas,
        "currency": "eur",
        "last_payment_at": ultimo.paid_at.isoformat() if ultimo else None,
        "total_count": int(db.scalar(select(func.count(Payment.id))) or 0),
        "stripe_enabled": bool(settings.stripe_enabled),
    }


def monthly_series(db: Session, *, months: int = 6) -> list[dict]:
    """Ingresos NETOS por mes natural (zona del coach) para la gráfica de la
    pantalla de Pagos: cobrado − devuelto, solo dinero real (livemode).
    Devuelve los últimos `months` meses, el actual incluido, con ceros donde
    no hubo movimiento — la gráfica no puede "saltarse" un mes malo."""
    tz = _tz()
    ahora_local = datetime.now(timezone.utc).astimezone(tz)
    # Primer día del mes más antiguo de la ventana.
    ini_local = ahora_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    for _ in range(max(0, months - 1)):
        ini_local = (ini_local - timedelta(days=1)).replace(day=1)

    filas = db.execute(
        select(
            func.date_trunc("month", func.timezone(str(tz), Payment.paid_at)).label("mes"),
            Payment.status,
            func.coalesce(func.sum(Payment.amount_cents), 0),
            func.count(Payment.id),
        )
        .where(Payment.paid_at >= ini_local.astimezone(timezone.utc),
               Payment.livemode.is_(True), Payment.status.in_(("paid", "refunded")))
        .group_by("mes", Payment.status)
    ).all()
    por_mes: dict[str, dict] = {}
    for mes, status, suma, n in filas:
        clave = mes.strftime("%Y-%m")
        agg = por_mes.setdefault(clave, {"total": 0, "count": 0})
        if status == "paid":
            agg["total"] += int(suma or 0)
            agg["count"] += int(n or 0)
        else:
            agg["total"] -= int(suma or 0)

    out: list[dict] = []
    cursor = ini_local
    for _ in range(max(1, months)):
        clave = cursor.strftime("%Y-%m")
        agg = por_mes.get(clave, {"total": 0, "count": 0})
        out.append({"month": clave, "total_cents": agg["total"], "count": agg["count"]})
        siguiente = (cursor + timedelta(days=32)).replace(day=1)
        cursor = siguiente
    return out


def list_payments(db: Session, *, limit: int = 50, offset: int = 0,
                  status: str | None = None,
                  client_id: int | None = None,
                  orphan: bool = False) -> tuple[list[Payment], int]:
    """Página del feed (más reciente primero) + total que cumple el filtro.

    orphan=True: solo los cobros SIN ficha. El resumen avisaba de cuántos hay y
    no había forma de llegar a ellos desde la web."""
    filtros = []
    if status in STATUSES:
        filtros.append(Payment.status == status)
    if client_id:
        filtros.append(Payment.client_id == client_id)
    if orphan:
        # MISMO criterio que el contador del resumen: si no, el chip decía "3
        # sin ficha" y la lista enseñaba 12 (incluyendo pruebas, devoluciones y
        # cobros ya anonimizados por RGPD).
        filtros += [Payment.client_id.is_(None), Payment.status == "paid",
                    Payment.livemode.is_(True),
                    Payment.anonymized_at.is_(None)]
    total = int(db.scalar(select(func.count(Payment.id)).where(*filtros)) or 0)
    filas = list(db.scalars(
        select(Payment).where(*filtros)
        # id como desempate: dos cobros con la misma fecha (backfill) no pueden
        # bailar entre páginas y duplicarse/perderse al pulsar "Ver más".
        .order_by(Payment.paid_at.desc(), Payment.id.desc())
        .limit(max(1, min(limit, 100))).offset(max(0, offset))
    ))
    return filas, total


def mark_seen(db: Session, ids: list[int] | None = None) -> int:
    """Sella como leídos los movimientos indicados (o TODOS). Devuelve cuántos."""
    q = select(Payment).where(Payment.seen_at.is_(None))
    if ids:
        q = q.where(Payment.id.in_(ids))
    filas = list(db.scalars(q))
    ahora = datetime.now(timezone.utc)
    for f in filas:
        f.seen_at = ahora
    if filas:
        db.commit()
    return len(filas)


def adopt_orphans(db: Session, client: Client, *, days: int = 30) -> int:
    """Reasocia a `client` los movimientos HUÉRFANOS que llevan su email.

    Hay una carrera real en el alta self-serve de la oferta: Stripe cobra y paga
    la primera factura ANTES de completar la sesión de checkout, así que
    `invoice.paid` llega cuando el cliente todavía no existe y su movimiento se
    anota sin ficha. Nadie lo reasociaba después: el aviso "pago sin ficha
    asociada" se quedaba encendido para siempre en un alta impecable, el cobro
    no salía en la ficha del cliente y —lo más grave— el borrado RGPD no lo
    alcanzaba (se quedaban ahí su nombre y su email).

    Best-effort: nunca lanza (la contabilidad no puede romper el alta)."""
    email = (client.email or "").strip().lower()
    if not email:
        return 0
    try:
        desde = datetime.now(timezone.utc) - timedelta(days=max(1, days))
        filas = list(db.scalars(
            select(Payment).where(
                Payment.client_id.is_(None),
                func.lower(Payment.customer_email) == email,
                Payment.paid_at >= desde,
            )
        ))
        for f in filas:
            f.client_id = client.id
            if not f.customer_name:
                f.customer_name = client.full_name
        return len(filas)
    except SQLAlchemyError as exc:
        _log.warning("Adopción de movimientos huérfanos fallida (%s): %s", email, exc)
        return 0


def anonymize_client(db: Session, client_id: int) -> int:
    """Borrado RGPD: el movimiento se CONSERVA (el libro de caja no puede perder
    dinero) pero deja de apuntar a la persona — sin ficha, sin nombre y sin
    email. Devuelve cuántas filas se anonimizaron."""
    filas = list(db.scalars(select(Payment).where(Payment.client_id == client_id)))
    ahora = datetime.now(timezone.utc)
    for f in filas:
        f.client_id = None
        f.customer_name = None
        f.customer_email = None
        # Sellado: un cobro anonimizado NO es un "cobro sin ficha" que el coach
        # deba investigar — antes el aviso de huérfanos se quedaba encendido
        # para siempre tras un borrado RGPD, sin nada que hacer al respecto.
        f.anonymized_at = ahora
    return len(filas)


# -------------------------------------------------- sincronización Stripe ----

def _visto_por_antiguedad(cuando: datetime | None) -> bool:
    """True si el movimiento es lo bastante viejo como para darlo por visto."""
    if cuando is None:
        return True
    return cuando < datetime.now(timezone.utc) - timedelta(hours=SYNC_SEEN_OLDER_THAN_H)


def _client_by_email(db: Session, email: str | None) -> Client | None:
    if not email:
        return None
    return db.scalar(select(Client).where(func.lower(Client.email) == email.strip().lower()))


def _refresca_ficha(client: Client | None, *, pagado_en: datetime | None,
                    livemode: bool) -> None:
    """La repesca también pone al día la FICHA del cliente: si el webhook de un
    cobro se perdió, el movimiento entraba al libro pero el cliente seguía
    'pendiente' (o con `paid_at` del pago anterior → alerta de renovación
    eterna). Misma regla de fechas que `_mark_paid`; sin push (lo recuperado
    ya queda SIN LEER en el feed si es reciente)."""
    if client is None or not livemode:
        return
    client.payment_status = "paid"
    cuando = pagado_en or datetime.now(timezone.utc)
    if client.paid_at is None or cuando > client.paid_at:
        client.paid_at = cuando


def sync_from_stripe(db: Session, *, days: int = SYNC_DEFAULT_DAYS) -> dict:
    """Trae de Stripe los movimientos de los últimos `days` días y anota los que
    falten. Sirve para DOS cosas: rellenar el histórico anterior a esta tabla y
    repescar cobros cuyo webhook se perdió (Stripe caído, deploy en marcha…).

    Recorre las tres fuentes que cubren el negocio:
      · Checkout Sessions pagadas (planes de pago único),
      · Facturas pagadas (renovaciones de la suscripción de la oferta),
      · Cobros con devolución (reembolsos).

    Idempotente: lo ya anotado se ignora. Nunca lanza al caller salvo que Stripe
    no esté configurado.
    """
    from app.services.stripe_service import (
        StripeError,
        _client_from_invoice,
        _invoice_es_de_la_oferta,
        _stripe,
    )

    if not settings.stripe_enabled:
        raise StripeError("Stripe no está configurado (falta STRIPE_SECRET_KEY en el .env).")

    stripe = _stripe()
    desde = int((datetime.now(timezone.utc) - timedelta(days=max(1, days))).timestamp())
    creados = 0
    revisados = 0
    errores: list[str] = []

    def _limitado(iterador):
        """Corta el barrido: ni la cuenta más movida de un coach pasa de aquí."""
        nonlocal revisados
        for obj in iterador:
            if revisados >= SYNC_MAX_OBJECTS:
                break
            revisados += 1
            yield obj

    # 1) Checkout Sessions de PAGO ÚNICO. Las de modo suscripción se saltan: su
    #    dinero llega como factura (anotarlas también duplicaría el ingreso).
    try:
        for s in _limitado(stripe.checkout.Session.list(
                created={"gte": desde}, limit=100).auto_paging_iter()):
            if s.get("payment_status") != "paid" or s.get("mode") == "subscription":
                continue
            meta = s.get("metadata") or {}
            detalles = s.get("customer_details") or {}
            cliente = None
            cid = meta.get("client_id") or s.get("client_reference_id")
            if cid:
                try:
                    cliente = db.get(Client, int(cid))
                except (TypeError, ValueError):
                    cliente = None
            cliente = cliente or _client_by_email(db, detalles.get("email"))
            tier = meta.get("tier")
            period = meta.get("billing_period")
            if record_payment(
                db, object_id=s["id"], kind="checkout", status="paid",
                amount_cents=s.get("amount_total") or 0,
                currency=s.get("currency") or "eur", livemode=bool(s.get("livemode", True)),
                client=cliente, customer_name=detalles.get("name"),
                customer_email=detalles.get("email"), tier=tier, billing_period=period,
                description=describe(tier or (cliente.package_tier if cliente else None),
                                     period or (cliente.billing_period if cliente else None)),
                paid_at=ts_to_dt(s.get("created")),
                seen=_visto_por_antiguedad(ts_to_dt(s.get("created"))),
                payment_intent=(s.get("payment_intent") or None)
                if not isinstance(s.get("payment_intent"), dict)
                else s["payment_intent"].get("id"),
            ) is not None:
                creados += 1
                _refresca_ficha(cliente, pagado_en=ts_to_dt(s.get("created")),
                                livemode=bool(s.get("livemode", True)))
    except Exception as exc:  # noqa: BLE001 — una fuente caída no anula las demás
        errores.append(f"checkout: {exc}")

    # 2) Facturas pagadas (renovaciones de la oferta).
    try:
        for inv in _limitado(stripe.Invoice.list(
                created={"gte": desde}, status="paid", limit=100).auto_paging_iter()):
            if not _invoice_es_de_la_oferta(inv):
                continue  # factura de otro producto de la misma cuenta de Stripe
            from app.services.stripe_service import periodo_de_factura

            cliente = _client_from_invoice(db, inv)
            periodo = periodo_de_factura(inv, cliente)
            pagada_en = ((inv.get("status_transitions") or {}).get("paid_at")
                         or inv.get("created"))
            if record_payment(
                db, object_id=inv["id"], kind="invoice", status="paid",
                amount_cents=inv.get("amount_paid") or 0,
                currency=inv.get("currency") or "eur",
                livemode=bool(inv.get("livemode", True)),
                client=cliente, customer_name=inv.get("customer_name"),
                customer_email=inv.get("customer_email"),
                tier=(cliente.package_tier if cliente else "full"),
                billing_period=periodo,
                description=describe("full", periodo, kind="invoice",
                                     billing_reason=inv.get("billing_reason")),
                paid_at=ts_to_dt(pagada_en),
                seen=_visto_por_antiguedad(ts_to_dt(pagada_en)),
                payment_intent=(inv.get("payment_intent") or None)
                if not isinstance(inv.get("payment_intent"), dict)
                else inv["payment_intent"].get("id"),
            ) is not None:
                creados += 1
                _refresca_ficha(cliente, pagado_en=ts_to_dt(pagada_en),
                                livemode=bool(inv.get("livemode", True)))
    except Exception as exc:  # noqa: BLE001
        errores.append(f"facturas: {exc}")

    # 3) Devoluciones (un reembolso resta de los ingresos del mes).
    try:
        # MISMO criterio de pertenencia que el webhook (_cargo_es_nuestro): la
        # cuenta puede tener cobros de OTROS productos (facturas manuales, un
        # taller) que aquí nunca sumaron — su devolución tampoco puede restar.
        # Sin este filtro, la sincronización reintroducía por la puerta de
        # atrás el bug ya corregido en el webhook (auditoría crítica).
        from app.services.stripe_service import _cargo_es_nuestro

        for ch in _limitado(stripe.Charge.list(
                created={"gte": desde}, limit=100).auto_paging_iter()):
            if (ch.get("amount_refunded") or 0) <= 0:
                continue
            facturado = ch.get("billing_details") or {}
            cliente = _client_by_email(db, facturado.get("email") or ch.get("receipt_email"))
            if not _cargo_es_nuestro(db, ch, cliente):
                continue
            creados += record_refunds_of_charge(
                db, ch, client=cliente, seen_by_age=True,
                seen=_visto_por_antiguedad(ts_to_dt(ch.get("created"))))
    except Exception as exc:  # noqa: BLE001
        errores.append(f"devoluciones: {exc}")

    if creados:
        db.commit()
    else:
        db.rollback()
    if errores:
        _log.warning("Sincronización de pagos con incidencias: %s", "; ".join(errores))
    # `partial`: el freno duro cortó el barrido — el resultado NO cubre todo el
    # rango pedido y el caller/UI no debe darlo por completo en silencio.
    return {"created": creados, "scanned": revisados, "errors": errores,
            "partial": revisados >= SYNC_MAX_OBJECTS}


# ------------------------------------------------- cobros FUERA de Stripe ----

# Cómo pagó el cliente cuando no fue por Stripe. Se guarda en `description`
# para que el feed diga de un vistazo de dónde viene el dinero.
METODOS_MANUALES = {
    "efectivo": "Efectivo",
    "transferencia": "Transferencia",
    "bizum": "Bizum",
    "otro": "Otro método",
}


def hoy_local() -> date:
    """Fecha de NEGOCIO (zona del coach). Con la de UTC, de madrugada el cobro
    se anotaba en el día —y a veces en el mes— anterior."""
    return datetime.now(timezone.utc).astimezone(_tz()).date()


def existe_cobro_manual(db: Session, *, client_id: int, paid_on: date,
                        amount_cents: int, method: str, note: str | None) -> bool:
    """¿Ya está anotado ESTE cobro? (mismo cliente, día, importe, método y
    nota). Sirve para distinguir el doble clic de un fallo de la base."""
    obj = _id_cobro_manual(client_id, paid_on, int(amount_cents), method, note)
    return db.scalar(
        select(func.count(Payment.id)).where(
            Payment.stripe_object_id == obj, Payment.status == "paid")
    ) not in (0, None)


def _id_cobro_manual(client_id: int, cuando: date, importe: int,
                     metodo: str, nota: str | None) -> str:
    """Identidad del cobro a mano: mismo cliente, día, importe, método y nota =
    el mismo cobro. Sin instante: si no, el doble clic duplicaba el dinero."""
    firma = hashlib.sha1(
        f"{(nota or '').strip().lower()}".encode("utf-8")
    ).hexdigest()[:8]
    return f"manual_{client_id}_{cuando.isoformat()}_{importe}_{metodo}_{firma}"


def record_manual_payment(
    db: Session,
    *,
    client: Client,
    amount_cents: int,
    method: str = "otro",
    paid_on: date | None = None,
    note: str | None = None,
) -> Payment | None:
    """Anota un cobro que NO pasó por Stripe (efectivo, transferencia, Bizum).

    El libro de caja tiene que contar TODO el dinero de la asesoría, no solo lo
    que entra por la pasarela: si no, el total del mes miente. Se guarda como un
    movimiento normal (`livemode=True`, `status="paid"`) para que sume en el
    resumen y salga en el feed y en el CSV exactamente igual que un cobro de
    Stripe, distinguido por `kind="manual"`.

    El id sintético identifica el COBRO, no el instante: cliente, día, importe,
    método y nota. Así un doble clic (o volver atrás y reenviar) no duplica el
    ingreso — antes el id llevaba el segundo actual y solo protegía si los dos
    envíos caían dentro del mismo segundo, que es justo lo que no pasa con un
    doble clic humano. Si de verdad hay dos cobros iguales el mismo día, basta
    con anotarlos con notas distintas.
    """
    cuando = paid_on or datetime.now(timezone.utc).astimezone(_tz()).date()
    momento = datetime.now(timezone.utc)
    etiqueta = METODOS_MANUALES.get(method, METODOS_MANUALES["otro"])
    descripcion = f"{etiqueta} · registrado por el coach"
    if note:
        descripcion = f"{descripcion} — {note.strip()[:80]}"
    return record_payment(
        db,
        object_id=_id_cobro_manual(client.id, cuando, int(amount_cents), method, note),
        kind="manual",
        status="paid",
        amount_cents=int(amount_cents),
        client=client,
        customer_name=client.full_name,
        customer_email=client.email,
        tier=getattr(client, "package_tier", None),
        billing_period=getattr(client, "billing_period", None),
        description=descripcion,
        # Fecha del COBRO (la que dice el coach), no la de registro: el mes al
        # que pertenece el ingreso es aquel en que se cobró. Si es HOY se usa la
        # hora actual para que salga arriba del feed nada más anotarlo; en una
        # fecha pasada, el mediodía (evita saltos de día por zona horaria).
        paid_at=(momento if cuando == datetime.now(timezone.utc).astimezone(_tz()).date()
                 else datetime.combine(cuando, time(12, 0), tzinfo=timezone.utc)),
        # Lo apunta el coach: ya se ha enterado, no tiene que salir sin leer.
        seen=True,
    )
