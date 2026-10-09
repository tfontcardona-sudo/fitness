"""EL INTERRUPTOR GLOBAL: pausar todo el acceso público, y rotar quién entra
al panel — las dos piezas de la misma petición (24-09-2026 → 08-10-2026).

1. Modo mantenimiento (`services/mantenimiento.py` + `deps.no_en_mantenimiento`):
   activo, TODO lo público (portal del cliente, pagos, landing/planes/oferta)
   responde 503 con el mensaje del coach. El panel del coach y el webhook de
   Stripe NUNCA pasan por aquí — si se cortan, nadie puede ni trabajar ni
   volver a activarlo, y los cobros/bajas en marcha se perderían.
2. Rotación de admins (`seeds.run.seed_admins`): cambiar `ADMIN_1_USER`/`PASS`
   (o `ADMIN_2_*`) en el `.env` y reiniciar basta para que el acceso ANTIGUO
   deje de servir — sin tocar nada más, porque `get_current_user` vuelve a
   consultar la tabla `users` en cada petición.
"""
import os

import pytest
from sqlalchemy import delete, select

from app.config import Settings
from app.models import User


def _db_available() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings

        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytest_db = pytest.mark.skipif(not _db_available(), reason="Requiere PostgreSQL")


# --------------------------------------------------------- modo mantenimiento ---

@pytest_db
def test_mantenimiento_bloquea_lo_publico_y_respeta_el_mensaje():
    """REGRESIÓN: portal del cliente y landing pública responden 503 con el
    mensaje del coach cuando el interruptor está activo — y vuelven a su
    comportamiento normal al desactivarlo. Falla sin `deps.no_en_mantenimiento`."""
    from fastapi.testclient import TestClient

    from app.db import SessionLocal
    from app.main import app
    from app.services import mantenimiento as m

    db = SessionLocal()
    try:
        m.desactivar(db)
        with TestClient(app) as c:
            # Sin mantenimiento: comportamiento normal (404 de token inválido,
            # no 503 — confirma que el interruptor no está "siempre puesto").
            assert c.get("/api/p/token-que-no-existe/state").status_code == 404
            assert c.get("/api/public/landing").status_code == 200
            assert c.get("/api/public/plan-prices").status_code == 200

            m.activar(db, "Pausado por mantenimiento — vuelve pronto.")
            r = c.get("/api/p/token-que-no-existe/state")
            assert r.status_code == 503
            assert r.json()["detail"] == "Pausado por mantenimiento — vuelve pronto."
            r2 = c.get("/api/public/landing")
            assert r2.status_code == 503
            r3 = c.get("/api/public/plan-prices")
            assert r3.status_code == 503
            # El enlace de pago directo (sin alta previa) también se corta.
            r4 = c.get("/api/pay/plan/full/1m", follow_redirects=False)
            assert r4.status_code == 503
            # Lo abre una PERSONA desde WhatsApp: ve el aviso del coach en una
            # página, nunca el JSON crudo (y el mensaje va escapado).
            assert r4.headers["content-type"].startswith("text/html")
            assert "Pausado por mantenimiento" in r4.text
            assert '"detail"' not in r4.text
            r5 = c.get("/api/pay/token-cualquiera-largo", follow_redirects=False)
            assert r5.status_code == 503
            assert r5.headers["content-type"].startswith("text/html")

            m.desactivar(db)
            assert c.get("/api/public/landing").status_code == 200
    finally:
        m.desactivar(db)
        db.close()


@pytest_db
def test_mantenimiento_no_toca_el_panel_del_coach_ni_el_webhook():
    """REGRESIÓN CRÍTICA: con el interruptor activo, el coach TIENE que poder
    seguir entrando (si no, nadie puede volver a desactivarlo) y el webhook de
    Stripe TIENE que seguir llevando la cuenta de los cobros. Falla si alguien
    mueve el `Depends(no_en_mantenimiento)` a un sitio que los alcance."""
    from fastapi.testclient import TestClient

    from app.db import SessionLocal
    from app.main import app
    from app.services import mantenimiento as m

    db = SessionLocal()
    try:
        m.activar(db, "Pausado")
        with TestClient(app) as c:
            # Login del coach: 401 (credenciales de prueba inventadas) y NO 503
            # — si estuviera gateado, también daría 401 por casualidad, así que
            # se comprueba el MENSAJE para no colar un falso verde.
            r = c.post("/api/auth/login", json={"username": "x", "password": "y"})
            assert r.status_code == 401
            assert "incorrectas" in r.json()["detail"].lower()

            # Webhook de Stripe: firma inválida → 400 (llegó al handler), no 503.
            r2 = c.post("/api/stripe/webhook", content=b"{}",
                        headers={"stripe-signature": "firma-invalida"})
            assert r2.status_code != 503

            # /api/health tampoco: es la sonda de vida del despliegue (con la
            # pausa activa, sondear una ruta pública haría fallar SIEMPRE el
            # deploy aunque la API estuviera sana).
            r3 = c.get("/api/health")
            assert r3.status_code == 200 and r3.json()["status"] == "ok"
    finally:
        m.desactivar(db)
        db.close()


@pytest_db
def test_endpoint_de_mantenimiento_exige_coach_y_cambia_el_estado():
    """`GET/POST /api/system/mantenimiento`: público = 401; con el JWT del
    coach, activa/desactiva y el cambio se nota YA (sin esperar la caché)."""
    from fastapi.testclient import TestClient

    from app.db import SessionLocal
    from app.main import app
    from app.security import create_access_token
    from app.services import mantenimiento as m

    db = SessionLocal()
    try:
        m.desactivar(db)
        usuario = os.environ.get("ADMIN_1_USER", "coach1")
        auth = {"Authorization": f"Bearer {create_access_token(usuario)}"}
        with TestClient(app) as c:
            assert c.get("/api/system/mantenimiento").status_code == 401

            r = c.get("/api/system/mantenimiento", headers=auth)
            assert r.status_code == 200 and r.json()["activo"] is False

            r2 = c.post("/api/system/mantenimiento", headers=auth,
                        json={"activo": True, "mensaje": "Cerrado por hoy"})
            assert r2.status_code == 200 and r2.json()["activo"] is True

            # El cambio se aplica YA a una ruta pública, sin esperar la caché.
            assert c.get("/api/public/landing").status_code == 503

            r3 = c.post("/api/system/mantenimiento", headers=auth, json={"activo": False})
            assert r3.status_code == 200 and r3.json()["activo"] is False
            assert c.get("/api/public/landing").status_code == 200
    finally:
        m.desactivar(db)
        db.close()


# ------------------------------------------------------- rotación de admins ---

def _settings(**kw) -> Settings:
    base = dict(jwt_secret="x" * 48, portal_token_secret="y" * 48, domain="",
                _env_file=None)
    base.update(kw)
    return Settings(**base)


@pytest_db
def test_rotar_admin_invalida_el_antiguo_y_habilita_el_nuevo(monkeypatch):
    """REGRESIÓN: cambiar ADMIN_1_USER/PASS y volver a correr `seed_admins` (lo
    que hace `entrypoint.sh` en cada arranque) hace que el usuario ANTIGUO dé
    401 de inmediato y el NUEVO pueda entrar — sin tocar nada más, porque
    `get_current_user` consulta `users` en cada petición. Falla sin la
    reescritura de `seed_admins` (el admin antiguo se quedaba vivo para
    siempre, solo se creaban admins nuevos, nunca se borraban los viejos)."""
    from app.db import SessionLocal
    from app.routers import auth
    from app.security import create_access_token, verify_password
    from app.seeds.run import seed_admins

    # /api/auth/login comparte el límite de 5/minuto con TODA la suite (mismo
    # criterio que test_public_register.py/test_stripe.py): sin esto, este
    # test podía chocar con un 429 si corría cerca de otros que también
    # inician sesión de verdad.
    monkeypatch.setattr(auth.limiter, "enabled", False)
    db = SessionLocal()
    try:
        db.execute(delete(User).where(User.username.in_(["viejo-admin-test", "tonifont-test"])))
        db.commit()

        monkeypatch.setattr(
            "app.seeds.run.settings",
            _settings(admin_1_user="viejo-admin-test", admin_1_pass="passvieja1234",
                      admin_2_user="", admin_2_pass=""),
        )
        seed_admins(db)
        assert db.scalar(select(User).where(User.username == "viejo-admin-test"))

        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app) as c:
            tok_viejo = create_access_token("viejo-admin-test")
            r = c.get("/api/auth/me", headers={"Authorization": f"Bearer {tok_viejo}"})
            assert r.status_code == 200  # todavía sirve: aún está en el .env

            # Rotación: nuevo usuario/contraseña en el .env + "reinicio" (volver
            # a correr seed_admins, exactamente lo que hace entrypoint.sh).
            monkeypatch.setattr(
                "app.seeds.run.settings",
                _settings(admin_1_user="tonifont-test", admin_1_pass="nuevapass1234",
                          admin_2_user="", admin_2_pass=""),
            )
            seed_admins(db)

            # El ANTIGUO deja de servir YA, con el mismo token de antes.
            r2 = c.get("/api/auth/me", headers={"Authorization": f"Bearer {tok_viejo}"})
            assert r2.status_code == 401

            # El NUEVO funciona, con su contraseña nueva.
            r3 = c.post("/api/auth/login",
                        json={"username": "tonifont-test", "password": "nuevapass1234"})
            assert r3.status_code == 200
    finally:
        # `seed_admins` ROTA de verdad: sin restaurar el admin REAL del
        # entorno aquí, este test se lo come para el resto de la suite (que
        # comparte la misma base) en cuanto deshace el monkeypatch.
        monkeypatch.undo()
        seed_admins(db)
        db.execute(delete(User).where(User.username.in_(["viejo-admin-test", "tonifont-test"])))
        db.commit()
        db.close()


@pytest_db
def test_rotar_admin_actualiza_la_contrasena_del_mismo_usuario(monkeypatch):
    """Si solo cambia la CONTRASEÑA (mismo username), el hash se actualiza: la
    contraseña vieja deja de valer y la nueva funciona."""
    from app.db import SessionLocal
    from app.routers import auth
    from app.seeds.run import seed_admins

    # Tres logins REALES en este test (la única forma de comprobar hash viejo
    # vs nuevo): sin apagar el límite compartido de /api/auth/login, choca con
    # un 429 si corre cerca de otros tests que también inician sesión.
    monkeypatch.setattr(auth.limiter, "enabled", False)
    db = SessionLocal()
    try:
        db.execute(delete(User).where(User.username == "mismo-admin-test"))
        db.commit()
        monkeypatch.setattr(
            "app.seeds.run.settings",
            _settings(admin_1_user="mismo-admin-test", admin_1_pass="passA1234",
                      admin_2_user="", admin_2_pass=""),
        )
        seed_admins(db)

        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app) as c:
            r = c.post("/api/auth/login",
                       json={"username": "mismo-admin-test", "password": "passA1234"})
            assert r.status_code == 200

            monkeypatch.setattr(
                "app.seeds.run.settings",
                _settings(admin_1_user="mismo-admin-test", admin_1_pass="passB5678",
                          admin_2_user="", admin_2_pass=""),
            )
            seed_admins(db)

            r2 = c.post("/api/auth/login",
                        json={"username": "mismo-admin-test", "password": "passA1234"})
            assert r2.status_code == 401  # la contraseña vieja ya no vale

            r3 = c.post("/api/auth/login",
                        json={"username": "mismo-admin-test", "password": "passB5678"})
            assert r3.status_code == 200
    finally:
        monkeypatch.undo()
        seed_admins(db)
        db.execute(delete(User).where(User.username == "mismo-admin-test"))
        db.commit()
        db.close()


@pytest_db
def test_guarda_de_seguridad_nunca_borra_a_todos(monkeypatch):
    """Si el `.env` se quedara SIN ningún admin configurado (los dos vacíos,
    por un error al editarlo), `seed_admins` NO borra a nadie: mejor un admin
    "de más" que un sistema sin ninguno y sin forma de arreglarlo desde fuera."""
    from app.db import SessionLocal
    from app.seeds.run import seed_admins

    db = SessionLocal()
    try:
        db.execute(delete(User).where(User.username == "superviviente-test"))
        db.commit()
        monkeypatch.setattr(
            "app.seeds.run.settings",
            _settings(admin_1_user="superviviente-test", admin_1_pass="passX1234",
                      admin_2_user="", admin_2_pass=""),
        )
        seed_admins(db)
        assert db.scalar(select(User).where(User.username == "superviviente-test"))

        monkeypatch.setattr(
            "app.seeds.run.settings",
            _settings(admin_1_user="", admin_1_pass="", admin_2_user="", admin_2_pass=""),
        )
        seed_admins(db)
        assert db.scalar(select(User).where(User.username == "superviviente-test"))
    finally:
        monkeypatch.undo()
        seed_admins(db)
        db.execute(delete(User).where(User.username == "superviviente-test"))
        db.commit()
        db.close()


@pytest_db
def test_cambiar_solo_la_contrasena_mata_las_sesiones_abiertas(monkeypatch):
    """REGRESIÓN: rotar SOLO la contraseña (el usuario conserva su nombre) debe
    invalidar los tokens ya emitidos con la anterior. Antes `get_current_user`
    solo miraba que el usuario siguiera existiendo, así que una sesión robada
    seguía viva hasta 72 h después de 'rotar'. Falla sin `password_changed_at`."""
    import time

    import jwt

    from app.config import settings as real_settings
    from app.db import SessionLocal
    from app.routers import auth
    from app.security import JWT_ALGORITHM, create_access_token
    from app.seeds.run import seed_admins

    monkeypatch.setattr(auth.limiter, "enabled", False)
    db = SessionLocal()
    try:
        db.execute(delete(User).where(User.username == "sesion-admin-test"))
        db.commit()
        monkeypatch.setattr(
            "app.seeds.run.settings",
            _settings(admin_1_user="sesion-admin-test", admin_1_pass="passA1234",
                      admin_2_user="", admin_2_pass=""),
        )
        seed_admins(db)

        from fastapi.testclient import TestClient

        from app.main import app

        # Token emitido ANTES de la rotación (hace un minuto, para no depender
        # de que caiga en el mismo segundo que el cambio de contraseña).
        ahora = int(time.time())
        viejo = jwt.encode(
            {"sub": "sesion-admin-test", "iat": ahora - 60, "exp": ahora + 3600},
            real_settings.jwt_secret, algorithm=JWT_ALGORITHM)
        # Y un token SIN cambio de contraseña de por medio sigue sirviendo.
        with TestClient(app) as c:
            assert c.get("/api/auth/me", headers={"Authorization": f"Bearer {viejo}"}).status_code == 200

            monkeypatch.setattr(
                "app.seeds.run.settings",
                _settings(admin_1_user="sesion-admin-test", admin_1_pass="passB5678",
                          admin_2_user="", admin_2_pass=""),
            )
            seed_admins(db)

            r = c.get("/api/auth/me", headers={"Authorization": f"Bearer {viejo}"})
            assert r.status_code == 401
            assert "vuelve a entrar" in r.json()["detail"].lower()

            # Entrar de nuevo con la contraseña nueva da un token que SÍ sirve.
            r2 = c.post("/api/auth/login",
                        json={"username": "sesion-admin-test", "password": "passB5678"})
            assert r2.status_code == 200
            nuevo = r2.json()["access_token"]
            assert c.get("/api/auth/me", headers={"Authorization": f"Bearer {nuevo}"}).status_code == 200
            # Y los tokens sin el sello (p. ej. de tests) no se ven afectados
            # mientras nadie haya cambiado esa contraseña.
            assert create_access_token("sesion-admin-test")
    finally:
        monkeypatch.undo()
        seed_admins(db)
        db.execute(delete(User).where(User.username == "sesion-admin-test"))
        db.commit()
        db.close()


@pytest_db
def test_admin_a_medias_en_el_env_no_se_borra(monkeypatch):
    """REGRESIÓN: un admin con SOLO usuario o SOLO contraseña (error al editar
    el `.env`) no es una baja: `seed_admins` no borra a nadie hasta que se
    complete — aunque el OTRO admin siga bien configurado. Antes la guarda solo
    miraba si quedaban los dos vacíos, y borraba al admin roto dejándolo sin
    cuenta vieja NI nueva."""
    from app.db import SessionLocal
    from app.seeds.run import seed_admins

    db = SessionLocal()
    try:
        db.execute(delete(User).where(User.username.in_(["roto-test", "bueno-test", "nuevo-roto-test"])))
        db.commit()
        monkeypatch.setattr(
            "app.seeds.run.settings",
            _settings(admin_1_user="roto-test", admin_1_pass="passX1234",
                      admin_2_user="bueno-test", admin_2_pass="passY1234"),
        )
        seed_admins(db)
        assert db.scalar(select(User).where(User.username == "roto-test"))

        # El dueño cambia el usuario del admin 1 y deja su contraseña vacía.
        monkeypatch.setattr(
            "app.seeds.run.settings",
            _settings(admin_1_user="nuevo-roto-test", admin_1_pass="",
                      admin_2_user="bueno-test", admin_2_pass="passY1234"),
        )
        seed_admins(db)
        assert db.scalar(select(User).where(User.username == "roto-test")) is not None
        assert db.scalar(select(User).where(User.username == "bueno-test")) is not None
        assert db.scalar(select(User).where(User.username == "nuevo-roto-test")) is None
    finally:
        monkeypatch.undo()
        seed_admins(db)
        db.execute(delete(User).where(User.username.in_(["roto-test", "bueno-test", "nuevo-roto-test"])))
        db.commit()
        db.close()


@pytest_db
def test_vaciar_un_hueco_del_env_da_de_baja_a_ese_admin(monkeypatch):
    """El contrapunto de la guarda anterior: dejar AMBOS campos de un hueco
    vacíos es dar de baja a ese admin a propósito (un único login compartido)."""
    from app.db import SessionLocal
    from app.seeds.run import seed_admins

    db = SessionLocal()
    try:
        db.execute(delete(User).where(User.username.in_(["uno-test", "dos-test"])))
        db.commit()
        monkeypatch.setattr(
            "app.seeds.run.settings",
            _settings(admin_1_user="uno-test", admin_1_pass="passX1234",
                      admin_2_user="dos-test", admin_2_pass="passY1234"),
        )
        seed_admins(db)
        assert db.scalar(select(User).where(User.username == "dos-test"))

        monkeypatch.setattr(
            "app.seeds.run.settings",
            _settings(admin_1_user="uno-test", admin_1_pass="passX1234",
                      admin_2_user="", admin_2_pass=""),
        )
        seed_admins(db)
        assert db.scalar(select(User).where(User.username == "uno-test")) is not None
        assert db.scalar(select(User).where(User.username == "dos-test")) is None
    finally:
        monkeypatch.undo()
        seed_admins(db)
        db.execute(delete(User).where(User.username.in_(["uno-test", "dos-test"])))
        db.commit()
        db.close()


@pytest_db
def test_mismo_usuario_en_los_dos_huecos_gana_el_primero_y_el_log_no_nombra(monkeypatch, capsys):
    """REGRESIÓN (revisión del mecanismo de órdenes): con el MISMO usuario en
    ADMIN_1 y ADMIN_2 la contraseña vigente dependía del orden de un set — y cada
    arranque podía cerrar todas las sesiones. Ahora gana siempre el admin 1. Y los
    mensajes del seed no imprimen nombres de usuario (el log del despliegue es
    público: con el usuario conocido, el único secreto del panel sería la
    contraseña)."""
    from app.db import SessionLocal
    from app.security import verify_password
    from app.seeds.run import seed_admins

    db = SessionLocal()
    try:
        db.execute(delete(User).where(User.username.in_(["dup-test", "retirado-test"])))
        db.commit()
        monkeypatch.setattr(
            "app.seeds.run.settings",
            _settings(admin_1_user="retirado-test", admin_1_pass="passR1234",
                      admin_2_user="", admin_2_pass=""),
        )
        seed_admins(db)
        monkeypatch.setattr(
            "app.seeds.run.settings",
            _settings(admin_1_user="dup-test", admin_1_pass="primera1234",
                      admin_2_user="dup-test", admin_2_pass="segunda5678"),
        )
        capsys.readouterr()
        seed_admins(db)
        salida = capsys.readouterr().out
        fila = db.scalar(select(User).where(User.username == "dup-test"))
        assert fila is not None
        assert verify_password("primera1234", fila.password_hash)
        assert not verify_password("segunda5678", fila.password_hash)
        assert db.scalar(select(User).where(User.username == "retirado-test")) is None
        assert "retirado-test" not in salida and "dup-test" not in salida
        assert "accesos retirados" in salida
    finally:
        monkeypatch.undo()
        seed_admins(db)
        db.execute(delete(User).where(User.username.in_(["dup-test", "retirado-test"])))
        db.commit()
        db.close()
