"""Cuánto documento quiere cada marca.

El plan de DQR es un documento elaborado: índice, tarjeta del plato saludable y
una sección educativa completa (píldoras, técnica por patrón de movimiento y
preguntas frecuentes). Es su forma de trabajar y no se toca.

Una marca sencilla quiere el plan y poco más. `doc_variant`:

- 'completo' (por defecto): el documento de siempre, entero.
- 'simple': sin índice, sin la tarjeta de plantilla y sin la sección educativa.
  Lo que se queda es el PLAN — objetivos, cifras del día, tomas y sus opciones,
  suplementación, sesiones con series/repeticiones/progresión, cardio, deload y
  el bloque de contacto. Cumple su función; ocupa bastante menos.

Lo que NO depende de esto: los números. Salen del mismo motor de cálculo y
pasan por los mismos guardarraíles en las dos variantes.
"""
from alembic import op
import sqlalchemy as sa

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None


def _cols(insp, table: str) -> set[str]:
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "doc_variant" not in _cols(insp, "brand_config"):
        op.add_column("brand_config",
                      sa.Column("doc_variant", sa.String(20), nullable=False,
                                server_default="completo"))
    bind.execute(sa.text(
        "UPDATE brand_config SET doc_variant = 'simple'"
        " WHERE slug = 'professional-fitness'"))


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "doc_variant" in _cols(insp, "brand_config"):
        op.drop_column("brand_config", "doc_variant")
