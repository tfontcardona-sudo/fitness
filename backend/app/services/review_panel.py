"""Panel de supervisión (hardening §9) + Índice de Confianza del Plan (§11).

Antes de que salga un plan pasa por un panel de revisores especializados. Cada uno
es INDEPENDIENTE: recibe el texto íntegro de la anamnesis (o del check-in) y el
plan, SIN el razonamiento de la generación y SIN los informes de los demás. La
independencia es lo que da valor a que coincidan; si comparten contexto se anclan
y validan los errores entre ellos.

Composición:
  0 · Validador determinista (código, veto absoluto) — ya existe en guardrails.
  1 · Auditor de anamnesis        2 · Nutricionista sénior
  3 · Preparador físico sénior    4 · Abogado del cliente
  5 · Revisor clínico (veto duro) 6 · Coherencia dieta↔entreno
  7 · Fidelidad al criterio       8 · Editor
  9 · Árbitro (único que ve todos los informes; NO anula los vetos 0 y 5).

Los revisores 1–8 son llamadas a la IA. Aquí el panel recibe un `ai_reviewer`
INYECTABLE (para test/mocks); el adaptador real vive en `make_ai_reviewer`. El
revisor 0 y el ICP son deterministas y viven aquí.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Callable

from app.services import guardrails as gr
from app.services.safety_gate import red_flags, traffic_light


# ------------------------------------------------------------- contrato ----

@dataclass
class ReviewFinding:
    severity: str            # bloqueante | mayor | menor
    description: str
    # Lo que el coach ve de un vistazo: el problema en 3-6 palabras y QUÉ HACER.
    # Vacíos en hallazgos antiguos (el frontend los deriva de `description`).
    title: str = ""
    action: str = ""
    cita_anamnesis: str = ""
    donde_en_el_plan: str = ""
    correccion_propuesta: str = ""


@dataclass
class ReviewerVerdict:
    reviewer: str
    veredicto: str           # aprobado | aprobado_con_reservas | rechazado
    puntuacion_rubrica: int  # 0-100
    hallazgos: list[ReviewFinding] = field(default_factory=list)
    can_veto: bool = False   # True para el 0 (determinista) y el 5 (clínico)


# Roles de los revisores IA (1–8). Cada uno con su rúbrica; el clínico veta.
REVIEWER_ROLES: list[dict] = [
    {"key": "auditor_anamnesis", "name": "Auditor de anamnesis", "can_veto": False,
     "rubric": "Recorre la anamnesis frase a frase de arriba abajo. Por cada "
     "afirmación del cliente indica si el plan la atiende (atendido true/false/"
     "no_aplica), dónde y un comentario. Cualquier 'false' relevante es bloqueante. "
     "Es el filtro que evita el clásico 'el plan está bien pero olvidó que trabaja "
     "a turnos'."},
    {"key": "nutricionista", "name": "Nutricionista sénior", "can_veto": False,
     "rubric": "Reparto y timing de macros, calidad de las elecciones, "
     "micronutrientes de riesgo según perfil (B12, hierro, calcio, vitamina D, "
     "omega-3), digestibilidad, saciedad y sostenibilidad."},
    {"key": "preparador", "name": "Preparador físico sénior", "can_veto": False,
     "rubric": "Volumen, frecuencia, selección y orden de ejercicios, progresión, "
     "gestión de la fatiga y respeto a lesiones."},
    {"key": "abogado_cliente", "name": "Abogado del cliente", "can_veto": False,
     "rubric": "Busca por qué este plan FRACASARÍA. ¿Esta persona, con esta vida, "
     "trabajo, presupuesto e historial, lo sostiene 12 semanas? Si solo funciona "
     "con un cliente perfecto, no funciona."},
    {"key": "clinico", "name": "Revisor clínico", "can_veto": True,
     "rubric": "Veto duro. Patologías, medicación e interacciones, poblaciones "
     "especiales, IMC, señales de TCA (screening tipo SCOFF sobre texto libre). "
     "Ante duda, escala."},
    {"key": "coherencia_dieta_entreno", "name": "Coherencia dieta↔entreno", "can_veto": False,
     "rubric": "Hidratos según días de entreno/descanso, comidas pre/post sobre la "
     "hora real, volumen/intensidad acorde a la profundidad del déficit, horarios "
     "encajados con la jornada."},
    {"key": "fidelidad_criterio", "name": "Fidelidad al criterio", "can_veto": False,
     "rubric": "Contrasta contra CRITERIOS_ASESORIA.md: ¿esto lo firmaría el coach? "
     "Juzga contra SU criterio, no contra la nutrición en general."},
    {"key": "editor", "name": "Editor", "can_veto": False,
     "rubric": "Claridad, estructura, tono, ortografía y coherencia entre los "
     "números y los textos que hablan de esos números."},
]

# En revisiones quincenales se añaden dos (continuidad y tendencia).
CHECKIN_EXTRA_ROLES: list[dict] = [
    {"key": "continuidad", "name": "Continuidad", "can_veto": False,
     "rubric": "¿El cambio es proporcional a los datos o es ruido? ¿El cliente "
     "reconocerá su plan?"},
    {"key": "tendencia", "name": "Tendencia", "can_veto": False,
     "rubric": "Mira el histórico COMPLETO, no solo estos 15 días."},
]


def reviewer_prompt(role: dict, plan_text: str, anamnesis_text: str,
                    criterios_text: str = "") -> str:
    """Prompt AISLADO de un revisor: SOLO la anamnesis y el plan; NUNCA el
    razonamiento de la generación ni los informes de los demás."""
    extra = f"\n\nCRITERIO DEL COACH (referencia):\n{criterios_text}" if criterios_text else ""
    return (
        f"Eres «{role['name']}». Tu rúbrica: {role['rubric']}\n\n"
        "Revisa el PLAN contra la ANAMNESIS del cliente. Devuelve SOLO un JSON "
        "con EXACTAMENTE estas claves: \"veredicto\" "
        "(aprobado|aprobado_con_reservas|rechazado), \"puntuacion_rubrica\" "
        "(entero 0-100) y \"hallazgos\" (lista; cada hallazgo con \"severidad\" "
        "(bloqueante|mayor|menor), \"titulo\", \"accion\", \"descripcion\", "
        "\"cita_anamnesis\", \"donde_en_el_plan\" y \"correccion_propuesta\"). "
        "No inventes datos que no estén en la anamnesis.\n"
        "FORMATO (el coach lo lee en el móvil; TITULO y ACCION es lo único que ve "
        "de un vistazo, el resto va plegado):\n"
        "· \"titulo\": el problema en 3-6 PALABRAS, con el dato concreto. "
        "Ej.: \"Gluten en la toma 1\", \"8 zonas lesionadas sin adaptar\". "
        "Sin frases ni verbos conjugados largos.\n"
        "· \"accion\": lo que el coach debe HACER, 3-6 palabras, empezando por un "
        "verbo en infinitivo. Ej.: \"Cambiar esa comida\", \"Regenerar el entreno\".\n"
        "· \"descripcion\": el detalle, MÁXIMO 20 palabras, sin razonar en voz alta.\n"
        "· \"cita_anamnesis\": la cita literal MÁS CORTA (máx. 12 palabras).\n"
        "· \"donde_en_el_plan\": la ubicación, no una explicación (máx. 8 palabras).\n"
        "· \"correccion_propuesta\": el cómo, máx. 15 palabras.\n"
        "MÁXIMO 6 hallazgos: los que más importen.\n\n"
        f"=== ANAMNESIS ===\n{anamnesis_text}\n\n=== PLAN ===\n{plan_text}{extra}"
    )


# --------------------------------------------- revisor 0 (determinista) ----

def deterministic_reviewer(
    nutrition: dict, profile: dict, *, objective_macros: dict | None = None,
) -> ReviewerVerdict:
    """Revisor 0: envuelve el validador determinista + guardrails + lista roja en
    el contrato del panel. Veto absoluto si hay cualquier violación."""
    report = gr.validate_plan_deterministic(
        nutrition,
        objective_macros=objective_macros,
        allergies=profile.get("food_allergies"),
        dislikes=profile.get("food_dislikes"),
        diet_pattern=profile.get("diet_pattern"),
        meals_expected=profile.get("meals_per_day"),
    )
    # Guardrails clásicos de nutrición (suelos, déficit/superávit) si hay métricas.
    if profile.get("bmr") and profile.get("tdee"):
        report = report.merge(gr.check_nutrition(
            nutrition, sex=profile.get("sex", "male"),
            weight_kg=profile.get("weight_kg", 0),
            bmr=profile["bmr"], tdee=profile["tdee"],
        ))
    hallazgos = [ReviewFinding("bloqueante", v) for v in report.violations]
    hallazgos += [ReviewFinding("menor", w) for w in report.warnings]
    veredicto = "rechazado" if report.violations else (
        "aprobado_con_reservas" if report.warnings else "aprobado")
    score = 0 if report.violations else max(60, 100 - 8 * len(report.warnings))
    return ReviewerVerdict("validador_determinista", veredicto, score, hallazgos, can_veto=True)


# ------------------------------------------------------------------ ICP ----

# Pesos del ICP (§11). Los dos que suelen olvidarse (consenso, estabilidad) son de
# los más informativos.
ICP_WEIGHTS = {
    "deterministic": 0.30,   # binario: si falla, ICP = 0
    "coverage": 0.20,        # % de afirmaciones del cliente atendidas
    "panel_mean": 0.20,      # media de los revisores 2-8
    "consensus": 0.15,       # 100 - dispersión entre revisores independientes
    "extraction": 0.10,      # media de confianza en campos críticos
    "stability": 0.05,       # 2 generaciones con seeds distintas comparadas
}


def _consensus_score(scores: list[float]) -> float:
    if len(scores) < 2:
        return 100.0
    sd = statistics.pstdev(scores)
    return max(0.0, min(100.0, 100.0 - 2.0 * sd))


@dataclass
class IcpResult:
    icp: float
    breakdown: dict


def compute_icp(
    *,
    deterministic_ok: bool,
    coverage_ratio: float,
    panel_scores: list[float],
    extraction_confidence: float | None = None,
    stability: float | None = None,
) -> IcpResult:
    """Índice de Confianza del Plan (0-100). Si el validador determinista falla,
    ICP = 0 (binario). Los factores ausentes (extracción/estabilidad) no penalizan:
    su peso se reparte entre los presentes."""
    if not deterministic_ok:
        return IcpResult(0.0, {"deterministic": 0, "reason": "validador determinista falló"})

    factors = {
        "deterministic": 100.0,
        "coverage": max(0.0, min(100.0, coverage_ratio * 100)),
        "panel_mean": statistics.fmean(panel_scores) if panel_scores else 0.0,
        "consensus": _consensus_score(panel_scores),
    }
    if extraction_confidence is not None:
        factors["extraction"] = max(0.0, min(100.0, extraction_confidence * 100))
    if stability is not None:
        factors["stability"] = max(0.0, min(100.0, stability * 100))

    # Renormaliza los pesos entre los factores presentes.
    total_w = sum(ICP_WEIGHTS[k] for k in factors)
    icp = sum(factors[k] * ICP_WEIGHTS[k] for k in factors) / total_w
    breakdown = {k: round(factors[k], 1) for k in factors}
    breakdown["weights_used"] = {k: ICP_WEIGHTS[k] for k in factors}
    return IcpResult(round(icp, 1), breakdown)


# --------------------------------------------------------------- árbitro ----

@dataclass
class PanelResult:
    color: str                      # verde | ambar | rojo
    icp: float
    verdicts: list[ReviewerVerdict]
    findings: list[ReviewFinding]   # deduplicadas, ordenadas por severidad
    red_flags: list[str]
    vetoed: bool
    # Revisores IA que NO llegaron a ejecutarse (API caída/sin crédito): el
    # coach debe saber que esta revisión está DEGRADADA, no fingirla completa.
    degraded_reviewers: list[str] = field(default_factory=list)

    def blocking(self) -> list[ReviewFinding]:
        return [f for f in self.findings if f.severity == "bloqueante"]


_SEV_ORDER = {"bloqueante": 0, "mayor": 1, "menor": 2}


def _dedupe_findings(verdicts: list[ReviewerVerdict]) -> list[ReviewFinding]:
    seen: dict[str, ReviewFinding] = {}
    for v in verdicts:
        for f in v.hallazgos:
            key = (f.description or "").strip().lower()[:80]
            # conserva la severidad MÁS grave si dos revisores coinciden
            if key not in seen or _SEV_ORDER[f.severity] < _SEV_ORDER[seen[key].severity]:
                seen[key] = f
    return sorted(seen.values(), key=lambda f: _SEV_ORDER.get(f.severity, 9))


def consolidate(
    verdicts: list[ReviewerVerdict], profile: dict, *,
    icp_threshold: int = 80,
) -> PanelResult:
    """Árbitro (revisor 9): consolida, deduplica y decide el color. NO puede anular
    el veto del validador determinista ni el del revisor clínico."""
    findings = _dedupe_findings(verdicts)
    # Veto: cualquier revisor con can_veto que rechace, o un hallazgo bloqueante.
    vetoed = any(v.can_veto and v.veredicto == "rechazado" for v in verdicts)
    has_blocking = any(f.severity == "bloqueante" for f in findings) or vetoed
    reds = red_flags(profile)

    # ICP a partir de los revisores NO deterministas (2-8) para la media del panel.
    # Los "no_ejecutado" (degradados) NO puntúan: ni aprueban ni hunden la media —
    # su ausencia ya pesa vía su hallazgo (mayor si el rol tenía veto).
    panel_scores = [v.puntuacion_rubrica for v in verdicts
                    if v.reviewer != "validador_determinista"
                    and v.veredicto != "no_ejecutado"]
    det_ok = not any(v.reviewer == "validador_determinista" and v.veredicto == "rechazado"
                     for v in verdicts)
    coverage = _coverage_from(verdicts)
    icp = compute_icp(deterministic_ok=det_ok and not has_blocking,
                      coverage_ratio=coverage, panel_scores=panel_scores).icp

    minor = sum(1 for f in findings if f.severity in ("mayor", "menor"))
    color = traffic_light(
        has_deterministic_violation=has_blocking, red=reds, icp=icp,
        minor_findings=minor, icp_threshold=icp_threshold,
    )
    return PanelResult(color=color, icp=icp, verdicts=verdicts, findings=findings,
                       red_flags=[f.code for f in reds], vetoed=vetoed or bool(reds))


def _coverage_from(verdicts: list[ReviewerVerdict]) -> float:
    """Cobertura de anamnesis a partir del auditor (si aportó su ratio) o, en su
    defecto, 1.0 menos una penalización por hallazgos del auditor."""
    aud = next((v for v in verdicts if v.reviewer == "auditor_anamnesis"), None)
    if aud is None:
        return 1.0
    unmet = sum(1 for f in aud.hallazgos if f.severity in ("bloqueante", "mayor"))
    return max(0.0, 1.0 - 0.15 * unmet)


# ------------------------------------------------------------ orquestador ----

MAX_REPAIR_ITERATIONS = 3


@dataclass
class RepairOutcome:
    final: PanelResult
    iterations: int
    escalated: bool          # persiste un bloqueante tras el máximo de iteraciones
    history: list[PanelResult] = field(default_factory=list)


def run_panel_with_repair(
    nutrition: dict,
    profile: dict,
    *,
    repair: Callable[[dict, list[ReviewFinding]], dict],
    objective_macros: dict | None = None,
    ai_reviewer: Callable[[dict], ReviewerVerdict] | None = None,
    is_checkin: bool = False,
    icp_threshold: int = 80,
    max_iterations: int = MAX_REPAIR_ITERATIONS,
) -> RepairOutcome:
    """Bucle de reparación (§9): corre el panel; si hay bloqueantes, los hallazgos
    vuelven al generador (`repair`), que corrige SOLO la parte afectada y devuelve
    el plan nuevo; se vuelve a correr el panel completo. Máximo `max_iterations`;
    si persiste un bloqueante, se ESCALA (no se envía). `repair(plan, findings) ->
    plan_corregido` es inyectable (el generador real o un mock en tests)."""
    history: list[PanelResult] = []
    current = nutrition
    for i in range(1, max_iterations + 1):
        res = run_panel(current, profile, objective_macros=objective_macros,
                        ai_reviewer=ai_reviewer, is_checkin=is_checkin,
                        icp_threshold=icp_threshold)
        history.append(res)
        blocking = res.blocking()
        if not blocking and not res.vetoed:
            return RepairOutcome(res, i, escalated=False, history=history)
        if i == max_iterations:
            return RepairOutcome(res, i, escalated=True, history=history)
        # Los hallazgos vuelven al generador: corrige SOLO lo afectado.
        try:
            current = repair(current, blocking)
        except Exception:  # noqa: BLE001 — si la reparación falla, se escala
            return RepairOutcome(res, i, escalated=True, history=history)
    return RepairOutcome(history[-1], max_iterations, escalated=True, history=history)


def make_ai_reviewer(
    ai_client, plan_text: str, anamnesis_text: str, *, criterios_text: str = "",
) -> Callable[[dict], ReviewerVerdict]:
    """Adaptador real: convierte un rol de revisor en una llamada a la IA con
    contexto AISLADO y salida estructurada. Devuelve un callable para `run_panel`.
    `ai_client` debe exponer `generate_json(model, system, user, schema)` (como
    AIClient). Determinismo: se pide temperatura 0 vía el system prompt del rol."""
    from app.schemas.ai import ReviewerOutput  # schema Pydantic del veredicto
    from app.config import settings

    # AHORRO (prompt caching): el contexto compartido (instrucciones + criterio
    # + anamnesis + plan) es IDÉNTICO para los 8-10 roles del panel y se
    # reenviaba entero en cada llamada. Ahora viaja como bloques de system con
    # cache_control: el primer rol escribe la caché y los demás la leen al 10%.
    # Dos cortes: (criterio+anamnesis) | (plan) — así el bucle de reparación,
    # que solo cambia el PLAN, conserva cacheado el primer tramo.
    extra = (f"\n\nCRITERIO DEL COACH (referencia):\n{criterios_text}"
             if criterios_text else "")
    _instrucciones = (
        SYSTEM_REVIEWER + "\n\n"
        "Revisa el PLAN contra la ANAMNESIS del cliente. Devuelve SOLO un JSON "
        "con EXACTAMENTE estas claves: \"veredicto\" "
        "(aprobado|aprobado_con_reservas|rechazado), \"puntuacion_rubrica\" "
        "(entero 0-100) y \"hallazgos\" (lista; cada hallazgo con \"severidad\" "
        "(bloqueante|mayor|menor), \"titulo\", \"accion\", \"descripcion\", "
        "\"cita_anamnesis\", \"donde_en_el_plan\" y \"correccion_propuesta\"). "
        "No inventes datos que no estén en la anamnesis.\n"
        "FORMATO (el coach lo lee en el móvil; TITULO y ACCION es lo único que ve "
        "de un vistazo, el resto va plegado):\n"
        "· \"titulo\": el problema en 3-6 PALABRAS, con el dato concreto. "
        "Ej.: \"Gluten en la toma 1\", \"8 zonas lesionadas sin adaptar\". "
        "Sin frases ni verbos conjugados largos.\n"
        "· \"accion\": lo que el coach debe HACER, 3-6 palabras, empezando por un "
        "verbo en infinitivo. Ej.: \"Cambiar esa comida\", \"Regenerar el entreno\".\n"
        "· \"descripcion\": el detalle, MÁXIMO 20 palabras, sin razonar en voz alta.\n"
        "· \"cita_anamnesis\": la cita literal MÁS CORTA (máx. 12 palabras).\n"
        "· \"donde_en_el_plan\": la ubicación, no una explicación (máx. 8 palabras).\n"
        "· \"correccion_propuesta\": el cómo, máx. 15 palabras.\n"
        "MÁXIMO 6 hallazgos: los que más importen."
    )
    system_blocks = [
        {"type": "text",
         "text": f"{_instrucciones}{extra}\n\n=== ANAMNESIS ===\n{anamnesis_text}",
         "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": f"=== PLAN ===\n{plan_text}",
         "cache_control": {"type": "ephemeral"}},
    ]

    def reviewer(role: dict) -> ReviewerVerdict:
        out = ai_client.generate_json(
            model=settings.model_light, system=system_blocks,
            user=f"Eres «{role['name']}». Tu rúbrica: {role['rubric']}",
            schema=ReviewerOutput,
            temperature=0,  # §14: cada revisor juzga de forma determinista
            max_tokens=2000,  # JSON de 0-6 hallazgos: techo holgado anti-desbocadas
        )
        hallazgos = [ReviewFinding(
            severity=h.severidad, description=h.descripcion,
            title=(h.titulo or "").strip(), action=(h.accion or "").strip(),
            cita_anamnesis=h.cita_anamnesis or "", donde_en_el_plan=h.donde_en_el_plan or "",
            correccion_propuesta=h.correccion_propuesta or "",
        ) for h in out.hallazgos]
        return ReviewerVerdict(role["key"], out.veredicto, out.puntuacion_rubrica,
                               hallazgos, can_veto=role.get("can_veto", False))

    return reviewer


SYSTEM_REVIEWER = (
    "Eres un revisor experto de planes de nutrición y entrenamiento. Respondes "
    "EXCLUSIVAMENTE con JSON válido conforme al schema. Sé estricto y concreto: "
    "cita la anamnesis literalmente y señala dónde en el plan. No inventes datos."
)


def run_panel(
    nutrition: dict,
    profile: dict,
    *,
    objective_macros: dict | None = None,
    ai_reviewer: Callable[[dict], ReviewerVerdict] | None = None,
    is_checkin: bool = False,
    icp_threshold: int = 80,
) -> PanelResult:
    """Ejecuta el panel. Siempre corre el revisor 0 (determinista). Si se pasa
    `ai_reviewer` (adaptador de IA o mock), corre además los revisores 1–8 con
    CONTEXTO AISLADO y consolida. Sin `ai_reviewer`, el panel es solo el revisor 0
    (útil como puerta determinista mínima)."""
    verdicts: list[ReviewerVerdict] = [
        deterministic_reviewer(nutrition, profile, objective_macros=objective_macros)
    ]
    degraded: list[str] = []
    if ai_reviewer is not None:
        roles = REVIEWER_ROLES + (CHECKIN_EXTRA_ROLES if is_checkin else [])
        for role in roles:
            try:
                verdicts.append(ai_reviewer(role))
            except Exception:  # noqa: BLE001 — un revisor caído no tumba el panel
                # SIN puntuación fabricada: el revisor no se ejecutó. Si era un
                # rol con veto (p. ej. clínico), su ausencia pesa como hallazgo
                # MAYOR (empuja el semáforo a ámbar) — nunca un aprobado ficticio.
                degraded.append(role["key"])
                sev = "mayor" if role.get("can_veto") else "menor"
                verdicts.append(ReviewerVerdict(
                    role["key"], "no_ejecutado", 0,
                    [ReviewFinding(sev, f"revisor {role['key']} NO ejecutado "
                                        "(API no disponible): revisión degradada")],
                    can_veto=False,
                ))
    result = consolidate(verdicts, profile, icp_threshold=icp_threshold)
    result.degraded_reviewers = degraded
    return result
