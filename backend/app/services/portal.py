"""Lógica de presentación del portal del cliente (G.4).

Resuelve "el plan y período vigentes" de un cliente y arma la vista HOY a
partir del plan publicado y los registros del día. Mantener esto fuera del
router permite testearlo y reutilizarlo (p. ej. el documento Word offline de
seguimiento de la Fase 7 parte de la misma estructura día a día).

La vista HOY mapea el día de la semana actual a la sesión de entrenamiento
correspondiente del plan y a las comidas del día (banco flexible: las 7
opciones por slot; estricto: el plato del día).
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import BrandConfig, Client, DailyLog, Exercise, Period, Plan, RecommendedProduct
from app.services.storage import media_url

# URLs que el portal renderiza como href/src: solo esquema http(s) — los datos
# LEGADOS (guardados antes del validador de entrada) se re-filtran aquí.
_HTTP_RE = re.compile(r"^https?://", re.IGNORECASE)
# Nuestros propios archivos subidos (mismo origen que el portal).
_MEDIA_PREFIX = "/api/media/"


def _playable(url: str | None) -> str | None:
    """URL que el portal puede poner en un href/src, o None.

    Vale lo NUESTRO (/api/media/…, relativa y del mismo origen) y los enlaces
    http(s). Todo lo demás se descarta: los datos LEGADOS sin esquema
    ("www.youtube.com/…") y cualquier javascript:/data: no pueden llegar al
    navegador como enlace ni como fuente de vídeo.
    """
    u = (url or "").strip()
    if not u:
        return None
    return u if u.startswith(_MEDIA_PREFIX) or _HTTP_RE.match(u) else None

DAY_LABELS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DAY_SLUGS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
_MONTHS_ES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
              "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def format_when_es(dt: datetime) -> str:
    """"jueves 21 de julio a las 17:00" (para emails/push, sin depender de locale).

    Se muestra en la zona horaria del negocio (settings.tz)."""
    from app.config import settings

    if dt.tzinfo is not None:
        try:
            dt = dt.astimezone(ZoneInfo(getattr(settings, "tz", None) or "Europe/Madrid"))
        except Exception:
            pass
    return (f"{DAY_LABELS[dt.weekday()].lower()} {dt.day} de "
            f"{_MONTHS_ES[dt.month]} a las {dt:%H:%M}")


def today_local() -> date:
    """HOY en la zona horaria del negocio (settings.tz, Europe/Madrid).

    El servidor corre en UTC: entre las 00:00 y ~02:00 de Madrid, date.today()
    aún es "ayer" y descuadra días restantes, cierre quincenal y semana del
    mesociclo con el calendario real del cliente. Igual que hace push.py."""
    from app.config import settings

    try:
        return datetime.now(ZoneInfo(getattr(settings, "tz", None) or "Europe/Madrid")).date()
    except Exception:
        return date.today()


def active_period(db: Session, client_id: int) -> Period | None:
    """Período más reciente no analizado (el que el cliente está viviendo)."""
    return db.scalar(
        select(Period)
        .where(Period.client_id == client_id, Period.status != "analyzed")
        .order_by(Period.period_index.desc())
        .limit(1)
    )


def published_plan_for_period(db: Session, period: Period) -> Plan | None:
    plan = db.get(Plan, period.plan_id)
    if plan is not None and plan.status == "published":
        return plan
    # El plan del período fue SUPERSEDIDO (p. ej. el coach adaptó y publicó una
    # versión nueva a mitad de período): el portal debe enseñar siempre la
    # última versión publicada, no la rutina antigua anclada al período.
    return latest_published_plan(db, period.client_id)


def latest_published_plan(db: Session, client_id: int) -> Plan | None:
    return db.scalar(
        select(Plan)
        .where(Plan.client_id == client_id, Plan.status == "published")
        .order_by(Plan.month_index.desc(), Plan.version.desc())
        .limit(1)
    )


# Explicación de CADA fase del mesociclo (por qué haces lo que haces esta
# semana) — periodización ondulante con descarga, estándar en la evidencia.
_WEEK_WHY = [
    ("deload|descarga|recuper", "Semana de DESCARGA a propósito: bajamos volumen e intensidad "
     "para que el cuerpo absorba el trabajo de las semanas anteriores, recuperes "
     "articulaciones y sistema nervioso, y vuelvas más fuerte al siguiente bloque."),
    ("pico|intens", "Semana de PICO: la de mayor intensidad del bloque. Cargas arriba con "
     "poco margen (RIR bajo) para dar el estímulo fuerte que dispara las adaptaciones. "
     "Prioriza técnica, descansos completos y sueño."),
    ("progres", "Semana de PROGRESIÓN: busca superar ligeramente la semana anterior — una "
     "repetición más por serie o +2,5 kg si ya cerraste el rango alto — manteniendo la "
     "técnica. La sobrecarga progresiva es lo que hace crecer fuerza y músculo."),
    ("base|referencia|adapta", "Semana BASE: es tu punto de partida del bloque. Registra "
     "cargas y repeticiones reales con técnica cómoda; las semanas siguientes progresan "
     "sobre estos números."),
]


def current_training_week(db: Session, plan: Plan | None, today: date) -> dict | None:
    """Semana del mesociclo (1-N) que el cliente vive HOY, con su fase, el
    multiplicador de carga respecto a la semana base y el PORQUÉ.

    Anclada al primer día con plan ACTIVO de este mes de entrenamiento
    (mín. published_at del month_index): adaptar el plan a mitad de mes NO
    reinicia la semana. Si el mes se alarga, el ciclo se repite en oleadas.
    """
    if plan is None:
        return None
    # El esquema dice `list[WeeklyProgressionWeek]`, pero a `training_json` le
    # llegan planes editados a mano, importados del Word y copiados de un
    # modelo: si ahí viene un objeto (o una lista de cualquier cosa), el
    # `weeks[idx]` de abajo reventaba con un KeyError y el cliente se quedaba
    # con un 500 y la pantalla de Entreno EN BLANCO. Mismo criterio que el
    # resto de la pantalla: lo que no se entiende se ignora, no se cae.
    weeks = (plan.training_json or {}).get("weekly_progression") or []
    if not isinstance(weeks, list):
        return None
    weeks = [w for w in weeks if isinstance(w, dict)]
    if not weeks:
        return None
    start_dt = db.scalar(
        select(func.min(Plan.published_at)).where(
            Plan.client_id == plan.client_id,
            Plan.month_index == plan.month_index,
            Plan.published_at.is_not(None),
        )
    )
    start = start_dt.date() if start_dt else today
    n = len(weeks)
    idx = (max(0, (today - start).days) // 7) % n
    w = weeks[idx] or {}
    base_pct = (weeks[0] or {}).get("load_pct") or 100
    pct = w.get("load_pct") or base_pct
    factor = (pct / base_pct) if base_pct else 1.0
    intent = str(w.get("intent") or "")
    why = next((txt for pat, txt in _WEEK_WHY if re.search(pat, intent, re.I)),
               w.get("volume_note") or "Sigue la pauta de esta semana tal y como está "
               "programada: cada fase del bloque tiene su función.")
    return {
        "week": w.get("week") or idx + 1,
        "total_weeks": n,
        "intent": intent or None,
        "load_pct": pct,
        "rir_target": w.get("rir_target"),
        "volume_note": w.get("volume_note"),
        "load_factor": round(factor, 3),
        "started_on": start,
        "why": why,
    }


def streak_days(db, client_id: int, today: date) -> int:
    """Días CONSECUTIVOS con el diario rellenado, contando hacia atrás.

    Palanca de adherencia (racha 🔥 del portal): el cliente no quiere romperla.
    Reglas: una fila VACÍA no cuenta (existen — el autosave crea la fila antes
    de teclear); el día de HOY aún sin rellenar no rompe la racha (se rompe al
    terminar el día en blanco). Tope de mirada: 90 días (más que de sobra y la
    consulta se mantiene barata)."""
    from sqlalchemy import and_, or_, select

    from app.models import DailyLog, Period, WorkoutLog

    desde = today - timedelta(days=90)
    # Las SERIES de entreno también son un día registrado: quien más entrena
    # (y un DQR Train no tiene diario de dieta) veía racha 0 y la palanca de
    # adherencia se le volvía en contra.
    tiene_series = (select(WorkoutLog.id)
                    .where(WorkoutLog.daily_log_id == DailyLog.id)
                    .exists())
    # Espejo EXACTO de `push.diary_is_filled`, que descarta el vacío además del
    # nulo. Con solo `is_not(None)`, una nota escrita y borrada dejaba el campo
    # en cadena vacía: la racha contaba ese día y el motor de "sin registros"
    # no, así que el portal decía "🔥 5 días" mientras el panel del coach
    # avisaba de "sin registros desde hace 5 días". Los campos de texto se
    # comparan también contra "" (los numéricos no admiten esa comparación).
    def _relleno(col):
        return col.is_not(None) if col.type.python_type is not str else and_(
            col.is_not(None), col != "")

    con_algo = [
        _relleno(DailyLog.weight_kg), _relleno(DailyLog.sleep_hours),
        _relleno(DailyLog.steps), _relleno(DailyLog.satiety_1_10),
        _relleno(DailyLog.water_liters), _relleno(DailyLog.diet_adherence),
        _relleno(DailyLog.energy_1_5), _relleno(DailyLog.mood_1_5),
        _relleno(DailyLog.fatigue_1_5), _relleno(DailyLog.free_notes),
        DailyLog.chosen_options_json.is_not(None),
        tiene_series,
    ]
    dias = set(db.scalars(
        select(DailyLog.log_date)
        .join(Period, DailyLog.period_id == Period.id)
        .where(Period.client_id == client_id,
               DailyLog.log_date >= desde, DailyLog.log_date <= today,
               or_(*con_algo))
    ))
    if not dias:
        return 0
    racha = 0
    # Hoy vacío no rompe: si hoy no está, se empieza a contar desde ayer.
    cursor = today if today in dias else today - timedelta(days=1)
    while cursor in dias:
        racha += 1
        cursor -= timedelta(days=1)
    return racha


def period_info(period: Period | None, today: date) -> dict | None:
    if period is None:
        return None
    days_total = (period.ends_on - period.starts_on).days + 1
    days_elapsed = max(0, min(days_total, (today - period.starts_on).days + 1))
    days_left = max(0, (period.ends_on - today).days)
    # Cierre disponible desde el día 14 del período (G.4) — o el ÚLTIMO día, si
    # ese período resulta ser más corto (uno abierto a mano, uno recortado al
    # publicar el plan a mitad de ciclo). Con el 14 fijo, un período de 13 días
    # dejaba al cliente en un callejón: el anillo del portal decía "¡toca
    # revisión!" y la pantalla, "disponible al día 14 · se activa el <fecha que
    # YA pasó>". No podía enviarla nunca y solo lo desbloqueaba el coach.
    can_close = days_elapsed >= min(14, days_total) and period.status == "open"
    return {
        "period_id": period.id,
        "period_index": period.period_index,
        "starts_on": period.starts_on,
        "ends_on": period.ends_on,
        "days_total": days_total,
        "days_elapsed": days_elapsed,
        "days_left": days_left,
        "can_close": can_close,
        "status": period.status,
    }


def brand_payload(db: Session) -> dict:
    cfg = db.scalar(select(BrandConfig).limit(1))
    if cfg is None:
        return {
            "name": "Tu asesoría", "color_primary": "#E8833A",
            "color_secondary": "#2E5E8C", "color_bg": "#0B111C",
            "font_family": "Inter", "portal_theme": "light", "logo_path": None,
        }
    return {
        "name": cfg.name, "color_primary": cfg.color_primary,
        "color_secondary": cfg.color_secondary, "color_bg": cfg.color_bg,
        "font_family": cfg.font_family, "portal_theme": cfg.portal_theme,
        "logo_path": cfg.logo_path,
    }


def _meals_for_today(plan: Plan, client: Client, chosen: dict | None) -> list[dict]:
    """Comidas del día desde el plan. Flexible: 7 opciones/slot. Estricto: plato del día."""
    nutrition = plan.nutrition_json or {}
    meal_defs = nutrition.get("meals", [])  # slots con name/time/target
    bank = nutrition.get("meal_bank") or {}
    # El formato lo decide el banco PERSISTIDO (bank["mode"]); diet_mode del
    # cliente es solo fallback. Si el coach cambia diet_mode sin regenerar, el
    # plan servido sigue siendo el que existe, no un menú vacío/equivocado.
    mode = bank.get("mode") or client.diet_mode
    chosen = chosen or {}

    slots_out: list[dict] = []
    for mdef in meal_defs:
        slot = mdef["slot"]
        entry = {
            "slot": slot,
            "name": mdef.get("name", f"Comida {slot}"),
            "time": mdef.get("time", ""),
            "target": mdef.get("target", {}),
            "options": [],
            "chosen_key": chosen.get(str(slot)),
        }
        if mode == "flexible_7":
            for s in bank.get("slots", []):
                if s["slot"] == slot:
                    entry["options"] = [
                        {"key": o.get("key"), "title": o["title"], "macros": o["macros"],
                         "prep_minutes": o.get("prep_minutes"), "tags": o.get("tags", [])}
                        for o in s.get("options", [])
                    ]
                    entry["equivalences"] = s.get("equivalences")
            if not entry["options"] and not entry.get("equivalences"):
                # Plan antiguo con una toma sin banco: el cliente ve igualmente
                # 3 opciones por defecto escaladas a sus macros, nunca un hueco.
                from app.services.meal_fallback import build_fallback_options

                entry["options"] = [
                    {"key": o["key"], "title": o["title"], "macros": o["macros"],
                     "prep_minutes": o.get("prep_minutes"), "tags": o.get("tags", [])}
                    for o in build_fallback_options(
                        mdef, allergies=client.food_allergies or [],
                        dislikes=client.food_dislikes or [],
                        # mismo criterio que el PDF y el Revisor 0: sin el
                        # patrón dietético se colaban pavo/huevo a un vegano
                        # justo en la toma que quedó vacía por seguridad
                        diet_pattern=client.diet_pattern)
                ]
        elif mode == "strict":
            # plato del día = el del weekday actual en el menú cerrado
            today_idx = today_local().weekday()
            slug = DAY_SLUGS[today_idx]
            # Lectura defensiva: el menú cerrado también llega editado a
            # mano o importado del Word, y con una clave de menos el corchete
            # tumbaba la pantalla entera en vez de saltarse ese día.
            for d in bank.get("days") or []:
                if not isinstance(d, dict) or d.get("day") != slug:
                    continue
                for meal in d.get("meals") or []:
                    if not isinstance(meal, dict) or meal.get("slot") != slot:
                        continue
                    dish = meal.get("dish") or {}
                    if not dish.get("title"):
                        continue
                    entry["options"] = [{
                        "key": dish.get("key", "A"), "title": dish["title"],
                        "macros": dish.get("macros") or {},
                        "prep_minutes": dish.get("prep_minutes"),
                        "tags": dish.get("tags", []),
                    }]
        slots_out.append(entry)
    return slots_out


def _biblioteca_de(db: Session, sesiones: list[dict]) -> dict[int, Exercise]:
    """Los ejercicios de VARIAS sesiones en UNA consulta.

    La pantalla de Entreno del portal resolvía la biblioteca una vez POR SESIÓN
    (4-6 consultas por carga, con los mismos ejercicios repetidos entre días) y
    es de las pantallas más visitadas del sistema: la abre cada cliente cada día
    que entrena."""
    ids = {e.get("exercise_id") for s in sesiones for e in (s.get("exercises") or [])
           if e.get("exercise_id") is not None}
    if not ids:
        return {}
    return {ex.id: ex for ex in db.scalars(select(Exercise).where(Exercise.id.in_(ids)))}


def _resolve_session(db: Session, sess: dict, load_factor: float = 1.0,
                     lib: dict[int, Exercise] | None = None) -> dict:
    """Convierte una sesión del plan (con exercise_id) en una sesión con nombres
    de ejercicio y vídeo resueltos desde la biblioteca. `load_factor` ajusta el
    peso sugerido a la SEMANA del mesociclo que vive el cliente (p. ej. 1.05 en
    la semana de pico, 0.6 en la descarga), redondeado a 0,5 kg.

    `lib` (opcional): biblioteca YA resuelta para varias sesiones a la vez."""
    if lib is None:
        ex_ids = [e.get("exercise_id") for e in sess.get("exercises", [])
                  if e.get("exercise_id") is not None]
        lib = {
            ex.id: ex
            for ex in db.scalars(select(Exercise).where(Exercise.id.in_(ex_ids)))
        } if ex_ids else {}
    exercises = []
    for e in sess.get("exercises", []):
        ex = lib.get(e.get("exercise_id"))
        # Vídeo del ejercicio: el archivo SUBIDO (servido por /api/media) tiene
        # prioridad; si no, el enlace externo re-filtrado (solo http(s)) — los
        # datos legados sin esquema no pueden llegar al portal como href.
        video = media_url(ex.video_path) if ex else None
        if not video:
            video = ((ex.video_url or "").strip()) if ex else ""
        hint = e.get("start_weight_hint_kg")
        # Redondeo HALF-UP a 0,5 kg (convención del sistema; round() bancario
        # mostraba 21,0 donde tocaba 21,5). Valor que VE el cliente.
        import math
        week_hint = (math.floor(hint * load_factor * 2 + 0.5) / 2) if isinstance(hint, (int, float)) else None
        # Acceso DEFENSIVO: el resto del bloque ya usa `.get()`, pero estas tres
        # claves se leían con corchete, así que un plan al que le faltara una
        # —editado a mano por el coach, importado del Word, copiado de la
        # biblioteca— tumbaba con un 500 la pantalla ENTERA de Entreno del
        # cliente. Mejor una sesión con un hueco que un portal roto.
        exercises.append({
            "exercise_id": e.get("exercise_id"),
            "name": ex.canonical_name if ex else f"Ejercicio {e.get('exercise_id') or '?'}",
            "sets": e.get("sets") or 0, "rep_range": e.get("rep_range") or "",
            "rir": e.get("rir", ""),
            "rest_sec": e.get("rest_sec", 90),
            "start_weight_hint_kg": e.get("start_weight_hint_kg"),
            "week_weight_hint_kg": week_hint,
            "technique_cue": e.get("technique_cue"),
            # Indicaciones personalizadas del coach (capacidades/limitaciones):
            # el portal las destaca junto al ejercicio.
            "coach_notes": e.get("coach_notes"),
            # Prescripción completa: la regla de progresión, la clave
            # biomecánica y el tempo se escribían en el plan y el cliente del
            # portal no los veía por ningún canal (auditoría 27-08).
            "progression_rule": e.get("progression_rule"),
            "biomech_cue": e.get("biomech_cue"),
            "tempo": e.get("tempo"),
            "video_url": _playable(video),
        })
    return {
        "day": sess.get("day", ""), "name": sess.get("name", ""),
        "warmup": sess.get("warmup"), "exercises": exercises,
        "cooldown": sess.get("cooldown"),
    }


def dia_de_sesion(sess: dict) -> str:
    """El día de una sesión, en minúsculas y a prueba de basura.

    El esquema dice `day: str` ("Lunes"…), pero a `training_json` le llegan
    planes editados a mano, importados del Word y copiados de un modelo. Con un
    `day` numérico —o nulo— el `.strip()` de quien lo leía reventaba con un
    AttributeError: la pantalla "Hoy" del cliente (la más visitada del portal)
    se caía con un 500, y el recordatorio diario se llevaba por delante el
    aviso de TODOS los clientes, no solo el del plan roto."""
    return str(sess.get("day") or "").strip().lower()


def _session_for_today(db: Session, plan: Plan, today: date) -> dict | None:
    """Sesión de entrenamiento que toca hoy según el día de la semana.

    Mapea el weekday actual al `day` de las sesiones del plan (que vienen como
    "Lunes", "Martes"…). Si hoy no hay sesión, es día de descanso → None.
    Los pesos sugeridos van AJUSTADOS a la semana del mesociclo (mismo factor
    que la pestaña Entreno — sin desincronizaciones entre vistas).
    """
    training = plan.training_json or {}
    today_label = DAY_LABELS[today.weekday()].lower()
    week = current_training_week(db, plan, today)
    factor = (week or {}).get("load_factor") or 1.0
    for sess in training.get("sessions", []):
        if dia_de_sesion(sess) == today_label:
            return _resolve_session(db, sess, factor)
    return None


def build_training_sessions(db: Session, client: Client) -> list[dict]:
    """TODAS las sesiones del plan vigente, con nombres de ejercicio resueltos
    y el peso sugerido AJUSTADO a la semana del mesociclo en curso.

    Para el selector de sesión del portal (el cliente registra la que ha hecho,
    no solo la del día)."""
    period = active_period(db, client.id)
    plan = published_plan_for_period(db, period) if period else latest_published_plan(db, client.id)
    if plan is None:
        return []
    week = current_training_week(db, plan, today_local())
    factor = (week or {}).get("load_factor") or 1.0
    training = plan.training_json or {}
    sesiones = training.get("sessions", []) or []
    lib = _biblioteca_de(db, sesiones)  # UNA consulta para todas las sesiones
    return [_resolve_session(db, s, factor, lib) for s in sesiones]


# ------------------------------------------------ recursos del portal ----
# Host de YouTube ANCLADO de verdad: se parsea la URL y se compara el hostname
# entero (no subcadenas ni límites de regex, que también casaban dentro del path:
# "example.com/x//youtu.be/…"). Solo estos hosts producen portada.
_YT_HOSTS = {"youtu.be", "www.youtu.be", "youtube.com", "www.youtube.com", "m.youtube.com",
             "music.youtube.com", "youtube-nocookie.com", "www.youtube-nocookie.com"}
_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def youtube_thumbnail(url: str | None) -> str | None:
    """Portada (hqdefault) si `url` es un vídeo de YouTube; si no, None. Sirve de
    imagen por defecto de los vídeos de ejercicio cuando el coach no sube una."""
    if not url:
        return None
    from urllib.parse import parse_qs, urlsplit

    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    host = (parts.hostname or "").lower()
    if host not in _YT_HOSTS:
        return None
    vid: str | None = None
    segs = [s for s in parts.path.split("/") if s]
    if host in ("youtu.be", "www.youtu.be"):
        vid = segs[0] if segs else None
    elif segs and segs[0] == "watch":
        vid = (parse_qs(parts.query).get("v") or [None])[0]
    elif len(segs) >= 2 and segs[0] in ("embed", "shorts", "v", "live"):
        vid = segs[1]
    return f"https://img.youtube.com/vi/{vid}/hqdefault.jpg" if vid and _YT_ID.fullmatch(vid) else None


def discount_buy_url(product_url: str | None, code: str | None,
                     store_url: str | None) -> str | None:
    """URL de compra con el código de descuento PRE-APLICADO al carrito, usando
    el patrón universal de las tiendas Shopify (/discount/CODE?redirect=…),
    como la del partner (ESN). Solo se construye cuando el producto es de la
    tienda del partner (mismo dominio) — en otros dominios no sabemos si el
    patrón existe y se devuelve el enlace normal del producto."""
    from urllib.parse import quote, urlsplit

    if not product_url or not code or not store_url:
        return product_url
    try:
        pu, su = urlsplit(product_url), urlsplit(store_url)
    except ValueError:
        return product_url
    if not pu.netloc or pu.netloc.lower() != su.netloc.lower():
        return product_url
    path = pu.path or "/"
    if pu.query:
        path += "?" + pu.query
    return (f"{pu.scheme}://{pu.netloc}/discount/{quote(code, safe='')}"
            f"?redirect={quote(path, safe='')}")


def product_image_url(p: RecommendedProduct) -> str | None:
    """URL efectiva de la imagen de un producto: la subida (servida por la API,
    con cache-busting por updated_at) tiene prioridad; si no, la URL externa.

    Si la ficha dice que hay imagen subida pero el FICHERO ya no está —una
    restauración de la base sin el volumen de storage, un borrado a mano— se
    cae a la URL externa en vez de prometer una imagen que devuelve 404: en
    Recursos y en el portal del cliente salía un hueco roto por cada producto.
    """
    if p.image_path:
        try:
            from app.services.storage import abs_path

            if abs_path(p.image_path).exists():
                ver = int(p.updated_at.timestamp()) if p.updated_at else 0
                return f"/api/resources/products/{p.id}/image?v={ver}"
        except Exception:  # noqa: BLE001 — una ruta rara no puede tumbar la lista
            pass
    return p.image_url or None


def build_resources(db: Session, client: Client) -> dict:
    """Sección "Recursos" del portal: vídeos de los ejercicios de la rutina
    vigente (solo los que tienen vídeo, en el orden en que aparecen en el plan,
    sin duplicados) + catálogo de productos recomendados activos."""
    period = active_period(db, client.id)
    plan = published_plan_for_period(db, period) if period else latest_published_plan(db, client.id)

    videos: list[dict] = []
    ordered_ids: list[int] = []
    if plan is not None:
        seen: set[int] = set()
        for sess in (plan.training_json or {}).get("sessions", []):
            for e in sess.get("exercises", []):
                eid = e.get("exercise_id")
                if isinstance(eid, int) and eid not in seen:
                    seen.add(eid)
                    ordered_ids.append(eid)
    brand = db.scalar(select(BrandConfig).limit(1))
    cover = media_url(brand.video_cover_path) if brand else None
    # Código de descuento ÚNICO del coach: si está configurado (Recursos →
    # Página de enlaces) manda sobre el de cada producto — cambiarlo allí lo
    # cambia en el portal, en la landing y en todas partes a la vez.
    global_code = (brand.partner_discount_code or "").strip() if brand else ""

    if ordered_ids:
        lib = {ex.id: ex for ex in db.scalars(select(Exercise).where(Exercise.id.in_(ordered_ids)))}
        for eid in ordered_ids:
            ex = lib.get(eid)
            if ex is None:
                continue
            # El vídeo SUBIDO (archivo, /api/media) manda; si no, el enlace
            # externo re-filtrado — los datos LEGADOS (guardados antes del
            # validador de entrada) no pueden llegar al portal como href/src
            # sin esquema http(s).
            video = _playable(media_url(ex.video_path) or ex.video_url)
            if not video:
                continue
            image = (ex.image_url or "").strip()
            # Portada: la GLOBAL (una para todos los vídeos) tiene prioridad;
            # sin ella, la imagen propia o la derivada de YouTube.
            videos.append({
                "exercise_id": ex.id,
                "title": ex.canonical_name,
                "muscle": ex.muscle_primary,
                "video_url": video,
                "image_url": cover or _playable(image) or youtube_thumbnail(video),
                "technique_notes": ex.technique_notes,
            })

    product_rows = db.scalars(
        select(RecommendedProduct)
        .where(RecommendedProduct.active.is_(True))
        .order_by(RecommendedProduct.sort_order, RecommendedProduct.id)
    ).all()

    # Productos DE SU PLANIFICACIÓN primero: los que corresponden a los
    # suplementos pautados en su plan van destacados (in_plan) y arriba.
    from app.services.product_match import match_products, plan_supplement_names

    supplements = plan_supplement_names(plan.nutrition_json if plan else None)
    covered = match_products(supplements, [p.title for p in product_rows])["covered_titles"]

    store_url = (brand.partner_store_url or "").strip() if brand else ""
    products = [{
        "id": p.id,
        "title": p.title,
        "description": p.description,
        "url": p.url,
        # URL de COMPRA: si la tienda lo soporta (patrón /discount/ de las
        # tiendas Shopify, como la del partner), abre el producto con el código
        # ya aplicado al carrito; si no aplica, el enlace normal del producto.
        "buy_url": discount_buy_url(p.url, global_code or p.discount_code, store_url),
        "category": p.category,
        "image_url": product_image_url(p),
        "discount_code": global_code or p.discount_code,
        "in_plan": p.title in covered,
    } for p in product_rows]
    products.sort(key=lambda x: (not x["in_plan"]))

    return {"exercise_videos": videos, "products": products}


def build_today_view(db: Session, client: Client, today: date) -> dict:
    period = active_period(db, client.id)
    plan = published_plan_for_period(db, period) if period else latest_published_plan(db, client.id)

    meals: list[dict] = []
    session = None
    already_logged = False

    if plan is not None:
        chosen = None
        if period is not None:
            log = db.scalar(
                select(DailyLog).where(
                    DailyLog.period_id == period.id, DailyLog.log_date == today
                )
            )
            if log is not None:
                already_logged = True
                chosen = log.chosen_options_json
        meals = _meals_for_today(plan, client, chosen)
        session = _session_for_today(db, plan, today)

    return {
        "date": today,
        "day_label": DAY_LABELS[today.weekday()],
        "period": period_info(period, today),
        "meals": meals,
        "session": session,
        "already_logged": already_logged,
    }
