"""Centro de ALERTAS del coach — preventivo e inteligente.

Cada alerta se CALCULA del estado real del cliente (nada que marcar como
leído): en cuanto el coach hace la acción que pide, la alerta desaparece sola.
Cubre el ciclo completo de la asesoría para que sea imposible dejar pasos sin
atender:

  onboarding  → crear la planificación (queda ACTIVA al generarse; "activar"
                solo aplica a borradores antiguos)
  revisión    → generar el feedback → enviarlo por WhatsApp
  adaptación  → adaptar el plan a la última revisión (queda activo al momento)
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


# Duración contratada (días) de cada periodicidad de pago único. "oferta" es
# una suscripción de Stripe: se renueva sola, no genera aviso.
_BILLING_DAYS = {"1m": 30, "3m": 90, "6m": 180}
RENEWAL_WARN_DAYS = 7


def _renewal_alert(client: Client, today: date) -> dict | None:
    """Aviso de RENOVACIÓN de un plan de pago único a punto de agotarse."""
    if getattr(client, "payment_status", None) != "paid":
        return None
    if getattr(client, "stripe_subscription_id", None):
        return None  # suscripción: se cobra sola
    paid_at = getattr(client, "paid_at", None)
    days = _BILLING_DAYS.get(getattr(client, "billing_period", "") or "")
    if paid_at is None or days is None:
        return None
    ends_on = paid_at.date() + timedelta(days=days)
    left = (ends_on - today).days
    if left > RENEWAL_WARN_DAYS:
        return None
    if left >= 0:
        msg = (f"Su plan contratado termina {'hoy' if left == 0 else f'en {left} días'} "
               f"({ends_on.strftime('%d/%m')}): ofrécele la renovación.")
        sev = "media"
    else:
        msg = (f"Su plan venció hace {-left} días ({ends_on.strftime('%d/%m')}) y sigue "
               "activo: cóbrale la renovación o cierra la asesoría.")
        sev = "alta"
    return _alert(client, "renewal_due", sev, msg, "resumen", "Renovar plan")


def client_alerts(db: Session, client: Client, today: date | None = None) -> list[dict]:
    """Alertas de UN cliente (reutilizado por el listado y el backtest)."""
    from app.services.portal import today_local

    # Fecha de NEGOCIO (settings.tz): con date.today() en UTC, de madrugada las
    # alertas de "sin registros"/videollamada salían descuadradas un día.
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

    # --- Renovación a la vista (pago único, sin suscripción) -----------------
    # Los planes de 1/3/6 meses se cobran de una vez: al acabar la duración no
    # hay nada que lo recuerde y la asesoría seguía corriendo gratis (o el
    # cliente se perdía sin que nadie le ofreciera renovar). La suscripción de
    # la oferta se cobra sola: ahí no hace falta aviso.
    renewal = _renewal_alert(client, today)
    if renewal is not None:
        out.append(renewal)

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

    # --- Revisión quincenal recibida sin feedback ---------------------------
    if last_period is not None and last_period.status == "closed":
        # Pestaña FEEDBACK: es donde está el botón "Generar feedback" (con el
        # resumen de métricas y las fotos del cierre). Antes llevaba a
        # Seguimiento, donde esa acción no existe (auditoría de calidad).
        out.append(_alert(client, "generate_feedback", "alta",
                          f"Revisión #{last_period.period_index} recibida: revisa los datos y genera el feedback.",
                          "feedback", "Generar feedback"))

    # --- Feedback generado pero sin enviar / plan sin adaptar ---------------
    # ANCLADO al último período ANALIZADO, no al último absoluto: enviar el
    # feedback abre el período siguiente en el acto, y con el ancla vieja la
    # alerta "sin adaptar" moría justo entonces — el ciclo nuevo corría 14 días
    # con las kcal antiguas sin que nadie lo persiguiera (auditoría del ciclo).
    last_analyzed = last_period if (
        last_period is not None and last_period.status == "analyzed"
    ) else db.scalar(
        select(Period).where(Period.client_id == client.id,
                             Period.status == "analyzed")
        .order_by(Period.period_index.desc()).limit(1)
    )
    if last_analyzed is not None:
        fb = db.scalar(
            select(FeedbackDoc).where(FeedbackDoc.period_id == last_analyzed.id)
            .order_by(FeedbackDoc.id.desc()).limit(1)
        )
        if fb is not None and fb.sent_at is None:
            out.append(_alert(client, "send_feedback", "alta",
                              f"Feedback de la revisión #{last_analyzed.period_index} sin enviar al cliente.",
                              "feedback", "Enviar por WhatsApp"))

        def _adapted_idx(p: Plan | None) -> int | None:
            if p is None:
                return None
            return ((p.nutrition_json or {}).get("applied_adjustments") or {}).get("period_index")

        if _adapted_idx(latest) != last_analyzed.period_index:
            out.append(_alert(client, "adapt_plan", "alta",
                              f"Planificación sin adaptar a la revisión #{last_analyzed.period_index}.",
                              "planificacion", "Adaptar planificación"))
        elif latest is not None and latest.status == "draft":
            out.append(_alert(client, "publish_plan", "alta",
                              f"Borrador adaptado a la revisión #{last_analyzed.period_index} sin activar.",
                              "planificacion", "Activar planificación"))
    if last_analyzed is None and latest is not None and latest.status == "draft":
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

        # --- Período vencido sin cerrar: el cliente registra pero no envía ---
        overdue = (today - last_period.ends_on).days
        if overdue >= 2:
            out.append(_alert(
                client, "period_overdue", "alta" if overdue >= 5 else "media",
                f"Su revisión quincenal venció hace {overdue} días y no la ha "
                "enviado: recuérdaselo por WhatsApp.",
                "seguimiento", "Reclamar la revisión"))

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

    # --- Suplementos del plan SIN producto en Recursos ----------------------
    # El portal del cliente destaca los productos de SU planificación (con el
    # código del coach). Si un suplemento pautado no tiene producto subido, el
    # cliente no lo verá comprable → aviso para subirlo a Recursos.
    from app.models import RecommendedProduct
    from app.services.product_match import match_products, plan_supplement_names

    sups = plan_supplement_names(published.nutrition_json)
    if sups:
        titles = list(db.scalars(
            select(RecommendedProduct.title).where(RecommendedProduct.active.is_(True))
        ))
        missing = match_products(sups, titles)["missing"]
        if missing:
            listado = ", ".join(missing[:4]) + ("…" if len(missing) > 4 else "")
            out.append(_alert(
                client, "missing_products", "media",
                f"Suplementos de su plan sin producto en Recursos: {listado}. "
                "Súbelos en Recursos → Productos para que le salgan en su portal "
                "con tu código.",
                "planificacion", "Ver planificación"))

    # --- Videollamada quincenal (Pro) ---------------------------------------
    # El cliente propone día/hora al enviar su revisión → el coach ACEPTA (crea el
    # Meet) o MODIFICA (lo acuerda por WhatsApp y agenda a mano). Estados:
    # proposed → accept|modify → scheduled|pending_manual → done. Se ancla a la
    # última revisión CERRADA/ANALIZADA; los agendados salen SIEMPRE (aunque el
    # siguiente período ya se haya abierto): una llamada no puede olvidarse.
    from app.models import VideoCall
    from app.services.portal import format_when_es

    if pkgs.has_video_call(client.package_tier):
        last_review = db.scalar(
            select(Period).where(Period.client_id == client.id,
                                 Period.status.in_(("closed", "analyzed")))
            .order_by(Period.period_index.desc()).limit(1)
        )
        if last_review is not None:
            vc = db.scalar(select(VideoCall).where(
                VideoCall.client_id == client.id,
                VideoCall.period_index == last_review.period_index))
            if vc is None:
                out.append(_alert(
                    client, "video_call_wait", "media",
                    f"Revisión #{last_review.period_index}: esperando que el cliente proponga "
                    "la videollamada (o agéndala tú a mano).",
                    "feedback", "Agendar videollamada"))

    # TODAS las videollamadas vivas — de cualquier revisión y aunque el cliente
    # ya no sea Pro: una propuesta sin responder o una llamada agendada no puede
    # esfumarse en silencio (antes, al cerrar la revisión siguiente quedaban
    # huérfanas y desaparecían de las alertas para siempre).
    for vc in db.scalars(select(VideoCall).where(
            VideoCall.client_id == client.id,
            VideoCall.status.in_(("proposed", "pending_manual", "scheduled")))):
        if vc.status == "proposed" and vc.scheduled_at is not None:
            out.append(_alert(
                client, "video_call_proposed", "alta",
                f"El cliente propuso videollamada: {format_when_es(vc.scheduled_at)}. "
                "Acéptala o modifícala.",
                "feedback", "Aceptar o modificar"))
        elif vc.status == "pending_manual":
            out.append(_alert(
                client, "video_call_manual", "alta",
                "Videollamada a agendar a mano (acordado por WhatsApp): escribe el día y la hora.",
                "feedback", "Agendar día y hora"))
        elif vc.status == "scheduled" and vc.scheduled_for is not None:
            if vc.scheduled_for == today + timedelta(days=1):
                out.append(_alert(
                    client, "video_call_tomorrow", "alta",
                    f"Videollamada MAÑANA ({vc.scheduled_for.strftime('%d/%m')}).",
                    "feedback", "Ver videollamada"))
            elif vc.scheduled_for <= today:
                out.append(_alert(
                    client, "video_call_confirm", "alta",
                    "¿Se realizó la videollamada? Confírmala, o reagéndala si no pudo ser.",
                    "feedback", "Confirmar videollamada"))

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


@router.get("/video-calls/agenda")
def video_calls_agenda(db: Session = Depends(get_db)) -> dict:
    """Agenda de videollamadas AGENDADAS (con Meet): día, hora, cliente y enlace.
    Salen ordenadas por fecha y permanecen hasta que el coach las confirma como
    realizadas (las ya pasadas sin confirmar salen marcadas para revisar)."""
    from app.models import VideoCall
    from app.services.portal import format_when_es, today_local

    today = today_local()
    rows = db.scalars(
        select(VideoCall).where(VideoCall.status == "scheduled",
                                VideoCall.scheduled_at.is_not(None))
        .order_by(VideoCall.scheduled_at.asc())
    ).all()
    out = []
    for vc in rows:
        client = db.get(Client, vc.client_id)
        if client is None or client.status == "inactive":
            continue
        out.append({
            "id": vc.id,
            "client_id": vc.client_id,
            "client_name": client.full_name,
            "scheduled_at": vc.scheduled_at.isoformat(),
            "when_label": format_when_es(vc.scheduled_at),
            "duration_min": vc.duration_min,
            "meet_url": vc.meet_url,
            "is_past": vc.scheduled_for is not None and vc.scheduled_for < today,
        })
    return {"calls": out, "count": len(out)}
