import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, ArrowUpRight, CalendarClock, ClipboardList, UserPlus } from "lucide-react";
import { api } from "../lib/api";
import type { ClientOut } from "../types";
import { PageLoader, StatusBadge } from "../components/ui";
import { initials, relativeDays } from "../lib/format";

/**
 * Dashboard = puesto de mando. El brief pide que las acciones frecuentes estén
 * a 2 clics: por eso lo primero que ve el coach son las COLAS DE ACCIÓN
 * (clientes en riesgo y revisiones pendientes), no métricas decorativas.
 */
export default function DashboardPage() {
  const [clients, setClients] = useState<ClientOut[] | null>(null);

  useEffect(() => {
    api.listClients().then(setClients).catch(() => setClients([]));
  }, []);

  const groups = useMemo(() => {
    const c = clients ?? [];
    return {
      atRisk: c.filter((x) => x.status === "at_risk"),
      reviewPending: c.filter((x) => x.status === "review_pending"),
      awaiting: c.filter((x) => x.status === "awaiting_feedback"),
      onboarding: c.filter((x) => x.status === "onboarding"),
      active: c.filter((x) => x.status === "active"),
      total: c.length,
    };
  }, [clients]);

  if (clients === null) return <PageLoader />;

  const needsAttention = [...groups.atRisk, ...groups.reviewPending];

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <header className="flex items-end justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-zinc-500">Panel</p>
          <h1 className="mt-1 text-2xl font-semibold text-zinc-100">Hoy</h1>
        </div>
        <Link to="/clientes?nuevo=1" className="btn btn-primary">
          <UserPlus size={16} /> Nuevo cliente
        </Link>
      </header>

      {/* Tira de métricas: contexto, no protagonismo */}
      <div className="mt-7 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Metric label="Clientes activos" value={groups.active.length} />
        <Metric label="En riesgo" value={groups.atRisk.length} tone="#F77E7E" />
        <Metric label="Revisión pendiente" value={groups.reviewPending.length} tone="#C99EF7" />
        <Metric label="En onboarding" value={groups.onboarding.length} tone="#8B9DF7" />
      </div>

      {/* COLA DE ACCIÓN — el corazón del dashboard */}
      <section className="mt-8">
        <div className="mb-3 flex items-center gap-2">
          <AlertTriangle size={16} className="text-zinc-400" />
          <h2 className="text-sm font-semibold text-zinc-200">Requiere tu atención</h2>
        </div>

        {needsAttention.length === 0 ? (
          <div className="card p-8 text-center text-sm text-zinc-500">
            Todo en orden. No hay clientes en riesgo ni revisiones pendientes.
          </div>
        ) : (
          <div className="space-y-2">
            {needsAttention.map((c) => (
              <Link
                key={c.id}
                to={`/clientes/${c.id}`}
                className="card card-hover flex items-center justify-between p-4"
              >
                <div className="flex items-center gap-3">
                  <Avatar name={c.full_name} />
                  <div>
                    <p className="text-sm font-medium text-zinc-100">{c.full_name}</p>
                    <p className="text-xs text-zinc-500">
                      {c.status === "at_risk"
                        ? "Adherencia baja o período sin cerrar"
                        : "Cierre listo para revisar y publicar"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={c.status} />
                  <ArrowUpRight size={16} className="text-zinc-600" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Próximos cierres + onboarding pendientes en dos columnas */}
      <div className="mt-8 grid gap-5 lg:grid-cols-2">
        <Panel title="Esperando cierre" icon={CalendarClock} clients={groups.awaiting}
          emptyHint="Ningún período pendiente de cierre." />
        <Panel title="Onboarding en curso" icon={ClipboardList} clients={groups.onboarding}
          emptyHint="Ningún cliente en onboarding." />
      </div>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <div className="card p-4">
      <p className="text-2xl font-semibold" style={{ color: tone ?? "#e7e7ea" }}>
        {value}
      </p>
      <p className="mt-0.5 text-xs text-zinc-500">{label}</p>
    </div>
  );
}

function Panel({
  title,
  icon: Icon,
  clients,
  emptyHint,
}: {
  title: string;
  icon: typeof CalendarClock;
  clients: ClientOut[];
  emptyHint: string;
}) {
  return (
    <div className="card p-5">
      <div className="mb-3 flex items-center gap-2">
        <Icon size={15} className="text-zinc-400" />
        <h3 className="text-sm font-semibold text-zinc-200">{title}</h3>
        <span className="ml-auto text-xs text-zinc-600">{clients.length}</span>
      </div>
      {clients.length === 0 ? (
        <p className="py-4 text-sm text-zinc-600">{emptyHint}</p>
      ) : (
        <ul className="space-y-1">
          {clients.slice(0, 6).map((c) => (
            <li key={c.id}>
              <Link
                to={`/clientes/${c.id}`}
                className="flex items-center justify-between rounded-lg px-2 py-2 hover:bg-[var(--surface-raised)]"
              >
                <span className="flex items-center gap-2.5">
                  <Avatar name={c.full_name} size={28} />
                  <span className="text-sm text-zinc-200">{c.full_name}</span>
                </span>
                <span className="text-xs text-zinc-600">{relativeDays(c.updated_at)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function Avatar({ name, size = 34 }: { name: string; size?: number }) {
  return (
    <span
      className="flex shrink-0 items-center justify-center rounded-full text-xs font-semibold"
      style={{
        width: size,
        height: size,
        background: "var(--surface-raised)",
        color: "var(--brand-accent)",
        border: "1px solid var(--line-strong)",
      }}
    >
      {initials(name)}
    </span>
  );
}
