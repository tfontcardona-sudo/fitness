import { BrowserRouter, Navigate, Route, Routes, useParams } from "react-router-dom";
import { useAuth } from "./hooks/useAuth";
import { PageLoader } from "./components/ui";
import LoginPage from "./pages/LoginPage";
import AppShell from "./components/AppShell";
import DashboardPage from "./pages/DashboardPage";
import ClientsPage from "./pages/ClientsPage";
import ClientProfilePage from "./pages/ClientProfilePage";
import RecursosPage from "./pages/RecursosPage";
import PortalApp from "./portal/PortalApp";
import PortalLogin from "./portal/PortalLogin";
import PlansPage, { PaymentOkPage } from "./pages/PlansPage";

/**
 * Raíz. El portal del cliente (login en /portal y acceso por token en /p/:token)
 * es público y se resuelve ANTES del gate de autenticación del coach; el resto
 * de rutas exigen sesión.
 */
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/portal" element={<PortalLogin />} />
        <Route path="/p/:token" element={<PortalRoute />} />
        {/* Registro personal del cliente: página pública de planes (Stripe). */}
        <Route path="/planes" element={<PlansPage />} />
        <Route path="/pago-ok" element={<PaymentOkPage />} />
        <Route path="/*" element={<CoachApp />} />
      </Routes>
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
        <Route path="recursos" element={<RecursosPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
