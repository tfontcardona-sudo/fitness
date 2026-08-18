/** Texto plano del informe del cliente — para el botón "Copiar todo" de la
 *  pestaña Feedback. Las mismas secciones que se ven en pantalla, en el mismo
 *  orden, listas para pegar donde haga falta. */

/** Cuerpo del feedback (mismas secciones que la pestaña Feedback). */
export function feedbackBody(content: any): string {
  const parts: string[] = [];
  if (content?.natural_analysis) parts.push(content.natural_analysis);
  if (Array.isArray(content?.changes_bullets) && content.changes_bullets.length)
    parts.push("Cambios en el plan:\n" + content.changes_bullets.map((x: string) => `• ${x}`).join("\n"));
  if (content?.answers) parts.push("Respuesta a tus dudas:\n" + content.answers);
  if (Array.isArray(content?.next_objectives) && content.next_objectives.length)
    parts.push("Próximos objetivos:\n" + content.next_objectives.map((x: string) => `• ${x}`).join("\n"));
  if (content?.closing_message) parts.push(content.closing_message);
  return parts.join("\n\n");
}
