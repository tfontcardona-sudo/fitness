"""Lo que USA cada negocio: que el switch no enseñe pantallas de la otra marca.

El panel enseñaba lo mismo con Professional activa que con DQR: la pestaña de
PRODUCTOS recomendados (el catálogo de afiliación de una asesoría online), la
PÁGINA DE ENLACES del perfil de Instagram, la conexión con Google… Un centro
con local no usa nada de eso —vende en el mostrador, tiene su dirección y
revisa a sus clientes en la sala—, así que el coach veía media docena de
apartados de un negocio que no es el que tiene delante.

`features` es la DECLARACIÓN de lo que un negocio usa, y guarda solo lo que NO
se puede deducir de otro dato. Lo demás ya estaba dicho y sería una segunda
verdad que se contradice sola:

· las videollamadas las dice `cita_modo` (una visita al centro no es una
  videollamada y no necesita Google),
· la oferta la dicen sus `prices` (la marca que no la vende no la anuncia),
· el bloque educativo lo dice `doc_variant`,
· el cuestionario en PDF lo dice `anamnesis_variant` (el PDF oficial es el de
  DQR: dárselo al cliente de otro negocio es mandarle el cuestionario de una
  asesoría con la que no ha contratado nada).

Un diccionario VACÍO significa "usa todo": DQR y cualquier marca nueva siguen
igual, y añadir un negocio no obliga a rellenar una lista.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0054"
down_revision = "0053"
branch_labels = None
depends_on = None


def _cols(insp, tabla: str) -> set[str]:
    try:
        return {c["name"] for c in insp.get_columns(tabla)}
    except Exception:  # noqa: BLE001 — tabla aún inexistente
        return set()


def upgrade() -> None:
    bind = op.get_bind()
    # En una instalación NUEVA la 0001 crea las columnas desde los modelos: sin
    # la guarda, `alembic upgrade head` muere aquí y deja la base SIN UNA SOLA
    # TABLA (Alembic corre la cadena en una transacción).
    if "features" not in _cols(sa.inspect(bind), "brand_config"):
        op.add_column("brand_config",
                      sa.Column("features", postgresql.JSONB, nullable=True))
    # Lo que el CENTRO no usa. Se escribe solo lo que se apaga: lo que no está
    # declarado se usa, así que esta marca no se queda sin nada que se añada
    # al sistema en el futuro.
    bind.execute(sa.text(
        "UPDATE brand_config SET features = '{\"productos\": false,"
        " \"enlaces\": false}'::jsonb WHERE slug = 'professional-fitness'"))


def downgrade() -> None:
    if "features" in _cols(sa.inspect(op.get_bind()), "brand_config"):
        op.drop_column("brand_config", "features")
