"""Pagos: a qué suscripción pertenece cada factura.

Sin este dato, "¿cuántas facturas de la oferta lleva pagadas este cliente?" se
respondía contando TODAS las que constaban a su nombre, de siempre. Con eso, un
cliente que vuelve y contrata la oferta por SEGUNDA vez arrastraba las tres del
programa anterior: en cuanto pagaba la primera factura de 1 €, la cuenta daba
cuatro, el sistema daba el programa por cobrado entero y cancelaba la
suscripción. El coach entregaba tres meses de asesoría por 1 €.

Nullable: los movimientos antiguos se quedan sin él y el recuento sigue
funcionando (cae al criterio de antes solo para esas filas).

Revision ID: 0042
Revises: 0041
"""
from alembic import op
import sqlalchemy as sa

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None


def _cols(insp, table: str) -> set[str]:
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "subscription_id" not in _cols(insp, "payments"):
        op.add_column("payments", sa.Column(
            "subscription_id", sa.String(length=80), nullable=True))
        op.create_index("ix_payments_subscription_id", "payments", ["subscription_id"])
        # Las facturas de las suscripciones EN CURSO se sellan con la de su
        # ficha: una contratación a medio camino en el momento del despliegue
        # tiene que seguir contando entera (si no, no se cancelaría al cobrar
        # su última factura y habría un cargo de más). Las de un programa ya
        # terminado se quedan sin sello, que es justo lo que hay que excluir
        # cuando ese cliente vuelva a contratar.
        op.execute(sa.text("""
            UPDATE payments p
               SET subscription_id = c.stripe_subscription_id
              FROM clients c
             WHERE p.client_id = c.id
               AND p.kind = 'invoice'
               AND p.subscription_id IS NULL
               AND c.stripe_subscription_id IS NOT NULL
        """))


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "subscription_id" in _cols(insp, "payments"):
        op.drop_index("ix_payments_subscription_id", table_name="payments")
        op.drop_column("payments", "subscription_id")
