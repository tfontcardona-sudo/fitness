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
