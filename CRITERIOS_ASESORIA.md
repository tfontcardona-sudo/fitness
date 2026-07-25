# CRITERIOS DE ASESORÍA — libro de estilo (metodología explícita)

> **Para qué sirve** (hardening §7): éste es *tu* criterio, no "la nutrición en
> general". Se inyecta como referencia en la generación de planes y, en el futuro,
> en el panel de supervisión: los revisores juzgan un plan **contra este documento**,
> no contra un libro de texto. Cuanto más completo esté, menos tendrás que corregir
> a mano.
>
> **Estado**: arrancado automáticamente extrayendo lo que YA está implícito en el
> código (`services/ai/prompts.py`, `services/guardrails.py`, `services/metrics.py`,
> `services/nutrition_scale.py`). Los huecos que solo tú puedes rellenar están
> marcados **`[PENDIENTE TONI]`** — complétalos cuando puedas.

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

`[PENDIENTE TONI]`: ¿ajustas estos rangos para algún perfil concreto (mujer en
menopausia, mayores de 60, deportista de resistencia)? ¿Prefieres un extremo del
rango por defecto (más conservador / más agresivo)?

## 2. Estructura de comidas

- Nº de comidas: el del cliente; si lo delega, 3–5 según objetivo y rutina.
- Proteína repartida 0,3–0,5 g/kg por toma.
- Doble medida siempre (gramos crudos + medida casera).
- Comidas pre/post entreno sobre la **hora real** declarada.

`[PENDIENTE TONI]`: ¿estructuras de comida que usas por defecto (ej. desayuno
salado, cena ligera)? ¿alimentos "bandera" que casi siempre metes? ¿alimentos que
NO usas nunca aunque cuadren macros?

## 3. Alimentos que priorizo / evito

`[PENDIENTE TONI]`: lista tus **fuentes preferidas** por macro (proteínas, hidratos,
grasas, verduras, lácteos/alternativas) y las que **descartas** por criterio propio
(no solo por alergia). Esto es lo que más "suena a ti" en un plan.

## 4. Suplementación que contemplo

- Con evidencia: creatina 5 g/día · cafeína 3–6 mg/kg pre-entreno si tolera ·
  proteína en polvo (conveniencia) · vitamina D · omega-3. **Nunca** fármacos.

`[PENDIENTE TONI]`: ¿algún protocolo propio (magnesio nocturno, electrolitos en
definición, etc.)? ¿marcas o formatos que recomiendas?

## 5. Entrenamiento

- División por días: 2→Full Body · 3→FB o U-L+FB · 4→Upper-Lower · 5→U-L+PPL ·
  6→PPL×2. Siempre justificada.
- Sobrecarga progresiva explícita (doble progresión + RIR objetivo), deload
  semana 4 (volumen −40–50%, intensidad −10–20%).
- Volumen por grupo con landmarks: mínimo productivo ~6 series/sem, techo ~25;
  frecuencia ≥2/sem salvo justificación. Equilibrio empuje/tracción y rodilla/cadera.
- Volumen e intensidad ajustados a la profundidad del déficit (nada de mesociclo
  de sobrecarga con −25% de kcal).

`[PENDIENTE TONI]`: ¿ejercicios que prefieres/evitas por criterio? ¿rangos de reps
por objetivo que uses siempre? ¿cómo planteas la progresión con tus palabras?

## 6. Cómo redacto / tono

- Español, cercano pero profesional; explico el **porqué** en lenguaje claro, sin
  aritmética. Reglas de flexibilidad explícitas (comidas sociales 1–2/sem, alcohol,
  viajes, qué hacer si falla una comida: compensación simple, nunca castigo).

`[PENDIENTE TONI]`: ¿muletillas o frases que usas? ¿cómo abres y cierras un plan?
¿qué NO dices nunca a un cliente?

## 7. Seguridad clínica (ya en el sistema)

- Pautas específicas por patología (diabetes/tiroides) aplicadas en la dieta.
- Lesiones/medicación filtran ejercicios antes de la IA.
- Lista roja de auto-envío (ver §12 del prompt de hardening): menores/mayores,
  embarazo/lactancia, IMC<18,5, TCA, patologías y medicación con interacción.

`[PENDIENTE TONI]`: ¿patologías adicionales para las que tienes pautas propias?
¿cuándo derivas a médico?

---

*Este documento es la fuente de verdad de "mi criterio". Edítalo con libertad; el
sistema lo usará como referencia de generación y de revisión.*
