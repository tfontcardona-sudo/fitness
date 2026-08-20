# Política y mecanismos de seguridad — Sistema DQR

Este documento resume CÓMO está blindado el sistema contra pirateo, robo de
datos y copia, y QUÉ pasos manuales quedan en manos del dueño (ajustes que no se
pueden hacer desde el código: GitHub, servidor, `.env`).

## Reportar una vulnerabilidad
Si detectas un problema de seguridad, **no abras un issue público**. Escribe en
privado a **tfontcardona@gmail.com** con los detalles y pasos para reproducirlo.

---

## 1. Protecciones YA implementadas en el código

- **Cabeceras de seguridad HTTP** (Caddy, `frontend/Caddyfile`): `HSTS` (fuerza
  HTTPS), `X-Frame-Options: DENY` + `frame-ancestors 'none'` (la web NO se puede
  meter en un iframe ajeno → no se puede clonar ni suplantar por enmarcado),
  `X-Content-Type-Options: nosniff`, `Referrer-Policy` (no filtra la URL a
  terceros), `Permissions-Policy` (desactiva cámara/micro/ubicación) y una
  `Content-Security-Policy` que solo permite cargar recursos del propio dominio
  (más las fuentes de Google y los reproductores de vídeo de los ejercicios).
- **Cabeceras también a nivel de app** (`backend/app/main.py`,
  `SecurityHeadersMiddleware`): `nosniff` en todas las respuestas de la API y
  `Cache-Control: no-store` + `Referrer-Policy: no-referrer` en el portal del
  cliente (que sirve datos de salud) — defensa en profundidad por si algún día
  se accediera a la API sin pasar por Caddy.
- **Guardián de secretos al arrancar** (`config.py` + `main.py`): en producción
  la app **rehúsa arrancar** si `JWT_SECRET` o `PORTAL_TOKEN_SECRET` son los
  valores de ejemplo del repo (públicos → cualquiera forjaría tokens). Si son
  propios pero cortos (<32), **avisa fuerte en el log pero no bloquea** (no tira
  abajo una producción en marcha por un aviso de higiene).
- **Documentación de la API oculta en producción**: `/api/docs` y
  `/api/openapi.json` solo existen en desarrollo (no se regala el mapa de la API).
- **CORS restringido**: en producción el único origen permitido es el dominio
  público (los `localhost` solo en desarrollo); métodos y cabeceras enumerados.
- **Errores 500 sin fugas**: el detalle interno del error solo se muestra a un
  coach autenticado; a un desconocido (incluido el login) se le da un mensaje
  genérico. La traza completa va al log del servidor.
- **Login sin oráculo de tiempo**: si el usuario no existe, se gasta el mismo
  tiempo (hash señuelo) que con una contraseña incorrecta → no se puede deducir
  qué usuarios existen. Login limitado a 5 intentos/minuto por IP.
- **Tokens del portal firmados y revocables**: no se pueden fabricar ni
  enumerar; regenerar el enlace desde la ficha revoca el anterior al instante.
- **Puertos del overlay de desarrollo** atados a `127.0.0.1` (nunca se exponen
  a Internet aunque se levante por error en un servidor).
- **Despliegue compatible con repo privado**: el auto-deploy (`deploy.yml`)
  autentica el `git pull` con un token (`GH_PAT`) si está definido, así que el
  repositorio puede pasar a privado sin romper el despliegue.

## 2. Pasos MANUALES del dueño (imprescindibles)

Estos ajustes viven fuera del código. En orden de prioridad:

1. **Hacer el repositorio PRIVADO** (lo más importante contra la copia): GitHub →
   repo `fitness` → **Settings → General → Danger Zone → Change visibility →
   Make private**. Antes, crear un token de solo lectura y guardarlo como secreto
   para que el deploy siga funcionando:
   - GitHub → **Settings (tu perfil) → Developer settings → Personal access
     tokens → Fine-grained tokens → Generate**. Acceso: solo el repo `fitness`;
     permiso **Contents: Read-only**.
   - En el repo: **Settings → Secrets and variables → Actions → New repository
     secret**, nombre **`GH_PAT`**, valor = el token.
2. **Secretos de firma largos** en el `.env` del servidor: `JWT_SECRET` y
   `PORTAL_TOKEN_SECRET` de ≥32 caracteres aleatorios y distintos
   (`python -c "import secrets; print(secrets.token_urlsafe(48))"`).
3. **Contraseña de la base de datos**: fijar `POSTGRES_PASSWORD` y la contraseña
   dentro de `DATABASE_URL` (deben coincidir) a una cadena larga
   (`openssl rand -base64 32`). Reiniciar los contenedores.
4. **Servidor (SSH)**: cambiar el acceso de contraseña de root a **clave SSH**,
   crear un usuario de despliegue no-root, y en `/etc/ssh/sshd_config` poner
   `PermitRootLogin no` y `PasswordAuthentication no`. Cortafuegos permitiendo
   solo 22/80/443 entrantes (`ufw allow 22,80,443/tcp`).

## 3. Revocación de emergencia (si crees que algo se ha filtrado)

- **Sesión de coach comprometida**: cambia `JWT_SECRET` en el `.env` y reinicia
  → todas las sesiones de coach mueren al instante (hay que volver a entrar).
- **Enlace de un cliente filtrado**: regenera su enlace del portal desde la
  ficha → el anterior deja de funcionar.

## 4. Secretos y datos personales (RGPD)

- El repositorio **no contiene** claves ni credenciales reales (verificado en
  todo el historial de git). Toda la config sensible vive en `.env`, **excluido**
  del repositorio (`.gitignore`).
- Los datos de clientes (`storage/`) **nunca** se versionan ni se publican:
  contienen información de salud protegida.

## 5. Decisiones asumidas (riesgo aceptado / mejoras futuras)

- La sesión del coach y el token del portal se guardan en `localStorage`. Está
  mitigado por una CSP estricta (`script-src 'self'`, sin scripts inline ni
  `eval`). Moverlo a cookies `HttpOnly` es una mejora futura (requiere rehacer la
  autenticación del panel y del portal).
- Los enlaces del portal no caducan por sí solos (se revocan a mano). Ponerles
  caducidad rompería los enlaces y las apps instaladas de los clientes actuales;
  queda como opción a decidir.

## Licencia
Software propietario. Ver [`LICENSE`](LICENSE): todos los derechos reservados.
