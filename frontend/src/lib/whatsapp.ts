/** Envío por WhatsApp con un clic (wa.me): feedback y plan del cliente. */

/** Normaliza un teléfono a formato wa.me (dígitos con prefijo de país).
 *  9 dígitos → se asume España (+34). Devuelve null si no hay teléfono. */
export function waPhone(phone: string | null | undefined): string | null {
  const digits = (phone ?? "").replace(/\D/g, "");
  if (!digits) return null;
  return digits.length === 9 ? `34${digits}` : digits;
}

/** Abre WhatsApp con el texto ya escrito para ese número. */
export function openWhatsApp(phoneDigits: string, text: string): void {
  window.open(
    `https://wa.me/${phoneDigits}?text=${encodeURIComponent(text)}`,
    "_blank",
    "noopener",
  );
}
