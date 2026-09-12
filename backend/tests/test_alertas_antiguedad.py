"""La campana ordenada "de menos recientes a más recientes" (petición del
dueño): quien lleva MÁS tiempo con un aviso pendiente sale PRIMERO, no el
orden alfabético de siempre. Para eso cada aviso lleva ahora un `since` — la
fecha en que el problema empezó a existir, no cuándo se calculó (que es
siempre "hoy") — y `list_alerts` ordena por esa fecha antes que por severidad
o nombre.

Estos tests cubren tres cosas que un cambio así puede romper en silencio:
1. que `since` sea la fecha REAL de cada aviso concreto (no una que se cuele
   por error, como "hoy"),
2. que un mensaje que antes llevaba un número FIJO ("30 días") ahora cuente
   los días de verdad transcurridos,
3. que el orden global respete esa fecha, con los avisos SIN fecha propia (un
   choque estructural, no una espera) cayendo al final.
"""
import uuid
from datetime import date, timedelta

import warnings

warnings.filterwarnings("ignore")


def _cliente(db, nombre, marca, **over):
    from app.models import Client

    campos = dict(full_name=f"{nombre} {marca}",
                  email=f"{nombre.lower()}-{marca}@test.local",
                  package_tier="full", billing_period="1m", status="active",
                  portal_token=f"tok-{nombre.lower()}-{marca}", payment_status="paid")
    campos.update(over)
    c = Client(**campos)
    db.add(c)
    db.flush()
    return c


def _plan_publicado(db, client):
    from app.models import Plan

    plan = Plan(client_id=client.id, month_index=1, version=1, status="published",
                goal_type="fat_loss", generated_by="test",
                nutrition_json={}, training_json={}, education_json={})
    db.add(plan)
    db.flush()
    return plan


def _borra(db, clientes):
    from sqlalchemy import delete

    from app.models import Client, DailyLog, Period, Plan, VideoCall

    ids = [c.id for c in clientes]
    per_ids = [p.id for p in db.query(Period).filter(Period.client_id.in_(ids))]
    if per_ids:
        db.execute(delete(DailyLog).where(DailyLog.period_id.in_(per_ids)))
    db.execute(delete(VideoCall).where(VideoCall.client_id.in_(ids)))
    db.execute(delete(Period).where(Period.client_id.in_(ids)))
    db.execute(delete(Plan).where(Plan.client_id.in_(ids)))
    db.execute(delete(Client).where(Client.id.in_(ids)))
    db.commit()


def test_period_overdue_since_es_el_fin_del_periodo_no_hoy():
    """"Su revisión venció hace N días" no llevaba NINGUNA fecha propia. Para
    ordenar por antigüedad hace falta el día en que el período TERMINÓ
    (`ends_on`) — si se colara "hoy" por error, el aviso nunca envejecería."""
    from app.db import SessionLocal
    from app.models import Period
    from app.routers.alerts import client_alerts

    db = SessionLocal()
    hoy = date.today()
    marca = uuid.uuid4().hex[:8]
    c = _cliente(db, "Vencido", marca)
    try:
        plan = _plan_publicado(db, c)
        ends_on = hoy - timedelta(days=10)
        per = Period(client_id=c.id, plan_id=plan.id, period_index=1, status="open",
                     starts_on=ends_on - timedelta(days=14), ends_on=ends_on)
        db.add(per)
        db.commit()

        avisos = client_alerts(db, c, today=hoy, titulos_producto=[])
        overdue = next(a for a in avisos if a["kind"] == "period_overdue")
        assert overdue["since"] == ends_on.isoformat()
        assert overdue["since"] != hoy.isoformat()
    finally:
        _borra(db, [c])
        db.close()


def test_client_inactive_dice_los_dias_reales_no_30_fijo():
    """El mensaje decía SIEMPRE "30 días" (el umbral que dispara el estado),
    fuera cual fuera el tiempo real transcurrido: un inactivo de hace 90 días
    se leía IGUAL que uno de ayer. Ahora cuenta desde la última fecha con
    contenido real de su último período (mismo criterio que "sin registros")."""
    from app.db import SessionLocal
    from app.models import DailyLog, Period
    from app.routers.alerts import client_alerts

    db = SessionLocal()
    hoy = date.today()
    marca = uuid.uuid4().hex[:8]
    c = _cliente(db, "Inactivo", marca, status="inactive")
    try:
        plan = _plan_publicado(db, c)
        ultimo_registro = hoy - timedelta(days=60)
        per = Period(client_id=c.id, plan_id=plan.id, period_index=1, status="analyzed",
                     starts_on=ultimo_registro - timedelta(days=5),
                     ends_on=ultimo_registro + timedelta(days=9))
        db.add(per)
        db.flush()
        db.add(DailyLog(period_id=per.id, log_date=ultimo_registro, weight_kg=78.0,
                        sleep_hours=7, diet_adherence="yes"))
        db.commit()

        avisos = client_alerts(db, c, today=hoy, titulos_producto=[])
        inactivo = next(a for a in avisos if a["kind"] == "client_inactive")
        assert inactivo["since"] == ultimo_registro.isoformat()
        assert inactivo["message"] == "Inactivo · 60 días sin actividad"
        assert "30 días" not in inactivo["message"]
    finally:
        _borra(db, [c])
        db.close()


def test_list_alerts_ordena_de_menos_recientes_a_mas_recientes():
    """El orden por defecto de la campana: quien lleva MÁS tiempo pendiente
    sale PRIMERO. Tres avisos de antigüedad muy distinta —uno de hace ~100
    días, uno de hace ~5 y uno SIN fecha propia (un choque puntual, no una
    espera)— tienen que salir en ese orden, con el que no tiene `since`
    siempre al final de los tres."""
    from app.models import VideoCall
    from app.db import SessionLocal
    from app.models import DailyLog, Period
    from app.routers.alerts import list_alerts

    db = SessionLocal()
    hoy = date.today()
    marca = uuid.uuid4().hex[:8]
    # Los tres empiezan por "ZZOrden" para no rozar ningún cliente sembrado.
    viejo = _cliente(db, "ZZOrdenViejo", marca, status="inactive")
    medio = _cliente(db, "ZZOrdenMedio", marca)
    nuevo = _cliente(db, "ZZOrdenNuevo", marca)
    creados = [viejo, medio, nuevo]
    try:
        # A) Inactivo desde hace ~100 días: el más antiguo de los tres.
        plan_v = _plan_publicado(db, viejo)
        ultimo_v = hoy - timedelta(days=100)
        per_v = Period(client_id=viejo.id, plan_id=plan_v.id, period_index=1,
                       status="analyzed", starts_on=ultimo_v - timedelta(days=5),
                       ends_on=ultimo_v + timedelta(days=9))
        db.add(per_v)
        db.flush()
        db.add(DailyLog(period_id=per_v.id, log_date=ultimo_v, weight_kg=70.0,
                        sleep_hours=7, diet_adherence="yes"))

        # B) Revisión vencida desde hace ~5 días: el intermedio.
        plan_m = _plan_publicado(db, medio)
        ends_m = hoy - timedelta(days=5)
        per_m = Period(client_id=medio.id, plan_id=plan_m.id, period_index=1,
                       status="open", starts_on=ends_m - timedelta(days=14), ends_on=ends_m)
        db.add(per_m)

        # C) Videollamada agendada AYER, por confirmar: choque puntual, sin
        #    "desde cuándo" real que contar.
        _plan_publicado(db, nuevo)
        db.add(VideoCall(client_id=nuevo.id, period_index=1, status="scheduled",
                         scheduled_for=hoy - timedelta(days=1)))
        db.commit()

        alerts = list_alerts(db)["alerts"]
        idx_viejo = next(i for i, a in enumerate(alerts)
                         if a["client_id"] == viejo.id and a["kind"] == "client_inactive")
        idx_medio = next(i for i, a in enumerate(alerts)
                         if a["client_id"] == medio.id and a["kind"] == "period_overdue")
        idx_nuevo = next(i for i, a in enumerate(alerts)
                         if a["client_id"] == nuevo.id and a["kind"] == "video_call_confirm")

        assert alerts[idx_viejo]["since"] == ultimo_v.isoformat()
        assert alerts[idx_medio]["since"] == ends_m.isoformat()
        assert alerts[idx_nuevo]["since"] is None

        # El orden real: más antiguo primero, el que no tiene fecha al final.
        assert idx_viejo < idx_medio < idx_nuevo, (idx_viejo, idx_medio, idx_nuevo)
    finally:
        _borra(db, creados)
        db.close()
