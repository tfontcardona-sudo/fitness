"""Cada edición del coach, con SEÑAL y ORIGEN.

`plan_edits` guardaba la categoría ("calculo", "volumen"…) y la frase del diff.
Con eso se puede decir "el coach corrige mucho el cálculo", pero no lo que él
quiere saber: QUÉ campo concreto toca siempre, y POR QUÉ lo cambia por.

Tres columnas, todas derivadas de forma DETERMINISTA (0 créditos):

- `signal`: el campo normalizado ("nutricion.kcal", "entreno.ejercicio",
  "comida.desayuno"). Es la clave por la que se cuentan los patrones.
- `source`: de dónde vino la edición — el editor del panel, un Word subido, un
  plan ajeno importado, una COPIA de otro cliente, un modelo aplicado, un swap
  de ejercicio o la corrección de los ajustes de la revisión. Sin esto, cambiar
  lo copiado y corregir a la IA se mezclaban en la misma bolsa.
- `detail`: la sustitución en limpio ("pollo → pavo"), que es de donde sale
  "siempre cambias X por Y".

Las filas que ya existen se quedan sin señal: no se puede inventar (su frase
original sí sigue ahí, en `note`). El minero las ignora y aprende de las nuevas.
"""
from alembic import op
import sqlalchemy as sa

revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None


def _cols(insp, table: str) -> set[str]:
    return {c["name"] for c in insp.get_columns(table)}


def _indices(insp, table: str) -> set[str]:
    return {i["name"] for i in insp.get_indexes(table)}


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = _cols(insp, "plan_edits")
    if "signal" not in cols:
        op.add_column("plan_edits", sa.Column("signal", sa.String(60), nullable=True))
    if "source" not in cols:
        op.add_column("plan_edits", sa.Column("source", sa.String(20), nullable=True))
    if "detail" not in cols:
        op.add_column("plan_edits", sa.Column("detail", sa.String(200), nullable=True))
    idx = _indices(insp, "plan_edits")
    if "ix_plan_edits_signal" not in idx:
        op.create_index("ix_plan_edits_signal", "plan_edits", ["signal"])
    if "ix_plan_edits_source" not in idx:
        op.create_index("ix_plan_edits_source", "plan_edits", ["source"])


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    idx = _indices(insp, "plan_edits")
    if "ix_plan_edits_source" in idx:
        op.drop_index("ix_plan_edits_source", table_name="plan_edits")
    if "ix_plan_edits_signal" in idx:
        op.drop_index("ix_plan_edits_signal", table_name="plan_edits")
    cols = _cols(insp, "plan_edits")
    for c in ("detail", "source", "signal"):
        if c in cols:
            op.drop_column("plan_edits", c)
