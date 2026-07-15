"""Endurecimiento de las subidas de imagen (fotos de progreso y productos).

Dos invariantes de seguridad/corrección, para AMBOS caminos (save_photo, que es
alcanzable desde el portal del cliente, y save_resource_image, del coach):
- Una "bomba" (pequeña comprimida, enorme en píxeles) se rechaza ANTES de
  decodificar — no infla la memoria del worker.
- Un PNG con PALETA (modo P) se guarda con sus colores reales (el rebuild
  antiguo copiaba los índices sin la paleta y salía corrupto/negro).
"""
from __future__ import annotations

import io

import pytest
from PIL import Image

from app.services.storage import (
    PhotoValidationError,
    abs_path,
    save_photo,
    save_resource_image,
)


def _png(img: Image.Image) -> bytes:
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()


def _palette_png() -> bytes:
    return _png(Image.new("RGB", (32, 32), (200, 40, 40)).convert("P", palette=Image.Palette.ADAPTIVE))


def _bomb_png(side: int) -> bytes:
    # Color plano: enorme en píxeles, diminuto comprimido.
    return _png(Image.new("RGB", (side, side), (255, 255, 255)))


def test_save_photo_rechaza_bomba_de_pixeles():
    raw = _bomb_png(7500)  # 56 MP > tope de 50 MP, pero <15 MB comprimidos
    with pytest.raises(PhotoValidationError):
        save_photo(999_001, raw)


def test_save_resource_image_rechaza_bomba_de_pixeles():
    raw = _bomb_png(6000)  # 36 MP > tope de 25 MP
    with pytest.raises(PhotoValidationError):
        save_resource_image(raw)


def test_save_photo_paleta_conserva_colores():
    rel = save_photo(999_002, _palette_png())
    out = Image.open(abs_path(rel)).convert("RGB")
    r, g, _ = out.getpixel((16, 16))
    assert r > 150 and g < 100  # rojo, no negro


def test_save_resource_image_paleta_conserva_colores():
    rel = save_resource_image(_palette_png())
    out = Image.open(abs_path(rel)).convert("RGB")
    r, g, _ = out.getpixel((16, 16))
    assert r > 150 and g < 100
