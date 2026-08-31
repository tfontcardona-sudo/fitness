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
import threading
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.config import settings

TEMPERATURE = 0.3
# Generoso: el banco de comidas (4 slots × 7 opciones con ingredientes/macros) y el
# núcleo del plan son salidas grandes; 8000 truncaba el JSON → fallo de parseo.
MAX_TOKENS = 16000
# Techo al que sube el reintento cuando la respuesta se CORTÓ por longitud. Sin
# esto, un JSON truncado se leía como "JSON mal formado" y el reintento salía
# con el MISMO techo: se cortaba en el mismo sitio, se pagaban las dos llamadas
# enteras y el fallo era seguro. Ver `generate_json`.
MAX_TOKENS_TECHO = 32000

# ¿Se cortó por longitud la última respuesta de ESTE hilo? Va en un
# `threading.local` porque el panel de revisión (§9) lanza varios revisores a la
# vez con el mismo AIClient: un atributo de instancia se pisarían entre sí.
_corte = threading.local()

# PROMPT CACHING (ahorro de créditos): un system prompt a partir de este tamaño
# se envía como bloque con cache_control — la primera llamada escribe la caché
# (+25% de ese tramo) y las siguientes en ~5 min lo LEEN al 10% del precio.
# Gana en: reintentos de validación, bucle de reparación del panel (hasta 30
# llamadas con el mismo contexto) y generaciones seguidas. Por debajo del
# mínimo cacheable de la API el marcador se ignora en silencio (sin coste).
CACHE_SYSTEM_MIN_CHARS = 4000

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
        créditos (botón "Créditos IA" del sidebar). Best-effort: nunca rompe.

        Con prompt caching, los tokens cacheados van en campos aparte y con otro
        precio (escritura ×1,25; lectura ×0,1): se convierten a "tokens de
        entrada equivalentes" para que el saldo local siga cuadrando."""
        usage = getattr(resp, "usage", None)
        if usage is None:
            return
        from app.services.ai_credit import record_usage

        entrada = float(getattr(usage, "input_tokens", 0) or 0)
        entrada += 1.25 * float(getattr(usage, "cache_creation_input_tokens", 0) or 0)
        entrada += 0.10 * float(getattr(usage, "cache_read_input_tokens", 0) or 0)
        record_usage(
            model,
            int(round(entrada)),
            getattr(usage, "output_tokens", 0) or 0,
        )

    @staticmethod
    def _system_payload(system):
        """System prompt → carga para la API. Uno GRANDE se marca con
        cache_control (ver CACHE_SYSTEM_MIN_CHARS); una lista de bloques ya
        montada por el llamador (p. ej. el panel §9) pasa tal cual."""
        if isinstance(system, list):
            return system
        if isinstance(system, str) and len(system) >= CACHE_SYSTEM_MIN_CHARS:
            return [{"type": "text", "text": system,
                     "cache_control": {"type": "ephemeral"}}]
        return system

    @staticmethod
    def _effective_temperature(model: str, temperature: float | None) -> float | None:
        """Gotcha §5.2: el modelo pesado (claude-opus-4-8) RECHAZA `temperature`
        con un 400 de la API. Se filtra aquí, en un único sitio, para que ningún
        llamador pueda reintroducir el fallo: al modelo pesado nunca se le envía;
        el resto (p. ej. el ligero, en los revisores §14) lo conserva."""
        from app.config import settings

        if temperature is not None and model == settings.model_heavy:
            return None
        return temperature

    def _create_message(self, kwargs: dict):
        """messages.create con red de seguridad: si aun así un modelo rechaza
        `temperature` (400), reintenta UNA vez sin él — perder el determinismo
        es mejor que tumbar la extracción o el feedback en producción."""
        try:
            return self._anthropic().messages.create(**kwargs)
        except Exception as exc:
            if kwargs.pop("temperature", None) is not None and "temperature" in str(exc).lower():
                return self._anthropic().messages.create(**kwargs)
            raise

    def _raw_call(self, *, model: str, system: "str | list", user: str,
                  temperature: float | None = None,
                  max_tokens: int | None = None) -> str:
        """Una llamada cruda al modelo. Sobrescribible en tests.

        `temperature` fija el determinismo: 0 en extracción/revisión (§14) donde la
        reproducibilidad importa; None (por defecto del modelo) en generación."""
        temperature = self._effective_temperature(model, temperature)
        try:
            kwargs = {
                "model": model,
                # Techo POR LLAMADA (no se factura lo no generado; esto solo
                # limita el daño de una respuesta desbocada en la parte cara).
                "max_tokens": max_tokens or MAX_TOKENS,
                "system": self._system_payload(system),
                "messages": [{"role": "user", "content": user}],
            }
            if temperature is not None:
                kwargs["temperature"] = temperature
            resp = self._create_message(kwargs)
        except Exception as exc:
            translated = _translate_api_error(exc)
            if translated:
                raise translated from exc
            raise
        self._record_usage(model, resp)
        _corte.cortada = getattr(resp, "stop_reason", None) == "max_tokens"
        return "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )

    def _raw_call_with_pdf(
        self, *, model: str, system: str, user: str, pdf_bytes: bytes,
        temperature: float | None = None,
    ) -> str:
        """Una llamada al modelo incluyendo un PDF como documento adjunto.

        Usa el bloque `document` de la API de Anthropic (lectura nativa de PDF).
        Sobrescribible en tests.
        """
        import base64

        temperature = self._effective_temperature(model, temperature)
        b64 = base64.standard_b64encode(pdf_bytes).decode("ascii")
        try:
            kwargs = {
                "model": model,
                "max_tokens": MAX_TOKENS,
                "system": self._system_payload(system),
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": b64,
                            },
                            # El PDF (~10 páginas en base64) es EL coste de la
                            # extracción: cachearlo hace que el reintento de
                            # validación lo LEA al 10% en vez de repagarlo entero.
                            "cache_control": {"type": "ephemeral"},
                        },
                        {"type": "text", "text": user},
                    ],
                }],
            }
            if temperature is not None:
                kwargs["temperature"] = temperature
            # Misma red de seguridad del retry-sin-temperature que _raw_call
            # (antes esta ruta llamaba a la API directamente — asimetría).
            resp = self._create_message(kwargs)
        except Exception as exc:
            translated = _translate_api_error(exc)
            if translated:
                raise translated from exc
            raise
        self._record_usage(model, resp)
        _corte.cortada = getattr(resp, "stop_reason", None) == "max_tokens"
        return "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )

    def read_pdf_json(
        self, *, model: str, system: str, user: str, pdf_bytes: bytes, schema: type[T],
        temperature: float | None = None,
    ) -> T:
        """Lee un PDF, extrae datos y los valida contra el esquema. Reintenta una vez."""
        last_error: str | None = None
        attempt_user = user
        for _ in range(2):
            raw = self._raw_call_with_pdf(
                model=model, system=system, user=attempt_user, pdf_bytes=pdf_bytes,
                temperature=temperature,
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
        self, *, model: str, system: "str | list", user: str, schema: type[T],
        temperature: float | None = None, max_tokens: int | None = None,
    ) -> T:
        """Genera, parsea y valida. Reintenta UNA vez con el error inyectado."""
        last_error: str | None = None
        attempt_user = user

        techo = max_tokens
        for attempt in range(2):
            _corte.cortada = False
            raw = self._raw_call(model=model, system=system, user=attempt_user,
                                 temperature=temperature, max_tokens=techo)
            cortada = bool(getattr(_corte, "cortada", False))
            try:
                data = json.loads(_extract_json(raw))
            except json.JSONDecodeError as exc:
                last_error = (
                    "la respuesta se CORTÓ por longitud (max_tokens), no es un "
                    "error de formato" if cortada else f"JSON mal formado: {exc}")
            else:
                try:
                    return schema.model_validate(data)
                except ValidationError as exc:
                    last_error = _summarize_validation_error(exc)

            if cortada:
                # SUBIR EL TECHO y pedir brevedad. Reintentar idéntico se corta
                # en el mismo sitio: dos llamadas pagadas enteras para un fallo
                # seguro. Y el mensaje decía "JSON mal formado", que manda a
                # buscar el fallo donde no está.
                techo = min(MAX_TOKENS_TECHO, (techo or MAX_TOKENS) * 2)
                attempt_user = (
                    f"{user}\n\n--- CORRECCIÓN REQUERIDA ---\n"
                    "Tu respuesta anterior se quedó A MEDIAS: era demasiado larga "
                    "y se cortó. Devuelve el MISMO JSON pero más COMPACTO — textos "
                    "más breves, sin repetir— y completo, sin texto adicional."
                )
                continue

            # Preparar reintento con el error concreto inyectado.
            attempt_user = (
                f"{user}\n\n--- CORRECCIÓN REQUERIDA ---\n"
                f"Tu respuesta anterior falló la validación: {last_error}\n"
                "Devuelve de nuevo SOLO el JSON corregido, sin texto adicional."
            )

        if bool(getattr(_corte, "cortada", False)):
            # Decir la VERDAD: con "JSON mal formado" el coach (y quien mire el
            # log) busca el fallo en el prompt, y lo que pasa es que la
            # respuesta no cabe.
            raise AIGenerationError(
                "La respuesta de la IA se CORTÓ por longitud incluso tras subir "
                "el techo: el contenido pedido no cabe", last_error)
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
