# Hallazgos pendientes de verificar (agosto 2026)

> **REPARTO ENTRE SESIONES PARALELAS.** Añade tu reclamo aquí antes de tocar
> nada: tres sesiones hicimos la tanda 3 a la vez y hubo que reconciliar a mano
> un aviso duplicado, un N+1 reintroducido y dos ficheros de test homónimos.
>
> - **Tanda 1** (graves + Stripe) — sesión "DQR asesories"
>   (`claude/stripe-integration-steps-somce4`). **HECHA** en su mitad no-Stripe;
>   los seis de pagos los absorbió la tanda 2.
> - **Tanda 2** (pagos, libro de caja, altas) — sesión "rutina y dieta quice"
>   (`claude/continue-previous-n6layq`). **HECHA**.
> - **Tanda 3** (el ciclo: automatismos, avisos, recordatorios) — la hicieron
>   TRES sesiones a la vez. La de `portal-recursos` ya está en `main` (PR #113);
>   la de `claude/stripe-integration-steps-somce4` se fusionó con ella y se
>   reconciliaron las discrepancias. **HECHA**.
> - **Tanda 4** (IA y planes) — sesión "rutina y dieta quice"
>   (`claude/continue-previous-n6layq`). **HECHA**. Suya es, entre otros,
>   `charts.py:146`, `word_import.py:722`, `adapt_plan.py:548`,
>   `pdf_convert.py:55`, `plans.py:576` y `plan_doc.py:637`.
> - **Tanda 5 (RGPD, borrado y portabilidad) — sesión "DQR asesories"
>   (`claude/stripe-integration-steps-somce4`). HECHA.** Alcance acotado a lo
>   (`claude/stripe-integration-steps-somce4`). HECHA.**
> - **Tanda 6 (portal del cliente y anamnesis) — sesión "DQR asesories"
>   (`claude/stripe-integration-steps-somce4`), EN CURSO.** Alcance:
>   `PortalDiary.tsx` 48/64/213, `AnamnesisPage.tsx` 254/497/501,
>   `PortalApp.tsx:290`, `PortalResources.tsx:46`, `portal_public.py` 268/406 y
>   `clients.py:927` (contradicciones de la anamnesis). `feedback_service.py:116`
>   (fotos iniciales como "front") entra aquí por ser del mismo camino. Alcance acotado a lo
>   que la tanda 4 no lleva: `clients.py` 618/626/702/730/751 (borrado RGPD,
>   "Descargar todo", ZIP de portabilidad), `tests/test_borrado_rgpd.py:74` y
>   `frontend/Caddyfile:43` (el tope de subida contra los vídeos de ejercicio).
>   La mitad "documentos" de esta tanda es de la 4: no la toco.
> - **Tanda 6 (portal del cliente y anamnesis) — sesión "DQR asesories"
>   (`claude/stripe-integration-steps-somce4`). HECHA.** Alcance:
>   `PortalDiary.tsx` 48/64/213, `AnamnesisPage.tsx` 254/497/501,
>   `PortalApp.tsx:290`, `PortalResources.tsx:46`, `portal_public.py` 268/406 y
>   `clients.py:927` (contradicciones de la anamnesis). `feedback_service.py:116`
>   (fotos iniciales como "front") entra aquí por ser del mismo camino.
> - **Tanda 7 (optimización backend + frontend) — sesión "rutina y dieta quice"
>   (`claude/continue-previous-n6layq`), EN CURSO.** Alcance: `clients.py`
>   1233/1242 (ficha e historial), `plan_library.py:426`, `plans.py` 477/721,
>   `exercises.py:58`, `portal.py:412`, `ClientPlanEditor.tsx:102`,
>   `ClientFeedbackTab.tsx:1129`, `DashboardPage.tsx:145`, `RecursosPage.tsx:1087`
>   y `AppShell.tsx:127`. NO toco nada del portal ni de la anamnesis (tanda 6).
> - **Tanda 8 (créditos de IA, código sin conectar, UX del panel e
>   integraciones) — sesión "DQR asesories"
>   (`claude/stripe-integration-steps-somce4`). HECHA.** Es la ÚLTIMA: barre
>   todo lo que no lleva la tanda 7. Alcance: las seis de "Créditos de IA", las
>   cinco de "Construido y sin conectar", las cinco de UX del panel del coach,
>   las seis de Stripe, las dos de email/push, las cuatro de Google/WhatsApp y
>   los cinco que las tandas 1 y 4 dejaron abiertos a propósito
>   (`generator.py` 1079/1086/1088, `coach_lessons.py:219`,
>   `stripe_service.py:1091`). NO toco nada de optimización (tanda 7).
>
> - **INTEGRACIÓN Y VERIFICACIÓN DEL CONJUNTO — sesión "rutina y dieta quice"
>   (`claude/continue-previous-n6layq`), EN CURSO.** Con las ocho tandas
>   repartidas ya no queda hallazgo libre, así que esta sesión pasa a lo que
>   ninguna estaba haciendo: comprobar que las TRES fuentes juntas no se hayan
>   roto entre ellas. NO toca hallazgos de la 6 ni de la 8. Cubre: arranque de
>   la base DESDE CERO, suite completa sobre el código combinado, `tsc`/build/
>   guardas, navegador real sobre el panel y el portal (§10 de CLAUDE.md), y
>   búsqueda de arreglos DUPLICADOS o contradictorios entre sesiones. Lo que
>   encuentre se arregla aquí o se avisa a quien tenga ese fichero abierto.
>
> ⚠️ **Ojo con `main`**: va POR DETRÁS de esta rama (no tiene la caché del PDF ni
> la rejilla de la gráfica de perímetros). Las tandas 2 y 4 se apilan sobre esta
> rama a propósito: llevadas a `main` por separado, se aplicarían sobre una base
> que no tiene sus prerrequisitos.
>
> - **Tanda 7 (optimización: backend + frontend) — sesión "videollamadas Google
>   Meet" (`claude/google-meet-calendar-integration-1po1c2`), HECHA.**
>   Alcance: TODO el apartado "Pendientes · optimización" salvo lo que ya sea de
>   otra tanda. Backend: `clients.py` 1233/1242 (historial y ficha),
>   `plan_library.py:426`, `plans.py` 477/721, `exercises.py:58`,
>   `services/portal.py:412`. Frontend: `ClientPlanEditor.tsx:102`,
>   `ClientFeedbackTab.tsx:1129`, `DashboardPage.tsx:145`,
>   `RecursosPage.tsx:1087`, `AppShell.tsx:127`. **NO toco** `portal_public.py`,
>   `AnamnesisPage.tsx`, `PortalDiary/PortalApp/PortalResources` ni la zona RGPD
>   de `clients.py` (618-751): son de la tanda 6. En `clients.py` y
>   `RecursosPage.tsx` coincidimos de fichero pero no de región.
>   **HECHA** (todo el apartado de optimización verificado uno a uno y
>   corregido, con `tests/test_optimizacion.py` — 11 regresiones que fallan sin
>   el arreglo). Los tres de "Créditos de IA" y los de "Construido y sin
>   conectar" NO son míos: son la tanda 8.
> **REPARTO EN CURSO (sesiones paralelas).** Tanda 1 (graves + Stripe): sesión
> "DQR asesories" (rama `claude/stripe-integration-steps-somce4`). Tanda 2
> (pagos/libro de caja/altas): sesión "rutina y dieta quice"
> (`claude/continue-previous-n6layq`). **Tanda 3 (el ciclo: automatismos, avisos
> y recordatorios): sesión "Google Meet y Calendario integrados"
> (`claude/google-meet-calendar-integration-1po1c2`)** — alcance: jobs.py
> (63/106/253), job_state.py (38/109), push.py (589/742), alerts.py
> («Escribir a mi coach»), portal.py (racha), sw.js (badge sin count). Si coges
> otra tanda, añade tu reclamo aquí para que nadie se solape.

> **Qué es esto.** El inventario en crudo de dos barridos automáticos: una
> verificación adversarial de los 27 commits de la auditoría anterior, y los dos
> dominios que aquella auditoría nunca llegó a cubrir (coherencia de UX e
> integraciones) más un barrido de optimización y de código a medias.
>
> **ESTADO: SIN VERIFICAR.** De los 146 agentes lanzados terminaron 25; el resto
> murió contra el límite de sesión y con ellos casi toda la fase de verificación
> adversarial. Lo de abajo es, por tanto, salida de los BUSCADORES: pistas con
> fichero y línea, **no hechos comprobados**. De los nueve que comprobé a mano
> los nueve eran reales — pero eso no autoriza a dar por bueno el resto, y hay
> falsos positivos garantizados (un buscador que no ejecuta el código confunde a
> menudo "no lo veo" con "no existe").
>
> **Cómo usarlo.** Abrir el fichero, reproducir el daño y solo entonces
> arreglar, con su regresión. Lo ya comprobado y arreglado NO está aquí.
>
> Lo pendiente de verdad es **volver a lanzar la verificación adversarial** con
> presupuesto de sesión suficiente: dos verificadores independientes por
> hallazgo, con instrucción de REFUTAR.

## Tanda 3 · verificados y arreglados (sesión de Google Meet)

Verificación adversarial (refutador + reproductor por hallazgo) y arreglo con
regresión que **falla sin el arreglo**. Ninguno se dio por bueno sin reproducir.

| Hallazgo | Veredicto | Qué pasaba de verdad |
|---|---|---|
| El tope de avisos de cierre cuenta emails FALLIDOS (`jobs.py:253`) | confirmado | `_enviados_desde`/`_already_sent_today` contaban filas de `email_log` sin mirar su `status`. Con el SMTP caído, los intentos fallidos gastaban el cupo: el cliente se quedaba sin recordatorio el resto de la quincena aunque el correo volviera esa tarde. Ahora solo cuentan `sent` y `disabled` (final deliberado); `failed` se reintenta. |
| Un correo que falla cuenta como enviado (`jobs.py:63`) | confirmado | Misma raíz: el aviso del día 12 no se reintentaba nunca. Mismo arreglo. |
| La vigilancia solo mira el mantenimiento diario (`job_state.py:38`) | confirmado | `CRITICOS` solo llevaba `daily_maintenance`: los recordatorios del cliente, el resumen del coach y los avisos de videollamada podían estar muertos días sin que nadie se enterara. Ahora los secundarios también se vigilan, con margen ancho (una vuelta perdida no alarma). |
| Tras un fallo ya no escala a "lleva N horas" (`job_state.py:109`) | confirmado | La rama de `last_ok is False` devolvía ANTES de mirar la antigüedad: un trabajo que falló y además se paró se quedaba para siempre en "terminó con errores" —que suena a que sigue corriendo—. Ahora la antigüedad se mira primero y el motivo conserva el error. |
| La huella del resumen se guarda truncada a 300 (`push.py:742`) | confirmado | `record_job` recorta el detalle a 300 caracteres y la lista de claves los pasa con ~10 alertas: dos conjuntos DISTINTOS se leían como "sin novedades" y el resumen se silenciaba justo cuando había algo nuevo. Ahora se guarda un sha256 (64 caracteres siempre). |
| Tag de push del coach compartida (`push.py:589`) | confirmado | `"dq-vc-coach"` fija: dos clientes con videollamada el mismo día → el móvil solo enseñaba la última. Ahora la tag lleva el id de la llamada (como ya hacía `dq-vc-propuesta-{id}`). |
| "Escribir a mi coach" sin alerta (`alerts.py:252`) | confirmado | La alerta vivía DETRÁS de los `return` de "sin plan publicado" e "inactivo". Justo los dos que más escriben —el que aún no tiene plan y pregunta por él, y el que lleva semanas parado— mandaban su mensaje a un agujero. Ahora se evalúa lo primero. |
| La racha no usa la "única verdad" (`portal.py:195`) | confirmado | Tenía su propio predicado en SQL (`is_not(None)`), que da por bueno lo que el motor descarta (`free_notes` vacío, `chosen_options_json` sin elegir: filas que el autosave crea al abrir la pantalla). Premiaba días que para el coach no existían. Ahora consume `dias_registrados`. |
| Un push sin `count` apaga el badge (`sw.js:37`) | confirmado | `Number(undefined) \|\| 0` → `clearAppBadge()`. **Dos emisores reales** lo hacían: el resumen semanal y el aviso de cliente inactivo, que borraban el "N pagos sin leer". Ahora "sin count" ≠ "count 0" (no se toca el badge) y los dos emisores mandan el suyo. |
| Contar las series como día registrado deja ciego al coach (`jobs.py:106`) | **matizado** | El contador amplio es DELIBERADO y está blindado con test (un DQR Train que entrena a diario no puede salir "en riesgo"): **no se toca**. Pero el reproductor destapó el hueco real detrás: quien elige su comida cada día cuenta como registrado, va verde en todas las pantallas, y al cerrar la quincena el motor se encuentra con 0-1 pesajes, responde `dato_insuficiente` y no se puede ajustar nada — catorce días perdidos que el coach descubría tarde. Aviso NUEVO `sin_pesajes` pasada la mitad del período (sin una consulta extra en el barrido). |

**De propina, arreglado al toparme con ello:** la suite era dependiente del
estado — correr `pytest` dos veces daba resultados distintos. La caché del
contenido educativo se guarda en un sidecar del storage y SOBREVIVE entre
ejecuciones: el primer pase la poblaba y el siguiente se saltaba la llamada de
IA que los tests del pipeline cuentan (`test_ai_service` fallaba a la segunda).
Se apaga en los tests (que es lo que el traspaso ya daba por hecho). Con eso,
los DOS fallos que arrastraba `test_ai_service` desaparecen: **652 en verde,
dos pases seguidos**.

## Ya comprobados a mano y arreglados (no vuelvas a mirarlos)

| Hallazgo | Dónde | Commit |
|---|---|---|
| El token del portal en claro en el access log de `/api/pay/{token}` | `backend/app/main.py` | `4265e4d` |
| El contador de fotos del cierre vive solo en memoria (reetiqueta desde "frontal", promete huecos que no hay) | `frontend/src/portal/PortalClose.tsx` | `4265e4d` |
| Una segunda contratación de la oferta se cancela tras cobrar 1 € | `backend/app/services/stripe_service.py` | `ca73e6e` |
| El rollback al agendar resucita la credencial de Google revocada | `backend/app/routers/clients.py` | `4ddd2d9` |
| Sin Google, la videollamada propuesta no se puede cerrar nunca | `frontend/src/components/ClientFeedbackTab.tsx` | `4ddd2d9` |
| Las equivalencias se leen de una clave que no existe: comida y cena invisibles para los revisores IA | `backend/app/services/plan_review.py` | `39666fd` |
| El test de las equivalencias inventa una forma de banco que el sistema no produce | `backend/tests/test_plan_review.py` | `39666fd` |
| El barrido de `/api/alerts` hace 7 consultas por cliente | `backend/app/routers/alerts.py` | `86eef25` |
| El plan declaraba macros que sus ingredientes no dan (cuadre de composición) | `backend/app/services/ai/generator.py` | `bf14bc0` |
| La memoria de vetos solo se saneaba al escribir, no al leer | `backend/app/services/coach_lessons.py` | `03c5149` |
| Una petición del cliente no avisaba si estaba inactivo o sin plan | `backend/app/routers/alerts.py` | `feb62ca` |
| Dos videollamadas el mismo día = un solo aviso al coach (tag compartida) | `backend/app/services/push.py` | `feb62ca` |
| Un correo que falló consumía su intento (día 12 y tope de cierre) | `backend/app/services/jobs.py` | `f15a561` |
| El que entrena pero no se pesa figuraba "al día" toda la quincena | `backend/app/routers/alerts.py` | `f9c8e03` |
| Un push sin `count` apagaba el badge del coach | `frontend/public/sw.js` | `2a0827f` |
| La huella del resumen se guardaba truncada: se repetía cada barrido | `backend/app/services/push.py` | `2a0827f` |
| Cuatro de los cinco automatismos podían morir en silencio | `backend/app/services/job_state.py` | `d1fa9ab` |
| El aviso de fallo del mantenimiento no escalaba nunca | `backend/app/services/job_state.py` | `d1fa9ab` |
| El gasto de IA se pisaba entre revisores en paralelo | `backend/app/services/ai_credit.py` | `616d2d4` |
| La racha contaba días que el motor descarta (cadena vacía) | `backend/app/services/portal.py` | `616d2d4` |
| Un `weekly_progression` malformado tumbaba la pantalla de Entreno (500) | `backend/app/services/portal.py` | `91d5f39` |
| Un `day` no textual tumbaba "Hoy" y los recordatorios de todos (500) | `backend/app/services/portal.py` | `3c6a561` |
| El cliente no podía subir fotos tras enviar la revisión | `frontend/src/portal/PortalApp.tsx` | `2ea541f` |
| Una baja fallida se llevaba los ficheros (borrado antes del commit) | `backend/app/routers/clients.py` | `7a3b3c4` |
| La baja RGPD no cancelaba el evento en Google Calendar | `backend/app/routers/clients.py` | `7a3b3c4` |
| "Descargar todo" no llevaba informes ni mensajes al coach | `backend/app/routers/clients.py` | `7a3b3c4` |
| El ZIP de portabilidad se armaba en memoria sin tope | `backend/app/routers/clients.py` | `7a3b3c4` |
| Caddy cortaba a 30 MB los vídeos que el backend admite hasta 300 | `frontend/Caddyfile` | `7a3b3c4` |
| El nombre del borrado sobrevivía en los planes de otros clientes | `backend/app/routers/clients.py` | `d65b343` |
| La red de seguridad del borrado no miraba si el cobro se anonimizó | `backend/tests/test_borrado_rgpd.py` | (esta tanda) |
| El reenvío del pendiente del Diario corre sin control de concurrencia y borra lo tecleado después | `frontend/src/portal/PortalDiary.tsx:213` | (tanda 6) |
| El pendiente del Diario se guarda con una clave sin cliente: en un móvil compartido escribe el diario de otro | `frontend/src/portal/PortalDiary.tsx:48` | (tanda 6) |
| El sidecar de la vía formulario congela el retrato y las correcciones del coach dejan de llegar al prompt | `backend/app/routers/portal_public.py:268` | (tanda 6) |
| Las contradicciones del nuevo endpoint son una foto fija: no se apagan al corregir la ficha ni aparecen si las crea el coach | `backend/app/routers/clients.py:927` | (tanda 6) |
| Las fotos iniciales se guardan todas como `front`: el primer informe empareja un ángulo equivocado | `backend/app/services/feedback_service.py:116` | (tanda 6) |
| El cliente que mandó su anamnesis en PDF ve la tarjeta de fotos iniciales y recibe un 403 imposible de satisfacer | `frontend/src/pages/AnamnesisPage.tsx:501` | (tanda 6) |
| El diario sin guardar al cruzar la medianoche se tira a la basura, pudiendo reenviarse con su fecha | `frontend/src/portal/PortalDiary.tsx:64` | (tanda 6) |
| El pre-relleno "solo si está vacío" deja muerto el campo de duración de sesión (y trata `false` como vacío) | `frontend/src/pages/AnamnesisPage.tsx:254` | (tanda 6) |
| El criterio único no llega a `/anamnesis-pdf`: el camino inverso sigue pisando la ficha revisada | `backend/app/routers/portal_public.py:406` | (tanda 6) |
| El sello editado (y el `rev` nuevo) se tiran: `normalize` se queda con el plan viejo | `frontend/src/components/ClientPlanPanel.tsx:320` | (tanda 4) |
| DQR Train: regenerar el plan no sella la adaptación → el banner "sin adaptar" es eterno | `backend/app/routers/clients.py:1726` | (tanda 4) |
| Copiar un plan/modelo arrastra el sello de adaptación de OTRO cliente dentro de `training_json` | `backend/app/services/plan_library.py:268` | (tanda 4) |
| La fila DIFERENCIA reabre el doble descuento que el commit venía a cerrar | `backend/app/services/payments.py:258` | (tanda 2) |
| Borrar un cobro a mano puede marcar como IMPAGADO a un cliente que sí pagó | `backend/app/routers/payments.py:215` | (tanda 2) |
| La gráfica de perímetros invierte las series cuando las etiquetas no coinciden | `backend/app/services/docs/charts.py:146` | (tanda 4) |
| El Word del educativo deja de importarse en cuanto el cliente tiene alergias o patrón dietético | `backend/app/services/word_import.py:722` | (tanda 4) |
| "Por qué este enfoque" hereda el volcado interno viejo y suma una frase en cada revisión | `backend/app/services/adapt_plan.py:548` | (tanda 4) |
| La caché por contenido del PDF nunca acierta con el plan: cada descarga arranca LibreOffice | `backend/app/services/docs/pdf_convert.py:55` | (tanda 4) |
| El cupo global de altas apaga el formulario todo el día con 25 peticiones, y el único aviso es un push best-effort | `backend/app/routers/public_site.py:146` | (tanda 2) |
| El aviso del barrido cortado pide al coach dos cosas que no puede hacer | `frontend/src/pages/PagosPage.tsx:250` | (tanda 2) |
| El test del borrado del cobro a mano pasa igual sin el recálculo de la ficha | `backend/tests/test_cobro_manual.py:211` | (tanda 2) |
| El "total" de cobros de la ficha se corta en 20 movimientos y suma dinero de prueba | `frontend/src/pages/ClientProfilePage.tsx:789` | (tanda 2) |
| Una devolución repescada por la sincronización entra ya marcada como leída | `backend/app/services/payments.py:219` | (tanda 2) |
| Regenerar solo el educativo vuelve a pedirlo sin alergias ni patrón dietético | `backend/app/routers/plans.py:576` | (tanda 4) |
| La lista de la compra va en una caja marcada como no divisible entre páginas | `backend/app/services/docs/plan_doc.py:637` | (tanda 4) |
| El test del cupo pasa aunque el contador de altas esté muerto | `backend/tests/test_public_register.py:213` | (tanda 2) |
| El cuadre deshace lo que el solver §2 acaba de fijar: se salta las cotas del catálogo y deja la medida casera mintiendo ("4 ud (165 g)") | `backend/app/services/ai/generator.py:1086` | (tanda 8) |
| Un ingrediente pequeño que cae a 0 g hace fallar el `model_validate` y el `except` tira TODAS las reparaciones del banco, en silencio | `backend/app/services/ai/generator.py:1088` | (tanda 8) |
| La baja RGPD puede quedar bloqueada por un error de Stripe que el filtro no reconoce | `backend/app/services/stripe_service.py:1091` | (tanda 8) |
| Las ramas de "aversión" y "patrón" de `_sin_cifras` no coinciden con ningún veto real: el prompt recibe frases mutiladas | `backend/app/services/coach_lessons.py:219` | (tanda 8) |
| La memoria de vetos (§13) deja de aprender del banco de comidas: los alérgenos y los desvíos ya no se anotan | `backend/app/services/ai/generator.py:1079` | (tanda 8) |
| La pestaña Historial se queda girando para siempre si su carga falla | `frontend/src/components/ClientHistoryTab.tsx:25` | (tanda 8) |
| Recursos → Aprendizaje: `PageLoader` eterno si fallan las lecciones | `frontend/src/pages/RecursosPage.tsx:100` | (tanda 8) |
| Las acciones del documento del plan no dan señal de estar trabajando (y "Enviar plan por email" permite doble envío al cliente) | `frontend/src/components/ClientPlanPanel.tsx:1219` | (tanda 8) |
| "Copiar enlace" del alta afirma que copió aunque no copie | `frontend/src/pages/ClientsPage.tsx:445` | (tanda 8) |
| El panel enseña fechas en crudo (2026-08-17) donde el resto usa formato español | `frontend/src/components/ClientTrackingTab.tsx:218` | (tanda 8) |
| Cancelar la oferta no limpia `stripe_subscription_id`: el cliente queda sin renovación posible | `backend/app/services/stripe_service.py:1096` | (tanda 8) |
| La sincronización no repesca los cobros FALLIDOS, que es lo más caro de perder | `backend/app/services/payments.py:621` | (tanda 8) |
| Los contracargos (`charge.dispute.*`) no se manejan: el dinero se va y nadie se entera | `backend/app/services/stripe_service.py:265` | (tanda 8) |
| El aviso "N sin ficha" del feed de pagos no tiene salida: ninguna acción lo apaga | `backend/app/services/payments.py:331` | (tanda 8) |
| `int(client_id)` sin proteger en el webhook: un checkout ajeno con referencia no numérica lo tumba | `backend/app/services/stripe_service.py:1416` | (tanda 8) |
| El diagnóstico de correo existe en el backend y no hay ninguna pantalla que lo abra | `backend/app/routers/email.py:35` | (tanda 8) |
| La página de "¡Pago recibido!" promete un correo que en la renovación no existe | `frontend/src/pages/PlansPage.tsx:312` | (tanda 8) |
| El "enlace de reservas" se guarda y no lo lee nadie | `frontend/src/pages/RecursosPage.tsx:447` | (tanda 8) |
| Sin enlace de Meet no se avisa al cliente, pero el toast dice que sí | `backend/app/routers/clients.py:1033` | (tanda 8) |
| Marcar el feedback como enviado falla en silencio en la vía WhatsApp | `frontend/src/components/ClientFeedbackTab.tsx:258` | (tanda 8) |
| Modificar sin teléfono promete un WhatsApp que nunca se abre | `frontend/src/components/ClientFeedbackTab.tsx:108` | (tanda 8) |
| El entrenamiento llega como recuento: dos revisores se pagan a ciegas (y enteros en planes solo-nutrición) | `backend/app/services/plan_review.py` | (tanda 8) |
| El atajo para recuperar el educativo sin repagar el plan no tiene botón (y genera el prompt sin el contexto del cliente) | `backend/app/routers/plans.py` | (tanda 8) |
| Una respuesta cortada por `max_tokens` se trata como "JSON mal formado" y se reintenta idéntica | `backend/app/services/ai/client.py` | (tanda 8) |
| El núcleo manda ~28 KB de biblioteca de ejercicios sin cachear y los repaga enteros en cada reintento | `backend/app/services/ai/generator.py` | (tanda 8) |
| "Coste medio por plan" y "~N planes" reparten TODO el gasto de IA entre los planes | `backend/app/services/ai_credit.py` | (tanda 8) |
| "Descargar todo" (export RGPD) está construido y no tiene ni un botón | `frontend/src/pages/ClientProfilePage.tsx` | (tanda 8) |
| El endpoint que recupera el educativo fallido no lo llama nadie: el coach solo puede repagar el plan entero | `frontend/src/components/ClientPlanPanel.tsx` | (tanda 8) |
| El estado del email (SMTP) tiene endpoints de diagnóstico y ninguna pantalla | `frontend/src/pages/RecursosPage.tsx` | (tanda 8) |
| El "Enlace de reservas" que el coach guarda no lo lee nadie | `frontend/src/lib/whatsapp.ts` | (tanda 8) |
| `AUTO_PILOT_DEFAULT` documentado y sin efecto | `backend/app/config.py` | (tanda 8) |
| El cuestionario dice "te hemos enviado el acceso por email" aunque no se haya enviado ninguno, y no deja vía de vuelta al portal | `frontend/src/pages/AnamnesisPage.tsx:497` | (tanda 6) |
| Al cliente DQR Train el portal le anuncia una dieta que su PDF no contiene | `frontend/src/portal/PortalApp.tsx:290` | (tanda 6) |
| "Recursos" es la única pantalla del portal cuyo error no se puede reintentar, y el texto invita a hacerlo | `frontend/src/portal/PortalResources.tsx:46` | (tanda 6) |


---

## Pendientes · verificación adversarial de la ronda anterior

Tipos: `arreglo_incompleto` (el commit dice cerrar algo que no cierra),
`regresion` (el commit rompió algo que funcionaba), `suposicion_falsa` (el
commit da por cierto algo que no lo es), `test_flojo` (la regresión no caza el
fallo que dice cazar).

### Graves


### Medias

- **[media] El cuadre deshace lo que el solver §2 acaba de fijar: se salta las cotas del catálogo y deja la medida casera mintiendo ("4 ud (165 g)")** — `backend/app/services/ai/generator.py:1086` · `regresion`
- **[media] Un ingrediente pequeño que cae a 0 g hace fallar el `model_validate` y el `except` tira TODAS las reparaciones del banco, en silencio** — `backend/app/services/ai/generator.py:1088` · `arreglo_incompleto`
- **[media] El sello editado (y el `rev` nuevo) se tiran: `normalize` se queda con el plan viejo** — `frontend/src/components/ClientPlanPanel.tsx:320` · `suposicion_falsa`
- **[media] DQR Train: regenerar el plan no sella la adaptación → el banner "sin adaptar" es eterno** — `backend/app/routers/clients.py:1726` · `arreglo_incompleto`
- **[media] Copiar un plan/modelo arrastra el sello de adaptación de OTRO cliente dentro de `training_json`** — `backend/app/services/plan_library.py:268` · `arreglo_incompleto`


- **[media] El reenvío del pendiente del Diario corre sin control de concurrencia y borra lo tecleado después** — `frontend/src/portal/PortalDiary.tsx:213` · `regresion`
- **[media] El pendiente del Diario se guarda con una clave sin cliente: en un móvil compartido escribe el diario de otro** — `frontend/src/portal/PortalDiary.tsx:48` · `regresion`
- **[media] El sidecar de la vía formulario congela el retrato y las correcciones del coach dejan de llegar al prompt** — `backend/app/routers/portal_public.py:268` · `regresion`
- **[media] Las contradicciones del nuevo endpoint son una foto fija: no se apagan al corregir la ficha ni aparecen si las crea el coach** — `backend/app/routers/clients.py:927` · `arreglo_incompleto`
- **[media] Las fotos iniciales se guardan todas como `front`: el primer informe empareja un ángulo equivocado** — `backend/app/services/feedback_service.py:116` · `regresion`
- **[media] El cliente que mandó su anamnesis en PDF ve la tarjeta de fotos iniciales y recibe un 403 imposible de satisfacer** — `frontend/src/pages/AnamnesisPage.tsx:501` · `regresion`
- **[media] La fila DIFERENCIA reabre el doble descuento que el commit venía a cerrar** — `backend/app/services/payments.py:258` · `regresion`
- **[media] Borrar un cobro a mano puede marcar como IMPAGADO a un cliente que sí pagó** — `backend/app/routers/payments.py:215` · `suposicion_falsa`
- **[media] La baja RGPD puede quedar bloqueada por un error de Stripe que el filtro no reconoce** — `backend/app/services/stripe_service.py:1091` · `arreglo_incompleto`
- **[media] La gráfica de perímetros invierte las series cuando las etiquetas no coinciden** — `backend/app/services/docs/charts.py:146` · `regresion`
- **[media] El Word del educativo deja de importarse en cuanto el cliente tiene alergias o patrón dietético** — `backend/app/services/word_import.py:722` · `regresion`
- **[media] "Por qué este enfoque" hereda el volcado interno viejo y suma una frase en cada revisión** — `backend/app/services/adapt_plan.py:548` · `arreglo_incompleto`
- **[media] La caché por contenido del PDF nunca acierta con el plan: cada descarga arranca LibreOffice** — `backend/app/services/docs/pdf_convert.py:55` · `suposicion_falsa`
- **[media] El cupo global de altas apaga el formulario todo el día con 25 peticiones, y el único aviso es un push best-effort** — `backend/app/routers/public_site.py:146` · `arreglo_incompleto`

### Bajas

- **[baja] Las ramas de "aversión" y "patrón" de `_sin_cifras` no coinciden con ningún veto real: el prompt recibe frases mutiladas** — `backend/app/services/coach_lessons.py:219`
- **[baja] La memoria de vetos (§13) deja de aprender del banco de comidas: los alérgenos y los desvíos ya no se anotan** — `backend/app/services/ai/generator.py:1079`

- **[baja] Los revisores en paralelo se pisan el saldo de créditos (lost update sobre `ai_credit_state`)** — `backend/app/services/ai_credit.py:70`
- **[baja] El diario sin guardar al cruzar la medianoche se tira a la basura, pudiendo reenviarse con su fecha** — `frontend/src/portal/PortalDiary.tsx:64`
- **[baja] El pre-relleno "solo si está vacío" deja muerto el campo de duración de sesión (y trata `false` como vacío)** — `frontend/src/pages/AnamnesisPage.tsx:254`
- **[baja] El criterio único no llega a `/anamnesis-pdf`: el camino inverso sigue pisando la ficha revisada** — `backend/app/routers/portal_public.py:406`
- **[baja] El aviso del barrido cortado pide al coach dos cosas que no puede hacer** — `frontend/src/pages/PagosPage.tsx:250`
- **[baja] El test del borrado del cobro a mano pasa igual sin el recálculo de la ficha** — `backend/tests/test_cobro_manual.py:211`
- **[baja] El "total" de cobros de la ficha se corta en 20 movimientos y suma dinero de prueba** — `frontend/src/pages/ClientProfilePage.tsx:789`
- **[baja] Una devolución repescada por la sincronización entra ya marcada como leída** — `backend/app/services/payments.py:219`
- **[baja] Regenerar solo el educativo vuelve a pedirlo sin alergias ni patrón dietético** — `backend/app/routers/plans.py:576`
- **[baja] La lista de la compra va en una caja marcada como no divisible entre páginas** — `backend/app/services/docs/plan_doc.py:637`
- **[baja] El test del cupo pasa aunque el contador de altas esté muerto** — `backend/tests/test_public_register.py:213`

### Bajas


---

## Pendientes · los dos dominios que faltaban

### Coherencia de UX — panel del coach


### Coherencia de UX — portal del cliente


- **[media] El cuestionario dice "te hemos enviado el acceso por email" aunque no se haya enviado ninguno, y no deja vía de vuelta al portal** — `frontend/src/pages/AnamnesisPage.tsx:497`
- **[media] Al cliente DQR Train el portal le anuncia una dieta que su PDF no contiene** — `frontend/src/portal/PortalApp.tsx:290`
- **[baja] "Recursos" es la única pantalla del portal cuyo error no se puede reintentar, y el texto invita a hacerlo** — `frontend/src/portal/PortalResources.tsx:46`

### Integraciones — Stripe

- **[media] El embudo self-serve de `/planes` está construido y desconectado: tres endpoints públicos sin consumidor** — `backend/app/routers/public_site.py:128`
  · VERIFICADO y REAL (`publicPlanPrices`/`publicRegister`/`publicCheckout` no
  los llama nadie). NO se retiran: son públicos y estables y pueden estar
  enlazados desde fuera (bio de Instagram, un QR). Anotado en el código.
  Si el dueño confirma que el embudo no vuelve, se borran de una vez.

### Integraciones — email y push


- **[alta] El diagnóstico de correo existe en el backend y no hay ninguna pantalla que lo abra** — `backend/app/routers/email.py:35`
- **[alta] La página de "¡Pago recibido!" promete un correo que en la renovación no existe** — `frontend/src/pages/PlansPage.tsx:312`

### Integraciones — Google y WhatsApp


---

## Pendientes · optimización

### Backend

- **[media] El historial del cliente relee las series de todas las revisiones anteriores en cada iteración (coste cuadrático)** — `backend/app/routers/clients.py:1242`
- **[media] La ficha carga todas las versiones del plan con sus cuatro JSONB para imprimir cuatro escalares** — `backend/app/routers/clients.py:1233`
- **[media] "Elegir base" lee el plan entero de todos los clientes para pintar una línea de cada uno** — `backend/app/services/plan_library.py:426`
- **[media] El panel de Planificación descarga todas las versiones históricas del plan enteras, y las repide tras cada acción** — `backend/app/routers/plans.py:477`
- **[baja] La biblioteca de ejercicios (141 KB) viaja dos veces al abrir el editor, y una cuarta parte son notas que ninguna pantalla pinta** — `backend/app/routers/exercises.py:58`
- **[baja] La pantalla de Entreno del portal resuelve dos veces el plan y consulta la biblioteca una vez por sesión** — `backend/app/services/portal.py:412`
- **[baja] La lista de períodos hace una consulta de feedback por cada revisión** — `backend/app/routers/plans.py:721`

### Frontend

- **[media] La biblioteca de ejercicios (146 KB) se descarga dos veces por visita, y otra vez en cada apertura del editor** — `frontend/src/components/ClientPlanEditor.tsx:102`
- **[media] Fotos del período: N peticiones idénticas de la lista y descarga EN SERIE a resolución original para miniaturas de 80×96 px** — `frontend/src/components/ClientFeedbackTab.tsx:1129`
- **[media] `/api/clients` se pide entero cada 3 s desde Hoy y desde Clientes, con las notas clínicas que ninguna de las dos pantallas lee** — `frontend/src/pages/DashboardPage.tsx:145`
- **[baja] "Vídeos de ejercicios": 279 filas sin virtualizar que se repintan enteras en cada tecla, y miniaturas de YouTube de 480×360 sin lazy** — `frontend/src/pages/RecursosPage.tsx:1087`
- **[baja] El aviso "Sin conexión" del panel móvil está montado dos veces** — `frontend/src/components/AppShell.tsx:127`

### Créditos de IA

- **[media] El panel de revisión de la revisión quincenal está construido y nunca se ejecuta**
  · VERIFICADO y REAL (`is_checkin` + `CHECKIN_EXTRA_ROLES` existen en
  `review_panel.py`; nadie pasa `is_checkin=True`, y `adapt_plan` solo corre
  `check_nutrition`). NO se enchufa a propósito: pagar los 8-10 roles en cada
  quincena de cada cliente va justo contra el recorte de créditos que pidió el
  dueño, y hacerlo "solo si el Revisor 0 veta" exige construir un `ClientContext`
  completo dentro de `adapt_plan`. Es una DECISIÓN de producto: dígalo el dueño.

### Construido y sin conectar


---

## Tanda 2 (pagos, libro de caja y altas) — VERIFICADOS Y ARREGLADOS en paralelo

> Sesión paralela sobre esta misma rama. Cada uno se reprodujo leyendo el
> código antes de tocarlo, y va con su regresión (`tests/test_auditoria_pagos.py`).

| Hallazgo | Dónde | Qué era de verdad |
|---|---|---|
| La fila DIFERENCIA reabre el doble descuento | `services/payments.py` | Real. El guard solo miraba la fila con el id del cargo, no las sintéticas `…_difN`: al llegar después el desglose, el mismo dinero restaba dos veces. Ahora el desglose COMPLETO las sustituye (y si viene corto —Stripe pagina de 10 en 10— se respetan las sintéticas). |
| Una devolución repescada entra ya marcada como leída | `services/payments.py` | Real, solo estaba arreglado en la vía del desglose. La devolución posterior a lo anotado vuelve a "sin leer". |
| Borrar un cobro a mano puede marcar como IMPAGADO a quien sí pagó | `routers/payments.py` | Real: el recálculo solo miraba `client_id` y los cobros de Stripe se enlazan por EMAIL. Ahora mira también por correo y nunca degrada a un cliente con suscripción viva. |
| El "total" de cobros de la ficha se corta en 20 y suma dinero de prueba | `ClientProfilePage.tsx` | Real. El total lo calcula ahora el backend (`neto_de_cliente`) sobre TODOS los movimientos y sin `livemode=false`. |
| El aviso del barrido cortado pide dos cosas que el coach no puede hacer | `PagosPage.tsx` | Real: no había control de días y repetir el barrido relee lo mismo. Ahora hay selector de ventana y, al cortarse, se repasan solos los últimos 7 días. |
| El cupo de altas apaga el formulario todo el día | `routers/public_site.py` | Real, y además el lead se perdía entero. Ahora queda anotado (`public_signup_blocked`) y sale un aviso de sistema en "Hoy" con nombre y teléfono para darle el alta a mano. |
| El test del borrado del cobro a mano pasa sin el recálculo | `tests/test_cobro_manual.py` | Real: comparaba con "no es None". Ahora compara con la fecha del cobro que queda. |
| El test del cupo pasa aunque el contador esté muerto | `tests/test_public_register.py` | Real (tope 0 → `0 >= 0`). Ahora da un alta real y agota el cupo. |

**No tocado a propósito** (es de otra tanda en marcha): todo `services/stripe_service.py`,
`PlansPage.tsx` y el embudo self-serve de `/planes`.

**Aviso**: `tests/test_ai_service.py::test_full_pipeline_generates_plan` falla en
esta rama desde antes de esta tanda (el pipeline hace 2 llamadas y el test espera 3).


---

## Tanda 4 (IA y planes) — VERIFICADOS A MANO Y ARREGLADOS

> Sesión "rutina y dieta quice". El workflow de verificación adversarial (13
> hallazgos × 2 verificadores) **murió entero contra el límite de sesión**, así
> que la verificación se hizo A MANO, leyendo el código y reproduciendo la
> cadena del daño. **9 de 9 comprobados eran reales.**

| Hallazgo | Dónde | Qué era de verdad |
|---|---|---|
| El sello editado y el `rev` nuevo se tiran: `normalize` se queda con el plan viejo | `ClientPlanPanel.tsx` | Real y en DOS sitios. `normalize` lee `p.nutrition ?? p.nutrition_json`, y se le pasaba `{...plan, nutrition_json: …}`: el valor VIEJO gana siempre y la respuesta del backend se tira entera. Consecuencias: tras aplicar un Word el panel seguía enseñando las cifras de antes ("Word aplicado" y nada cambia en pantalla), y el `rev` rancio hacía morir la siguiente edición con un 409 falso — justo lo que el comentario decía evitar. |
| DQR Train: regenerar no sella la adaptación → banner "sin adaptar" eterno | `routers/clients.py` | Real. El sello solo se escribía `if nutrition is not None`; un plan solo-entreno no tiene nutrición. Ahora va a `training_json`, que es donde lo busca la alerta y donde lo escribe `adapt_plan`. |
| Copiar un plan/modelo arrastra el sello de adaptación de OTRO cliente | `services/plan_library.py` | Real, y es fuga de datos: la limpieza de `applied_adjustments`/`rev`/`gen_inputs`/`manual_changes` existía SOLO para la nutrición, y en los planes solo-entreno el sello vive en el entreno. El destino salía "adaptado a la revisión #7" de otro cliente, con las CIFRAS del origen dentro de sus Novedades, y su aviso de "sin adaptar" se apagaba solo. Arreglado también en los MODELOS. |
| "Por qué este enfoque" hereda el volcado viejo y suma una frase por revisión | `services/adapt_plan.py` | Real (la parte del volcado ya estaba; la ACUMULACIÓN no). La marca lleva el nº de revisión, así que cada quincena añadía otro párrafo idéntico. Peor aún en `split_rationale`, que no deduplicaba nada: "· Adaptado a la revisión quincenal #1. · … #2. · … #3." impreso en el PDF bajo "Estructura ·". Ahora la coletilla SUSTITUYE a la anterior y el argumentario original queda intacto. |
| El Word del educativo deja de importarse si el cliente tiene alergias | `services/word_import.py` | Real. El importador comparaba contra todas las píldoras "con texto", pero `plan_doc` imprime solo las que pasan el filtro de alérgenos y patrón: con alergias el Word traía 2 y el plan 3, el recuento no cuadraba y la caja entera se descartaba. Ahora delega en `_blocked_line`, el MISMO criterio del documento. |
| La gráfica de perímetros invierte las series cuando las etiquetas no coinciden | `docs/charts.py` + `feedback_service.py` | Real. Con una medida del cierre anterior ("Anterior") y otra de la anamnesis ("Inicio") la rejilla tenía 3 columnas y las series de 2 puntos se desplazaban una posición: **el "antes" se pintaba sobre "Actual"**. Doble arreglo: una sola etiqueta de "antes" en origen ("Antes" si las fuentes se mezclan) y, en la gráfica, cada punto en la columna de SU etiqueta. |
| La caché por contenido del PDF nunca acierta: cada descarga arranca LibreOffice | `docs/pdf_convert.py` | Real y **medido**: python-docx sella la hora en cada entrada del zip, así que el mismo plan guardado 1,2 s después ya da otro sha1. Con solo 2 conversiones simultáneas, el portal contestaba "el servidor está preparando otros documentos" sin necesidad. La clave se calcula ahora sobre el contenido del zip, ignorando timestamps. |
| Regenerar solo el educativo lo pide sin alergias ni patrón dietético | `routers/plans.py` | Real: el atajo montaba un ctx falso con solo el nombre del split, así que `_education_user_prompt` no recibía restricciones y devolvía el educativo genérico. El documento las filtra al imprimir, así que el cliente con alergias se quedaba además con menos contenido del que ha pagado. |
| La lista de la compra va en una caja no divisible entre páginas | `docs/plan_doc.py` | Real. La lista no tiene cota (todos los alimentos de la semana): en una caja `cant_split=True`, lo que no cabe en la página se pierde de vista y el cliente va al súper con media lista. |

**De regalo, la suite deja de dar rojos falsos** (`tests/conftest.py`): la caché
del educativo no se apagaba durante los tests, así que un sidecar de una
ejecución real —o simplemente un test anterior de la misma suite, que la
rellena— servía el educativo de vuelta y los tests que CUENTAN llamadas a la IA
fallaban sin que nada estuviera roto (`test_full_pipeline_generates_plan` 2≠3 y
`test_plan_solo_entrenamiento_sin_dieta` 1≠2). CLAUDE.md ya lo pedía; faltaba
imponerlo. **Con esto la suite entera queda en verde.**

**No tocado a propósito** (los tiene abiertos la tanda 1 en este momento):
`services/ai/generator.py` (los tres hallazgos del cuadre/0 g/lecciones del
banco) y `services/coach_lessons.py:219`. Quedan PENDIENTES para quien cierre
esa tanda.

⚠️ **Aviso de reparto**: la sesión de la tanda 1 está commiteando desde las
20:18 en `jobs.py`, `job_state.py`, `push.py`, `alerts.py` y `sw.js` — que son
exactamente los ficheros que la tanda 3 reclamó a las 14:58. Conviene que se
pongan de acuerdo antes de que dupliquen trabajo.


---

## Tanda 7 (optimización backend + frontend) — MEDIDA Y ARREGLADA

> Sesión "rutina y dieta quice". Verificación con banco sintético propio (40
> fichas, 120 planes, 160 revisiones, 27.000 series) contando CONSULTAS, BYTES y
> MILISEGUNDOS por endpoint, antes y después. Nada aquí es una estimación.

| Endpoint | Antes | Después |
|---|---|---|
| `GET /api/clients` (cada 3 s × 2 pantallas) | 69,2 KB | **42,0 KB** |
| `GET /api/exercises` | 146,2 KB | **89,0 KB** + cacheada en el front |
| `GET /clients/{id}/plans` (3 versiones) | 54,8 KB | **19,8 KB** |
| `GET /clients/{id}/history` | 27 consultas · 39 ms | **18 consultas · 25 ms** |
| `GET /clients/{id}/periods` (4 revisiones) | 7 consultas | **4 consultas** |
| `GET /api/p/{token}/training` | 11 consultas | **8 consultas** |
| `list_alerts` (cada 20 s) | 108 ms de CPU | **45 ms** |

**Qué se hizo, y por qué:**

- **El listado de clientes deja de enviar el historial clínico** (lesiones,
  patologías, medicación, hábitos, alergias). Lo piden "Hoy" y "Clientes" cada
  3 segundos y NINGUNA de las dos lo pinta; la ficha lo sigue trayendo entero
  por su endpoint. ⚠️ Con una respuesta de tipo LISTA, `response_model_exclude`
  va bajo `{"__all__": …}`: con el set suelto no excluye nada (se probó).
- **La biblioteca de ejercicios** deja de mandar las notas técnicas y
  biomecánicas (38,6 KB de 146: el 26 %) que ninguna pantalla pinta —las lee el
  BACKEND de la base— y el detalle de un ejercicio las sigue devolviendo. En el
  front, la biblioteca se **cachea en memoria** (5 min, compartiendo la petición
  en vuelo): viajaba dos veces al abrir la ficha y otra en cada apertura del
  editor. Cualquier cambio en Recursos la invalida.
- **Los planes históricos ya no viajan enteros**: el listado devuelve completos
  solo los DOS que el panel puede pintar (el publicado y el borrador más nuevo)
  y recortados el resto. `?ligero=true` y `?todo=true` siguen disponibles.
- **El historial deja de ser cuadrático**: `compute_period_summary` acepta las
  series YA cargadas (`sets_por_periodo`), así que resumir 8 revisiones no
  relee ocho veces el mismo histórico. Y los planes de la cabecera se leen como
  4 escalares, no como 4 JSONB por versión.
- **Fuera dos N+1** de informes: la lista de revisiones y el historial pedían un
  `FeedbackDoc` por revisión.
- **El portal resuelve la biblioteca una vez** para todas las sesiones de
  entreno (era una consulta por sesión, con los mismos ejercicios repetidos), y
  es de las pantallas más visitadas del sistema.
- **`/api/alerts`**: `product_match` normalizaba el catálogo entero una vez POR
  CLIENTE (18.160 normalizaciones y 168.000 pasadas de sinónimos por barrido, el
  100 % del tiempo del endpoint). La función es pura → memorizada.
- **Frontend**: las fotos de la revisión se descargaban EN SERIE y cada tarjeta
  de revisión pedía la lista entera de fotos (6 peticiones idénticas con 6
  revisiones) → lista cacheada 30 s y descargas en paralelo; el aviso "Sin
  conexión" estaba montado DOS VECES en el móvil del coach; y las ~300 portadas
  de vídeo de Recursos se pedían todas de golpe → `loading="lazy"`.

**Refutado con medida** (no se toca): `plan_library:426` — "Elegir base" lee los
planes enteros, sí, pero son ~20 ms y se abre unas pocas veces al día: del orden
de 0,1 s de CPU diarios. Dos verificaciones independientes coinciden.

**Queda medido y sin tocar** (para quien siga): el historial aún hace ~3
consultas por revisión (diario, ejercicios y el índice de períodos anteriores);
bajarlo exigiría más cirugía en `compute_period_summary`, que es la fuente de
verdad de las métricas del informe y no conviene tocar más de lo necesario.

Regresiones: `tests/test_auditoria_rendimiento.py` (7), con topes de consultas y
comprobación de que los campos que las pantallas SÍ usan siguen llegando.


---

## Integración de las tres fuentes — lo que encontró el navegador

> Con las ocho tandas repartidas, esta sesión verificó el CONJUNTO: base desde
> cero, suite completa, `tsc`/build/guardas y un recorrido real con Chromium por
> el panel (escritorio y móvil, 13 rutas cada uno) y el portal.

**Un 500 en la pantalla principal del cliente.** `GET /api/p/{token}/today`
devolvía 500 —el cliente veía "No se pudo cargar"— en cuanto el plan traía un
tipo inesperado. Comprobado con una matriz de ocho formas:

| forma del ejercicio | HOY antes | ENTRENO antes | ahora |
|---|---|---|---|
| `rir` numérico (`2` en vez de `"2"`) | **500** | 200 | 200 |
| `rep_range` numérico | **500** | 200 | 200 |
| sin `exercise_id` | **500** | 200 | 200 |
| `rest_sec` nulo | **500** | 200 | 200 |
| `sets` texto / nulo, `rest_sec` texto | 200 | 200 | 200 |

El mismo dato servido por dos endpoints con contratos distintos: Entreno
aguantaba las ocho y Hoy se caía con cuatro. Al `training_json` le llegan planes
editados a mano, importados del Word y copiados de un modelo, así que el
contrato de SALIDA no puede ser más estricto que lo que el sistema es capaz de
guardar. Arreglado en el único sitio donde se construye el payload
(`portal.py`: `_texto`/`_entero`), misma regla que `dia_de_sesion`. Regresión
con las seis formas en `tests/test_auditoria_rendimiento.py`.

**Latente, avisado y NO tocado** (es de la tanda 6, portal del cliente):
`PortalWorkout.tsx` indexa por `exercise_id` y el endpoint de Entreno ya podía
mandarlo nulo ANTES de este cambio (un ejercicio que no se resolvió contra la
biblioteca). No rompe la pantalla, pero en JS `logged[null]` mete todos los
ejercicios sin id en el mismo saco. Al declarar el tipo honesto (`number | null`)
salen 7 errores de TypeScript en ese fichero: ahí está el trabajo real. Se deja
para quien lleve esa pantalla.

**Comprobado y sano**: cero errores de consola, cero `pageerror` y cero 5xx en
las 13 rutas del panel (escritorio y móvil) y en las 6 del portal; una sola
cabeza de Alembic y arranque desde cero en verde; suite completa, `tsc`, build,
`check:anclas`, `check:avisos` y `lint:hooks` (0 errores) sobre el código de las
tres sesiones junto.

