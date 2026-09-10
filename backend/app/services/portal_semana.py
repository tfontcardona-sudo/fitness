"""TU SEMANA: lo que el cliente hizo, dicho como se lo diría su coach.

El portal enseñaba lo que hay que hacer HOY. Lo que faltaba —y es lo que pidió
el dueño— es lo de ATRÁS: qué hiciste la semana pasada, cuántos kilos movías en
tu último press, si tu peso va donde tiene que ir. Un cliente que ve su
progreso vuelve; uno que solo ve tareas, se cansa.

TODO DETERMINISTA. Ni una llamada a la IA: son datos que ya están en la base
(diario, series, pesajes) contados con las mismas reglas que usa el coach
—`push.dias_registrados` decide qué es "un día registrado", `metrics.e1rm`
calcula la fuerza—, así que el portal y el panel nunca se contradicen.

Y los CONSEJOS son reglas, no frases motivacionales al azar: se disparan por lo
que de verdad pasa (llevas 4 días sin pesarte, tu banca sube, te queda un día
para la revisión). Un consejo que no mira tus datos es ruido, y el cliente
aprende a ignorarlo.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Client, DailyLog, Exercise, Period, WorkoutLog

# La ventana que el cliente entiende por "esta semana".
DIAS_SEMANA = 7


@dataclass
class Consejo:
    """Un consejo con su motivo. `tono` decide el color, no el capricho."""

    texto: str
    tono: str = "info"      # info | bien | ojo


def _periodo_vivo(db: Session, client_id: int) -> Period | None:
    return db.scalar(
        select(Period).where(Period.client_id == client_id)
        .order_by(Period.period_index.desc()).limit(1))


def _logs(db: Session, period_id: int, desde: date, hasta: date) -> list[DailyLog]:
    return list(db.scalars(
        select(DailyLog).where(DailyLog.period_id == period_id,
                               DailyLog.log_date >= desde, DailyLog.log_date <= hasta)
        .order_by(DailyLog.log_date)))


def _ultima_sesion(db: Session, logs: list[DailyLog]) -> dict | None:
    """La última sesión con series registradas, en una frase con datos.

    "El lunes hiciste 18 series · lo más pesado, press banca 62,5 kg × 8". Es el
    recordatorio que el dueño pidió: el cliente llega al gimnasio sabiendo de
    dónde viene, sin abrir nada."""
    if not logs:
        return None
    por_log = {lg.id: lg for lg in logs}
    filas = list(db.scalars(
        select(WorkoutLog).where(WorkoutLog.daily_log_id.in_(list(por_log)))))
    if not filas:
        return None
    # La fecha más reciente que tenga series.
    fechas = {por_log[f.daily_log_id].log_date for f in filas if f.daily_log_id in por_log}
    if not fechas:
        return None
    ultima = max(fechas)
    ids_de_ese_dia = {lg.id for lg in logs if lg.log_date == ultima}
    del_dia = [f for f in filas if f.daily_log_id in ids_de_ese_dia]
    if not del_dia:
        return None

    # La serie MÁS PESADA del día, con el nombre del ejercicio.
    mejor = None
    for f in del_dia:
        peso = float(getattr(f, "weight_kg", 0) or 0)
        if peso <= 0:
            continue
        if mejor is None or peso > float(getattr(mejor, "weight_kg", 0) or 0):
            mejor = f
    nombre = None
    if mejor is not None and getattr(mejor, "exercise_id", None):
        nombre = db.scalar(
            select(Exercise.canonical_name).where(Exercise.id == mejor.exercise_id))
    return {
        "fecha": ultima.isoformat(),
        "dia": _dia_es(ultima),
        "series": len(del_dia),
        "top_ejercicio": nombre,
        "top_peso_kg": (float(mejor.weight_kg) if mejor is not None
                        and getattr(mejor, "weight_kg", None) else None),
        "top_reps": (int(mejor.reps) if mejor is not None
                     and getattr(mejor, "reps", None) else None),
    }


_DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


def _dia_es(d: date) -> str:
    return _DIAS[d.weekday()]


def _pesajes(logs: list[DailyLog]) -> list[tuple[date, float]]:
    return [(lg.log_date, float(lg.weight_kg)) for lg in logs if lg.weight_kg]


def lo_de_hoy(db: Session, client: Client, periodo: Period | None, hoy: date) -> dict:
    """QUÉ TOCA HOY y qué está ya hecho: entrenar, el diario, la revisión.

    El portal enseñaba una lista de tarjetas informativas y dejaba media
    pantalla en blanco: al abrirlo no se sabía «¿qué tengo que hacer ahora?».
    Esto lo dice en tres líneas, con lo hecho marcado.

    Determinista y con las MISMAS reglas que el resto del sistema: «día
    registrado» lo decide `push.dias_registrados` y la sesión del día sale del
    plan publicado, igual que la pantalla de Entreno."""
    fuera = {"entrena_hoy": False, "sesion": None, "entreno_hecho": False,
             "diario_hecho": False, "toca_revision": False}
    if periodo is None or periodo.status != "open":
        return fuera
    if not (periodo.starts_on <= hoy <= periodo.ends_on):
        # Período vencido y sin cerrar: lo único que toca es la revisión.
        from app.services import portal as portal_svc

        info = portal_svc.period_info(periodo, hoy) or {}
        fuera["toca_revision"] = bool(info.get("can_close"))
        return fuera

    from app.services import portal as portal_svc
    from app.services.push import diary_is_filled, has_session_on

    log = db.scalar(select(DailyLog).where(
        DailyLog.period_id == periodo.id, DailyLog.log_date == hoy))
    fuera["diario_hecho"] = bool(diary_is_filled(log))

    plan = portal_svc.published_plan_for_period(db, periodo)
    if plan is not None and has_session_on(plan.training_json, hoy):
        fuera["entrena_hoy"] = True
        fuera["sesion"] = _nombre_de_la_sesion(plan.training_json, hoy)
        if log is not None:
            fuera["entreno_hecho"] = bool(db.scalar(
                select(WorkoutLog.id).where(WorkoutLog.daily_log_id == log.id).limit(1)))

    info = portal_svc.period_info(periodo, hoy) or {}
    fuera["toca_revision"] = bool(info.get("can_close"))
    return fuera


def _nombre_de_la_sesion(training: dict | None, hoy: date) -> str | None:
    """«Torso A» — para que el cliente sepa qué le espera sin abrir nada.

    Con el MISMO lector de días que `push.has_session_on` y que la pantalla de
    Entreno (`portal.dia_de_sesion`): dos formas de leer "¿es hoy?" acaban
    siempre en una pantalla diciendo que hoy entrenas y otra diciendo que no."""
    if not isinstance(training, dict):
        return None
    from app.services import portal as portal_svc

    etiqueta = portal_svc.DAY_LABELS[hoy.weekday()].lower()
    for sesion in training.get("sessions") or []:
        if not isinstance(sesion, dict):
            continue
        if portal_svc.dia_de_sesion(sesion) == etiqueta:
            return str(sesion.get("name") or "").strip() or None
    return None


def resumen(db: Session, client: Client, hoy: date) -> dict:
    """Lo que el cliente ha hecho, con sus consejos. Sin IA y sin sorpresas:
    si no hay datos, se dice que no los hay en vez de rellenar con humo."""
    periodo = _periodo_vivo(db, client.id)
    vacio = {"dias_registrados": 0, "dias_objetivo": DIAS_SEMANA, "series": 0,
             "peso_delta_kg": None, "ultima_sesion": None, "consejos": [],
             "racha": 0, "hoy": lo_de_hoy(db, client, None, hoy)}
    if periodo is None:
        return vacio

    desde = hoy - timedelta(days=DIAS_SEMANA - 1)
    logs = _logs(db, periodo.id, desde, hoy)
    from app.services.push import dias_registrados

    dias = dias_registrados(db, logs)
    series = int(db.scalar(
        select(func.count(WorkoutLog.id))
        .where(WorkoutLog.daily_log_id.in_([lg.id for lg in logs]))) or 0) if logs else 0

    # Peso: el de toda la QUINCENA, no el de la semana — con siete días el ruido
    # diario se come la señal y el cliente lee subidas que no existen.
    logs_periodo = _logs(db, periodo.id, periodo.starts_on or desde, hoy)
    pesos = _pesajes(logs_periodo)
    delta = round(pesos[-1][1] - pesos[0][1], 1) if len(pesos) >= 3 else None

    from app.services.portal import streak_days

    datos = {
        "dias_registrados": len(dias),
        "dias_objetivo": DIAS_SEMANA,
        "series": series,
        "peso_delta_kg": delta,
        "ultima_sesion": _ultima_sesion(db, logs),
        "racha": streak_days(db, client.id, hoy),
        "hoy": lo_de_hoy(db, client, periodo, hoy),
    }
    datos["consejos"] = [
        {"texto": c.texto, "tono": c.tono}
        for c in consejos(client, datos, pesos, hoy, periodo)
    ]
    return datos


def consejos(client: Client, datos: dict, pesos: list, hoy: date,
             periodo: Period) -> list[Consejo]:
    """Los consejos, por REGLAS sobre sus datos reales. Como mucho tres: una
    lista larga se lee como un muro y no se lee ninguna."""
    out: list[Consejo] = []

    # 1. Lo que BLOQUEA la revisión: sin pesajes no hay con qué ajustar el plan.
    dias_sin_pesar = None
    if pesos:
        dias_sin_pesar = (hoy - pesos[-1][0]).days
    if not pesos:
        out.append(Consejo("Pésate un par de veces esta semana: sin ese dato tu "
                           "coach no puede ajustarte el plan.", "ojo"))
    elif dias_sin_pesar is not None and dias_sin_pesar >= 4:
        out.append(Consejo(f"Llevas {dias_sin_pesar} días sin pesarte. Con dos o "
                           "tres pesajes por semana basta.", "ojo"))

    # 2. Lo que va BIEN, dicho con el número (que es lo que lo hace creíble).
    delta = datos.get("peso_delta_kg")
    objetivo = (client.goal_type or "")
    if isinstance(delta, (int, float)) and abs(delta) >= 0.5:
        baja = delta < 0
        va_bien = (baja and objetivo == "fat_loss") or (not baja and objetivo == "muscle_gain")
        signo = "−" if baja else "+"
        texto = f"{signo}{abs(delta):g} kg en esta quincena".replace(".", ",")
        out.append(Consejo(f"{texto}: vas donde toca." if va_bien else f"{texto}.",
                           "bien" if va_bien else "info"))

    # 3. La constancia, con su cifra.
    dias = int(datos.get("dias_registrados") or 0)
    if dias >= 6:
        out.append(Consejo(f"{dias} de 7 días registrados. Esto es lo que hace "
                           "que el plan del mes que viene sea bueno.", "bien"))
    elif dias <= 2:
        out.append(Consejo("Apunta el día aunque sea a medias: media hoja vale "
                           "más que una en blanco.", "ojo"))

    # 4. La revisión que viene (solo si está a la vuelta de la esquina).
    if periodo.ends_on:
        faltan = (periodo.ends_on - hoy).days
        if 0 <= faltan <= 2:
            cuando = ("hoy" if faltan == 0 else "mañana" if faltan == 1
                      else f"en {faltan} días")
            out.append(Consejo(f"Tu revisión quincenal es {cuando}.", "info"))
    return out[:3]
