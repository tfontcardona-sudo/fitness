"""El PDF del cliente explica, no solo lista.

Estas regresiones cubren lo que la auditoría encontró perdido: el POR QUÉ del
enfoque y el margen de maniobra se pautaban en el plan y nunca llegaban al
documento, y las cifras salían sin contexto ni formato español.
"""
import io

from docx import Document

from app.services.docs.plan_doc import _ajuste_text, _macro_lines, generate_plan_doc
from app.services.docs.word_base import DocBrand

BRAND = DocBrand(name="DQR", color_primary="#8B1A2B", color_secondary="#4A7BA8",
                 font_family="Calibri", contact_email="hola@dqr.es")

NUTRICION = {
    "tdee_kcal": 2650, "target_kcal": 2200,
    "macros": {"carbs_g": 210, "protein_g": 165, "fat_g": 68},
    "rationale": "Déficit moderado y proteína alta para no perder fuerza.",
    "flexibility_rules": ["Una comida libre a la semana."],
    "refeed_or_break": "Recarga de carbohidratos el día de pierna.",
    "meals": [{"slot": 1, "name": "Desayuno", "time": "08:00",
               "target": {"kcal": 700, "protein_g": 50, "carbs_g": 70, "fat_g": 20}}],
    "meal_bank": {"mode": "flexible", "slots": []},
}


def _texto(**kwargs) -> str:
    data = generate_plan_doc(
        brand=BRAND, client_name="Mario", month_index=3, goal_type="fat_loss",
        diet_mode="flexible", nutrition=kwargs.pop("nutrition", NUTRICION),
        training={}, education={}, include_training=False, include_nutrition=True,
        **kwargs,
    )
    doc = Document(io.BytesIO(data))
    partes = [p.text for p in doc.paragraphs]
    for t in doc.tables:
        for row in t.rows:
            partes += [c.text for c in row.cells]
    return "\n".join(partes)


def test_el_documento_explica_el_porque_y_el_margen():
    texto = _texto()
    # El criterio del coach viaja al cliente (antes se quedaba en el sistema).
    assert "POR QUÉ ESTE ENFOQUE" in texto
    assert "Déficit moderado y proteína alta" in texto
    assert "Una comida libre a la semana." in texto
    assert "Recarga de carbohidratos el día de pierna." in texto
    # Mapa del documento y origen de la cifra.
    assert "EN ESTE DOCUMENTO" in texto
    assert "De dónde sale tu cifra" in texto
    assert "2.650" in texto and "2.200" in texto   # formato es-ES


def test_sin_argumentario_no_se_pintan_secciones_vacias():
    nut = {k: v for k, v in NUTRICION.items()
           if k not in ("rationale", "flexibility_rules", "refeed_or_break")}
    texto = _texto(nutrition=nut)
    assert "POR QUÉ ESTE ENFOQUE" not in texto
    assert "TU MARGEN DE MANIOBRA" not in texto


def test_los_porcentajes_del_reparto_suman_cien():
    lineas = _macro_lines({"carbs_g": 210, "protein_g": 165, "fat_g": 68}, 2200)
    pct = [int(x.rstrip("%")) for x in lineas[1].split(" de ")[0].split(" · ")]
    assert sum(pct) == 100


def test_el_ajuste_no_repite_el_signo_con_la_palabra():
    # "Déficit -450 kcal" decía dos veces lo mismo y con un guion feo.
    assert _ajuste_text({"tdee_kcal": 2650, "target_kcal": 2200}, "fat_loss") \
        == "Déficit de 450 kcal (17%)"
    assert _ajuste_text({"tdee_kcal": 2000, "target_kcal": 2000}, "maintenance") \
        == "Mantenimiento · sin ajuste"
