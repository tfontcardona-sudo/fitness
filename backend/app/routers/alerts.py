"""Centro de ALERTAS del coach — preventivo e inteligente.

Cada alerta se CALCULA del estado real del cliente (nada que marcar como
leído): en cuanto el coach hace la acción que pide, la alerta desaparece sola.
Cubre el ciclo completo de la asesoría para que sea imposible dejar pasos sin
atender:

  onboarding  → crear la planificación (queda ACTIVA al generarse; "activar"
                solo aplica a borradores antiguos)
  revisión    → generar el informe → enviarlo al cliente
  seguimiento → cliente sin registros varios días
  objetivo    → 45 días en la misma etapa: valorar cambio (posponible)
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Client, DailyLog, FeedbackDoc, Period, Plan
from app.services import packages as pkgs

router = APIRouter(prefix="/api", tags=["alerts"], dependencies=[Depends(get_current_user)])

GOAL_REVIEW_DAYS = 45
NO_LOGS_DAYS = 4
# Seguimiento continuo: días registrados para que el informe merezca la pena y
# días NUEVOS a partir de los cuales conviene ponerlo al día.
INFORME_MIN_DIAS = 7
INFORME_DIAS_NUEVOS = 7

_GOAL_LABEL = {
    "fat_loss": "pérdida de grasa", "muscle_gain": "ganancia muscular",
    "recomp": "recomposición", "maintenance": "mantenimiento",
    "injury_recovery": "recuperación de lesión",
}


def _alert(client: Client, kind: str, severity: str, message: str, tab: str,
           action: str) -> dict:
    return {
        "client_id": client.id, "client_name": client.full_name,
        "kind": kind, "severity": severity, "message": message,
        "tab": tab, "action": action,
    }


def client_alerts(db: Session, client: Client, today: date | None = None) -> list[dict]:
    """Alertas de UN cliente (reutilizado por el listado y el backtest)."""
    from app.services.portal import today_local

    # Fecha de NEGOCIO (settings.tz): con date.today() en UTC, de madrugada las
    # alertas de "sin registros" salían descuadradas un día.
    today = today or today_local()
    out: list[dict] = []
    if client.status == "inactive":
        # Antes se devolvía [] y el cliente inactivo desaparecía de TODO el
        # radar (auditoría del ciclo): estado sin salida y sin aviso. Una única
        # alerta persistente para decidir: reactivar o archivar de verdad.
        out.append(_alert(client, "client_inactive", "media",
                          "Cliente inactivo (30 días sin actividad): reactívalo "
                          "desde su perfil o acuerda con él el cierre.",
                          "resumen", "Revisar cliente"))
        return out

    # --- Pago pendiente ------------------------------------------------------
    # Sin alerta, un pago sin completar solo se veía en la carpeta "Falta pago":
    # el coach debe enterarse también por la campana y el resumen del móvil.
    if getattr(client, "payment_status", None) == "pending":
        out.append(_alert(client, "payment_pending", "media",
                          "Pago pendiente: cobra su plan (o márcalo como pagado "
                          "si te pagó por otra vía).",
                          "resumen", "Revisar pago"))

    plans = list(db.scalars(
        select(Plan).where(Plan.client_id == client.id)
        .order_by(Plan.month_index.desc(), Plan.version.desc())
    ))
    published = next((p for p in plans if p.status == "published"), None)
    latest = plans[0] if plans else None
    last_period = db.scalar(
        select(Period).where(Period.client_id == client.id)
        .order_by(Period.period_index.desc()).limit(1)
    )

    # --- Arranque: sin planificación aún -----------------------------------
    if published is None:
        if latest is not None:  # borrador ANTIGUO sin activar (legado)
            out.append(_alert(client, "publish_plan", "alta",
                              f"Borrador v{latest.version} sin activar: revísalo y actívalo.",
                              "planificacion", "Activar planificación"))
        else:
            # La llegada de la anamnesis era un evento invisible (auditoría del
            # ciclo): el mensaje decía lo mismo antes y después de que el
            # cliente la subiera, y si la IA no pudo extraer los campos el
            # coach creía que no había llegado nada. La alerta ahora distingue.
            try:
                from app.services.storage import list_documents
                has_doc = bool(list_documents(client.id))
            except Exception:  # noqa: BLE001 — el storage nunca tumba las alertas
                has_doc = False
            if has_doc:
                extra = ("" if client.goal_type else
                         " (la IA no pudo extraer todos los campos: revísalos a mano)")
                out.append(_alert(client, "create_plan", "alta",
                                  f"Anamnesis recibida{extra}: revísala y genera la planificación.",
                                  "anamnesis", "Revisar anamnesis"))
            else:
                days_wait = ((today - client.created_at.date()).days
                             if getattr(client, "created_at", None) else 0)
                aging = (f" Lleva {days_wait} días sin enviarla: reclámasela."
                         if days_wait >= 7 else "")
                out.append(_alert(client, "create_plan",
                                  "alta" if days_wait >= 7 else "media",
                                  f"Sin planificación: falta su anamnesis.{aging}",
                                  "anamnesis", "Crear planificación"))
        return out  # sin plan publicado, el resto del ciclo no aplica

    # --- SEGUIMIENTO CONTINUO -----------------------------------------------
    # El informe se pone al día con lo que el cliente registra y el coach lo
    # envía cuando lo ve listo. Dos avisos, que son TODO el ciclo aquí:
    #   · hay datos nuevos suficientes → ponerlo al día,
    #   · hay un informe en borrador → enviárselo.
    if last_period is not None and last_period.status == "open":
        registrados = db.scalar(
            select(func.count()).select_from(DailyLog)
            .where(DailyLog.period_id == last_period.id)
        ) or 0
        fb_ultimo = db.scalar(
            select(FeedbackDoc).where(FeedbackDoc.period_id == last_period.id)
            .order_by(FeedbackDoc.id.desc()).limit(1)
        )
        if fb_ultimo is None:
            if registrados >= INFORME_MIN_DIAS:
                out.append(_alert(
                    client, "generate_feedback", "alta",
                    f"Ya lleva {registrados} días registrados y no tiene informe: "
                    "genéralo y envíaselo.",
                    "feedback", "Generar informe"))
        elif fb_ultimo.sent_at is None:
            out.append(_alert(client, "send_feedback", "alta",
                              "Informe en borrador sin enviar al cliente.",
                              "feedback", "Revisar y enviar"))
        else:
            nuevos = registrados - ((fb_ultimo.content_json or {}).get("logs_at_generation") or 0)
            if nuevos >= INFORME_DIAS_NUEVOS:
                out.append(_alert(
                    client, "generate_feedback", "media",
                    f"{nuevos} días registrados desde el último informe: ponlo al día.",
                    "feedback", "Actualizar informe"))

    # --- Borrador de planificación sin activar (legado) ---------------------
    if latest is not None and latest.status == "draft":
        # Borrador antiguo suelto (legado): los planes nuevos se activan solos
        out.append(_alert(client, "publish_plan", "media",
                          f"Borrador v{latest.version} sin activar.",
                          "planificacion", "Activar planificación"))

    # --- Cliente sin registros varios días (período abierto) ----------------
    if last_period is not None and last_period.status == "open":
        last_log = db.scalar(
            select(func.max(DailyLog.log_date)).where(DailyLog.period_id == last_period.id)
        )
        since = last_log or (last_period.starts_on - date.resolution)
        gap = (today - since).days
        days_in = (today - last_period.starts_on).days
        if gap >= NO_LOGS_DAYS and days_in >= NO_LOGS_DAYS:
            out.append(_alert(client, "no_logs", "media",
                              f"Sin registros del cliente desde hace {gap} días.",
                              "seguimiento", "Ver seguimiento"))

    # --- Petición de cambio del cliente sin atender (portal → coach) ---------
    # El cliente escribió una duda/petición desde su portal: el coach debe
    # verlo. Persiste hasta que se marque resuelta.
    from app.models import ChangeRequest

    open_crs = list(db.scalars(
        select(ChangeRequest)
        .where(ChangeRequest.client_id == client.id, ChangeRequest.status == "open")
        .order_by(ChangeRequest.created_at.desc())
    ))
    if open_crs:
        # Con el TEXTO de la petición: el coach debe poder leer QUÉ pide sin
        # depender del email (en dev está apagado y el mensaje se perdía).
        extracto = (open_crs[0].message or "").strip()
        if len(extracto) > 140:
            extracto = extracto[:137] + "…"
        prefix = (f"Tiene {len(open_crs)} peticiones sin responder. Última: "
                  if len(open_crs) > 1 else "Te ha escrito desde su portal: ")
        out.append(_alert(
            client, "change_request", "alta",
            f"{prefix}«{extracto}»",
            "seguimiento", "Ver petición"))

    # --- Objetivo cambiado sin regenerar el plan ----------------------------
    # Tras cambiar el objetivo, si la IA falló al regenerar, el cliente seguiría
    # sirviéndose el plan del objetivo anterior en silencio. Lo señalamos.
    if (published.goal_type and client.goal_type
            and published.goal_type != client.goal_type):
        cur = _GOAL_LABEL.get(client.goal_type, client.goal_type)
        old = _GOAL_LABEL.get(published.goal_type, published.goal_type)
        out.append(_alert(client, "regenerate_goal", "alta",
                          f"El objetivo es «{cur}» pero el plan activo sigue en «{old}»: regenéralo.",
                          "planificacion", "Regenerar planificación"))

    # --- Alergia/aversión añadida DESPUÉS de generar: el plan activo puede ---
    # seguir sirviendo el alérgeno en el portal y el PDF (auditoría de
    # ediciones). Chequeo EN VIVO del banco publicado contra la ficha actual:
    # se enciende al editar la ficha y se apaga al corregir/regenerar el plan.
    if client.food_allergies or client.food_dislikes or getattr(client, "diet_pattern", None):
        from app.services.guardrails import (
            _DIET_PATTERN_FORBIDDEN, _all_option_texts, _iter_options,
            _match_term, _norm_food, option_allergen,
        )

        forbidden_pat = (_DIET_PATTERN_FORBIDDEN.get(
            _norm_food(client.diet_pattern).replace(" ", "_"))
            if getattr(client, "diet_pattern", None) else None)

        hit_allergy = hit_dislike = hit_pattern = None
        try:
            for slot, opt in _iter_options(published.nutrition_json or {}):
                if hit_allergy is None and client.food_allergies:
                    found = option_allergen(opt, client.food_allergies)
                    if found:
                        hit_allergy = (slot, opt.get("title") or opt.get("key") or "?", found)
                if hit_dislike is None and client.food_dislikes:
                    found = option_allergen(opt, client.food_dislikes)
                    if found:
                        hit_dislike = (slot, opt.get("title") or opt.get("key") or "?", found)
                if hit_pattern is None and forbidden_pat:
                    found = _match_term(forbidden_pat, _all_option_texts(opt))
                    if found:
                        hit_pattern = (slot, opt.get("title") or opt.get("key") or "?", found)
                if hit_allergy and hit_dislike and (hit_pattern or not forbidden_pat):
                    break
        except Exception:  # noqa: BLE001 — un plan legado raro no tumba las alertas
            pass
        if hit_allergy:
            s, t, f = hit_allergy
            out.append(_alert(
                client, "plan_allergen_conflict", "alta",
                f"⚠ Su plan activo contiene un ALÉRGENO de su ficha: «{t}» "
                f"(toma {s}, contiene {f}). Edita esa comida o regenera el plan.",
                "planificacion", "Corregir planificación"))
        elif hit_pattern:
            s, t, f = hit_pattern
            out.append(_alert(
                client, "plan_allergen_conflict", "alta",
                f"⚠ Su plan activo viola su patrón «{client.diet_pattern}»: "
                f"«{t}» (toma {s}, contiene {f}). Corrige esa comida o regenera.",
                "planificacion", "Corregir planificación"))
        elif hit_dislike:
            s, t, f = hit_dislike
            out.append(_alert(
                client, "plan_dislike_conflict", "media",
                f"Su plan activo incluye un alimento que ahora no tolera/odia: "
                f"«{t}» (toma {s}, {f}). Valora cambiar esa opción.",
                "planificacion", "Revisar planificación"))

    # --- Ficha cambiada tras generar (peso/altura/nivel/días/lugar/dieta) ----
    # El PATCH de la ficha era silencioso: la IA extraía mal la altura, el
    # coach la corregía y las kcal del plan seguían calculadas con el dato
    # viejo sin ningún aviso (auditoría de ediciones). El plan guarda ahora un
    # snapshot de sus inputs y aquí se compara con la ficha actual.
    gen_inputs = (published.nutrition_json or {}).get("gen_inputs") or {}
    if gen_inputs:
        diffs: list[str] = []
        checks = (
            ("height_cm", client.height_cm, "altura"),
            ("level", client.level, "nivel"),
            ("training_days", client.training_days, "días de entreno"),
            ("training_place", client.training_place, "lugar de entreno"),
            ("diet_mode", client.diet_mode, "modo de dieta"),
        )
        for key, current, label in checks:
            old = gen_inputs.get(key)
            if old is not None and current is not None and old != current:
                diffs.append(f"{label} {old}→{current}")
        old_w = gen_inputs.get("weight_kg")
        cur_w = client.current_weight_kg or client.start_weight_kg
        if (isinstance(old_w, (int, float)) and isinstance(cur_w, (int, float))
                and abs(float(old_w) - float(cur_w)) >= 3):
            diffs.append(f"peso {old_w:g}→{cur_w:g} kg")
        if diffs:
            out.append(_alert(
                client, "plan_stale_inputs", "media",
                "La ficha cambió tras generar el plan (" + ", ".join(diffs[:4]) +
                "): las kcal/entreno del plan activo salen de los datos viejos — "
                "valora regenerar o adaptar.",
                "planificacion", "Revisar planificación"))

    # --- 45 días en la misma etapa de objetivo ------------------------------
    if client.goal_started_on is not None:
        days_goal = (today - client.goal_started_on).days
        snoozed = (client.goal_review_snoozed_on is not None
                   and (today - client.goal_review_snoozed_on).days < GOAL_REVIEW_DAYS)
        if days_goal >= GOAL_REVIEW_DAYS and not snoozed:
            goal = _GOAL_LABEL.get(client.goal_type or "", client.goal_type or "—")
            out.append(_alert(client, "goal_review", "media",
                              f"Lleva {days_goal} días con el objetivo de {goal}: valora si toca cambiarlo.",
                              "planificacion", "Valorar objetivo"))

    return out


@router.get("/alerts")
def list_alerts(db: Session = Depends(get_db)) -> dict:
    """Todas las alertas pendientes, más graves primero."""
    clients = db.scalars(select(Client).order_by(Client.full_name)).all()
    alerts: list[dict] = []
    for c in clients:
        alerts.extend(client_alerts(db, c))
    alerts.sort(key=lambda a: (0 if a["severity"] == "alta" else 1, a["client_name"]))
    return {"alerts": alerts, "count": len(alerts),
            "high": sum(1 for a in alerts if a["severity"] == "alta")}
