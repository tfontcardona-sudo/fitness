import { useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import { aplicarPiel, pielDe } from "../lib/marca";
import type { LandingOut } from "../types";

export interface MarcaPublicaState {
  landing: LandingOut | null;
  /** Mensaje del coach si el modo mantenimiento está activo, o null si no. */
  mantenimiento: string | null;
}

/**
 * LA MARCA DEL ESCAPARATE, para las páginas públicas.
 *
 * /dq, /planes, /oferta y la pantalla de gracias del pago no tienen sesión ni
 * token: su marca es la ACTIVA. Cada una la pedía por su cuenta (o no la pedía
 * y pintaba la de DQ clavada), así que el switch se notaba en unas y en otras
 * no. Aquí se pide una vez, y de paso se aplica la PIEL: sin eso, la página de
 * un centro salía con el fondo crema de DQR aunque su contenido fuera negro.
 *
 * También es la única puerta por la que estas páginas saben si el coach
 * activó el MODO MANTENIMIENTO (backend: `services/mantenimiento.py`): la
 * landing responde 503 con su mensaje, y aquí se traduce a `mantenimiento`
 * para que cada pantalla pinte `<PantallaMantenimiento>` en vez de su
 * contenido normal (que ya no tendría datos con los que pintarse).
 */
export function useMarcaPublica(): MarcaPublicaState {
  const [landing, setLanding] = useState<LandingOut | null>(null);
  const [mantenimiento, setMantenimiento] = useState<string | null>(null);
  useEffect(() => {
    let vivo = true;
    api.publicLanding()
      .then((l) => {
        if (!vivo) return;
        setLanding(l);
        aplicarPiel(pielDe(l.skin));
        document.documentElement.style.setProperty("--marca-1", l.color_primary);
        document.documentElement.style.setProperty("--marca-2", l.color_secondary);
      })
      .catch((err) => {
        if (!vivo) return;
        setLanding(null);
        // Sin respuesta se queda la piel por defecto: una página sin logo es
        // mucho menos malo que una con el logo del otro negocio. Con un 503
        // del interruptor global, se guarda el mensaje del coach.
        if (err instanceof ApiError && err.status === 503) setMantenimiento(err.message);
      });
    return () => { vivo = false; };
  }, []);
  return { landing, mantenimiento };
}
