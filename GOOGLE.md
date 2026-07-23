# Google Calendar + Meet — Videollamadas Pro

Guía para conectar tu cuenta de Google y agendar videollamadas de revisión con
enlace de **Google Meet** e invitación automática al cliente. Una vez conectado,
agendar es **1 clic** desde la ficha del cliente.

> Igual que Stripe, esto es **opcional**: sin las claves de OAuth, la web sigue
> funcionando con el flujo manual (enlace de reservas por WhatsApp). Al añadir las
> claves, aparece el botón **"Conectar con Google"** en **Recursos / Ajustes**.

---

## Cómo funciona el flujo

1. El cliente **envía su revisión quincenal** → en su **portal** le aparece un
   formulario para **proponer día y hora** de la videollamada.
2. Tú lo ves en la **agenda del Panel** y en la ficha del cliente (pestaña
   **Feedback**): puedes **Aceptar** o **Modificar**.
   - **Aceptar** → se crea el evento en **tu Google Calendar** con **enlace de
     Meet**, se invita al cliente por email y se le manda el enlace.
   - **Modificar** → se abre **WhatsApp** para acordar otra hora; queda
     *pendiente de agendar a mano* y, cuando lo acordáis, escribes el día/hora y
     se crea igual.
3. La videollamada queda en tu **agenda** (día, hora, cliente y un **icono de
   Meet** para unirte) hasta que la marcas como realizada.

### Notificaciones "para que no pase por alto"

- **Invitación de Google Calendar** al cliente con recordatorios nativos
  (email 24 h antes + avisos 60 y 10 min antes).
- **Email de la app** con el enlace de Meet al agendar.
- **Push** en el portal del cliente + botón **"Unirme"**.
- **Recordatorio el día antes y 1 hora antes**, a ti y al cliente.
- Reprogramar/cancelar desde la web **actualiza el evento en Google** y reavisa.

---

## Configuración (una sola vez)

### 1. Crear el proyecto y habilitar la API

1. Entra en [Google Cloud Console](https://console.cloud.google.com/).
2. Crea un proyecto (o usa uno existente).
3. **APIs y servicios → Biblioteca** → busca **Google Calendar API** → **Habilitar**.

### 2. Pantalla de consentimiento de OAuth

1. **APIs y servicios → Pantalla de consentimiento de OAuth**.
2. Tipo de usuario: **Externo** (o **Interno** si usas Google Workspace).
3. Rellena nombre de la app, email de asistencia y de contacto.
4. En **Ámbitos/Scopes** no hace falta añadir nada a mano (los pide la app):
   `openid`, `email` y `.../auth/calendar.events`.
5. Si la app queda en modo **"En pruebas"**, añade tu propio email de coach en
   **Usuarios de prueba** (si no, Google bloquea el acceso).

### 3. Crear las credenciales de OAuth

1. **APIs y servicios → Credenciales → Crear credenciales → ID de cliente de OAuth**.
2. Tipo de aplicación: **Aplicación web**.
3. En **URIs de redirección autorizados** añade EXACTAMENTE tu callback:

   ```
   https://TU-DOMINIO/api/google/oauth/callback
   ```

   - En producción con dominio: `https://app.tudominio.com/api/google/oauth/callback`
   - En local: `http://localhost/api/google/oauth/callback`
   - Debe coincidir carácter por carácter con `{DOMAIN|BASE_URL}` del `.env`.
4. Copia el **Client ID** y el **Client secret**.

### 4. Rellenar el `.env` y reiniciar

```env
GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxxxxxxx
GOOGLE_CALENDAR_ID=primary
# La cuenta de Google de la asesoría: Google abrirá "Conectar" ya con ella.
GOOGLE_LOGIN_HINT=asesoriasdqr@gmail.com
```

Reinicia el backend. En el arranque, si las claves están puestas, la integración
queda activa.

> **`GOOGLE_LOGIN_HINT`** hace que, al pulsar "Conectar", Google abra
> directamente con la cuenta de la asesoría (no con la que tengas por defecto en
> el navegador). Ponla igual que la cuenta con la que creaste las credenciales.
> Además, esa cuenta debe estar en **Usuarios de prueba** de la pantalla de
> consentimiento (Paso 2.5) si la app está "En pruebas".

### 5. Conectar tu cuenta desde la web

1. Entra en la web del coach → **Recursos → Página de enlaces**.
2. Pulsa **"Conectar con Google Calendar / Meet"**.
3. Acepta los permisos en Google. Vuelves a la web con "Conectado como tu-email".

Listo. A partir de aquí, cuando un cliente Pro proponga su videollamada desde el
portal, te saldrá en la **agenda del Panel** y en su ficha (pestaña **Feedback**)
con los botones **Aceptar** / **Modificar**.

---

## Notas y resolución de problemas

- **`redirect_uri_mismatch`**: la URI de redirección del `.env`/dominio no coincide
  con la de Google Cloud. Revisa que sean idénticas (incluido `http` vs `https` y
  sin barra final de más).
- **No aparece el botón "Conectar"**: faltan `GOOGLE_CLIENT_ID`/`SECRET` en el
  `.env`, o no reiniciaste el backend.
- **"Se perdió la conexión con Google"**: el refresh token se revocó (cambiaste la
  contraseña, o revocaste el acceso). Vuelve a **Conectar con Google**.
- **Meet en cuentas @gmail.com**: funciona (Google Meet está disponible para
  cuentas personales). Con Google Workspace también.
- **Zona horaria**: los eventos se crean en `TZ` del `.env` (Europe/Madrid por
  defecto).
- La app pide el permiso **mínimo** (`calendar.events`): solo puede crear/editar
  los eventos que ella misma genera, no leer tu agenda entera.
