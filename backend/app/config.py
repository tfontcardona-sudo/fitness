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
    # Modelo del FEEDBACK quincenal (solo redacta; no calcula). Vacío = usa el
    # pesado. Ponlo a un modelo intermedio para ahorrar sin apenas riesgo.
    model_feedback: str = ""

    # --- Base de datos ---
    database_url: str = "postgresql+psycopg://fitness:fitness@db:5432/fitness"

    # --- Seguridad ---
    jwt_secret: str = "dev-insecure-jwt-secret"
    portal_token_secret: str = "dev-insecure-portal-secret"
    jwt_expire_minutes: int = 60 * 72  # el coach vive con la pestaña abierta días: 12 h lo expulsaba al login en mitad de una acción cada mañana (single-tenant, riesgo asumible)

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
    # IDs de precio por plan × duración. OPCIONALES: si están vacíos, el sistema
    # resuelve el precio en Stripe por lookup_key ("dqr_nutri_1m"…) — los crea
    # scripts/setup_stripe_prices.py, así no hay que copiar IDs a mano.
    stripe_price_nutri_1m: str = ""
    stripe_price_nutri_3m: str = ""
    stripe_price_nutri_6m: str = ""
    stripe_price_train_1m: str = ""
    stripe_price_train_3m: str = ""
    stripe_price_train_6m: str = ""
    stripe_price_full_1m: str = ""
    stripe_price_full_3m: str = ""
    stripe_price_full_6m: str = ""
    # Nombres antiguos (start/pro): se aceptan para no romper un .env previo.
    stripe_price_start_1m: str = ""
    stripe_price_start_3m: str = ""
    stripe_price_start_6m: str = ""
    stripe_price_pro_1m: str = ""
    stripe_price_pro_3m: str = ""
    stripe_price_pro_6m: str = ""
    stripe_mode: str = "payment"  # payment | subscription

    @property
    def stripe_enabled(self) -> bool:
        return bool(self.stripe_secret_key)

    def stripe_price_for(self, tier: str, period: str) -> str:
        """ID de precio del .env (nombres nuevos). La resolución completa —con
        lookup_key en Stripe y nombres antiguos como último recurso— vive en
        stripe_service._resolve_price_id (los antiguos NO deben pisar los
        precios nuevos creados por lookup_key)."""
        return getattr(self, f"stripe_price_{tier}_{period}", "")

    def stripe_price_legacy(self, tier: str, period: str) -> str:
        """Nombre antiguo equivalente (START→nutri, PRO→full), último recurso."""
        legacy = {"nutri": "start", "full": "pro"}.get(tier)
        return getattr(self, f"stripe_price_{legacy}_{period}", "") if legacy else ""

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
    # Email de la cuenta de Google de la asesoría (p. ej. asesoriasdqr@gmail.com):
    # al pulsar "Conectar", Google abre YA con esta cuenta en vez de la que el
    # navegador tenga por defecto (evita conectar sin querer la cuenta personal).
    google_login_hint: str = ""

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def google_redirect_uri(self) -> str:
        """URI de redirección OAuth (debe coincidir EXACTA con la de Google Cloud)."""
        return f"{self.public_base_url.rstrip('/')}/api/google/oauth/callback"

    # --- Comportamiento ---
    tz: str = "Europe/Madrid"
    # Apaga TODOS los jobs (recordatorios, cierres, resúmenes): tests/CI.
    scheduler_enabled: bool = True
    # Tope diario de ALTAS por el formulario público. El límite por IP no frena
    # a quien rota IPs y direcciones, y cada alta manda un email desde el buzón
    # del coach: con la cuota diaria agotada no salen ni los accesos al portal
    # ni los planes de los clientes reales. Se puede subir para una campaña.
    public_signups_per_day: int = 25
    # Caché del contenido educativo por split (sidecar): el mismo split reutiliza
    # las píldoras/técnica/FAQ ya generadas → 0 créditos. false en tests.
    education_cache_enabled: bool = True
    # Lector universal (§5 doble pase, por fin cableado): tras extraer la
    # anamnesis de un documento, un SEGUNDO pase relee el mismo documento (ya
    # cacheado → ~10 % del coste) y comprueba los campos críticos (sexo, fecha
    # de nacimiento, altura, peso, objetivo, alergias, medicación, patologías,
    # lesiones). Las discrepancias NO se resuelven solas: se enseñan al coach.
    extraction_double_pass: bool = True

    @property
    def public_base_url(self) -> str:
        """URL pública del sistema (portal, links de email)."""
        if self.domain:
            return f"https://{self.domain}"
        return self.base_url

    @property
    def is_production(self) -> bool:
        """Producción = hay un dominio público configurado. En dev/tests el
        dominio está vacío, así que los guardianes de secretos solo AVISAN."""
        return bool(self.domain)

    # Valores por defecto que viven en el repositorio (público): usarlos en
    # producción permitiría FALSIFICAR sesiones y tokens. Nunca deben llegar al
    # servidor sin sustituir.
    # Valores PÚBLICOS: los del código Y los marcadores de .env.example. Copiar
    # el ejemplo tal cual daba secretos conocidos por cualquiera que vea el repo
    # y, por ser largos, pasaban el control de longitud sin un solo aviso.
    _INSECURE_DEFAULTS = {
        "jwt_secret": (
            "dev-insecure-jwt-secret",
            "cambia-esto-por-una-cadena-larga-aleatoria-de-32-o-mas",
        ),
        "portal_token_secret": (
            "dev-insecure-portal-secret",
            "cambia-esto-por-otra-cadena-larga-aleatoria-distinta",
        ),
    }

    def insecure_secrets(self) -> list[str]:
        """Lista de secretos de firma inseguros (por defecto o demasiado cortos).
        Un secreto corto o conocido se puede adivinar/forjar: quien lo tenga
        fabrica tokens de coach (acceso total) o de cualquier cliente."""
        return self._secret_problems(blocking_only=False)

    def blocking_secret_problems(self) -> list[str]:
        """Solo los problemas CATASTRÓFICOS que justifican no arrancar: el
        secreto es EXACTAMENTE el de ejemplo del repo (público → cualquiera
        forja tokens). Un secreto corto pero propio es débil, no catastrófico:
        se avisa, pero NO se tira abajo una producción que ya funciona."""
        return self._secret_problems(blocking_only=True)

    def _secret_problems(self, *, blocking_only: bool) -> list[str]:
        problemas: list[str] = []
        for campo, publicos in self._INSECURE_DEFAULTS.items():
            valor = getattr(self, campo, "") or ""
            # Cualquier variante del marcador cuenta: "cambia-esto…" en
            # cualquier forma es un secreto que está publicado en el repo.
            es_publico = valor in publicos or valor.lower().startswith("cambia-esto")
            if es_publico:
                problemas.append(f"{campo.upper()} sigue con el valor de ejemplo del repo")
            elif not blocking_only and len(valor) < 32:
                problemas.append(f"{campo.upper()} es demasiado corto (<32 caracteres)")
        return problemas


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
