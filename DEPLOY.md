# Desplegar en internet — link público permanente

> Objetivo: que `https://app.tudominio.com` funcione **desde cualquier sitio,
> a cualquier hora y para cualquiera** (tú, tu socio y los clientes), sin
> depender de tu PC. Tiempo estimado: ~30 min. Coste: ~5–7 €/mes (VPS) +
> ~10 €/año (dominio).

El proyecto ya está preparado: el `docker-compose.yml` de producción levanta
Postgres + API + **Caddy**, que sirve el frontend compilado, proxyea `/api` y
**obtiene el certificado HTTPS solo** en cuanto le das un dominio.

---

## ⚡ Vía rápida — instalador automático

Con el VPS creado y el DNS apuntando (pasos 0–2 de abajo), conéctate por SSH
(`ssh root@IP-DEL-VPS`) y pega **una sola línea** (sustituye `TU_TOKEN` por un
token de GitHub de solo-lectura del repo, ver paso 3):

```bash
apt-get update -qq; apt-get install -y -qq git; [ -d /root/fitness ] || git clone https://TU_TOKEN@github.com/tfontcardona-sudo/fitness.git /root/fitness; bash /root/fitness/deploy/install-vps.sh
```

El instalador (`deploy/install-vps.sh`) pregunta el dominio, los dos usuarios
del coach y la clave de Anthropic, y hace **todo lo demás solo**: Docker,
firewall, `.env` con secretos aleatorios, arranque, claves VAPID del push y un
resumen final con los links. Es seguro re-ejecutarlo. Los pasos manuales de
abajo quedan como referencia/detalle.

---

## 0. Qué necesitas comprar (una vez)

1. **Un VPS** (servidor Linux siempre encendido). Vale el más barato:
   - Hetzner Cloud CX22 (~4,5 €/mes) · DigitalOcean Basic (~6 $/mes) · OVH, Contabo…
   - Sistema: **Ubuntu 24.04 LTS**. Apunta la **IP pública** que te den.
2. **Un dominio** (Namecheap, Cloudflare Registrar, OVH… ~10 €/año), p. ej.
   `dqfitness.com`. Usaremos el subdominio `app.dqfitness.com`.

## 1. Apuntar el dominio al servidor

En el panel DNS del dominio, crea un registro:

| Tipo | Nombre | Valor |
|------|--------|-------|
| A    | `app`  | IP del VPS |

(Se propaga en minutos. Puedes comprobarlo con `ping app.tudominio.com`.)

## 2. Preparar el servidor (SSH)

```bash
ssh root@IP-DEL-VPS

# Docker (script oficial)
curl -fsSL https://get.docker.com | sh

# Firewall: solo SSH + web
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable
```

## 3. Clonar el repo

El repo es privado: crea un token en GitHub (Settings → Developer settings →
**Fine-grained token**, solo lectura de este repo) y:

```bash
git clone https://TU_TOKEN@github.com/tfontcardona-sudo/fitness.git
cd fitness
```

## 4. Configurar el `.env` de producción

```bash
cp .env.example .env
nano .env
```

Rellena **como mínimo**:

```ini
# Dominio → activa HTTPS automático y las URLs públicas
DOMAIN=app.tudominio.com

# Secretos NUEVOS y aleatorios (genera cada uno con: openssl rand -hex 32)
JWT_SECRET=...
PORTAL_TOKEN_SECRET=...
POSTGRES_PASSWORD=...
# ¡DATABASE_URL debe llevar LA MISMA contraseña!
DATABASE_URL=postgresql+psycopg://fitness:LA_MISMA_CONTRASEÑA@db:5432/fitness

# Usuarios del coach (tú y tu socio)
ADMIN_1_USER=david
ADMIN_1_PASS=una-buena-contraseña
ADMIN_2_USER=socio
ADMIN_2_PASS=otra-buena-contraseña

# IA (cuando haya crédito)
ANTHROPIC_API_KEY=sk-ant-...

# Email: en producción NO hay Mailpit. O configura un SMTP real
# (p. ej. Brevo/Sendgrid gratis) o desactívalo de momento:
EMAILS_ENABLED=false
```

`BASE_URL` puedes ignorarlo: con `DOMAIN` definido, todos los enlaces
(portal de clientes, emails, push) se generan como `https://DOMAIN`.

## 5. Arrancar

```bash
docker compose up -d --build
```

(Solo el compose de producción — **sin** `-f docker-compose.dev.yml`. Las
migraciones de BD se aplican solas al arrancar.)

Abre `https://app.tudominio.com` → login del coach. Ya es el link que se puede
abrir donde sea, cuando sea y por quien sea (con el certificado HTTPS válido).

## 6. Activar los recordatorios push (una vez)

Con HTTPS ya funcionan en móviles reales (en iOS, instalando la PWA):

```bash
docker compose exec api python -m scripts.generate_vapid_keys
nano .env          # pegar las 3 líneas VAPID_*
docker compose up -d
```

## 7. Los links del día a día

- **Coach (tú y tu socio):** `https://app.tudominio.com` (entráis con
  `ADMIN_1` / `ADMIN_2`).
- **Cada cliente:** su link de portal `https://app.tudominio.com/p/{token}`
  (botón "enlace del portal" en su ficha; sin login, y puede instalarse como
  app en el móvil).

## 8. Mantenimiento

```bash
# Actualizar a la última versión del código
cd ~/fitness && git pull && docker compose up -d --build

# Ver logs si algo falla
docker compose logs api --tail 100
```

### Copias de seguridad (automáticas)

El instalador programa una **copia diaria** (a las 04:00) de la base de datos
**y** de los ficheros subidos (fotos de progreso, PDFs). Se guardan en
`/root/fitness-backups` (fuera del repo) y se conservan las últimas 14, rotando
solas. Si ya tenías el sistema instalado de antes, actívalas una vez con:

```bash
bash ~/fitness/deploy/install-backups.sh   # programa el cron diario
bash ~/fitness/deploy/backup.sh            # y haz una copia ahora mismo
```

Restaurar una copia (DESTRUCTIVO: reemplaza los datos actuales):

```bash
bash ~/fitness/deploy/restore.sh                       # lista las copias
bash ~/fitness/deploy/restore.sh /root/fitness-backups/db-2026-07-08_0400.sql.gz
```

> Recomendado: copia también `/root/fitness-backups` a otro sitio (otro
> servidor, un bucket S3/Backblaze, o `scp` a tu PC) para no depender de un
> único disco. El VPS puede fallar entero.

## Notas

- **La BD del VPS empieza vacía**: los clientes de prueba de tu PC no viajan
  solos. Si quieres llevarte los datos: `pg_dump` en el PC → `psql` en el VPS.
- **No expongas Postgres**: el compose de producción ya no publica el puerto
  5432 (solo el dev lo hace). No lo añadas.
- Si cambias las claves VAPID después de que haya clientes suscritos, sus
  suscripciones push se invalidan. Genéralas una vez y guárdalas.
