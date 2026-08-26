import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { AuthProvider } from "./hooks/useAuth";
import { BrandProvider } from "./hooks/useBrand";
import { ToastProvider } from "./components/ui";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { recargarUnaVez } from "./lib/recarga";
import "./index.css";

// Cada deploy purga los assets viejos: una pestaña abierta de antes que
// navega a una sección no visitada pide un chunk que ya no existe. Vite avisa
// con este evento ANTES de que el error tumbe nada: recargamos una vez y la
// versión nueva se sirve sola (la auditoría del 26-08 reprodujo la pantalla
// en blanco exactamente aquí).
window.addEventListener("vite:preloadError", (e) => {
  if (recargarUnaVez()) e.preventDefault();
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrandProvider>
        <AuthProvider>
          <ToastProvider>
            <App />
          </ToastProvider>
        </AuthProvider>
      </BrandProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
