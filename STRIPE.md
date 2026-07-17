# Stripe — enlazar los pagos (guía paso a paso)

> Objetivo: que los clientes puedan **pagar su plan** (Start / Full / Pro) y que
> el sistema lo registre solo. El **código ya está hecho e instalado**; lo único
> que falta es la parte de la **cuenta de Stripe** y pegar 6 valores en el
> `.env` del servidor. Tiempo estimado: ~30–45 min (+ 1–2 días si Stripe pide
> verificar la identidad para activar los cobros reales).

---

## 0. Qué hay ya hecho (no hay que programar nada)

Dos formas de cobrar, ya funcionando en el código:

1. **Registro personal (self-serve)** — página pública
   `https://app.dqrassessories.com/planes`: el cliente elige la **duración**
   (mensual / trimestral / semestral) y el plan, paga en Stripe y **el sistema
   crea su ficha solo** (marcada como "Pagado", con su plan y duración), le
   pide el teléfono en la pantalla de pago y le envía por email el acceso a su
   portal para rellenar la anamnesis.
2. **Alta manual** — el coach crea el cliente en la web (eligiendo plan **y
   duración**) y le manda su **enlace de pago** (botón verde "Enlace de pago"
   en la ficha; se copia al portapapeles y desaparece cuando ya ha pagado). El
   enlace cobra el plan × duración de ESA ficha; la duración se puede cambiar
   en la fila "Duración" de la ficha antes de enviarlo. Al pagar, la ficha
   pasa a "Pagado".

Piezas del código (por si hay que tocar algo):

| Pieza | Dónde |
|-------|-------|
| Página de planes + página "¡Pago recibido!" | `frontend/src/pages/PlansPage.tsx` (rutas `/planes` y `/pago-ok`) |
| Crear sesión de pago (self-serve) | `POST /api/public/checkout` (`backend/app/routers/stripe_router.py`) |
| Enlace de pago del alta manual (usa el token del portal) | `GET /api/pay/{token}` (redirige a Stripe) |
| Webhook de cobro (verificado por firma) | `POST /api/stripe/webhook` |
| Lógica (crear cliente, marcar pagado) | `backend/app/services/stripe_service.py` |
| Variables de configuración | `backend/app/config.py` + `.env.example` |

El estado de pago es **solo informativo**: aparece como etiqueta **"Pagado"** /
**"Pago pendiente"** junto al nombre del cliente (en la lista y en su ficha),
pero **no bloquea** el trabajo del coach. (No confundir con la carpeta
"Pendientes" de la lista de clientes, que se refiere a clientes sin
planificación, no al pago.)

Lo ÚNICO que falta para que funcione: rellenar estas 12 variables del `.env`
del servidor (hoy están vacías). Cada plan tiene **3 precios** (uno por
duración): 1M = mensual · 3M = trimestral · 6M = semestral.

```ini
STRIPE_SECRET_KEY=       # paso 3
STRIPE_WEBHOOK_SECRET=   # paso 4
STRIPE_PRICE_START_1M=   # paso 2 (los 9 precios)
STRIPE_PRICE_START_3M=
STRIPE_PRICE_START_6M=
STRIPE_PRICE_FULL_1M=
STRIPE_PRICE_FULL_3M=
STRIPE_PRICE_FULL_6M=
STRIPE_PRICE_PRO_1M=
STRIPE_PRICE_PRO_3M=
STRIPE_PRICE_PRO_6M=
STRIPE_MODE=payment      # paso 2 (payment = pago único · subscription = cuota recurrente)
```

---

## 1. Crear (y activar) la cuenta de Stripe

1. Entra en <https://dashboard.stripe.com/register> y crea la cuenta con el
   email del negocio. País: España. Confirma el email.
2. **Activar la cuenta** (Dashboard → "Activar pagos"): datos del negocio
   (autónomo o empresa, NIF, dirección), identidad del responsable y el **IBAN**
   donde Stripe ingresará el dinero. Sin esto solo funciona el **modo de
   prueba** (test), que no cobra de verdad.
3. Fíjate en el conmutador **"Modo de prueba" / "Test mode"** (arriba en el
   Dashboard). Stripe tiene DOS mundos separados (test y real): productos,
   claves y webhooks van **por duplicado**. Haremos primero TODO en modo de
   prueba (pasos 2–6) y al final lo repetiremos en modo real (paso 7).

> Puedes hacer los pasos 2–6 en modo de prueba **sin esperar** a que Stripe
> termine de verificar la cuenta.

---

## 2. Crear los 3 productos con su precio (en modo de PRUEBA)

Con el conmutador en **modo de prueba**:

1. Dashboard → **Catálogo de productos** (Product catalog) → **+ Añadir producto**.
2. Crea **3 productos**, uno por plan (los nombres los verá el cliente en la
   pantalla de pago):
   - `Plan Start`
   - `Plan Full`
   - `Plan Pro`
3. A cada producto añádele **3 precios** en EUR, uno por duración (en el
   producto: "Añadir otro precio"): **mensual**, **trimestral** y
   **semestral**. Ponles una descripción/apodo para distinguirlos. Y una
   **decisión importante** — los 9 precios deben ser del MISMO tipo:
   - **Pago único** ("One-off"): el cliente paga esa cantidad una vez (tú le
     reenvías el enlace cuando toque renovar). → en el `.env`:
     `STRIPE_MODE=payment`.
   - **Recurrente** ("Recurring"): Stripe cobra solo cada período — para eso
     crea cada precio con su intervalo: mensual = cada 1 mes, trimestral =
     cada 3 meses, semestral = cada 6 meses. → `STRIPE_MODE=subscription`.

   > Nota si eliges suscripción: el sistema marca la ficha como "Pagado" con el
   > **primer** cobro. Las renovaciones las gestiona Stripe (avisos,
   > reintentos, cancelaciones se ven en su Dashboard); la app no cambia el
   > estado con cada renovación.
4. **Métodos de pago — importante**: en Dashboard → **Configuración** →
   **Pagos** → **Métodos de pago**, deja activos solo los **inmediatos**
   (tarjeta, Apple Pay / Google Pay, Link). **No actives SEPA, transferencia
   bancaria ni aplazados**: son pagos "diferidos" que se confirman días
   después, y el sistema solo registra los cobros confirmados en el momento —
   con un método diferido el cliente pagaría pero su ficha nunca se marcaría
   como "Pagado" (habría que ampliar el código para escuchar el evento
   `checkout.session.async_payment_succeeded`).
5. Abre cada producto, pincha en CADA precio y **copia el ID del precio**:
   empieza por `price_...` (¡el del PRECIO, no el `prod_...` del producto!).
   Apunta los nueve:

   ```
   Start mensual    → price________________
   Start trimestral → price________________
   Start semestral  → price________________
   Full  mensual    → price________________
   Full  trimestral → price________________
   Full  semestral  → price________________
   Pro   mensual    → price________________
   Pro   trimestral → price________________
   Pro   semestral  → price________________
   ```

---

## 3. Copiar la clave secreta de la API (modo de prueba)

1. Dashboard → **Desarrolladores** (Developers) → **Claves de API** (API keys).
2. Copia la **Clave secreta** (Secret key): en modo de prueba empieza por
   `sk_test_...`. (La "clave publicable" `pk_...` NO se usa en este sistema.)

> Trátala como una contraseña: solo va al `.env` del servidor, nunca al chat,
> a un email o al repositorio.

---

## 4. Crear el webhook (el "aviso de cobro" hacia el servidor)

El webhook es cómo Stripe le dice a la app "este pago se ha completado". Sin
él, el cliente paga pero la ficha nunca se marca como pagada.

1. Dashboard (aún en modo de prueba) → **Desarrolladores** → **Webhooks** →
   **+ Añadir endpoint** (Add endpoint / Add destination).
2. **URL del endpoint**:

   ```
   https://app.dqrassessories.com/api/stripe/webhook
   ```
3. **Eventos a escuchar**: selecciona solo
   **`checkout.session.completed`**. (El backend ignora cualquier otro evento,
   así que no hace falta más.)
4. Al crearlo, abre el endpoint y copia el **Secreto de firma** (Signing
   secret): empieza por `whsec_...`. Sirve para que el servidor compruebe que
   el aviso viene DE VERDAD de Stripe.

---

## 5. Pegar los valores en el `.env` del servidor y reiniciar

```bash
ssh root@46.225.57.25
cd /root/fitness
nano .env
```

Rellena las 12 líneas de la sección `# --- Pagos (Stripe) ---` (1M = mensual ·
3M = trimestral · 6M = semestral):

```ini
STRIPE_SECRET_KEY=sk_test_...      # paso 3
STRIPE_WEBHOOK_SECRET=whsec_...    # paso 4
STRIPE_PRICE_START_1M=price_...    # los 9 precios del paso 2
STRIPE_PRICE_START_3M=price_...
STRIPE_PRICE_START_6M=price_...
STRIPE_PRICE_FULL_1M=price_...
STRIPE_PRICE_FULL_3M=price_...
STRIPE_PRICE_FULL_6M=price_...
STRIPE_PRICE_PRO_1M=price_...
STRIPE_PRICE_PRO_3M=price_...
STRIPE_PRICE_PRO_6M=price_...
STRIPE_MODE=payment                # o subscription, según el paso 2
```

Guarda (Ctrl+O, Enter, Ctrl+X) y reinicia para que la API lea el `.env` nuevo:

```bash
docker compose up -d --force-recreate api
```

Comprobación: al arrancar, la API avisa en los logs si falta algo:

```bash
docker compose logs api --tail 50 | grep -i stripe
# Si sale "STRIPE INCOMPLETO: ... Falta: X" → revisa esa variable.
# Con la clave puesta y sin ningún aviso → configuración completa.
```

> Ojo: ese aviso solo se emite si `STRIPE_SECRET_KEY` está rellenada. Si la
> clave está vacía (o el nombre de la variable mal escrito) no sale NINGUNA
> línea de Stripe en los logs; lo notarás al probar, como
> "Stripe no está configurado" al elegir un plan.

> **Importante para el registro personal**: el acceso al portal se envía por
> **email**. Si en el `.env` tienes `EMAILS_ENABLED=false` o el SMTP sin
> configurar, el cliente que se registre solo **pagará y se creará su ficha**,
> pero no recibirá el correo: te aparecerá en Clientes y tendrás que enviarle
> el acceso a mano (su teléfono queda guardado, Stripe lo pide al pagar). Para
> el flujo 100 % automático, configura el SMTP (sección Email del `.env`).

---

## 6. Probar en modo de prueba (sin dinero real)

Tarjeta de prueba de Stripe: **4242 4242 4242 4242**, caducidad cualquiera
futura (p. ej. 12/34), CVC cualquiera (p. ej. 123), cualquier nombre y CP.

**Flujo A — registro personal:**

1. Abre `https://app.dqrassessories.com/planes` (mejor en ventana de incógnito).
2. Elige una duración (mensual/trimestral/semestral) y un plan → te lleva a la
   pantalla de pago de Stripe (comprueba que el precio es el de esa
   combinación) → paga con la tarjeta de prueba (pon un email tuyo real para
   ver el correo de acceso).
3. Debe llevarte a la página **"¡Pago recibido!"** (`/pago-ok`).
4. Entra como coach → **Clientes**: debe existir el cliente nuevo con estado de
   pago **"Pagado"** y su plan correcto. Si el email está activo, en tu buzón
   estará el correo con el acceso al portal.

**Flujo B — alta manual:**

1. Crea un cliente de prueba en la web (eligiendo su plan Start/Full/Pro y su
   duración; la duración se puede cambiar luego en la fila "Duración" de la
   ficha).
2. En su ficha, pulsa el botón verde **"Enlace de pago"** (se copia al
   portapapeles) y ábrelo en otra pestaña → paga con la tarjeta de prueba.
3. Vuelve a su ficha: el estado debe pasar a **"Pagado"** y el botón verde
   desaparece.

**Si algo no cuadra**, mira los dos lados:

- Stripe → Desarrolladores → Webhooks → tu endpoint → **Intentos/Entregas**:
  cada pago debe mostrar una entrega con respuesta **200**. Si sale 400, el
  cuerpo de la respuesta dice qué falta (Stripe **reintenta solo** durante
  horas, así que al corregir el `.env` los pagos "perdidos" acaban entrando).
  Ojo: mira también el **cuerpo** de las entregas 200 — si contiene
  `{"error": ...}` (p. ej. `client_not_found` porque el cliente se borró
  después de enviarle el enlace), el aviso llegó pero no se aplicó, y esas
  Stripe NO las reintenta.
- Servidor: `docker compose logs api --tail 100 | grep -i stripe`.

---

## 7. Pasar a REAL (cobrar de verdad)

Cuando el modo de prueba funcione entero y Stripe haya **activado** la cuenta
(paso 1.2):

1. Quita el conmutador de **modo de prueba** en el Dashboard.
2. **Repite en modo real** los pasos 2, 3 y 4 (los datos de test NO se copian
   solos; en muchos productos Stripe ofrece el botón "copiar al modo activo"):
   - los 3 productos con sus 3 precios cada uno → 9 `price_...` nuevos,
   - la clave secreta real → `sk_live_...`,
   - el webhook con la MISMA URL → `whsec_...` nuevo.
3. Sustituye los 11 valores en el `.env` del servidor (los 9 `price_...`, la
   `sk_live_...` y el `whsec_...`; `STRIPE_MODE` no cambia) y reinicia:

   ```bash
   docker compose up -d --force-recreate api
   ```
4. Prueba con la tarjeta 4242… → ahora debe **rechazarla** (es solo de test):
   señal de que estás en modo real. Si quieres, haz un pago real pequeño y
   **reembólsalo** desde Stripe → Pagos → ⋯ → Reembolsar.

> No mezcles mundos: clave `sk_live_` + webhook de test (o al revés) = error de
> "firma inválida" en todos los avisos.

---

## 8. El día a día (ya enlazado)

- **Dónde se ve**: etiqueta "Pagado" / "Pago pendiente" junto al nombre del
  cliente, en la lista de Clientes y en su ficha. Recuerda: informativo, no
  bloquea nada.
- **No regenerar el enlace del portal a la ligera**: el enlace de pago usa el
  mismo token que el portal del cliente. Si pulsas "Regenerar enlace del
  portal" en la ficha, el enlace de pago ya enviado por WhatsApp/email **deja
  de funcionar** (da "No encontrado"): copia el botón verde de nuevo y
  reenvíalo.
- **Reembolsos, recibos, facturas**: desde el Dashboard de Stripe (Pagos). Los
  recibos al cliente los envía Stripe si activas "Enviar recibos" en
  Configuración → Emails de clientes.
- **El dinero**: Stripe lo ingresa en el IBAN en tandas ("payouts"); la primera
  suele tardar ~7 días, luego es periódica (configurable en Configuración →
  Payouts).
- **Cambiar un precio**: en Stripe los precios son inmutables → crea un precio
  nuevo en el producto, copia su `price_...` nuevo al `.env` y reinicia la API.
  Los pagos ya hechos no se ven afectados.

## 9. Problemas típicos

| Síntoma | Causa / arreglo |
|---------|-----------------|
| Al pulsar un plan: "Stripe no está configurado" | Falta `STRIPE_SECRET_KEY` en el `.env` (o no se reinició la API). |
| "Falta el precio de Stripe del plan X" | La variable `STRIPE_PRICE_{PLAN}_{1M/3M/6M}` de esa combinación está vacía o con el `prod_...` en vez del `price_...`. |
| El cliente paga pero nunca sale "Pagado" | Webhook: URL mal escrita, evento `checkout.session.completed` sin marcar, o `STRIPE_WEBHOOK_SECRET` vacío/equivocado. Mira las entregas del webhook en Stripe. |
| Webhook responde "Firma del webhook inválida" | `whsec_...` de otro endpoint u otro modo (test/real cruzados). Copia el secreto del endpoint correcto. |
| Error de Stripe al crear la sesión con `STRIPE_MODE=subscription` | Los precios se crearon como pago único (o al revés). El tipo del precio y `STRIPE_MODE` deben coincidir. |
| El cliente self-serve no recibe el email de acceso | `EMAILS_ENABLED=false` o SMTP sin configurar. El cliente y su pago SÍ quedan registrados; envíale el acceso desde su ficha. |
| El enlace de pago enviado da "No encontrado" (404) | Se regeneró el enlace del portal después de enviarlo (el pago usa el mismo token). Copia el botón verde otra vez y reenvíalo. |
| El cliente pagó por SEPA/transferencia y no sale "Pagado" | El sistema solo registra métodos de cobro inmediato. Desactiva los métodos diferidos en Stripe (paso 2.4); el pago real está en el Dashboard de Stripe aunque la ficha siga "Pago pendiente". |
| Probar en el PC (desarrollo local) | Stripe no puede llamar a `localhost`. Usa la CLI de Stripe: `stripe listen --forward-to localhost:8000/api/stripe/webhook` y pon en el `.env` local el `whsec_...` temporal que imprime. |
