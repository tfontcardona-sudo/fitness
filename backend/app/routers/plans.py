"""Gestión de planes y períodos por el coach (soporte de Fases 6–7).

Cierra el ciclo de vida para que el portal tenga datos reales:
- POST /api/clients/{id}/plans         crea un plan (borrador) con el contenido
                                       generado (núcleo + banco + educativo).
- POST /api/plans/{id}/publish         publica el plan → cliente pasa a active,
                                       email de bienvenida/nuevo plan (G.5).
- POST /api/clients/{id}/periods       abre un período sobre un plan publicado.
- GET  /api/clients/{id}/plans         lista de planes del cliente (para la app).
- GET  /api/clients/{id}/change-requests  cola de solicitudes de ajuste.

La generación con IA (Fase 3) produce el contenido; aquí se persiste y publica.
El endpoint de creación acepta el contenido ya ensamblado para no acoplar la
publicación a una llamada de IA en vivo (que puede orquestarse aparte).
"""


from datetime import date, datetime, timedelta, timezone

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi import File as FastFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.models import ChangeRequest, Client, FeedbackDoc, Period, Plan
from app.schemas.entities import ChangeRequestOut, PeriodCreateIn
from app.services import email_templates as tpl
from app.services.audit import log_event
from app.services.email_service import EmailService, brand_from_config
from app.services import packages as pkgs

router = APIRouter(tags=["plans"], dependencies=[Depends(get_current_user)])


class PlanCreateIn(BaseModel):
    month_index: int = 1
    nutrition_json: dict | None = None
    training_json: dict | None = None
    education_json: dict | None = None
    guardrail_flags: list[str] | None = None
    generated_by: str | None = None


class PlanOut(BaseModel):
    id: int
    client_id: int
    month_index: int
    version: int
    status: str
    nutrition_json: dict | None
    training_json: dict | None
    education_json: dict | None
    guardrail_flags: list[str] | None
    review_json: dict | None = None  # §9: color/ICP/hallazgos del panel
    goal_type: str | None = None
    published_at: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


from app.services.branding import fila_de_marca


def _client_or_404(db: Session, client_id: int) -> Client:
    c = db.get(Client, client_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    return c


@router.post("/api/clients/{client_id}/plans", response_model=PlanOut,
             status_code=status.HTTP_201_CREATED)
def create_plan(client_id: int, body: PlanCreateIn, db: Session = Depends(get_db)) -> PlanOut:
    _client_or_404(db, client_id)
    # versión siguiente para ese mes
    last = db.scalar(
        select(Plan).where(Plan.client_id == client_id, Plan.month_index == body.month_index)
        .order_by(Plan.version.desc()).limit(1)
    )
    version = (last.version + 1) if last else 1
    client = _client_or_404(db, client_id)
    # MISMA red de coherencia que la edición (PATCH): este endpoint acepta el
    # contenido ya ensamblado y era la única puerta por la que una nutrición
    # descuadrada (totales ≠ macros ≠ comidas) llegaba TAL CUAL a la BD → PDF
    # y portal con tres cifras distintas. Topes sanos + reconciliación siempre.
    if isinstance(body.nutrition_json, dict):
        from app.services.nutrition_scale import reconcile_nutrition

        _sanitize_nutrition(body.nutrition_json)
        reconcile_nutrition(
            body.nutrition_json,
            weight_kg=client.current_weight_kg or client.start_weight_kg,
        )
    plan = Plan(
        client_id=client_id, month_index=body.month_index, version=version,
        status="draft", nutrition_json=body.nutrition_json,
        training_json=body.training_json, education_json=body.education_json,
        guardrail_flags=body.guardrail_flags, generated_by=body.generated_by,
        goal_type=client.goal_type,
    )
    db.add(plan)
    db.flush()
    log_event(db, "plan", plan.id, "plan_created", {"client_id": client_id, "version": version})
    db.commit()
    db.refresh(plan)
    return PlanOut.model_validate(plan)


class PlanUpdateIn(BaseModel):
    """Edición manual del plan por el coach (revisión antes de enviar)."""
    nutrition_json: dict | None = None
    training_json: dict | None = None
    education_json: dict | None = None
    # Control de concurrencia optimista: revisión del plan que el editor tenía
    # abierta. Si no coincide con la actual → 409 (otra pestaña guardó antes).
    base_rev: int | None = None


def _sanitize_nutrition(nut: dict) -> None:
    """Topes sanos (defensa en profundidad): un valor absurdo tecleado en el
    editor —36.000.000 kcal— no debe llegar a la BD ni corromper el PDF."""
    def clamp(v, hi):
        return min(hi, max(0, v)) if isinstance(v, (int, float)) else v

    if "target_kcal" in nut:
        nut["target_kcal"] = clamp(nut.get("target_kcal"), 8000)
    m = nut.get("macros")
    if isinstance(m, dict):
        for k in ("protein_g", "carbs_g", "fat_g"):
            if k in m:
                m[k] = clamp(m.get(k), 800)
    for meal in nut.get("meals") or []:
        t = meal.get("target") if isinstance(meal, dict) else None
        if isinstance(t, dict):
            t["kcal"] = clamp(t.get("kcal"), 8000)
            for k in ("protein_g", "carbs_g", "fat_g"):
                if k in t:
                    t[k] = clamp(t.get(k), 800)


@router.patch("/api/plans/{plan_id}", response_model=PlanOut)
def update_plan(plan_id: int, body: PlanUpdateIn, db: Session = Depends(get_db)) -> PlanOut:
    """Guarda los cambios manuales del coach en el plan (núcleo/comidas/educativo).

    No re-ejecuta los guardrails: son ediciones del coach, que revisa bajo su
    criterio (el principio de seguridad aplica a lo que genera la IA, no a la
    corrección manual). El plan editado queda persistido y descargable.
    """
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    # CONCURRENCIA (auditoría de ediciones): dos pestañas con el editor abierto
    # hacían last-write-wins silencioso (una revertía los macros de la otra y el
    # diff "cambios manuales" registraba la reversión como si fuera del coach), y
    # un PATCH desde una pestaña rancia aterrizaba sobre un plan ya SUSTITUIDO.
    if plan.status == "superseded":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta versión del plan quedó sustituida por otra más nueva: recarga "
            "la pestaña Planificación y edita la versión vigente.")
    changes = body.model_dump(exclude_unset=True)
    base_rev = changes.pop("base_rev", None)
    current_rev = int((plan.nutrition_json or {}).get("rev") or 0) \
        if isinstance(plan.nutrition_json, dict) else 0
    if base_rev is not None and base_rev != current_rev:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El plan cambió desde que abriste el editor (otra pestaña o una "
            "adaptación): recarga para ver la versión actual antes de guardar.")
    # Historial §4: instantánea completa del plan ANTES de mutarlo — el coach
    # puede restaurar cualquier versión desde "Historial" si una edición sale mal.
    if changes:
        from app.services.plan_history import snapshot_plan

        snapshot_plan(plan, "antes de editar")
    # Foto del plan ANTES de aplicar la edición: al final se calcula el diff
    # (determinista) de lo que el coach cambió a mano, para avisar y para el
    # mensaje al cliente ("he ajustado X → Y").
    old_nutrition = dict(plan.nutrition_json) if isinstance(plan.nutrition_json, dict) else None
    old_training = dict(plan.training_json) if isinstance(plan.training_json, dict) else None
    # Para el diff, el "antes" se compara NORMALIZADO igual que el "después":
    # si el plan guardado era legado (sin reconciliar), guardar SIN TOCAR NADA
    # generaba avisos fantasma ("Calorías: 2000 → 2180") que no eran del coach.
    old_for_diff = old_nutrition
    for field, value in changes.items():
        if value is not None:
            # Plan SOLO-ENTRENO (nutrition_json NULL): el editor siempre echa un
            # nutrition_json aunque no haya dieta — un eco vacío (sin comidas ni
            # macros con contenido) NO debe convertir el NULL en dict, porque
            # plan_delivery/plan_doc deciden el formato por bool(nutrition_json)
            # y el PDF pasaría a "plan nutricional" vacío perdiendo el entreno.
            if (field == "nutrition_json" and plan.nutrition_json is None
                    and isinstance(value, dict) and not value.get("meals")):
                continue
            # Simétrico para SOLO-DIETA (training_json NULL): el editor echa un
            # training vacío ({sessions: [], cardio…}) también en la vista de
            # solo nutrición; persistirlo convertía el PDF del cliente en
            # "dieta y entrenamiento" con una sección de entreno vacía.
            if (field == "training_json" and plan.training_json is None
                    and isinstance(value, dict) and not value.get("sessions")):
                continue
            # Red de seguridad: nutrition_json se reemplaza entero; si el editor
            # manda un objeto sin `applied_adjustments` pero el plan lo tenía,
            # se conserva (si no, el portal y el PDF perderían las "Novedades").
            if field == "nutrition_json" and isinstance(value, dict):
                _sanitize_nutrition(value)  # topes sanos (kcal/macros) antes de guardar
                # Coherencia numérica: target_kcal ≡ macros ≡ suma de comidas. El
                # editor ya la mantiene; esto es la red final para que un retoque
                # manual de una comida no deje el plan descuadrado. Idempotente.
                from app.services.nutrition_scale import reconcile_nutrition

                cli = db.get(Client, plan.client_id)
                from app.services.periods import reference_weight_kg
                w = reference_weight_kg(db, cli) if cli else None
                reconcile_nutrition(value, weight_kg=w)
                if isinstance(old_nutrition, dict):
                    import copy

                    old_for_diff = copy.deepcopy(old_nutrition)
                    reconcile_nutrition(old_for_diff, weight_kg=w)
                # Ninguna toma sin contenido: si el coach añadió comidas en el
                # editor, los slots nuevos reciben 3 opciones por defecto
                # escaladas a sus macros (el cliente nunca ve una "toma libre").
                from app.services.meal_fallback import ensure_bank_slots

                ensure_bank_slots(
                    value,
                    allergies=(cli.food_allergies or []) if cli else [],
                    dislikes=(cli.food_dislikes or []) if cli else [],
                    diet_pattern=cli.diet_pattern if cli else None,
                    diet_mode=cli.diet_mode if cli else None,
                )
                # Estructura de comidas: si el coach la cambió en el editor (nº de
                # tomas), la anamnesis del cliente se sincroniza — las próximas
                # regeneraciones/adaptaciones parten de ESTE reparto, no del viejo.
                meals = [m for m in (value.get("meals") or []) if isinstance(m, dict) and m.get("name")]
                if cli is not None and meals:
                    sched = [{"slot": i + 1, "name": m.get("name"), "time": m.get("time") or ""}
                             for i, m in enumerate(meals)]
                    if sched != (cli.meal_schedule or []):
                        cli.meal_schedule = sched
                        cli.meals_per_day = len(sched)
                if ("applied_adjustments" not in value
                        and isinstance(plan.nutrition_json, dict)
                        and plan.nutrition_json.get("applied_adjustments")):
                    value = {**value, "applied_adjustments": plan.nutrition_json["applied_adjustments"]}
            setattr(plan, field, value)
    # Cambios manuales DETECTADOS (diff exacto antes/después). El diff se
    # calcula SIEMPRE (alimenta la auditoría y el aprendizaje §13), pero solo
    # los planes YA ENTREGADOS (published) acumulan manual_changes con su
    # tarjeta "envíaselo actualizado": editar un borrador (la base sin IA del
    # avanzado, o un draft legado) no es modificar lo que el cliente tiene.
    from app.services.plan_diff import manual_change_summary

    diff_items = manual_change_summary(
        db,
        old_nutrition=old_for_diff, new_nutrition=plan.nutrition_json,
        old_training=old_training, new_training=plan.training_json,
    )
    if diff_items and plan.status == "published":
        nut = dict(plan.nutrition_json) if isinstance(plan.nutrition_json, dict) else {}
        # Los pendientes previos viven en el plan ANTES de la edición (el editor
        # no reenvía manual_changes): se acumulan hasta que el coach los envía.
        pending = (old_nutrition or {}).get("manual_changes") or {}
        seen = list(pending.get("items") or [])
        for it in diff_items:
            if it not in seen:
                seen.append(it)
        nut["manual_changes"] = {
            "at": datetime.now(timezone.utc).isoformat(), "items": seen[:20],
        }
        plan.nutrition_json = nut

    log_event(db, "plan", plan.id, "plan_edited",
              {"fields": list(changes.keys()), "diff": diff_items[:20]})

    # §13 (hardening): captura de las ediciones del coach para el aprendizaje
    # continuo. Best-effort con savepoint: si algo falla NUNCA corrompe la edición.
    # SOLO CORRECCIONES (auditoría 28-08): montar a mano una base/copia en
    # borrador es CONSTRUCCIÓN, no una corrección de la IA — aprender de esas
    # tandas contaminaba las lecciones con ruido ("el coach siempre cambia X"
    # cuando estaba escribiendo X por primera vez). En cuanto el plan está
    # activo, sus ediciones sí son correcciones y sí se aprenden.
    from app.services.plan_library import BORRADORES_EN_CONSTRUCCION

    es_construccion = (plan.status == "draft"
                      and plan.generated_by in BORRADORES_EN_CONSTRUCCION)
    if diff_items and not es_construccion:
        try:
            from app.services.continuous_learning import classify_change_text, record_edit

            with db.begin_nested():
                for it in diff_items[:20]:
                    record_edit(db, plan_id=plan.id, category=classify_change_text(it),
                                note=it, commit=False)
        except Exception:  # noqa: BLE001 — captura best-effort
            pass
    # Revisión del plan tras la edición: sube el contador de concurrencia para
    # que otra pestaña con el editor abierto reciba un 409 claro al guardar.
    if isinstance(plan.nutrition_json, dict):
        nj = dict(plan.nutrition_json)
        nj["rev"] = current_rev + 1
        plan.nutrition_json = nj

    # Editar también ACTIVA: si el coach retoca un borrador (legado), el plan
    # queda vigente al guardar — no existe el paso "Publicar". EXCEPCIÓN: la
    # BASE SIN IA del cliente avanzado (generated_by="scaffold") se edita en
    # varias tandas antes de estar lista; activarla al primer guardado enviaría
    # al cliente un plan a medio hacer. Esa se activa SOLO con el botón Activar.
    # …ni la COPIA de la biblioteca ("library") ni el plan IMPORTADO de un
    # documento ajeno ("document"): también se adaptan en varias tandas
    # (cambiar el alérgeno señalado, quitar días…) antes de estar listos.
    if plan.status == "draft" and plan.generated_by not in BORRADORES_EN_CONSTRUCCION:
        from app.services.plan_activation import activate_plan

        # SEGURIDAD (auditoría 28-08): un borrador RETENIDO por los
        # guardarraíles (violación / semáforo ROJO) NO se activa por el mero
        # hecho de guardarlo — el coach pudo tocar UNA celda (o aplicar un
        # Word) sin corregir la violación, y activar avisa al cliente. Al
        # guardar se RE-VALIDA el contenido EDITADO con el Revisor 0:
        # · limpio → los avisos rancios se apagan y el plan se activa;
        # · sigue violando → sigue en borrador con las violaciones ACTUALES.
        # El ROJO del panel §9 es un juicio CUALITATIVO que el Revisor 0 no
        # puede avalar: es PEGAJOSO — solo lo levanta el botón «Activar»
        # explícito (que lo asume y lo deja en auditoría).
        flags_act = [str(f) for f in (plan.guardrail_flags or [])]
        retenia = any(f.startswith(("violation:", "retenido:", "revisión: ROJO"))
                      for f in flags_act)
        if not retenia:
            activate_plan(db, plan)
        else:
            vivas: list[str] = []
            if isinstance(plan.nutrition_json, dict):
                try:
                    from app.services.guardrails import (
                        check_nutrition, validate_plan_deterministic,
                    )

                    _c = db.get(Client, plan.client_id)
                    vivas_rep = check_nutrition(
                        plan.nutrition_json,
                        sex=(_c.sex if _c else None) or "male",
                        weight_kg=float(((_c.current_weight_kg or _c.start_weight_kg or 0)
                                         if _c else 0) or 70.0),
                        bmr=0.0,
                        tdee=float(plan.nutrition_json.get("tdee_kcal") or 0),
                    ).merge(validate_plan_deterministic(
                        plan.nutrition_json,
                        allergies=(_c.food_allergies or []) if _c else [],
                        dislikes=(_c.food_dislikes or []) if _c else [],
                        diet_pattern=_c.diet_pattern if _c else None,
                    ))
                    vivas = [f"violation: {v}" for v in vivas_rep.violations]
                except Exception:  # noqa: BLE001 — ante la duda, conserva la retención
                    vivas = [f for f in flags_act if f.startswith("violation:")]
            else:
                # Retención sin bloque de nutrición (solo-entreno): no hay
                # re-chequeo determinista fiable — la activa el botón Activar.
                vivas = [f for f in flags_act if f.startswith("violation:")] or [
                    "violation: retenido sin re-chequeo automático"]
            rojo = [f for f in flags_act if f.startswith("revisión: ROJO")]
            resto = [f for f in flags_act
                     if not f.startswith(("violation:", "retenido:", "revisión: ROJO"))]
            if vivas or rojo:
                plan.guardrail_flags = resto + rojo + vivas + [
                    "retenido: sigue en BORRADOR — corrige lo señalado o pulsa "
                    "«Activar» si lo decides tú (el cliente no ha sido avisado)"]
            else:
                # La edición corrigió lo que retenía: fuera avisos rancios.
                plan.guardrail_flags = resto or None
                activate_plan(db, plan)
    db.commit()
    db.refresh(plan)
    return PlanOut.model_validate(plan)


class PlanRevertIn(BaseModel):
    """Restauración de una versión del historial. `index` viene de
    GET /api/plans/{id}/history."""

    index: int


@router.get("/api/plans/{plan_id}/history")
def plan_history(plan_id: int, db: Session = Depends(get_db)) -> list[dict]:
    """Historial de versiones del plan (§4): metadatos + resumen de cada
    instantánea guardada antes de cada edición/restauración."""
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    from app.services.plan_history import list_history

    return list_history(plan)


@router.post("/api/plans/{plan_id}/revert", response_model=PlanOut)
def revert_plan(plan_id: int, body: PlanRevertIn, db: Session = Depends(get_db)) -> PlanOut:
    """Restaura una versión del historial (§4). El estado ACTUAL se snapshotea
    antes, así el revert también es reversible. Sube `rev` (concurrencia): una
    pestaña con el editor abierto recibirá su 409 al guardar."""
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    if plan.status == "superseded":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta versión del plan quedó sustituida: restaura desde la versión vigente.")
    from app.services.plan_history import get_version, snapshot_plan

    version = get_version(plan, body.index)
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versión del historial no encontrada")

    current_rev = int((plan.nutrition_json or {}).get("rev") or 0) \
        if isinstance(plan.nutrition_json, dict) else 0
    snapshot_plan(plan, "antes de restaurar")

    plan.nutrition_json = version.get("nutrition_json")
    plan.training_json = version.get("training_json")
    plan.education_json = version.get("education_json")
    if isinstance(plan.nutrition_json, dict):
        nj = dict(plan.nutrition_json)
        nj["rev"] = current_rev + 1
        plan.nutrition_json = nj
    log_event(db, "plan", plan.id, "plan_reverted",
              {"index": body.index, "snapshot_at": version.get("at")})
    db.commit()
    db.refresh(plan)
    return PlanOut.model_validate(plan)


def _plan_ligero(p: Plan) -> Plan:
    """Copia del plan con los JSON GORDOS recortados a lo que pintan las
    pantallas de solo lectura (la línea "Dieta" del resumen, el sello de la
    adaptación). Un cliente veterano tiene 12-20 versiones, cada una con su
    banco de 4×7 recetas con ingredientes, el educativo y los hallazgos del
    panel: devolverlo entero DOS veces al abrir cada ficha eran varios MB."""
    nut = p.nutrition_json or None
    if nut:
        comidas = nut.get("meals") or []
        nut = {
            "target_kcal": nut.get("target_kcal"), "tdee_kcal": nut.get("tdee_kcal"),
            "macros": nut.get("macros"), "rev": nut.get("rev"),
            "applied_adjustments": nut.get("applied_adjustments"),
            "meals": [{"slot": m.get("slot"), "name": m.get("name"),
                       "time": m.get("time")} for m in comidas if isinstance(m, dict)],
        }
    tr = p.training_json or None
    if tr:
        sesiones = tr.get("sessions") or []
        tr = {
            "split_name": tr.get("split_name"),
            "applied_adjustments": tr.get("applied_adjustments"),
            "sessions": [{"day": x.get("day"), "name": x.get("name")}
                         for x in sesiones if isinstance(x, dict)],
        }
    # Objeto SUELTO (no la fila de la sesión): recortar el dict del ORM haría
    # que SQLAlchemy persistiera el recorte en el siguiente flush.
    return Plan(
        id=p.id, client_id=p.client_id, month_index=p.month_index, version=p.version,
        status=p.status, goal_type=p.goal_type, generated_by=p.generated_by,
        nutrition_json=nut, training_json=tr, education_json=None,
        guardrail_flags=p.guardrail_flags, review_json=None,
        created_at=p.created_at, published_at=p.published_at,
    )


@router.get("/api/clients/{client_id}/plans", response_model=list[PlanOut])
def list_plans(client_id: int, todo: bool = False,
               db: Session = Depends(get_db)) -> list[PlanOut]:
    """Planes del cliente, del más reciente al más antiguo.

    Dos modos:

    · por defecto — recortados MENOS los dos que el panel puede llegar a
      pintar: el plan vigente (publicado) y el borrador más nuevo. El resto de
      versiones históricas no se pintan nunca enteras, y arrastraban su banco
      de recetas, su educativo y los hallazgos del panel de supervisión en cada
      recarga (medido: 55 KB con 3 versiones; un cliente de medio año tiene
      12-20 y son cientos de KB, y el panel lo repide tras CADA acción).
    · `todo=true` — todos completos, tal cual estaban. Para quien de verdad
      necesite el histórico entero (importar/exportar, depurar).

    Para pintar UNA LÍNEA por versión (el archivo de planificaciones
    anteriores, el chip de dieta, el selector) está el endpoint de RESUMEN de
    aquí abajo, que ni siquiera devuelve los JSONB. Al fusionar las dos
    sesiones que atacaron esto se quedó ese resumen y se retiró el parámetro
    `ligero`, que hacía el mismo recorte a medias y sin ningún consumidor.
    """
    _client_or_404(db, client_id)
    plans = db.scalars(
        select(Plan).where(Plan.client_id == client_id)
        .order_by(Plan.month_index.desc(), Plan.version.desc())
    ).all()
    if todo:
        return [PlanOut.model_validate(p) for p in plans]
    # Los que el panel SÍ pinta enteros: el publicado y el borrador más nuevo
    # (la banda de "borrador retenido" lo enseña y permite activarlo).
    completos = {p.id for p in plans if p.status == "published"}
    borrador = next((p for p in sorted(plans, key=lambda x: x.id, reverse=True)
                     if p.status == "draft"), None)
    if borrador is not None:
        completos.add(borrador.id)
    if not completos and plans:  # sin publicado ni borrador: el más nuevo
        completos.add(max(plans, key=lambda x: x.id).id)
    return [PlanOut.model_validate(p if p.id in completos else _plan_ligero(p))
            for p in plans]


class PlanSummaryOut(BaseModel):
    """Una versión del plan EN UNA LÍNEA: lo justo para el archivo de
    "Planificaciones anteriores", el chip de dieta de la ficha y el selector.

    El panel pedía la lista COMPLETA (los cuatro JSONB de cada versión) en el
    montaje y otra vez tras cada acción, para pintar cuatro cifras por versión:
    un cliente con un año de asesoría arrastraba megas por cada clic. El plan
    que se EDITA se pide entero y aparte (`GET /api/plans/{id}`)."""

    id: int
    client_id: int
    month_index: int
    version: int
    status: str
    goal_type: str | None = None
    generated_by: str | None = None
    guardrail_flags: list[str] | None = None
    published_at: datetime | None = None
    created_at: datetime | None = None
    # Resumen de la dieta (sin el banco de comidas, que es lo que pesa)
    target_kcal: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    meals_count: int | None = None
    # Resumen del entrenamiento
    split_name: str | None = None
    sessions_count: int | None = None
    # Por qué cambió esta versión
    applied_adjustments: dict | None = None
    rationale: str | None = None
    has_nutrition: bool = False
    has_training: bool = False


def _plan_summary(row) -> PlanSummaryOut:
    """Construye el resumen desde (Plan.id, client_id, …, nutrition_json,
    training_json): recibe la fila tal cual la devuelve la consulta acotada."""
    nut = row.nutrition_json or {}
    tr = row.training_json or {}
    macros = nut.get("macros") or {}
    aj = nut.get("applied_adjustments") or tr.get("applied_adjustments") or None
    meals = nut.get("meals")
    sesiones = tr.get("sessions")
    return PlanSummaryOut(
        id=row.id, client_id=row.client_id, month_index=row.month_index,
        version=row.version, status=row.status, goal_type=row.goal_type,
        generated_by=row.generated_by, guardrail_flags=row.guardrail_flags, published_at=row.published_at,
        created_at=row.created_at,
        target_kcal=nut.get("target_kcal"),
        protein_g=macros.get("protein_g"), carbs_g=macros.get("carbs_g"),
        fat_g=macros.get("fat_g"),
        meals_count=len(meals) if isinstance(meals, list) else None,
        split_name=tr.get("split_name"),
        sessions_count=len(sesiones) if isinstance(sesiones, list) else None,
        applied_adjustments=aj if isinstance(aj, dict) else None,
        rationale=nut.get("rationale") or tr.get("rationale"),
        has_nutrition=bool(nut), has_training=bool(tr),
    )


@router.get("/api/clients/{client_id}/plans/summary", response_model=list[PlanSummaryOut])
def list_plan_summaries(client_id: int, db: Session = Depends(get_db)) -> list[PlanSummaryOut]:
    """Todas las versiones del plan, resumidas. Mismo orden que la lista completa."""
    _client_or_404(db, client_id)
    filas = db.execute(
        select(Plan.id, Plan.client_id, Plan.month_index, Plan.version, Plan.status,
               Plan.goal_type, Plan.generated_by, Plan.guardrail_flags,
               Plan.published_at, Plan.created_at,
               Plan.nutrition_json, Plan.training_json)
        .where(Plan.client_id == client_id)
        .order_by(Plan.month_index.desc(), Plan.version.desc())
    ).all()
    return [_plan_summary(f) for f in filas]


@router.get("/api/plans/{plan_id}", response_model=PlanOut)
def get_plan(plan_id: int, db: Session = Depends(get_db)) -> PlanOut:
    """Una versión CONCRETA con todo su contenido (la que el panel enseña y edita)."""
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    return PlanOut.model_validate(plan)


@router.post("/api/plans/{plan_id}/discard", response_model=PlanOut)
def discard_plan(plan_id: int, db: Session = Depends(get_db)) -> PlanOut:
    """Descarta un BORRADOR (copia equivocada, base que no va a usarse).

    Solo borradores: un plan publicado no se descarta (se sustituye activando
    otro). Así una copia con avisos no se queda parpadeando para siempre sin
    salida. No borra la fila (el historial es historia): pasa a `superseded`,
    que es exactamente "versión que no rige"."""
    from app.services.audit import log_event

    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    if plan.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Solo se descartan borradores. Para cambiar el plan "
                            "activo, activa otro en su lugar.")
    plan.status = "superseded"
    log_event(db, "plan", plan.id, "plan_discarded",
              {"client_id": plan.client_id, "version": plan.version})
    db.commit()
    db.refresh(plan)
    return PlanOut.model_validate(plan)


@router.post("/api/plans/{plan_id}/publish", response_model=PlanOut)
def publish_plan(plan_id: int, db: Session = Depends(get_db)) -> PlanOut:
    """LEGADO: activa un borrador antiguo. Los planes nuevos quedan ACTIVOS
    al generarse o adaptarse (services/plan_activation) — sin paso de publicar."""
    from app.services.plan_activation import activate_plan

    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    # IDEMPOTENTE: re-pulsar Activar sobre un plan ya activo no reenvía email ni
    # push al cliente. Y una versión SUSTITUIDA no puede resucitarse desde aquí
    # (pisaría a la vigente sin querer): para eso está el historial/revert.
    if plan.status == "published":
        return PlanOut.model_validate(plan)
    if plan.status == "superseded":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta versión fue sustituida por otra más nueva: usa el historial "
            "si quieres restaurarla.")
    # Activar EXPLÍCITO sobre un plan retenido = decisión del coach: la
    # retención se apaga (dejarla encendida mantenía la banda roja «retenido»
    # para siempre sobre un plan que él ya asumió). Queda en la auditoría.
    flags_pub = [str(f) for f in (plan.guardrail_flags or [])]
    asumidas = [f for f in flags_pub
                if f.startswith(("violation:", "retenido:", "revisión: ROJO"))]
    if asumidas:
        plan.guardrail_flags = [f for f in flags_pub if f not in asumidas] or None
        log_event(db, "plan", plan.id, "plan_activated_with_override",
                  {"asumidas": asumidas[:10]})
    activate_plan(db, plan)
    db.commit()
    db.refresh(plan)
    return PlanOut.model_validate(plan)


@router.post("/api/plans/{plan_id}/generate-education", response_model=PlanOut)
def generate_education(plan_id: int, db: Session = Depends(get_db)) -> PlanOut:
    """Regenera SOLO el contenido educativo de un plan (modelo ligero + caché).

    El educativo es complementario: si falló al generar (quedó el aviso "no se
    pudo generar el contenido educativo"), antes tocaba regenerar el plan
    ENTERO — repagando núcleo, comidas y panel — para recuperarlo."""
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    if not plan.training_json:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "El contenido educativo acompaña al entrenamiento: este plan no lo incluye.")

    from types import SimpleNamespace

    from app.services.ai.client import AIClient, AIGenerationError
    from app.services.ai.generator import (
        _education_user_prompt,
        _education_user_prompt_training,
        _education_with_cache,
    )

    split = (plan.training_json or {}).get("split_name") or ""
    tr_ns = SimpleNamespace(split_name=split)
    # Las RESTRICCIONES del cliente viajan en el prompt (y por eso separan la
    # caché): sin ellas, este atajo devolvía el educativo genérico del split y
    # a un alérgico o a un vegano le llegaban píldoras y FAQ con sus alimentos
    # vetados — el documento las filtra al imprimir, así que además se quedaba
    # con menos contenido del que ha pagado.
    cliente = db.get(Client, plan.client_id) if plan.client_id else None
    ctx_rest = SimpleNamespace(
        diet_pattern=getattr(cliente, "diet_pattern", None),
        food_allergies=list(getattr(cliente, "food_allergies", None) or []),
    )
    try:
        if plan.nutrition_json:
            edu = _education_with_cache(
                AIClient(), split_name=split, variant="full",
                user=_education_user_prompt(SimpleNamespace(training=tr_ns), ctx_rest))
        else:
            edu = _education_with_cache(
                AIClient(), split_name=split, variant="train",
                user=_education_user_prompt_training(tr_ns))
    except AIGenerationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    plan.education_json = edu.model_dump()
    # El aviso de la generación ya no aplica: el educativo existe.
    flags_e = [f for f in (plan.guardrail_flags or [])
               if "no se pudo generar el contenido educativo" not in str(f)]
    plan.guardrail_flags = flags_e or None
    log_event(db, "plan", plan.id, "education_generated", {})
    db.commit()
    db.refresh(plan)
    return PlanOut.model_validate(plan)


@router.post("/api/clients/{client_id}/periods", response_model=dict,
             status_code=status.HTTP_201_CREATED)
def create_period(client_id: int, body: PeriodCreateIn, db: Session = Depends(get_db)) -> dict:
    _client_or_404(db, client_id)
    plan = db.get(Plan, body.plan_id)
    if not plan or plan.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado para este cliente")
    if plan.status != "published":
        raise HTTPException(status.HTTP_409_CONFLICT, "El plan debe estar publicado")

    # Invariante: un solo período NO analizado por cliente. La publicación del
    # plan ya abre el primer período sola. Este endpoint es IDEMPOTENTE:
    # - si ya hay uno ABIERTO, lo devuelve (no inserta un duplicado que violaría
    #   uq_period_one_open y daría un 500);
    # - si hay uno CERRADO (revisión entregada, feedback pendiente), NO abre otro
    #   —dejaría dos períodos sin analizar y "huérfano" el cierre sin feedback—:
    #   responde 409 para que el coach genere el feedback primero.
    pending = db.scalar(
        select(Period).where(Period.client_id == client_id, Period.status.in_(("open", "closed")))
        .order_by(Period.period_index.desc()).limit(1)
    )
    if pending is not None:
        if pending.status == "open":
            return {"period_id": pending.id, "period_index": pending.period_index,
                    "starts_on": pending.starts_on.isoformat(),
                    "ends_on": pending.ends_on.isoformat()}
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Hay una revisión pendiente de feedback: genera el feedback antes de abrir un período nuevo",
        )

    last = db.scalar(
        select(Period).where(Period.client_id == client_id)
        .order_by(Period.period_index.desc()).limit(1)
    )
    period_index = (last.period_index + 1) if last else 1
    period = Period(
        client_id=client_id, plan_id=plan.id, period_index=period_index,
        starts_on=body.starts_on, ends_on=body.starts_on + timedelta(days=body.days - 1),
        status="open",
    )
    # Savepoint + captura de IntegrityError por si dos peticiones corren a la vez
    # (doble clic): una gana y la otra reutiliza el período abierto que quedó.
    try:
        with db.begin_nested():
            db.add(period)
            db.flush()
    except IntegrityError:
        existing = db.scalar(
            select(Period).where(Period.client_id == client_id, Period.status == "open")
            .order_by(Period.period_index.desc()).limit(1)
        )
        if existing is None:
            raise
        return {"period_id": existing.id, "period_index": existing.period_index,
                "starts_on": existing.starts_on.isoformat(),
                "ends_on": existing.ends_on.isoformat()}
    log_event(db, "period", period.id, "period_opened", {"index": period_index})
    db.commit()
    return {"period_id": period.id, "period_index": period_index,
            "starts_on": period.starts_on.isoformat(), "ends_on": period.ends_on.isoformat()}


@router.get("/api/clients/{client_id}/change-requests", response_model=list[ChangeRequestOut])
def list_change_requests(client_id: int, db: Session = Depends(get_db)) -> list[ChangeRequestOut]:
    _client_or_404(db, client_id)
    crs = db.scalars(
        select(ChangeRequest).where(ChangeRequest.client_id == client_id)
        .order_by(ChangeRequest.created_at.desc())
    ).all()
    return [ChangeRequestOut.model_validate(c) for c in crs]


@router.post("/api/change-requests/{cr_id}/resolve", response_model=ChangeRequestOut)
def resolve_change_request(cr_id: int, db: Session = Depends(get_db)) -> ChangeRequestOut:
    from datetime import datetime, timezone

    cr = db.get(ChangeRequest, cr_id)
    if not cr:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada")
    cr.status = "resolved"
    cr.resolved_at = datetime.now(timezone.utc)
    log_event(db, "client", cr.client_id, "change_request_resolved", {"id": cr.id})
    db.commit()
    db.refresh(cr)
    return ChangeRequestOut.model_validate(cr)


# ------------------------------------------------------- feedback (cierre → informe) ----

class PeriodOut(BaseModel):
    id: int
    plan_id: int | None = None
    period_index: int
    starts_on: date
    ends_on: date
    status: str
    closing_weight_kg: float | None = None
    closing_rating: int | None = None
    closing_hardest: str | None = None
    closing_questions: str | None = None
    closing_waist_cm: float | None = None
    closing_hip_cm: float | None = None
    closing_arm_cm: float | None = None
    closing_thigh_cm: float | None = None
    feedback_id: int | None = None
    # Ajustes propuestos por el feedback IA de esta revisión (área/cambio/motivo):
    # la pestaña Planificación los muestra ANTES de pulsar "Adaptar".
    plan_adjustments: list[dict] | None = None
    # Decisión de la revisión automática (§8): la tarjeta "Adaptar" debe salir
    # aunque la IA no propusiera ajustes de texto (p. ej. solo un diet break).
    biweekly_decision: dict | None = None

    model_config = {"from_attributes": True}


@router.get("/api/clients/{client_id}/periods", response_model=list[PeriodOut])
def list_periods(client_id: int, db: Session = Depends(get_db)) -> list[PeriodOut]:
    """Períodos del cliente (con datos de cierre) + si ya tienen feedback."""
    _client_or_404(db, client_id)
    periods = db.scalars(
        select(Period).where(Period.client_id == client_id)
        .order_by(Period.period_index.desc())
    ).all()
    # El feedback de CADA revisión en UNA consulta: antes era una por período
    # (con 8 revisiones, 9 viajes a la base para pintar una lista que el panel
    # recarga tras cada acción). Se queda el de id más alto, igual que antes.
    from sqlalchemy import func as _func

    ids = [p.id for p in periods]
    ultimo_fb = dict(db.execute(
        select(FeedbackDoc.period_id, _func.max(FeedbackDoc.id))
        .where(FeedbackDoc.period_id.in_(ids))
        .group_by(FeedbackDoc.period_id)
    ).all()) if ids else {}
    out = []
    for p in periods:
        po = PeriodOut.model_validate(p)
        po.feedback_id = ultimo_fb.get(p.id)
        po.plan_adjustments = (p.ai_analysis_json or {}).get("plan_adjustments") or None
        po.biweekly_decision = (p.ai_analysis_json or {}).get("biweekly_decision") or None
        out.append(po)
    return out


class CoachCloseIn(BaseModel):
    """Cierre de la revisión hecho POR EL COACH (el cliente no la envió)."""
    closing_weight_kg: float | None = None
    note: str | None = None


@router.post("/api/periods/{period_id}/close-by-coach")
def close_period_by_coach(period_id: int, body: CoachCloseIn | None = None,
                          db: Session = Depends(get_db)) -> dict:
    """Cierra el período SIN esperar al cliente.

    El ciclo se bloqueaba entero cuando el cliente no pulsaba "enviar revisión":
    sin cierre no hay feedback, sin feedback no hay adaptación ni período nuevo,
    y el coach solo podía insistirle (auditoría de calidad). Con esto el coach
    lo desbloquea: el peso final se toma del último pesaje del diario si no se
    indica otro, y el resto de datos del cierre quedan vacíos (el feedback los
    trata como ausentes, igual que un cierre incompleto del cliente).
    """
    from app.services.portal import today_local

    period = db.get(Period, period_id)
    if period is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Período no encontrado")
    if period.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "El período ya está cerrado")
    today = today_local()
    if today < period.ends_on:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"El período termina el {period.ends_on.strftime('%d/%m')}: espera a esa fecha "
            "para cerrarlo tú.",
        )

    client = db.get(Client, period.client_id)
    peso = body.closing_weight_kg if body else None
    if peso is None:
        from app.models import DailyLog

        peso = db.scalar(
            select(DailyLog.weight_kg)
            .where(DailyLog.period_id == period.id, DailyLog.weight_kg.is_not(None))
            .order_by(DailyLog.log_date.desc()).limit(1)
        )
    if peso is None and client is not None:
        peso = client.current_weight_kg or client.start_weight_kg
    if peso is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No hay ningún peso registrado en esta quincena: indica tú el peso final "
            "para poder cerrarla.",
        )

    period.closing_weight_kg = float(peso)
    period.status = "closed"
    period.closing_submitted_at = datetime.now(timezone.utc)
    # Cerrado por el coach: no arrancamos el recordatorio de fotos al cliente
    # (no ha enviado nada) — el feedback se genera con lo que haya.
    period.photos_confirmed = True
    if body is not None and (body.note or "").strip():
        period.closing_hardest = body.note.strip()
    if client is not None and client.status in ("active", "at_risk", "inactive"):
        client.status = "review_pending"
    log_event(db, "period", period.id, "period_closed_by_coach",
              {"period_index": period.period_index, "closing_weight_kg": float(peso)})
    db.commit()
    return {"closed": True, "period_index": period.period_index,
            "closing_weight_kg": float(peso)}


@router.get("/api/periods/{period_id}/metrics")
def period_metrics(period_id: int, db: Session = Depends(get_db)) -> dict:
    """Resumen de métricas del período (sin IA): peso, adherencia, fuerza, objetivo."""
    from app.services.feedback_service import FeedbackError, compute_period_summary

    if not db.get(Period, period_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Período no encontrado")
    try:
        return compute_period_summary(db, period_id)
    except FeedbackError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.post("/api/periods/{period_id}/feedback")
def generate_feedback(period_id: int, db: Session = Depends(get_db)) -> dict:
    """Genera (con IA) el feedback del período cerrado y lo persiste."""
    from app.services.feedback_service import FeedbackError, build_period_feedback

    period = db.get(Period, period_id)
    if not period:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Período no encontrado")
    try:
        fb = build_period_feedback(db, period_id)
    except FeedbackError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(exc)},
        ) from exc
    return {
        "feedback_id": fb.id, "period_id": period_id,
        "kind": fb.kind, "content": fb.content_json,
    }


@router.get("/api/feedback/{doc_id}")
def get_feedback(doc_id: int, db: Session = Depends(get_db)) -> dict:
    """Contenido del feedback (para mostrarlo en la pestaña del coach)."""
    fb = db.get(FeedbackDoc, doc_id)
    if not fb:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feedback no encontrado")
    return {
        "id": fb.id, "period_id": fb.period_id, "kind": fb.kind,
        "content": fb.content_json,
        "sent_at": fb.sent_at.isoformat() if fb.sent_at else None,
    }


class FeedbackEditIn(BaseModel):
    """Edición manual del feedback por el coach (texto + ajustes del plan)."""
    natural_analysis: str | None = None
    changes_bullets: list[str] | None = None
    answers: str | None = None
    next_objectives: list[str] | None = None
    closing_message: str | None = None
    # La cuadrícula que "Adaptar planificación" aplica NUMÉRICAMENTE al plan:
    # el coach debe poder corregirla ANTES de adaptar (no después, a mano).
    plan_adjustments: list[dict] | None = None


@router.patch("/api/feedback/{doc_id}")
def edit_feedback(doc_id: int, body: FeedbackEditIn, db: Session = Depends(get_db)) -> dict:
    """Guarda los cambios del coach en el texto del feedback y regenera el Word.
    Si ya estaba enviado, el cliente verá la versión editada en su Progreso."""
    from app.services.feedback_service import FeedbackError, update_feedback_text

    fb0 = db.get(FeedbackDoc, doc_id)
    if not fb0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feedback no encontrado")
    old_adjust = list((fb0.content_json or {}).get("plan_adjustments") or [])
    try:
        fb = update_feedback_text(db, doc_id, body.model_dump(exclude_unset=True))
    except FeedbackError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    # §13: corregir los AJUSTES que propuso la IA es una lección de primera
    # (la cuadrícula que "Adaptar" aplica al plan estaba mal) — antes esta
    # corrección no se registraba y el aprendizaje nunca la veía.
    if body.plan_adjustments is not None and body.plan_adjustments != old_adjust:
        try:
            from app.services.continuous_learning import classify_change_text, record_edit

            period = db.get(Period, fb.period_id)
            plan = db.scalar(
                select(Plan).where(Plan.client_id == period.client_id)
                .order_by(Plan.month_index.desc(), Plan.version.desc()).limit(1)
            ) if period else None
            if plan is not None:
                nuevos = "; ".join(
                    f"[{a.get('area')}] {a.get('change')}" for a in body.plan_adjustments)
                with db.begin_nested():
                    record_edit(
                        db, plan_id=plan.id,
                        category=classify_change_text(nuevos),
                        field_path="feedback.plan_adjustments",
                        before=old_adjust, after=body.plan_adjustments,
                        note="el coach corrigió los ajustes propuestos por la "
                             "revisión: " + (nuevos or "los dejó vacíos"),
                        commit=False,
                    )
                db.commit()
        except Exception:  # noqa: BLE001 — el aprendizaje nunca rompe la edición
            pass
    return {
        "id": fb.id, "content": fb.content_json,
        "sent_at": fb.sent_at.isoformat() if fb.sent_at else None,
    }


def _advance_cycle_after_feedback(db: Session, fb: FeedbackDoc) -> Client | None:
    """Marca el feedback como enviado y avanza el ciclo de la asesoría
    (review_pending → active + abre el siguiente período). NO envía email ni
    hace commit: eso lo decide cada endpoint (WhatsApp vs email)."""
    from datetime import datetime, timezone

    fb.sent_at = datetime.now(timezone.utc)
    period = db.get(Period, fb.period_id)
    # El "!" de "revisión recibida" se apagaba SOLO al abrir la pestaña
    # Seguimiento: el coach podía generar el informe, enviárselo al cliente y
    # seguir con la marca encendida en su lista. Enviar la revisión ES haberla
    # atendido.
    if period is not None and period.coach_reviewed_at is None:
        period.coach_reviewed_at = datetime.now(timezone.utc)
    client = db.get(Client, period.client_id) if period else None
    if client and client.status == "review_pending":
        client.status = "active"  # cerrado el feedback, arranca el siguiente ciclo
        # El nuevo período de 14 días empieza HOY (día del envío), no cuando
        # alguien vuelva a abrir el portal: el ciclo queda determinista.
        from app.services.periods import ensure_open_period
        ensure_open_period(db, client.id)
    if client:
        log_event(db, "client", client.id, "feedback_sent", {"feedback_id": fb.id})
    return client


def _first_name_of(client: Client) -> str:
    return ((client.full_name or "").split() or [(client.email or "cliente").split("@")[0]])[0]


@router.post("/api/feedback/{doc_id}/send")
def send_feedback(doc_id: int, db: Session = Depends(get_db)) -> dict:
    """Envía el feedback al cliente: lo hace visible en su portal (Progreso),
    avanza el ciclo (review_pending → active, cierra la notificación) y le avisa
    por email. Hasta este punto el feedback es un borrador que solo ve el coach."""
    fb = db.get(FeedbackDoc, doc_id)
    if not fb:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feedback no encontrado")
    client = _advance_cycle_after_feedback(db, fb)

    if client:
        # Aviso al cliente (si los emails están activos)
        try:
            brand = brand_from_config(db)
            portal_url = f"{settings.public_base_url}/p/{client.portal_token}"
            subject, html = tpl.feedback_ready(
                brand, _first_name_of(client), portal_url,
                has_training=pkgs.has_training(client.package_tier))
            EmailService(db).send(to=client.email, subject=subject, html=html,
                                  kind="feedback_ready", client=client)
        except Exception:
            pass
        # Push al MOMENTO de mayor valor del ciclo: el informe está listo. Antes
        # dependía de que el cliente abriera el correo (auditoría de calidad).
        try:
            from app.services import push as push_svc

            push_svc.notify_feedback_ready(db, client)
        except Exception:  # noqa: BLE001
            pass
    db.commit()
    return {"sent": True, "sent_at": fb.sent_at.isoformat()}


@router.post("/api/feedback/{doc_id}/send-email")
def send_feedback_email(doc_id: int, db: Session = Depends(get_db)) -> dict:
    """Entrega el feedback POR EMAIL (paquetes Start/Full): el informe completo
    va en el propio correo y el ciclo avanza igual que con el envío por WhatsApp."""
    fb = db.get(FeedbackDoc, doc_id)
    if not fb:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feedback no encontrado")
    client = _advance_cycle_after_feedback(db, fb)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")

    brand = brand_from_config(db)
    portal_url = f"{settings.public_base_url}/p/{client.portal_token}"
    subject, html = tpl.feedback_delivery(brand, _first_name_of(client),
                                          fb.content_json or {}, portal_url=portal_url)
    # El informe COMPLETO (gráficas, comparativa de fuerza y fotos) va adjunto
    # en PDF: el email solo llevaba el texto y perdía lo más premium del ciclo.
    adjuntos = None
    try:
        if fb.docx_path:
            from app.services.storage import abs_path as _abs

            ruta = _abs(fb.docx_path)
            if ruta.exists():
                crudo = ruta.read_bytes()
                try:
                    from app.services.docs.pdf_convert import docx_bytes_to_pdf

                    adjuntos = [(f"informe_progreso_{fb.id}.pdf",
                                 docx_bytes_to_pdf(crudo), "application/pdf")]
                except Exception:  # noqa: BLE001 — sin LibreOffice, va el Word
                    adjuntos = [(
                        f"informe_progreso_{fb.id}.docx", crudo,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )]
    except Exception:  # noqa: BLE001 — sin adjunto sigue saliendo el email
        adjuntos = None
    email_status = EmailService(db).send(
        to=client.email, subject=subject, html=html,
        kind="feedback_delivery", client=client, attachments=adjuntos,
    )
    db.commit()
    return {"sent": True, "sent_at": fb.sent_at.isoformat(), "email_status": email_status}


@router.get("/api/feedback/{doc_id}/document")
def download_feedback_document(doc_id: int, db: Session = Depends(get_db)):
    """Descarga el documento Word del feedback."""
    from fastapi import Response

    from app.services.storage import abs_path

    fb = db.get(FeedbackDoc, doc_id)
    if not fb or not fb.docx_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feedback no encontrado")
    path = abs_path(fb.docx_path)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")
    period = db.get(Period, fb.period_id)
    idx = period.period_index if period else fb.id
    return Response(
        content=path.read_bytes(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="feedback_periodo{idx}.docx"'},
    )


# ------------------------------------------- documentos Word del plan (Fase 7) ----

def _doc_brand(db: Session, client=None):
    from app.models import BrandConfig
    from app.services.docs.word_base import DocBrand

    cfg = fila_de_marca(db, client)
    if cfg is None:
        return DocBrand(name="Tu asesoría", color_primary="#6EE7B7",
                        color_secondary="#8B9DF7", font_family="Inter")
    logo_abs = None
    if cfg.logo_path:
        from app.services.storage import abs_path

        try:
            logo_abs = str(abs_path(cfg.logo_path))
        except Exception:
            logo_abs = None
    return DocBrand(
        name=cfg.name, color_primary=cfg.color_primary,
        color_secondary=cfg.color_secondary, font_family=cfg.font_family,
        tagline=cfg.tagline, contact_email=cfg.contact_email, logo_path=logo_abs,
    )


@router.get("/api/plans/{plan_id}/document")
def download_plan_document(
    plan_id: int,
    format: str = Query("pdf", pattern="^(pdf|docx)$"),
    db: Session = Depends(get_db),
):
    """Genera y descarga el plan. format=pdf (por defecto) para entregar;
    format=docx devuelve el Word ORIGINAL editable, para que el coach pueda
    modificar cualquier apartado antes de enviarlo. Constructor compartido con
    el enlace público del cliente — ver services/plan_delivery."""
    from fastapi import Response

    from app.services.plan_delivery import build_plan_pdf

    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    client = db.get(Client, plan.client_id)

    content, media_type, filename = build_plan_pdf(db, plan, client, fmt=format)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/plans/{plan_id}/import-word")
def import_plan_word(
    plan_id: int,
    file: "UploadFile" = FastFile(...),
    db: Session = Depends(get_db),
) -> dict:
    """IDA Y VUELTA del Word editable: el coach sube el .docx que editó en Word
    y aquí se LEE (determinista, 0 créditos de IA) y se devuelven los JSON
    candidatos + la lista de cambios detectados + avisos. NO aplica nada: la
    aplicación la hace el PATCH de siempre desde el panel, previa confirmación
    del coach (mismo camino: sanitizado, reconcile, historial, rev, §13)."""
    from app.services.word_import import MAX_DOCX_BYTES, WordImportError, parse_word_edits

    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    if plan.status == "superseded":
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Este plan fue sustituido por una versión más nueva")
    data = file.file.read(MAX_DOCX_BYTES + 1)
    if len(data) > MAX_DOCX_BYTES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "El Word supera el tamaño máximo (15 MB)")
    if not data.startswith(b"PK"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "El archivo no es un .docx (¿has subido un PDF o un .doc antiguo?)")
    try:
        r = parse_word_edits(db, plan, data)
    except WordImportError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    # Frases legibles del diff (mismas que el resto del sistema) + las extra
    # del parser (textos que plan_diff no describe), sin duplicar.
    from app.services.plan_diff import manual_change_summary

    frases = manual_change_summary(
        db,
        old_nutrition=plan.nutrition_json, new_nutrition=r["nutrition_json"],
        old_training=plan.training_json, new_training=r["training_json"],
    )
    vistos = set(frases)
    for extra in r["extra_changes"]:
        if extra not in vistos:
            frases.append(extra)
            vistos.add(extra)

    rev = int((plan.nutrition_json or {}).get("rev") or 0)
    return {
        "changes": frases,
        "warnings": r["warnings"],
        "has_changes": bool(frases),
        "base_rev": rev,
        "nutrition_json": r["nutrition_json"],
        "training_json": r["training_json"],
        # solo viaja si el Word trae cambios del educativo (píldoras/FAQ/técnica)
        "education_json": r["education_json"],
    }


# ------------------------------------------- plan desde CUALQUIER documento ----
# El Word de ida y vuelta solo entiende NUESTRO .docx. Lo demás —la dieta en
# Excel, la rutina que traía el cliente de otro entrenador en PDF, una foto de
# una hoja con las comidas— entra por aquí: la IA TRANSCRIBE, el backend pone
# las cifras (contrato del cliente, biblioteca de ejercicios, base de
# alimentos) y el coach confirma antes de que exista el borrador.

class PlanImportConfirmIn(BaseModel):
    nutrition_json: dict | None = None
    training_json: dict | None = None
    origen: str = "un documento"
    # Violaciones que devolvió la PREVIEW (Revisor determinista sobre lo
    # importado): se guardan como flags que retienen el borrador.
    violaciones: list[str] = []


@router.post("/api/clients/{client_id}/plans/import-document")
def import_plan_document(
    client_id: int,
    file: Annotated[UploadFile | None, FastFile(description="Documento (cualquier formato)")] = None,
    files: Annotated[List[UploadFile] | None, FastFile(description="Varias fotos = un documento")] = None,
    db: Session = Depends(get_db),
) -> dict:
    """PREVIEW: lee el documento con IA y devuelve los JSON candidatos del plan
    (cifras del backend), el resumen de lo reconocido y los avisos. NO
    persiste: el coach confirma en `/import-document/confirm`."""
    from app.services.ai.client import AIClient, AIGenerationError
    from app.services.document_reader import DocumentoIlegible, normalizar_varios
    from app.services.plan_import import build_plan_candidates, extract_plan_from_document
    from app.services.plan_library import PlanLibraryError

    client = _client_or_404(db, client_id)
    subidos = [f for f in ([file] if file is not None else []) + list(files or []) if f is not None]
    if not subidos:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No has adjuntado ningún fichero.")
    ficheros = [(f.file.read(25 * 1024 * 1024 + 1), f.filename) for f in subidos]
    try:
        documento = normalizar_varios(ficheros)
    except DocumentoIlegible as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    try:
        ext = extract_plan_from_document(documento, AIClient())
    except AIGenerationError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail={"message": "La IA no pudo leer el documento.", "error": str(exc)},
        ) from exc
    try:
        r = build_plan_candidates(db, client, ext, documento.nombre)
    except PlanLibraryError as exc:
        detalle = ({"message": str(exc), "missing": exc.missing} if exc.missing else str(exc))
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detalle) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    r["document_description"] = documento.descripcion
    r["avisos"] = list(documento.avisos) + r["avisos"]
    r["violaciones"] = [a[len("violation: "):] for a in r["avisos"]
                        if str(a).startswith("violation: ")]
    log_event(db, "client", client_id, "plan_document_previewed",
              {"document": documento.nombre, "kind": ext.document_kind,
               "resumen": {k: v for k, v in r["resumen"].items() if not isinstance(v, list)}})
    db.commit()
    return r


@router.post("/api/clients/{client_id}/plans/import-document/confirm")
def confirm_plan_document(client_id: int, body: PlanImportConfirmIn,
                          db: Session = Depends(get_db)) -> dict:
    """Crea el BORRADOR a partir de los JSON confirmados por el coach, por el
    MISMO camino que copiar de la biblioteca (reescala al contrato, completa la
    mitad que falte, avisos de seguridad, «copiado de …, revísalo»)."""
    from app.services.plan_library import PlanLibraryError, copiar_a_cliente, resumen_plan

    client = _client_or_404(db, client_id)
    if not body.nutrition_json and not body.training_json:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No hay nada que importar.")
    if isinstance(body.nutrition_json, dict):
        _sanitize_nutrition(body.nutrition_json)
    try:
        plan, avisos = copiar_a_cliente(
            db, client, nutrition=body.nutrition_json, training=body.training_json,
            education=None, origen=f"el documento «{body.origen[:80]}»")
    except PlanLibraryError as exc:
        detalle = ({"message": str(exc), "missing": exc.missing} if exc.missing else str(exc))
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detalle) from exc
    plan.generated_by = "document"
    # Las violaciones que detectó el Revisor determinista sobre el contenido
    # importado viajan con el prefijo que RETIENE el borrador: aunque el coach
    # pulse Activar, el guardado del editor no lo publica sin resolverlas.
    if body.violaciones:
        plan.guardrail_flags = list(plan.guardrail_flags or []) + [
            v if str(v).startswith("violation:") else f"violation: {v}"
            for v in body.violaciones[:12]]
    db.commit()
    db.refresh(plan)
    return {
        "id": plan.id, "month_index": plan.month_index, "version": plan.version,
        "status": plan.status, "guardrail_flags": plan.guardrail_flags or [],
        "nutrition": plan.nutrition_json, "training": plan.training_json,
        "education": plan.education_json, "review": None,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "published_at": None,
        "warnings": avisos,
        "summary": resumen_plan(plan.nutrition_json, plan.training_json, plan.goal_type),
    }


@router.post("/api/plans/{plan_id}/send-email")
def send_plan_email(plan_id: int, db: Session = Depends(get_db)) -> dict:
    """Entrega la planificación POR EMAIL (paquetes Start/Full): adjunta el PDF
    del plan y enlaza el portal de seguimiento. Equivale al envío por WhatsApp
    de los paquetes Pro, pero por correo."""
    from app.services.plan_delivery import build_plan_pdf

    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    client = db.get(Client, plan.client_id)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")

    # El PDF es un extra: si su generación fallara, el email con el enlace al
    # portal sigue siendo útil, así que no bloqueamos el envío por ello.
    attachments: list[tuple[str, bytes, str]] = []
    try:
        content, _media, filename = build_plan_pdf(db, plan, client)
        attachments.append((filename, content, "application/pdf"))
    except Exception:
        pass

    is_adapted = bool((plan.nutrition_json or {}).get("applied_adjustments")
                      or (plan.training_json or {}).get("applied_adjustments"))
    brand = brand_from_config(db)
    portal_url = f"{settings.public_base_url}/p/{client.portal_token}"
    _first = ((client.full_name or "").split() or [(client.email or "cliente").split("@")[0]])[0]
    subject, html = tpl.plan_delivery(brand, _first, portal_url, is_adapted, bool(attachments))
    email_status = EmailService(db).send(
        to=client.email, subject=subject, html=html, kind="plan_delivery",
        client=client, attachments=attachments or None,
    )
    log_event(db, "plan", plan.id, "plan_sent_email", {"client_id": client.id, "status": email_status})
    db.commit()
    return {"sent": email_status != "failed", "email_status": email_status,
            "attached_pdf": bool(attachments)}


# --------------------------------- cambios manuales del plan (aviso + envío) ----

def _clear_manual_changes(plan: Plan) -> list[str]:
    """Quita el aviso de cambios manuales del plan y devuelve los items."""
    nut = dict(plan.nutrition_json) if isinstance(plan.nutrition_json, dict) else {}
    items = list((nut.pop("manual_changes", None) or {}).get("items") or [])
    plan.nutrition_json = nut
    return items


@router.post("/api/plans/{plan_id}/manual-changes/ack")
def ack_manual_changes(plan_id: int, db: Session = Depends(get_db)) -> dict:
    """Marca los cambios manuales como ENVIADOS/atendidos (los quita del aviso).
    Lo llama la web tras abrir el WhatsApp con el mensaje, o al descartarlos."""
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    items = _clear_manual_changes(plan)
    log_event(db, "plan", plan.id, "manual_changes_acked", {"items": items[:20]})
    db.commit()
    return {"cleared": len(items)}


@router.post("/api/plans/{plan_id}/send-update-email")
def send_plan_update_email(plan_id: int, db: Session = Depends(get_db)) -> dict:
    """Envía al cliente POR EMAIL la actualización manual del plan: el mensaje
    EXPLICA qué se cambió (diff detectado al editar) y adjunta el PDF al día.
    Al enviarse, el aviso de cambios pendientes se apaga."""
    from app.services.plan_delivery import build_plan_pdf

    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    client = db.get(Client, plan.client_id)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    items = list(((plan.nutrition_json or {}).get("manual_changes") or {}).get("items") or [])
    if not items:
        raise HTTPException(status.HTTP_409_CONFLICT, "No hay cambios manuales pendientes de enviar")

    attachments: list[tuple[str, bytes, str]] = []
    try:
        content, _media, filename = build_plan_pdf(db, plan, client)
        attachments.append((filename, content, "application/pdf"))
    except Exception:
        pass

    brand = brand_from_config(db)
    portal_url = f"{settings.public_base_url}/p/{client.portal_token}"
    _first = ((client.full_name or "").split() or [(client.email or "cliente").split("@")[0]])[0]
    subject, html = tpl.plan_manual_update(brand, _first, items, portal_url, bool(attachments))
    email_status = EmailService(db).send(
        to=client.email, subject=subject, html=html, kind="plan_update",
        client=client, attachments=attachments or None,
    )
    if email_status == "sent":
        _clear_manual_changes(plan)
    log_event(db, "plan", plan.id, "plan_update_sent_email",
              {"client_id": client.id, "status": email_status, "items": items[:20]})
    db.commit()
    return {"sent": email_status == "sent", "email_status": email_status,
            "attached_pdf": bool(attachments)}


# ----------------------------------------------- swap de ejercicios (Fase 8, F.5) ----

class SwapProposeOut(BaseModel):
    exercise_id: int
    name: str
    movement_pattern: str
    muscle_primary: str
    equipment: list[str]
    similarity: int


class SwapApplyIn(BaseModel):
    session_index: int
    old_exercise_id: int
    new_exercise_id: int
    permanent: bool = False
    reason: str = ""


@router.get("/api/clients/{client_id}/plans/{plan_id}/swap-options/{exercise_id}",
            response_model=list[SwapProposeOut])
def swap_options(client_id: int, plan_id: int, exercise_id: int,
                 db: Session = Depends(get_db)) -> list[SwapProposeOut]:
    """Propone 2–3 alternativas válidas para sustituir un ejercicio (F.5.1)."""
    from app.services.swap import propose_alternatives

    client = _client_or_404(db, client_id)
    plan = db.get(Plan, plan_id)
    if not plan or plan.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    alts = propose_alternatives(db, client, exercise_id)
    return [SwapProposeOut(**a.__dict__) for a in alts]


@router.post("/api/clients/{client_id}/plans/{plan_id}/swap", response_model=dict)
def swap_apply(client_id: int, plan_id: int, body: SwapApplyIn,
               db: Session = Depends(get_db)) -> dict:
    """Aplica el swap creando una nueva versión del plan (borrador) (F.5.2–4)."""
    from app.services.swap import apply_swap

    client = _client_or_404(db, client_id)
    plan = db.get(Plan, plan_id)
    if not plan or plan.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    try:
        result = apply_swap(
            db, client=client, plan=plan, session_index=body.session_index,
            old_exercise_id=body.old_exercise_id, new_exercise_id=body.new_exercise_id,
            permanent=body.permanent, reason=body.reason,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {
        "new_plan_id": result.new_plan_id, "new_version": result.new_version,
        "group_volume_after": result.group_volume_after,
        "guardrail_flags": result.guardrail_flags,
    }


# ------------------------------------------- plantilla de anamnesis (PDF oficial) ----

@router.get("/api/anamnesis-template")
def download_anamnesis_template():
    """Descarga la plantilla oficial de anamnesis (PDF en blanco) para que el
    coach la envíe por correo al cliente."""
    from pathlib import Path

    from fastapi import Response

    path = Path(__file__).resolve().parent.parent / "assets" / "anamnesis_template.pdf"
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plantilla no encontrada")
    return Response(
        content=path.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="anamnesis.pdf"'},
    )
