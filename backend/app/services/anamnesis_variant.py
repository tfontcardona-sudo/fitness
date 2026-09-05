"""La ANAMNESIS de cada marca: misma sustancia, distinta piel.

Lo que NO cambia entre marcas, y no puede cambiar: las preguntas de las que
salen los números. Sexo, edad, altura, peso, objetivo, nivel, días y lugar de
entreno, alergias y patologías alimentan el motor de cálculo
(`metrics.energy_targets`) y los guardarraíles. Quitar una sola de esas
preguntas no simplifica el formulario: rompe el plan.

Lo que sí cambia:

· los BLOQUES OPCIONALES — los extras que afinan el plan pero que no lo
  bloquean (zonas a priorizar, ejercicios favoritos, horarios de comida). Una
  marca sencilla los deja fuera y su formulario se hace notablemente más corto.
· las PREGUNTAS PROPIAS de la marca — lo que un negocio necesita saber y otro
  no. En un centro con local: si es socio y qué días viene. Las respuestas se
  anexan ETIQUETADAS a las notas del cliente (mismo camino que las zonas a
  priorizar), así que no hacen falta columnas nuevas ni migraciones.

El identificador de variante vive en el perfil de marca
(`brand_config.anamnesis_variant`).
"""
from __future__ import annotations

# Bloques opcionales que el wizard sabe pintar. La marca dice cuáles quiere.
BLOQUES = ("priority_zones", "exercise_prefs", "meal_times_text")

_VARIANTES: dict[str, dict] = {
    # DQR: la anamnesis completa de siempre. NO se toca.
    "dq": {
        "optional_blocks": list(BLOQUES),
        "extra_questions": [],
    },
    # Marca sencilla (un centro): sin los extras y con lo suyo. El cuestionario
    # cumple igual —los números salen de lo mismo— pero se rellena antes.
    "simple": {
        "optional_blocks": [],
        "extra_questions": [
            {"key": "socio", "label": "¿Eres socio del centro?",
             "placeholder": "Sí / No — y desde cuándo, si lo recuerdas"},
            {"key": "horario", "label": "¿Qué días y a qué hora sueles venir?",
             "placeholder": "Ej.: lunes, miércoles y viernes por la tarde"},
        ],
    },
}


def definicion(variant: str | None) -> dict:
    """Bloques y preguntas de una variante. Una variante desconocida cae en la
    completa: ante la duda, se pregunta de más, nunca de menos."""
    v = _VARIANTES.get((variant or "").strip().lower())
    if v is None:
        v = _VARIANTES["dq"]
    return {"optional_blocks": list(v["optional_blocks"]),
            "extra_questions": [dict(q) for q in v["extra_questions"]]}


def etiquetas(variant: str | None) -> dict[str, str]:
    """{clave: enunciado} de las preguntas propias, para etiquetar la respuesta
    en las notas del cliente."""
    return {q["key"]: q["label"] for q in definicion(variant)["extra_questions"]}


def anexar_respuestas(notas: str | None, variant: str | None,
                      respuestas: dict | None) -> str | None:
    """Devuelve las notas con las respuestas propias de la marca añadidas al
    final, etiquetadas. Ignora claves que la variante no pregunta: el cuerpo
    llega del navegador y no puede escribir lo que le apetezca en la ficha."""
    if not respuestas:
        return notas
    permitidas = etiquetas(variant)
    lineas = []
    for clave, valor in respuestas.items():
        texto = str(valor or "").strip()
        if not texto or clave not in permitidas:
            continue
        lineas.append(f"[{permitidas[clave]}] {texto[:500]}")
    if not lineas:
        return notas
    bloque = "\n".join(lineas)
    return f"{notas}\n{bloque}" if (notas or "").strip() else bloque
