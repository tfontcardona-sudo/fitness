"""LA PLANIFICACIÓN, BIEN CONECTADA: que cada cambio tenga salida y se note.

Revisión de los clics y las combinaciones de la pestaña Planificación. Lo que
se rompía era siempre lo mismo: **un dato de la ficha que cambia lo que se
genera, pero que con un plan ya publicado no toca nada y no avisa nadie**. El
coach cambiaba el ciclo, veía la cifra nueva en su tarjeta, y el cliente seguía
con la rutina de antes — sin un aviso y sin un botón.

Cubre:
  1. El SNAPSHOT de entradas incluye la estructura (ciclo, mesociclo,
     prioridad muscular), que es lo que compara la alerta.
  2. Un plan SOLO-ENTRENO también lo guarda: el snapshot vivía en la dieta, así
     que para un DQR Train la alerta estaba MUERTA.
  3. La alerta `plan_stale_inputs` salta al cambiar cada uno de ellos, y lo lee
     esté donde esté el snapshot.
"""
import datetime as dt
import uuid

import pytest

from app.models import Client, Plan
from app.routers.clients import _snapshot_de_entradas


class _Ficha:
    """Lo mínimo que mira el snapshot."""

    def __init__(self, **kw):
        self.height_cm = 178
        self.level = "intermediate"
        self.training_days = 4
        self.training_place = "gym"
        self.diet_mode = "flexible_7"
        self.diet_pattern = None
        self.cycle_days = None
        self.mesocycle_blocks = None
        self.muscle_priority = None
        self.muscle_deprioritized = None
        self.__dict__.update(kw)


# ============================================ 1 · el snapshot lo recoge ====

def test_el_snapshot_guarda_la_estructura_de_la_planificacion():
    """Si la estructura no entra aquí, cambiarla no avisa de nada: la alerta
    compara CONTRA esto."""
    snap = _snapshot_de_entradas(
        _Ficha(cycle_days=10, mesocycle_blocks=5,
               muscle_priority=["hombros", "espalda"],
               muscle_deprioritized=["gemelos"]), 82.0)
    assert snap["cycle_days"] == 10
    assert snap["mesocycle_blocks"] == 5
    # ORDENADAS: el coach puede marcarlas en cualquier orden y eso no es un
    # cambio — sin ordenar, reordenar dos grupos fabricaba un aviso falso.
    assert snap["muscle_priority"] == ["espalda", "hombros"]
    assert snap["muscle_deprioritized"] == ["gemelos"]


def test_una_ficha_sin_estructura_no_inventa_valores():
    """Lo de siempre (ciclo semanal, 4 bloques) NO se declara: los planes que
    ya existen no llevan el campo y no pueden empezar a avisar solos."""
    snap = _snapshot_de_entradas(_Ficha(), 82.0)
    assert snap["cycle_days"] is None
    assert snap["mesocycle_blocks"] is None
    assert snap["muscle_priority"] == []


# ===================================== 2 y 3 · la alerta, con y sin dieta ====

@pytest.fixture()
def db():
    """Sesión propia + limpieza: la suite no trae fixture de BD y estos tests
    crean clientes y planes reales para que la alerta los recorra de verdad."""
    from app.db import SessionLocal

    s = SessionLocal()
    creados: list[int] = []
    s.info["creados"] = creados
    try:
        yield s
    finally:
        try:
            from app.models import Client, Plan

            for cid in creados:
                s.query(Plan).filter(Plan.client_id == cid).delete()
                s.query(Client).filter(Client.id == cid).delete()
            s.commit()
        except Exception:
            s.rollback()
        finally:
            s.close()


def _alerta_de(db, client, plan):
    from app.routers.alerts import client_alerts

    # Las alertas de UN cliente: `list_alerts` filtra además por la cartera de
    # la marca activa, que aquí no es lo que se está probando.
    # La clave va con el cliente y el ancla dentro («8450:plan_stale_inputs:…»).
    return [a for a in client_alerts(db, client)
            if "plan_stale_inputs" in str(a.get("key", ""))]


def _cliente(db, email, tier="full", **kw):
    email = f"{uuid.uuid4().hex[:8]}.{email}"
    from app.security import new_portal_token

    c = Client(full_name="Estructura Test", email=email, portal_token="x",
               package_tier=tier, status="active", sex="male",
               birth_date=dt.date(1992, 5, 3), height_cm=178,
               start_weight_kg=82, current_weight_kg=82, body_fat_pct=18,
               goal_type="fat_loss", level="intermediate", training_days=4,
               daily_activity_level="active", session_max_min=60,
               training_place="gym", meals_per_day=4, diet_mode="flexible_7",
               payment_status="paid")
    for k, v in kw.items():
        setattr(c, k, v)
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    db.flush()
    db.info.setdefault("creados", []).append(c.id)
    return c


def _plan(db, client, *, con_dieta, snapshot):
    nut = {"target_kcal": 2200, "macros": {"protein_g": 170, "carbs_g": 200, "fat_g": 70},
           "meals": []} if con_dieta else None
    tr = {"split_name": "X", "sessions": [], "weekly_progression": []}
    if con_dieta:
        nut["gen_inputs"] = snapshot
    else:
        tr["gen_inputs"] = snapshot
    p = Plan(client_id=client.id, month_index=1, version=1, status="published",
             nutrition_json=nut, training_json=tr, education_json={},
             generated_by="ai",
             published_at=dt.datetime.now(dt.timezone.utc))
    db.add(p)
    db.flush()
    return p


def test_cambiar_el_ciclo_con_un_plan_publicado_avisa(db):
    """El fallo de fondo: el coach cambiaba el ciclo de 7 a 10, la tarjeta le
    decía «6 sesiones» y el cliente seguía con su rutina de lunes a viernes.
    Nada en el panel lo contaba."""
    c = _cliente(db, "estructura.ciclo@example.com")
    snap = _snapshot_de_entradas(c, 82.0)          # ciclo None = el de siempre
    _plan(db, c, con_dieta=True, snapshot={**snap, "cycle_days": 7})
    db.commit()
    assert not _alerta_de(db, c, None), "sin cambios no debe avisar"

    c.cycle_days = 10
    db.commit()
    avisos = _alerta_de(db, c, None)
    assert avisos, "cambiar el ciclo tiene que avisar"
    assert "ciclo" in avisos[0]["message"].lower()


def test_cambiar_la_prioridad_muscular_avisa(db):
    """La prioridad se hornea en el plan al generarlo: añadirla después no
    cambia ni una serie de lo que el cliente tiene."""
    c = _cliente(db, "estructura.prioridad@example.com")
    _plan(db, c, con_dieta=True, snapshot=_snapshot_de_entradas(c, 82.0))
    db.commit()
    assert not _alerta_de(db, c, None)

    c.muscle_priority = ["espalda", "hombros"]
    db.commit()
    avisos = _alerta_de(db, c, None)
    assert avisos, "cambiar la prioridad tiene que avisar"
    assert "espalda" in avisos[0]["message"]


def test_reordenar_la_prioridad_NO_avisa(db):
    """Marcarlas en otro orden no es un cambio. Sin ordenar, el aviso saltaba
    solo y el coach aprendía a ignorarlo."""
    c = _cliente(db, "estructura.orden@example.com",
                 muscle_priority=["espalda", "hombros"])
    _plan(db, c, con_dieta=True, snapshot=_snapshot_de_entradas(c, 82.0))
    db.commit()
    c.muscle_priority = ["hombros", "espalda"]
    db.commit()
    assert not _alerta_de(db, c, None)


def test_un_plan_SOLO_ENTRENO_tambien_avisa(db):
    """El snapshot vivía en `nutrition_json` y un DQR Train no tiene dieta: la
    alerta de ficha cambiada estaba MUERTA para él, con cualquier campo."""
    c = _cliente(db, "estructura.train@example.com", tier="train", cycle_days=10)
    _plan(db, c, con_dieta=False, snapshot=_snapshot_de_entradas(c, 82.0))
    db.commit()
    assert not _alerta_de(db, c, None)

    c.cycle_days = 5
    db.commit()
    assert _alerta_de(db, c, None), "un plan solo-entreno también tiene que avisar"


def test_un_plan_ANTIGUO_sin_la_clave_no_empieza_a_avisar(db):
    """Los planes generados antes de esta ronda no llevan `muscle_priority` en
    su snapshot: compararlo contra una lista vacía haría saltar un aviso a toda
    la cartera el día del despliegue."""
    c = _cliente(db, "estructura.antiguo@example.com",
                 muscle_priority=["espalda"])
    viejo = {"weight_kg": 82.0, "height_cm": 178, "level": "intermediate",
             "training_days": 4, "training_place": "gym",
             "diet_mode": "flexible_7", "diet_pattern": None}
    _plan(db, c, con_dieta=True, snapshot=viejo)
    db.commit()
    assert not _alerta_de(db, c, None)
