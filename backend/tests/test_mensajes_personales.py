"""MENSAJES AL CLIENTE ADAPTADOS A SU SITUACIÓN.

El dueño: «que los mensajes a los clientes sean adaptados a la situación del
cliente, sobre datos suyos, preguntando o abordando desde la información que va
dando el cliente, para que se vea más atendido y supervisado… por ejemplo, si
se ve que duerme mal, pues pregunta eso; si no entrena lo que debe, pues
pregunta eso… si no hay nada que decir se mandará uno genérico».

Antes, la ronda diaria mandaba a TODA la cartera el mismo brief del pool con el
nombre cambiado. Ahora el tema sale de SUS datos, calculado con reglas (no por
un modelo: un modelo "vería" tendencias que no constan y le hablaría de un mal
sueño que nunca registró), y la IA solo lo REDACTA.

Cada test de aquí falla con el código anterior.
"""
import uuid
from datetime import date, timedelta

import pytest


def _db_available() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings

        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="Requiere PostgreSQL")


@pytest.fixture()
def db():
    from app.db import SessionLocal

    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture()
def cliente(db):
    """Un cliente con su plan y su quincena abierta, y limpieza al terminar."""
    from app.models import Client, Period, Plan
    from app.security import new_portal_token

    c = Client(full_name="Nuria Prats", email=f"msg-{uuid.uuid4().hex[:8]}@test.local",
               portal_token="tmp", status="active", package_tier="full",
               training_days=4, goal_type="fat_loss", phone="600000000")
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    plan = Plan(client_id=c.id, month_index=1, version=1, status="published")
    db.add(plan)
    db.flush()
    p = Period(client_id=c.id, plan_id=plan.id, period_index=1,
               starts_on=date.today() - timedelta(days=8),
               ends_on=date.today() + timedelta(days=6), status="open")
    db.add(p)
    db.commit()
    cid, pid = c.id, p.id
    yield c, p
    # La prueba de la baja RGPD borra el cliente ella misma, así que aquí nada
    # puede dar por hecho que siga existiendo: se limpia por ID y en orden.
    from app.models import DailyLog, WorkoutLog

    db.rollback()
    ids = [lg.id for lg in db.query(DailyLog).filter(DailyLog.period_id == pid)]
    if ids:
        db.query(WorkoutLog).filter(WorkoutLog.daily_log_id.in_(ids)).delete(
            synchronize_session=False)
    db.query(DailyLog).filter(DailyLog.period_id == pid).delete(synchronize_session=False)
    db.query(Period).filter(Period.client_id == cid).delete(synchronize_session=False)
    db.query(Plan).filter(Plan.client_id == cid).delete(synchronize_session=False)
    db.query(Client).filter(Client.id == cid).delete(synchronize_session=False)
    db.commit()


def _diario(db, periodo, dias_atras: int, serie: bool = False, **campos):
    from app.models import DailyLog, WorkoutLog

    lg = DailyLog(period_id=periodo.id, log_date=date.today() - timedelta(days=dias_atras),
                  **campos)
    db.add(lg)
    db.flush()
    if serie:
        from app.models import Exercise

        ex = db.query(Exercise).order_by(Exercise.id).first()
        db.add(WorkoutLog(daily_log_id=lg.id, exercise_id=ex.id if ex else 1,
                          set_number=1, reps=10, weight_kg=40.0))
    db.commit()
    return lg


def _semana_de_entrenos_al_dia(db, periodo):
    """Cuatro sesiones registradas: las que tiene pautadas. Sin esto, el tema
    del día sería «has entrenado menos de lo pautado» —correcto, y lo que el
    sistema debe decir primero—, y estas pruebas van de OTRA cosa."""
    for d in (1, 2, 3, 4):
        _diario(db, periodo, d, serie=True)


# ----------------------------------------------------------------- el foco --

def test_sin_nada_que_destacar_no_se_fuerza_un_tema(db, cliente):
    """Al cliente que va bien y al día NO se le inventa un problema: se le
    manda el brief general del día, que para eso está."""
    from app.services.client_focus import focos_de

    c, p = cliente
    for d in range(1, 8):
        _diario(db, p, d, weight_kg=70.0, sleep_hours=8.0, diet_adherence="yes",
                mood_1_5=4, fatigue_1_5=2)
    claves = {f.key for f in focos_de(db, c, hoy=date.today())}
    assert "sueno_bajo" not in claves and "adherencia_baja" not in claves
    assert "sin_registros" not in claves


def test_quien_duerme_poco_recibe_su_cifra_exacta(db, cliente):
    """«¿Qué tal duermes?» lo manda cualquiera. Lo que hace que el cliente se
    vea mirado es «te veo en 5,3 h de media esta semana»."""
    from app.services.client_focus import focos_de

    c, p = cliente
    for d, h in ((1, 5.0), (2, 5.5), (3, 5.5)):
        _diario(db, p, d, sleep_hours=h, weight_kg=70.0)
    foco = next(f for f in focos_de(db, c, hoy=date.today()) if f.key == "sueno_bajo")
    assert "5,3 h" in foco.dato
    assert "5,3 h" in foco.reserva            # también sin IA


def test_lo_que_el_cliente_ha_escrito_manda_sobre_sus_datos(db, cliente):
    """Si ha preguntado algo, el mensaje del día es responderle: por encima de
    cualquier cosa que digan sus registros."""
    from app.models import ChangeRequest
    from app.services.client_focus import focos_de

    c, p = cliente
    for d, h in ((1, 5.0), (2, 5.0), (3, 5.0)):
        _diario(db, p, d, sleep_hours=h)
    db.add(ChangeRequest(client_id=c.id, message="¿Puedo cambiar la cena del martes?",
                         status="open"))
    db.commit()
    try:
        focos = focos_de(db, c, hoy=date.today())
        assert focos[0].key == "peticion_abierta"
        assert "cena del martes" in focos[0].dato
    finally:
        db.query(ChangeRequest).filter(ChangeRequest.client_id == c.id).delete()
        db.commit()


def test_a_quien_solo_entrena_no_se_le_habla_de_dieta(db, cliente):
    """Hablarle de su adherencia a una dieta que no ha contratado es decirle
    que no le estamos mirando a él."""
    from app.services.client_focus import focos_de

    c, p = cliente
    for d in range(1, 5):
        _diario(db, p, d, diet_adherence="no", satiety_1_10=2)
    solo_entreno = {f.key for f in focos_de(db, c, hoy=date.today(),
                                            has_nutrition=False, has_training=True)}
    assert "adherencia_baja" not in solo_entreno and "hambre" not in solo_entreno
    con_dieta = {f.key for f in focos_de(db, c, hoy=date.today())}
    assert "adherencia_baja" in con_dieta


def test_quien_empezo_ayer_no_lleva_dos_semanas_desaparecido(db, cliente):
    """El contador de días sin registrar no puede mirar antes del principio de
    su quincena: a un cliente recién arrancado le decía que llevaba 14 días
    sin aparecer."""
    from app.models import Period
    from app.services.client_focus import focos_de

    c, p = cliente
    db.query(Period).filter(Period.id == p.id).update(
        {"starts_on": date.today() - timedelta(days=1)})
    db.commit()
    assert "sin_registros" not in {f.key for f in focos_de(db, c, hoy=date.today())}


# ---------------------------------------------------------------- la ronda --

def test_la_ronda_lleva_el_dato_al_prompt_y_lo_dice_en_el_panel(db, cliente):
    """El coach REVISA antes de enviar: si no ve el dato que ha motivado el
    mensaje, no puede saber si el texto le cuadra o si la IA se lo inventó."""
    from app.services import whatsapp_round as wa

    c, p = cliente
    for d, h in ((1, 5.0), (2, 5.2), (3, 5.4)):
        _diario(db, p, d, sleep_hours=h, serie=True)
    _diario(db, p, 4, serie=True)

    vistos = []

    class IAFalsa:
        def _raw_call(self, *, model, system, user, max_tokens=None):
            vistos.append(user)
            return "Hola Nuria, te veo durmiendo poco. ¿Qué tal la semana?"

    ronda = wa.build_round(db, ai=IAFalsa(), force=True)
    mio = next(i for i in ronda["items"] if i["client_id"] == c.id)
    assert mio["personalizado"] is True
    assert "5,2 h" in (mio["motivo"] or "")
    prompt = next(u for u in vistos if "Nuria" in u)
    assert "5,2 h" in prompt, "el dato tiene que viajar al prompt, no deducirlo la IA"
    assert ronda["personalizados"] >= 1


def test_sin_ia_el_mensaje_sigue_siendo_suyo(db, cliente):
    """El día que la API esté caída, el cliente no tiene por qué recibir un
    mensaje peor: la reserva lleva su dato y va en segunda persona."""
    from app.services import whatsapp_round as wa

    c, p = cliente
    for d, h in ((1, 5.0), (2, 5.2), (3, 5.4)):
        _diario(db, p, d, sleep_hours=h, serie=True)
    _diario(db, p, 4, serie=True)
    ronda = wa.build_round(db, ai=None, force=True)
    texto = next(i["text"] for i in ronda["items"] if i["client_id"] == c.id)
    assert "Nuria" in texto and "5,2 h" in texto
    assert "Lleva" not in texto, "el dato del prompt habla en tercera persona"


def test_no_se_le_repite_el_mismo_tema_dos_dias_seguidos_salvo_lo_urgente(db, cliente):
    """Repetirle «¿qué tal duermes?» tres mañanas seguidas es la sensación de
    plantilla que esto viene a quitar. Lo URGENTE sí se repite: callar que
    lleva cuatro días sin aparecer por no repetirse sería perder al cliente
    por educación."""
    from app.services.client_focus import Foco
    from app.services.whatsapp_round import _foco_del_dia

    c, _p = cliente
    sueno = Foco("sueno_bajo", 3, "t", "g", "d", "r")
    urgente = Foco("sin_registros", 2, "t", "g", "d", "r")

    import app.services.whatsapp_round as wa

    original = wa.focos_de
    try:
        wa.focos_de = lambda *a, **k: [sueno]
        assert _foco_del_dia(db, c, hoy=date.today(), has_nutrition=True,
                             has_training=True, recientes=["sueno_bajo"]) is None
        wa.focos_de = lambda *a, **k: [urgente]
        assert _foco_del_dia(db, c, hoy=date.today(), has_nutrition=True,
                             has_training=True, recientes=["sin_registros"]) is urgente
    finally:
        wa.focos_de = original


def test_la_baja_rgpd_se_lleva_tambien_el_tema_que_se_le_asigno(db, cliente):
    """De qué había que hablarle (su sueño, su adherencia) es un dato suyo
    aunque no lleve su nombre."""
    from app.models import WhatsAppRound
    from app.services.whatsapp_round import _CLAVE_FOCOS

    c, _p = cliente
    # Se guardan ANTES: tras la baja, tocar el objeto va a la base a refrescar
    # una fila que ya no existe (y el fallo parecería del código, no del test).
    cid, nombre = str(c.id), c.full_name
    hoy = date.today()
    fila = db.query(WhatsAppRound).filter(WhatsAppRound.round_date == hoy).first()
    if fila is None:
        fila = WhatsAppRound(round_date=hoy, brief_index=0, brief_key="x")
        db.add(fila)
    fila.texts_json = {cid: "hola", _CLAVE_FOCOS: {cid: "sueno_bajo", "9999": "racha"}}
    db.commit()

    from fastapi.testclient import TestClient

    from app.main import app
    from app.config import settings

    api = TestClient(app)
    tok = api.post("/api/auth/login", json={"username": settings.admin_1_user,
                                            "password": settings.admin_1_pass})
    if tok.status_code != 200:
        pytest.skip("sin admin sembrado")
    cab = {"Authorization": f"Bearer {tok.json()['access_token']}"}
    # La baja pide el nombre completo como confirmación (RGPD: es irreversible).
    r = api.delete(f"/api/clients/{cid}", headers=cab, params={"confirm": nombre})
    assert r.status_code in (200, 204), r.text
    db.expire_all()
    fila = db.query(WhatsAppRound).filter(WhatsAppRound.round_date == hoy).first()
    focos = (fila.texts_json or {}).get(_CLAVE_FOCOS) or {}
    assert cid not in focos
    assert focos.get("9999") == "racha", "no puede llevarse por delante el de los demás"
