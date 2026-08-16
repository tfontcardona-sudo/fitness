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
# Windows: DOBLE CLIC a demo.bat (evita el bloqueo de scripts de Windows)
```

El script lo hace TODO: crea el `.env` de demo (panel: `professional` /
`Professional-Demo-2026`), levanta Docker, espera a la API, siembra los 4
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
**cuatro clientes = los tres servicios y el ciclo entero**, para que se vea
TODO el producto:

| Cliente | Servicio y momento | Para enseñar |
|---|---|---|
| **Marta Serra** | **Pack completo** (130 €), 8 días de seguimiento (74,8→73,9, comidas elegidas, 4 entrenos con series) + una **petición abierta** desde su portal | El portal vivo + el dossier + el circuito de dudas del cliente |
| **Carlos Bosch** | **Pack completo** con 14 días registrados y el **informe YA redactado en borrador** (camino real del motor, sin gastar API), con **fotos** y medidas actualizadas desde su portal | **Resumen** de métricas (−1,2 kg, adherencia 89 %, e1RM) + el informe: revisar, **editar**, **Word** y **Enviar al cliente** |
| **Jordi Puig** | **Entrenamiento** (70 €), día 5, 2 sesiones registradas, pagado en el centro | El servicio de solo entreno |
| **Núria Camps** | **Dieta** (70 €), 9 días registrados, vegetariana y sin lactosa | El portal REDUCIDO del cliente de dieta: su diario, su evolución y la tienda — sin nada de entreno |

La QUINTA situación —el alta de un cliente nuevo— se enseña **en vivo** durante
la demo (paso 3 del guión): crear a "Laura Vidal" desde el pool tarda 2
minutos y demuestra el onboarding real delante de ellos.

El script imprime los **enlaces del portal** de los cuatro: tenlos a mano
(o re-ejecútalo justo antes de la demo para regenerarlos).

---

## 2. Guión de la demo (~15 minutos)

> Regla de oro: enseña el CICLO completo con Marta y no te desvíes. Todo lo
> demás (editor fino, historial, Marca) son "extras" si sobra tiempo.

**1) La venta — página pública de planes (2')**
Abre `/planes`. "Así os llega un cliente desde Instagram": vuestros tres
servicios REALES, de pago único — **Dieta 70 €**, **Entrenamiento 70 €** y el
**Pack completo 130 €** (dieta + entrenamiento + cuota del gimnasio), cada uno
con su pago online. Baja hasta el bloque del centro (dirección, horario).
Mensaje: *la web vende sola y el que paga entra solo al sistema*.

**2) El panel del coach — "Hoy" (2')**
Login. El dashboard prioriza el trabajo: **Carlos Bosch** (informe en borrador
→ "Enviar") y **Marta Serra** (te ha escrito una duda desde su portal → "Ver
petición", con el texto ya visible). Los demás quedan abajo, "Al día". Mensaje:
*nadie se pierde; el sistema persigue, vosotros decidís*.

**3) Alta EN VIVO de un cliente — desde el pool de RUTINAS (2')**
Abre **Rutinas** (menú): **tres grupos** —Masa muscular, Definición y
Mantenimiento y salud— con **160 planificaciones** de fábrica cuyo título ya
dice para quién es («Ganar músculo · desde cero», «Perder grasa · come fuera
cada día», «Dolor lumbar de estar sentado»), y un **buscador inteligente**:
escribe el caso como lo piensas («adelgazar barriga 3 días», «señora 55
espalda») y sale la que buscas aunque uses otras palabras. Arriba, el filtro de
**servicio**: mira el pool como Dieta, como Entrenamiento o como Pack — cada
plantilla trae también su dieta (cuántas comidas, patrón y en qué se centra).
Elige una para "Laura Vidal" → **"Usar" → Cliente nuevo** → el perfil se crea EN
EL MOMENTO con el plan en borrador y te deja en su Planificación. Enseña también
**"Subir rutina"**: un PDF/Word externo se lee, se mapea a la biblioteca y queda
re-maquetado con el diseño de la marca. Mensaje: *todo el conocimiento del
centro, ordenado y reutilizable en dos clics*.

**3b) La ficha de Marta — anamnesis y plan (3')**
Abre Marta → pestaña **Anamnesis**: todo estructurado (objetivo, medidas,
lesiones, gustos, alergias). Cuenta el flujo real: *el cliente rellena un PDF,
lo sube, y la IA lee hasta la letra manuscrita y rellena esta ficha; vosotros
solo revisáis*. (Con `ANTHROPIC_API_KEY` puesta puedes enseñarlo en vivo con un
PDF rellenado; sin clave, se cuenta con la ficha ya rellena.)
Pestaña **Planificación**: arriba, las **5 planificaciones recomendadas** para
ESTE cliente, cada una con su resumen y el porqué («Encaja por el mismo
objetivo: definición, 3 días, en gimnasio y contempla su rodilla») — salen de su
anamnesis y de lo que registra en el portal. Un clic y ya la tiene; si no
convencen, se busca en el pool o se genera con IA. Debajo, el plan — objetivo,
kcal y macros calculados por el sistema (la IA nunca inventa números), 3
opciones por comida, editor por si queréis retocar cualquier cifra.

**4) El dossier (2')**
Botón **Descargar** → PDF. Portada negra con el laurel — "esto es lo que
recibe el cliente el día 1 por WhatsApp". Pasa 2-3 páginas: se lee como un
documento serio, con las 3 opciones por comida. Mensaje: *producto premium con
vuestra marca, generado en un clic*.

**5) El portal — en el móvil de ellos (3') ← el momento fuerte**
Abre el enlace de Marta en un móvil (mejor el suyo). Portal oscuro con la
marca: **Entreno** (registra una serie en vivo: peso y reps), **Diario** (peso
bajando desde el día 1), **Evolución** (peso, perímetros y cómo se encuentra:
lo actualiza cuando se mide, sin fechas límite) y **Tienda** (vuestros
productos, con su código de descuento). Instala la PWA (añadir a pantalla de
inicio → icono dorado). Abre después el de **Núria**: el portal de quien solo
tiene dieta se reduce a su diario, su evolución y la tienda. Mensaje: *cada
cliente ve exactamente lo que ha contratado*.

**6) El informe — donde está el negocio (3')**
Abre la ficha de **Carlos Bosch** → **Feedback**. Aquí NO hay quincenas ni
cierres: el seguimiento es continuo y el informe se pone al día con lo que el
cliente lleva registrado. El **Resumen** enseña las métricas calculadas al
momento y SIN IA: 84,6 → 83,4 (−1,2 kg), adherencia 89 %, 14 días y la fuerza
por ejercicio (e1RM), con sus **fotos** y sus medidas. Y debajo, **el informe ya
redactado en BORRADOR**: análisis, cambios propuestos, respuesta a su duda y
objetivos. Enséñalo entero: **"Editar texto"**, **descargar el Word** y
**"Enviar al cliente"** — solo al enviarlo lo ve Carlos en su portal. Si el
cliente sigue registrando, el botón **"Poner al día (N días nuevos)"** lo
regenera con todo lo nuevo, y lo que ya se envió NO se toca: sale un borrador
aparte. Mensaje: *el informe se escribe solo con sus datos; vosotros lo
revisáis y decidís cuándo enviarlo*. (Con clave de IA se redacta en vivo.)

**6b) La petición de Marta (1')**
Desde "Hoy", pulsa **"Ver petición"** de Marta: su duda aparece en Seguimiento,
se le responde por WhatsApp y se marca resuelta. Mensaje: *las dudas del
cliente no viven en tu cabeza ni en un chat perdido: entran en la cola*.

**7) Cierre (1')**
Recorre el menú: la web es SOLO el ciclo de asesoría — Hoy, Clientes,
Rutinas y Tienda, sin distracciones (nada de módulos que no vais a usar; todo lo demás
está apagado de fábrica para vosotros). Mensaje: *herramienta de trabajo, no
un ERP*. Y lo
que falta para arrancar de verdad: su Stripe, su dominio y su email
(`PENDIENTE.md`) — todo configuración, cero desarrollo.

---

## 3. Preguntas que van a hacer (y respuesta corta)

- **"¿Qué recibe cada cliente?"** — El de **dieta**, su dossier de nutrición y
  un portal con su diario, su evolución y la tienda. El de **entrenamiento**,
  su dossier de entreno y el portal con el registro de series. El del **pack**,
  las dos cosas. Todo por email, como el resto de envíos.
- **"¿Y si el cliente no registra nada?"** — Salta el aviso en "Hoy" y le
  entra un recordatorio por email. El informe solo se genera cuando hay datos
  suficientes (5 días): el sistema no inventa análisis.
- **"¿La IA decide las calorías?"** — No. BMR/TDEE/kcal/macros los calcula el
  sistema con fórmulas fijas y validador; la IA solo redacta comidas y
  entrenos DENTRO de esos números, y todo pasa por vuestra revisión.
- **"¿Y si el cliente es alérgico?"** — Alergias y aversiones se filtran de
  forma determinista ANTES de generar, y un validador veta cualquier plan que
  las incumpla.
- **"¿Cuánto tardo yo por cliente?"** — Alta 2', revisar anamnesis leída 3',
  revisar plan 5', informe ~5'. El resto lo empuja el sistema
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
- **Sin clave de IA**: no toques "Generar plan"/"Leer con IA"/"Generar
  informe"/"Poner al día" en vivo; todo lo demás funciona (el plan de Marta y el informe de
  Carlos ya están generados y se pueden editar, descargar y enviar).
- **No enseñes** `/oferta` (redirige a planes: correcto, esta marca no la usa).
- Los clientes de demo son `@demo.local`: bórralos antes de entregar la
  instancia real (re-ejecutar el script y luego eliminarlos desde el panel, o
  `wipe_demo_clients`).
