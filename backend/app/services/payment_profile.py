"""El estado de pago de un cliente, contado ENTERO y en un solo sitio.

La ficha sabía dos cosas del dinero —`payment_status` y `paid_at`— y con eso no
se responde a lo que el coach pregunta delante de un cliente: cuánto le toca
pagar, cuándo fue el último cobro, cuándo es el próximo, cómo paga, cuánto
lleva pagado y, si no ha pagado, POR QUÉ. Cada pantalla que lo intentaba lo
deducía por su cuenta (el listado con un `payment_status === "pending"`, la
ficha con otra corazonada, el portal con ninguna) y tres deducciones sobre lo
mismo acaban contradiciéndose: el listado decía "pago pendiente" a quien acaba
de renovar y el portal no decía nada a quien llevaba un mes sin pagar.

Aquí hay DOS funciones, y la separación importa:

- `estado(client, marca, today)` es PURA: no toca la base. Sale entera de la
  ficha y de los precios de SU marca, así que el listado de clientes la puede
  llamar por cada fila sin una sola consulta más (el barrido de la cartera ya
  costó caro una vez: 431 consultas por refresco).
- `historial(db, client)` sí consulta, y es para la FICHA: el último cobro con
  su importe y su método, el total pagado y cuántos cobros lleva. Una pantalla,
  una consulta.

REGLA: el motivo del impago se GUARDA solo cuando es un hecho que no se puede
deducir (una baja, un cobro fallido); "vencido" se deduce de la ventana de
renovación —que ya es la única verdad del sistema, `services/renewals.py`— y
"alta" de no tener ningún cobro. Dos verdades sobre lo mismo se contradicen.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Client, Payment

# Cómo paga, en cristiano. `stripe` no es un "método" que el coach elija: es
# que el dinero entró solo por la pasarela, y decirlo evita que nadie lo anote
# a mano por segunda vez.
METODO_LABEL = {
    "stripe": "Tarjeta (Stripe)",
    "efectivo": "Efectivo",
    "transferencia": "Transferencia",
    "bizum": "Bizum",
    "otro": "Otro método",
}

# Cada cuánto paga. Las dos formas de la oferta son programas CERRADOS de tres
# meses: no se renuevan solas, por eso no son "cada 3 meses".
CADENCIA_LABEL = {
    "1m": "cada mes",
    "3m": "cada 3 meses",
    "6m": "cada 6 meses",
    "oferta": "oferta de 3 pagos (1 € + 120 € + 120 €)",
    "oferta2": "oferta en 2 pagos",
}

# Por qué no está pagado. Los dos primeros se GUARDAN (son hechos que llegan de
# Stripe y no se pueden deducir después); los dos últimos se deducen aquí.
MOTIVO_TEXTO = {
    "alta": "Nunca ha pagado: es un alta sin cobrar.",
    "cancelado": "Canceló su suscripción: no habrá más cobros.",
    "fallido": "Stripe no pudo cobrarle (tarjeta rechazada o caducada).",
    "vencido": "Su ciclo pagado ha terminado y sigue en activo.",
}
MOTIVO_CORTO = {
    "alta": "Sin cobrar",
    "cancelado": "Canceló",
    "fallido": "Cobro fallido",
    "vencido": "Ciclo vencido",
}


def _importe_previsto(client: Client, marca) -> int | None:
    """Céntimos que le tocan por SU plan y SU duración, según SU marca.

    None si su marca no vende esa combinación: un precio inventado en la
    pantalla del cobro es peor que no dar ninguno — el coach lo daría por bueno
    y cobraría de menos.
    """
    if marca is None:
        return None
    periodo = getattr(client, "billing_period", None) or "1m"
    tier = getattr(client, "package_tier", None) or "full"
    if periodo in ("oferta", "oferta2"):
        # El programa de captación no tiene "cuota": lo que toca depende de en
        # qué pago va, y eso lo sabe Stripe, no la ficha.
        return None
    try:
        return marca.importe(tier, periodo)
    except Exception:  # noqa: BLE001 — una marca mal configurada no tumba la ficha
        return None


def estado(client: Client, marca=None, today: date | None = None) -> dict:
    """Todo lo que se sabe del pago de este cliente, SIN tocar la base.

    Devuelve siempre las mismas claves (nunca lanza): el listado, la ficha, la
    alerta y el portal leen de aquí y no vuelven a deducir nada.
    """
    from app.services.renewals import RENEWAL_WARN_DAYS, renewal_window

    hoy = today or datetime.now(timezone.utc).date()
    pagado = getattr(client, "payment_status", None) == "paid"
    paid_at = getattr(client, "paid_at", None)
    periodo = getattr(client, "billing_period", None) or "1m"
    suscrito = bool(getattr(client, "stripe_subscription_id", None))

    ventana = renewal_window(client, hoy)
    proximo: date | None = None
    dias: int | None = None
    if ventana is not None:
        proximo, dias = ventana

    # --- ¿Está al día? -------------------------------------------------------
    # Tres estados y no dos: "pagó pero su ciclo terminó" no es lo mismo que
    # "no ha pagado nunca" y tampoco es estar al día. Sin el tercero, un cliente
    # con el plan vencido seguía saliendo en verde y trabajando gratis.
    vencido = bool(pagado and dias is not None and dias < 0)
    if not pagado:
        situacion = "pendiente"
    elif vencido:
        situacion = "vencido"
    else:
        situacion = "al_dia"

    # --- Motivo --------------------------------------------------------------
    motivo: str | None = None
    if situacion == "vencido":
        motivo = "vencido"
    elif not pagado:
        guardado = (getattr(client, "unpaid_reason", None) or "").strip() or None
        if guardado in MOTIVO_TEXTO:
            motivo = guardado
        elif paid_at is None:
            # Nunca cobró nada: es un alta, se sepa o no lo que dice la columna.
            motivo = "alta"

    desde = getattr(client, "unpaid_since", None)
    if situacion == "vencido" and proximo is not None:
        desde = datetime.combine(proximo, datetime.min.time(), tzinfo=timezone.utc)
    elif not pagado and desde is None:
        desde = getattr(client, "created_at", None) if paid_at is None else paid_at

    # --- ¿Se le bloquea el perfil? ------------------------------------------
    # Solo por falta de pago REAL. Un cliente con la suscripción viva de Stripe
    # NUNCA se bloquea aunque la ficha se quede rancia un rato: el cobro está
    # domiciliado y bloquear al que sí paga es el peor fallo posible aquí.
    bloqueado = (situacion != "al_dia") and not suscrito

    previsto = _importe_previsto(client, marca)
    return {
        "situacion": situacion,            # al_dia | pendiente | vencido
        "bloqueado": bloqueado,
        "motivo": motivo,                  # alta | cancelado | fallido | vencido | None
        "motivo_corto": MOTIVO_CORTO.get(motivo or "", "Falta pago"),
        "motivo_texto": MOTIVO_TEXTO.get(motivo or "",
                                         "Falta el pago de su plan."),
        "desde": desde,
        "ultimo_pago_en": paid_at,
        "metodo": getattr(client, "payment_method", None),
        "metodo_label": METODO_LABEL.get(getattr(client, "payment_method", None) or "",
                                         None),
        "cadencia": periodo,
        "cadencia_label": CADENCIA_LABEL.get(periodo, periodo),
        "proximo_pago": proximo,
        "dias_para_pago": dias,
        # "Toca cobrar ya": el MISMO criterio que la alerta y que el enlace de
        # pago (services/renewals.is_due), no una segunda fórmula.
        "toca_cobrar": (not pagado) or (dias is not None and dias <= RENEWAL_WARN_DAYS),
        "importe_previsto_cents": previsto,
        # Una suscripción viva se cobra sola: ni aviso, ni bloqueo, ni enlace.
        "domiciliado": suscrito,
    }


def historial(db: Session, client: Client) -> dict:
    """Lo que el libro de caja sabe de este cliente. UNA consulta.

    Se mira por ficha Y por email, igual que la pasarela: un cliente que pagó
    con otro correo tiene filas sin `client_id`, y contarlas solo por la ficha
    le daba un "0 € pagados" a quien llevaba tres meses pagando.
    """
    email = (getattr(client, "email", None) or "").strip().lower()
    suyos = [Payment.client_id == client.id]
    if email:
        suyos.append(func.lower(Payment.customer_email) == email)
    filas = list(db.scalars(
        select(Payment)
        .where(or_(*suyos), Payment.status.in_(("paid", "refunded")),
               Payment.livemode.is_(True))
        .order_by(Payment.paid_at.desc().nullslast())
        .limit(200)
    ))
    cobrados = [p for p in filas if p.status == "paid"]
    devueltos = [p for p in filas if p.status == "refunded"]
    total = sum(p.amount_cents or 0 for p in cobrados) - \
        sum(p.amount_cents or 0 for p in devueltos)
    ultimo = cobrados[0] if cobrados else None
    return {
        "total_cents": total,
        "num_pagos": len(cobrados),
        "ultimo": None if ultimo is None else {
            "id": ultimo.id,
            "amount_cents": ultimo.amount_cents,
            "paid_at": ultimo.paid_at,
            "kind": ultimo.kind,
            "description": ultimo.description,
            "method": _metodo_de_movimiento(ultimo),
        },
        "primero_en": cobrados[-1].paid_at if cobrados else None,
    }


def _metodo_de_movimiento(pago: Payment) -> str:
    """De qué vía entró ese movimiento. Lo de Stripe es stripe; lo de fuera, lo
    que el coach anotó (va en la descripción: "Transferencia · registrado…")."""
    if pago.kind != "manual":
        return "stripe"
    texto = (pago.description or "").lower()
    for clave in ("efectivo", "transferencia", "bizum"):
        if texto.startswith(clave):
            return clave
    return "otro"


def marcar_impago(client: Client, motivo: str, *, cuando: datetime | None = None) -> None:
    """Deja al cliente en PENDIENTE con su motivo. Una sola puerta para los
    tres sitios que lo hacen (baja de suscripción, cobro fallido, alta sin
    cobrar): repartido, cada uno sellaba unas columnas y no otras.

    No pisa un motivo ANTERIOR más grave con uno genérico: si ya constaba una
    baja, un cobro fallido posterior no la convierte en "alta sin cobrar".
    """
    antes = client.unpaid_reason
    client.payment_status = "pending"
    if motivo in MOTIVO_TEXTO:
        client.unpaid_reason = motivo
    # "Debe desde" es la fecha del PRIMER impago de esta racha, no la del
    # último reintento: Stripe reintenta una tarjeta rechazada varios días y
    # cada reintento fallido habría movido la fecha hacia adelante, dejando
    # para siempre un "debe desde hoy" a quien lleva tres semanas sin pagar.
    if client.unpaid_since is None or (motivo and motivo != antes):
        client.unpaid_since = cuando or datetime.now(timezone.utc)


def marcar_pagado(client: Client, *, metodo: str | None = None,
                  cuando: datetime | None = None) -> None:
    """Deja al cliente AL DÍA y borra el rastro del impago.

    El motivo y el "debe desde" se limpian SIEMPRE al cobrar: dejarlos puestos
    hacía que la ficha de alguien que acaba de pagar siguiera diciendo "canceló
    su suscripción" —cierto ayer, falso hoy— y el rojo del listado no se iba.
    Los avisos de renovación también se re-arman: el ciclo empieza de cero.
    """
    client.payment_status = "paid"
    if cuando is not None and (client.paid_at is None or cuando > client.paid_at):
        client.paid_at = cuando
    if metodo:
        client.payment_method = metodo
    client.unpaid_reason = None
    client.unpaid_since = None
    client.renewal_reminder_sent_at = None
    client.payment_notice_sent_at = None


def enlace_de_pago(client: Client, base_url: str) -> str:
    """Su enlace ESTABLE de pago. En ventana de renovación vuelve a abrir un
    checkout aunque la ficha diga "paid" (routers/stripe_router.pay_link), así
    que sirve igual para cobrar el alta y para renovar."""
    return f"{base_url.rstrip('/')}/api/pay/{client.portal_token}"


def euros(cents: int | None) -> str:
    """Céntimos → "129,00 €" (formato español, para avisos y pantallas)."""
    return f"{(cents or 0) / 100:.2f}".replace(".", ",") + " €"


def dias_de_cadencia(billing_period: str | None) -> int | None:
    """Cada cuántos días le toca pagar, o None si no se renueva sola."""
    from app.services.renewals import BILLING_DAYS

    return BILLING_DAYS.get(billing_period or "")


def proximo_desde(paid_at: datetime | None, billing_period: str | None) -> date | None:
    """Fecha del PRÓXIMO pago a partir de uno dado. La usa el formulario del
    cobro a mano para decir, antes de anotar nada, cuándo tocará el siguiente."""
    dias = dias_de_cadencia(billing_period)
    if paid_at is None or dias is None:
        return None
    return paid_at.date() + timedelta(days=dias)
