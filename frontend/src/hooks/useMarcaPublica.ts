import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { aplicarPiel, pielDe } from "../lib/marca";
import type { LandingOut } from "../types";

/**
 * LA MARCA DEL ESCAPARATE, para las páginas públicas.
 *
 * /dq, /planes, /oferta y la pantalla de gracias del pago no tienen sesión ni
 * token: su marca es la ACTIVA. Cada una la pedía por su cuenta (o no la pedía
 * y pintaba la de DQ clavada), así que el switch se notaba en unas y en otras
 * no. Aquí se pide una vez, y de paso se aplica la PIEL: sin eso, la página de
 * un centro salía con el fondo crema de DQR aunque su contenido fuera negro.
 */
export function useMarcaPublica(): LandingOut | null {
  const [landing, setLanding] = useState<LandingOut | null>(null);
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
      // Sin respuesta se queda la piel por defecto: una página sin logo es
      // mucho menos malo que una con el logo del otro negocio.
      .catch(() => { if (vivo) setLanding(null); });
    return () => { vivo = false; };
  }, []);
  return landing;
}
