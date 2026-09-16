"""El CONTRATO de volumen y frecuencia por grupo muscular: lo calcula el
BACKEND, no la IA.

Mismo principio que la nutrición (`metrics.energy_targets` → kcal y macros): el
modelo no calcula cuántas series necesita una espalda, se le ENTREGAN. Aquí
salen, a partir del nivel, el objetivo y la prioridad muscular que declare el
coach, tres cifras por grupo —mínimo, objetivo y techo— y la frecuencia mínima,
ya ESCALADAS a la duración del ciclo.

Los landmarks son los de `CRITERIOS_ASESORIA.md` §5, que es el criterio del
coach y no una invención: mínimo productivo ~6 series/semana, techo ~25,
frecuencia ≥2/semana, y por nivel 8-12 / 10-18 / 14-22.

⚠️ TODO lo de fuera piensa en SERIES POR SEMANA (es la unidad en la que está
escrita la literatura y el criterio). Lo que devuelve este módulo son series
POR CICLO: con un ciclo de 10 días, 14 series/semana son 20 series/ciclo. Ese
escalado es justo lo que hace que un ciclo de 10 días no parezca de golpe un
exceso de volumen — y es la cuenta que, hecha a ojo, saldría mal.
"""
from app.services.metrics import _rhu
from app.services.training_cycle import SEMANA, dias_de_ciclo

# Los grupos que llevan objetivo de volumen. El resto de la biblioteca
# (antebrazos, aductores, trapecio, gemelos…) se entrena, pero exigirle un
# mínimo productivo a cada uno llenaría el plan de relleno: no son el motivo
# por el que nadie contrata una asesoría.
GRUPOS_PRINCIPALES = (
    "pecho", "espalda", "hombros", "cuadriceps", "isquios", "gluteos",
    "biceps", "triceps",
)

# Series efectivas por grupo y SEMANA según nivel (mínimo, objetivo, techo).
_POR_NIVEL: dict[str, tuple[int, int, int]] = {
    "beginner": (8, 10, 12),
    "intermediate": (10, 14, 18),
    "advanced": (14, 18, 22),
}
_NIVEL_POR_DEFECTO = "intermediate"

SUELO_SEMANA = 6       # mínimo productivo (criterio del coach)
TECHO_SEMANA = 25      # techo (criterio del coach)
FRECUENCIA_MIN_SEMANA = 2

# Un grupo PRIORIZADO se lleva más estímulo; uno desenfatizado se mantiene, que
# no es lo mismo que abandonarlo: nunca baja del mínimo productivo.
FACTOR_PRIORIDAD = 1.30
FACTOR_SECUNDARIO = 0.70
# En déficit la recuperación es peor: no se persigue el techo. Es el criterio
# del coach ("nada de mesociclo de sobrecarga con −25% de kcal").
FACTOR_DEFICIT = 0.85


def _nivel(level: str | None) -> str:
    return level if level in _POR_NIVEL else _NIVEL_POR_DEFECTO


def por_ciclo(series_semana: float, ciclo: int) -> int:
    """Series por SEMANA → series por CICLO, con el redondeo de siempre."""
    return max(0, _rhu(series_semana * ciclo / SEMANA))


def objetivos_por_grupo(
    *,
    level: str | None,
    goal_type: str | None,
    cycle_days: int,
    priority: list[str] | tuple[str, ...] | None = None,
    deprioritized: list[str] | tuple[str, ...] | None = None,
) -> dict:
    """El contrato: qué volumen y qué frecuencia le toca a cada grupo EN ESTE
    CICLO. Es lo que se le entrega a la IA y lo que después validan los
    guardarraíles — las dos cosas leen de aquí, así que no pueden discrepar."""
    ciclo = max(1, int(cycle_days or SEMANA))
    prio = {str(g).strip().lower() for g in (priority or []) if str(g).strip()}
    baja = {str(g).strip().lower() for g in (deprioritized or []) if str(g).strip()}
    # Un grupo no puede ser prioritario y secundario a la vez: manda la
    # prioridad (es lo que el coach ha pedido de forma explícita).
    baja -= prio
    piso_n, objetivo_n, techo_n = _POR_NIVEL[_nivel(level)]
    en_deficit = goal_type == "fat_loss"

    grupos: dict[str, dict] = {}
    for grupo in GRUPOS_PRINCIPALES:
        if grupo in prio:
            objetivo = objetivo_n * FACTOR_PRIORIDAD
            piso, techo = objetivo_n, TECHO_SEMANA
        elif grupo in baja:
            objetivo = objetivo_n * FACTOR_SECUNDARIO
            piso, techo = SUELO_SEMANA, objetivo_n
        else:
            objetivo, piso, techo = objetivo_n, piso_n, techo_n
        if en_deficit:
            objetivo *= FACTOR_DEFICIT
            techo *= FACTOR_DEFICIT
        # El mínimo productivo no se negocia ni en déficit ni desenfatizando.
        objetivo = max(SUELO_SEMANA, objetivo)
        piso = max(SUELO_SEMANA, min(piso, objetivo))
        techo = max(objetivo, min(TECHO_SEMANA, techo))
        grupos[grupo] = {
            "min": por_ciclo(piso, ciclo),
            "target": por_ciclo(objetivo, ciclo),
            "max": por_ciclo(techo, ciclo),
            "min_frequency": max(1, _rhu(FRECUENCIA_MIN_SEMANA * ciclo / SEMANA)),
            "priority": grupo in prio,
            "deprioritized": grupo in baja,
        }
    return {
        "cycle_days": ciclo,
        "level": _nivel(level),
        "in_deficit": en_deficit,
        "groups": grupos,
        # El techo y el suelo GENERALES, ya por ciclo: es lo que valida el
        # guardarraíl para cualquier grupo, principal o no.
        "floor_per_cycle": por_ciclo(SUELO_SEMANA, ciclo),
        "ceiling_per_cycle": por_ciclo(TECHO_SEMANA, ciclo),
    }


def contrato_de_cliente(client, training: dict | None = None) -> dict:
    """El contrato de ESTE cliente: lee su nivel, su objetivo, su prioridad
    muscular y la duración de su ciclo. Una sola puerta para que la generación,
    los guardarraíles y el panel no calculen cada uno por su cuenta."""
    ciclo = dias_de_ciclo(training) if training is not None else (
        getattr(client, "cycle_days", None) or SEMANA)
    return objetivos_por_grupo(
        level=getattr(client, "level", None),
        goal_type=getattr(client, "goal_type", None),
        cycle_days=ciclo,
        priority=getattr(client, "muscle_priority", None),
        deprioritized=getattr(client, "muscle_deprioritized", None),
    )


def texto_para_prompt(contrato: dict) -> str:
    """El contrato en una línea por grupo, para inyectarlo en el prompt.

    Se nombra la unidad EN CADA LÍNEA ("series/ciclo") a propósito: el modelo
    tiene la literatura de series/semana muy metida y, sin decírselo, devuelve
    volumen de semana en un ciclo de 10 días."""
    ciclo = contrato.get("cycle_days", SEMANA)
    lineas = []
    for grupo, d in (contrato.get("groups") or {}).items():
        marca = " [PRIORITARIO]" if d.get("priority") else (
            " [mantenimiento]" if d.get("deprioritized") else "")
        lineas.append(
            f"- {grupo}: {d['target']} series efectivas por ciclo de {ciclo} días "
            f"(rango {d['min']}-{d['max']}), en ≥{d['min_frequency']} sesiones{marca}"
        )
    return "\n".join(lineas)
