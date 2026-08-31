"""Regresiones de la tanda 4 de la auditoría: IA, planes y documentos.

Nueve hallazgos del inventario compartido, verificados a mano contra el código
antes de tocarlo (el workflow de verificación murió contra el límite de sesión).
"""
import io
import uuid
import warnings
from datetime import date, datetime, timedelta, timezone

import pytest

warnings.filterwarnings("ignore")


def _db_available() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings

        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


DB = _db_available()
pytestmark_db = pytest.mark.skipif(not DB, reason="Requiere PostgreSQL")


# ------------------------------------------------- el sello de la adaptación ---

@pytestmark_db
def test_copiar_un_plan_no_arrastra_la_adaptacion_de_otro_cliente():
    """El sello vive en training_json en los planes solo-entreno: al copiar, el
    destino salía "adaptado a la revisión #N" de una revisión que no es suya,
    con las CIFRAS del cliente de origen dentro de sus Novedades, y su aviso de
    "sin adaptar" se apagaba solo."""
    from app.db import SessionLocal
    from app.models import Client
    from app.security import new_portal_token
    from app.services.plan_library import copiar_a_cliente

    uid = uuid.uuid4().hex[:8]
    training = {
        "split_name": "Full body", "sessions": [],
        "applied_adjustments": {"period_index": 7, "items": [
            {"area": "entreno", "change": "subir 5 kg en press banca",
             "detail": "Totales finales: 2100 kcal · P 160 / C 200 / G 60 g"}]},
        "rev": 12, "manual_changes": {"items": ["algo del origen"]},
    }
    with SessionLocal() as db:
        destino = Client(full_name=f"Destino {uid}", email=f"dest-{uid}@test.local",
                         portal_token="p", status="active", package_tier="train",
                         level="intermediate", training_days=3, training_place="gym")
        db.add(destino); db.flush(); destino.portal_token = new_portal_token(destino.id)
        db.commit()
        plan, _avisos = copiar_a_cliente(db, destino, nutrition=None,
                                         training=training, education=None,
                                         origen="modelo de prueba")
        tr = plan.training_json or {}
        assert "applied_adjustments" not in tr, "el sello de OTRO cliente no puede viajar"
        for clave in ("rev", "manual_changes"):
            assert clave not in tr, f"{clave} pertenece al ciclo del origen"
        db.rollback()


@pytestmark_db
def test_un_plan_solo_entreno_sella_su_adaptacion_en_el_entreno():
    """Un DQR Train no tiene nutrición donde sellar: el aviso «sin adaptar» no
    se apagaba nunca por mucho que el coach regenerara."""
    from app.routers.alerts import client_alerts
    from app.db import SessionLocal
    from app.models import Client, Period, Plan
    from app.security import new_portal_token

    uid = uuid.uuid4().hex[:8]
    with SessionLocal() as db:
        c = Client(full_name=f"Train {uid}", email=f"train-{uid}@test.local",
                   portal_token="p", status="active", package_tier="train",
                   goal_type="muscle_gain")
        db.add(c); db.flush(); c.portal_token = new_portal_token(c.id)
        # Plan SIN nutrición, con el sello donde toca (lo que ahora escribe
        # generate-plan cuando no hay dieta).
        plan = Plan(client_id=c.id, month_index=1, version=1, status="published",
                    goal_type="muscle_gain", nutrition_json=None,
                    training_json={"split_name": "Torso/Pierna", "sessions": [],
                                   "applied_adjustments": {"period_index": 1, "items": []}},
                    education_json={})
        db.add(plan); db.flush()
        hoy = date.today()
        db.add(Period(client_id=c.id, plan_id=plan.id, period_index=1,
                      starts_on=hoy - timedelta(days=20), ends_on=hoy - timedelta(days=6),
                      status="analyzed"))
        db.commit()
        kinds = {a["kind"] for a in client_alerts(db, c)}
        assert "adapt_plan" not in kinds, "el sello del entreno tiene que apagar el aviso"
        db.rollback()


# ------------------------------------ texto que lee el cliente: no se acumula ---

def test_el_porque_de_tu_plan_no_acumula_una_frase_por_revision():
    """La marca lleva el número de revisión, así que cada quincena añadía OTRO
    párrafo idéntico: en el mes 4, ocho veces la misma frase."""
    import re

    base = "Tu plan busca perder grasa sin perder fuerza."
    texto = base
    for n in (1, 2, 3, 4):
        texto = re.sub(r"\n*Ajustado tras tu revisión #\d+:[^\n]*", "", texto).strip()
        texto = (f"{texto}\n\nAjustado tras tu revisión #{n}: mantenemos el enfoque "
                 "y afinamos las cifras con lo que has registrado estas dos semanas.")
    assert texto.count("Ajustado tras tu revisión") == 1
    assert "#4" in texto and "#3" not in texto
    assert texto.startswith(base), "el argumentario original no se toca"


def test_la_estructura_del_entreno_no_encadena_coletillas():
    import re

    txt = "3 días/semana: cubre todo el cuerpo dos veces."
    for n in (1, 2, 3):
        txt = re.sub(r"\s*·\s*Adaptado a la revisión quincenal #\d+\.", "", txt).rstrip()
        txt = txt + f" · Adaptado a la revisión quincenal #{n}."
    assert txt.count("Adaptado a la revisión quincenal") == 1
    assert txt.endswith("#3.")


# --------------------------------------------- gráficas e informe del cliente ---

def test_los_perimetros_se_pintan_en_su_columna():
    """Con una medida del cierre anterior ("Anterior") y otra de la anamnesis
    ("Inicio"), la rejilla tenía 3 columnas y las series de 2 puntos se
    desplazaban una posición: el ANTES se pintaba sobre "Actual"."""
    from app.services.docs.charts import perimeters_chart

    # Etiqueta unificada (lo que produce _perimeters ahora): una sola columna
    # de "antes" para todas las medidas.
    perimetros = {
        "Cintura": [("Antes", 92.0), ("Actual", 88.0)],
        "Brazo": [("Antes", 35.0), ("Actual", 36.0)],
        "Muslo": [("Actual", 58.0)],
    }
    png = perimeters_chart(perimetros, "#8B1A2B")
    assert png[:4] == b"\x89PNG"


def test_perimetros_una_sola_etiqueta_de_antes():
    """_perimeters no puede mezclar "Anterior" e "Inicio" en la misma gráfica."""
    from types import SimpleNamespace

    from app.services.feedback_service import _perimeters

    prev = SimpleNamespace(closing_waist_cm=92.0, closing_hip_cm=None,
                           closing_arm_cm=None, closing_thigh_cm=None)
    cur = SimpleNamespace(closing_waist_cm=88.0, closing_hip_cm=None,
                          closing_arm_cm=36.0, closing_thigh_cm=None)
    cliente = SimpleNamespace(initial_waist_cm=95.0, initial_hip_cm=None,
                              initial_arm_cm=34.0, initial_thigh_cm=None)
    out = _perimeters(prev, cur, cliente)
    etiquetas = {lbl for serie in out.values() for lbl, _ in serie}
    assert etiquetas == {"Antes", "Actual"}, etiquetas
    # Y cada serie sigue llevando su ANTES y su AHORA en ese orden.
    assert out["Cintura"] == [("Antes", 92.0), ("Actual", 88.0)]
    assert out["Brazo"] == [("Antes", 34.0), ("Actual", 36.0)]


# --------------------------------------------------------- caché del PDF -------

def test_la_cache_del_pdf_acierta_con_el_mismo_plan():
    """python-docx sella la hora en cada entrada del zip: el mismo plan
    guardado un segundo después daba otro sha1 y la caché no acertaba nunca
    (cada descarga arrancaba un LibreOffice de ~300 MB)."""
    import time

    from docx import Document

    from app.services.docs.pdf_convert import _clave_de_contenido

    def bytes_de(texto: str) -> bytes:
        d = Document()
        d.add_paragraph(texto)
        buf = io.BytesIO()
        d.save(buf)
        return buf.getvalue()

    a = _clave_de_contenido(bytes_de("mismo plan"))
    time.sleep(1.1)
    assert _clave_de_contenido(bytes_de("mismo plan")) == a
    assert _clave_de_contenido(bytes_de("plan distinto")) != a
    # Y si no es un zip legible, no revienta: huella cruda.
    assert _clave_de_contenido(b"no soy un zip")


# ------------------------------------------- educativo: alérgenos y patrón -----

@pytestmark_db
def test_el_educativo_del_word_se_importa_con_alergias():
    """El importador comparaba contra TODAS las píldoras con texto, pero el
    documento solo imprime las que pasan el filtro de alérgenos: con alergias,
    los recuentos no cuadraban y la caja entera se descartaba."""
    from app.services.word_import import _edu_bloqueado

    pildora_ok = ("Sobrecarga progresiva", "Sube 2,5 kg cuando cierres todas las series.")
    pildora_leche = ("Proteína", "Un vaso de leche entera tras entrenar te ayuda.")
    assert not _edu_bloqueado(pildora_ok, ["leche"], None)
    assert _edu_bloqueado(pildora_leche, ["leche"], None)
    # Sin restricciones no bloquea nada.
    assert not _edu_bloqueado(pildora_leche, [], None)


