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
  "title": "Fuerza · base con los básicos, 3 días",
  "case": "Para quien empieza con la barra y quiere construir base en sentadilla, press y peso muerto.",
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
  "title": "Fuerza · programación 4 días para estancados",
  "case": "Para el intermedio estancado en los básicos que quiere una programación clara de cuatro días.",
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
  "title": "Fuerza · oposiciones (carrera, dominadas y press)",
  "case": "Para quien prepara pruebas físicas y debe rendir en carrera, dominadas y fuerza a la vez.",
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
  "title": "Fuerza · iniciación al powerlifting",
  "case": "Para quien apunta a competir a medio plazo y necesita técnica y programación desde el principio.",
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
  "title": "Fuerza · complemento para corredores",
  "case": "Para quien corre varios días por semana y añade dos sesiones de fuerza sin restarle a los rodajes.",
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
     "times_per_week": 4,
     "notes": "Rodajes suaves ya previstos en su plan de carrera; aquí solo se reflejan."
    }
   ]
  },
  "deload_instructions": "Semana 4: cargas al 90 por ciento y dos series por ejercicio, coincidiendo si es posible con la semana de menos kilómetros."
 },
 {
  "category": "fuerza",
  "title": "Fuerza · complemento para pádel y tenis",
  "case": "Para quien juega varios días por semana y busca potencia y prevención en dos sesiones.",
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
  "title": "Fuerza · bloque de invierno para ciclistas",
  "case": "Para quien pedalea y quiere dos días de fuerza para subir vatios y proteger la espalda.",
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
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Bloqueo de cadera con el glúteo: los vatios salen de aquí, no de más cuádriceps."
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
  "title": "Fuerza · a partir de los 40",
  "case": "Para quien entrenó de joven, vuelve pasados los 40 y quiere fuerza sin castigar articulaciones.",
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
  "title": "Fuerza · solo 2 días",
  "case": "Para quien únicamente puede pisar el gimnasio dos veces por semana.",
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
  "title": "Fuerza · mixta con hipertrofia, 4 días",
  "case": "Para quien quiere subir los básicos sin renunciar a ganar masa muscular.",
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
  "title": "Fuerza · objetivo primeras dominadas",
  "case": "Para quien apenas saca una dominada y quiere llegar a varias estrictas.",
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
  "title": "Fuerza · especialización en press banca",
  "case": "Para quien tiene la banca estancada y quiere un bloque específico de empuje.",
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
  "title": "Fuerza · en casa con mancuernas y bandas",
  "case": "Para quien no quiere pisar un gimnasio y entrena en casa con material básico.",
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
  "title": "Fuerza · pretemporada de deportes de equipo",
  "case": "Para quien entrena con su equipo y compite el fin de semana: fuerza sin llegar cargado al partido.",
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
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Trabajo de isquios sin daño excéntrico máximo: el partido manda."
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
  "title": "Fuerza · cuidando el hombro",
  "case": "Para quien nota el hombro en press por encima de la cabeza y en banca profunda.",
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
  "title": "Fuerza · cuidando la zona lumbar",
  "case": "Para quien ha tenido lumbalgia y quiere entrenar fuerte respetando la columna.",
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
  "title": "Fuerza · fuerte y firme, sin ganar volumen",
  "case": "Para quien quiere verse fuerte y firme y teme que las pesas la pongan grande.",
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
  "title": "Fuerza · complemento para escalada",
  "case": "Para quien escala varios días y busca tirón, core y prevención en dos sesiones.",
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
  "title": "Fuerza · potencia y salto",
  "case": "Para quien quiere saltar más y ganar arranque en deportes de equipo.",
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
  "title": "Fuerza · funcional a partir de los 55",
  "case": "Para quien busca subir escaleras sin fatiga y cargar peso del día a día con seguridad.",
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
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Empuja con el glúteo y aprieta un segundo arriba: es lo que te levanta de la silla y sube la cadera al cargar peso."
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
  "title": "Ganar músculo · desde cero",
  "case": "Para quien empieza de cero y quiere ganar músculo con una estructura sencilla de aprender.",
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
  "title": "Ganar músculo · romper el estancamiento",
  "case": "Para el intermedio que lleva meses sin progresar y necesita alternar fuerza y volumen.",
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
  "title": "Ganar músculo · avanzado, 5 días",
  "case": "Para el avanzado que dispone de cinco días y busca un bloque de alta frecuencia.",
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
  "title": "Ganar músculo · prioridad glúteo y pierna",
  "case": "Para quien quiere centrar el trabajo en glúteo y pierna sin descuidar el torso.",
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
  "title": "Ganar músculo · a partir de los 50",
  "case": "Para quien pasa de los 50 y quiere ganar masa cuidando articulaciones y hueso.",
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
  "title": "Ganar músculo · solo 2 días",
  "case": "Para quien solo puede entrenar dos días y necesita el máximo estímulo por sesión.",
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
      "name": "Sentadilla goblet",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 150,
      "technique_cue": "Mancuerna vertical al pecho, torso alto; aprende el patrón antes de pasar a la barra."
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
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Pecho apoyado y sin despegarlo: la espalda trabaja sin cargar la lumbar."
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
  "title": "Ganar músculo · prioridad torso",
  "case": "Para quien tiene la pierna adelantada y quiere igualar el tren superior.",
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
  "title": "Ganar músculo · espalda más ancha",
  "case": "Para quien busca amplitud de espalda manteniendo el resto en proporción.",
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
  "title": "Ganar músculo · brazos rezagados",
  "case": "Para quien tiene los brazos por detrás del resto y necesita doble estímulo semanal.",
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
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Codos hacia los bolsillos; mantiene la espalda mientras priorizamos el brazo."
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
  "title": "Ganar músculo · full body, 3 días",
  "case": "Para quien quiere músculo y fuerza general con tres sesiones completas y sin complicaciones.",
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
  "title": "Ganar músculo · torso-pierna, 4 días",
  "case": "Para quien tiene cuatro días fijos y quiere la estructura clásica y sostenible.",
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
  "title": "Ganar músculo · empuje, tracción y pierna",
  "case": "Para quien prefiere sesiones monotemáticas de una hora, tres veces por semana.",
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
  "title": "Ganar músculo · en casa con mancuernas",
  "case": "Para quien entrena en casa con mancuernas y bandas y quiere seguir ganando músculo.",
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
  "title": "Ganar músculo · volver tras un parón",
  "case": "Para quien ya entrenó antes, vuelve tras meses parado y quiere recuperar sin lesionarse.",
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
  "title": "Ganar músculo · cuidando la rodilla",
  "case": "Para quien nota la rodilla en flexiones profundas y quiere seguir ganando pierna.",
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
  "title": "Ganar músculo · cuidando el hombro",
  "case": "Para quien le molesta el hombro en los presses por encima de la cabeza.",
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
  "title": "Ganar músculo · horario imprevisible, en casa",
  "case": "Para quien no puede fijar días: dos sesiones intercambiables en casa con material básico.",
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
  "title": "Ganar músculo · sesiones de 45 minutos",
  "case": "Para quien solo dispone de huecos de 45 minutos y quiere aprovecharlos al máximo.",
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
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Mancuerna al pecho y torso alto; con poco tiempo, prioriza el patrón limpio."
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
  "title": "Ganar músculo · con trabajo cardiovascular",
  "case": "Para quien quiere ganar músculo y a la vez cuidar el corazón y la analítica.",
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
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadera atrás y espalda neutra; baja hasta notar el estiramiento detrás del muslo."
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
  "title": "Ganar músculo · prioridad pierna",
  "case": "Para el avanzado con el torso adelantado que necesita poner la pierna al día.",
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
    "rir_target": "1-2",
    "volume_note": "Semana fuerte, pero el peso muerto se queda en RIR 2: nunca al fallo con la barra en la espalda."
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
  "category": "mantenimiento",
  "title": "Mantener · el físico ya conseguido",
  "case": "Para quien acaba de lograr su objetivo y quiere conservarlo sin volver al volumen de antes.",
  "level": "advanced",
  "days_per_week": 4,
  "place": "gym",
  "split_name": "Torso/Pierna x2 de mantenimiento",
  "split_rationale": "Cuatro sesiones de una hora escasa cubren cada patrón dos veces por semana, que es lo que hace falta para conservar masa y fuerza. El volumen baja alrededor de un tercio respecto a su etapa de definición y se mantiene la intensidad: así retiene el estímulo sin la carga de fatiga que le acabó quemando.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Torso A - empuje horizontal y espalda densa",
    "warmup": "5 minutos de remo suave, movilidad de hombro con banda y dos series de aproximación al primer ejercicio al 50 y al 70 por ciento.",
    "exercises": [
     {
      "name": "Press banca con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Escápulas retraídas y pies clavados; baja controlado a la línea del pezón y no rebotes en el pecho."
     },
     {
      "name": "Remo con barra",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Tronco a 45 grados y bloqueado; lleva la barra al ombligo sin dar tirones con la lumbar."
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "8-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Respaldo casi vertical, codos algo adelantados y sin arquear la zona lumbar al empujar."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho arriba y codos hacia el bolsillo; frena la subida en lugar de dejar que el peso te estire."
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Sube hasta la altura del hombro con el codo ligeramente flexionado y sin impulso de cadera."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cuerda a la altura de los ojos, separa las manos al final y aguanta medio segundo."
     }
    ],
    "cooldown": "Cinco minutos de respiración nasal tumbado y estiramiento suave de pectoral en marco de puerta."
   },
   {
    "day": "Martes",
    "name": "Pierna A - cuádriceps y cadena posterior",
    "warmup": "Bicicleta 6 minutos, movilidad de tobillo y cadera, y dos series de aproximación en sentadilla.",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Barra apoyada en el trapecio, rodillas siguiendo la punta del pie y profundidad hasta donde no se retroverse la pelvis."
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Cadera atrás con la barra pegada al muslo; para cuando el isquio ya no dé más sin redondear."
     },
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Pies a la anchura de las caderas y sin bloquear la rodilla de golpe arriba."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Cadera pegada al banco y bajada de tres segundos para aprovechar la fase excéntrica."
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo, pausa arriba de un segundo y sin rebotar abajo."
     },
     {
      "name": "Plancha con lastre",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Glúteo apretado y costillas abajo; el disco va en la zona media de la espalda."
     }
    ],
    "cooldown": "Estiramiento de psoas y cuádriceps, dos minutos por lado, y respiración lenta."
   },
   {
    "day": "Jueves",
    "name": "Torso B - inclinado y espalda en anchura",
    "warmup": "5 minutos de elíptica, band pull-apart y aproximaciones al press inclinado.",
    "exercises": [
     {
      "name": "Press inclinado con mancuernas",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Banco a 30 grados; baja hasta sentir el pectoral estirado sin que el hombro se vaya adelante."
     },
     {
      "name": "Dominadas neutras",
      "sets": 4,
      "rep_range": "6-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Arranca deprimiendo la escápula antes de doblar el codo y controla la bajada completa."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Ajusta el asiento para que las manos queden a la altura del pecho, no del cuello."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tronco quieto, que trabaje el codo; nada de balancearte para sumar kilos."
     },
     {
      "name": "Curl de bíceps con barra EZ",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos fijos al costado y sin usar la cadera para arrancar la subida."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos pegados al tronco, abre la cuerda al final del recorrido."
     }
    ],
    "cooldown": "Movilidad torácica en el rodillo, dos minutos, y estiramiento de dorsal colgado suave."
   },
   {
    "day": "Viernes",
    "name": "Pierna B - bisagra, glúteo y unilateral",
    "warmup": "Bicicleta 6 minutos, puente de glúteo sin carga y aproximaciones a la hexagonal.",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Pecho alto en la salida y empuja el suelo con el pie entero; no tires con la espalda."
     },
     {
      "name": "Sentadilla búlgara",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Pie delantero lo bastante adelante para que la rodilla no se coma el recorrido."
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Barbilla al pecho, costillas abajo y pausa de un segundo arriba con el glúteo apretado."
     },
     {
      "name": "Extensión de rodilla en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Extiende sin dar el latigazo final y baja frenando durante dos segundos."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Espalda pegada al respaldo y sin levantar la cadera para ayudarte."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Extiende los brazos sin dejar que el tronco gire hacia la polea."
     }
    ],
    "cooldown": "Estiramiento de isquios y glúteo, dos minutos por lado, y paseo suave de cinco minutos."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: recolocar cargas tras la definición, sin buscar sensaciones de etapa de volumen",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "El volumen ya está recortado un tercio respecto a su definición; no añadas series aunque se vea con fuerza de sobra."
   },
   {
    "week": 2,
    "intent": "Progresión: subir peso solo en los cuatro ejercicios principales",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismas series que la semana 1; el avance viene del kilo añadido, no de más trabajo."
   },
   {
    "week": 3,
    "intent": "Carga: semana más exigente para confirmar que no ha perdido fuerza",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Una serie extra únicamente en press banca y sentadilla; el resto se queda igual."
   },
   {
    "week": 4,
    "intent": "Descarga: bajar la carga para llegar al mes siguiente con ganas de venir",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Quita una serie de cada ejercicio accesorio y sal del centro con la sensación de que te has quedado corto."
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 3,
     "notes": "Caminar rápido o bicicleta suave los días sin pesas; el objetivo es sostener el gasto sin sumar fatiga a las piernas."
    }
   ]
  },
  "deload_instructions": "La semana 4 se entrena al 90 por ciento de la carga, con una serie menos en cada accesorio y RIR 3-4 en todo. Se mantienen los cuatro días para no romper el hábito, que en su caso es lo que más pesa. Si acumula dos semanas durmiendo mal o llega tres sesiones seguidas sin ganas, adelanta la descarga sin esperar a que toque."
 },
 {
  "category": "mantenimiento",
  "title": "Mantener · tono general, 3 días",
  "case": "Para quien quiere estar en forma con tres sesiones sencillas y sin complicaciones.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body sencillo de tres días",
  "split_rationale": "Tres sesiones de cuerpo completo con la misma estructura (pierna, tirón, empuje, glúteo, hombro y core) para que solo cambien los aparatos y nunca el guion. Así aprende el orden en dos semanas y deja de necesitar el papel en la mano.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Día A - máquinas guiadas",
    "warmup": "6 minutos de bicicleta estática a ritmo cómodo y diez sentadillas al aire sujetándose al marco.",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Pies a la anchura de las caderas y baja hasta que la rodilla forme un ángulo recto, ni más."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Siéntate erguida, lleva la barra a la clavícula y suelta despacio sin dejar que te levante."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Asiento a la altura del pecho; empuja sin bloquear el codo de golpe."
     },
     {
      "name": "Puente de glúteos",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Aprieta el glúteo arriba un segundo y evita arquear la lumbar para subir más."
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Mancuerna ligera; sube solo hasta el hombro y baja contando dos segundos."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Si te cuesta, apoya las rodillas; lo importante es que la cadera no se hunda."
     }
    ],
    "cooldown": "Cinco minutos caminando en cinta a ritmo suave y estiramiento de cuádriceps y pectoral."
   },
   {
    "day": "Miércoles",
    "name": "Día B - peso libre básico",
    "warmup": "6 minutos de elíptica y movilidad de hombro con banda ligera.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Mancuerna pegada al pecho, codos dentro y baja como si te sentaras en una silla alta."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Pecho apoyado, tira con los codos hacia atrás y junta los omóplatos al final."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Espalda pegada al respaldo; si notas el cuello, baja el peso."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Cadera pegada al banco y baja el peso frenando, sin soltarlo."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Codos pegados a las costillas; solo se mueve el antebrazo."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Lumbar pegada al suelo todo el rato; si se despega, acorta el recorrido de la pierna."
     }
    ],
    "cooldown": "Cinco minutos de bicicleta suave y estiramiento de isquios sentada."
   },
   {
    "day": "Viernes",
    "name": "Día C - patrones de vida diaria",
    "warmup": "6 minutos caminando en cinta con inclinación y diez puentes de glúteo sin carga.",
    "exercises": [
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Cajón bajo al principio; sube empujando con el pie de arriba y baja despacio, sin saltar."
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 75,
      "technique_cue": "Mirada al frente-abajo y pausa arriba de un segundo apretando el glúteo."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Rodillas algo dobladas y tronco quieto; no te vayas atrás con el peso."
     },
     {
      "name": "Contractora de pecho",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Codos a la altura del pecho y cierre suave, sin chocar los brazos."
     },
     {
      "name": "Curl alterno con mancuernas",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Un brazo cada vez, codo quieto y sin balancear el cuerpo."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Estira brazo y pierna contrarios sin que la cadera se abra hacia un lado."
     }
    ],
    "cooldown": "Cinco minutos de paseo por la sala y estiramiento global de espalda y piernas."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: aprender el orden de los aparatos y anotar los kilos de cada máquina",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Cargas conservadoras a propósito; la primera semana el objetivo es acabar sin agujetas que la asusten."
   },
   {
    "week": 2,
    "intent": "Progresión: repetir el mismo circuito subiendo una placa donde las últimas repeticiones salieron fáciles",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Mismas series; solo cambia el peso y ya se moverá sin mirar la hoja."
   },
   {
    "week": 3,
    "intent": "Carga: la semana en la que debe notar que las últimas dos repeticiones cuestan",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "Añade una serie a prensa y jalón, que son los dos ejercicios que mejor domina."
   },
   {
    "week": 4,
    "intent": "Descarga: aligerar para que el mes acabe con buena sensación y no con cansancio",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Dos series por ejercicio y sin plancha con lastre; se sale del centro con energía."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 2,
     "notes": "Paseo a buen ritmo por la Devesa o al salir del trabajo; no hace falta cinta ni ropa de deporte."
    }
   ]
  },
  "deload_instructions": "La semana 4 baja al 90 por ciento de la carga y a dos series por ejercicio, manteniendo los tres días y el mismo orden de siempre. Es la semana en la que se revisa su hoja de kilos y se comprueba que ya no necesita preguntar la regulación de ninguna máquina. Si llega alguna semana con más de dos días perdidos por trabajo, se repite la semana anterior en lugar de saltar adelante."
 },
 {
  "category": "mantenimiento",
  "title": "Mantener · tonificar sin ganar volumen",
  "case": "Para quien quiere verse definida y teme que las pesas la pongan grande.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body con énfasis en glúteo, espalda y hombro",
  "split_rationale": "Cuerpo completo tres días con más trabajo de glúteo, dorsal y deltoides lateral: son los grupos que dibujan la silueta que ella describe cuando dice definida. La carga sube de forma muy gradual porque el objetivo real es firmeza y postura, no ganar sección muscular, y así se le puede enseñar con sus propios registros que el volumen no aparece por entrenar fuerte.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Día A - cadera y espalda",
    "warmup": "5 minutos de bicicleta, activación de glúteo con banda y movilidad torácica.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Talones apoyados, pecho alto y baja hasta el punto donde la espalda siga recta."
     },
     {
      "name": "Hip thrust con barra",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pausa de un segundo arriba con el glúteo apretado y sin arquear la lumbar."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tira del codo hacia la cadera y junta los omóplatos sin encoger el hombro."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 75,
      "technique_cue": "Asiento a la altura del pecho y recorrido completo, sin bloquear el codo."
     },
     {
      "name": "Elevación lateral en polea unilateral",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Cable por detrás del cuerpo, sube hasta el hombro y baja frenando."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Cadera a la altura de los hombros y glúteo activo; nada de aguantar con la lumbar hundida."
     }
    ],
    "cooldown": "Estiramiento de glúteo y flexor de cadera, dos minutos por lado."
   },
   {
    "day": "Miércoles",
    "name": "Día B - tirón vertical y cadena posterior",
    "warmup": "5 minutos de elíptica, band pull-apart y bisagra de cadera sin carga.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Pies algo altos en la plataforma para repartir el trabajo hacia glúteo e isquio."
     },
     {
      "name": "Jalón agarre estrecho neutro",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho arriba, codos abajo y atrás; el dorsal es el que dibuja la cintura."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadera atrás con las mancuernas rozando el muslo; para donde el isquio ya no ceda."
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 75,
      "technique_cue": "Respaldo casi vertical y sin sacar las costillas al empujar."
     },
     {
      "name": "Abducción de cadera en máquina",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Tronco ligeramente inclinado adelante y apertura controlada, sin golpes."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Extiende los brazos sin permitir que el tronco gire hacia la polea."
     }
    ],
    "cooldown": "Respiración diafragmática tumbada tres minutos y estiramiento de isquios."
   },
   {
    "day": "Viernes",
    "name": "Día C - unilateral y detalle",
    "warmup": "5 minutos de cinta con inclinación y activación de glúteo medio con banda.",
    "exercises": [
     {
      "name": "Sentadilla búlgara",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tronco algo inclinado adelante para cargar el glúteo y no la rodilla."
     },
     {
      "name": "Remo con pecho apoyado en banco",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Pecho fijo en el banco; que no haya balanceo, solo trabajo del codo."
     },
     {
      "name": "Patada de glúteo en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Cadera cuadrada y extiende sin arquear la espalda para llegar más lejos."
     },
     {
      "name": "Contractora de pecho",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Cierre suave delante del pecho y apertura hasta sentir estiramiento sin dolor."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cuerda a la altura de los ojos; abre las manos al final y aguanta medio segundo."
     },
     {
      "name": "Crunch en polea alta",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Redondea la espalda alta llevando las costillas a la pelvis; la cadera no se mueve."
     }
    ],
    "cooldown": "Cinco minutos de paseo suave y estiramiento de dorsal y glúteo."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: aprender los seis patrones y registrar los kilos de partida en su hoja",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Cargas prudentes y sesiones de 50 minutos justos; el objetivo es que salga antes del cierre sin correr."
   },
   {
    "week": 2,
    "intent": "Progresión: subir peso en hip thrust y jalón, que son sus dos ejercicios clave",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Mismas series; se le enseña que en dos semanas el peso ha subido y las medidas siguen iguales."
   },
   {
    "week": 3,
    "intent": "Carga: semana firme para que note de verdad el estímulo en glúteo y espalda",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Una serie más en hip thrust y en abducción; el resto sin cambios."
   },
   {
    "week": 4,
    "intent": "Descarga: aligerar y revisar medidas con cinta métrica para desmontar el miedo al volumen",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Dos series por ejercicio y sesión de 35 minutos; se dedica el rato final a comparar perímetros."
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Caminata rápida el fin de semana; nada de cardio a última hora entre semana porque le altera el sueño."
    }
   ]
  },
  "deload_instructions": "La semana 4 se entrena al 90 por ciento con dos series por ejercicio y se aprovecha para tomar perímetros de muslo, cadera y cintura delante de ella. Ese registro es la parte más importante de la descarga en este caso: es la prueba objetiva de que ha subido cargas sin ganar volumen en la pierna. Si en algún momento pide reducir el trabajo de pierna por miedo, se mantiene el hip thrust y se negocia el resto, nunca al revés."
 },
 {
  "category": "mantenimiento",
  "title": "Mantener · salud general por consejo médico",
  "case": "Para quien viene con la recomendación del médico de moverse más, sin objetivo estético.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body guiado en tres días",
  "split_rationale": "Cuerpo completo tres veces por semana con máquinas de recorrido guiado: es la vía más segura para alguien sin técnica ni condición previa, y reparte el estímulo cardiovascular a lo largo de la semana en lugar de concentrarlo. Nada de esfuerzos con la respiración bloqueada ni cargas cercanas al fallo, porque su tensión manda sobre cualquier otro criterio.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Día A - tren inferior guiado y espalda",
    "warmup": "8 minutos de bicicleta estática a ritmo de conversación y movilidad de hombro y cadera.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Suelta el aire al empujar; no aguantes nunca la respiración con el peso arriba."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Siéntate erguido y tira a la clavícula; sube el peso despacio sin dejar que te levante."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Empuja soltando el aire y frena la vuelta contando dos segundos."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Espalda apoyada, movimiento suave y sin tirones al final."
     },
     {
      "name": "Elevaciones laterales en máquina",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 75,
      "technique_cue": "Carga ligera; el hombro se calienta rápido y no hace falta forzar."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Respira todo el rato mientras mueves brazo y pierna contrarios; la lumbar no se despega del suelo."
     }
    ],
    "cooldown": "6 minutos caminando en cinta a ritmo bajo hasta que las pulsaciones bajen y estiramiento de pecho."
   },
   {
    "day": "Miércoles",
    "name": "Día B - patrones de levantarse y empujar",
    "warmup": "8 minutos de cinta caminando con inclinación suave y movilidad de tobillo.",
    "exercises": [
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Empieza con el cajón bajo, sube sin impulso del pie de atrás y baja controlando."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Pecho apoyado, codos hacia atrás y hombros lejos de las orejas."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Recorrido cómodo; si notas presión en la cabeza, baja el peso y avisa."
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Sube apretando el glúteo y suelta el aire arriba, sin aguantar la respiración."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 75,
      "technique_cue": "Codos pegados al costado; movimiento pequeño y controlado."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Alterna lados despacio; si pierdes el equilibrio, acorta el recorrido."
     }
    ],
    "cooldown": "6 minutos de bicicleta muy suave y estiramiento de isquios y glúteo."
   },
   {
    "day": "Viernes",
    "name": "Día C - repaso completo",
    "warmup": "8 minutos de elíptica a ritmo cómodo y movilidad general de columna.",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "No bajes hasta que la cadera se despegue del respaldo; ese es tu tope."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Tronco quieto y tirón corto; nada de echarte atrás para mover más peso."
     },
     {
      "name": "Contractora de pecho",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Cierre suave delante del pecho, sin llegar a chocar los brazos."
     },
     {
      "name": "Puente de glúteos",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Apoya los pies cerca del glúteo y sube apretando; respira arriba."
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo y pausa arriba; el gemelo agradece el trabajo tras tantas horas sentado."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Con rodillas apoyadas si hace falta; respira con normalidad todo el tiempo."
     }
    ],
    "cooldown": "8 minutos caminando en cinta y estiramiento de cadera y espalda baja."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: aprender a respirar en cada repetición y quitarle el miedo a la sala",
    "load_pct": 100,
    "rir_target": "4",
    "volume_note": "Cargas muy conservadoras; la primera semana se mide el pulso al acabar cada bloque."
   },
   {
    "week": 2,
    "intent": "Progresión: subir una placa donde haya acabado con las repeticiones sobradas",
    "load_pct": 102.5,
    "rir_target": "3-4",
    "volume_note": "Mismas series y mismo orden; el cambio es mínimo a propósito."
   },
   {
    "week": 3,
    "intent": "Carga: primera semana en la que debe notar esfuerzo real sin llegar a ahogarse",
    "load_pct": 105,
    "rir_target": "3",
    "volume_note": "Se añade una serie a prensa y jalón; nada más, porque la recuperación aún es baja."
   },
   {
    "week": 4,
    "intent": "Descarga: semana ligera para consolidar el hábito y revisar tensión con su médico",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Dos series por ejercicio y más minutos de caminata; se sale sin sensación de esfuerzo."
   }
  ],
  "cardio": {
   "daily_steps": 7000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 4,
     "notes": "Caminar a ritmo en el que pueda hablar pero no cantar; puede repartirlo en dos paseos de 15 minutos entre carreras."
    }
   ]
  },
  "deload_instructions": "La semana 4 baja al 90 por ciento con dos series por ejercicio y se sustituye una sesión de fuerza por 40 minutos de caminata si llega muy cansado. En su caso la descarga es también el momento de la revisión: se le pide que enseñe al médico el registro de tensión antes y después de entrenar. Nunca se progresa de semana si ha aparecido mareo, dolor en el pecho o falta de aire desproporcionada; en ese caso se para y se deriva."
 },
 {
  "category": "mantenimiento",
  "title": "Mantener · en verano, 2 días fuera de casa",
  "case": "Para quien pasa el verano fuera y quiere no perder lo ganado con dos sesiones.",
  "level": "intermediate",
  "days_per_week": 2,
  "place": "home",
  "split_name": "Dos full body de mantenimiento con material mínimo",
  "split_rationale": "Con mancuernas ligeras no se puede replicar la carga del centro, así que se compensa con dos sesiones de cuerpo completo, repeticiones más altas, trabajo unilateral y tempo lento. Dos días bastan para conservar masa y fuerza durante ocho semanas, y encajan sin pelearse con la natación y la bici, que ya cubren de sobra el apartado cardiovascular.",
  "sessions": [
   {
    "day": "Martes",
    "name": "Full body A - bisagra y empuje",
    "warmup": "5 minutos de saltos suaves de cuerda imaginaria o marcha en el sitio, más movilidad de cadera y hombro con banda.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 4,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Con 8 kg necesitas tempo: baja en tres segundos y sube sin pausa para compensar la falta de carga."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 4,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Mancuernas rozando el muslo y cadera muy atrás; el rango largo es lo que suple los kilos."
     },
     {
      "name": "Remo con banda sentado",
      "sets": 4,
      "rep_range": "15-20",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Pisa la banda con las dos piernas para tensarla y aguanta un segundo con los omóplatos juntos."
     },
     {
      "name": "Press de hombro unilateral con mancuerna de pie",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Aprieta el glúteo y el abdomen para que el tronco no se incline hacia el lado libre."
     },
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Da el paso atrás largo y baja la rodilla hasta rozar el suelo, sin apoyarla."
     },
     {
      "name": "Plancha lateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Cadera bien alta y alineada; si aguantas más de 45 segundos, sube la pierna de arriba."
     }
    ],
    "cooldown": "Estiramiento de isquios y pectoral y tres minutos de respiración lenta en la terraza."
   },
   {
    "day": "Viernes",
    "name": "Full body B - unilateral y tirón vertical",
    "warmup": "5 minutos de marcha y movilidad de tobillo, más dos series ligeras de puente de glúteo.",
    "exercises": [
     {
      "name": "Sentadilla búlgara con peso corporal",
      "sets": 4,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pie de atrás en una silla; si te resulta fácil, baja en cuatro segundos y pausa un segundo abajo."
     },
     {
      "name": "Jalón con banda de pie",
      "sets": 4,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Ancla la banda alta y tira con los codos hacia el bolsillo, sin encoger los hombros."
     },
     {
      "name": "Press de pecho con banda",
      "sets": 4,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Banda por la espalda a la altura de la escápula; junta las manos al final del empuje."
     },
     {
      "name": "Curl femoral con deslizadores",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Cadera alta todo el recorrido y estira las piernas muy despacio; ahí está el trabajo."
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Una sola mancuerna, hombros nivelados y pasos cortos; alterna el lado en cada serie."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Lumbar pegada al suelo; si se despega, acorta el recorrido de la pierna."
     }
    ],
    "cooldown": "Estiramiento de cadera y dorsal y cinco minutos de paseo hasta el agua."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: ajustar tempos y bandas para que 8 kg se acerquen al esfuerzo del centro",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Se fija el tempo de cada ejercicio la primera semana; sin él, esta rutina se queda corta."
   },
   {
    "week": 2,
    "intent": "Progresión: sumar repeticiones dentro del rango antes de tocar nada más",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismas series; el avance es llegar al tope del rango en todos los ejercicios."
   },
   {
    "week": 3,
    "intent": "Carga: alargar la excéntrica a cuatro segundos en los tres primeros ejercicios",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Una serie más en sentadilla goblet y en jalón con banda; no hace falta más."
   },
   {
    "week": 4,
    "intent": "Descarga: semana de playa con lo justo para no perder el hábito",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Tres series por ejercicio y tempo normal; ese verano el objetivo es mantener, no rendir."
   }
  ],
  "cardio": {
   "daily_steps": 11000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 45,
     "times_per_week": 2,
     "notes": "Las salidas en bici con su pareja ya cuentan como sesión; no hay que añadir nada encima."
    },
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 3,
     "notes": "Natación tranquila en el mar; sirve además como recuperación entre los dos días de fuerza."
    }
   ]
  },
  "deload_instructions": "La semana 4 se hace al 90 por ciento con tres series por ejercicio y tempo normal, coincidiendo con la semana de más playa. En verano la descarga es fácil de justificar: el objetivo del bloque es llegar a septiembre habiendo mantenido, no progresar. Si algún día se salta una sesión por un plan familiar, se mueve al día siguiente y no se recupera acumulando dos seguidas."
 },
 {
  "category": "mantenimiento",
  "title": "Mantener · semana comprimida en 3 días seguidos",
  "case": "Para quien viaja media semana y concentra los entrenos en días consecutivos.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Reentrada suave + Torso + Pierna",
  "split_rationale": "Al concentrar los tres días seguidos no se puede repartir el trabajo como en una semana normal, así que se ordena por fatiga creciente: jueves ligero de cuerpo completo para recuperar del viaje, viernes torso con el grueso del trabajo de brazos y espalda, y sábado pierna, que es el día en el que tiene tiempo y no hay reunión detrás. El domingo y los tres días fuera actúan como descanso natural.",
  "sessions": [
   {
    "day": "Jueves",
    "name": "Reentrada - cuerpo completo suave",
    "warmup": "8 minutos de bicicleta a ritmo cómodo y movilidad de cadera, tobillo y columna torácica.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Sin buscar récords: hoy el objetivo es mover sangre después de tres días de silla y avión."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Tirón largo y junta los omóplatos; es el mejor antídoto contra el hombro adelantado del portátil."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Recorrido completo y sin bloquear el codo; carga moderada."
     },
     {
      "name": "Puente de glúteos",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Pausa arriba de un segundo apretando el glúteo, que lleva tres días apagado."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cuerda a la altura de los ojos y abre las manos al final del recorrido."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Movimiento lento alternando lados; sirve de reconexión del core antes del viernes."
     }
    ],
    "cooldown": "Cinco minutos de caminata suave y estiramiento de flexor de cadera, dos minutos por lado."
   },
   {
    "day": "Viernes",
    "name": "Torso completo",
    "warmup": "5 minutos de remo, band pull-apart y dos aproximaciones al press inclinado.",
    "exercises": [
     {
      "name": "Press inclinado con mancuernas",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Banco a 30 grados; baja hasta notar el pectoral estirado, sin que el hombro caiga adelante."
     },
     {
      "name": "Jalón agarre estrecho neutro",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Pecho arriba y codos hacia el bolsillo; controla la subida en lugar de soltar."
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Respaldo casi vertical y costillas abajo; nada de arquear para empujar más."
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadera cuadrada; tira del codo hacia atrás sin rotar el tronco."
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Sube hasta el hombro con el codo algo flexionado y sin impulso de cadera."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos pegados al tronco y abre la cuerda al final."
     },
     {
      "name": "Curl martillo",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Agarre neutro y codo quieto; sin balanceo de tronco."
     }
    ],
    "cooldown": "Estiramiento de pectoral en marco de puerta y movilidad torácica en el rodillo."
   },
   {
    "day": "Sábado",
    "name": "Pierna y core",
    "warmup": "8 minutos de bicicleta, movilidad de cadera y dos aproximaciones a la sentadilla goblet.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Mancuerna al pecho, codos dentro y profundidad hasta donde la espalda siga recta."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Cadera atrás con las mancuernas rozando el muslo; para donde el isquio ya no ceda."
     },
     {
      "name": "Sentadilla búlgara",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tronco algo inclinado adelante para repartir el trabajo hacia el glúteo."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Cadera pegada al banco y bajada frenada de dos segundos."
     },
     {
      "name": "Abducción de cadera en máquina",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Tronco algo adelante y apertura controlada, sin golpes."
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo con pausa arriba de un segundo."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Extiende los brazos sin permitir que el tronco gire hacia la polea."
     }
    ],
    "cooldown": "Diez minutos de paseo y estiramiento de glúteo, isquios y cuádriceps."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: comprobar que tres días seguidos son asumibles con la sesión suave delante",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Si el sábado llega con la pierna floja, se recorta ahí y no en el viernes."
   },
   {
    "week": 2,
    "intent": "Progresión: subir carga en press inclinado, jalón y sentadilla goblet",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismas series; el jueves se mantiene deliberadamente ligero toda la semana."
   },
   {
    "week": 3,
    "intent": "Carga: semana fuerte aprovechando que el sábado no tiene prisa",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Una serie más en la sesión de pierna; el jueves no se toca nunca."
   },
   {
    "week": 4,
    "intent": "Descarga: aligerar para encajar la semana de cierre de auditoría",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Dos sesiones en lugar de tres si el trabajo se dispara: se conservan viernes y sábado."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Caminar en los días de viaje, aunque sea del hotel a la oficina y vuelta; es lo único que se le pide fuera de Girona."
    }
   ]
  },
  "deload_instructions": "La semana 4 se hace al 90 por ciento y, si coincide con cierre de auditoría, se reduce a viernes y sábado manteniendo los ejercicios principales de cada sesión. Su descarga real son los tres días fuera, así que aquí lo importante es no castigarla por una semana mala de trabajo. Si vuelve de un viaje con menos de cinco horas de sueño dos noches seguidas, el jueves se convierte en 30 minutos de caminata y movilidad."
 },
 {
  "category": "mantenimiento",
  "title": "Mantener · 45 minutos a mediodía",
  "case": "Para quien entrena en la pausa del trabajo y necesita entrar y salir a su hora.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body en pares, tres días",
  "split_rationale": "Cuerpo completo tres veces por semana con los ejercicios emparejados (un tren inferior con un tren superior) para que el descanso de uno sea el trabajo del otro. Así caben seis ejercicios y un core en 45 minutos reales, calentamiento incluido, y ninguna sesión depende de un aparato concreto que pueda estar ocupado a la hora punta del mediodía.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Día A - hexagonal y empuje",
    "warmup": "4 minutos de remo y movilidad de cadera y hombro; se cronometra.",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Pecho alto en la salida y empuja el suelo; la barra hexagonal no requiere rack y siempre está libre."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Emparejado con el ejercicio anterior: mientras descansas de uno, haces el otro."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho apoyado y codos atrás; sin balanceo para ganar tiempo."
     },
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Paso atrás largo y rodilla casi al suelo; alterna piernas sin descanso entre lados."
     },
     {
      "name": "Elevación lateral en polea unilateral",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 45,
      "technique_cue": "Dos series por lado, encadenadas; no hay tiempo para más."
     },
     {
      "name": "Plancha con lastre",
      "sets": 2,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Disco en la zona media de la espalda; glúteo apretado y costillas abajo."
     }
    ],
    "cooldown": "Tres minutos de respiración y estiramiento de flexor de cadera mientras se enfría."
   },
   {
    "day": "Miércoles",
    "name": "Día B - prensa y vertical",
    "warmup": "4 minutos de elíptica y band pull-apart.",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Sin bloquear la rodilla arriba; cambio de disco rápido y a la siguiente serie."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Emparejado con la prensa; espalda pegada al respaldo."
     },
     {
      "name": "Jalón al pecho",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Codos hacia el bolsillo y control en la subida; nada de soltar el peso."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Espalda apoyada y sin levantar la cadera para ayudarte."
     },
     {
      "name": "Curl bayesian en polea",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 45,
      "technique_cue": "Un paso por delante de la polea, codo detrás del cuerpo y sin moverlo."
     },
     {
      "name": "Press Pallof",
      "sets": 2,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Aprovecha que ya estás en la polea; extiende sin girar el tronco."
     }
    ],
    "cooldown": "Tres minutos de movilidad torácica y estiramiento de dorsal."
   },
   {
    "day": "Viernes",
    "name": "Día C - goblet e inclinado",
    "warmup": "4 minutos de bicicleta y movilidad de tobillo y hombro.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Mancuerna pesada al pecho; sustituye a la sentadilla con barra para no depender del rack."
     },
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Banco a 30 grados y bajada controlada; emparejado con la sentadilla."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tronco quieto, tirón del codo a la cadera."
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Pausa arriba de un segundo apretando el glúteo; entra y sal rápido."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 45,
      "technique_cue": "Codos pegados al tronco; dos series encadenadas y fuera."
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 2,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Una mancuerna pesada, hombros nivelados; es el core y el remate de la semana."
     }
    ],
    "cooldown": "Tres minutos de paseo y estiramiento rápido de cadera antes de la ducha."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: cronometrar de verdad las tres sesiones y ajustar lo que no quepa",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Si alguna sesión pasa de 45 minutos, se quita una serie del último accesorio, nunca del primer ejercicio."
   },
   {
    "week": 2,
    "intent": "Progresión: subir carga en hexagonal, prensa y goblet manteniendo el reloj",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismas series; el tiempo es el límite, así que se progresa en peso y no en volumen."
   },
   {
    "week": 3,
    "intent": "Carga: semana más exigente en los tres ejercicios principales",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Una serie extra solo en el primer ejercicio de cada día; el resto intacto."
   },
   {
    "week": 4,
    "intent": "Descarga: semana ligera para llegar entero al cierre trimestral",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Dos series por ejercicio; la sesión baja a 30 minutos y él lo agradece esa semana."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 2,
     "notes": "Caminar el fin de semana o bajar del coche unas calles antes; el mediodía entre semana ya está ocupado."
    }
   ]
  },
  "deload_instructions": "La semana 4 se hace al 90 por ciento con dos series por ejercicio, dejando las sesiones en unos 30 minutos. En su caso la descarga tiene una función extra: demostrarle que una semana suave no le hace perder nada, porque la tentación de saltársela cuando va justo de tiempo es alta. Si un mes tiene cierre contable y solo puede venir dos días, se conservan el día A y el día C."
 },
 {
  "category": "mantenimiento",
  "title": "Mantener · en casa cuando no puede ir al centro",
  "case": "Para quien es socio pero algunas semanas no puede ir y necesita la misma rutina en casa.",
  "level": "intermediate",
  "days_per_week": 3,
  "place": "home",
  "split_name": "Full body silencioso en tres días",
  "split_rationale": "Se replican los mismos patrones que hace en la sala (bisagra, sentadilla, tirón horizontal, tirón vertical, empuje y core) pero con material que cabe debajo del sofá y sin ningún ejercicio con fase de vuelo o impacto. Tres días de cuerpo completo compensan que la carga máxima disponible sean 10 kg: se gana con más series efectivas, unilateral y tempo.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Comedor A - bisagra y empuje vertical",
    "warmup": "5 minutos de movilidad de cadera, tobillo y hombro en la alfombra, sin saltos.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 4,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Con 10 kg necesitas tempo: tres segundos de bajada y sin pausa arriba."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 4,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Cadera muy atrás y mancuernas rozando el muslo; el rango largo sustituye a los kilos."
     },
     {
      "name": "Remo con banda sentado",
      "sets": 4,
      "rep_range": "15-20",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Pisa la banda con las dos piernas y aguanta un segundo con los omóplatos juntos."
     },
     {
      "name": "Press de hombro con banda",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Pisa la banda y empuja sin arquear la lumbar; el ruido cero es parte del ejercicio."
     },
     {
      "name": "Frog pump",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "1-2",
      "rest_sec": 45,
      "technique_cue": "Plantas de los pies juntas y rodillas abiertas; aprieta el glúteo un segundo arriba."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Glúteo apretado y costillas abajo; si aguantas más de 45 segundos, apoya una mancuerna en la espalda."
     }
    ],
    "cooldown": "Estiramiento de isquios y pectoral y tres minutos de respiración lenta antes de acostarse."
   },
   {
    "day": "Miércoles",
    "name": "Comedor B - unilateral y tirón vertical",
    "warmup": "5 minutos de marcha en el sitio suave y activación de glúteo con banda.",
    "exercises": [
     {
      "name": "Zancada inversa",
      "sets": 4,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Paso atrás largo y apoyo silencioso; con mancuernas si la banda del suelo lo permite."
     },
     {
      "name": "Jalón con banda de pie",
      "sets": 4,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Ancla la banda en la parte alta de una puerta y tira con los codos hacia el bolsillo."
     },
     {
      "name": "Press de pecho con banda",
      "sets": 4,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Banda por detrás a la altura de la escápula y junta las manos al final."
     },
     {
      "name": "Curl femoral con deslizadores",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cadera alta todo el recorrido y estira las piernas muy despacio."
     },
     {
      "name": "Abducción de cadera con banda",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "1-2",
      "rest_sec": 45,
      "technique_cue": "Banda por encima de la rodilla y apertura sin que la cadera se vaya atrás."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Lumbar pegada al suelo; si se despega, acorta el recorrido de la pierna."
     }
    ],
    "cooldown": "Estiramiento de cuádriceps y glúteo y dos minutos de respiración diafragmática."
   },
   {
    "day": "Sábado",
    "name": "Comedor C - unilateral pesado y core",
    "warmup": "5 minutos de movilidad general aprovechando que a esa hora los niños están despiertos y no hay problema de ruido.",
    "exercises": [
     {
      "name": "Sentadilla búlgara con peso corporal",
      "sets": 4,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Pie de atrás en el sofá; si sale fácil, baja en cuatro segundos con pausa abajo."
     },
     {
      "name": "Remo invertido bajo una mesa",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Mesa firme, cuerpo recto como una tabla; cuanto más horizontal, más difícil."
     },
     {
      "name": "Press de hombro unilateral con mancuerna de pie",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Aprieta glúteo y abdomen para que el tronco no se incline al lado libre."
     },
     {
      "name": "Peso muerto rumano a una pierna",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cadera cuadrada y bajada lenta; si pierdes el equilibrio, roza el suelo con la punta del pie."
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Una mancuerna, hombros nivelados y pasos por el pasillo; alterna lado cada serie."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Alterna brazo y pierna contrarios sin que la cadera se abra."
     }
    ],
    "cooldown": "Estiramiento global de espalda, cadera y hombro, cinco minutos."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: montar el rincón de entreno y fijar los tempos que compensan los 10 kg",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Se anota qué banda se usa en cada ejercicio para poder progresar de verdad después."
   },
   {
    "week": 2,
    "intent": "Progresión: llegar al tope del rango de repeticiones en todos los ejercicios",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismas series; el avance es en repeticiones porque las mancuernas no dan más."
   },
   {
    "week": 3,
    "intent": "Carga: pasar a la banda más dura en remo, jalón y press de pecho",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Una serie más en los dos primeros ejercicios de cada día."
   },
   {
    "week": 4,
    "intent": "Descarga: semana ligera que coincide con las guardias de Navidad",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Tres series por ejercicio y tempo normal; si un día no puede, se mueve al sábado."
   }
  ],
  "cardio": {
   "daily_steps": 10000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Paseo con los niños el fin de semana; entre semana el turno del centro de salud ya le deja muchos pasos."
    }
   ]
  },
  "deload_instructions": "La semana 4 se hace al 90 por ciento con tres series por ejercicio y tempo normal. Este bloque es de mantenimiento puro: el objetivo es que en febrero vuelva a la sala moviendo los mismos kilos que dejó en octubre, no que progrese en casa. Si algún día no consigue el rato de las 21:30, se hace la sesión el sábado y se acepta la semana de dos días sin darle más vueltas."
 },
 {
  "category": "mantenimiento",
  "title": "Mantener · masa y hueso pasados los 45",
  "case": "Para quien quiere conservar músculo y densidad ósea de cara a los próximos años.",
  "level": "intermediate",
  "days_per_week": 4,
  "place": "gym",
  "split_name": "Pierna/Torso alternado en cuatro días",
  "split_rationale": "Cuatro sesiones alternando tren inferior y superior permiten dar dos estímulos semanales a la cadera y la columna con carga axial, que es lo que estimula al hueso, sin acumular fatiga en el hombro. Toda la vertical se hace en máquina o con landmine, que respetan su rango sin dolor, y se conserva la sentadilla con barra porque es el mejor ejercicio disponible para su objetivo óseo.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Pierna A - carga axial",
    "warmup": "8 minutos de bicicleta, movilidad de tobillo y cadera y tres series de aproximación en sentadilla.",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Barra en el trapecio y profundidad hasta donde la pelvis no se retroverse; esta es la carga que necesita tu cadera."
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Cadera atrás con la barra pegada al muslo; espalda neutra de principio a fin."
     },
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Recorrido completo sin que la cadera se despegue del respaldo."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Bajada frenada de tres segundos; el isquio protege la rodilla."
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 4,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "De pie y con carga, que es como el hueso del tobillo recibe el estímulo."
     },
     {
      "name": "Plancha con lastre",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Disco en la zona media de la espalda; glúteo apretado y costillas abajo."
     }
    ],
    "cooldown": "Cinco minutos de paseo y estiramiento de cuádriceps y psoas."
   },
   {
    "day": "Martes",
    "name": "Torso A - hombro amable",
    "warmup": "5 minutos de remo, rotación externa con banda y band pull-apart.",
    "exercises": [
     {
      "name": "Press de pecho en máquina",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Recorrido guiado y sin que el hombro caiga adelante; aquí no hay dolor."
     },
     {
      "name": "Remo con barra",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Tronco a 45 grados y bloqueado; la barra al ombligo sin tirones lumbares."
     },
     {
      "name": "Press landmine de pie",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Trayectoria en diagonal: es la vertical que tu hombro tolera, en lugar del press militar."
     },
     {
      "name": "Jalón agarre estrecho neutro",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Agarre neutro para descargar el hombro; codos hacia el bolsillo."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cuerda a la altura de los ojos; este es tu ejercicio de mantenimiento del hombro, no lo saltes."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos pegados al tronco y abre la cuerda al final."
     }
    ],
    "cooldown": "Movilidad torácica en el rodillo y estiramiento suave de pectoral."
   },
   {
    "day": "Jueves",
    "name": "Pierna B - cadera y unilateral",
    "warmup": "8 minutos de bicicleta, puente de glúteo sin carga y aproximaciones a la hexagonal.",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Pecho alto y empuja el suelo con el pie entero; carga axial sin castigar el hombro."
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Pausa arriba de un segundo con el glúteo apretado y costillas abajo."
     },
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cajón a la altura de la rodilla y sube sin impulso; es el gesto que protege del tropiezo."
     },
     {
      "name": "Extensión de rodilla en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Extiende sin latigazo final y baja frenando dos segundos."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Espalda pegada al respaldo y sin levantar la cadera."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Extiende los brazos sin dejar que el tronco gire; el core de pie es el que te sostiene si tropiezas."
     }
    ],
    "cooldown": "Estiramiento de isquios y glúteo y cinco minutos de paseo."
   },
   {
    "day": "Viernes",
    "name": "Torso B - volumen sin barra por encima de la cabeza",
    "warmup": "5 minutos de elíptica, rotación externa con banda y band pull-apart.",
    "exercises": [
     {
      "name": "Cruce de poleas",
      "sets": 4,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Recorrido amplio pero sin llevar el hombro más atrás de la línea del cuerpo."
     },
     {
      "name": "Dominadas neutras",
      "sets": 4,
      "rep_range": "6-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Agarre neutro, deprime la escápula antes de doblar el codo y controla la bajada."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Ajusta el asiento para que el recorrido acabe donde no te molesta; ese es tu tope."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho apoyado y hombros lejos de las orejas."
     },
     {
      "name": "Contractora invertida",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Apertura sin encoger el trapecio; el deltoides posterior es el que reequilibra tu hombro."
     },
     {
      "name": "Curl de bíceps con barra EZ",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos fijos al costado y sin usar la cadera para arrancar."
     }
    ],
    "cooldown": "Estiramiento de dorsal y pectoral y tres minutos de respiración lenta."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: confirmar que la sentadilla y la hexagonal no despiertan el hombro",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Si el hombro protesta en alguna serie, se cambia el ejercicio esa misma sesión y se anota."
   },
   {
    "week": 2,
    "intent": "Progresión: subir kilos en sentadilla, hexagonal y remo con barra",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismas series; el estímulo óseo depende de la carga, así que aquí sí importa el peso."
   },
   {
    "week": 3,
    "intent": "Carga: la semana clave del mes para la cadera y la columna",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Una serie más en sentadilla y en hexagonal; nada en el trabajo de hombro."
   },
   {
    "week": 4,
    "intent": "Descarga: bajar carga axial y dejar que la articulación se recupere",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Se quita una serie de cada ejercicio y se mantiene íntegro el face pull, que es trabajo de mantenimiento."
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 40,
     "times_per_week": 2,
     "notes": "Caminata por terreno irregular, mejor en cuesta o por camino: el impacto suave y el desequilibrio también son estímulo para el hueso."
    }
   ]
  },
  "deload_instructions": "La semana 4 se entrena al 90 por ciento con una serie menos por ejercicio, manteniendo íntegro el trabajo de face pull y rotación externa, que es prevención y no carga. Es también el momento de revisar si el hombro ha aguantado el mes: si ha ido bien, en el siguiente bloque se puede probar el press de hombro unilateral con mancuerna. Si ha aparecido dolor nocturno o al dormir del lado derecho, se retira toda la vertical y se deriva a valoración."
 },
 {
  "category": "mantenimiento",
  "title": "Mantener · en la menopausia",
  "case": "Para quien está en menopausia y necesita fuerza e impacto medido para hueso y descanso.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body con dosis de impacto controlada",
  "split_rationale": "Cuerpo completo tres días para dar frecuencia a los grandes grupos, con un bloque corto de impacto colocado al inicio de la primera sesión, cuando está fresca y el tejido responde mejor. La carga es el estímulo principal para el hueso y el músculo; el salto es solo una dosis pequeña y progresiva, porque nueve horas de pie ya le dan sobrecarga suficiente en el tren inferior.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Día A - impacto y carga",
    "warmup": "8 minutos de bicicleta, movilidad de tobillo y cadera y activación de glúteo con banda.",
    "exercises": [
     {
      "name": "Sentadilla con salto",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Salto bajo y aterrizaje silencioso con rodilla y cadera flexionadas; calidad, no altura."
     },
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Mancuerna al pecho, talones apoyados y profundidad cómoda."
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pausa de un segundo arriba apretando el glúteo; nada de arquear la lumbar."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tira del codo a la cadera y junta los omóplatos sin encoger el hombro."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 75,
      "technique_cue": "Asiento a la altura del pecho y recorrido completo."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Cadera a la altura de los hombros; si se hunde, apoya las rodillas."
     }
    ],
    "cooldown": "Cinco minutos de paseo y estiramiento de gemelo y planta del pie, que es donde acumula la jornada."
   },
   {
    "day": "Miércoles",
    "name": "Día B - carga sin impacto",
    "warmup": "8 minutos de elíptica y movilidad de columna y hombro.",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Pies a la anchura de las caderas; sin bloquear la rodilla arriba."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Pecho arriba y barra a la clavícula; controla la subida."
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 75,
      "technique_cue": "Respaldo casi vertical y sin sacar las costillas."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadera atrás y espalda neutra; para donde el isquio ya no ceda."
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo con pausa arriba; fortalecer el gemelo hace que aguante mejor las nueve horas."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Lumbar pegada al suelo todo el rato y respiración continua."
     }
    ],
    "cooldown": "Estiramiento de isquios y cadena posterior y tres minutos de respiración lenta."
   },
   {
    "day": "Viernes",
    "name": "Día C - unilateral y postura",
    "warmup": "8 minutos de cinta caminando con inclinación y activación de glúteo medio.",
    "exercises": [
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Cajón a la altura de la rodilla y sube empujando con el pie de arriba, sin impulso."
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Cadera cuadrada y tirón del codo hacia atrás, sin rotar el tronco."
     },
     {
      "name": "Contractora de pecho",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Cierre suave delante del pecho y apertura hasta notar estiramiento, sin dolor."
     },
     {
      "name": "Abducción de cadera en máquina",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Tronco algo inclinado adelante y apertura controlada."
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Peso ligero, sube al hombro y baja contando dos segundos."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "3",
      "rest_sec": 45,
      "technique_cue": "Alterna brazo y pierna contrarios sin abrir la cadera hacia un lado."
     }
    ],
    "cooldown": "Estiramiento de cadera y gemelo y cinco minutos de paseo suave."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: comprobar cómo tolera el bloque de saltos con la jornada de pie encima",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Solo 18 saltos en toda la semana; si aparece molestia en tibia o rodilla, se retiran y se sustituyen por subida a cajón."
   },
   {
    "week": 2,
    "intent": "Progresión: subir carga en hip thrust y prensa manteniendo el mismo número de saltos",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "El impacto no se progresa aún; solo la carga."
   },
   {
    "week": 3,
    "intent": "Carga: semana firme y primera subida del bloque de saltos a cuatro series",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Se añade una serie de saltos y una de hip thrust; el resto sin cambios."
   },
   {
    "week": 4,
    "intent": "Descarga: quitar el impacto y aligerar para dormir mejor esa semana",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Sin saltos y dos series por ejercicio; se aprovecha para valorar cómo va el sueño."
   }
  ],
  "cardio": {
   "daily_steps": 10000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 35,
     "times_per_week": 2,
     "notes": "Caminata a buen ritmo el fin de semana, mejor por la mañana; el cardio de tarde le empeora el descanso."
    }
   ]
  },
  "deload_instructions": "La semana 4 se hace al 90 por ciento, con dos series por ejercicio y sin ningún salto. En su caso la descarga tiene una función clara: separar el efecto del entrenamiento del efecto de la menopausia sobre el sueño y la energía, así que se le pregunta expresamente cómo ha dormido esa semana. Si aparece dolor persistente en el talón o la tibia, el bloque de impacto se retira del todo y se compensa con más carga en hip thrust y elevación de talones."
 },
 {
  "category": "mantenimiento",
  "title": "Mantener · 2 días de pesas para quien corre",
  "case": "Para quien sale a correr varios días y solo quiere dos sesiones de pesas de apoyo.",
  "level": "intermediate",
  "days_per_week": 2,
  "place": "gym",
  "split_name": "Dos full body con carga alta y volumen bajo",
  "split_rationale": "Dos sesiones de cuerpo completo con pocas series y repeticiones medias-bajas: es la fórmula que mejora la economía de carrera y la rigidez del tendón sin generar el daño muscular que le arruinaría el rodaje siguiente. Se colocan martes y viernes para dejar limpio el domingo del rodaje largo, y se descarta cualquier trabajo de alto volumen o cerca del fallo en la pierna.",
  "sessions": [
   {
    "day": "Martes",
    "name": "Full body A - cadena posterior y empuje",
    "warmup": "6 minutos de bicicleta, movilidad de tobillo y cadera y dos aproximaciones a la hexagonal.",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 4,
      "rep_range": "4-6",
      "rir": "3",
      "rest_sec": 180,
      "technique_cue": "Pocas repeticiones y lejos del fallo: buscamos fuerza, no daño muscular que te cargue el rodaje."
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Escápulas retraídas; el torso también cuenta en el braceo de los últimos kilómetros."
     },
     {
      "name": "Remo con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Tronco a 45 grados y bloqueado; la barra al ombligo sin tirones."
     },
     {
      "name": "Sentadilla búlgara",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Unilateral y controlada: corrige el desequilibrio entre piernas que aparece a base de kilómetros."
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Carga alta y pausa arriba; el sóleo y el aquiles son los que devuelven energía en cada zancada."
     },
     {
      "name": "Plancha lateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Cadera alta y alineada; el core lateral evita que la pelvis caiga en apoyo monopodal."
     }
    ],
    "cooldown": "Cinco minutos de trote muy suave y estiramiento de flexor de cadera y gemelo."
   },
   {
    "day": "Viernes",
    "name": "Full body B - guiado y vertical",
    "warmup": "6 minutos de elíptica, band pull-apart y movilidad de cadera.",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "3",
      "rest_sec": 150,
      "technique_cue": "Guiada y lejos del fallo; el sábado tienes rodaje suave y el domingo el largo."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Pecho arriba, codos hacia el bolsillo y control en la subida."
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Respaldo casi vertical y costillas abajo al empujar."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Rango controlado; el isquio fuerte es lo que te protege del tirón en el cambio de ritmo."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Bajada frenada de dos segundos, sin llegar nunca al fallo."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Extiende los brazos sin que el tronco gire; así se mantiene la pelvis estable corriendo."
     }
    ],
    "cooldown": "Cinco minutos de bicicleta suave y estiramiento de isquios y gemelo."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: comprobar que el rodaje del día siguiente no se resiente",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Empezamos con menos carga de la que podría mover; si el miércoles corre bien, subimos."
   },
   {
    "week": 2,
    "intent": "Progresión: subir kilos en hexagonal y prensa manteniendo el RIR alto",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Mismas series; el volumen se queda bajo a propósito porque la carga de carrera ya es alta."
   },
   {
    "week": 3,
    "intent": "Carga: semana más fuerte, colocada lejos de la tirada larga del mes",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Una serie extra solo en elevación de talones; el resto igual."
   },
   {
    "week": 4,
    "intent": "Descarga: aligerar coincidiendo con la semana de más volumen de carrera",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Dos series por ejercicio; cuando se acerque octubre, esta semana se repetirá antes de competir."
   }
  ],
  "cardio": {
   "daily_steps": 12000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 60,
     "times_per_week": 4,
     "notes": "Sus rodajes habituales; no se toca su plan de carrera, la fuerza se adapta a él y no al revés."
    },
    {
     "type": "hiit",
     "minutes": 30,
     "times_per_week": 1,
     "notes": "La sesión de series que ya hace; se coloca en día distinto al de pesas siempre que sea posible."
    }
   ]
  },
  "deload_instructions": "La semana 4 se hace al 90 por ciento con dos series por ejercicio, y se sincroniza con la semana de mayor volumen de su plan de carrera. Diez días antes de la competición de octubre se repite este esquema y se elimina la sentadilla búlgara, que es lo que más agujetas le deja. Regla firme: si un día tiene que elegir entre el rodaje de calidad y las pesas, gana el rodaje, y la sesión de fuerza se mueve, no se recupera acumulando."
 },
 {
  "category": "mantenimiento",
  "title": "Mantener · rutina variada para no aburrirse",
  "case": "Para quien se cansa de la misma rutina y acaba abandonando.",
  "level": "intermediate",
  "days_per_week": 4,
  "place": "gym",
  "split_name": "Cuatro bloques temáticos por semana",
  "split_rationale": "Cada día tiene una identidad propia (empuje, tracción, pierna y una sesión cronometrada de cuerpo completo) y termina con un reto medible que se anota: eso convierte la rutina en una competición contra su propia hoja y le da el elemento de novedad que necesita. La estructura de patrones no cambia, así que el progreso es real aunque a él le parezca que cada día hace algo distinto.",
  "sessions": [
   {
    "day": "Martes",
    "name": "Bloque empuje - reto de core al final",
    "warmup": "6 minutos de remo, movilidad de hombro con banda y dos aproximaciones al press banca.",
    "exercises": [
     {
      "name": "Press banca con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Escápulas retraídas y pies clavados; anota el mejor peso de cada semana."
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Respaldo casi vertical y sin arquear la lumbar al empujar."
     },
     {
      "name": "Fondos en paralelas (énfasis tríceps)",
      "sets": 3,
      "rep_range": "8-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Tronco casi vertical y codos pegados; baja hasta 90 grados, no más."
     },
     {
      "name": "Cruce de poleas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Recorrido amplio y cierre delante del pecho, sin bloquear el codo."
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Sin impulso de cadera; sube al hombro y baja frenando."
     },
     {
      "name": "Rueda abdominal",
      "sets": 3,
      "rep_range": "8-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "El reto del día: cada semana se marca en el suelo hasta dónde has llegado sin arquear la lumbar."
     }
    ],
    "cooldown": "Estiramiento de pectoral y hombro y tres minutos de respiración lenta."
   },
   {
    "day": "Miércoles",
    "name": "Bloque tracción - reto de agarre al final",
    "warmup": "6 minutos de bicicleta, band pull-apart y colgarse 20 segundos de la barra.",
    "exercises": [
     {
      "name": "Dominadas pronas",
      "sets": 4,
      "rep_range": "6-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Anota el total de repeticiones de las cuatro series; ese número es tu marca de la semana."
     },
     {
      "name": "Remo con barra T",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Pecho apoyado y codos atrás; sin tirones de la cadera."
     },
     {
      "name": "Remo en polea a una mano",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Deja que la escápula se abra al estirar y ciérrala al tirar."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cuerda a la altura de los ojos; equilibra todo el empuje del martes."
     },
     {
      "name": "Curl martillo",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Agarre neutro, codo quieto y sin balanceo."
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "El reto del día: sube la mancuerna cada semana que aguantes los 45 segundos con la técnica intacta."
     }
    ],
    "cooldown": "Estiramiento de dorsal y antebrazo y movilidad torácica."
   },
   {
    "day": "Viernes",
    "name": "Bloque pierna - reto de potencia al final",
    "warmup": "8 minutos de bicicleta, movilidad de cadera y tobillo y tres aproximaciones a la sentadilla.",
    "exercises": [
     {
      "name": "Sentadilla trasera con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Barra en el trapecio y profundidad constante; el peso solo cuenta si repites la misma profundidad."
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Cadera atrás, barra pegada al muslo y espalda neutra."
     },
     {
      "name": "Zancadas caminando con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pasos largos por el pasillo de la sala; rodilla casi al suelo en cada apoyo."
     },
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 120,
      "technique_cue": "Recorrido completo sin despegar la cadera del respaldo."
     },
     {
      "name": "Sentadilla con salto",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "El reto del día: se mide la altura del mejor salto con la cinta de la pared cada viernes."
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo con pausa arriba de un segundo."
     }
    ],
    "cooldown": "Diez minutos de paseo y estiramiento de cuádriceps, isquios y gemelo."
   },
   {
    "day": "Sábado",
    "name": "Bloque cronometrado - cuerpo completo",
    "warmup": "8 minutos de movilidad general y dos vueltas ligeras al circuito para reconocerlo.",
    "exercises": [
     {
      "name": "Swing con kettlebell",
      "sets": 4,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Bisagra de cadera, no sentadilla; la kettlebell sube por el impulso, no por los brazos."
     },
     {
      "name": "Sentadilla goblet",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Mancuerna al pecho y ritmo constante; se cronometra la sesión entera."
     },
     {
      "name": "Remo invertido",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cuerpo recto como una tabla; baja la barra si te cuesta mantener la línea."
     },
     {
      "name": "Flexiones",
      "sets": 4,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos a 45 grados y cuerpo en bloque; no dejes caer la cadera."
     },
     {
      "name": "Escaladores",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Cadera baja y ritmo sostenido; no aceleres los primeros diez segundos."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "El reto del día: se anota el tiempo total de la sesión y se intenta bajar un minuto cada semana."
     }
    ],
    "cooldown": "Cinco minutos de paseo y estiramiento global."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: establecer las cuatro marcas de referencia, una por sesión",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Lo importante de esta semana no son los kilos, sino que las cuatro marcas queden anotadas en su hoja."
   },
   {
    "week": 2,
    "intent": "Progresión: batir al menos dos de las cuatro marcas de la semana anterior",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismas series; si bate tres de cuatro, se le enseña la hoja y se le dice."
   },
   {
    "week": 3,
    "intent": "Carga: la semana de récords, justo cuando en los otros gimnasios lo dejaba",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Una serie más en los ejercicios principales; es la semana en la que se juega la permanencia."
   },
   {
    "week": 4,
    "intent": "Descarga: semana ligera con los retos mantenidos pero sin carga alta",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Dos series por ejercicio; los cuatro retos se conservan porque son lo que le hace venir."
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "hiit",
     "minutes": 12,
     "times_per_week": 1,
     "notes": "Bloque corto de bicicleta o remo al final del sábado, solo si le apetece; se plantea como reto, no como obligación."
    }
   ]
  },
  "deload_instructions": "La semana 4 baja al 90 por ciento con dos series por ejercicio, pero los cuatro retos finales se mantienen intactos: son el motivo por el que aparece por la puerta. En su caso la descarga es también la revisión de adherencia; se repasa con él la hoja del mes y se le enseña cuánto ha subido cada marca. Si en algún momento falla dos semanas seguidas, se reduce a tres días antes de que abandone del todo, porque conservar el hábito vale más que el cuarto día."
 },
 {
  "category": "mantenimiento",
  "title": "Mantener · el mínimo que funciona, 2 días",
  "case": "Para quien no puede más de dos días y quiere que le cundan de verdad.",
  "level": "beginner",
  "days_per_week": 2,
  "place": "gym",
  "split_name": "Dos full body completos",
  "split_rationale": "Con dos días, cada sesión tiene que cubrir el cuerpo entero: empuje, tirón, rodilla dominante, cadera dominante y core. Se usan siete ejercicios por sesión y series suficientes para que dos días den estímulo real de mantenimiento y algo de progreso, en lugar de la versión aguada de un plan de cuatro. La distancia de tres días entre sesiones facilita además que llegue recuperada aunque haya tenido guardia.",
  "sessions": [
   {
    "day": "Martes",
    "name": "Full body A",
    "warmup": "8 minutos de bicicleta y movilidad de cadera, tobillo y hombro.",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Pies a la anchura de las caderas y recorrido completo; sin bloquear la rodilla arriba."
     },
     {
      "name": "Jalón al pecho",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Pecho arriba, barra a la clavícula y control en la subida."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Asiento a la altura del pecho; empuja sin bloquear el codo de golpe."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadera atrás con las mancuernas rozando el muslo y espalda neutra."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Espalda apoyada y sin levantar la cadera para ayudarte."
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Sube al hombro con el codo algo flexionado y sin impulso."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Glúteo apretado y cadera a la altura de los hombros."
     }
    ],
    "cooldown": "Cinco minutos de paseo y estiramiento de cuádriceps, isquios y pectoral."
   },
   {
    "day": "Viernes",
    "name": "Full body B",
    "warmup": "8 minutos de elíptica, activación de glúteo con banda y movilidad torácica.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Mancuerna al pecho, codos dentro y profundidad hasta donde la espalda siga recta."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Tronco quieto y tirón del codo hacia la cadera."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Espalda pegada al respaldo y recorrido cómodo, sin forzar el final."
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pausa de un segundo arriba apretando el glúteo, con las costillas abajo."
     },
     {
      "name": "Extensión de rodilla en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Extiende sin latigazo final y baja frenando dos segundos."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cuerda a la altura de los ojos y abre las manos al final del recorrido."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2-3",
      "rest_sec": 45,
      "technique_cue": "Lumbar pegada al suelo; si se despega, acorta el recorrido de la pierna."
     }
    ],
    "cooldown": "Cinco minutos de bicicleta suave y estiramiento de espalda y cadera."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: dejar claro que estas dos sesiones son un plan completo, no un plan recortado",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Siete ejercicios por sesión y cuatro series en los principales; esa es la dosis que hace que dos días valgan."
   },
   {
    "week": 2,
    "intent": "Progresión: subir una placa en prensa, jalón y press de pecho",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Mismas series; con dos días el volumen no puede crecer, así que crece el peso."
   },
   {
    "week": 3,
    "intent": "Carga: la semana en la que debe salir con la sensación de haber entrenado en serio",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Una serie extra en sentadilla goblet y hip thrust."
   },
   {
    "week": 4,
    "intent": "Descarga: aligerar y revisar la hoja de kilos del mes con ella delante",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Tres series en los principales y dos en el resto; se sale sin agujetas."
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 3,
     "notes": "Caminar con el perro a buen ritmo; en su caso el cardio no se programa en el centro porque no vendría un tercer día."
    }
   ]
  },
  "deload_instructions": "La semana 4 se hace al 90 por ciento con una serie menos en cada ejercicio y sirve para enseñarle en su hoja lo que ha subido en cuatro semanas con solo dos días. Ese repaso es la parte más importante del bloque, porque su patrón de abandono nace de creer que si no viene cuatro días no sirve de nada. Si una semana tiene guardia y solo puede venir un día, se hace la sesión A y se retoma la semana siguiente donde quedó, sin recuperar nada."
 },
 {
  "category": "mantenimiento",
  "title": "Mantener · tras una gran pérdida de peso",
  "case": "Para quien ha perdido mucho peso y teme recuperarlo.",
  "level": "intermediate",
  "days_per_week": 5,
  "place": "gym",
  "split_name": "Cinco sesiones cortas de lunes a viernes",
  "split_rationale": "Cinco días cortos, de cinco ejercicios cada uno, dan la frecuencia diaria que él necesita para sostener el hábito sin que ninguna sesión sea una paliza. Repartir el volumen en cinco días permite además mantener la masa muscular ganada durante la pérdida, que es la verdadera garantía de no recuperar el peso, y deja el fin de semana libre para vida social sin que eso se viva como un fallo.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Empuje corto",
    "warmup": "5 minutos de remo y movilidad de hombro con banda.",
    "exercises": [
     {
      "name": "Press banca con mancuernas",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Escápulas retraídas y bajada controlada hasta notar el pectoral estirado."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Espalda pegada al respaldo y recorrido completo sin forzar el final."
     },
     {
      "name": "Cruce de poleas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Cierre delante del pecho con el codo ligeramente flexionado."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos pegados al tronco; abre la cuerda al final."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Glúteo apretado y costillas abajo; 35 minutos de sesión y a casa."
     }
    ],
    "cooldown": "Tres minutos de respiración lenta y estiramiento de pectoral."
   },
   {
    "day": "Martes",
    "name": "Pierna corta",
    "warmup": "6 minutos de bicicleta y movilidad de cadera y tobillo.",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Recorrido completo sin despegar la cadera del respaldo."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadera atrás y mancuernas rozando el muslo; espalda neutra."
     },
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Paso atrás largo y rodilla casi al suelo; alterna piernas."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Cadera pegada al banco y bajada de dos segundos."
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "1-2",
      "rest_sec": 45,
      "technique_cue": "Recorrido completo con pausa arriba; termina y vete, hoy no hace falta más."
     }
    ],
    "cooldown": "Cinco minutos de paseo y estiramiento de isquios y cuádriceps."
   },
   {
    "day": "Miércoles",
    "name": "Tracción corta",
    "warmup": "5 minutos de elíptica y band pull-apart.",
    "exercises": [
     {
      "name": "Jalón al pecho",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Pecho arriba y codos hacia el bolsillo; controla la subida."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tronco quieto y tirón del codo a la cadera."
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Cadera cuadrada y sin rotar el tronco para llegar más arriba."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cuerda a la altura de los ojos y apertura al final."
     },
     {
      "name": "Curl alterno con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codo quieto y sin balanceo de tronco."
     }
    ],
    "cooldown": "Estiramiento de dorsal y movilidad torácica, cuatro minutos."
   },
   {
    "day": "Jueves",
    "name": "Cadera y core",
    "warmup": "6 minutos de cinta con inclinación y activación de glúteo con banda.",
    "exercises": [
     {
      "name": "Hip thrust con barra",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Pausa de un segundo arriba con el glúteo apretado y las costillas abajo."
     },
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Mancuerna al pecho y profundidad cómoda; tras 28 kilos menos, la técnica ya no te limita."
     },
     {
      "name": "Abducción de cadera en máquina",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Tronco algo adelante y apertura controlada."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Espalda apoyada y sin levantar la cadera."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Extiende sin que el tronco gire hacia la polea."
     }
    ],
    "cooldown": "Estiramiento de glúteo y cadera y tres minutos de respiración."
   },
   {
    "day": "Viernes",
    "name": "Cuerpo completo ligero",
    "warmup": "6 minutos de bicicleta y movilidad general.",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2-3",
      "rest_sec": 150,
      "technique_cue": "Pecho alto y empuja el suelo; es el ejercicio que más masa te ayuda a conservar."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Recorrido completo y sin bloquear el codo."
     },
     {
      "name": "Jalón agarre estrecho neutro",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Agarre neutro y codos hacia el bolsillo."
     },
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Cajón a la altura de la rodilla; sube sin impulso del pie de atrás."
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Una mancuerna y hombros nivelados; buen cierre de semana."
     }
    ],
    "cooldown": "Cinco minutos de paseo y estiramiento global."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: comprobar que cinco días cortos son sostenibles y no una carga más",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Ninguna sesión debe pasar de 40 minutos; si se alarga, se recorta el último ejercicio."
   },
   {
    "week": 2,
    "intent": "Progresión: subir carga en los primeros ejercicios de cada día",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismas series; el objetivo del bloque es conservar músculo, y eso se consigue subiendo peso, no minutos."
   },
   {
    "week": 3,
    "intent": "Carga: semana firme para confirmar que mantiene fuerza con el peso ya estable",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Una serie más en hexagonal, prensa y hip thrust; el resto igual."
   },
   {
    "week": 4,
    "intent": "Descarga: bajar carga y reducir a cuatro días para probar que saltarse uno no rompe nada",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Se elimina la sesión del viernes esa semana; el ejercicio mental de comprobar que no pasa nada vale tanto como el físico."
   }
  ],
  "cardio": {
   "daily_steps": 12000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 35,
     "times_per_week": 3,
     "notes": "Caminata a buen ritmo; se prioriza el paso diario sobre las sesiones formales porque es lo que sostiene el peso a largo plazo."
    }
   ]
  },
  "deload_instructions": "La semana 4 baja al 90 por ciento y se reduce a cuatro días, quitando el viernes. Esa reducción es deliberada y se le explica: necesita comprobar con datos que una semana con un día menos no le hace recuperar peso, porque su riesgo real no es el sedentarismo sino la mentalidad de todo o nada. Se acuerda además pesarse una sola vez por semana, siempre el mismo día, y anotarlo en la hoja del centro en lugar de tres veces al día en casa."
 },
 {
  "category": "mantenimiento",
  "title": "Mantener · deportista de fin de semana",
  "case": "Para quien juega el fin de semana y entrena para no lesionarse.",
  "level": "intermediate",
  "days_per_week": 2,
  "place": "gym",
  "split_name": "Dos sesiones de prevención y fuerza",
  "split_rationale": "Dos días de cuerpo completo orientados a lo que le rompe: gemelo, isquios y aductor en aceleraciones y frenadas. El martes lleva el trabajo de fuerza más pesado, lejos del partido, y el jueves se centra en cadena posterior y control excéntrico con volumen moderado, que es preventivo sin dejar agujetas a 48 horas del sábado.",
  "sessions": [
   {
    "day": "Martes",
    "name": "Fuerza general lejos del partido",
    "warmup": "8 minutos de bicicleta, movilidad de tobillo y cadera y dos aproximaciones a la hexagonal.",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2",
      "rest_sec": 180,
      "technique_cue": "Pecho alto y empuje del suelo; la fuerza de cadera es lo que evita que el gemelo tenga que salvar la jugada."
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Escápulas retraídas y bajada controlada."
     },
     {
      "name": "Remo con pecho apoyado en banco",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho fijo en el banco y codos hacia atrás, sin balanceo."
     },
     {
      "name": "Sentadilla búlgara",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Trabajo a una pierna: el fútbol sala es unilateral y tu entrenamiento también debe serlo."
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Carga alta con pausa arriba y bajada de tres segundos; el gemelo se rompe por débil, no por falta de estiramiento."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Extiende sin girar el tronco; controla el giro que en pista haces sin pensar."
     }
    ],
    "cooldown": "Cinco minutos de bicicleta suave y estiramiento de cadera y gemelo."
   },
   {
    "day": "Jueves",
    "name": "Cadena posterior y control",
    "warmup": "8 minutos de cinta caminando con inclinación, movilidad de cadera y activación de glúteo.",
    "exercises": [
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Bajada de tres segundos: el isquio se protege trabajando en estiramiento y controlado."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Bajada frenada de tres segundos en cada repetición; esta es la parte que no se salta nunca."
     },
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Carga moderada; a 48 horas del partido no buscamos récords."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho arriba y codos hacia el bolsillo."
     },
     {
      "name": "Elevación de gemelo a una pierna en escalón",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo desde abajo y a una pierna; así se detecta si un lado va por detrás."
     },
     {
      "name": "Plancha lateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Cadera alta y alineada; el core lateral sostiene la pelvis en los cambios de dirección."
     }
    ],
    "cooldown": "Diez minutos de paseo, estiramiento suave de gemelo, isquio y aductor."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: medir cómo llega al sábado y si el jueves le deja alguna carga",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Se anota cada sábado cómo se ha encontrado en el partido; ese es el indicador que manda aquí."
   },
   {
    "week": 2,
    "intent": "Progresión: subir carga en hexagonal y elevación de talones, que son la clave preventiva",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismas series; se mantiene el volumen del jueves bajo a propósito."
   },
   {
    "week": 3,
    "intent": "Carga: semana más fuerte el martes, sin tocar nada del jueves",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Una serie extra en hexagonal y sentadilla búlgara, solo en la sesión de martes."
   },
   {
    "week": 4,
    "intent": "Descarga: aligerar y llegar al partido con las piernas frescas del todo",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Dos series por ejercicio; se conserva íntegro el trabajo excéntrico de isquio y gemelo."
   }
  ],
  "cardio": {
   "daily_steps": 10000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Caminata o bicicleta suave el domingo y el lunes para descargar tras el partido; nada de correr entre semana."
    }
   ]
  },
  "deload_instructions": "La semana 4 se hace al 90 por ciento con dos series por ejercicio, manteniendo completo el trabajo excéntrico de isquio y gemelo, que es lo que le protege y no se recorta nunca. Si algún jueves llega con la pierna cargada del partido anterior, se sustituye la prensa por diez minutos de bicicleta y se conservan curl femoral y elevación de talones. En cuanto note el gemelo tirante durante un partido, la semana siguiente se entrena solo cadena posterior y se avisa al fisioterapeuta antes de volver a jugar."
 },
 {
  "category": "mantenimiento",
  "title": "Mantener · con un trabajo ya muy activo",
  "case": "Para quien se mueve todo el día por trabajo y solo necesita fuerza de apoyo.",
  "level": "beginner",
  "days_per_week": 2,
  "place": "home",
  "split_name": "Dos sesiones con prioridad de tren superior",
  "split_rationale": "Su trabajo ya le da un volumen enorme de tren inferior y de gasto diario, así que añadir pierna sería sumar fatiga sin ganancia. Las dos sesiones priorizan empuje, tirón y core, con un solo ejercicio de cadera por sesión para no desatender el patrón de bisagra, que la bicicleta no entrena. Media hora por sesión y descansos cortos para que quepa de verdad.",
  "sessions": [
   {
    "day": "Miércoles",
    "name": "Pasillo A - empuje y tirón horizontal",
    "warmup": "4 minutos de movilidad de hombro y columna torácica; las piernas ya vienen calientes del turno.",
    "exercises": [
     {
      "name": "Press de pecho con banda",
      "sets": 4,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Banda por detrás a la altura de la escápula; junta las manos al final del empuje."
     },
     {
      "name": "Remo con banda sentado",
      "sets": 4,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Pisa la banda y aguanta un segundo con los omóplatos juntos; es el antídoto de ocho horas encorvada sobre el manillar."
     },
     {
      "name": "Press de hombro unilateral con mancuerna de pie",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Aprieta glúteo y abdomen para que el tronco no se incline al lado libre."
     },
     {
      "name": "Curl martillo",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Codo quieto y sin balanceo; también refuerza el agarre para la jornada."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Único ejercicio de cadera del día: la bici no entrena la bisagra y el isquio te lo agradecerá."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Glúteo apretado y costillas abajo; media hora y a la ducha."
     }
    ],
    "cooldown": "Estiramiento de pectoral en el marco de la puerta y de flexor de cadera, dos minutos por lado."
   },
   {
    "day": "Domingo",
    "name": "Pasillo B - tirón vertical y hombro",
    "warmup": "5 minutos de movilidad general; el domingo no viene del turno y conviene calentar algo más.",
    "exercises": [
     {
      "name": "Jalón con banda de pie",
      "sets": 4,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Ancla la banda alta en la puerta y tira con los codos hacia el bolsillo."
     },
     {
      "name": "Flexiones",
      "sets": 4,
      "rep_range": "8-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos a 45 grados y cuerpo en bloque; si no salen ocho, apoya las manos en el sofá."
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Sube al hombro con el codo algo flexionado y baja frenando."
     },
     {
      "name": "Extensión de tríceps sobre la cabeza con mancuerna",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Codos apuntando al techo y quietos; solo se mueve el antebrazo."
     },
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Única sentadilla de la semana y sin buscar fatiga: mañana vuelves a pedalear."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Alterna brazo y pierna contrarios sin que la cadera se abra."
     }
    ],
    "cooldown": "Estiramiento de dorsal, cuádriceps y gemelo, cinco minutos en total."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: encontrar la banda adecuada para cada ejercicio de tirón y empuje",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Nada de pierna añadida: su turno ya cubre de sobra ese apartado y sumar más sería contraproducente."
   },
   {
    "week": 2,
    "intent": "Progresión: llegar al tope del rango de repeticiones en los cuatro ejercicios de torso",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismas series; si acaba las cuatro con facilidad, se cambia a la banda más dura."
   },
   {
    "week": 3,
    "intent": "Carga: subir a la banda superior en remo, jalón y press de pecho",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Una serie más en flexiones; el trabajo de pierna se mantiene en tres series y no crece."
   },
   {
    "week": 4,
    "intent": "Descarga: semana suave que coincide con los picos de reparto de fin de mes",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Tres series por ejercicio; si un día llega destrozada del turno, se hace solo el domingo."
   }
  ],
  "cardio": {
   "daily_steps": 15000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 1,
     "notes": "Un paseo tranquilo en su día libre, sin bicicleta y sin mochila; es recuperación activa, no entrenamiento."
    }
   ]
  },
  "deload_instructions": "La semana 4 se hace al 90 por ciento con tres series por ejercicio. En su caso la descarga se decide por el trabajo, no por el calendario: en las semanas de más volumen de reparto se pasa directamente a la sesión del domingo y se acepta un solo día. Lo importante es que el trabajo de tren superior no desaparezca, porque es lo único que su jornada no cubre y lo único que le pidió."
 },
 {
  "category": "mantenimiento",
  "title": "Mantener · tono de brazos y abdomen (joven)",
  "case": "Para el joven que quiere brazos y abdomen sin descuidar el resto del cuerpo.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body con remate de brazo y core",
  "split_rationale": "Cuerpo completo tres días para construir la base que necesita a esa edad, con los dos últimos ejercicios de cada sesión dedicados a brazo y core, que es lo que él ha venido a buscar. Darle lo que pide al final de la sesión es lo que hace que se quede; ponerle solo curl y abdominales sería fallarle. Todo con máquinas y mancuernas mientras aprende a colocar la espalda.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Día A - base y bíceps",
    "warmup": "6 minutos de bicicleta, movilidad de hombro con banda y dos series ligeras del primer ejercicio.",
    "exercises": [
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-12",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Escápulas retraídas y pies en el suelo; baja hasta notar el pectoral, sin rebotar."
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Cadera cuadrada y tirón del codo hacia atrás; nada de rotar el tronco."
     },
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "La pierna también entra en el plan aunque no la hayas pedido; sin ella el resto se queda a medias."
     },
     {
      "name": "Curl de bíceps con barra EZ",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos fijos al costado y sin usar la cadera; con menos peso se nota el doble."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "El tríceps es dos tercios del brazo: aquí está la mitad de lo que has venido a buscar."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Glúteo apretado y cadera a la altura de los hombros."
     }
    ],
    "cooldown": "Cinco minutos de paseo y estiramiento de pectoral y cuádriceps."
   },
   {
    "day": "Miércoles",
    "name": "Día B - espalda, hombro y colgado",
    "warmup": "6 minutos de elíptica, band pull-apart y colgarse 20 segundos de la barra.",
    "exercises": [
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Pecho arriba y barra a la clavícula; la espalda ancha es lo que hace parecer el brazo más grande."
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Respaldo casi vertical y sin arquear la lumbar al empujar."
     },
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Mancuerna al pecho y talones apoyados; aprende aquí antes de tocar una barra."
     },
     {
      "name": "Curl martillo",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Agarre neutro; este es el que engrosa el antebrazo y el lateral del brazo."
     },
     {
      "name": "Fondos entre bancos",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos hacia atrás y baja solo hasta 90 grados; si molesta el hombro, para."
     },
     {
      "name": "Elevaciones de rodillas colgado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Sube las rodillas sin balancearte; el balanceo es lo que hace que no notes nada."
     }
    ],
    "cooldown": "Estiramiento de dorsal colgado suave y de hombro, cuatro minutos."
   },
   {
    "day": "Viernes",
    "name": "Día C - repaso y bombeo",
    "warmup": "6 minutos de bicicleta y movilidad general de hombro y cadera.",
    "exercises": [
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tronco quieto y codos a la cadera; sin echarte atrás para mover más."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Asiento a la altura del pecho y recorrido completo."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Cadera atrás y espalda recta; se entrena ligero porque estás aprendiendo el patrón."
     },
     {
      "name": "Curl bayesian en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Un paso por delante de la polea, codo detrás del cuerpo y quieto todo el recorrido."
     },
     {
      "name": "Patada de tríceps con mancuerna",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 45,
      "technique_cue": "Brazo pegado al costado y extensión completa; peso ligero y mucha calidad."
     },
     {
      "name": "Crunch en polea alta",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Redondea la espalda alta llevando las costillas a la pelvis; la cadera no se mueve."
     }
    ],
    "cooldown": "Cinco minutos de paseo y estiramiento global."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: aprender la técnica de los seis patrones y anotar todo en su hoja",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Cargas ligeras a propósito; a su edad la técnica vale más que cualquier kilo de esta semana."
   },
   {
    "week": 2,
    "intent": "Progresión: subir peso en press, jalón y prensa manteniendo la ejecución",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Mismas series; si la técnica se rompe al subir, se vuelve al peso anterior sin discusión."
   },
   {
    "week": 3,
    "intent": "Carga: primera semana en la que puede acercarse al esfuerzo real en brazo",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Una serie más en curl y en tríceps; el resto se mantiene."
   },
   {
    "week": 4,
    "intent": "Descarga: aligerar coincidiendo con la semana de exámenes",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Dos series por ejercicio y sesiones de 35 minutos; los estudios mandan esa semana."
   }
  ],
  "cardio": {
   "daily_steps": 10000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Bicicleta al instituto o partido con los amigos; no hace falta programarle cardio formal a su edad."
    }
   ]
  },
  "deload_instructions": "La semana 4 se hace al 90 por ciento con dos series por ejercicio y coincide siempre que se pueda con exámenes. Con él la descarga es también educativa: se le explica por qué una semana suave no le hace perder brazo, porque a los diecisiete la tentación es entrenar más cuanto más impaciente se está. Se revisa la hoja del mes con su padre delante y se le enseña cuánto han subido los pesos, que es la mejor forma de que siga tres años más."
 },
 {
  "category": "mantenimiento",
  "title": "Mantener · tono de glúteo y pierna",
  "case": "Para quien quiere glúteo y pierna sin sentadilla con barra.",
  "level": "intermediate",
  "days_per_week": 4,
  "place": "gym",
  "split_name": "Tres días de tren inferior sin sentadilla profunda y uno de torso",
  "split_rationale": "Tres sesiones de tren inferior repartidas en la semana permiten sostener la forma del glúteo y la pierna con volumen moderado por día, que es lo que su rodilla tolera, y una cuarta sesión de torso cubre el resto del cuerpo sin restarle protagonismo. Todo el trabajo se apoya en extensión de cadera, bisagra y máquinas de recorrido controlado; se elimina cualquier ejercicio que la obligue a flexionar la rodilla bajo carga en rango profundo.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Glúteo dominante",
    "warmup": "8 minutos de bicicleta con sillín alto, activación de glúteo medio con banda y movilidad de cadera.",
    "exercises": [
     {
      "name": "Hip thrust con barra",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Barbilla al pecho, costillas abajo y pausa de un segundo arriba; la rodilla no sufre en este patrón."
     },
     {
      "name": "Peso muerto rumano con barra",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Cadera muy atrás con la barra pegada al muslo; la rodilla apenas se dobla."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Cadera pegada al banco y bajada frenada de dos segundos."
     },
     {
      "name": "Patada de glúteo en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Cadera cuadrada; extiende sin arquear la espalda para llegar más lejos."
     },
     {
      "name": "Abducción de cadera en máquina",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Tronco algo inclinado adelante y apertura controlada, sin golpes."
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo con pausa arriba de un segundo."
     }
    ],
    "cooldown": "Estiramiento de glúteo e isquios y cinco minutos de paseo."
   },
   {
    "day": "Martes",
    "name": "Torso completo",
    "warmup": "5 minutos de remo, band pull-apart y movilidad torácica.",
    "exercises": [
     {
      "name": "Jalón al pecho",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho arriba y codos hacia el bolsillo; controla la subida."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Asiento a la altura del pecho y recorrido completo."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tronco quieto y tirón del codo hacia la cadera."
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Respaldo casi vertical y costillas abajo al empujar."
     },
     {
      "name": "Elevación lateral en polea unilateral",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Cable por detrás del cuerpo, sube al hombro y baja frenando."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Glúteo apretado y cadera a la altura de los hombros."
     }
    ],
    "cooldown": "Estiramiento de pectoral y dorsal, cuatro minutos."
   },
   {
    "day": "Jueves",
    "name": "Pierna general en rango seguro",
    "warmup": "8 minutos de bicicleta, movilidad de tobillo y cadera y dos series ligeras de goblet.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Baja solo hasta donde la rodilla esté cómoda; con la mancuerna delante controlas la profundidad mucho mejor que con barra."
     },
     {
      "name": "Prensa de piernas horizontal",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Ajusta el tope para no pasar de los 90 grados de rodilla; ese es tu límite."
     },
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cajón a la altura de la rodilla, sube sin impulso y baja controlando."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 75,
      "technique_cue": "Espalda apoyada y sin levantar la cadera para ayudarte."
     },
     {
      "name": "Aducción de cadera en máquina",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Cierre controlado y sin llegar al tope duro de la máquina."
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo y pausa arriba; el sóleo aguanta tus ocho horas de pie."
     }
    ],
    "cooldown": "Estiramiento de cuádriceps y gemelo y cinco minutos de bicicleta suave."
   },
   {
    "day": "Sábado",
    "name": "Cadera y core",
    "warmup": "8 minutos de cinta caminando con inclinación y activación de glúteo con banda.",
    "exercises": [
     {
      "name": "Hip thrust en máquina",
      "sets": 4,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 90,
      "technique_cue": "Segunda dosis de glúteo de la semana, más ligera y con más repeticiones que el lunes."
     },
     {
      "name": "Peso muerto rumano a una pierna",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Cadera cuadrada y bajada lenta; si pierdes el equilibrio, roza el suelo con la punta del pie."
     },
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Paso atrás largo: la rodilla de delante apenas se adelanta, por eso este sí lo toleras."
     },
     {
      "name": "Pull through en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Bisagra pura de cadera; termina apretando el glúteo sin arquear la lumbar."
     },
     {
      "name": "Abducción de cadera con banda",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "1-2",
      "rest_sec": 45,
      "technique_cue": "Banda por encima de la rodilla y apertura sin que la cadera se vaya atrás."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Extiende los brazos sin que el tronco gire hacia la polea."
     }
    ],
    "cooldown": "Estiramiento de glúteo, aductor e isquios, cinco minutos."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: confirmar que ningún ejercicio del plan despierta la rodilla derecha",
    "load_pct": 100,
    "rir_target": "2-3",
    "volume_note": "Se anota tras cada sesión si ha habido pinchazo; si aparece, se retira ese ejercicio y no se negocia."
   },
   {
    "week": 2,
    "intent": "Progresión: subir carga en hip thrust y peso muerto rumano, sus dos ejercicios clave",
    "load_pct": 102.5,
    "rir_target": "2",
    "volume_note": "Mismas series; el volumen de pierna ya está repartido en tres días y no debe crecer más."
   },
   {
    "week": 3,
    "intent": "Carga: semana firme para sostener la forma del glúteo sin ganar sección",
    "load_pct": 105,
    "rir_target": "1-2",
    "volume_note": "Una serie más en hip thrust del lunes; el jueves y el sábado no se tocan."
   },
   {
    "week": 4,
    "intent": "Descarga: aligerar y revisar cómo ha respondido la rodilla al mes completo",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Tres series por ejercicio y se retira la subida a cajón, que es lo que más flexión de rodilla le pide."
   }
  ],
  "cardio": {
   "daily_steps": 11000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 35,
     "times_per_week": 2,
     "notes": "Bicicleta con sillín alto o caminata llana; se evita la cuesta abajo prolongada, que es lo que más le carga la rodilla."
    }
   ]
  },
  "deload_instructions": "La semana 4 se entrena al 90 por ciento con tres series por ejercicio y sin subida a cajón. Es también la semana de revisión de la rodilla: se le pregunta expresamente si ha notado pinchazos, chasquidos o inflamación tras alguna sesión, y con esa información se decide si en el siguiente bloque se puede probar la prensa con algo más de recorrido. Si aparece dolor que dure más de 48 horas, se retira todo el trabajo de rodilla dominante y se deriva a valoración."
 },
 {
  "category": "mantenimiento",
  "title": "Mantener · fuerza sin buscar máximos",
  "case": "Para quien viene de entrenar fuerte y quiere seguir fuerte sin volver a los máximos.",
  "level": "advanced",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Tres full body de fuerza submáxima",
  "split_rationale": "Cuerpo completo tres días con los patrones de fuerza que domina, pero siempre a RIR 3 y sin series por debajo de cinco repeticiones: mantiene la capacidad de fuerza sin acercarse nunca al rango que le ha lesionado. Se sustituyen sentadilla libre, peso muerto convencional y remo con barra por variantes que cargan igual sin comprimir la columna, porque a su edad y con su historial la lumbar es el factor limitante del plan.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Full body A - cajón y banca",
    "warmup": "8 minutos de bicicleta, movilidad de cadera y tres aproximaciones progresivas a la sentadilla a cajón.",
    "exercises": [
     {
      "name": "Sentadilla a cajón",
      "sets": 4,
      "rep_range": "5-6",
      "rir": "3",
      "rest_sec": 180,
      "technique_cue": "El cajón fija la profundidad y evita que busques el rango extremo donde se te carga la espalda."
     },
     {
      "name": "Press banca con barra",
      "sets": 4,
      "rep_range": "5-6",
      "rir": "3",
      "rest_sec": 180,
      "technique_cue": "Escápulas retraídas y pies clavados; se acaba la serie cuando la barra pierde velocidad, no cuando falla."
     },
     {
      "name": "Remo con pecho apoyado en banco",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Pecho fijo en el banco: mismo trabajo de espalda que el remo libre y cero carga lumbar."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Bajada frenada de dos segundos; el isquio fuerte descarga la espalda en todo lo demás."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cuerda a la altura de los ojos; a los cuarenta y tres esto es tan importante como la banca."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Sin lastre: buscamos rigidez del tronco, no carga añadida sobre la columna."
     }
    ],
    "cooldown": "Cinco minutos de paseo y estiramiento de cadera y pectoral."
   },
   {
    "day": "Miércoles",
    "name": "Full body B - hexagonal y vertical",
    "warmup": "8 minutos de remo, movilidad de hombro y cadera y tres aproximaciones a la hexagonal.",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 4,
      "rep_range": "5-6",
      "rir": "3",
      "rest_sec": 180,
      "technique_cue": "La hexagonal te deja el peso en línea con el cuerpo: misma fuerza, mucho menos brazo de palanca lumbar."
     },
     {
      "name": "Press militar sentado con barra",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "3",
      "rest_sec": 150,
      "technique_cue": "Sentado con respaldo para que la lumbar no compense el recorrido final."
     },
     {
      "name": "Dominadas neutras",
      "sets": 4,
      "rep_range": "6-10",
      "rir": "2",
      "rest_sec": 150,
      "technique_cue": "Deprime la escápula antes de doblar el codo; añade lastre solo cuando saques diez limpias."
     },
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Recorrido completo sin que la cadera se despegue del respaldo."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos pegados al tronco y abre la cuerda al final."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Antirrotación de pie: la clase de core que de verdad protege tu espalda."
     }
    ],
    "cooldown": "Movilidad torácica en el rodillo y estiramiento de dorsal, cinco minutos."
   },
   {
    "day": "Viernes",
    "name": "Full body C - volumen moderado",
    "warmup": "8 minutos de bicicleta y movilidad general de cadera y hombro.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Día de rango completo con poco peso; la columna descansa y la pierna sigue trabajando."
     },
     {
      "name": "Press inclinado con mancuernas",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 120,
      "technique_cue": "Banco a 30 grados y bajada controlada hasta notar el pectoral."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tronco quieto; el tirón sale del codo y no de la espalda baja."
     },
     {
      "name": "Hiperextensiones 45°",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Sin peso y sin hiperextender arriba: es trabajo de resistencia lumbar, no de carga."
     },
     {
      "name": "Curl de bíceps con barra EZ",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Codos fijos al costado y sin balanceo de tronco."
     },
     {
      "name": "Plancha lateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cadera alta y alineada; el cuadrado lumbar trabajado así aguanta mejor todo lo demás."
     }
    ],
    "cooldown": "Diez minutos de paseo y estiramiento de cadena posterior."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: fijar los pesos de trabajo a RIR 3 y aceptar que se queda lejos de sus marcas",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Nada por debajo de cinco repeticiones en ningún ejercicio del bloque; esa es la regla que le mantiene entrenando."
   },
   {
    "week": 2,
    "intent": "Progresión: subir kilos manteniendo el mismo RIR, sin bajar de repeticiones",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Mismas series; el progreso sale del peso a repeticiones iguales, nunca de bajar el rango."
   },
   {
    "week": 3,
    "intent": "Carga: semana algo más exigente sin acercarse al fallo en ningún momento",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "Una serie más en sentadilla a cajón y hexagonal; el RIR nunca baja de 2."
   },
   {
    "week": 4,
    "intent": "Descarga: semana ligera para que la espalda llegue fresca al mes siguiente",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Tres series en los principales y se elimina la hiperextensión; sale del centro sin notar la sesión."
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 40,
     "times_per_week": 2,
     "notes": "Caminata o bicicleta el fin de semana; le sienta bien a la espalda y no interfiere con la fuerza."
    }
   ]
  },
  "deload_instructions": "La semana 4 se hace al 90 por ciento con tres series en los ejercicios principales y RIR 4. Con él la descarga es innegociable y hay que decírselo claro: su historial de dos semanas parado nace precisamente de saltarse las semanas suaves cuando se ve fuerte. Regla de este plan: ninguna serie por debajo de cinco repeticiones y ningún intento de máximo, ni siquiera para probar; si algún día llega con la espalda cargada, se sustituye la sentadilla a cajón por prensa horizontal y se sigue."
 },
 {
  "category": "mantenimiento",
  "title": "Mantener · autonomía y fuerza para el día a día",
  "case": "Para quien pasa de los 65 y quiere seguir cargando peso y jugando con los nietos.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body funcional en tres días",
  "split_rationale": "Cuerpo completo tres veces por semana centrado en los tres gestos que le importan: levantarse de una superficie, cargar peso caminando y subir un escalón con control. Se usan máquinas de recorrido guiado para la fuerza base y se añade en cada sesión un ejercicio de estabilidad, que es lo que le falta. Todo con respiración continua y cargas moderadas por la hernia operada.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Día A - empujar, tirar y cargar",
    "warmup": "8 minutos de bicicleta a ritmo cómodo, movilidad de tobillo, cadera y hombro.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Suelta el aire al empujar; no aguantes nunca la respiración por la operación de la hernia."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Siéntate erguido y tira a la clavícula; suelta despacio sin que el peso te levante."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Este es el gesto de levantar al pequeño por encima de la cabeza; recorrido completo y suave."
     },
     {
      "name": "Puente de glúteos",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 75,
      "technique_cue": "Sube apretando el glúteo y respira arriba; nada de aguantar el aire."
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "3",
      "rest_sec": 75,
      "technique_cue": "Esto es literalmente llevar al niño en brazos: hombros nivelados y pasos cortos y seguros."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Alterna brazo y pierna contrarios muy despacio; si te tambaleas, acorta el recorrido."
     }
    ],
    "cooldown": "Ocho minutos caminando en cinta a ritmo bajo y estiramiento de cadera y pectoral."
   },
   {
    "day": "Miércoles",
    "name": "Día B - subir y estabilizar",
    "warmup": "8 minutos de cinta caminando con inclinación suave y movilidad de tobillo y cadera.",
    "exercises": [
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Empieza con el cajón muy bajo y sujeto a la barandilla; sube sin impulso y baja controlando."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Tronco quieto y codos hacia atrás; junta los omóplatos al final."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Recorrido cómodo y respiración continua; si notas presión en la cabeza, baja el peso."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Movimiento suave, sin tirones al final del recorrido."
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo con pausa arriba; el gemelo fuerte te da estabilidad al caminar."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Muy lento y respirando todo el rato; es el trabajo abdominal que la hernia operada tolera bien."
     }
    ],
    "cooldown": "Ocho minutos de bicicleta muy suave y estiramiento de isquios y gemelo."
   },
   {
    "day": "Viernes",
    "name": "Día C - levantarse del suelo",
    "warmup": "8 minutos de elíptica a ritmo cómodo y movilidad general de columna y cadera.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Kettlebell ligera al pecho; este es el gesto de levantarte del suelo con el niño encima."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Pecho apoyado, codos atrás y hombros lejos de las orejas."
     },
     {
      "name": "Contractora de pecho",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Cierre suave delante del pecho, sin llegar a chocar los brazos."
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Sube apretando el glúteo y suelta el aire arriba; el glúteo es lo que te levanta de la silla."
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Sujétate a la barra para no perder el equilibrio; recorrido completo."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "De pie y sin girar el tronco; esto es lo que te sostiene si un nieto te empuja sin querer."
     }
    ],
    "cooldown": "Diez minutos caminando y estiramiento de cadera, gemelo y hombro."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación: aprender a respirar en cada repetición y encontrar la altura de cajón segura",
    "load_pct": 100,
    "rir_target": "4",
    "volume_note": "Cargas muy conservadoras; la primera semana se comprueba el equilibrio en cada ejercicio de pie."
   },
   {
    "week": 2,
    "intent": "Progresión: subir una placa donde acabe con repeticiones sobradas y subir un dedo el cajón",
    "load_pct": 102.5,
    "rir_target": "3-4",
    "volume_note": "Mismas series; el cambio es mínimo porque a esta edad la constancia pesa más que la carga."
   },
   {
    "week": 3,
    "intent": "Carga: semana en la que debe notar esfuerzo real en prensa y paseo del granjero",
    "load_pct": 105,
    "rir_target": "3",
    "volume_note": "Se añade una serie a prensa y a paseo del granjero, que son los dos ejercicios más ligados a lo que pidió."
   },
   {
    "week": 4,
    "intent": "Descarga: semana suave y prueba de los gestos reales que quería recuperar",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Dos series por ejercicio y al final se cronometra cuánto tarda en levantarse del suelo sin apoyarse."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 4,
     "notes": "Caminar cada día que pueda, mejor acompañando a los nietos al parque; es el mejor cardio para su objetivo."
    }
   ]
  },
  "deload_instructions": "La semana 4 se hace al 90 por ciento con dos series por ejercicio y se reserva el final de la última sesión para comprobar los gestos que le trajeron aquí: levantarse del suelo sin apoyo y subir cinco escalones seguidos sin agarrarse. Ese registro es su verdadero indicador de progreso, más que cualquier kilo de la máquina. Si aparece bulto, molestia o sensación de peso en la zona de la hernia operada, se para de inmediato y se le manda a revisión antes de continuar."
 },
 {
  "category": "perdida_grasa",
  "title": "Perder grasa · vida sedentaria de oficina",
  "case": "Para quien pasa el día sentado y quiere perder barriga empezando por lo básico.",
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
  "title": "Perder grasa · posparto, sin impacto",
  "case": "Para quien vuelve tras el parto, con alta médica: core suave y cero impactos.",
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
  "title": "Perder grasa · mucho peso que perder",
  "case": "Para quien parte de un sobrepeso alto y necesita máquinas guiadas y bajo impacto.",
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
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Termina apretando el glúteo un segundo, con las costillas bajas."
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
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Flexión completa y controlada; sin rebote al final."
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
  "title": "Perder grasa · recomposición, 4 días",
  "case": "Para el intermedio que quiere perder grasa y ganar algo de músculo a la vez.",
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
  "title": "Perder grasa · definición, 4 días",
  "case": "Para quien viene de una etapa de volumen y quiere definir sin perder músculo.",
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
  "title": "Perder grasa · solo 2 días",
  "case": "Para quien solo puede asegurar dos entrenamientos a la semana.",
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
  "title": "Perder grasa · en casa sin material",
  "case": "Para quien entrena en casa sin ningún equipamiento.",
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
  "title": "Perder grasa · en casa con mancuernas",
  "case": "Para quien tiene un par de mancuernas en casa y horario partido.",
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
  "title": "Perder grasa · a partir de los 55",
  "case": "Para quien pasa de los 55, tiene algo de rigidez articular y quiere perder grasa ganando fuerza.",
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
      "sets": 3,
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
      "sets": 3,
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
  "title": "Perder grasa · sin perder fuerza",
  "case": "Para el avanzado con buenos básicos que teme perder músculo al definir.",
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
  "title": "Perder grasa · turnos y sueño irregular",
  "case": "Para quien trabaja a turnos y necesita sesiones cortas y constantes.",
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
  "title": "Perder grasa · viajando, gimnasio de hotel",
  "case": "Para quien viaja entre semana y entrena con lo mínimo de un hotel.",
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
      "name": "Peso muerto rumano a una pierna sin carga",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Cadera atrás con la espalda recta; la pierna libre acompaña alineada con el tronco."
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
  "title": "Perder grasa · cuidando la rodilla",
  "case": "Para quien nota la rodilla en sentadillas profundas y en los impactos.",
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
  "title": "Perder grasa · cuidando la espalda baja",
  "case": "Para quien ha tenido lumbalgia y quiere perder barriga sin cargar la columna.",
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
  "title": "Perder grasa · sin cardio, a base de pasos",
  "case": "Para quien detesta el cardio: pesas y muchos pasos diarios.",
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
  "title": "Perder grasa · para quien disfruta del cardio",
  "case": "Para quien no quiere renunciar a sus sesiones de cardio y le sumamos pesas.",
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
  "title": "Perder grasa · fase de choque, 6 días",
  "case": "Para el avanzado que hace una fase corta e intensa bajo supervisión.",
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
  "title": "Perder grasa · sesiones de 40 minutos",
  "case": "Para quien solo tiene ventanas de 30-40 minutos y necesita cumplirlas siempre.",
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
   "daily_steps": 10000,
   "sessions": [
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
  "title": "Perder grasa · volver tras años parado",
  "case": "Para quien lleva años sin entrenar y quiere retomar sin agujetas paralizantes.",
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
  "title": "Perder grasa · prioridad cintura y core",
  "case": "Para quien acumula en la zona media y quiere además un core fuerte.",
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
  "category": "principiantes",
  "title": "Empezar · solo con máquinas guiadas",
  "case": "Para quien se agobia en la zona de peso libre y quiere empezar con material guiado.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body guiado A-B-C",
  "split_rationale": "Tres sesiones de cuerpo completo con máquinas y poleas, que ocupan siempre la misma esquina de la sala y no obligan a pedir ni compartir material. La sesión C introduce de forma progresiva el primer trabajo con mancuerna y multipower para que el paso a la zona de peso libre llegue cuando ya domine el patrón, no por obligación.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Full body A — máquinas seleccionadas",
    "warmup": "5 minutos de bicicleta suave, 10 círculos de hombro por lado y 10 sentadillas sin carga hasta la altura que resulte cómoda.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Pies a la anchura de las caderas y talones bien apoyados; baja hasta que la rodilla llegue a noventa grados sin que la cadera se despegue del respaldo."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Pecho alto y codos hacia los bolsillos; lleva la barra a la clavícula sin echar el tronco atrás más de unos pocos grados."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Ajusta el asiento para que las asas queden a la altura del esternón y deja los omóplatos apoyados en el respaldo durante todo el recorrido."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Cadera pegada al banco; sube sin despegar la pelvis y baja contando dos segundos."
     },
     {
      "name": "Face pull en polea",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cuerda a la altura de los ojos, codos altos y separa las manos al final del recorrido sin encoger los hombros."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos bajo los hombros, glúteo apretado y costillas hacia abajo; si la lumbar se hunde, corta la serie."
     }
    ],
    "cooldown": "5 minutos de caminata en cinta a ritmo cómodo y estiramiento suave de pectoral en el marco de una puerta, 30 segundos por lado."
   },
   {
    "day": "Miércoles",
    "name": "Full body B — poleas y estabilidad",
    "warmup": "5 minutos de elíptica, 10 rotaciones de cadera por lado y una serie ligera de la prensa a modo de aproximación.",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Controla la bajada tres segundos y no bloquees la rodilla de golpe al empujar."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tronco firme y quieto; lleva el agarre al ombligo juntando los omóplatos sin balancearte hacia atrás."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Asiento alto para que el recorrido empiece a la altura de la barbilla; sube sin arquear la zona lumbar."
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Termina el empuje con las costillas bajas y el glúteo apretado un segundo, sin buscar más recorrido con la lumbar."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos pegados al costado y quietos; solo se mueve el antebrazo."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Lumbar pegada al suelo todo el rato; baja brazo y pierna contrarios solo hasta donde puedas mantenerla."
     }
    ],
    "cooldown": "Cinco minutos de bicicleta muy suave y respiración nasal lenta tumbado con las piernas apoyadas en un banco."
   },
   {
    "day": "Viernes",
    "name": "Full body C — primer contacto con el peso libre",
    "warmup": "5 minutos de caminata inclinada, 10 band pull-apart y una serie de sentadilla sin carga sujetando una mancuerna ligera.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Mancuerna vertical pegada al pecho y codos dentro; baja entre las rodillas manteniendo el pecho alto. Hazla en la zona de estiramientos si la sala está llena."
     },
     {
      "name": "Jalón agarre estrecho neutro",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Agarre neutro, tira con los codos hacia las costillas y aguanta medio segundo abajo."
     },
     {
      "name": "Press banca en multipower",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Los topes de seguridad puestos un dedo por debajo del pecho: puedes fallar sin depender de nadie que te ayude."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho apoyado y sin despegarlo; el tirón termina cuando los codos pasan la línea del tronco."
     },
     {
      "name": "Curl bayesian en polea",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Un paso por delante de la polea, codo ligeramente detrás del cuerpo y sin mover el hombro."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Estira los brazos sin dejar que el tronco rote hacia la polea; es un ejercicio de aguantar, no de empujar fuerte."
     }
    ],
    "cooldown": "Cinco minutos de caminata y movilidad de cadera en el suelo. Antes de irte, date una vuelta por la zona de mancuernas: solo mirar dónde está cada peso."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Aprender el recorrido de cada máquina y anotar el número de asiento y el peso usado. Sesiones de 45 minutos como mucho."
   },
   {
    "week": 2,
    "intent": "Progresión",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Mismo esquema con una serie más en prensa y jalón. Esta semana la sentadilla goblet se hace fuera del pasillo de máquinas."
   },
   {
    "week": 3,
    "intent": "Carga",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Semana de más peso en los tres empujes y tirones principales; el resto se mantiene igual para no alargar la sesión."
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Se retira una serie de cada ejercicio accesorio. Buena semana para probar el press con mancuernas sin presión de rendimiento."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 20,
     "times_per_week": 3,
     "notes": "Cinta o elíptica al terminar cada sesión, a un ritmo que permita hablar."
    }
   ]
  },
  "deload_instructions": "En la semana 4 baja la carga al 90% y quita una serie de los accesorios manteniendo los tres ejercicios principales. Si alguna semana entrenas menos de dos días, repite la semana en lugar de saltar a la siguiente."
 },
 {
  "category": "principiantes",
  "title": "Empezar · por recomendación médica",
  "case": "Para quien llega derivado por su médico y necesita que le digan exactamente qué hacer cada día.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body de introducción A-B-C",
  "split_rationale": "Tres sesiones de cuerpo completo con el mismo esqueleto de patrones (empujar, tirar, pierna, cadera y core) para que en tres semanas se los sepa de memoria. El volumen por grupo se reparte entre los tres días para evitar el pico de agujetas que arruinaría su jornada laboral.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Sesión A — patrones básicos",
    "warmup": "5 minutos de bicicleta, 10 elevaciones de brazos por encima de la cabeza y 10 puentes de glúteo sin carga.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Baja solo hasta donde la espalda siga apoyada; empuja con todo el pie, no con la punta."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Muslos bien sujetos bajo el rodillo y codos hacia abajo; imagina que guardas los omóplatos en los bolsillos traseros."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Muñeca alineada con el antebrazo y empuje sin bloquear el codo de golpe."
     },
     {
      "name": "Puente de glúteos",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Sube empujando con los talones y aprieta el glúteo arriba un segundo; sin arquear la lumbar."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Extiende brazo y pierna contrarios sin que la cadera se ladee; movimiento lento."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Apoya en codos, aprieta glúteo y abdomen a la vez; mejor 20 segundos bien que 45 con la espalda hundida."
     }
    ],
    "cooldown": "Estiramiento de gemelo y de la parte anterior del hombro, 30 segundos por lado, más cinco minutos de caminata."
   },
   {
    "day": "Miércoles",
    "name": "Sesión B — pierna y espalda",
    "warmup": "5 minutos de elíptica, 10 rotaciones de cadera por lado y una serie ligera de sentadilla goblet.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Pies un poco abiertos, baja el culo entre los talones y mantén la mancuerna pegada al esternón."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Rodillas algo flexionadas; el tirón sale de la espalda, no de tirar con la lumbar hacia atrás."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Solo dos series: es el gesto que más se parece a tu jornada con los brazos altos y no queremos sobrecargarlo."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Ajusta el rodillo por encima del talón y vuelve al inicio sin dejar que el peso caiga solo."
     },
     {
      "name": "Abducción de cadera en máquina",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Tronco erguido, abre sin echar el cuerpo hacia atrás y aguanta un segundo en la apertura."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Suelta el aire mientras bajas la pierna; si notas la lumbar despegarse, acorta el recorrido."
     }
    ],
    "cooldown": "Cinco minutos de bicicleta suave y estiramiento de isquios tumbada con una banda."
   },
   {
    "day": "Viernes",
    "name": "Sesión C — cuerpo completo",
    "warmup": "5 minutos de caminata inclinada, 10 band pull-apart y 10 subidas al escalón sin carga.",
    "exercises": [
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Cajón a la altura de la rodilla; sube empujando con el pie de arriba y baja controlando, sin impulso del pie de abajo."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Pecho apoyado y hombros lejos de las orejas durante todo el recorrido."
     },
     {
      "name": "Contractora de pecho",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Codos a la altura del hombro, junta sin llegar a chocar las manos y abre despacio."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Lleva la cadera atrás como si cerraras un cajón con el culo; las mancuernas rozan el muslo y bajas hasta media espinilla con la espalda recta."
     },
     {
      "name": "Face pull en polea",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos por encima de las muñecas; este es el ejercicio que compensa las horas con los brazos por delante."
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 3,
      "rep_range": "30-40s",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Una sola mancuerna en una mano, hombros nivelados y pasos cortos; cambia de mano en cada serie."
     }
    ],
    "cooldown": "Movilidad de columna dorsal en el suelo y estiramiento de cuádriceps de pie, 30 segundos por lado."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Cargas deliberadamente cortas: el objetivo es acabar cada sesión con la sensación de que podías más. Anota qué peso usas en cada máquina."
   },
   {
    "week": 2,
    "intent": "Progresión",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Sube un escalón de peso donde hayas hecho las repeticiones altas sin esfuerzo. Todo lo demás igual."
   },
   {
    "week": 3,
    "intent": "Carga",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "Semana de mayor exigencia en prensa, jalón y peso muerto rumano; el trabajo de hombro se mantiene en dos series."
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Se quita una serie de cada ejercicio. Semana ideal para revisar la técnica del rumano con el coach delante."
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 2,
     "notes": "Caminata al aire libre los días que no entrenes, sin sumarla a la sesión de fuerza."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90% de la carga y una serie menos por ejercicio. Si una semana llegas con las piernas muy cansadas del trabajo, cambia la prensa por dos series de puente de glúteos y sigue el resto igual."
 },
 {
  "category": "principiantes",
  "title": "Empezar · con la tensión alta",
  "case": "Para quien tiene la tensión al límite y debe empezar sin bloquear la respiración ni llegar al fallo.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body en máquinas con descansos amplios",
  "split_rationale": "Cuerpo completo tres veces por semana en material guiado, con rangos de 10 a 15 repeticiones y descansos de 90 a 120 segundos: así la carga por serie es moderada, no hace falta apretar la respiración y la tensión no dispara. Se evitan isométricos largos y cualquier serie llevada al límite.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Sesión A — máquinas sentado",
    "warmup": "8 minutos de bicicleta a ritmo suave subiendo poco a poco, más 10 círculos de hombro por lado. No entres en frío a la primera serie.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Suelta el aire al empujar y coge aire al bajar; en ningún momento aguantes la respiración."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Tira con el tronco quieto y exhala en el esfuerzo; si aprietas la mandíbula, el peso es excesivo."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Empuje continuo, sin pausas apretando arriba y sin bloquear los codos con fuerza."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Ritmo constante, dos segundos de bajada; nada de tirones."
     },
     {
      "name": "Face pull en polea",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 75,
      "technique_cue": "Trabajo ligero de postura para compensar las horas inclinado sobre el motor."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Respiración marcada: suelta el aire cada vez que estiras la pierna. Nunca aguantes el aire en el core."
     }
    ],
    "cooldown": "5 minutos de bicicleta muy suave hasta que las pulsaciones bajen y respiración nasal sentado, 2 minutos."
   },
   {
    "day": "Miércoles",
    "name": "Sesión B — cadera y torso",
    "warmup": "8 minutos de elíptica progresiva y 10 sentadillas sin carga apoyándose en un banco.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Peso ligero y bajada hasta banco alto; exhala mientras subes, sin apretar los dientes."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Codos hacia abajo y tronco casi vertical; que el esfuerzo se note en la espalda, no en el cuello."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Solo dos series y peso moderado: el gesto por encima de la cabeza es el que más sube la tensión."
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 105,
      "technique_cue": "Empuja con los talones y suelta el aire arriba; no aguantes el bloqueo más de un segundo."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 75,
      "technique_cue": "Codos fijos al costado; ejercicio de cierre, sin buscar carga máxima."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Cinco segundos por repetición respirando con normalidad."
     }
    ],
    "cooldown": "Caminata suave 6 minutos y estiramiento de pectoral y flexor de cadera, 30 segundos por lado."
   },
   {
    "day": "Viernes",
    "name": "Sesión C — cuerpo completo ligero",
    "warmup": "8 minutos de caminata inclinada suave y 10 band pull-apart.",
    "exercises": [
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 105,
      "technique_cue": "Escalón bajo, sin mancuernas al principio; sube y baja con ritmo constante y respirando."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 105,
      "technique_cue": "Pecho apoyado para que no tengas que hacer fuerza con la espalda baja."
     },
     {
      "name": "Contractora de pecho",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Cierra sin llegar a tocar las manos y abre despacio; exhala al cerrar."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Mancuernas ligeras. Cadera atrás, espalda recta y aire fuera al subir; este es el gesto que te va a evitar sustos levantando piezas en el taller."
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo y pausa arriba de un segundo."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 75,
      "technique_cue": "Trabajo de core sin flexionar la columna ni apretar el abdomen conteniendo el aire."
     }
    ],
    "cooldown": "8 minutos de caminata a ritmo cómodo y dos minutos sentado respirando lento antes de irte."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Cargas bajas y foco absoluto en respirar durante la serie. Toma la tensión en casa dos mañanas y anótala."
   },
   {
    "week": 2,
    "intent": "Progresión",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Sube un punto la carga solo en prensa, remo y press de pecho. El trabajo por encima de la cabeza se queda igual."
   },
   {
    "week": 3,
    "intent": "Carga",
    "load_pct": 105,
    "rir_target": "3",
    "volume_note": "Semana más exigente pero manteniendo tres repeticiones en reserva: en este caso nunca se llega al fallo, en ninguna serie ni ejercicio."
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Una serie menos por ejercicio y más minutos de caminata. Revisa la tensión otra vez y llévale el registro al médico."
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 35,
     "times_per_week": 5,
     "notes": "Caminata a paso vivo, mejor por la tarde. Es la parte del plan con más impacto sobre la tensión, así que tiene la misma prioridad que las pesas."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90% con una serie menos por ejercicio, manteniendo las caminatas intactas. Si algún día notas mareo, dolor de cabeza o pulsaciones desbocadas, para la sesión, avisa y consúltalo con tu médico antes de volver."
 },
 {
  "category": "principiantes",
  "title": "Volver · tras diez años sin entrenar",
  "case": "Para quien entrenó hace mucho y vuelve desde cero con una progresión ordenada.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body de reacondicionamiento A-B-C",
  "split_rationale": "Aunque la técnica la recuerda, el tejido lleva diez años sin cargar: tres sesiones de cuerpo completo permiten repetir cada patrón tres veces por semana con poco volumen por sesión, que es exactamente lo que acelera la readaptación sin dejarla dolorida cuatro días.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Sesión A — reencuentro con las mancuernas",
    "warmup": "5 minutos de remo ergómetro suave, 10 band pull-apart y una serie de aproximación muy ligera del primer ejercicio.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Empieza con una mancuerna que te parezca ridícula: hoy la sentadilla es para recordar el patrón, no para demostrar nada."
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Omóplatos juntos contra el banco y codos a 45 grados; baja hasta que la mancuerna quede a la altura del pecho."
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Apoya rodilla y mano en el banco, espalda plana y tira el codo hacia la cadera sin rotar el tronco."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Bajada de tres segundos: los isquios son lo que más nota el parón largo."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Costillas abajo y glúteo apretado; nada de aguantar minutos, calidad por encima de tiempo."
     },
     {
      "name": "Face pull en polea",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Compensación directa de las horas al volante: codos altos y sin encoger los hombros."
     }
    ],
    "cooldown": "5 minutos de caminata y estiramiento de flexor de cadera en zancada, 40 segundos por lado."
   },
   {
    "day": "Miércoles",
    "name": "Sesión B — bisagra y tirón vertical",
    "warmup": "5 minutos de bicicleta, 10 puentes de glúteo y 10 rotaciones de cadera por lado.",
    "exercises": [
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Cadera atrás, mancuernas rozando el muslo y parada donde notes el estiramiento del isquio, no más abajo."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tira con los codos y aguanta medio segundo abajo antes de dejar subir la barra."
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Respaldo casi vertical; sube sin arquear la lumbar ni chocar las mancuernas arriba."
     },
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 105,
      "technique_cue": "Recorrido cómodo y talones apoyados; aquí sí puedes acercarte algo más al esfuerzo real."
     },
     {
      "name": "Curl martillo",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos quietos al costado, sin balancear el cuerpo."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Lumbar pegada al suelo y respiración fluida."
     }
    ],
    "cooldown": "Movilidad dorsal sobre rodillo y estiramiento de isquios, 30 segundos por lado."
   },
   {
    "day": "Viernes",
    "name": "Sesión C — unilateral y glúteo",
    "warmup": "5 minutos de elíptica, 10 zancadas inversas sin carga y 10 band pull-apart.",
    "exercises": [
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 105,
      "technique_cue": "Paso atrás largo, rodilla de atrás al suelo con suavidad y tronco vertical; empieza sin peso."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Lleva el agarre al ombligo sin dejar que los hombros se adelanten al final."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Máquina en el tercer día para acumular volumen de empuje sin castigar más el hombro con mancuerna."
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Barbilla ligeramente metida y glúteo apretado arriba un segundo."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos pegados; solo se mueve el antebrazo."
     },
     {
      "name": "Plancha lateral",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cadera alta y alineada; si molesta el hombro, apoya la rodilla de abajo."
     }
    ],
    "cooldown": "5 minutos de caminata y estiramiento de glúteo sentada, 40 segundos por lado."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Semana de freno consciente: aunque puedas mover más, te quedas donde marca la hoja. Nada de series extra ni de probar tus pesos de los 28."
   },
   {
    "week": 2,
    "intent": "Progresión",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Primera subida de carga en sentadilla, press y remo. Si las agujetas de la semana 1 duraron más de dos días, repite cargas."
   },
   {
    "week": 3,
    "intent": "Carga",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "Ya se puede apretar algo más. Añade una serie al peso muerto rumano, que es el patrón que más ha perdido."
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Una serie menos por ejercicio. A partir del mes que viene sí se puede plantear barra en sentadilla y peso muerto."
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Caminata o bicicleta los días sin pesas; aprovecha las esperas entre visitas comerciales para caminar en vez de esperar en el coche."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90% con una serie menos por ejercicio. Regla firme para este caso: si un día te sientes fuerte y con ganas de más, esa energía se guarda para la semana siguiente en forma de kilos, no de series improvisadas."
 },
 {
  "category": "principiantes",
  "title": "Volver · tras una lesión ya dada de alta",
  "case": "Para quien tiene el alta médica tras una lesión y necesita volver a cargar progresivamente.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body con agarre neutro",
  "split_rationale": "Cuerpo completo tres veces por semana seleccionando exclusivamente ejercicios que no exigen extensión de muñeca ni apoyo con la palma en el suelo. Las máquinas y las poleas permiten cargar pierna y espalda a tope mientras la muñeca sigue readaptándose, y los agarres neutros van devolviendo confianza al brazo derecho.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Sesión A — carga sin muñeca",
    "warmup": "5 minutos de bicicleta, movilidad de muñeca sin dolor (giros suaves, 20 por lado) y 10 band pull-apart.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Aquí no interviene la mano: agárrate de las asas laterales sin apretar y empuja fuerte con las piernas."
     },
     {
      "name": "Jalón agarre estrecho neutro",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Agarre neutro con palmas enfrentadas: es la posición que menos tensa la muñeca. Si notas pinchazo, usa correas."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Muñeca perfectamente alineada con el antebrazo; si se dobla hacia atrás, baja el peso ya."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Cadera pegada al banco y bajada controlada de dos segundos."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Apoyo en antebrazos, nunca con la mano abierta en el suelo. El puño relajado."
     },
     {
      "name": "Face pull en polea",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cuerda con agarre neutro; tira con el codo, no con la mano."
     }
    ],
    "cooldown": "5 minutos de caminata y descarga suave del antebrazo con masaje manual, 1 minuto por cara."
   },
   {
    "day": "Miércoles",
    "name": "Sesión B — neutro y unilateral",
    "warmup": "5 minutos de elíptica, movilidad de muñeca y una serie ligera de sentadilla goblet.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Sujeta la mancuerna por el disco superior con las dos manos y las palmas enfrentadas; el peso se apoya en el pecho, no en las muñecas."
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Agarre neutro y muñeca firme y recta durante todo el tirón; empieza más suave con el lado derecho."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Elige la máquina de agarre neutro si la sala la tiene; si no, ajusta para que la muñeca no quede volcada."
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Trabajo de cadera potente sin implicación del brazo; aquí puedes cargar sin miedo."
     },
     {
      "name": "Curl martillo",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Martillo, nunca supino: la muñeca queda neutra y el codo trabaja igual."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Brazos extendidos sin carga; el trabajo es del abdomen, la mano solo acompaña."
     }
    ],
    "cooldown": "Bicicleta suave 5 minutos y estiramiento de dorsal colgado ligero de una polea baja, sin peso."
   },
   {
    "day": "Viernes",
    "name": "Sesión C — volumen de espalda y cadera",
    "warmup": "5 minutos de caminata inclinada, movilidad de muñeca y 10 puentes de glúteo.",
    "exercises": [
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Mancuernas a los lados con agarre neutro; si en las últimas repeticiones te falla el agarre derecho, usa correas antes que forzar."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Triángulo neutro y muñeca recta; el tirón termina en las costillas."
     },
     {
      "name": "Contractora de pecho",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Empuja con el antebrazo apoyado en el acolchado, sin agarrar con fuerza."
     },
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Empieza sin peso; cuando lo lleves, mancuernas colgando con agarre neutro y sin apretar en exceso."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cuerda y no barra recta: la barra obliga a la muñeca a una posición que hoy no toca."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Sujeta el asa con las dos manos, muñecas rectas y resiste la rotación con el tronco."
     }
    ],
    "cooldown": "Caminata 5 minutos y trabajo de agarre suave con una pelota blanda, 20 aperturas y cierres por mano."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Sesiones de prueba: cualquier ejercicio que dé molestia en la muñeca se retira sin discusión y se anota. Pierna y cadera pueden ir a su ritmo normal."
   },
   {
    "week": 2,
    "intent": "Progresión",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Sube carga en tren inferior y en máquinas; el trabajo de brazo derecho se mantiene igual una semana más."
   },
   {
    "week": 3,
    "intent": "Carga",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "Primera subida real en remo y curl martillo si la muñeca lleva dos semanas sin protestar. Sigue sin apoyos con la palma."
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio. Antes del siguiente mes valoramos con tu traumatólogo si ya se pueden introducir apoyos y agarre pronado."
   }
  ],
  "cardio": {
   "daily_steps": 11000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 20,
     "times_per_week": 2,
     "notes": "Bicicleta estática con manos apoyadas sin cargar peso, o caminata. Nada de remo ergómetro por ahora."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90% con una serie menos por ejercicio. Norma innegociable: si la muñeca duele durante la serie o al día siguiente, ese ejercicio se retira y se sustituye por su versión en máquina, y si el dolor persiste más de tres días se vuelve a consultar con el médico."
 },
 {
  "category": "principiantes",
  "title": "Empezar · adolescente, técnica antes que carga",
  "case": "Para el adolescente que empieza con permiso familiar: peso corporal y técnica primero.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body educativo A-B-C",
  "split_rationale": "A esta edad el objetivo es el aprendizaje motor, no la carga: tres sesiones de cuerpo completo que repiten los patrones básicos con peso corporal, mancuernas ligeras y máquinas. Se prioriza el rango completo, la posición de la columna y el control de la bajada, que es la base sobre la que dentro de dos años podrá cargar de verdad.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Sesión A — dominar el propio cuerpo",
    "warmup": "5 minutos de bicicleta, 10 sentadillas sin carga, 10 band pull-apart y 5 planchas de 10 segundos.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 105,
      "technique_cue": "Baja hasta que los muslos pasen la paralela si tu cadera te lo permite sin redondear la espalda. La profundidad manda sobre el peso."
     },
     {
      "name": "Remo invertido",
      "sets": 3,
      "rep_range": "8-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Barra a la altura de la cadera, cuerpo recto como una tabla y pecho a la barra en cada repetición."
     },
     {
      "name": "Flexiones",
      "sets": 3,
      "rep_range": "6-10",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Si no salen limpias desde el suelo, apoya las manos en un banco; nunca hagas repeticiones con la cadera colgando."
     },
     {
      "name": "Puente de glúteos",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Empuja con los talones y aprieta el glúteo arriba; la lumbar no debe arquearse."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cuerpo en línea recta desde la oreja al tobillo; en cuanto se rompa la posición, se acaba la serie."
     },
     {
      "name": "Band pull-apart",
      "sets": 2,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Brazos rectos y apertura hasta el pecho sin encoger los hombros."
     }
    ],
    "cooldown": "5 minutos de caminata y estiramiento de cuádriceps e isquios, 30 segundos por lado."
   },
   {
    "day": "Miércoles",
    "name": "Sesión B — patrones con mancuerna",
    "warmup": "5 minutos de elíptica, 10 zancadas inversas sin carga y 10 rotaciones de hombro.",
    "exercises": [
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Paso atrás, rodilla al suelo con suavidad y tronco vertical. Sin peso hasta que salgan diez limpias por pierna."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Es la preparación para tus primeras dominadas: tira con los codos y controla la subida."
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Mancuernas ligeras, costillas abajo y sin arquear la espalda para poder subirlas."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 105,
      "technique_cue": "El movimiento es de cadera hacia atrás, no de agacharse. Si la espalda se redondea, para la serie."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Lento y con la lumbar pegada al suelo; este ejercicio te protege el tronco en los cambios de dirección de la pista."
     },
     {
      "name": "Curl martillo",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos quietos y sin balanceo. Dos series bastan a tu edad."
     }
    ],
    "cooldown": "5 minutos de bicicleta suave y movilidad de tobillo, 20 repeticiones por lado."
   },
   {
    "day": "Viernes",
    "name": "Sesión C — control y unilateral",
    "warmup": "5 minutos de caminata inclinada, 10 subidas a escalón bajo y 10 band pull-apart.",
    "exercises": [
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Sube sin impulso del pie de abajo y baja frenando: ese freno es lo que te va a dar el cambio de ritmo en la pista."
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Espalda plana como una mesa; tira el codo hacia la cadera sin girar el tronco."
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 105,
      "technique_cue": "Tu primer press es con mancuernas, no con barra: te obliga a controlar cada brazo y respeta el hombro."
     },
     {
      "name": "Curl femoral con deslizadores",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Cadera arriba todo el recorrido; si no puedes mantenerla, acorta el deslizamiento."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Sin que la cadera se ladee. Cinco segundos por repetición."
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo hasta abajo y pausa arriba; el gemelo fuerte protege el tobillo en pista."
     }
    ],
    "cooldown": "5 minutos de caminata y estiramiento de aductor y gemelo, 30 segundos por lado."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Semana de aprendizaje: se graba en vídeo la sentadilla y el peso muerto rumano para revisarlos juntos. Ninguna serie cerca del fallo."
   },
   {
    "week": 2,
    "intent": "Progresión",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Solo sube peso quien haya hecho todas las repeticiones con técnica limpia la semana anterior. Si no, se repite carga."
   },
   {
    "week": 3,
    "intent": "Carga",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "Semana algo más exigente en sentadilla, remo y press. Sigue sin trabajar al fallo: a tu edad no aporta nada y aumenta el riesgo."
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio, coincidiendo con la parte alta de la competición escolar. Buena semana para repasar técnica con el coach."
   }
  ],
  "cardio": {
   "daily_steps": 11000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 15,
     "times_per_week": 1,
     "notes": "Poco cardio añadido: los entrenamientos y partidos de fútbol sala ya cubren de sobra la parte aeróbica."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90% con una serie menos por ejercicio; si esa semana hay torneo o dos partidos, se entrena una sola vez y se prioriza el descanso. Norma para este caso: nada de series máximas ni de comparar kilos con los compañeros, la carga sube solo cuando la técnica está limpia."
 },
 {
  "category": "principiantes",
  "title": "Empezar · con horario de estudiante",
  "case": "Para quien está en exámenes y necesita dos sesiones cortas y movibles.",
  "level": "beginner",
  "days_per_week": 2,
  "place": "gym",
  "split_name": "Full body de dos días intercambiables",
  "split_rationale": "Con dos días la única opción sensata es cuerpo completo en ambas sesiones, así ningún patrón se queda sin entrenar si una semana solo puede ir una vez. Las dos sesiones son intercambiables entre sí y entre días de la semana: lo único fijo es que haya al menos 48 horas entre ellas.",
  "sessions": [
   {
    "day": "Martes",
    "name": "Sesión A — cuerpo completo",
    "warmup": "5 minutos de bicicleta subiendo el ritmo poco a poco y 10 band pull-apart. Nada más: el calentamiento no puede comerse la sesión.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Mancuerna al pecho, bajada controlada y subida decidida; es el ejercicio que más despeja de toda la sesión."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Codos hacia abajo y pecho alto; contrarresta las horas encorvada sobre los apuntes."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Asiento a la altura del esternón; empuje continuo sin bloquear el codo con fuerza."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Cadera atrás con la espalda recta; para donde notes el estiramiento del isquio."
     },
     {
      "name": "Face pull en polea",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos altos y sin encoger los hombros; dos series rápidas."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Glúteo y abdomen apretados a la vez; corta la serie cuando la cadera se caiga."
     }
    ],
    "cooldown": "Cinco minutos de caminata suave y respiración nasal lenta sentada, 2 minutos. Sirve para bajar revoluciones antes de volver a estudiar."
   },
   {
    "day": "Viernes",
    "name": "Sesión B — cuerpo completo",
    "warmup": "5 minutos de elíptica y 10 rotaciones de cadera por lado.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Talones bien apoyados, bajada hasta noventa grados; es la opción rápida cuando llegas justa de tiempo."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tira al ombligo con el tronco quieto; junta los omóplatos al final."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Costillas abajo y sin arquear la lumbar para completar la repetición."
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Empuje con los talones y un segundo de pausa arriba."
     },
     {
      "name": "Curl martillo",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos quietos, sin balanceo del tronco."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Suelta el aire al estirar la pierna y mantén la lumbar pegada al suelo."
     }
    ],
    "cooldown": "Estiramiento de cuello y dorsal, 30 segundos por lado, y cinco minutos de caminata."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Dos sesiones cortas, sin buscar sensaciones fuertes. Anota el peso de cada máquina en el móvil para no perder tiempo la próxima vez."
   },
   {
    "week": 2,
    "intent": "Progresión",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Sube un escalón donde te hayan sobrado repeticiones. Si esa semana tienes dos exámenes, quédate en las mismas cargas: no pasa nada."
   },
   {
    "week": 3,
    "intent": "Carga",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "Semana algo más exigente en sentadilla, jalón y prensa. El resto se mantiene para no alargar la sesión de los cuarenta minutos."
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Una serie menos por ejercicio, ideal si coincide con la semana de exámenes finales. Prioriza dormir por encima de entrenar."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 2,
     "notes": "Volver caminando de la biblioteca en lugar de coger el bus cuenta como sesión. Sirve para desconectar, no para quemar."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90% con una serie menos. Si una semana solo puedes entrenar un día, haz la sesión A completa y no intentes recuperar la otra; el plan está pensado para sobrevivir a los exámenes, no para batir marcas."
 },
 {
  "category": "principiantes",
  "title": "Empezar · con un bebé en casa, 2 días",
  "case": "Para quien duerme poco y solo tiene dos huecos fijos a la semana.",
  "level": "beginner",
  "days_per_week": 2,
  "place": "gym",
  "split_name": "Full body de dos días con carga controlada",
  "split_rationale": "Dos sesiones de cuerpo completo cubren todos los patrones aunque una semana se caiga una. Con sueño fragmentado la recuperación es la variable limitante, así que el volumen por sesión es contenido y ningún ejercicio llega al fallo: buscamos que el lunes siguiente pueda cargar al niño sin agujetas.",
  "sessions": [
   {
    "day": "Martes",
    "name": "Sesión A — noche, carga moderada",
    "warmup": "6 minutos de bicicleta suave y 10 band pull-apart. A las 21:30 el cuerpo va frío del sofá: no te saltes esto.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Mancuerna vertical al pecho, bajada de dos segundos; controlar es más importante que el kilaje a estas horas."
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Omóplatos apretados contra el banco y codos a 45 grados; con sueño acumulado, deja siempre tres repeticiones en la recámara."
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Rodilla y mano apoyadas en el banco; tira el codo a la cadera con la espalda plana."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Bajada de dos segundos sin despegar la cadera del banco."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Costillas abajo; es el trabajo que te va a proteger la espalda cada vez que cojas al niño del suelo."
     },
     {
      "name": "Face pull en polea",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Compensación de las horas de teclado y de brazos por delante llevando al bebé."
     }
    ],
    "cooldown": "Cinco minutos de caminata y respiración nasal lenta dos minutos; entrenar tarde y salir acelerado te costará dormir."
   },
   {
    "day": "Sábado",
    "name": "Sesión B — mañana, sesión principal",
    "warmup": "6 minutos de bicicleta o remo suave, 10 puentes de glúteo y una serie de aproximación del peso muerto con barra hexagonal.",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "3",
      "rest_sec": 150,
      "technique_cue": "La barra hexagonal te deja la espalda más vertical que la recta: pecho alto, empuja el suelo con los pies y bloquea sin echar la cadera adelante."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tira con los codos hacia los bolsillos y controla la subida."
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Respaldo alto, sin arquear la lumbar; sube hasta casi extender sin chocar las mancuernas."
     },
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 105,
      "technique_cue": "Trabajo de pierna adicional sin exigir técnica fina: perfecto para el día que has dormido poco."
     },
     {
      "name": "Curl martillo",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos al costado y sin balanceo."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Lumbar pegada al suelo y respiración fluida."
     }
    ],
    "cooldown": "Cinco minutos de caminata y estiramiento de flexor de cadera y pectoral, 40 segundos por lado."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Cargas conservadoras y sesiones de 50 minutos. Anota cuántas horas has dormido junto a los pesos: te explicará muchas sesiones malas."
   },
   {
    "week": 2,
    "intent": "Progresión",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Sube carga solo en la sesión del sábado, que es la que haces descansado. El martes se mantiene igual."
   },
   {
    "week": 3,
    "intent": "Carga",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "Semana más exigente en peso muerto hexagonal, sentadilla y press. Si esa semana el niño ha dormido mal, salta directamente a la descarga."
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Una serie menos por ejercicio. El objetivo del mes no es la marca, es haber cumplido los ocho entrenamientos."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 3,
     "notes": "Los paseos con el carrito cuentan como sesión de cardio; hazlos a ritmo algo más vivo de lo normal."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90% con una serie menos por ejercicio. Si una semana solo consigues entrenar un día, haz la sesión B, que es la más completa. Si has dormido menos de cinco horas, baja un 10% las cargas ese día y mantén las series: entrenar algo siempre gana a no venir."
 },
 {
  "category": "principiantes",
  "title": "Volver · tras el parón del verano",
  "case": "Para quien ya entrenaba, ha estado semanas parado y quiere recuperar el ritmo sin empezar de cero.",
  "level": "intermediate",
  "days_per_week": 5,
  "place": "gym",
  "split_name": "Empuje, tracción, pierna y dos sesiones de refuerzo",
  "split_rationale": "Se le devuelve la frecuencia de cinco días a la que estaba acostumbrado porque para él la rutina es el hábito, pero con menos series por sesión y cargas rebajadas. Empuje, tracción y pierna al principio de semana, y dos sesiones complementarias de torso y pierna el viernes y el sábado para repartir el volumen sin acumular fatiga.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Empuje",
    "warmup": "6 minutos de bicicleta, 15 band pull-apart, 10 rotaciones externas con banda y dos series de aproximación en el primer ejercicio.",
    "exercises": [
     {
      "name": "Press banca con mancuernas",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 150,
      "technique_cue": "Empieza con el 70% de lo que movías en julio; las diez semanas parado se notan primero en el tendón, no en la fuerza."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 105,
      "technique_cue": "Máquina en lugar de barra estas primeras semanas: menos exigencia de estabilidad, más control."
     },
     {
      "name": "Contractora de pecho",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Recorrido completo y apertura controlada; sin rebotes en la posición de estiramiento."
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Sube hasta la altura del hombro con el codo ligeramente flexionado, sin encogerte."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos fijos al costado y apertura de la cuerda al final."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Glúteo apretado y costillas abajo durante todo el tiempo."
     }
    ],
    "cooldown": "Cinco minutos de caminata y estiramiento de pectoral en el marco de una puerta, 40 segundos por lado."
   },
   {
    "day": "Martes",
    "name": "Tracción",
    "warmup": "6 minutos de remo suave, 15 band pull-apart y una serie ligera de jalón.",
    "exercises": [
     {
      "name": "Jalón al pecho",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Antes de volver a las dominadas, tres semanas de jalón: el dorsal responde rápido, el codo no tanto."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 105,
      "technique_cue": "Tronco quieto; el recorrido lo hace el brazo y el omóplato."
     },
     {
      "name": "Remo con pecho apoyado en banco",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho pegado al banco todo el rato para que la lumbar no participe."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos altos; tres series porque llegas de un verano de mesa y coche."
     },
     {
      "name": "Curl alterno con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Sin balanceo; supina al subir y controla la bajada."
     },
     {
      "name": "Curl martillo",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Agarre neutro, codos quietos."
     },
     {
      "name": "Elevaciones de rodillas colgado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Sube las rodillas sin balancearte; si te columpias, baja el número de repeticiones."
     }
    ],
    "cooldown": "Cinco minutos de bicicleta suave y estiramiento de dorsal colgado de una polea, 30 segundos por lado."
   },
   {
    "day": "Miércoles",
    "name": "Pierna completa",
    "warmup": "6 minutos de bicicleta, 10 sentadillas sin carga, 10 puentes de glúteo y dos series de aproximación en prensa.",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 150,
      "technique_cue": "Empieza por prensa y no por sentadilla libre: la pierna ha perdido más coordinación que fuerza tras el parón."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Cadera atrás con la espalda recta; para donde el isquio te frene, no más abajo."
     },
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tronco vertical y rodilla de atrás al suelo con suavidad."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Bajada de dos segundos y cadera pegada al banco."
     },
     {
      "name": "Extensión de rodilla en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Pausa de un segundo arriba; sin lanzar el peso."
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo con pausa arriba y estiramiento abajo."
     }
    ],
    "cooldown": "Cinco minutos de caminata y estiramiento de cuádriceps y glúteo, 40 segundos por lado."
   },
   {
    "day": "Viernes",
    "name": "Torso completo",
    "warmup": "6 minutos de elíptica, 15 band pull-apart y una serie ligera de press inclinado.",
    "exercises": [
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Banco a 30 grados; codos a 45 y bajada hasta la altura de la clavícula."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Pecho apoyado, tirón hasta pasar el tronco con los codos."
     },
     {
      "name": "Jalón agarre estrecho neutro",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Agarre neutro para variar el ángulo respecto al martes."
     },
     {
      "name": "Elevación lateral en polea unilateral",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Polea por detrás del cuerpo; sube hasta la horizontal sin encoger el hombro."
     },
     {
      "name": "Patada de tríceps con mancuerna",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Brazo pegado al costado y extensión completa; peso ligero."
     },
     {
      "name": "Curl bayesian en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codo detrás del cuerpo y sin mover el hombro."
     }
    ],
    "cooldown": "Cinco minutos de caminata y movilidad dorsal sobre rodillo, 2 minutos."
   },
   {
    "day": "Sábado",
    "name": "Pierna y core",
    "warmup": "6 minutos de bicicleta, 10 puentes de glúteo y 10 zancadas sin carga.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Segunda dosis de sentadilla de la semana en versión amable; profundidad completa y torso alto."
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Barbilla metida y costillas abajo; el bloqueo lo hace el glúteo, no la lumbar."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Sin dejar caer el peso en la vuelta."
     },
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Sube sin impulso y baja frenando; cajón a la altura de la rodilla."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Resiste la rotación sin mover la cadera."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cuerpo en línea; corta cuando la posición se rompa."
     }
    ],
    "cooldown": "Ocho minutos de caminata a ritmo cómodo y estiramiento general de tren inferior."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Punto de partida al 70% de los kilos de julio. Sí, se te va a quedar corto: ese es el plan. El objetivo de la semana es acabar sin agujetas."
   },
   {
    "week": 2,
    "intent": "Progresión",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Subida general de carga en los básicos de cada día. Si la semana 1 te dejó dolorido más de 48 horas, repítela tal cual."
   },
   {
    "week": 3,
    "intent": "Carga",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "Semana de mayor exigencia con una serie extra en los primeros ejercicios de empuje, tracción y pierna. Ya deberías rondar el 85% de tus marcas."
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio y se recorta la sesión del sábado. A partir del mes siguiente se recuperan barra libre y dominadas."
   }
  ],
  "cardio": {
   "daily_steps": 10000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 2,
     "notes": "Caminata o bicicleta en los días de descanso, sin sumarla al final de las sesiones de pierna."
    },
    {
     "type": "hiit",
     "minutes": 12,
     "times_per_week": 1,
     "notes": "Solo a partir de la semana 3, en bicicleta estática: 8 series de 20 segundos fuertes por 60 suaves."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90% con una serie menos por ejercicio y sin el hiit. Si en cualquier semana llegas a dos sesiones seguidas con sensación de piernas pesadas y menos repeticiones, adelanta la descarga: volver de un parón largo se estropea casi siempre por acelerar, no por ir lento."
 },
 {
  "category": "principiantes",
  "title": "Empezar · pasar de máquinas a peso libre",
  "case": "Para quien lleva meses en el circuito de máquinas y quiere dar el salto al peso libre.",
  "level": "intermediate",
  "days_per_week": 4,
  "place": "gym",
  "split_name": "Torso-pierna con transición a peso libre",
  "split_rationale": "Cuatro días en torso-pierna permiten empezar cada sesión con un ejercicio de peso libre, cuando está fresca y con la cabeza clara para aprender, y cerrarla con las máquinas que ya conoce para acumular volumen sin riesgo técnico. Cada semana el peso libre gana un puesto en el orden de la sesión.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Torso A — empuje libre",
    "warmup": "6 minutos de bicicleta, 15 band pull-apart y dos series de aproximación con mancuernas muy ligeras.",
    "exercises": [
     {
      "name": "Press banca con mancuernas",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Siéntate con las mancuernas sobre los muslos y túmbate impulsándolas con las piernas; omóplatos juntos y codos a 45 grados."
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Espalda plana como una mesa, tirón del codo a la cadera; nada de girar el tronco para subir más peso."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Tu ejercicio de siempre, ahora como accesorio: aprovecha para apretar de verdad."
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Respaldo alto y costillas abajo; las mancuernas suben en línea con las orejas."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos altos y hombros lejos de las orejas."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cuerpo en línea recta; es la base para estabilizar la barra más adelante."
     }
    ],
    "cooldown": "Cinco minutos de caminata y estiramiento de pectoral y dorsal, 30 segundos por lado."
   },
   {
    "day": "Martes",
    "name": "Pierna A — aprender la sentadilla",
    "warmup": "6 minutos de bicicleta, 10 sentadillas sin carga, 10 rotaciones de cadera y una serie con la barra vacía.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 105,
      "technique_cue": "Primero el patrón con mancuerna al pecho: te obliga a mantener el torso alto y a bajar entre los talones."
     },
     {
      "name": "Sentadilla a cajón",
      "sets": 3,
      "rep_range": "6-8",
      "rir": "3",
      "rest_sec": 150,
      "technique_cue": "Barra vacía las dos primeras sesiones. Siéntate en el cajón sin dejarte caer y levántate empujando el suelo con todo el pie."
     },
     {
      "name": "Prensa de piernas 45°",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 105,
      "technique_cue": "Tu máquina de confianza: aquí es donde acumulas el volumen fuerte de cuádriceps."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Cadera pegada al banco, bajada de dos segundos."
     },
     {
      "name": "Abducción de cadera en máquina",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Pausa de un segundo en la apertura."
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo, sin rebotar abajo."
     }
    ],
    "cooldown": "Movilidad de tobillo y estiramiento de cuádriceps, 30 segundos por lado."
   },
   {
    "day": "Jueves",
    "name": "Torso B — tracción y estabilidad",
    "warmup": "6 minutos de remo suave, 15 band pull-apart y una serie ligera de press inclinado.",
    "exercises": [
     {
      "name": "Press inclinado con mancuernas",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Banco a 30 grados; el mismo control que el lunes, cambiando el ángulo."
     },
     {
      "name": "Remo con pecho apoyado en banco",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho pegado al banco; te enseña a tirar con la espalda sin ayuda de la lumbar."
     },
     {
      "name": "Jalón agarre estrecho neutro",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Codos a las costillas y medio segundo de pausa abajo."
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Sube a la altura del hombro; si tienes que impulsar con la cadera, pesa demasiado."
     },
     {
      "name": "Curl martillo",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos quietos al costado."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Aguanta la rotación con el tronco: es el trabajo que sostiene el peso libre."
     }
    ],
    "cooldown": "Cinco minutos de caminata y movilidad de columna dorsal, 2 minutos."
   },
   {
    "day": "Viernes",
    "name": "Pierna B — aprender la bisagra",
    "warmup": "6 minutos de bicicleta, 10 puentes de glúteo, 10 bisagras con un palo en la espalda y una serie con la barra vacía.",
    "exercises": [
     {
      "name": "Peso muerto rumano con barra",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 150,
      "technique_cue": "Barra rozando el muslo, cadera atrás y espalda recta. Con el palo apoyado en cabeza, dorsal y sacro no debe perderse el contacto."
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Almohadilla en la cadera, barbilla metida y bloqueo con el glúteo, no con la lumbar."
     },
     {
      "name": "Zancadas caminando con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pasos largos y tronco vertical; empieza con mancuernas ligeras hasta que el equilibrio sea sólido."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Recorrido completo sin dejar caer el peso."
     },
     {
      "name": "Extensión de rodilla en máquina",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Pausa arriba de un segundo."
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 3,
      "rep_range": "30-40s",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Una mancuerna en una mano, hombros nivelados; te construye el agarre que vas a necesitar con la barra."
     }
    ],
    "cooldown": "Cinco minutos de caminata y estiramiento de isquios y glúteo, 40 segundos por lado."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Barra vacía en sentadilla a cajón y peso muerto rumano toda la semana. La carga sube en las máquinas, no en los ejercicios nuevos."
   },
   {
    "week": 2,
    "intent": "Progresión",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Primeros discos en la barra si la técnica es limpia y grabada en vídeo. Las mancuernas de press suben un escalón."
   },
   {
    "week": 3,
    "intent": "Carga",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Semana de mayor exigencia; el peso libre pasa a ser el ejercicio principal en las cuatro sesiones y las máquinas cierran."
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Una serie menos por ejercicio, manteniendo los movimientos nuevos para no perder el aprendizaje motor recién adquirido."
   }
  ],
  "cardio": {
   "daily_steps": 10000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 2,
     "notes": "Caminata en los días sin gimnasio; nada de cardio antes de las sesiones de pierna."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90% de la carga con una serie menos por ejercicio, sin eliminar ningún ejercicio de peso libre. Regla del caso: si un día un movimiento con barra no sale limpio, se vuelve ese día a la versión con mancuerna o máquina, sin dramatizar; el objetivo del mes es aprender, no cargar."
 },
 {
  "category": "principiantes",
  "title": "Empezar · sin mirar la báscula",
  "case": "Para quien no quiere oír hablar de kilos y busca encontrarse mejor y con más energía.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body de bienestar A-B-C",
  "split_rationale": "Cuerpo completo tres veces por semana con progresión medida en kilos levantados y repeticiones, no en peso corporal. Cada sesión combina un patrón de pierna, uno de empuje, uno de tirón y trabajo de cadera y core, que es la combinación que más rápido cambia las sensaciones del día a día: espalda, escaleras y energía por la tarde.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Sesión A — fuerza y postura",
    "warmup": "5 minutos de bicicleta, 10 band pull-apart y 10 puentes de glúteo.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Mancuerna al pecho y bajada controlada; anota el peso de hoy, porque ese número es tu progreso, no el de la báscula."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tira al ombligo juntando los omóplatos; esto es lo que compensa el día entero inclinada sobre las mesas de los niños."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Asiento a la altura del esternón y empuje continuo."
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "El glúteo fuerte es lo que le quita trabajo a tu espalda baja al final del día."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Movimiento lento sin que la cadera se ladee."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Apoyo en codos, glúteo apretado; calidad antes que segundos."
     }
    ],
    "cooldown": "Cinco minutos de caminata y estiramiento de flexor de cadera en zancada, 40 segundos por lado."
   },
   {
    "day": "Miércoles",
    "name": "Sesión B — piernas y espalda",
    "warmup": "5 minutos de elíptica, 10 rotaciones de cadera y 10 band pull-apart.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Talones apoyados y bajada hasta noventa grados; empuja fuerte, aquí sí puedes exigirte."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Codos hacia abajo, pecho alto y sin echar el tronco atrás."
     },
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Costillas abajo; subir la mochila al altillo del aula empieza aquí."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 105,
      "technique_cue": "Cadera atrás con la espalda recta: este es el gesto que estás haciendo mal cada vez que recoges algo del suelo en clase."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos altos y hombros lejos de las orejas."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Lumbar pegada al suelo, respiración fluida."
     }
    ],
    "cooldown": "Movilidad dorsal sobre rodillo, 2 minutos, y estiramiento de isquios."
   },
   {
    "day": "Viernes",
    "name": "Sesión C — energía para el fin de semana",
    "warmup": "5 minutos de caminata inclinada, 10 subidas a escalón y 10 band pull-apart.",
    "exercises": [
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Cajón a la altura de la rodilla; sube sin impulso y baja frenando. Es la escalera del colegio en versión entrenada."
     },
     {
      "name": "Remo con pecho apoyado en banco",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho pegado al banco durante todo el tirón."
     },
     {
      "name": "Contractora de pecho",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Cierra sin chocar las manos y abre despacio."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Bajada de dos segundos sin despegar la cadera."
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 3,
      "rep_range": "30-40s",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Camina erguida con una sola mancuerna; el día que la bolsa de la compra pese menos, ese es el resultado que buscamos."
     },
     {
      "name": "Plancha lateral",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cadera alta y alineada; apoya la rodilla si hace falta."
     }
    ],
    "cooldown": "Cinco minutos de caminata y respiración nasal lenta tumbada, 2 minutos."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Semana de referencia. Al acabar cada sesión anota dos cosas: el peso que has movido y cómo has dormido esa noche. Esos son tus indicadores."
   },
   {
    "week": 2,
    "intent": "Progresión",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Sube un escalón donde las repeticiones hayan salido fáciles. Empieza a notarse en la espalda al final de la jornada."
   },
   {
    "week": 3,
    "intent": "Carga",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "Semana de más exigencia en sentadilla, prensa y remo. Compara los pesos con los de la semana 1: ahí está la prueba objetiva de que avanzas."
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Una serie menos por ejercicio. Revisión de sensaciones: sueño, energía por la tarde y molestias de espalda; ninguna báscula."
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 3,
     "notes": "Caminata tranquila, mejor acompañada. Aquí no se persigue gasto, se persigue llegar mejor al viernes."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90% con una serie menos por ejercicio. En este caso la descarga no es negociable: el patrón de las dietas fallidas fue siempre acelerar hasta reventar. Si una semana llegas agotada del colegio, cambia una sesión por una caminata larga y sigue el plan la semana siguiente."
 },
 {
  "category": "principiantes",
  "title": "Empezar · con muy baja forma física",
  "case": "Para quien se ahoga subiendo escaleras y necesita empezar por lo más básico.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body sentado con descansos largos",
  "split_rationale": "Cuerpo completo tres días por semana con la mayoría de ejercicios sentados o con apoyo, para que la limitación respiratoria no le obligue a abandonar la serie antes de que el músculo trabaje. Los descansos son deliberadamente largos, de 90 a 150 segundos, porque su recuperación entre series es lo que hay que entrenar primero.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Sesión A — máquinas y respiración",
    "warmup": "6 minutos de bicicleta sentado a ritmo muy suave; el objetivo es acabar el calentamiento pudiendo hablar sin cortarte.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 150,
      "technique_cue": "Suelta el aire al empujar. Descansa lo que marca la hoja aunque te veas listo antes: el descanso es parte del entrenamiento."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Tronco quieto y tirón al ombligo; si te falta el aire, baja el peso antes que acortar la serie."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Empuje continuo sin aguantar la respiración en ningún momento."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Ritmo constante y bajada de dos segundos."
     },
     {
      "name": "Face pull en polea",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 75,
      "technique_cue": "Codos altos; trabajo de postura para las horas al volante."
     },
     {
      "name": "Dead bug",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Tumbado y respirando: suelta el aire cada vez que estiras la pierna."
     }
    ],
    "cooldown": "6 minutos de bicicleta muy suave hasta recuperar el aliento del todo y dos minutos sentado respirando por la nariz."
   },
   {
    "day": "Miércoles",
    "name": "Sesión B — tirón y cadera",
    "warmup": "6 minutos de elíptica muy suave y 10 rotaciones de hombro.",
    "exercises": [
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Codos hacia abajo con el pecho alto; sentado, sin tener que sostener el peso del cuerpo."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Sube sin arquear la espalda y respirando; peso moderado."
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 105,
      "technique_cue": "Empuja con los talones; el glúteo fuerte es la mitad de subir escaleras."
     },
     {
      "name": "Abducción de cadera en máquina",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Tronco erguido y pausa de un segundo en la apertura."
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo; el gemelo es la otra mitad de las escaleras."
     },
     {
      "name": "Press Pallof",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 75,
      "technique_cue": "Aguanta la rotación sin bloquear la respiración."
     }
    ],
    "cooldown": "6 minutos de bicicleta suave y respiración diafragmática tumbado, 3 minutos."
   },
   {
    "day": "Viernes",
    "name": "Sesión C — de pie con apoyo",
    "warmup": "6 minutos de caminata en cinta a ritmo cómodo con inclinación cero.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 150,
      "technique_cue": "Con una mancuerna ligera y bajando hasta un banco alto; siéntate y levántate, ese es el ejercicio."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Pecho apoyado; así el tirón no te obliga a sostener el tronco y respiras mejor."
     },
     {
      "name": "Contractora de pecho",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Cierra sin chocar las manos y exhala al cerrar."
     },
     {
      "name": "Subida a cajón",
      "sets": 2,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Escalón bajo y sin peso, sujetándote a una barra. Este es literalmente el ejercicio de las escaleras de tu casa."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos al costado; ejercicio de cierre, ligero."
     },
     {
      "name": "Plancha abdominal",
      "sets": 2,
      "rep_range": "20-30s",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Veinte segundos bien hechos bastan; respira con normalidad todo el tiempo."
     }
    ],
    "cooldown": "8 minutos de caminata suave. Ese día, al llegar a casa, sube los dos pisos y anota cómo has llegado arriba."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Sesiones de 40 minutos con descansos generosos. La medida de éxito de la semana es completar las series, no el peso."
   },
   {
    "week": 2,
    "intent": "Progresión",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Mismo esquema con 15 segundos menos de descanso en los ejercicios de máquina. Cargas casi iguales."
   },
   {
    "week": 3,
    "intent": "Carga",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "Primera subida real de peso en prensa, remo y press. La caminata diaria sube a 25 minutos."
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Una serie menos por ejercicio. Prueba de referencia: subir los dos pisos y comparar con la semana 1."
   }
  ],
  "cardio": {
   "daily_steps": 6000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 15,
     "times_per_week": 4,
     "notes": "Bicicleta estática o caminata llana a un ritmo en el que puedas hablar. Empieza por 15 minutos y suma 2 minutos cada semana; esta es la parte del plan que resuelve tu queja principal."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90% con una serie menos por ejercicio, manteniendo las caminatas. Si en cualquier sesión te falta el aire de forma desproporcionada, aparecen mareos o presión en el pecho, se para el entrenamiento y se consulta con el médico antes de volver."
 },
 {
  "category": "principiantes",
  "title": "Volver · exdeportista desentrenado",
  "case": "Para quien fue deportista y vuelve años después: sabe entrenar pero el cuerpo ya no está.",
  "level": "intermediate",
  "days_per_week": 4,
  "place": "gym",
  "split_name": "Torso-pierna con hombro protegido",
  "split_rationale": "Cuatro días en torso-pierna para repartir el volumen y poder incluir dos dosis semanales de trabajo específico de manguito rotador y escápula. En el torso se sustituye todo el empuje libre por encima de la cabeza y el banco con mancuernas por versiones en máquina, landmine y press de suelo, que respetan el hombro de lanzadora sin renunciar a la carga.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Torso A — empuje guiado",
    "warmup": "6 minutos de bicicleta, 15 band pull-apart, 15 rotaciones externas con banda y 10 deslizamientos de escápula en pared.",
    "exercises": [
     {
      "name": "Press de pecho en máquina",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Ajusta el asiento para que las asas queden a la altura del esternón y no bajes el codo por detrás de la línea del tronco."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 105,
      "technique_cue": "Tirón al ombligo con el tronco quieto; el volumen de tirón dobla al de empuje en este plan y es intencionado."
     },
     {
      "name": "Jalón agarre estrecho neutro",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Agarre neutro, que es el que menos comprime el hombro."
     },
     {
      "name": "Press landmine de pie",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 105,
      "technique_cue": "El ángulo del landmine te deja empujar en diagonal sin llegar a la vertical pura: ese es el motivo de que esté aquí."
     },
     {
      "name": "Rotación externa de hombro en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codo pegado al costado con una toalla enrollada; movimiento lento y sin compensar con el tronco."
     },
     {
      "name": "Face pull en polea",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos por encima de las muñecas; ejercicio innegociable en tu caso."
     }
    ],
    "cooldown": "Cinco minutos de caminata y movilidad de dorsal sobre rodillo, 2 minutos."
   },
   {
    "day": "Martes",
    "name": "Pierna A — base de fuerza",
    "warmup": "6 minutos de bicicleta, 10 sentadillas sin carga, 10 puentes de glúteo y una serie de aproximación en prensa.",
    "exercises": [
     {
      "name": "Prensa de piernas 45°",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 150,
      "technique_cue": "Tu pierna aguanta más de lo que crees, pero el tendón lleva veinte años sin cargar: sube de kilos con paciencia."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Cadera atrás con la espalda recta; para donde te frene el isquio."
     },
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tronco vertical y bajada controlada; nada de zancadas con salto por ahora."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Bajada de dos segundos, cadera pegada al banco."
     },
     {
      "name": "Abducción de cadera en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Pausa de un segundo en la apertura."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cuerpo en línea; cierra la sesión sin buscar récords de tiempo."
     }
    ],
    "cooldown": "Cinco minutos de caminata y estiramiento de cuádriceps y glúteo, 40 segundos por lado."
   },
   {
    "day": "Jueves",
    "name": "Torso B — empuje horizontal y volumen",
    "warmup": "6 minutos de remo suave, 15 band pull-apart y 15 rotaciones externas con banda.",
    "exercises": [
     {
      "name": "Press de suelo con barra",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "3",
      "rest_sec": 150,
      "technique_cue": "El suelo frena el codo antes de que el hombro entre en el rango que te molesta; ese tope es la razón del ejercicio."
     },
     {
      "name": "Remo con pecho apoyado en banco",
      "sets": 4,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho pegado al banco todo el recorrido."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Codos hacia las costillas y control en la subida."
     },
     {
      "name": "Elevaciones laterales en máquina",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "En máquina y no con mancuerna: el recorrido guiado evita que el hombro se te vaya hacia delante al fatigarte."
     },
     {
      "name": "Curl martillo",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos quietos al costado."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos fijos; nada de versiones sobre la cabeza en tu caso."
     }
    ],
    "cooldown": "Cinco minutos de caminata y estiramiento suave de pectoral sin forzar la apertura del hombro."
   },
   {
    "day": "Viernes",
    "name": "Pierna B — cadera y unilateral",
    "warmup": "6 minutos de bicicleta, 10 puentes de glúteo y 10 subidas a escalón.",
    "exercises": [
     {
      "name": "Hip thrust con barra",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Barbilla metida, costillas abajo y bloqueo con glúteo; el ejercicio donde más rápido vas a recuperar tus números."
     },
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 105,
      "technique_cue": "Torso alto y profundidad completa; la mancuerna al pecho no carga el hombro."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Recorrido completo, sin dejar caer el peso."
     },
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Sube sin impulso y baja frenando; empieza con cajón a la altura de la rodilla."
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Pausa arriba y estiramiento completo abajo."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Resiste la rotación sin mover la cadera; te va a servir cuando vuelvas a lanzar por diversión."
     }
    ],
    "cooldown": "Cinco minutos de caminata y estiramiento de isquios y aductor, 40 segundos por lado."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Semana de contención deliberada: cargas moderadas y ninguna serie cerca del fallo. Registro diario de cómo amanece el hombro."
   },
   {
    "week": 2,
    "intent": "Progresión",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Sube carga en pierna con normalidad; en torso, solo si el hombro ha estado tranquilo los siete días."
   },
   {
    "week": 3,
    "intent": "Carga",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "Semana más exigente en prensa, hip thrust y press de suelo. El trabajo de manguito se mantiene, nunca se recorta."
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio salvo en rotación externa y face pull. Revisión del hombro antes de plantear el mes siguiente."
   }
  ],
  "cardio": {
   "daily_steps": 10000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Caminata o bicicleta. Nada de volver a pistas ni partidos de veteranas hasta que el hombro lleve un mes sin protestar."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90% con una serie menos por ejercicio, manteniendo intacto el trabajo de manguito rotador. La norma central de este caso: cualquier serie extra improvisada, cualquier vuelta a un gesto de lanzamiento o cualquier dolor de hombro que dure más de 48 horas obliga a parar el torso una semana y avisar al coach."
 },
 {
  "category": "principiantes",
  "title": "Empezar · entrar y salir en 40 minutos",
  "case": "Para quien entrena antes de trabajar y necesita sesiones cerradas y sin esperas.",
  "level": "intermediate",
  "days_per_week": 4,
  "place": "gym",
  "split_name": "Torso-pierna exprés de cinco ejercicios",
  "split_rationale": "Cuatro sesiones cortas de cinco ejercicios cada una, montadas casi por completo sobre banco y mancuernas: material del que siempre hay repuesto y que se puede llevar a un rincón sin cruzar la sala. Al repartir en cuatro días, cada sesión cabe en cuarenta minutos sin recortar el volumen semanal.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Torso A — empuje horizontal",
    "warmup": "4 minutos de bicicleta y 15 band pull-apart mientras montas las mancuernas. Sin pausas largas: el reloj cuenta desde que entras.",
    "exercises": [
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Ten las dos parejas de mancuernas preparadas antes de empezar: la primera y la de aproximación."
     },
     {
      "name": "Remo con mancuerna a una mano",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Encadénalo con el press: mientras descansas de uno haces el otro y ahorras siete minutos de sesión."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Codos hacia abajo, pecho alto. A las siete de la mañana la polea siempre está libre."
     },
     {
      "name": "Elevaciones laterales con mancuernas",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Peso ligero y subida hasta la horizontal, sin impulso."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Cierra la sesión con esto y sal; descansos de 45 segundos, mirando el reloj."
     }
    ],
    "cooldown": "Tres minutos de caminata y estiramiento de pectoral, 30 segundos por lado."
   },
   {
    "day": "Martes",
    "name": "Pierna A — sentadilla y bisagra",
    "warmup": "4 minutos de bicicleta, 10 sentadillas sin carga y una serie de aproximación con la mancuerna.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 4,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 120,
      "technique_cue": "Cuatro series al principio, cuando estás fresco; una sola mancuerna pesada resuelve el ejercicio."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Cadera atrás, espalda recta y mancuernas rozando el muslo."
     },
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Con las mismas mancuernas del ejercicio anterior; no vuelvas al rack a media sesión."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cadera pegada al banco y bajada de dos segundos."
     },
     {
      "name": "Elevación de talones de pie",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Último ejercicio, rápido y con recorrido completo."
     }
    ],
    "cooldown": "Tres minutos de caminata y estiramiento de isquios, 30 segundos por lado."
   },
   {
    "day": "Jueves",
    "name": "Torso B — hombro y volumen",
    "warmup": "4 minutos de bicicleta y 15 band pull-apart.",
    "exercises": [
     {
      "name": "Press de hombros con mancuernas sentado",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Respaldo alto y costillas abajo; con el banco ya montado del ejercicio siguiente."
     },
     {
      "name": "Remo con pecho apoyado en banco",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Mismo banco inclinado que el press: cero desplazamientos por la sala."
     },
     {
      "name": "Press inclinado con mancuernas",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Banco a 30 grados; encadénalo con el remo para ganar minutos."
     },
     {
      "name": "Curl martillo",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos quietos, sin balanceo."
     },
     {
      "name": "Patada de tríceps con mancuerna",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 45,
      "technique_cue": "Brazo pegado al costado y extensión completa; cierre rápido de sesión."
     }
    ],
    "cooldown": "Tres minutos de caminata y movilidad de hombro con banda, 1 minuto."
   },
   {
    "day": "Viernes",
    "name": "Pierna B — fuerza y unilateral",
    "warmup": "4 minutos de bicicleta, 10 puentes de glúteo y una serie de aproximación con la barra hexagonal.",
    "exercises": [
     {
      "name": "Peso muerto con barra hexagonal",
      "sets": 4,
      "rep_range": "6-8",
      "rir": "2-3",
      "rest_sec": 150,
      "technique_cue": "A las siete de la mañana la hexagonal está libre; es el ejercicio con mejor relación fuerza-tiempo de tu semana."
     },
     {
      "name": "Sentadilla búlgara",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Pie de atrás en el banco, tronco ligeramente inclinado y bajada controlada."
     },
     {
      "name": "Hip thrust con barra",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Aprovecha que ya tienes barra y discos de la hexagonal montados."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Recorrido completo sin dejar caer el peso."
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 3,
      "rep_range": "30-40s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Camina por el pasillo lateral, que a esa hora está vacío; hombros nivelados."
     }
    ],
    "cooldown": "Tres minutos de caminata y estiramiento de glúteo y cuádriceps, 30 segundos por lado."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Semana de cronometrar: apunta cuánto tardas en cada sesión y ajusta el material que dejas preparado antes de empezar."
   },
   {
    "week": 2,
    "intent": "Progresión",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Sube carga en los dos primeros ejercicios de cada día, que son los que sostienen el plan si un día vas con prisa."
   },
   {
    "week": 3,
    "intent": "Carga",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Semana fuerte en peso muerto hexagonal, sentadilla goblet y press con mancuernas. Sigue sin pasar de los cuarenta minutos."
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3",
    "volume_note": "Una serie menos por ejercicio; sesiones de treinta minutos que te dejan abrir la tienda con margen."
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 25,
     "times_per_week": 2,
     "notes": "Caminata al cerrar la tienda, no por la mañana: el hueco de las siete es solo para las pesas."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90% con una serie menos por ejercicio. Si un día llegas con veinte minutos en lugar de cuarenta, haz solo los dos primeros ejercicios de la sesión al peso previsto y vete: media sesión completa vale mucho más que saltártela entera."
 },
 {
  "category": "principiantes",
  "title": "Empezar · con un trabajo físico exigente",
  "case": "Para quien acaba la jornada agotado y necesita entrenar sin sumar más desgaste.",
  "level": "beginner",
  "days_per_week": 2,
  "place": "gym",
  "split_name": "Full body de dos días con lumbar descargada",
  "split_rationale": "Dos sesiones semanales de cuerpo completo que evitan por completo la carga axial y las bisagras con peso libre, porque su columna ya acumula ocho horas diarias de eso. Todo va con pecho o espalda apoyados y con el core trabajado en anti-extensión y anti-rotación, que es lo que le va a quitar molestias al final del turno.",
  "sessions": [
   {
    "day": "Martes",
    "name": "Sesión A — empuje, tirón y pierna apoyada",
    "warmup": "8 minutos de bicicleta suave para descargar piernas y espalda, más 10 rotaciones de cadera por lado. Entrenar con la espalda cargada del trabajo exige calentar más, no menos.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Espalda completamente apoyada en el respaldo; ningún kilo pasa por tu columna en este ejercicio, que es justo lo que buscamos."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Pecho apoyado; usa correas si el agarre te falla antes que la espalda, tus manos ya han trabajado hoy."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Sentado con respaldo; empuje continuo y muñeca alineada."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Bajada de dos segundos; el isquio fuerte es media protección de la lumbar."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Lumbar pegada al suelo: aprende a mantenerla ahí y llevarás esa posición al andamio."
     },
     {
      "name": "Face pull en polea",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos altos, trabajo ligero de hombro y espalda alta."
     }
    ],
    "cooldown": "Cinco minutos de bicicleta muy suave y estiramiento de psoas y glúteo, 40 segundos por lado."
   },
   {
    "day": "Jueves",
    "name": "Sesión B — cadera, espalda y core",
    "warmup": "8 minutos de bicicleta o elíptica suave y 10 puentes de glúteo sin carga.",
    "exercises": [
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 105,
      "technique_cue": "El glúteo es el músculo que debería estar haciendo el trabajo que ahora hace tu lumbar cuando levantas sacos."
     },
     {
      "name": "Jalón agarre estrecho neutro",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Agarre neutro, más amable con tus manos; tira con el codo."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Sentado con respaldo y sin arquear la espalda para completar la repetición."
     },
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 105,
      "technique_cue": "El único ejercicio de pie del plan: peso moderado y torso alto. Si un día llegas fundido, cámbialo por prensa."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Lento, sin que la cadera se ladee."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Aguanta la rotación con el tronco firme; esto es lo que estabiliza la columna cuando cargas peso en un solo lado."
     }
    ],
    "cooldown": "Cinco minutos de caminata y descarga de la espalda tumbado con las piernas en alto sobre un banco, 3 minutos."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Cargas cortas: sales del gimnasio con la sensación de haber descansado, no de haber trabajado más. Anota cómo tienes la espalda al llegar el viernes."
   },
   {
    "week": 2,
    "intent": "Progresión",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Pequeña subida en prensa, remo y hip thrust. El core se mantiene igual, pero más lento."
   },
   {
    "week": 3,
    "intent": "Carga",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "Semana más exigente. Si esa semana hay descarga de camiones o jornadas de diez horas, quédate en las cargas de la semana 2."
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Una serie menos por ejercicio. Compara las molestias lumbares de esta semana con las del inicio del mes."
   }
  ],
  "cardio": {
   "daily_steps": 12000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 20,
     "times_per_week": 2,
     "notes": "Paseo tranquilo después de cenar los días sin gimnasio. No es para gastar, es para descargar la espalda antes de dormir."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90% con una serie menos por ejercicio. Norma para este caso: nunca se añaden días ni ejercicios de espalda baja porque tu trabajo ya los pone. Si un día llegas con la lumbar cargada de verdad, haz solo el hip thrust, el core y bicicleta suave, y vete a casa."
 },
 {
  "category": "principiantes",
  "title": "Empezar · crear el hábito con 2 días",
  "case": "Para quien se ha apuntado varias veces y lo ha dejado: lo primero es la constancia.",
  "level": "beginner",
  "days_per_week": 2,
  "place": "gym",
  "split_name": "Sesión única repetida dos veces por semana",
  "split_rationale": "La misma sesión de cuatro ejercicios los dos días. Repetirla es deliberado: elimina la carga mental de decidir, permite mejorar la técnica el doble de rápido y hace que la progresión sea visible de una semana a otra. Cubre pierna, empuje, tirón y core, que es lo mínimo para no dejar huecos.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Sesión única — primera del mes",
    "warmup": "5 minutos de bicicleta y 10 sentadillas sin carga. Cinco minutos, ni uno más.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Mancuerna vertical al pecho, bajada de dos segundos y subida decidida. Anota el peso en el móvil: es la única tarea del día."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Muslos sujetos bajo el rodillo, codos hacia abajo y pecho alto."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Asiento a la altura del esternón; empuje sin bloquear el codo con fuerza."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos bajo los hombros y glúteo apretado. Con esto se acaba: en treinta minutos estás fuera."
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Empuja con el glúteo y aprieta arriba un segundo; es el gesto de levantarte de la silla."
     }
    ],
    "cooldown": "Cinco minutos de caminata en cinta. Antes de salir, deja fijado en el calendario el día de la próxima sesión."
   },
   {
    "day": "Jueves",
    "name": "Sesión única — segunda del mes",
    "warmup": "5 minutos de bicicleta y 10 sentadillas sin carga.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Misma mancuerna que el lunes; si las diez repeticiones salieron cómodas, hoy sube un escalón."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Idéntico al lunes: repetir es lo que hace que en tres semanas te salga sin pensar."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Mismo número de asiento apuntado el lunes; así no pierdes tiempo ajustando."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Intenta cinco segundos más que el lunes, sin romper la posición."
     }
    ],
    "cooldown": "Cinco minutos de caminata y marca la sesión como hecha en el calendario."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "El objetivo de esta semana no es entrenar bien, es venir dos veces. Pesos cómodos y sesiones de treinta minutos."
   },
   {
    "week": 2,
    "intent": "Progresión",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Segunda semana con las mismas cuatro cosas. Sube un escalón donde te sobren repeticiones; nada de añadir ejercicios."
   },
   {
    "week": 3,
    "intent": "Carga",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "Aquí es donde otras veces lo dejaste. Se sube algo de peso y no se toca nada más: sin ejercicios nuevos, sin días extra."
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Semana ligera. Si has cumplido las ocho sesiones del mes, el mes que viene añadimos un tercer día y dos ejercicios."
   }
  ],
  "cardio": {
   "daily_steps": 7000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 20,
     "times_per_week": 2,
     "notes": "Caminar hasta el trabajo o bajarse una parada antes. No cuenta como sesión de gimnasio ni la sustituye."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90% con una serie menos por ejercicio. La regla que sostiene este plan: si un día solo tienes veinte minutos, haz la sentadilla y el jalón y vete. Venir y hacer la mitad siempre cuenta como sesión cumplida; no venir es lo único que rompe la racha."
 },
 {
  "category": "principiantes",
  "title": "Empezar · en casa solo con el peso corporal",
  "case": "Para quien no tiene gimnasio cerca ni material y empieza con su propio peso.",
  "level": "beginner",
  "days_per_week": 4,
  "place": "home",
  "split_name": "Alternancia inferior-superior con peso corporal",
  "split_rationale": "Sin material externo, el estímulo se consigue con frecuencia y control del tempo, no con carga: cuatro sesiones cortas alternando tren inferior y tren superior permiten repetir cada patrón dos veces por semana en sesiones de media hora. La progresión se hace alargando la fase de bajada, añadiendo repeticiones y pasando a versiones a una pierna.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Tren inferior y core",
    "warmup": "3 minutos de marcha en el sitio, 10 círculos de cadera por lado y 10 sentadillas parciales.",
    "exercises": [
     {
      "name": "Sentadilla en pared (isométrica)",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Espalda pegada a la pared y rodillas a noventa grados; respira con normalidad todo el tiempo."
     },
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 75,
      "technique_cue": "Paso atrás largo, tronco vertical y rodilla al suelo con suavidad; apóyate en la silla los primeros días."
     },
     {
      "name": "Puente de glúteo",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Empuja con los talones y aprieta el glúteo dos segundos arriba."
     },
     {
      "name": "Peso muerto rumano a una pierna sin carga",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Roza la silla con la mano para no perder el equilibrio; la espalda recta y la cadera atrás."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Lumbar pegada al suelo, movimiento lento."
     },
     {
      "name": "Elevación de gemelo a una pierna en escalón",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "En el escalón de casa, bajando el talón todo lo que puedas antes de subir."
     }
    ],
    "cooldown": "Estiramiento de cuádriceps y gemelo, 30 segundos por lado, y dos minutos de respiración tumbado."
   },
   {
    "day": "Martes",
    "name": "Tren superior",
    "warmup": "3 minutos de marcha en el sitio, 10 círculos de hombro y 5 flexiones apoyadas en la mesa.",
    "exercises": [
     {
      "name": "Flexiones",
      "sets": 3,
      "rep_range": "6-10",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Si no salen limpias desde el suelo, apoya las manos en el borde de la mesa; cuerpo recto como una tabla."
     },
     {
      "name": "Remo invertido bajo una mesa",
      "sets": 3,
      "rep_range": "8-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Túmbate bajo una mesa sólida y agárrate al canto; pecho a la mesa en cada repetición. Comprueba antes que la mesa aguanta."
     },
     {
      "name": "Flexiones pike",
      "sets": 2,
      "rep_range": "6-8",
      "rir": "3",
      "rest_sec": 75,
      "technique_cue": "Cadera alta formando una uve invertida; baja la coronilla hacia las manos con control."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos bajo los hombros, glúteo apretado."
     },
     {
      "name": "Plancha lateral",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cadera alta y alineada; apoya la rodilla de abajo si hace falta."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Sin que la cadera se ladee; cinco segundos por repetición."
     }
    ],
    "cooldown": "Estiramiento de pectoral en el marco de la puerta y de dorsal apoyado en la mesa, 30 segundos por lado."
   },
   {
    "day": "Jueves",
    "name": "Piernas unilaterales",
    "warmup": "3 minutos de marcha en el sitio, 10 zancadas sin carga y 10 puentes de glúteo.",
    "exercises": [
     {
      "name": "Sentadilla búlgara con peso corporal",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Pie de atrás sobre la silla; baja recto y con control. Es tu ejercicio más exigente de pierna sin material."
     },
     {
      "name": "Zancadas caminando sin carga",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Si no tienes espacio para caminar, hazlas en el sitio alternando pierna."
     },
     {
      "name": "Puente de glúteo a una pierna",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Cadera nivelada; no dejes que el lado libre caiga."
     },
     {
      "name": "Curl femoral con toalla deslizante",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Sobre suelo liso, con una toalla bajo los talones; mantén la cadera arriba todo el recorrido."
     },
     {
      "name": "Marcha del oso",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Rodillas a un palmo del suelo y cadera baja; pasos cortos, sin que el culo suba."
     },
     {
      "name": "Plancha lateral",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cadera alta; alterna lados en cada serie."
     }
    ],
    "cooldown": "Estiramiento de isquios y glúteo sentado, 40 segundos por lado."
   },
   {
    "day": "Viernes",
    "name": "Cuerpo completo corto",
    "warmup": "3 minutos de marcha en el sitio y 10 círculos de hombro y cadera.",
    "exercises": [
     {
      "name": "Remo invertido bajo una mesa",
      "sets": 3,
      "rep_range": "8-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cuanto más horizontal te pongas, más pesa; usa esa inclinación como si fueran discos."
     },
     {
      "name": "Flexiones",
      "sets": 3,
      "rep_range": "6-10",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Bajada de tres segundos: es la forma de hacerlas más duras sin añadir peso."
     },
     {
      "name": "Zancada estática",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Pies fijos, sube y baja en el sitio con el tronco vertical."
     },
     {
      "name": "Puente de glúteo",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Dos segundos de pausa arriba en cada repetición."
     },
     {
      "name": "Escaladores",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Ritmo controlado, sin que la cadera suba y baje; el vecino de abajo no se va a enterar."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cierra la semana con la posición limpia, sin buscar tiempos récord."
     }
    ],
    "cooldown": "Cinco minutos de estiramiento general y respiración tumbado. Con el turno de las cuatro, esta parte es la que te ayuda a dormir la siesta."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación",
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Aprender las posiciones y comprobar qué mueble aguanta. Sesiones de 25 minutos, cuatro días. Anota repeticiones de cada ejercicio."
   },
   {
    "week": 2,
    "intent": "Progresión",
    "load_pct": 102.5,
    "rir_target": "2-3",
    "volume_note": "Misma estructura sumando una o dos repeticiones por serie donde puedas. Sin material, el progreso son repeticiones, no kilos."
   },
   {
    "week": 3,
    "intent": "Carga",
    "load_pct": 105,
    "rir_target": "2",
    "volume_note": "Semana de bajadas de tres segundos en flexiones, sentadilla búlgara y remo invertido, y remo más horizontal. Ahí está el aumento de carga."
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "3-4",
    "volume_note": "Una serie menos por ejercicio y tempo normal. Si las flexiones desde el suelo ya salen a diez, el mes que viene toca versión a un brazo asistida."
   }
  ],
  "cardio": {
   "daily_steps": 11000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 3,
     "notes": "Caminata por el pueblo al terminar el turno, mejor a mediodía; sirve también para no acostarte demasiado pronto."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90% de exigencia (una serie menos y tempo normal). Si un día sales del obrador destrozado, haz solo los tres primeros ejercicios de la sesión: con turno de madrugada, la constancia vale más que cualquier serie extra."
 },
 {
  "category": "principiantes",
  "title": "Empezar · en casa con bandas elásticas",
  "case": "Para quien entrena en casa con bandas, sin saltos ni ruido.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "home",
  "split_name": "Full body con bandas, sin impacto",
  "split_rationale": "Tres sesiones de cuerpo completo construidas solo con bandas y peso corporal, sin ningún ejercicio de salto ni apoyo ruidoso. La banda permite graduar la resistencia acortando el agarre, así que la progresión existe aunque no haya discos, y el trabajo de espalda alta se repite en los tres días por las horas de ordenador.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Sesión A — empuje, tirón y pierna",
    "warmup": "3 minutos de marcha en el sitio, 10 círculos de hombro y 10 sentadillas parciales sujetándote a una silla.",
    "exercises": [
     {
      "name": "Zancada inversa",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Paso atrás y rodilla al suelo con suavidad; apóyate en el respaldo de una silla hasta que el equilibrio sea sólido."
     },
     {
      "name": "Remo con banda sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 75,
      "technique_cue": "Sentada en el suelo con la banda en los pies; tira llevando los codos atrás y junta los omóplatos."
     },
     {
      "name": "Press de pecho con banda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 75,
      "technique_cue": "Banda por detrás de la espalda a la altura de las axilas; empuja hasta casi extender sin bloquear."
     },
     {
      "name": "Puente de glúteo",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Empuja con los talones y aprieta el glúteo dos segundos arriba."
     },
     {
      "name": "Band pull-apart",
      "sets": 2,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Brazos rectos, abre hasta el pecho sin encoger los hombros. Este es el antídoto de tus horas de ordenador."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Lumbar pegada al suelo y respiración fluida."
     }
    ],
    "cooldown": "Estiramiento de pectoral en el marco de la puerta y de cuello, 30 segundos por lado."
   },
   {
    "day": "Miércoles",
    "name": "Sesión B — vertical y glúteo",
    "warmup": "3 minutos de marcha en el sitio, 10 band pull-apart suaves y 10 puentes de glúteo.",
    "exercises": [
     {
      "name": "Sentadilla en pared (isométrica)",
      "sets": 3,
      "rep_range": "30-45s",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Espalda pegada a la pared, rodillas a noventa grados y respirando con normalidad. Cero ruido para los vecinos."
     },
     {
      "name": "Jalón con banda de pie",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 75,
      "technique_cue": "Banda anclada arriba en una puerta cerrada; tira con los codos hacia las costillas."
     },
     {
      "name": "Press de hombro con banda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 75,
      "technique_cue": "Pisa la banda y empuja por encima de la cabeza sin arquear la espalda."
     },
     {
      "name": "Abducción de cadera con banda",
      "sets": 3,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Banda por encima de las rodillas, tumbada de lado; abre sin girar la pelvis atrás."
     },
     {
      "name": "Face pull con banda",
      "sets": 2,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Banda a la altura de los ojos, codos altos, hombros lejos de las orejas."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Movimiento lento, sin ladear la cadera."
     }
    ],
    "cooldown": "Movilidad de columna a cuatro apoyos, 2 minutos, y estiramiento de glúteo sentada."
   },
   {
    "day": "Viernes",
    "name": "Sesión C — cuerpo completo",
    "warmup": "3 minutos de marcha en el sitio y 10 círculos de cadera y hombro.",
    "exercises": [
     {
      "name": "Zancada estática",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Pies fijos, sube y baja en el sitio con el tronco vertical; sujétate a la silla si lo necesitas."
     },
     {
      "name": "Press de pecho con banda",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 75,
      "technique_cue": "Acorta el agarre de la banda para que pese más que el lunes."
     },
     {
      "name": "Remo con banda sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Tronco erguido; el tirón lo hace la espalda, no la lumbar echándose atrás."
     },
     {
      "name": "Puente de glúteo a una pierna",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Cadera nivelada; no dejes caer el lado libre."
     },
     {
      "name": "Elevaciones laterales con banda",
      "sets": 2,
      "rep_range": "15-20",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Sube hasta la altura del hombro sin encogerte; peso ligero y control."
     },
     {
      "name": "Plancha lateral",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cadera alta y alineada; empieza apoyando la rodilla de abajo."
     }
    ],
    "cooldown": "Estiramiento general de cinco minutos y dos minutos de respiración tumbada antes de seguir con la tarde."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Semana de sacar las bandas del armario y aprender a anclarlas. Usa la banda más ligera y sesiones de 25 minutos."
   },
   {
    "week": 2,
    "intent": "Progresión",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Acorta un palmo el agarre de la banda en remo y press: ese es tu escalón de peso. Mismo número de series."
   },
   {
    "week": 3,
    "intent": "Carga",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "Cambia a la banda del siguiente color en los ejercicios donde llegues a 15 repeticiones cómodas. La sentadilla en pared sube a 45 segundos."
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Vuelve a la banda anterior y quita una serie por ejercicio. Semana ligera pensada para no fallar ninguna de las tres sesiones."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 3,
     "notes": "Caminata al ir a casa de tu madre, o dos vueltas a la manzana después de comer. Sin impacto y sin material."
    }
   ]
  },
  "deload_instructions": "Semana 4 con la banda más suave y una serie menos por ejercicio. Si una tarde se complica con el cuidado de tu madre, haz solo los cuatro primeros ejercicios: media sesión hecha en casa sigue siendo una sesión, y es exactamente lo que hace que este plan no acabe otra vez en el armario."
 },
 {
  "category": "principiantes",
  "title": "Empezar · en pareja, misma rutina",
  "case": "Para dos personas que empiezan juntas y quieren la misma rutina adaptable a cada una.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body compartido A-B-C",
  "split_rationale": "Una única hoja para los dos con sesiones de cuerpo completo, pensadas para hacerse alternando series en el mismo aparato: mientras uno trabaja, el otro descansa, y así el descanso real coincide con el tiempo de la serie del compañero. Cada uno lleva su propia columna de pesos; el ejercicio, las series y las repeticiones son idénticos.",
  "sessions": [
   {
    "day": "Martes",
    "name": "Sesión A — alternando en el mismo aparato",
    "warmup": "5 minutos de bicicleta cada uno y 10 band pull-apart juntos. Empezad y acabad a la vez.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Alternad serie a serie con la misma mancuerna solo si os cuadra el peso; si no, dos mancuernas al lado y cambio rápido."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Anotad cada uno el número de asiento: cambiarlo entre series es cuestión de dos segundos."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Tirón al ombligo con el tronco quieto; corregíos el uno al otro desde fuera."
     },
     {
      "name": "Curl femoral tumbado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Cadera pegada al banco y bajada de dos segundos."
     },
     {
      "name": "Face pull en polea",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos altos; dos series rápidas alternando."
     },
     {
      "name": "Plancha abdominal",
      "sets": 3,
      "rep_range": "20-30s",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Esta la hacéis a la vez, uno al lado del otro; el que rompa la posición para."
     }
    ],
    "cooldown": "Cinco minutos de caminata juntos y estiramiento de pectoral y cuádriceps, 30 segundos por lado."
   },
   {
    "day": "Jueves",
    "name": "Sesión B — máquinas y cadera",
    "warmup": "5 minutos de elíptica y 10 rotaciones de cadera por lado.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "El cambio de discos entre series es el descanso del otro; tenedlos preparados a los dos lados."
     },
     {
      "name": "Jalón al pecho",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Codos hacia abajo, pecho alto y sin echar el tronco atrás."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Costillas abajo, sin arquear la lumbar para completar la repetición."
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Empuje con los talones y pausa de un segundo arriba."
     },
     {
      "name": "Curl martillo",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos quietos al costado, sin balanceo."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "A la vez en dos esterillas; lumbar pegada al suelo."
     }
    ],
    "cooldown": "Cinco minutos de caminata y movilidad dorsal, 2 minutos."
   },
   {
    "day": "Sábado",
    "name": "Sesión C — peso libre en pareja",
    "warmup": "5 minutos de bicicleta, 10 puentes de glúteo y una serie de aproximación con mancuernas ligeras.",
    "exercises": [
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Miraos de perfil el uno al otro: la espalda tiene que quedarse recta toda la bajada. Corregid antes de subir kilos."
     },
     {
      "name": "Remo con pecho apoyado en banco",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Pecho pegado al banco todo el tirón; dos bancos contiguos si están libres."
     },
     {
      "name": "Press banca con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "El que no entrena vigila la serie del otro desde detrás del banco."
     },
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Mismo cajón, alturas distintas si hace falta; subid sin impulso y bajad frenando."
     },
     {
      "name": "Extensión de tríceps en polea con cuerda",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Codos fijos al costado."
     },
     {
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Cierre de la semana; aguantad la rotación sin mover la cadera."
     }
    ],
    "cooldown": "Diez minutos de caminata juntos comentando cómo ha ido la semana. Esa conversación es parte del plan."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Semana de aprender la mecánica de alternar en el aparato. Cada uno anota sus pesos en su columna; nada de comparar cifras entre vosotros."
   },
   {
    "week": 2,
    "intent": "Progresión",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Cada uno sube donde le hayan sobrado repeticiones, con independencia del otro. Las subidas no tienen por qué coincidir."
   },
   {
    "week": 3,
    "intent": "Carga",
    "load_pct": 105,
    "rir_target": "2-3",
    "volume_note": "Semana más exigente en sentadilla, prensa y peso muerto rumano. Sigue siendo la misma hoja, con dos columnas de kilos."
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Una serie menos por ejercicio. Revisad juntos cuántas de las doce sesiones del mes habéis cumplido: ese es el número que importa."
   }
  ],
  "cardio": {
   "daily_steps": 9000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 2,
     "notes": "Caminata en pareja los domingos y algún día entre semana; es la parte más fácil de sostener cuando se hace acompañado."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90% con una serie menos por ejercicio. Regla del caso: si uno de los dos no puede ir un día, el otro entrena igual. La rutina es compartida, la asistencia es individual, y ese es el punto donde suelen fracasar las parejas que empiezan juntas."
 },
 {
  "category": "principiantes",
  "title": "Empezar · primera vez a los 60",
  "case": "Para quien nunca ha entrenado y empieza pasados los 60, con calma y seguridad.",
  "level": "beginner",
  "days_per_week": 3,
  "place": "gym",
  "split_name": "Full body funcional A-B-C",
  "split_rationale": "Cuerpo completo tres veces por semana en máquinas y con mancuerna ligera, eligiendo ejercicios que reproducen sus gestos del día a día: levantarse de una silla, subir un escalón, recoger algo del suelo y cargar peso caminando. La progresión es de repeticiones antes que de kilos y se evita cualquier movimiento que fuerce el rango de cadera que hoy tiene limitado.",
  "sessions": [
   {
    "day": "Lunes",
    "name": "Sesión A — base con máquinas",
    "warmup": "8 minutos de bicicleta a resistencia baja para soltar la cadera, más 10 círculos de hombro y 10 puentes de glúteo.",
    "exercises": [
     {
      "name": "Prensa de piernas horizontal",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Baja solo hasta donde la cadera te deje sin molestar; el recorrido cómodo de hoy será más amplio dentro de un mes."
     },
     {
      "name": "Remo sentado en polea",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 105,
      "technique_cue": "Pecho alto y tirón al ombligo; sin echar el tronco atrás."
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 105,
      "technique_cue": "Asiento a la altura del esternón; empuja sin bloquear el codo de golpe."
     },
     {
      "name": "Curl femoral sentado",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "3",
      "rest_sec": 90,
      "technique_cue": "Ritmo lento en la vuelta; sin tirones."
     },
     {
      "name": "Puente de glúteos",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "En colchoneta y sin peso al principio; empuja con los talones y aprieta arriba dos segundos."
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Lumbar pegada al suelo y respiración tranquila; movimiento pequeño y bien hecho."
     }
    ],
    "cooldown": "Cinco minutos de bicicleta suave y estiramiento de flexor de cadera apoyado en un banco, 40 segundos por lado."
   },
   {
    "day": "Miércoles",
    "name": "Sesión B — levantarse y empujar",
    "warmup": "8 minutos de bicicleta, 10 sentadillas parciales apoyándose en un banco y 10 band pull-apart.",
    "exercises": [
     {
      "name": "Sentadilla goblet",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Con un banco detrás: siéntate rozándolo y levántate. Es exactamente el gesto de bajar del coche, entrenado."
     },
     {
      "name": "Jalón agarre estrecho neutro",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 105,
      "technique_cue": "Agarre neutro, más cómodo para el hombro; tira con los codos."
     },
     {
      "name": "Press de hombros en máquina",
      "sets": 2,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 105,
      "technique_cue": "Peso ligero; poder levantar a la nieta por encima de la cabeza empieza aquí, pero sin prisa."
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2-3",
      "rest_sec": 105,
      "technique_cue": "Empuje con los talones; el glúteo fuerte es lo que suelta la cadera rígida."
     },
     {
      "name": "Elevación de talones sentado",
      "sets": 2,
      "rep_range": "12-15",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Recorrido completo con pausa arriba; el tobillo también participa en el equilibrio."
     },
     {
      "name": "Bird dog",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Lento, sin ladear la cadera; cinco segundos por repetición."
     }
    ],
    "cooldown": "Cinco minutos de caminata y movilidad de cadera sentado, 3 minutos."
   },
   {
    "day": "Viernes",
    "name": "Sesión C — gestos del día a día",
    "warmup": "8 minutos de caminata en cinta, 10 subidas a escalón bajo y 10 band pull-apart.",
    "exercises": [
     {
      "name": "Subida a cajón",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 105,
      "technique_cue": "Escalón bajo y sujeto a la barra; sube sin impulso y baja frenando. Son las escaleras de tu casa entrenadas."
     },
     {
      "name": "Remo en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "3",
      "rest_sec": 105,
      "technique_cue": "Pecho apoyado y hombros lejos de las orejas."
     },
     {
      "name": "Contractora de pecho",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 90,
      "technique_cue": "Cierra sin chocar las manos y abre despacio."
     },
     {
      "name": "Peso muerto rumano con mancuernas",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "3",
      "rest_sec": 120,
      "technique_cue": "Mancuernas muy ligeras. Cadera atrás y espalda recta: este es el gesto de recoger a tu nieta del suelo, y es el ejercicio más importante de tu plan."
     },
     {
      "name": "Paseo del granjero unilateral",
      "sets": 3,
      "rep_range": "30-40s",
      "rir": "2",
      "rest_sec": 75,
      "technique_cue": "Una mancuerna en una mano, camina erguido y sin inclinarte; la compra de los sábados en versión entrenada."
     },
     {
      "name": "Plancha abdominal",
      "sets": 2,
      "rep_range": "20-30s",
      "rir": "3",
      "rest_sec": 60,
      "technique_cue": "Apoyo en codos y rodillas si hace falta; veinte segundos bien hechos son suficientes."
     }
    ],
    "cooldown": "Ocho minutos de caminata a ritmo cómodo y estiramiento de isquios y glúteo, 40 segundos por lado."
   }
  ],
  "weekly_progression": [
   {
    "week": 1,
    "intent": "Adaptación",
    "load_pct": 100,
    "rir_target": "3-4",
    "volume_note": "Semana de conocer las máquinas y anotar asientos y pesos. Cargas muy conservadoras: salir con ganas de más es exactamente el objetivo."
   },
   {
    "week": 2,
    "intent": "Progresión",
    "load_pct": 102.5,
    "rir_target": "3",
    "volume_note": "Se progresa primero en repeticiones y en recorrido, no en kilos. Si la cadera va soltándose, baja un poco más en prensa y sentadilla."
   },
   {
    "week": 3,
    "intent": "Carga",
    "load_pct": 105,
    "rir_target": "3",
    "volume_note": "Primera subida real de peso en prensa, remo y hip thrust. En este caso nunca se entrena al fallo, en ninguna serie."
   },
   {
    "week": 4,
    "intent": "Descarga",
    "load_pct": 90,
    "rir_target": "4",
    "volume_note": "Una serie menos por ejercicio. Prueba práctica de la semana: levantar a la nieta del suelo y bajar del coche sin manos, y comparar con el primer día."
   }
  ],
  "cardio": {
   "daily_steps": 8000,
   "sessions": [
    {
     "type": "liss",
     "minutes": 30,
     "times_per_week": 4,
     "notes": "Caminata diaria a paso cómodo, mejor por la mañana. Es la base de tu autonomía y no se salta ni las semanas de descarga."
    }
   ]
  },
  "deload_instructions": "Semana 4 al 90% con una serie menos por ejercicio, manteniendo las caminatas. Si algún día notas la cadera especialmente rígida, dedica diez minutos más de bicicleta suave antes de empezar y reduce el recorrido de las sentadillas ese día; nunca fuerces un rango que duela."
 },
 {
  "category": "salud_espalda",
  "title": "Dolor lumbar de estar sentado",
  "case": "Para quien pasa el día sentado y arrastra dolor lumbar inespecífico al final de la jornada.",
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
  "title": "Hernia discal estabilizada (con alta médica)",
  "case": "Para quien tiene una hernia lumbar estabilizada y alta médica para entrenar fuerza.",
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
  "title": "Cervicales y muchas horas de pantalla",
  "case": "Para quien sufre cervicalgia por trabajar frente al ordenador y entrena en casa.",
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
      "name": "Curl femoral con toalla deslizante",
      "sets": 3,
      "rep_range": "8-10",
      "rir": "2-3",
      "rest_sec": 75,
      "technique_cue": "Con una toalla en suelo liso; si notas tirón, acorta el recorrido."
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
  "title": "Hombro que duele al elevar el brazo",
  "case": "Para quien entrena desde hace años y arrastra un hombro doloroso en los movimientos por encima de la cabeza.",
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
     },
     {
      "name": "Hip thrust en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Empuje de cadera sin implicar el hombro; termina apretando el glúteo."
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
     },
     {
      "name": "Dead bug",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 60,
      "technique_cue": "Lumbar pegada al suelo; el core trabaja sin cargar el hombro."
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
  "title": "Rodilla del corredor",
  "case": "Para quien corre y tiene dolor anterior de rodilla que le impide sumar kilómetros.",
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
  "title": "Artrosis leve de rodilla",
  "case": "Para quien tiene artrosis leve diagnosticada y quiere mantener fuerza y autonomía sin impacto.",
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
  "title": "Posparto tras cesárea (con alta médica)",
  "case": "Para quien vuelve a entrenar tras una cesárea, con visto bueno médico, desde casa.",
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
  "title": "Embarazo (con autorización médica)",
  "case": "Para quien está embarazada, tiene autorización médica y experiencia previa en el gimnasio.",
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
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "12-15",
      "rir": "2-3",
      "rest_sec": 75,
      "technique_cue": "Isquios sin tumbarte boca abajo: ayuda con las molestias lumbopélvicas."
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
    "load_pct": 100,
    "rir_target": "3",
    "volume_note": "Se mantienen las cargas de la semana 2; si hay fatiga inusual, se repiten las de la semana 1."
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
  "title": "Osteoporosis incipiente",
  "case": "Para quien necesita cargar el esqueleto con seguridad tras una densitometría con pérdida de hueso.",
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
     },
     {
      "name": "Curl femoral sentado",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Cadena posterior: protege la columna y ayuda a no perder el equilibrio."
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
  "title": "Tensión alta controlada",
  "case": "Para quien es hipertenso con medicación y alta médica: sin bloqueos de respiración ni llegar al fallo.",
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
  "title": "Diabetes tipo 2 y vida sedentaria",
  "case": "Para quien tiene diabetes tipo 2 controlada y necesita constancia casi diaria.",
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
  "title": "Obesidad con dolor articular",
  "case": "Para quien pesa de más y le duelen rodillas y tobillos al final del día.",
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
  "title": "Escoliosis leve",
  "case": "Para quien tiene escoliosis leve diagnosticada sin dolor limitante y quiere ganar fuerza con criterio.",
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
      "name": "Press Pallof",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "1-2",
      "rest_sec": 60,
      "technique_cue": "Antirrotación pura: aguanta sin girar el tronco, que es justo lo que buscamos aquí."
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
  "title": "Postura encorvada (cifosis postural)",
  "case": "Para quien pasa muchas horas encorvado y quiere abrir el pecho y corregir la postura.",
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
     },
     {
      "name": "Press de pecho en máquina",
      "sets": 3,
      "rep_range": "10-12",
      "rir": "2",
      "rest_sec": 90,
      "technique_cue": "Recorrido completo con los omóplatos apoyados: empujar también educa la postura."
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
  "title": "Codo con tendinopatía (epicondilitis)",
  "case": "Para quien tiene el codo irritado con los agarres intensos y quiere seguir entrenando.",
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
  "title": "Fascitis plantar",
  "case": "Para quien pasa el día de pie con dolor en la planta y no puede asumir impactos.",
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
  "title": "Estrés alto y mal descanso",
  "case": "Para quien vive con estrés, duerme mal y necesita entrenar en casa sin sumar fatiga.",
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
  "title": "Fibromialgia leve",
  "case": "Para quien tiene fibromialgia diagnosticada y sufre brotes si se pasa de intensidad.",
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
    "load_pct": 100,
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
  "title": "Equilibrio y autonomía a partir de los 65",
  "case": "Para quien pasa de los 65, ha perdido equilibrio y fuerza, y quiere mantener su autonomía en casa.",
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
  "title": "Mareos al esfuerzo, empezar muy suave",
  "case": "Para quien es muy sedentario y se marea al esforzarse: progresión mínima y controlada.",
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
