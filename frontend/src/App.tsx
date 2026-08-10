import { Suspense, lazy } from "react";
import { BrowserRouter, Navigate, Route, Routes, useParams } from "react-router-dom";
import { useAuth } from "./hooks/useAuth";
import { FEATURE_RESOURCES, PUBLIC_SLUG } from "./lib/branding";
import { PageLoader } from "./components/ui";
import LoginPage from "./pages/LoginPage";
import AppShell from "./components/AppShell";

// Code-splitting por ruta: el cliente del portal NO descarga el panel del
// coach (ni al revés) — el bundle único de ~940 KB penalizaba el primer
// arranque en móvil. Cada página cae en su chunk y se carga al navegar.
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const ClientsPage = lazy(() => import("./pages/ClientsPage"));
const ClientProfilePage = lazy(() => import("./pages/ClientProfilePage"));
const RecursosPage = lazy(() => import("./pages/RecursosPage"));
const PortalApp = lazy(() => import("./portal/PortalApp"));
const PortalLogin = lazy(() => import("./portal/PortalLogin"));
const PlansPage = lazy(() => import("./pages/PlansPage"));
const PaymentOkPage = lazy(() =>
  import("./pages/PlansPage").then((m) => ({ default: m.PaymentOkPage }))
);
const LinksPage = lazy(() => import("./pages/LinksPage"));
const AnamnesisPage = lazy(() => import("./pages/AnamnesisPage"));
const OfertaPage = lazy(() => import("./pages/OfertaPage"));

/**
 * Raíz. El portal del cliente (login en /portal y acceso por token en /p/:token)
 * es público y se resuelve ANTES del gate de autenticación del coach; el resto
 * de rutas exigen sesión.
 */
export default function App() {
  return (
    <BrowserRouter>
      <Suspense
        fallback={
          <div className="flex h-screen items-center justify-center">
            <PageLoader />
          </div>
        }
      >
        <Routes>
          <Route path="/portal" element={<PortalLogin />} />
          <Route path="/p/:token" element={<PortalRoute />} />
          {/* Registro personal del cliente: página pública de planes (Stripe). */}
          <Route path="/planes" element={<PlansPage />} />
          {/* Campaña story/post: primer mes del plan Full por 1 € (suscripción). */}
          <Route path="/oferta" element={<OfertaPage />} />
          <Route path="/pago-ok" element={<PaymentOkPage />} />
          {/* Link del perfil de Instagram (landing pública de enlaces). */}
          <Route path={`/${PUBLIC_SLUG}`} element={<LinksPage />} />
          {/* Anamnesis del cliente: descarga del PDF editable + subida (por token). */}
          <Route path="/anamnesis/:token" element={<AnamnesisPage />} />
          <Route path="/*" element={<CoachApp />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

function PortalRoute() {
  const { token } = useParams();
  return <PortalApp token={token!} />;
}

function CoachApp() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <PageLoader />
      </div>
    );
  }
  if (!user) return <LoginPage />;

  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="clientes" element={<ClientsPage />} />
        <Route path="clientes/:id" element={<ClientProfilePage />} />
        {/* Recursos: fuera en esta instancia (FEATURE_RESOURCES); sin la ruta,
            /recursos cae en el comodín y redirige al panel. */}
        {FEATURE_RESOURCES && <Route path="recursos" element={<RecursosPage />} />}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
