"""Prueba el envío de email (SMTP) y muestra el resultado real.

Comprueba la configuración SMTP del `.env` y, si le pasas una dirección, envía
un correo de prueba y dice si salió o por qué falló (contraseña de aplicación
de Gmail rechazada, conexión, SMTP sin configurar, etc.).

Uso (desde la raíz del proyecto, en el servidor):
    docker compose exec api python -m scripts.test_email tu-correo@ejemplo.com
    # solo ver la configuración, sin enviar:
    docker compose exec api python -m scripts.test_email
"""

from __future__ import annotations

import sys

from app.db import SessionLocal
from app.services import email_templates as tpl
from app.services.email_service import (
    EmailService,
    brand_from_config,
    email_config_status,
)


def main() -> int:
    cfg = email_config_status()
    print("=== Configuración SMTP ===")
    for k, v in cfg.items():
        print(f"  {k}: {v}")

    if len(sys.argv) < 2:
        print("\nNo se ha indicado destinatario: solo se ha mostrado la configuración.")
        print("Para enviar una prueba:  python -m scripts.test_email tu-correo@ejemplo.com")
        return 0 if cfg["ready"] else 1

    to = sys.argv[1]
    db = SessionLocal()
    try:
        brand = brand_from_config(db)
        subject, html = tpl.test_email(brand)
        svc = EmailService(db)
        status = svc.send(to=to, subject=subject, html=html, kind="test")
        db.commit()
    finally:
        db.close()

    print(f"\n=== Envío de prueba a {to} ===")
    print(f"  status: {status}")
    if status == "sent":
        print("  ✅ Correo enviado. Revisa la bandeja (y la carpeta de spam).")
        return 0
    print(f"  ❌ No se envió. Motivo: {svc.last_error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
