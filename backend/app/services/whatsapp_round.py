"""Ronda diaria de seguimiento por WhatsApp.

PRIMERO SE MIRA A CADA CLIENTE; el pool es el plan B.

Para cada cliente activo se calcula de qué hay que hablarle HOY a partir de sus
datos (`services/client_focus`): si duerme cinco horas, del sueño; si ha
entrenado uno de sus cuatro días, de eso; si dejó una pregunta en su diario, se
le responde. El tema sale de REGLAS sobre lo que consta, no del criterio de un
modelo, y viaja al prompt con el dato exacto que lo justifica.

Solo cuando no hay nada que destacar —el cliente va bien y al día— entra el
brief del día del pool de 100 (rotación sin repetir), que es un tema general
que le vale a cualquiera. Inventarle un problema a quien no lo tiene sería
peor que mandarle algo genérico.

En los dos casos la IA hace lo mismo: REDACTARLO como una persona. El coach
revisa la ronda y va enviando.

El envío es asistido (se abre WhatsApp con el texto escrito): no se manda nada
solo, y así ningún mensaje sale sin que el coach lo haya visto.

Todo degrada con dignidad: si la IA no está disponible, cada cliente recibe un
texto de reserva correcto (nunca un mensaje vacío ni un error).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Client, WhatsAppRound, WhatsAppSend
from app.services import packages as pkgs
from app.services.client_focus import Foco, focos_de
from app.services.whatsapp_pool import POOL, Brief, applies_to, brief_for_index

TZ = ZoneInfo("Europe/Madrid")

# Estados de cliente a los que SÍ se escribe en la ronda diaria.
ACTIVE_STATUSES = ("active", "at_risk", "review_pending")


def franja_of(now: datetime) -> str:
    """Franja horaria del día (para elegir el tono y el saludo)."""
    h = now.hour
    if h < 13:
        return "manana"
    if h < 20:
        return "tarde"
    return "noche"


def get_or_create_round(db: Session, *, today: date | None = None) -> WhatsAppRound:
    """Ronda de HOY. El brief se fija la primera vez que se abre el panel, así
    que reabrirlo no cambia el mensaje del día."""
    today = today or datetime.now(TZ).date()
    row = db.scalar(select(WhatsAppRound).where(WhatsAppRound.round_date == today))
    if row is not None:
        return row
    # El índice avanza sobre la última ronda, no sobre el nº de días: si un día
    # no se manda nada, el pool no se salta un mensaje.
    last = db.scalar(select(WhatsAppRound).order_by(WhatsAppRound.round_date.desc()).limit(1))
    index = ((last.brief_index + 1) % len(POOL)) if last else 0
    brief = brief_for_index(index)
    row = WhatsAppRound(round_date=today, brief_index=index, brief_key=brief.key)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # Dos aperturas simultáneas del panel: la otra ganó el unique de
        # round_date. Se usa la suya (misma ronda, mismo brief).
        db.rollback()
        row = db.scalar(select(WhatsAppRound).where(WhatsAppRound.round_date == today))
        if row is None:  # carrera + rollback ajeno: reintento único
            raise
        return row
    db.refresh(row)
    return row


def active_clients(db: Session) -> list[Client]:
    """Clientes a los que toca escribir: activos y con teléfono."""
    return list(db.scalars(
        select(Client)
        .where(Client.status.in_(ACTIVE_STATUSES), Client.phone.isnot(None))
        .order_by(Client.full_name)
    ))


def _first_name(client: Client) -> str:
    parts = (client.full_name or "").split()
    return parts[0] if parts else "¡hola!"


def client_context(db: Session, client: Client) -> dict:
    """Contexto REAL del cliente para que el mensaje no sea genérico: plan,
    objetivo, en qué día del período va y su último registro."""
    from app.models import DailyLog, Period

    ctx: dict = {
        "nombre": _first_name(client),
        "plan": pkgs.label(client.package_tier),
        "tiene_dieta": pkgs.has_nutrition(client.package_tier),
        "tiene_entreno": pkgs.has_training(client.package_tier),
        "objetivo": client.goal_type,
        "objetivo_en_sus_palabras": (client.lifestyle_notes or "")[:300] or None,
    }
    try:
        period = db.scalar(
            select(Period).where(Period.client_id == client.id, Period.status == "open")
            .order_by(Period.period_index.desc()).limit(1)
        )
        if period is not None:
            ctx["dia_del_periodo"] = (datetime.now(TZ).date() - period.starts_on).days + 1
            last = db.scalar(
                select(DailyLog).where(DailyLog.period_id == period.id)
                .order_by(DailyLog.log_date.desc()).limit(1)
            )
            if last is not None:
                ctx["ultimo_registro"] = {
                    "fecha": last.log_date.isoformat(),
                    "peso": last.weight_kg,
                    "adherencia_dieta": last.diet_adherence,
                    "sueno_h": last.sleep_hours,
                }
            ctx["dias_registrados"] = int(db.scalar(
                select(func.count(DailyLog.id)).where(DailyLog.period_id == period.id)
            ) or 0)
    except Exception:  # noqa: BLE001 — el contexto es un extra, nunca bloquea
        pass
    return ctx


SYSTEM = (
    "Eres el coach de fitness escribiendo un WhatsApp de seguimiento a UN cliente "
    "suyo. Tuteas, tono cercano pero profesional, en español de España. "
    "REGLAS: 1 solo mensaje, 2-4 frases, máximo ~40 palabras. Sin emojis salvo "
    "que aporten (máximo uno). No firmes ni pongas asunto. No inventes datos que "
    "no te den (nada de pesos, cifras ni logros que no consten). No des consejo "
    "médico. Si el brief pide una pregunta, termina con UNA pregunta concreta y "
    "fácil de responder. Suena a persona, no a plantilla ni a newsletter."
)


def _user_prompt(brief: Brief, ctx: dict, *, franja: str, dia_semana: str,
                 foco: Foco | None = None) -> str:
    import json

    # JSON compacto (sin indent): mismo contenido, ~25% menos tokens de entrada.
    ctx_json = json.dumps(ctx, ensure_ascii=False, separators=(",", ":"))
    if foco is not None:
        # EL DATO VA LITERAL. Es la diferencia entre "¿qué tal duermes?" y
        # "veo que llevas la semana en cinco horas y media": lo segundo es lo
        # que hace que el cliente se sienta mirado, y es justo lo que la IA no
        # puede deducir sola sin inventarse la cifra.
        tema = f"TEMA DE HOY (de ESTE cliente): {foco.tema}\n"
        guia = f"QUÉ DEBE CONSEGUIR: {foco.guia}\n"
        dato = (f"EL DATO QUE LO MOTIVA (menciónalo tal cual, sin redondear ni "
                f"adornar): {foco.dato}\n")
    else:
        tema = f"TEMA DE HOY: {brief.tema}\n"
        guia = f"QUÉ DEBE CONSEGUIR: {brief.guia}\n"
        dato = ""
    return (
        tema + guia + dato + "\n"
        f"MOMENTO: {dia_semana}, franja de {franja}. Saluda acorde a la hora.\n\n"
        f"CLIENTE (usa solo lo que haya aquí):\n{ctx_json}\n\n"
        "Escribe SOLO el texto del mensaje, sin comillas ni explicaciones."
    )


_DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


def fallback_text(brief: Brief, ctx: dict, foco: Foco | None = None) -> str:
    """Texto de reserva si la IA no está disponible.

    Con foco sigue siendo PERSONAL aunque no lo haya escrito un modelo: lleva
    su dato y una pregunta. Es lo que se manda el día que la API está caída, y
    ese día el cliente no tiene por qué recibir un mensaje peor."""
    nombre = ctx.get("nombre", "")
    if foco is not None and foco.reserva:
        return f"¡Hola {nombre}! {foco.reserva}".replace("  ", " ")
    return f"¡Hola {nombre}! {brief.guia.rstrip('.')}. ¿Cómo lo llevas?".replace("  ", " ")


def compose_for_client(brief: Brief, ctx: dict, *, ai=None, now: datetime | None = None,
                       foco: Foco | None = None) -> str:
    """Redacta el mensaje de ESTE cliente. Con `ai=None` (o si la IA falla)
    devuelve el texto de reserva."""
    now = now or datetime.now(TZ)
    if ai is None:
        return fallback_text(brief, ctx, foco)
    try:
        from app.config import settings

        raw = ai._raw_call(  # noqa: SLF001 — texto libre, no JSON
            model=settings.model_light,
            system=SYSTEM,
            user=_user_prompt(brief, ctx, franja=franja_of(now),
                              dia_semana=_DIAS[now.weekday()], foco=foco),
            max_tokens=300,  # ~40 palabras de salida: techo anti-desbocadas
        )
        text = (raw or "").strip().strip('"').strip()
        return text or fallback_text(brief, ctx, foco)
    except Exception:  # noqa: BLE001 — un fallo de IA no deja al coach sin ronda
        return fallback_text(brief, ctx, foco)


def build_round(db: Session, *, ai=None, now: datetime | None = None,
                force: bool = False) -> dict:
    """Ronda de hoy lista para revisar y enviar: un mensaje por cliente activo.

    Los textos se redactan UNA vez por cliente y día y quedan guardados en la
    ronda (texts_json): reabrir el panel no vuelve a gastar llamadas de IA.
    `force=True` (botón "Reescribir") regenera todos. Los clientes cuyo plan no
    encaja con el brief del día reciben el SIGUIENTE brief que sí les aplica.
    """
    now = now or datetime.now(TZ)
    hoy = now.date()
    round_row = get_or_create_round(db, today=hoy)
    sent_ids = set(db.scalars(
        select(WhatsAppSend.client_id).where(WhatsAppSend.round_id == round_row.id)
    ))
    guardado: dict = dict(round_row.texts_json or {}) if not force else {}
    cached = {k: v for k, v in guardado.items() if k != _CLAVE_FOCOS}
    focos_de_hoy: dict = dict(guardado.get(_CLAVE_FOCOS) or {})
    recientes = _focos_recientes(db, hoy)

    clients = active_clients(db)
    # Contextos, focos y briefs en el hilo principal (la sesión de BD no es
    # thread-safe); a los hilos solo va la LLAMADA de redacción.
    prepared = []
    for client in clients:
        has_n = pkgs.has_nutrition(client.package_tier)
        has_t = pkgs.has_training(client.package_tier)
        brief = _brief_for_client(round_row.brief_index, has_nutrition=has_n, has_training=has_t)
        foco = _foco_del_dia(db, client, hoy=hoy, has_nutrition=has_n, has_training=has_t,
                             recientes=recientes.get(client.id, []))
        if foco is not None:
            focos_de_hoy[str(client.id)] = foco.key
        prepared.append((client, brief, client_context(db, client), foco))

    missing = [t for t in prepared if str(t[0].id) not in cached]
    if missing:
        if ai is not None and len(missing) > 1:
            from concurrent.futures import ThreadPoolExecutor

            with ThreadPoolExecutor(max_workers=4) as pool:
                texts = list(pool.map(
                    lambda t: compose_for_client(t[1], t[2], ai=ai, now=now, foco=t[3]),
                    missing))
        else:
            texts = [compose_for_client(b, ctx, ai=ai, now=now, foco=f)
                     for _, b, ctx, f in missing]
        for (client, _b, _ctx, _f), text in zip(missing, texts):
            cached[str(client.id)] = text
    if missing or focos_de_hoy != (guardado.get(_CLAVE_FOCOS) or {}):
        # Los focos se guardan JUNTO a los textos (misma columna, clave
        # reservada): sirven para no repetirle el mismo tema dos días seguidos
        # y no merecen una migración propia.
        round_row.texts_json = {**cached, _CLAVE_FOCOS: focos_de_hoy}
        db.commit()

    items = []
    for client, brief, _ctx, foco in prepared:
        items.append({
            "client_id": client.id,
            "name": client.full_name,
            "phone": client.phone,
            "tier": pkgs.normalize(client.package_tier),
            "brief_key": foco.key if foco else brief.key,
            "brief_tema": foco.tema if foco else brief.tema,
            # POR QUÉ le toca este tema: el coach ve el dato antes de enviar y
            # puede corregir el mensaje si no le cuadra. Un mensaje que no se
            # entiende no se manda.
            "motivo": foco.dato if foco else None,
            "personalizado": foco is not None,
            "text": cached.get(str(client.id), ""),
            "already_sent": client.id in sent_ids,
        })
    return {
        "personalizados": sum(1 for i in items if i["personalizado"]),
        "round_id": round_row.id,
        "date": round_row.round_date.isoformat(),
        "brief_index": round_row.brief_index,
        "brief_key": round_row.brief_key,
        "brief_tema": brief_for_index(round_row.brief_index).tema,
        "pool_size": len(POOL),
        "items": items,
        "pending": sum(1 for i in items if not i["already_sent"]),
    }


# Clave reservada dentro de `texts_json` para la memoria de temas. Los demás
# nombres del diccionario son ids de cliente (numéricos): no pueden chocar.
_CLAVE_FOCOS = "_focos"
# Cuántos días atrás se mira para no repetirle el mismo tema.
_DIAS_SIN_REPETIR = 3


def sin_cliente(texts_json: dict | None, client_id: int) -> dict:
    """El JSON de una ronda SIN nada de este cliente (baja RGPD).

    Vive aquí y no en el endpoint de la baja porque es esta función la que
    conoce la forma del diccionario: su texto va con su id como clave, y el
    TEMA que se le asignó ese día —de qué había que hablarle: su sueño, su
    adherencia— dentro de `_focos`. Es un dato suyo aunque no lleve su nombre,
    y quien borra un cliente no tiene por qué saberse esa estructura.
    """
    datos = dict(texts_json or {})
    focos = {k: v for k, v in (datos.get(_CLAVE_FOCOS) or {}).items()
             if k != str(client_id)}
    out = {k: v for k, v in datos.items()
           if k not in (str(client_id), _CLAVE_FOCOS)}
    if focos:
        out[_CLAVE_FOCOS] = focos
    return out


def _focos_recientes(db: Session, hoy: date) -> dict[int, list[str]]:
    """Qué tema le tocó a cada cliente en las últimas rondas.

    Repetirle «¿qué tal duermes?» tres mañanas seguidas es exactamente la
    sensación de plantilla que esto viene a quitar. Una sola consulta para
    toda la ronda: esto corre con la cartera entera delante.
    """
    filas = db.scalars(
        select(WhatsAppRound)
        .where(WhatsAppRound.round_date < hoy,
               WhatsAppRound.round_date >= hoy - timedelta(days=_DIAS_SIN_REPETIR))
    ).all()
    out: dict[int, list[str]] = {}
    for fila in filas:
        for cid, key in ((fila.texts_json or {}).get(_CLAVE_FOCOS) or {}).items():
            try:
                out.setdefault(int(cid), []).append(str(key))
            except (TypeError, ValueError):
                continue
    return out


def _foco_del_dia(db: Session, client, *, hoy: date, has_nutrition: bool,
                  has_training: bool, recientes: list[str]) -> Foco | None:
    """El tema de hoy para este cliente, o None si no hay nada que destacar.

    Lo URGENTE se repite sin complejos (prioridad 1-2): si lleva cuatro días
    sin aparecer, el mensaje de hoy vuelve a ser ese — callarlo por no repetir
    sería perder al cliente por educación. Lo demás cede el turno al siguiente
    tema si ya se le mandó estos días.
    """
    focos = focos_de(db, client, hoy=hoy, has_nutrition=has_nutrition,
                     has_training=has_training)
    for foco in focos:
        if foco.prioridad <= 2 or foco.key not in recientes:
            return foco
    return None


def _brief_for_client(index: int, *, has_nutrition: bool, has_training: bool) -> Brief:
    """Primer brief aplicable a partir del índice del día (evita mandar un tema
    de dieta a quien no tiene dieta)."""
    for offset in range(len(POOL)):
        brief = brief_for_index(index + offset)
        if applies_to(brief, has_nutrition=has_nutrition, has_training=has_training):
            return brief
    return brief_for_index(index)


def mark_sent(db: Session, *, round_id: int, client_id: int, text: str | None = None) -> bool:
    """Marca que la ronda de hoy ya se le envió a este cliente (idempotente).
    Devuelve False si el cliente ya no existe (borrado entre la carga y el clic)."""
    if db.get(Client, client_id) is None:
        return False
    exists = db.scalar(
        select(WhatsAppSend).where(WhatsAppSend.round_id == round_id,
                                   WhatsAppSend.client_id == client_id)
    )
    if exists is not None:
        return True
    db.add(WhatsAppSend(round_id=round_id, client_id=client_id, text=text))
    db.commit()
    return True
