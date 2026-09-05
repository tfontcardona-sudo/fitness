"""La marca PROFESSIONAL con sus datos de verdad, y lo que una marca simple
necesita que DQR no tenía.

Professional (Centre Salut & Fitness, Girona) es un CENTRO, no una asesoría
online: tiene una dirección física, un solo plan mensual —Génesis.99, 99 €/mes—
y el resto de sus servicios (entreno personal por horas y packs de 10 sesiones)
se cobran en el propio centro, no por la web. Dos cosas que el perfil de marca
no sabía representar y que se añaden aquí:

- `contact_address`: la dirección del centro. En una asesoría online no hacía
  falta; en un gimnasio es de lo primero que busca el cliente.
- `extra_services`: lo que la marca vende pero NO cobra por la web. Sin esto,
  la pantalla de Vender de Professional enseñaría un solo producto y daría la
  impresión de que el resto no existe.

Y las TARIFAS de Professional sustituyen a la copia de las de DQR que se dejó
en el perfil al crearlo: 99 €/mes y nada más. Que un plan no esté en `prices`
significa que esta marca NO lo vende — el catálogo y el alta de precios en
Stripe lo respetan.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None


# Génesis.99: el único plan mensual del centro. Va en `full` (entreno +
# nutrición) porque es una preparación completa, y sin más duraciones: no se
# vende ni trimestral ni semestral, y no hay oferta de captación.
_PRECIOS_PF = {"full": {"1m": 9900}}

# Lo que se cobra EN EL CENTRO. Aquí solo se muestran (la web no los cobra).
_EXTRA_PF = [
    {"title": "Entreno personal · socios", "price": "50 €/h"},
    {"title": "Entreno personal · no socios", "price": "60 €/h"},
    {"title": "Pack 10 sesiones · socios", "price": "350 €"},
    {"title": "Pack 10 sesiones · no socios", "price": "450 €"},
]

_LABELS_PF = {"full": "Génesis.99", "train": "Entreno personal",
              "nutri": "Plan nutricional"}
_TAGLINES_PF = {"full": "preparación mensual completa",
                "train": "entrenamiento personal",
                "nutri": "pauta de nutrición"}


def _cols(insp, table: str) -> set[str]:
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = _cols(insp, "brand_config")
    if "contact_address" not in cols:
        op.add_column("brand_config", sa.Column("contact_address", sa.String(200), nullable=True))
    if "extra_services" not in cols:
        op.add_column("brand_config",
                      sa.Column("extra_services", postgresql.JSONB(), nullable=True))

    import json

    op.get_bind().execute(
        sa.text(
            "UPDATE brand_config SET"
            " name = 'Professional',"
            " tagline = 'Centre Salut & Fitness · Lidia Miralpeix i Toni Pérez',"
            " color_primary = '#F2C230', color_secondary = '#2E2E2E',"
            " color_bg = '#1F1F1F',"
            " contact_phone = '+34 640 756 220',"
            " contact_address = 'Carretera Pierre Vilar, 2 · 17002 Girona',"
            " service_labels = CAST(:labels AS jsonb),"
            " service_taglines = CAST(:taglines AS jsonb),"
            " prices = CAST(:precios AS jsonb),"
            " extra_services = CAST(:extra AS jsonb),"
            " page_title = 'Professional · Centre Salut & Fitness',"
            " app_name = 'Professional', app_short_name = 'Professional'"
            " WHERE slug = 'professional-fitness'"),
        {"labels": json.dumps(_LABELS_PF, ensure_ascii=False),
         "taglines": json.dumps(_TAGLINES_PF, ensure_ascii=False),
         "precios": json.dumps(_PRECIOS_PF),
         "extra": json.dumps(_EXTRA_PF, ensure_ascii=False)},
    )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = _cols(insp, "brand_config")
    if "extra_services" in cols:
        op.drop_column("brand_config", "extra_services")
    if "contact_address" in cols:
        op.drop_column("brand_config", "contact_address")
