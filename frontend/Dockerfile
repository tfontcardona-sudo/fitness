# --- Etapa de build (también usada como base en dev con target: build) ---
FROM node:20-alpine AS build
WORKDIR /app
# El LOCKFILE manda: sin él, npm install re-resuelve los rangos ^ y un build
# tras limpiar la caché de Docker metía versiones nuevas sin probar (y cambiaba
# TODOS los hashes de los chunks de golpe) — auditoría 26-08.
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# --- Etapa de producción: Caddy sirve el estático y proxyea /api ---
FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
