import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Library,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Users,
  Wallet,
} from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { useBrand } from "../hooks/useBrand";
import { ALERTS_REFRESH_MS, api } from "../lib/api";
import { useAppUpdate } from "../lib/appUpdate";
import { AlertsBell } from "./AlertsBell";
import { PinDock } from "./Pins";
import { activarAcordeon } from "../lib/accordion";
import { AiCreditButton } from "./AiCreditButton";

const NAV = [
  { to: "/", label: "Hoy", icon: LayoutDashboard, end: true },
  { to: "/clientes", label: "Clientes", icon: Users, end: false },
  { to: "/pagos", label: "Pagos", icon: Wallet, end: false },
  { to: "/recursos", label: "Recursos", icon: Library, end: false },
];

/** Cobros SIN LEER: el numerito rojo de "Pagos", como el del banco. Se apaga
 *  solo al abrir la pantalla (que los sella). Se recalcula al navegar y de
 *  fondo cada 20 s — el dato es ligero (un COUNT), pero un cobro no es algo
 *  que cambie segundo a segundo. */
function usePagosSinLeer(): number {
  const [sinLeer, setSinLeer] = useState(0);
  const location = useLocation();
  useEffect(() => {
    let vivo = true;
    const leer = () => {
      if (document.hidden) return;
      api.paymentsSummary()
        .then((s) => { if (vivo) setSinLeer(s.unseen); })
        .catch(() => {});
    };
    leer();
    const t = window.setInterval(leer, ALERTS_REFRESH_MS);
    return () => { vivo = false; window.clearInterval(t); };
  }, [location.pathname]);
  return sinLeer;
}

/** Numerito del menú (99+ como tope para no romper el ancho). */
function NavBadge({ count }: { count: number }) {
  if (count <= 0) return null;
  return (
    <span
      className="ml-auto rounded-full px-1.5 py-0.5 text-[10px] font-bold leading-none text-white"
      style={{ background: "#C2453A" }}
    >
      {count > 99 ? "99+" : count}
    </span>
  );
}

/** ¿Pantalla de móvil? (reactiva al girar el dispositivo) */
function useIsMobile(): boolean {
  const [mobile, setMobile] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(max-width: 767px)").matches,
  );
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    const on = () => setMobile(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return mobile;
}

export default function AppShell() {
  // Abrir un desplegable cierra el hermano abierto: la pantalla no se ensucia.
  useEffect(activarAcordeon, []);
  const { user, logout } = useAuth();
  const { brand } = useBrand();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const pagosSinLeer = usePagosSinLeer();
  // Versión nueva desplegada: el panel se pone al día solo al volver del
  // segundo plano, o con un toque si el coach está trabajando (mismo
  // mecanismo que el portal del cliente — nadie reinstala nada).
  const update = useAppUpdate();
  const updateBanner = update.ready ? (
    <button
      onClick={update.apply}
      className="fixed inset-x-0 top-2 z-50 mx-auto flex w-fit items-center gap-2 rounded-full px-4 py-2 text-xs font-semibold text-white shadow-lg"
      style={{ background: "var(--brand-accent)" }}
    >
      ✨ Panel actualizado — toca para recargar
    </button>
  ) : null;
  // Barra lateral inteligente: en móvil arranca contraída (pantalla estrecha).
  const [collapsed, setCollapsed] = useState(
    () => typeof window !== "undefined" && window.innerWidth < 768,
  );

  // ---- MÓVIL: sin sidebar — navegación inferior tipo app (como el portal) ----
  if (isMobile) {
    return (
      <div className="flex h-screen flex-col overflow-hidden">
        <main className="coach-mobile relative flex-1 overflow-y-auto pb-24" style={{ background: "var(--bg)" }}>
          {updateBanner}
          <AlertsBell />
          <PinDock />
          <Outlet />
        </main>
        <nav
          className="coach-bottom-nav fixed inset-x-0 bottom-0 z-40 flex justify-around border-t px-2 py-1.5"
          style={{ background: "var(--surface)", borderColor: "var(--line)" }}
        >
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className="tap relative flex flex-1 flex-col items-center gap-0.5 rounded-xl py-1.5 text-[11px] font-medium"
              style={({ isActive }) => ({ color: isActive ? "var(--brand-accent)" : "var(--text-faint)" })}
            >
              <span className="relative">
                <Icon size={20} />
                {/* Cobros sin leer sobre el icono (en móvil no cabe el numerito
                    al lado de la etiqueta). */}
                {to === "/pagos" && pagosSinLeer > 0 && (
                  <span
                    className="absolute -right-2 -top-1 rounded-full px-1 text-[9px] font-bold leading-tight text-white"
                    style={{ background: "#C2453A" }}
                  >
                    {pagosSinLeer > 9 ? "9+" : pagosSinLeer}
                  </span>
                )}
              </span>
              {label}
            </NavLink>
          ))}
          <button
            onClick={() => { logout(); navigate("/"); }}
            className="tap flex flex-1 flex-col items-center gap-0.5 rounded-xl py-1.5 text-[11px] font-medium"
            style={{ color: "var(--text-faint)" }}
          >
            <LogOut size={20} />
            Salir
          </button>
        </nav>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar colapsable e INTELIGENTE:
          - contraída + pulsar la franja → se despliega (y si tocas un icono,
            además navega: una sola pulsación hace las dos cosas);
          - desplegada + pulsar el contenido de la derecha → se contrae sola. */}
      <aside
        onClick={collapsed ? () => setCollapsed(false) : undefined}
        title={collapsed ? "Desplegar menú" : undefined}
        className={`flex flex-col border-r transition-all duration-200 ${collapsed ? "cursor-pointer" : ""}`}
        style={{ borderColor: "var(--line)", width: collapsed ? 64 : 232, background: "var(--surface)" }}
      >
        <div className="flex h-16 items-center gap-3 border-b px-4" style={{ borderColor: "var(--line)" }}>
          <img src="/dq-logo.png" alt="DQ" className="h-8 w-auto shrink-0 rounded-md" />
          {!collapsed && (
            <span className="truncate text-sm font-semibold tracking-wide text-zinc-100">
              {brand?.name ?? "Asesorías"}
            </span>
          )}
        </div>

        <nav className="mt-2 flex-1 space-y-1 px-2.5">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              // Contraído solo se ve el icono: el title dice a dónde lleva.
              title={collapsed ? label : undefined}
              aria-label={label}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive ? "text-zinc-100" : "text-zinc-500 hover:text-zinc-200"
                }`
              }
              style={({ isActive }) =>
                isActive
                  ? { background: "var(--surface-raised)", boxShadow: "inset 2px 0 0 var(--brand-accent)" }
                  : undefined
              }
            >
              <span className="relative shrink-0">
                <Icon size={18} />
                {/* Con el menú contraído no hay sitio para el número: un punto
                    basta para saber que hay cobros sin ver. */}
                {to === "/pagos" && collapsed && pagosSinLeer > 0 && (
                  <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full"
                        title={`${pagosSinLeer} cobro${pagosSinLeer === 1 ? "" : "s"} sin ver`}
                        style={{ background: "#C2453A" }} />
                )}
              </span>
              {!collapsed && <span>{label}</span>}
              {!collapsed && to === "/pagos" && <NavBadge count={pagosSinLeer} />}
            </NavLink>
          ))}
          {/* Créditos de la API de Anthropic: saldo restante + recarga */}
          <AiCreditButton collapsed={collapsed} />
        </nav>

        <div className="border-t p-2.5" style={{ borderColor: "var(--line)" }}>
          <button
            onClick={() => setCollapsed((c) => !c)}
            aria-label={collapsed ? "Desplegar menú" : "Contraer menú"}
            className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-zinc-500 hover:text-zinc-200"
          >
            {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
            {!collapsed && <span>Contraer</span>}
          </button>
          <button
            onClick={() => {
              logout();
              navigate("/");
            }}
            aria-label="Salir"
            title={collapsed ? "Salir" : undefined}
            className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-zinc-500 hover:text-zinc-200"
          >
            <LogOut size={18} />
            {!collapsed && <span className="truncate">Salir ({user?.username})</span>}
          </button>
        </div>
      </aside>

      <main
        onClick={!collapsed ? () => setCollapsed(true) : undefined}
        className="relative flex-1 overflow-y-auto"
        style={{ background: "var(--bg)" }}
      >
        {updateBanner}
        {/* Centro de alertas: preventivo, se autolimpia al resolver acciones */}
        <AlertsBell />
        {/* Lo que ibas a arreglar: se borra solo al quedar resuelto */}
        <PinDock />
        <Outlet />
      </main>
    </div>
  );
}
