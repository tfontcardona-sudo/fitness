/**
 * Formatos que admite el lector universal de documentos del backend.
 *
 * Una sola verdad para TODOS los inputs de fichero (anamnesis, adjuntos,
 * importar plan desde documento, página pública del cliente): el backend
 * valida por la magia del archivo, así que aquí solo se orienta al selector
 * del navegador y se explica en humano qué se puede subir.
 */
export const ACEPTA_DOCUMENTOS = ".pdf,.docx,.doc,.odt,.rtf,.txt,.md,.csv,.xlsx,image/*";

export const FORMATOS_HUMANOS = "PDF, Word, fotos, Excel o texto";

/** Una verificación de la lectura (2º pase) con lo que hace falta para
 *  explicar la duda; espejo de `DocumentVerification` en api.ts. */
export interface DudasLectura {
  discrepancies?: string[];
  omissions?: string[];
  low_confidence_labels?: string[];
  needs_review?: boolean;
}

/** Frase corta con el POR QUÉ de la duda, por motivo. Antes se contaban solo
 *  los desajustes y con confianza baja y cero desajustes salía «no coincide en
 *  0 datos». Devuelve null si no hay dudas. */
export function resumenDudas(v: DudasLectura | null | undefined): string | null {
  if (!v?.needs_review) return null;
  const partes: string[] = [];
  const disc = v.discrepancies ?? [];
  const bajos = v.low_confidence_labels ?? [];
  const omis = v.omissions ?? [];
  if (disc.length) partes.push(`la relectura no coincide en ${disc.length} dato${disc.length === 1 ? "" : "s"}`);
  if (bajos.length) partes.push(`confianza baja en ${bajos.join(", ")}`);
  if (omis.length) partes.push(`${omis.length} dato${omis.length === 1 ? "" : "s"} que la relectura echa en falta`);
  if (!partes.length) partes.push("la relectura deja dudas en algún campo crítico");
  return partes.join(" · ");
}
