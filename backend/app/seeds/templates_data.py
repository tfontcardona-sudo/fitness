"""POOL DE RUTINAS de fábrica — 20 casos por carpeta (services/templates.CATEGORIES).

Contenido redactado para la marca (casos recurrentes de gimnasio) con ejercicios
por NOMBRE EXACTO de la biblioteca: `seed_plan_templates` los resuelve a
exercise_id al sembrar (insert-por-título: re-ejecutar no duplica ni pisa
ediciones del coach). Validado por tests/test_templates_pool.py.

Generado con asistencia de IA y verificación en dos pasadas (técnica/clínica +
mecánica); los textos son editables desde la página Rutinas.
"""

TEMPLATES = [
 {
  "category": "fuerza",
  "title": "Fuerza base 3 días",
  "case": "Hombre de 28 años, oficinista, sin experiencia seria con barra. Quiere construir una base de fuerza en sentadilla, press y peso muerto entrenando lunes, miércoles y viernes.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full-body A/B/C",
  "split_rationale": "Tres sesiones de cuerpo completo permiten practicar los levantamientos básicos con alta frecuencia, que es lo que más acelera la técnica y la fuerza en un principiante.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Día A — Sentadilla y banca",
    "warmup": "5 min de bici suave y movilidad de cadera y hombro; series de aproximación en los básicos.",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Rompe con la cadera y las rodillas a la vez, torso firme."
     },
     {
      "name": "Press banca con barra",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Escápulas retraídas y pies firmes en el suelo."
     },
     {
      "name": "Remo con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Espalda neutra, lleva la barra al abdomen sin impulso."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Glúteo y abdomen apretados, sin hundir la cadera."
     }
    ],
    "cooldown": "5 min de caminata y estiramientos suaves de cadera y pectoral."
   },
   {
    "day": "Miércoles",
    "name": "Día B — Peso muerto y press militar",
    "warmup": "5 min de remo o bici; bisagra de cadera con palo y aproximaciones al peso muerto.",
    "exercises": [
     {
      "name": "Peso muerto convencional",
      "sets": 3,
      "rep_range": "3-5",
      "rir": "2",
      "rest_sec": 240,
      "technique_cue": "Barra pegada a la pierna, empuja el suelo con las piernas."
     },
     {
      "name": "Press militar de pie con barra",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Glúteo apretado para no arquear la lumbar."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Lleva los codos hacia el bolsillo, sin balanceo."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Extiende los brazos sin dejar que el tronco rote."
     }
    ],
    "cooldown": "Estiramiento de isquios y dorsal, 5 minutos."
   },
   {
    "day": "Viernes",
    "name": "Día C — Variantes y consolidación",
    "warmup": "5 min de bici y movilidad general; aproximaciones en sentadilla pausada.",
    "exercises": [
     {
      "name": "Sentadilla pausada con barra",
      "sets": 3,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Pausa de 2 segundos abajo sin perder tensión."
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Baja controlado hasta notar estiramiento en el pecho."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho alto, tira con la espalda y no con el brazo."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Lumbar pegada al suelo durante todo el gesto."
     }
    ],
    "cooldown": "Caminata suave y respiraciones, 5 minutos."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: fijar técnica y encontrar los pesos de trabajo.",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Series indicadas; prioriza calidad de ejecución."
   },
   {
    "week": 2,
    "intent": "Progresión: pequeño aumento de carga manteniendo la técnica.",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismo volumen, cargas ligeramente superiores."
   },
   {
    "week": 3,
    "intent": "Carga: semana más exigente del bloque en los básicos.",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Mantén las series; no añadas trabajo extra."
   },
   {
    "week": 4,
    "intent": "Descarga: recuperar para empezar el siguiente bloque fresco.",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Reduce una serie en cada básico y afloja las cargas."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 1,
     "notes": "Caminata rápida o bici suave en día libre."
    }
   ]
  },
  "deload_instructions": "En la semana 4 baja las cargas al 90 por ciento y quita una serie de cada ejercicio principal; mantén la frecuencia de tres días."
 },
 {
  "category": "fuerza",
  "title": "Texas 531 simplificado",
  "case": "Hombre de 33 años con cuatro años de experiencia, estancado en los básicos. Dispone de cuatro días y quiere una estructura de volumen e intensidad clara al estilo Texas/531.",
  "level": "intermediate",
  "days_per_week": 4,
  "place": "gym",
  "split_name": "Básico diario con día de volumen y día de intensidad",
  "split_rationale": "Cada levantamiento tiene su día protagonista: dos sesiones de volumen y dos de intensidad reparten el estímulo semanal y permiten progresar en los cuatro básicos sin interferencias.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Sentadilla — volumen",
    "warmup": "5 min de bici, movilidad de tobillo y cadera, aproximaciones progresivas.",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 5,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Mismo peso en las cinco series, profundidad constante."
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Cadera atrás, barra rozando el muslo."
     },
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "No despegues la cadera del respaldo."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Costillas abajo, cuerpo en línea recta."
     }
    ],
    "cooldown": "Estiramiento de cuádriceps y cadera, 5 minutos."
   },
   {
    "day": "Martes",
    "name": "Press banca — volumen",
    "warmup": "Movilidad de hombro con banda y series de aproximación en banca.",
    "exercises": [
     {
      "name": "Press banca con barra",
      "sets": 5,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Toca el pecho siempre en el mismo punto."
     },
     {
      "name": "Remo con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Torso estable, sin dar tirones."
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Sube las mancuernas sin chocarlas arriba."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos pegados al cuerpo, separa la cuerda abajo."
     }
    ],
    "cooldown": "Estiramiento de pectoral en marco de puerta, 3-5 minutos."
   },
   {
    "day": "Jueves",
    "name": "Peso muerto — intensidad",
    "warmup": "5 min de remo, bisagra con poco peso y aproximaciones al peso de trabajo.",
    "exercises": [
     {
      "name": "Peso muerto convencional",
      "sets": 4,
      "rep_range": "3-5",
      "rir": "1-2",
      "rest_sec": 240,
      "technique_cue": "Tensión en el dorsal antes de despegar la barra."
     },
     {
      "name": "Sentadilla frontal con barra",
      "sets": 3,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Codos altos, torso lo más vertical posible."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadera pegada al banco, sube sin impulso."
     },
     {
      "name": "Elevaciones de rodillas colgado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Sube las rodillas con control, sin balanceo."
     }
    ],
    "cooldown": "Estiramiento de isquios y glúteo, 5 minutos."
   },
   {
    "day": "Viernes",
    "name": "Press militar — intensidad",
    "warmup": "Movilidad de hombro y torácica, aproximaciones en press militar.",
    "exercises": [
     {
      "name": "Press militar de pie con barra",
      "sets": 4,
      "rep_range": "3-5",
      "rir": "1-2",
      "rest_sec": 180,
      "technique_cue": "Mete la cabeza al pasar la barra por la frente."
     },
     {
      "name": "Press banca agarre cerrado",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Agarre a la anchura de los hombros, codos cerca del cuerpo."
     },
     {
      "name": "Dominadas pronas",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Pecho hacia la barra, extensión completa abajo."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Tira hacia la cara y rota los nudillos hacia atrás."
     }
    ],
    "cooldown": "Movilidad de hombro suave, 5 minutos."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: calibrar los pesos de volumen e intensidad.",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Series completas sin llegar al fallo."
   },
   {
    "week": 2,
    "intent": "Progresión: sube ligeramente los días de intensidad.",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mantén el volumen del lunes y martes estable."
   },
   {
    "week": 3,
    "intent": "Carga: semana punta en los cuatro básicos.",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Si la técnica se degrada, congela el peso."
   },
   {
    "week": 4,
    "intent": "Descarga antes de repetir el ciclo con nuevos máximos de trabajo.",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Reduce a 3 series los básicos y mantén los accesorios ligeros."
   }
  ],
  "cardio": {
   "daily_steps": 7000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 20,
     "times_per_week": 2,
     "notes": "Caminata o bici suave como recuperación activa."
    }
   ]
  },
  "deload_instructions": "Semana 4: 90 por ciento de las cargas, tres series en los levantamientos principales y accesorios lejos del fallo."
 },
 {
  "category": "fuerza",
  "title": "Opositor a bombero",
  "case": "Hombre de 26 años que prepara oposiciones de bombero: debe rendir en carrera, dominadas y press. Combina tres días de fuerza con la carrera que exigen las pruebas.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full-body orientado a pruebas físicas",
  "split_rationale": "Tres sesiones de cuerpo completo dejan días libres para la carrera y priorizan los gestos de las pruebas: dominadas, empuje y fuerza de tren inferior con transferencia al sprint y la escalera.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Dominadas y fuerza general",
    "warmup": "5 min de carrera suave, movilidad de hombro y aproximaciones.",
    "exercises": [
     {
      "name": "Dominadas pronas",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Barbilla sobre la barra sin patada."
     },
     {
      "name": "Press banca con barra",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Baja controlado y empuja explosivo."
     },
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 3,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Espalda neutra, empuja el suelo con fuerza."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cuerpo rígido como una tabla."
     }
    ],
    "cooldown": "Trote muy suave 5 min y estiramientos."
   },
   {
    "day": "Miércoles",
    "name": "Empuje vertical y pierna unilateral",
    "warmup": "Movilidad de hombro con banda y cadera; aproximaciones al press.",
    "exercises": [
     {
      "name": "Press militar de pie con barra",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Bloquea arriba con la barra sobre la nuca del cuello."
     },
     {
      "name": "Zancadas caminando con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Pasos amplios, rodilla alineada con el pie."
     },
     {
      "name": "Remo invertido",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cuerpo en línea, pecho a la barra."
     },
     {
      "name": "Elevaciones de rodillas colgado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Agarre firme; trabaja también la suspensión."
     }
    ],
    "cooldown": "Estiramiento de cadera y antebrazos, 5 minutos."
   },
   {
    "day": "Viernes",
    "name": "Fuerza-resistencia de prueba",
    "warmup": "5 min de carrera progresiva y movilidad general.",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Ritmo constante, sin rebotes abajo."
     },
     {
      "name": "Flexiones lastradas",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cuerpo en bloque, pecho al suelo."
     },
     {
      "name": "Remo con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tira al abdomen manteniendo el torso fijo."
     },
     {
      "name": "Swing con kettlebell",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "El impulso sale de la cadera, no de los brazos."
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Camina erguido sin inclinarte hacia la carga."
     }
    ],
    "cooldown": "Caminata y estiramientos de cadena posterior."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: acoplar fuerza y carrera sin acumular fatiga.",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Controla las sensaciones en las piernas tras las series de carrera."
   },
   {
    "week": 2,
    "intent": "Progresión: sube cargas en básicos y añade alguna repetición en dominadas.",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Dominadas: busca una repetición más por serie."
   },
   {
    "week": 3,
    "intent": "Carga: semana más dura de fuerza; mantén la carrera estable.",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "No subas volumen de carrera esta semana."
   },
   {
    "week": 4,
    "intent": "Descarga: llegar fresco para simular las pruebas.",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Reduce una serie por ejercicio; buen momento para un simulacro de prueba."
   }
  ],
  "cardio": {
   "daily_steps": 10000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 40,
     "times_per_week": 2,
     "notes": "Carrera continua en zona 2."
    },
    {
     "type": "hiit",
     "minutes": 20,
     "times_per_week": 1,
     "notes": "Series de 400-800 m al ritmo objetivo de la prueba."
    }
   ]
  },
  "deload_instructions": "Semana 4 con cargas al 90 por ciento y una serie menos por ejercicio; mantén una sola sesión corta de series de carrera."
 },
 {
  "category": "fuerza",
  "title": "Powerlifting novato",
  "case": "Hombre de 21 años, estudiante, quiere competir en powerlifting a medio plazo. Nunca ha seguido programación; necesita frecuencia alta en los tres básicos con técnica prioritaria.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "SBD rotativo con básico pesado y básico ligero",
  "split_rationale": "Cada sesión tiene un levantamiento pesado y otro ligero de práctica: el novato progresa por técnica y frecuencia, no por volumen accesorio.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Sentadilla pesada",
    "warmup": "Bici 5 min, movilidad de tobillo y cadera, aproximaciones escalonadas.",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 5,
      "rep_range": "3-5",
      "rir": "2",
      "rest_sec": 240,
      "technique_cue": "Misma profundidad en cada repetición, mira un punto fijo."
     },
     {
      "name": "Press banca con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Trabajo técnico: pausa breve en el pecho."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Junta las escápulas al final del tirón."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Aprieta el abdomen como si esperaras un golpe."
     }
    ],
    "cooldown": "Estiramiento de cuádriceps y aductor, 5 minutos."
   },
   {
    "day": "Miércoles",
    "name": "Banca pesada",
    "warmup": "Movilidad de hombro con banda, retracción escapular, aproximaciones.",
    "exercises": [
     {
      "name": "Press banca con barra",
      "sets": 5,
      "rep_range": "3-5",
      "rir": "2",
      "rest_sec": 240,
      "technique_cue": "Pies clavados, aprovecha el leg drive."
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Bisagra pura: la cadera manda, la barra pegada."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tira hacia la clavícula con el pecho alto."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cadera y hombros cuadrados al frente."
     }
    ],
    "cooldown": "Estiramiento de pectoral y dorsal."
   },
   {
    "day": "Viernes",
    "name": "Peso muerto pesado",
    "warmup": "Remo 5 min, bisagra con barra vacía, aproximaciones al peso de trabajo.",
    "exercises": [
     {
      "name": "Peso muerto convencional",
      "sets": 4,
      "rep_range": "3-5",
      "rir": "2",
      "rest_sec": 240,
      "technique_cue": "Quita la holgura de la barra antes de tirar."
     },
     {
      "name": "Sentadilla pausada con barra",
      "sets": 3,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Dos segundos abajo, sube sin rebote."
     },
     {
      "name": "Press militar sentado con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Antebrazos verticales bajo la barra."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Controla la bajada en 2-3 segundos."
     }
    ],
    "cooldown": "Estiramiento de cadena posterior, 5 minutos."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: consolidar patrones con cargas cómodas.",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Graba tus series pesadas para revisar técnica."
   },
   {
    "week": 2,
    "intent": "Progresión: añade 2,5 kg a los básicos si la técnica aguanta.",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismo esquema de series."
   },
   {
    "week": 3,
    "intent": "Carga: semana de mayor exigencia del bloque.",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "No busques máximos: repeticiones limpias."
   },
   {
    "week": 4,
    "intent": "Descarga para asimilar y empezar el siguiente ciclo.",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Tres series en los básicos, accesorios a la mitad."
   }
  ],
  "cardio": {
   "daily_steps": 6000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 20,
     "times_per_week": 2,
     "notes": "Caminata para capacidad de trabajo, sin fatigar las piernas."
    }
   ]
  },
  "deload_instructions": "En la semana 4 baja al 90 por ciento y limita los básicos a tres series; nada de probar máximos hasta cerrar el bloque."
 },
 {
  "category": "fuerza",
  "title": "Fuerza para corredora de fondo",
  "case": "Mujer de 35 años que corre cuatro días por semana y prepara una media maratón. Busca dos sesiones de fuerza que mejoren economía de carrera y prevengan lesiones sin restar frescura a los rodajes.",
  "level": "intermediate",
  "days_per_week": 2,
  "place": "gym",
  "split_name": "Full-body bilateral + full-body unilateral",
  "split_rationale": "Dos sesiones separadas de los rodajes exigentes: una de fuerza pesada bilateral y otra unilateral con gemelo y tronco, los puntos que más protegen a un corredor.",
  "sessions": [
   {
    "day": "Martes",
    "name": "Fuerza pesada y cadena posterior",
    "warmup": "5 min de trote suave y movilidad de cadera y tobillo.",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Poca repetición y peso alto: no busques agujetas."
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Estira el isquio con la espalda neutra."
     },
     {
      "name": "Remo con pecho apoyado en banco",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "El pecho no se despega del banco."
     },
     {
      "name": "Elevación de gemelo a una pierna en escalón",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Rango completo: talón bien abajo y sube a la punta."
     },
     {
      "name": "Plancha lateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cadera alta, cuerpo en línea recta."
     }
    ],
    "cooldown": "Estiramiento suave de isquios y gemelo."
   },
   {
    "day": "Viernes",
    "name": "Unilateral y tronco",
    "warmup": "Movilidad dinámica de cadera y dos series ligeras de búlgara.",
    "exercises": [
     {
      "name": "Sentadilla búlgara",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Torso ligeramente inclinado, empuja con el talón."
     },
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Sube sin impulsarte con la pierna de abajo."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Bajada lenta para proteger el isquio en carrera."
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Core activo, sin arquear la zona lumbar."
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tira del codo hacia la cadera."
     }
    ],
    "cooldown": "Caminata 5 min y estiramientos generales."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: introducir la fuerza sin interferir con los rodajes.",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Deja 48 h entre fuerza y sesiones de calidad de carrera."
   },
   {
    "week": 2,
    "intent": "Progresión: sube carga en sentadilla y rumano.",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Volumen estable; vigila las sensaciones en los rodajes."
   },
   {
    "week": 3,
    "intent": "Carga: semana más pesada de fuerza.",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Si coincide con tirada larga exigente, prioriza la carrera."
   },
   {
    "week": 4,
    "intent": "Descarga coordinada con la asimilación del plan de carrera.",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Dos series por ejercicio; ideal en semana de descarga de kilómetros."
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 45,
     "times_per_week": 3,
     "notes": "Rodajes suaves ya previstos en su plan de carrera; aquí solo se reflejan."
    }
   ]
  },
  "deload_instructions": "Semana 4: cargas al 90 por ciento y dos series por ejercicio, coincidiendo si es posible con la semana de menos kilómetros."
 },
 {
  "category": "fuerza",
  "title": "Fuerza para pádel",
  "case": "Hombre de 42 años que juega a pádel tres días por semana a nivel competitivo amateur. Quiere dos sesiones de gimnasio para golpear con más potencia y proteger hombro y aductores.",
  "level": "intermediate",
  "days_per_week": 2,
  "place": "gym",
  "split_name": "Pierna unilateral y core + empuje-tracción rotacional",
  "split_rationale": "El pádel exige desplazamientos laterales, rotación y hombro sano: una sesión de pierna unilateral con antirrotación y otra de empuje-tracción con trabajo rotacional y de manguito cubren eso sin robar días de pista.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Pierna unilateral y antirrotación",
    "warmup": "5 min de bici, movilidad de cadera y tobillo, desplazamientos laterales suaves.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Codos por dentro de las rodillas al bajar."
     },
     {
      "name": "Zancada lateral",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Siéntate sobre la pierna que trabaja, la otra estirada."
     },
     {
      "name": "Peso muerto rumano a una pierna",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadera cuadrada, sin abrirte hacia fuera."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Resiste la rotación con el abdomen, no con los brazos."
     }
    ],
    "cooldown": "Estiramiento de aductores y cadera, 5 minutos."
   },
   {
    "day": "Jueves",
    "name": "Empuje, tracción y rotación",
    "warmup": "Movilidad de hombro con banda y rotaciones suaves de tronco.",
    "exercises": [
     {
      "name": "Press landmine de pie",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Empuja en diagonal acompañando con el tronco firme."
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Sin rotar el torso al tirar."
     },
     {
      "name": "Leñador en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Gira desde la cadera, brazos como palancas."
     },
     {
      "name": "Rotación externa de hombro en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codo pegado al costado, movimiento lento."
     }
    ],
    "cooldown": "Estiramiento de pectoral y antebrazo."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: aprender los gestos unilaterales y rotacionales.",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Coloca las sesiones lejos de los partidos importantes."
   },
   {
    "week": 2,
    "intent": "Progresión: algo más de carga en goblet y landmine.",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismo volumen; vigila el hombro tras los partidos."
   },
   {
    "week": 3,
    "intent": "Carga: semana más exigente del bloque.",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Si hay torneo, adelanta o suaviza la segunda sesión."
   },
   {
    "week": 4,
    "intent": "Descarga: prioriza frescura para la pista.",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Dos series por ejercicio, cargas cómodas."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 1,
     "notes": "Bici o caminata suave; la alta intensidad ya la pone el pádel."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90 por ciento con dos series por ejercicio; si coincide con torneo, convierte la segunda sesión en solo movilidad y manguito."
 },
 {
  "category": "fuerza",
  "title": "Fuerza de invierno para ciclista",
  "case": "Hombre de 38 años, ciclista de gran fondo, en bloque de invierno. Quiere dos días de fuerza para subir vatios y proteger la espalda de tantas horas de sillín.",
  "level": "intermediate",
  "days_per_week": 2,
  "place": "gym",
  "split_name": "Pierna dominante de rodilla + cadena posterior y tronco",
  "split_rationale": "El ciclista necesita fuerza máxima de pierna y un tronco sólido: una sesión centrada en empuje de rodilla y otra en bisagra, unilateral y espalda compensan las horas de bici sin apenas fatiga residual.",
  "sessions": [
   {
    "day": "Martes",
    "name": "Fuerza máxima de pierna",
    "warmup": "10 min de rodillo suave y aproximaciones en sentadilla.",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Empuja el suelo con toda la planta del pie."
     },
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Baja hasta 90 grados sin redondear la lumbar."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Sube en un segundo, baja en tres."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Postura de tronco que luego mantendrás sobre la bici."
     }
    ],
    "cooldown": "Rodillo muy suave 5 min o caminata."
   },
   {
    "day": "Viernes",
    "name": "Cadena posterior y torso",
    "warmup": "5 min de bici y bisagra de cadera con poco peso.",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Sube con intención de velocidad, baja controlado."
     },
     {
      "name": "Sentadilla búlgara",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Trabaja cada pierna como pedalada independiente."
     },
     {
      "name": "Remo con pecho apoyado en banco",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Compensa la postura de la bici: aprieta las escápulas."
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Recorrido completo sin perder el apoyo escapular."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Alarga mano y talón opuestos sin mover la lumbar."
     }
    ],
    "cooldown": "Estiramiento de flexores de cadera y pectoral."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación anatómica tras meses sin gimnasio.",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Espera agujetas: no las persigas subiendo peso aún."
   },
   {
    "week": 2,
    "intent": "Progresión hacia cargas de fuerza máxima.",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mantén el rodillo en zona 2 esta semana."
   },
   {
    "week": 3,
    "intent": "Carga: pico de fuerza del bloque de invierno.",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Evita series de vatios altos en la bici los días de pierna."
   },
   {
    "week": 4,
    "intent": "Descarga para transferir la fuerza al pedaleo.",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Dos series por ejercicio; buen momento para test suave en bici."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 60,
     "times_per_week": 2,
     "notes": "Rodillo o carretera en zona 2, según su plan de ciclismo."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90 por ciento y dos series por ejercicio; mantén las piernas frescas para valorar sensaciones sobre la bici."
 },
 {
  "category": "fuerza",
  "title": "Fuerza a partir de los 40",
  "case": "Hombre de 45 años que entrenó de joven y vuelve tras años parado por trabajo y familia. Quiere recuperar fuerza cuidando articulaciones y sin sesiones eternas.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full-body con variantes de bajo estrés articular",
  "split_rationale": "Tres cuerpos completos con sentadilla a cajón, barra hexagonal y trabajo en máquina o mancuerna: estímulo de fuerza real con menos exigencia de movilidad y menos riesgo tras años de parón.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Full-body 1 — Cajón y banca",
    "warmup": "5 min de bici, movilidad de cadera y hombro, aproximaciones.",
    "exercises": [
     {
      "name": "Sentadilla a cajón",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Toca el cajón sin sentarte del todo y sube firme."
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Muñecas neutras, recorrido cómodo para el hombro."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tira sin encoger los hombros hacia las orejas."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Exhala al extender la pierna, lumbar apoyada."
     }
    ],
    "cooldown": "Estiramientos generales 5 minutos."
   },
   {
    "day": "Miércoles",
    "name": "Full-body 2 — Hexagonal y jalón",
    "warmup": "Remo 5 min y bisagra con poco peso.",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Agarres neutros: deja que la espalda trabaje en su sitio."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Empuja sin bloquear los codos con violencia."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Baja la barra al pecho con el torso casi vertical."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Salud de hombro: tira alto y abre los codos."
     }
    ],
    "cooldown": "Estiramiento de dorsal e isquios."
   },
   {
    "day": "Viernes",
    "name": "Full-body 3 — Prensa y unilateral",
    "warmup": "5 min de bici y movilidad dinámica.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Rodillas siguiendo la línea de los pies."
     },
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Banco a 30 grados, baja hasta estiramiento cómodo."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pausa de un segundo con las escápulas juntas."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Ajusta el rodillo justo sobre el tendón de Aquiles."
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Hombros nivelados, pasos cortos y firmes."
     }
    ],
    "cooldown": "Caminata suave y respiraciones, 5 minutos."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: reacostumbrar tendones y articulaciones.",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Cargas conservadoras aunque la fuerza antigua pida más."
   },
   {
    "week": 2,
    "intent": "Progresión moderada si no hay molestias.",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Cualquier molestia articular: repite el peso de la semana 1."
   },
   {
    "week": 3,
    "intent": "Carga: semana más exigente, siempre con margen.",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "El RIR 2 es innegociable en esta etapa."
   },
   {
    "week": 4,
    "intent": "Descarga: a esta edad la recuperación es parte del plan.",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio y estiramientos amplios."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Caminata rápida o bici suave para salud cardiovascular."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90 por ciento con una serie menos por ejercicio; si alguna articulación avisa, adelanta la descarga sin dudar."
 },
 {
  "category": "fuerza",
  "title": "Fuerza exprés en dos días",
  "case": "Mujer de 31 años con jornada larga y dos hijos pequeños: solo puede pisar el gimnasio dos veces por semana, 45 minutos por sesión. Quiere el máximo retorno de fuerza en ese tiempo.",
  "level": "intermediate",
  "days_per_week": 2,
  "place": "gym",
  "split_name": "Full-body doble de básicos",
  "split_rationale": "Con dos sesiones de 45 minutos, todo va a multiarticulares pesados: dos cuerpos completos con patrones complementarios cubren empuje, tracción, pierna y core sin un solo ejercicio de relleno.",
  "sessions": [
   {
    "day": "Martes",
    "name": "Sentadilla y empuje horizontal",
    "warmup": "4 min de bici y aproximaciones directas en sentadilla.",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Aprieta el aire abajo y sube compacta."
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Codos a unos 45 grados del torso."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Torso quieto: tira solo con la espalda."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "No aguantes de más: corta al perder la línea."
     }
    ],
    "cooldown": "Estiramiento breve de piernas y pecho, 3 minutos."
   },
   {
    "day": "Viernes",
    "name": "Bisagra y empuje vertical",
    "warmup": "4 min de remo y bisagra con barra ligera.",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Pecho alto antes de despegar el peso."
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Sube en línea vertical, sin empujar con las piernas."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Siente el dorsal, no los brazos."
     },
     {
      "name": "Sentadilla búlgara",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Dosis mínima unilateral: dos series bien hechas."
     }
    ],
    "cooldown": "Estiramiento de isquios y hombro, 3 minutos."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: fijar pesos que quepan en 45 minutos.",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Cronometra los descansos para cumplir el horario."
   },
   {
    "week": 2,
    "intent": "Progresión: sube carga en los dos levantamientos principales.",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismo volumen, cero ejercicios añadidos."
   },
   {
    "week": 3,
    "intent": "Carga: semana punta del bloque.",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Si una sesión se cae por agenda, no la recuperes doblando."
   },
   {
    "week": 4,
    "intent": "Descarga breve para sostener la adherencia.",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Tres series en los principales; sesión más corta aún."
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 20,
     "times_per_week": 2,
     "notes": "Caminata rápida integrada en desplazamientos diarios."
    }
   ]
  },
  "deload_instructions": "Semana 4 con cargas al 90 por ciento y una serie menos en los levantamientos principales; los pasos diarios se mantienen."
 },
 {
  "category": "fuerza",
  "title": "Fuerza-hipertrofia torso-pierna",
  "case": "Hombre de 24 años, tres años entrenando, quiere seguir subiendo sus básicos sin renunciar a ganar masa muscular. Dispone de cuatro días y buena capacidad de recuperación.",
  "level": "intermediate",
  "days_per_week": 4,
  "place": "gym",
  "split_name": "Torso-pierna: dos días de fuerza y dos de hipertrofia",
  "split_rationale": "El torso-pierna duplicado permite tocar cada zona dos veces por semana con estímulos distintos: fuerza pesada a inicio de semana e hipertrofia con más repeticiones al final.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Torso — fuerza",
    "warmup": "Movilidad de hombro y aproximaciones en banca y remo.",
    "exercises": [
     {
      "name": "Press banca con barra",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Arco moderado y escápulas clavadas al banco."
     },
     {
      "name": "Remo con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Torso a 45 grados fijo toda la serie."
     },
     {
      "name": "Press militar de pie con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Empuja la cabeza a través al bloquear."
     },
     {
      "name": "Dominadas pronas",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Añade lastre solo si completas todas las repeticiones."
     }
    ],
    "cooldown": "Estiramiento de pectoral y dorsal."
   },
   {
    "day": "Martes",
    "name": "Pierna — fuerza",
    "warmup": "Bici 5 min, movilidad de tobillo y aproximaciones en sentadilla.",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Baja bajo control y sube con máxima intención."
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Termina el gesto apretando el glúteo, sin hiperextender."
     },
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Pies a media altura de la plataforma."
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Pausa de un segundo arriba y abajo."
     }
    ],
    "cooldown": "Estiramiento de cuádriceps e isquios."
   },
   {
    "day": "Jueves",
    "name": "Torso — hipertrofia",
    "warmup": "Movilidad de hombro con banda y series ligeras de inclinado.",
    "exercises": [
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Estira bien el pectoral abajo sin perder tensión."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Aguanta un segundo la contracción final."
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Sube con el codo, no con la mano."
     },
     {
      "name": "Curl de bíceps con barra EZ",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos fijos a los costados."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Extiende del todo y separa la cuerda abajo."
     }
    ],
    "cooldown": "Estiramiento de brazos y pecho, 3 minutos."
   },
   {
    "day": "Viernes",
    "name": "Pierna — hipertrofia",
    "warmup": "Bici 5 min y activación de glúteo con banda.",
    "exercises": [
     {
      "name": "Sentadilla búlgara",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "La rodilla puede pasar la punta si el talón no se levanta."
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Mentón recogido y bloqueo total de cadera arriba."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "No despegues la cadera del banco."
     },
     {
      "name": "Extensión de rodilla en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Pausa arriba con el cuádriceps contraído."
     },
     {
      "name": "Crunch en polea alta",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Flexiona el tronco, la cadera no se mueve."
     }
    ],
    "cooldown": "Estiramiento general de pierna, 5 minutos."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: separar bien los pesos de fuerza y de hipertrofia.",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Apunta cargas de ambos bloques por separado."
   },
   {
    "week": 2,
    "intent": "Progresión: sube kilos en fuerza y repeticiones en hipertrofia.",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Doble progresión en los días de hipertrofia."
   },
   {
    "week": 3,
    "intent": "Carga: semana más dura de ambos estímulos.",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Vigila el sueño: cuatro días exigentes."
   },
   {
    "week": 4,
    "intent": "Descarga para consolidar fuerza y masa.",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Dos series por ejercicio en todas las sesiones."
   }
  ],
  "cardio": {
   "daily_steps": 7000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 2,
     "notes": "Cardio suave los días libres para la recuperación."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90 por ciento con dos series por ejercicio; mantén los cuatro días para no perder el hábito."
 },
 {
  "category": "fuerza",
  "title": "Objetivo: cinco dominadas estrictas",
  "case": "Mujer de 29 años que entrena desde hace un año pero apenas saca una dominada. Su objetivo concreto es llegar a cinco dominadas estrictas en tres meses.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Tracción prioritaria con frecuencia tres",
  "split_rationale": "Las dominadas mejoran con práctica frecuente y específica: dos sesiones de tracción vertical (fuerza y negativas) más una de empuje y pierna mantienen el equilibrio estructural.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Tracción vertical — fuerza",
    "warmup": "Movilidad de hombro, activación escapular colgada de la barra.",
    "exercises": [
     {
      "name": "Dominadas neutras",
      "sets": 4,
      "rep_range": "3-5",
      "rir": "1-2",
      "rest_sec": 180,
      "technique_cue": "Usa la banda de asistencia justa para 3-5 repeticiones limpias."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Mismo gesto que la dominada: pecho a la barra."
     },
     {
      "name": "Curl de bíceps con barra EZ",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "El bíceps fuerte ayuda al tramo final de la dominada."
     },
     {
      "name": "Elevaciones de rodillas colgado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cuelga activa: hombros lejos de las orejas."
     }
    ],
    "cooldown": "Estiramiento de dorsal y antebrazo."
   },
   {
    "day": "Miércoles",
    "name": "Empuje y pierna",
    "warmup": "5 min de bici y movilidad general.",
    "exercises": [
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Controla la bajada en dos segundos."
     },
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Talones firmes, pecho alto."
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Sin arquear la lumbar al empujar."
     },
     {
      "name": "Remo invertido",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cuanto más horizontal el cuerpo, más difícil."
     }
    ],
    "cooldown": "Estiramiento de pectoral y cadera."
   },
   {
    "day": "Viernes",
    "name": "Tracción — volumen y negativas",
    "warmup": "Activación escapular y jalones ligeros.",
    "exercises": [
     {
      "name": "Dominadas pronas",
      "sets": 4,
      "rep_range": "3-5",
      "rir": "1-2",
      "rest_sec": 180,
      "technique_cue": "Solo la fase negativa: salta arriba y baja en 3-5 segundos."
     },
     {
      "name": "Jalón agarre estrecho neutro",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Codos hacia las costillas, sin echarte atrás."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Espalda media fuerte para sostener el gesto."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Bisagra limpia: mancuernas rozando las piernas."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "El cuerpo tenso transfiere a la dominada estricta."
     }
    ],
    "cooldown": "Estiramiento de dorsal, bíceps y antebrazos."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: fijar la asistencia justa y la técnica de negativas.",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Anota banda usada y segundos de cada negativa."
   },
   {
    "week": 2,
    "intent": "Progresión: menos asistencia o negativas más lentas.",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Busca una repetición más por serie asistida."
   },
   {
    "week": 3,
    "intent": "Carga: máximo estímulo de tracción del bloque.",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Prueba una dominada estricta al inicio del lunes, fresca."
   },
   {
    "week": 4,
    "intent": "Descarga: los codos y hombros agradecen la pausa.",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Mitad de series de tracción; test de dominadas al final de la semana."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Caminata o elíptica suave; el peso corporal estable ayuda al objetivo."
    }
   ]
  },
  "deload_instructions": "Semana 4 con la mitad de series de tracción y cargas al 90 por ciento; cierra la semana con un test de dominadas estrictas descansada."
 },
 {
  "category": "fuerza",
  "title": "Camino al press banca de 100 kg",
  "case": "Hombre de 27 años con una banca estancada en 85 kg desde hace meses. Quiere un bloque específico de cuatro días para lograr su primer press banca de 100 kg.",
  "level": "intermediate",
  "days_per_week": 4,
  "place": "gym",
  "split_name": "Especialización de banca con frecuencia tres",
  "split_rationale": "Para mover un estancamiento de banca hay que tocarla más a menudo con estímulos distintos: día pesado, día de volumen y día técnico, más un día de pierna que sostiene el conjunto.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Banca pesada",
    "warmup": "Movilidad de hombro, band pull-apart ligeros fuera de serie y aproximaciones largas.",
    "exercises": [
     {
      "name": "Press banca con barra",
      "sets": 5,
      "rep_range": "3-5",
      "rir": "1-2",
      "rest_sec": 240,
      "technique_cue": "Ajusta el arco y clava los pies antes de sacar la barra."
     },
     {
      "name": "Press banca agarre cerrado",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Refuerza el tramo final de la extensión."
     },
     {
      "name": "Remo con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Una espalda fuerte es la base del press."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Equilibra el volumen de empuje de la semana."
     }
    ],
    "cooldown": "Estiramiento de pectoral y rotadores."
   },
   {
    "day": "Martes",
    "name": "Pierna estructural",
    "warmup": "Bici 5 min y aproximaciones en sentadilla.",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Las piernas fuertes estabilizan también la banca."
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Cadera atrás y barra pegada al cuerpo."
     },
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Baja controlado sin despegar la cadera."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Rigidez de tronco: la misma que usarás en el banco."
     }
    ],
    "cooldown": "Estiramiento de pierna, 5 minutos."
   },
   {
    "day": "Jueves",
    "name": "Banca volumen",
    "warmup": "Movilidad de hombro y aproximaciones en banca.",
    "exercises": [
     {
      "name": "Press banca con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Mismo montaje que el día pesado, velocidad constante."
     },
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Cubre el pectoral superior sin castigar el hombro."
     },
     {
      "name": "Dominadas pronas",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Compensa el volumen de empuje del bloque."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "El tríceps decide los últimos centímetros del press."
     }
    ],
    "cooldown": "Estiramiento de pectoral y tríceps."
   },
   {
    "day": "Viernes",
    "name": "Banca técnica y hombro",
    "warmup": "Movilidad completa de hombro y series muy ligeras de press de suelo.",
    "exercises": [
     {
      "name": "Press de suelo con barra",
      "sets": 3,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Pausa en el suelo: elimina el rebote y aprende a empujar desde cero."
     },
     {
      "name": "Press militar de pie con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Hombro fuerte y estable para el arranque del press."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Aprieta las escápulas como en el banco."
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Ligero y controlado, sin balanceo."
     }
    ],
    "cooldown": "Estiramiento de hombro y pectoral, 5 minutos."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: establecer los tres pesos de banca de la semana.",
    "load_pct": 100,
    "rir_target": "2",
    "volume_note": "Día pesado sobre el 85 por ciento de tu mejor marca."
   },
   {
    "week": 2,
    "intent": "Progresión: añade 2,5 kg al día pesado si las barras vuelan.",
    "load_pct": 102.5,
    "rir_target": "1-2",
    "volume_note": "El día de volumen progresa por repeticiones."
   },
   {
    "week": 3,
    "intent": "Carga: semana punta; sencillos pesados con margen.",
    "load_pct": 105,
    "rir_target": "1",
    "volume_note": "Nada de fallos en el banco: cada fallo retrasa el bloque."
   },
   {
    "week": 4,
    "intent": "Descarga y test: intento a 100 kg si las señales acompañan.",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Volumen a la mitad; el intento, el viernes descansado y con observador."
   }
  ],
  "cardio": {
   "daily_steps": 7000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 20,
     "times_per_week": 2,
     "notes": "Caminata suave; el cardio intenso restaría al press."
    }
   ]
  },
  "deload_instructions": "Semana 4: reduce el volumen de banca a la mitad, cargas accesorias al 90 por ciento, y programa el intento de 100 kg al final de la semana con ayuda de un compañero."
 },
 {
  "category": "fuerza",
  "title": "Fuerza en el salón de casa",
  "case": "Mujer de 33 años que teletrabaja y no quiere gimnasios: dispone de mancuernas ajustables, bandas, deslizadores y una esterilla. Busca fuerza general en tres días sin salir de casa.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "home",
  "split_name": "Full-body en casa A/B/C",
  "split_rationale": "Con material mínimo, tres cuerpos completos rotando patrones (sentadilla, bisagra, zancada; empuje y tracción con banda y peso corporal) dan estímulo completo y variado sin máquinas ni rack.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Casa A — Sentadilla y empuje",
    "warmup": "3 min de marcha en el sitio y movilidad de cadera y hombro.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Mancuerna pegada al pecho, talones firmes."
     },
     {
      "name": "Flexiones",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Apoya las rodillas si pierdes la línea del cuerpo."
     },
     {
      "name": "Remo con banda sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Espalda recta, tira de los codos hacia atrás."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Glúteo apretado, mirada al suelo."
     }
    ],
    "cooldown": "Estiramiento de piernas y pecho, 3 minutos."
   },
   {
    "day": "Miércoles",
    "name": "Casa B — Bisagra y tracción",
    "warmup": "Movilidad de cadera y bisagra sin peso frente al espejo.",
    "exercises": [
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadera atrás hasta notar el isquio, espalda neutra."
     },
     {
      "name": "Remo invertido bajo una mesa",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Mesa estable; pecho hacia el borde."
     },
     {
      "name": "Press de hombro con banda",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Pisa la banda y empuja vertical sin arquear."
     },
     {
      "name": "Curl femoral con deslizadores",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadera alta mientras deslizas los talones."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Movimiento lento, lumbar siempre apoyada."
     }
    ],
    "cooldown": "Estiramiento de isquios y hombros."
   },
   {
    "day": "Viernes",
    "name": "Casa C — Unilateral y empuje-tirón",
    "warmup": "Marcha, círculos de cadera y zancadas cortas sin peso.",
    "exercises": [
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Paso atrás largo, rodilla delantera estable."
     },
     {
      "name": "Sentadilla búlgara con peso corporal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Usa una silla firme como apoyo trasero."
     },
     {
      "name": "Press de pecho con banda",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Banda a la altura del pecho, empuja al frente."
     },
     {
      "name": "Jalón con banda de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Ancla la banda arriba y tira de los codos abajo."
     },
     {
      "name": "Puente de glúteo a una pierna",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cadera nivelada, aprieta el glúteo arriba."
     }
    ],
    "cooldown": "Estiramiento general en la esterilla, 5 minutos."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: aprender los gestos y ajustar mancuernas y bandas.",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Anota el peso de la mancuerna y el color de banda en cada ejercicio."
   },
   {
    "week": 2,
    "intent": "Progresión: más peso en mancuerna o banda más dura.",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Si no puedes subir carga, añade 1-2 repeticiones."
   },
   {
    "week": 3,
    "intent": "Carga: semana más exigente con tempo más lento si falta material.",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Bajadas de 3 segundos cuando la mancuerna se quede corta."
   },
   {
    "week": 4,
    "intent": "Descarga para asimilar y descansar articulaciones.",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Dos series por ejercicio, moviéndote con calidad."
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 3,
     "notes": "Caminata diaria al aire libre para romper el sedentarismo del teletrabajo."
    }
   ]
  },
  "deload_instructions": "Semana 4 con dos series por ejercicio y cargas cómodas; mantén las caminatas y la movilidad diaria."
 },
 {
  "category": "fuerza",
  "title": "Pretemporada futbolista amateur",
  "case": "Hombre de 23 años, futbolista amateur en pretemporada: entrena con el equipo dos tardes y juega el domingo. Quiere tres días de fuerza para sprintar más y evitar lesiones de isquios.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Fuerza máxima, potencia y prevención",
  "split_rationale": "El futbolista rinde con fuerza máxima de cadera, potencia de salto y unos isquios a prueba de sprints: cada día ataca uno de esos frentes sin acumular fatiga para el campo.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Fuerza máxima",
    "warmup": "Bici 5 min, movilidad de cadera y aproximaciones en hexagonal.",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 4,
      "rep_range": "3-5",
      "rir": "2",
      "rest_sec": 240,
      "technique_cue": "Sube el peso con máxima velocidad intencional."
     },
     {
      "name": "Sentadilla búlgara",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Cada pierna trabaja sola, como en la zancada del sprint."
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Empuje sólido para los duelos con el rival."
     },
     {
      "name": "Plancha Copenhagen",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Aductor fuerte: sube progresivo el tiempo de aguante."
     }
    ],
    "cooldown": "Estiramiento de aductor y cadera, 5 minutos."
   },
   {
    "day": "Miércoles",
    "name": "Potencia",
    "warmup": "Salto a la comba o skipping suave y movilidad dinámica.",
    "exercises": [
     {
      "name": "Sentadilla con salto",
      "sets": 4,
      "rep_range": "3-5",
      "rir": "3",
      "rest_sec": 150,
      "technique_cue": "Aterriza blando y resetea entre saltos: calidad, no cansancio."
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Extiende la cadera rápido, el glúteo es tu motor de sprint."
     },
     {
      "name": "Remo invertido",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tracción horizontal sin cargar la lumbar."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Tronco estable para los cambios de dirección."
     }
    ],
    "cooldown": "Caminata suave y movilidad de tobillo."
   },
   {
    "day": "Viernes",
    "name": "Cadena posterior y prevención",
    "warmup": "Trote suave 5 min y movilidad de isquios progresiva.",
    "exercises": [
     {
      "name": "Curl nórdico",
      "sets": 3,
      "rep_range": "3-5",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Baja lo más lento que puedas y ayúdate con las manos al volver."
     },
     {
      "name": "Peso muerto rumano a una pierna",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Equilibrio y bisagra: cadera cuadrada al suelo."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Completa el tirón vertical de la semana."
     },
     {
      "name": "Elevación de gemelo a una pierna en escalón",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Tobillo fuerte para el césped irregular."
     }
    ],
    "cooldown": "Estiramiento de isquios y gemelos, suave y sin rebotes."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: introducir nórdicos y saltos con volumen prudente.",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Las agujetas de nórdico son normales: no añadas series."
   },
   {
    "week": 2,
    "intent": "Progresión en fuerza y calidad de salto.",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mide o percibe la altura de tus saltos: debe mantenerse o subir."
   },
   {
    "week": 3,
    "intent": "Carga: semana más fuerte del bloque de pretemporada.",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Coordina con el técnico si hay amistoso exigente."
   },
   {
    "week": 4,
    "intent": "Descarga: llegar fresco al inicio de liga.",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Dos series por ejercicio y saltos a la mitad."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "hiit",
     "minutes": 15,
     "times_per_week": 1,
     "notes": "Sprints cortos de 10-30 m con recuperación completa, tras el calentamiento del miércoles."
    },
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 1,
     "notes": "Trote regenerativo el día después del partido."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90 por ciento, dos series por ejercicio y mitad de saltos; el fútbol del fin de semana se mantiene."
 },
 {
  "category": "fuerza",
  "title": "Fuerza con hombro delicado",
  "case": "Hombre de 36 años con molestias recurrentes de hombro al hacer press por encima de la cabeza y banca profunda. Quiere seguir ganando fuerza general sin provocar dolor.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full-body sin gestos agresivos para el hombro",
  "split_rationale": "Se sustituyen los press dolorosos por máquina, landmine y press de suelo, y se añade trabajo de manguito y espalda alta en cada sesión: fuerza completa respetando el hombro.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Pierna pesada y empuje guiado",
    "warmup": "Bici 5 min, movilidad escapular suave y rotaciones con banda ligera.",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Si el agarre molesta, abre las manos en la barra."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Ajusta el asiento para empujar sin pinzamiento."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Hombros abajo y atrás durante todo el tirón."
     },
     {
      "name": "Rotación externa de hombro en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Carga mínima, ejecución perfecta y sin dolor."
     }
    ],
    "cooldown": "Movilidad suave de hombro, 5 minutos."
   },
   {
    "day": "Miércoles",
    "name": "Bisagra y empuje inclinado seguro",
    "warmup": "Remo suave 5 min y bisagra con poco peso.",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Agarre neutro: posición amable para el hombro."
     },
     {
      "name": "Press landmine de pie",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Trayectoria diagonal: empuja solo en rango sin dolor."
     },
     {
      "name": "Jalón agarre estrecho neutro",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "El agarre neutro protege la articulación."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Termina con los nudillos mirando atrás."
     }
    ],
    "cooldown": "Estiramiento de dorsal y pectoral sin forzar."
   },
   {
    "day": "Viernes",
    "name": "Fuerza general y hombro sano",
    "warmup": "Bici 5 min y activación escapular con banda muy ligera.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Recorrido completo sin despegar la cadera."
     },
     {
      "name": "Press de suelo con barra",
      "sets": 3,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "El suelo limita la bajada: empuja sin llegar al rango doloroso."
     },
     {
      "name": "Dominadas neutras",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Si molesta arriba, corta el rango a tres cuartos."
     },
     {
      "name": "Elevación lateral en polea unilateral",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Sube solo hasta la altura del hombro."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Core sin apoyo de brazos: apto para tu hombro."
     }
    ],
    "cooldown": "Movilidad general y respiraciones, 5 minutos."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: confirmar que todos los gestos son indoloros.",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Cualquier ejercicio con dolor se sustituye, no se aguanta."
   },
   {
    "week": 2,
    "intent": "Progresión en pierna y tirones; empujes conservadores.",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "El manguito progresa por repeticiones, no por kilos."
   },
   {
    "week": 3,
    "intent": "Carga: semana más fuerte del bloque, hombro siempre cómodo.",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "En empujes mantén RIR 2 estricto."
   },
   {
    "week": 4,
    "intent": "Descarga: dar aire a los tejidos del hombro.",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio; duplica el trabajo suave de movilidad."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Bici o caminata; evita nadar mientras el hombro esté sensible."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90 por ciento con una serie menos por ejercicio; si reaparece dolor en cualquier semana, vuelve a las cargas de la semana 1 y consúltalo."
 },
 {
  "category": "fuerza",
  "title": "Fuerza con lumbar protegida",
  "case": "Hombre de 48 años con episodios previos de lumbalgia, ya sin dolor pero con respeto a la zona. Quiere entrenar fuerza seria con una bisagra controlada y ejercicios que no comprometan la lumbar.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full-body con carga axial controlada",
  "split_rationale": "Se sustituyen las cargas más exigentes para la lumbar por cajón, barra hexagonal, hip thrust y remos apoyados, y el core se trabaja con antiextensión y antirrotación: fuerza real con la espalda a salvo.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Sentadilla a cajón y empuje",
    "warmup": "Bici 5 min, gato-camello suave y activación de glúteo.",
    "exercises": [
     {
      "name": "Sentadilla a cajón",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "El cajón fija la profundidad: siéntate atrás con control."
     },
     {
      "name": "Press banca con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Arco cómodo, sin exagerar la extensión lumbar."
     },
     {
      "name": "Remo con pecho apoyado en banco",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "El banco absorbe la carga: la lumbar descansa."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Movimiento lento, pelvis sin girar."
     }
    ],
    "cooldown": "Caminata suave 5 min y respiración diafragmática."
   },
   {
    "day": "Miércoles",
    "name": "Bisagra controlada",
    "warmup": "Bisagra con palo contra la pared hasta dominar el patrón.",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 3,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Espalda neutra y empuje de piernas: para la carga si la forma se rompe."
     },
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "No bajes tanto que la pelvis bascule."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Torso vertical estable, sin balanceos."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Antirrotación pura: la mejor faja es tu core."
     }
    ],
    "cooldown": "Estiramiento de glúteo y cadera, nunca flexión lumbar forzada."
   },
   {
    "day": "Viernes",
    "name": "Cadera dominante y empuje vertical guiado",
    "warmup": "Puente de glúteo suave y movilidad de cadera.",
    "exercises": [
     {
      "name": "Hip thrust con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Bloquea con el glúteo, no arquees la lumbar arriba."
     },
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "El contrapeso frontal mantiene el torso erguido."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Respaldo completo: empuja sin compensar con la espalda."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Torso quieto, sin mecerte con la carga."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Presiona la lumbar contra el suelo en cada repetición."
     }
    ],
    "cooldown": "Caminata suave y estiramiento de flexores de cadera."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: consolidar la bisagra y la confianza en la zona.",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "La técnica manda: ninguna repetición fea cuenta."
   },
   {
    "week": 2,
    "intent": "Progresión prudente si la espalda responde bien.",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Ante cualquier aviso lumbar, repite cargas de la semana 1."
   },
   {
    "week": 3,
    "intent": "Carga: semana más fuerte, siempre con margen amplio.",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "En hexagonal y cajón mantén RIR 2 real."
   },
   {
    "week": 4,
    "intent": "Descarga: descanso activo para los tejidos de la espalda.",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio y más caminata."
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 3,
     "notes": "Caminar a diario es parte del tratamiento de una lumbar sensible."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90 por ciento y una serie menos por ejercicio; si aparece dolor irradiado o que no cede en 48 horas, detén el plan y consulta a un profesional sanitario."
 },
 {
  "category": "fuerza",
  "title": "Fuerza femenina sin miedo al volumen",
  "case": "Mujer de 26 años que quiere verse fuerte y firme pero teme que las pesas la pongan grande. Empieza casi de cero en sala y puede entrenar tres días.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full-body de fuerza con volumen contenido",
  "split_rationale": "Cargas altas y pocas repeticiones con volumen moderado construyen fuerza y firmeza sin el volumen de entrenamiento que haría crecer masa de forma notable: exactamente lo que pide, con datos y no con mitos.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Fuerza 1 — Sentadilla",
    "warmup": "5 min de bici y movilidad de cadera; aproximaciones en sentadilla.",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Peso desafiante: las últimas repeticiones deben costar."
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Empuja fuerte; los brazos firmes salen de aquí."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Postura erguida: espalda fuerte, hombros atrás."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Abdomen firme sin aguantar la respiración."
     }
    ],
    "cooldown": "Estiramiento de piernas y pecho, 3-5 minutos."
   },
   {
    "day": "Miércoles",
    "name": "Fuerza 2 — Bisagra y glúteo",
    "warmup": "Activación de glúteo con banda y bisagra sin peso.",
    "exercises": [
     {
      "name": "Peso muerto rumano con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Cadera atrás, la barra baja pegada a las piernas."
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Sube con el glúteo y bloquea la cadera arriba."
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Hombros fuertes y definidos: empuja vertical."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tira con la espalda, siente el dorsal."
     }
    ],
    "cooldown": "Estiramiento de isquios y glúteo."
   },
   {
    "day": "Viernes",
    "name": "Fuerza 3 — Unilateral y hexagonal",
    "warmup": "Bici 5 min y zancadas cortas sin peso.",
    "exercises": [
     {
      "name": "Sentadilla búlgara",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Pierna y glúteo trabajan a fondo sin cargar la espalda."
     },
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 3,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Levanta pesado con la espalda recta: aquí nace la fuerza."
     },
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Recorrido completo con control."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Postura y hombro sano en una sola pieza."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cintura firme resistiendo el giro."
     }
    ],
    "cooldown": "Estiramiento general, 5 minutos."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: perder el miedo a la barra con técnica guiada.",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Ganar fuerza rápido las primeras semanas es normal: es coordinación."
   },
   {
    "week": 2,
    "intent": "Progresión: sube kilos sin miedo; el volumen sigue contenido.",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismo número de series: la masa no se dispara con esto."
   },
   {
    "week": 3,
    "intent": "Carga: semana más fuerte del bloque.",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Peso alto y pocas repeticiones: firmeza sin volumen extra."
   },
   {
    "week": 4,
    "intent": "Descarga: recuperar y valorar el progreso del mes.",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio; revisa fotos y sensaciones, no solo báscula."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Caminata rápida o elíptica suave los días sin pesas."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90 por ciento con una serie menos por ejercicio; mantén los tres días para consolidar el hábito."
 },
 {
  "category": "fuerza",
  "title": "Fuerza de soporte para escalada",
  "case": "Hombre de 30 años que escala boulder tres días por semana a buen nivel. Busca dos sesiones de gimnasio: tracción máxima para grados duros y antagonistas para equilibrar hombros y codos.",
  "level": "advanced",
  "days_per_week": 2,
  "place": "gym",
  "split_name": "Tracción máxima + antagonistas",
  "split_rationale": "El escalador ya acumula mucho volumen de dedos y tirón en el muro: el gimnasio debe aportar tracción pesada de baja repetición y empuje antagonista que proteja hombros y codos, sin robar días de roca.",
  "sessions": [
   {
    "day": "Martes",
    "name": "Tracción máxima y core de suspensión",
    "warmup": "Activación escapular colgado y dominadas suaves progresivas.",
    "exercises": [
     {
      "name": "Dominadas lastradas",
      "sets": 4,
      "rep_range": "3-5",
      "rir": "1-2",
      "rest_sec": 240,
      "technique_cue": "Lastre exigente y subida explosiva sin perder la estricta."
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tirón unilateral como en un bloqueo de escalada."
     },
     {
      "name": "Elevaciones de piernas colgado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Core de techo: piernas rectas hasta la barra si puedes."
     },
     {
      "name": "Curl de muñeca con barra",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Antebrazo flexor con cargas suaves: complemento, no sustituto del muro."
     }
    ],
    "cooldown": "Estiramiento suave de antebrazos y dorsal."
   },
   {
    "day": "Viernes",
    "name": "Antagonistas y pierna",
    "warmup": "Movilidad de hombro completa y flexiones suaves.",
    "exercises": [
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "El empuje equilibra tanto tirón semanal."
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Hombro estable por encima de la cabeza, clave en aristas."
     },
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Piernas fuertes para talonajes y placas."
     },
     {
      "name": "Curl invertido con barra EZ",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Extensores del antebrazo: seguro de vida contra epicondilitis."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Espalda alta y rotadores para cerrar la semana."
     }
    ],
    "cooldown": "Estiramiento de pectoral, antebrazo y hombro."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: fijar el lastre de trabajo sin interferir con el muro.",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Deja al menos un día entre gimnasio y sesión dura de boulder."
   },
   {
    "week": 2,
    "intent": "Progresión: algo más de lastre si los dedos van frescos.",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Si los antebrazos van cargados del muro, no subas el curl."
   },
   {
    "week": 3,
    "intent": "Carga: pico de tracción del bloque.",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Semana ideal para no intentar proyectos al límite en roca."
   },
   {
    "week": 4,
    "intent": "Descarga: codos y hombros recuperan.",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Mitad de series de tracción; buen momento para escalar fino y técnico."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 1,
     "notes": "Caminata o aproximaciones; la escalada ya cubre la intensidad."
    }
   ]
  },
  "deload_instructions": "Semana 4 con la mitad de series de tracción y cargas al 90 por ciento; los codos mandan: ante molestia interna o externa, retira lastre antes que series."
 },
 {
  "category": "fuerza",
  "title": "Potencia para deportes de equipo",
  "case": "Hombre de 20 años, jugador de baloncesto universitario, quiere saltar más y ganar arranque en los dos primeros pasos. Tres días de gimnasio compatibles con sus entrenamientos de pista.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Fuerza máxima, potencia y fuerza-velocidad",
  "split_rationale": "La potencia se construye en dos frentes: fuerza máxima como base y gestos rápidos como expresión. Un día pesado, un día de saltos y balísticos y un día de fuerza-velocidad unilateral cubren la cadena completa.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Fuerza máxima",
    "warmup": "Bici 5 min, movilidad dinámica y aproximaciones en sentadilla.",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "3-5",
      "rir": "2",
      "rest_sec": 240,
      "technique_cue": "Baja controlado y sube con intención de despegar del suelo."
     },
     {
      "name": "Press banca con barra",
      "sets": 3,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Empuje sólido para pantallas y contactos."
     },
     {
      "name": "Remo Pendlay",
      "sets": 3,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Cada repetición arranca desde el suelo, explosiva."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Tronco rígido: el puente entre piernas y brazos."
     }
    ],
    "cooldown": "Estiramiento de cadera y tobillo."
   },
   {
    "day": "Miércoles",
    "name": "Potencia y balísticos",
    "warmup": "Skipping, saltos suaves progresivos y movilidad de tobillo.",
    "exercises": [
     {
      "name": "Sentadilla con salto",
      "sets": 4,
      "rep_range": "3-5",
      "rir": "3",
      "rest_sec": 150,
      "technique_cue": "Máxima altura en cada salto; para la serie si pierdes chispa."
     },
     {
      "name": "Push press",
      "sets": 4,
      "rep_range": "3-5",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "El impulso de piernas transfiere a la barra: un gesto, no dos."
     },
     {
      "name": "Swing con kettlebell",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadera explosiva, brazos relajados."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Estabilidad para absorber contactos en el aire."
     }
    ],
    "cooldown": "Caminata suave y movilidad de muñeca y hombro."
   },
   {
    "day": "Viernes",
    "name": "Fuerza-velocidad y unilateral",
    "warmup": "Bici 5 min y aproximaciones rápidas en hexagonal.",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 4,
      "rep_range": "3-5",
      "rir": "2",
      "rest_sec": 240,
      "technique_cue": "Mueve la barra lo más rápido posible con técnica intacta."
     },
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Impulsa solo con la pierna de arriba, como en un primer paso."
     },
     {
      "name": "Dominadas pronas",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Tracción vertical para equilibrar tanto empuje."
     },
     {
      "name": "Elevación de gemelo a una pierna en escalón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Tobillo reactivo para el despegue a una pierna."
     }
    ],
    "cooldown": "Estiramiento de gemelos y cuádriceps."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: aprender push press y calibrar los saltos.",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "En balísticos la calidad manda: nada de series arrastradas."
   },
   {
    "week": 2,
    "intent": "Progresión: más carga en fuerza, misma frescura en saltos.",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Coordina con pista: no saltes el día después de partido."
   },
   {
    "week": 3,
    "intent": "Carga: pico de fuerza del bloque.",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Los saltos se mantienen, no aumentan: la potencia se cuida."
   },
   {
    "week": 4,
    "intent": "Descarga: supercompensar para rendir en cancha.",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Mitad de series; buena semana para medir tu salto vertical."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "hiit",
     "minutes": 12,
     "times_per_week": 1,
     "notes": "Sprints de 15-20 m con vuelta andando, tras calentar bien."
    },
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 1,
     "notes": "Bici suave regenerativa tras los partidos."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90 por ciento y mitad de series en todo; mide el salto vertical al final para valorar el bloque."
 },
 {
  "category": "fuerza",
  "title": "Fuerza funcional a partir de los 55",
  "case": "Mujer de 58 años que nunca ha entrenado fuerza. Quiere subir escaleras sin fatiga, cargar la compra con seguridad y proteger sus huesos tras la menopausia. Dispone de dos mañanas por semana.",
  "level": "beginner",
  "days_per_week": 2,
  "place": "gym",
  "split_name": "Full-body funcional con máquinas y gestos cotidianos",
  "split_rationale": "Dos cuerpos completos combinan máquinas seguras para ganar confianza con gestos trasladables a su día a día (sentarse y levantarse, subir escalones, cargar peso), la mejor receta contra la sarcopenia y la pérdida ósea.",
  "sessions": [
   {
    "day": "Martes",
    "name": "Funcional 1 — Sentarse, empujar y tirar",
    "warmup": "5 min de caminata en cinta y movilidad suave de todo el cuerpo.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Como sentarse y levantarse de una silla, con el peso abrazado."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Empuja exhalando, sin bloquear los codos de golpe."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tira llevando los hombros atrás, pecho abierto."
     },
     {
      "name": "Sentadilla en pared (isométrica)",
      "sets": 2,
      "rep_range": "30-45s",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Espalda apoyada, muslos hacia paralelo según tolerancia."
     },
     {
      "name": "Bird dog",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Equilibrio y espalda estable, sin prisa."
     }
    ],
    "cooldown": "Caminata suave 5 min y estiramientos asistidos."
   },
   {
    "day": "Viernes",
    "name": "Funcional 2 — Escalones, cargar y tirar",
    "warmup": "5 min de bici estática y movilidad de cadera y hombro.",
    "exercises": [
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Escalón bajo al principio; sube sin impulsarte con la otra pierna."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tira suave hacia el pecho, torso erguido."
     },
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Empuja con toda la planta, rodillas alineadas."
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Como llevar la bolsa de la compra: erguida y sin inclinarte."
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Agárrate a un apoyo y sube a las puntas con control."
     }
    ],
    "cooldown": "Estiramientos suaves y respiración, 5 minutos."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: aprender los gestos con cargas muy cómodas.",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "La sensación al acabar debe ser de energía, no de agotamiento."
   },
   {
    "week": 2,
    "intent": "Progresión: pequeño aumento donde la técnica sea segura.",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Sube el mínimo escalón de peso que permita la máquina."
   },
   {
    "week": 3,
    "intent": "Carga: semana más activa, siempre con margen amplio.",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "El hueso agradece la carga progresiva y regular."
   },
   {
    "week": 4,
    "intent": "Descarga: consolidar el hábito sin fatiga.",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Dos series por ejercicio y más tiempo de movilidad."
   }
  ],
  "cardio": {
   "daily_steps": 7000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 3,
     "notes": "Caminata a paso vivo, mejor con alguna cuesta suave."
    }
   ]
  },
  "deload_instructions": "Semana 4 con cargas al 90 por ciento y dos series por ejercicio; si alguna semana hay dolor articular o mareo, reduce la carga y coméntalo antes de continuar."
 },
 {
  "category": "ganancia_muscular",
  "title": "Base de volumen para novato",
  "case": "Chico de 19 años muy delgado, sin experiencia previa, quiere ganar peso y músculo con una estructura sencilla que pueda aprender bien.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body A/B/C",
  "split_rationale": "Tres estímulos semanales por grupo con técnica sencilla, la frecuencia alta acelera el aprendizaje motor del novato.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Full body A",
    "warmup": "5 min de bici suave y movilidad general",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Torso erguido, rodillas hacia fuera"
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Escápulas retraídas en el banco"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tira con los codos, pecho alto"
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadera atrás, espalda neutra"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Glúteo y abdomen apretados"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   },
   {
    "day": "Miércoles",
    "name": "Full body B",
    "warmup": "5 min de bici suave y movilidad general",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Baja controlado sin despegar la cadera"
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "No bloquees los codos arriba"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Lleva la barra a la clavícula"
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Cadera pegada al banco"
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Lumbar pegada al suelo"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   },
   {
    "day": "Viernes",
    "name": "Full body C",
    "warmup": "5 min de bici suave y movilidad general",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2-3",
      "rest_sec": 150,
      "technique_cue": "Empuja el suelo con las piernas"
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Recorrido completo sin rebotes"
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Junta las escápulas al final"
     },
     {
      "name": "Zancada estática",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Rodilla alineada con el pie"
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Pausa arriba un segundo"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: aprender técnica con cargas cómodas",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Series indicadas"
   },
   {
    "week": 2,
    "intent": "Progresión: sube ligeramente el peso",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Misma estructura"
   },
   {
    "week": 3,
    "intent": "Carga: semana más exigente",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Añade 1 serie al primer ejercicio"
   },
   {
    "week": 4,
    "intent": "Descarga: recuperar para el siguiente bloque",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Quita 1 serie por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 20,
     "times_per_week": 1,
     "notes": "Paseo rápido, día libre"
    }
   ]
  },
  "deload_instructions": "Semana 4: reduce el peso al 90 por ciento y una serie por ejercicio, mantén la técnica intacta."
 },
 {
  "category": "ganancia_muscular",
  "title": "Torso-pierna antiestancamiento",
  "case": "Hombre de 28 años con tres años de gimnasio, lleva meses sin progresar en los básicos y necesita variar estímulo entre fuerza y volumen.",
  "level": "intermediate",
  "days_per_week": 4,
  "place": "gym",
  "split_name": "Torso-pierna con días de fuerza y volumen",
  "split_rationale": "Doble frecuencia por grupo combinando rangos pesados y medios, la variación intra-semanal suele romper el estancamiento.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Torso fuerza",
    "warmup": "Movilidad de hombro y aproximaciones",
    "exercises": [
     {
      "name": "Press banca con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Pies firmes, escápulas retraídas"
     },
     {
      "name": "Remo con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Torso fijo, sin impulso lumbar"
     },
     {
      "name": "Press militar sentado con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Costillas abajo, core firme"
     },
     {
      "name": "Jalón agarre estrecho neutro",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Codos hacia las caderas"
     },
     {
      "name": "Curl de bíceps con barra EZ",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Codos pegados al cuerpo"
     }
    ],
    "cooldown": "Estiramiento de pectoral y dorsal"
   },
   {
    "day": "Martes",
    "name": "Pierna fuerza",
    "warmup": "Movilidad de cadera y series de aproximación",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Rompe la paralela con control"
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Barra pegada a las piernas"
     },
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "No bloquees rodillas arriba"
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Flexión completa sin rebote"
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Estira abajo, pausa arriba"
     }
    ],
    "cooldown": "Estiramiento de cuádriceps e isquios"
   },
   {
    "day": "Jueves",
    "name": "Torso volumen",
    "warmup": "Movilidad de hombro y aproximaciones",
    "exercises": [
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Baja hasta estirar el pectoral"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Pausa breve en la contracción"
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Sube con el codo, no la mano"
     },
     {
      "name": "Cruce de poleas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Junta las manos delante del pecho"
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Separa la cuerda al final"
     }
    ],
    "cooldown": "Estiramiento suave de torso"
   },
   {
    "day": "Viernes",
    "name": "Pierna volumen",
    "warmup": "Movilidad de cadera y tobillo",
    "exercises": [
     {
      "name": "Sentadilla búlgara",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Torso ligeramente inclinado"
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Bloqueo de cadera con glúteo"
     },
     {
      "name": "Extensión de rodilla en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Pausa de un segundo arriba"
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Cadera pegada al banco"
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo lento"
     }
    ],
    "cooldown": "Estiramientos de pierna 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación al nuevo reparto de intensidades",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Series base"
   },
   {
    "week": 2,
    "intent": "Progresión de carga en los básicos",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Misma estructura"
   },
   {
    "week": 3,
    "intent": "Carga: semana pico del bloque",
    "load_pct": 105,
    "rir_target": "1",
    "volume_note": "Añade 1 serie a press y sentadilla"
   },
   {
    "week": 4,
    "intent": "Descarga para consolidar",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Reduce un tercio de las series"
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 1
    }
   ]
  },
  "deload_instructions": "Semana 4: 90 por ciento de la carga y dos tercios de las series, sin llegar nunca al fallo."
 },
 {
  "category": "ganancia_muscular",
  "title": "Especialización avanzada en cinco días",
  "case": "Hombre de 34 años con diez años de entrenamiento serio, busca exprimir un bloque de hipertrofia con alta frecuencia y buena recuperación entre sesiones.",
  "level": "advanced",
  "days_per_week": 5,
  "place": "gym",
  "split_name": "Empuje-tracción-pierna más torso-pierna",
  "split_rationale": "Cada grupo se toca dos veces con volúmenes repartidos, lo que permite alta carga semanal sin sesiones eternas.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Empuje pesado",
    "warmup": "Movilidad de hombro y aproximaciones",
    "exercises": [
     {
      "name": "Press banca con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "1-2",
      "rest_sec": 180,
      "technique_cue": "Codos a 45 grados del torso"
     },
     {
      "name": "Press militar de pie con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Glúteo apretado, sin arquear"
     },
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Trayectoria en ligera diagonal"
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1",
      "rest_sec": 60,
      "technique_cue": "Sin balanceo del torso"
     },
     {
      "name": "Fondos en paralelas (énfasis tríceps)",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Torso vertical, codos atrás"
     }
    ],
    "cooldown": "Estiramiento de pectoral y tríceps"
   },
   {
    "day": "Martes",
    "name": "Tracción pesada",
    "warmup": "Activación escapular y aproximaciones",
    "exercises": [
     {
      "name": "Dominadas lastradas",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "1-2",
      "rest_sec": 180,
      "technique_cue": "Pecho a la barra, sin kipping"
     },
     {
      "name": "Remo Pendlay",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Cada repetición desde el suelo"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Pausa en la contracción"
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Rota los hombros hacia fuera"
     },
     {
      "name": "Curl de bíceps con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "1",
      "rest_sec": 75,
      "technique_cue": "Sin balanceo lumbar"
     }
    ],
    "cooldown": "Estiramiento de dorsal y bíceps"
   },
   {
    "day": "Miércoles",
    "name": "Pierna fuerza",
    "warmup": "Movilidad de cadera y aproximaciones",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "1-2",
      "rest_sec": 180,
      "technique_cue": "Rodillas siguen la punta del pie"
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Estira el isquio, no la lumbar"
     },
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Baja profundo sin retroversión"
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1",
      "rest_sec": 90,
      "technique_cue": "Excéntrica de tres segundos"
     },
     {
      "name": "Elevación de talones en prensa",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "1",
      "rest_sec": 60,
      "technique_cue": "Estiramiento completo abajo"
     }
    ],
    "cooldown": "Estiramientos de pierna 5 min"
   },
   {
    "day": "Viernes",
    "name": "Torso volumen",
    "warmup": "Movilidad de hombro y aproximaciones",
    "exercises": [
     {
      "name": "Press banca inclinado con barra",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "1-2",
      "rest_sec": 150,
      "technique_cue": "Barra a la parte alta del pecho"
     },
     {
      "name": "Remo con barra T",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Aprieta la espalda media"
     },
     {
      "name": "Press Arnold",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Gira sin perder tensión"
     },
     {
      "name": "Pullover en polea alta",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1",
      "rest_sec": 60,
      "technique_cue": "Brazos casi rectos todo el arco"
     },
     {
      "name": "Press francés con barra EZ",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1",
      "rest_sec": 75,
      "technique_cue": "Codos fijos apuntando al techo"
     }
    ],
    "cooldown": "Estiramiento suave de torso"
   },
   {
    "day": "Sábado",
    "name": "Pierna volumen",
    "warmup": "Movilidad de cadera y tobillo",
    "exercises": [
     {
      "name": "Sentadilla frontal con barra",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Codos altos todo el recorrido"
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Mentón recogido al bloquear"
     },
     {
      "name": "Zancadas caminando con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Pasos largos y estables"
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1",
      "rest_sec": 75,
      "technique_cue": "Flexión completa sin rebote"
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 4,
      "rep_range": "12-15",
      "rir": "1",
      "rest_sec": 60,
      "technique_cue": "Pausa arriba un segundo"
     }
    ],
    "cooldown": "Estiramientos de pierna 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: fijar cargas de referencia",
    "load_pct": 100,
    "rir_target": "2",
    "volume_note": "Series base"
   },
   {
    "week": 2,
    "intent": "Progresión de cargas en básicos",
    "load_pct": 102.5,
    "rir_target": "1-2",
    "volume_note": "Añade 1 serie a un accesorio por sesión"
   },
   {
    "week": 3,
    "intent": "Carga: pico de esfuerzo del bloque",
    "load_pct": 105,
    "rir_target": "0-1",
    "volume_note": "Volumen máximo tolerable"
   },
   {
    "week": 4,
    "intent": "Descarga profunda",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Mitad de series, sin fallar"
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 20,
     "times_per_week": 2,
     "notes": "Recuperación activa"
    }
   ]
  },
  "deload_instructions": "Semana 4: mitad de series y 90 por ciento de carga; si el sueño o el apetito caen, adelanta la descarga."
 },
 {
  "category": "ganancia_muscular",
  "title": "Glúteo y pierna con base de torso",
  "case": "Mujer de 26 años, dos años de gimnasio, prioriza glúteo y pierna sin descuidar el torso, con tres días reales disponibles.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Inferior-superior-inferior con énfasis en glúteo",
  "split_rationale": "Dos sesiones de tren inferior con patrones de extensión de cadera dominantes y una de torso completo para no dejar huecos.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Glúteo fuerza",
    "warmup": "Activación de glúteo con banda y aproximaciones",
    "exercises": [
     {
      "name": "Hip thrust con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Bloqueo total de cadera arriba"
     },
     {
      "name": "Sentadilla trasera con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Profundidad cómoda y estable"
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Cadera atrás, barra pegada"
     },
     {
      "name": "Abducción de cadera en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Torso inclinado adelante"
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Pausa arriba un segundo"
     }
    ],
    "cooldown": "Estiramientos de cadera 5 min"
   },
   {
    "day": "Miércoles",
    "name": "Torso completo",
    "warmup": "Movilidad de hombro y aproximaciones",
    "exercises": [
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Escápulas retraídas en el banco"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Codos hacia abajo y atrás"
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Sube sin chocar arriba"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Pecho alto, tira con los codos"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Cadera alineada, sin hundirla"
     }
    ],
    "cooldown": "Estiramiento suave de torso"
   },
   {
    "day": "Viernes",
    "name": "Glúteo volumen",
    "warmup": "Activación de glúteo y movilidad de tobillo",
    "exercises": [
     {
      "name": "Sentadilla búlgara",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Torso inclinado carga el glúteo"
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Contracción de un segundo arriba"
     },
     {
      "name": "Zancada curtsy",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Cruza sin rotar la cadera"
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Excéntrica controlada"
     },
     {
      "name": "Patada de glúteo en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1",
      "rest_sec": 60,
      "technique_cue": "Extiende sin arquear la lumbar"
     }
    ],
    "cooldown": "Estiramientos de pierna 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación con cargas cómodas",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Series base"
   },
   {
    "week": 2,
    "intent": "Progresión en hip thrust y sentadilla",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Misma estructura"
   },
   {
    "week": 3,
    "intent": "Carga: semana más dura",
    "load_pct": 105,
    "rir_target": "1",
    "volume_note": "Añade 1 serie a los dos primeros ejercicios"
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Quita 1 serie por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 1,
     "notes": "Paseo o elíptica suave"
    }
   ]
  },
  "deload_instructions": "Semana 4: baja al 90 por ciento y elimina una serie por ejercicio, mantén la activación de glúteo."
 },
 {
  "category": "ganancia_muscular",
  "title": "Masa magra pasados los cincuenta",
  "case": "Mujer de 56 años, oficina y poca actividad, quiere ganar masa muscular y proteger hueso y articulaciones con máquinas y cargas progresivas.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body en máquinas y peso libre ligero",
  "split_rationale": "Frecuencia tres con ejercicios estables y de baja demanda técnica, ideal para progresar con seguridad articular.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Cuerpo completo A",
    "warmup": "7 min de bici y movilidad articular",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Empuja con todo el pie"
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Recorrido cómodo sin dolor"
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Hombros lejos de las orejas"
     },
     {
      "name": "Curl femoral sentado",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Movimiento lento y completo"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Respira sin perder tensión"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   },
   {
    "day": "Miércoles",
    "name": "Cuerpo completo B",
    "warmup": "7 min de bici y movilidad articular",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Siéntate entre las caderas"
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Sin bloquear los codos"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Baja la barra sin echarte atrás"
     },
     {
      "name": "Hiperextensiones 45°",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Sube con glúteo, no con lumbar"
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Lumbar pegada al suelo"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   },
   {
    "day": "Viernes",
    "name": "Cuerpo completo C",
    "warmup": "7 min de bici y movilidad articular",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 150,
      "technique_cue": "Espalda neutra, empuja el suelo"
     },
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Baja controlado al pecho"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho alto, codos atrás"
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Apoyo estable, sube completo"
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Cadera nivelada, sin girar"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: técnica y confianza",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Series base"
   },
   {
    "week": 2,
    "intent": "Progresión suave de carga",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Misma estructura"
   },
   {
    "week": 3,
    "intent": "Carga: semana más exigente",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Añade 1 serie a los ejercicios de pierna"
   },
   {
    "week": 4,
    "intent": "Descarga y recuperación",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Reduce una serie por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 7500,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Caminata a paso vivo"
    }
   ]
  },
  "deload_instructions": "Semana 4: reduce carga al 90 por ciento y una serie por ejercicio; prioriza dormir bien esa semana."
 },
 {
  "category": "ganancia_muscular",
  "title": "Volumen esencial en dos días",
  "case": "Hombre de 22 años, ectomorfo, trabaja y estudia a la vez, solo dispone de dos días de gimnasio y quiere el máximo estímulo por sesión.",
  "level": "beginner",
  "days_per_week": 2,
  "place": "gym",
  "split_name": "Full body pesado en dos sesiones",
  "split_rationale": "Con dos días, dos sesiones de cuerpo completo con básicos multiarticulares cubren todos los patrones con estímulo suficiente.",
  "sessions": [
   {
    "day": "Martes",
    "name": "Cuerpo completo 1",
    "warmup": "Movilidad general y series de aproximación",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Aprieta el core antes de bajar"
     },
     {
      "name": "Press banca con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Escápulas retraídas y pies firmes"
     },
     {
      "name": "Remo con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Torso fijo, tira al abdomen"
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Sube sin chocar las mancuernas"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Glúteo apretado todo el tiempo"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   },
   {
    "day": "Viernes",
    "name": "Cuerpo completo 2",
    "warmup": "Movilidad general y series de aproximación",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Empuja el suelo, no tires"
     },
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Baja hasta estirar el pectoral"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Codos hacia abajo y atrás"
     },
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Paso atrás largo y estable"
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Cadera pegada al banco"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación a los básicos",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Series base"
   },
   {
    "week": 2,
    "intent": "Progresión de carga",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Misma estructura"
   },
   {
    "week": 3,
    "intent": "Carga: máximo del bloque",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Añade 1 serie a sentadilla y press"
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Tres series máximo por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 6000,
   "sessions": []
  },
  "deload_instructions": "Semana 4: 90 por ciento de la carga y máximo tres series por ejercicio; el ectomorfo no debe sumar cardio extra."
 },
 {
  "category": "ganancia_muscular",
  "title": "Prioridad torso con pierna de mantenimiento",
  "case": "Hombre de 30 años con pierna fuerte de su etapa de ciclista, torso visiblemente rezagado, tres días de gimnasio.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Dos días de torso, uno de pierna",
  "split_rationale": "El volumen semanal se desplaza al torso rezagado, la pierna mantiene con una sesión de básicos.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Pecho y espalda pesado",
    "warmup": "Movilidad de hombro y aproximaciones",
    "exercises": [
     {
      "name": "Press banca con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Barra a la línea del pezón"
     },
     {
      "name": "Remo con barra",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Sin impulso lumbar"
     },
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Estira bien abajo"
     },
     {
      "name": "Jalón agarre estrecho neutro",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Codos hacia las caderas"
     },
     {
      "name": "Cruce de poleas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1",
      "rest_sec": 60,
      "technique_cue": "Contracción de un segundo"
     }
    ],
    "cooldown": "Estiramiento de pectoral y dorsal"
   },
   {
    "day": "Miércoles",
    "name": "Pierna de mantenimiento",
    "warmup": "Movilidad de cadera y aproximaciones",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Profundidad estable y constante"
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Cadera atrás, espalda neutra"
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Sin rebotes en la flexión"
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Pausa arriba un segundo"
     }
    ],
    "cooldown": "Estiramientos de pierna 5 min"
   },
   {
    "day": "Viernes",
    "name": "Hombro y brazo",
    "warmup": "Movilidad de hombro y aproximaciones",
    "exercises": [
     {
      "name": "Press militar sentado con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Cabeza atraviesa al bloquear"
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 4,
      "rep_range": "12-15",
      "rir": "1",
      "rest_sec": 60,
      "technique_cue": "Codos por encima de las manos"
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Tira hacia la frente"
     },
     {
      "name": "Curl de bíceps con barra EZ",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Codos fijos al costado"
     },
     {
      "name": "Press francés con barra EZ",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Baja a la frente controlado"
     }
    ],
    "cooldown": "Estiramiento de hombro y brazo"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación al reparto priorizado",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Series base"
   },
   {
    "week": 2,
    "intent": "Progresión en presses y remos",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Misma estructura"
   },
   {
    "week": 3,
    "intent": "Carga: pico del bloque",
    "load_pct": 105,
    "rir_target": "1",
    "volume_note": "Añade 1 serie a los ejercicios de torso"
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Quita una serie por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 20,
     "times_per_week": 1
    }
   ]
  },
  "deload_instructions": "Semana 4: reduce al 90 por ciento y una serie menos por ejercicio, mantén la sesión de pierna intacta."
 },
 {
  "category": "ganancia_muscular",
  "title": "Amplitud de espalda dominante",
  "case": "Hombre de 27 años, nadador aficionado, quiere una espalda claramente más ancha manteniendo el resto del cuerpo proporcionado.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Espalda-anchura, empuje-pierna, espalda-densidad",
  "split_rationale": "Dos sesiones de espalda separan trabajo vertical de horizontal, el día central cubre empuje y pierna sin huecos.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Espalda anchura",
    "warmup": "Activación escapular con banda",
    "exercises": [
     {
      "name": "Dominadas pronas",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Pecho a la barra, escápulas abajo"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Agarre ancho, codos abajo"
     },
     {
      "name": "Jalón con brazos rectos en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Siente el dorsal todo el arco"
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos altos, rotación externa"
     },
     {
      "name": "Curl de bíceps con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Sin balanceo del torso"
     }
    ],
    "cooldown": "Estiramiento de dorsal 5 min"
   },
   {
    "day": "Miércoles",
    "name": "Empuje y pierna",
    "warmup": "Movilidad general y aproximaciones",
    "exercises": [
     {
      "name": "Press banca con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Escápulas retraídas, pies firmes"
     },
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Core firme antes de bajar"
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Trayectoria vertical limpia"
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Excéntrica controlada"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   },
   {
    "day": "Viernes",
    "name": "Espalda densidad",
    "warmup": "Activación escapular con banda",
    "exercises": [
     {
      "name": "Remo con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Tira a la parte baja del abdomen"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Pausa en la contracción"
     },
     {
      "name": "Remo en polea a una mano",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Rota ligeramente al tirar"
     },
     {
      "name": "Encogimientos con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Sube recto, sin rodar hombros"
     },
     {
      "name": "Curl martillo",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Muñecas neutras firmes"
     }
    ],
    "cooldown": "Estiramiento de dorsal 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: fija cargas en dominadas y remos",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Series base"
   },
   {
    "week": 2,
    "intent": "Progresión de carga o repeticiones",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Misma estructura"
   },
   {
    "week": 3,
    "intent": "Carga: semana pico",
    "load_pct": 105,
    "rir_target": "1",
    "volume_note": "Añade 1 serie a los jalones y remos"
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Quita una serie por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 1,
     "notes": "Natación suave cuenta"
    }
   ]
  },
  "deload_instructions": "Semana 4: dominadas sin lastre, cargas al 90 por ciento y una serie menos por ejercicio."
 },
 {
  "category": "ganancia_muscular",
  "title": "Rescate de brazos rezagados",
  "case": "Hombre de 31 años con buena espalda y pecho pero brazos finos que no responden, tres días con doble estímulo directo de brazo.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Brazo pesado, pierna, torso con brazo de volumen",
  "split_rationale": "El brazo recibe dos sesiones directas en rangos distintos, pierna y torso mantienen el resto sin robar recuperación.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Brazos fuerza",
    "warmup": "Movilidad de codo y muñeca, aproximaciones",
    "exercises": [
     {
      "name": "Press banca agarre cerrado",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Codos pegados al torso"
     },
     {
      "name": "Curl de bíceps con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Sube sin echar el cuerpo atrás"
     },
     {
      "name": "Extensión de tríceps en polea con barra",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos fijos al costado"
     },
     {
      "name": "Curl inclinado con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Estira el bíceps abajo"
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Sin encoger los trapecios"
     }
    ],
    "cooldown": "Estiramiento de brazo 5 min"
   },
   {
    "day": "Miércoles",
    "name": "Pierna y core",
    "warmup": "Movilidad de cadera y aproximaciones",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Rodillas hacia fuera al bajar"
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Barra pegada a las piernas"
     },
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Sin despegar la cadera"
     },
     {
      "name": "Crunch en polea alta",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Flexiona desde las costillas"
     }
    ],
    "cooldown": "Estiramientos de pierna 5 min"
   },
   {
    "day": "Viernes",
    "name": "Torso y brazos volumen",
    "warmup": "Movilidad de hombro y aproximaciones",
    "exercises": [
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Baja hasta estirar el pectoral"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho alto, codos atrás"
     },
     {
      "name": "Curl predicador",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1",
      "rest_sec": 75,
      "technique_cue": "Extiende casi completo abajo"
     },
     {
      "name": "Extensión de tríceps sobre la cabeza en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1",
      "rest_sec": 60,
      "technique_cue": "Estira el tríceps atrás"
     },
     {
      "name": "Curl martillo",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "1",
      "rest_sec": 60,
      "technique_cue": "Sin balanceo, ritmo constante"
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "1",
      "rest_sec": 60,
      "technique_cue": "Separa la cuerda al extender"
     }
    ],
    "cooldown": "Estiramiento de brazo 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación al volumen de brazo",
    "load_pct": 100,
    "rir_target": "2",
    "volume_note": "Series base"
   },
   {
    "week": 2,
    "intent": "Progresión en curls y extensiones",
    "load_pct": 102.5,
    "rir_target": "1-2",
    "volume_note": "Misma estructura"
   },
   {
    "week": 3,
    "intent": "Carga: pico de estímulo de brazo",
    "load_pct": 105,
    "rir_target": "0-1",
    "volume_note": "Añade 1 serie a un curl y una extensión"
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Mitad de series de brazo"
   }
  ],
  "cardio": {
   "daily_steps": 7500,
   "sessions": [
    {
     "type": "liss",
     "minutes": 20,
     "times_per_week": 1
    }
   ]
  },
  "deload_instructions": "Semana 4: mitad de series de brazo y 90 por ciento de carga; si aparecen molestias de codo, cambia a agarres neutros."
 },
 {
  "category": "ganancia_muscular",
  "title": "Full body clásico de tres días",
  "case": "Mujer de 38 años, madre con agenda apretada, quiere ganar músculo general y fuerza funcional con tres sesiones completas por semana.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body A/B/C clásico",
  "split_rationale": "Tres sesiones completas alternando variantes cubren todos los patrones con frecuencia tres y sesiones de menos de una hora.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Full body A",
    "warmup": "5 min de cardio suave y movilidad",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Codos por dentro de las rodillas"
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Recorrido completo controlado"
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Espalda plana sobre el banco"
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadera atrás, rodillas suaves"
     },
     {
      "name": "Plancha lateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Cadera alta y alineada"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   },
   {
    "day": "Miércoles",
    "name": "Full body B",
    "warmup": "5 min de cardio suave y movilidad",
    "exercises": [
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Paso atrás controlado"
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Sube sin chocar arriba"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Codos hacia abajo y atrás"
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Cadera pegada al banco"
     },
     {
      "name": "Crunch en polea alta",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Enrolla la columna al bajar"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   },
   {
    "day": "Viernes",
    "name": "Full body C",
    "warmup": "5 min de cardio suave y movilidad",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Baja controlado, empuja fuerte"
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Escápulas retraídas"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho alto al tirar"
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Bloqueo de glúteo arriba"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Abdomen y glúteo firmes"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación con técnica limpia",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Series base"
   },
   {
    "week": 2,
    "intent": "Progresión suave de carga",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Misma estructura"
   },
   {
    "week": 3,
    "intent": "Carga: semana más exigente",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Añade 1 serie al primer ejercicio"
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 8500,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 1,
     "notes": "Caminata a paso vivo"
    }
   ]
  },
  "deload_instructions": "Semana 4: baja al 90 por ciento de carga y una serie por ejercicio, mantén las tres sesiones."
 },
 {
  "category": "ganancia_muscular",
  "title": "Torso-pierna en cuatro días",
  "case": "Hombre de 24 años con horario laboral estable de mañanas, quiere una estructura clásica y sostenible de cuatro días para ganar masa general.",
  "level": "intermediate",
  "days_per_week": 4,
  "place": "gym",
  "split_name": "Upper-lower clásico",
  "split_rationale": "Frecuencia dos por grupo con reparto claro de básicos y accesorios, la estructura más sostenible para un intermedio con rutina fija.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Torso A",
    "warmup": "Movilidad de hombro y aproximaciones",
    "exercises": [
     {
      "name": "Press banca con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Pies firmes, arco natural"
     },
     {
      "name": "Remo con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Torso fijo a 45 grados"
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Trayectoria vertical limpia"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Baja a la clavícula"
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos fijos al costado"
     }
    ],
    "cooldown": "Estiramiento suave de torso"
   },
   {
    "day": "Martes",
    "name": "Pierna A",
    "warmup": "Movilidad de cadera y aproximaciones",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Core firme antes de bajar"
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Excéntrica de tres segundos"
     },
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "No bloquees rodillas arriba"
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Pausa arriba un segundo"
     },
     {
      "name": "Crunch en polea alta",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Enrolla la columna"
     }
    ],
    "cooldown": "Estiramientos de pierna 5 min"
   },
   {
    "day": "Jueves",
    "name": "Torso B",
    "warmup": "Movilidad de hombro y aproximaciones",
    "exercises": [
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Baja hasta estirar el pectoral"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Pausa en la contracción"
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1",
      "rest_sec": 60,
      "technique_cue": "Codos por encima de las manos"
     },
     {
      "name": "Face pull en polea",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Rotación externa al final"
     },
     {
      "name": "Curl martillo",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Muñecas neutras firmes"
     }
    ],
    "cooldown": "Estiramiento suave de torso"
   },
   {
    "day": "Viernes",
    "name": "Pierna B",
    "warmup": "Movilidad de cadera y tobillo",
    "exercises": [
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Cadera atrás, barra pegada"
     },
     {
      "name": "Sentadilla búlgara",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Rodilla alineada con el pie"
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Bloqueo total de cadera"
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1",
      "rest_sec": 75,
      "technique_cue": "Flexión completa sin rebote"
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo lento"
     }
    ],
    "cooldown": "Estiramientos de pierna 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: cargas de referencia",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Series base"
   },
   {
    "week": 2,
    "intent": "Progresión en los básicos",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Misma estructura"
   },
   {
    "week": 3,
    "intent": "Carga: semana pico",
    "load_pct": 105,
    "rir_target": "1",
    "volume_note": "Añade 1 serie al primer ejercicio de cada día"
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 20,
     "times_per_week": 1
    }
   ]
  },
  "deload_instructions": "Semana 4: reduce al 90 por ciento y una serie por ejercicio; no metas trabajo extra ese fin de semana."
 },
 {
  "category": "ganancia_muscular",
  "title": "Empuje, tracción y pierna semanal",
  "case": "Hombre de 29 años, intermedio, entrena en un gimnasio de barrio bien equipado y prefiere sesiones monotemáticas de una hora, tres veces por semana.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Push-pull-legs de frecuencia uno",
  "split_rationale": "Cada patrón concentra su volumen semanal en una sesión completa; con recuperación amplia encaja bien en tres días fijos.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Empuje",
    "warmup": "Movilidad de hombro y aproximaciones",
    "exercises": [
     {
      "name": "Press banca con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Escápulas retraídas, pies firmes"
     },
     {
      "name": "Press militar sentado con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Costillas abajo al empujar"
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1",
      "rest_sec": 60,
      "technique_cue": "Sube con el codo"
     },
     {
      "name": "Cruce de poleas",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "1",
      "rest_sec": 60,
      "technique_cue": "Junta manos delante del pecho"
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Separa la cuerda al final"
     }
    ],
    "cooldown": "Estiramiento de pectoral y hombro"
   },
   {
    "day": "Miércoles",
    "name": "Tracción",
    "warmup": "Activación escapular con banda",
    "exercises": [
     {
      "name": "Dominadas pronas",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Escápulas abajo antes de tirar"
     },
     {
      "name": "Remo con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Torso fijo, sin impulso"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Pausa en la contracción"
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Tira hacia la frente"
     },
     {
      "name": "Curl de bíceps con barra EZ",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Codos fijos al costado"
     }
    ],
    "cooldown": "Estiramiento de dorsal y bíceps"
   },
   {
    "day": "Viernes",
    "name": "Pierna",
    "warmup": "Movilidad de cadera y aproximaciones",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Profundidad constante"
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Estira el isquio, no la lumbar"
     },
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Sin despegar la cadera"
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Cadera pegada al banco"
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Pausa arriba un segundo"
     }
    ],
    "cooldown": "Estiramientos de pierna 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación al reparto por patrones",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Series base"
   },
   {
    "week": 2,
    "intent": "Progresión de carga",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Misma estructura"
   },
   {
    "week": 3,
    "intent": "Carga: pico del bloque",
    "load_pct": 105,
    "rir_target": "1",
    "volume_note": "Añade 1 serie al básico de cada día"
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 20,
     "times_per_week": 1
    }
   ]
  },
  "deload_instructions": "Semana 4: 90 por ciento de la carga y una serie menos por ejercicio, deja las dominadas sin lastre."
 },
 {
  "category": "ganancia_muscular",
  "title": "Hipertrofia en casa con mancuernas",
  "case": "Mujer de 29 años que teletrabaja, dispone de mancuernas, bandas y una esterilla en casa; quiere ganar músculo sin pisar un gimnasio.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "home",
  "split_name": "Full body en casa A/B/C",
  "split_rationale": "Tres sesiones completas con mancuernas, bandas y peso corporal cubren todos los patrones sin necesitar banco ni máquinas.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Casa A",
    "warmup": "Movilidad general y activación con banda",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Torso erguido, talones firmes"
     },
     {
      "name": "Flexiones",
      "sets": 3,
      "rep_range": "8-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cuerpo en línea recta"
     },
     {
      "name": "Remo con banda sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Junta escápulas al final"
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadera atrás, espalda neutra"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Glúteo y abdomen apretados"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   },
   {
    "day": "Miércoles",
    "name": "Casa B",
    "warmup": "Movilidad general y activación con banda",
    "exercises": [
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Paso atrás largo y estable"
     },
     {
      "name": "Press de hombro unilateral con mancuerna de pie",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Core firme, sin arquear"
     },
     {
      "name": "Remo invertido bajo una mesa",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho a la mesa, cuerpo recto"
     },
     {
      "name": "Puente de glúteo a una pierna",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Cadera arriba sin rotar"
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Lumbar pegada al suelo"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   },
   {
    "day": "Viernes",
    "name": "Casa C",
    "warmup": "Movilidad general y activación con banda",
    "exercises": [
     {
      "name": "Sentadilla búlgara con peso corporal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Rodilla alineada con el pie"
     },
     {
      "name": "Press de pecho con banda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Tensión constante de la banda"
     },
     {
      "name": "Jalón con banda de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos hacia las caderas"
     },
     {
      "name": "Peso muerto rumano a una pierna",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Cadera cuadrada al suelo"
     },
     {
      "name": "Curl alterno con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Sin balanceo del torso"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación al material de casa",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Series base"
   },
   {
    "week": 2,
    "intent": "Progresión: más repeticiones o tempo lento",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Misma estructura"
   },
   {
    "week": 3,
    "intent": "Carga: ritmo lento y rangos altos",
    "load_pct": 105,
    "rir_target": "1",
    "volume_note": "Añade 1 serie a pierna y empuje"
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 1,
     "notes": "Caminata al aire libre"
    }
   ]
  },
  "deload_instructions": "Semana 4: usa las mancuernas más ligeras y quita una serie por ejercicio; con mancuernas fijas progresa por repeticiones y tempo."
 },
 {
  "category": "ganancia_muscular",
  "title": "Reconstrucción tras un parón largo",
  "case": "Hombre de 41 años que entrenó fuerte en su juventud y lleva año y medio parado por trabajo; quiere volver sin lesionarse por las prisas.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body de reintroducción",
  "split_rationale": "La memoria muscular responde rápido; frecuencia tres con cargas moderadas y máquinas estables reduce las agujetas brutales de la vuelta.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Reintroducción A",
    "warmup": "8 min de cardio suave y movilidad completa",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Profundidad cómoda al inicio"
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Baja controlado sin rebote"
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Hombros lejos de las orejas"
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 75,
      "technique_cue": "Movimiento lento y completo"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Cadera alineada"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   },
   {
    "day": "Miércoles",
    "name": "Reintroducción B",
    "warmup": "8 min de cardio suave y movilidad completa",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Empuja con todo el pie"
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Sin bloquear los codos"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Baja a la clavícula"
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Cadera atrás, espalda neutra"
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Extiende sin girar la cadera"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   },
   {
    "day": "Viernes",
    "name": "Reintroducción C",
    "warmup": "8 min de cardio suave y movilidad completa",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 150,
      "technique_cue": "Empuja el suelo con las piernas"
     },
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Estira sin forzar el hombro"
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tira con el codo al costado"
     },
     {
      "name": "Zancada estática",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Rodilla estable, torso erguido"
     },
     {
      "name": "Crunch en polea alta",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Flexiona desde las costillas"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: cargas muy conservadoras",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Series base, sin fallar nunca"
   },
   {
    "week": 2,
    "intent": "Progresión si no hay molestias",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Misma estructura"
   },
   {
    "week": 3,
    "intent": "Carga moderada, escucha al cuerpo",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Añade 1 serie al primer ejercicio"
   },
   {
    "week": 4,
    "intent": "Descarga antes del siguiente bloque",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 2,
     "notes": "Bici o caminata suave"
    }
   ]
  },
  "deload_instructions": "Semana 4: 90 por ciento de carga y una serie menos; si alguna articulación avisa antes, descarga esa semana sin esperar."
 },
 {
  "category": "ganancia_muscular",
  "title": "Hipertrofia con rodilla protegida",
  "case": "Hombre de 37 años con molestia crónica de rodilla al flexionar profundo; quiere seguir ganando pierna y masa general sin agravarla.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Pierna adaptada, torso y día mixto",
  "split_rationale": "La pierna se trabaja con bisagras de cadera, prensa horizontal y patrones tolerables, evitando todo ejercicio con contraindicación de rodilla.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Pierna sin estrés de rodilla",
    "warmup": "10 min de bici suave y movilidad de cadera",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Rango que no provoque dolor"
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Cadera atrás, rodillas suaves"
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Excéntrica controlada"
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Bloqueo con glúteo, tibia vertical"
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo lento"
     }
    ],
    "cooldown": "Estiramientos suaves de pierna"
   },
   {
    "day": "Miércoles",
    "name": "Torso completo",
    "warmup": "Movilidad de hombro y aproximaciones",
    "exercises": [
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Escápulas retraídas"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho alto al tirar"
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Sin bloquear arriba"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Codos hacia abajo y atrás"
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos fijos al costado"
     }
    ],
    "cooldown": "Estiramiento suave de torso"
   },
   {
    "day": "Viernes",
    "name": "Mixto tolerable",
    "warmup": "10 min de bici suave y movilidad general",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Empuja el suelo, torso firme"
     },
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Altura de cajón sin dolor"
     },
     {
      "name": "Sentadilla en pared (isométrica)",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Ángulo cómodo, sin molestia"
     },
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Baja controlado al pecho"
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Espalda plana en el banco"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación respetando la rodilla",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Series base"
   },
   {
    "week": 2,
    "intent": "Progresión solo sin molestias",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Misma estructura"
   },
   {
    "week": 3,
    "intent": "Carga en bisagras y torso",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Añade 1 serie a bisagras y presses"
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 7000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 2,
     "notes": "Bici sin resistencia alta"
    }
   ]
  },
  "deload_instructions": "Semana 4: 90 por ciento y una serie menos; cualquier dolor de rodilla durante una serie la termina en ese momento."
 },
 {
  "category": "ganancia_muscular",
  "title": "Hipertrofia con hombro protegido",
  "case": "Mujer de 44 años con molestia de hombro en presses por encima de la cabeza; quiere ganar masa general evitando los gestos que la irritan.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Torso adaptado, pierna y torso complementario",
  "split_rationale": "Los empujes se hacen en máquina, polea y landmine, sin ejercicios con contraindicación de hombro; la pierna carga sin limitación.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Torso adaptado",
    "warmup": "Movilidad escapular y rotaciones suaves",
    "exercises": [
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Rango cómodo sin dolor"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho alto, codos atrás"
     },
     {
      "name": "Elevación lateral en polea unilateral",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Sube solo hasta la horizontal"
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Rotación externa al final"
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos pegados al cuerpo"
     }
    ],
    "cooldown": "Estiramiento suave de hombro"
   },
   {
    "day": "Miércoles",
    "name": "Pierna completa",
    "warmup": "Movilidad de cadera y aproximaciones",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Baja controlado, empuja fuerte"
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Cadera atrás, espalda neutra"
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Flexión completa sin rebote"
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Bloqueo total de cadera"
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Pausa arriba un segundo"
     }
    ],
    "cooldown": "Estiramientos de pierna 5 min"
   },
   {
    "day": "Viernes",
    "name": "Torso complementario",
    "warmup": "Movilidad escapular y rotaciones suaves",
    "exercises": [
     {
      "name": "Press landmine de pie",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Empuje en diagonal amable"
     },
     {
      "name": "Jalón agarre estrecho neutro",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Codos hacia las caderas"
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Junta escápulas al final"
     },
     {
      "name": "Contractora de pecho",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Abre solo hasta rango cómodo"
     },
     {
      "name": "Rotación externa de hombro en polea",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Codo pegado, giro lento"
     }
    ],
    "cooldown": "Estiramiento suave de hombro"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación sin irritar el hombro",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Series base"
   },
   {
    "week": 2,
    "intent": "Progresión en pierna y tracciones",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Misma estructura"
   },
   {
    "week": 3,
    "intent": "Carga donde no hay molestia",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Añade 1 serie a pierna y remos"
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 1
    }
   ]
  },
  "deload_instructions": "Semana 4: 90 por ciento y una serie menos; el trabajo de rotación externa se mantiene todas las semanas."
 },
 {
  "category": "ganancia_muscular",
  "title": "Turnos rotativos, sesiones intercambiables",
  "case": "Hombre de 33 años, enfermero con turnos rotativos imprevisibles, entrena en casa con kettlebell, mancuernas y bandas los dos días que consigue librar.",
  "level": "intermediate",
  "days_per_week": 2,
  "place": "home",
  "split_name": "Dos full body intercambiables",
  "split_rationale": "Dos sesiones completas y autónomas que puede colocar en cualquier hueco de la semana; ninguna depende de la otra ni de un orden fijo.",
  "sessions": [
   {
    "day": "Martes",
    "name": "Sesión A (colócala donde puedas)",
    "warmup": "Movilidad general y activación con banda",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Torso erguido, talones firmes"
     },
     {
      "name": "Flexiones",
      "sets": 4,
      "rep_range": "8-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cuerpo en línea, codos a 45"
     },
     {
      "name": "Remo invertido bajo una mesa",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho a la mesa, cuerpo recto"
     },
     {
      "name": "Swing con kettlebell",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Impulso de cadera, no de brazos"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Glúteo y abdomen firmes"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   },
   {
    "day": "Sábado",
    "name": "Sesión B (colócala donde puedas)",
    "warmup": "Movilidad general y activación con banda",
    "exercises": [
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Paso atrás largo y estable"
     },
     {
      "name": "Press de hombro unilateral con mancuerna de pie",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Core firme, sin arquear"
     },
     {
      "name": "Remo con banda sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Junta escápulas al final"
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadera atrás, espalda neutra"
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Camina recto sin inclinarte"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: dos sesiones donde encajen",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Series base"
   },
   {
    "week": 2,
    "intent": "Progresión por repeticiones o tempo",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Misma estructura"
   },
   {
    "week": 3,
    "intent": "Carga: semana más densa",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Añade 1 serie a los dos primeros ejercicios"
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 10000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 20,
     "times_per_week": 1,
     "notes": "Solo si el turno lo permite"
    }
   ]
  },
  "deload_instructions": "Semana 4: pesos ligeros y una serie menos; si una semana de turnos solo permite una sesión, haz la A y no la recuperes."
 },
 {
  "category": "ganancia_muscular",
  "title": "Hipertrofia exprés para universitario",
  "case": "Chico de 20 años, universitario con huecos de 45 minutos entre clases, entrena en el gimnasio del campus y quiere ganar masa sin sesiones largas.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body exprés de básicos",
  "split_rationale": "Sesiones de cuatro o cinco ejercicios centradas en multiarticulares; con 45 minutos el volumen va a lo esencial de cada patrón.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Exprés A",
    "warmup": "5 min de movilidad y aproximaciones rápidas",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Core firme antes de bajar"
     },
     {
      "name": "Press banca con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Escápulas retraídas"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho alto al tirar"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Cadera alineada"
     }
    ],
    "cooldown": "Estiramiento breve 3 min"
   },
   {
    "day": "Miércoles",
    "name": "Exprés B",
    "warmup": "5 min de movilidad y aproximaciones rápidas",
    "exercises": [
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Cadera atrás, barra pegada"
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Trayectoria vertical limpia"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Codos hacia abajo y atrás"
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Pausa arriba un segundo"
     }
    ],
    "cooldown": "Estiramiento breve 3 min"
   },
   {
    "day": "Viernes",
    "name": "Exprés C",
    "warmup": "5 min de movilidad y aproximaciones rápidas",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Sin bloquear rodillas arriba"
     },
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Baja hasta estirar el pectoral"
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tira con el codo al costado"
     },
     {
      "name": "Curl de bíceps con barra EZ",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos fijos al costado"
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Separa la cuerda al final"
     }
    ],
    "cooldown": "Estiramiento breve 3 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación con sesiones cortas",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Series base"
   },
   {
    "week": 2,
    "intent": "Progresión de carga en básicos",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Misma estructura"
   },
   {
    "week": 3,
    "intent": "Carga: semana pico",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Añade 1 serie al primer ejercicio si hay tiempo"
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 10000,
   "sessions": []
  },
  "deload_instructions": "Semana 4: 90 por ciento de carga y una serie menos por ejercicio; los desplazamientos por el campus ya cubren el cardio."
 },
 {
  "category": "ganancia_muscular",
  "title": "Músculo y corazón en equilibrio",
  "case": "Hombre de 45 años sedentario con analítica mejorable; su médico le recomienda fuerza y cardio, y él quiere ganar masa sin descuidar la salud cardiovascular.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body más cardio programado",
  "split_rationale": "Tres sesiones completas de fuerza y cardio en días o momentos separados: la masa muscular es prioridad y el cardio suma salud sin interferir.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Fuerza A",
    "warmup": "5 min de cardio suave y movilidad",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Torso erguido al bajar"
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Escápulas retraídas"
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Junta escápulas al final"
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Excéntrica controlada"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Abdomen firme, respira"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   },
   {
    "day": "Miércoles",
    "name": "Fuerza B",
    "warmup": "5 min de cardio suave y movilidad",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Empuja con todo el pie"
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Sin bloquear los codos"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Baja a la clavícula"
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Bloqueo de glúteo arriba"
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Lumbar pegada al suelo"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   },
   {
    "day": "Viernes",
    "name": "Fuerza C",
    "warmup": "5 min de cardio suave y movilidad",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Empuja el suelo, espalda neutra"
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Recorrido completo controlado"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho alto al tirar"
     },
     {
      "name": "Zancada inversa",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Paso atrás estable"
     },
     {
      "name": "Crunch en polea alta",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Flexiona desde las costillas"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación de fuerza y cardio a la vez",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Series base"
   },
   {
    "week": 2,
    "intent": "Progresión de carga en fuerza",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Misma estructura"
   },
   {
    "week": 3,
    "intent": "Carga: semana más exigente",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Añade 1 serie al primer ejercicio"
   },
   {
    "week": 4,
    "intent": "Descarga de fuerza, cardio suave se mantiene",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Bici o caminata rápida, días sin pesas"
    },
    {
     "type": "hiit",
     "minutes": 12,
     "times_per_week": 1,
     "notes": "Solo si la semana fue bien, nunca antes de pierna"
    }
   ]
  },
  "deload_instructions": "Semana 4: 90 por ciento en fuerza y una serie menos; mantén el cardio suave y elimina el HIIT esa semana."
 },
 {
  "category": "ganancia_muscular",
  "title": "Pierna primero, torso de apoyo",
  "case": "Hombre de 26 años, avanzado, con torso desarrollado y pierna claramente por detrás tras años de priorizar press; asume cuatro días con la pierna al frente.",
  "level": "advanced",
  "days_per_week": 4,
  "place": "gym",
  "split_name": "Doble pierna con dos días de torso",
  "split_rationale": "Dos sesiones de pierna separadas por dominante de rodilla y de cadera concentran el volumen donde falta; el torso mantiene con dos días compactos.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Pierna dominante de rodilla",
    "warmup": "Movilidad de cadera y tobillo, aproximaciones",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "1-2",
      "rest_sec": 180,
      "technique_cue": "Profundidad completa controlada"
     },
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Pies bajos para cuádriceps"
     },
     {
      "name": "Extensión de rodilla en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1",
      "rest_sec": 75,
      "technique_cue": "Pausa de un segundo arriba"
     },
     {
      "name": "Zancadas caminando con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Pasos largos y estables"
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "1",
      "rest_sec": 60,
      "technique_cue": "Estira abajo, pausa arriba"
     }
    ],
    "cooldown": "Estiramientos de pierna 5 min"
   },
   {
    "day": "Martes",
    "name": "Torso A",
    "warmup": "Movilidad de hombro y aproximaciones",
    "exercises": [
     {
      "name": "Press banca con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Escápulas retraídas, pies firmes"
     },
     {
      "name": "Remo con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Torso fijo, sin impulso"
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Sube sin chocar arriba"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Codos hacia abajo y atrás"
     }
    ],
    "cooldown": "Estiramiento suave de torso"
   },
   {
    "day": "Jueves",
    "name": "Pierna dominante de cadera",
    "warmup": "Activación de glúteo y aproximaciones",
    "exercises": [
     {
      "name": "Peso muerto convencional",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Barra pegada, empuja el suelo"
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Bloqueo total de cadera"
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1",
      "rest_sec": 90,
      "technique_cue": "Excéntrica de tres segundos"
     },
     {
      "name": "Hiperextensiones 45°",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Sube con glúteo, no con lumbar"
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo lento"
     }
    ],
    "cooldown": "Estiramientos de pierna 5 min"
   },
   {
    "day": "Sábado",
    "name": "Torso B",
    "warmup": "Movilidad de hombro y aproximaciones",
    "exercises": [
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Baja hasta estirar el pectoral"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pausa en la contracción"
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1",
      "rest_sec": 60,
      "technique_cue": "Sube con el codo"
     },
     {
      "name": "Curl martillo",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Sin balanceo del torso"
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Separa la cuerda al extender"
     }
    ],
    "cooldown": "Estiramiento suave de torso"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación al volumen alto de pierna",
    "load_pct": 100,
    "rir_target": "2",
    "volume_note": "Series base"
   },
   {
    "week": 2,
    "intent": "Progresión en sentadilla y peso muerto",
    "load_pct": 102.5,
    "rir_target": "1-2",
    "volume_note": "Misma estructura"
   },
   {
    "week": 3,
    "intent": "Carga: pico de estímulo de pierna",
    "load_pct": 105,
    "rir_target": "0-1",
    "volume_note": "Añade 1 serie a un ejercicio por sesión de pierna"
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Mitad de series en pierna, torso ligero"
   }
  ],
  "cardio": {
   "daily_steps": 7000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 20,
     "times_per_week": 1,
     "notes": "Recuperación activa"
    }
   ]
  },
  "deload_instructions": "Semana 4: mitad de series en pierna y 90 por ciento de carga; si la lumbar acumula fatiga del peso muerto, sustitúyelo esa semana por hip thrust ligero."
 },
 {
  "category": "perdida_grasa",
  "title": "Oficinista activo",
  "case": "Hombre de 38 años, trabajo de oficina con más de nueve horas sentado y abdomen prominente. Busca perder grasa y ganar energía sin experiencia previa en gimnasio.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body 3 días",
  "split_rationale": "Tres sesiones de cuerpo completo maximizan el gasto calórico y la frecuencia de estímulo en un principiante con poco tiempo.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Cuerpo completo A",
    "warmup": "5 min de bici suave y movilidad de cadera y hombro",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Baja controlado sin despegar la zona lumbar del respaldo"
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Escápulas atrás y abajo durante todo el recorrido"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Lleva los codos hacia atrás sin encoger los hombros"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Aprieta glúteo y abdomen para no arquear la lumbar"
     }
    ],
    "cooldown": "5 min de estiramientos de cadera y pectoral"
   },
   {
    "day": "Miércoles",
    "name": "Cuerpo completo B",
    "warmup": "5 min de cinta inclinada y movilidad articular",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Pecho alto y rodillas siguiendo la línea de los pies"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tira de los codos hacia el suelo, no de las manos"
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "No bloquees los codos arriba de forma brusca"
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Lumbar pegada al suelo mientras extiendes brazo y pierna"
     }
    ],
    "cooldown": "Estiramientos suaves de isquios y dorsal, 5 min"
   },
   {
    "day": "Viernes",
    "name": "Cuerpo completo C",
    "warmup": "5 min de remo suave y movilidad de cadera",
    "exercises": [
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Empuja la cadera atrás con la espalda neutra"
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pausa un segundo con el pecho abierto al final del tirón"
     },
     {
      "name": "Cruce de poleas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Junta las manos delante del esternón sin encorvarte"
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Resiste la rotación manteniendo la cadera quieta"
     }
    ],
    "cooldown": "5 min de estiramientos generales y respiración"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: aprender técnica y ritmo de trabajo",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Series indicadas, prioriza la ejecución"
   },
   {
    "week": 2,
    "intent": "Progresión: pequeño aumento de carga",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismo volumen, algo más de peso"
   },
   {
    "week": 3,
    "intent": "Carga: semana más exigente del bloque",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Puedes añadir 1 serie a los básicos si vas bien"
   },
   {
    "week": 4,
    "intent": "Descarga: recuperar para el siguiente bloque",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Reduce una serie por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Caminata rápida o bici suave tras entrenar o en días libres"
    }
   ]
  },
  "deload_instructions": "En la semana 4 baja las cargas al 90 por ciento y una serie por ejercicio, manteniendo la técnica."
 },
 {
  "category": "perdida_grasa",
  "title": "Posparto sin impacto",
  "case": "Mujer de 33 años, ocho meses posparto con suelo pélvico aún sensible. Quiere perder la grasa del embarazo entrenando en casa, sin impactos ni presión abdominal alta.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "home",
  "split_name": "Full body suave en casa",
  "split_rationale": "Cuerpo completo con cargas ligeras y core de baja presión intraabdominal, respetando el suelo pélvico y sin ningún impacto.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Sesión A",
    "warmup": "5 min de marcha en el sitio y respiración diafragmática",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Exhala al subir sin apnea ni empuje abdominal"
     },
     {
      "name": "Remo con banda sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Espalda larga y hombros lejos de las orejas"
     },
     {
      "name": "Puente de glúteo",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Sube activando glúteo, no la lumbar"
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Movimiento lento, lumbar siempre apoyada"
     }
    ],
    "cooldown": "Estiramientos suaves y respiración 5 min"
   },
   {
    "day": "Miércoles",
    "name": "Sesión B",
    "warmup": "5 min de movilidad de cadera y activación de glúteo",
    "exercises": [
     {
      "name": "Zancada estática",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Baja vertical, sin rebotar en el paso"
     },
     {
      "name": "Press de pecho con banda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Muñecas firmes y recorrido controlado"
     },
     {
      "name": "Abducción de cadera con banda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Abre contra la banda sin inclinar el tronco"
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Cadera nivelada al extender brazo y pierna contrarios"
     }
    ],
    "cooldown": "5 min de estiramientos de cadera y pecho"
   },
   {
    "day": "Viernes",
    "name": "Sesión C",
    "warmup": "5 min de marcha suave y círculos de brazos",
    "exercises": [
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Cadera atrás y mancuernas pegadas a las piernas"
     },
     {
      "name": "Jalón con banda de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Tira de los codos hacia las costillas"
     },
     {
      "name": "Elevaciones laterales con banda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Sube hasta la altura del hombro, sin balanceo"
     },
     {
      "name": "Plancha lateral",
      "sets": 2,
      "rep_range": "20-30s",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Cadera alta formando una línea recta, respira"
     }
    ],
    "cooldown": "Respiración y estiramientos suaves 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: reconectar con el ejercicio sin fatiga",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Volumen mínimo eficaz, sensaciones ante todo"
   },
   {
    "week": 2,
    "intent": "Progresión: una repetición más por serie",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Mismo volumen, sube repeticiones"
   },
   {
    "week": 3,
    "intent": "Carga: ligero aumento de banda o mancuerna",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Añade una serie al puente si todo va bien"
   },
   {
    "week": 4,
    "intent": "Descarga: consolidar y recuperar",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Reduce una serie por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 7000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 3,
     "notes": "Paseos con o sin carrito; nada de carrera ni saltos"
    }
   ]
  },
  "deload_instructions": "Semana 4 con bandas más suaves y una serie menos por ejercicio; si aparece molestia pélvica, detén el ejercicio y consúltalo."
 },
 {
  "category": "perdida_grasa",
  "title": "Gran pérdida bajo impacto",
  "case": "Hombre de 42 años con 118 kg y más de 20 kg que perder. Necesita empezar en gimnasio con ejercicios guiados y sin impacto en las articulaciones.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body en máquinas",
  "split_rationale": "Máquinas y apoyos estables protegen articulaciones con mucho peso corporal, permitiendo trabajar duro sin riesgo ni impacto.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Cuerpo completo A",
    "warmup": "5 min de bici estática suave y movilidad general",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Rango cómodo, sin que la cadera se despegue"
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Ajusta el asiento para empujar a la altura del pecho"
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tira con la espalda, no con los brazos"
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Zona lumbar pegada al suelo en todo momento"
     }
    ],
    "cooldown": "5 min de bici muy suave y estiramientos"
   },
   {
    "day": "Miércoles",
    "name": "Cuerpo completo B",
    "warmup": "5 min de elíptica suave y movilidad de cadera",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Siéntate atrás y abajo con el pecho alto"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Barra hacia la clavícula con torso casi vertical"
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Empuja sin arquear la espalda baja"
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Extiende los brazos sin dejar que el tronco gire"
     }
    ],
    "cooldown": "Estiramientos de piernas y espalda 5 min"
   },
   {
    "day": "Viernes",
    "name": "Cuerpo completo C",
    "warmup": "5 min de cinta llana y círculos articulares",
    "exercises": [
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Empuja con la pierna del cajón, sin impulso"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Pecho abierto al final de cada tirón"
     },
     {
      "name": "Contractora de pecho",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Junta los brazos con codos ligeramente flexionados"
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Camina erguido sin inclinarte hacia la carga"
     }
    ],
    "cooldown": "5 min de estiramientos y respiración"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: técnica y confianza con las máquinas",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "No busques el fallo en ninguna serie"
   },
   {
    "week": 2,
    "intent": "Progresión: sube una placa donde salga fácil",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Mismo volumen total"
   },
   {
    "week": 3,
    "intent": "Carga: semana más dura del mes",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Añade una serie a prensa y remo si respondes bien"
   },
   {
    "week": 4,
    "intent": "Descarga: aliviar articulaciones",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 3,
     "notes": "Bici estática o elíptica; evita correr por el impacto"
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90 por ciento con una serie menos por ejercicio; mantén los pasos diarios."
 },
 {
  "category": "perdida_grasa",
  "title": "Recomposición torso-pierna",
  "case": "Hombre de 28 años con dos años de experiencia, quiere perder grasa abdominal mientras gana algo de músculo. Entrena cuatro días con buena disponibilidad.",
  "level": "intermediate",
  "days_per_week": 4,
  "place": "gym",
  "split_name": "Torso-pierna 4 días",
  "split_rationale": "Frecuencia 2 por grupo con volumen moderado: ideal para recomponer, sosteniendo la fuerza en déficit.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Torso A",
    "warmup": "5 min de remo y movilidad de hombro con banda",
    "exercises": [
     {
      "name": "Press banca con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Pies firmes y escápulas retraídas en el banco"
     },
     {
      "name": "Remo con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Torso fijo, tira hacia el abdomen bajo"
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Baja hasta la altura de las orejas con control"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Evita balancear el torso para completar la repetición"
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos pegados al cuerpo, separa la cuerda abajo"
     }
    ],
    "cooldown": "Estiramientos de pectoral y dorsal 5 min"
   },
   {
    "day": "Martes",
    "name": "Pierna A",
    "warmup": "5 min de bici y movilidad de tobillo y cadera",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Rompe la cadera y rodilla a la vez, torso firme"
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Barra rozando las piernas, espalda neutra"
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Pausa arriba un segundo en cada repetición"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Pelvis en retroversión ligera, sin hundir la cadera"
     }
    ],
    "cooldown": "5 min de estiramientos de isquios y cuádriceps"
   },
   {
    "day": "Jueves",
    "name": "Torso B",
    "warmup": "5 min de cardio suave y band pull-apart ligeros",
    "exercises": [
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Codos a unos 45 grados del torso"
     },
     {
      "name": "Jalón agarre estrecho neutro",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Lleva el pecho hacia la barra al tirar"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "No uses impulso lumbar para mover más peso"
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos ligeramente flexionados, sube sin encoger"
     },
     {
      "name": "Curl alterno con mancuernas",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codo fijo al costado durante todo el curl"
     }
    ],
    "cooldown": "Estiramientos de brazos y hombros 5 min"
   },
   {
    "day": "Viernes",
    "name": "Pierna B",
    "warmup": "5 min de bici y activación de glúteo con banda",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Baja hasta donde la lumbar siga apoyada"
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Cadera pegada al banco, sube sin latigazo"
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Bloquea arriba con glúteo, mirada al frente"
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo, estira abajo del todo"
     },
     {
      "name": "Crunch en polea alta",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Flexiona la columna, no tires con los brazos"
     }
    ],
    "cooldown": "5 min de estiramientos generales"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: fijar cargas de referencia",
    "load_pct": 100,
    "rir_target": "2",
    "volume_note": "Volumen base del bloque"
   },
   {
    "week": 2,
    "intent": "Progresión: más peso en los básicos",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismo volumen, cargas algo mayores"
   },
   {
    "week": 3,
    "intent": "Carga: pico de esfuerzo del mes",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Añade una serie a press banca y sentadilla"
   },
   {
    "week": 4,
    "intent": "Descarga: disipar fatiga en pleno déficit",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Reduce una serie por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 2,
     "notes": "Cardio suave separado de las piernas para no interferir"
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90 por ciento y una serie menos por ejercicio; mantén pasos y técnica intactos."
 },
 {
  "category": "perdida_grasa",
  "title": "Definición de verano",
  "case": "Mujer de 26 años, intermedia, quiere llegar definida al verano tras una buena etapa de volumen. Dispone de cuatro días y buen gimnasio.",
  "level": "intermediate",
  "days_per_week": 4,
  "place": "gym",
  "split_name": "Superior-inferior 4 días",
  "split_rationale": "Reparto superior-inferior con frecuencia 2 que mantiene la masa muscular mientras el déficit hace su trabajo.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Superior A",
    "warmup": "5 min de cardio suave y movilidad de hombro",
    "exercises": [
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Baja las mancuernas a la línea del pecho"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Codos hacia abajo y pecho alto al tirar"
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Sube hasta la horizontal sin balanceo"
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Extiende del todo y controla la vuelta"
     },
     {
      "name": "Crunch en polea alta",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Redondea la espalda llevando codos a rodillas"
     }
    ],
    "cooldown": "Estiramientos de torso 5 min"
   },
   {
    "day": "Martes",
    "name": "Inferior A",
    "warmup": "5 min de bici y activación de glúteo",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Profundidad hasta paralelo con talones firmes"
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Estira los isquios empujando la cadera atrás"
     },
     {
      "name": "Abducción de cadera en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Abre con pausa arriba, sin inercia"
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Sube alto y pausa un segundo arriba"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cuerpo en línea, glúteo apretado"
     }
    ],
    "cooldown": "5 min de estiramientos de piernas"
   },
   {
    "day": "Jueves",
    "name": "Superior B",
    "warmup": "5 min de remo y rotaciones de hombro con banda",
    "exercises": [
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Espalda apoyada, empuja sin arquear"
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tira del codo hacia la cadera sin rotar el torso"
     },
     {
      "name": "Cruce de poleas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Aprieta el pecho al juntar las manos"
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Tira de la cuerda hacia la cara separando las manos"
     },
     {
      "name": "Curl alterno con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Gira la muñeca al subir sin mover el codo"
     }
    ],
    "cooldown": "Estiramientos de hombro y antebrazo 5 min"
   },
   {
    "day": "Viernes",
    "name": "Inferior B",
    "warmup": "5 min de bici y movilidad de cadera",
    "exercises": [
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Barbilla recogida y bloqueo total de cadera arriba"
     },
     {
      "name": "Sentadilla búlgara",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Torso ligeramente inclinado, baja vertical"
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Flexiona fuerte y controla tres segundos la vuelta"
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Rango completo sin rebotar abajo"
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Abdomen firme, resiste el giro de la polea"
     }
    ],
    "cooldown": "5 min de estiramientos generales"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: entrar en el bloque con margen",
    "load_pct": 100,
    "rir_target": "2",
    "volume_note": "Volumen base, técnica impecable"
   },
   {
    "week": 2,
    "intent": "Progresión: subir cargas manteniendo reps",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismo volumen semanal"
   },
   {
    "week": 3,
    "intent": "Carga: semana pico antes de descargar",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Una serie extra en sentadilla y hip thrust"
   },
   {
    "week": 4,
    "intent": "Descarga: proteger el rendimiento en déficit",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 10000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Cinta inclinada o elíptica en días de superior"
    },
    {
     "type": "hiit",
     "minutes": 15,
     "times_per_week": 1,
     "notes": "Bici o elíptica, lejos del día de pierna"
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90 por ciento con una serie menos por ejercicio; mantén pasos y el HIIT se sustituye por LISS suave."
 },
 {
  "category": "perdida_grasa",
  "title": "Dos días eficaces",
  "case": "Hombre de 40 años, consultor con agenda imprevisible: solo puede asegurar dos entrenamientos semanales. Busca perder grasa con el máximo rendimiento por sesión.",
  "level": "intermediate",
  "days_per_week": 2,
  "place": "gym",
  "split_name": "Full body 2 días",
  "split_rationale": "Dos sesiones completas con básicos multiarticulares cubren todo el cuerpo dos veces por semana, el mínimo eficaz para retener músculo.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Cuerpo completo A",
    "warmup": "5 min de cardio suave y movilidad general",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Codos por dentro de las rodillas al bajar"
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Trayectoria en ligero arco hacia la vertical"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tira hacia el ombligo con el pecho abierto"
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Siente la tensión en isquios antes de subir"
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Muñecas neutras, sube sin impulso"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Empuja el suelo separando las escápulas"
     }
    ],
    "cooldown": "Estiramientos generales 5 min"
   },
   {
    "day": "Jueves",
    "name": "Cuerpo completo B",
    "warmup": "5 min de remo suave y movilidad de cadera",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Empuja con toda la planta del pie"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Baja la barra a la clavícula sin echarte atrás"
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Empuje vertical sin despegar la lumbar"
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Sube el talón al glúteo con control total"
     },
     {
      "name": "Cruce de poleas",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos semiflexionados fijos durante el cruce"
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Extiende despacio y aguanta dos segundos"
     }
    ],
    "cooldown": "5 min de estiramientos y respiración"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: fijar cargas cómodas",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Seis ejercicios por sesión, sin fallo"
   },
   {
    "week": 2,
    "intent": "Progresión: subir peso donde sobren reps",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismo esquema de series"
   },
   {
    "week": 3,
    "intent": "Carga: la semana más exigente",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Una serie extra en sentadilla y prensa"
   },
   {
    "week": 4,
    "intent": "Descarga: recuperación activa",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 10000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 40,
     "times_per_week": 2,
     "notes": "Caminatas largas el fin de semana para compensar los pocos días de pesas"
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90 por ciento con una serie menos; los pasos diarios no se negocian."
 },
 {
  "category": "perdida_grasa",
  "title": "Casa sin material",
  "case": "Mujer de 29 años que trabaja desde casa y no tiene ningún equipamiento. Quiere perder grasa entrenando solo con su peso corporal en el salón.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "home",
  "split_name": "Full body con peso corporal",
  "split_rationale": "Tres sesiones de cuerpo completo con autocargas progresivas: sin material, la densidad y las variantes unilaterales marcan la intensidad.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Sesión A",
    "warmup": "5 min de marcha en el sitio y movilidad articular",
    "exercises": [
     {
      "name": "Zancadas caminando sin carga",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Pasos largos y rodilla trasera cerca del suelo"
     },
     {
      "name": "Flexiones",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cuerpo en tabla, apóyate en rodillas si hace falta"
     },
     {
      "name": "Remo invertido bajo una mesa",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho a la mesa con el cuerpo rígido"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "No dejes caer la cadera al fatigarte"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   },
   {
    "day": "Miércoles",
    "name": "Sesión B",
    "warmup": "5 min de movilidad dinámica y sentadillas al aire",
    "exercises": [
     {
      "name": "Sentadilla búlgara con peso corporal",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Usa una silla estable, baja vertical"
     },
     {
      "name": "Flexiones pike",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadera alta, la cabeza baja entre las manos"
     },
     {
      "name": "Puente de glúteo a una pierna",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cadera nivelada, empuja con el talón"
     },
     {
      "name": "Marcha del oso",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Rodillas a un palmo del suelo, espalda plana"
     }
    ],
    "cooldown": "5 min de estiramientos de piernas y hombros"
   },
   {
    "day": "Viernes",
    "name": "Sesión C",
    "warmup": "5 min de marcha y círculos de cadera",
    "exercises": [
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Paso atrás controlado, empuja con la pierna delantera"
     },
     {
      "name": "Remo invertido bajo una mesa",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tira con la espalda, no con las manos"
     },
     {
      "name": "Curl femoral con toalla deslizante",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadera extendida mientras deslizas los talones"
     },
     {
      "name": "Plancha lateral",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codo bajo el hombro y cadera arriba"
     }
    ],
    "cooldown": "Estiramientos generales 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: dominar cada patrón",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Aprende las variantes con calma"
   },
   {
    "week": 2,
    "intent": "Progresión: más repeticiones por serie",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Suma 1-2 reps donde puedas"
   },
   {
    "week": 3,
    "intent": "Carga: ritmos más lentos y pausas",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Añade una serie a zancadas y flexiones"
   },
   {
    "week": 4,
    "intent": "Descarga: semana suave",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Caminata rápida al aire libre"
    },
    {
     "type": "hiit",
     "minutes": 12,
     "times_per_week": 1,
     "notes": "Intervalos de escaladores y marcha rápida, sin saltos si molestan"
    }
   ]
  },
  "deload_instructions": "En la semana 4 haz una serie menos por ejercicio y versiones más fáciles (flexiones con rodillas, plancha más corta)."
 },
 {
  "category": "perdida_grasa",
  "title": "Mancuernas en el salón",
  "case": "Hombre de 31 años con un par de mancuernas ajustables en casa y horario partido. Quiere perder la grasa acumulada sin pisar el gimnasio.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "home",
  "split_name": "Full body con mancuernas",
  "split_rationale": "Con solo mancuernas, tres sesiones de cuerpo completo con unilaterales y bisagras cubren todos los patrones y sostienen el músculo en déficit.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Sesión A",
    "warmup": "5 min de comba imaginaria y movilidad de hombro",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Mancuerna pegada al pecho, talones firmes"
     },
     {
      "name": "Flexiones",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Codos a 45 grados del torso"
     },
     {
      "name": "Remo invertido bajo una mesa",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Aprieta las escápulas al final del tirón"
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Hombros nivelados, no te inclines a un lado"
     }
    ],
    "cooldown": "Estiramientos generales 5 min"
   },
   {
    "day": "Miércoles",
    "name": "Sesión B",
    "warmup": "5 min de movilidad dinámica de cadera",
    "exercises": [
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Espalda neutra y mancuernas rozando los muslos"
     },
     {
      "name": "Press de hombro unilateral con mancuerna de pie",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Glúteo y abdomen firmes para no arquear"
     },
     {
      "name": "Zancadas caminando con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Torso erguido y pasos estables"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Línea recta de tobillos a cabeza"
     }
    ],
    "cooldown": "5 min de estiramientos de isquios y hombros"
   },
   {
    "day": "Viernes",
    "name": "Sesión C",
    "warmup": "5 min de marcha rápida y círculos articulares",
    "exercises": [
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Rodilla delantera estable sobre el pie"
     },
     {
      "name": "Remo invertido bajo una mesa",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Sube el pecho sin flexionar la cadera"
     },
     {
      "name": "Curl martillo",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Agarre neutro y codos quietos"
     },
     {
      "name": "Extensión de tríceps sobre la cabeza con mancuerna",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos apuntando al techo, baja controlado"
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Movimiento lento con la lumbar apoyada"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: ajustar el peso de las mancuernas",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Encuentra cargas que respeten el RIR"
   },
   {
    "week": 2,
    "intent": "Progresión: subir discos o repeticiones",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismo volumen semanal"
   },
   {
    "week": 3,
    "intent": "Carga: tempo lento si el peso se queda corto",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Serie extra en goblet y peso muerto rumano"
   },
   {
    "week": 4,
    "intent": "Descarga: aliviar antes del nuevo bloque",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 10000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 3,
     "notes": "Caminata rápida diaria o bici si dispone de ella"
    }
   ]
  },
  "deload_instructions": "Semana 4 con mancuernas más ligeras (90 por ciento) y una serie menos por ejercicio."
 },
 {
  "category": "perdida_grasa",
  "title": "Fuerza serena 55+",
  "case": "Mujer de 58 años con sobrepeso y algo de rigidez articular, sin experiencia reciente. Busca perder grasa y ganar autonomía con un trabajo seguro en gimnasio.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body guiado 3 días",
  "split_rationale": "Cuerpo completo en máquinas y autocargas sencillas: máxima seguridad articular, aprendizaje progresivo y estímulo suficiente para conservar músculo y hueso.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Sesión A",
    "warmup": "6 min de bici suave y movilidad de hombro y cadera",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Empuja sin bloquear las rodillas de golpe"
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Movimiento fluido, sin rebotes en el pecho"
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Hombros abajo mientras tiras hacia atrás"
     },
     {
      "name": "Bird dog",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Alarga brazo y pierna sin girar la cadera"
     }
    ],
    "cooldown": "Estiramientos suaves y respiración 5 min"
   },
   {
    "day": "Miércoles",
    "name": "Sesión B",
    "warmup": "6 min de cinta llana y movilidad general",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Baja a una profundidad cómoda y estable"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tira suave hasta la parte alta del pecho"
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Empuja hasta casi extender, sin forzar arriba"
     },
     {
      "name": "Puente de glúteos",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Aprieta el glúteo dos segundos arriba"
     }
    ],
    "cooldown": "5 min de estiramientos de piernas"
   },
   {
    "day": "Viernes",
    "name": "Sesión C",
    "warmup": "6 min de elíptica suave y círculos articulares",
    "exercises": [
     {
      "name": "Subida a cajón",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Cajón bajo, sube sin impulsarte con la otra pierna"
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Flexiona con control, sin tirones"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Torso estable, tira hacia el abdomen"
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Sube y baja lento en todo el rango"
     },
     {
      "name": "Dead bug",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Exhala al extender la pierna"
     }
    ],
    "cooldown": "Estiramientos y respiración 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: familiarizarse con máquinas y patrones",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Trabajo lejos del fallo, técnica primero"
   },
   {
    "week": 2,
    "intent": "Progresión: una placa o dos repeticiones más",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Mismo esquema de series"
   },
   {
    "week": 3,
    "intent": "Carga: semana de mayor esfuerzo controlado",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Añade una serie a prensa y jalón si va bien"
   },
   {
    "week": 4,
    "intent": "Descarga: dejar descansar las articulaciones",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 7000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 3,
     "notes": "Caminata o bici suave; ritmo que permita hablar"
    }
   ]
  },
  "deload_instructions": "Semana 4 con cargas al 90 por ciento y una serie menos; si alguna articulación molesta, cambia a la variante en máquina más cómoda."
 },
 {
  "category": "perdida_grasa",
  "title": "Definir sin perder fuerza",
  "case": "Hombre de 33 años, avanzado, con buenos básicos y miedo a perder músculo al definir. Cuatro días de gimnasio y prioridad absoluta a mantener sus marcas.",
  "level": "advanced",
  "days_per_week": 4,
  "place": "gym",
  "split_name": "Fuerza + hipertrofia 4 días",
  "split_rationale": "Dos días de fuerza pesada conservan las adaptaciones neurales y dos de hipertrofia sostienen el volumen: la receta para no perder músculo en déficit.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Fuerza inferior",
    "warmup": "8 min de bici y aproximaciones progresivas de sentadilla",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 210,
      "technique_cue": "Bracea fuerte el core antes de cada repetición"
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Dorsales activos para mantener la barra pegada"
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Pausa arriba, estiramiento completo abajo"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Tensión total de glúteo y abdomen"
     }
    ],
    "cooldown": "Estiramientos de cadera 5 min"
   },
   {
    "day": "Martes",
    "name": "Fuerza superior",
    "warmup": "5 min de remo y series de aproximación en press",
    "exercises": [
     {
      "name": "Press banca con barra",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "2",
      "rest_sec": 210,
      "technique_cue": "Baja a la base del esternón con codos a 45 grados"
     },
     {
      "name": "Remo con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Tronco fijo a 45 grados, sin dar tirones"
     },
     {
      "name": "Dominadas neutras",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Sube el pecho a la barra, baja completo"
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos altos y rotación externa final"
     }
    ],
    "cooldown": "Estiramientos de pectoral y dorsal 5 min"
   },
   {
    "day": "Jueves",
    "name": "Hipertrofia inferior",
    "warmup": "5 min de bici y activación de glúteo e isquios",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Empuja el suelo con las piernas, torso firme"
     },
     {
      "name": "Sentadilla búlgara",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Baja profundo con la rodilla alineada"
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Evita levantar la cadera al flexionar"
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Trabajo lento y rango completo"
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Costillas abajo, resiste la rotación"
     }
    ],
    "cooldown": "5 min de estiramientos de piernas"
   },
   {
    "day": "Viernes",
    "name": "Hipertrofia superior",
    "warmup": "5 min de cardio suave y movilidad de hombro",
    "exercises": [
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Recorrido amplio sin chocar las mancuernas"
     },
     {
      "name": "Jalón agarre estrecho neutro",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Codos por delante, tira hasta la clavícula"
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1",
      "rest_sec": 60,
      "technique_cue": "Sube en arco amplio sin encoger trapecios"
     },
     {
      "name": "Curl de bíceps con barra EZ",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Codos fijos por delante de las costillas"
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Separa la cuerda al extender del todo"
     }
    ],
    "cooldown": "Estiramientos de brazos 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: cargas de entrada al 100 por cien del plan",
    "load_pct": 100,
    "rir_target": "2",
    "volume_note": "Registra todas las series pesadas"
   },
   {
    "week": 2,
    "intent": "Progresión: subir 2,5 por ciento en los básicos",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Volumen estable"
   },
   {
    "week": 3,
    "intent": "Carga: pico de intensidad del bloque",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Mantén series; el déficit ya suma fatiga"
   },
   {
    "week": 4,
    "intent": "Descarga: proteger las marcas de fuerza",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Una serie menos en todo"
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 2,
     "notes": "Solo LISS suave para no interferir con la fuerza"
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90 por ciento y una serie menos por ejercicio; si una marca cae dos semanas seguidas, revisa sueño y descanso antes de tocar el plan."
 },
 {
  "category": "perdida_grasa",
  "title": "Turno de noche",
  "case": "Hombre de 36 años, enfermero con turnos rotativos de noche y sueño irregular. Quiere perder grasa con sesiones que pueda mover de día según el turno.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body flexible 3 días",
  "split_rationale": "Sesiones completas e intercambiables: si un turno rompe la semana, ningún grupo muscular queda sin estímulo y el volumen se conserva.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Cuerpo completo A",
    "warmup": "5 min de bici suave y movilidad general",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Baja controlado sin despegar la cadera"
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Antebrazos verticales bajo las mancuernas"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tira hacia el abdomen sin balancear el torso"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Respira sin perder la tensión abdominal"
     }
    ],
    "cooldown": "Estiramientos generales 5 min"
   },
   {
    "day": "Miércoles",
    "name": "Cuerpo completo B",
    "warmup": "5 min de cinta y movilidad de cadera",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Peso repartido en toda la planta del pie"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Controla la subida de la barra, no la sueltes"
     },
     {
      "name": "Press landmine de pie",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Empuja en diagonal con el core firme"
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Ritmo lento y lumbar apoyada"
     }
    ],
    "cooldown": "5 min de estiramientos y respiración"
   },
   {
    "day": "Viernes",
    "name": "Cuerpo completo C",
    "warmup": "5 min de remo suave y movilidad de hombro",
    "exercises": [
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Bisagra de cadera pura, rodillas semiflexionadas"
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Aprieta las escápulas un segundo atrás"
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Empuja simétrico con ambos brazos"
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cadera y hombros encarados al frente"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: encajar el entreno en los turnos",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Si duermes mal, mantén cargas y recorta una serie"
   },
   {
    "week": 2,
    "intent": "Progresión: subir carga en días de buen descanso",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Volumen estable"
   },
   {
    "week": 3,
    "intent": "Carga: semana exigente solo si el sueño acompaña",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Serie extra opcional en prensa y remo"
   },
   {
    "week": 4,
    "intent": "Descarga: coincide con la peor semana de turnos",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 20,
     "times_per_week": 3,
     "notes": "Caminata al salir del turno para regular el ritmo circadiano"
    }
   ]
  },
  "deload_instructions": "Haz la descarga la semana de noches: 90 por ciento de carga, una serie menos y prioridad total al sueño."
 },
 {
  "category": "perdida_grasa",
  "title": "Rutina de hotel",
  "case": "Hombre de 45 años, comercial que viaja de lunes a jueves y entrena en habitaciones y gimnasios mínimos de hotel. Solo cuenta con bandas y su peso corporal.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "home",
  "split_name": "Full body portátil",
  "split_rationale": "Tres sesiones con bandas y peso corporal que caben en cualquier habitación: material de un solo bulto y estímulo completo semanal.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Sesión A",
    "warmup": "5 min de marcha rápida y movilidad articular",
    "exercises": [
     {
      "name": "Zancadas caminando sin carga",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Pasos controlados a lo largo de la habitación"
     },
     {
      "name": "Flexiones",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Abdomen firme para no arquear la lumbar"
     },
     {
      "name": "Remo con banda sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Ancla la banda en los pies y tira al abdomen"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Aprieta glúteos para mantener la línea"
     }
    ],
    "cooldown": "Estiramientos generales 5 min"
   },
   {
    "day": "Miércoles",
    "name": "Sesión B",
    "warmup": "5 min de movilidad dinámica y sentadillas al aire",
    "exercises": [
     {
      "name": "Sentadilla búlgara con peso corporal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pie trasero sobre la cama o una silla firme"
     },
     {
      "name": "Press de hombro con banda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Pisa la banda y empuja vertical sin arquear"
     },
     {
      "name": "Jalón con banda de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Ancla alto y tira de los codos a las costillas"
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Extiende despacio manteniendo la lumbar pegada"
     }
    ],
    "cooldown": "5 min de estiramientos de cadera"
   },
   {
    "day": "Viernes",
    "name": "Sesión C",
    "warmup": "5 min de marcha y círculos de brazos",
    "exercises": [
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Baja la rodilla trasera cerca del suelo"
     },
     {
      "name": "Press de pecho con banda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Banda a la espalda, empuja al frente controlado"
     },
     {
      "name": "Band pull-apart",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Abre la banda hasta tocar el pecho"
     },
     {
      "name": "Puente de glúteo a una pierna",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Sube sin que la cadera se incline"
     },
     {
      "name": "Plancha lateral",
      "sets": 2,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cuerpo alineado, no dejes caer la cadera"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: establecer la rutina viajera",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Elige la banda que respete el RIR"
   },
   {
    "week": 2,
    "intent": "Progresión: banda más dura o más repeticiones",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismo volumen semanal"
   },
   {
    "week": 3,
    "intent": "Carga: tempos lentos y pausas de un segundo",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Serie extra en zancadas y remo"
   },
   {
    "week": 4,
    "intent": "Descarga: semana de viajes más pesada",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 10000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 3,
     "notes": "Cinta del hotel o caminar a las reuniones"
    }
   ]
  },
  "deload_instructions": "Semana 4 con bandas más suaves y una serie menos; conserva los pasos aunque cambie la ciudad."
 },
 {
  "category": "perdida_grasa",
  "title": "Rodilla protegida",
  "case": "Mujer de 40 años con condropatía leve: la rodilla se resiente con sentadillas profundas e impactos. Quiere perder grasa entrenando fuerte sin provocar dolor.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body sin estrés de rodilla",
  "split_rationale": "Se sustituyen los dominantes de rodilla agresivos por cajón, prensa horizontal y bisagras de cadera: estímulo completo sin comprometer la articulación.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Sesión A",
    "warmup": "8 min de bici suave y movilidad de tobillo y cadera",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Rango sin dolor, no busques la flexión máxima"
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Empuja con las escápulas fijas al respaldo"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho abierto al final del tirón"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cadera en línea, sin hundirla"
     }
    ],
    "cooldown": "Estiramientos suaves de cuádriceps sin dolor 5 min"
   },
   {
    "day": "Miércoles",
    "name": "Sesión B",
    "warmup": "8 min de elíptica y activación de glúteo",
    "exercises": [
     {
      "name": "Sentadilla a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Siéntate atrás al cajón alto, tibias casi verticales"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tira de los codos hacia abajo y atrás"
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Empuje vertical sin arquear la lumbar"
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Control total, lumbar pegada al suelo"
     }
    ],
    "cooldown": "5 min de estiramientos y bici muy suave"
   },
   {
    "day": "Viernes",
    "name": "Sesión C",
    "warmup": "8 min de bici suave y bisagras de cadera sin carga",
    "exercises": [
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Flexión completa sin despegar la cadera"
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Bloqueo de cadera arriba con el glúteo"
     },
     {
      "name": "Press landmine de pie",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Empuja en diagonal sin ceder el core"
     },
     {
      "name": "Jalón agarre estrecho neutro",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Codos pegados, lleva el pecho a la barra"
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Resiste el giro con la pelvis neutra"
     }
    ],
    "cooldown": "Estiramientos generales 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: confirmar rangos sin molestia",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Cualquier dolor de rodilla manda parar el ejercicio"
   },
   {
    "week": 2,
    "intent": "Progresión: subir carga en rangos tolerados",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismo volumen"
   },
   {
    "week": 3,
    "intent": "Carga: semana fuerte respetando la rodilla",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Serie extra en prensa y curl femoral"
   },
   {
    "week": 4,
    "intent": "Descarga: aliviar tejidos",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 3,
     "notes": "Bici o elíptica; nada de correr ni saltar"
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90 por ciento con una serie menos; si la rodilla se inflama, sustituye la prensa por bisagras y avisa al coach."
 },
 {
  "category": "perdida_grasa",
  "title": "Espalda baja a salvo",
  "case": "Hombre de 48 años con episodios de lumbalgia mecánica ya sin dolor agudo. Quiere perder barriga entrenando sin cargar la columna en flexión ni compresión alta.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body lumbar-friendly",
  "split_rationale": "Se eliminan bisagras con barra, remos inclinados y flexiones lumbares: piernas con apoyo, tirones sentados y core antiextensión protegen la zona baja.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Sesión A",
    "warmup": "6 min de bici suave y gato-camello sin dolor",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Rango corto: la pelvis nunca se despega"
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Espalda completamente apoyada al empujar"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Torso vertical estable, tira sin balanceo"
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Presiona la lumbar contra el suelo siempre"
     }
    ],
    "cooldown": "Caminar 3 min y estiramientos suaves de cadera"
   },
   {
    "day": "Miércoles",
    "name": "Sesión B",
    "warmup": "6 min de cinta y activación de glúteo con banda",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Carga frontal ligera y torso lo más vertical posible"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tira sin arquear la zona baja"
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Costillas abajo, sin extender la lumbar"
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Columna neutra, movimiento lento y simétrico"
     }
    ],
    "cooldown": "5 min de estiramientos suaves"
   },
   {
    "day": "Viernes",
    "name": "Sesión C",
    "warmup": "6 min de elíptica y puentes de glúteo sin carga",
    "exercises": [
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Trabaja el isquio sin implicar la espalda"
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Extiende la cadera sin hiperextender la lumbar"
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho apoyado en el soporte todo el tiempo"
     },
     {
      "name": "Contractora de pecho",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Cierra los brazos con control y pausa"
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Resiste la rotación sin mover la pelvis"
     }
    ],
    "cooldown": "Caminar suave 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: construir confianza sin dolor",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Ninguna serie debe reproducir síntomas"
   },
   {
    "week": 2,
    "intent": "Progresión: cargas ligeramente mayores",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Mismo volumen"
   },
   {
    "week": 3,
    "intent": "Carga: semana más dura del bloque",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Serie extra en prensa e hip thrust si no hay molestias"
   },
   {
    "week": 4,
    "intent": "Descarga: descanso activo de la zona",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 3,
     "notes": "Caminar llano o bici reclinada; evita remo ergómetro"
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90 por ciento y una serie menos; ante cualquier irradiación o dolor agudo, se detiene el plan y se consulta."
 },
 {
  "category": "perdida_grasa",
  "title": "NEAT alto, cardio mínimo",
  "case": "Mujer de 30 años a la que las sesiones de cardio le generan rechazo y ansiedad. Quiere perder grasa a base de pesas y mucho movimiento diario.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body + NEAT",
  "split_rationale": "El gasto se construye con pasos y actividad diaria en lugar de cardio formal; tres días de fuerza completa protegen el músculo.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Cuerpo completo A",
    "warmup": "5 min de caminata rápida y movilidad general",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Baja entre las caderas con el torso alto"
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Controla la bajada dos segundos"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Escápulas atrás antes de tirar con los brazos"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Mantén la respiración fluida bajo tensión"
     }
    ],
    "cooldown": "Estiramientos generales 5 min"
   },
   {
    "day": "Miércoles",
    "name": "Cuerpo completo B",
    "warmup": "5 min de movilidad dinámica y activación de glúteo",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Sube empujando el suelo, no tirando con la espalda"
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Empuja sin encoger los hombros"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pausa un segundo con la barra en el pecho"
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Extiende sin que la lumbar se despegue"
     }
    ],
    "cooldown": "5 min de estiramientos de cadera"
   },
   {
    "day": "Viernes",
    "name": "Cuerpo completo C",
    "warmup": "5 min de caminata en cinta y círculos articulares",
    "exercises": [
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Empuja fuerte con la pierna adelantada al subir"
     },
     {
      "name": "Cruce de poleas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Abre controlado sintiendo el estiramiento"
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Espalda plana apoyada en el banco"
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Hombros y cadera cuadrados al frente"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: asentar el hábito de pasos y pesas",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Prioriza cumplir los pasos diarios"
   },
   {
    "week": 2,
    "intent": "Progresión: más carga en los básicos",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Volumen estable"
   },
   {
    "week": 3,
    "intent": "Carga: semana exigente de fuerza",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Serie extra en sentadilla y peso muerto"
   },
   {
    "week": 4,
    "intent": "Descarga: aflojar sin bajar los pasos",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 13000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 15,
     "times_per_week": 1,
     "notes": "Paseo suave opcional escuchando música; sin pulsómetro ni presión"
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90 por ciento y una serie menos; los 13.000 pasos se mantienen porque son el motor del déficit."
 },
 {
  "category": "perdida_grasa",
  "title": "Corazón de fondista",
  "case": "Hombre de 27 años, aficionado al cardio de toda la vida, que quiere perder grasa sin renunciar a sus sesiones largas. Necesita fuerza para no perder músculo.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Fuerza 3 días + LISS abundante",
  "split_rationale": "Tres días de fuerza con básicos sostienen la masa muscular mientras el LISS, que es lo que disfruta, genera la mayor parte del gasto.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Cuerpo completo A",
    "warmup": "5 min de trote suave y movilidad de cadera",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Baja con control y sube con intención de velocidad"
     },
     {
      "name": "Press banca con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Pausa breve en el pecho sin rebotar"
     },
     {
      "name": "Remo con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Core firme, tira hacia el abdomen"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Glúteo apretado y cuerpo en línea"
     }
    ],
    "cooldown": "5 min de bici suave"
   },
   {
    "day": "Miércoles",
    "name": "Cuerpo completo B",
    "warmup": "5 min de remo ergómetro suave",
    "exercises": [
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "La barra viaja pegada a las piernas"
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Sube en arco natural sin chocar arriba"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tira sin impulsarte con el torso"
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Aguanta dos segundos con los brazos extendidos"
     }
    ],
    "cooldown": "Estiramientos de isquios y hombros 5 min"
   },
   {
    "day": "Viernes",
    "name": "Cuerpo completo C",
    "warmup": "5 min de bici y movilidad general",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "No bloquees las rodillas al extender"
     },
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Baja hasta un estiramiento cómodo del pectoral"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tirón limpio sin encoger los hombros"
     },
     {
      "name": "Elevaciones de rodillas colgado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Sube las rodillas sin balancear el cuerpo"
     }
    ],
    "cooldown": "5 min de trote muy suave"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: compaginar fuerza y volumen de cardio",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Separa fuerza y LISS largo al menos 6 horas"
   },
   {
    "week": 2,
    "intent": "Progresión: subir cargas en básicos",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Volumen de pesas estable"
   },
   {
    "week": 3,
    "intent": "Carga: semana fuerte de pesas",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Si las piernas no rinden, recorta un LISS"
   },
   {
    "week": 4,
    "intent": "Descarga: bajar pesas, mantener cardio suave",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 10000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 45,
     "times_per_week": 4,
     "notes": "Carrera suave, bici o elíptica a ritmo conversacional"
    },
    {
     "type": "hiit",
     "minutes": 20,
     "times_per_week": 1,
     "notes": "Series en bici o cuestas, nunca antes del día de pierna"
    }
   ]
  },
  "deload_instructions": "Semana 4: pesas al 90 por ciento con una serie menos y el HIIT se cambia por LISS suave."
 },
 {
  "category": "perdida_grasa",
  "title": "Choque supervisado 6 días",
  "case": "Mujer de 24 años, avanzada y con historial deportivo, que inicia una fase corta de pérdida rápida bajo supervisión directa del coach. Puede entrenar seis días.",
  "level": "advanced",
  "days_per_week": 6,
  "place": "gym",
  "split_name": "Empuje-tirón-pierna x2",
  "split_rationale": "Con seis días, el PPL doble reparte la fatiga por patrones y permite alto gasto semanal con sesiones cortas y densas bajo supervisión.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Empuje 1",
    "warmup": "5 min de cardio suave y movilidad de hombro",
    "exercises": [
     {
      "name": "Press banca con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Escápulas fijas y pies enraizados"
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Baja a la altura de las orejas"
     },
     {
      "name": "Cruce de poleas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Aprieta el pectoral al cerrar"
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos inmóviles junto al torso"
     }
    ],
    "cooldown": "Estiramientos de pecho 3 min"
   },
   {
    "day": "Martes",
    "name": "Tirón 1",
    "warmup": "5 min de remo suave y band pull-apart",
    "exercises": [
     {
      "name": "Dominadas neutras",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Inicia el tirón deprimiendo las escápulas"
     },
     {
      "name": "Remo con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Torso fijo, sin tirones lumbares"
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Termina con las manos junto a las orejas"
     },
     {
      "name": "Curl de bíceps con barra EZ",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Sube sin balancear el cuerpo"
     }
    ],
    "cooldown": "Estiramientos de dorsal 3 min"
   },
   {
    "day": "Miércoles",
    "name": "Pierna 1",
    "warmup": "6 min de bici y aproximaciones de sentadilla",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Core presurizado antes de romper la cadera"
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Cadera atrás hasta sentir los isquios"
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Pausa arriba en cada repetición"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Tensión global sin hundir la cadera"
     }
    ],
    "cooldown": "Estiramientos de piernas 5 min"
   },
   {
    "day": "Jueves",
    "name": "Empuje 2",
    "warmup": "5 min de cardio suave y rotaciones con banda",
    "exercises": [
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Trayectoria estable, sin chocar arriba"
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Empuje simétrico y controlado"
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1",
      "rest_sec": 60,
      "technique_cue": "Codos suben antes que las manos"
     },
     {
      "name": "Extensión de tríceps en polea con barra",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Extiende completo sin abrir los codos"
     }
    ],
    "cooldown": "Estiramientos de hombro 3 min"
   },
   {
    "day": "Viernes",
    "name": "Tirón 2",
    "warmup": "5 min de remo suave y movilidad torácica",
    "exercises": [
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tira a la clavícula con el pecho alto"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Pausa atrás apretando la espalda"
     },
     {
      "name": "Pájaros con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Abre en arco con torso firme apoyado en cadera"
     },
     {
      "name": "Curl martillo",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos pegados, sin balanceo"
     }
    ],
    "cooldown": "Estiramientos de espalda 3 min"
   },
   {
    "day": "Sábado",
    "name": "Pierna 2",
    "warmup": "6 min de bici y activación de glúteo",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Baja profundo sin despegar la pelvis"
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Sube rápido, baja en tres segundos"
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Extensión completa con mirada al frente"
     },
     {
      "name": "Crunch en polea alta",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Flexiona el tronco, no la cadera"
     }
    ],
    "cooldown": "Estiramientos completos 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: encajar la alta frecuencia",
    "load_pct": 100,
    "rir_target": "2",
    "volume_note": "Sesiones cortas, nada al fallo"
   },
   {
    "week": 2,
    "intent": "Progresión: subir cargas con fatiga controlada",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Reporta sensaciones diarias al coach"
   },
   {
    "week": 3,
    "intent": "Carga: pico del bloque de choque",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Sin series extra: la frecuencia ya es alta"
   },
   {
    "week": 4,
    "intent": "Descarga: obligatoria tras el choque",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Una serie menos por ejercicio y un día de pesas menos si hay fatiga"
   }
  ],
  "cardio": {
   "daily_steps": 10000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 3,
     "notes": "Tras el entreno o en la pausa de mediodía"
    },
    {
     "type": "hiit",
     "minutes": 15,
     "times_per_week": 2,
     "notes": "Bici o elíptica, nunca la víspera de pierna"
    }
   ]
  },
  "deload_instructions": "La semana 4 es innegociable: 90 por ciento de carga, una serie menos y sin HIIT; esta fase no se alarga más de un bloque sin revisión del coach."
 },
 {
  "category": "perdida_grasa",
  "title": "Cuarenta minutos justos",
  "case": "Mujer de 37 años con dos hijos pequeños y ventanas de 30-40 minutos como máximo. Quiere perder grasa con sesiones cortas que siempre pueda cumplir.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body exprés",
  "split_rationale": "Cuatro ejercicios por sesión con descansos ajustados: estímulo completo en menos de 40 minutos, sin sensación de tarea a medias.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Exprés A",
    "warmup": "4 min de cinta rápida y movilidad básica",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Empuja con talones y medio pie"
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Recorrido completo sin rebotes"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Tira hasta la clavícula con torso estable"
     },
     {
      "name": "Plancha abdominal",
      "sets": 2,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Aprieta abdomen como si esperases un golpe"
     }
    ],
    "cooldown": "2 min de respiración y estiramiento breve"
   },
   {
    "day": "Miércoles",
    "name": "Exprés B",
    "warmup": "4 min de bici y movilidad de cadera",
    "exercises": [
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadera atrás, espalda recta siempre"
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Sube sin encoger los trapecios"
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Abre el pecho al tirar"
     },
     {
      "name": "Dead bug",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Lumbar pegada, ritmo lento"
     }
    ],
    "cooldown": "2 min de estiramientos suaves"
   },
   {
    "day": "Viernes",
    "name": "Exprés C",
    "warmup": "4 min de elíptica y círculos articulares",
    "exercises": [
     {
      "name": "Zancada estática",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Baja vertical con el tronco erguido"
     },
     {
      "name": "Cruce de poleas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Codos semiflexionados constantes"
     },
     {
      "name": "Jalón agarre estrecho neutro",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Lleva los codos a las costillas"
     },
     {
      "name": "Press Pallof",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Ni el tronco ni la cadera rotan"
     }
    ],
    "cooldown": "2 min de respiración"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: consolidar la logística familiar",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Mejor sesión corta hecha que perfecta cancelada"
   },
   {
    "week": 2,
    "intent": "Progresión: subir carga sin alargar la sesión",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismos descansos cortos"
   },
   {
    "week": 3,
    "intent": "Carga: semana más intensa",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Serie extra solo si el reloj lo permite"
   },
   {
    "week": 4,
    "intent": "Descarga: semana ligera",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "hiit",
     "minutes": 15,
     "times_per_week": 2,
     "notes": "Bici o elíptica al acabar la sesión, si queda hueco"
    },
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 1,
     "notes": "Paseo largo del fin de semana, con o sin niños"
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90 por ciento y una serie menos; si una semana solo caben dos sesiones, haz A y C."
 },
 {
  "category": "perdida_grasa",
  "title": "Regreso tras la pausa",
  "case": "Hombre de 52 años, exfutbolista amateur que lleva más de diez años sin entrenar. Quiere perder grasa y retomar el hábito sin agujetas paralizantes ni lesiones.",
  "level": "beginner",
  "days_per_week": 2,
  "place": "gym",
  "split_name": "Full body de readaptación",
  "split_rationale": "Dos sesiones completas con volumen bajo permiten recuperar patrones y tolerancia al esfuerzo sin saturar a un cuerpo desentrenado.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Readaptación A",
    "warmup": "8 min de bici suave y movilidad completa",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Rango cómodo y velocidad controlada"
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "No dejes caer el peso entre repeticiones"
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tira con la espalda y pausa atrás"
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Sube despacio y baja más despacio"
     },
     {
      "name": "Dead bug",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Coordina respiración y movimiento"
     }
    ],
    "cooldown": "5 min de estiramientos generales"
   },
   {
    "day": "Jueves",
    "name": "Readaptación B",
    "warmup": "8 min de cinta y sentadillas al aire",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Baja hasta donde controles la postura"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Movimiento amplio sin echarte hacia atrás"
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Empuja sin arquear la zona lumbar"
     },
     {
      "name": "Curl femoral sentado",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Flexión controlada sin tirones"
     },
     {
      "name": "Plancha abdominal",
      "sets": 2,
      "rep_range": "20-30s",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Línea recta y respiración constante"
     }
    ],
    "cooldown": "5 min de estiramientos y bici muy suave"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: despertar patrones sin dolor posterior",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Sal del gimnasio con sensación de poder hacer más"
   },
   {
    "week": 2,
    "intent": "Progresión: pequeño aumento de carga",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Mismo volumen"
   },
   {
    "week": 3,
    "intent": "Carga: primera semana realmente exigente",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Añade una serie a prensa y jalón"
   },
   {
    "week": 4,
    "intent": "Descarga: consolidar el hábito",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Caminata rápida o bici; ritmo conversacional"
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90 por ciento y una serie menos; si las agujetas duran más de tres días, repite la semana anterior antes de progresar."
 },
 {
  "category": "perdida_grasa",
  "title": "Cintura de acero",
  "case": "Mujer de 25 años, intermedia, con grasa localizada en la zona media y prioridad estética en cintura y abdomen. Sabe que el déficit manda, pero quiere un core sobresaliente.",
  "level": "intermediate",
  "days_per_week": 4,
  "place": "gym",
  "split_name": "Full body con énfasis en core",
  "split_rationale": "Cuatro sesiones completas con doble ración de core variado (antiextensión, antirrotación y flexión): la cintura se marca con déficit y un core fuerte.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Día 1 - Base + core frontal",
    "warmup": "5 min de cardio suave y movilidad general",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Core firme como un corsé en cada repetición"
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Baja controlado hasta la línea del pecho"
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tira sin inclinar el torso atrás"
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Pelvis neutra y glúteo activo"
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Extiende y aguanta dos segundos sin girar"
     }
    ],
    "cooldown": "Estiramientos generales 5 min"
   },
   {
    "day": "Martes",
    "name": "Día 2 - Bisagra + antirrotación",
    "warmup": "5 min de remo suave y activación de glúteo",
    "exercises": [
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Espalda neutra y barra pegada al cuerpo"
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Costillas abajo mientras empujas"
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Codos hacia el suelo, pecho alto"
     },
     {
      "name": "Leñador en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Gira desde el tronco con brazos casi rectos"
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Lumbar sellada al suelo todo el tiempo"
     }
    ],
    "cooldown": "5 min de estiramientos de cadera"
   },
   {
    "day": "Jueves",
    "name": "Día 3 - Glúteo + flexión",
    "warmup": "5 min de bici y puentes sin carga",
    "exercises": [
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Bloqueo completo con barbilla recogida"
     },
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Sube empujando con el talón delantero"
     },
     {
      "name": "Cruce de poleas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Cierra en abrazo amplio y controlado"
     },
     {
      "name": "Crunch en polea alta",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Enrolla la columna, no tires de brazos"
     },
     {
      "name": "Plancha lateral",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cadera elevada y cuerpo alineado"
     }
    ],
    "cooldown": "Estiramientos suaves 5 min"
   },
   {
    "day": "Viernes",
    "name": "Día 4 - Mixto + carga asimétrica",
    "warmup": "5 min de cinta y movilidad de hombro",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Rodillas alineadas con los pies al bajar"
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "No dejes que el torso rote al tirar"
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Termina con doble mentón y manos altas"
     },
     {
      "name": "Elevaciones de rodillas colgado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Sube sin balanceo, baja controlado"
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Camina recto resistiendo la inclinación"
     }
    ],
    "cooldown": "Estiramientos completos 5 min"
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: dominar el trabajo de core variado",
    "load_pct": 100,
    "rir_target": "2",
    "volume_note": "Calidad absoluta en los ejercicios de core"
   },
   {
    "week": 2,
    "intent": "Progresión: más carga en básicos y core",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Volumen estable"
   },
   {
    "week": 3,
    "intent": "Carga: semana pico del bloque",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Serie extra en plancha y Pallof"
   },
   {
    "week": 4,
    "intent": "Descarga: recuperar la zona media",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Una serie menos por ejercicio"
   }
  ],
  "cardio": {
   "daily_steps": 11000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 3,
     "notes": "Cinta inclinada o paseo rápido"
    },
    {
     "type": "hiit",
     "minutes": 12,
     "times_per_week": 1,
     "notes": "Bici o elíptica en día sin pierna pesada"
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90 por ciento con una serie menos, también en el core; la cintura la define el déficit sostenido, no castigar el abdomen a diario."
 },
 {
  "category": "salud_espalda",
  "title": "Espalda fuerte para oficinistas",
  "case": "Hombre de 38 años, programador con 9 horas diarias sentado y dolor lumbar inespecífico que aparece al final de la jornada. Busca fortalecer espalda y core sin agravar la molestia.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body 3 días",
  "split_rationale": "Tres sesiones de cuerpo completo permiten frecuencia alta de core y cadera con poca fatiga acumulada por sesión, ideal para desensibilizar la zona lumbar.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Cuerpo completo A",
    "warmup": "8-10 min: bici suave, movilidad de cadera y gato-camello, 2 series de aproximación.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Torso vertical y peso repartido en todo el pie."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Escápulas apoyadas en el respaldo todo el recorrido."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tira con los codos sin balancear el tronco."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Baja controlado en 2-3 segundos."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Zona lumbar pegada al suelo, exhala al extender."
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Camina erguido sin inclinarte hacia la carga."
     }
    ],
    "cooldown": "5 min de respiración diafragmática y estiramiento suave de flexores de cadera."
   },
   {
    "day": "Miércoles",
    "name": "Cuerpo completo B",
    "warmup": "8-10 min: cinta andando, movilidad torácica y activación de glúteo con banda.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "No despegues la pelvis del respaldo al bajar."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Lleva la barra a la clavícula con pecho alto."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Empuja sin arquear la zona lumbar."
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Bloquea arriba con glúteo, sin hiperextender lumbar."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Alarga brazo y pierna sin rotar la pelvis."
     },
     {
      "name": "Plancha lateral",
      "sets": 2,
      "rep_range": "30-45s",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Cadera alta, cuerpo en línea recta."
     }
    ],
    "cooldown": "5 min de estiramientos suaves de glúteo y respiración lenta."
   },
   {
    "day": "Viernes",
    "name": "Cuerpo completo C",
    "warmup": "8-10 min: remo suave, movilidad de cadera y series de aproximación.",
    "exercises": [
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Paso atrás controlado, rodilla alineada con el pie."
     },
     {
      "name": "Remo con pecho apoyado en banco",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "El pecho no se separa del banco al tirar."
     },
     {
      "name": "Cruce de poleas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Junta las manos con ligera flexión de codo fija."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Cadera pegada al banco durante toda la serie."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Extiende los brazos sin dejar que el tronco gire."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Aprieta glúteo y abdomen, no hundas la cadera."
     }
    ],
    "cooldown": "5 min de movilidad suave de columna y respiración nasal."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: aprender técnica y tolerancia de la zona lumbar",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Series indicadas, sin buscar el fallo en ningún caso."
   },
   {
    "week": 2,
    "intent": "Progresión suave si no hay molestia posterior al entreno",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Misma estructura, sube ligeramente la carga si la técnica es limpia."
   },
   {
    "week": 3,
    "intent": "Carga: semana más exigente manteniendo espalda neutra",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Puede añadirse 1 serie al remo y al core si va bien."
   },
   {
    "week": 4,
    "intent": "Descarga para consolidar sin acumular fatiga",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Reduce 1 serie por ejercicio y mantén la técnica."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Caminata rápida o bici suave; levántate del escritorio cada 45-60 min."
    }
   ]
  },
  "deload_instructions": "Semana 4: baja la carga un 10 % y quita una serie por ejercicio. Si el dolor lumbar aumenta dos sesiones seguidas, reduce carga y consulta con el coach."
 },
 {
  "category": "salud_espalda",
  "title": "Vuelta a la carga tras hernia",
  "case": "Hombre de 52 años, administrativo con hernia discal lumbar estabilizada y alta médica para entrenar fuerza. Quiere recuperar tono general con máxima seguridad.",
  "level": "beginner",
  "days_per_week": 2,
  "place": "gym",
  "split_name": "Full body 2 días",
  "split_rationale": "Dos sesiones completas con apoyos y máquinas minimizan la carga compresiva sobre la columna mientras se reconstruye fuerza básica.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Cuerpo completo A",
    "warmup": "10 min: bici suave, gato-camello, activación de core en el suelo.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Rango cómodo, la pelvis nunca se despega del respaldo."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Empuja exhalando, sin arquear la espalda."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Tronco estable, tira llevando los codos atrás."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Movimiento lento y sin tirones."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Lumbar apoyada; si se despega, acorta el recorrido."
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 2,
      "rep_range": "30-40s",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Hombros nivelados, pasos cortos y firmes."
     }
    ],
    "cooldown": "5 min de respiración diafragmática tumbado con piernas elevadas."
   },
   {
    "day": "Jueves",
    "name": "Cuerpo completo B",
    "warmup": "10 min: cinta andando con ligera pendiente y movilidad de cadera.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Baja solo hasta donde la espalda se mantenga neutra."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Sin balanceo del tronco al tirar."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Zona lumbar apoyada en el respaldo siempre."
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Sube con glúteo y detente al alinear cadera."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Imagina un vaso de agua sobre la zona lumbar."
     },
     {
      "name": "Plancha abdominal",
      "sets": 2,
      "rep_range": "20-30s",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Tiempo corto y calidad alta; corta si tiembla la cadera."
     }
    ],
    "cooldown": "5 min de estiramiento suave de glúteos e isquios sin rebotes."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: confirmar que ningún ejercicio genera síntomas",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Cargas cómodas; prioridad absoluta a la técnica."
   },
   {
    "week": 2,
    "intent": "Progresión mínima solo en ejercicios sin molestia",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Misma estructura; sube carga solo donde la ejecución sea perfecta."
   },
   {
    "week": 3,
    "intent": "Carga moderada manteniendo columna neutra en todo momento",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "Puede añadirse 1 serie a prensa y remo si no hay síntomas."
   },
   {
    "week": 4,
    "intent": "Descarga para asentar adaptaciones",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Una serie menos por ejercicio y sensación de facilidad."
   }
  ],
  "cardio": {
   "daily_steps": 7000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 3,
     "notes": "Caminata llana o bici estática; evita impactos y giros bruscos."
    }
   ]
  },
  "deload_instructions": "Semana 4: reduce un 10 % la carga y una serie por ejercicio. Ante cualquier irradiación hacia la pierna, detén la sesión y comunícalo al coach y al médico."
 },
 {
  "category": "salud_espalda",
  "title": "Cuello y pantallas en equilibrio",
  "case": "Mujer de 29 años, diseñadora que trabaja desde casa con cervicalgia por muchas horas frente a pantallas. Quiere entrenar en casa con bandas y mancuernas para descargar cuello y hombros.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "home",
  "split_name": "Full body 3 días en casa",
  "split_rationale": "Cuerpo completo con mucho trabajo de tracción y espalda alta reparte estímulo postural en tres días sin sobrecargar el cuello en ninguna sesión.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Cuerpo completo A",
    "warmup": "8 min: movilidad de cuello suave, círculos de hombros y retracciones escapulares.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Mirada al frente, cuello largo y relajado."
     },
     {
      "name": "Press de pecho con banda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Hombros lejos de las orejas al empujar."
     },
     {
      "name": "Remo con banda sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Lleva los codos atrás sin encoger los trapecios."
     },
     {
      "name": "Face pull con banda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Tira hacia la cara y abre las manos al final."
     },
     {
      "name": "Puente de glúteo",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Sube con glúteo, barbilla ligeramente recogida."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Cabeza apoyada en el suelo, sin tensar el cuello."
     }
    ],
    "cooldown": "5 min de estiramiento suave de trapecio y pectoral en el marco de una puerta."
   },
   {
    "day": "Miércoles",
    "name": "Cuerpo completo B",
    "warmup": "8 min: caminata en casa, movilidad torácica y band pull-apart ligeros.",
    "exercises": [
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tronco erguido, empuja con el talón delantero."
     },
     {
      "name": "Remo invertido bajo una mesa",
      "sets": 3,
      "rep_range": "8-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Cuerpo en línea, pecho hacia el borde de la mesa."
     },
     {
      "name": "Elevación lateral con banda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Sube solo hasta la altura del hombro."
     },
     {
      "name": "Band pull-apart",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Abre la banda apretando las escápulas sin subir hombros."
     },
     {
      "name": "Curl femoral con deslizadores",
      "sets": 3,
      "rep_range": "8-12",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Cadera extendida mientras deslizas los talones."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Cuello neutro mirando al suelo."
     }
    ],
    "cooldown": "5 min de respiración lenta y estiramiento de columna torácica sobre cojín."
   },
   {
    "day": "Viernes",
    "name": "Cuerpo completo C",
    "warmup": "8 min: movilidad general y activación escapular con banda ligera.",
    "exercises": [
     {
      "name": "Peso muerto rumano a una pierna",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Cadera atrás, espalda recta y cuello alineado."
     },
     {
      "name": "Flexiones",
      "sets": 3,
      "rep_range": "8-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Apoya en rodillas si pierdes la línea corporal."
     },
     {
      "name": "Jalón con banda de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Tira de los codos hacia las costillas."
     },
     {
      "name": "Face pull con banda",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Termina con las manos a la altura de las orejas."
     },
     {
      "name": "Frog pump",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "2-3",
      "rest_sec": 45,
      "technique_cue": "Plantas de los pies juntas y aprieta glúteo arriba."
     },
     {
      "name": "Plancha lateral",
      "sets": 2,
      "rep_range": "30-45s",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Cabeza en línea con la columna, no la adelantes."
     }
    ],
    "cooldown": "5 min de estiramiento de cuello suave (inclinaciones, sin rebotes) y respiración."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: técnica y hábito de pausas frente a la pantalla",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Cargas suaves; nada debe aumentar la tensión del cuello."
   },
   {
    "week": 2,
    "intent": "Progresión ligera en tracciones y pierna",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Banda algo más tensa o mancuerna algo mayor si no hay molestia."
   },
   {
    "week": 3,
    "intent": "Carga: semana de mayor esfuerzo con postura impecable",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Añade 1 serie a face pull y remo si el cuello responde bien."
   },
   {
    "week": 4,
    "intent": "Descarga y consolidación postural",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio, énfasis en ejecución lenta."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Paseo al aire libre; pausa de pantalla de 2-3 min cada hora de trabajo."
    }
   ]
  },
  "deload_instructions": "Semana 4: baja un 10 % la resistencia y una serie por ejercicio. Si el dolor cervical irradia al brazo u ocasiona hormigueo, suspende y derivamos al médico."
 },
 {
  "category": "salud_espalda",
  "title": "Hombro sin dolor, torso completo",
  "case": "Hombre de 45 años, comercial que entrena desde hace años y arrastra un hombro doloroso al elevar el brazo. Quiere seguir fuerte evitando lo que le irrita el hombro.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Torso A - Pierna - Torso B",
  "split_rationale": "Dos días de torso con empujes de recorrido amigable y mucho trabajo de rotadores, separados por un día de pierna, permiten mantener volumen sin irritar el hombro.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Torso A",
    "warmup": "10 min: movilidad escapular, rotaciones externas ligeras y series de aproximación.",
    "exercises": [
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Ajusta el asiento para empujar sin pinzamiento."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Escápulas atrás y abajo antes de tirar."
     },
     {
      "name": "Press landmine de pie",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Trayectoria diagonal, empuja sin dolor en el arco."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Rota externamente al final del tirón."
     },
     {
      "name": "Rotación externa de hombro en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Codo pegado al costado, movimiento lento."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos fijos junto al torso."
     }
    ],
    "cooldown": "5 min de estiramiento suave de pectoral y dorsal sin forzar el hombro."
   },
   {
    "day": "Miércoles",
    "name": "Pierna",
    "warmup": "10 min: bici, movilidad de cadera y tobillo, aproximaciones en prensa.",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Baja controlado sin despegar la pelvis."
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Cadera atrás, barra rozando los muslos."
     },
     {
      "name": "Sentadilla búlgara",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Rodilla delantera estable, torso ligeramente inclinado."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Sin impulso, control total de la bajada."
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Pausa de 1 segundo arriba y abajo."
     }
    ],
    "cooldown": "5 min de estiramiento de cuádriceps e isquios y respiración."
   },
   {
    "day": "Viernes",
    "name": "Torso B",
    "warmup": "10 min: movilidad escapular, band pull-apart y aproximaciones en jalón.",
    "exercises": [
     {
      "name": "Jalón al pecho",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Agarre que no provoque molestia; tira al pecho."
     },
     {
      "name": "Contractora de pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Recorrido corto y sin dolor en la apertura."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho apoyado, tira sin encoger hombros."
     },
     {
      "name": "Elevación lateral en polea unilateral",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Sube solo dentro del rango sin dolor."
     },
     {
      "name": "Curl de bíceps con barra EZ",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos quietos junto al cuerpo."
     },
     {
      "name": "Extensión de tríceps en polea con barra",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Bloqueo completo sin mover los hombros."
     }
    ],
    "cooldown": "5 min de movilidad suave de hombro dentro de rango indoloro."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: mapear rangos sin dolor en cada empuje",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Anota qué ejercicios y rangos son 100 % cómodos."
   },
   {
    "week": 2,
    "intent": "Progresión en tracciones y pierna; empujes conservadores",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Sube carga en remos y jalones antes que en presses."
   },
   {
    "week": 3,
    "intent": "Carga: semana fuerte respetando el rango indoloro",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Puede añadirse 1 serie de face pull y rotación externa."
   },
   {
    "week": 4,
    "intent": "Descarga para dar descanso a los tejidos del hombro",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Una serie menos por ejercicio, mantén el trabajo de rotadores."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Bici o cinta con pendiente; evita crol o remo intenso mientras dure la molestia."
    }
   ]
  },
  "deload_instructions": "Semana 4: baja un 10 % la carga y una serie por ejercicio. Si el dolor de hombro pasa de 3/10 durante un press, cámbialo por su variante en máquina o reduce el rango."
 },
 {
  "category": "salud_espalda",
  "title": "Rodilla de corredor bajo control",
  "case": "Mujer de 34 años, corredora popular con dolor anterior de rodilla que le impide sumar kilómetros. Busca fuerza de cadera y pierna que le permita volver a correr sin molestias.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Pierna - Torso - Full body",
  "split_rationale": "Dos estímulos semanales de pierna con patrones dominantes de cadera y carga tolerable para la rodilla, más un día de torso para mantener el conjunto.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Pierna y core",
    "warmup": "10 min: bici sin resistencia, movilidad de cadera y activación de glúteo medio.",
    "exercises": [
     {
      "name": "Sentadilla a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Siéntate atrás tocando el cajón sin rebotar."
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Bisagra de cadera pura, rodillas semiflexionadas."
     },
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Empuja con el talón, sube sin impulso del pie trasero."
     },
     {
      "name": "Abducción de cadera en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Pausa de 1 segundo en la apertura máxima."
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo, bajada lenta."
     },
     {
      "name": "Plancha lateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2-3",
      "rest_sec": 45,
      "technique_cue": "Pelvis alta, aprieta el glúteo del lado de apoyo."
     }
    ],
    "cooldown": "5 min de estiramiento suave de cuádriceps, glúteo y gemelo."
   },
   {
    "day": "Miércoles",
    "name": "Torso",
    "warmup": "8-10 min: remo suave y movilidad escapular con series de aproximación.",
    "exercises": [
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Baja las mancuernas controladas a la altura del pecho."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Tira hacia el abdomen con el tronco quieto."
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Respaldo alto y core activo al empujar."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Codos hacia abajo y atrás, sin balanceo."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Separa la cuerda al final de la extensión."
     },
     {
      "name": "Curl alterno con mancuernas",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Sin balancear el tronco entre repeticiones."
     }
    ],
    "cooldown": "5 min de estiramientos de pectoral y dorsal."
   },
   {
    "day": "Viernes",
    "name": "Full body dominante de cadera",
    "warmup": "10 min: bici suave, movilidad de cadera y activación con banda.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Profundidad que no reproduzca el dolor; empuja con talones."
     },
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Paso atrás largo para cargar el glúteo."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Control excéntrico de 3 segundos."
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Mentón recogido y bloqueo con glúteo arriba."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Codos altos y rotación externa final."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 45,
      "technique_cue": "Resiste el giro con el abdomen, no con los brazos."
     }
    ],
    "cooldown": "5 min de movilidad de tobillo y estiramiento de cadena posterior."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: cargar la rodilla solo en rangos tolerables",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "El dolor no debe pasar de 3/10 ni empeorar al día siguiente."
   },
   {
    "week": 2,
    "intent": "Progresión de carga en bisagras y prensa",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Sube carga donde no haya síntomas; mantén zancadas estables."
   },
   {
    "week": 3,
    "intent": "Carga: semana más fuerte y valoración de trote suave",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Si la rodilla va bien, se valora reintroducir carrera con el coach."
   },
   {
    "week": 4,
    "intent": "Descarga para absorber el estímulo",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Una serie menos por ejercicio; nada de pruebas nuevas."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Bici o elíptica sin dolor en sustitución temporal de la carrera."
    }
   ]
  },
  "deload_instructions": "Semana 4: reduce un 10 % la carga y una serie por ejercicio. La vuelta a correr se decide con el coach solo si las semanas 1-3 cursan sin dolor relevante."
 },
 {
  "category": "salud_espalda",
  "title": "Artrosis leve, piernas activas",
  "case": "Hombre de 63 años, jubilado activo con artrosis leve de rodilla diagnosticada. Quiere mantener fuerza y autonomía para caminar y subir escaleras sin dolor.",
  "level": "beginner",
  "days_per_week": 2,
  "place": "gym",
  "split_name": "Full body 2 días",
  "split_rationale": "Dos sesiones completas en máquinas y apoyos estables cargan la musculatura de la pierna con mínimo estrés articular y máxima seguridad.",
  "sessions": [
   {
    "day": "Martes",
    "name": "Cuerpo completo A",
    "warmup": "10 min: bici suave sin resistencia y movilidad progresiva de rodilla y cadera.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Rango cómodo; el dolor no debe pasar de leve."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Movimiento suave, sin bloqueos bruscos."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Empuja exhalando, espalda apoyada."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Tira con la espalda, hombros lejos de las orejas."
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Pausa arriba de 1 segundo."
     },
     {
      "name": "Dead bug",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Movimiento lento coordinado con la respiración."
     }
    ],
    "cooldown": "5 min de paseo suave y estiramiento de cuádriceps y gemelo."
   },
   {
    "day": "Viernes",
    "name": "Cuerpo completo B",
    "warmup": "10 min: cinta andando y movilidad de cadera, 2 aproximaciones en cajón alto.",
    "exercises": [
     {
      "name": "Sentadilla a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Cajón alto; siéntate y levántate sin impulso."
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Empuja con talones y aprieta glúteo arriba."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Barra a la clavícula con pecho alto."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Sin arquear la zona lumbar al empujar."
     },
     {
      "name": "Abducción de cadera en máquina",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Abre controlado, sin golpear los topes."
     },
     {
      "name": "Bird dog",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Estabilidad ante todo; apoya si pierdes el equilibrio."
     }
    ],
    "cooldown": "5 min de estiramientos generales suaves y respiración."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: encontrar rangos y cargas que la rodilla tolera",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Sensación de trabajo fácil en todas las series."
   },
   {
    "week": 2,
    "intent": "Progresión mínima si no aumenta el dolor en 24 h",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Sube el peso más pequeño disponible en máquinas."
   },
   {
    "week": 3,
    "intent": "Carga moderada consolidando fuerza de pierna",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "Puede añadirse 1 serie a prensa y curl femoral."
   },
   {
    "week": 4,
    "intent": "Descarga articular",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Menos series y más movilidad suave."
   }
  ],
  "cardio": {
   "daily_steps": 6000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 3,
     "notes": "Caminata llana o bici; evita cuestas pronunciadas y escaleras largas cargado."
    }
   ]
  },
  "deload_instructions": "Semana 4: reduce un 10 % la carga y una serie por ejercicio. Si la rodilla se inflama o duele más de 24 h tras entrenar, baja carga y avisa al coach."
 },
 {
  "category": "salud_espalda",
  "title": "Recuperación posparto tras cesárea",
  "case": "Mujer de 33 años, madre reciente con cesárea hace cuatro meses y visto bueno médico para ejercitarse. Quiere recuperar core y fuerza general entrenando en casa con poco tiempo.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "home",
  "split_name": "Full body progresivo en casa",
  "split_rationale": "Tres sesiones cortas de cuerpo completo con core de baja presión reconstruyen la base abdominal y la fuerza general sin exigir material ni sesiones largas.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Base A",
    "warmup": "8 min: respiración diafragmática, movilidad de cadera y activación suave de core.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Exhala al subir, sin apnea en ningún momento."
     },
     {
      "name": "Puente de glúteo",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Sube vértebra a vértebra y aprieta glúteo."
     },
     {
      "name": "Remo con banda sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Espalda recta, tira sin encoger hombros."
     },
     {
      "name": "Press de pecho con banda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Empuja exhalando de forma continua."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "3-4",
      "rest_sec": 45,
      "technique_cue": "Si el abdomen hace cresta, acorta el recorrido."
     }
    ],
    "cooldown": "5 min de respiración 4-6 tumbada y estiramiento suave de cadera."
   },
   {
    "day": "Miércoles",
    "name": "Base B",
    "warmup": "8 min: paseo suave y movilidad general articular.",
    "exercises": [
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Apóyate en una silla si necesitas equilibrio."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Cadera atrás y espalda larga, carga ligera."
     },
     {
      "name": "Jalón con banda de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Codos hacia las costillas al tirar."
     },
     {
      "name": "Elevación lateral con banda",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Movimiento controlado hasta la altura del hombro."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Pelvis estable, alarga sin arquear la lumbar."
     }
    ],
    "cooldown": "5 min de estiramiento suave y respiración diafragmática."
   },
   {
    "day": "Viernes",
    "name": "Base C",
    "warmup": "8 min: movilidad de columna y activación de glúteo y core.",
    "exercises": [
     {
      "name": "Sentadilla en pared (isométrica)",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Respira de forma continua, no aguantes el aire."
     },
     {
      "name": "Frog pump",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Pelvis en ligera retroversión al apretar arriba."
     },
     {
      "name": "Remo invertido bajo una mesa",
      "sets": 3,
      "rep_range": "6-10",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Rodillas flexionadas para aligerar si hace falta."
     },
     {
      "name": "Face pull con banda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Abre las manos al final apretando escápulas."
     },
     {
      "name": "Curl femoral con deslizadores",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Mantén la cadera arriba mientras deslizas."
     },
     {
      "name": "Plancha lateral",
      "sets": 2,
      "rep_range": "20-30s",
      "rir": "3-4",
      "rest_sec": 45,
      "technique_cue": "Empieza con rodillas apoyadas si notas presión abdominal."
     }
    ],
    "cooldown": "5 min de respiración lenta y estiramientos generales."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: reconectar core y suelo pélvico sin presión",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Todo debe sentirse fácil; vigila cualquier presión abdominal."
   },
   {
    "week": 2,
    "intent": "Progresión suave en pierna y tracciones",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Aumenta ligeramente banda o mancuerna si no hay síntomas."
   },
   {
    "week": 3,
    "intent": "Carga moderada manteniendo el control respiratorio",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "Puede alargarse la isometría 5-10 segundos."
   },
   {
    "week": 4,
    "intent": "Descarga y evaluación con el coach",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Menos series; valorar progresar el core el mes siguiente."
   }
  ],
  "cardio": {
   "daily_steps": 7000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 20,
     "times_per_week": 3,
     "notes": "Paseo con o sin carrito a ritmo cómodo; sin impacto por ahora."
    }
   ]
  },
  "deload_instructions": "Semana 4: reduce una serie por ejercicio y la resistencia un 10 %. Ante dolor en la cicatriz, pérdidas de orina o abombamiento abdominal, se pausa y se consulta al médico."
 },
 {
  "category": "salud_espalda",
  "title": "Fuerza segura en el embarazo",
  "case": "Mujer de 31 años, embarazada de 22 semanas con autorización médica y experiencia previa en gimnasio. Quiere mantener fuerza y bienestar evitando posiciones y esfuerzos de riesgo.",
  "level": "intermediate",
  "days_per_week": 2,
  "place": "gym",
  "split_name": "Full body 2 días adaptado",
  "split_rationale": "Dos sesiones completas en máquinas y posiciones sentadas o de pie mantienen fuerza sin decúbito prono, sin Valsalva y con fatiga controlada.",
  "sessions": [
   {
    "day": "Martes",
    "name": "Cuerpo completo A",
    "warmup": "10 min: bici suave, movilidad de cadera y respiración continua.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Exhala al subir; carga moderada y postura amplia."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Tronco erguido, tira sin retener el aire."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Sentada con respaldo, ritmo cómodo de respiración."
     },
     {
      "name": "Abducción de cadera en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Abre controlado sin llegar a molestia en el pubis."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "De pie, resiste el giro respirando con normalidad."
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Bombea con pausa arriba para favorecer el retorno venoso."
     }
    ],
    "cooldown": "5 min de paseo suave y estiramientos generales sin forzar."
   },
   {
    "day": "Viernes",
    "name": "Cuerpo completo B",
    "warmup": "10 min: cinta andando y movilidad de hombro y cadera.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Rango cómodo que no comprima el abdomen."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Tira exhalando, sin arquear la lumbar."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Empuja sin bloquear la respiración en ningún punto."
     },
     {
      "name": "Patada de glúteo en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "De pie, extiende la cadera sin arquear la espalda."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Codos altos y escápulas activas."
     },
     {
      "name": "Bird dog",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3-4",
      "rest_sec": 45,
      "technique_cue": "En cuadrupedia, movimiento lento y estable."
     }
    ],
    "cooldown": "5 min de respiración lenta sentada y movilidad suave."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: confirmar comodidad de cada ejercicio en esta etapa",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Nada de esfuerzos máximos; conversación posible en cardio."
   },
   {
    "week": 2,
    "intent": "Progresión mínima solo si la sensación es buena",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "La prioridad es la constancia, no la carga."
   },
   {
    "week": 3,
    "intent": "Mantener estímulo estable escuchando al cuerpo",
    "load_pct": 105,
    "rir_target": "3",
    "volume_note": "Si hay fatiga inusual, repetir cargas de la semana 1."
   },
   {
    "week": 4,
    "intent": "Descarga y revisión de sensaciones con el coach",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Menos series y más movilidad y respiración."
   }
  ],
  "cardio": {
   "daily_steps": 7000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 3,
     "notes": "Caminata o bici estática pudiendo mantener una conversación."
    }
   ]
  },
  "deload_instructions": "Semana 4: reduce un 10 % la carga y una serie por ejercicio. Ante mareo, sangrado, contracciones o cualquier señal inusual, se detiene la sesión y se contacta con su médico."
 },
 {
  "category": "salud_espalda",
  "title": "Huesos fuertes con carga inteligente",
  "case": "Mujer de 58 años, profesora con densitometría que muestra osteoporosis incipiente. Busca cargar el esqueleto de forma progresiva y segura para frenar la pérdida ósea.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body 3 días con carga axial",
  "split_rationale": "Tres sesiones completas con carga axial moderada (peso muerto hexagonal, sentadillas, cargas en pie) estimulan el hueso, evitando flexiones bruscas de columna.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Cuerpo completo A",
    "warmup": "10 min: cinta con pendiente suave y movilidad de cadera y hombro.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Columna larga y pecho alto en todo el recorrido."
     },
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Empuja con talones sin despegar la pelvis."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tira manteniendo la espalda erguida, sin encorvarte."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Movimiento fluido, sin apnea."
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Carga vertical controlada, apóyate si lo necesitas."
     },
     {
      "name": "Bird dog",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Columna neutra, sin girar la pelvis."
     }
    ],
    "cooldown": "5 min de paseo y estiramientos suaves sin flexionar la columna a fondo."
   },
   {
    "day": "Miércoles",
    "name": "Cuerpo completo B",
    "warmup": "10 min: bici y movilidad progresiva, aproximaciones con la barra hexagonal vacía.",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2-3",
      "rest_sec": 150,
      "technique_cue": "Empuja el suelo con las piernas, espalda recta."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Pecho alto, tira sin inclinarte atrás en exceso."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Zona lumbar apoyada, empuje simétrico."
     },
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Cajón bajo; sube controlado sin saltar al bajar."
     },
     {
      "name": "Plancha abdominal",
      "sets": 2,
      "rep_range": "20-30s",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Línea recta de cabeza a talones."
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 2,
      "rep_range": "30-40s",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Erguida, sin inclinarte hacia el peso."
     }
    ],
    "cooldown": "5 min de respiración y movilidad suave de cadera."
   },
   {
    "day": "Viernes",
    "name": "Cuerpo completo C",
    "warmup": "10 min: cinta andando y activación de glúteo y espalda alta.",
    "exercises": [
     {
      "name": "Sentadilla a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Toca el cajón sin dejarte caer, sube firme."
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Bloqueo de cadera con glúteo, sin hiperextensión."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Escápulas atrás y abajo en cada tirón."
     },
     {
      "name": "Cruce de poleas",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Movimiento controlado, sin tirones."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Refuerza la postura: codos altos y pecho abierto."
     },
     {
      "name": "Dead bug",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Lumbar apoyada, movimiento lento."
     }
    ],
    "cooldown": "5 min de estiramientos suaves evitando flexión máxima de columna."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: técnica impecable con cargas moderadas",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "El hueso responde a la carga progresiva, no a la prisa."
   },
   {
    "week": 2,
    "intent": "Progresión de carga en los ejercicios axiales",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Prioriza subir peso muerto hexagonal y sentadillas."
   },
   {
    "week": 3,
    "intent": "Carga: semana de mayor estímulo óseo",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Puede añadirse 1 serie al peso muerto si la técnica aguanta."
   },
   {
    "week": 4,
    "intent": "Descarga para recuperar",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio; mantén la caminata diaria."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 3,
     "notes": "Caminata enérgica, mejor con tramos de pendiente; el paso también carga el hueso."
    }
   ]
  },
  "deload_instructions": "Semana 4: reduce un 10 % la carga y una serie por ejercicio. Evita flexiones y giros bruscos de columna con carga; ante dolor óseo localizado, parar y avisar al coach."
 },
 {
  "category": "salud_espalda",
  "title": "Fuerza con tensión controlada",
  "case": "Hombre de 55 años, hipertenso controlado con medicación y autorización médica, sin experiencia reciente de gimnasio. Busca ganar fuerza cuidando la tensión arterial.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body 3 días sin Valsalva",
  "split_rationale": "Cuerpo completo con repeticiones medias-altas, descansos amplios y sin isometrías largas ni apneas mantiene la respuesta tensional bajo control.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Cuerpo completo A",
    "warmup": "10 min: bici suave con progresión gradual y movilidad general.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Exhala siempre al subir, nunca retengas el aire."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Ritmo continuo, respiración fluida."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Tira exhalando, sin apretar la mandíbula."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Movimiento suave, sin agarrar fuerte los mangos."
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 2,
      "rep_range": "15-20",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Bombea sin bloquear la respiración."
     },
     {
      "name": "Dead bug",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Exhala largo en cada extensión de pierna."
     }
    ],
    "cooldown": "5-8 min de vuelta a la calma en bici muy suave y respiración lenta."
   },
   {
    "day": "Miércoles",
    "name": "Cuerpo completo B",
    "warmup": "10 min: cinta andando y movilidad de cadera y hombro.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Carga moderada; no bloquees rodillas ni respiración."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Tira al pecho exhalando de forma audible."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Empuje fluido, sin apretar el agarre en exceso."
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Sube exhalando y baja controlado."
     },
     {
      "name": "Curl alterno con mancuernas",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Agarre relajado, sin estrujar la mancuerna."
     },
     {
      "name": "Bird dog",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Dinámico y fluido, sin mantener posiciones largas."
     }
    ],
    "cooldown": "5-8 min de caminata suave y respiración nasal."
   },
   {
    "day": "Viernes",
    "name": "Cuerpo completo C",
    "warmup": "10 min: bici o cinta suave y activación escapular.",
    "exercises": [
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Pasos controlados, respira en cada repetición."
     },
     {
      "name": "Remo con pecho apoyado en banco",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "El apoyo del pecho evita retener el aire."
     },
     {
      "name": "Cruce de poleas",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Movimiento amplio y continuo."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Sin tirones; ritmo constante."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Tira suave hacia la cara, hombros relajados."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Extiende exhalando, codos pegados."
     }
    ],
    "cooldown": "8 min de vuelta a la calma progresiva; no termines la sesión de golpe."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: aprender a respirar en cada ejercicio",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Cargas cómodas; toma la tensión en casa según pauta médica."
   },
   {
    "week": 2,
    "intent": "Progresión suave manteniendo repeticiones altas",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Sube el escalón mínimo de peso en máquinas."
   },
   {
    "week": 3,
    "intent": "Carga moderada sin acercarse al fallo",
    "load_pct": 105,
    "rir_target": "3",
    "volume_note": "Nunca por debajo de 3 repeticiones en reserva."
   },
   {
    "week": 4,
    "intent": "Descarga cardiovascular y muscular",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Menos series y más caminata suave."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 3,
     "notes": "Ritmo conversacional; evita esprints y cuestas duras."
    }
   ]
  },
  "deload_instructions": "Semana 4: baja un 10 % la carga y una serie por ejercicio. Prohibido el fallo muscular, las apneas y las isometrías prolongadas; ante mareo o palpitaciones, parar y consultar."
 },
 {
  "category": "salud_espalda",
  "title": "Constancia diaria frente a la diabetes",
  "case": "Hombre de 48 años, transportista con diabetes tipo 2 controlada y hábitos muy sedentarios. Necesita una rutina frecuente y sencilla que dispare su gasto diario y su constancia.",
  "level": "beginner",
  "days_per_week": 4,
  "place": "gym",
  "split_name": "Torso-Pierna x2",
  "split_rationale": "Cuatro sesiones cortas alternando torso y pierna crean hábito diario, mejoran la sensibilidad a la insulina con estímulo frecuente y no agotan a un principiante.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Pierna A",
    "warmup": "8 min: bici suave y movilidad de cadera y tobillo.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Empuja con talones, ritmo constante."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Bajada controlada de 2-3 segundos."
     },
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Pecho alto y peso en el centro del pie."
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Sube a la punta con pausa breve arriba."
     },
     {
      "name": "Dead bug",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Coordina el movimiento con la exhalación."
     }
    ],
    "cooldown": "5 min de caminata suave en cinta."
   },
   {
    "day": "Martes",
    "name": "Torso A",
    "warmup": "8 min: remo suave y movilidad de hombro.",
    "exercises": [
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Recorrido completo sin bloquear codos con brusquedad."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tira hacia el abdomen con la espalda firme."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Sin arquear la zona lumbar."
     },
     {
      "name": "Curl alterno con mancuernas",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Codos quietos junto al cuerpo."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Extiende del todo separando la cuerda."
     }
    ],
    "cooldown": "5 min de estiramientos de pecho y espalda."
   },
   {
    "day": "Jueves",
    "name": "Pierna B",
    "warmup": "8 min: bici y activación de glúteo con banda.",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Piernas empujan, espalda recta como una tabla."
     },
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Paso atrás controlado, torso erguido."
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Aprieta glúteo un segundo arriba."
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo sin rebotes."
     },
     {
      "name": "Bird dog",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Lento y estable, sin girar la cadera."
     }
    ],
    "cooldown": "5 min de caminata y estiramiento de isquios."
   },
   {
    "day": "Viernes",
    "name": "Torso B",
    "warmup": "8 min: cinta suave y movilidad escapular.",
    "exercises": [
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Barra a la clavícula, sin balanceo."
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Baja controlado hasta la altura del pecho."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Escápulas atrás en cada repetición."
     },
     {
      "name": "Face pull en polea",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Codos altos, tira hacia la cara."
     },
     {
      "name": "Plancha abdominal",
      "sets": 2,
      "rep_range": "30-40s",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Cuerpo en línea, respiración continua."
     }
    ],
    "cooldown": "5 min de estiramientos generales."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: crear el hábito de 4 días y aprender las máquinas",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "La asistencia importa más que la carga esta semana."
   },
   {
    "week": 2,
    "intent": "Progresión ligera y pasos diarios al alza",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Sube un escalón de peso donde la técnica sea limpia."
   },
   {
    "week": 3,
    "intent": "Carga: semana más exigente en fuerza",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Puede añadirse 1 serie a prensa y jalón."
   },
   {
    "week": 4,
    "intent": "Descarga manteniendo la actividad diaria",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Menos series en el gimnasio, pero los pasos no bajan."
   }
  ],
  "cardio": {
   "daily_steps": 10000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 3,
     "notes": "Caminata rápida, idealmente tras las comidas principales; el NEAT es parte del tratamiento."
    }
   ]
  },
  "deload_instructions": "Semana 4: reduce un 10 % la carga y una serie por ejercicio, manteniendo los 10.000 pasos. Lleva siempre algo de hidrato rápido por si aparece hipoglucemia y registra sensaciones."
 },
 {
  "category": "salud_espalda",
  "title": "Moverse mejor con menos dolor",
  "case": "Mujer de 41 años, dependienta con obesidad y dolor articular en rodillas y tobillos al final del día. Quiere ganar fuerza y capacidad sin que las articulaciones se resientan.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body 3 días bajo impacto",
  "split_rationale": "Cuerpo completo en máquinas y apoyos estables permite entrenar duro los músculos con estrés articular mínimo y cero impacto.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Cuerpo completo A",
    "warmup": "10 min: bici suave y movilidad progresiva de cadera, rodilla y tobillo.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Rango cómodo y sin dolor; empuja con talones."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tira con la espalda, no con los brazos."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Espalda apoyada, empuje simétrico."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Control total en la bajada."
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 2,
      "rep_range": "15-20",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Trabaja el gemelo sin cargar el tobillo de pie."
     },
     {
      "name": "Dead bug",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Lumbar pegada al suelo, ritmo lento."
     }
    ],
    "cooldown": "5 min de bici muy suave y estiramientos de pierna."
   },
   {
    "day": "Miércoles",
    "name": "Cuerpo completo B",
    "warmup": "10 min: cinta andando llana y movilidad general.",
    "exercises": [
     {
      "name": "Sentadilla a cajón",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Cajón alto al inicio; levántate sin balanceo."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Pecho alto y tirón fluido."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Empuja sin encoger los hombros."
     },
     {
      "name": "Abducción de cadera en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Pausa breve con las rodillas abiertas."
     },
     {
      "name": "Puente de glúteos",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Aprieta glúteo arriba sin arquear la lumbar."
     },
     {
      "name": "Bird dog",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Estable y lento, sin prisa."
     }
    ],
    "cooldown": "5 min de estiramientos suaves y respiración."
   },
   {
    "day": "Viernes",
    "name": "Cuerpo completo C",
    "warmup": "10 min: bici y activación de glúteo con banda.",
    "exercises": [
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Cajón bajo; baja despacio, sin dejarte caer."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tronco quieto, codos hacia atrás."
     },
     {
      "name": "Cruce de poleas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Movimiento controlado sin tirones."
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Extiende la cadera por completo con glúteo."
     },
     {
      "name": "Face pull en polea",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Abre el pecho al final del tirón."
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 2,
      "rep_range": "30-40s",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Camina erguida con el abdomen firme."
     }
    ],
    "cooldown": "5 min de caminata suave y estiramientos."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: cargas cómodas y cero dolor articular",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "El objetivo es acabar cada sesión con buenas sensaciones."
   },
   {
    "week": 2,
    "intent": "Progresión suave en máquinas",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Sube el escalón mínimo de placa cuando sea fácil."
   },
   {
    "week": 3,
    "intent": "Carga moderada consolidando el hábito",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "Puede añadirse 1 serie a prensa y remo."
   },
   {
    "week": 4,
    "intent": "Descarga articular y de fatiga",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Menos series; mantén los paseos diarios."
   }
  ],
  "cardio": {
   "daily_steps": 7000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 3,
     "notes": "Bici estática o caminata llana con buen calzado; nada de saltos ni carrera."
    }
   ]
  },
  "deload_instructions": "Semana 4: baja un 10 % la carga y una serie por ejercicio. Si una articulación duele más de 24 h tras entrenar, se reduce el rango o la carga de ese patrón y se avisa al coach."
 },
 {
  "category": "salud_espalda",
  "title": "Simetría y core para escoliosis",
  "case": "Mujer de 24 años, estudiante con escoliosis leve diagnosticada y sin dolor limitante. Quiere ganar fuerza general con trabajo unilateral que equilibre ambos lados.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body unilateral 3 días",
  "split_rationale": "El énfasis unilateral y el core antirrotación reparten carga simétrica entre hemicuerpos, clave en escoliosis, dentro de un cuerpo completo eficiente.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Full body A",
    "warmup": "10 min: movilidad de columna en todos los planos y activación de core.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Reparte el peso por igual entre ambos pies."
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Mismo peso y repeticiones en ambos lados."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Empuje simétrico; vigila que un lado no domine."
     },
     {
      "name": "Jalón unilateral en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tira sin inclinar el tronco hacia un lado."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 45,
      "technique_cue": "Trabaja ambos lados; anota si uno cuesta más."
     },
     {
      "name": "Plancha lateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2-3",
      "rest_sec": 45,
      "technique_cue": "Mismo tiempo por lado, cadera alta."
     }
    ],
    "cooldown": "5 min de estiramiento suave y respiración costal a ambos lados."
   },
   {
    "day": "Miércoles",
    "name": "Full body B",
    "warmup": "10 min: bici suave, movilidad de cadera y activación escapular.",
    "exercises": [
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Cargas iguales en ambas manos, espalda larga."
     },
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Alterna la pierna de inicio en cada serie."
     },
     {
      "name": "Remo en polea a una mano",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tronco firme, sin rotar al tirar."
     },
     {
      "name": "Press de hombro unilateral con mancuerna de pie",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Core activo para no inclinarte al empujar."
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 3,
      "rep_range": "30-40s",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Hombros nivelados pese a la carga en un lado."
     },
     {
      "name": "Bird dog",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Extiende sin que la pelvis rote."
     }
    ],
    "cooldown": "5 min de movilidad torácica y estiramientos suaves."
   },
   {
    "day": "Viernes",
    "name": "Full body C",
    "warmup": "10 min: remo suave y movilidad completa de columna.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Empuje igual con ambas piernas."
     },
     {
      "name": "Sentadilla búlgara",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Mismo volumen por pierna, tronco estable."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tirón simétrico con pecho alto."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Codos altos, escápulas activas."
     },
     {
      "name": "Leñador en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Gira desde el tronco con brazos casi rectos."
     },
     {
      "name": "Dead bug",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Lumbar apoyada, control absoluto."
     }
    ],
    "cooldown": "5 min de respiración dirigida al lado convexo y estiramientos."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: detectar asimetrías de fuerza y control",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Anota diferencias entre lados en cada unilateral."
   },
   {
    "week": 2,
    "intent": "Progresión igualando el lado más débil",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "El lado fuerte no progresa hasta que el débil lo alcance."
   },
   {
    "week": 3,
    "intent": "Carga: semana más exigente con simetría mantenida",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Puede añadirse 1 serie de core antirrotación."
   },
   {
    "week": 4,
    "intent": "Descarga y reevaluación de asimetrías",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Menos series; compara sensaciones entre lados."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Caminata o natación suave si le resulta cómoda."
    }
   ]
  },
  "deload_instructions": "Semana 4: baja un 10 % la carga y una serie por ejercicio. Si aparece dolor de espalda nuevo o progresivo, se revisa la técnica y se consulta con su traumatólogo."
 },
 {
  "category": "salud_espalda",
  "title": "Abrir el pecho, ganar postura",
  "case": "Hombre de 27 años, opositor que estudia muchas horas encorvado y presenta cifosis postural marcada sin dolor. Quiere estética, fuerza y sobre todo enderezar su postura.",
  "level": "intermediate",
  "days_per_week": 5,
  "place": "gym",
  "split_name": "Torso-Pierna con prioridad de espalda",
  "split_rationale": "Cinco días con ratio de tracción a empuje 2:1, mucho trabajo de espalda alta y rotadores, más dos días de pierna, corrigen el patrón cifótico sin descuidar nada.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Espalda y tracción",
    "warmup": "10 min: movilidad torácica en foam, band pull-apart y aproximaciones.",
    "exercises": [
     {
      "name": "Remo con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Torso firme, tira a la parte baja del pecho."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Pecho alto, clavículas hacia la barra."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Retrae escápulas antes de flexionar los codos."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Termina con manos junto a las orejas."
     },
     {
      "name": "Pájaros con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Bisagra estable, abre con el deltoides posterior."
     },
     {
      "name": "Curl de bíceps con barra EZ",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos fijos, sin balanceo."
     }
    ],
    "cooldown": "5 min de estiramiento de pectoral en marco de puerta."
   },
   {
    "day": "Martes",
    "name": "Pierna A",
    "warmup": "10 min: bici, movilidad de cadera y tobillo, aproximaciones en sentadilla.",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Barra sobre trapecios con pecho alto y torso firme."
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Cadera atrás, espalda larga en todo el rango."
     },
     {
      "name": "Zancadas caminando con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Torso erguido, mirada al frente."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Excéntrica de 3 segundos."
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Pausa arriba, estiramiento completo abajo."
     }
    ],
    "cooldown": "5 min de estiramiento de cuádriceps e isquios."
   },
   {
    "day": "Miércoles",
    "name": "Empuje y espalda alta",
    "warmup": "10 min: movilidad escapular y rotadores con banda ligera.",
    "exercises": [
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Escápulas retraídas sobre el banco."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Empuja sin proyectar la cabeza al frente."
     },
     {
      "name": "Band pull-apart",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Abre apretando escápulas, hombros abajo."
     },
     {
      "name": "Contractora invertida",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Abre hasta sentir el deltoides posterior."
     },
     {
      "name": "Rotación externa de hombro en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Codo pegado, giro lento y completo."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos quietos junto al torso."
     }
    ],
    "cooldown": "5 min de estiramiento de pectoral y movilidad torácica."
   },
   {
    "day": "Viernes",
    "name": "Pierna B",
    "warmup": "10 min: bici y movilidad completa de cadera.",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Pecho alto al despegar, empuja el suelo."
     },
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Baja controlado sin levantar la pelvis."
     },
     {
      "name": "Sentadilla búlgara",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tronco erguido, desciende vertical."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Ajusta el respaldo y controla la vuelta."
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Rango completo con pausa arriba."
     }
    ],
    "cooldown": "5 min de estiramientos de pierna y respiración."
   },
   {
    "day": "Sábado",
    "name": "Tracción y core",
    "warmup": "10 min: movilidad general y activación escapular con banda.",
    "exercises": [
     {
      "name": "Dominadas neutras",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Pecho hacia la barra, sin encoger hombros."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Aprieta 1 segundo la contracción final."
     },
     {
      "name": "Jalón con brazos rectos en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Brazos casi rectos, baja la barra con el dorsal."
     },
     {
      "name": "Elevación lateral en polea unilateral",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Sube sin inclinar el tronco."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "40-60s",
      "rir": "2-3",
      "rest_sec": 45,
      "technique_cue": "Glúteo y abdomen firmes, sin hundir cadera."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 45,
      "technique_cue": "Postura alta mientras resistes el giro."
     }
    ],
    "cooldown": "5 min de estiramiento de pectoral y dorsal."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: asentar técnica con el nuevo énfasis de tracción",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Domina la retracción escapular en todos los tirones."
   },
   {
    "week": 2,
    "intent": "Progresión de cargas en remos y jalones",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "La espalda progresa primero; los presses acompañan."
   },
   {
    "week": 3,
    "intent": "Carga: semana más pesada del ciclo",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Puede añadirse 1 serie a remo con barra y dominadas."
   },
   {
    "week": 4,
    "intent": "Descarga para consolidar",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Una serie menos por ejercicio; mantén face pull y pull-apart."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 2,
     "notes": "Caminata con postura activa; pausas de estudio cada 50 minutos con 10 pull-apart."
    }
   ]
  },
  "deload_instructions": "Semana 4: reduce un 10 % la carga y una serie por ejercicio, manteniendo el trabajo ligero de espalda alta a diario. La postura mejora con constancia, no con semanas heroicas."
 },
 {
  "category": "salud_espalda",
  "title": "Codo tranquilo, entreno completo",
  "case": "Hombre de 36 años, carpintero con tendinopatía en el codo derecho que se irrita con agarres intensos y extensiones bruscas. Quiere mantener su fuerza sin inflamar el codo.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Torso - Pierna - Full body",
  "split_rationale": "Reparte el trabajo de brazo en dos días con ejercicios de codo amigables y agarres neutros, dejando un día de pierna para progresar sin comprometer el codo.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Torso A",
    "warmup": "10 min: movilidad de muñeca y codo sin dolor, activación escapular.",
    "exercises": [
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Agarre firme pero sin estrangular la mancuerna."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Tira con la espalda, agarre relajado."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Empuje fluido sin bloquear codos de golpe."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Usa agarre que no provoque molestia en el codo."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Carga ligera, extensión suave sin latigazo final."
     },
     {
      "name": "Curl martillo",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Agarre neutro; para si aparece dolor puntual."
     }
    ],
    "cooldown": "5 min de estiramiento suave de antebrazo sin dolor."
   },
   {
    "day": "Miércoles",
    "name": "Pierna",
    "warmup": "10 min: bici, movilidad de cadera y aproximaciones en sentadilla.",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "La barra descansa en el trapecio, no en las manos."
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Usa agarre mixto o straps si el codo protesta."
     },
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Empuja con talones, pelvis apoyada."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Control excéntrico marcado."
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Pausa arriba y abajo de 1 segundo."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2-3",
      "rest_sec": 45,
      "technique_cue": "Apoya antebrazos para descargar muñecas y codos."
     }
    ],
    "cooldown": "5 min de estiramiento de pierna y respiración."
   },
   {
    "day": "Viernes",
    "name": "Full body",
    "warmup": "10 min: movilidad general y calentamiento específico de antebrazo.",
    "exercises": [
     {
      "name": "Dominadas neutras",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "El agarre neutro protege el codo; baja controlado."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Recorrido completo sin rebotes."
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Codo cerca del cuerpo al tirar."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Agarre suave sobre la cuerda."
     },
     {
      "name": "Patada de tríceps con mancuerna",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Peso ligero, extiende sin sacudida."
     },
     {
      "name": "Curl alterno con mancuernas",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Gira la muñeca solo si no molesta."
     }
    ],
    "cooldown": "5 min de estiramiento suave de flexoextensores de muñeca."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: identificar agarres y cargas que el codo tolera",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Molestia máxima aceptable 3/10 que cede al acabar."
   },
   {
    "week": 2,
    "intent": "Progresión en pierna y espalda; brazo estable",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "El trabajo directo de brazo mantiene cargas ligeras."
   },
   {
    "week": 3,
    "intent": "Carga en ejercicios grandes con codo controlado",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Sube sentadilla y remo; el codo solo si va bien 2 semanas."
   },
   {
    "week": 4,
    "intent": "Descarga tendinosa",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Menos series de tirón y de brazo; el tendón agradece la pausa."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Caminata o bici; evita remoergómetro mientras el codo esté sensible."
    }
   ]
  },
  "deload_instructions": "Semana 4: reduce un 10 % la carga y una serie por ejercicio, en especial en tirones y trabajo de brazo. Si el dolor de codo despierta por la noche o empeora semana a semana, se deriva a fisioterapia."
 },
 {
  "category": "salud_espalda",
  "title": "Pisar sin dolor",
  "case": "Mujer de 44 años, enfermera que pasa el turno de pie y sufre fascitis plantar en el pie derecho. Necesita mantener su fuerza sin impacto y fortalecer pie y gemelo con criterio.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Inferior - Torso - Full body sin impacto",
  "split_rationale": "Dos estímulos de pierna sin impacto con gemelo en posiciones descargadas y un día de torso mantienen todo el cuerpo mientras el pie se desensibiliza.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Inferior sin impacto",
    "warmup": "10 min: bici suave y movilidad de tobillo y dedos del pie sin dolor.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Empuja con el mediopié, sin dolor en la planta."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Control total de la fase de bajada."
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Talones firmes, extiende con glúteo."
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Subida lenta de 3 segundos; carga progresiva sin dolor agudo."
     },
     {
      "name": "Elevación de puntas (tibial anterior)",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 45,
      "technique_cue": "Sube las puntas con talón apoyado."
     },
     {
      "name": "Dead bug",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Lumbar apoyada y ritmo lento."
     }
    ],
    "cooldown": "5 min de automasaje plantar con pelota y estiramiento suave de gemelo."
   },
   {
    "day": "Miércoles",
    "name": "Torso",
    "warmup": "8-10 min: remo suave con poca presión en el pie y movilidad escapular.",
    "exercises": [
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Escápulas fijas sobre el banco."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Tronco quieto, tirón limpio."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho alto hacia la barra."
     },
     {
      "name": "Elevación lateral en polea unilateral",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Sube controlado hasta la horizontal."
     },
     {
      "name": "Curl de bíceps con barra EZ",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos pegados al torso."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Extensión completa sin mover los hombros."
     }
    ],
    "cooldown": "5 min de estiramientos de torso; sentada, descarga el pie."
   },
   {
    "day": "Viernes",
    "name": "Full body sin impacto",
    "warmup": "10 min: bici y movilidad general; nada de saltos ni trote.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Peso repartido en todo el pie, sin dolor plantar."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Bisagra de cadera con espalda larga."
     },
     {
      "name": "Abducción de cadera en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Pausa en la apertura, vuelta controlada."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Aprieta la espalda al final del tirón."
     },
     {
      "name": "Elevación de talones en prensa",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Rango que no despierte la planta; progresa despacio."
     },
     {
      "name": "Plancha lateral",
      "sets": 2,
      "rep_range": "30-45s",
      "rir": "2-3",
      "rest_sec": 45,
      "technique_cue": "Cadera alta y cuerpo alineado."
     }
    ],
    "cooldown": "5 min de estiramiento de cadena posterior y planta del pie."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: cargar el gemelo sin irritar la fascia",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Dolor matinal del pie como termómetro: no debe aumentar."
   },
   {
    "week": 2,
    "intent": "Progresión en pierna y gemelo sentado",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Sube carga en prensa y gemelos si la planta responde bien."
   },
   {
    "week": 3,
    "intent": "Carga: semana más fuerte, todavía sin impacto",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Nada de saltos ni carrera aunque haya mejoría."
   },
   {
    "week": 4,
    "intent": "Descarga del tejido plantar",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Menos series de gemelo; mantén el automasaje diario."
   }
  ],
  "cardio": {
   "daily_steps": 5000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 3,
     "notes": "Bici o elíptica en lugar de caminatas largas mientras la fascia esté sensible; calzado con buena amortiguación en el trabajo."
    }
   ]
  },
  "deload_instructions": "Semana 4: baja un 10 % la carga y una serie por ejercicio, en especial en gemelos. Si el dolor del primer paso matinal empeora dos semanas seguidas, se deriva a fisioterapia o podología."
 },
 {
  "category": "salud_espalda",
  "title": "Entrenar para dormir mejor",
  "case": "Hombre de 39 años, directivo con estrés alto, sueño irregular y poco tiempo, que entrena en casa con mancuernas y bandas. Necesita un estímulo eficaz que no le dispare más el estrés.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "home",
  "split_name": "Full body breve 3 días",
  "split_rationale": "Sesiones completas de unos 40 minutos con volumen moderado dan estímulo suficiente sin añadir carga de estrés, y la regularidad ayuda al sueño.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Full body A",
    "warmup": "8 min: movilidad general y 2 series de aproximación en sentadilla.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Baja controlado, sube con intención."
     },
     {
      "name": "Flexiones",
      "sets": 3,
      "rep_range": "10-15",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cuerpo en tabla, codos a 45 grados."
     },
     {
      "name": "Remo con banda sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Tira con la espalda, pausa breve atrás."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadera atrás y mancuernas rozando las piernas."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2-3",
      "rest_sec": 45,
      "technique_cue": "Respira de forma continua durante el apoyo."
     }
    ],
    "cooldown": "5 min de respiración 4-7-8 tumbado; ideal como transición a la noche."
   },
   {
    "day": "Miércoles",
    "name": "Full body B",
    "warmup": "8 min: movilidad de cadera y hombro con banda ligera.",
    "exercises": [
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Paso atrás firme, torso erguido."
     },
     {
      "name": "Remo invertido bajo una mesa",
      "sets": 3,
      "rep_range": "8-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho al borde de la mesa, cuerpo recto."
     },
     {
      "name": "Press de hombro con banda",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Empuja vertical sin arquear la lumbar."
     },
     {
      "name": "Puente de glúteo a una pierna",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Pelvis nivelada durante toda la serie."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Movimiento lento sincronizado con la exhalación."
     }
    ],
    "cooldown": "5 min de estiramientos suaves y respiración nasal lenta."
   },
   {
    "day": "Viernes",
    "name": "Full body C",
    "warmup": "8 min: movilidad general y activación de glúteo y escápula.",
    "exercises": [
     {
      "name": "Peso muerto rumano a una pierna",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadera cuadrada, espalda larga."
     },
     {
      "name": "Press de pecho con banda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Empuje completo sin encoger hombros."
     },
     {
      "name": "Jalón con banda de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos a las costillas, pecho alto."
     },
     {
      "name": "Face pull con banda",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "2-3",
      "rest_sec": 45,
      "technique_cue": "Abre las manos al final apretando la espalda alta."
     },
     {
      "name": "Plancha lateral",
      "sets": 2,
      "rep_range": "30-45s",
      "rir": "2-3",
      "rest_sec": 45,
      "technique_cue": "Cadera alta y respiración fluida."
     }
    ],
    "cooldown": "5 min de respiración diafragmática; pantallas fuera 60 min antes de dormir."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: encajar el entreno en la agenda sin fricción",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Mejor 40 minutos constantes que sesiones épicas aisladas."
   },
   {
    "week": 2,
    "intent": "Progresión ligera si el sueño se mantiene o mejora",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Sube carga o repeticiones, no duración de la sesión."
   },
   {
    "week": 3,
    "intent": "Carga: semana más intensa vigilando el descanso",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Si duerme mal 3 noches seguidas, repite cargas de semana 2."
   },
   {
    "week": 4,
    "intent": "Descarga: recuperar y consolidar el hábito",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Menos series y más paseos al aire libre."
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Paseo a ritmo cómodo, mejor a primera hora con luz natural; evita cardio intenso por la noche."
    }
   ]
  },
  "deload_instructions": "Semana 4: reduce un 10 % la carga y una serie por ejercicio. El sueño manda: si empeora de forma sostenida, se recorta volumen antes que abandonar la rutina."
 },
 {
  "category": "salud_espalda",
  "title": "Progresión amable en fibromialgia",
  "case": "Mujer de 47 años, administrativa con fibromialgia leve diagnosticada que sufre brotes de fatiga si se pasa de intensidad. Quiere ganar fuerza con una progresión muy gradual en casa.",
  "level": "beginner",
  "days_per_week": 2,
  "place": "home",
  "split_name": "Full body suave 2 días",
  "split_rationale": "Dos sesiones cortas de cuerpo completo con cargas bajas y mucho margen dejan 72 horas de recuperación y minimizan el riesgo de brote post esfuerzo.",
  "sessions": [
   {
    "day": "Martes",
    "name": "Cuerpo completo A",
    "warmup": "10 min: movilidad articular muy suave y caminata en casa.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "4",
      "rest_sec": 90,
      "technique_cue": "Carga simbólica al inicio; técnica cómoda y fluida."
     },
     {
      "name": "Remo con banda sentado",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "4",
      "rest_sec": 60,
      "technique_cue": "Tirón suave, hombros relajados."
     },
     {
      "name": "Press de pecho con banda",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "4",
      "rest_sec": 60,
      "technique_cue": "Empuje cómodo sin llegar a temblar."
     },
     {
      "name": "Puente de glúteo",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3-4",
      "rest_sec": 60,
      "technique_cue": "Sube sin prisa y aprieta glúteo arriba."
     },
     {
      "name": "Dead bug",
      "sets": 2,
      "rep_range": "6-8",
      "rir": "4",
      "rest_sec": 60,
      "technique_cue": "Pocas repeticiones y muy controladas."
     }
    ],
    "cooldown": "5-8 min de respiración lenta y estiramientos globales suaves."
   },
   {
    "day": "Viernes",
    "name": "Cuerpo completo B",
    "warmup": "10 min: movilidad suave de columna y cadera, respiración diafragmática.",
    "exercises": [
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "4",
      "rest_sec": 90,
      "technique_cue": "Mancuernas ligeras, espalda larga."
     },
     {
      "name": "Jalón con banda de pie",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "4",
      "rest_sec": 60,
      "technique_cue": "Tira sin tensar el cuello."
     },
     {
      "name": "Elevación lateral con banda",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "4",
      "rest_sec": 60,
      "technique_cue": "Sube solo hasta donde sea cómodo."
     },
     {
      "name": "Face pull con banda",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "4",
      "rest_sec": 60,
      "technique_cue": "Movimiento amable, abre el pecho."
     },
     {
      "name": "Bird dog",
      "sets": 2,
      "rep_range": "6-8",
      "rir": "4",
      "rest_sec": 60,
      "technique_cue": "Equilibrio tranquilo, sin exigencia."
     }
    ],
    "cooldown": "5-8 min de estiramientos suaves generales y respiración."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: dosis mínima eficaz sin despertar síntomas",
    "load_pct": 100,
    "rir_target": "4",
    "volume_note": "Debe terminar con sensación de poder hacer más."
   },
   {
    "week": 2,
    "intent": "Progresión mínima solo si la semana 1 no dio brote",
    "load_pct": 102.5,
    "rir_target": "4",
    "volume_note": "Sube 1-2 repeticiones por serie, no la carga."
   },
   {
    "week": 3,
    "intent": "Consolidar: pequeño aumento de carga si todo va bien",
    "load_pct": 105,
    "rir_target": "3-4",
    "volume_note": "Si hay fatiga inusual, repetir semana 2 sin culpa."
   },
   {
    "week": 4,
    "intent": "Descarga profunda",
    "load_pct": 90,
    "rir_target": "4-5",
    "volume_note": "Solo movilidad, paseos y las series que apetezcan."
   }
  ],
  "cardio": {
   "daily_steps": 6000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 20,
     "times_per_week": 3,
     "notes": "Paseo suave a ritmo agradable; fraccionable en dos tramos de 10 minutos."
    }
   ]
  },
  "deload_instructions": "Semana 4: la mitad de series y cargas un 10 % menores. Regla general del mes: nunca terminar agotada; si un brote aparece, se reduce todo a movilidad y paseos hasta que remita."
 },
 {
  "category": "salud_espalda",
  "title": "Equilibrio y autonomía después de los 65",
  "case": "Hombre de 67 años, jubilado que vive solo, sin patología relevante pero con pérdida de equilibrio y fuerza al subir escaleras. Quiere entrenar en casa para mantener su autonomía.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "home",
  "split_name": "Full body funcional 3 días",
  "split_rationale": "Tres sesiones completas centradas en piernas, equilibrio y patrones cotidianos (sentarse, levantarse, cargar) sostienen la autonomía con material mínimo.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Funcional A",
    "warmup": "8-10 min: marcha en el sitio, movilidad de cadera y tobillo con apoyo.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Como sentarse en una silla; usa una si da seguridad."
     },
     {
      "name": "Remo con banda sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Espalda erguida, tira sin encoger hombros."
     },
     {
      "name": "Press de pecho con banda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Empuje estable y controlado."
     },
     {
      "name": "Puente de glúteo",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Aprieta glúteo arriba 1 segundo."
     },
     {
      "name": "Elevación de gemelo a una pierna en escalón",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Sujétate a la barandilla; sube y baja despacio."
     },
     {
      "name": "Dead bug",
      "sets": 2,
      "rep_range": "6-8",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Movimiento lento con la lumbar apoyada."
     }
    ],
    "cooldown": "5 min de paseo por casa y estiramientos suaves de pierna."
   },
   {
    "day": "Miércoles",
    "name": "Funcional B",
    "warmup": "8-10 min: movilidad general y equilibrio a un pie junto a la pared.",
    "exercises": [
     {
      "name": "Zancada estática",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Mano en la pared si hace falta; torso erguido."
     },
     {
      "name": "Jalón con banda de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Codos hacia abajo, pecho abierto."
     },
     {
      "name": "Elevación lateral con banda",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Sube hasta la altura del hombro sin prisa."
     },
     {
      "name": "Peso muerto rumano a una pierna sin carga",
      "sets": 2,
      "rep_range": "6-8",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Apoya la mano libre; es un ejercicio de equilibrio."
     },
     {
      "name": "Bird dog",
      "sets": 2,
      "rep_range": "6-8",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Estable y lento; calidad ante todo."
     }
    ],
    "cooldown": "5 min de respiración tranquila y movilidad de columna."
   },
   {
    "day": "Viernes",
    "name": "Funcional C",
    "warmup": "8-10 min: marcha, movilidad y dos levantadas de silla de prueba.",
    "exercises": [
     {
      "name": "Sentadilla a una pierna al cajón asistida",
      "sets": 2,
      "rep_range": "5-6",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Baja despacio al asiento apoyándote en el respaldo."
     },
     {
      "name": "Face pull con banda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Abre el pecho, mirada al frente."
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 2,
      "rep_range": "20-30s",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Como llevar la compra: erguido y con pasos firmes."
     },
     {
      "name": "Elevación de puntas (tibial anterior)",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Fortalece el tobillo para no tropezar."
     },
     {
      "name": "Puente de glúteo a una pierna",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Pelvis nivelada; si cuesta, vuelve a dos piernas."
     }
    ],
    "cooldown": "5 min de estiramientos suaves y respiración."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: seguridad y confianza en cada ejercicio",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Todo con apoyo disponible; ninguna serie hasta el límite."
   },
   {
    "week": 2,
    "intent": "Progresión de repeticiones antes que de carga",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Añade 1-2 repeticiones donde se sienta seguro."
   },
   {
    "week": 3,
    "intent": "Carga ligera y menos asistencia en el equilibrio",
    "load_pct": 105,
    "rir_target": "3",
    "volume_note": "Reduce el apoyo de la mano solo si no hay inestabilidad."
   },
   {
    "week": 4,
    "intent": "Descarga activa",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Menos series; mantén los paseos y el equilibrio diario."
   }
  ],
  "cardio": {
   "daily_steps": 6000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 3,
     "notes": "Paseo diario por terreno conocido; un tramo de escaleras con barandilla cuenta como entreno."
    }
   ]
  },
  "deload_instructions": "Semana 4: reduce una serie por ejercicio y la carga un 10 %. Ante mareo, pérdida de equilibrio nueva o dolor articular persistente, se pausa y se comenta con su médico de cabecera."
 },
 {
  "category": "salud_espalda",
  "title": "Primeros pasos sin mareos",
  "case": "Hombre de 21 años, estudiante muy sedentario que nota mareos al esforzarse y al incorporarse rápido, con revisión médica normal. Necesita empezar desde cero con progresión mínima.",
  "level": "beginner",
  "days_per_week": 2,
  "place": "gym",
  "split_name": "Full body 2 días de iniciación",
  "split_rationale": "Dos sesiones en máquinas, mayormente sentado, con cambios de postura lentos y cargas muy suaves construyen tolerancia al esfuerzo sin provocar mareos.",
  "sessions": [
   {
    "day": "Martes",
    "name": "Iniciación A",
    "warmup": "10 min: bici estática empezando muy suave, subiendo el ritmo de forma gradual.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3-4",
      "rest_sec": 120,
      "technique_cue": "Respira en cada repetición; nada de apneas."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3-4",
      "rest_sec": 120,
      "technique_cue": "Carga ligera y ritmo constante."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3-4",
      "rest_sec": 120,
      "technique_cue": "Tira exhalando, tronco estable."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3-4",
      "rest_sec": 90,
      "technique_cue": "Movimiento suave sin tirones."
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 2,
      "rep_range": "15-20",
      "rir": "3-4",
      "rest_sec": 60,
      "technique_cue": "Bombea tranquilo; te levantas despacio al acabar."
     }
    ],
    "cooldown": "8 min de bici muy suave; incorpórate despacio y bebe agua."
   },
   {
    "day": "Viernes",
    "name": "Iniciación B",
    "warmup": "10 min: cinta andando con incremento gradual de ritmo.",
    "exercises": [
     {
      "name": "Jalón al pecho",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3-4",
      "rest_sec": 120,
      "technique_cue": "Tirón suave a la clavícula, exhalando."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3-4",
      "rest_sec": 120,
      "technique_cue": "Empuja sin retener el aire ni apretar la mandíbula."
     },
     {
      "name": "Sentadilla goblet",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "3-4",
      "rest_sec": 120,
      "technique_cue": "Mancuerna muy ligera; sube sin impulso brusco."
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3-4",
      "rest_sec": 90,
      "technique_cue": "Extiende la cadera exhalando."
     },
     {
      "name": "Dead bug",
      "sets": 2,
      "rep_range": "6-8",
      "rir": "4",
      "rest_sec": 60,
      "technique_cue": "Lento; levántate del suelo por fases, sin prisa."
     }
    ],
    "cooldown": "8 min de caminata suave decreciente y respiración lenta."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: terminar cada sesión sin mareo ni agobio",
    "load_pct": 100,
    "rir_target": "4",
    "volume_note": "Cargas casi simbólicas; el objetivo es tolerar la sesión."
   },
   {
    "week": 2,
    "intent": "Progresión mínima de repeticiones",
    "load_pct": 102.5,
    "rir_target": "3-4",
    "volume_note": "Añade 1-2 repeticiones si no hubo síntomas."
   },
   {
    "week": 3,
    "intent": "Primer aumento suave de carga",
    "load_pct": 105,
    "rir_target": "3",
    "volume_note": "Sube el escalón mínimo de placa en 2-3 máquinas."
   },
   {
    "week": 4,
    "intent": "Descarga y valoración de tolerancia",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Menos series; si el mes cursó limpio, se planifica subir a 3 días."
   }
  ],
  "cardio": {
   "daily_steps": 6000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 20,
     "times_per_week": 3,
     "notes": "Caminata o bici muy suave con inicio y final graduales; hidratación y comida previa ligera."
    }
   ]
  },
  "deload_instructions": "Semana 4: reduce un 10 % la carga y una serie por ejercicio. Levantarse siempre despacio entre ejercicios; si aparece mareo, sentarse, hidratarse y dar por buena la sesión. Si los mareos persisten o van a más, se vuelve a derivar al médico."
 }
]
