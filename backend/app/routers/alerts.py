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


# Dónde se arregla cada aviso y CÓMO. El `target` es un ANCLA: la misma cadena
# la lleva el elemento en el DOM (`data-ancla`) y es lo que la web centra y
# MARCA al llegar; `fix` es la nota corta que se enseña pegada a esa marca.
# Un aviso sin entrada aquí sigue funcionando: lleva a su pestaña sin marcar
# nada — mejor eso que un ancla inventada que no existe y deja al coach
# mirando una pantalla sin nada señalado.
_DESTINO: dict[str, tuple[str, str]] = {
    "client_inactive": (
        "resumen.estado",
        "Reactívalo si sigue contigo, o archívalo para sacarlo del radar."),
    "payment_pending": (
        "resumen.pago",
        "Mándale su enlace de pago, o anota aquí el cobro si te pagó en mano."),
    "renewal_due": (
        "resumen.pago",
        "Su ciclo se acaba: ofrécele la renovación antes de que venza."),
    "create_plan": (
        "anamnesis.revision",
        "Repasa los campos extraídos (la IA se equivoca con la letra a mano) "
        "y genera la planificación."),
    "publish_plan": (
        "plan.activar",
        "Repasa el borrador y actívalo: hasta entonces el cliente no lo ve."),
    "generate_feedback": (
        "feedback.generar",
        "Genera el informe de la revisión con sus métricas y sus fotos."),
    "send_feedback": (
        "feedback.enviar",
        "Envíaselo: mientras no lo mandes, el cliente no lo ve en su portal."),
    "adapt_plan": (
        "plan.adaptar",
        "Adapta el plan a lo que salió en la revisión y actívalo."),
    "no_logs": (
        "seguimiento.registros",
        "Escríbele: lleva días sin registrar y la revisión saldrá coja."),
    "period_overdue": (
        "feedback.cerrar",
        "Reclámasela por WhatsApp; si no la manda, ciérrala tú aquí para no "
        "dejar el ciclo bloqueado."),
    "change_request": (
        "seguimiento.peticiones",
        "Léela, respóndele y márcala resuelta para que deje de avisar."),
    "missing_products": (
        "plan.suplementos",
        "Súbelos en Recursos: si no, al cliente no le aparecen comprables."),
    "regenerate_goal": (
        "plan.objetivo",
        "Aquí cambias de etapa y regeneras el plan con el objetivo nuevo."),
    "plan_stale_inputs": (
        "plan.acciones",
        "Las cifras del plan salen de datos que ya cambiaste: regenera o adapta."),
    "goal_review": (
        "plan.objetivo",
        "Aquí decides: mantener el objetivo (y se pospone el aviso) o "
        "cambiar de etapa y regenerar el plan."),
    "video_call_wait": (
        "feedback.videollamada",
        "Aún no ha propuesto hora: recuérdaselo."),
}


def _alert(client: Client, kind: str, severity: str, message: str, tab: str,
           action: str, *, target: str | None = None, fix: str | None = None,
           to: str | None = None) -> dict:
    """Un aviso. Además del texto lleva a DÓNDE se arregla (`target`, el ancla
    que la web marca al llegar) y CÓMO (`fix`, la nota pegada a la marca).

    `key` identifica el PROBLEMA de forma estable: el panel ancla recordatorios
    por esa clave y los borra solos cuando deja de aparecer entre los avisos
    vivos. `to` es un destino FUERA de la ficha (p. ej. /recursos), para los
    pocos avisos que se arreglan en otra pantalla.
    """
    por_defecto = _DESTINO.get(kind)
    if por_defecto:
        target = target or por_defecto[0]
        fix = fix or por_defecto[1]
    return {
        "client_id": client.id, "client_name": client.full_name,
        "kind": kind, "severity": severity, "message": message,
        "tab": tab, "action": action,
        "target": target, "fix": fix, "to": to,
        "key": f"{client.id}:{kind}:{target or ''}",
    }


def _renewal_alert(client: Client, today: date) -> dict | None:
    """Aviso de RENOVACIÓN de un plan de pago único a punto de agotarse.
    La fórmula vive en services/renewals.py (una sola verdad, compartida con el
    email al cliente y con el enlace de pago)."""
    from app.services.renewals import RENEWAL_WARN_DAYS, renewal_window

    w = renewal_window(client, today)
    if w is None:
        return None
    ends_on, left = w
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
                          "Inactivo · 30 días sin actividad",
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
                from app.services.storage import anamnesis_documents
                has_doc = bool(anamnesis_documents(client.id))
            except Exception:  # noqa: BLE001 — el storage nunca tumba las alertas
                has_doc = False
            # El formulario DIGITAL del portal también cuenta como recibida
            # (sello de consentimiento): mismos datos, sin PDF que leer.
            por_formulario = getattr(client, "consent_signed_at", None) is not None
            if has_doc or por_formulario:
                extra = "" if client.goal_type else " · ⚠ IA incompleta, revisa a mano"
                origen = " (formulario del portal)" if (por_formulario and not has_doc) else ""
                out.append(_alert(client, "create_plan", "alta",
                                  f"Anamnesis recibida{origen}{extra}",
                                  "anamnesis", "Revisar anamnesis"))
            else:
                days_wait = ((today - client.created_at.date()).days
                             if getattr(client, "created_at", None) else 0)
                aging = (f" Lleva {days_wait} días sin enviarla: reclámasela."
                         if days_wait >= 7 else "")
                out.append(_alert(client, "create_plan",
                                  "alta" if days_wait >= 7 else "media",
                                  f"Sin planificación: falta su anamnesis.{aging}",
                                  "anamnesis", "Reclamar la anamnesis",
                                  target="anamnesis.enviar",
                                  fix="Reenvíale el cuestionario por WhatsApp o "
                                      "sube tú su PDF si te lo pasó por otra vía."))
        return out  # sin plan publicado, el resto del ciclo no aplica

    # --- Revisión quincenal recibida sin feedback ---------------------------
    if last_period is not None and last_period.status == "closed":
        # Pestaña FEEDBACK: es donde está el botón "Generar feedback" (con el
        # resumen de métricas y las fotos del cierre). Antes llevaba a
        # Seguimiento, donde esa acción no existe (auditoría de calidad).
        out.append(_alert(client, "generate_feedback", "alta",
                          f"Revisión #{last_period.period_index} recibida",
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
            # En un plan solo-entreno el sello vive en training_json.
            return (((p.nutrition_json or {}).get("applied_adjustments")
                     or (p.training_json or {}).get("applied_adjustments")
                     or {})).get("period_index")

        if _adapted_idx(latest) != last_analyzed.period_index:
            if (latest is not None and latest.status == "draft"
                    and latest.generated_by in ("scaffold", "library")):
                # El coach YA está montando el plan nuevo (base sin IA o copia
                # de la biblioteca): gritarle "sin adaptar" mientras trabaja es
                # falso ruido. Se le recuerda terminar y activar, en media.
                out.append(_alert(client, "publish_plan", "media",
                                  f"Borrador v{latest.version} en preparación: "
                                  "termínalo y actívalo.",
                                  "planificacion", "Activar planificación"))
            else:
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
        # Solo cuentan filas CON CONTENIDO: el autosave del portal crea la fila
        # vacía con solo abrir la pantalla, y ese max() crudo reseteaba el gap
        # — un cliente que solo ABRÍA la app nunca disparaba la alerta
        # (auditoría crítica). Registro real = diario rellenado, series de
        # entreno o comidas elegidas.
        from app.models import WorkoutLog
        from app.services.push import _DIARY_FIELDS

        logs_periodo = list(db.scalars(
            select(DailyLog).where(DailyLog.period_id == last_period.id)))
        con_series = set(db.scalars(
            select(WorkoutLog.daily_log_id).where(
                WorkoutLog.daily_log_id.in_([l.id for l in logs_periodo] or [0]))))
        fechas_reales = [
            l.log_date for l in logs_periodo
            if l.id in con_series
            or l.chosen_options_json
            or any(getattr(l, f, None) not in (None, "") for f in _DIARY_FIELDS)
        ]
        last_log = max(fechas_reales) if fechas_reales else None
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
                "feedback", "Cerrar la revisión"))

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
        prefix = f"{len(open_crs)} peticiones · última: " if len(open_crs) > 1 else ""
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
                f"Sin producto en Recursos: {listado}",
                "planificacion", "Subir a Recursos",
                to="/recursos?tab=productos"))

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
                    f"Revisión #{last_review.period_index} · esperando su propuesta de videollamada",
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
                "feedback", "Aceptar o modificar",
                target=f"feedback.videollamada.{vc.id}",
                fix="Acéptala y se crea el Meet con invitación, o modifícala "
                    "para acordar otra hora por WhatsApp."))
        elif vc.status == "pending_manual":
            out.append(_alert(
                client, "video_call_manual", "alta",
                "Videollamada a agendar a mano (acordado por WhatsApp): escribe el día y la hora.",
                "feedback", "Agendar día y hora",
                target=f"feedback.videollamada.{vc.id}",
                fix="Escribe el día y la hora acordados y se crea el Meet."))
        elif vc.status == "scheduled" and vc.scheduled_for is not None:
            if vc.scheduled_for == today + timedelta(days=1):
                out.append(_alert(
                    client, "video_call_tomorrow", "alta",
                    f"Videollamada MAÑANA ({vc.scheduled_for.strftime('%d/%m')}).",
                    "feedback", "Ver videollamada",
                    target=f"feedback.videollamada.{vc.id}",
                    fix="Prepara la revisión antes de la llamada."))
            elif vc.scheduled_for <= today:
                out.append(_alert(
                    client, "video_call_confirm", "alta",
                    "¿Se realizó la videollamada? Confírmala, o reagéndala si no pudo ser.",
                    "feedback", "Confirmar videollamada",
                    target=f"feedback.videollamada.{vc.id}",
                    fix="Márcala como hecha, o reagéndala si no pudo ser."))

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
            _match_term, _norm_food, option_conflict,
        )

        forbidden_pat = (_DIET_PATTERN_FORBIDDEN.get(
            _norm_food(client.diet_pattern).replace(" ", "_"))
            if getattr(client, "diet_pattern", None) else None)

        hit_allergy = hit_dislike = hit_pattern = None
        try:
            for slot, opt in _iter_options(published.nutrition_json or {}):
                if hit_allergy is None and client.food_allergies:
                    # Criterio COMPLETO del Revisor 0 (ingredientes + título +
                    # preparación): un «pesto» en la elaboración también avisa.
                    found = option_conflict(opt, client.food_allergies)
                    if found:
                        hit_allergy = (slot, opt.get("title") or opt.get("key") or "?", found)
                if hit_dislike is None and client.food_dislikes:
                    found = option_conflict(opt, client.food_dislikes)
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
                f"⚠ ALÉRGENO en el plan activo: «{t}» (toma {s}, contiene {f})",
                "planificacion", "Corregir planificación",
                target=f"nutricion.comida.{s}",
                fix=f"Aquí está «{f}», que es alérgeno suyo. Cambia esta opción "
                    f"por otra sin ese alimento, o regenera el plan."))
        elif hit_pattern:
            s, t, f = hit_pattern
            out.append(_alert(
                client, "plan_allergen_conflict", "alta",
                f"⚠ Su plan activo viola su patrón «{client.diet_pattern}»: "
                f"«{t}» (toma {s}, contiene {f}). Corrige esa comida o regenera.",
                "planificacion", "Corregir planificación",
                target=f"nutricion.comida.{s}",
                fix=f"Aquí hay «{f}», que su patrón «{client.diet_pattern}» no "
                    f"admite. Cambia esta opción, o regenera el plan."))
        elif hit_dislike:
            s, t, f = hit_dislike
            out.append(_alert(
                client, "plan_dislike_conflict", "media",
                f"Su plan activo incluye un alimento que ahora no tolera/odia: "
                f"«{t}» (toma {s}, {f}). Valora cambiar esa opción.",
                "planificacion", "Revisar planificación",
                target=f"nutricion.comida.{s}",
                fix=f"Aquí está «{f}», que ahora no tolera. Cámbiale esta opción "
                    f"por otra que sí le guste."))

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
                "Ficha cambiada tras generar: " + ", ".join(diffs[:4]),
                "planificacion", "Regenerar o adaptar"))

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
        # Aislamiento por cliente: un solo cliente con datos rotos tumbaba el
        # endpoint ENTERO (500) y el panel se quedaba sin campana ni colas,
        # en silencio. Su fallo se registra y los demás siguen saliendo.
        try:
            alerts.extend(client_alerts(db, c))
        except Exception:  # noqa: BLE001
            import logging

            logging.getLogger("app.alerts").exception(
                "alertas del cliente %s ilegibles; se omite", c.id)
    # AUTOMATISMOS PARADOS: si el mantenimiento diario no corre, no se abren
    # períodos, no salen recordatorios y las suscripciones de la oferta no se
    # cortan solas. Antes eso solo se veía en el log del contenedor: el coach
    # creía que el sistema trabajaba por él.
    try:
        from app.services.job_state import automatismos_parados

        motivo = automatismos_parados()
        if motivo:
            alerts.insert(0, {
                "client_id": 0, "client_name": "Sistema",
                "kind": "jobs_parados", "severity": "alta", "message": motivo,
                "tab": "resumen", "action": "Revisar el servidor",
                "target": None, "fix": "Avisa a quien lleva el servidor: los "
                                       "automatismos del sistema no se están ejecutando.",
                "to": None, "key": "sistema:jobs_parados",
            })
    except Exception:  # noqa: BLE001 — el chequeo no puede tumbar las alertas
        pass

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
