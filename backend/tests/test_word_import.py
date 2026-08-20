"""IDA Y VUELTA del Word editable: el coach descarga el .docx, lo edita en Word
y lo sube — el sistema detecta los cambios y los aplica por el PATCH de siempre.

Se prueba el ciclo REAL: generar el documento por el endpoint, mutar celdas con
python-docx (como haría Word), subirlo a /import-word y aplicar. Requiere
PostgreSQL (se salta sin él)."""
import io
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


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app.main import app
    from app.seeds.run import main as seed_main

    seed_main()
    return TestClient(app)


@pytest.fixture(scope="module")
def auth(client):
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token('coach1')}"}


def _nutrition() -> dict:
    return {
        "tdee_kcal": 2500, "target_kcal": 2000,
        "macros": {"protein_g": 150, "carbs_g": 200, "fat_g": 60},
        "meals": [
            {"slot": 1, "name": "Desayuno", "time": "08:00",
             "target": {"kcal": 1000, "protein_g": 75, "carbs_g": 100, "fat_g": 30}},
            {"slot": 2, "name": "Cena", "time": "21:00",
             "target": {"kcal": 1000, "protein_g": 75, "carbs_g": 100, "fat_g": 30}},
        ],
        "supplements": [{"name": "Creatina", "dose": "5 g", "timing": "post-entreno",
                         "evidence_note": "sólida"}],
        "meal_bank": {"mode": "flexible_7", "slots": []},
    }


def _training(ex1: int, ex2: int) -> dict:
    def ex(eid, sets=3):
        return {"exercise_id": eid, "sets": sets, "rep_range": "8-10", "rir": "2",
                "tempo": None, "rest_sec": 90, "start_weight_hint_kg": None,
                "progression_rule": "Sube 2,5 kg al completar el rango",
                "technique_cue": "Controla la bajada", "biomech_cue": "",
                "coach_notes": None}

    return {
        "split_name": "Torso/Pierna", "split_rationale": "2 días",
        "weekly_progression": [
            {"week": 1, "intent": "Base", "load_pct": 70, "rir_target": "3",
             "volume_note": "arranque"},
            {"week": 2, "intent": "Progresión", "load_pct": 75, "rir_target": "2",
             "volume_note": ""},
            {"week": 3, "intent": "Pico", "load_pct": 80, "rir_target": "1-2",
             "volume_note": ""},
            {"week": 4, "intent": "Deload", "load_pct": 60, "rir_target": "4",
             "volume_note": "descarga"},
        ],
        "sessions": [
            {"day": "Lunes", "name": "Torso A", "warmup": "5 min bici",
             "exercises": [ex(ex1), ex(ex2, sets=4)], "cooldown": "estiramientos"},
        ],
        "cardio": {"daily_steps": 8000, "sessions": []},
        "deload_instructions": "Semana 4: volumen a la mitad.",
    }


@pytest.fixture(scope="module")
def setup(client, auth):
    exs = client.get("/api/exercises", headers=auth).json()
    assert len(exs) >= 3
    ex1, ex2, ex3 = exs[0], exs[1], exs[2]
    r = client.post("/api/clients", headers=auth, json={
        "full_name": "Word Import", "email": f"word-{uuid.uuid4().hex[:8]}@example.com",
    })
    cid = r.json()["client"]["id"]
    r = client.post(f"/api/clients/{cid}/plans", headers=auth, json={
        "month_index": 1, "nutrition_json": _nutrition(),
        "training_json": _training(ex1["id"], ex2["id"]), "education_json": {},
    })
    assert r.status_code == 201, r.text
    return {"cid": cid, "plan_id": r.json()["id"], "ex": (ex1, ex2, ex3)}


def _download_docx(client, auth, plan_id: int) -> bytes:
    r = client.get(f"/api/plans/{plan_id}/document?format=docx", headers=auth)
    assert r.status_code == 200
    return r.content


def _edit_docx(content: bytes, edits) -> bytes:
    """Aplica `edits(doc)` sobre el documento y lo devuelve como bytes."""
    from docx import Document

    doc = Document(io.BytesIO(content))
    edits(doc)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def _find_table(doc, first_header: str):
    for t in doc.tables:
        try:
            if t.rows[0].cells[0].text.strip().lower().startswith(first_header):
                return t
        except Exception:
            continue
    return None


def test_import_word_detecta_y_aplica_cambios(client, auth, setup):
    plan_id = setup["plan_id"]
    ex1, ex2, ex3 = setup["ex"]
    original = _download_docx(client, auth, plan_id)

    def edits(doc):
        # kcal y macros del resumen energético
        t = _find_table(doc, "calorías")
        assert t is not None
        t.rows[1].cells[0].text = "≈ 2200 kcal"
        t.rows[1].cells[1].text = "CH 220 g · P 160 g · G 62 g"
        # hora de la cena
        tt = _find_table(doc, "hora")
        assert tt is not None
        tt.rows[2].cells[0].text = "20:30"
        # sesión: series del primer ejercicio, descanso del segundo y CAMBIO de
        # ejercicio (el segundo pasa a ser ex3, otro de la biblioteca)
        ts = _find_table(doc, "ejercicio")
        assert ts is not None
        ts.rows[1].cells[1].text = "5×6-8"
        ts.rows[2].cells[0].text = ex3["canonical_name"]
        ts.rows[2].cells[3].text = "120s"
        # progresión: carga de la semana 2
        tp = _find_table(doc, "semana")
        assert tp is not None
        tp.rows[2].cells[2].text = "78%"

    editado = _edit_docx(original, edits)
    r = client.post(
        f"/api/plans/{plan_id}/import-word", headers=auth,
        files={"file": ("plan.docx", editado,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["has_changes"]
    frases = " | ".join(data["changes"])
    assert "2000" in frases and "2200" in frases          # kcal detectadas
    assert "20:30" in frases                              # hora de la cena
    assert "5×6-8" in frases or "5x6-8" in frases         # series
    assert ex3["canonical_name"] in frases                # cambio de ejercicio
    assert "78" in frases                                 # carga semana 2

    # Aplicar por el MISMO camino que el editor (PATCH con base_rev)
    r2 = client.patch(f"/api/plans/{plan_id}", headers=auth, json={
        "nutrition_json": data["nutrition_json"],
        "training_json": data["training_json"],
        "base_rev": data["base_rev"],
    })
    assert r2.status_code == 200, r2.text
    guardado = r2.json()
    # El PATCH reconcilia (kcal ≡ 4/4/9 de los macros redondeados): tolerancia
    # de unas pocas kcal alrededor de lo escrito en el Word.
    assert abs(guardado["nutrition_json"]["target_kcal"] - 2200) <= 5
    assert guardado["nutrition_json"]["macros"]["protein_g"] == 160
    ses = guardado["training_json"]["sessions"][0]
    assert ses["exercises"][0]["sets"] == 5
    assert ses["exercises"][0]["rep_range"] == "6-8"
    assert ses["exercises"][1]["exercise_id"] == ex3["id"]
    assert ses["exercises"][1]["rest_sec"] == 120
    assert guardado["training_json"]["weekly_progression"][1]["load_pct"] == 78
    assert guardado["nutrition_json"]["meals"][1]["time"] == "20:30"


def test_import_word_rechaza_archivos_invalidos(client, auth, setup):
    plan_id = setup["plan_id"]
    # No es un zip/docx
    r = client.post(f"/api/plans/{plan_id}/import-word", headers=auth,
                    files={"file": ("plan.docx", b"%PDF-1.4 no soy word", "application/pdf")})
    assert r.status_code == 422
    # Es un docx pero NO nuestro plan (sin ninguna tabla reconocible)
    from docx import Document as _D

    buf = io.BytesIO()
    d = _D()
    d.add_paragraph("Documento cualquiera")
    d.save(buf)
    r2 = client.post(f"/api/plans/{plan_id}/import-word", headers=auth,
                     files={"file": ("otro.docx", buf.getvalue(),
                                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert r2.status_code == 422
    assert "No reconozco" in r2.json()["detail"]


def test_import_word_sin_cambios_no_inventa_nada(client, auth, setup):
    plan_id = setup["plan_id"]
    original = _download_docx(client, auth, plan_id)
    r = client.post(
        f"/api/plans/{plan_id}/import-word", headers=auth,
        files={"file": ("plan.docx", original,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["changes"] == []
