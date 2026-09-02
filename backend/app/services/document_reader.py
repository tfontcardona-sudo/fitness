"""Lector UNIVERSAL de documentos: cualquier fichero que suba el coach o el
cliente —PDF, Word, foto del móvil, Excel, texto pegado— se convierte aquí en
BLOQUES que la IA puede leer tal cual, sin asumir ninguna estructura.

Por qué existe: la lectura de DQR estaba atada a dos formas conocidas (el PDF
oficial de la anamnesis y el Word que generamos nosotros). Todo lo demás se
rechazaba en la puerta («Solo se admiten archivos PDF») o ni se leía (los
adjuntos). Pero la información llega como llega: la anamnesis de otro
profesional en Word, una analítica fotografiada, una dieta en Excel, notas de
WhatsApp en un .txt. El criterio del dueño es que el sistema lea CUALQUIER
fuente y haga después lo que toque con lo leído.

Cómo se normaliza (todo determinista, sin IA):
- PDF → bloque `document` nativo (la API lee texto Y maquetación, también
  escaneados). Más de 100 páginas → se trocea con pypdf en varios bloques.
- Word/ODT/RTF/DOC → LibreOffice lo convierte a PDF (tablas y columnas
  intactas). Si la conversión falla u ocupa el servidor, reserva: texto de
  python-docx (párrafos y tablas en orden) para .docx.
- Foto (JPG/PNG/WebP/GIF) → bloque `image`, enderezada por EXIF (las fotos de
  móvil vienen giradas), redimensionada al máximo útil y recomprimida a JPEG
  (tope de 5 MB por imagen de la API). Varias fotos = UN documento.
- Excel/CSV → tablas en texto (openpyxl; Calc no está en la imagen).
- Texto/Markdown/JSON → bloque de texto.
- HEIC del iPhone → mensaje claro (Pillow no lo abre sin códec).

Lo que sale es un `Documento`: bloques listos para `AIClient.read_document_json`,
un texto plano cuando existe, y —para guardarlo en la carpeta del cliente— el
contenido canónico (las fotos, por ejemplo, se guardan como UN PDF de varias
páginas, que es lo que vuelve a leer «Leer con IA» sin repetir el proceso).
"""
from __future__ import annotations

import base64
import hashlib
import io
import re
import zipfile
from dataclasses import dataclass, field

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_PDF_PAGES_PER_BLOCK = 100      # tope de la API por bloque `document`
MAX_IMAGES = 20                    # fotos por documento (una hoja por foto)
IMAGE_MAX_SIDE = 1568              # lado mayor recomendado por la API
IMAGE_MAX_BYTES = 4_500_000        # < 5 MB en base64 con margen
MAX_TEXT_CHARS = 400_000
MAX_SHEET_ROWS = 2_000

# Extensiones por familia (para nombrar el fichero guardado y para la UI).
_IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "gif"}
_TEXT_EXTS = {"txt", "md", "csv", "tsv", "json", "log"}
_OFFICE_EXTS = {"docx", "doc", "odt", "rtf", "dot", "dotx"}
_SHEET_EXTS = {"xlsx", "xlsm", "xls", "ods"}

ACCEPTED_HUMAN = "PDF, Word, foto (JPG/PNG), Excel/CSV o texto"


class DocumentoIlegible(ValueError):
    """El fichero no se puede convertir en nada que la IA pueda leer. El
    mensaje está pensado para enseñárselo tal cual al coach o al cliente."""


@dataclass
class Documento:
    origen: str                      # pdf | office | imagen | hoja | texto
    nombre: str
    bloques: list[dict] = field(default_factory=list)
    paginas: int | None = None       # páginas del PDF o nº de fotos
    avisos: list[str] = field(default_factory=list)
    texto: str | None = None         # texto plano cuando lo hay (hojas, texto,
                                     # reserva del Word) — útil para tests/caché
    conversion: str | None = None    # libreoffice | python-docx | openpyxl | pillow
    extension: str = "pdf"           # extensión CANÓNICA con la que se guarda
    contenido: bytes = b""           # bytes canónicos a guardar
    huella: str = ""

    @property
    def descripcion(self) -> str:
        """Frase corta para el prompt y la UI: «PDF de 10 páginas», «3 fotos»…"""
        if self.origen == "pdf":
            n = self.paginas or 0
            base = f"PDF de {n} página{'s' if n != 1 else ''}" if n else "PDF"
            if self.conversion == "libreoffice":
                base += " (convertido desde Word)"
            if self.conversion == "pillow":
                base = f"{n} foto{'s' if n != 1 else ''} (guardadas como PDF)"
            return base
        if self.origen == "imagen":
            n = self.paginas or 1
            return f"{n} foto{'s' if n != 1 else ''}"
        if self.origen == "hoja":
            return "hoja de cálculo"
        if self.origen == "texto":
            return "texto"
        if self.origen == "office":
            return "documento de texto"
        return "documento"

    @property
    def es_pdf(self) -> bool:
        return self.origen == "pdf"


# ------------------------------------------------------------ detección ----

def _ext_de(nombre: str | None) -> str:
    n = (nombre or "").rsplit("/", 1)[-1]
    return n.rsplit(".", 1)[-1].lower() if "." in n else ""


def detectar_tipo(raw: bytes, nombre: str | None = None) -> tuple[str, str]:
    """(familia, extensión) leyendo la MAGIA del fichero, no su nombre: un
    «.pdf» que en realidad es una foto se lee como foto. El nombre solo
    desempata donde la magia no distingue (zip de Office, texto, OLE2)."""
    ext = _ext_de(nombre)
    head = raw[:16]
    if head.startswith(b"%PDF-"):
        return "pdf", "pdf"
    if head.startswith(b"\xff\xd8\xff"):
        return "imagen", "jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "imagen", "png"
    if head[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "imagen", "webp"
    if head.startswith((b"GIF87a", b"GIF89a")):
        return "imagen", "gif"
    if raw[4:12] in (b"ftypheic", b"ftypheix", b"ftyphevc", b"ftypmif1", b"ftypmsf1", b"ftypheif"):
        return "heic", "heic"
    if head.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                nombres = set(z.namelist())
                if "word/document.xml" in nombres:
                    return "office", "docx"
                if "xl/workbook.xml" in nombres:
                    return "hoja", "xlsx"
                if "ppt/presentation.xml" in nombres:
                    return "office", "pptx"
                if "mimetype" in nombres:
                    mt = z.read("mimetype")[:80]
                    if b"opendocument.text" in mt:
                        return "office", "odt"
                    if b"opendocument.spreadsheet" in mt:
                        return "hoja", "ods"
        except zipfile.BadZipFile:
            pass
        return "desconocido", ext or "zip"
    if head.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):   # OLE2: .doc / .xls
        if ext in ("xls",):
            return "hoja", "xls"
        return "office", "doc"
    if head.lstrip().startswith(b"{\\rtf"):
        return "office", "rtf"
    if _parece_texto(raw):
        return "texto", ext if ext in _TEXT_EXTS else "txt"
    return "desconocido", ext or "bin"


def _parece_texto(raw: bytes) -> bool:
    if not raw:
        return False
    muestra = raw[:20_000]
    if b"\x00" in muestra:
        return False
    try:
        muestra.decode("utf-8")
        return True
    except UnicodeDecodeError:
        pass
    # latin-1 siempre decodifica: exigimos que sea mayormente imprimible
    txt = muestra.decode("latin-1")
    imprimibles = sum(ch.isprintable() or ch in "\r\n\t" for ch in txt)
    return imprimibles / max(1, len(txt)) > 0.95


def _decodifica(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


# ------------------------------------------------------------- bloques ----

def _b64(raw: bytes) -> str:
    return base64.standard_b64encode(raw).decode("ascii")


def bloque_pdf(raw: bytes) -> dict:
    return {"type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": _b64(raw)}}


def bloque_imagen(raw_jpeg: bytes, media_type: str = "image/jpeg") -> dict:
    return {"type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": _b64(raw_jpeg)}}


def bloque_texto(texto: str, nombre: str, que: str) -> dict:
    return {"type": "text",
            "text": f"=== Contenido del fichero «{nombre}» ({que}) ===\n{texto}"}


# ----------------------------------------------------------------- PDF ----

def _paginas_pdf(raw: bytes) -> int | None:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:  # noqa: BLE001
                return None
        return len(reader.pages)
    except Exception:  # noqa: BLE001 — un PDF raro se manda entero igual
        return None


def _trocear_pdf(raw: bytes, por_bloque: int) -> list[bytes]:
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(raw))
    trozos: list[bytes] = []
    for inicio in range(0, len(reader.pages), por_bloque):
        w = PdfWriter()
        for p in reader.pages[inicio:inicio + por_bloque]:
            w.add_page(p)
        buf = io.BytesIO()
        w.write(buf)
        trozos.append(buf.getvalue())
    return trozos


def _documento_pdf(raw: bytes, nombre: str, conversion: str | None = None,
                   avisos: list[str] | None = None) -> Documento:
    avisos = list(avisos or [])
    paginas = _paginas_pdf(raw)
    bloques: list[dict]
    if paginas and paginas > MAX_PDF_PAGES_PER_BLOCK:
        try:
            trozos = _trocear_pdf(raw, MAX_PDF_PAGES_PER_BLOCK)
            bloques = [bloque_pdf(t) for t in trozos]
            avisos.append(f"PDF de {paginas} páginas: se lee en {len(trozos)} partes.")
        except Exception:  # noqa: BLE001
            bloques = [bloque_pdf(raw)]
            avisos.append(f"PDF de {paginas} páginas: no se pudo trocear; la IA "
                          f"leerá las primeras {MAX_PDF_PAGES_PER_BLOCK}.")
    else:
        bloques = [bloque_pdf(raw)]
    if paginas is None:
        avisos.append("No se pudo contar las páginas del PDF (¿protegido?); se envía entero.")
    return Documento(origen="pdf", nombre=nombre, bloques=bloques, paginas=paginas,
                     avisos=avisos, conversion=conversion, extension="pdf",
                     contenido=raw, huella=_huella(raw))


# ------------------------------------------------------------- imágenes ----

def _abrir_imagen(raw: bytes):
    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise DocumentoIlegible("La imagen no se puede abrir (¿está dañada?). "
                                "Prueba a guardarla como JPG o PNG.") from exc
    # Las fotos de móvil llegan giradas por EXIF: sin esto la IA lee una hoja
    # tumbada y los perímetros/cifras manuscritas se leen peor.
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:  # noqa: BLE001
        pass
    return img


def _jpeg_normalizado(img) -> bytes:
    """RGB, lado mayor ≤ IMAGE_MAX_SIDE, JPEG ≤ IMAGE_MAX_BYTES."""
    from PIL import Image

    if img.mode not in ("RGB", "L"):
        fondo = Image.new("RGB", img.size, (255, 255, 255))
        try:
            fondo.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA", "P") and "A" in img.getbands() else None)
        except Exception:  # noqa: BLE001
            fondo.paste(img.convert("RGB"))
        img = fondo
    elif img.mode == "L":
        img = img.convert("RGB")
    lado = max(img.size)
    if lado > IMAGE_MAX_SIDE:
        factor = IMAGE_MAX_SIDE / float(lado)
        img = img.resize((max(1, int(img.width * factor)), max(1, int(img.height * factor))))
    calidad = 88
    while True:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=calidad, optimize=True)
        data = buf.getvalue()
        if len(data) <= IMAGE_MAX_BYTES or calidad <= 40:
            return data
        calidad -= 12


def _pdf_desde_jpegs(jpegs: list[bytes]) -> bytes:
    """Varias fotos → UN PDF (una página por foto). Es lo que se GUARDA como
    anamnesis: «Leer con IA» vuelve a leer ese PDF, y el coach lo abre con
    «Ver PDF» como cualquier otro."""
    from PIL import Image

    imgs = [Image.open(io.BytesIO(j)).convert("RGB") for j in jpegs]
    buf = io.BytesIO()
    imgs[0].save(buf, format="PDF", save_all=True, append_images=imgs[1:],
                 resolution=150.0)
    return buf.getvalue()


def _documento_imagenes(partes: list[tuple[bytes, str]], nombre: str) -> Documento:
    if len(partes) > MAX_IMAGES:
        raise DocumentoIlegible(f"Máximo {MAX_IMAGES} fotos por documento "
                                f"(has enviado {len(partes)}).")
    jpegs = [_jpeg_normalizado(_abrir_imagen(raw)) for raw, _n in partes]
    avisos: list[str] = []
    if len(jpegs) == 1:
        return Documento(origen="imagen", nombre=nombre, bloques=[bloque_imagen(jpegs[0])],
                         paginas=1, avisos=avisos, conversion="pillow", extension="jpg",
                         contenido=jpegs[0], huella=_huella(jpegs[0]))
    # Varias fotos: la IA recibe las imágenes (mejor resolución que un PDF
    # rasterizado) y el fichero guardado es un PDF de N páginas.
    pdf = _pdf_desde_jpegs(jpegs)
    return Documento(origen="imagen", nombre=nombre, bloques=[bloque_imagen(j) for j in jpegs],
                     paginas=len(jpegs), avisos=avisos, conversion="pillow", extension="pdf",
                     contenido=pdf, huella=_huella(pdf))


# --------------------------------------------------------------- office ----

def _texto_docx(raw: bytes) -> str:
    """Reserva sin LibreOffice: párrafos y tablas del .docx EN ORDEN (una tabla
    se vuelca fila a fila con « | »). Pierde maquetación, no información."""
    from docx import Document
    from docx.oxml.ns import qn

    doc = Document(io.BytesIO(raw))
    lineas: list[str] = []
    cuerpo = doc.element.body
    for child in cuerpo.iterchildren():
        if child.tag == qn("w:p"):
            t = "".join(n.text or "" for n in child.iter(qn("w:t")))
            if t.strip():
                lineas.append(t.strip())
        elif child.tag == qn("w:tbl"):
            for fila in child.iter(qn("w:tr")):
                celdas = []
                for celda in fila.iter(qn("w:tc")):
                    celdas.append(" ".join(
                        (n.text or "") for n in celda.iter(qn("w:t"))).strip())
                if any(celdas):
                    lineas.append(" | ".join(celdas))
            lineas.append("")
    return "\n".join(lineas).strip()


def _documento_office(raw: bytes, ext: str, nombre: str) -> Documento:
    avisos: list[str] = []
    try:
        from app.services.docs.pdf_convert import office_bytes_to_pdf

        pdf = office_bytes_to_pdf(raw, ext)
        d = _documento_pdf(pdf, nombre, conversion="libreoffice", avisos=avisos)
        return d
    except Exception as exc:  # noqa: BLE001 — LibreOffice ocupado/ausente/fallo
        motivo = str(exc)[:160]
    if ext == "docx":
        try:
            texto = _texto_docx(raw)
        except Exception as exc:  # noqa: BLE001
            raise DocumentoIlegible(
                "El Word no se pudo leer. Guárdalo como PDF y vuelve a subirlo."
            ) from exc
        if not texto.strip():
            raise DocumentoIlegible("El Word no contiene texto legible (¿solo imágenes?). "
                                    "Guárdalo como PDF y vuelve a subirlo.")
        avisos.append("No se pudo convertir el Word a PDF (" + motivo + "); "
                      "se lee su texto (tablas incluidas) sin maquetación.")
        texto = texto[:MAX_TEXT_CHARS]
        return Documento(origen="office", nombre=nombre,
                         bloques=[bloque_texto(texto, nombre, "documento Word")],
                         avisos=avisos, texto=texto, conversion="python-docx",
                         extension="docx", contenido=raw, huella=_huella(raw))
    raise DocumentoIlegible(
        f"No se pudo convertir el .{ext} ({motivo}). Guárdalo como PDF o .docx y vuelve a subirlo.")


# --------------------------------------------------------------- hojas ----

def _texto_xlsx(raw: bytes) -> str:
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    partes: list[str] = []
    for ws in wb.worksheets:
        filas: list[str] = []
        for i, fila in enumerate(ws.iter_rows(values_only=True)):
            if i >= MAX_SHEET_ROWS:
                filas.append(f"… (hoja truncada a {MAX_SHEET_ROWS} filas)")
                break
            celdas = ["" if v is None else str(v).strip() for v in fila]
            if any(celdas):
                filas.append("\t".join(celdas).rstrip("\t"))
        if filas:
            partes.append(f"--- Hoja «{ws.title}» ---\n" + "\n".join(filas))
    return "\n\n".join(partes).strip()


def _documento_hoja(raw: bytes, ext: str, nombre: str) -> Documento:
    if ext not in ("xlsx", "xlsm"):
        raise DocumentoIlegible(
            f"Las hojas .{ext} no se pueden leer aquí: guárdala como .xlsx o exporta a CSV/PDF.")
    try:
        texto = _texto_xlsx(raw)
    except Exception as exc:  # noqa: BLE001
        raise DocumentoIlegible("La hoja de cálculo no se pudo leer. Exporta a CSV o PDF.") from exc
    if not texto:
        raise DocumentoIlegible("La hoja de cálculo está vacía.")
    texto = texto[:MAX_TEXT_CHARS]
    return Documento(origen="hoja", nombre=nombre,
                     bloques=[bloque_texto(texto, nombre, "hoja de cálculo, celdas separadas por tabulador")],
                     texto=texto, conversion="openpyxl", extension=ext,
                     contenido=raw, huella=_huella(raw))


# --------------------------------------------------------------- texto ----

def _documento_texto(raw: bytes, ext: str, nombre: str) -> Documento:
    texto = _decodifica(raw).replace("\r\n", "\n").strip()
    if not texto:
        raise DocumentoIlegible("El fichero de texto está vacío.")
    avisos: list[str] = []
    if len(texto) > MAX_TEXT_CHARS:
        avisos.append(f"Texto muy largo: se leen los primeros {MAX_TEXT_CHARS // 1000} mil caracteres.")
        texto = texto[:MAX_TEXT_CHARS]
    que = {"csv": "tabla CSV", "tsv": "tabla TSV", "md": "texto Markdown",
           "json": "JSON"}.get(ext, "texto plano")
    return Documento(origen="texto", nombre=nombre,
                     bloques=[bloque_texto(texto, nombre, que)], texto=texto,
                     extension=ext or "txt", contenido=texto.encode("utf-8"),
                     huella=_huella(texto.encode("utf-8")))


# ------------------------------------------------------------- entrada ----

def _huella(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _nombre_limpio(nombre: str | None, ext: str) -> str:
    base = (nombre or "documento").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    stem = base.rsplit(".", 1)[0] if "." in base else base
    stem = re.sub(r"[^A-Za-z0-9._ -]", "_", stem).strip(" ._") or "documento"
    return f"{stem[:60]}.{ext}"


def normalizar(raw: bytes, nombre: str | None = None,
               content_type: str | None = None) -> Documento:
    """UN fichero → Documento. Lanza DocumentoIlegible con un mensaje que se
    puede enseñar tal cual («Envía la foto en JPG…»)."""
    del content_type  # la magia manda; el tipo que declara el navegador miente a menudo
    if not raw:
        raise DocumentoIlegible("El fichero está vacío.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise DocumentoIlegible(f"El fichero supera {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    familia, ext = detectar_tipo(raw, nombre)
    limpio = _nombre_limpio(nombre, ext)
    if familia == "pdf":
        return _documento_pdf(raw, limpio)
    if familia == "imagen":
        return _documento_imagenes([(raw, limpio)], limpio)
    if familia == "heic":
        raise DocumentoIlegible(
            "Las fotos HEIC del iPhone no se pueden leer aquí. En Ajustes → Cámara → "
            "Formatos elige «Más compatible», o comparte la foto como JPG.")
    if familia == "office":
        return _documento_office(raw, ext, limpio)
    if familia == "hoja":
        return _documento_hoja(raw, ext, limpio)
    if familia == "texto":
        return _documento_texto(raw, ext, limpio)
    raise DocumentoIlegible(
        f"No reconozco el formato de «{limpio}». Se admite {ACCEPTED_HUMAN}.")


def normalizar_varios(ficheros: list[tuple[bytes, str | None]],
                      nombre: str | None = None) -> Documento:
    """VARIOS ficheros → UN documento (la anamnesis en 10 fotos, un informe en
    dos PDFs). Solo se combinan fotos y PDFs/Office (que acaban en PDF); una
    hoja o un texto van siempre solos."""
    ficheros = [(r, n) for r, n in ficheros if r]
    if not ficheros:
        raise DocumentoIlegible("No has adjuntado ningún fichero.")
    if len(ficheros) == 1:
        return normalizar(ficheros[0][0], ficheros[0][1])
    total = sum(len(r) for r, _n in ficheros)
    if total > MAX_UPLOAD_BYTES:
        raise DocumentoIlegible(f"Los ficheros suman más de {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")

    tipos = [detectar_tipo(r, n) for r, n in ficheros]
    familias = {f for f, _e in tipos}
    if familias <= {"imagen"}:
        base = _nombre_limpio(nombre or ficheros[0][1], "pdf")
        return _documento_imagenes([(r, n or "foto") for r, n in ficheros], base)
    if familias - {"pdf", "imagen", "office"}:
        raise DocumentoIlegible(
            "Solo se pueden juntar fotos, PDF y Word en un mismo envío; "
            "una hoja de cálculo o un texto se sube por separado.")
    # Mezcla de PDF/Word/fotos → todo a PDF y se une en uno solo.
    from pypdf import PdfReader, PdfWriter

    w = PdfWriter()
    avisos: list[str] = []
    for (raw, n), (familia, ext) in zip(ficheros, tipos):
        if familia == "pdf":
            pdf = raw
        elif familia == "imagen":
            pdf = _pdf_desde_jpegs([_jpeg_normalizado(_abrir_imagen(raw))])
        else:
            d = _documento_office(raw, ext, _nombre_limpio(n, ext))
            if not d.es_pdf:
                raise DocumentoIlegible(
                    f"«{d.nombre}» no se pudo convertir a PDF para unirlo; súbelo aparte.")
            pdf = d.contenido
            avisos += d.avisos
        try:
            for p in PdfReader(io.BytesIO(pdf)).pages:
                w.add_page(p)
        except Exception as exc:  # noqa: BLE001
            raise DocumentoIlegible(f"«{n or 'documento'}» no se pudo unir: {exc}") from exc
    buf = io.BytesIO()
    w.write(buf)
    unido = buf.getvalue()
    d = _documento_pdf(unido, _nombre_limpio(nombre or ficheros[0][1], "pdf"),
                       conversion="union", avisos=avisos)
    d.avisos.append(f"{len(ficheros)} ficheros unidos en un solo PDF.")
    return d


def bloques_con_cache(doc: Documento) -> list[dict]:
    """Los bloques del documento con `cache_control` en el ÚLTIMO: el
    documento es EL coste de la lectura; con la marca, el reintento de
    validación y el segundo pase de verificación lo leen al 10 %."""
    bloques = [dict(b) for b in doc.bloques]
    if bloques:
        bloques[-1] = {**bloques[-1], "cache_control": {"type": "ephemeral"}}
    return bloques
