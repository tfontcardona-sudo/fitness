"""Cliente de IA — capa fina sobre la API de Anthropic (PARTE D).

Responsabilidades:
- Llamar al modelo (HEAVY para generación/visión, LIGHT para parseo/matching).
- Forzar salida JSON, parsearla de forma robusta (tolera ```json ... ``` por si
  el modelo se desvía) y validarla contra un schema Pydantic.
- Retry 1 con el error de validación inyectado ("tu JSON falló en X, corrígelo").
- Segundo fallo → AIGenerationError, que el orquestador traduce a estado de
  error recuperable + notificación al coach.

Parámetros fijos (D.2): temperatura 0.3, max_tokens generoso.

El cliente NO conoce el dominio (nutrición/entrenamiento): solo recibe system
prompt, user prompt y schema. El conocimiento experto vive en prompts.py y la
orquestación en generator.py.
"""

from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.config import settings

TEMPERATURE = 0.3
# Generoso: el banco de comidas (4 slots × 7 opciones con ingredientes/macros) y el
# núcleo del plan son salidas grandes; 8000 truncaba el JSON → fallo de parseo.
MAX_TOKENS = 16000

T = TypeVar("T", bound=BaseModel)

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class AIGenerationError(RuntimeError):
    """La IA no produjo JSON válido conforme al schema tras el reintento."""

    def __init__(self, message: str, last_error: str | None = None):
        super().__init__(message)
        self.last_error = last_error


def _translate_api_error(exc: Exception) -> "AIGenerationError | None":
    """Traduce un error de la API de Anthropic (sin crédito, rate limit, clave
    inválida, etc.) a AIGenerationError con mensaje legible, para que el endpoint
    devuelva un 502 claro en vez de un 500 opaco. Devuelve None si no es un error
    de la API (en ese caso, se deja propagar)."""
    try:
        from anthropic import APIError
    except Exception:
        return None
    if isinstance(exc, APIError):
        msg = getattr(exc, "message", None) or str(exc)
        return AIGenerationError(f"La API de Anthropic devolvió un error: {msg}")
    return None


def _extract_json(text: str) -> str:
    """Aísla el JSON aunque venga envuelto en markdown o con texto alrededor."""
    text = text.strip()
    fenced = _JSON_FENCE.search(text)
    if fenced:
        return fenced.group(1).strip()
    # Primer { hasta el último } — defensa ante preámbulos accidentales.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


class AIClient:
    """Wrapper con reintento y validación. Inyectable/mockeable en tests."""

    def __init__(self, api_key: str | None = None):
        key = (api_key or settings.anthropic_api_key or "").strip()
        # Una clave corrupta (p. ej. mal pegada en el .env por el terminal, con
        # caracteres no ASCII) rompe httpx al montar la cabecera x-api-key con
        # un UnicodeEncodeError opaco. Mejor fallar aquí con un mensaje claro.
        if not key:
            raise AIGenerationError(
                "Falta ANTHROPIC_API_KEY en el .env del servidor: añádela y reinicia."
            )
        if not key.isascii():
            raise AIGenerationError(
                "La ANTHROPIC_API_KEY del .env contiene caracteres no válidos "
                "(probablemente se corrompió al pegarla). Vuelve a escribirla en el .env."
            )
        self._api_key = key
        self._client = None  # perezoso: no instanciar SDK si se usa un mock

    def _anthropic(self):
        if self._client is None:
            from anthropic import Anthropic

            self._client = Anthropic(api_key=self._api_key)
        return self._client

    @staticmethod
    def _record_usage(model: str, resp) -> None:
        """Descuenta el coste real (tokens de la respuesta) del saldo local de
        créditos (botón "Créditos IA" del sidebar). Best-effort: nunca rompe."""
        usage = getattr(resp, "usage", None)
        if usage is None:
            return
        from app.services.ai_credit import record_usage

        record_usage(
            model,
            getattr(usage, "input_tokens", 0) or 0,
            getattr(usage, "output_tokens", 0) or 0,
        )

    def _raw_call(self, *, model: str, system: str, user: str) -> str:
        """Una llamada cruda al modelo. Sobrescribible en tests."""
        try:
            resp = self._anthropic().messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as exc:
            translated = _translate_api_error(exc)
            if translated:
                raise translated from exc
            raise
        self._record_usage(model, resp)
        return "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )

    def _raw_call_with_pdf(
        self, *, model: str, system: str, user: str, pdf_bytes: bytes
    ) -> str:
        """Una llamada al modelo incluyendo un PDF como documento adjunto.

        Usa el bloque `document` de la API de Anthropic (lectura nativa de PDF).
        Sobrescribible en tests.
        """
        import base64

        b64 = base64.standard_b64encode(pdf_bytes).decode("ascii")
        try:
            resp = self._anthropic().messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": user},
                    ],
                }],
            )
        except Exception as exc:
            translated = _translate_api_error(exc)
            if translated:
                raise translated from exc
            raise
        self._record_usage(model, resp)
        return "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )

    def read_pdf_json(
        self, *, model: str, system: str, user: str, pdf_bytes: bytes, schema: type[T]
    ) -> T:
        """Lee un PDF, extrae datos y los valida contra el esquema. Reintenta una vez."""
        last_error: str | None = None
        attempt_user = user
        for _ in range(2):
            raw = self._raw_call_with_pdf(
                model=model, system=system, user=attempt_user, pdf_bytes=pdf_bytes
            )
            try:
                data = json.loads(_extract_json(raw))
            except json.JSONDecodeError as exc:
                last_error = f"JSON mal formado: {exc}"
            else:
                try:
                    return schema.model_validate(data)
                except ValidationError as exc:
                    last_error = _summarize_validation_error(exc)
            attempt_user = (
                f"{user}\n\n--- CORRECCIÓN REQUERIDA ---\n"
                f"Tu respuesta anterior falló la validación: {last_error}\n"
                "Devuelve de nuevo SOLO el JSON corregido, sin texto adicional."
            )
        raise AIGenerationError(
            "La IA no extrajo un JSON válido del PDF tras el reintento", last_error
        )

    def generate_json(
        self, *, model: str, system: str, user: str, schema: type[T]
    ) -> T:
        """Genera, parsea y valida. Reintenta UNA vez con el error inyectado."""
        last_error: str | None = None
        attempt_user = user

        for attempt in range(2):
            raw = self._raw_call(model=model, system=system, user=attempt_user)
            try:
                data = json.loads(_extract_json(raw))
            except json.JSONDecodeError as exc:
                last_error = f"JSON mal formado: {exc}"
            else:
                try:
                    return schema.model_validate(data)
                except ValidationError as exc:
                    last_error = _summarize_validation_error(exc)

            # Preparar reintento con el error concreto inyectado.
            attempt_user = (
                f"{user}\n\n--- CORRECCIÓN REQUERIDA ---\n"
                f"Tu respuesta anterior falló la validación: {last_error}\n"
                "Devuelve de nuevo SOLO el JSON corregido, sin texto adicional."
            )

        raise AIGenerationError(
            "La IA no devolvió un JSON válido tras el reintento", last_error
        )


def _summarize_validation_error(exc: ValidationError) -> str:
    """Resumen compacto y accionable de los errores de Pydantic para el reintento."""
    parts = []
    for err in exc.errors()[:6]:
        loc = ".".join(str(p) for p in err["loc"])
        parts.append(f"{loc}: {err['msg']}")
    return " | ".join(parts)
