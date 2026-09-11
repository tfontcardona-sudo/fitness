import { pielDe, logoDeMarca, type Piel } from "../lib/marca";

/**
 * EL LOGO DE LA MARCA, en un solo sitio.
 *
 * Había NUEVE pantallas con `/dq-logo.png` escrito a mano —login, pantalla de
 * error, /dq, /planes, /oferta, el login del portal, el portal, el
 * cuestionario—, así que el cliente de Professional veía el logo de DQ en casi
 * todas partes. Ahora todas preguntan aquí.
 *
 * Si la marca tiene un logo SUBIDO (Recursos → Marca), se pinta ese. Si no, se
 * pinta su MARCA TIPOGRÁFICA: el nombre compuesto con la tipografía y el color
 * de la marca. Es lo mismo que hace ya el documento del plan de Professional
 * («PROFESSIONAL» en dorado) y es la única salida honesta — el logo de un
 * negocio no se puede inventar, pero el del OTRO negocio no puede salir ahí.
 *
 * ⚠️ Cuando el dueño suba el logo de Professional (Recursos → Marca → logo),
 * esta marca tipográfica desaparece sola en todas las pantallas a la vez.
 */
export default function MarcaLogo({
  logoUrl, skin, nombre, alto = 40, className = "",
}: {
  /** `logo_url` que da el backend (ya servible). */
  logoUrl?: string | null;
  /** `skin` de la marca. */
  skin?: string | null;
  /** Nombre de la marca, para el texto alternativo. */
  nombre?: string | null;
  /** Alto en píxeles. La marca tipográfica se escala con él. */
  alto?: number;
  className?: string;
}) {
  const piel: Piel = pielDe(skin);
  const src = logoDeMarca(logoUrl, piel);

  if (src) {
    return (
      <img src={src} alt={nombre || ""} className={className}
        style={{ height: alto, width: "auto", objectFit: "contain" }} />
    );
  }
  return <MarcaTipografica piel={piel} nombre={nombre} alto={alto} className={className} />;
}

/** La marca escrita. Un rótulo, no un dibujo: letra ancha, filete y bajada. */
function MarcaTipografica({ piel, nombre, alto, className }: {
  piel: Piel; nombre?: string | null; alto: number; className?: string;
}) {
  // El rótulo de Professional es su nombre corto en versales espaciadas: es
  // exactamente lo que imprime su documento, así que app y papel dicen lo
  // mismo. Para cualquier otra marca sin logo, su propio nombre.
  const rotulo = piel === "professional" ? "PROFESSIONAL" : (nombre || "").toUpperCase();
  const color = piel === "professional" ? "var(--pf-oro, #C9A227)" : "var(--brand-accent)";
  return (
    <span className={`marca-rotulo ${className}`} aria-label={nombre || rotulo}
      style={{ height: alto, fontSize: Math.max(12, Math.round(alto * 0.4)), color }}>
      {rotulo}
    </span>
  );
}
