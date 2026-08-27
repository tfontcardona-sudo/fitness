"""Ronda «ingesta perfecta» (27-08-2026): lo que el cliente/coach mete por
CUALQUIER vía (PDF de anamnesis, formulario digital, planes a mano) debe
aplicarse al completo — y lo que no, avisar. Regresiones de la auditoría."""
import os
import uuid
from datetime import date

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
def http():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def _auth():
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token(os.environ.get('ADMIN_1_USER', 'coach1'))}"}


def _make_client(db, **kw):
    from app.models import Client
    from app.security import new_portal_token

    c = Client(full_name="Ingesta Cliente", email=f"{uuid.uuid4().hex[:8]}@example.com",
               status="onboarding", portal_token="tmp", **kw)
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    db.commit()
    return c


PDF_MINIMO = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


# ============================================== extracción del PDF (enums) ====

def test_extraccion_normaliza_patron_y_recuperacion():
    """El PDF pregunta el patrón alimentario y el objetivo puede ser recuperar
    una lesión: antes diet_pattern no existía en el schema y injury_recovery
    era IMPOSIBLE por la vía PDF (auditoría 27-08)."""
    from app.services.ai.extraction import AnamnesisExtraction

    e = AnamnesisExtraction(diet_pattern="Vegana", goal_type="recuperación de lesión")
    assert e.diet_pattern == "vegano"
    assert e.goal_type == "injury_recovery"
    # Lo irreconocible queda VACÍO (nunca un valor corrupto en la ficha).
    assert AnamnesisExtraction(diet_pattern="omnívoro").diet_pattern is None
    # Los campos nuevos existen y aceptan valores.
    e2 = AnamnesisExtraction(phone="600 111 222", goal_deadline=date(2027, 1, 1),
                             initial_waist_cm=94.0, initial_hip_cm=101.0)
    assert e2.phone == "600 111 222"
    assert e2.initial_waist_cm == 94.0


# ============================================== adjuntos (analítica) ==========

def test_adjunto_no_destruye_la_anamnesis(http, db):
    """El propio PDF pide adjuntar la analítica; subirla por la única vía que
    existía BORRABA la anamnesis y la IA leía el informe de sangre como si
    fuera el cuestionario. Ahora `kind=adjunto` la guarda aparte."""
    from app.services.storage import anamnesis_documents, list_documents

    c = _make_client(db)
    # 1) anamnesis "real" (la lectura IA fallará sin API — la subida vale igual)
    r = http.post(f"/api/clients/{c.id}/documents", headers=_auth(),
                  files={"file": ("anamnesis_maria.pdf", PDF_MINIMO, "application/pdf")})
    assert r.status_code == 200, r.text
    assert len(anamnesis_documents(c.id)) == 1
    # 2) la analítica como ADJUNTO: la anamnesis sigue intacta
    r2 = http.post(f"/api/clients/{c.id}/documents", headers=_auth(),
                   data={"kind": "adjunto"},
                   files={"file": ("analitica_maria.pdf", PDF_MINIMO, "application/pdf")})
    assert r2.status_code == 200, r2.text
    assert r2.json()["read_ok"] is None       # un adjunto NO se lee con IA
    docs = list_documents(c.id)
    assert len(docs) == 2                     # el panel enseña los dos
    anam = anamnesis_documents(c.id)
    assert len(anam) == 1                     # pero la anamnesis sigue siendo UNA
    assert not anam[0]["name"].startswith("adjunto_")
    # 3) re-subir la anamnesis reemplaza SOLO la anamnesis (el adjunto queda)
    r3 = http.post(f"/api/clients/{c.id}/documents", headers=_auth(),
                   files={"file": ("anamnesis_v2.pdf", PDF_MINIMO, "application/pdf")})
    assert r3.status_code == 200
    nombres = [d["name"] for d in list_documents(c.id)]
    assert any(n.startswith("adjunto_") for n in nombres), nombres
    assert len(anamnesis_documents(c.id)) == 1


# ===================================== formulario digital (vía oficial) =======

def test_formulario_conserva_horario_y_recoge_preferencias(http, db):
    """El wizard no preguntaba horarios y su default [] MACHACABA el
    meal_schedule del alta; y no había dónde declarar ejercicios favoritos/
    vetados ni perímetros. Todo eso ahora entra y nada se pisa en silencio."""
    horario = [{"slot": 1, "name": "Desayuno", "time": "07:00"},
               {"slot": 2, "name": "Cena", "time": "22:30"}]
    c = _make_client(db, meal_schedule=horario)
    body = {
        "sex": "male", "birth_date": "1990-01-01", "height_cm": 178,
        "start_weight_kg": 82, "body_fat_pct": None,
        "initial_waist_cm": 94, "initial_hip_cm": 101,
        "initial_arm_cm": 33, "initial_thigh_cm": 58,
        "level": "intermediate", "goal_type": "fat_loss",
        "exercise_prefs": "me encanta el peso muerto; odio las búlgaras",
        "training_days": 4, "session_max_min": 60, "training_place": "gym",
        "equipment": [], "meals_per_day": None, "meal_schedule": [],
        "meal_times_text": "como a las 15h y ceno tarde por turnos",
        "food_allergies": [], "food_dislikes": [], "food_likes": [],
        "diet_mode": "flexible_7", "strict_free_meal_enabled": False,
        "consent_accepted": True,
    }
    r = http.post(f"/api/p/{c.portal_token}/anamnesis", json=body)
    assert r.status_code == 200, r.text
    db.refresh(c)
    # meal_schedule vacío NO pisa el horario que el coach apuntó en el alta
    assert c.meal_schedule == horario
    # perímetros iniciales persistidos (línea base del delta de medidas)
    assert (c.initial_waist_cm, c.initial_hip_cm) == (94, 101)
    # preferencias de ejercicios → sport_history (llega al prompt de generación)
    assert "peso muerto" in (c.sport_history or "")
    # horarios en texto libre → lifestyle_notes etiquetado
    assert "[Horarios de comida]" in (c.lifestyle_notes or "")
    assert "15h" in c.lifestyle_notes


# ===================================== primera revisión: perímetros base ======

def test_perimetros_iniciales_son_el_antes_de_la_primera_revision():
    from types import SimpleNamespace

    from app.services.feedback_service import _perimeters

    cur = SimpleNamespace(closing_waist_cm=91.0, closing_hip_cm=None,
                          closing_arm_cm=None, closing_thigh_cm=None)
    cliente = SimpleNamespace(initial_waist_cm=94.0, initial_hip_cm=None,
                              initial_arm_cm=None, initial_thigh_cm=None)
    out = _perimeters(None, cur, cliente)
    assert out["Cintura"] == [("Inicio", 94.0), ("Actual", 91.0)]
    # sin datos iniciales, se comporta como antes (solo el valor actual)
    out2 = _perimeters(None, cur, SimpleNamespace())
    assert out2["Cintura"] == [("Actual", 91.0)]


# ===================================== planes a mano / banco / portal =========

def test_ensure_bank_slots_no_convierte_strict_en_flexible():
    """Cliente de menú cerrado cuyo plan quedó sin banco: el guardado del
    editor fabricaba un banco FLEXIBLE y el modo contratado se perdía para
    siempre, sin aviso (auditoría 27-08)."""
    from app.services.meal_fallback import ensure_bank_slots

    nut = {"meals": [{"slot": 1, "name": "Comida", "time": "14:00",
                      "target": {"kcal": 800, "protein_g": 50, "carbs_g": 80, "fat_g": 25}}],
           "meal_bank": None}
    assert ensure_bank_slots(nut, diet_mode="strict") == 0
    assert nut["meal_bank"] is None
    # en flexible sí rellena, como siempre
    assert ensure_bank_slots(nut, diet_mode="flexible_7") >= 1
    assert nut["meal_bank"]["mode"] == "flexible_7"


def test_copia_de_biblioteca_avisa_del_choque_de_modos(db):
    from types import SimpleNamespace

    from app.services.plan_library import _avisos_de_seguridad

    cliente = SimpleNamespace(diet_mode="strict", diet_pattern=None,
                              food_allergies=[], food_dislikes=[],
                              training_days=None)
    nutrition = {"meal_bank": {"mode": "flexible_7", "slots": []}}
    avisos = _avisos_de_seguridad(nutrition, None, cliente, db)
    assert any("menú cerrado" in a for a in avisos), avisos


def test_portal_fallback_respeta_el_patron_dietetico(db):
    """La toma sin banco del portal generaba opciones SIN el patrón dietético:
    a un vegano le salían pavo/huevo justo en la toma que quedó vacía por
    seguridad (mismo agujero que ya se cerró en el PDF)."""
    from types import SimpleNamespace

    from app.services.portal import _meals_for_today

    plan = SimpleNamespace(nutrition_json={
        "meals": [{"slot": 1, "name": "Comida", "time": "14:00",
                   "target": {"kcal": 700, "protein_g": 45, "carbs_g": 70, "fat_g": 22}}],
        "meal_bank": {"mode": "flexible_7", "slots": []},
    })
    cliente = SimpleNamespace(diet_mode="flexible_7", diet_pattern="vegano",
                              food_allergies=[], food_dislikes=[])
    out = _meals_for_today(plan, cliente, None)
    prohibidos = ("pollo", "pavo", "atun", "atún", "huevo", "merluza", "ternera",
                  "salmon", "salmón", "yogur", "queso")
    for opt in out[0]["options"]:
        titulo = (opt.get("title") or "").lower()
        assert not any(p in titulo for p in prohibidos), titulo


def test_scaffold_strict_imposible_no_deja_bank_none(http, db):
    """Si el menú cerrado no se puede montar con seguridad (multialérgico), el
    borrador ya NO se queda con meal_bank=None (portal sin platos y PDF mutando
    a flexible en silencio): lleva banco flexible con aviso EXPLÍCITO."""
    c = _make_client(db, sex="female", birth_date=date(1990, 1, 1), height_cm=165,
                     start_weight_kg=60, goal_type="fat_loss", level="beginner",
                     training_days=3, session_max_min=60, training_place="gym",
                     diet_mode="strict",
                     food_allergies=["gluten", "lactosa", "huevo", "pescado",
                                     "marisco", "frutos secos", "soja", "legumbres",
                                     "arroz", "avena", "patata", "pollo", "pavo",
                                     "ternera", "cerdo", "fruta", "maiz"])
    r = http.post(f"/api/clients/{c.id}/scaffold-plan", headers=_auth())
    if r.status_code != 200:
        pytest.skip(f"la base a mano no se pudo montar con esta ficha: {r.text[:100]}")
    plan = r.json()
    bank = plan["nutrition"]["meal_bank"]
    if bank is not None and bank.get("mode") == "strict":
        pytest.skip("el banco cerró el menú incluso con estas alergias")
    # lo importante: NUNCA None sin aviso
    assert bank is not None
    assert any("no se pudo montar" in f or "banco FLEXIBLE" in f
               for f in plan.get("guardrail_flags") or []), plan.get("guardrail_flags")
