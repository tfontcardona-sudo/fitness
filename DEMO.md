# DEMO.md — Enseñar Professional a los clientes (guión + preparación)

Todo lo necesario para una demo de ~15 minutos: cómo levantar el entorno, los
datos de demostración y el recorrido en orden vendedor. Sin Stripe, sin Google
y sin email: el sistema funciona igual (esas piezas se activan luego, ver
`PENDIENTE.md`).

---

## 1. Preparar el entorno (una vez, ~15 min)

### Opción A — Tu PC con Docker (demo en persona) ← UN SOLO COMANDO

Con Docker Desktop instalado, clona la rama y lanza el script de demo:

```bash
git clone -b claude/dqr-white-label-4ojp01 <repo> professional && cd professional
./demo.sh              # Mac/Linux
# Windows: clic derecho a demo.ps1 → "Ejecutar con PowerShell"
```

El script lo hace TODO: crea el `.env` de demo (panel: `professional` /
`Professional-Demo-2026`), levanta Docker, espera a la API, siembra los 3
clientes y te imprime los enlaces (panel http://localhost:5173, planes y los
portales de cada cliente con el puerto correcto). Re-ejecutarlo reinicia la
demo. Para IA en vivo, añade `ANTHROPIC_API_KEY` al `.env` y re-lanza.

### Opción B — VPS con subdominio temporal (demo remota, portal en SU móvil)

```bash
# En un VPS Ubuntu limpio, con un subdominio apuntando a su IP (p. ej. demo.tudominio.com):
bash deploy/install-vps.sh     # pide dominio y credenciales; deja HTTPS con Caddy
```

La ventaja: en la reunión abres el portal en el móvil DE ELLOS y lo instalan
como app (icono dorado). Vende más que cualquier pantalla compartida.

### Datos de demostración (en ambos casos)

```bash
docker compose exec api python scripts/demo_seed.py
```

Crea (y REINICIA si se re-ejecuta — idempotente, solo toca `@demo.local`)
**tres clientes = tres fases del ciclo**, para que se vea TODO el producto:

| Cliente | Fase del ciclo | Para enseñar |
|---|---|---|
| **Marta Serra** | Génesis.99 a MITAD de seguimiento (día **8 de 14**, peso 74,8→73,9, comidas elegidas, 4 entrenos con series) | El portal vivo + el dossier |
| **Carlos Bosch** | Génesis.99 con la revisión quincenal **CERRADA ayer** (14/14 días, cierre completo con perímetros y sensaciones) | La notificación al coach + el **Resumen** de métricas (peso −1,2 kg, adherencia 89 %, fuerza e1RM) |
| **Jordi Puig** | **Entreno Personal** presencial (día 5, 2 sesiones registradas, pagado en el centro) | El segundo producto del catálogo |

La CUARTA situación —el alta de un cliente nuevo— se enseña **en vivo** durante
la demo (paso 3 del guión): crear a "Laura Vidal" desde el panel tarda 2
minutos y demuestra el onboarding real delante de ellos.

El script imprime los **enlaces del portal** de los tres: tenlos a mano
(o re-ejecútalo justo antes de la demo para regenerarlos).

---

## 2. Guión de la demo (~15 minutos)

> Regla de oro: enseña el CICLO completo con Marta y no te desvíes. Todo lo
> demás (editor fino, historial, Marca) son "extras" si sobra tiempo.

**1) La venta — página pública de planes (2')**
Abre `/planes`. "Así os llega un cliente desde Instagram": el catálogo REAL —
Génesis.99 a 99 €/mes con pago online, y las tarifas de Entreno Personal tal
cual vuestra web, con reserva por WhatsApp. Baja hasta el bloque del centro
(dirección, horario). Mensaje: *la web vende sola y el que paga entra solo al
sistema*.

**2) El panel del coach — "Hoy" (2')**
Login. El dashboard prioriza el trabajo: fíjate en **Carlos Bosch** — cerró su
revisión quincenal ayer y el sistema tiene al coach avisado y la revisión en
cola. Mensaje: *nadie se pierde; el sistema persigue, vosotros decidís*.

**3) Alta EN VIVO de un cliente (2')**
Crea a "Laura Vidal" delante de ellos: alta manual → selector de plan
(Génesis.99 / Entreno Personal) → queda en cola de anamnesis con
recordatorios automáticos (D+3/D+7). Mensaje: *dar de alta cuesta 2 minutos
y el sistema se encarga de perseguir la anamnesis*.

**3b) La ficha de Marta — anamnesis y plan (3')**
Abre Marta → pestaña **Anamnesis**: todo estructurado (objetivo, medidas,
lesiones, gustos, alergias). Cuenta el flujo real: *el cliente rellena un PDF,
lo sube, y la IA lee hasta la letra manuscrita y rellena esta ficha; vosotros
solo revisáis*. (Con `ANTHROPIC_API_KEY` puesta puedes enseñarlo en vivo con un
PDF rellenado; sin clave, se cuenta con la ficha ya rellena.)
Pestaña **Planificación**: el plan del mes — objetivo, kcal y macros calculados
por el sistema (la IA nunca inventa números), 3 opciones por comida, editor por
si queréis retocar cualquier cifra.

**4) El dossier (2')**
Botón **Descargar** → PDF. Portada negra con el laurel — "esto es lo que
recibe el cliente el día 1 por WhatsApp". Pasa 2-3 páginas: se lee como un
documento serio, con las 3 opciones por comida. Mensaje: *producto premium con
vuestra marca, generado en un clic*.

**5) El portal — en el móvil de ellos (3') ← el momento fuerte**
Abre el enlace de Marta en un móvil (mejor el suyo). Portal oscuro con la
marca: **Hoy** (día 8 de 14, medidor, elegir comida de hoy), **Entreno**
(registra una serie en vivo: peso y reps), **Diario** (peso bajando desde el
día 1). Instala la PWA (añadir a pantalla de inicio → icono dorado). Mensaje:
*el cliente vive aquí; el papel es solo la entrega inicial*.

**6) El ciclo quincenal — donde está el negocio (2')**
Abre la ficha de **Carlos Bosch** → **Seguimiento/Feedback**: su revisión está
CERRADA de ayer — cierre completo (peso final, perímetros, sensaciones 1-5,
adherencia 9/8, qué le costó más) y el botón **"Resumen"** enseña las métricas
calculadas al momento y SIN IA: peso 84,6 → 83,4 (−1,2 kg), adherencia de
dieta 89 %, registro 14/14 días y la fuerza por ejercicio (e1RM). Desde aquí,
"Generar feedback" redacta el informe (IA) que el coach revisa y ENVÍA — con
clave de IA puedes enseñarlo en vivo. Mensaje: *la revisión quincenal, que es
lo que os come horas, queda a un clic — siempre con vuestra supervisión*.

**7) Cierre (1')**
Kit de ventas (Recursos): responder a un interesado con el catálogo o el
enlace de pago en dos clics. Página **Marca**: cambia el color en vivo — *todo
esto es vuestro, con vuestra marca, y se ajusta sin tocar código*. Y lo que
falta para arrancar de verdad: su Stripe, su dominio y su email
(`PENDIENTE.md`) — todo configuración, cero desarrollo.

---

## 3. Preguntas que van a hacer (y respuesta corta)

- **"¿Y el entreno no va en el PDF de Génesis?"** — El dossier entrega la
  nutrición; el entrenamiento vive en la app, donde se registra cada serie y
  se ve el progreso (enséñalo en el portal). Un cliente de solo-entreno sí
  recibe su dossier de entrenamiento. (Si lo quieren también en el PDF de
  Génesis, es un cambio pequeño — apuntarlo.)
- **"¿La IA decide las calorías?"** — No. BMR/TDEE/kcal/macros los calcula el
  sistema con fórmulas fijas y validador; la IA solo redacta comidas y
  entrenos DENTRO de esos números, y todo pasa por vuestra revisión.
- **"¿Y si el cliente es alérgico?"** — Alergias y aversiones se filtran de
  forma determinista ANTES de generar, y un validador veta cualquier plan que
  las incumpla.
- **"¿Cuánto tardo yo por cliente?"** — Alta 2', revisar anamnesis leída 3',
  revisar plan 5', revisión quincenal ~5'. El resto lo empuja el sistema
  (recordatorios, avisos, colas).
- **"¿Qué pagamos aparte?"** — Su Stripe (comisión estándar), el servidor
  (~10-20 €/mes) y el consumo de IA por plan generado (céntimos por plan).

## 4. Reset y trucos

- **¿Mismo PC que DQR?** Sin problema: los proyectos están AISLADOS (Docker
  los separa en `professional-fitness` y `fitness-system`, cada uno con su
  base de datos). Pero usan los mismos puertos, así que **no pueden correr a
  la vez**: para el otro primero (`docker compose down` en su carpeta); el
  lanzador te avisa si detecta los puertos ocupados.
- **Reiniciar la demo**: re-ejecuta `./demo.sh` (o `demo.ps1`) — borra y
  recrea los `@demo.local` e imprime enlaces nuevos del portal. La Laura creada
  en vivo se borra desde el panel (o quedará para la siguiente demo).
- **Sin clave de IA**: no toques "Generar plan"/"Leer con IA" en vivo; todo lo
  demás funciona (el plan de Marta ya está generado).
- **No enseñes** `/oferta` (redirige a planes: correcto, esta marca no la usa).
- Los clientes de demo son `@demo.local`: bórralos antes de entregar la
  instancia real (re-ejecutar el script y luego eliminarlos desde el panel, o
  `wipe_demo_clients`).
