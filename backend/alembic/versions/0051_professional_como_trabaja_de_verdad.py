"""PROFESSIONAL, como trabaja de verdad: cuota mensual, negro y dorado.

Lo que se sabía del centro al crear su perfil venía de una foto de tarifas.
Después hubo una conversación con ellos y su servicio es OTRO, así que el
perfil pasa a describir el negocio real:

- **Pack Premium, 129,90 €/mes** es la asesoría: nutrición + entrenamiento con
  seguimiento continuo y RENOVACIÓN MENSUAL. No es un programa cerrado de 3 o 6
  meses como los de DQR — aquí la relación es mes a mes mientras el cliente
  siga—, así que la marca vende un solo plan y una sola duración. Sustituye a
  «Génesis.99», que era otra cosa.
- El **plan de gimnasio (60 €/mes)** NO es asesoría: es acceso a la sala. Se
  enseña con el resto de lo que se cobra en el centro (entrenos personales y
  packs), para que la pantalla de Vender no dé a entender que el centro solo
  ofrece una cosa.
- **Negro con detalles dorados**: la identidad del centro. El dorado es el
  acento (lo que se pulsa, lo que se destaca) y el negro la estructura y el
  fondo; el portal del cliente pasa a tema oscuro, que es donde ese par de
  colores se lee como se tiene que leer.
- **Cuestionario y documento PROPIOS** (`anamnesis_variant`/`doc_variant` =
  'professional'): mismas preguntas de las que salen los números —quitarlas no
  simplifica, rompe— pero con su propia estructura, su redacción y su diseño.
  Compartir la variante 'simple' con cualquier otra marca futura habría hecho
  que tocar una cambiara la otra.
"""
from alembic import op
import sqlalchemy as sa

revision = "0051"
down_revision = "0050"
branch_labels = None
depends_on = None

# La asesoría del centro: una cuota, un mes. 129,90 € = 12990 céntimos.
_PRECIOS_PF = {"full": {"1m": 12990}}

_LABELS_PF = {"full": "Pack Premium", "train": "Entreno personal",
              "nutri": "Plan nutricional"}
_TAGLINES_PF = {"full": "nutrición y entrenamiento con seguimiento",
                "train": "entrenamiento personal",
                "nutri": "pauta de nutrición"}

# Lo que se cobra EN EL CENTRO (la web no lo cobra, solo lo enseña).
_EXTRA_PF = [
    {"title": "Plan de gimnasio · acceso 7 días", "price": "60 €/mes"},
    {"title": "Entreno personal · socios", "price": "50 €/h"},
    {"title": "Entreno personal · no socios", "price": "60 €/h"},
    {"title": "Pack 10 sesiones · socios", "price": "350 €"},
    {"title": "Pack 10 sesiones · no socios", "price": "450 €"},
]


def upgrade() -> None:
    import json

    op.get_bind().execute(
        sa.text(
            "UPDATE brand_config SET"
            " tagline = 'Centre Salut & Fitness · Girona',"
            # Dorado de acento sobre negro. El #F2C230 anterior era un amarillo
            # de señal: sobre fondo oscuro vibra y no se lee como una marca.
            " color_primary = '#C9A227',"
            " color_secondary = '#161616',"
            " color_bg = '#0B0B0B',"
            " portal_theme = 'dark',"
            " service_labels = CAST(:labels AS jsonb),"
            " service_taglines = CAST(:taglines AS jsonb),"
            " prices = CAST(:precios AS jsonb),"
            " extra_services = CAST(:extra AS jsonb),"
            " anamnesis_variant = 'professional',"
            " doc_variant = 'professional'"
            " WHERE slug = 'professional-fitness'"),
        {"labels": json.dumps(_LABELS_PF, ensure_ascii=False),
         "taglines": json.dumps(_TAGLINES_PF, ensure_ascii=False),
         "precios": json.dumps(_PRECIOS_PF),
         "extra": json.dumps(_EXTRA_PF, ensure_ascii=False)},
    )


def downgrade() -> None:
    # Vuelve a lo que había: Génesis.99 y las variantes compartidas.
    import json

    op.get_bind().execute(
        sa.text(
            "UPDATE brand_config SET"
            " color_primary = '#F2C230', color_secondary = '#2E2E2E',"
            " color_bg = '#1F1F1F', portal_theme = 'light',"
            " service_labels = CAST(:labels AS jsonb),"
            " prices = CAST(:precios AS jsonb),"
            " anamnesis_variant = 'simple', doc_variant = 'simple'"
            " WHERE slug = 'professional-fitness'"),
        {"labels": json.dumps({"full": "Génesis.99", "train": "Entreno personal",
                               "nutri": "Plan nutricional"}, ensure_ascii=False),
         "precios": json.dumps({"full": {"1m": 9900}})},
    )
