"""Clave de rate-limit por IP real del cliente.

Detrás de Caddy, `request.client.host` es siempre la IP interna del contenedor
proxy (idéntica para todos) → los límites serían un cubo global compartido. Caddy
inyecta `X-Real-IP` con la IP real del cliente ({remote_host}, no falseable);
aquí la usamos como clave, con respaldo a la IP directa en pruebas locales.
"""
from __future__ import annotations

from slowapi.util import get_remote_address


def client_key(request) -> str:
    return request.headers.get("x-real-ip") or get_remote_address(request)
