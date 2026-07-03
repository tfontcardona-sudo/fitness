import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Copy, Search, UserPlus, AlertCircle } from "lucide-react";
import { api, ApiError } from "../lib/api";
import type { ClientOut, ClientStatus, PortalLinkOut } from "../types";
import { EmptyState, PageLoader, StatusBadge, useToast } from "../components/ui";
import { Avatar } from "./DashboardPage";
import { GOAL_LABEL, relativeDays, STATUS_LABEL } from "../lib/format";

const STATUS_FILTERS: (ClientStatus | "all")[] = [
  "all", "active", "at_risk", "review_pending", "awaiting_feedback", "onboarding", "inactive",
];

export default function ClientsPage() {
  const [params, setParams] = useSearchParams();
  const [clients, setClients] = useState<ClientOut[] | null>(null);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<ClientStatus | "all">("all");
  const [showNew, setShowNew] = useState(params.get("nuevo") === "1");

  const load = useCallback(() => {
    api
      .listClients({
        status: filter === "all" ? undefined : filter,
        q: q.length >= 2 ? q : undefined,
      })
      .then(setClients)
      .catch(() => setClients([]));
  }, [filter, q]);

  useEffect(() => {
    const t = setTimeout(load, 200); // debounce de la búsqueda
    return () => clearTimeout(t);
  }, [load]);

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
          {STATUS_FILTERS.map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className="rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
              style={
                filter === s
                  ? { background: "var(--brand-accent)", color: "#0a0a0f" }
                  : { background: "var(--surface)", color: "var(--text-dim)" }
              }
            >
              {s === "all" ? "Todos" : STATUS_LABEL[s]}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-5">
        {clients === null ? (
          <PageLoader />
        ) : clients.length === 0 ? (
          <EmptyState
            title="Sin clientes que mostrar"
            hint="Da de alta tu primer cliente para generarle el enlace de anamnesis."
            action={
              <button className="btn btn-primary" onClick={() => setShowNew(true)}>
                <UserPlus size={16} /> Nuevo cliente
              </button>
            }
          />
        ) : (
          <ClientsTable clients={clients} />
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
              style={{ borderColor: "var(--line)", background: i % 2 ? "rgba(255,255,255,0.012)" : undefined }}
            >
              <td className="px-4 py-3">
                <Link to={`/clientes/${c.id}?tab=seguimiento`} className="flex items-center gap-3">
                  <div className="relative">
                    <Avatar name={c.full_name} size={32} />
                    {c.pending_review && (
                      <span
                        className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold text-white shadow"
                        style={{ background: "var(--brand-primary, #8B1A2B)" }}
                        title={`Revisión quincenal #${c.pending_review_period ?? ""} pendiente de ver`}
                      >
                        !
                      </span>
                    )}
                  </div>
                  <div>
                    <p className="flex items-center gap-1.5 font-medium text-zinc-100">
                      {c.full_name}
                      {c.pending_review && (
                        <span
                          className="inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-semibold"
                          style={{ background: "rgba(139,26,43,0.15)", color: "var(--brand-primary, #C0455A)" }}
                        >
                          <AlertCircle size={10} /> Revisión #{c.pending_review_period}
                        </span>
                      )}
                    </p>
                    <p className="text-xs text-zinc-500">{c.email}</p>
                  </div>
                </Link>
              </td>
              <td className="px-4 py-3 text-zinc-400">
                {c.goal_type ? GOAL_LABEL[c.goal_type] : <span className="text-zinc-600">—</span>}
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={c.status} />
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div
        className="card animate-rise w-full max-w-md p-6"
        style={{ background: "var(--surface-raised)" }}
        onClick={(e) => e.stopPropagation()}
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
