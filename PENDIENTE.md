# PENDIENTE.md — puntos a hablar con los clientes (Professional Girona)

El producto está completo y verificado en código (suite en verde, dossiers
renderizados, instalación desde cero validada). Estos puntos NO son de código:
dependen de decisiones o credenciales del cliente, y quedan aquí apuntados
hasta que se hablen con ellos.

| # | Punto | Qué hace falta de ellos | Estado |
|---|---|---|---|
| 1 | **Stripe** (cobro online de los tres servicios) | Crear su cuenta de Stripe y pasar la clave (`STRIPE_SECRET_KEY` + webhook, escuchando solo `checkout.session.completed`). El sistema crea los precios solo: Dieta 70 €, Entrenamiento 70 € y Pack completo 130 €, todos de **pago único** (`pgirona_*`). | Pendiente de hablar |
| 2 | **Dominio y despliegue** | Decidir dominio (p. ej. `app.professionalgirona.com`), apuntar DNS y desplegar en su VPS (`deploy/install-vps.sh`). | Pendiente de hablar |
| 3 | **Logo definitivo** | El actual es una recreación fiel (serif + laurel). Si quieren el PNG original, se sustituye el archivo empaquetado (`frontend/public/brand-logo.png` + assets del dossier) en 1 minuto. | Se queda el actual salvo que digan lo contrario |
| 4 | **Email remitente** | Contraseña de aplicación de Gmail de `professionalsaludifitness@gmail.com` (o la cuenta que decidan) → `SMTP_USER/PASS`. Es la vía de TODOS los envíos: anamnesis, planificaciones e informes. | Se enlazará cuando digan |
| 5 | **Claves de la instancia** | Al desplegar: `JWT_SECRET`, `PORTAL_TOKEN_SECRET`, claves VAPID nuevas (`scripts/generate_vapid_keys.py`) y credenciales de los 2 admins. | Pendiente (se generan en el deploy) |
| 6 | **Clave de Anthropic** | Su clave de API para la IA (planificaciones, lectura de anamnesis e informes) con su propio saldo. Sin ella el sistema funciona igual salvo esos tres botones. | Pendiente de hablar |
| 7 | **Fotos reales del centro** | Para los fondos de `/planes` y la página de enlaces (hoy hay degradado de marca). Se suben desde **Enlaces**. | Pendiente de hablar |

> Cambios de código asociados a estos puntos: ninguno pendiente. Cuando el
> cliente entregue cada pieza, todo se conecta por configuración (`.env`,
> assets, seed de marca) sin desplegar código nuevo.

## Fuera del producto (decisión de agosto de 2026)

Se **borraron** del código, no están apagadas por configuración: tienda de
productos, vídeos de ejercicios, videollamadas con Google Meet, ronda diaria de
WhatsApp y WhatsApp como canal de entrega, ciclo quincenal con cierre del
cliente, y la oferta de captación de 1 €. Si algún día se quisieran, hay que
recuperarlas del historial de git. Detalle en `CLAUDE.md` §9 punto 9.
