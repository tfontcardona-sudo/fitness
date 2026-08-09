# PENDIENTE.md — puntos a hablar con los clientes (Professional Girona)

El producto está completo y verificado en código (suite en verde, dossiers
renderizados, instalación desde cero validada). Estos puntos NO son de código:
dependen de decisiones o credenciales del cliente, y quedan aquí apuntados
hasta que se hablen con ellos.

| # | Punto | Qué hace falta de ellos | Estado |
|---|---|---|---|
| 1 | **Stripe** (cobro online de Génesis.99) | Crear su cuenta de Stripe y pasar la clave (`STRIPE_SECRET_KEY` + webhook). El sistema crea los precios solo (99 €/mes, `pgirona_*`). | Pendiente de hablar |
| 2 | **Dominio y despliegue** | Decidir dominio (p. ej. `app.professionalgirona.com`), apuntar DNS y desplegar en su VPS (`deploy/install-vps.sh`). | Pendiente de hablar |
| 3 | **Logo definitivo** | El actual es una recreación fiel (serif + laurel). Si quieren el PNG original, se sube desde la página Marca en 1 minuto. | Se queda el actual salvo que digan lo contrario |
| 4 | **Email remitente** | Contraseña de aplicación de Gmail de `professionalsaludifitness@gmail.com` (o la cuenta que decidan) → `SMTP_USER/PASS`. | Se enlazará cuando digan |
| 5 | **Claves de la instancia** | Al desplegar: `JWT_SECRET`, `PORTAL_TOKEN_SECRET`, claves VAPID nuevas (`scripts/generate_vapid_keys.py`) y credenciales de los 2 admins. | Pendiente (se generan en el deploy) |
| 6 | **Google Calendar / Meet** (videollamada de Génesis) | OAuth en su Google Cloud + conectar la cuenta desde Recursos. Opcional: sin ello funciona el flujo manual. | Pendiente de hablar |
| 7 | **Clave de Anthropic** | Su clave de API para la IA (planes + lectura de anamnesis) con su propio saldo. | Pendiente de hablar |
| 8 | **Fotos reales del centro** | Para los fondos de `/planes` y la página de enlaces (se suben desde Recursos; hoy hay degradado de marca). | Pendiente de hablar |
| 9 | **Tarifas 3m/6m de Génesis** | Hoy: 99 €/mes exactos en todas las duraciones (su web no anuncia descuento). ¿Quieren descuento por compromiso? | Pendiente de decisión |

> Cambios de código asociados a estos puntos: ninguno pendiente. Cuando el
> cliente entregue cada pieza, todo se conecta por configuración (`.env`,
> página Marca, Recursos) sin desplegar código nuevo — salvo la 9, que es
> editar `CANONICAL_AMOUNTS` + `packages.ts` y ejecutar el script de precios.
