"""DE QUÉ HAY QUE HABLARLE HOY A ESTE CLIENTE.

La ronda diaria mandaba a TODO el mundo el mismo tema —el brief del día— con
el nombre cambiado. Funciona como recordatorio, pero no es lo que un cliente
que paga por un coach espera leer: si lleva cinco días durmiendo cinco horas,
o si esta semana ha entrenado uno de los cuatro días que tiene pautados, de
eso es de lo que hay que hablarle, y no del truco del batch cooking que tocaba
en el pool.

CÓMO SE DECIDE, y por qué así: el tema NO lo elige un modelo. Se calcula aquí,
con reglas sobre sus datos, igual que los números del plan. Un modelo leyendo
un diario "vería" tendencias que no están y hablaría de un mal sueño que no ha
registrado; una regla solo habla de lo que consta, dice el dato exacto que la
dispara y se puede leer, discutir y corregir. La IA sigue haciendo lo que sabe
hacer: REDACTARLO como una persona.

Y si no hay nada que destacar —el cliente va bien y al día— no se fuerza un
tema: se devuelve la lista vacía y la ronda usa su brief genérico, que para eso
está. Inventarle un problema a quien no lo tiene es peor que no escribirle.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ChangeRequest, DailyLog, Period, WorkoutLog

# Cuántos días atrás se mira. Dos semanas es el ciclo del sistema; más allá, lo
# que pasó pertenece a la quincena anterior y ya se habló en su revisión.
VENTANA_DIAS = 14
# La ventana CORTA, la de "cómo va esta semana".
VENTANA_CORTA = 7


@dataclass(frozen=True)
class Foco:
    """Una cosa concreta de la que hablarle, con el dato que la justifica.

    `key` es estable (el mismo problema, el mismo nombre) para no repetir tema
    dos días seguidos; `dato` es literal y va al prompt tal cual, de modo que
    la IA no tenga que deducir ninguna cifra.
    """

    key: str
    prioridad: int
    tema: str
    guia: str
    dato: str
    # La frase ya escrita, EN SEGUNDA PERSONA, para el día que la IA no esté.
    # `dato` está redactado para el prompt (habla del cliente en tercera
    # persona) y usarlo tal cual daba mensajes en un castellano raro: "Lleva 14
    # días sin registrar. Que lleva días sin apuntar nada: cuéntame".
    reserva: str = ""
    # A quién le aplica: un tema de dieta no se le manda a un cliente que solo
    # tiene entrenamiento (le estaríamos hablando de algo que no ha contratado).
    scope: str = "any"


def _media(valores: list[float]) -> float:
    return sum(valores) / len(valores)


def _fmt(x: float, dec: int = 1) -> str:
    """Cifra en castellano: coma decimal y sin decimales de adorno."""
    s = f"{x:.{dec}f}".rstrip("0").rstrip(".")
    return (s or "0").replace(".", ",")


def _logs_recientes(db: Session, client_id: int, hoy: date) -> list[DailyLog]:
    """Diarios de los últimos días, del período que sea.

    A caballo entre dos quincenas hay dos períodos abiertos/cerrados y mirar
    solo el abierto dejaba al cliente "sin datos" justo el día después de una
    revisión, que es cuando más atención necesita.
    """
    desde = hoy - timedelta(days=VENTANA_DIAS)
    return list(db.scalars(
        select(DailyLog)
        .join(Period, Period.id == DailyLog.period_id)
        .where(Period.client_id == client_id, DailyLog.log_date >= desde,
               DailyLog.log_date <= hoy)
        .order_by(DailyLog.log_date)
    ))


def focos_de(db: Session, client, *, hoy: date,
             has_nutrition: bool = True, has_training: bool = True) -> list[Foco]:
    """Lo que hoy merece un mensaje, de lo más importante a lo menos.

    Nunca lanza: un fallo leyendo el diario deja la ronda sin foco (mensaje
    genérico), jamás sin mensaje.
    """
    try:
        return _focos(db, client, hoy=hoy, has_nutrition=has_nutrition,
                      has_training=has_training)
    except Exception:  # noqa: BLE001 — el foco es una mejora, nunca un bloqueo
        return []


def _focos(db: Session, client, *, hoy: date,
           has_nutrition: bool, has_training: bool) -> list[Foco]:
    out: list[Foco] = []
    logs = _logs_recientes(db, client.id, hoy)
    recientes = [lg for lg in logs if lg.log_date >= hoy - timedelta(days=VENTANA_CORTA)]
    periodo = db.scalar(
        select(Period).where(Period.client_id == client.id, Period.status == "open")
        .order_by(Period.period_index.desc()).limit(1))
    # Día de la quincena. Sirve para dos cosas: saber en qué punto del ciclo
    # está y no acusar de "llevas días sin apuntar" a quien empezó ayer.
    dia = ((hoy - periodo.starts_on).days + 1) if periodo and periodo.starts_on else None

    # --- 1. LO QUE ÉL HA DICHO. Manda sobre cualquier cosa que digan sus datos:
    # si ha escrito preguntando algo, el mensaje del día es responderle.
    peticion = db.scalar(
        select(ChangeRequest).where(ChangeRequest.client_id == client.id,
                                    ChangeRequest.status == "open")
        .order_by(ChangeRequest.created_at.desc()).limit(1))
    if peticion is not None:
        out.append(Foco(
            "peticion_abierta", 1,
            "responder a lo que te ha escrito",
            "Responde a su mensaje: dile que lo has visto, contesta a lo que "
            "plantea y cierra con lo que vas a hacer.",
            f"Te escribió: «{(peticion.message or '').strip()[:200]}»",
            "He visto tu mensaje. Dame un rato y te contesto con calma."))

    # Una duda en el diario (con interrogante) es lo mismo por otra puerta: el
    # cliente pregunta donde está escribiendo, no donde toca.
    for lg in reversed(recientes):
        nota = (lg.free_notes or "").strip()
        if "?" in nota or "¿" in nota:
            out.append(Foco(
                "duda_en_el_diario", 2,
                "la duda que dejó escrita en su diario",
                "Contéstale a lo que preguntó en su diario, en concreto y sin "
                "rodeos.",
                f"El {lg.log_date.strftime('%d/%m')} escribió: «{nota[:180]}»",
                "He leído la duda que dejaste en tu diario. Te contesto hoy mismo."))
            break

    # --- 2. SEGURIDAD Y ABANDONO. Antes que cualquier consejo.
    dias_con_algo = _dias_con_algo(db, recientes)
    sin_registrar = _dias_seguidos_sin_registrar(dias_con_algo, hoy, desde=(
        periodo.starts_on if periodo and periodo.starts_on else None))
    # SIN QUINCENA ABIERTA no hay de dónde faltar: al cliente al que el coach
    # todavía no le ha arrancado el seguimiento no se le puede decir que lleva
    # dos semanas desaparecido — no tenía dónde apuntar nada.
    if periodo is not None and sin_registrar >= 3:
        out.append(Foco(
            "sin_registros", 2,
            "que lleva días sin apuntar nada",
            "Pregúntale qué tal va sin reproche: interésate por si ha pasado "
            "algo y ponle fácil retomarlo hoy mismo.",
            f"Lleva {sin_registrar} días seguidos sin registrar nada en la app",
            "Te veo desconectado estos días, ¿va todo bien? Con que apuntes hoy "
            "algo, ya volvemos."))

    pesos = [(lg.log_date, lg.weight_kg) for lg in logs if lg.weight_kg]
    ritmo = _ritmo_semanal(pesos)
    if ritmo is not None and has_nutrition and client.goal_type in (
            "fat_loss", "recomp", "maintenance"):
        # Bajar más rápido de lo que toca no es una buena noticia: es el aviso
        # de que se está perdiendo músculo y de que el plan no se está siguiendo
        # como está escrito.
        peso_ref = pesos[-1][1]
        pct = abs(ritmo) / peso_ref * 100 if peso_ref else 0
        if ritmo < 0 and pct > 1.0:
            out.append(Foco(
                "peso_rapido", 2,
                "que está bajando demasiado rápido",
                "Dile que eso es más rápido de lo que interesa, pregúntale si "
                "está comiendo todo lo pautado y recuérdale que la prisa aquí "
                "se paga en músculo.",
                f"Está bajando {_fmt(abs(ritmo))} kg por semana "
                f"({_fmt(pct)} % de su peso)",
                "Estás bajando más rápido de lo que nos interesa. ¿Te estás "
                "comiendo todo lo que tienes pautado?", scope="nutri"))

    # --- 3. LO QUE SE PUEDE CORREGIR ESTA SEMANA.
    if has_training:
        hechas = _sesiones_de_la_semana(db, recientes)
        pautadas = int(client.training_days or 0)
        # Solo con la semana ya empezada: en el día 2 de su plan nadie ha hecho
        # cuatro sesiones, y decírselo sería regañarle por ir al día.
        if pautadas and hechas < pautadas - 1 and (dia is None or dia >= 5):
            out.append(Foco(
                "entreno_por_debajo", 3,
                "que esta semana ha entrenado menos de lo pautado",
                "Pregúntale qué se lo ha impedido y ayúdale a encajar las "
                "sesiones que quedan, sin culpabilizar.",
                f"Esta semana ha registrado {hechas} de {pautadas} sesiones",
                f"Esta semana te veo en {hechas} de tus {pautadas} sesiones. "
                "¿Qué te lo está complicando?", scope="train"))

    suenos = [lg.sleep_hours for lg in recientes if lg.sleep_hours]
    if len(suenos) >= 3 and _media(suenos) < 6.0:
        out.append(Foco(
            "sueno_bajo", 3,
            "que está durmiendo poco",
            "Pregúntale por el sueño: qué le está quitando horas y qué puede "
            "mover para dormir algo más. Sin recetas médicas.",
            f"Duerme {_fmt(_media(suenos))} h de media en sus últimos "
            f"{len(suenos)} registros",
            f"Te veo durmiendo {_fmt(_media(suenos))} h de media esta semana. "
            "¿Qué te está quitando horas?"))

    fatigas = [lg.fatigue_1_5 for lg in recientes if lg.fatigue_1_5]
    if len([f for f in fatigas if f >= 4]) >= 2:
        out.append(Foco(
            "fatiga_alta", 3,
            "que está acumulando fatiga",
            "Pregúntale cómo se está encontrando en los entrenos y si nota que "
            "le cuesta más de lo normal.",
            f"Ha marcado fatiga alta {len([f for f in fatigas if f >= 4])} días "
            f"de los últimos {len(fatigas)} registrados",
            "Te veo con bastante fatiga estos días. ¿Cómo te encuentras en los "
            "entrenos?", scope="train"))

    animos = [lg.mood_1_5 for lg in recientes if lg.mood_1_5]
    if len([m for m in animos if m <= 2]) >= 2:
        out.append(Foco(
            "animo_bajo", 3,
            "que anda de bajón",
            "Interésate por cómo está, sin dramatizar y sin consejo médico. "
            "Que sepa que lo has visto y que estás ahí.",
            f"Ha marcado el ánimo bajo {len([m for m in animos if m <= 2])} de "
            f"sus últimos {len(animos)} registros",
            "Te he visto un poco de bajón estos días. ¿Cómo andas?"))

    if has_nutrition:
        nos = len([lg for lg in recientes if lg.diet_adherence == "no"])
        if nos >= 2:
            out.append(Foco(
                "adherencia_baja", 3,
                "que le está costando seguir la dieta",
                "Pregúntale qué toma se le está atragantando y ofrécele "
                "cambiarla por algo que sí le encaje.",
                f"Ha marcado que no siguió la dieta en {nos} de los últimos "
                f"{len(recientes)} días",
                "Esta semana te veo que la dieta se te está atragantando. ¿Qué "
                "toma es la que peor llevas?", scope="nutri"))

        saciedades = [lg.satiety_1_10 for lg in recientes if lg.satiety_1_10]
        if len([s for s in saciedades if s <= 3]) >= 2:
            out.append(Foco(
                "hambre", 4,
                "que se está quedando con hambre",
                "Pregúntale en qué momento del día pasa hambre: con eso se "
                "puede recolocar el reparto sin tocar el total.",
                f"Ha marcado saciedad baja {len([s for s in saciedades if s <= 3])} "
                f"días de los últimos {len(saciedades)} registrados",
                "Te veo pasando hambre algún día. ¿En qué momento se te hace "
                "más duro?", scope="nutri"))

    # --- 4. EL CICLO. Dónde está dentro de su quincena.
    if dia is not None:
        if 12 <= dia <= 15:
            out.append(Foco(
                "cierre_cerca", 2,
                "que se le acaba la quincena",
                "Recuérdale que toca cerrar la revisión: peso, medidas, fotos "
                "y cómo se ha encontrado. Díselo como algo fácil, no como un "
                "trámite.",
                f"Va por el día {dia} de su quincena",
                "Ya casi tienes la quincena. Cuando puedas cierra tu revisión: "
                "peso, medidas y fotos."))
        elif dia <= 2:
            out.append(Foco(
                "arranque", 4,
                "que acaba de empezar plan nuevo",
                "Pregúntale qué tal el arranque con lo nuevo y si hay algo que "
                "no le encaje, que ahora es cuando se ajusta.",
                f"Está en el día {dia} de su plan nuevo",
                "¿Qué tal el arranque con lo nuevo? Si algo no te encaja, "
                "dímelo y lo ajustamos."))
        elif has_nutrition and dia >= 6 and periodo is not None:
            pesajes = len([p for p in pesos if p[0] >= periodo.starts_on])
            if pesajes <= 1:
                out.append(Foco(
                    "sin_pesajes", 3,
                    "que no se está pesando",
                    "Pídele que se pese por las mañanas: sin ese dato la "
                    "revisión de la quincena se queda sin con qué ajustar.",
                    f"Lleva {pesajes} pesaje(s) en lo que va de quincena",
                    "Necesito que te peses por las mañanas: sin ese dato me "
                    "quedo sin con qué ajustarte la próxima quincena.",
                    scope="nutri"))

    # --- 5. LO BUENO. A un cliente al que solo se le escribe cuando algo va mal
    # le acaban dando miedo los mensajes de su coach.
    racha = _racha(dias_con_algo, hoy)
    if racha >= 7:
        out.append(Foco(
            "racha", 5,
            "su racha de constancia",
            "Reconóceselo con naturalidad, sin exagerar, y pregúntale cómo lo "
            "está llevando.",
            f"Lleva {racha} días seguidos registrando",
            f"{racha} días seguidos apuntando: así da gusto. ¿Cómo lo llevas?"))

    if has_training:
        marca = _mejor_marca_reciente(db, recientes, hoy)
        if marca:
            out.append(Foco(
                "mejor_marca", 5,
                "la marca que acaba de hacer",
                "Felicítale por esa serie en concreto y enlázalo con lo que "
                "viene: de eso se trata.",
                marca,
                "¡Buena marca la de tu último entreno! Seguimos por ahí.",
                scope="train"))

    out.sort(key=lambda f: f.prioridad)
    return [f for f in out if _aplica(f, has_nutrition=has_nutrition,
                                      has_training=has_training)]


def _aplica(foco: Foco, *, has_nutrition: bool, has_training: bool) -> bool:
    if foco.scope == "nutri":
        return has_nutrition
    if foco.scope == "train":
        return has_training
    return True


def _dias_con_algo(db: Session, logs: list[DailyLog]) -> set[date]:
    """Los días en que registró algo, con la MISMA regla que el resto del
    sistema (`push.dias_registrados`): cuentan el diario relleno, las SERIES de
    entreno y las comidas elegidas. Una consulta para todos los días y no una
    por día: esto corre con la cartera entera delante."""
    from app.services.push import dias_registrados

    return dias_registrados(db, logs) if logs else set()


def _dias_seguidos_sin_registrar(dias: set[date], hoy: date,
                                 *, desde: date | None = None) -> int:
    """Días seguidos sin registro contando desde AYER.

    Hoy no cuenta: a media mañana nadie ha rellenado su diario todavía, y
    contarlo convertía cada mañana en un cliente "abandonado". Y no se mira
    ANTES de que empezara su quincena: a quien arrancó ayer no se le puede
    decir que lleva dos semanas desaparecido.
    """
    n = 0
    d = hoy - timedelta(days=1)
    while d not in dias and n < VENTANA_DIAS and (desde is None or d >= desde):
        n += 1
        d -= timedelta(days=1)
    return n


def _racha(dias: set[date], hoy: date) -> int:
    """Días seguidos CON registro. Arranca en hoy si hoy ya registró, y si no
    en ayer: una racha no se rompe porque sea por la mañana."""
    inicio = hoy if hoy in dias else hoy - timedelta(days=1)
    n, d = 0, inicio
    while d in dias and n < VENTANA_DIAS:
        n += 1
        d -= timedelta(days=1)
    return n


def _sesiones_de_la_semana(db: Session, logs: list[DailyLog]) -> int:
    """Días de los últimos siete con al menos una serie registrada."""
    if not logs:
        return 0
    ids = {lg.id: lg.log_date for lg in logs}
    con_series = set(db.scalars(
        select(WorkoutLog.daily_log_id).where(WorkoutLog.daily_log_id.in_(list(ids)))))
    return len({ids[i] for i in con_series if i in ids})


def _ritmo_semanal(pesos: list[tuple[date, float]]) -> float | None:
    """kg por semana entre la primera y la última mitad de los pesajes.

    Media de mitades y no dos puntos sueltos: el peso de un día concreto se
    mueve un kilo por la sal de la cena, y con dos puntos cualquiera el
    mensaje habría acusado de un "bajón" que es agua.
    """
    if len(pesos) < 4:
        return None
    mitad = len(pesos) // 2
    v1 = _media([p for _, p in pesos[:mitad]])
    v2 = _media([p for _, p in pesos[mitad:]])
    d1 = _media([p.toordinal() for p, _ in pesos[:mitad]])
    d2 = _media([p.toordinal() for p, _ in pesos[mitad:]])
    if d2 - d1 < 3:
        return None
    return (v2 - v1) / (d2 - d1) * 7


def _mejor_marca_reciente(db: Session, logs: list[DailyLog], hoy: date) -> str | None:
    """Una serie de los últimos 3 días que sea la mejor del cliente en ese
    ejercicio dentro de la ventana. Sin nombre de ejercicio no se dice nada:
    "has mejorado" sin decir en qué no es un reconocimiento, es un relleno."""
    from app.models import Exercise

    if not logs:
        return None
    ids = {lg.id: lg.log_date for lg in logs}
    series = list(db.scalars(
        select(WorkoutLog).where(WorkoutLog.daily_log_id.in_(list(ids)))))
    mejor: dict[int, tuple[float, date]] = {}
    for s in series:
        if not s.exercise_id or not s.weight_kg or not s.reps:
            continue
        fecha = ids.get(s.daily_log_id)
        if fecha is None:
            continue
        previo = mejor.get(s.exercise_id)
        if previo is None or s.weight_kg > previo[0]:
            mejor[s.exercise_id] = (s.weight_kg, fecha)
    for ex_id, (kg, fecha) in mejor.items():
        if fecha >= hoy - timedelta(days=3):
            ex = db.get(Exercise, ex_id)
            nombre = getattr(ex, "canonical_name", None)
            if nombre:
                return (f"El {fecha.strftime('%d/%m')} movió {_fmt(kg)} kg en "
                        f"{nombre}, su mejor serie de estas dos semanas")
    return None
