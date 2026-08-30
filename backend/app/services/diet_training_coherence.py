"""Coherencia dieta ↔ entrenamiento (hardening §6).

Validación DETERMINISTA cruzada entre el bloque de nutrición y el de
entrenamiento — cosas que ninguna validación puntual de un solo bloque detecta:

- Hidratos distribuidos según días de entreno vs. descanso (ciclado si procede).
- Comidas pre/post entreno sobre la HORA REAL declarada, no sobre plantilla.
- Volumen e intensidad acordes a la profundidad del déficit (nada de mesociclo de
  sobrecarga con −25% de kcal).
- Horarios de comida encajados con la jornada y la hora de entreno.

Devuelve `GuardrailReport` (mismos `violations`/`warnings` del resto del sistema)
para poder fusionarlo con los demás guardrails y alimentar el panel/validador.
"""
from __future__ import annotations

import re

from app.services.guardrails import GuardrailReport

# Déficit (fracción sobre TDEE) a partir del cual un mesociclo de SOBRECARGA
# (semana de acumulación de volumen/intensidad alta) es incoherente: el cuerpo
# no recupera. Por encima de este déficit, el entreno debe ser de mantenimiento
# de fuerza, no de sobrecarga.
DEEP_DEFICIT_PCT = 0.20            # −20%: a partir de aquí, nada de sobrecarga
# Volumen semanal por grupo que se considera "de sobrecarga" (alto).
OVERLOAD_SETS_PER_GROUP = 20
# Minutos alrededor del entreno para considerar una comida "peri-entreno".
PERI_WINDOW_MIN = 150


def _to_minutes(hhmm: str | None) -> int | None:
    if not hhmm or ":" not in str(hhmm):
        return None
    try:
        h, m = str(hhmm).split(":")[:2]
        return int(h) * 60 + int(m)
    except (ValueError, TypeError):
        return None


_RE_HORA = re.compile(r"\b([01]?\d|2[0-3])(?::([0-5]\d))?\s*(?:h|hs|horas)?\b")
_RE_RANGO = re.compile(
    r"\b([01]?\d|2[0-3])(?::([0-5]\d))?\s*(?:h|hs)?\s*(?:a|-|–|hasta)\s*"
    r"([01]?\d|2[0-3])(?::([0-5]\d))?\s*(?:h|hs)?")


def _hhmm(h: str, m: str | None) -> str:
    return f"{int(h):02d}:{int(m or 0):02d}"


def horarios_de_las_notas(lifestyle_notes: str | None) -> dict:
    """Saca de las notas de estilo de vida la JORNADA, la hora de ENTRENO y las
    horas de SUEÑO, que es lo que la anamnesis ya recoge en texto.

    Sin esto, tres de las comprobaciones de coherencia de este módulo no se
    ejecutaban NUNCA en producción: existían, tenían tests… y nadie les pasaba
    los datos. Parser deliberadamente CONSERVADOR: solo entiende lo que está
    escrito de forma inequívoca (una hora o un rango en la línea de su tema) y
    ante la duda devuelve nada, que es mejor que un aviso inventado.
    """
    out: dict = {}
    for linea in (lifestyle_notes or "").splitlines():
        limpio = linea.strip().lstrip("-·• ").strip()
        bajo = limpio.lower()
        cuerpo = limpio.split(":", 1)[1] if ":" in limpio else limpio
        if bajo.startswith("trabajo"):
            m = _RE_RANGO.search(cuerpo)
            if m:
                out["workday"] = (_hhmm(m.group(1), m.group(2)),
                                  _hhmm(m.group(3), m.group(4)))
        elif bajo.startswith(("horario de entreno", "hora de entreno", "entreno")):
            m = _RE_HORA.search(cuerpo)
            if m:
                out["training_time"] = _hhmm(m.group(1), m.group(2))
        elif bajo.startswith("sueño") or bajo.startswith("sueno"):
            m = re.search(r"(\d{1,2})(?:[.,](\d))?\s*(?:h|horas)", cuerpo.lower())
            if m:
                horas = float(f"{m.group(1)}.{m.group(2) or 0}")
                if 3 <= horas <= 14:
                    out["sleep_hours"] = horas
    return out


def check_diet_training_coherence(
    nutrition: dict,
    training: dict | None,
    *,
    tdee: float | None = None,
    training_time: str | None = None,
    workday: tuple[str, str] | None = None,   # (entrada, salida) HH:MM
    sleep_hours: float | None = None,
    exercise_lookup: dict[int, dict] | None = None,
) -> GuardrailReport:
    """Coherencia cruzada dieta↔entreno. `training_time` es la hora real de
    entreno declarada; `workday` la jornada laboral (entrada, salida);
    `exercise_lookup` {id: {muscle_primary}} para agrupar el volumen."""
    r = GuardrailReport()
    if not isinstance(nutrition, dict):
        return r

    macros = nutrition.get("macros") or {}
    target = float(nutrition.get("target_kcal") or 0)
    meals = [m for m in (nutrition.get("meals") or []) if isinstance(m, dict)]

    # 1) Volumen/intensidad vs profundidad del déficit
    if training and tdee and target and tdee > 0:
        deficit = (tdee - target) / tdee  # positivo = déficit
        if deficit >= DEEP_DEFICIT_PCT:
            by_group = _weekly_sets_by_group(training, exercise_lookup)
            overloaded = [g for g, n in by_group.items() if n >= OVERLOAD_SETS_PER_GROUP]
            if overloaded:
                r.warnings.append(
                    f"déficit del {deficit*100:.0f}% con volumen de sobrecarga en "
                    f"{', '.join(sorted(overloaded))} ({OVERLOAD_SETS_PER_GROUP}+ series/sem): "
                    "en déficit profundo el entreno debe MANTENER, no sobrecargar."
                )

    # 2) Comidas pre/post sobre la hora real de entreno
    if training_time and meals:
        t = _to_minutes(training_time)
        times = [(_to_minutes(m.get("time")), m) for m in meals if _to_minutes(m.get("time")) is not None]
        if t is not None and times:
            near = [m for mt, m in times if abs(mt - t) <= PERI_WINDOW_MIN]
            if not near:
                r.warnings.append(
                    f"ninguna comida cae cerca de la hora de entreno ({training_time}): "
                    "conviene una toma con hidratos antes o después."
                )

    # 3) Ciclado de hidratos: si el entreno concentra días duros, tiene sentido
    #    que los HC no sean planos. Aviso informativo (no bloqueo) cuando hay
    #    entreno intenso y los HC del plan son bajos.
    if training and macros:
        carbs = float(macros.get("carbs_g") or 0)
        # Señal simple: muchos días de entreno con pocos HC → sugerir ciclado.
        n_sessions = len(training.get("sessions") or [])
        if n_sessions >= 4 and carbs and target and (carbs * 4 / target) < 0.35:
            r.warnings.append(
                f"{n_sessions} días de entreno con hidratos bajos (~{carbs*4/target*100:.0f}% "
                "de las kcal): valora subir HC los días de entreno (ciclado)."
            )

    # 4) Horarios encajados con la jornada y el sueño
    if workday and meals:
        entrada, salida = _to_minutes(workday[0]), _to_minutes(workday[1])
        # El bucle estaba VACÍO (solo un comentario): esta comprobación se
        # quedó sin escribir y nunca avisó de nada. Lo que de verdad importa
        # aquí es cuántas tomas caen DENTRO del turno: son las que el cliente
        # tiene que llevarse preparadas, y si son varias el plan tiene que
        # estar pensado para eso (táper, comida fría, nada de "recién hecho").
        if entrada is not None and salida is not None:
            def _dentro(minuto: int | None) -> bool:
                if minuto is None:
                    return False
                if salida >= entrada:          # turno normal
                    return entrada <= minuto <= salida
                return minuto >= entrada or minuto <= salida   # turno de noche

            en_turno = [m for m in meals if _dentro(_to_minutes(m.get("time")))]
            if len(en_turno) >= 2:
                nombres = ", ".join(str(m.get("name") or f"toma {m.get('slot')}")
                                    for m in en_turno[:3])
                r.warnings.append(
                    f"{len(en_turno)} tomas caen dentro de su jornada ({nombres}): "
                    "tienen que ser transportables (táper/frías), no de preparar "
                    "al momento."
                )
        # sueño: última comida no debería solaparse con la hora de dormir
    if sleep_hours and meals:
        last = max((_to_minutes(m.get("time")) for m in meals
                    if _to_minutes(m.get("time")) is not None), default=None)
        if last is not None and last >= 23 * 60 + 30:
            r.warnings.append(
                "la última comida es muy tardía (≥23:30): puede afectar al descanso; "
                "adelántala si la hora de sueño es temprana."
            )
    return r


def _weekly_sets_by_group(training: dict, lookup: dict[int, dict] | None = None) -> dict[str, float]:
    """Series semanales por grupo primario. Usa `muscle_primary` del ejercicio si
    está en el JSON; si no, lo busca en `lookup` por exercise_id."""
    out: dict[str, float] = {}
    for sess in training.get("sessions") or []:
        for ex in sess.get("exercises") or []:
            group = ex.get("muscle_primary")
            if not group and lookup:
                group = (lookup.get(ex.get("exercise_id")) or {}).get("muscle_primary")
            group = group or "desconocido"
            out[group] = out.get(group, 0) + int(ex.get("sets") or 0)
    return out
