"""Genera un par de claves VAPID para Web Push (ejecutar UNA vez).

Las claves identifican al servidor ante los servicios de push (FCM, Mozilla,
Apple). Se generan una vez, se pegan en el `.env` y NO se cambian: si cambian,
todas las suscripciones existentes dejan de ser válidas y los clientes tendrían
que volver a activar las notificaciones.

Uso (desde la raíz del proyecto):
    docker compose exec api python -m scripts.generate_vapid_keys
    # o en local:  python backend/scripts/generate_vapid_keys.py

Copia las dos líneas que imprime al `.env` y reinicia el contenedor `api`.
"""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate() -> tuple[str, str]:
    """Devuelve (private_key_b64url, public_key_b64url) en el formato crudo
    que esperan pywebpush (privada: 32 bytes) y PushManager.subscribe
    (pública: punto EC sin comprimir de 65 bytes, prefijo 0x04)."""
    key = ec.generate_private_key(ec.SECP256R1())
    private_raw = key.private_numbers().private_value.to_bytes(32, "big")
    public_raw = key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return _b64url(private_raw), _b64url(public_raw)


if __name__ == "__main__":
    priv, pub = generate()
    print("# Pega esto en tu .env (y guarda una copia segura):")
    print(f"VAPID_PRIVATE_KEY={priv}")
    print(f"VAPID_PUBLIC_KEY={pub}")
    print("VAPID_SUBJECT=mailto:tu-email@ejemplo.com")
