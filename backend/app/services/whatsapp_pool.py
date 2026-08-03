"""Pool de 100 seguimientos informales por WhatsApp (uno por día, sin repetir).

Cada entrada NO es un texto literal: es un BRIEF (intención + guía) que la IA
convierte en un mensaje escrito para ESE cliente concreto, a ESA hora, ESE día.
Mandar el mismo texto clonado a 20 personas se nota y quema el canal; un brief
distinto cada día, redactado según el momento del cliente, no.

Campos de cada brief:
  key    identificador estable (para el registro de envíos y no repetir).
  tema   de qué va el mensaje (una línea).
  guia   qué debe conseguir el mensaje; la IA lo adapta al cliente.
  scope  a qué planes aplica: "any" | "nutri" | "train" (por servicio contratado).
  franja "any" | "manana" | "tarde" | "noche" — cuándo tiene sentido mandarlo.

El orden de la lista ES la rotación: día 1 → índice 0, día 101 → vuelve al 0.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Brief:
    key: str
    tema: str
    guia: str
    scope: str = "any"      # any | nutri | train
    franja: str = "any"     # any | manana | tarde | noche


def _b(key, tema, guia, scope="any", franja="any") -> Brief:
    return Brief(key=key, tema=tema, guia=guia, scope=scope, franja=franja)


# 100 briefs. Mezcla deliberada: ánimo, técnica, hábitos, escucha, educación,
# celebración y "sin agenda" — como escribiría un coach de verdad, no un bot.
POOL: tuple[Brief, ...] = (
    _b("arranque_semana", "Arranque de semana", "Pregunta cómo encara la semana y qué día ve más difícil, para anticiparlo juntos.", franja="manana"),
    _b("check_energia", "Nivel de energía", "Interésate por su energía estos días y si nota diferencia respecto a cuando empezó."),
    _b("sueno", "Descanso", "Pregunta cuántas horas está durmiendo y cómo se levanta; el descanso manda en todo lo demás."),
    _b("agua", "Hidratación", "Recuérdale beber agua de forma natural, sin sermón, y pregúntale cómo lo lleva."),
    _b("pasos_diarios", "Pasos / NEAT", "Pregunta si está moviéndose fuera del entreno y proponle una forma fácil de sumar pasos hoy."),
    _b("victoria_pequena", "Victoria pequeña", "Pídele que te cuente una cosa pequeña que le haya salido bien esta semana."),
    _b("dudas_abiertas", "Puerta abierta", "Mensaje corto recordando que puede escribirte cualquier duda, por tonta que le parezca."),
    _b("tecnica_basico", "Técnica en un básico", "Ofrécele revisar un vídeo suyo de un ejercicio básico para pulir técnica.", scope="train"),
    _b("progresion_cargas", "Progresión de cargas", "Pregunta si ha podido subir algo de peso o repeticiones respecto a la semana pasada.", scope="train"),
    _b("agujetas", "Agujetas y fatiga", "Interésate por cómo va recuperando entre sesiones y si arrastra fatiga.", scope="train"),
    _b("comida_fuera", "Comer fuera", "Dale una pauta sencilla para cuando come fuera sin salirse del plan.", scope="nutri"),
    _b("saciedad", "Saciedad", "Pregunta si termina las comidas saciado o se queda con hambre, para ajustar volumen de comida.", scope="nutri"),
    _b("antojos", "Antojos", "Pregunta a qué hora le entran los antojos y proponle una estrategia concreta."),
    _b("desayuno", "Desayuno", "Interésate por cómo lleva el desayuno y si le cuadra con su horario.", scope="nutri", franja="manana"),
    _b("compra_semanal", "Compra de la semana", "Recuérdale dejar la compra hecha para que la semana ruede sola.", scope="nutri"),
    _b("batch_cooking", "Cocinar por lotes", "Sugiérele cocinar de una vez para varios días y pregúntale si le encaja.", scope="nutri"),
    _b("finde_dificil", "El fin de semana", "Pregunta cómo suele irle el finde y acordad un plan realista para este."),
    _b("motivo_inicial", "Por qué empezaste", "Recuérdale con cariño el motivo por el que empezó y pregúntale si sigue vigente."),
    _b("foto_progreso", "Progreso visual", "Anímale a compararse con hace unas semanas, no con ayer."),
    _b("balanza", "La báscula", "Explícale que el peso fluctúa y pregúntale si le está afectando el número."),
    _b("constancia", "Constancia sobre intensidad", "Refuerza que lo que funciona es sostener, no matarse un día."),
    _b("entreno_hoy", "Entreno de hoy", "Pregúntale si ya ha entrenado hoy o cuándo piensa hacerlo.", scope="train"),
    _b("calentamiento", "Calentamiento", "Recuérdale la importancia de calentar y pregúntale si lo está haciendo.", scope="train"),
    _b("rir", "RIR / cerca del fallo", "Pregúntale si está llegando cerca del fallo o se está quedando corto.", scope="train"),
    _b("descansos", "Descansos entre series", "Pregúntale si respeta los descansos o va con prisa.", scope="train"),
    _b("dolor_molestia", "Molestias", "Pregunta directamente si arrastra alguna molestia; quieres saberlo pronto."),
    _b("estres", "Estrés", "Interésate por su nivel de estrés y cómo le está afectando al plan."),
    _b("trabajo", "Trabajo y horarios", "Pregunta si el trabajo le está complicando entrenar o comer bien."),
    _b("proteina", "Proteína del día", "Pregúntale si está llegando a su proteína y dale un truco para cuadrarla.", scope="nutri"),
    _b("verdura", "Verdura y fibra", "Anímale a no descuidar la verdura; digestión y saciedad.", scope="nutri"),
    _b("alcohol", "Alcohol", "Habla sin juzgar de cómo encajar alguna copa sin tirar la semana."),
    _b("plan_b", "Plan B", "Proponle tener un plan B para los días que se tuercen."),
    _b("racha", "Racha", "Reconoce los días que lleva siendo constante y anímale a no romper la cadena."),
    _b("medio_camino", "Mitad de semana", "Empujón de mitad de semana: queda menos de lo que parece.", franja="tarde"),
    _b("cierre_semana", "Cierre de semana", "Repasa con él cómo ha ido la semana y qué se lleva para la siguiente.", franja="tarde"),
    _b("recordatorio_diario", "Registro del diario", "Recuérdale apuntar el diario en el portal, que es lo que te deja ajustar bien."),
    _b("recordatorio_series", "Registro de series", "Recuérdale apuntar las series para poder ver su progreso real.", scope="train"),
    _b("preguntale_comida", "Comida favorita", "Pregúntale qué comida del plan le está gustando más, para repetirla."),
    _b("comida_odiada", "Lo que no le gusta", "Pregúntale si hay algo del plan que no le entra, para cambiarlo."),
    _b("horarios_comida", "Horarios", "Pregunta si los horarios de comida le encajan de verdad con su día.", scope="nutri"),
    _b("viaje", "Viajes / fuera de casa", "Pregunta si tiene algún viaje próximo para adaptar el plan antes."),
    _b("gimnasio_lleno", "Gimnasio lleno", "Dale una salida para cuando el gimnasio está a tope y no puede seguir el orden.", scope="train"),
    _b("material_casa", "Entrenar en casa", "Pregunta si algún día necesita alternativa en casa y ofrécesela.", scope="train"),
    _b("cardio", "Cardio", "Pregúntale cómo lleva el cardio y si le resulta llevadero."),
    _b("movilidad", "Movilidad", "Sugiere un par de minutos de movilidad y pregúntale por sus zonas rígidas.", scope="train"),
    _b("postura", "Postura en el día a día", "Comenta la postura fuera del gym si pasa muchas horas sentado."),
    _b("mentalidad", "Mentalidad a largo plazo", "Recuérdale que esto va de meses, no de días."),
    _b("comparacion", "No compararse", "Anímale a compararse solo con su versión de hace un mes."),
    _b("celebra_habito", "Celebrar un hábito", "Celebra un hábito que ya haya automatizado sin darse cuenta."),
    _b("pregunta_libre", "Sin agenda", "Mensaje breve y humano, sin pedir nada: solo saber cómo está."),
    _b("suplementos", "Suplementos", "Pregunta si está tomando lo acordado y si le genera dudas.", scope="nutri"),
    _b("cafe", "Cafeína", "Pregunta por su consumo de café y si le está afectando al sueño."),
    _b("digestion", "Digestiones", "Pregunta cómo lleva las digestiones con el plan actual.", scope="nutri"),
    _b("hambre_noche", "Hambre por la noche", "Pregunta si le entra hambre de noche y dale una idea para gestionarla.", scope="nutri", franja="noche"),
    _b("desayuno_rapido", "Desayuno con prisa", "Dale una idea de desayuno rápido para días con prisa.", scope="nutri", franja="manana"),
    _b("tupper", "Tupper del trabajo", "Pregúntale cómo se organiza la comida del trabajo.", scope="nutri"),
    _b("finde_social", "Compromisos sociales", "Pregunta si tiene algún evento y preparad juntos cómo encajarlo."),
    _b("dormir_mejor", "Rutina de sueño", "Proponle una pequeña rutina para dormir mejor.", franja="noche"),
    _b("pantallas", "Pantallas antes de dormir", "Comenta el efecto de las pantallas en el descanso.", franja="noche"),
    _b("animo_bajo", "Días de bajón", "Reconoce que hay días de bajón y que no pasa nada; lo importante es volver."),
    _b("recaida", "Después de un desliz", "Normaliza un desliz y céntrale en la siguiente comida, no en el castigo."),
    _b("fuerza_record", "Récord personal", "Pregúntale si ha hecho algún récord suyo últimamente para celebrarlo.", scope="train"),
    _b("ropa", "La ropa como medida", "Pregúntale si nota la ropa distinta; a veces dice más que la báscula."),
    _b("espejo", "Percepción propia", "Pregunta cómo se está viendo él, más allá de los números."),
    _b("familia", "Apoyo del entorno", "Pregunta si tiene apoyo en casa o le ponen difícil el plan."),
    _b("cocinar", "Cocinar", "Pregunta si le gusta cocinar o necesita opciones de cero esfuerzo.", scope="nutri"),
    _b("presupuesto", "Presupuesto", "Pregunta si el plan le encaja en presupuesto; hay alternativas baratas.", scope="nutri"),
    _b("temporada", "Producto de temporada", "Sugiere aprovechar producto de temporada, más barato y rico.", scope="nutri"),
    _b("prisa", "Días sin tiempo", "Dale una versión mínima del entreno para días sin tiempo.", scope="train"),
    _b("sesion_corta", "Sesión corta que vale", "Recuérdale que una sesión corta bien hecha cuenta.", scope="train"),
    _b("volumen_semanal", "Volumen de la semana", "Pregunta si está completando las sesiones previstas.", scope="train"),
    _b("deload", "Semana de descarga", "Explica para qué sirve bajar el pistón y pregúntale cómo la lleva.", scope="train"),
    _b("adherencia", "Adherencia real", "Pregúntale con honestidad qué porcentaje del plan está cumpliendo."),
    _b("obstaculo", "El mayor obstáculo", "Pregúntale qué es lo que más le está costando ahora mismo."),
    _b("siguiente_paso", "Siguiente objetivo", "Pregúntale qué le gustaría conseguir en las próximas semanas."),
    _b("recordar_portal", "Portal", "Recuérdale que tiene todo su plan en el portal, por si no lo abre."),
    _b("feedback_coach", "Feedback sobre ti", "Pregúntale si hay algo que podrías hacer mejor como coach."),
    _b("rutina_manana", "Rutina de mañana", "Pregunta cómo empieza el día y si eso le condiciona el resto.", franja="manana"),
    _b("merienda", "Merienda", "Pregunta cómo lleva la tarde y si necesita una merienda que aguante.", scope="nutri", franja="tarde"),
    _b("post_entreno", "Después de entrenar", "Pregunta cómo se siente al terminar de entrenar.", scope="train"),
    _b("musica", "Motivación en el entreno", "Ligero: pregúntale con qué se motiva para entrenar.", scope="train"),
    _b("compañero", "Entrenar acompañado", "Pregunta si entrena solo o acompañado y cómo le influye.", scope="train"),
    _b("calor_frio", "Clima", "Comenta cómo el clima afecta al entreno o al apetito y cómo adaptarse."),
    _b("vacaciones", "Vacaciones", "Pregunta si tiene vacaciones cerca para planificar el mantenimiento."),
    _b("mantenimiento", "Mantener lo ganado", "Explícale que mantener también es un objetivo válido."),
    _b("paciencia", "Paciencia con el proceso", "Recuérdale que los cambios reales tardan y se sostienen."),
    _b("pequeno_ajuste", "Ajuste fino", "Cuéntale que un ajuste pequeño puede desbloquear el progreso."),
    _b("preguntas_tecnicas", "Dudas técnicas", "Ábrele la puerta a preguntar dudas de técnica de cualquier ejercicio.", scope="train"),
    _b("etiquetas", "Leer etiquetas", "Dale un truco para leer etiquetas sin volverse loco.", scope="nutri"),
    _b("porciones", "Ojo de buen cubero", "Enséñale a calcular porciones sin báscula cuando no puede pesar.", scope="nutri"),
    _b("pesar_comida", "Pesar la comida", "Pregunta si está pesando y si le resulta sostenible.", scope="nutri"),
    _b("flexibilidad_plan", "Flexibilidad", "Recuérdale que el plan admite cambios; que no lo viva como una cárcel."),
    _b("cansancio_acumulado", "Cansancio acumulado", "Pregunta si nota cansancio acumulado y si necesita bajar el ritmo."),
    _b("respiracion", "Respiración en el esfuerzo", "Comenta cómo respirar en las series pesadas.", scope="train"),
    _b("calzado", "Material y calzado", "Comenta la importancia del calzado según lo que entrene.", scope="train"),
    _b("rutina_finde", "Entrenar en finde", "Pregunta si le cuadra mejor entrenar en finde y ajustarlo."),
    _b("recompensa", "Recompensa no comestible", "Proponle premiarse con algo que no sea comida."),
    _b("identidad", "Verse como alguien que entrena", "Refuerza su identidad: ya es alguien que se cuida."),
    _b("gracias", "Agradecimiento", "Agradécele la confianza y su trabajo; sincero y breve."),
    _b("cierre_mes", "Cierre de etapa", "Repasa lo conseguido en las últimas semanas y qué viene ahora."),
)

assert len(POOL) == 100, f"el pool debe tener 100 briefs, tiene {len(POOL)}"
assert len({b.key for b in POOL}) == 100, "hay claves de brief repetidas"


def brief_for_index(index: int) -> Brief:
    """Brief que toca en la rotación (vuelve a empezar tras el 100)."""
    return POOL[index % len(POOL)]


def applies_to(brief: Brief, *, has_nutrition: bool, has_training: bool) -> bool:
    """¿Este brief tiene sentido para los servicios que tiene contratados?"""
    if brief.scope == "nutri":
        return has_nutrition
    if brief.scope == "train":
        return has_training
    return True
