import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Copy, Search, UserPlus, ChevronRight, Flag } from "lucide-react";
import { useDismiss, useModalFocus } from "../lib/useDismiss";
import { api, ApiError } from "../lib/api";
import type { ClientOut, PortalLinkOut } from "../types";
import { EmptyState, PageLoader, StatusBadge, useToast } from "../components/ui";
import { Avatar } from "./DashboardPage";
import { GOAL_LABEL, goalReviewDue, relativeDays } from "../lib/format";

/** CARPETAS de la cartera según el punto del ciclo (no solo el estado crudo):
 *  Activos = planificación publicada · Pendientes = aún sin planificación
 *  (solo anamnesis / alta) · Revisión pendiente = quincenal subida (con su nº)
 *  · Objetivo 45 días = toca valorar cambio (sale de la carpeta al mantener). */
type Category = "all" | "activos" | "pendientes" | "revision" | "objetivo" | "inactivos";
const CATEGORIES: { id: Category; label: string }[] = [
  { id: "all", label: "Todos" },
  { id: "activos", label: "Activos" },
  { id: "pendientes", label: "Pendientes" },
  { id: "revision", label: "Revisión pendiente" },
  { id: "objetivo", label: "Objetivo 45 días" },
  { id: "inactivos", label: "Inactivos" },
];

function inCategory(c: ClientOut, cat: Category): boolean {
  switch (cat) {
    case "all": return true;
    case "activos": return !!c.has_published_plan && c.status !== "inactive" && c.status !== "review_pending";
    case "pendientes": return !c.has_published_plan && c.status !== "inactive";
    case "revision": return c.status === "review_pending";
    case "objetivo": return goalReviewDue(c) != null && c.status !== "inactive";
    case "inactivos": return c.status === "inactive";
  }
}

export default function ClientsPage() {
  const [params, setParams] = useSearchParams();
  const [clients, setClients] = useState<ClientOut[] | null>(null);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<Category>("all");
  const [showNew, setShowNew] = useState(params.get("nuevo") === "1");

  const load = useCallback(() => {
    api
      .listClients({ q: q.length >= 2 ? q : undefined })
      .then(setClients)
      .catch(() => setClients([]));
  }, [q]);

  useEffect(() => {
    const t = setTimeout(load, 200); // debounce de la búsqueda
    return () => clearTimeout(t);
  }, [load]);

  // Refresco cada 30 s (pestaña visible): carpetas y badges siempre al día
  useEffect(() => {
    const t = window.setInterval(() => {
      if (!document.hidden) load();
    }, 30000);
    return () => window.clearInterval(t);
  }, [load]);

  const counts = useMemo(() => {
    const all = clients ?? [];
    return Object.fromEntries(
      CATEGORIES.map((c) => [c.id, all.filter((x) => inCategory(x, c.id)).length]),
    ) as Record<Category, number>;
  }, [clients]);

  const visible = useMemo(
    () => (clients ?? []).filter((c) => inCategory(c, filter)),
    [clients, filter],
  );

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <header className="flex items-end justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-zinc-500">Cartera</p>
          <h1 className="mt-1 text-2xl font-semibold text-zinc-100">Clientes</h1>
        </div>
        <button className="btn btn-primary" onClick={() => setShowNew(true)}>
          <UserPlus size={16} /> Nuevo cliente
        </button>
      </header>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-600" />
          <input
            className="input pl-10"
            placeholder="Buscar por nombre o email…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="flex flex-wrap gap-1.5">
          {CATEGORIES.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setFilter(id)}
              className="tap rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
              style={
                filter === id
                  ? { background: "var(--brand-accent)", color: "#221407" }
                  : { background: "var(--surface)", color: "var(--text-dim)" }
              }
            >
              {label}
              {clients !== null && counts[id] > 0 && (
                <span className="ml-1 opacity-70">{counts[id]}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-5">
        {clients === null ? (
          <PageLoader />
        ) : visible.length === 0 ? (
          <EmptyState
            title={filter === "all" ? "Sin clientes que mostrar" : "Nada en esta carpeta"}
            hint={
              filter === "all"
                ? "Da de alta tu primer cliente para generarle el enlace de anamnesis."
                : "Cuando un cliente esté en este punto del ciclo aparecerá aquí."
            }
            action={
              filter === "all" ? (
                <button className="btn btn-primary" onClick={() => setShowNew(true)}>
                  <UserPlus size={16} /> Nuevo cliente
                </button>
              ) : undefined
            }
          />
        ) : (
          <>
            {/* Tabla en pantallas medianas/grandes; TARJETAS en el móvil */}
            <div className="hidden sm:block">
              <ClientsTable clients={visible} />
            </div>
            <div className="space-y-2 sm:hidden">
              {visible.map((c) => (
                <ClientCard key={c.id} c={c} />
              ))}
            </div>
          </>
        )}
      </div>

      {showNew && (
        <NewClientModal
          onClose={() => {
            setShowNew(false);
            params.delete("nuevo");
            setParams(params, { replace: true });
          }}
          onCreated={load}
        />
      )}
    </div>
  );
}

/** Estado con contexto del ciclo: nº de revisión pendiente y aviso de objetivo. */
function CycleBadges({ c }: { c: ClientOut }) {
  const due = goalReviewDue(c);
  const reviewIdx = c.review_period_index ?? c.pending_review_period;
  return (
    <span className="flex flex-wrap items-center gap-1.5">
      {c.status === "review_pending" && reviewIdx != null ? (
        <span
          className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium"
          style={{ background: "rgba(123,79,201,0.14)", color: "#7B4FC9" }}
        >
          <span className="pulse-dot h-1.5 w-1.5 rounded-full" style={{ background: "#7B4FC9" }} />
          Revisión #{reviewIdx} pendiente
        </span>
      ) : (
        <StatusBadge status={c.status} />
      )}
      {due != null && c.status !== "inactive" && (
        <span
          className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium"
          style={{ background: "color-mix(in srgb, var(--brand-accent-2) 14%, transparent)", color: "var(--brand-accent-2)" }}
          title={`${due} días con el mismo objetivo: valora si toca cambiarlo`}
        >
          <Flag size={10} /> Objetivo · {due} d
        </span>
      )}
    </span>
  );
}

/** Tarjeta de cliente para MÓVIL: toda la fila en un solo toque cómodo. */
function ClientCard({ c }: { c: ClientOut }) {
  return (
    <Link
      to={`/clientes/${c.id}?tab=seguimiento`}
      className="card flex items-center gap-3 p-3.5 active:scale-[0.99]"
    >
      <div className="relative shrink-0">
        <Avatar name={c.full_name} size={38} />
        {c.pending_review && (
          <span
            className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold text-white shadow"
            style={{ background: "var(--brand-accent)" }}
          >
            !
          </span>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-zinc-100">{c.full_name}</p>
        <p className="truncate text-xs text-zinc-500">
          {c.goal_type ? GOAL_LABEL[c.goal_type] : "Sin objetivo aún"} · {relativeDays(c.updated_at)}
        </p>
        <div className="mt-1.5">
          <CycleBadges c={c} />
        </div>
      </div>
      <ChevronRight size={16} className="shrink-0 text-zinc-600" />
    </Link>
  );
}

function ClientsTable({ clients }: { clients: ClientOut[] }) {
  return (
    <div className="card overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wider text-zinc-500">
            <th className="px-4 py-3 font-medium">Cliente</th>
            <th className="px-4 py-3 font-medium">Objetivo</th>
            <th className="px-4 py-3 font-medium">Estado</th>
            <th className="px-4 py-3 font-medium">Actualizado</th>
          </tr>
        </thead>
        <tbody>
          {clients.map((c, i) => (
            <tr
              key={c.id}
              className="border-t transition-colors hover:bg-[var(--surface-raised)]"
              style={{ borderColor: "var(--line)", background: i % 2 ? "rgba(38,33,26,0.02)" : undefined }}
            >
              <td className="px-4 py-3">
                <Link to={`/clientes/${c.id}?tab=seguimiento`} className="flex items-center gap-3">
                  <div className="relative">
                    <Avatar name={c.full_name} size={32} />
                    {c.pending_review && (
                      <span
                        className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold text-white shadow"
                        style={{ background: "var(--brand-accent)" }}
                        title={`Revisión quincenal #${c.review_period_index ?? c.pending_review_period ?? ""} pendiente de ver`}
                      >
                        !
                      </span>
                    )}
                  </div>
                  <div>
                    <p className="font-medium text-zinc-100">{c.full_name}</p>
                    <p className="text-xs text-zinc-500">{c.email}</p>
                  </div>
                </Link>
              </td>
              <td className="px-4 py-3 text-zinc-400">
                {c.goal_type ? GOAL_LABEL[c.goal_type] : <span className="text-zinc-600">—</span>}
              </td>
              <td className="px-4 py-3">
                <CycleBadges c={c} />
              </td>
              <td className="px-4 py-3 text-zinc-500">{relativeDays(c.updated_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function NewClientModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const toast = useToast();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<PortalLinkOut | null>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  useDismiss(dialogRef, onClose); // fuera + ESC, en una sola pulsación
  useModalFocus(dialogRef, true); // foco atrapado; al cerrar vuelve al botón

  async function submit() {
    if (!name || !email || busy) return;
    setBusy(true);
    try {
      const res = await api.createClient({ full_name: name, email, phone: phone || null });
      setCreated(res.links);
      onCreated();
      toast.push("Cliente creado");
    } catch (e) {
      toast.push(e instanceof ApiError ? e.message : "No se pudo crear el cliente", "error");
      setBusy(false);
    }
  }

  function copy(text: string) {
    navigator.clipboard.writeText(text);
    toast.push("Enlace copiado");
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Nuevo cliente"
        className="card animate-rise w-full max-w-md p-6"
        style={{ background: "var(--surface-raised)" }}
      >
        {!created ? (
          <>
            <h3 className="text-base font-semibold text-zinc-100">Nuevo cliente</h3>
            <p className="mt-1 text-sm text-zinc-500">
              Solo necesitas nombre y email. El cliente completará su anamnesis desde el enlace.
            </p>
            <div className="mt-5 space-y-4">
              <div>
                <label className="label">Nombre completo</label>
                <input className="input" autoFocus value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div>
                <label className="label">Email</label>
                <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
              </div>
              <div>
                <label className="label">Teléfono (opcional)</label>
                <input className="input" value={phone} onChange={(e) => setPhone(e.target.value)} />
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button className="btn btn-ghost" onClick={onClose}>
                Cancelar
              </button>
              <button className="btn btn-primary" disabled={busy || !name || !email} onClick={submit}>
                Crear cliente
              </button>
            </div>
          </>
        ) : (
          <>
            <h3 className="text-base font-semibold text-zinc-100">Cliente creado</h3>
            <p className="mt-1 text-sm text-zinc-500">
              Envía este enlace al cliente para que complete su anamnesis y consentimiento.
            </p>
            <div className="mt-4 flex items-center gap-2 rounded-xl border p-3" style={{ borderColor: "var(--line-strong)" }}>
              <code className="flex-1 truncate text-xs text-zinc-300">{created.anamnesis_url}</code>
              <button className="btn btn-ghost px-2.5 py-1.5" onClick={() => copy(created.anamnesis_url)}>
                <Copy size={14} />
              </button>
            </div>
            <div className="mt-6 flex justify-end">
              <button className="btn btn-primary" onClick={onClose}>
                Hecho
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
