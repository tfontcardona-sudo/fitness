import { useEffect, useRef, useState } from "react";

/**
 * Actualización EN CALIENTE de la app instalada (PWA) — sin reinstalar.
 *
 * El service worker no cachea assets (solo hace push), así que cada carga trae
 * la versión desplegada. El problema era la app YA ABIERTA o anclada en el
 * móvil: seguía ejecutando el JavaScript antiguo hasta que el cliente cerrara
 * y reabriera a mano — y muchos no lo hacen nunca ("tengo que borrar la app y
 * volverla a instalar" era la percepción).
 *
 * Cómo funciona: Vite fija en el index.html el nombre HASHEADO del bundle
 * (/assets/index-XXXX.js). Se re-descarga el index (no-store, unos bytes) y,
 * si ya no menciona el bundle que está corriendo, hay un deploy nuevo:
 *  - si el usuario VUELVE a la app tras ≥5 min en segundo plano, se recarga
 *    sola (momento natural: no hay nada a medio teclear);
 *  - si está usándola, se le enseña un aviso discreto para tocar y actualizar.
 *
 * En desarrollo (sin bundle hasheado) queda desactivado.
 */

/**
 * La HUELLA de la versión que está corriendo: el bundle de JavaScript Y la hoja
 * de estilos, los dos hasheados por Vite.
 *
 * ⚠️ Mirar solo el JavaScript dejaba fuera los despliegues de SOLO CSS —una
 * ronda de diseño entera, por ejemplo—: el hash del bundle no cambia, la
 * comprobación decía "no hay nada nuevo" y el cliente con la app instalada
 * seguía viendo el portal viejo hasta que la cerrara del todo. Justo lo que
 * esto existe para evitar.
 */
const HUELLA_ACTUAL: string[] = (() => {
  const out: string[] = [];
  const js = document.querySelector('script[type="module"]')?.getAttribute("src") ?? "";
  if (js.includes("/assets/")) out.push(js);
  document.querySelectorAll('link[rel="stylesheet"]').forEach((el) => {
    const href = el.getAttribute("href") ?? "";
    if (href.includes("/assets/")) out.push(href);
  });
  return out;
})();

// Tras este tiempo en segundo plano, la vuelta a la app recarga sola si hay
// versión nueva (no puede haber nada a medio escribir después de tanto rato).
const RECARGA_TRAS_OCULTO_MS = 5 * 60_000;
// Comprobación periódica con la app visible (barata: HEAD-like sobre el index).
const CHECK_MS = 30 * 60_000;

export function useAppUpdate(): { ready: boolean; apply: () => void } {
  const [ready, setReady] = useState(false);
  const ocultoDesde = useRef<number | null>(null);

  useEffect(() => {
    if (HUELLA_ACTUAL.length === 0) return;
    let vivo = true;

    const hayVersionNueva = async (): Promise<boolean> => {
      try {
        const res = await fetch("/", { cache: "no-store" });
        if (!res.ok) return false;
        const html = await res.text();
        // Basta con que UNA de las piezas haya cambiado de hash: un despliegue
        // que solo toca los estilos es un despliegue igual.
        return vivo && HUELLA_ACTUAL.some((pieza) => !html.includes(pieza));
      } catch {
        return false; // sin red: ya se comprobará a la vuelta
      }
    };

    const onVisibility = async () => {
      if (document.hidden) {
        ocultoDesde.current = Date.now();
        return;
      }
      const dormido = ocultoDesde.current !== null
        && Date.now() - ocultoDesde.current >= RECARGA_TRAS_OCULTO_MS;
      ocultoDesde.current = null;
      if (await hayVersionNueva()) {
        if (dormido) window.location.reload();
        else setReady(true);
      }
    };

    document.addEventListener("visibilitychange", onVisibility);
    const t = window.setInterval(async () => {
      if (!document.hidden && (await hayVersionNueva())) setReady(true);
    }, CHECK_MS);
    // Primera comprobación al montar (por si la pestaña lleva días abierta).
    hayVersionNueva().then((si) => { if (si) setReady(true); });

    return () => {
      vivo = false;
      document.removeEventListener("visibilitychange", onVisibility);
      window.clearInterval(t);
    };
  }, []);

  return { ready, apply: () => window.location.reload() };
}
