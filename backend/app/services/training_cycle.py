"""El CICLO de entrenamiento: cuánto dura una vuelta al split y qué toca HOY.

Hasta ahora una rutina era SIEMPRE una semana de lunes a domingo: cada sesión
llevaba el nombre de su día ("Lunes") y el portal buscaba la de hoy comparando
ese nombre con el weekday. Eso obliga a encajar a la persona dentro del split
en vez de al revés: con 7 días no se puede dar más frecuencia a una espalda
que la necesita sin quitársela a otra cosa.

Ahora el MICROCICLO dura entre 2 y 10 días:

  - `cycle_days` == 7 → EXACTAMENTE lo de siempre. Los días son los de la
    semana y hoy se resuelve por el weekday. Ni un plan de los que ya existen
    cambia de comportamiento (no llevan `cycle_days`, y aquí eso es 7).
  - `cycle_days` != 7 → el ciclo ROTA. Los días son "Día 1…N" y hoy se
    resuelve contando los días transcurridos desde el ANCLA (el día en que
    arrancó esta planificación) módulo la duración del ciclo.

⚠️ La regla de "qué sesión toca hoy" vivía COPIADA EN TRES SITIOS —la pantalla
del portal, el recordatorio diario y "tu semana"— y las tres daban por DESCANSO
cualquier día cuyo nombre no fuera el de un weekday. Con un ciclo de 10 días
eso significa que el cliente no vería su entreno NINGÚN día, en silencio. Una
sola puerta: si mañana cambia la regla, cambia aquí y cambia en los tres.
"""
import re
import unicodedata
from datetime import date

# La semana natural: el ciclo por defecto y la unidad en la que se piensan el
# volumen y la frecuencia (series/semana), aunque el ciclo dure otra cosa.
SEMANA = 7
MIN_DIAS_CICLO = 2
MAX_DIAS_CICLO = 10
# Cuántas vueltas al ciclo puede durar un mesociclo. 1 = una sola vuelta (sin
# progresión entre bloques); el tope existe para que el plan siga cabiendo en
# una llamada a la IA y en un documento legible.
MIN_BLOQUES = 1
MAX_BLOQUES = 8
BLOQUES_POR_DEFECTO = 4

DAY_LABELS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DAY_SLUGS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto)
                   if not unicodedata.combining(c))


def dia_de_sesion(sess: dict) -> str:
    """El `day` de una sesión, en minúsculas y a prueba de basura.

    El esquema dice `day: str`, pero a `training_json` le llegan planes
    editados a mano, importados de un Word y copiados de un modelo. Con un
    `day` numérico —o nulo— el `.strip()` de quien lo leía reventaba con un
    AttributeError: la pantalla "Hoy" del cliente (la más visitada del portal)
    se caía con un 500 y el recordatorio diario se llevaba por delante el aviso
    de TODOS los clientes, no solo el del plan roto."""
    if not isinstance(sess, dict):
        return ""
    return str(sess.get("day") or "").strip().lower()


def dias_de_ciclo(training: dict | None) -> int:
    """Cuántos días dura una vuelta al split. Sin dato, la semana de siempre."""
    if not isinstance(training, dict):
        return SEMANA
    crudo = training.get("cycle_days")
    try:
        n = int(crudo)
    except (TypeError, ValueError):
        return SEMANA
    return max(MIN_DIAS_CICLO, min(MAX_DIAS_CICLO, n))


def es_semanal(ciclo: int) -> bool:
    """¿El ciclo es la semana natural? Entonces los días son los del calendario
    y todo se comporta como siempre."""
    return ciclo == SEMANA


def indice_de_dia(sess: dict, ciclo: int) -> int | None:
    """Qué día del ciclo (1…ciclo) es esta sesión, o None si no se sabe.

    Por orden: el `day_index` explícito; el nombre del día de la semana (los
    planes de siempre y los ciclos de 7); y por último un "Día 3" escrito a
    mano o importado, que es lo que produce un ciclo rotativo."""
    if not isinstance(sess, dict):
        return None
    crudo = sess.get("day_index")
    try:
        idx = int(crudo)
        if 1 <= idx <= ciclo:
            return idx
    except (TypeError, ValueError):
        pass
    texto = _sin_acentos(dia_de_sesion(sess))
    if texto in DAY_SLUGS:
        idx = DAY_SLUGS.index(texto) + 1
        return idx if idx <= ciclo else None
    # "Día 3", "dia 3", "d3" — y en un ciclo ROTATIVO también un "3" a secas.
    # ⚠️ En el ciclo SEMANAL un número suelto NO es un día: los días se llaman
    # por su nombre, así que un `day` numérico es basura (un plan importado a
    # medias, un JSON editado a mano) y darlo por bueno le enseñaría al cliente
    # la sesión de otro día. Es justo lo que vigila el test del portal.
    patron = r"d(?:ia)?\s*(\d{1,2})" if es_semanal(ciclo) else r"(?:d(?:ia)?\s*)?(\d{1,2})"
    m = re.fullmatch(patron, texto)
    if m:
        idx = int(m.group(1))
        if 1 <= idx <= ciclo:
            return idx
    return None


def etiqueta_de_dia(indice: int, ciclo: int) -> str:
    """Cómo se llama ese día delante del cliente: el día de la semana cuando el
    ciclo ES la semana, y "Día N" cuando el ciclo rota."""
    if es_semanal(ciclo) and 1 <= indice <= SEMANA:
        return DAY_LABELS[indice - 1]
    return f"Día {indice}"


def indice_de_hoy(hoy: date, *, ancla: date | None, ciclo: int) -> int:
    """Qué día del ciclo (1…ciclo) es `hoy`.

    Con la semana natural, el del calendario (lunes = 1): así el cliente que
    lleva años con su lunes de pecho lo sigue teniendo el lunes. Con un ciclo
    rotativo, los días transcurridos desde el ancla módulo la duración — y
    antes del ancla (un plan publicado con fecha futura) el ciclo aún no ha
    empezado, así que se cuenta como su primer día."""
    if es_semanal(ciclo):
        return hoy.weekday() + 1
    if ancla is None:
        return 1
    transcurridos = (hoy - ancla).days
    if transcurridos < 0:
        return 1
    return (transcurridos % ciclo) + 1


def sesion_de_dia(training: dict | None, indice: int, ciclo: int) -> dict | None:
    """La sesión que cae en ese día del ciclo, o None si es descanso."""
    if not isinstance(training, dict):
        return None
    for sess in training.get("sessions") or []:
        if indice_de_dia(sess, ciclo) == indice:
            return sess
    return None


def sesion_de_fecha(training: dict | None, hoy: date, *, ancla: date | None) -> dict | None:
    """La sesión que toca ese día, o None si toca descansar."""
    ciclo = dias_de_ciclo(training)
    return sesion_de_dia(training, indice_de_hoy(hoy, ancla=ancla, ciclo=ciclo), ciclo)


def bloque_de_fecha(hoy: date, *, ancla: date | None, ciclo: int, bloques: int) -> int:
    """En qué bloque del mesociclo (0…bloques-1) cae `hoy`.

    Un bloque es UNA VUELTA COMPLETA al ciclo: con la semana natural es la
    semana de siempre (y por eso el mesociclo se lee como "semana 1, 2, 3…"),
    y con un ciclo de 10 días un bloque son esos 10 días."""
    if bloques <= 0:
        return 0
    if ancla is None:
        return 0
    transcurridos = max(0, (hoy - ancla).days)
    return (transcurridos // max(1, ciclo)) % bloques


def etiqueta_de_bloque(ciclo: int) -> str:
    """Cómo se llama una vuelta al ciclo: "Semana" cuando el ciclo es la semana
    (que es como lo llama todo el mundo) y "Bloque" cuando rota."""
    return "Semana" if es_semanal(ciclo) else "Bloque"


def sesiones_objetivo(training_days: int | None, ciclo: int) -> int:
    """Cuántas sesiones caben en el ciclo para alguien que puede entrenar
    `training_days` días POR SEMANA.

    La anamnesis pregunta lo único que una persona sabe contestar ("¿cuántos
    días puedes entrenar a la semana?"); cuántas sesiones son eso dentro de un
    ciclo de 10 días lo calcula el backend, no se le pregunta a nadie ni se lo
    inventa el modelo. Con ciclo de 7 sale exactamente `training_days`."""
    try:
        dias = int(training_days)
    except (TypeError, ValueError):
        dias = 3
    dias = max(1, min(SEMANA, dias))
    objetivo = round(dias * ciclo / SEMANA)
    return max(1, min(ciclo, int(objetivo)))


def resumen(training: dict | None, *, training_days: int | None = None) -> dict:
    """Los rasgos del ciclo, para pintarlos sin recalcularlos en cada pantalla."""
    ciclo = dias_de_ciclo(training)
    bloques = len((training or {}).get("weekly_progression") or []) or BLOQUES_POR_DEFECTO
    sesiones = len((training or {}).get("sessions") or [])
    return {
        "cycle_days": ciclo,
        "semanal": es_semanal(ciclo),
        "sessions": sesiones,
        "sessions_target": sesiones_objetivo(training_days, ciclo) if training_days else sesiones,
        "blocks": bloques,
        "block_label": etiqueta_de_bloque(ciclo),
        "total_days": ciclo * bloques,
    }
