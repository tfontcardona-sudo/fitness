# INFORME DE HARDENING — Endurecimiento del generador de asesorías

**Rama**: `hardening/asesorias-v2` (nunca `main`; **no se ha desplegado nada**).
**Base**: último `main` (integra hasta PR #78).
**Suite**: **224/224 en verde** (incluye los nuevos tests de §1, §3 y §9.0).
**Modelo de trabajo**: commits atómicos, cada uno con la suite en verde, para que
puedas revisar la rama por partes.

---

## 0. Lectura honesta del alcance

El prompt es una hoja de ruta para una **v2 completa** (14 secciones, varias de
ellas proyectos en sí mismas: base de datos de alimentos con solver, panel de 10
revisores independientes, motor quincenal determinista, ICP, golden set, modo
sombra, aprendizaje continuo). No es realista construir las 14 a calidad de
producción y con la suite en verde en una sola tanda — y fingirlo sería justo la
deriva que este encargo quiere eliminar.

Por eso he priorizado por **impacto y por lo que reduce tu necesidad de revisar**,
siguiendo el propio orden del documento: he cerrado del todo y con tests las piezas
**fundacionales** (§1, §3, §9.0 validador) y he dejado el resto con **andamiaje +
las partes deterministas** donde aportaba, documentado aquí con precisión.

---

## 1. Lo que queda HECHO y probado

### §1 · Consolidación (commit `f52eee7`)
- `CLAUDE (1).md` → **`CLAUDE.md`** (doc vivo único; Claude Code lo autocarga).
- Los 3 traspasos solapados → **`docs/HISTORICO.md`** (archivo histórico de solo
  referencia). Borrados `TRASPASO.md` (raíz), `traspaso/TRASPASO.md`,
  `fable-bundle/01-TRASPASO.md`.
- Borrados los **snapshots de código obsoletos** que competían como fuente de
  verdad (`traspaso/CODIGO-*.md`, todo `fable-bundle/`). El código es la fuente.
- **Preservados** los assets de referencia reales en `docs/referencias/`
  (anamnesis oficial en blanco, ejemplo rellenado, ejemplo de feedback).
- Descartada `canvis-anamnesi/`: parche **ya aplicado y superado** (comprobado
  endpoint por endpoint; el `storage.py` actual, 339 líneas, supera al del parche).

### §1 · Fin de la duplicación Python↔TS (commit `50cf448`)
La lógica de objetivos calóricos estaba duplicada en `nutrition_scale.py`
(backend, autoridad) y `nutritionTargets.ts` (editor). Solución (opción del propio
prompt): **contrato compartido + test de paridad**, sin obligar a un único
lenguaje (el editor necesita cálculo local para responder al instante).
- `shared/nutrition_contract.json`: vectores dorados generados desde el backend
  (`scripts/gen_nutrition_contract.py`).
- `tests/test_nutrition_parity.py`: verifica que **Python reproduce el contrato**
  y que el **TS, transpilado con esbuild y ejecutado con node, produce lo mismo**.
  Si cualquiera deriva, **falla la CI**.
- **Bug real cazado al escribir el test**: `macros_for_kcal` usaba `round()`
  bancario de Python (95×1,9 = 180,5 → **180 g**) mientras el editor usa
  `Math.round` half-up (**181 g**): el coach veía 181 y el backend persistía 180.
  Alineado el backend al helper `_rhu` (half-up, la convención ya usada en el
  reescalado). **Una sola verdad numérica.**

### §3 · Cálculo energético individualizado + macros en código (commits `fc0b05c`, `8eab701`)
Corrige los hallazgos **#2, #3, #4 y #6** del audit:
- **#3** `energy_targets` ya **no usa el punto medio**. El ajuste sobre el TDEE se
  elige por **% graso** (pérdida: alto/medio/bajo por sexo) o **experiencia**
  (ganancia: novato vs int/avanzado), con su **ritmo diana** (%/semana); la
  adherencia histórica, si se conoce, mueve el punto dentro del rango. Un cliente
  al 12% y otro al 35% ya **no** reciben el mismo déficit. **Ya está en vivo** (fluye
  por el punto de consumo existente en `clients.py`).
- **#4** `tdee_by_components`: **NEAT por pasos + EAT del entreno planificado + ETA**,
  con el método clásico como fallback y **aviso si divergen >15%**. Pasos aproximados
  por nivel de actividad declarado (la anamnesis aún no pide pasos exactos).
- **#2** `macro_targets`: **reparto completo en código** (proteína por objetivo;
  grasa ≥0,6 g/kg —0,7 en mujer— y 20–35% de kcal; carbohidratos = resto con suelo
  2/3 g/kg; fibra; agua). Si los suelos no caben, **sube las kcal** en vez de romper
  un suelo. Se **entrega a la IA como contrato** (`metricas_backend.macros_objetivo_g`):
  la IA construye el menú, **no decide los gramos de macros**. `kcal declaradas =
  suma 4/4/9 exacta` (una sola verdad).
- **#6** `prompts.py`: **quitadas las fórmulas** de BMR/TDEE y el reparto de macros
  del prompt (contradecían el "el backend ya te los da, no recalcules"). La IA ya
  no conoce ni necesita las fórmulas.
- **Nota**: `metrics.py` se **extendió, no se reescribió** (respeta "no reescribir lo
  que funciona"). Tests contra valores calculados a mano
  (`tests/test_metrics_hardening.py`).

### §9.0 · Validador determinista con veto (commit `03e1e3d`)
`validate_plan_deterministic` en `guardrails.py` — el **"Revisor 0"** del panel de
supervisión, en código y más estricto que `check_nutrition`:
- **Atwater**: kcal declaradas = 4/4/9 de sus macros (totales **y cada opción**).
- **Σ objetivos de comida = total del día**, eje por eje.
- **Tolerancias vs el contrato** del §3: kcal ±2%, P ±5 g, G ±5 g, HC ±10 g.
- **Cero alérgenos y cero alimentos odiados** (aquí odiado = **veto**), buscando
  también en **título y preparación** (subingredientes: "pesto", "tortilla",
  "salsa césar").
- **Restricción dietética ética/religiosa al 100%** (vegano/vegetariano/pescetariano/
  sin cerdo/halal/kosher).
- **nº de comidas correcto** y **porciones realistas** (nada de 900 g de pollo ni
  10 huevos; los líquidos no cuentan como porción absurda).
- Extiende guardrails (no reescribe). 11 tests (`tests/test_deterministic_validator.py`).

### Documentos entregados
- **`CLAUDE.md`** actualizado (sección de estado del hardening; ver §4 abajo).
- **`CRITERIOS_ASESORIA.md`** arrancado desde el código, con huecos `[PENDIENTE TONI]`.
- **`INFORME_HARDENING.md`** (este documento).

---

## 2. Decisiones que he tomado por mi cuenta (y por qué)

1. **Dedup por contrato, no por reescritura.** El prompt permitía "una sola
   implementación (front consume API)" **o** "contrato compartido con tests de
   paridad". Elegí lo segundo: el editor necesita cálculo local para responder al
   instante; forzar una ida y vuelta al backend en cada tecla degradaría la UX sin
   ganancia real. El contrato + test de paridad mata la deriva igual de bien.

2. **No borré las ramas `claude/*`.** El prompt decía "ya están integradas,
   bórralas", pero `git` reporta `claude/continue-previous-n6layq` como **no
   fusionada** (sus cambios están en `main` vía *squash-merge*, que cambia los SHA).
   Verifiqué que el contenido (p. ej. `ai_credit.py`) **sí está en `main`**, pero
   borrar una rama remota es **irreversible** y prefiero no arriesgar sobre una
   señal ambigua de git. **Recomendación**: bórrala tú desde GitHub cuando lo
   confirmes; es inofensiva mientras tanto.

3. **`recomp` pasa a ser −5%…0% (no mantenimiento exacto).** El audit lo pide en la
   tabla del §3. Actualicé el test que asumía "recomp = 0% exacto" al nuevo
   contrato (no es "trampa": el test viejo codificaba el comportamiento que el
   hardening cambia a propósito).

4. **TDEE por componentes con datos aproximados.** La anamnesis no pide pasos
   exactos, así que mapeo `daily_activity_level` → pasos representativos y uso el
   método clásico como fallback. Así el método por componentes **funciona ya** y no
   cambia los números actuales (el clásico sigue siendo la base); la divergencia se
   avisa. Cuando añadas "pasos/día" a la anamnesis, se vuelve primario sin tocar código.

5. **El validador determinista se entrega como función probada, aún no como veto
   bloqueante en generación.** Es el "Revisor 0" del panel del §9; hacerlo
   bloqueante **sin el bucle de reparación** del §9 podría tumbar generaciones sin
   forma de auto-corregirlas. Queda listo y testeado para enchufarlo cuando exista
   el panel + bucle (ver pendientes).

---

## 3. Lo que queda PENDIENTE (y por qué)

Ordenado por impacto. Nada de esto está a medias en el código: está **no empezado**
salvo donde indico "andamiaje".

- **§2 · Base de datos de alimentos + solver de porciones (scipy).** Es el cambio
  de mayor impacto y también el más grande. Requiere: tabla `food` (composición
  real BEDCA/USDA con alérgenos y etiquetas), cambiar el contrato con la IA
  (devuelve IDs, no gramos), y un solver `scipy.optimize` que fije las cantidades.
  **`scipy` no está instalado** en el entorno y la descarga de BEDCA/USDA a través
  del proxy no es fiable en esta sesión. Pendiente como bloque propio. *(El
  validador de porciones del §9.0 ya mitiga lo peor —cantidades absurdas— mientras
  tanto.)*
- **§4 · Modelo único `PlanState` + versionado v1/v2/v3 + grafo de dependencias
  bidireccional.** El sistema ya reconcilia el plan como organismo
  (`reconcile_nutrition`) y el documento se genera desde los datos; falta el
  `PlanState` Pydantic formal con historial y revert, y la propagación bottom-up
  explícita.
- **§5 · Extracción de anamnesis con confianza + doble pase + detección de
  contradicciones + matriz de cobertura.** No empezado.
- **§6 · Coherencia dieta↔entreno profunda** (ciclado de HC por día, pre/post sobre
  hora real, volumen vs profundidad del déficit). Parcial: las pautas ya están en
  el prompt; falta la validación determinista cruzada.
- **§7 · Libro de estilo**: **arrancado** (`CRITERIOS_ASESORIA.md`), pendiente que
  Toni rellene los `[PENDIENTE TONI]` y su inyección en generación/panel.
- **§8 · Motor quincenal determinista** (medias móviles, reglas de decisión, tope
  de cambio por revisión, "no tocar" como decisión válida). No empezado; el sistema
  ya adapta quincenalmente pero sin el motor determinista de reglas.
- **§9 · Panel de 10 revisores independientes + árbitro + bucle de reparación.**
  **Andamiaje**: el Validador 0 (determinista) está hecho y testeado; falta el
  contrato JSON de revisores IA, la ejecución en paralelo con contexto aislado, el
  árbitro y el bucle de reparación (máx. 3 iteraciones).
- **§10 · Simulación 12 semanas, prueba de estrés de adherencia, mejor-de-N,
  checklist de sentido común, canario.** No empezado.
- **§11 · Índice de Confianza del Plan (ICP).** No empezado (depende del panel).
- **§12 · Semáforo + desbloqueo progresivo por segmento.** No empezado (depende de
  ICP + panel).
- **§13 · Aprendizaje continuo** (captura de ediciones, clasificador,
  `MEJORAS_PROPUESTAS.md`). No empezado; `plan_diff.py` ya da la base del diff.
- **§14 · Golden set (30–40 perfiles) + determinismo (temp 0) + prompts versionados
  + modo sombra + telemetría.** No empezado. **Nota**: el "CRITERIO DE TERMINADO"
  pide el golden set en verde; no está creado, así que ese criterio queda
  parcialmente cumplido (suite completa en verde, golden set pendiente).

---

## 4. Cómo revisar esta rama

```bash
git checkout hardening/asesorias-v2
git log --oneline main..HEAD          # 5 commits atómicos, uno por pieza
cd backend && python -m pytest        # 224/224 (necesita Postgres local)
```
Los commits están pensados para revisarse de uno en uno; cada uno deja la suite en
verde. La CI puede añadir el test de paridad TS (necesita node+esbuild, que ya
están en el frontend).

---

*Ningún cambio toca `main` ni se ha desplegado. La rama queda lista para tu
revisión y merge cuando lo decidas.*
