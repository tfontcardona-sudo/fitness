"""El pago del cliente deja de ser un sí/no sin memoria.

Hasta aquí la ficha solo sabía DOS cosas del dinero: `payment_status`
("pending"|"paid") y `paid_at` (el último cobro, sin importe). Con eso no se
puede responder a lo que el coach pregunta de verdad delante de un cliente:
cuánto le toca pagar, cuándo fue el último, cuándo es el próximo, cómo paga, y
—cuando no ha pagado— POR QUÉ.

  payment_method          cómo pagó la última vez: stripe | efectivo |
                          transferencia | bizum | otro. Los cobros de la
                          pasarela lo sellan solos; los de fuera, el coach al
                          anotarlos. Sin esto, "pagó 129 €" no decía por dónde
                          entró el dinero y el coach tenía que abrir el libro.
  unpaid_reason           por qué NO está pagado: alta (nunca ha pagado) |
                          cancelado (dio de baja su suscripción) | fallido
                          (Stripe no pudo cobrar). Lo demás se DEDUCE y no se
                          guarda: "vencido" sale de la ventana de renovación,
                          que ya es una sola verdad (services/renewals.py).
                          Un impago sin motivo es un rojo que no se sabe
                          atender: no es lo mismo reclamar un alta que llamar a
                          quien se acaba de dar de baja.
  unpaid_since            desde cuándo debe (el día de la baja o del fallo).
  payment_notice_sent_at  aviso PUSH de "toca pagar" mandado AL CLIENTE en este
                          ciclo. Sello propio, no el del email: si el correo
                          falla se reintenta al día siguiente, y compartir el
                          sello habría matado ese reintento (o, al revés,
                          repetido el push cada día).

TODAS nulables y TODAS a NULL para quien ya existe. NULL en `unpaid_reason`
significa "no consta", y quien está pagado no tiene ninguno: ni un cliente en
curso cambia de estado al desplegar esto.
"""
from alembic import op
import sqlalchemy as sa

revision = "0057"
down_revision = "0056"
branch_labels = None
depends_on = None

# Idempotente a propósito: `tests/test_migraciones.py` corre la cadena entera
# desde una base VACÍA, y una migración que no se puede repetir deja el
# arranque del VPS a merced de un despliegue cortado a medias.
_COLUMNAS = (
    ("payment_method", "VARCHAR(20)"),
    ("unpaid_reason", "VARCHAR(16)"),
    ("unpaid_since", "TIMESTAMPTZ"),
    ("payment_notice_sent_at", "TIMESTAMPTZ"),
)


def upgrade() -> None:
    bind = op.get_bind()
    for nombre, tipo in _COLUMNAS:
        bind.execute(sa.text(
            f"ALTER TABLE clients ADD COLUMN IF NOT EXISTS {nombre} {tipo}"))
    # Relleno del pasado, solo donde es un HECHO y no una suposición: quien
    # está pendiente y no tiene ningún cobro es un alta sin pagar. A quien pagó
    # alguna vez y hoy está pendiente no se le inventa el motivo (pudo ser una
    # baja, un impago o un ciclo vencido): queda sin motivo y el panel dice lo
    # que sí sabe.
    bind.execute(sa.text(
        "UPDATE clients SET unpaid_reason = 'alta', unpaid_since = created_at "
        "WHERE payment_status = 'pending' AND paid_at IS NULL "
        "AND unpaid_reason IS NULL"))


def downgrade() -> None:
    bind = op.get_bind()
    for nombre, _ in _COLUMNAS:
        bind.execute(sa.text(f"ALTER TABLE clients DROP COLUMN IF EXISTS {nombre}"))
