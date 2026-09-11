"""La cita de la revisión puede ser una VISITA AL CENTRO, no solo una videollamada.

DQR es una asesoría online: su revisión quincenal se hace por Meet y por eso
todo el ciclo se llamaba «videollamada». Professional es un centro con sala: su
cliente entrena allí y lo natural es que la revisión sea una VISITA — sin Meet
y, sobre todo, sin depender de que el coach tenga una cuenta de Google conectada
(un gimnasio no tiene por qué tenerla, y sin ella el ciclo entero se quedaba
atascado en «pendiente de agendar»).

Dos columnas, ninguna obligatoria:

- `brand_config.cita_modo` — qué hace ESTA marca: 'videollamada' (por defecto,
  lo de siempre) o 'presencial'. Explícito a propósito: deducirlo de «la marca
  tiene dirección» habría convertido rellenar un dato de contacto en cambiarle
  el tipo de cita a toda la cartera.
- `video_calls.modo` — lo que se acordó en ESTA cita, SELLADO en la fila. Igual
  que la marca del cliente: si mañana el centro pasa a hacerlas por vídeo, la
  visita ya confirmada sigue siendo una visita.

NULL = 'videollamada' en las dos: las filas de siempre no se tocan.
"""
from alembic import op
import sqlalchemy as sa

revision = "0052"
down_revision = "0051"
branch_labels = None
depends_on = None


def _cols(insp, table: str) -> set[str]:
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "cita_modo" not in _cols(insp, "brand_config"):
        op.add_column("brand_config", sa.Column("cita_modo", sa.String(16), nullable=True))
    if "modo" not in _cols(insp, "video_calls"):
        op.add_column("video_calls", sa.Column("modo", sa.String(16), nullable=True))
    op.get_bind().execute(sa.text(
        "UPDATE brand_config SET cita_modo = 'presencial'"
        " WHERE slug = 'professional-fitness'"))


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "modo" in _cols(insp, "video_calls"):
        op.drop_column("video_calls", "modo")
    if "cita_modo" in _cols(insp, "brand_config"):
        op.drop_column("brand_config", "cita_modo")
