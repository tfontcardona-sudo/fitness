import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Users,
} from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { useBrand } from "../hooks/useBrand";
import { AlertsBell } from "./AlertsBell";

const NAV = [
  { to: "/", label: "Hoy", icon: LayoutDashboard, end: true },
  { to: "/clientes", label: "Clientes", icon: Users, end: false },
];

export default function AppShell() {
  const { user, logout } = useAuth();
  const { brand } = useBrand();
  const navigate = useNavigate();
  // Barra lateral inteligente: en móvil arranca contraída (pantalla estrecha).
  const [collapsed, setCollapsed] = useState(
    () => typeof window !== "undefined" && window.innerWidth < 768,
  );

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
              <Icon size={18} className="shrink-0" />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          ))}
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
        {/* Centro de alertas: preventivo, se autolimpia al resolver acciones */}
        <AlertsBell />
        <Outlet />
      </main>
    </div>
  );
}
