/** Envío por WhatsApp con un clic (wa.me): feedback y plan del cliente.
 *  Los mensajes van SIN emojis (WhatsApp los corrompía en algunos móviles) y
 *  con un tono profesional: saludo, cuerpo estructurado y despedida. */

/** Normaliza un teléfono a formato wa.me (dígitos con prefijo de país).
 *  9 dígitos → se asume España (+34). Devuelve null si no hay teléfono. */
export function waPhone(phone: string | null | undefined): string | null {
  const digits = (phone ?? "").replace(/\D/g, "");
  if (!digits) return null;
  return digits.length === 9 ? `34${digits}` : digits;
}

/** Abre WhatsApp con el texto ya escrito para ese número. */
export function waUrl(phoneDigits: string, text: string): string {
  return `https://wa.me/${phoneDigits}?text=${encodeURIComponent(text)}`;
}

export function openWhatsApp(phoneDigits: string, text: string): void {
  window.open(waUrl(phoneDigits, text), "_blank", "noopener");
}

/** Primer nombre con la inicial en mayúscula ("mohamadou diallo" → "Mohamadou"). */
export function waFirstName(fullName: string): string {
  const first = (fullName ?? "").trim().split(/\s+/)[0] ?? "";
  return first ? first[0].toUpperCase() + first.slice(1) : "";
}

const CIERRE = "Cualquier duda que te surja, escríbeme por aquí y la vemos.\n\nUn saludo.";

/** Cuerpo del feedback (mismas secciones que la pestaña Feedback).
 *  Con bold=true los títulos van entre *asteriscos* (negrita de WhatsApp). */
export function feedbackBody(content: any, opts?: { bold?: boolean }): string {
  const b = (s: string) => (opts?.bold ? `*${s}*` : s);
  const parts: string[] = [];
  if (content?.natural_analysis) parts.push(content.natural_analysis);
  if (Array.isArray(content?.changes_bullets) && content.changes_bullets.length)
    parts.push(b("Cambios en el plan:") + "\n" + content.changes_bullets.map((x: string) => `• ${x}`).join("\n"));
  if (content?.answers) parts.push(b("Respuesta a tus dudas:") + "\n" + content.answers);
  if (Array.isArray(content?.next_objectives) && content.next_objectives.length)
    parts.push(b("Objetivos próximas 2 semanas:") + "\n" + content.next_objectives.map((x: string) => `• ${x}`).join("\n"));
  if (content?.closing_message) parts.push(content.closing_message);
  return parts.join("\n\n");
}

/** 5 "voces" distintas para los mensajes automáticos (feedback y plan): mismo
 *  tono profesional y misma estructura (así la INFO del cliente siempre va
 *  completa), pero cambian el saludo, la entrada, el cierre de frase y la
 *  despedida. Se reparten entre clientes (y varían entre revisiones) para que
 *  no reciban todos siempre el mismo texto. */
interface Voice {
  greet: (name: string) => string;
  cierre: string;
  fbIntro: string;
  fbTail: string;
  planIntro: (que: string) => string;
  planTail: (adapted: boolean) => string;
  cbIntro: string;
  cbTail: string;
}

const VOICES: Voice[] = [
  {
    greet: (n) => `Hola ${n},`,
    cierre: "Cualquier duda que te surja, escríbeme por aquí y la vemos.\n\nUn saludo.",
    fbIntro: "Te envío el feedback de tu revisión quincenal, con el análisis de estas dos semanas:",
    fbTail: "Léelo con calma.",
    planIntro: (que) => `Te envío ${que}. Puedes consultarla y descargarla en PDF desde este enlace:`,
    planTail: (a) => a
      ? "Los cambios aplicados y su porqué vienen detallados en el propio documento."
      : "Revísala con calma antes de empezar.",
    cbIntro: "Te envío el cierre completo de tu revisión quincenal: el feedback de estas dos semanas y tu planificación.",
    cbTail: "Léelo todo con calma.",
  },
  {
    greet: (n) => `¡Hola ${n}!`,
    cierre: "Si te queda cualquier duda, me escribes por aquí sin problema.\n\nUn abrazo.",
    fbIntro: "Aquí tienes el resumen de estas dos semanas: he revisado tus datos y te dejo el análisis y los ajustes.",
    fbTail: "Cuéntame qué te parece.",
    planIntro: (que) => `Aquí tienes ${que}. La puedes ver y descargar en PDF en este enlace:`,
    planTail: (a) => a
      ? "En el documento tienes los cambios y el porqué de cada uno."
      : "Échale un ojo con calma antes de arrancar.",
    cbIntro: "Cerramos la quincena: te dejo el feedback de estas dos semanas junto con tu planificación.",
    cbTail: "Míralo todo con calma.",
  },
  {
    greet: (n) => `Buenas ${n},`,
    cierre: "Para cualquier cosa que necesites, aquí me tienes.\n\nUn saludo.",
    fbIntro: "Ya tengo lista la valoración de tu quincena. Te la detallo a continuación:",
    fbTail: "Revísala con tranquilidad.",
    planIntro: (que) => `Te comparto ${que}. Disponible para consultar y descargar en PDF aquí:`,
    planTail: (a) => a
      ? "Los ajustes realizados y su justificación están recogidos en el propio PDF."
      : "Léela con calma antes de empezar.",
    cbIntro: "Te paso el cierre de tu revisión quincenal: la valoración de estas dos semanas y tu nueva planificación.",
    cbTail: "Revísalo todo con tranquilidad.",
  },
  {
    greet: (n) => `${n}, ¿qué tal?`,
    cierre: "Cualquier cosa que no veas clara, me lo dices y lo ajustamos.\n\nUn saludo grande.",
    fbIntro: "Toca revisión quincenal. He mirado cómo ha ido todo y esto es lo que veo:",
    fbTail: "Lo comentamos si quieres.",
    planIntro: (que) => `Te mando ${que}. La tienes para ver y descargar en PDF en este enlace:`,
    planTail: (a) => a
      ? "Dentro del documento te explico qué he cambiado y por qué."
      : "Dale un repaso con calma antes de ponerte.",
    cbIntro: "Cerramos estas dos semanas: te dejo el feedback y, con él, tu planificación.",
    cbTail: "Repásalo todo con calma.",
  },
  {
    greet: (n) => `Hola de nuevo, ${n},`,
    cierre: "Si surge alguna duda, hablamos por aquí cuando quieras.\n\nÁnimo y a por ello.",
    fbIntro: "Te comparto la valoración de esta quincena, con lo conseguido y lo que ajustamos de cara a las próximas semanas:",
    fbTail: "Tómate un momento para leerlo.",
    planIntro: (que) => `Te hago llegar ${que}. Puedes consultarla y descargarla en PDF desde aquí:`,
    planTail: (a) => a
      ? "Todos los cambios y su motivo quedan explicados en el documento."
      : "Léela con calma antes de empezar la etapa.",
    cbIntro: "Cerramos la quincena con todo: el feedback de estas dos semanas y tu planificación actualizada.",
    cbTail: "Léelo con calma.",
  },
];

/** Elige una de las 5 voces de forma estable: mezcla el nombre del cliente con
 *  un número de contexto (nº de período/mes) para que clientes distintos reciban
 *  estilos distintos y, además, varíe entre una revisión y la siguiente. */
function pickVoice(fullName: string, extra = 0): Voice {
  let s = 0;
  const name = fullName ?? "";
  for (let i = 0; i < name.length; i++) s = (s + name.charCodeAt(i)) % 100000;
  const e = Number.isFinite(extra) ? Math.trunc(Math.abs(extra)) : 0;
  return VOICES[(s + e) % VOICES.length];
}

/** Mensaje para PROPONER la videollamada de revisión (paquete Pro): saludo +
 *  propuesta directa. Con enlace de reservas (Google Calendar/Meet, Calendly…)
 *  el cliente elige día y hora él mismo; sin él, se acuerda en la conversación. */
export function videoCallMessage(fullName: string, meetUrl?: string | null): string {
  const cita = meetUrl
    ? `Elige el día y la hora que mejor te vengan desde este enlace de reservas:\n${meetUrl}`
    : "¿Qué día y hora te vienen bien esta semana? Te paso el enlace en cuanto lo cerremos.";
  return [
    `Hola ${waFirstName(fullName)},`,
    "Como parte de tu acompañamiento, vamos a hacer una videollamada de revisión "
    + "para repasar tu progreso, resolver dudas y ajustar lo que haga falta.",
    cita,
    "Un saludo.",
  ].join("\n\n");
}

/** Mensaje para AVISAR de la videollamada YA agendada con Google Meet: fecha,
 *  hora y enlace de Meet directo. Se usa desde el botón "Enviar por WhatsApp"
 *  cuando la cita ya está creada (además del email y la invitación de Google). */
export function videoCallScheduledMessage(
  fullName: string, whenLabel: string, meetUrl: string,
): string {
  return [
    `Hola ${waFirstName(fullName)},`,
    `Te confirmo tu videollamada de revisión: ${whenLabel}.`,
    `Nos vemos en Google Meet, puedes unirte desde aquí:\n${meetUrl}`,
    "Te llegará también la invitación a tu Google Calendar con recordatorios. Un saludo.",
  ].join("\n\n");
}

/** Mensaje de ARRANQUE (alta manual): pagar el plan + rellenar la anamnesis
 *  (página del PDF editable), con la instrucción EN MAYÚSCULAS de enviarla
 *  rellena. Un solo mensaje. */
export function onboardingMessage(
  fullName: string, planLabel: string, payUrl: string, anamnesisUrl: string,
): string {
  return [
    `Hola ${waFirstName(fullName)},`,
    "Para empezar tu asesoría necesito dos cosas:",
    `1) Realiza el pago de tu plan (${planLabel}) desde este enlace:\n${payUrl}`,
    `2) Descarga tu cuestionario inicial (anamnesis), réllenalo y súbelo desde este enlace:\n${anamnesisUrl}`,
    "IMPORTANTE: RELLENA Y ENVÍAME TU ANAMNESIS COMPLETA PARA QUE PUEDA PREPARARTE EL PLAN.",
    "Un saludo.",
  ].join("\n\n");
}

/** Mensaje de AJUSTE MANUAL de la planificación: explica exactamente qué se
 *  cambió (lista del diff detectado al editar) + enlace al PDF actualizado. */
export function manualUpdateMessage(
  fullName: string, items: string[], pdfUrl: string,
): string {
  const lista = items.map((i) => `- ${i}`).join("\n");
  return [
    `Hola ${waFirstName(fullName)},`,
    "He hecho unos ajustes en tu planificación para que siga siendo la óptima para ti. En concreto:",
    lista,
    `El resto se mantiene igual. Tienes tu plan ya actualizado aquí:\n${pdfUrl}`,
    "Cualquier duda me dices. Un saludo.",
  ].join("\n\n");
}

/** Mensaje del feedback quincenal: entrada + informe + cierre profesional.
 *  `periodIndex` hace que la voz varíe entre una revisión y la siguiente. */
export function feedbackMessage(fullName: string, content: any, periodIndex = 0): string {
  const v = pickVoice(fullName, periodIndex);
  return [
    v.greet(waFirstName(fullName)),
    v.fbIntro,
    feedbackBody(content, { bold: true }),
    `${v.fbTail} ${v.cierre}`,
  ].join("\n\n");
}

/** Mensaje de acceso al PORTAL del cliente (su app): saludo + enlace directo.
 *  Es el enlace de la web del cliente, donde primero rellena la anamnesis y
 *  luego hace el seguimiento y ve su planificación. */
export function portalAccessMessage(fullName: string, portalUrl: string): string {
  return [
    `Hola ${waFirstName(fullName)},`,
    "Te doy acceso a tu portal, tu espacio para el seguimiento del día a día y para ver tu planificación. Ábrelo desde este enlace y guárdalo en tu móvil:",
    portalUrl,
    `Nada más entrar, completa tu cuestionario inicial para que pueda prepararte el plan. ${CIERRE}`,
  ].join("\n\n");
}

/** Mensaje de la planificación (original o adaptada) con su enlace al PDF.
 *  La voz varía según el cliente y el mes/adaptación. */
export function planMessage(
  fullName: string,
  pdfUrl: string,
  adaptedIdx: number | null,
  monthIndex: number,
): string {
  const v = pickVoice(fullName, monthIndex + (adaptedIdx ?? 0));
  const que = adaptedIdx != null
    ? `tu planificación actualizada tras la revisión #${adaptedIdx}`
    : `tu planificación del mes ${monthIndex}`;
  return [
    v.greet(waFirstName(fullName)),
    v.planIntro(que),
    pdfUrl,
    `${v.planTail(adaptedIdx != null)} ${v.cierre}`,
  ].join("\n\n");
}

/** Mensaje conjunto: feedback de la quincena + planificación con su PDF. */
export function planAndFeedbackMessage(
  fullName: string,
  content: any,
  pdfUrl: string,
  adaptedIdx: number | null,
): string {
  const v = pickVoice(fullName, (adaptedIdx ?? 0) + 1);
  return [
    v.greet(waFirstName(fullName)),
    v.cbIntro,
    "*Feedback de la quincena*",
    feedbackBody(content, { bold: true }),
    adaptedIdx != null
      ? `*Tu planificación (actualizada tras la revisión #${adaptedIdx})*`
      : "*Tu planificación*",
    `Puedes consultarla y descargarla en PDF desde este enlace:\n${pdfUrl}`,
    `${v.cbTail} ${v.cierre}`,
  ].join("\n\n");
}
