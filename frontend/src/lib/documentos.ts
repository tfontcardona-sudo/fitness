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
