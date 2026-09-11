import React from "react";
import { esErrorDeChunk, recargarUnaVez } from "../lib/recarga";

/** Red de seguridad GLOBAL: cualquier error que tumbe el árbol de React
 *  (un chunk purgado por un deploy, un dato inesperado, un bug puntual)
 *  dejaba la pantalla EN BLANCO sin explicación. Aquí:
 *  - error de chunk → recarga automática (una vez): la versión nueva lo cura;
 *  - cualquier otro → pantalla amable con botón de recarga, nunca el vacío. */
type Estado = { error: Error | null };

export class ErrorBoundary extends React.Component<React.PropsWithChildren, Estado> {
  state: Estado = { error: null };

  static getDerivedStateFromError(error: Error): Estado {
    return { error };
  }

  componentDidCatch(error: Error) {
    if (esErrorDeChunk(error) && recargarUnaVez()) return;
  }

  render() {
    if (!this.state.error) return this.props.children;
    const esChunk = esErrorDeChunk(this.state.error);
    // La pantalla de caída también lleva la marca de quien la está mirando.
    const pf = document.documentElement.dataset.piel === "professional";
    const logo = pf ? null : "/dq-logo.png";
    const oro = "#C9A227";
    return (
      <div style={{
        minHeight: "100vh", display: "flex", alignItems: "center",
        justifyContent: "center", background: pf ? "#151515" : "#101014",
        color: pf ? "#F2EFE9" : "#f4f4f5",
        fontFamily: "system-ui, sans-serif", padding: 24, textAlign: "center",
      }}>
        <div style={{ maxWidth: 420 }}>
          {/* El logo lo decide la PIEL que quedó aplicada en <html>. Este
              componente envuelve a BrandProvider (tiene que sobrevivir a que
              este reviente), así que no puede preguntar por la marca con un
              hook: lee el atributo, que ya está puesto desde la carga. Y si
              la marca no tiene logo propio, su rótulo — nunca el de la otra. */}
          {logo
            ? <img src={logo} alt="" style={{ height: 44, borderRadius: 10, marginBottom: 18 }} />
            : <p style={{ height: 44, marginBottom: 18, color: oro, fontWeight: 800,
                          letterSpacing: ".16em", fontSize: 18, lineHeight: "44px" }}>
                PROFESSIONAL
              </p>}
          <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 10 }}>
            {esChunk ? "Hay una versión nueva de la aplicación" : "Algo ha fallado en esta pantalla"}
          </h1>
          <p style={{ fontSize: 15, opacity: 0.75, lineHeight: 1.5, marginBottom: 22 }}>
            {esChunk
              ? "Recarga para seguir donde estabas — tus datos están guardados en el servidor."
              : "No has perdido nada: tus datos viven en el servidor. Recarga y continúa; si se repite, avísanos."}
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              background: pf ? oro : "linear-gradient(135deg,#F6A560,#E8833A)",
              color: pf ? "#1A1405" : "#160B02",
              fontWeight: 700, fontSize: 15, border: 0, borderRadius: 12,
              padding: "12px 28px", cursor: "pointer",
            }}
          >
            Recargar la aplicación
          </button>
        </div>
      </div>
    );
  }
}
