"""Dice, en una línea, con qué usuario y contraseña se entra al panel.

Existe porque el lanzador de la demo solo sabía decir "usuario y contraseña del
.env", y quien no abría el fichero se quedaba adivinando delante de un
"credenciales incorrectas" sin ninguna pista. Aquí se comprueba lo mismo que
comprueba el login (`verify_password` contra el hash guardado), pero desde
dentro del contenedor: sin pasar por HTTP no gasta ninguno de los 5 intentos
por minuto del endpoint, y no hay que meter la contraseña en una línea de
comandos del host (comillas, acentos y `$` la destrozaban).

Uso:  docker compose ... exec -T api python scripts/check_login.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402
from app.security import verify_password  # noqa: E402


def main() -> int:
    usuario = (settings.admin_1_user or "").strip()
    clave = settings.admin_1_pass or ""

    if not usuario or not clave:
        print("X falta ADMIN_1_USER o ADMIN_1_PASS en el .env")
        return 1

    with SessionLocal() as db:
        fila = db.scalar(select(User).where(User.username == usuario))

    if fila is None:
        # El arranque siembra los admins del .env, así que llegar aquí significa
        # que los seeds no corrieron (o el .env cambió sin reiniciar la API).
        print(f"X el usuario '{usuario}' no está en la base de datos: reinicia la API")
        return 1
    if not verify_password(clave, fila.password_hash):
        print(f"X la contraseña del .env no es la de '{usuario}': reinicia la API")
        return 1

    print(f"{usuario} / {clave}   (comprobado, entra)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
