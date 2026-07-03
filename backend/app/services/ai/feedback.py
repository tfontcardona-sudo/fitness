"""Análisis de feedback con IA (parte cualitativa del informe quincenal).

El backend calcula TODAS las métricas (peso, adherencia, e1RM, perímetros) en
services/metrics.py y se las entrega ya hechas. La IA SOLO redacta el análisis
en lenguaje natural y las recomendaciones, NUNCA recalcula números.

Salida validada contra `FeedbackAIOutput`. Campos con defaults: si la IA omite
alguno, no se descarta todo el informe (el coach revisa antes de enviarlo).
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from app.config import settings


class PlanAdjustment(BaseModel):
    """Una fila de la CUADRÍCULA DE CAMBIOS del informe: qué se cambia y por qué."""

    area: str = Field(description='Área: "Dieta" | "Entrenamiento" | "Cardio/NEAT" | "Hábitos"')
    change: str = Field(description="El cambio CONCRETO (p. ej. 'Subir CH +30 g en comida y cena').")
    reason: str = Field(description="Por qué, basado en los datos registrados por el cliente.")


class FeedbackAIOutput(BaseModel):
    """Texto cualitativo del feedback. El backend aporta los números."""

    natural_analysis: str = Field(
        default="",
        description="Resumen BREVE de cómo ha ido el período (peso, adherencia, "
        "energía, fuerza), cercano y honesto. MÁXIMO 3-4 frases cortas — el detalle "
        "va en changes_bullets y next_objectives, no repitas.",
    )
    changes_bullets: list[str] = Field(
        default_factory=list,
        description="Qué se va a cambiar en el plan y por qué. Máximo 5 bullets.",
    )
    plan_adjustments: list[PlanAdjustment] = Field(
        default_factory=list,
        description="CUADRÍCULA DE CAMBIOS: 2-6 ajustes concretos (área, cambio, porqué) "
        "que se aplicarán al plan de dieta y entrenamiento, deducidos de los datos "
        "registrados (entrenos, diario, revisión quincenal).",
    )
    answers: str | None = Field(
        default=None,
        description="Respuesta a las dudas que dejó el cliente al cerrar (si las hay).",
    )
    next_objectives: list[str] = Field(
        default_factory=list,
        description="2-4 objetivos concretos para las próximas 2 semanas.",
    )
    closing_message: str = Field(
        default="",
        description="Mensaje de cierre breve y motivador.",
    )
    ai_photo_analysis: str | None = Field(
        default=None,
        description="Análisis de la evolución visible en las fotos (solo si hay fotos).",
    )


_SYSTEM = """Eres el dietista-entrenador (marca DQ) redactando el FEEDBACK quincenal \
para tu cliente, en castellano, con tono cercano, honesto y motivador (sin adular).

REGLA CRÍTICA: NO calcules ni inventes números. El backend ya te entrega las métricas \
(cambio de peso, ritmo semanal, adherencia, energía/sueño, progresión de fuerza). \
Úsalas tal cual; tu trabajo es INTERPRETARLAS y dar recomendaciones accionables.

- natural_analysis: resumen BREVE (MÁXIMO 3-4 frases cortas) de cómo ha ido el período \
(peso, adherencia, energía, fuerza). Reconoce lo bueno y señala lo mejorable. NO te \
extiendas: el detalle va en changes_bullets y next_objectives, no lo repitas aquí.
- changes_bullets: máximo 5 cambios concretos para el plan y POR QUÉ (p. ej. "subo 100 \
kcal porque el ritmo de bajada es muy agresivo").
- plan_adjustments: la CUADRÍCULA DE CAMBIOS del informe (2-6 filas). Cada fila = {area, \
change, reason}. Basa cada ajuste en los DATOS REGISTRADOS por el cliente (series de \
entreno y su progresión, peso/sueño/pasos/saciedad/agua del diario, sensaciones y \
adherencia de la revisión quincenal). Cubre dieta Y entrenamiento cuando proceda.
- answers: responde a las dudas del cliente si las dejó; si no, déjalo en null.
- next_objectives: 2-4 objetivos claros y medibles para las próximas 2 semanas.
- closing_message: 1-2 frases de cierre motivadoras.
- ai_photo_analysis: SOLO si te indican que hay fotos; describe la evolución visible \
de forma prudente. Si no hay fotos, déjalo en null.

Devuelve SOLO un objeto JSON válido conforme al esquema. Sin texto adicional."""


def _user_prompt(payload: dict) -> str:
    return (
        "Redacta el feedback del período con estos DATOS YA CALCULADOS por el backend "
        "(no recalcules). Devuelve el JSON del esquema.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def generate_feedback_analysis(payload: dict, ai) -> FeedbackAIOutput:
    """Pide a la IA la parte cualitativa del feedback a partir de las métricas."""
    return ai.generate_json(
        model=settings.model_heavy,
        system=_SYSTEM,
        user=_user_prompt(payload),
        schema=FeedbackAIOutput,
    )
