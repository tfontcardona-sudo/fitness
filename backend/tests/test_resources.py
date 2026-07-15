"""Sección "Recursos" del portal (productos recomendados + vídeos de ejercicio).

Cubre la gestión del coach (CRUD de productos, subida y servido de imagen,
validación de URL) y la vista del cliente (GET /api/p/{token}/resources):
vídeos de los ejercicios de su rutina con portada, y productos activos.
"""

from __future__ import annotations

import io
import uuid
from datetime import date

import pytest
from PIL import Image

from tests.test_portal import (  # infra compartida (DB, plan de prueba)
    ADMIN_USER,
    _db_available,
    _generate_plan_content,
)

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
    # Firmamos el token directamente (no vía /auth/login) para no consumir el
    # límite de 5 logins/minuto por IP, que comparten todos los módulos de test.
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token(ADMIN_USER)}"}


def _png_bytes(color=(200, 120, 60)) -> bytes:
    img = Image.new("RGB", (48, 48), color)
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()


def _client_with_published_plan(client, auth) -> tuple[int, str, list[int]]:
    """Crea cliente + anamnesis + plan publicado. Devuelve (id, token, exercise_ids)."""
    body = client.post(
        "/api/clients", headers=auth,
        json={"full_name": "Recursos Tester", "email": f"rec-{uuid.uuid4().hex[:8]}@example.com"},
    ).json()
    cid = body["client"]["id"]
    token = body["links"]["portal_token"]

    anam = {
        "sex": "male", "birth_date": "1994-03-10", "height_cm": 180, "start_weight_kg": 82,
        "goal_type": "fat_loss", "goal_weight_kg": 76, "level": "intermediate",
        "training_days": 4, "session_max_min": 75, "training_place": "gym",
        "equipment": ["barra"], "meals_per_day": 4,
        "meal_schedule": [{"slot": i, "name": n, "time": t} for i, n, t in
                          [(1, "Desayuno", "08:00"), (2, "Comida", "14:00"),
                           (3, "Merienda", "18:00"), (4, "Cena", "21:30")]],
        "food_allergies": [], "food_dislikes": [], "food_likes": ["pollo"],
        "diet_mode": "flexible_7", "consent_accepted": True,
    }
    assert client.post(f"/api/p/{token}/anamnesis", json=anam).status_code == 200

    nutrition, training, education, flags = _generate_plan_content()
    plan = client.post(f"/api/clients/{cid}/plans", headers=auth, json={
        "month_index": 1, "nutrition_json": nutrition, "training_json": training,
        "education_json": education, "guardrail_flags": flags, "generated_by": "test",
    }).json()
    assert client.post(f"/api/plans/{plan['id']}/publish", headers=auth).json()["status"] == "published"

    ex_ids: list[int] = []
    for s in training.get("sessions", []):
        for e in s.get("exercises", []):
            if e["exercise_id"] not in ex_ids:
                ex_ids.append(e["exercise_id"])
    assert ex_ids, "el plan de prueba debe referenciar al menos un ejercicio"
    return cid, token, ex_ids


# ------------------------------------------------ vídeos de ejercicio ----
def test_exercise_videos_in_routine(client, auth):
    _, token, ex_ids = _client_with_published_plan(client, auth)
    eid = ex_ids[0]

    # Sin vídeo → la sección de vídeos está vacía
    client.patch(f"/api/exercises/{eid}", headers=auth, json={"video_url": "", "image_url": None})
    res = client.get(f"/api/p/{token}/resources").json()
    assert all(v["exercise_id"] != eid for v in res["exercise_videos"])

    # Con vídeo de YouTube y SIN imagen → portada derivada automáticamente
    client.patch(f"/api/exercises/{eid}", headers=auth,
                 json={"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
    res = client.get(f"/api/p/{token}/resources").json()
    vid = next(v for v in res["exercise_videos"] if v["exercise_id"] == eid)
    assert vid["title"] and vid["muscle"]
    assert vid["video_url"].endswith("dQw4w9WgXcQ")
    assert vid["image_url"] == "https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg"

    # Con imagen explícita → tiene prioridad sobre la portada de YouTube
    client.patch(f"/api/exercises/{eid}", headers=auth,
                 json={"image_url": "https://example.com/press.jpg"})
    res = client.get(f"/api/p/{token}/resources").json()
    vid = next(v for v in res["exercise_videos"] if v["exercise_id"] == eid)
    assert vid["image_url"] == "https://example.com/press.jpg"

    # Un vídeo NO-YouTube que contiene la subcadena no debe dar portada de YouTube
    client.patch(f"/api/exercises/{eid}", headers=auth,
                 json={"video_url": "https://notyoutube.com/watch?v=dQw4w9WgXcQ", "image_url": None})
    res = client.get(f"/api/p/{token}/resources").json()
    vid = next(v for v in res["exercise_videos"] if v["exercise_id"] == eid)
    assert vid["image_url"] is None

    # Un vídeo con esquema no http (javascript:) se rechaza (se renderiza como enlace)
    assert client.patch(f"/api/exercises/{eid}", headers=auth,
                        json={"video_url": "javascript:alert(1)"}).status_code == 422


# --------------------------------------------- productos recomendados ----
def test_product_crud_and_portal(client, auth):
    _, token, _ = _client_with_published_plan(client, auth)

    # Crear
    created = client.post("/api/resources/products", headers=auth, json={
        "title": "Proteína Whey", "description": "30 g por toma",
        "url": "https://tienda.example.com/whey", "category": "suplemento",
    })
    assert created.status_code == 201
    prod = created.json()
    pid = prod["id"]
    assert prod["title"] == "Proteína Whey"
    assert prod["image_url"] is None and prod["has_upload"] is False
    assert prod["active"] is True

    # Aparece en el catálogo del coach
    all_products = client.get("/api/resources/products", headers=auth).json()
    assert any(p["id"] == pid for p in all_products)

    # Aparece en el portal del cliente
    res = client.get(f"/api/p/{token}/resources").json()
    p = next(p for p in res["products"] if p["id"] == pid)
    assert p["title"] == "Proteína Whey" and p["url"].endswith("/whey")

    # Subir imagen → prioridad sobre URL externa; se sirve públicamente
    up = client.post(f"/api/resources/products/{pid}/image", headers=auth,
                     files=[("file", ("p.png", _png_bytes(), "image/png"))])
    assert up.status_code == 200
    upj = up.json()
    assert upj["has_upload"] is True
    assert upj["image_url"].startswith(f"/api/resources/products/{pid}/image")

    # La imagen se sirve sin login del coach (misma miniatura del portal)
    img = client.get(f"/api/resources/products/{pid}/image")
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"

    # Desactivar → desaparece del portal (y su imagen deja de servirse) pero sigue
    # en el catálogo del coach
    client.patch(f"/api/resources/products/{pid}", headers=auth, json={"active": False})
    res = client.get(f"/api/p/{token}/resources").json()
    assert all(p["id"] != pid for p in res["products"])
    assert client.get(f"/api/resources/products/{pid}/image").status_code == 404
    assert any(p["id"] == pid for p in client.get("/api/resources/products", headers=auth).json())

    # Borrar → 404 al pedir su imagen
    assert client.delete(f"/api/resources/products/{pid}", headers=auth).status_code == 204
    assert client.get(f"/api/resources/products/{pid}/image").status_code == 404


def test_product_url_must_be_http(client, auth):
    bad = client.post("/api/resources/products", headers=auth, json={
        "title": "Malicioso", "url": "javascript:alert(1)", "category": "otro",
    })
    assert bad.status_code == 422

    bad_img = client.post("/api/resources/products", headers=auth, json={
        "title": "Imagen mala", "url": "https://ok.example.com",
        "image_url": "data:text/html,evil", "category": "otro",
    })
    assert bad_img.status_code == 422

    # URL obligatoria en blanco (solo espacios): 422 limpio, no un 500 por NOT NULL
    blank = client.post("/api/resources/products", headers=auth, json={
        "title": "Sin enlace", "url": "   ", "category": "otro",
    })
    assert blank.status_code == 422


def test_youtube_thumbnail_helper():
    from app.services.portal import youtube_thumbnail

    THUMB = "https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
    for ok in (
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ&t=30s",
        "https://m.youtube.com/watch?feature=share&v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube.com/live/dQw4w9WgXcQ",
    ):
        assert youtube_thumbnail(ok) == THUMB, ok
    for no in (
        None, "", "https://vimeo.com/123456789",
        "https://notyoutube.com/watch?v=dQw4w9WgXcQ",   # host que solo contiene la subcadena
        "https://example.com/youtu.be/dQw4w9WgXcQ",     # path que contiene la subcadena
    ):
        assert youtube_thumbnail(no) is None, no


def test_products_require_auth(client):
    # Sin token → la gestión está protegida…
    assert client.get("/api/resources/products").status_code == 401
    assert client.post("/api/resources/products",
                       json={"title": "X", "url": "https://x.example.com"}).status_code == 401


def test_start_client_resources_without_training(client, auth):
    """Paquete Start (solo nutrición): sus recursos NO llevan vídeos de ejercicios
    (no tiene rutina) pero SÍ los productos activos. El endpoint no revienta con
    un plan sin training_json."""
    from tests.test_package_tiers import _nutrition_only_plan_content

    body = client.post("/api/clients", headers=auth, json={
        "full_name": "Start Recursos",
        "email": f"startrec-{uuid.uuid4().hex[:8]}@example.com",
        "package_tier": "start",
    }).json()
    cid, token = body["client"]["id"], body["links"]["portal_token"]

    # Sin plan todavía: vacío digno, no error.
    res = client.get(f"/api/p/{token}/resources")
    assert res.status_code == 200
    assert res.json()["exercise_videos"] == []

    # Con plan SOLO-NUTRICIÓN publicado: sigue sin vídeos, y ve los productos.
    nutrition, training, education, flags = _nutrition_only_plan_content()
    assert training is None
    plan = client.post(f"/api/clients/{cid}/plans", headers=auth, json={
        "month_index": 1, "nutrition_json": nutrition, "training_json": training,
        "education_json": education, "guardrail_flags": flags, "generated_by": "test",
    }).json()
    client.post(f"/api/plans/{plan['id']}/publish", headers=auth)

    prod = client.post("/api/resources/products", headers=auth, json={
        "title": "Creatina", "url": "https://tienda.example.com/creatina",
        "category": "suplemento",
    }).json()
    res = client.get(f"/api/p/{token}/resources").json()
    assert res["exercise_videos"] == []
    assert any(p["id"] == prod["id"] for p in res["products"])


def test_upload_image_validation(client, auth):
    """La subida rechaza lo que no es una imagen real y lo que pasa de 5 MB."""
    prod = client.post("/api/resources/products", headers=auth, json={
        "title": "Con imagen", "url": "https://tienda.example.com/img",
        "category": "material",
    }).json()
    pid = prod["id"]

    # Un fichero que NO es imagen (texto renombrado a .png) → 422
    bad = client.post(f"/api/resources/products/{pid}/image", headers=auth,
                      files=[("file", ("evil.png", b"<script>alert(1)</script>", "image/png"))])
    assert bad.status_code == 422

    # Más de 5 MB → 413 (la lectura acotada corta sin bufferizar el resto)
    big = client.post(f"/api/resources/products/{pid}/image", headers=auth,
                      files=[("file", ("big.png", b"\x89PNG" + b"0" * (5 * 1024 * 1024 + 10), "image/png"))])
    assert big.status_code == 413

    # Sin login del coach, la subida está prohibida
    anon = client.post(f"/api/resources/products/{pid}/image",
                       files=[("file", ("p.png", _png_bytes(), "image/png"))])
    assert anon.status_code == 401
