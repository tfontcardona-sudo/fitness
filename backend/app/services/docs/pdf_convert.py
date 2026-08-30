"""Conversión determinista de .docx → PDF con LibreOffice headless.

Los planes se generan con python-docx y se entregan como PDF convertido EN EL
SERVIDOR con LibreOffice, no como .docx. Así el documento que recibe el coach/
cliente es exactamente el que se verifica (mismo motor de render), sin depender
de la versión de Word de cada cual ni de sus sustituciones de fuente/layout.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
import threading


def _soffice_bin() -> str:
    for name in ("soffice", "libreoffice"):
        path = shutil.which(name)
        if path:
            return path
    return "/usr/bin/soffice"


# CADA conversión arranca un LibreOffice completo (~200-400 MB) con perfil
# propio. Los endpoints del portal permiten 10-30 descargas/minuto POR IP y
# FastAPI ejecuta los endpoints síncronos en un threadpool de 40 hilos: un solo
# cliente pulsando "ver mi plan" podía tener decenas de procesos vivos a la vez
# contra un VPS de un worker que comparte máquina con Postgres. Se queda sin
# RAM y cae la API entera: el coach pierde el panel y TODOS los clientes su
# portal. Dos a la vez es de sobra para un solo coach.
_MAX_CONVERSIONES = 2
_ESPERA_MAX_S = 25
_hueco = threading.BoundedSemaphore(_MAX_CONVERSIONES)

# Caché en memoria por CONTENIDO del .docx: el mismo plan se descarga muchas
# veces (el cliente lo reabre desde el portal) y la conversión es determinista.
_CACHE_MAX = 8
_cache: "dict[str, bytes]" = {}
_cache_orden: list[str] = []
_cache_lock = threading.Lock()


class ConversionOcupada(RuntimeError):
    """No hay hueco para convertir ahora mismo (se traduce a un 503 amable)."""


def docx_bytes_to_pdf(docx_bytes: bytes, timeout: int = 120) -> bytes:
    """Convierte un .docx (bytes) a PDF (bytes). Lanza RuntimeError si falla.

    Con caché por contenido y un tope de conversiones simultáneas.
    """
    clave = hashlib.sha1(docx_bytes).hexdigest()
    with _cache_lock:
        cacheado = _cache.get(clave)
    if cacheado is not None:
        return cacheado
    if not _hueco.acquire(timeout=_ESPERA_MAX_S):
        raise ConversionOcupada(
            "El servidor está preparando otros documentos. Inténtalo en un minuto.")
    try:
        pdf = _convierte(docx_bytes, timeout)
    finally:
        _hueco.release()
    with _cache_lock:
        _cache[clave] = pdf
        _cache_orden.append(clave)
        while len(_cache_orden) > _CACHE_MAX:
            _cache.pop(_cache_orden.pop(0), None)
    return pdf


def _convierte(docx_bytes: bytes, timeout: int) -> bytes:
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
