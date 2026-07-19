"""0021: vídeos de ejercicios subidos como archivo + portada global.

`exercises.video_path`: archivo de vídeo subido (relativo al storage, bajo
media/). Tiene prioridad sobre `video_url` (enlace externo) al mostrarse.
`brand_config.video_cover_path`: imagen de PORTADA única para todos los vídeos
de ejercicios del portal. Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    ex_cols = {c["name"] for c in insp.get_columns("exercises")}
    if "video_path" not in ex_cols:
        op.add_column("exercises", sa.Column("video_path", sa.String(500), nullable=True))
    brand_cols = {c["name"] for c in insp.get_columns("brand_config")}
    if "video_cover_path" not in brand_cols:
        op.add_column("brand_config", sa.Column("video_cover_path", sa.String(500), nullable=True))


def downgrade() -> None:
    pass
