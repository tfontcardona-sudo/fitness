# CRITERIOS DE ASESORÍA — libro de estilo (metodología explícita)

> **Para qué sirve** (hardening §7): éste es *tu* criterio, no "la nutrición en
> general". Se inyecta como referencia en la generación de planes y, en el futuro,
> en el panel de supervisión: los revisores juzgan un plan **contra este documento**,
> no contra un libro de texto. Cuanto más completo esté, menos tendrás que corregir
> a mano.
>
> **Estado**: arrancado automáticamente extrayendo lo que YA está implícito en el
> código (`services/ai/prompts.py`, `services/guardrails.py`, `services/metrics.py`,
> `services/nutrition_scale.py`) y COMPLETADO con el criterio del coach
> (agosto 2026). Edítalo con libertad cuando tu criterio evolucione.

---

## 0. Principio rector: la anamnesis manda

**Toda la asesoría parte de la anamnesis del cliente.** No hay plantillas ni
preferencias del coach por encima de lo que el cliente declaró: objetivo, número
de comidas, alimentos que le gustan o rechaza, alergias, lesiones, medicación,
horarios y contexto salen de SU anamnesis, leída completa y sin omitir nada. El
sistema debe entender el documento entero — frase a frase, incluidas notas a
mano y comentarios sueltos — porque el plan, el seguimiento diario y los
informes se construyen y se juzgan contra esa información. Si un
dato de la anamnesis es ambiguo o contradictorio, se recoge y lo resuelve el
coach: nunca se descarta en silencio.

---

## 1. Energía y macros (ya calculado por el backend — no lo decide la IA)

- **BMR**: Mifflin-St Jeor; Katch-McArdle si hay % graso fiable (3–60%).
- **TDEE**: NEAT por ocupación/pasos + entreno; método por componentes con
  fallback al factor clásico (aviso si divergen >15%).
- **Ajuste calórico individualizado** por % graso y experiencia (no punto medio):
  | Objetivo | Ajuste sobre TDEE | Ritmo diana |
  |---|---|---|
  | Pérdida, % graso alto (H≥25 / M≥32) | −20% a −25% | 0,7–1,0 %/sem |
  | Pérdida, % graso medio | −15% a −20% | 0,5–0,7 %/sem |
  | Pérdida, % graso bajo (H<15 / M<23) | −10% a −15% | 0,3–0,5 %/sem |
  | Recomposición | −5% a 0% | peso estable |
  | Ganancia, novato | +12% a +15% | 0,25–0,5 %/sem |
  | Ganancia, intermedio/avanzado | +5% a +10% | 0,1–0,25 %/sem |
- **Proteína** (g/kg, punto medio del rango): pérdida 2,0–2,4 · ganancia 1,6–2,2 ·
  recomp 2,2–2,6 · mantenimiento 1,6–2,2 · lesión 2,0–2,5.
- **Grasa**: ≥0,6 g/kg (≥0,7 en mujeres) **y** dentro del 20–35% de las kcal.
- **Carbohidratos**: el resto, con **suelo 2 g/kg** si entrena ≥3 días y **3 g/kg**
  si ≥5; priorizados peri-entrenamiento.
- **Fibra** 14 g/1.000 kcal (mínimo 25 g). **Agua** 30–40 ml/kg (guía 35).
- **Regla innegociable**: si los suelos no caben en las kcal, se **suben las kcal**
  (se reduce el déficit). Nunca se rompe un suelo ni un tope de ritmo por un plazo.

**Criterio del coach**: por defecto se arranca SIEMPRE en el **extremo
conservador** del rango (déficit/superávit más suave). Solo la adherencia
demostrada en el seguimiento (≥85%) da derecho a moverse hacia el extremo
agresivo; sin historial, prudencia. Los rangos no se personalizan por plantillas
de perfil: la individualización sale del perfil REAL que aparezca en la
anamnesis subida (sexo, % graso, experiencia, contexto), que es la que fija el
bracket de la tabla.

## 2. Estructura de comidas

- Nº de comidas: el del cliente; si lo delega, 3–5 según objetivo y rutina.
- Proteína repartida 0,3–0,5 g/kg por toma.
- Doble medida siempre (gramos crudos + medida casera).
- Comidas pre/post entreno sobre la **hora real** declarada.

**Criterio del coach**: el número y reparto de comidas lo define la ANAMNESIS
(lo que el cliente declaró) o el coach a mano en la ficha; si el cliente lo
delega, decide la IA dentro del marco 3–5. **No hay estructuras por defecto**
(ni "desayuno salado" ni "cena ligera" impuestos): la estructura se adapta al
horario y contexto real del cliente.

## 3. Alimentos que priorizo / evito

**Criterio del coach**: **no hay alimentos "estrella" ni vetos predefinidos del
coach.** Los alimentos a priorizar y a evitar son EXACTAMENTE los que el cliente
especifica en su anamnesis: preferencias (`food_likes`), aversiones
(`food_dislikes`), alergias/intolerancias (`food_allergies`) y patrón dietético
(vegano, halal…). La IA construye el banco de comidas con alimentos comunes,
frescos y fáciles de encontrar, respetando al 100% lo declarado — las aversiones
vetan igual que las alergias en la práctica del menú.

## 4. Suplementación que contemplo

- Con evidencia: creatina 5 g/día · cafeína 3–6 mg/kg pre-entreno si tolera ·
  proteína en polvo (conveniencia) · vitamina D · omega-3. **Nunca** fármacos.

**Criterio del coach**: no hay protocolos fijos propios — la suplementación la
propone la IA **según los datos y objetivos del cliente en su anamnesis**
(sueño, estrés, dieta real, entrenamiento, analítica declarada), siempre dentro
del marco con evidencia de arriba y justificando cada suplemento con su porqué.
Menos es más: solo lo que aporte a ESE cliente. Los productos concretos se
enlazan desde Recursos (partner ESN) cuando existen.

## 5. Entrenamiento

- División por días: 2→Full Body · 3→FB o U-L+FB · 4→Upper-Lower · 5→U-L+PPL ·
  6→PPL×2. Siempre justificada.
- Sobrecarga progresiva explícita (doble progresión + RIR objetivo), deload
  semana 4 (volumen −40–50%, intensidad −10–20%).
- Volumen por grupo con landmarks: mínimo productivo ~6 series/sem, techo ~25;
  frecuencia ≥2/sem salvo justificación. Equilibrio empuje/tracción y rodilla/cadera.
- Volumen e intensidad ajustados a la profundidad del déficit (nada de mesociclo
  de sobrecarga con −25% de kcal).

**Criterio del coach**: no hay ejercicios favoritos ni vetados por sistema — la
selección la hace la IA **a partir de la anamnesis** (nivel, lesiones, material,
días, duración de sesión, historial deportivo), dentro de los guardrails
deterministas que filtran por lesión y material. Los rangos de repeticiones y la
progresión siguen el marco de arriba (doble progresión + RIR, deload semana 4),
adaptados al nivel real declarado.

## 6. Cómo redacto / tono

- Español, cercano pero profesional; explico el **porqué** en lenguaje claro, sin
  aritmética. Reglas de flexibilidad explícitas (comidas sociales 1–2/sem, alcohol,
  viajes, qué hacer si falla una comida: compensación simple, nunca castigo).

**Criterio del coach**: tono **serio y profesional con un toque cercano**, y
COHERENTE en todos los mensajes que recibe el cliente, sean del tipo que sean
(plan, informe de seguimiento, modificación, recordatorio, email, push).
Una sola voz de marca:
- Se abre saludando por el nombre y yendo al grano; se cierra con un refuerzo
  breve y la puerta abierta ("cualquier duda, me escribes").
- Se explica siempre el PORQUÉ de cada decisión en lenguaje claro, sin
  aritmética ni jerga innecesaria.
- Nunca: culpabilizar ("has fallado"), lenguaje de castigo o compensación
  punitiva, promesas de plazos ("en X semanas pesarás Y"), diagnósticos médicos
  ni alarmismo. Los tropiezos se tratan con normalidad y plan de acción, no con
  bronca.

## 7. Seguridad clínica (ya en el sistema)

- Pautas específicas por patología (diabetes/tiroides) aplicadas en la dieta.
- Lesiones/medicación filtran ejercicios antes de la IA.
- Lista roja de auto-envío (ver §12 del prompt de hardening): menores/mayores,
  embarazo/lactancia, IMC<18,5, TCA, patologías y medicación con interacción.

**Patologías comunes con pauta propia** (añadidas a la lista roja del sistema:
el plan queda retenido para revisión del coach, nunca se auto-envía):
- **Gota / hiperuricemia**: moderar carnes rojas, vísceras, marisco y alcohol
  (cerveza sobre todo); limitar fructosa añadida; hidratación alta; el déficit,
  si lo hay, gradual (una pérdida brusca puede disparar un ataque).
- **Intestino irritable / SIBO**: menú simple y repetible, cocciones suaves,
  fibra progresiva (no un salto brusco), cuidado con FODMAP evidentes si el
  cliente ya identificó gatillos; nada de "detox" ni restricciones extremas.
- **Reflujo / hernia de hiato / gastritis**: cena ligera y ≥2-3 h antes de
  acostarse; moderar café, alcohol, picante y fritos; comidas más pequeñas y
  frecuentes si hay síntomas; evitar entrenar tumbado justo tras comer.
- **Anemia / ferropenia**: priorizar hierro hemo (carnes magras, posible
  pescado) + vitamina C en la misma comida; separar café/té y lácteos de las
  comidas ricas en hierro; vigilar energía en el entreno y no forzar volumen
  con síntomas.
- **Osteoporosis / osteopenia**: calcio y vitamina D cubiertos; entrenamiento
  de fuerza CON carga progresiva (es terapéutico), evitando flexión espinal
  cargada y saltos de impacto alto sin progresión; nunca déficits agresivos.
- **Apnea del sueño**: el sueño manda — la pérdida de grasa suele mejorar el
  cuadro; recuperación vigilada (la fatiga real es mayor que la percibida) y
  cafeína con más cautela.
- **Betabloqueantes**: la frecuencia cardíaca NO sirve como referencia de
  intensidad → prescribir por RPE/RIR, nunca por pulsaciones.
- **Antidepresivos / ansiolíticos**: posibles cambios de apetito y peso no
  atribuibles a la dieta — se tiene en cuenta en las revisiones antes de tocar
  kcal; adherencia flexible, cero culpabilización.

**Cuándo derivo a médico** (no se asesora hasta tener el visto bueno o el dato):
HTA no controlada, dolor torácico o arritmias con esfuerzo, sospecha de TCA,
embarazo, patología renal/hepática/cardiovascular activa sin seguimiento,
analítica claramente alterada sin explicación, dolor articular agudo que no
remite, o cualquier medicación cuya interacción con dieta/entreno no esté clara.
Ante la duda: primero el médico, después el plan.

---

*Este documento es la fuente de verdad de "mi criterio". Edítalo con libertad; el
sistema lo usará como referencia de generación y de revisión. Resumen en una
frase: la anamnesis del cliente manda, el arranque es conservador, y el tono es
serio, profesional y cercano en todo lo que le llega al cliente.*
