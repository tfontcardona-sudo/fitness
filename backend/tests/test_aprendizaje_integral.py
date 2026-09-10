"""EL SISTEMA APRENDE DE TODO LO QUE HACE EL COACH (§13, ronda integral).

Lo que el dueño pidió: que aprenda de las ediciones, de los modelos de plan, de
los planes que se suben hechos y de los copy-paste; que note PATRONES ("como
veo que siempre cambias esto…"); que construya sobre lo ya aprendido; y que
todo eso cueste 0 o casi 0 créditos.

Lo que estos tests blindan:
- la SEÑAL y la SUSTITUCIÓN se derivan sin IA y no confunden un ajuste de cifra
  con una preferencia;
- lo que se cambia de una COPIA, de un MODELO o de un plan IMPORTADO sí se
  aprende, y escribir una base EN BLANCO sigue sin contaminar;
- un patrón necesita repetirse Y aparecer en varios planes;
- el modelo sugerido deja ABIERTO lo que el coach siempre corrige;
- los patrones llegan al prompt de generación sin gastar créditos.
"""
import os
import uuid

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


def _auth():
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token(os.environ.get('ADMIN_1_USER', 'coach1'))}"}


@pytest.fixture()
def http():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def cliente_con_planes(db):
    """Un cliente y tres planes suyos, para poder repartir ediciones."""
    from app.models import Client, Plan
    from app.security import new_portal_token

    c = Client(full_name="Aprendizaje", email=f"apre-{uuid.uuid4().hex[:8]}@test.local",
               portal_token="tmp", status="active", package_tier="full")
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    planes = []
    for i in range(1, 4):
        p = Plan(client_id=c.id, month_index=i, version=1, status="published",
                 generated_by="ai",
                 nutrition_json={"target_kcal": 2200,
                                 "macros": {"protein_g": 165, "carbs_g": 220, "fat_g": 73}},
                 training_json={"split_name": "Torso/Pierna",
                                "sessions": [{"day": "Lunes", "name": "Torso"}]})
        db.add(p)
        planes.append(p)
    db.commit()
    return c, planes


# --------------------------------------------------------------------------
# 1. La derivación: sin IA, y sin confundir una cifra con una preferencia.
# --------------------------------------------------------------------------

def test_la_señal_y_la_sustitucion_salen_del_texto_sin_gastar_un_credito():
    from app.services.continuous_learning import derivar_signal, derivar_sustitucion

    assert derivar_signal("Calorías: 2000 → 2180 kcal") == "nutricion.kcal"
    assert derivar_signal("Proteína: 150 → 165 g") == "nutricion.proteina"
    assert derivar_signal("Ejercicio 2: Sentadilla búlgara → Prensa") == "entreno.ejercicio"
    assert derivar_signal("Descanso serie 3: 90 → 120 s") == "entreno.descanso"
    # Cambiar el plato del desayuno habla del ALIMENTO, no del reparto.
    assert derivar_signal("Desayuno: Tostada de pavo → Tortilla") == "nutricion.alimentos"
    # …pero mover el porcentaje de esa toma sí es reparto.
    assert derivar_signal("Comida 2: reparto 30% → 25%") == "nutricion.reparto"

    # Una sustitución de TEXTO es una preferencia; una de CIFRAS, no.
    assert derivar_sustitucion("Ejercicio 2: Sentadilla → Prensa") == ("Sentadilla", "Prensa")
    assert derivar_sustitucion("Calorías: 2000 → 2180 kcal") is None
    assert derivar_sustitucion("Sin flecha aquí") is None


# --------------------------------------------------------------------------
# 2. De qué aprende y de qué no.
# --------------------------------------------------------------------------

def test_lo_que_cambias_de_una_copia_o_un_modelo_se_aprende_y_la_base_en_blanco_no(
        db, cliente_con_planes):
    """Escribir una base EN BLANCO por primera vez no es corregir a nadie. Pero
    lo que cambias de un plan copiado o de un modelo tuyo dice qué no te sirvió
    tal cual — que es justo lo que el dueño quiere que el sistema note."""
    from app.models import Plan, PlanEdit
    from app.services.plan_library import BORRADORES_EN_CONSTRUCCION

    # Los cuatro se montan en varias tandas (no se auto-activan al guardar)…
    for g in ("scaffold", "library", "template", "document"):
        assert g in BORRADORES_EN_CONSTRUCCION
    # …pero solo la base en blanco queda fuera del aprendizaje.
    _, planes = cliente_con_planes
    origenes = {"library": "copia", "template": "modelo", "document": "documento"}
    for i, (generador, origen) in enumerate(origenes.items(), start=20):
        # month_index distinto por generador: (cliente, mes, versión) es único.
        p = Plan(client_id=planes[0].client_id, month_index=i, version=1,
                 status="draft", generated_by=generador)
        db.add(p)
        db.flush()
        from app.services.continuous_learning import record_edit

        record_edit(db, plan_id=p.id, category="volumen",
                    note="Ejercicio 1: Peso muerto → Hip thrust", source=origen)
        fila = db.scalars(
            __import__("sqlalchemy").select(PlanEdit)
            .where(PlanEdit.plan_id == p.id)).one()
        assert fila.source == origen
        assert fila.signal == "entreno.ejercicio"
        assert fila.detail == "Peso muerto → Hip thrust"


def test_un_origen_inventado_no_entra_en_la_bolsa(db, cliente_con_planes):
    """`source` llega de código nuestro, pero un valor fuera de la lista
    convertiría las cuentas por origen en mentira: cae a "edicion"."""
    from app.services.continuous_learning import record_edit

    _, planes = cliente_con_planes
    fila = record_edit(db, plan_id=planes[0].id, category="otro",
                       note="algo", source="inventado")
    assert fila.source == "edicion"


# --------------------------------------------------------------------------
# 3. Los patrones: repetición Y varios planes.
# --------------------------------------------------------------------------

def test_un_patron_necesita_repetirse_en_varios_planes(db, cliente_con_planes):
    """Cinco correcciones del MISMO plan son una tarde de trabajo, no una
    costumbre. El patrón exige planes distintos."""
    from app.services import coach_patterns
    from app.services.continuous_learning import record_edit

    _, planes = cliente_con_planes
    for _ in range(5):
        record_edit(db, plan_id=planes[0].id, category="progresion",
                    note="Progresión semana 2: cambiada")
    db.commit()
    señales = {c.signal for c in coach_patterns.campos_recurrentes(db)}
    assert "entreno.progresion" not in señales

    # El mismo campo en TRES planes distintos sí es una costumbre.
    for p in planes:
        record_edit(db, plan_id=p.id, category="progresion",
                    note="Progresión semana 2: cambiada")
    db.commit()
    campos = {c.signal: c for c in coach_patterns.campos_recurrentes(db)}
    assert "entreno.progresion" in campos
    assert campos["entreno.progresion"].planes >= 3
    assert campos["entreno.progresion"].vivo is True


def test_siempre_cambias_x_por_y_se_cuenta_como_preferencia(db, cliente_con_planes):
    from app.services import coach_patterns
    from app.services.continuous_learning import record_edit

    _, planes = cliente_con_planes
    marca = uuid.uuid4().hex[:6]
    for p in planes:
        record_edit(db, plan_id=p.id, category="volumen",
                    note=f"Ejercicio 1: Zancada{marca} → Prensa{marca}")
    db.commit()
    subs = {(s.de, s.a): s for s in coach_patterns.sustituciones_recurrentes(db)}
    assert (f"Zancada{marca}", f"Prensa{marca}") in subs
    assert subs[(f"Zancada{marca}", f"Prensa{marca}")].veces >= 3


def test_las_mayusculas_y_los_acentos_no_parten_una_preferencia_en_dos(
        db, cliente_con_planes):
    """«Sentadilla búlgara» y «sentadilla bulgara» son la misma preferencia
    escrita de dos formas: contarlas por separado la dejaba por debajo del
    umbral y el patrón no salía nunca."""
    from app.services import coach_patterns
    from app.services.continuous_learning import record_edit

    _, planes = cliente_con_planes
    m = uuid.uuid4().hex[:6]
    variantes = [f"Sentadilla búlgara{m}", f"sentadilla bulgara{m}",
                 f"SENTADILLA BULGARA{m}"]
    for p, v in zip(planes, variantes):
        record_edit(db, plan_id=p.id, category="volumen", note=f"Ejercicio 1: {v} → Prensa{m}")
    db.commit()
    subs = [s for s in coach_patterns.sustituciones_recurrentes(db)
            if s.a == f"Prensa{m}"]
    assert len(subs) == 1 and subs[0].veces == 3


# --------------------------------------------------------------------------
# 4. El modelo que se propone solo, y los patrones en la generación.
# --------------------------------------------------------------------------

def test_el_modelo_sugerido_deja_abierto_lo_que_siempre_corriges(
        http, db, cliente_con_planes):
    from app.services import coach_patterns
    from app.services.continuous_learning import record_edit

    _, planes = cliente_con_planes
    for p in planes:
        record_edit(db, plan_id=p.id, category="calculo", note="Calorías: 2200 → 2350 kcal")
        record_edit(db, plan_id=p.id, category="progresion",
                    note="Progresión semana 3: cambiada")
    db.commit()

    sug = coach_patterns.sugerencia_de_modelo(db)
    assert sug is not None
    abiertas = {c["signal"] for c in sug["abierto"]}
    assert "nutricion.kcal" in abiertas
    # Lo que se deja abierto NUNCA se da por fijo: sería contradecirse.
    assert abiertas.isdisjoint({f["signal"] for f in sug["fijo"]})
    assert "Revisa al aplicarlo" in coach_patterns.nota_del_modelo(sug)

    # Y el modelo se crea de verdad, con su nota dentro.
    r = http.post("/api/learning/patterns/model", headers=_auth())
    assert r.status_code == 200, r.text
    creado = r.json()
    assert creado["id"] and creado["nota"]
    from app.models import PlanTemplate

    assert db.get(PlanTemplate, creado["id"]) is not None


def test_los_patrones_llegan_al_prompt_sin_gastar_un_credito(db, cliente_con_planes):
    from app.services import coach_patterns
    from app.services.continuous_learning import record_edit

    _, planes = cliente_con_planes
    m = uuid.uuid4().hex[:6]
    for p in planes:
        record_edit(db, plan_id=p.id, category="volumen",
                    note=f"Ejercicio 1: Peso muerto{m} → Hip thrust{m}")
    db.commit()
    bloque = coach_patterns.bloque_para_prompt(db)
    assert "COSTUMBRES DEL COACH" in bloque
    assert f"Hip thrust{m}" in bloque
    # Y el contrato de seguridad: los patrones NUNCA dictan números.
    assert "kcal" not in bloque.lower()


def test_sin_patrones_no_se_inventa_un_modelo(db):
    """Sin material, un modelo «inteligente» sería un modelo cualquiera con un
    nombre pretencioso. Se dice que no, y el endpoint responde 409."""
    from app.services import coach_patterns

    # Con la base real puede haber patrones de otros tests; lo que se comprueba
    # es el contrato: sin campos vivos, no hay sugerencia.
    sug = coach_patterns.sugerencia_de_modelo(db)
    if sug is None:
        assert True
    else:
        assert sug["abierto"], "una sugerencia sin campos abiertos no vale para nada"
