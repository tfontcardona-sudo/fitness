"""El barrido de alertas del panel, sin una consulta por cliente.

`/api/alerts` recorre TODOS los clientes y el panel lo refresca cada 20 s (los
avisos programados también lo recorren). Cada cliente disparaba siete consultas
—planes, períodos, feedback, diarios, series, peticiones, videollamadas—: con
60 fichas eran 432 consultas y ~400 ms por refresco.

Ahora el listado precarga esas filas de una vez (`_EnLote`). Lo que estos tests
vigilan es lo único que importa: que el atajo devuelva EXACTAMENTE las mismas
alertas que consultar cliente a cliente, hoy y cuando alguien añada una alerta
nueva que consulte algo más.
"""
import uuid
import warnings
from datetime import date, timedelta

warnings.filterwarnings("ignore")


def _clientes_en_varios_estados(db):
    """Un cliente de cada fase del ciclo: es donde divergen las consultas."""
    from app.models import (ChangeRequest, Client, DailyLog, FeedbackDoc, Period,
                            Plan, VideoCall)

    hoy = date.today()
    marca = uuid.uuid4().hex[:8]
    creados = []

    def _nuevo(nombre, **over):
        campos = dict(full_name=f"Lote {nombre} {marca}",
                      email=f"lote-{nombre}-{marca}@test.local",
                      package_tier="full", billing_period="1m", status="active",
                      portal_token=f"tok-{nombre}-{marca}", payment_status="paid",
                      sex="male", birth_date=hoy - timedelta(days=365 * 30),
                      height_cm=178, start_weight_kg=80, goal_type="fat_loss",
                      level="intermediate")
        campos.update(over)
        c = Client(**campos)
        db.add(c)
        db.flush()
        creados.append(c)
        return c

    # 1) Recién dado de alta: sin plan ni anamnesis.
    _nuevo("sinplan")

    # 2) Con plan publicado y período abierto con registros reales.
    con_periodo = _nuevo("activo")
    plan = Plan(client_id=con_periodo.id, month_index=1, version=1,
                status="published", goal_type="fat_loss", generated_by="test",
                nutrition_json={}, training_json={}, education_json={})
    db.add(plan)
    db.flush()
    per = Period(client_id=con_periodo.id, plan_id=plan.id, period_index=1,
                 status="open", starts_on=hoy - timedelta(days=9),
                 ends_on=hoy + timedelta(days=4))
    db.add(per)
    db.flush()
    for d in range(3):
        db.add(DailyLog(period_id=per.id, log_date=hoy - timedelta(days=d),
                        weight_kg=80.0 - d, sleep_hours=7, diet_adherence="yes"))
    # 3) Revisión analizada con feedback SIN enviar, petición de cambio abierta
    #    y videollamada propuesta: los tres caminos que quedaban por cubrir.
    cerrado = _nuevo("revisado")
    plan2 = Plan(client_id=cerrado.id, month_index=1, version=1,
                 status="published", goal_type="fat_loss", generated_by="test",
                 nutrition_json={}, training_json={}, education_json={})
    db.add(plan2)
    db.flush()
    per2 = Period(client_id=cerrado.id, plan_id=plan2.id, period_index=1,
                  status="analyzed", starts_on=hoy - timedelta(days=20),
                  ends_on=hoy - timedelta(days=7))
    db.add(per2)
    db.flush()
    db.add(FeedbackDoc(period_id=per2.id, kind="biweekly",
                       content_json={"analysis": "x"}, sent_at=None))
    db.add(ChangeRequest(client_id=cerrado.id, status="open",
                         message="¿Puedo cambiar el pollo por pavo?"))
    db.add(VideoCall(client_id=cerrado.id, period_index=1, status="proposed",
                     scheduled_at=None))
    db.commit()
    return creados


def _borra(db, clientes):
    from sqlalchemy import delete

    from app.models import (ChangeRequest, Client, DailyLog, FeedbackDoc, Period,
                            Plan, VideoCall)

    ids = [c.id for c in clientes]
    per_ids = [p.id for p in db.query(Period).filter(Period.client_id.in_(ids))]
    if per_ids:
        db.execute(delete(FeedbackDoc).where(FeedbackDoc.period_id.in_(per_ids)))
        db.execute(delete(DailyLog).where(DailyLog.period_id.in_(per_ids)))
    db.execute(delete(VideoCall).where(VideoCall.client_id.in_(ids)))
    db.execute(delete(ChangeRequest).where(ChangeRequest.client_id.in_(ids)))
    db.execute(delete(Period).where(Period.client_id.in_(ids)))
    db.execute(delete(Plan).where(Plan.client_id.in_(ids)))
    db.execute(delete(Client).where(Client.id.in_(ids)))
    db.commit()


def test_el_lote_da_exactamente_las_mismas_alertas_que_ir_cliente_a_cliente():
    from app.db import SessionLocal
    from app.routers.alerts import _EnLote, client_alerts

    db = SessionLocal()
    clientes = _clientes_en_varios_estados(db)
    try:
        uno_a_uno = [client_alerts(db, c, titulos_producto=[]) for c in clientes]
        lote = _EnLote(db, clientes)
        en_lote = [client_alerts(db, c, titulos_producto=[], datos=lote)
                   for c in clientes]
        assert uno_a_uno == en_lote
        # Y que la muestra no sea trivial: alguno tiene que avisar de algo.
        assert any(uno_a_uno), "los clientes de prueba no generan ninguna alerta"
    finally:
        _borra(db, clientes)
        db.close()


def test_el_barrido_no_crece_con_el_numero_de_clientes():
    """La prueba de que el N+1 no vuelve: el mismo puñado de consultas para
    tres clientes que para uno."""
    import collections

    from sqlalchemy import event

    from app.db import SessionLocal, engine
    from app.routers.alerts import _EnLote, client_alerts

    db = SessionLocal()
    clientes = _clientes_en_varios_estados(db)
    consultas = collections.Counter()

    @event.listens_for(engine, "before_cursor_execute")
    def _cuenta(conn, cursor, statement, params, context, executemany):
        consultas["n"] += 1

    try:
        consultas.clear()
        for c in clientes:
            client_alerts(db, c, titulos_producto=[])
        sueltas = consultas["n"]

        consultas.clear()
        lote = _EnLote(db, clientes)
        for c in clientes:
            client_alerts(db, c, titulos_producto=[], datos=lote)
        agrupadas = consultas["n"]

        # Precargar cuesta un número FIJO de consultas (una por tabla), así que
        # con tres clientes ya tiene que salir a cuenta; con sesenta, la
        # diferencia medida fue de 431 a 8.
        assert agrupadas < sueltas, (agrupadas, sueltas)
        assert agrupadas <= 10, f"el lote hace {agrupadas} consultas: ¿volvió el N+1?"
    finally:
        event.remove(engine, "before_cursor_execute", _cuenta)
        _borra(db, clientes)
        db.close()
