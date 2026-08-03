"""Gate de seguridad — lista roja y semáforo (hardening §12).

Determinista y NO anulable: define qué planes NUNCA pueden auto-enviarse y en qué
color queda un plan. El semáforo:
- VERDE: validación limpia + ICP ≥ umbral + ningún veto → envío automático.
- ÁMBAR: hallazgos menores o ICP intermedio → revisión rápida.
- ROJO: cualquier bandera de la lista roja → nunca auto-envío (revisión humana).

La lista roja (§12) cubre poblaciones y condiciones de riesgo: menores/mayores,
embarazo/lactancia, IMC<18,5, señales o historial de TCA, patologías (diabetes,
renal, hepática, cardiovascular, tiroidea, EII, celiaquía, SOP, HTA no controlada,
dislipemia en tratamiento, gota, intestino irritable/SIBO, reflujo/gastritis,
anemia, osteoporosis, apnea del sueño — las comunes añadidas por criterio del
coach, CRITERIOS_ASESORIA §7), medicación con interacción (anticoagulantes, IMAO,
levotiroxina, corticoides, GLP-1, diuréticos, betabloqueantes, antidepresivos),
antecedente de anafilaxia, cirugía bariátrica y contradicciones sin resolver.
Esta lista NO se desactiva.

Se apoya en el texto libre de la anamnesis (notas médicas, medicación, estilo de
vida) con normalización acento-insensible.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass


def _norm(s: str | None) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii").lower()


# Cada bandera: (código, etiqueta legible, términos que la disparan en texto libre).
# Los términos ya van normalizados (sin acentos, minúsculas).
_RED_TERMS: list[tuple[str, str, tuple[str, ...]]] = [
    ("embarazo", "Embarazo o lactancia",
     ("embaraz", "gestante", "gestacion", "lactancia", "amamant", "dando el pecho")),
    ("tca", "Señales o historial de TCA",
     ("anorexia", "bulimia", "tca", "trastorno alimentario", "trastorno de la conducta",
      "atracon", "purga", "vomito autoinducido", "me provoco el vomito", "laxante para adelgazar",
      "miedo a engordar", "ortorexia")),
    ("diabetes", "Diabetes",
     ("diabetes tipo 1", "diabetes tipo 2", "diabetico", "diabetica", "insulinodependiente",
      "diabetes mellitus", "prediabetes", "metformina")),
    ("renal", "Enfermedad renal",
     ("insuficiencia renal", "enfermedad renal", "dialisis", "nefropatia", "trasplante de rinon")),
    ("hepatica", "Enfermedad hepática",
     ("cirrosis", "hepatitis", "insuficiencia hepatica", "enfermedad hepatica", "higado graso severo")),
    ("cardiovascular", "Patología cardiovascular",
     ("cardiopatia", "insuficiencia cardiaca", "arritmia", "infarto", "angina de pecho",
      "marcapasos", "stent", "bypass")),
    ("tiroides", "Patología tiroidea",
     ("hipotiroid", "hipertiroid", "hashimoto", "graves", "nodulo tiroideo", "tiroidectomia")),
    ("eii", "Enfermedad inflamatoria intestinal",
     ("crohn", "colitis ulcerosa", "enfermedad inflamatoria intestinal", "eii")),
    ("celiaquia", "Celiaquía",
     ("celiac", "celiaquia", "enfermedad celiaca")),
    ("sop", "SOP",
     ("sop", "ovario poliquistico", "ovarios poliquisticos", "sindrome de ovario")),
    ("hta", "HTA no controlada",
     ("hipertension no controlada", "tension descontrolada", "hta no controlada")),
    ("dislipemia", "Dislipemia en tratamiento",
     ("colesterol en tratamiento", "estatina", "dislipemia", "hipercolesterolemia en tratamiento",
      "triglicéridos altos en tratamiento", "trigliceridos en tratamiento")),
    ("anafilaxia", "Antecedente de anafilaxia",
     ("anafilaxia", "shock anafilactico", "epipen", "adrenalina autoinyectable")),
    ("bariatrica", "Cirugía bariátrica",
     ("cirugia bariatrica", "bypass gastrico", "manga gastrica", "gastrectomia", "balon gastrico")),
    # Patologías COMUNES añadidas por criterio del coach (CRITERIOS_ASESORIA §7):
    # frecuentes en consulta y con pauta dietética/de entreno propia — el plan
    # queda retenido para revisión, no se auto-envía.
    ("gota", "Gota / hiperuricemia",
     ("gota", "hiperuricemia", "acido urico alto", "urico alto", "ataque de gota")),
    ("sii", "Intestino irritable / digestivo funcional",
     ("intestino irritable", "colon irritable", "sibo", "dispepsia funcional")),
    ("reflujo", "Reflujo / hernia de hiato / gastritis",
     ("reflujo", "hernia de hiato", "gastritis", "esofagitis", "acidez cronica")),
    ("anemia", "Anemia / ferropenia",
     ("anemia", "ferropenia", "ferritina baja", "hierro bajo", "deficit de hierro")),
    ("osteoporosis", "Osteoporosis / osteopenia",
     ("osteoporosis", "osteopenia", "densidad osea baja")),
    ("apnea", "Apnea del sueño",
     ("apnea del sueno", "apnea obstructiva", "cpap")),
    # Medicación con interacción nutricional relevante.
    ("med_anticoagulante", "Medicación: anticoagulantes",
     ("sintrom", "warfarina", "acenocumarol", "anticoagulante", "heparina")),
    ("med_imao", "Medicación: IMAO",
     ("imao", "inhibidor de la monoaminooxidasa", "fenelzina", "tranilcipromina")),
    ("med_levotiroxina", "Medicación: levotiroxina",
     ("levotiroxina", "eutirox", "levothroid", "tirosint")),
    ("med_corticoides", "Medicación: corticoides",
     ("corticoide", "prednisona", "prednisolona", "dexametasona", "cortisona")),
    ("med_glp1", "Medicación: GLP-1",
     ("ozempic", "wegovy", "semaglutida", "saxenda", "liraglutida", "glp-1", "glp1", "mounjaro",
      "tirzepatida")),
    ("med_diureticos", "Medicación: diuréticos",
     ("diuretico", "furosemida", "seguril", "hidroclorotiazida", "espironolactona")),
    ("med_betabloqueante", "Medicación: betabloqueantes",
     ("betabloqueante", "bisoprolol", "atenolol", "propranolol", "metoprolol", "carvedilol")),
    ("med_antidepresivo", "Medicación: antidepresivos/ansiolíticos",
     ("antidepresivo", "sertralina", "fluoxetina", "escitalopram", "paroxetina",
      "venlafaxina", "mirtazapina", "ansiolitico", "benzodiacepina", "lorazepam", "diazepam")),
]

# Umbral de ICP para el verde (por defecto). Configurable por el caller.
ICP_GREEN_THRESHOLD = 80

IMC_MIN = 18.5
AGE_MIN = 18
AGE_MAX = 65


@dataclass
class RedFlag:
    code: str
    label: str
    source: str  # de dónde salió (edad, imc, o el término de texto)


def _text_of(profile: dict) -> str:
    parts = [profile.get(k) for k in
             ("medical_notes", "medication_notes", "injuries_notes",
              "lifestyle_notes", "clinical_notes", "current_supplements")]
    return _norm(" \n ".join(p for p in parts if p))


def bmi(weight_kg: float | None, height_cm: float | None) -> float | None:
    if not weight_kg or not height_cm:
        return None
    m = height_cm / 100.0
    return round(weight_kg / (m * m), 1) if m > 0 else None


def red_flags(profile: dict, *, unresolved_contradictions: list[str] | None = None) -> list[RedFlag]:
    """Banderas rojas del cliente. `profile`: dict con sex, age, height_cm,
    weight_kg y las notas de texto libre. Nunca lanza."""
    flags: list[RedFlag] = []
    age = profile.get("age")
    if isinstance(age, (int, float)):
        if age < AGE_MIN:
            flags.append(RedFlag("menor", "Menor de edad", f"edad {age:.0f}"))
        elif age > AGE_MAX:
            flags.append(RedFlag("mayor_65", "Mayor de 65", f"edad {age:.0f}"))
    imc = bmi(profile.get("weight_kg"), profile.get("height_cm"))
    if imc is not None and imc < IMC_MIN:
        flags.append(RedFlag("bajo_peso", f"IMC {imc} < {IMC_MIN}", f"imc {imc}"))

    text = _text_of(profile)
    for code, label, terms in _RED_TERMS:
        hit = next((t for t in terms if t in text), None)
        if hit:
            flags.append(RedFlag(code, label, hit))

    for c in (unresolved_contradictions or []):
        flags.append(RedFlag("contradiccion", "Contradicción sin resolver", c))
    return flags


def traffic_light(
    *,
    has_deterministic_violation: bool,
    red: list[RedFlag],
    icp: float | None,
    minor_findings: int = 0,
    icp_threshold: int = ICP_GREEN_THRESHOLD,
) -> str:
    """Color del plan (§12). ROJO manda sobre todo lo demás y no se puede
    desactivar. VERDE exige limpieza total + ICP alto. Resto → ÁMBAR."""
    if red or has_deterministic_violation:
        return "rojo"
    if icp is not None and icp >= icp_threshold and minor_findings == 0:
        return "verde"
    return "ambar"
