"""Ningún ajuste documentado puede estar muerto.

`.env.example` es la documentación viva de la configuración: lo que sale ahí es
lo que el dueño creerá que puede tocar. Un interruptor que no hace nada es peor
que no tenerlo — se cambia, no pasa nada, y nadie sabe por qué.

Alcance HONESTO de esta guarda: caza la clave documentada que no existe en
`Settings` (poner nada en el .env no cambiaría nada) y el ajuste declarado que
NADIE menciona en todo `app/`. No caza el caso más sutil —un ajuste que sí se
lee, pero cuyo valor va a parar a un sitio que nadie consulta después—, que es
justo lo que le pasaba a `AUTO_PILOT_DEFAULT`: se leía para escribirlo en una
columna que no leía nadie. Ese hay que verlo a mano.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
APP = RAIZ / "backend" / "app"
EJEMPLO = RAIZ / ".env.example"

# Claves que NO son ajustes de la aplicación: las consumen Docker, Postgres,
# Caddy o Vite antes de que arranque nada de Python.
AJENAS = {
    "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB",
    "VITE_API_URL", "COMPOSE_PROJECT_NAME",
}

# Ajustes que el propio `config.py` resuelve por nombre COMPUESTO
# (`Settings.stripe_price_for(tier, periodo)` hace el `getattr`), así que su
# nombre nunca aparece escrito en el resto del código.
POR_NOMBRE_COMPUESTO = ("stripe_price_",)


def _claves_del_ejemplo() -> list[str]:
    if not EJEMPLO.exists():
        return []
    out = []
    for linea in EJEMPLO.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Z][A-Z0-9_]*)=", linea.strip())
        if m and m.group(1) not in AJENAS:
            out.append(m.group(1))
    return out


def _fuentes() -> str:
    """Todo `app/`, `config.py` INCLUIDO: hay ajustes que solo lee el propio
    config para derivar otra cosa (`DOMAIN` → `public_base_url`/`is_production`)
    y esos están perfectamente vivos. Lo que se descuenta después es la LÍNEA
    que los declara, que es la única mención que tiene un ajuste muerto."""
    return "\n".join(f.read_text(encoding="utf-8")
                     for f in APP.rglob("*.py") if "__pycache__" not in str(f))


def test_el_ejemplo_de_entorno_tiene_claves():
    assert len(_claves_del_ejemplo()) > 10, "no se pudo leer .env.example"


def test_todo_ajuste_documentado_existe_en_settings():
    from app.config import Settings

    campos = set(Settings.model_fields)
    huerfanas = [k for k in _claves_del_ejemplo() if k.lower() not in campos]
    assert not huerfanas, (
        "Estas claves están documentadas en .env.example y no existen en "
        "Settings: quien las ponga en su .env no cambiará nada. "
        + ", ".join(huerfanas))


def test_todo_ajuste_documentado_lo_menciona_alguien():
    from app.config import Settings

    fuentes = _fuentes()
    resolutor = (APP / "config.py").read_text(encoding="utf-8")
    mudos = []
    for k in _claves_del_ejemplo():
        campo = k.lower()
        if campo not in Settings.model_fields:
            continue  # lo cubre el test de arriba
        if campo.startswith(POR_NOMBRE_COMPUESTO):
            assert "stripe_price_for" in resolutor
            continue
        menciones = len(re.findall(rf"\b{campo}\b", fuentes))
        declaraciones = len(re.findall(rf"^\s*{campo}\s*:", fuentes, re.M))
        if menciones - declaraciones <= 0:
            mudos.append(k)
    assert not mudos, (
        "Estos ajustes están documentados y no los toca NADIE en todo app/: "
        "el dueño cree que configura algo y no configura nada. "
        + ", ".join(mudos))


def test_el_piloto_automatico_no_vuelve():
    """`AUTO_PILOT_DEFAULT` prometía un modo que no existía y que además iría
    contra el criterio del sistema (el coach revisa antes de generar). Se
    retiró: ni ajuste, ni superficie de API, ni escritura en el alta."""
    from app.config import Settings
    from app.schemas.entities import ClientOut, ClientUpdate

    assert "auto_pilot_default" not in Settings.model_fields
    assert "auto_pilot" not in ClientOut.model_fields
    assert "auto_pilot" not in ClientUpdate.model_fields
    assert "AUTO_PILOT" not in EJEMPLO.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# La página de "¡Pago recibido!" y lo que promete
# ---------------------------------------------------------------------------

def test_la_renovacion_no_promete_un_cuestionario_que_no_se_manda():
    """`success_url` marca la renovación con `?r=1`. Sin eso, el cartel de
    "¡Pago recibido!" decía a TODO el mundo que ya tenía su cuestionario en el
    correo, y quien renueva no recibe ninguno: se quedaba esperándolo, y
    rebuscando en el spam, un email que no existe."""
    from app.models import Client
    from app.services.stripe_service import _es_primera_compra

    assert _es_primera_compra(None) is True                       # registro personal
    assert _es_primera_compra(Client(status="onboarding")) is True  # alta manual
    for estado in ("active", "review_pending", "at_risk", "inactive"):
        assert _es_primera_compra(Client(status=estado)) is False, estado
