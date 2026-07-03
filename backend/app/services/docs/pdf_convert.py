"""Conversión determinista de .docx → PDF con LibreOffice headless.

Los planes se generan con python-docx y se entregan como PDF convertido EN EL
SERVIDOR con LibreOffice, no como .docx. Así el documento que recibe el coach/
cliente es exactamente el que se verifica (mismo motor de render), sin depender
de la versión de Word de cada cual ni de sus sustituciones de fuente/layout.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile


def _soffice_bin() -> str:
    for name in ("soffice", "libreoffice"):
        path = shutil.which(name)
        if path:
            return path
    return "/usr/bin/soffice"


def docx_bytes_to_pdf(docx_bytes: bytes, timeout: int = 120) -> bytes:
    """Convierte un .docx (bytes) a PDF (bytes). Lanza RuntimeError si falla."""
    with tempfile.TemporaryDirectory() as tmp:
        docx_path = os.path.join(tmp, "plan.docx")
        with open(docx_path, "wb") as fh:
            fh.write(docx_bytes)
        # Perfil de usuario propio por conversión → evita bloqueos con concurrencia.
        profile = "file://" + os.path.join(tmp, "lo_profile")
        env = dict(os.environ, HOME=tmp)
        try:
            proc = subprocess.run(
                [_soffice_bin(), "--headless", "--norestore", "--nologo", "--nofirststartwizard",
                 f"-env:UserInstallation={profile}", "--convert-to", "pdf:writer_pdf_Export",
                 "--outdir", tmp, docx_path],
                check=True, capture_output=True, timeout=timeout, env=env,
            )
        except subprocess.CalledProcessError as exc:  # pragma: no cover
            raise RuntimeError(
                f"LibreOffice falló al convertir a PDF: {exc.stderr.decode('utf-8', 'ignore')[:400]}"
            ) from exc
        except FileNotFoundError as exc:  # soffice no instalado
            raise RuntimeError("LibreOffice (soffice) no está disponible en el servidor") from exc
        pdf_path = os.path.join(tmp, "plan.pdf")
        if not os.path.exists(pdf_path):
            raise RuntimeError(
                f"LibreOffice no produjo PDF. stdout={proc.stdout.decode('utf-8', 'ignore')[:300]}"
            )
        with open(pdf_path, "rb") as fh:
            return fh.read()
