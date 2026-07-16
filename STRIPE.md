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
   `https://app.dqrassessories.com/planes`: el cliente elige plan, paga en
   Stripe y **el sistema crea su ficha solo** (marcada como "Pagado"), le pide
   el teléfono en la pantalla de pago y le envía por email el acceso a su
   portal para rellenar la anamnesis.
2. **Alta manual** — el coach crea el cliente en la web y le manda su **enlace
   de pago** (botón verde "Enlace de pago" en la ficha del cliente; se copia al
   portapapeles y desaparece cuando ya ha pagado). Al pagar, la ficha pasa a
   "Pagado".

Piezas del código (por si hay que tocar algo):

| Pieza | Dónde |
|-------|-------|
| Página de planes + página "¡Pago recibido!" | `frontend/src/pages/PlansPage.tsx` (rutas `/planes` y `/pago-ok`) |
| Crear sesión de pago (self-serve) | `POST /api/public/checkout` (`backend/app/routers/stripe_router.py`) |
| Enlace de pago estable del alta manual | `GET /api/pay/{token}` (redirige a Stripe) |
| Webhook de cobro (verificado por firma) | `POST /api/stripe/webhook` |
| Lógica (crear cliente, marcar pagado) | `backend/app/services/stripe_service.py` |
| Variables de configuración | `backend/app/config.py` + `.env.example` |

El estado de pago es **solo informativo**: aparece como "Pagado / Pendiente" en
la lista de clientes y en la ficha, pero **no bloquea** el trabajo del coach.

Lo ÚNICO que falta para que funcione: rellenar estas 6 variables del `.env`
del servidor (hoy están vacías):

```ini
STRIPE_SECRET_KEY=      # paso 3
STRIPE_WEBHOOK_SECRET=  # paso 4
STRIPE_PRICE_START=     # paso 2
STRIPE_PRICE_FULL=      # paso 2
STRIPE_PRICE_PRO=       # paso 2
STRIPE_MODE=payment     # paso 2 (payment = pago único · subscription = cuota mensual)
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
3. En cada producto, añade su **precio** en EUR y elige el tipo. Aquí hay una
   **decisión importante** — los 3 precios deben ser del MISMO tipo:
   - **Pago único** ("One-off"): el cliente paga una vez. → en el `.env`:
     `STRIPE_MODE=payment`.
   - **Recurrente mensual** ("Recurring / Monthly"): Stripe le cobra cada mes
     solo. → en el `.env`: `STRIPE_MODE=subscription`.

   > Nota si eliges suscripción: el sistema marca la ficha como "Pagado" con el
   > **primer** cobro. Los cobros mensuales siguientes los gestiona Stripe
   > (avisos, reintentos, cancelaciones se ven en su Dashboard); la app no
   > cambia el estado con cada renovación.
4. Abre cada producto, pincha en su precio y **copia el ID del precio**: empieza
   por `price_...` (¡el del PRECIO, no el `prod_...` del producto!). Apunta los
   tres:

   ```
   Start → price_________________
   Full  → price_________________
   Pro   → price_________________
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

Rellena las 6 líneas de la sección `# --- Pagos (Stripe) ---`:

```ini
STRIPE_SECRET_KEY=sk_test_...      # paso 3
STRIPE_WEBHOOK_SECRET=whsec_...    # paso 4
STRIPE_PRICE_START=price_...       # paso 2
STRIPE_PRICE_FULL=price_...        # paso 2
STRIPE_PRICE_PRO=price_...         # paso 2
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
# Si no sale nada de Stripe → configuración completa.
```

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
2. Elige un plan → te lleva a la pantalla de pago de Stripe → paga con la
   tarjeta de prueba (pon un email tuyo real para ver el correo de acceso).
3. Debe llevarte a la página **"¡Pago recibido!"** (`/pago-ok`).
4. Entra como coach → **Clientes**: debe existir el cliente nuevo con estado de
   pago **"Pagado"** y su plan correcto. Si el email está activo, en tu buzón
   estará el correo con el acceso al portal.

**Flujo B — alta manual:**

1. Crea un cliente de prueba en la web (con su plan Start/Full/Pro).
2. En su ficha, pulsa el botón verde **"Enlace de pago"** (se copia al
   portapapeles) y ábrelo en otra pestaña → paga con la tarjeta de prueba.
3. Vuelve a su ficha: el estado debe pasar a **"Pagado"** y el botón verde
   desaparece.

**Si algo no cuadra**, mira los dos lados:

- Stripe → Desarrolladores → Webhooks → tu endpoint → **Intentos/Entregas**:
  cada pago debe mostrar una entrega con respuesta **200**. Si sale 400, el
  cuerpo de la respuesta dice qué falta (Stripe **reintenta solo** durante
  horas, así que al corregir el `.env` los pagos "perdidos" acaban entrando).
- Servidor: `docker compose logs api --tail 100 | grep -i stripe`.

---

## 7. Pasar a REAL (cobrar de verdad)

Cuando el modo de prueba funcione entero y Stripe haya **activado** la cuenta
(paso 1.2):

1. Quita el conmutador de **modo de prueba** en el Dashboard.
2. **Repite en modo real** los pasos 2, 3 y 4 (los datos de test NO se copian
   solos; en muchos productos Stripe ofrece el botón "copiar al modo activo"):
   - los 3 productos con sus precios → 3 `price_...` nuevos,
   - la clave secreta real → `sk_live_...`,
   - el webhook con la MISMA URL → `whsec_...` nuevo.
3. Sustituye los 5 valores en el `.env` del servidor (los `price_...`, la
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

- **Dónde se ve**: columna/etiqueta "Pagado · Pendiente" en la lista de
  Clientes y en la ficha. Recuerda: informativo, no bloquea nada.
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
| "Falta el precio de Stripe del plan X" | La variable `STRIPE_PRICE_X` está vacía o con el `prod_...` en vez del `price_...`. |
| El cliente paga pero nunca sale "Pagado" | Webhook: URL mal escrita, evento `checkout.session.completed` sin marcar, o `STRIPE_WEBHOOK_SECRET` vacío/equivocado. Mira las entregas del webhook en Stripe. |
| Webhook responde "Firma del webhook inválida" | `whsec_...` de otro endpoint u otro modo (test/real cruzados). Copia el secreto del endpoint correcto. |
| Error de Stripe al crear la sesión con `STRIPE_MODE=subscription` | Los precios se crearon como pago único (o al revés). El tipo del precio y `STRIPE_MODE` deben coincidir. |
| El cliente self-serve no recibe el email de acceso | `EMAILS_ENABLED=false` o SMTP sin configurar. El cliente y su pago SÍ quedan registrados; envíale el acceso desde su ficha. |
| Probar en el PC (desarrollo local) | Stripe no puede llamar a `localhost`. Usa la CLI de Stripe: `stripe listen --forward-to localhost:8000/api/stripe/webhook` y pon en el `.env` local el `whsec_...` temporal que imprime. |
