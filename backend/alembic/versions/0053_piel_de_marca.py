"""La PIEL de la marca: que el switch cambie de verdad lo que se ve.

Hasta aquí, cambiar a Professional cambiaba tres colores y poco más. El panel
seguía siendo crema, el portal seguía siendo el azul noche de DQR con un brillo
naranja abajo, y las páginas públicas seguían imprimiendo el logo de DQ. Peor:
el `color_secondary` de Professional es un negro (#161616) y ese color pinta el
ANILLO DE FOCO del panel y el ANILLO DE PROGRESO del portal — negro sobre negro,
invisible. Tres colores sueltos no son una identidad.

`skin` es el nombre de la identidad COMPLETA de la marca: no un color, sino el
juego entero (fondo, tinta, superficies, líneas, luces, formas y tipografía)
que el frontend aplica de golpe con `data-piel`. Es data y no un `if` por slug
a propósito, igual que `anamnesis_variant` y `doc_variant`: una marca nueva
elige su piel sin tocar código, y la piel de una marca no puede alterar la otra.

· 'dqr'          — crema, naranja y azul. Exactamente lo que había.
· 'professional' — negro y dorado, la identidad del Centre Salut & Fitness.
"""
from alembic import op
import sqlalchemy as sa

revision = "0053"
down_revision = "0052"
branch_labels = None
depends_on = None


def _cols(insp, tabla: str) -> set[str]:
    try:
        return {c["name"] for c in insp.get_columns(tabla)}
    except Exception:  # noqa: BLE001 — tabla aún inexistente
        return set()


def upgrade() -> None:
    bind = op.get_bind()
    # En una instalación NUEVA la 0001 ya crea las columnas desde los modelos:
    # sin esta guarda, `alembic upgrade head` muere aquí y —como Alembic corre
    # la cadena en una transacción— deja la base SIN UNA SOLA TABLA y el
    # contenedor en bucle de arranque. Es el camino del día que se pierda el
    # VPS, y `tests/test_migraciones.py` lo vigila.
    if "skin" not in _cols(sa.inspect(bind), "brand_config"):
        op.add_column("brand_config", sa.Column("skin", sa.String(20), nullable=True))
    # Toda marca existente conserva lo que ve hoy: la piel de DQR.
    bind.execute(sa.text("UPDATE brand_config SET skin = 'dqr' WHERE skin IS NULL"))
    bind.execute(sa.text(
        "UPDATE brand_config SET skin = 'professional'"
        " WHERE slug = 'professional-fitness'"))


def downgrade() -> None:
    if "skin" in _cols(sa.inspect(op.get_bind()), "brand_config"):
        op.drop_column("brand_config", "skin")
