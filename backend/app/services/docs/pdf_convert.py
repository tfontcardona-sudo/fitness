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
    return office_bytes_to_pdf(docx_bytes, "docx", timeout=timeout)


# Extensiones que el LibreOffice de la imagen (writer + core) sabe abrir. Las
# hojas de cálculo NO están aquí a propósito: Calc no viene instalado y el
# lector universal las lee con openpyxl. Si algún día se añade Calc/Impress a
# la imagen, basta con ampliar esta tupla.
OFFICE_CONVERTIBLE = ("docx", "doc", "odt", "rtf", "dot", "dotx", "wps", "txt")


def office_bytes_to_pdf(raw: bytes, ext: str, timeout: int = 120) -> bytes:
    """Convierte un documento de oficina (bytes + extensión) a PDF con el mismo
    LibreOffice, la misma caché y el mismo freno de concurrencia que el plan.

    Es la puerta del LECTOR UNIVERSAL: un Word ajeno (la anamnesis de otro
    profesional, una dieta hecha en Word) se convierte a PDF y la IA lo lee
    NATIVAMENTE —tablas, columnas y maquetación incluidas— en vez de recibir
    un volcado de texto plano que pierde la estructura.
    """
    ext = (ext or "docx").lower().lstrip(".")
    if ext not in OFFICE_CONVERTIBLE:
        raise RuntimeError(f"LibreOffice no puede convertir .{ext} en este servidor")
    clave = _clave_de_contenido(raw) + f":{ext}"
    with _cache_lock:
        cacheado = _cache.get(clave)
    if cacheado is not None:
        return cacheado
    if not _hueco.acquire(timeout=_ESPERA_MAX_S):
        raise ConversionOcupada(
            "El servidor está preparando otros documentos. Inténtalo en un minuto.")
    try:
        # .docx sin `ext`: compatibilidad con quien sustituye `_convierte`
        # (tests) con la firma de siempre (bytes, timeout).
        pdf = _convierte(raw, timeout) if ext == "docx" else _convierte(raw, timeout, ext=ext)
    finally:
        _hueco.release()
    with _cache_lock:
        _cache[clave] = pdf
        _cache_orden.append(clave)
        while len(_cache_orden) > _CACHE_MAX:
            _cache.pop(_cache_orden.pop(0), None)
    return pdf


def _clave_de_contenido(docx_bytes: bytes) -> str:
    """Huella del CONTENIDO del .docx, ignorando las marcas de tiempo del zip.

    python-docx sella cada entrada del zip con la hora del guardado, así que el
    MISMO plan generado dos veces en segundos distintos daba bytes distintos:
    la caché no acertaba NUNCA y cada descarga arrancaba un LibreOffice de
    ~300 MB (con solo dos huecos simultáneos, el portal contestaba "el servidor
    está preparando otros documentos" sin necesidad). Medido: dos guardados con
    1,2 s de diferencia ya no comparten sha1.
    """
    try:
        import io
        import zipfile

        h = hashlib.sha1()
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
            for nombre in sorted(z.namelist()):
                h.update(nombre.encode("utf-8"))
                h.update(z.read(nombre))
        return h.hexdigest()
    except Exception:  # noqa: BLE001 — si no es un zip legible, huella cruda
        return hashlib.sha1(docx_bytes).hexdigest()


def _convierte(docx_bytes: bytes, timeout: int, ext: str = "docx") -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        docx_path = os.path.join(tmp, f"plan.{ext}")
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
