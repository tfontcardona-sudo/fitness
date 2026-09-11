import { lazy, Suspense, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { aplicarPiel, pielDe } from "../lib/marca";

/**
 * QUÉ CUESTIONARIO LE TOCA A ESTE CLIENTE.
 *
 * `/anamnesis/{token}` es una sola dirección para las dos marcas, pero no el
 * mismo formulario: DQR tiene el suyo y Professional el suyo (estructura,
 * preguntas y piel completamente distintas — el sistema interno sí es el
 * mismo). Lo decide la marca SELLADA en la ficha del cliente, nunca el switch
 * que el coach tenga puesto hoy: a quien ya contrató no se le cambia el
 * formulario a media inscripción.
 *
 * El único dato que se pide aquí es la variante; cada página carga después lo
 * suyo. La espera se pinta en NEGRO NEUTRO a propósito: con el fondo claro de
 * DQR, el cliente de Professional veía un fogonazo blanco antes de su
 * pantalla.
 */
const AnamnesisPage = lazy(() => import("./AnamnesisPage"));
const AnamnesisProfesional = lazy(() => import("./AnamnesisProfesional"));

export default function AnamnesisRouter() {
  const { token } = useParams();
  const [variante, setVariante] = useState<string | null>(null);

  useEffect(() => {
    let vivo = true;
    fetch(`/api/p/${token}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((st) => {
        if (!vivo) return;
        // La PIEL de la marca del cliente, en <html>: el fondo de la ventana
        // (lo que se ve al estirar de más en un iPhone) y el color de la barra
        // de estado del móvil cuelgan de ahí, no del contenedor. Sin esto, el
        // cuestionario negro del centro salía enmarcado en el crema de DQR.
        aplicarPiel(pielDe(st?.skin));
        if (st?.color_primary) {
          document.documentElement.style.setProperty("--marca-1", st.color_primary);
        }
        setVariante(String(st?.anamnesis_variant || "dq"));
      })
      // Sin respuesta (red caída, enlace roto) cae en la completa: cada página
      // vuelve a preguntar por su cuenta y enseña el error que toque.
      .catch(() => { if (vivo) setVariante("dq"); });
    return () => { vivo = false; };
  }, [token]);

  if (variante === null) return <Espera />;
  return (
    <Suspense fallback={<Espera />}>
      {variante === "professional"
        ? <AnamnesisProfesional token={token} />
        : <AnamnesisPage />}
    </Suspense>
  );
}

function Espera() {
  return <div style={{ minHeight: "100vh", background: "#151515" }} aria-busy="true" />;
}
