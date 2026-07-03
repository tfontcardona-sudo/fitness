

===== FILE: frontend/src/pages/BrandPage.tsx =====

import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { api, ApiError } from "../lib/api";
import type { BrandConfigOut, Theme } from "../types";
import { PageLoader, Spinner, useToast } from "../components/ui";
import { useBrand } from "../hooks/useBrand";

const FONTS = ["Inter", "Montserrat", "Poppins", "DM Sans", "Plus Jakarta Sans"] as const;

export default function BrandPage() {
  const toast = useToast();
  const { reload } = useBrand();
  const [brand, setBrand] = useState<BrandConfigOut | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.getBrand().then(setBrand).catch(() => setBrand(null));
  }, []);

  function set<K extends keyof BrandConfigOut>(key: K, value: BrandConfigOut[K]) {
    setBrand((b) => (b ? { ...b, [key]: value } : b));
    // Vista previa en vivo del acento
    if (key === "color_primary") {
      document.documentElement.style.setProperty("--brand-accent", value as string);
    }
  }

  async function save() {
    if (!brand || busy) return;
    setBusy(true);
    try {
      const { id, logo_path, ...payload } = brand;
      await api.updateBrand(payload);
      toast.push("Marca guardada");
      reload();
    } catch (e) {
      toast.push(e instanceof ApiError ? e.message : "No se pudo guardar", "error");
    } finally {
      setBusy(false);
    }
  }

  if (brand === null) return <PageLoader />;

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <header>
        <p className="text-xs uppercase tracking-widest text-zinc-500">Configuración</p>
        <h1 className="mt-1 text-2xl font-semibold text-zinc-100">Marca</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Se aplica en tiempo real a la app, el portal del cliente, los documentos y los emails.
        </p>
      </header>

      <div className="mt-7 grid gap-5 lg:grid-cols-[1fr_280px]">
        <div className="space-y-5">
          <div className="card p-5">
            <h3 className="mb-4 text-sm font-semibold text-zinc-200">Identidad</h3>
            <div className="space-y-4">
              <div>
                <label className="label">Nombre</label>
                <input className="input" value={brand.name} onChange={(e) => set("name", e.target.value)} />
              </div>
              <div>
                <label className="label">Tagline</label>
                <input
                  className="input"
                  value={brand.tagline ?? ""}
                  onChange={(e) => set("tagline", e.target.value || null)}
                />
              </div>
              <div>
                <label className="label">Tipografía</label>
                <select
                  className="input"
                  value={brand.font_family}
                  onChange={(e) => set("font_family", e.target.value as BrandConfigOut["font_family"])}
                >
                  {FONTS.map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="card p-5">
            <h3 className="mb-4 text-sm font-semibold text-zinc-200">Colores</h3>
            <div className="grid gap-4 sm:grid-cols-3">
              <ColorField label="Primario" value={brand.color_primary} onChange={(v) => set("color_primary", v)} />
              <ColorField label="Secundario" value={brand.color_secondary} onChange={(v) => set("color_secondary", v)} />
              <ColorField label="Fondo" value={brand.color_bg} onChange={(v) => set("color_bg", v)} />
            </div>
          </div>

          <div className="card p-5">
            <h3 className="mb-4 text-sm font-semibold text-zinc-200">Contacto</h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="label">Email</label>
                <input className="input" value={brand.contact_email ?? ""} onChange={(e) => set("contact_email", e.target.value || null)} />
              </div>
              <div>
                <label className="label">Teléfono</label>
                <input className="input" value={brand.contact_phone ?? ""} onChange={(e) => set("contact_phone", e.target.value || null)} />
              </div>
              <div>
                <label className="label">Web</label>
                <input className="input" value={brand.contact_web ?? ""} onChange={(e) => set("contact_web", e.target.value || null)} />
              </div>
            </div>
          </div>

          <div className="card p-5">
            <h3 className="mb-4 text-sm font-semibold text-zinc-200">Temas</h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <ThemeField label="Documentos" value={brand.docs_theme} onChange={(v) => set("docs_theme", v)} />
              <ThemeField label="Portal del cliente" value={brand.portal_theme} onChange={(v) => set("portal_theme", v)} />
            </div>
          </div>
        </div>

        {/* Vista previa pegajosa */}
        <div className="lg:sticky lg:top-8 lg:self-start">
          <div className="card overflow-hidden">
            <div className="px-4 pt-4 text-xs uppercase tracking-wider text-zinc-500">Vista previa</div>
            <div className="p-4">
              <div
                className="rounded-xl p-5"
                style={{ background: brand.color_bg, fontFamily: brand.font_family }}
              >
                <div
                  className="mb-3 inline-flex h-8 items-center rounded-lg px-3 text-sm font-semibold"
                  style={{ background: brand.color_primary, color: "#0a0a0f" }}
                >
                  {brand.name || "Tu marca"}
                </div>
                {brand.tagline && <p className="text-sm text-zinc-400">{brand.tagline}</p>}
                <div className="mt-3 h-1.5 w-2/3 rounded-full" style={{ background: brand.color_primary, opacity: 0.6 }} />
                <div className="mt-2 h-1.5 w-1/2 rounded-full" style={{ background: brand.color_secondary, opacity: 0.5 }} />
              </div>
            </div>
          </div>

          <button className="btn btn-primary mt-4 w-full" disabled={busy} onClick={save}>
            {busy ? <Spinner /> : <><Save size={15} /> Guardar marca</>}
          </button>
        </div>
      </div>
    </div>
  );
}

function ColorField({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="label">{label}</label>
      <div className="flex items-center gap-2 rounded-xl border p-1.5" style={{ borderColor: "var(--line-strong)" }}>
        <input
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="h-8 w-8 cursor-pointer rounded-lg border-0 bg-transparent p-0"
        />
        <input
          className="flex-1 bg-transparent text-sm text-zinc-300 outline-none"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>
    </div>
  );
}

function ThemeField({ label, value, onChange }: { label: string; value: Theme; onChange: (v: Theme) => void }) {
  return (
    <div>
      <label className="label">{label}</label>
      <div className="flex gap-2">
        {(["dark", "light"] as Theme[]).map((t) => (
          <button
            key={t}
            onClick={() => onChange(t)}
            className="flex-1 rounded-xl border px-3 py-2.5 text-sm capitalize transition-colors"
            style={
              value === t
                ? { borderColor: "var(--brand-accent)", color: "#e7e7ea" }
                : { borderColor: "var(--line-strong)", color: "var(--text-faint)" }
            }
          >
            {t === "dark" ? "Oscuro" : "Claro"}
          </button>
        ))}
      </div>
    </div>
  );
}


===== FILE: frontend/src/pages/ClientProfilePage.tsx =====

import { useCallback, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft, ExternalLink, BellRing } from "lucide-react";
import { api } from "../lib/api";
import type { ClientOut } from "../types";
import {
  ConfirmDialog,
  PageLoader,
  StatusBadge,
  useToast,
} from "../components/ui";
import { Avatar } from "./DashboardPage";
import { ClientSummaryTab } from "../components/ClientSummaryTab";
import { ClientAnamnesisTab } from "../components/ClientAnamnesisTab";
import { ClientDocuments } from "../components/ClientDocuments";
import { ClientPlanPanel } from "../components/ClientPlanPanel";
import { ClientFeedbackTab } from "../components/ClientFeedbackTab";
import { ClientHistoryTab } from "../components/ClientHistoryTab";
import { ClientTrackingTab } from "../components/ClientTrackingTab";
import { ageFrom, DIET_LABEL, GOAL_LABEL, LEVEL_LABEL, PLACE_LABEL } from "../lib/format";

type Tab = "resumen" | "anamnesis" | "planificacion" | "seguimiento" | "feedback" | "historial";

export default function ClientProfilePage() {
  const { id } = useParams();
  const clientId = Number(id);
  const toast = useToast();
  const [client, setClient] = useState<ClientOut | null>(null);
  const [searchParams] = useSearchParams();
  const initialTab = (["resumen", "anamnesis", "planificacion", "seguimiento", "feedback", "historial"] as Tab[])
    .includes(searchParams.get("tab") as Tab) ? (searchParams.get("tab") as Tab) : "resumen";
  const [tab, setTab] = useState<Tab>(initialTab);
  const [confirmRegen, setConfirmRegen] = useState(false);
  const [portalUrl, setPortalUrl] = useState<string | null>(null);

  const load = useCallback(() => {
    api.getClient(clientId).then(setClient).catch(() => setClient(null));
  }, [clientId]);

  useEffect(load, [load]);

  // Precargamos el enlace del portal con el ORIGEN actual del navegador (en dev
  // :5173, en prod el dominio) para poder abrirlo de forma síncrona (sin que el
  // navegador bloquee la pestaña) y que el enlace funcione siempre.
  useEffect(() => {
    api.portalLink(clientId)
      .then((l) => setPortalUrl(`${window.location.origin}/p/${l.portal_token}`))
      .catch(() => setPortalUrl(null));
  }, [clientId]);

  function openPortal() {
    if (!portalUrl) return;
    navigator.clipboard.writeText(portalUrl).catch(() => {});
    window.open(portalUrl, "_blank", "noopener");
    toast.push("Enlace del portal copiado y abierto");
  }

  async function regenerate() {
    if (!client) return;
    setConfirmRegen(false);
    try {
      await api.regeneratePortalToken(client.id);
      toast.push("Enlace regenerado. El anterior ya no funciona.");
    } catch {
      toast.push("No se pudo regenerar", "error");
    }
  }

  if (client === null) return <PageLoader />;

  const age = ageFrom(client.birth_date);

  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <Link to="/clientes" className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-300">
        <ArrowLeft size={15} /> Clientes
      </Link>

      {/* Notificación: el cliente cerró su período → toca generar feedback */}
      {client.status === "review_pending" && (
        <div
          className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border p-3.5"
          style={{ borderColor: "var(--brand-accent)", background: "rgba(110,231,183,0.10)" }}
        >
          <div className="flex items-center gap-2.5 text-sm text-zinc-200">
            <BellRing size={18} style={{ color: "var(--brand-accent)" }} />
            <span><b>El cliente ha cerrado su período.</b> Revisa los datos y genera el feedback.</span>
          </div>
          <button onClick={() => setTab("feedback")} className="btn btn-primary">
            Ir a Feedback
          </button>
        </div>
      )}

      <div className="mt-4 grid gap-6 lg:grid-cols-[300px_1fr]">
        {/* SIDEBAR del cliente */}
        <aside className="space-y-4">
          <div className="card p-5">
            <div className="flex items-center gap-3">
              <Avatar name={client.full_name} size={48} />
              <div className="min-w-0">
                <h1 className="truncate text-lg font-semibold text-zinc-100">{client.full_name}</h1>
                <p className="truncate text-xs text-zinc-500">{client.email}</p>
              </div>
            </div>
            <div className="mt-4">
              <StatusBadge status={client.status} />
            </div>

            <dl className="mt-5 space-y-2.5 text-sm">
              <Row label="Edad" value={age ? `${age} años` : "—"} />
              <Row label="Objetivo" value={client.goal_type ? GOAL_LABEL[client.goal_type] : "—"} />
              <Row label="Nivel" value={client.level ? LEVEL_LABEL[client.level] : "—"} />
              <Row label="Entreno" value={client.training_place ? PLACE_LABEL[client.training_place] : "—"} />
              <Row label="Dieta" value={client.diet_mode ? DIET_LABEL[client.diet_mode] : "—"} />
            </dl>
          </div>

          {/* Portal del cliente: el enlace (dosier) que rellena el cliente.
              Lo copia y lo abre para previsualizarlo. */}
          <div className="card space-y-1 p-3">
            <ActionRow icon={ExternalLink} label="Abrir / copiar enlace del portal" onClick={openPortal} />
          </div>

          {/* Anamnesis: enviar enlace + subir PDF rellenado */}
          <ClientDocuments client={client} onUploaded={load} />
        </aside>

        {/* CONTENIDO con tabs */}
        <div>
          <div className="mb-5 flex gap-1 border-b" style={{ borderColor: "var(--line)" }}>
            {(["resumen", "anamnesis", "planificacion", "seguimiento", "feedback", "historial"] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className="relative px-4 py-2.5 text-sm font-medium capitalize transition-colors"
                style={{ color: tab === t ? "#e7e7ea" : "var(--text-faint)" }}
              >
                {t === "resumen" ? "Resumen" : t === "anamnesis" ? "Anamnesis" : t === "planificacion" ? "Planificación" : t === "seguimiento" ? "Seguimiento" : t === "feedback" ? "Feedback" : "Historial"}
                {tab === t && (
                  <span
                    className="absolute inset-x-2 -bottom-px h-0.5 rounded-full"
                    style={{ background: "var(--brand-accent)" }}
                  />
                )}
              </button>
            ))}
          </div>

          {tab === "resumen" && <ClientSummaryTab client={client} />}
          {tab === "anamnesis" && <ClientAnamnesisTab client={client} onSaved={load} />}
          {tab === "planificacion" && <ClientPlanPanel client={client} />}
          {tab === "seguimiento" && <ClientTrackingTab client={client} />}
          {tab === "feedback" && <ClientFeedbackTab client={client} onClientChanged={load} onGoPlan={() => setTab("planificacion")} />}
          {tab === "historial" && <ClientHistoryTab client={client} />}
        </div>
      </div>

      <ConfirmDialog
        open={confirmRegen}
        title="Regenerar enlace del portal"
        body="El enlace actual dejará de funcionar de inmediato. Tendrás que enviar el nuevo al cliente."
        confirmLabel="Regenerar"
        onConfirm={regenerate}
        onCancel={() => setConfirmRegen(false)}
      />
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-zinc-500">{label}</dt>
      <dd className="font-medium text-zinc-200">{value}</dd>
    </div>
  );
}

function ActionRow({ icon: Icon, label, onClick }: { icon: typeof ExternalLink; label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm text-zinc-300 hover:bg-[var(--surface-raised)]"
    >
      <Icon size={15} className="text-zinc-500" />
      {label}
    </button>
  );
}


===== FILE: frontend/src/pages/ClientsPage.tsx =====

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


===== FILE: frontend/src/pages/DashboardPage.tsx =====

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


===== FILE: frontend/src/pages/LoginPage.tsx =====

import { useState } from "react";
import { Dumbbell } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { useBrand } from "../hooks/useBrand";
import { Spinner } from "../components/ui";
import { ApiError } from "../lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const { brand } = useBrand();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!username || !password || busy) return;
    setBusy(true);
    setError("");
    try {
      await login(username, password);
    } catch (e) {
      // El error no se disculpa y es concreto (skill): credenciales o caída.
      setError(
        e instanceof ApiError && e.status === 401
          ? "Usuario o contraseña incorrectos."
          : "No se pudo conectar. Inténtalo de nuevo.",
      );
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      {/* Atmósfera: un halo tenue del color de marca, sin estridencias */}
      <div
        className="pointer-events-none fixed inset-0"
        style={{
          background:
            "radial-gradient(60% 50% at 50% 0%, rgba(110,231,183,0.06), transparent 70%)",
        }}
      />
      <div className="animate-rise card relative w-full max-w-sm p-8">
        <div
          className="mb-6 flex h-11 w-11 items-center justify-center rounded-xl"
          style={{ background: "var(--brand-accent)" }}
        >
          <Dumbbell size={22} color="#0a0a0f" />
        </div>
        <h1 className="text-xl font-semibold text-zinc-100">
          {brand?.name ?? "Asesorías Fitness"}
        </h1>
        <p className="mt-1 text-sm text-zinc-500">Panel del coach</p>

        <div className="mt-7 space-y-4">
          <div>
            <label className="label">Usuario</label>
            <input
              className="input"
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
          </div>
          <div>
            <label className="label">Contraseña</label>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
          </div>

          {error && (
            <p className="rounded-lg px-3 py-2 text-sm" style={{ background: "#F77E7E18", color: "#F7A0A0" }}>
              {error}
            </p>
          )}

          <button className="btn btn-primary w-full" disabled={busy} onClick={submit}>
            {busy ? <Spinner /> : "Entrar"}
          </button>
        </div>
      </div>
    </div>
  );
}


===== FILE: frontend/src/components/AppShell.tsx =====

import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Dumbbell,
  LayoutDashboard,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  Users,
} from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { useBrand } from "../hooks/useBrand";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/clientes", label: "Clientes", icon: Users, end: false },
  { to: "/marca", label: "Marca", icon: Settings, end: false },
];

export default function AppShell() {
  const { user, logout } = useAuth();
  const { brand } = useBrand();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar colapsable (H.2) */}
      <aside
        className="flex flex-col border-r transition-all duration-200"
        style={{ borderColor: "var(--line)", width: collapsed ? 64 : 232, background: "var(--surface)" }}
      >
        <div className="flex h-16 items-center gap-3 px-4">
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
            style={{ background: "var(--brand-accent)" }}
          >
            <Dumbbell size={18} color="#0a0a0f" />
          </div>
          {!collapsed && (
            <span className="truncate text-sm font-semibold text-zinc-100">
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
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${
                  isActive ? "text-zinc-100" : "text-zinc-500 hover:text-zinc-200"
                }`
              }
              style={({ isActive }) =>
                isActive ? { background: "var(--surface-raised)" } : undefined
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

      <main className="flex-1 overflow-y-auto" style={{ background: "var(--bg)" }}>
        <Outlet />
      </main>
    </div>
  );
}


===== FILE: frontend/src/components/ClientAnamnesisTab.tsx =====

import { useEffect, useState } from "react";
import { FileText, Save, Sparkles } from "lucide-react";
import { api, ApiError, getToken } from "../lib/api";
import type { ClientOut, GoalType, Level } from "../types";
import { Spinner, useToast } from "./ui";

/**
 * Tab Anamnesis: ficha estructurada del cliente. Es la fuente de datos que la
 * IA usa para generar el plan. Puede rellenarse de dos formas:
 *  1. "Leer anamnesis con IA": lee el PDF subido y pre-rellena estos campos.
 *  2. A mano.
 * En ambos casos el coach revisa y corrige antes de generar (seguridad). El
 * PATCH del backend registra el diff campo a campo (audit trail).
 */
export function ClientAnamnesisTab({ client, onSaved }: { client: ClientOut; onSaved: () => void }) {
  const toast = useToast();
  const [draft, setDraft] = useState<Partial<ClientOut>>({});
  const [busy, setBusy] = useState(false);
  const [reading, setReading] = useState(false);
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [pdfName, setPdfName] = useState<string | null>(null);

  // Nombre del PDF de anamnesis subido (para poder verlo/descargarlo desde aquí).
  useEffect(() => {
    api.listClientDocuments(client.id)
      .then((docs) => setPdfName(docs[0]?.name ?? null))
      .catch(() => setPdfName(null));
  }, [client.id]);

  function openPdf() {
    if (!pdfName) return;
    fetch(api.clientDocumentUrl(client.id, pdfName), { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        window.open(url, "_blank");
        setTimeout(() => URL.revokeObjectURL(url), 60000);
      })
      .catch(() => toast.push("No se pudo abrir el PDF", "error"));
  }

  function set<K extends keyof ClientOut>(key: K, value: ClientOut[K]) {
    setDraft((d) => ({ ...d, [key]: value }));
  }
  function current<K extends keyof ClientOut>(key: K): ClientOut[K] {
    return (key in draft ? draft[key] : client[key]) as ClientOut[K];
  }
  const dirty = Object.keys(draft).length > 0;

  async function save() {
    if (!dirty || busy) return;
    setBusy(true);
    try {
      await api.updateClient(client.id, draft);
      toast.push("Anamnesis actualizada");
      setDraft({});
      onSaved();
    } catch (e) {
      toast.push(e instanceof ApiError ? e.message : "No se pudo guardar", "error");
    } finally {
      setBusy(false);
    }
  }

  async function readWithAI() {
    if (reading) return;
    setReading(true);
    try {
      const res = await api.readAnamnesis(client.id);
      setAnalysis(res.deep_analysis);
      setDraft({});
      toast.push("Anamnesis leída. Revisa los datos antes de generar.");
      onSaved();
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push(detail?.message ?? e?.message ?? "No se pudo leer el PDF", "error");
    } finally {
      setReading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="card flex flex-wrap items-center justify-between gap-3 p-4">
        <div className="flex items-center gap-2.5">
          <Sparkles size={17} style={{ color: "var(--brand-accent)" }} />
          <div>
            <p className="text-sm font-medium text-zinc-200">Leer anamnesis con IA</p>
            <p className="text-xs text-zinc-500">Lee el PDF subido y rellena estos campos automáticamente.</p>
          </div>
        </div>
        <div className="flex gap-2">
          {pdfName && (
            <button onClick={openPdf} className="btn btn-ghost" title={pdfName}>
              <FileText size={15} /> Ver PDF
            </button>
          )}
          <button onClick={readWithAI} disabled={reading} className="btn btn-primary">
            <Sparkles size={15} /> {reading ? "Leyendo PDF…" : "Leer con IA"}
          </button>
        </div>
      </div>

      {analysis && (
        <div className="card p-4">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">Análisis de la IA</p>
          <p className="text-sm text-zinc-300">{analysis}</p>
        </div>
      )}

      <Section title="Datos personales">
        <Select label="Sexo" value={(current("sex") as string) ?? ""} onChange={(v) => set("sex", v as any)}
          options={[["", "—"], ["male", "Hombre"], ["female", "Mujer"]]} />
        <Field label="Fecha de nacimiento" type="date" value={(current("birth_date") as string) ?? ""}
          onChange={(v) => set("birth_date", v as any)} />
      </Section>

      <Section title="Antropometría inicial">
        <Num label="Altura (cm)" value={current("height_cm") as number} onChange={(v) => set("height_cm", v as any)} />
        <Num label="Peso actual (kg)" value={current("start_weight_kg") as number} onChange={(v) => set("start_weight_kg", v as any)} />
        <Num label="% graso (opcional)" value={current("body_fat_pct") as number} onChange={(v) => set("body_fat_pct", v as any)} />
        <Num label="Peso objetivo (kg)" value={current("goal_weight_kg") as number} onChange={(v) => set("goal_weight_kg", v as any)} />
      </Section>

      <Section title="Objetivo y nivel">
        <Select label="Objetivo" value={(current("goal_type") as string) ?? ""} onChange={(v) => set("goal_type", v as GoalType)}
          options={[["", "—"], ["fat_loss", "Pérdida de grasa"], ["muscle_gain", "Ganancia muscular"], ["recomp", "Recomposición"]]} />
        <Select label="Nivel" value={(current("level") as string) ?? ""} onChange={(v) => set("level", v as Level)}
          options={[["", "—"], ["beginner", "Principiante"], ["intermediate", "Intermedio"], ["advanced", "Avanzado"]]} />
      </Section>

      <Section title="Entrenamiento">
        <Num label="Días por semana" value={current("training_days") as number} onChange={(v) => set("training_days", v as any)} />
        <Num label="Duración sesión (min)" value={current("session_max_min") as number} onChange={(v) => set("session_max_min", v as any)} />
        <Select label="Dónde entrena" value={(current("training_place") as string) ?? ""} onChange={(v) => set("training_place", v as any)}
          options={[["", "—"], ["gym", "Gimnasio"], ["home", "Casa"], ["outdoor", "Exterior"]]} />
        <CSV label="Material (solo casa/exterior)" value={current("equipment") as string[]} onChange={(v) => set("equipment", v as any)} />
      </Section>

      <Section title="Experiencia y otros deportes">
        <Area label="Experiencia con pesas y otros deportes" value={(current("sport_history") as string) ?? ""} onChange={(v) => set("sport_history", v as any)} />
      </Section>

      <Section title="Dieta">
        <Select label="Modo de dieta" value={(current("diet_mode") as string) ?? ""} onChange={(v) => set("diet_mode", v as any)}
          options={[["", "—"], ["flexible_7", "Flexible (equivalencias)"], ["strict", "Menú cerrado"]]} />
        <Num label="Comidas al día" value={current("meals_per_day") as number} onChange={(v) => set("meals_per_day", v as any)} />
        <CSV label="Alimentos que le gustan" value={current("food_likes") as string[]} onChange={(v) => set("food_likes", v as any)} />
        <CSV label="Alimentos que evita" value={current("food_dislikes") as string[]} onChange={(v) => set("food_dislikes", v as any)} />
        <CSV label="Alergias" value={current("food_allergies") as string[]} onChange={(v) => set("food_allergies", v as any)} />
      </Section>

      <Section title="Historia clínica y salud">
        <Area label="Historia clínica (patologías, antecedentes, digestivo, salud femenina…)"
          value={(current("medical_notes") as string) ?? ""} onChange={(v) => set("medical_notes", v as any)} />
        <Area label="Medicación actual (nombre, dosis, frecuencia)"
          value={(current("medication_notes") as string) ?? ""} onChange={(v) => set("medication_notes", v as any)} />
        <Area label="Suplementación actual"
          value={(current("current_supplements") as string) ?? ""} onChange={(v) => set("current_supplements", v as any)} />
      </Section>

      <Section title="Lesiones y movilidad">
        <Area label="Lesiones / molestias (zona, lado y qué evitar)" value={(current("injuries_notes") as string) ?? ""} onChange={(v) => set("injuries_notes", v as any)} />
      </Section>

      <Section title="Estilo de vida">
        <Area label="Hábitos, sueño, estrés, hidratación, conducta alimentaria, motivo y objetivos"
          value={(current("lifestyle_notes") as string) ?? ""} onChange={(v) => set("lifestyle_notes", v as any)} />
      </Section>

      <div className="flex items-center gap-3">
        <button onClick={save} disabled={!dirty || busy} className="btn btn-primary">
          {busy ? <Spinner /> : <Save size={15} />} Guardar cambios
        </button>
        {dirty && <span className="text-xs text-zinc-500">Tienes cambios sin guardar</span>}
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card p-5">
      <h4 className="mb-3 text-sm font-semibold text-zinc-200">{title}</h4>
      <div className="grid grid-cols-2 gap-3">{children}</div>
    </div>
  );
}
function Field({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (v: string) => void; type?: string }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-zinc-500">{label}</span>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} className="input w-full" />
    </label>
  );
}
function Num({ label, value, onChange }: { label: string; value: number | null | undefined; onChange: (v: number | null) => void }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-zinc-500">{label}</span>
      <input type="number" value={value ?? ""} onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))} className="input w-full" />
    </label>
  );
}
function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: [string, string][] }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-zinc-500">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} className="input w-full">
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </label>
  );
}
function Area({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="col-span-2 block">
      <span className="mb-1 block text-xs text-zinc-500">{label}</span>
      <textarea value={value} onChange={(e) => onChange(e.target.value)} rows={3} className="input w-full resize-y" />
    </label>
  );
}
function CSV({ label, value, onChange }: { label: string; value: string[] | null | undefined; onChange: (v: string[]) => void }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-zinc-500">{label}</span>
      <input type="text" value={(value ?? []).join(", ")}
        onChange={(e) => onChange(e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
        placeholder="separa por comas" className="input w-full" />
    </label>
  );
}


===== FILE: frontend/src/components/ClientDocuments.tsx =====

import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Download, FileText, Upload } from "lucide-react";
import { api, getToken } from "../lib/api";
import { useToast } from "./ui";
import type { ClientOut } from "../types";

interface DocItem {
  name: string;
  size_kb: number;
  uploaded_at: number;
}

/**
 * Anamnesis (Camí A): el coach envía el enlace/PDF de la anamnesis al cliente y,
 * cuando este la devuelve rellenada, la sube aquí para conservarla asociada a su
 * ficha. Luego pasa los datos clave a la pestaña "Anamnesis" editable.
 */
export function ClientDocuments({ client, onUploaded }: { client: ClientOut; onUploaded?: () => void }) {
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [docs, setDocs] = useState<DocItem[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  function load() {
    api.listClientDocuments(client.id).then(setDocs).catch(() => setDocs([]));
  }
  useEffect(load, [client.id]);

  function downloadTemplate() {
    // El endpoint exige JWT; descargamos con fetch→blob para adjuntar el header.
    fetch(api.anamnesisTemplateUrl(), {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "anamnesis.pdf";
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch(() => toast.push("No se pudo descargar la plantilla", "error"));
  }

  async function upload(file: File) {
    if (busy) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      toast.push("Solo se admiten archivos PDF", "error");
      return;
    }
    setBusy(true);
    try {
      const res = await api.uploadClientDocument(client.id, file);
      if (res.read_ok) {
        toast.push("Anamnesis subida y leída con IA. Revisa los datos.");
        // La IA ya rellenó la ficha: refrescamos el cliente para que los campos
        // de la pestaña Anamnesis aparezcan al instante, sin recargar la página.
        onUploaded?.();
      } else {
        toast.push("Anamnesis subida. Pulsa 'Leer con IA' en la pestaña Anamnesis.");
      }
      load();
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo subir el documento", "error");
    } finally {
      setBusy(false);
    }
  }

  function openDoc(name: string) {
    // El endpoint exige JWT; abrimos con fetch→blob para adjuntar el header.
    fetch(api.clientDocumentUrl(client.id, name), {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        window.open(url, "_blank");
        setTimeout(() => URL.revokeObjectURL(url), 60000);
      })
      .catch(() => toast.push("No se pudo abrir el documento", "error"));
  }

  return (
    <div className="card p-5">
      <h3 className="mb-1 text-sm font-semibold text-zinc-200">Anamnesis</h3>
      <p className="mb-4 text-xs text-zinc-500">
        Descarga la anamnesis, envíala por correo y sube aquí la versión rellenada.
      </p>

      {/* Confirmación visual: anamnesis subida */}
      {docs && docs.length > 0 && (
        <div
          className="mb-3 flex items-center gap-2 rounded-lg px-3 py-2.5"
          style={{ background: "rgba(110,231,183,0.10)", border: "1px solid rgba(110,231,183,0.25)" }}
        >
          <CheckCircle2 size={16} style={{ color: "var(--brand-accent)" }} />
          <span className="text-sm font-medium" style={{ color: "var(--brand-accent)" }}>
            Anamnesis subida
          </span>
        </div>
      )}

      <button onClick={downloadTemplate} className="btn btn-ghost mb-3 w-full justify-start">
        <Download size={15} className="text-zinc-500" /> Descargar anamnesis (PDF)
      </button>

      {/* Zona de subida (arrastrar o clic) */}
      <div
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const f = e.dataTransfer.files?.[0];
          if (f) upload(f);
        }}
        className="flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed py-6 text-center transition-colors"
        style={{
          borderColor: dragOver ? "var(--brand-accent)" : "var(--line-strong)",
          background: dragOver ? "rgba(110,231,183,0.06)" : "transparent",
        }}
      >
        <Upload size={18} className="text-zinc-500" />
        <p className="mt-2 text-xs text-zinc-400">
          {busy
            ? "Subiendo y leyendo con IA…"
            : docs && docs.length > 0
            ? "Arrastra otro PDF para reemplazar"
            : "Arrastra el PDF aquí o haz clic"}
        </p>
      </div>
      <input
        ref={fileRef}
        type="file"
        accept="application/pdf,.pdf"
        hidden
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) upload(f);
          e.target.value = "";
        }}
      />

      {/* Lista de documentos */}
      {docs && docs.length > 0 && (
        <ul className="mt-4 space-y-1.5">
          {docs.map((d) => (
            <li key={d.name}>
              <button
                onClick={() => openDoc(d.name)}
                className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-left hover:bg-[var(--surface-raised)]"
              >
                <FileText size={15} style={{ color: "var(--brand-accent)" }} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm text-zinc-200">{d.name}</span>
                  <span className="text-xs text-zinc-500">{d.size_kb} KB</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}


===== FILE: frontend/src/components/ClientFeedbackTab.tsx =====

import { useCallback, useEffect, useState } from "react";
import { Sparkles, AlertTriangle, MessageSquare, Target, TrendingUp, BarChart3, Send, CheckCircle2, Pencil, Save, X, Copy } from "lucide-react";
import { api } from "../lib/api";
import { Spinner, useToast } from "./ui";
import type { ClientOut } from "../types";

interface Period {
  id: number;
  period_index: number;
  starts_on: string;
  ends_on: string;
  status: string;
  closing_weight_kg: number | null;
  closing_rating: number | null;
  closing_hardest: string | null;
  closing_questions: string | null;
  closing_waist_cm: number | null;
  closing_hip_cm: number | null;
  closing_arm_cm: number | null;
  closing_thigh_cm: number | null;
  feedback_id: number | null;
}

/**
 * Feedback: cierra el ciclo de la asesoría. Cuando el cliente cierra un período
 * (peso final, perímetros, valoración, dudas), el coach genera aquí el informe
 * de feedback con IA (análisis + recomendaciones) sobre las métricas calculadas
 * por el backend, lo revisa, y lo descarga en Word para enviarlo.
 */
export function ClientFeedbackTab({ client, onClientChanged, onGoPlan }: { client: ClientOut; onClientChanged?: () => void; onGoPlan?: () => void }) {
  const toast = useToast();
  const [periods, setPeriods] = useState<Period[] | null>(null);
  const [contents, setContents] = useState<Record<number, any>>({});
  const [generating, setGenerating] = useState<number | null>(null);
  const [sending, setSending] = useState<number | null>(null);
  const [editingFb, setEditingFb] = useState<number | null>(null);
  const [metrics, setMetrics] = useState<Record<number, any>>({});
  const [loadingMetrics, setLoadingMetrics] = useState<number | null>(null);
  const [adapting, setAdapting] = useState(false);

  async function adapt() {
    if (adapting) return;
    setAdapting(true);
    try {
      const r = await api.adaptPlan(client.id);
      toast.push(`Plan adaptado a la revisión (borrador v${r.version}). Revísalo y publícalo.`);
      onGoPlan?.();
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push(detail?.message ?? e?.message ?? "No se pudo adaptar el plan", "error");
    } finally {
      setAdapting(false);
    }
  }

  async function loadMetrics(periodId: number) {
    if (loadingMetrics != null) return;
    setLoadingMetrics(periodId);
    try {
      const m = await api.getPeriodMetrics(periodId);
      setMetrics((prev) => ({ ...prev, [periodId]: m }));
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push(detail?.message ?? e?.message ?? "No se pudo cargar el resumen", "error");
    } finally {
      setLoadingMetrics(null);
    }
  }

  const load = useCallback(() => {
    api.listPeriods(client.id)
      .then(async (ps) => {
        setPeriods(ps);
        // Carga el contenido de los feedbacks ya existentes para mostrarlo.
        const withFb = ps.filter((p) => p.feedback_id);
        const entries = await Promise.all(
          withFb.map((p) =>
            api.getFeedback(p.feedback_id as number)
              .then((f) => [p.feedback_id, { content: f.content, sent_at: f.sent_at }] as const)
              .catch(() => null),
          ),
        );
        const map: Record<number, any> = {};
        entries.forEach((e) => e && (map[e[0] as number] = e[1]));
        setContents(map);
      })
      .catch(() => setPeriods([]));
  }, [client.id]);

  useEffect(load, [load]);

  async function generate(periodId: number) {
    if (generating != null) return;
    setGenerating(periodId);
    try {
      await api.generateFeedback(periodId);
      toast.push("Feedback generado. Revísalo y descárgalo.");
      load();
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push(detail?.message ?? e?.message ?? "No se pudo generar el feedback", "error");
    } finally {
      setGenerating(null);
    }
  }

  async function send(feedbackId: number) {
    if (sending != null) return;
    setSending(feedbackId);
    try {
      await api.sendFeedback(feedbackId);
      toast.push("Feedback enviado: ya es visible en el portal del cliente");
      load();
      onClientChanged?.(); // refresca el perfil para cerrar la notificación
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo enviar el feedback", "error");
    } finally {
      setSending(null);
    }
  }

  function copyAll(content: any) {
    const parts: string[] = [];
    if (content.natural_analysis) parts.push(content.natural_analysis);
    if (Array.isArray(content.changes_bullets) && content.changes_bullets.length)
      parts.push("Cambios en el plan:\n" + content.changes_bullets.map((b: string) => `• ${b}`).join("\n"));
    if (content.answers) parts.push("Respuesta a tus dudas:\n" + content.answers);
    if (Array.isArray(content.next_objectives) && content.next_objectives.length)
      parts.push("Objetivos próximas 2 semanas:\n" + content.next_objectives.map((o: string) => `• ${o}`).join("\n"));
    if (content.closing_message) parts.push(content.closing_message);
    navigator.clipboard.writeText(parts.join("\n\n"))
      .then(() => toast.push("Feedback copiado al portapapeles"))
      .catch(() => toast.push("No se pudo copiar", "error"));
  }

  if (periods === null) {
    return (
      <div className="card flex items-center justify-center gap-2 p-8 text-sm text-zinc-500">
        <Spinner /> Cargando feedback…
      </div>
    );
  }

  if (periods.length === 0) {
    return (
      <div className="card p-6">
        <h3 className="text-base font-semibold text-zinc-100">Feedback</h3>
        <p className="mt-1 text-sm text-zinc-400">
          Aún no hay períodos. El feedback se genera cuando el cliente cierra un período
          (publica un plan, crea el período y el cliente registra su diario y lo cierra).
        </p>
      </div>
    );
  }

  const latestReview = periods
    .filter((p) => p.status === "analyzed")
    .reduce<Period | null>((a, b) => (!a || b.period_index > a.period_index ? b : a), null);

  return (
    <div className="space-y-4">
      {latestReview && (
        <div
          className="card flex flex-wrap items-center justify-between gap-2 p-3.5"
          style={{ borderColor: "var(--brand-primary, #8B1A2B)", borderWidth: 1 }}
        >
          <span className="flex items-center gap-2 text-sm text-zinc-200">
            <span
              className="flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold text-white"
              style={{ background: "var(--brand-primary, #8B1A2B)" }}
            >
              !
            </span>
            Revisión quincenal #{latestReview.period_index} lista — {latestReview.ends_on}
          </span>
          <button onClick={adapt} disabled={adapting} className="btn btn-primary">
            <Sparkles size={14} /> {adapting ? "Adaptando…" : `Adaptar planificación a la revisión #${latestReview.period_index}`}
          </button>
        </div>
      )}
      {periods.map((p) => {
        const fb = p.feedback_id ? contents[p.feedback_id] : null;
        const content = fb?.content;
        const sent: string | null = fb?.sent_at ?? null;
        const canGenerate = p.status !== "open"; // cerrado o analizado
        const daysElapsed = Math.floor((Date.now() - new Date(p.starts_on + "T00:00:00").getTime()) / 86400000) + 1;
        const ready = p.status !== "open" || daysElapsed >= 14; // resumen disponible a las 2 semanas
        const m = metrics[p.id];
        return (
          <div key={p.id} className="card p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-semibold text-zinc-100">Período {p.period_index}</h3>
                  <span className="rounded-full px-2 py-0.5 text-xs font-medium" style={badge(p.status)}>
                    {STATUS_LABEL[p.status] ?? p.status}
                  </span>
                  {sent && (
                    <span className="flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium" style={{ background: "rgba(110,231,183,0.15)", color: "var(--brand-accent)" }}>
                      <CheckCircle2 size={12} /> Feedback enviado
                    </span>
                  )}
                </div>
                <p className="mt-0.5 text-xs text-zinc-500">{p.starts_on} → {p.ends_on}</p>
              </div>
              <div className="flex gap-2">
                {ready && (
                  <button onClick={() => loadMetrics(p.id)} disabled={loadingMetrics === p.id} className="btn btn-ghost">
                    <BarChart3 size={15} /> {loadingMetrics === p.id ? "Calculando…" : "Resumen"}
                  </button>
                )}
                {p.feedback_id && !sent && (
                  <button onClick={() => send(p.feedback_id as number)} disabled={sending === p.feedback_id} className="btn btn-primary">
                    <Send size={15} /> {sending === p.feedback_id ? "Enviando…" : "Enviar al cliente"}
                  </button>
                )}
                {canGenerate && !p.feedback_id && (
                  <button onClick={() => generate(p.id)} disabled={generating === p.id} className="btn btn-primary">
                    <Sparkles size={15} />
                    {generating === p.id ? "Generando…" : "Generar feedback"}
                  </button>
                )}
              </div>
            </div>

            {p.status === "open" && (
              <div className="mt-3 flex items-center gap-2 rounded-lg p-2.5 text-xs" style={{ background: "rgba(247,201,110,0.08)", color: "#F7C96E" }}>
                <AlertTriangle size={14} /> El período aún está abierto: el cliente debe cerrarlo antes de generar el feedback.
              </div>
            )}

            {/* Datos del cierre */}
            {p.status !== "open" && (
              <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                {p.closing_weight_kg != null && <Stat label="Peso final" value={`${p.closing_weight_kg} kg`} />}
                {p.closing_rating != null && <Stat label="Valoración" value={`${p.closing_rating}/5`} />}
                {p.closing_waist_cm != null && <Stat label="Cintura" value={`${p.closing_waist_cm} cm`} />}
                {p.closing_hip_cm != null && <Stat label="Cadera" value={`${p.closing_hip_cm} cm`} />}
                {p.closing_arm_cm != null && <Stat label="Brazo" value={`${p.closing_arm_cm} cm`} />}
                {p.closing_thigh_cm != null && <Stat label="Muslo" value={`${p.closing_thigh_cm} cm`} />}
              </div>
            )}
            {p.closing_hardest && <p className="mt-2 text-xs text-zinc-400"><b className="text-zinc-300">Lo más difícil:</b> {p.closing_hardest}</p>}
            {p.closing_questions && <p className="mt-1 text-xs text-zinc-400"><b className="text-zinc-300">Dudas:</b> {p.closing_questions}</p>}

            {/* Resumen de métricas (sin IA): fuerza, peso, adherencia, objetivo — colapsable */}
            {m && (
              <details open className="mt-4 space-y-3 border-t pt-4" style={{ borderColor: "var(--line)" }}>
                <summary className="flex cursor-pointer items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                  <BarChart3 size={13} /> Resumen de las 2 semanas
                </summary>
                {/* Antes → después de los datos en 15 días (peso día 1 → día 15) */}
                <div className="mt-3">
                  <SubTitle icon={TrendingUp} text="Antes → después (15 días)" />
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    <BAStat label="Peso (kg)" before={m.weight?.start_kg} after={m.weight?.end_kg} lowerBetter />
                    {p.closing_waist_cm != null && <BAStat label="Cintura (cm)" before={null} after={p.closing_waist_cm} lowerBetter />}
                    {p.closing_hip_cm != null && <BAStat label="Cadera (cm)" before={null} after={p.closing_hip_cm} lowerBetter />}
                    {p.closing_arm_cm != null && <BAStat label="Brazo (cm)" before={null} after={p.closing_arm_cm} />}
                  </div>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
                  <Stat label="Δ peso corporal" value={fmtDelta(m.weight?.delta_kg, "kg")} />
                  <Stat label="Peso actual" value={m.body_weight_now_kg != null ? `${m.body_weight_now_kg} kg` : "—"} />
                  <Stat label="A su objetivo" value={m.distance_to_goal_kg != null ? `${Math.abs(m.distance_to_goal_kg)} kg` : "—"} />
                  <Stat label="Adherencia dieta" value={`${m.adherence?.diet_pct ?? 0}%`} />
                  <Stat label="Días registrados" value={`${m.adherence?.days_logged ?? 0}/${m.adherence?.period_days ?? 0}`} />
                  <Stat label="Ritmo semanal" value={fmtDelta(m.weight?.weekly_rate_kg, "kg/sem")} />
                </div>
                {Array.isArray(m.strength) && m.strength.length > 0 && (
                  <div>
                    <SubTitle icon={TrendingUp} text="Fuerza ganada (e1RM)" />
                    <ul className="space-y-1 text-sm">
                      {m.strength.map((s: any, i: number) => (
                        <li key={i} className="flex items-center justify-between rounded-lg px-3 py-1.5" style={{ background: "var(--surface-raised)" }}>
                          <span className="truncate text-zinc-300">{s.name}</span>
                          <span className="whitespace-nowrap text-zinc-400">
                            {Math.round(s.e1rm_kg)} kg
                            {s.delta_kg != null && (
                              <span style={{ color: s.delta_kg >= 0 ? "var(--brand-accent)" : "#F77E7E" }}>
                                {" "}{s.delta_kg >= 0 ? "▲" : "▼"} {Math.abs(s.delta_kg)}
                              </span>
                            )}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {(!m.strength || m.strength.length === 0) && (
                  <p className="mt-2 text-xs text-zinc-500">Sin series registradas aún para calcular la fuerza.</p>
                )}
              </details>
            )}

            {/* Feedback: edición o vista */}
            {content && editingFb === p.feedback_id && (
              <FeedbackEditor
                docId={p.feedback_id as number}
                content={content}
                onCancel={() => setEditingFb(null)}
                onSaved={() => { setEditingFb(null); load(); }}
              />
            )}
            {content && editingFb !== p.feedback_id && (
              <div className="mt-4 space-y-3 border-t pt-4" style={{ borderColor: "var(--line)" }}>
                <div className="flex items-center justify-between">
                  <SubTitle icon={TrendingUp} text="Feedback" />
                  <div className="flex items-center gap-3">
                    <button onClick={() => copyAll(content)} className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-200">
                      <Copy size={13} /> Copiar todo
                    </button>
                    <button onClick={() => setEditingFb(p.feedback_id as number)} className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-200">
                      <Pencil size={13} /> Editar texto
                    </button>
                  </div>
                </div>
                {content.natural_analysis && (
                  <div>
                    <p className="text-sm text-zinc-300">{content.natural_analysis}</p>
                  </div>
                )}
                {Array.isArray(content.changes_bullets) && content.changes_bullets.length > 0 && (
                  <div>
                    <SubTitle icon={Sparkles} text="Cambios en el plan" />
                    <ul className="list-disc space-y-0.5 pl-5 text-sm text-zinc-400">
                      {content.changes_bullets.map((b: string, i: number) => <li key={i}>{b}</li>)}
                    </ul>
                  </div>
                )}
                {content.answers && (
                  <div>
                    <SubTitle icon={MessageSquare} text="Respuesta a sus dudas" />
                    <p className="text-sm text-zinc-300">{content.answers}</p>
                  </div>
                )}
                {Array.isArray(content.next_objectives) && content.next_objectives.length > 0 && (
                  <div>
                    <SubTitle icon={Target} text="Objetivos próximas 2 semanas" />
                    <ul className="list-disc space-y-0.5 pl-5 text-sm text-zinc-400">
                      {content.next_objectives.map((o: string, i: number) => <li key={i}>{o}</li>)}
                    </ul>
                  </div>
                )}
                {content.closing_message && <p className="text-sm italic text-zinc-400">{content.closing_message}</p>}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

const STATUS_LABEL: Record<string, string> = { open: "Abierto", closed: "Cerrado", analyzed: "Analizado" };
function badge(status: string): React.CSSProperties {
  if (status === "analyzed") return { background: "rgba(110,231,183,0.15)", color: "var(--brand-accent)" };
  if (status === "closed") return { background: "rgba(247,201,110,0.15)", color: "#F7C96E" };
  return { background: "rgba(255,255,255,0.08)", color: "#a1a1aa" };
}

function fmtDelta(v: number | null | undefined, unit: string): string {
  if (v == null) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v} ${unit}`;
}

/** Antes → después para el resumen de feedback (día 1 → día 15). */
function BAStat({ label, before, after, lowerBetter }: {
  label: string; before: number | null | undefined; after: number | null | undefined; lowerBetter?: boolean;
}) {
  const b = before ?? null, a = after ?? null;
  const delta = b != null && a != null ? Math.round((a - b) * 10) / 10 : null;
  const good = delta != null && (lowerBetter ? delta < 0 : delta > 0);
  const bad = delta != null && delta !== 0 && !good;
  return (
    <div className="rounded-lg p-2.5" style={{ background: "var(--surface-raised)" }}>
      <div className="text-[11px] text-zinc-500">{label}</div>
      <div className="mt-0.5 flex items-baseline gap-1.5 text-sm text-zinc-100">
        <span className="text-zinc-400">{b ?? "—"}</span>
        <span className="text-zinc-600">→</span>
        <span className="font-semibold">{a ?? "—"}</span>
        {delta != null && delta !== 0 && (
          <span className="text-xs" style={{ color: good ? "var(--brand-accent)" : bad ? "#F77E7E" : "#a1a1aa" }}>
            {delta > 0 ? "+" : ""}{delta}
          </span>
        )}
      </div>
    </div>
  );
}

function FeedbackEditor({ docId, content, onCancel, onSaved }: {
  docId: number; content: any; onCancel: () => void; onSaved: () => void;
}) {
  const toast = useToast();
  const [d, setD] = useState<Record<string, string>>({
    natural_analysis: content?.natural_analysis ?? "",
    changes_bullets: (content?.changes_bullets ?? []).join("\n"),
    answers: content?.answers ?? "",
    next_objectives: (content?.next_objectives ?? []).join("\n"),
    closing_message: content?.closing_message ?? "",
  });
  const [saving, setSaving] = useState(false);
  const set = (k: string, v: string) => setD((p) => ({ ...p, [k]: v }));

  async function save() {
    if (saving) return;
    setSaving(true);
    try {
      await api.editFeedback(docId, {
        natural_analysis: d.natural_analysis,
        changes_bullets: d.changes_bullets.split("\n").map((s) => s.trim()).filter(Boolean),
        answers: d.answers.trim() || null,
        next_objectives: d.next_objectives.split("\n").map((s) => s.trim()).filter(Boolean),
        closing_message: d.closing_message,
      });
      toast.push("Feedback actualizado");
      onSaved();
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo guardar", "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mt-4 space-y-3 border-t pt-4" style={{ borderColor: "var(--line)" }}>
      <div className="flex items-center justify-between">
        <SubTitle icon={Pencil} text="Editar feedback" />
        <div className="flex gap-2">
          <button onClick={onCancel} className="btn btn-ghost"><X size={14} /> Cancelar</button>
          <button onClick={save} disabled={saving} className="btn btn-primary"><Save size={14} /> {saving ? "Guardando…" : "Guardar"}</button>
        </div>
      </div>
      <FbArea label="Análisis" value={d.natural_analysis} onChange={(v) => set("natural_analysis", v)} rows={4} />
      <FbArea label="Cambios en el plan (uno por línea)" value={d.changes_bullets} onChange={(v) => set("changes_bullets", v)} />
      <FbArea label="Respuesta a sus dudas" value={d.answers} onChange={(v) => set("answers", v)} />
      <FbArea label="Objetivos próximas 2 semanas (uno por línea)" value={d.next_objectives} onChange={(v) => set("next_objectives", v)} />
      <FbArea label="Mensaje de cierre" value={d.closing_message} onChange={(v) => set("closing_message", v)} rows={2} />
    </div>
  );
}

function FbArea({ label, value, onChange, rows = 3 }: { label: string; value: string; onChange: (v: string) => void; rows?: number }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-zinc-500">{label}</span>
      <textarea value={value} onChange={(e) => onChange(e.target.value)} rows={rows} className="input w-full resize-y" />
    </label>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg p-2.5 text-center" style={{ background: "var(--surface-raised)" }}>
      <div className="text-sm font-bold text-zinc-100">{value}</div>
      <div className="text-xs text-zinc-500">{label}</div>
    </div>
  );
}

function SubTitle({ icon: Icon, text }: { icon: typeof Target; text: string }) {
  return (
    <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">
      <Icon size={13} /> {text}
    </div>
  );
}


===== FILE: frontend/src/components/ClientHistoryTab.tsx =====

import { useEffect, useState } from "react";
import { Download, TrendingDown, History, Ruler } from "lucide-react";
import { api, getToken } from "../lib/api";
import { Spinner, useToast } from "./ui";
import type { ClientOut } from "../types";

type Hist = Awaited<ReturnType<typeof api.getClientHistory>>;

const STATUS: Record<string, string> = { open: "Abierto", closed: "Cerrado", analyzed: "Analizado" };
function badge(s: string): React.CSSProperties {
  if (s === "analyzed") return { background: "rgba(110,231,183,0.15)", color: "var(--brand-accent)" };
  if (s === "closed") return { background: "rgba(247,201,110,0.15)", color: "#F7C96E" };
  return { background: "rgba(255,255,255,0.08)", color: "#a1a1aa" };
}

/**
 * Historial: toda la evolución del cliente en el tiempo, resumida y limpia.
 * Resumen global + tabla por período (peso/adherencia/fuerza) + planes. Todo
 * descargable (ZIP completo o cada plan en Word). Editable desde sus pestañas.
 */
export function ClientHistoryTab({ client }: { client: ClientOut }) {
  const toast = useToast();
  const [h, setH] = useState<Hist | null>(null);

  useEffect(() => {
    api.getClientHistory(client.id).then(setH).catch(() => setH(null));
  }, [client.id]);

  function dl(url: string, name: string) {
    fetch(url, { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => r.blob())
      .then((b) => {
        const u = URL.createObjectURL(b);
        const a = document.createElement("a");
        a.href = u; a.download = name; a.click();
        URL.revokeObjectURL(u);
      })
      .catch(() => toast.push("No se pudo descargar", "error"));
  }

  if (!h) {
    return <div className="card flex items-center justify-center gap-2 p-8 text-sm text-zinc-500"><Spinner /> Cargando historial…</div>;
  }

  const delta = h.current_weight_kg != null && h.start_weight_kg != null
    ? Math.round((h.current_weight_kg - h.start_weight_kg) * 10) / 10 : null;
  const closings = h.periods.map((p) => p.closing_weight_kg).filter((w): w is number => w != null);
  const slug = client.full_name.replace(/\s+/g, "_").toLowerCase();
  const measureRows: [string, "waist" | "hip" | "arm" | "thigh"][] = [
    ["Cintura", "waist"], ["Cadera", "hip"], ["Brazo", "arm"], ["Muslo", "thigh"],
  ];
  const hasMeasures = measureRows.some(([, k]) => h.measures?.[k]?.before != null || h.measures?.[k]?.after != null);

  return (
    <div className="space-y-4">
      {/* Resumen global + objetivo */}
      <div className="card p-5">
        <div className="mb-3 flex items-center justify-between">
          <Title icon={History} text="Resumen del cliente" />
          <button onClick={() => dl(api.exportClientUrl(client.id), `cliente_${slug}.zip`)} className="btn btn-ghost">
            <Download size={15} /> Descargar todo
          </button>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <Stat label="Peso inicial" value={h.start_weight_kg != null ? `${h.start_weight_kg} kg` : "—"} />
          <Stat label="Peso actual" value={h.current_weight_kg != null ? `${h.current_weight_kg} kg` : "—"} />
          <Stat label="Cambio total" value={delta != null ? `${delta > 0 ? "+" : ""}${delta} kg` : "—"} highlight />
          <Stat label="Objetivo" value={h.goal_weight_kg != null ? `${h.goal_weight_kg} kg` : "—"} />
          <Stat label="Le quedan" value={h.remaining_to_goal_kg != null ? `${h.remaining_to_goal_kg} kg` : "—"} highlight />
          <Stat label="Fuerza ganada (total)" value={h.total_strength_gain_pct != null ? `${h.total_strength_gain_pct > 0 ? "+" : ""}${h.total_strength_gain_pct}%` : "—"} />
        </div>
        {closings.length >= 2 && <Spark data={closings} />}
      </div>

      {/* Medidas corporales antes → después */}
      {hasMeasures && (
        <div className="card p-5">
          <Title icon={Ruler} text="Medidas corporales (antes → después)" />
          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {measureRows.map(([label, key]) => (
              <BA key={key} label={`${label} (cm)`} before={h.measures?.[key]?.before ?? null} after={h.measures?.[key]?.after ?? null} lowerBetter={key !== "arm"} />
            ))}
          </div>
        </div>
      )}

      {/* Evolución por período (desplegable) */}
      <div className="card p-5">
        <Title icon={TrendingDown} text="Evolución por período" />
        {h.periods.length === 0 ? (
          <p className="mt-2 text-xs text-zinc-500">Aún no hay períodos.</p>
        ) : (
          <div className="mt-3 space-y-2">
            {h.periods.slice().reverse().map((p) => (
              <details key={p.period_index} className="overflow-hidden rounded-lg border" style={{ borderColor: "var(--line)" }}>
                <summary className="flex cursor-pointer items-center justify-between px-3 py-2.5 text-sm" style={{ background: "var(--surface-raised)" }}>
                  <span className="flex items-center gap-2">
                    <span className="font-semibold text-zinc-100">Período #{p.period_index}</span>
                    <span className="text-xs text-zinc-500">{p.starts_on} → {p.ends_on}</span>
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="rounded-full px-2 py-0.5 text-xs" style={badge(p.status)}>{STATUS[p.status] ?? p.status}</span>
                    <span className="text-xs text-zinc-400">{p.feedback_id ? (p.feedback_sent ? "FB enviado" : "FB borrador") : ""}</span>
                  </span>
                </summary>
                <div className="px-3 py-3">
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    <Stat label="Peso cierre" value={p.closing_weight_kg != null ? `${p.closing_weight_kg} kg${p.weight_delta_kg != null ? ` (${p.weight_delta_kg > 0 ? "+" : ""}${p.weight_delta_kg})` : ""}` : "—"} />
                    <Stat label="Adherencia" value={p.adherence_pct != null ? `${p.adherence_pct}%` : "—"} />
                    <Stat label="Fuerza (e1RM)" value={p.best_e1rm_kg != null ? `${Math.round(p.best_e1rm_kg)} kg` : "—"} />
                    <Stat label="↑ Fuerza período" value={p.strength_gain_pct != null ? `${p.strength_gain_pct > 0 ? "+" : ""}${p.strength_gain_pct}%` : "—"} />
                  </div>
                  <div className="mt-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                    <Ruler size={12} /> Cinta (cm)
                  </div>
                  <div className="mt-1 grid grid-cols-2 gap-2 text-xs text-zinc-300 sm:grid-cols-4">
                    <span>Cintura: <b>{p.waist_cm ?? "—"}</b></span>
                    <span>Cadera: <b>{p.hip_cm ?? "—"}</b></span>
                    <span>Brazo: <b>{p.arm_cm ?? "—"}</b></span>
                    <span>Muslo: <b>{p.thigh_cm ?? "—"}</b></span>
                  </div>
                </div>
              </details>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/** Antes → después con delta coloreado. */
function BA({ label, before, after, lowerBetter }: {
  label: string; before: number | null; after: number | null; lowerBetter?: boolean;
}) {
  const delta = before != null && after != null ? Math.round((after - before) * 10) / 10 : null;
  const good = delta != null && (lowerBetter ? delta < 0 : delta > 0);
  const bad = delta != null && delta !== 0 && !good;
  return (
    <div className="rounded-lg p-2.5" style={{ background: "var(--surface-raised)" }}>
      <div className="text-[11px] text-zinc-500">{label}</div>
      <div className="mt-0.5 flex items-baseline gap-1.5 text-sm text-zinc-100">
        <span className="text-zinc-400">{before ?? "—"}</span>
        <span className="text-zinc-600">→</span>
        <span className="font-semibold">{after ?? "—"}</span>
        {delta != null && delta !== 0 && (
          <span className="text-xs" style={{ color: good ? "var(--brand-accent)" : bad ? "#F77E7E" : "#a1a1aa" }}>
            {delta > 0 ? "+" : ""}{delta}
          </span>
        )}
      </div>
    </div>
  );
}

function Title({ icon: Icon, text }: { icon: typeof History; text: string }) {
  return (
    <div className="flex items-center gap-2">
      <Icon size={16} style={{ color: "var(--brand-accent)" }} />
      <h4 className="text-sm font-semibold text-zinc-200">{text}</h4>
    </div>
  );
}

function Stat({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="rounded-lg p-3 text-center" style={{ background: "var(--surface-raised)" }}>
      <div className="text-lg font-bold" style={{ color: highlight ? "var(--brand-accent)" : "#e7e7ea" }}>{value}</div>
      <div className="text-xs text-zinc-500">{label}</div>
    </div>
  );
}

function Spark({ data }: { data: number[] }) {
  const w = 280, h = 44, min = Math.min(...data), max = Math.max(...data), range = max - min || 1;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - 4 - ((v - min) / range) * (h - 8)}`).join(" ");
  return (
    <div className="mt-4">
      <div className="mb-1 text-xs text-zinc-500">Peso de cierre por período</div>
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ maxHeight: 56 }} preserveAspectRatio="none">
        <polyline points={pts} fill="none" stroke="var(--brand-accent)" strokeWidth="2" />
      </svg>
    </div>
  );
}


===== FILE: frontend/src/components/ClientPlanEditor.tsx =====

import { useState } from "react";
import { Save, X, Plus, Trash2, Utensils, Dumbbell } from "lucide-react";
import { api } from "../lib/api";
import { Spinner, useToast } from "./ui";

interface PlanData {
  id: number;
  month_index: number;
  version: number;
  status: string;
  guardrail_flags: string[];
  nutrition: any;
  training: any;
  education: any;
}

/**
 * Editor manual del plan (revisión del coach antes de enviar). Edita nutrición,
 * entrenamiento y educativo y los guarda (PATCH /plans/{id}). El banco de comidas
 * no se edita aquí (se muestra en la vista); cambiar un ejercicio por otro se hace
 * con el "swap". Guarda el JSON tal cual: los guardrails no se re-ejecutan (es
 * edición del coach bajo su criterio).
 */
export function ClientPlanEditor({
  plan, exMap, onSaved, onCancel,
}: {
  plan: PlanData;
  exMap: Record<number, string>;
  onSaved: (p: PlanData) => void;
  onCancel: () => void;
}) {
  const toast = useToast();
  const [draft, setDraft] = useState(() => ({
    nutrition: structuredClone(plan.nutrition ?? {}),
    training: structuredClone(plan.training ?? {}),
    education: structuredClone(plan.education ?? {}),
  }));
  const [saving, setSaving] = useState(false);

  function mutate(fn: (d: typeof draft) => void) {
    setDraft((d) => { const n = structuredClone(d); fn(n); return n; });
  }

  async function save() {
    if (saving) return;
    setSaving(true);
    try {
      const r = await api.updatePlan(plan.id, {
        nutrition_json: draft.nutrition,
        training_json: draft.training,
        education_json: draft.education,
      });
      toast.push("Plan actualizado");
      onSaved({
        ...plan,
        nutrition: r.nutrition_json, training: r.training_json, education: r.education_json,
        guardrail_flags: r.guardrail_flags ?? [], status: r.status, version: r.version,
      });
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo guardar el plan", "error");
    } finally {
      setSaving(false);
    }
  }

  const nut = draft.nutrition;
  const tr = draft.training;
  nut.macros = nut.macros ?? {};
  nut.supplements = nut.supplements ?? [];
  nut.flexibility_rules = nut.flexibility_rules ?? [];
  tr.weekly_progression = tr.weekly_progression ?? [];
  tr.sessions = tr.sessions ?? [];
  tr.cardio = tr.cardio ?? { daily_steps: 0, sessions: [] };

  return (
    <div className="space-y-4">
      <div className="card sticky top-2 z-10 flex items-center justify-between p-4">
        <h3 className="text-base font-semibold text-zinc-100">Editar plan · Mes {plan.month_index}</h3>
        <div className="flex gap-2">
          <button onClick={onCancel} className="btn btn-ghost"><X size={15} /> Cancelar</button>
          <button onClick={save} disabled={saving} className="btn btn-primary">
            {saving ? <Spinner /> : <Save size={15} />} Guardar cambios
          </button>
        </div>
      </div>

      {/* Nutrición */}
      <div className="card p-5">
        <Title icon={Utensils} text="Nutrición" />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Num label="Calorías objetivo" value={nut.target_kcal} onChange={(v) => mutate((d) => (d.nutrition.target_kcal = v))} />
          <Num label="Proteína (g)" value={nut.macros.protein_g} onChange={(v) => mutate((d) => (d.nutrition.macros.protein_g = v))} />
          <Num label="Carbohidratos (g)" value={nut.macros.carbs_g} onChange={(v) => mutate((d) => (d.nutrition.macros.carbs_g = v))} />
          <Num label="Grasas (g)" value={nut.macros.fat_g} onChange={(v) => mutate((d) => (d.nutrition.macros.fat_g = v))} />
        </div>
        <Area label="Justificación (rationale)" value={nut.rationale ?? ""} onChange={(v) => mutate((d) => (d.nutrition.rationale = v))} />
        <Area label="Reglas de flexibilidad (una por línea)" value={(nut.flexibility_rules ?? []).join("\n")}
          onChange={(v) => mutate((d) => (d.nutrition.flexibility_rules = v.split("\n").map((s) => s.trim()).filter(Boolean)))} />

        <Subhead text="Suplementos" onAdd={() => mutate((d) => d.nutrition.supplements.push({ name: "", dose: "", timing: "", evidence_note: "" }))} />
        {nut.supplements.map((s: any, i: number) => (
          <Row key={i} onRemove={() => mutate((d) => d.nutrition.supplements.splice(i, 1))}>
            <Text label="Nombre" value={s.name} onChange={(v) => mutate((d) => (d.nutrition.supplements[i].name = v))} />
            <Text label="Dosis" value={s.dose} onChange={(v) => mutate((d) => (d.nutrition.supplements[i].dose = v))} />
            <Text label="Momento" value={s.timing} onChange={(v) => mutate((d) => (d.nutrition.supplements[i].timing = v))} />
            <Text label="Nota" value={s.evidence_note ?? ""} onChange={(v) => mutate((d) => (d.nutrition.supplements[i].evidence_note = v))} />
          </Row>
        ))}
      </div>

      {/* Entrenamiento */}
      <div className="card p-5">
        <Title icon={Dumbbell} text="Entrenamiento" />
        <Text label="Nombre del split" value={tr.split_name ?? ""} onChange={(v) => mutate((d) => (d.training.split_name = v))} />
        <Area label="Justificación del split" value={tr.split_rationale ?? ""} onChange={(v) => mutate((d) => (d.training.split_rationale = v))} />

        <Subhead text="Progresión semanal" />
        {tr.weekly_progression.map((w: any, i: number) => (
          <div key={i} className="mt-2 grid grid-cols-2 gap-2 rounded-lg p-2 sm:grid-cols-4" style={{ background: "var(--surface-raised)" }}>
            <Text label={`Sem ${w.week ?? i + 1} · intención`} value={w.intent ?? ""} onChange={(v) => mutate((d) => (d.training.weekly_progression[i].intent = v))} />
            <Num label="Carga %" value={w.load_pct} onChange={(v) => mutate((d) => (d.training.weekly_progression[i].load_pct = v))} />
            <Text label="RIR" value={w.rir_target ?? ""} onChange={(v) => mutate((d) => (d.training.weekly_progression[i].rir_target = v))} />
            <Text label="Volumen" value={w.volume_note ?? ""} onChange={(v) => mutate((d) => (d.training.weekly_progression[i].volume_note = v))} />
          </div>
        ))}

        <Subhead text="Sesiones" />
        {tr.sessions.map((s: any, si: number) => (
          <div key={si} className="mt-2 rounded-lg p-3" style={{ background: "var(--surface-raised)" }}>
            <div className="grid grid-cols-2 gap-2">
              <Text label="Día" value={s.day ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].day = v))} />
              <Text label="Nombre" value={s.name ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].name = v))} />
            </div>
            <Area label="Calentamiento" value={s.warmup ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].warmup = v))} />
            {(s.exercises ?? []).map((ex: any, ei: number) => (
              <div key={ei} className="mt-2 rounded-md p-2" style={{ background: "var(--surface)" }}>
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-xs font-medium text-zinc-200">{exMap[ex.exercise_id] ?? `Ejercicio #${ex.exercise_id}`}</span>
                  <button onClick={() => mutate((d) => d.training.sessions[si].exercises.splice(ei, 1))} className="text-zinc-500 hover:text-red-400"><Trash2 size={14} /></button>
                </div>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <Num label="Series" value={ex.sets} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].sets = v))} />
                  <Text label="Reps" value={ex.rep_range ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].rep_range = v))} />
                  <Text label="RIR" value={ex.rir ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].rir = v))} />
                  <Num label="Descanso (s)" value={ex.rest_sec} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].rest_sec = v))} />
                  <Text label="Tempo" value={ex.tempo ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].tempo = v))} />
                  <Num label="Peso sug. (kg)" value={ex.start_weight_hint_kg} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].start_weight_hint_kg = v))} />
                </div>
                <Text label="Progresión" value={ex.progression_rule ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].progression_rule = v))} />
                <Text label="Cue técnica" value={ex.technique_cue ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].technique_cue = v))} />
              </div>
            ))}
            <Area label="Vuelta a la calma" value={s.cooldown ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].cooldown = v))} />
          </div>
        ))}

        <Subhead text="Cardio y descarga" />
        <div className="grid grid-cols-2 gap-2">
          <Num label="Pasos diarios" value={tr.cardio.daily_steps} onChange={(v) => mutate((d) => (d.training.cardio.daily_steps = v))} />
        </div>
        <Area label="Instrucciones de deload" value={tr.deload_instructions ?? ""} onChange={(v) => mutate((d) => (d.training.deload_instructions = v))} />
      </div>

      <p className="text-xs text-zinc-500">
        El banco de comidas no se edita aquí; para cambiar un ejercicio por otro usa el "swap" de la biblioteca.
      </p>
    </div>
  );
}

function Title({ icon: Icon, text }: { icon: typeof Utensils; text: string }) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <Icon size={16} style={{ color: "var(--brand-accent)" }} />
      <h4 className="text-sm font-semibold text-zinc-200">{text}</h4>
    </div>
  );
}
function Subhead({ text, onAdd }: { text: string; onAdd?: () => void }) {
  return (
    <div className="mt-4 mb-1 flex items-center justify-between">
      <h5 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{text}</h5>
      {onAdd && <button onClick={onAdd} className="flex items-center gap-1 text-xs text-[var(--brand-accent)]"><Plus size={13} /> Añadir</button>}
    </div>
  );
}
function Row({ children, onRemove }: { children: React.ReactNode; onRemove: () => void }) {
  return (
    <div className="mt-2 flex items-start gap-2 rounded-lg p-2" style={{ background: "var(--surface-raised)" }}>
      <div className="grid flex-1 grid-cols-1 gap-2 sm:grid-cols-2">{children}</div>
      <button onClick={onRemove} className="mt-5 text-zinc-500 hover:text-red-400"><Trash2 size={14} /></button>
    </div>
  );
}
function Text({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="block">
      <span className="mb-0.5 block text-xs text-zinc-500">{label}</span>
      <input type="text" value={value ?? ""} onChange={(e) => onChange(e.target.value)} className="input w-full" />
    </label>
  );
}
function Num({ label, value, onChange }: { label: string; value: number | null | undefined; onChange: (v: number | null) => void }) {
  return (
    <label className="block">
      <span className="mb-0.5 block text-xs text-zinc-500">{label}</span>
      <input type="number" value={value ?? ""} onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))} className="input w-full" />
    </label>
  );
}
function Area({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="mt-2 block">
      <span className="mb-0.5 block text-xs text-zinc-500">{label}</span>
      <textarea value={value ?? ""} onChange={(e) => onChange(e.target.value)} rows={2} className="input w-full resize-y" />
    </label>
  );
}


===== FILE: frontend/src/components/ClientPlanPanel.tsx =====

import { useEffect, useState } from "react";
import { Sparkles, Download, Send, AlertTriangle, Dumbbell, Utensils, Pill, CalendarDays, Pencil } from "lucide-react";
import { api, getToken } from "../lib/api";
import { Spinner, useToast } from "./ui";
import { ClientPlanEditor } from "./ClientPlanEditor";
import type { ClientOut } from "../types";

interface PlanData {
  id: number;
  month_index: number;
  version: number;
  status: string;
  guardrail_flags: string[];
  nutrition: any;
  training: any;
  education: any;
}

/** Normaliza un plan venga de generatePlan (nutrition/...) o de listPlans (nutrition_json/...). */
function normalize(p: any): PlanData {
  return {
    id: p.id,
    month_index: p.month_index,
    version: p.version,
    status: p.status,
    guardrail_flags: p.guardrail_flags ?? [],
    nutrition: p.nutrition ?? p.nutrition_json ?? null,
    training: p.training ?? p.training_json ?? null,
    education: p.education ?? p.education_json ?? null,
  };
}

/**
 * Planificación: genera el plan mensual con IA a partir de la anamnesis, lo
 * PERSISTE (al volver a la pestaña se recarga el último plan guardado), muestra
 * TODA la info (nutrición, banco de comidas, entrenamiento, educativo) y permite
 * publicarlo y descargarlo en Word.
 */
export function ClientPlanPanel({ client }: { client: ClientOut }) {
  const toast = useToast();
  const [plan, setPlan] = useState<PlanData | null>(null);
  const [exMap, setExMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [startingPeriod, setStartingPeriod] = useState(false);
  const [editing, setEditing] = useState(false);
  const [missing, setMissing] = useState<string[] | null>(null);
  const [periods, setPeriods] = useState<{ id: number; period_index: number; plan_id: number | null; starts_on: string; ends_on: string; status: string }[]>([]);

  // Al montar: carga el último plan guardado + el mapa de ejercicios + los períodos.
  useEffect(() => {
    let alive = true;
    Promise.all([
      api.listPlans(client.id),
      api.listExercises({ include_archived: true }),
      api.listPeriods(client.id),
    ])
      .then(([plans, exs, pds]) => {
        if (!alive) return;
        const map: Record<number, string> = {};
        exs.forEach((e) => (map[e.id] = e.canonical_name));
        setExMap(map);
        setPeriods(pds);
        if (plans.length) setPlan(normalize(plans[0])); // [0] = versión más reciente
      })
      .catch(() => {})
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [client.id]);

  async function startPeriod() {
    if (!plan || startingPeriod) return;
    setStartingPeriod(true);
    try {
      const today = new Date().toISOString().slice(0, 10);
      await api.createPeriod(client.id, plan.id, today, 14);
      setPeriods(await api.listPeriods(client.id));
      toast.push("Seguimiento iniciado (14 días). El cliente ya puede registrar su diario.");
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push(detail?.message ?? e?.message ?? "No se pudo iniciar el período", "error");
    } finally {
      setStartingPeriod(false);
    }
  }

  async function generate() {
    if (generating) return;
    setGenerating(true);
    setMissing(null);
    try {
      const p = await api.generatePlan(client.id, plan?.month_index ?? 1);
      setPlan(normalize(p));
      toast.push("Planificación generada");
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      if (detail?.missing) setMissing(detail.missing);
      else toast.push(detail?.message ?? e?.message ?? "No se pudo generar el plan", "error");
    } finally {
      setGenerating(false);
    }
  }

  async function adapt() {
    if (generating) return;
    setGenerating(true);
    try {
      const r = await api.adaptPlan(client.id);
      const plans = await api.listPlans(client.id);
      const full = plans.find((pl) => pl.id === r.id) ?? plans[0]; // listPlans → más reciente primero
      if (full) setPlan(normalize(full));
      toast.push(`Plan adaptado a la revisión (borrador v${r.version}). Revísalo y publícalo.`);
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push(detail?.message ?? e?.message ?? "No se pudo adaptar el plan", "error");
    } finally {
      setGenerating(false);
    }
  }

  async function publish() {
    if (!plan || publishing) return;
    setPublishing(true);
    try {
      await api.publishPlan(plan.id);
      setPlan({ ...plan, status: "published" });
      toast.push("Plan publicado: ya es visible en el portal del cliente");
    } catch {
      toast.push("No se pudo publicar", "error");
    } finally {
      setPublishing(false);
    }
  }

  function downloadPdf() {
    if (!plan) return;
    fetch(api.planDocumentUrl(plan.id), { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `plan_${client.full_name.replace(/\s+/g, "_").toLowerCase()}_mes${plan.month_index}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch(() => toast.push("No se pudo descargar", "error"));
  }

  if (loading) {
    return (
      <div className="card flex items-center justify-center gap-2 p-8 text-sm text-zinc-500">
        <Spinner /> Cargando planificación…
      </div>
    );
  }

  // ---------- Sin plan generado todavía ----------
  if (!plan) {
    return (
      <div className="card p-6">
        <div className="flex items-start gap-3">
          <div className="rounded-xl p-2.5" style={{ background: "rgba(110,231,183,0.12)" }}>
            <Sparkles size={20} style={{ color: "var(--brand-accent)" }} />
          </div>
          <div className="flex-1">
            <h3 className="text-base font-semibold text-zinc-100">Planificación mensual</h3>
            <p className="mt-1 text-sm text-zinc-400">
              Genera el plan de dieta y entrenamiento con IA a partir de los datos de la
              anamnesis. Podrás revisarlo, publicarlo y descargarlo.
            </p>

            {missing && (
              <div className="mt-4 rounded-lg border p-3" style={{ borderColor: "#7a5b1a", background: "rgba(247,201,110,0.08)" }}>
                <div className="flex items-center gap-2 text-sm font-medium text-amber-300">
                  <AlertTriangle size={15} /> Faltan datos en la anamnesis
                </div>
                <p className="mt-1 text-xs text-zinc-400">
                  Completa estos campos en la pestaña <b>Anamnesis</b> antes de generar:
                </p>
                <ul className="mt-2 flex flex-wrap gap-1.5">
                  {missing.map((m) => (
                    <li key={m} className="rounded-md px-2 py-0.5 text-xs" style={{ background: "rgba(247,201,110,0.15)", color: "#F7C96E" }}>
                      {m}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <button onClick={generate} disabled={generating} className="btn btn-primary mt-4">
              <Sparkles size={16} />
              {generating ? "Generando… (puede tardar 1-2 min)" : "Generar planificación"}
            </button>
            {generating && (
              <p className="mt-2 text-xs text-zinc-500">
                La IA está creando el plan (núcleo, comidas y contenido educativo). No cierres la página.
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ---------- Modo edición ----------
  if (editing) {
    return (
      <ClientPlanEditor
        plan={plan}
        exMap={exMap}
        onSaved={(p) => { setPlan(p); setEditing(false); }}
        onCancel={() => setEditing(false)}
      />
    );
  }

  // ---------- Plan generado / guardado: vista completa ----------
  const nut = plan.nutrition ?? {};
  const tr = plan.training ?? {};
  const macros = nut.macros ?? {};
  const mealBank = nut.meal_bank ?? null;
  const exName = (id: number) => exMap[id] ?? `Ejercicio #${id}`;
  const currentPeriod = periods.find((p) => p.plan_id === plan.id);

  return (
    <div className="space-y-4">
      {/* Cabecera con acciones */}
      <div className="card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-zinc-100">Planificación · Mes {plan.month_index}</h3>
              <span
                className="rounded-full px-2 py-0.5 text-xs font-medium"
                style={
                  plan.status === "published"
                    ? { background: "rgba(110,231,183,0.15)", color: "var(--brand-accent)" }
                    : { background: "rgba(255,255,255,0.08)", color: "#a1a1aa" }
                }
              >
                {plan.status === "published" ? "Publicado" : "Borrador"} · v{plan.version}
              </span>
            </div>
            <p className="mt-0.5 text-xs text-zinc-500">
              Revisa el plan. Cuando esté listo, publícalo (lo verá el cliente) y descárgalo.
            </p>
          </div>
          <div className="flex gap-2">
            {(() => {
              const review = periods
                .filter((p) => p.status === "analyzed")
                .reduce<(typeof periods)[number] | null>((a, b) => (!a || b.period_index > a.period_index ? b : a), null);
              return review ? (
                <button
                  onClick={adapt}
                  disabled={generating}
                  className="btn btn-primary"
                  title="Aplica los cambios de la última revisión quincenal (dieta + entreno) y crea un borrador. No usa IA."
                >
                  <span
                    className="mr-1 inline-flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold text-white"
                    style={{ background: "rgba(255,255,255,0.25)" }}
                  >
                    !
                  </span>
                  {generating ? "Adaptando…" : `Adaptar a la revisión #${review.period_index}`}
                </button>
              ) : null;
            })()}
            <button onClick={() => setEditing(true)} className="btn btn-ghost">
              <Pencil size={15} /> Editar
            </button>
            <button onClick={downloadPdf} className="btn btn-ghost">
              <Download size={15} /> Descargar PDF
            </button>
            {plan.status !== "published" && (
              <button onClick={publish} disabled={publishing} className="btn btn-primary">
                <Send size={15} /> {publishing ? "Publicando…" : "Publicar"}
              </button>
            )}
          </div>
        </div>

        {/* Seguimiento: tras publicar, iniciar el período para que el cliente
            registre el diario en el portal (cierra el ciclo hacia el feedback). */}
        {plan.status === "published" && (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-lg p-3" style={{ background: "var(--surface-raised)" }}>
            {currentPeriod ? (
              <span className="flex items-center gap-2 text-xs text-zinc-400">
                <CalendarDays size={14} style={{ color: "var(--brand-accent)" }} />
                Seguimiento activo · {currentPeriod.starts_on} → {currentPeriod.ends_on}
                <span className="rounded-full px-2 py-0.5" style={{ background: "rgba(110,231,183,0.12)", color: "var(--brand-accent)" }}>
                  {currentPeriod.status === "open" ? "abierto" : currentPeriod.status === "closed" ? "cerrado" : "analizado"}
                </span>
              </span>
            ) : (
              <>
                <span className="text-xs text-zinc-500">Inicia el seguimiento para que el cliente registre su diario y, al cerrarlo, puedas generar el feedback.</span>
                <button onClick={startPeriod} disabled={startingPeriod} className="btn btn-ghost">
                  <CalendarDays size={15} /> {startingPeriod ? "Iniciando…" : "Iniciar seguimiento (14 días)"}
                </button>
              </>
            )}
          </div>
        )}
      </div>

      {/* Nutrición */}
      <div className="card p-5">
        <SectionTitle icon={Utensils} title="Nutrición" />
        <div className="grid grid-cols-4 gap-2">
          {[
            ["Calorías", `${Math.round(nut.target_kcal ?? 0)}`],
            ["Proteína", `${Math.round(macros.protein_g ?? 0)} g`],
            ["Carbohid.", `${Math.round(macros.carbs_g ?? 0)} g`],
            ["Grasas", `${Math.round(macros.fat_g ?? 0)} g`],
          ].map(([label, val]) => (
            <Stat key={label} label={label} value={val} />
          ))}
        </div>
        {nut.tdee_kcal != null && (
          <p className="mt-2 text-xs text-zinc-500">TDEE estimado: {Math.round(nut.tdee_kcal)} kcal</p>
        )}
        {nut.rationale && (
          <details className="mt-3 text-sm">
            <summary className="cursor-pointer font-medium text-zinc-400 hover:text-zinc-200">Justificación de la nutrición</summary>
            <p className="mt-2 text-zinc-400">{nut.rationale}</p>
          </details>
        )}
        {nut.refeed_or_break && (
          <p className="mt-2 text-xs text-zinc-400"><b className="text-zinc-300">Recarga / descanso:</b> {nut.refeed_or_break}</p>
        )}

        {Array.isArray(nut.meals) && nut.meals.length > 0 && (
          <div className="mt-4">
            <h5 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">Objetivos por comida</h5>
            <div className="space-y-1.5">
              {nut.meals.map((m: any) => (
                <div key={m.slot} className="flex items-center justify-between rounded-lg px-3 py-2 text-xs" style={{ background: "var(--surface-raised)" }}>
                  <span className="text-zinc-300">{m.time} · {m.name}</span>
                  <span className="text-zinc-500">
                    {Math.round(m.target?.kcal ?? 0)} kcal · P{Math.round(m.target?.protein_g ?? 0)} / C{Math.round(m.target?.carbs_g ?? 0)} / G{Math.round(m.target?.fat_g ?? 0)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {Array.isArray(nut.flexibility_rules) && nut.flexibility_rules.length > 0 && (
          <div className="mt-3">
            <h5 className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">Reglas de flexibilidad</h5>
            <ul className="list-disc space-y-0.5 pl-5 text-xs text-zinc-400">
              {nut.flexibility_rules.map((r: string, i: number) => <li key={i}>{r}</li>)}
            </ul>
          </div>
        )}
      </div>

      {/* Suplementación */}
      {Array.isArray(nut.supplements) && nut.supplements.length > 0 && (
        <div className="card p-5">
          <SectionTitle icon={Pill} title="Suplementación" />
          <div className="space-y-1.5">
            {nut.supplements.map((s: any, i: number) => (
              <div key={i} className="rounded-lg px-3 py-2 text-xs" style={{ background: "var(--surface-raised)" }}>
                <span className="font-medium text-zinc-200">{s.name}</span>
                <span className="text-zinc-500"> · {s.dose} · {s.timing}</span>
                {s.evidence_note && <p className="mt-0.5 text-zinc-500">{s.evidence_note}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Banco de comidas */}
      {mealBank && (
        <div className="card p-5">
          <SectionTitle icon={Utensils} title={`Banco de comidas (${mealBank.mode === "strict" ? "menú cerrado" : "equivalencias"})`} />
          {mealBank.mode === "flexible_7" && Array.isArray(mealBank.slots) ? (
            <div className="space-y-3">
              {mealBank.slots.map((slot: any) => (
                <details key={slot.slot} className="rounded-lg" style={{ background: "var(--surface-raised)" }}>
                  <summary className="cursor-pointer px-3 py-2 text-sm font-medium text-zinc-200">
                    Comida {slot.slot} · {slot.options?.length ?? 0} opciones
                  </summary>
                  <div className="space-y-2 px-3 pb-3">
                    {slot.options?.map((o: any) => <MealOption key={o.key ?? o.title} o={o} />)}
                  </div>
                </details>
              ))}
            </div>
          ) : mealBank.mode === "strict" && Array.isArray(mealBank.days) ? (
            <div className="space-y-3">
              {mealBank.days.map((d: any) => (
                <details key={d.day} className="rounded-lg" style={{ background: "var(--surface-raised)" }}>
                  <summary className="cursor-pointer px-3 py-2 text-sm font-medium capitalize text-zinc-200">{d.day}</summary>
                  <div className="space-y-2 px-3 pb-3">
                    {d.meals?.map((m: any, i: number) => <MealOption key={i} o={m.dish} prefix={`Comida ${m.slot}: `} />)}
                  </div>
                </details>
              ))}
            </div>
          ) : (
            <p className="text-xs text-zinc-500">Sin banco de comidas.</p>
          )}
        </div>
      )}

      {/* Entrenamiento */}
      <div className="card p-5">
        <SectionTitle icon={Dumbbell} title={`Entrenamiento${tr.split_name ? ` · ${tr.split_name}` : ""}`} />
        {tr.split_rationale && (
          <details className="mb-3 text-sm">
            <summary className="cursor-pointer font-medium text-zinc-400 hover:text-zinc-200">Sobre esta estructura</summary>
            <p className="mt-2 text-zinc-400">{tr.split_rationale}</p>
          </details>
        )}

        {Array.isArray(tr.weekly_progression) && tr.weekly_progression.length > 0 && (
          <div className="mb-4">
            <h5 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">Progresión semanal</h5>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {tr.weekly_progression.map((w: any) => (
                <div key={w.week} className="rounded-lg p-2.5 text-xs" style={{ background: "var(--surface-raised)" }}>
                  <div className="font-semibold text-zinc-200">Sem {w.week} · {w.intent}</div>
                  <div className="text-zinc-500">Carga {w.load_pct}% · RIR {w.rir_target}</div>
                  {w.volume_note && <div className="mt-0.5 text-zinc-500">{w.volume_note}</div>}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-3">
          {(tr.sessions ?? []).map((s: any, i: number) => (
            <div key={i} className="rounded-lg p-3" style={{ background: "var(--surface-raised)" }}>
              <div className="text-sm font-medium text-zinc-200">{s.day} · {s.name}</div>
              {s.warmup && <p className="mt-1 text-xs text-zinc-500"><b>Calentamiento:</b> {s.warmup}</p>}
              <div className="mt-2 space-y-1.5">
                {(s.exercises ?? []).map((ex: any, j: number) => {
                  const hasDetail = ex.progression_rule || ex.technique_cue || ex.biomech_cue;
                  return (
                    <details key={j} className="rounded-md p-2 text-xs" style={{ background: "var(--surface)" }}>
                      <summary className="cursor-pointer">
                        <span className="font-medium text-zinc-200">{exName(ex.exercise_id)}</span>
                        <span className="ml-1 text-zinc-400">
                          · {ex.sets}×{ex.rep_range} · RIR {ex.rir} · {ex.rest_sec}s
                          {ex.tempo ? ` · tempo ${ex.tempo}` : ""}
                          {ex.start_weight_hint_kg != null ? ` · ~${ex.start_weight_hint_kg} kg` : ""}
                        </span>
                      </summary>
                      {hasDetail && (
                        <div className="mt-1.5 space-y-0.5 border-t pt-1.5 pl-1 text-zinc-500" style={{ borderColor: "var(--line)" }}>
                          {ex.progression_rule && <p><b className="text-zinc-400">Progresión:</b> {ex.progression_rule}</p>}
                          {ex.technique_cue && <p><b className="text-zinc-400">Técnica:</b> {ex.technique_cue}</p>}
                          {ex.biomech_cue && <p><b className="text-zinc-400">Biomecánica:</b> {ex.biomech_cue}</p>}
                        </div>
                      )}
                    </details>
                  );
                })}
              </div>
              {s.cooldown && <p className="mt-2 text-xs text-zinc-500"><b>Vuelta a la calma:</b> {s.cooldown}</p>}
            </div>
          ))}
        </div>

        {tr.cardio && (
          <div className="mt-3 rounded-lg p-3 text-xs" style={{ background: "var(--surface-raised)" }}>
            <div className="flex items-center gap-1.5 font-medium text-zinc-200"><CalendarDays size={13} /> Cardio y NEAT</div>
            <p className="mt-1 text-zinc-400">Pasos diarios objetivo: {tr.cardio.daily_steps}</p>
            {(tr.cardio.sessions ?? []).map((cs: any, i: number) => (
              <p key={i} className="text-zinc-500">{cs.type?.toUpperCase()} · {cs.minutes} min × {cs.times_per_week}/sem{cs.notes ? ` · ${cs.notes}` : ""}</p>
            ))}
          </div>
        )}
        {tr.deload_instructions && (
          <p className="mt-3 text-xs text-zinc-400"><b className="text-zinc-300">Descarga (deload):</b> {tr.deload_instructions}</p>
        )}
      </div>

      <button onClick={generate} disabled={generating} className="btn btn-ghost text-xs">
        <Sparkles size={14} /> {generating ? "Regenerando…" : "Regenerar plan (nueva versión)"}
      </button>
    </div>
  );
}

function SectionTitle({ icon: Icon, title }: { icon: typeof Utensils; title: string }) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <Icon size={16} style={{ color: "var(--brand-accent)" }} />
      <h4 className="text-sm font-semibold text-zinc-200">{title}</h4>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg p-3 text-center" style={{ background: "var(--surface-raised)" }}>
      <div className="text-lg font-bold" style={{ color: "var(--brand-accent)" }}>{value}</div>
      <div className="text-xs text-zinc-500">{label}</div>
    </div>
  );
}

function MealOption({ o, prefix = "" }: { o: any; prefix?: string }) {
  if (!o) return null;
  const m = o.macros ?? {};
  return (
    <div className="rounded-md p-2 text-xs" style={{ background: "var(--surface)" }}>
      <div className="flex flex-wrap items-baseline justify-between gap-1">
        <span className="font-medium text-zinc-200">
          {prefix}{o.key ? `${o.key}. ` : ""}{o.title}
        </span>
        <span className="text-zinc-500">
          {Math.round(m.kcal ?? 0)} kcal · P{Math.round(m.protein_g ?? 0)} / C{Math.round(m.carbs_g ?? 0)} / G{Math.round(m.fat_g ?? 0)}
          {o.prep_minutes != null ? ` · ${o.prep_minutes} min` : ""}
        </span>
      </div>
      {Array.isArray(o.ingredients) && o.ingredients.length > 0 && (
        <ul className="mt-1 list-disc space-y-0.5 pl-4 text-zinc-400">
          {o.ingredients.map((ing: any, i: number) => (
            <li key={i}>{ing.food} · {ing.grams} g <span className="text-zinc-500">({ing.household})</span></li>
          ))}
        </ul>
      )}
      {o.prep && <p className="mt-1 text-zinc-500">{o.prep}</p>}
      {Array.isArray(o.tags) && o.tags.length > 0 && (
        <p className="mt-0.5 text-zinc-600">{o.tags.join(" · ")}</p>
      )}
    </div>
  );
}


===== FILE: frontend/src/components/ClientSummaryTab.tsx =====

import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../lib/api";
import type { ClientOut } from "../types";
import { EmptyState } from "./ui";
import { formatDate } from "../lib/format";

/**
 * Tab Resumen: KPIs del cliente y evolución de peso hacia el objetivo.
 *
 * En Fase 5 el historial de períodos/logs aún no se expone por API (llega en
 * Fase 6 con el portal y los cierres), así que la gráfica usa los anclajes
 * disponibles: peso inicial → peso actual → objetivo. La estructura queda lista
 * para alimentarse de la serie real de períodos cuando exista.
 */
export function ClientSummaryTab({ client }: { client: ClientOut }) {
  const [history, setHistory] = useState<Awaited<ReturnType<typeof api.getClientHistory>> | null>(null);

  useEffect(() => {
    api.getClientHistory(client.id).then(setHistory).catch(() => setHistory(null));
  }, [client.id]);

  // Peso actual real: del historial (último cierre/registro), no del campo fijo.
  const currentWeight = history?.current_weight_kg ?? client.current_weight_kg ?? null;

  // Curva real: peso inicial + el cierre de cada período.
  const series = useMemo(() => {
    const pts: { label: string; peso: number }[] = [];
    if (client.start_weight_kg != null) pts.push({ label: "Inicio", peso: client.start_weight_kg });
    (history?.periods ?? []).forEach((p) => {
      if (p.closing_weight_kg != null) pts.push({ label: `P${p.period_index}`, peso: p.closing_weight_kg });
    });
    if (pts.length === 1 && currentWeight != null && currentWeight !== client.start_weight_kg)
      pts.push({ label: "Actual", peso: currentWeight });
    return pts;
  }, [client.start_weight_kg, history, currentWeight]);

  const accent = getComputedStyle(document.documentElement)
    .getPropertyValue("--brand-accent")
    .trim() || "#6EE7B7";

  return (
    <div className="space-y-5">
      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Kpi label="Peso inicial" value={client.start_weight_kg} unit="kg" />
        <Kpi label="Peso actual" value={currentWeight} unit="kg" />
        <Kpi label="Objetivo" value={client.goal_weight_kg} unit="kg" />
        <Kpi
          label="Diferencia"
          value={
            currentWeight != null && client.start_weight_kg != null
              ? Number((currentWeight - client.start_weight_kg).toFixed(1))
              : null
          }
          unit="kg"
          signed
        />
      </div>

      {/* Gráfica de peso */}
      <div className="card p-5">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-zinc-200">Evolución de peso</h3>
          {client.goal_deadline && (
            <span className="text-xs text-zinc-500">Objetivo para {formatDate(client.goal_deadline)}</span>
          )}
        </div>

        {series.length < 2 ? (
          <EmptyState
            title="Aún no hay datos de seguimiento"
            hint="La curva de peso se construirá con los cierres de período del cliente."
          />
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={series} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <defs>
                  <linearGradient id="pesoFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={accent} stopOpacity={0.25} />
                    <stop offset="100%" stopColor={accent} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="label" stroke="#6b6b76" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#6b6b76" fontSize={12} tickLine={false} axisLine={false} domain={["dataMin - 2", "dataMax + 2"]} />
                <Tooltip
                  contentStyle={{
                    background: "#1a1a24",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 12,
                    fontSize: 13,
                  }}
                  labelStyle={{ color: "#9a9aa6" }}
                />
                {client.goal_weight_kg != null && (
                  <ReferenceLine
                    y={client.goal_weight_kg}
                    stroke={accent}
                    strokeDasharray="4 4"
                    strokeOpacity={0.5}
                    label={{ value: "Objetivo", fill: "#9a9aa6", fontSize: 11, position: "right" }}
                  />
                )}
                <Area type="monotone" dataKey="peso" stroke={accent} strokeWidth={2} fill="url(#pesoFill)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Notas de salud relevantes */}
      {(client.injuries_notes || client.medical_notes || client.food_allergies?.length) && (
        <div className="card p-5">
          <h3 className="mb-3 text-sm font-semibold text-zinc-200">Notas clínicas</h3>
          <div className="space-y-2.5 text-sm">
            {client.injuries_notes && <NoteRow label="Lesiones" value={client.injuries_notes} />}
            {client.medical_notes && <NoteRow label="Patologías" value={client.medical_notes} />}
            {client.food_allergies?.length ? (
              <NoteRow label="Alergias" value={client.food_allergies.join(", ")} />
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}

function Kpi({
  label,
  value,
  unit,
  signed,
}: {
  label: string;
  value: number | null | undefined;
  unit: string;
  signed?: boolean;
}) {
  const display =
    value == null ? "—" : `${signed && value > 0 ? "+" : ""}${value} ${unit}`;
  const tone = signed && value != null ? (value < 0 ? "#6EE7B7" : value > 0 ? "#F7C96E" : undefined) : undefined;
  return (
    <div className="card p-4">
      <p className="text-xl font-semibold" style={{ color: tone ?? "#e7e7ea" }}>
        {display}
      </p>
      <p className="mt-0.5 text-xs text-zinc-500">{label}</p>
    </div>
  );
}

/** Convierte una nota (prosa o líneas con "- ") en puntos para verla ordenada. */
function toBullets(text: string): string[] {
  const t = (text ?? "").trim();
  if (!t) return [];
  // 1) Si ya viene en líneas (formato en puntos de la IA): una por línea.
  let parts = t.split(/\n+/).map((s) => s.replace(/^[-•*]\s*/, "").trim()).filter(Boolean);
  if (parts.length > 1) return parts;
  // 2) Prosa: divide por frases ("… . Siguiente" / "… ; Siguiente").
  parts = t.split(/(?<=[.;])\s+(?=[A-ZÁÉÍÓÚÑ¿¡])/).map((s) => s.trim()).filter(Boolean);
  return parts;
}

function NoteRow({ label, value }: { label: string; value: string }) {
  const items = toBullets(value);
  return (
    <div>
      <p className="mb-1 text-xs uppercase tracking-wide text-zinc-600">{label}</p>
      {items.length > 1 ? (
        <ul className="list-disc space-y-0.5 pl-5 text-zinc-300">
          {items.map((it, i) => <li key={i}>{it}</li>)}
        </ul>
      ) : (
        <p className="text-zinc-300">{items[0] ?? value}</p>
      )}
    </div>
  );
}


===== FILE: frontend/src/components/ClientTrackingTab.tsx =====

import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import type { ClientOut } from "../types";

type Tracking = Awaited<ReturnType<typeof api.getClientTracking>>;

/**
 * Seguimiento del cliente EN TIEMPO REAL para el coach. Hace polling cada 10 s:
 * lo que el cliente registra (diario con series, y revisión quincenal) aparece
 * en cuanto guarda; lo que falta se muestra como "pendiente".
 */
export function ClientTrackingTab({ client }: { client: ClientOut }) {
  const [data, setData] = useState<Tracking | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () =>
      api
        .getClientTracking(client.id)
        .then((d) => alive && setData(d))
        .catch((e) => alive && setErr(e?.message ?? "Error"));
    load();
    timer.current = window.setInterval(load, 10000); // polling → tiempo real
    return () => {
      alive = false;
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [client.id]);

  if (err) return <div className="card p-5 text-sm text-red-400">No se pudo cargar el seguimiento: {err}</div>;
  if (!data) return <div className="card p-5 text-sm opacity-60">Cargando seguimiento…</div>;
  if (!data.has_period)
    return <div className="card p-5 text-sm opacity-60">El cliente aún no tiene un período activo. Créalo en Planificación.</div>;

  const p = data.period!;
  const daily = data.daily ?? [];
  const avg = data.daily_averages;
  const quincenals = data.quincenals ?? [];
  const pct = Math.min(100, Math.round((p.days_elapsed / p.days_total) * 100));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-100">Seguimiento en tiempo real</h3>
        <span className="text-xs text-zinc-500">se actualiza solo · período {p.index}</span>
      </div>

      <div className="card p-4">
        <div className="flex justify-between text-xs text-zinc-400">
          <span>{p.starts_on} → {p.ends_on}</span>
          <span>día {p.days_elapsed}/{p.days_total}</span>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded bg-zinc-700">
          <div className="h-full bg-emerald-500" style={{ width: `${pct}%` }} />
        </div>
        <div className="mt-2 text-xs text-zinc-300">
          Días registrados: <b>{data.days_logged ?? 0}</b> ·{" "}
          Hoy:{" "}
          {data.today_logged
            ? <span className="text-emerald-400">registrado</span>
            : <span className="text-amber-400">pendiente</span>}
        </div>
      </div>

      <div className="card overflow-hidden p-0">
        <div className="border-b border-white/5 px-4 py-2 text-xs font-semibold text-zinc-300">Registros diarios</div>
        {daily.length === 0 ? (
          <p className="p-4 text-sm text-amber-400">Sin registros todavía (pendiente).</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="text-zinc-500">
                <tr className="text-left">
                  <th className="px-3 py-2">Fecha</th><th>Peso</th><th>Sueño</th>
                  <th>Pasos</th><th>Sac.</th><th>Agua</th><th>Dieta</th><th>Series</th>
                </tr>
              </thead>
              <tbody className="text-zinc-200">
                {daily.map((d) => (
                  <tr key={d.date} className="border-t border-white/5">
                    <td className="px-3 py-2">{d.date}</td>
                    <td>{d.weight_kg ?? "—"}</td>
                    <td>{d.sleep_hours ?? "—"}</td>
                    <td className="max-w-[130px] truncate">{d.steps ?? "—"}</td>
                    <td>{d.satiety_1_10 ?? "—"}</td>
                    <td>{d.water_liters ?? "—"}</td>
                    <td>{d.diet_adherence ?? "—"}</td>
                    <td>{d.workout_sets || "—"}</td>
                  </tr>
                ))}
              </tbody>
              {avg && (
                <tfoot>
                  <tr className="border-t border-white/10 font-semibold text-zinc-100" style={{ background: "var(--surface-raised)" }}>
                    <td className="px-3 py-2">Media</td>
                    <td>{avg.weight_kg ?? "—"}</td>
                    <td>{avg.sleep_hours ?? "—"}</td>
                    <td className="max-w-[130px] truncate">{avg.steps != null ? Math.round(avg.steps) : "—"}</td>
                    <td>{avg.satiety_1_10 ?? "—"}</td>
                    <td>{avg.water_liters ?? "—"}</td>
                    <td>{avg.diet_adherence_pct != null ? `${avg.diet_adherence_pct}%` : "—"}</td>
                    <td>{avg.workout_sets ?? "—"}</td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        )}
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-zinc-100">Revisiones quincenales</span>
          <span className="text-xs text-zinc-500">{quincenals.length} recibida{quincenals.length === 1 ? "" : "s"}</span>
        </div>
        {quincenals.length === 0 ? (
          <div className="card p-4 text-xs text-amber-400">Aún no hay revisiones quincenales (pendiente).</div>
        ) : (
          quincenals.map((q, i) => (
            <details key={q.period_index} className="card overflow-hidden p-0" open={i === 0}>
              <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-sm">
                <span className="font-semibold text-zinc-100">
                  Revisión #{q.period_index} · <span className="text-zinc-400">{q.starts_on} → {q.ends_on}</span>
                </span>
                <span className="flex items-center gap-2">
                  {q.feelings_score_10 != null && (
                    <span className="rounded-full px-2 py-0.5 text-xs font-semibold" style={{ background: "rgba(74,123,168,0.18)", color: "#8FB4D6" }}>
                      {q.feelings_score_10}/10
                    </span>
                  )}
                  <span className="text-xs text-emerald-400">{q.analyzed ? "analizada" : "recibida"}</span>
                </span>
              </summary>
              <div className="border-t border-white/5 px-4 py-3">
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <BeforeAfter label="Peso (kg)" before={q.weight_before} after={q.weight_after} lowerBetter />
                  <BeforeAfter label="Cintura (cm)" before={q.waist_before} after={q.waist_after} lowerBetter />
                  <BeforeAfter label="Cadera (cm)" before={q.hip_before} after={q.hip_after} lowerBetter />
                  <BeforeAfter label="Brazo (cm)" before={q.arm_before} after={q.arm_after} />
                  <BeforeAfter label="Muslo (cm)" before={q.thigh_before} after={q.thigh_after} />
                </div>
                <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs text-zinc-300">
                  <span>Adherencia dieta: <b>{q.adherence_diet ?? "—"}/10</b></span>
                  <span>Adherencia entreno: <b>{q.adherence_training ?? "—"}/10</b></span>
                  <span>Comidas libres: <b>{q.free_meals ?? "—"}</b></span>
                  <span>Valoración sensaciones: <b>{q.feelings_score_10 ?? "—"}/10</b></span>
                  {q.feelings && (
                    <span className="col-span-2">
                      Sensaciones: {Object.entries(q.feelings).map(([k, v]) => `${k} ${v}/5`).join(" · ")}
                    </span>
                  )}
                  {q.changes && <span className="col-span-2">Cambios: {q.changes}</span>}
                  {q.hardest && <span className="col-span-2">Le cuesta: {q.hardest}</span>}
                  {q.next_goal && <span className="col-span-2">Objetivo: {q.next_goal}</span>}
                  {q.questions && <span className="col-span-2">Dudas: {q.questions}</span>}
                </div>
              </div>
            </details>
          ))
        )}
      </div>
    </div>
  );
}

/** Antes → después con delta coloreado. */
function BeforeAfter({ label, before, after, lowerBetter }: {
  label: string; before: number | null; after: number | null; lowerBetter?: boolean;
}) {
  const delta = before != null && after != null ? Math.round((after - before) * 10) / 10 : null;
  const good = delta != null && (lowerBetter ? delta < 0 : delta > 0);
  const bad = delta != null && delta !== 0 && !good;
  return (
    <div className="rounded-lg p-2.5" style={{ background: "var(--surface-raised)" }}>
      <div className="text-[11px] text-zinc-500">{label}</div>
      <div className="mt-0.5 flex items-baseline gap-1.5 text-sm text-zinc-100">
        <span className="text-zinc-400">{before ?? "—"}</span>
        <span className="text-zinc-600">→</span>
        <span className="font-semibold">{after ?? "—"}</span>
        {delta != null && delta !== 0 && (
          <span className="text-xs" style={{ color: good ? "var(--brand-accent)" : bad ? "#F77E7E" : "#a1a1aa" }}>
            {delta > 0 ? "+" : ""}{delta}
          </span>
        )}
      </div>
    </div>
  );
}


===== FILE: frontend/src/components/ui.tsx =====

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { AlertTriangle, Check, Loader2, X } from "lucide-react";
import type { ClientStatus } from "../types";
import { STATUS_LABEL, STATUS_TONE } from "../lib/format";

/* ---------------------------------------------------------- StatusBadge ---- */

export function StatusBadge({ status }: { status: ClientStatus }) {
  const tone = STATUS_TONE[status];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
      style={{ background: `${tone}1a`, color: tone }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: tone }} />
      {STATUS_LABEL[status]}
    </span>
  );
}

/* -------------------------------------------------------------- Spinner ---- */

export function Spinner({ className = "" }: { className?: string }) {
  return <Loader2 className={`animate-spin ${className}`} size={18} />;
}

export function PageLoader() {
  return (
    <div className="flex h-full min-h-[300px] items-center justify-center text-zinc-500">
      <Spinner className="text-zinc-400" />
    </div>
  );
}

/* ----------------------------------------------------------- EmptyState ---- */

export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string;
  hint: string;
  action?: ReactNode;
}) {
  // Un estado vacío es una invitación a actuar (skill): título + siguiente paso.
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed py-16 text-center"
      style={{ borderColor: "var(--line-strong)" }}>
      <p className="text-sm font-medium text-zinc-200">{title}</p>
      <p className="mt-1 max-w-xs text-sm text-zinc-500">{hint}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

/* ---------------------------------------------------------------- Toast ---- */

type Toast = { id: number; message: string; tone: "ok" | "error" };
type ToastCtx = { push: (message: string, tone?: "ok" | "error") => void };

const ToastContext = createContext<ToastCtx | null>(null);

export function useToast(): ToastCtx {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast fuera de ToastProvider");
  return ctx;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const push = useCallback((message: string, tone: "ok" | "error" = "ok") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, message, tone }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000);
  }, []);

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="animate-rise flex items-center gap-2.5 rounded-xl border px-4 py-3 text-sm shadow-xl"
            style={{
              background: "var(--surface-raised)",
              borderColor: t.tone === "error" ? "#F77E7E55" : "var(--line-strong)",
            }}
          >
            <span
              className="flex h-5 w-5 items-center justify-center rounded-full"
              style={{ background: t.tone === "error" ? "#F77E7E22" : "#6EE7B722" }}
            >
              {t.tone === "error" ? (
                <AlertTriangle size={13} color="#F77E7E" />
              ) : (
                <Check size={13} color="#6EE7B7" />
              )}
            </span>
            <span className="text-zinc-100">{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/* -------------------------------------------------------- ConfirmDialog ---- */

export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel,
  destructive,
  requireText,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  body: ReactNode;
  confirmLabel: string;
  destructive?: boolean;
  requireText?: string; // si se define, hay que teclearlo para confirmar
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const [typed, setTyped] = useState("");

  useEffect(() => {
    if (open) setTyped("");
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onCancel();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  if (!open) return null;
  const canConfirm = !requireText || typed === requireText;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onCancel}>
      <div
        className="card animate-rise w-full max-w-md p-6"
        style={{ background: "var(--surface-raised)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <h3 className="text-base font-semibold text-zinc-100">{title}</h3>
          <button onClick={onCancel} className="text-zinc-500 hover:text-zinc-300">
            <X size={18} />
          </button>
        </div>
        <div className="mt-2 text-sm leading-relaxed text-zinc-400">{body}</div>
        {requireText && (
          <input
            autoFocus
            className="input mt-4"
            placeholder={requireText}
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
          />
        )}
        <div className="mt-6 flex justify-end gap-2">
          <button className="btn btn-ghost" onClick={onCancel}>
            Cancelar
          </button>
          <button
            className="btn btn-primary"
            style={destructive ? { background: "#F77E7E" } : undefined}
            disabled={!canConfirm}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}


===== FILE: frontend/src/lib/api.ts =====

/**
 * Capa de acceso a la API.
 *
 * Un único cliente fetch que adjunta el JWT, parsea JSON y normaliza errores.
 * Cada método mapea a un endpoint real de las Fases 2–4. Los tipos vienen de
 * types.ts (espejo de los schemas Pydantic).
 */

import type {
  BrandConfigOut,
  ChangeRequestOut,
  ClientCreate,
  ClientCreatedOut,
  ClientOut,
  ClientStatus,
  ExerciseOut,
  MeOut,
  PortalLinkOut,
  TokenOut,
} from "../types";

const TOKEN_KEY = "fitness_coach_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  opts: { raw?: boolean } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let payload: BodyInit | undefined;
  if (body instanceof FormData) {
    payload = body;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(`/api${path}`, { method, headers, body: payload });

  if (res.status === 401) {
    clearToken();
    // Señaliza a la app que debe volver al login.
    window.dispatchEvent(new CustomEvent("auth:expired"));
    throw new ApiError(401, "Sesión caducada");
  }

  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") detail = data.detail;
      else if (Array.isArray(data.detail)) detail = data.detail.map((d: any) => d.msg).join("; ");
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new ApiError(res.status, detail);
  }

  if (opts.raw) return res as unknown as T;
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  // --- auth ---
  login: (username: string, password: string) =>
    request<TokenOut>("POST", "/auth/login", { username, password }),
  me: () => request<MeOut>("GET", "/auth/me"),

  // --- clients ---
  listClients: (params: { status?: ClientStatus; q?: string } = {}) => {
    const qs = new URLSearchParams();
    if (params.status) qs.set("status", params.status);
    if (params.q) qs.set("q", params.q);
    const suffix = qs.toString() ? `?${qs}` : "";
    return request<ClientOut[]>("GET", `/clients${suffix}`);
  },
  getClient: (id: number) => request<ClientOut>("GET", `/clients/${id}`),
  createClient: (body: ClientCreate) =>
    request<ClientCreatedOut>("POST", "/clients", body),
  updateClient: (id: number, patch: Partial<ClientOut>) =>
    request<ClientOut>("PATCH", `/clients/${id}`, patch),
  portalLink: (id: number) =>
    request<PortalLinkOut>("GET", `/clients/${id}/portal-link`),
  regeneratePortalToken: (id: number) =>
    request<PortalLinkOut>("POST", `/clients/${id}/portal-token/regenerate`),
  exportClientUrl: (id: number) => `/api/clients/${id}/export`,
  listPlans: (clientId: number) =>
    request<{
      id: number; month_index: number; version: number; status: string;
      nutrition_json: any; training_json: any; education_json: any;
      guardrail_flags: string[] | null;
    }[]>("GET", `/clients/${clientId}/plans`),
  planDocumentUrl: (planId: number) => `/api/plans/${planId}/document`,
  listClientDocuments: (clientId: number) =>
    request<{ name: string; size_kb: number; uploaded_at: number }[]>(
      "GET", `/clients/${clientId}/documents`),
  uploadClientDocument: (clientId: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<{ name: string; read_ok: boolean; read_error: string | null }>(
      "POST", `/clients/${clientId}/documents`, fd);
  },
  clientDocumentUrl: (clientId: number, name: string) =>
    `/api/clients/${clientId}/documents/${encodeURIComponent(name)}`,
  listClientPhotos: (clientId: number) =>
    request<{ id: number; kind: string; period_id: number | null; taken_at: string }[]>(
      "GET", `/clients/${clientId}/photos`),
  clientPhotoUrl: (clientId: number, photoId: number) =>
    `/api/clients/${clientId}/photos/${photoId}`,
  getClientHistory: (clientId: number) =>
    request<{
      start_weight_kg: number | null; current_weight_kg: number | null; goal_weight_kg: number | null;
      remaining_to_goal_kg: number | null;
      measures: Record<"waist" | "hip" | "arm" | "thigh", { before: number | null; after: number | null }>;
      total_strength_gain_pct: number | null;
      periods: {
        period_index: number; starts_on: string; ends_on: string; status: string;
        closing_weight_kg: number | null; weight_delta_kg: number | null; adherence_pct: number | null;
        best_e1rm_kg: number | null; strength_gain_pct: number | null; distance_to_goal_kg: number | null;
        waist_cm: number | null; hip_cm: number | null; arm_cm: number | null; thigh_cm: number | null;
        feedback_id: number | null; feedback_sent: boolean;
      }[];
      plans: { id: number; month_index: number; version: number; status: string }[];
    }>("GET", `/clients/${clientId}/history`),
  getClientTracking: (clientId: number) =>
    request<{
      has_period: boolean;
      period?: { index: number; starts_on: string; ends_on: string; status: string; days_elapsed: number; days_total: number };
      daily?: {
        date: string; weight_kg: number | null; sleep_hours: number | null; steps: string | null;
        satiety_1_10: number | null; water_liters: number | null; diet_adherence: string | null;
        free_notes: string | null; workout_sets: number;
      }[];
      daily_averages?: {
        weight_kg: number | null; sleep_hours: number | null; steps: number | null;
        satiety_1_10: number | null; water_liters: number | null; workout_sets: number | null;
        diet_adherence_pct: number | null;
      };
      days_logged?: number;
      today_logged?: boolean;
      quincenal_pending?: boolean;
      quincenals?: {
        period_index: number; starts_on: string; ends_on: string; status: string; analyzed: boolean;
        weight_before: number | null; weight_after: number | null;
        waist_before: number | null; waist_after: number | null;
        hip_before: number | null; hip_after: number | null;
        arm_before: number | null; arm_after: number | null;
        thigh_before: number | null; thigh_after: number | null;
        feelings: Record<string, number> | null; feelings_score_10: number | null;
        adherence_diet: number | null; adherence_training: number | null;
        free_meals: number | null; changes: string | null; hardest: string | null;
        next_goal: string | null; questions: string | null;
      }[];
    }>("GET", `/clients/${clientId}/tracking`),
  anamnesisTemplateUrl: () => `/api/anamnesis-template`,
  generatePlan: (clientId: number, monthIndex = 1) =>
    request<{
      id: number; month_index: number; version: number; status: string;
      guardrail_flags: string[];
      nutrition: any; training: any; education: any;
    }>("POST", `/clients/${clientId}/generate-plan?month_index=${monthIndex}`),
  adaptPlan: (clientId: number) =>
    request<{ id: number; month_index: number; version: number; status: string }>(
      "POST", `/clients/${clientId}/adapt-plan`),
  publishPlan: (planId: number) =>
    request<{ status: string }>("POST", `/plans/${planId}/publish`),
  updatePlan: (planId: number, patch: { nutrition_json?: any; training_json?: any; education_json?: any }) =>
    request<{ id: number; status: string; nutrition_json: any; training_json: any; education_json: any; guardrail_flags: string[] | null; month_index: number; version: number }>(
      "PATCH", `/plans/${planId}`, patch),
  readAnamnesis: (clientId: number) =>
    request<{ extracted: any; deep_analysis: string | null; message: string }>(
      "POST", `/clients/${clientId}/read-anamnesis`),

  // --- feedback (cierre → informe) ---
  createPeriod: (clientId: number, planId: number, startsOn: string, days = 14) =>
    request<{ period_id: number; period_index: number; starts_on: string; ends_on: string }>(
      "POST", `/clients/${clientId}/periods`, { plan_id: planId, starts_on: startsOn, days }),
  listPeriods: (clientId: number) =>
    request<{
      id: number; plan_id: number | null; period_index: number; starts_on: string; ends_on: string; status: string;
      closing_weight_kg: number | null; closing_rating: number | null;
      closing_hardest: string | null; closing_questions: string | null;
      closing_waist_cm: number | null; closing_hip_cm: number | null;
      closing_arm_cm: number | null; closing_thigh_cm: number | null;
      feedback_id: number | null;
    }[]>("GET", `/clients/${clientId}/periods`),
  generateFeedback: (periodId: number) =>
    request<{ feedback_id: number; period_id: number; kind: string; content: any }>(
      "POST", `/periods/${periodId}/feedback`),
  getFeedback: (docId: number) =>
    request<{ id: number; period_id: number; kind: string; content: any; sent_at: string | null }>(
      "GET", `/feedback/${docId}`),
  sendFeedback: (docId: number) =>
    request<{ sent: boolean; sent_at: string }>("POST", `/feedback/${docId}/send`),
  editFeedback: (docId: number, patch: {
    natural_analysis?: string; changes_bullets?: string[]; answers?: string | null;
    next_objectives?: string[]; closing_message?: string;
  }) => request<{ id: number; content: any; sent_at: string | null }>("PATCH", `/feedback/${docId}`, patch),
  getPeriodMetrics: (periodId: number) =>
    request<{
      period_index: number; status: string;
      weight: { start_kg: number | null; end_kg: number | null; delta_kg: number | null; weekly_rate_kg: number | null };
      body_weight_now_kg: number | null; goal_weight_kg: number | null; distance_to_goal_kg: number | null;
      adherence: { diet_pct: number; log_pct: number; days_logged: number; period_days: number };
      strength: { name: string; e1rm_kg: number; delta_kg: number | null }[];
    }>("GET", `/periods/${periodId}/metrics`),
  feedbackDocumentUrl: (docId: number) => `/api/feedback/${docId}/document`,

  // --- brand ---
  getBrand: () => request<BrandConfigOut>("GET", "/brand"),
  updateBrand: (body: Omit<BrandConfigOut, "id" | "logo_path">) =>
    request<BrandConfigOut>("PUT", "/brand", body),
  uploadLogo: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<BrandConfigOut>("POST", "/brand/logo", fd);
  },

  // --- exercises ---
  listExercises: (params: { q?: string; pattern?: string; muscle?: string; include_archived?: boolean } = {}) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.pattern) qs.set("pattern", params.pattern);
    if (params.muscle) qs.set("muscle", params.muscle);
    if (params.include_archived) qs.set("include_archived", "true");
    const suffix = qs.toString() ? `?${qs}` : "";
    return request<ExerciseOut[]>("GET", `/exercises${suffix}`);
  },
  archiveExercise: (id: number) =>
    request<ExerciseOut>("POST", `/exercises/${id}/archive`),
  restoreExercise: (id: number) =>
    request<ExerciseOut>("POST", `/exercises/${id}/restore`),
  updateExercise: (id: number, patch: Partial<ExerciseOut>) =>
    request<ExerciseOut>("PATCH", `/exercises/${id}`, patch),
};

export type { ChangeRequestOut };


===== FILE: frontend/src/lib/format.ts =====

/**
 * Utilidades de presentación compartidas.
 *
 * Mapas de etiquetas en castellano (todo lo de cara al usuario va en español),
 * formateadores de fecha/número y helpers de color de estado. Centralizar esto
 * evita que cada vista invente sus propias traducciones.
 */

import type { ClientStatus, DietMode, GoalType, Level, TrainingPlace } from "../types";

export const STATUS_LABEL: Record<ClientStatus, string> = {
  onboarding: "Onboarding",
  active: "Activo",
  awaiting_feedback: "Esperando cierre",
  at_risk: "En riesgo",
  review_pending: "Revisión pendiente",
  inactive: "Inactivo",
};

// Color de acento por estado (para badges y puntos). Tonos sobrios sobre fondo oscuro.
export const STATUS_TONE: Record<ClientStatus, string> = {
  onboarding: "#8B9DF7", // índigo suave: aún configurándose
  active: "#6EE7B7", // acento de marca: todo en marcha
  awaiting_feedback: "#F7C96E", // ámbar: requiere acción próxima
  at_risk: "#F77E7E", // rojo: atención
  review_pending: "#C99EF7", // violeta: en cola del coach
  inactive: "#6B6B76", // gris: dormido
};

export const GOAL_LABEL: Record<GoalType, string> = {
  fat_loss: "Pérdida de grasa",
  muscle_gain: "Ganancia muscular",
  recomp: "Recomposición",
};

export const LEVEL_LABEL: Record<Level, string> = {
  beginner: "Principiante",
  intermediate: "Intermedio",
  advanced: "Avanzado",
};

export const PLACE_LABEL: Record<TrainingPlace, string> = {
  gym: "Gimnasio",
  home: "Casa",
  outdoor: "Exterior",
};

export const DIET_LABEL: Record<DietMode, string> = {
  flexible_7: "Flexible (7 opciones)",
  strict: "Estricta",
};

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" });
}

export function relativeDays(iso: string | null | undefined): string {
  if (!iso) return "—";
  const diff = Math.round((Date.now() - new Date(iso).getTime()) / 86400000);
  if (diff === 0) return "hoy";
  if (diff === 1) return "ayer";
  if (diff < 0) return `en ${-diff} días`;
  return `hace ${diff} días`;
}

export function ageFrom(birthIso: string | null): number | null {
  if (!birthIso) return null;
  const b = new Date(birthIso);
  const now = new Date();
  let age = now.getFullYear() - b.getFullYear();
  const m = now.getMonth() - b.getMonth();
  if (m < 0 || (m === 0 && now.getDate() < b.getDate())) age--;
  return age;
}

export function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}


===== FILE: frontend/src/hooks/useAuth.tsx =====

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api, clearToken, getToken, setToken } from "../lib/api";
import type { MeOut } from "../types";

interface AuthState {
  user: MeOut | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth fuera de AuthProvider");
  return ctx;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeOut | null>(null);
  const [loading, setLoading] = useState(true);

  // Validación inicial: si hay token, confirma que sigue vigente con /me.
  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  // Sesión caducada (lanzado por la capa de API ante un 401).
  useEffect(() => {
    const onExpired = () => setUser(null);
    window.addEventListener("auth:expired", onExpired);
    return () => window.removeEventListener("auth:expired", onExpired);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const { access_token } = await api.login(username, password);
    setToken(access_token);
    const me = await api.me();
    setUser(me);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}


===== FILE: frontend/src/hooks/useBrand.tsx =====

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../lib/api";
import type { BrandConfigOut } from "../types";

interface BrandState {
  brand: BrandConfigOut | null;
  reload: () => void;
}

const BrandContext = createContext<BrandState>({ brand: null, reload: () => {} });

export function useBrand(): BrandState {
  return useContext(BrandContext);
}

/**
 * Aplica la marca en runtime: el acento configurable se inyecta como variable
 * CSS (--brand-accent), de modo que toda la app y el portal reflejan al
 * instante los cambios de Settings (H.1), sin recompilar.
 */
export function BrandProvider({ children }: { children: ReactNode }) {
  const [brand, setBrand] = useState<BrandConfigOut | null>(null);

  const load = () => {
    api
      .getBrand()
      .then((b) => {
        setBrand(b);
        document.documentElement.style.setProperty("--brand-accent", b.color_primary);
      })
      .catch(() => {
        /* sin marca todavía: se mantienen los defaults del CSS */
      });
  };

  useEffect(load, []);

  return (
    <BrandContext.Provider value={{ brand, reload: load }}>{children}</BrandContext.Provider>
  );
}
