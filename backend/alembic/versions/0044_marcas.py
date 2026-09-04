"""Perfiles de MARCA: el switch entre DQR y otra marca (p. ej. Professional
Fitness) que convierte el mismo sistema en otro programa.

Qué cambia y qué no
-------------------
La MAQUINARIA es la misma para las dos marcas (motor de cálculo, guardarraíles,
ciclo quincenal, portal, IA). Lo que cambia por marca es lo que se VE y lo que
se VENDE: nombre, colores, logo, nombres de los servicios, tarifas, precios de
Stripe, la anamnesis y el pie del documento del cliente.

Cómo se hace sin romper lo que ya está vendido
---------------------------------------------
1) `brand_config` deja de ser UNA fila para ser un perfil por marca, con
   `slug` (identificador estable) y `activa` (la del escaparate: panel, landing,
   /planes y las altas nuevas).
2) Cada cliente queda SELLADO con su marca (`clients.brand_id`). Un cliente que
   entró por DQR sigue viendo DQR —su portal, sus documentos, sus precios de
   renovación— aunque el coach cambie el switch. Sin este sello, pulsar el
   switch le cambiaría la marca a gente que ya está pagando.
3) Los precios de Stripe se separan por `stripe_prefix`: `dqr_full_1m` frente a
   `pf_full_1m`. Cada marca crea los suyos la primera vez y NUNCA se pisan, así
   que las suscripciones en marcha no se tocan.

Los valores de hoy se quedan como el perfil DQR: hasta que no se cree y active
otra marca, el sistema se comporta exactamente igual que antes.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None


# Tarifas de DQR tal y como estaban clavadas en `stripe_service.CANONICAL_AMOUNTS`
# y en las constantes de la oferta. Al pasarlas a datos, cada marca tiene las
# suyas y el código deja de tener importes dentro.
_PRECIOS_DQR = {
    "train": {"1m": 6900, "3m": 17700, "6m": 32400},
    "nutri": {"1m": 7900, "3m": 20100, "6m": 37200},
    "full": {"1m": 12900, "3m": 33000, "6m": 60000},
    "oferta": {"monthly_cents": 12000, "first_month_cents": 100, "charges": 3},
    "oferta2": {"monthly_cents": 12050, "charges": 2},
}
_LABELS_DQR = {"train": "DQR Train", "nutri": "DQR Nutri", "full": "DQR Full"}
_TAGLINES_DQR = {
    "train": "solo entrenamiento",
    "nutri": "solo nutrición",
    "full": "nutrición + entrenamiento",
}

# La segunda marca nace APAGADA y con la misma escala de tarifas: el coach le
# pone su logo, sus colores y sus importes desde Recursos antes de activarla.
_LABELS_PF = {"train": "Professional Train", "nutri": "Professional Nutri",
              "full": "Professional Full"}


def _cols(insp, table: str) -> set[str]:
    return {c["name"] for c in insp.get_columns(table)}


def _indices(insp, table: str) -> set[str]:
    return {i["name"] for i in insp.get_indexes(table)}


def upgrade() -> None:
    # En una instalación NUEVA la 0001 ya crea estas columnas desde los modelos:
    # añadirlas a ciegas rompería `alembic upgrade head` y el arranque del
    # contenedor (por eso hay un test que lo vigila).
    insp = sa.inspect(op.get_bind())
    cols = _cols(insp, "brand_config")

    # --- el perfil de marca --------------------------------------------------
    nuevas = [
        ("slug", sa.Column("slug", sa.String(40), nullable=True)),
        ("activa", sa.Column("activa", sa.Boolean(), nullable=False,
                             server_default=sa.false())),
        ("service_labels", sa.Column("service_labels", postgresql.JSONB(), nullable=True)),
        ("service_taglines", sa.Column("service_taglines", postgresql.JSONB(), nullable=True)),
        ("prices", sa.Column("prices", postgresql.JSONB(), nullable=True)),
        ("stripe_prefix", sa.Column("stripe_prefix", sa.String(16), nullable=True)),
        ("page_title", sa.Column("page_title", sa.String(120), nullable=True)),
        ("app_name", sa.Column("app_name", sa.String(60), nullable=True)),
        ("app_short_name", sa.Column("app_short_name", sa.String(20), nullable=True)),
        ("anamnesis_variant", sa.Column("anamnesis_variant", sa.String(20), nullable=True)),
    ]
    for nombre, columna in nuevas:
        if nombre not in cols:
            op.add_column("brand_config", columna)

    # La fila que ya existe (o una nueva si la base está vacía) es DQR y queda
    # ACTIVA: sin esto, el sistema arrancaría sin escaparate.
    conn = op.get_bind()
    fila = conn.execute(sa.text("SELECT id FROM brand_config ORDER BY id LIMIT 1")).first()
    if fila is None:
        conn.execute(sa.text(
            "INSERT INTO brand_config (name, color_primary, color_secondary, color_bg,"
            " font_family, docs_theme, portal_theme, activa, slug)"
            " VALUES ('DQR Assessories', '#E8833A', '#2E5E8C', '#0B111C', 'Inter',"
            " 'light', 'light', true, 'dqr')"))
        fila = conn.execute(sa.text("SELECT id FROM brand_config ORDER BY id LIMIT 1")).first()
    conn.execute(
        sa.text(
            "UPDATE brand_config SET slug = COALESCE(NULLIF(slug, ''), 'dqr'), activa = true,"
            " service_labels = CAST(:labels AS jsonb),"
            " service_taglines = CAST(:taglines AS jsonb),"
            " prices = CAST(:precios AS jsonb),"
            " stripe_prefix = 'dqr', page_title = 'DQ · Asesorías Fitness',"
            " app_name = 'DQR · Assessories', app_short_name = 'DQR',"
            " anamnesis_variant = 'dq'"
            " WHERE id = :id"),
        {"labels": _json(_LABELS_DQR), "taglines": _json(_TAGLINES_DQR),
         "precios": _json(_PRECIOS_DQR), "id": fila[0]},
    )
    # El resto de perfiles (si alguien creó filas sueltas alguna vez) quedan
    # apagados y con un slug propio para no chocar con el índice único.
    conn.execute(sa.text(
        "UPDATE brand_config SET slug = 'marca-' || id, activa = false"
        " WHERE slug IS NULL"))
    op.alter_column("brand_config", "slug", nullable=False)
    insp = sa.inspect(op.get_bind())
    idx = _indices(insp, "brand_config")
    if "ix_brand_config_slug" not in idx:
        op.create_index("ix_brand_config_slug", "brand_config", ["slug"], unique=True)
    # UNA sola marca activa: lo garantiza la base, no el cuidado de quien programe.
    if "ix_brand_config_activa" not in idx:
        op.create_index("ix_brand_config_activa", "brand_config", ["activa"], unique=True,
                        postgresql_where=sa.text("activa"))

    # --- la SEGUNDA marca, apagada y lista para vestir ----------------------
    conn.execute(
        sa.text(
            "INSERT INTO brand_config (name, color_primary, color_secondary, color_bg,"
            " font_family, docs_theme, portal_theme, activa, slug, tagline,"
            " service_labels, service_taglines, prices, stripe_prefix,"
            " page_title, app_name, app_short_name, anamnesis_variant)"
            " VALUES ('Professional Fitness', '#1F6F8B', '#0F2A38', '#0A1620', 'Inter',"
            " 'light', 'light', false, 'professional-fitness',"
            " 'Entrenamiento y nutrición profesional',"
            " CAST(:labels AS jsonb), CAST(:taglines AS jsonb), CAST(:precios AS jsonb),"
            " 'pf', 'Professional Fitness', 'Professional Fitness', 'Professional', 'pf')"
            " ON CONFLICT DO NOTHING"),
        {"labels": _json(_LABELS_PF), "taglines": _json(_TAGLINES_DQR),
         "precios": _json(_PRECIOS_DQR)},
    )

    # --- el SELLO de marca en cada cliente ----------------------------------
    insp = sa.inspect(op.get_bind())
    if "brand_id" not in _cols(insp, "clients"):
        op.add_column("clients", sa.Column("brand_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_clients_brand", "clients", "brand_config",
                              ["brand_id"], ["id"], ondelete="SET NULL")
    if "ix_clients_brand_id" not in _indices(sa.inspect(op.get_bind()), "clients"):
        op.create_index("ix_clients_brand_id", "clients", ["brand_id"])
    # Todo lo que ya existe es DQR: los clientes de hoy no pueden cambiar de
    # marca porque el coach pulse el switch mañana.
    conn.execute(sa.text("UPDATE clients SET brand_id = :id WHERE brand_id IS NULL"),
                 {"id": fila[0]})


def downgrade() -> None:
    op.drop_index("ix_clients_brand_id", table_name="clients")
    op.drop_constraint("fk_clients_brand", "clients", type_="foreignkey")
    op.drop_column("clients", "brand_id")
    op.execute("DELETE FROM brand_config WHERE slug = 'professional-fitness'")
    op.drop_index("ix_brand_config_activa", table_name="brand_config")
    op.drop_index("ix_brand_config_slug", table_name="brand_config")
    for col in ("anamnesis_variant", "app_short_name", "app_name", "page_title",
                "stripe_prefix", "prices", "service_taglines", "service_labels",
                "activa", "slug"):
        op.drop_column("brand_config", col)


def _json(d: dict) -> str:
    import json

    return json.dumps(d, ensure_ascii=False)
