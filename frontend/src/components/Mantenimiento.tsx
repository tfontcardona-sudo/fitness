/**
 * PANTALLA DE MANTENIMIENTO: lo que ve cualquiera que llegue a una pantalla
 * pública (portal del cliente, `/dq`, `/planes`, `/oferta`, el cuestionario)
 * mientras el coach tiene el interruptor global activado
 * (`services/mantenimiento.py` en el backend). Nunca un error crudo — el
 * backend ya lo traduce a 503 con el mensaje que el coach escribió.
 *
 * Mismo lenguaje visual que `ErrorBoundary`: sin datos de marca disponibles
 * (la landing también está cortada), así que el logo sale de la PIEL que ya
 * quedó aplicada en `<html>`, nunca de una petición que ahora mismo fallaría.
 */
export function PantallaMantenimiento({ mensaje }: { mensaje: string }) {
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
        {logo
          ? <img src={logo} alt="" style={{ height: 44, borderRadius: 10, marginBottom: 18 }} />
          : <p style={{ height: 44, marginBottom: 18, color: oro, fontWeight: 800,
                        letterSpacing: ".16em", fontSize: 18, lineHeight: "44px" }}>
              PROFESSIONAL
            </p>}
        <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 10 }}>
          No disponible por ahora
        </h1>
        <p style={{ fontSize: 15, opacity: 0.75, lineHeight: 1.5 }}>{mensaje}</p>
      </div>
    </div>
  );
}
