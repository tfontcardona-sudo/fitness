/**
 * Copiar al portapapeles diciendo la VERDAD.
 *
 * El patrón que había repetido por toda la web era
 * `navigator.clipboard.writeText(x).catch(() => {})` seguido de un toast
 * "copiado" incondicional. Pero `navigator.clipboard` no existe fuera de
 * contexto seguro (el coach entrando por la IP de la red local desde la
 * tablet) y puede fallar por permisos: el coach se iba convencido de tener el
 * enlace del cliente en el portapapeles y pegaba lo que hubiera antes.
 *
 * Aquí se intenta la vía moderna, se cae a la clásica, y se devuelve si de
 * verdad se copió para que quien llama diga una cosa u otra.
 */
export async function copiar(texto: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(texto);
      return true;
    }
  } catch {
    /* sin permiso o sin contexto seguro: se prueba la vía clásica */
  }
  try {
    const ta = document.createElement("textarea");
    ta.value = texto;
    // Fuera de la vista pero enfocable: si se oculta con display:none el
    // navegador no deja seleccionar su contenido.
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    ta.style.pointerEvents = "none";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
  }
}

/** Copia y avisa: el mismo mensaje de siempre si sale bien, y uno honesto —
 *  con el texto a la vista para copiarlo a mano — si no. */
export async function copiarConAviso(
  texto: string,
  toast: { push: (m: string, tono?: "ok" | "error") => void },
  mensajeOk: string,
): Promise<void> {
  if (await copiar(texto)) {
    toast.push(mensajeOk);
    return;
  }
  toast.push("No se pudo copiar · selecciónalo a mano", "error");
  window.prompt("Copia esto a mano:", texto);
}
