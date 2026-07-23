"""0026: integración Google Calendar / Meet para las videollamadas Pro.

- `google_credentials`: credenciales OAuth de la cuenta de Google del coach
  (fila única single-tenant; guarda el refresh_token para crear eventos).
- `video_calls`: nuevas columnas para el evento con hora concreta creado en
  Google Calendar (scheduled_at, duration_min, meet_url, google_event_id,
  google_html_link). Se conserva `scheduled_for` (día) por compatibilidad con
  los recordatorios/alertas existentes.
Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if "google_credentials" not in insp.get_table_names():
        op.create_table(
            "google_credentials",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("google_email", sa.String(200), nullable=True),
            sa.Column("access_token", sa.Text, nullable=True),
            sa.Column("refresh_token", sa.Text, nullable=True),
            sa.Column("token_expiry", sa.DateTime(timezone=True), nullable=True),
            sa.Column("scope", sa.Text, nullable=True),
            sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
        )

    vc_cols = {c["name"] for c in insp.get_columns("video_calls")}
    new_cols = [
        ("scheduled_at", sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True)),
        ("duration_min", sa.Column("duration_min", sa.Integer, nullable=True)),
        ("meet_url", sa.Column("meet_url", sa.String(500), nullable=True)),
        ("google_event_id", sa.Column("google_event_id", sa.String(255), nullable=True)),
        ("google_html_link", sa.Column("google_html_link", sa.String(500), nullable=True)),
    ]
    for name, col in new_cols:
        if name not in vc_cols:
            op.add_column("video_calls", col)


def downgrade() -> None:
    pass
