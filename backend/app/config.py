"""Configuración central de la aplicación.

Todas las variables se leen del entorno (.env). Una sola fuente de verdad:
cualquier servicio (API, scheduler, generación de documentos, email) importa
`settings` desde aquí.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- IA ---
    anthropic_api_key: str = ""
    model_heavy: str = "claude-opus-4-8"
    model_light: str = "claude-haiku-4-5-20251001"

    # --- Base de datos ---
    database_url: str = "postgresql+psycopg://fitness:fitness@db:5432/fitness"

    # --- Seguridad ---
    jwt_secret: str = "dev-insecure-jwt-secret"
    portal_token_secret: str = "dev-insecure-portal-secret"
    jwt_expire_minutes: int = 60 * 12  # jornada de trabajo del coach

    # --- Admins (seed inicial single-tenant) ---
    admin_1_user: str = ""
    admin_1_pass: str = ""
    admin_2_user: str = ""
    admin_2_pass: str = ""

    # --- URLs y almacenamiento ---
    domain: str = ""
    base_url: str = "http://localhost"
    storage_path: str = "./storage"

    # --- Email ---
    # Remitente por defecto: los correos del cliente (acceso al portal, plan,
    # feedback…) salen a nombre de David. Para enviar DE VERDAD hay que rellenar
    # smtp_user + smtp_pass (contraseña de aplicación de Gmail) y EMAILS_ENABLED=true.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = "David Quiceno <david.dqr57@gmail.com>"
    emails_enabled: bool = True

    # --- Web Push (VAPID) ---
    # Generar UNA vez con scripts/generate_vapid_keys.py y no cambiar (si
    # cambian, todas las suscripciones existentes quedan inválidas).
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = ""  # mailto:... (contacto para los servicios de push)
    push_enabled: bool = True

    # --- Pagos (Stripe) ---
    # secret_key: clave secreta (sk_live_… o sk_test_…) para crear las sesiones
    # de pago y leer los webhooks. webhook_secret (whsec_…): valida que el aviso
    # de pago viene DE VERDAD de Stripe. price_{plan}_{duración}: id del precio
    # (price_…) de cada combinación plan × duración creada en el panel de Stripe
    # (1m mensual · 3m trimestral · 6m semestral). mode: "payment" (pago único)
    # o "subscription" (cuota recurrente) según cómo hayas creado los precios.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_start_1m: str = ""
    stripe_price_start_3m: str = ""
    stripe_price_start_6m: str = ""
    stripe_price_full_1m: str = ""
    stripe_price_full_3m: str = ""
    stripe_price_full_6m: str = ""
    stripe_price_pro_1m: str = ""
    stripe_price_pro_3m: str = ""
    stripe_price_pro_6m: str = ""
    stripe_mode: str = "payment"  # payment | subscription

    @property
    def stripe_enabled(self) -> bool:
        return bool(self.stripe_secret_key)

    def stripe_price_for(self, tier: str, period: str) -> str:
        return getattr(self, f"stripe_price_{tier}_{period}", "")

    # --- Google Calendar / Meet (videollamadas Pro) ---
    # client_id/secret: credenciales del cliente OAuth creado en Google Cloud
    # (APIs y servicios → Credenciales → ID de cliente de OAuth, tipo "Aplicación
    # web"). La URI de redirección autorizada debe ser
    # {public_base_url}/api/google/oauth/callback. calendar_id: normalmente
    # "primary" (el calendario principal del coach). El coach conecta su cuenta
    # UNA vez desde Ajustes → se guarda el refresh_token y el sistema crea los
    # eventos con enlace de Meet e invita al cliente. Sin estas claves, la
    # integración queda desactivada y sigue el flujo manual (enlace de reservas).
    google_client_id: str = ""
    google_client_secret: str = ""
    google_calendar_id: str = "primary"

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def google_redirect_uri(self) -> str:
        """URI de redirección OAuth (debe coincidir EXACTA con la de Google Cloud)."""
        return f"{self.public_base_url.rstrip('/')}/api/google/oauth/callback"

    # --- Comportamiento ---
    auto_pilot_default: bool = False
    tz: str = "Europe/Madrid"

    @property
    def public_base_url(self) -> str:
        """URL pública del sistema (portal, links de email)."""
        if self.domain:
            return f"https://{self.domain}"
        return self.base_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
