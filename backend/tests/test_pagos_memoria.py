"""EL PAGO DEL CLIENTE, CON MEMORIA Y CON CONSECUENCIAS.

Hasta esta ronda la ficha sabía dos cosas del dinero —"pagado" o "pendiente" y
la fecha del último cobro, sin importe— y con eso no se responde a lo que el
coach pregunta delante de un cliente. Además, un impago no tenía consecuencia
ninguna: el sistema seguía trabajando igual.

Lo que se cubre aquí, y por qué cada cosa:

  1. TRES situaciones y no dos. "Pagó y su ciclo ya terminó" salía en VERDE:
     el cliente seguía recibiendo la asesoría sin que nada lo dijera.
  2. Una suscripción VIVA de Stripe no se bloquea nunca. Bloquear al que sí
     paga (porque la ficha va un rato por detrás del cobro domiciliado) es el
     peor fallo posible de toda esta ronda.
  3. El motivo del impago se BORRA al cobrar. Dejarlo puesto hacía que la ficha
     de quien acaba de pagar siguiera diciendo "canceló su suscripción".
  4. "Debe desde" es la fecha del PRIMER impago de la racha, no la del último
     reintento: Stripe reintenta una tarjeta rechazada varios días.
  5. El cobro a mano avisa CON SU IMPORTE y sella por dónde entró el dinero.
  6. El alta avisa al coach (antes solo avisaba la que venía con pago de Stripe).
  7. El portal del cliente lleva el aviso con su enlace, y NO lo lleva si está
     al día o si se le cobra solo.
  8. La alerta del panel dice POR QUÉ debe y CUÁNTO.
"""
import os
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

from app.models import Client
from app.services import payment_profile as pp


# ------------------------------------------------------------- utilidades ---

class _Marca:
    """Lo mínimo que `payment_profile` le pregunta a una marca."""

    def __init__(self, precios=None):
        self.precios = precios if precios is not None else {
            "full": {"1m": 12900, "3m": 33000}, "train": {"1m": 6900},
        }

    def importe(self, tier, period):
        return (self.precios.get(tier) or {}).get(period)

    def label(self, tier):
        return {"full": "DQR Full", "train": "DQR Train"}.get(tier, tier)


class _Ficha:
    """Una ficha de mentira con solo las columnas del dinero."""

    def __init__(self, **kw):
        self.payment_status = "paid"
        self.paid_at = datetime.now(timezone.utc)
        self.package_tier = "full"
        self.billing_period = "1m"
        self.stripe_subscription_id = None
        self.payment_method = None
        self.unpaid_reason = None
        self.unpaid_since = None
        self.renewal_reminder_sent_at = None
        self.payment_notice_sent_at = None
        self.created_at = datetime.now(timezone.utc) - timedelta(days=60)
        self.portal_token = "tok"
        self.__dict__.update(kw)


HOY = date(2026, 9, 23)


# ================================================ 1 · tres situaciones ======

def test_al_dia_ni_bloquea_ni_pide_cobrar():
    e = pp.estado(_Ficha(paid_at=datetime(2026, 9, 20, tzinfo=timezone.utc)),
                  _Marca(), HOY)
    assert e["situacion"] == "al_dia"
    assert e["bloqueado"] is False
    assert e["toca_cobrar"] is False
    assert e["motivo"] is None


def test_el_ciclo_vencido_no_es_estar_al_dia():
    """EL FALLO DE FONDO: un cliente que pagó su mes hace 45 días salía en
    VERDE en todas las pantallas —"Pagado"— y seguía recibiendo la asesoría."""
    e = pp.estado(_Ficha(paid_at=datetime(2026, 8, 1, tzinfo=timezone.utc)),
                  _Marca(), HOY)
    assert e["situacion"] == "vencido"
    assert e["bloqueado"] is True
    assert e["motivo"] == "vencido"
    assert e["dias_para_pago"] < 0
    # Y dice CUÁNTO le toca, que es lo que hay que cobrarle.
    assert e["importe_previsto_cents"] == 12900


def test_alta_sin_cobrar_es_un_alta_aunque_no_conste_el_motivo():
    e = pp.estado(_Ficha(payment_status="pending", paid_at=None), _Marca(), HOY)
    assert e["situacion"] == "pendiente"
    assert e["motivo"] == "alta"
    assert e["bloqueado"] is True
    assert "Nunca ha pagado" in e["motivo_texto"]


def test_la_suscripcion_viva_nunca_bloquea():
    """El cobro está DOMICILIADO: bloquear al que sí paga porque la ficha va un
    rato por detrás del webhook sería el peor fallo posible de esta ronda."""
    e = pp.estado(_Ficha(payment_status="pending", billing_period="oferta",
                         stripe_subscription_id="sub_123"), _Marca(), HOY)
    assert e["domiciliado"] is True
    assert e["bloqueado"] is False


def test_el_motivo_guardado_manda_sobre_la_deduccion():
    f = _Ficha(payment_status="pending", unpaid_reason="cancelado",
               paid_at=datetime(2026, 8, 1, tzinfo=timezone.utc))
    e = pp.estado(f, _Marca(), HOY)
    assert e["motivo"] == "cancelado"
    assert e["motivo_corto"] == "Canceló"


def test_un_plan_que_su_marca_no_vende_no_inventa_precio():
    """Un importe inventado en la pantalla del cobro es peor que ninguno: el
    coach lo daría por bueno y cobraría de menos."""
    e = pp.estado(_Ficha(package_tier="train", billing_period="6m",
                         payment_status="pending", paid_at=None), _Marca(), HOY)
    assert e["importe_previsto_cents"] is None


# ============================================ 2 · cobrar limpia el rastro ===

def test_cobrar_borra_el_motivo_y_sella_el_metodo():
    """Sin esta limpieza, la ficha de quien ACABA de pagar seguía diciendo
    "canceló su suscripción" y el rojo del listado no se iba."""
    f = _Ficha(payment_status="pending", unpaid_reason="cancelado",
               unpaid_since=datetime(2026, 9, 1, tzinfo=timezone.utc),
               renewal_reminder_sent_at=datetime.now(timezone.utc),
               payment_notice_sent_at=datetime.now(timezone.utc))
    pp.marcar_pagado(f, metodo="bizum", cuando=datetime(2026, 9, 23, tzinfo=timezone.utc))
    assert f.payment_status == "paid"
    assert f.unpaid_reason is None and f.unpaid_since is None
    assert f.payment_method == "bizum"
    # Los avisos del ciclo se re-arman: empieza un ciclo nuevo.
    assert f.renewal_reminder_sent_at is None
    assert f.payment_notice_sent_at is None


def test_debe_desde_es_el_primer_impago_no_el_ultimo_reintento():
    """Stripe reintenta una tarjeta rechazada varios días. Si cada reintento
    moviera la fecha, quien lleva tres semanas sin pagar saldría siempre como
    "debe desde hoy"."""
    f = _Ficha()
    primero = datetime(2026, 9, 1, tzinfo=timezone.utc)
    pp.marcar_impago(f, "fallido", cuando=primero)
    pp.marcar_impago(f, "fallido", cuando=datetime(2026, 9, 5, tzinfo=timezone.utc))
    pp.marcar_impago(f, "fallido", cuando=datetime(2026, 9, 9, tzinfo=timezone.utc))
    assert f.unpaid_since == primero
    # Pero un motivo DISTINTO sí abre una racha nueva: pasar de un cobro
    # fallido a una baja es otra historia y otra fecha.
    pp.marcar_impago(f, "cancelado", cuando=datetime(2026, 9, 12, tzinfo=timezone.utc))
    assert f.unpaid_since == datetime(2026, 9, 12, tzinfo=timezone.utc)


# ======================================================== 3 · API (ficha) ===

@pytest.fixture()
def http():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def _auth():
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token(os.environ.get('ADMIN_1_USER', 'coach1'))}"}


@pytest.fixture()
def cliente():
    """Un cliente real en la base, borrado al terminar."""
    from app.db import SessionLocal
    from app.security import new_portal_token

    db = SessionLocal()
    c = Client(full_name="Pago Memoria", email=f"pagomem-{uuid.uuid4().hex[:8]}@x.com",
               package_tier="full", billing_period="1m", status="active",
               portal_token="pendiente", payment_status="pending")
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    db.commit()
    cid = c.id
    try:
        yield cid
    finally:
        from app.models import Payment

        db.query(Payment).filter(Payment.client_id == cid).delete()
        db.query(Client).filter(Client.id == cid).delete()
        db.commit()
        db.close()


def test_la_ficha_lleva_su_bloque_de_pago(http, cliente):
    r = http.get(f"/api/clients/{cliente}", headers=_auth())
    assert r.status_code == 200, r.text
    pago = r.json()["pago"]
    assert pago["situacion"] == "pendiente"
    assert pago["bloqueado"] is True
    assert pago["motivo"] == "alta"
    assert pago["cadencia_label"] == "cada mes"


def test_el_listado_tambien_lo_lleva(http, cliente):
    """Es lo que pinta el rojo de FALTA PAGO en la cartera: si no viaja en el
    listado, el coach solo lo descubre al entrar en la ficha."""
    r = http.get("/api/clients", headers=_auth())
    assert r.status_code == 200, r.text
    fila = next(c for c in r.json() if c["id"] == cliente)
    assert fila["pago"]["bloqueado"] is True


def test_el_estado_de_pago_trae_enlace_importe_y_proximo(http, cliente):
    r = http.get(f"/api/clients/{cliente}/pago", headers=_auth())
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["enlace_pago"].endswith(f"/api/pay/{_token_de(cliente)}")
    assert d["importe_previsto_cents"] == 12900  # tarifa Full mensual de DQR
    assert d["plan_label"]
    # Cuándo tocaría el SIGUIENTE si se anota un cobro hoy: el formulario lo
    # dice ANTES de guardar nada, que es cuando sirve de algo.
    assert d["proximo_si_cobro_hoy"] is not None


def _token_de(client_id: int) -> str:
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        return db.get(Client, client_id).portal_token
    finally:
        db.close()


def test_ver_la_ficha_sin_pagar_queda_registrado(http, cliente):
    """La salida del bloqueo existe porque hay obligaciones que no pueden
    esperar a un cobro (RGPD), pero deja constancia: si no, se usa siempre y el
    bloqueo deja de significar nada."""
    from app.db import SessionLocal
    from app.models import AuditLog

    r = http.post(f"/api/clients/{cliente}/acceso-sin-pago", headers=_auth())
    assert r.status_code == 200, r.text
    db = SessionLocal()
    try:
        fila = db.query(AuditLog).filter(
            AuditLog.entity == "client", AuditLog.entity_id == cliente,
            AuditLog.event == "perfil_abierto_sin_pago").first()
        assert fila is not None
        # Y NO es un "marcar pagado" encubierto.
        assert db.get(Client, cliente).payment_status == "pending"
    finally:
        db.close()


# ================================================= 4 · el cobro a mano ======

def test_el_cobro_a_mano_avisa_con_el_importe_y_sella_la_via(http, cliente, monkeypatch):
    """Lo de Stripe ya avisaba; lo de fuera entraba en el libro sin que sonara
    nada — con dos admins, el segundo se enteraba al abrir el panel."""
    from app.db import SessionLocal
    from app.services import push as push_svc

    avisos = []
    monkeypatch.setattr(push_svc, "notify_coach_cobro_anotado",
                        lambda db, c, **kw: avisos.append(kw))

    r = http.post("/api/payments/manual", headers=_auth(), json={
        "client_id": cliente, "amount_eur": 129.0, "method": "bizum"})
    assert r.status_code == 201, r.text
    assert avisos and avisos[0]["amount_cents"] == 12900
    assert avisos[0]["metodo"] == "bizum"

    db = SessionLocal()
    try:
        c = db.get(Client, cliente)
        assert c.payment_status == "paid"
        assert c.payment_method == "bizum"     # la FICHA dice por dónde pagó
        assert c.unpaid_reason is None          # y el rastro del impago se va
    finally:
        db.close()


def test_el_titulo_del_aviso_del_cobro_lleva_el_importe():
    """El push es "💰 +129,00 € · Cobro anotado": el importe en el TÍTULO, que
    es lo único que se lee de una notificación en el móvil."""
    from app.services.payment_profile import euros

    assert euros(12900) == "129,00 €"
    assert euros(None) == "0,00 €"


def test_el_alta_avisa_al_coach(http, monkeypatch):
    """Un alta del sábado se descubría el lunes: solo avisaba la que venía con
    pago de Stripe."""
    from app.db import SessionLocal
    from app.services import push as push_svc

    avisos = []
    monkeypatch.setattr(push_svc, "notify_coach_cliente_nuevo",
                        lambda db, c, **kw: avisos.append((c.full_name, kw)))
    email = f"altaaviso-{uuid.uuid4().hex[:8]}@x.com"
    r = http.post("/api/clients", headers=_auth(), json={
        "full_name": "Alta Con Aviso", "email": email, "package_tier": "full",
        "billing_period": "1m"})
    assert r.status_code in (200, 201), r.text
    assert avisos and avisos[0][0] == "Alta Con Aviso"
    db = SessionLocal()
    try:
        from app.models import EmailLog

        c = db.query(Client).filter(Client.email == email).first()
        # El alta intenta mandarle su acceso al portal y deja fila en el
        # registro de correos: sin borrarla primero, el DELETE del cliente
        # choca con su clave ajena.
        db.query(EmailLog).filter(EmailLog.client_id == c.id).delete()
        db.delete(c)
        db.commit()
    finally:
        db.close()


# ===================================================== 5 · portal cliente ===

def test_el_portal_avisa_de_pagar_con_su_enlace(http, cliente):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        c = db.get(Client, cliente)
        token = c.portal_token
        db.commit()
    finally:
        db.close()

    r = http.get(f"/api/p/{token}/state")
    assert r.status_code == 200, r.text
    aviso = r.json()["pago_pendiente"]
    assert aviso is not None
    assert aviso["url_pago"].endswith(f"/api/pay/{token}")
    assert aviso["importe_cents"] == 12900
    # No se le cuenta el motivo interno: el portal no es el panel del coach.
    assert "motivo" not in aviso


def test_el_aviso_del_portal_se_retira_al_cobrar(http, cliente):
    """"Se va la notificación cuando el sistema ve que ese cliente pagó": por
    eso vive en el ESTADO y no como una notificación suelta."""
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        c = db.get(Client, cliente)
        token = c.portal_token
        pp.marcar_pagado(c, metodo="stripe", cuando=datetime.now(timezone.utc))
        db.commit()
    finally:
        db.close()
    r = http.get(f"/api/p/{token}/state")
    assert r.json()["pago_pendiente"] is None


def test_al_domiciliado_no_se_le_pide_que_pague(http, cliente):
    """Pedirle que pague algo que tiene domiciliado es la mejor forma de que
    pague dos veces."""
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        c = db.get(Client, cliente)
        token = c.portal_token
        c.stripe_subscription_id = "sub_viva"
        db.commit()
    finally:
        db.close()
    r = http.get(f"/api/p/{token}/state")
    assert r.json()["pago_pendiente"] is None


# ========================================================= 6 · la alerta ====

def test_la_alerta_dice_por_que_debe_y_cuanto():
    """Un impago sin motivo es un rojo que no se sabe atender: no se llama
    igual a quien se acaba de dar de baja que a un alta sin cobrar."""
    from app.db import SessionLocal
    from app.routers.alerts import client_alerts

    db = SessionLocal()
    try:
        c = _Ficha(payment_status="pending", unpaid_reason="cancelado",
                   paid_at=datetime(2026, 8, 1, tzinfo=timezone.utc))
        # Una ficha de verdad: la alerta consulta la marca del cliente.
        cliente = Client(full_name="Alerta Pago",
                         email=f"alertapago-{uuid.uuid4().hex[:8]}@x.com",
                         package_tier="full", billing_period="1m",
                         status="active", portal_token=f"t{uuid.uuid4().hex}",
                         payment_status="pending", unpaid_reason="cancelado")
        db.add(cliente)
        db.commit()
        try:
            avisos = [a for a in client_alerts(db, cliente)
                      if "payment_pending" in str(a.get("key", ""))]
            assert avisos, "la alerta de pago no salió"
            a = avisos[0]
            assert "Canceló su suscripción" in a["message"]
            assert "129,00 €" in a["message"]      # cuánto
            assert "cada mes" in a["message"]      # cada cuánto
            # Una BAJA es urgente: el dinero ya se perdió una vez y el cliente
            # sigue recibiendo la asesoría.
            assert a["severity"] == "alta"
        finally:
            db.delete(cliente)
            db.commit()
    finally:
        db.close()


# ================================ 7 · el push de "toca pagar" al cliente ====

def test_el_push_de_pago_al_cliente_va_una_vez_por_ciclo(monkeypatch):
    """El portal INSISTE (su aviso está siempre mientras deba); el push no.
    Cinco notificaciones al día es la forma más rápida de que el cliente apague
    las notificaciones y deje de enterarse de nada.

    Y el sello es PROPIO, no el del email de renovación: ese solo se marca si
    el correo SALE de verdad, así que compartirlo habría matado el reintento
    del día siguiente cuando el SMTP se cae.
    """
    from app.db import SessionLocal
    from app.security import new_portal_token
    from app.services import jobs
    from app.services import push as push_svc

    db = SessionLocal()
    c = Client(full_name="Push Pago", email=f"pushpago-{uuid.uuid4().hex[:8]}@x.com",
               package_tier="full", billing_period="1m", status="active",
               portal_token="pendiente", payment_status="paid",
               paid_at=datetime.now(timezone.utc) - timedelta(days=40))
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    db.commit()
    cid = c.id
    todos = []
    monkeypatch.setattr(push_svc, "notify_client_toca_pagar",
                        lambda db, cl, **kw: (todos.append((cl.id, kw)), 1)[1])
    # SOLO los de ESTE cliente: el mantenimiento recorre la cartera entera, y
    # cualquier otra ficha con el ciclo vencido (las hay, es un estado normal)
    # contaría en el recuento y haría el test dependiente del orden.
    mios = lambda: [kw for cid_, kw in todos if cid_ == cid]  # noqa: E731
    try:
        jobs.run_daily_maintenance(db)
        assert len(mios()) == 1, "no se avisó al cliente de que le toca pagar"
        assert mios()[0]["vencido"] is True
        assert mios()[0]["importe_cents"] == 12900
        assert f"/api/pay/{c.portal_token}" in mios()[0]["url_pago"]
        db.expire_all()
        assert db.get(Client, cid).payment_notice_sent_at is not None

        # Segunda vuelta del mantenimiento: NO se repite.
        jobs.run_daily_maintenance(db)
        assert len(mios()) == 1

        # Pero un COBRO NUEVO re-arma el aviso del ciclo siguiente.
        cl = db.get(Client, cid)
        pp.marcar_pagado(cl, metodo="stripe", cuando=datetime.now(timezone.utc))
        cl.paid_at = datetime.now(timezone.utc) - timedelta(days=40)
        db.commit()
        jobs.run_daily_maintenance(db)
        assert len(mios()) == 2
    finally:
        from app.models import DailyLog, EmailLog, Period, WorkoutLog

        for periodo in db.query(Period).filter(Period.client_id == cid).all():
            logs = db.query(DailyLog).filter(DailyLog.period_id == periodo.id).all()
            for log in logs:
                db.query(WorkoutLog).filter(WorkoutLog.daily_log_id == log.id).delete()
            db.query(DailyLog).filter(DailyLog.period_id == periodo.id).delete()
        db.query(Period).filter(Period.client_id == cid).delete()
        db.query(EmailLog).filter(EmailLog.client_id == cid).delete()
        db.query(Client).filter(Client.id == cid).delete()
        db.commit()
        db.close()
