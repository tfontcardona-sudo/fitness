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

/** Mensaje del feedback quincenal: entrada + informe + cierre profesional. */
export function feedbackMessage(fullName: string, content: any): string {
  return [
    `Hola ${waFirstName(fullName)},`,
    "Te envío el feedback de tu revisión quincenal, con el análisis de estas dos semanas:",
    feedbackBody(content, { bold: true }),
    `Léelo con calma. ${CIERRE}`,
  ].join("\n\n");
}

/** Mensaje de la planificación (original o adaptada) con su enlace al PDF. */
export function planMessage(
  fullName: string,
  pdfUrl: string,
  adaptedIdx: number | null,
  monthIndex: number,
): string {
  const que = adaptedIdx != null
    ? `tu planificación actualizada tras la revisión #${adaptedIdx}`
    : `tu planificación del mes ${monthIndex}`;
  return [
    `Hola ${waFirstName(fullName)},`,
    `Te envío ${que}. Puedes consultarla y descargarla en PDF desde este enlace:`,
    pdfUrl,
    adaptedIdx != null
      ? `Los cambios aplicados y su porqué vienen detallados en el propio documento. ${CIERRE}`
      : `Revísala con calma antes de empezar. ${CIERRE}`,
  ].join("\n\n");
}

/** Mensaje conjunto: feedback de la quincena + planificación con su PDF. */
export function planAndFeedbackMessage(
  fullName: string,
  content: any,
  pdfUrl: string,
  adaptedIdx: number | null,
): string {
  return [
    `Hola ${waFirstName(fullName)},`,
    "Te envío el cierre completo de tu revisión quincenal: el feedback de estas dos semanas y tu planificación.",
    "*Feedback de la quincena*",
    feedbackBody(content, { bold: true }),
    adaptedIdx != null
      ? `*Tu planificación (actualizada tras la revisión #${adaptedIdx})*`
      : "*Tu planificación*",
    `Puedes consultarla y descargarla en PDF desde este enlace:\n${pdfUrl}`,
    `Léelo todo con calma. ${CIERRE}`,
  ].join("\n\n");
}
