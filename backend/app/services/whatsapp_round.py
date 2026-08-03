"""Ronda diaria de seguimiento por WhatsApp.

Cada día toca UN brief del pool de 100 (rotación sin repetir; al llegar a 100
vuelve a empezar). Para cada cliente activo, la IA REDACTA ese brief adaptado a
esa persona: su nombre, su plan, cómo le está yendo, la hora del día y el día de
la semana. El coach revisa la ronda y va enviando.

El envío es asistido (se abre WhatsApp con el texto escrito): no se manda nada
solo, y así ningún mensaje sale sin que el coach lo haya visto.

Todo degrada con dignidad: si la IA no está disponible, cada cliente recibe un
texto de reserva correcto (nunca un mensaje vacío ni un error).
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Client, WhatsAppRound, WhatsAppSend
from app.services import packages as pkgs
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
    db.commit()
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


def _user_prompt(brief: Brief, ctx: dict, *, franja: str, dia_semana: str) -> str:
    import json

    return (
        f"TEMA DE HOY: {brief.tema}\n"
        f"QUÉ DEBE CONSEGUIR: {brief.guia}\n\n"
        f"MOMENTO: {dia_semana}, franja de {franja}. Saluda acorde a la hora.\n\n"
        f"CLIENTE (usa solo lo que haya aquí):\n{json.dumps(ctx, ensure_ascii=False, indent=2)}\n\n"
        "Escribe SOLO el texto del mensaje, sin comillas ni explicaciones."
    )


_DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


def fallback_text(brief: Brief, ctx: dict) -> str:
    """Texto de reserva si la IA no está disponible: correcto y humano, aunque
    menos personalizado. Nunca se envía un mensaje vacío."""
    return f"¡Hola {ctx.get('nombre', '')}! {brief.guia.rstrip('.')}. ¿Cómo lo llevas?".replace("  ", " ")


def compose_for_client(brief: Brief, ctx: dict, *, ai=None, now: datetime | None = None) -> str:
    """Redacta el mensaje de ESTE cliente. Con `ai=None` (o si la IA falla)
    devuelve el texto de reserva."""
    now = now or datetime.now(TZ)
    if ai is None:
        return fallback_text(brief, ctx)
    try:
        from app.config import settings

        raw = ai._raw_call(  # noqa: SLF001 — texto libre, no JSON
            model=settings.model_light,
            system=SYSTEM,
            user=_user_prompt(brief, ctx, franja=franja_of(now),
                              dia_semana=_DIAS[now.weekday()]),
        )
        text = (raw or "").strip().strip('"').strip()
        return text or fallback_text(brief, ctx)
    except Exception:  # noqa: BLE001 — un fallo de IA no deja al coach sin ronda
        return fallback_text(brief, ctx)


def build_round(db: Session, *, ai=None, now: datetime | None = None) -> dict:
    """Ronda de hoy lista para revisar y enviar: un mensaje por cliente activo.

    Los clientes cuyo plan no encaja con el brief del día (p. ej. un brief de
    dieta para un cliente de solo entreno) reciben el SIGUIENTE brief que sí les
    aplica, para que nadie se quede sin mensaje ni reciba algo que no le toca.
    """
    now = now or datetime.now(TZ)
    round_row = get_or_create_round(db, today=now.date())
    sent_ids = set(db.scalars(
        select(WhatsAppSend.client_id).where(WhatsAppSend.round_id == round_row.id)
    ))

    items = []
    for client in active_clients(db):
        has_n = pkgs.has_nutrition(client.package_tier)
        has_t = pkgs.has_training(client.package_tier)
        brief = _brief_for_client(round_row.brief_index, has_nutrition=has_n, has_training=has_t)
        ctx = client_context(db, client)
        items.append({
            "client_id": client.id,
            "name": client.full_name,
            "phone": client.phone,
            "tier": pkgs.normalize(client.package_tier),
            "brief_key": brief.key,
            "brief_tema": brief.tema,
            "text": compose_for_client(brief, ctx, ai=ai, now=now),
            "already_sent": client.id in sent_ids,
        })
    return {
        "round_id": round_row.id,
        "date": round_row.round_date.isoformat(),
        "brief_index": round_row.brief_index,
        "brief_key": round_row.brief_key,
        "brief_tema": brief_for_index(round_row.brief_index).tema,
        "pool_size": len(POOL),
        "items": items,
        "pending": sum(1 for i in items if not i["already_sent"]),
    }


def _brief_for_client(index: int, *, has_nutrition: bool, has_training: bool) -> Brief:
    """Primer brief aplicable a partir del índice del día (evita mandar un tema
    de dieta a quien no tiene dieta)."""
    for offset in range(len(POOL)):
        brief = brief_for_index(index + offset)
        if applies_to(brief, has_nutrition=has_nutrition, has_training=has_training):
            return brief
    return brief_for_index(index)


def mark_sent(db: Session, *, round_id: int, client_id: int, text: str | None = None) -> None:
    """Marca que la ronda de hoy ya se le envió a este cliente (idempotente)."""
    exists = db.scalar(
        select(WhatsAppSend).where(WhatsAppSend.round_id == round_id,
                                   WhatsAppSend.client_id == client_id)
    )
    if exists is not None:
        return
    db.add(WhatsAppSend(round_id=round_id, client_id=client_id, text=text))
    db.commit()
