"""Guardrails — validación de seguridad de TODA salida de IA (E.4 + F.4).

Capa independiente de la validación de forma (Pydantic en schemas/ai.py).
Pydantic garantiza que el JSON tiene la *estructura* correcta; los guardrails
garantizan que los *valores* son seguros y coherentes con la metodología.

Cada función devuelve `GuardrailReport`:
- `violations`: problemas que BLOQUEAN la publicación (kcal por debajo del
  mínimo fisiológico, proteína insuficiente, volumen excesivo, ejercicio
  contraindicado…). Si hay alguna, el plan no se publica tal cual.
- `warnings`: avisos no bloqueantes que se registran en plans.guardrail_flags
  y se muestran al coach para revisión.

Diseño: los guardrails NO modifican la salida; informan. El servicio de IA
decide reintentar (con el error inyectado) o escalar al coach.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# --- Constantes E.4 (nutrición) ---
KCAL_FLOOR_FEMALE = 1400
KCAL_FLOOR_MALE = 1600
RECAL_KCAL_ADJUST_MAX = 0.15   # ±15% kcal por recalibración
PROTEIN_MIN_G_PER_KG = 1.4
FAT_MIN_G_PER_KG = 0.5
DEFICIT_MAX_PCT = 0.30         # 30% TDEE
SURPLUS_MAX_PCT = 0.15         # 15% TDEE
MEAL_OPTION_TOLERANCE = 0.05   # ±5% macros del slot

# --- Constantes F.4 (entrenamiento) ---
SETS_MAX_PER_GROUP_WEEK = 25
# Piso de volumen semanal por grupo entrenado: por debajo de ~6 series/semana el
# estímulo hipertrófico suele ser insuficiente (Schoenfeld/Krieger). Aviso, no
# bloqueo (el coach decide, p. ej. en un principiante o un grupo de mantenimiento).
SETS_MIN_PER_GROUP_WEEK = 6
LOAD_INCREMENT_MAX_PCT = 0.10  # +10% por ejercicio y recalibración
SESSION_MINUTES_FORMULA_PER_SET = 3
SESSION_MINUTES_FIXED_OVERHEAD = 10
# La duración es una ESTIMACIÓN heurística y la logística no es seguridad: un
# exceso leve sobre el máximo declarado es aviso (el coach recorta), no bloqueo.
# Solo bloquea un exceso holgado (> tolerancia).
SESSION_MINUTES_TOLERANCE = 0.20

KCAL_PER_G = {"protein_g": 4, "carbs_g": 4, "fat_g": 9}


@dataclass
class GuardrailReport:
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations

    def merge(self, other: "GuardrailReport") -> "GuardrailReport":
        return GuardrailReport(
            violations=self.violations + other.violations,
            warnings=self.warnings + other.warnings,
        )

    def as_flags(self) -> list[str]:
        """Para persistir en plans.guardrail_flags (prefijo legible)."""
        return [f"violation:{v}" for v in self.violations] + [
            f"warning:{w}" for w in self.warnings
        ]


# =================================================================== E.4 ====

def check_nutrition(
    nutrition: dict,
    *,
    sex: str,
    weight_kg: float,
    bmr: float,
    tdee: float,
    is_recalibration: bool = False,
    previous_target_kcal: float | None = None,
) -> GuardrailReport:
    """Valida el bloque de nutrición de la salida de IA contra E.4.

    `nutrition` es el dict `nutrition` de PlanCoreOutput (ya validado en forma).
    """
    r = GuardrailReport()
    target = float(nutrition["target_kcal"])
    macros = nutrition["macros"]
    protein = float(macros["protein_g"])
    fat = float(macros["fat_g"])

    # Suelo calórico: max(BMR, suelo por sexo)
    floor = max(bmr, KCAL_FLOOR_MALE if sex == "male" else KCAL_FLOOR_FEMALE)
    if target < floor:
        r.violations.append(
            f"kcal objetivo {target:.0f} por debajo del mínimo {floor:.0f} "
            f"(max BMR/{'1600' if sex == 'male' else '1400'})"
        )

    # Déficit / superávit máximos respecto al TDEE
    if tdee > 0:
        delta_pct = (target - tdee) / tdee
        if delta_pct < -DEFICIT_MAX_PCT:
            r.violations.append(
                f"déficit {abs(delta_pct) * 100:.0f}% supera el máximo "
                f"{DEFICIT_MAX_PCT * 100:.0f}% del TDEE"
            )
        if delta_pct > SURPLUS_MAX_PCT:
            r.violations.append(
                f"superávit {delta_pct * 100:.0f}% supera el máximo "
                f"{SURPLUS_MAX_PCT * 100:.0f}% del TDEE"
            )

    # Mínimos de proteína y grasa por kg
    if weight_kg > 0:
        if protein < PROTEIN_MIN_G_PER_KG * weight_kg - 0.5:
            r.violations.append(
                f"proteína {protein:.0f} g < mínimo "
                f"{PROTEIN_MIN_G_PER_KG * weight_kg:.0f} g ({PROTEIN_MIN_G_PER_KG} g/kg)"
            )
        if fat < FAT_MIN_G_PER_KG * weight_kg - 0.5:
            r.violations.append(
                f"grasa {fat:.0f} g < mínimo "
                f"{FAT_MIN_G_PER_KG * weight_kg:.0f} g ({FAT_MIN_G_PER_KG} g/kg)"
            )

    # Coherencia kcal ↔ macros (no debe desviarse mucho de target)
    macro_kcal = sum(float(macros[k]) * v for k, v in KCAL_PER_G.items())
    if target > 0 and abs(macro_kcal - target) / target > 0.10:
        r.warnings.append(
            f"suma de macros ({macro_kcal:.0f} kcal) se desvía >10% del "
            f"objetivo ({target:.0f} kcal)"
        )

    # Límite de ajuste en recalibración (±15%)
    if is_recalibration and previous_target_kcal:
        change = abs(target - previous_target_kcal) / previous_target_kcal
        if change > RECAL_KCAL_ADJUST_MAX:
            r.violations.append(
                f"ajuste de {change * 100:.0f}% supera el máximo "
                f"{RECAL_KCAL_ADJUST_MAX * 100:.0f}% por recalibración"
            )

    # Slots de comida: cada target de slot dentro de ±5% no aplica aquí
    # (se valida por opción en check_meal_options). Aquí: suma de slots ≈ target.
    meals = nutrition.get("meals", [])
    if meals:
        slot_sum = sum(float(m["target"]["kcal"]) for m in meals)
        if target > 0 and abs(slot_sum - target) / target > 0.10:
            r.warnings.append(
                f"suma de slots ({slot_sum:.0f} kcal) se desvía >10% del "
                f"objetivo diario ({target:.0f} kcal)"
            )
    return r


# --- Alérgenos/aversiones: sinónimos frecuentes en castellano por alérgeno ---
# La coincidencia es por término del cliente + expansión de sinónimos de alto
# nivel de confianza. Un alérgeno detectado => VIOLACIÓN (seguridad); una
# aversión => WARNING (preferencia).
_ALLERGEN_SYNONYMS: dict[str, tuple[str, ...]] = {
    "lactosa": ("lactosa", "leche", "yogur", "queso", "nata", "mantequilla", "lacteo",
                "cuajada", "kefir", "requeson", "cremoso"),
    "leche": ("leche", "lactosa", "yogur", "queso", "nata", "mantequilla", "lacteo", "requeson"),
    "gluten": ("gluten", "trigo", "cebada", "centeno", "espelta", "\bpan\b", "pasta",
               "harina", "cuscus", "seitan", "galleta", "biz cocho", "bizcocho"),
    "frutos secos": ("fruto seco", "frutos secos", "nuez", "nueces", "almendra", "avellana",
                     "anacardo", "pistacho", "cacahuete", "\bmani\b", "pinon", "piñon", "pesto"),
    "cacahuete": ("cacahuete", "\bmani\b", "crema de cacahuete"),
    "marisco": ("marisco", "gamba", "langostino", "mejillon", "almeja", "ostra", "calamar",
                "pulpo", "cangrejo", "langosta", "sepia", "berberecho", "cigala"),
    "crustaceos": ("gamba", "langostino", "cangrejo", "langosta", "cigala", "marisco"),
    "pescado": ("pescado", "atun", "salmon", "merluza", "bacalao", "sardina", "caballa",
                "trucha", "lubina", "dorada", "anchoa", "boqueron", "panga", "gallo"),
    "huevo": ("huevo", "\bclara\b", "\byema\b", "tortilla", "mayonesa"),
    "soja": ("\bsoja\b", "tofu", "edamame", "tempeh", "salsa de soja"),
    "sesamo": ("sesamo", "tahini", "tahin"),
    "fructosa": ("fructosa", "\bmiel\b", "sirope"),
}


def _norm_food(s: str | None) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii").lower()


def _terms_for(item: str) -> tuple[str, ...]:
    key = _norm_food(item).strip()
    for k, syns in _ALLERGEN_SYNONYMS.items():
        if _norm_food(k) == key or key in syns:
            return syns
    return (key,) if key else ()


def _ingredient_texts(opt: dict) -> list[str]:
    texts: list[str] = []
    for ing in opt.get("ingredients", []) or []:
        texts.append(_norm_food(ing.get("food", "")) + " " + _norm_food(ing.get("household", "")))
    # modo strict: el plato puede llevar 'ingredients' igual; si no, usa title
    if not texts and opt.get("title"):
        texts.append(_norm_food(opt.get("title")))
    return texts


def _match_term(terms: tuple[str, ...], texts: list[str]) -> str | None:
    for text in texts:
        for t in terms:
            if not t:
                continue
            hit = re.search(t, text) if "\\b" in t else (t in text)
            if hit:
                return t.replace("\\b", "")
    return None


def _check_option_restrictions(
    r: GuardrailReport, slot: int, opt: dict, allergies: list[str], dislikes: list[str], label: str = ""
) -> None:
    key = opt.get("key", opt.get("title", "?"))
    texts = _ingredient_texts(opt)
    for al in allergies or []:
        found = _match_term(_terms_for(al), texts)
        if found:
            r.violations.append(
                f"⚠ ALÉRGENO: opción {label}slot {slot} '{key}' contiene '{found}' "
                f"(alergia/intolerancia del cliente: {al}) — reemplazar"
            )
    for dl in dislikes or []:
        found = _match_term(_terms_for(dl), texts)
        if found:
            r.warnings.append(
                f"aversión: opción {label}slot {slot} '{key}' contiene '{found}' ({dl})"
            )


def check_meal_options(
    slots: list[dict], day_targets: dict[int, dict],
    allergies: list[str] | None = None, dislikes: list[str] | None = None,
) -> GuardrailReport:
    """Valida macros ±5% (E.4) Y que ninguna opción contenga alérgenos/aversiones.

    `slots`: lista de FlexibleSlot serializados (slot + options[]).
    `day_targets`: {slot: {kcal, protein_g, carbs_g, fat_g}} del plan núcleo.
    Un alérgeno detectado en los ingredientes => violación (flag prominente).
    """
    r = GuardrailReport()
    for slot_block in slots:
        slot = slot_block["slot"]
        target = day_targets.get(slot)
        for opt in slot_block["options"]:
            if target:
                _check_single_option(r, slot, opt, target)
            _check_option_restrictions(r, slot, opt, allergies or [], dislikes or [])
        if not target:
            r.warnings.append(f"slot {slot} sin target de referencia")
    return r


def check_strict_day_meals(
    days: list[dict], day_targets: dict[int, dict],
    allergies: list[str] | None = None, dislikes: list[str] | None = None,
) -> GuardrailReport:
    """Igual que check_meal_options pero para el modo strict (un plato/slot/día)."""
    r = GuardrailReport()
    for day_block in days:
        day_name = day_block.get("day", "?")
        for meal in day_block["meals"]:
            slot = meal["slot"]
            target = day_targets.get(slot)
            if target:
                _check_single_option(r, slot, meal["dish"], target, label=f"{day_name}/")
            else:
                r.warnings.append(f"slot {slot} sin target de referencia")
            _check_option_restrictions(r, slot, meal["dish"], allergies or [], dislikes or [], label=f"{day_name}/")
    return r


def _check_single_option(
    r: GuardrailReport, slot: int, opt: dict, target: dict, label: str = ""
) -> None:
    macros = opt["macros"]
    key = opt.get("key", opt.get("title", "?"))
    for macro in ("kcal", "protein_g", "carbs_g", "fat_g"):
        tgt = float(target[macro])
        val = float(macros[macro])
        if tgt <= 0:
            continue
        if abs(val - tgt) / tgt > MEAL_OPTION_TOLERANCE:
            r.violations.append(
                f"opción {label}slot {slot} '{key}': {macro} {val:.0f} fuera de "
                f"±{MEAL_OPTION_TOLERANCE * 100:.0f}% del objetivo {tgt:.0f}"
            )


# =================================================================== F.4 ====

def check_training(
    training: dict,
    *,
    training_days_declared: int,
    session_max_min: int,
    client_contraindications: set[str],
    exercise_lookup: dict[int, dict],
    is_recalibration: bool = False,
    previous_weights: dict[int, float] | None = None,
) -> GuardrailReport:
    """Valida el bloque de entrenamiento contra F.4.

    `exercise_lookup`: {exercise_id: {contraindications, muscle_primary, name}}
    para cruzar contraindicaciones y contar volumen por grupo.
    `previous_weights`: {exercise_id: start_weight_hint_kg} del plan anterior,
    para el límite de +10% por recalibración.
    """
    r = GuardrailReport()
    sessions = training.get("sessions", [])

    # 1) Nunca exceder días declarados
    if len(sessions) > training_days_declared:
        r.violations.append(
            f"{len(sessions)} sesiones > {training_days_declared} días declarados"
        )

    weekly_sets_by_group: dict[str, float] = {}

    for sess in sessions:
        session_sets = 0
        for ex in sess.get("exercises", []):
            ex_id = ex["exercise_id"]
            sets = int(ex["sets"])
            session_sets += sets
            info = exercise_lookup.get(ex_id)

            if info is None:
                r.violations.append(
                    f"exercise_id {ex_id} no existe en la biblioteca"
                )
                continue

            # 2) Contraindicaciones (doble verificación post-IA)
            contra = set(info.get("contraindications") or [])
            clash = contra & client_contraindications
            if clash:
                r.violations.append(
                    f"'{info.get('canonical_name', ex_id)}' contraindicado para "
                    f"lesión(es): {', '.join(sorted(clash))}"
                )

            # Volumen por grupo (primario cuenta completo)
            group = info.get("muscle_primary", "desconocido")
            weekly_sets_by_group[group] = weekly_sets_by_group.get(group, 0) + sets

            # 3) Incremento de carga máx +10% por recalibración
            if is_recalibration and previous_weights:
                prev = previous_weights.get(ex_id)
                new = ex.get("start_weight_hint_kg")
                if prev and new and prev > 0:
                    inc = (new - prev) / prev
                    if inc > LOAD_INCREMENT_MAX_PCT:
                        r.violations.append(
                            f"'{info.get('canonical_name', ex_id)}': subida de "
                            f"{inc * 100:.0f}% supera el máximo "
                            f"{LOAD_INCREMENT_MAX_PCT * 100:.0f}%"
                        )

        # 4) Duración estimada de la sesión: series×3min + 10. Exceso leve = aviso;
        # exceso holgado (> tolerancia) = violación que bloquea.
        est_min = session_sets * SESSION_MINUTES_FORMULA_PER_SET + SESSION_MINUTES_FIXED_OVERHEAD
        if est_min > session_max_min * (1 + SESSION_MINUTES_TOLERANCE):
            r.violations.append(
                f"sesión '{sess.get('name', '?')}' ~{est_min} min supera el "
                f"máximo declarado {session_max_min} min"
            )
        elif est_min > session_max_min:
            r.warnings.append(
                f"sesión '{sess.get('name', '?')}' ~{est_min} min supera "
                f"ligeramente el máximo declarado {session_max_min} min; revisa y recorta series si quieres"
            )

    # 5) Volumen semanal por grupo: techo (bloquea) y piso (avisa)
    for group, total in weekly_sets_by_group.items():
        if total > SETS_MAX_PER_GROUP_WEEK:
            r.violations.append(
                f"grupo '{group}': {total:.0f} series/semana supera el máximo "
                f"{SETS_MAX_PER_GROUP_WEEK}"
            )
        elif total < SETS_MIN_PER_GROUP_WEEK:
            r.warnings.append(
                f"grupo '{group}': solo {total:.0f} series/semana — por debajo del "
                f"mínimo productivo ({SETS_MIN_PER_GROUP_WEEK}); revisa si es intencionado"
            )
    return r


def filter_exercises_for_client(
    exercises: list[dict],
    *,
    client_contraindications: set[str],
    excluded_ids: set[int],
    equipment_available: set[str],
    level_max: int,
    training_place: str,
) -> list[dict]:
    """Filtro determinista PREVIO a la IA (F.3 / D.2): la IA solo ve ejercicios
    aptos. Reduce contexto y previene contraindicaciones de raíz.

    En 'home'/'outdoor' no se exige equipamiento de gimnasio; en 'gym' se
    requiere que el cliente disponga de TODO el equipamiento del ejercicio.
    """
    out = []
    for ex in exercises:
        if ex.get("archived"):
            continue
        if ex["id"] in excluded_ids:
            continue
        if ex.get("level_min", 1) > level_max:
            continue
        contra = set(ex.get("contraindications") or [])
        if contra & client_contraindications:
            continue
        needed = set(ex.get("equipment") or [])
        if training_place == "gym":
            # En gimnasio se asume equipamiento estándar; solo se exige que el
            # cliente no haya excluido el equipamiento explícitamente.
            if needed and equipment_available and not needed <= equipment_available:
                # permite peso corporal siempre
                if needed != {"peso_corporal"}:
                    continue
        else:
            # casa/exterior: solo lo que el cliente declaró tener (o peso corporal)
            if needed and not needed <= (equipment_available | {"peso_corporal"}):
                continue
        out.append(ex)
    return out
