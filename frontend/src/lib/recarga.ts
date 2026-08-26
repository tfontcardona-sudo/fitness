/** Recarga de emergencia tras un despliegue.
 *
 * Cada deploy reconstruye el frontend y PURGA los assets con hash viejos. Una
 * pestaña abierta de antes que navega a una sección aún no visitada pide un
 * fichero que ya no existe → el import dinámico falla y React se quedaba EN
 * BLANCO (reproducido en la auditoría del 26-08). La cura es recargar: el
 * index.html nuevo (no-cache en Caddy) trae las URLs nuevas y todo vuelve.
 *
 * UNA sola vez por ventana de 15 s: si tras recargar sigue fallando (caída de
 * red de verdad), no podemos entrar en un bucle infinito de recargas. */
const CLAVE = "dq_recarga_emergencia";

export function recargarUnaVez(): boolean {
  try {
    const ultima = Number(sessionStorage.getItem(CLAVE) || 0);
    if (Date.now() - ultima < 15000) return false;
    sessionStorage.setItem(CLAVE, String(Date.now()));
  } catch {
    // sessionStorage bloqueado (modo privado raro): recargar igual una vez
    // por vida del módulo.
    if ((recargarUnaVez as any)._hecho) return false;
    (recargarUnaVez as any)._hecho = true;
  }
  window.location.reload();
  return true;
}

/** ¿Es el error típico de "el deploy purgó este chunk"? */
export function esErrorDeChunk(err: unknown): boolean {
  const msg = String((err as any)?.message ?? err ?? "");
  return /dynamically imported module|Importing a module script failed|Loading chunk|Failed to fetch/i.test(msg);
}
