# Hallazgos pendientes de verificar (agosto 2026)

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

---

## Pendientes · verificación adversarial de la ronda anterior

Tipos: `arreglo_incompleto` (el commit dice cerrar algo que no cierra),
`regresion` (el commit rompió algo que funcionaba), `suposicion_falsa` (el
commit da por cierto algo que no lo es), `test_flojo` (la regresión no caza el
fallo que dice cazar).

### Graves

- **[alta] La memoria de vetos ya guardada sigue yendo al prompt con las cifras y los alimentos del cliente** — `backend/app/services/coach_lessons.py:276` · `arreglo_incompleto`
- **[alta] El cuadre fija los macros al objetivo pero los gramos por otro ratio: el plan declara macros que sus propios ingredientes no dan** — `backend/app/services/ai/generator.py:221` · `regresion`

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
- **[media] La baja RGPD no cancela el evento de Google Calendar del cliente** — `backend/app/routers/clients.py:702` · `arreglo_incompleto`
- **[media] El nombre del cliente borrado sobrevive en los planes copiados a otros clientes** — `backend/app/routers/clients.py:730` · `arreglo_incompleto`
- **[media] "Descargar todo" sigue sin llevar los informes quincenales ni lo que el cliente escribió a su coach** — `backend/app/routers/clients.py:626` · `arreglo_incompleto`
- **[media] Los archivos se borran ANTES del commit: una baja fallida deja al cliente sin sus ficheros** — `backend/app/routers/clients.py:751` · `arreglo_incompleto`
- **[media] La gráfica de perímetros invierte las series cuando las etiquetas no coinciden** — `backend/app/services/docs/charts.py:146` · `regresion`
- **[media] El Word del educativo deja de importarse en cuanto el cliente tiene alergias o patrón dietético** — `backend/app/services/word_import.py:722` · `regresion`
- **[media] "Por qué este enfoque" hereda el volcado interno viejo y suma una frase en cada revisión** — `backend/app/services/adapt_plan.py:548` · `arreglo_incompleto`
- **[media] El tope de 30 MB de Caddy rompe la subida de vídeos de ejercicio (el backend admite 300 MB)** — `frontend/Caddyfile:43` · `regresion`
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
- **[baja] Las dos redes de seguridad del borrado no cubren lo que dicen cubrir** — `backend/tests/test_borrado_rgpd.py:74`
- **[baja] El ZIP de portabilidad se construye entero en memoria, sin tope** — `backend/app/routers/clients.py:618`
- **[baja] Regenerar solo el educativo vuelve a pedirlo sin alergias ni patrón dietético** — `backend/app/routers/plans.py:576`
- **[baja] La lista de la compra va en una caja marcada como no divisible entre páginas** — `backend/app/services/docs/plan_doc.py:637`
- **[baja] El test del cupo pasa aunque el contador de altas esté muerto** — `backend/tests/test_public_register.py:213`

---

## Pendientes · los dos dominios que faltaban

### Coherencia de UX — panel del coach

- **[media] La pestaña Historial se queda girando para siempre si su carga falla** — `frontend/src/components/ClientHistoryTab.tsx:25`
- **[media] Recursos → Aprendizaje: `PageLoader` eterno si fallan las lecciones** — `frontend/src/pages/RecursosPage.tsx:100`
- **[media] Las acciones del documento del plan no dan señal de estar trabajando (y "Enviar plan por email" permite doble envío al cliente)** — `frontend/src/components/ClientPlanPanel.tsx:1219`
- **[media] "Copiar enlace" del alta afirma que copió aunque no copie** — `frontend/src/pages/ClientsPage.tsx:445`
- **[baja] El panel enseña fechas en crudo (2026-08-17) donde el resto usa formato español** — `frontend/src/components/ClientTrackingTab.tsx:218`

### Coherencia de UX — portal del cliente

- **[alta] Tras enviar la revisión desaparece la única pantalla que sube fotos, pero el portal y el push las siguen pidiendo cada 3 h** — `frontend/src/portal/PortalApp.tsx:764`
- **[media] El cuestionario dice "te hemos enviado el acceso por email" aunque no se haya enviado ninguno, y no deja vía de vuelta al portal** — `frontend/src/pages/AnamnesisPage.tsx:497`
- **[media] Al cliente DQR Train el portal le anuncia una dieta que su PDF no contiene** — `frontend/src/portal/PortalApp.tsx:290`
- **[baja] "Recursos" es la única pantalla del portal cuyo error no se puede reintentar, y el texto invita a hacerlo** — `frontend/src/portal/PortalResources.tsx:46`

### Integraciones — Stripe

- **[media] Cancelar la oferta no limpia `stripe_subscription_id`: el cliente queda sin renovación posible** — `backend/app/services/stripe_service.py:1096`
- **[media] La sincronización no repesca los cobros FALLIDOS, que es lo más caro de perder** — `backend/app/services/payments.py:621`
- **[media] Los contracargos (`charge.dispute.*`) no se manejan: el dinero se va y nadie se entera** — `backend/app/services/stripe_service.py:265`
- **[media] El embudo self-serve de `/planes` está construido y desconectado: tres endpoints públicos sin consumidor** — `backend/app/routers/public_site.py:128`
- **[baja] El aviso "N sin ficha" del feed de pagos no tiene salida: ninguna acción lo apaga** — `backend/app/services/payments.py:331`
- **[baja] `int(client_id)` sin proteger en el webhook: un checkout ajeno con referencia no numérica lo tumba** — `backend/app/services/stripe_service.py:1416`

### Integraciones — email y push

- **[alta] El diagnóstico de correo existe en el backend y no hay ninguna pantalla que lo abra** — `backend/app/routers/email.py:35`
- **[alta] La página de "¡Pago recibido!" promete un correo que en la renovación no existe** — `frontend/src/pages/PlansPage.tsx:312`

### Integraciones — Google y WhatsApp

- **[media] El "enlace de reservas" se guarda y no lo lee nadie** — `frontend/src/pages/RecursosPage.tsx:447`
- **[media] Sin enlace de Meet no se avisa al cliente, pero el toast dice que sí** — `backend/app/routers/clients.py:1033`
- **[media] Marcar el feedback como enviado falla en silencio en la vía WhatsApp** — `frontend/src/components/ClientFeedbackTab.tsx:258`
- **[baja] Modificar sin teléfono promete un WhatsApp que nunca se abre** — `frontend/src/components/ClientFeedbackTab.tsx:108`

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

- **[media] El entrenamiento llega como recuento: dos revisores se pagan a ciegas (y enteros en planes solo-nutrición)**
- **[media] El panel de revisión de la revisión quincenal está construido y nunca se ejecuta**
- **[media] El atajo para recuperar el educativo sin repagar el plan no tiene botón (y genera el prompt sin el contexto del cliente)**
- **[media] Una respuesta cortada por `max_tokens` se trata como "JSON mal formado" y se reintenta idéntica**
- **[media] El núcleo manda ~28 KB de biblioteca de ejercicios sin cachear y los repaga enteros en cada reintento**
- **[baja] "Coste medio por plan" y "~N planes" reparten TODO el gasto de IA entre los planes**

### Construido y sin conectar

- **[media] "Descargar todo" (export RGPD) está construido y no tiene ni un botón**
- **[media] El endpoint que recupera el educativo fallido no lo llama nadie: el coach solo puede repagar el plan entero**
- **[media] El estado del email (SMTP) tiene endpoints de diagnóstico y ninguna pantalla**
- **[baja] El "Enlace de reservas" que el coach guarda no lo lee nadie**
- **[baja] `AUTO_PILOT_DEFAULT` documentado y sin efecto**
