import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AlertTriangle, CalendarPlus, CheckCircle2, ClipboardList, Copy, CreditCard, Mail, MessageCircle, Search, Send, UserPlus, ChevronRight, Flag } from "lucide-react";
import { useDismiss, useModalFocus } from "../lib/useDismiss";
import { api, ApiError, keepIfSame, REFRESH_MS } from "../lib/api";
import type { ClientCreatedOut, ClientOut } from "../types";
import { EmptyState, PageLoader, StatusBadge, useToast } from "../components/ui";
import { Avatar } from "./DashboardPage";
import { GOAL_LABEL, goalReviewDue, relativeDays } from "../lib/format";
import { onboardingMessage, openWhatsApp, portalAccessMessage, waPhone } from "../lib/whatsapp";
import { BILLING_PERIODS, PACKAGES, PACKAGE_ORDER, pkg } from "../lib/packages";
import type { BillingPeriod, PackageTier } from "../types";

/** CARPETAS de la cartera según LO QUE FALTA de cada cliente (agrupado como
 *  las alertas): un lugar con todos y luego por la acción que requieren. Cada
 *  carpeta tiene su color e icono propios. Un cliente puede estar en varias
 *  (p. ej. falta pago Y falta anamnesis). */
type Category = "all" | "anamnesis" | "plan" | "revision" | "pago" | "aldia";
const CATEGORIES: {
  id: Category; label: string; color: string; icon: typeof UserPlus | null;
}[] = [
  { id: "all", label: "Todos", color: "var(--brand-accent)", icon: null },
  { id: "anamnesis", label: "Falta anamnesis", color: "#6366F1", icon: ClipboardList },
  { id: "plan", label: "Falta planificación", color: "#E8833A", icon: CalendarPlus },
  { id: "revision", label: "Falta revisión", color: "#8B5CF6", icon: Flag },
  { id: "pago", label: "Falta pago", color: "#2E7D46", icon: CreditCard },
  { id: "aldia", label: "Al día", color: "#2E5E8C", icon: CheckCircle2 },
];

function inCategory(c: ClientOut, cat: Category): boolean {
  if (c.status === "inactive") return cat === "all";
  switch (cat) {
    case "all": return true;
    // Sin anamnesis registrada (sin objetivo = el wizard/PDF no ha entrado aún)
    case "anamnesis": return !c.goal_type;
    // Anamnesis lista pero sin planificación activa
    case "plan": return !!c.goal_type && !c.has_published_plan;
    // Revisión quincenal recibida, pendiente de feedback/adaptación
    case "revision": return c.status === "review_pending";
    // Pago del plan pendiente (informativo, del enlace de Stripe)
    case "pago": return c.payment_status === "pending";
    // Nada pendiente: plan activo, sin revisión por atender y pago al día
    case "aldia":
      return !!c.has_published_plan && c.status !== "review_pending"
        && c.payment_status !== "pending";
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
      .then((cs) => setClients((prev) => keepIfSame(prev, cs)))  // sin re-render si nada cambió
      .catch(() => setClients([]));
  }, [q]);

  useEffect(() => {
    const t = setTimeout(load, 200); // debounce de la búsqueda
    return () => clearTimeout(t);
  }, [load]);

  // Refresco cada 3 s (pestaña visible): carpetas y badges siempre al día
  useEffect(() => {
    const t = window.setInterval(() => {
      if (!document.hidden) load();
    }, REFRESH_MS);
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
          {CATEGORIES.map(({ id, label, color, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setFilter(id)}
              className="tap flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
              style={
                filter === id
                  ? { background: color, color: "#fff" }
                  : {
                      background: `color-mix(in srgb, ${color} 9%, var(--surface))`,
                      color,
                      boxShadow: `inset 0 0 0 1px color-mix(in srgb, ${color} 25%, transparent)`,
                    }
              }
            >
              {Icon && <Icon size={12} />}
              {label}
              {clients !== null && counts[id] > 0 && (
                <span className="opacity-75">{counts[id]}</span>
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

/** Etiqueta del plan/paquete contratado por el cliente (Start/Full/Pro). */
function PackageBadge({ tier }: { tier: string }) {
  const p = pkg(tier);
  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold"
      style={{ background: `color-mix(in srgb, ${p.color} 14%, transparent)`, color: p.color }}
      title={p.includes}
    >
      {p.short}
    </span>
  );
}

/** Estado de pago del plan (Stripe): pagado / pendiente. */
function PaymentBadge({ status }: { status: string }) {
  const paid = status === "paid";
  const color = paid ? "#2E7D46" : "#C2453A";
  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold"
      style={{ background: `color-mix(in srgb, ${color} 14%, transparent)`, color }}
      title={paid ? "Pago realizado" : "Pago pendiente"}
    >
      {paid ? "Pagado" : "Pago pendiente"}
    </span>
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
        <div className="flex items-center gap-1.5">
          <p className="truncate text-sm font-medium text-zinc-100">{c.full_name}</p>
          <PackageBadge tier={c.package_tier} />
          <PaymentBadge status={c.payment_status} />
        </div>
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
  const navigate = useNavigate();
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
            // Toda la fila es clicable: pulsar en cualquier celda entra al perfil.
            <tr
              key={c.id}
              onClick={() => navigate(`/clientes/${c.id}?tab=seguimiento`)}
              role="link"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  navigate(`/clientes/${c.id}?tab=seguimiento`);
                }
              }}
              className="cursor-pointer border-t transition-colors hover:bg-[var(--surface-raised)]"
              style={{ borderColor: "var(--line)", background: i % 2 ? "rgba(38,33,26,0.02)" : undefined }}
            >
              <td className="px-4 py-3">
                <div className="flex items-center gap-3">
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
                    <div className="flex items-center gap-1.5">
                      <p className="font-medium text-zinc-100">{c.full_name}</p>
                      <PackageBadge tier={c.package_tier} />
                      <PaymentBadge status={c.payment_status} />
                    </div>
                    <p className="text-xs text-zinc-500">{c.email}</p>
                  </div>
                </div>
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
  const [tier, setTier] = useState<PackageTier>("full");
  const [period, setPeriod] = useState<BillingPeriod>("1m");
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<ClientCreatedOut | null>(null);
  // Estado del correo de acceso enviado al crear (y actualizable con "Reenviar").
  const [accessStatus, setAccessStatus] = useState<ClientCreatedOut["portal_access"]>(null);
  const [password, setPassword] = useState<string | null>(null);
  const [resending, setResending] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  useDismiss(dialogRef, onClose); // fuera + ESC, en una sola pulsación
  useModalFocus(dialogRef, true); // foco atrapado; al cerrar vuelve al botón

  async function submit() {
    if (!name || !email || busy) return;
    setBusy(true);
    try {
      const res = await api.createClient({
        full_name: name, email, phone: phone || null,
        package_tier: tier, billing_period: period,
      });
      setCreated(res);
      setAccessStatus(res.portal_access);
      onCreated();
      toast.push("Cliente creado");
    } catch (e) {
      toast.push(e instanceof ApiError ? e.message : "No se pudo crear el cliente", "error");
      setBusy(false);
    }
  }

  // (Re)envía el correo de acceso al portal al cliente. Si el correo está
  // desactivado o falla, muestra la contraseña para que el coach pueda dársela.
  async function resendEmail() {
    if (!created || resending) return;
    setResending(true);
    try {
      const r = await api.sendPortalAccess(created.client.id);
      setAccessStatus(r.status as ClientCreatedOut["portal_access"]);
      if (r.status === "sent") {
        setPassword(null);
        toast.push("Correo de acceso enviado al cliente por email.");
      } else if (r.password) {
        setPassword(r.password);
        toast.push(
          r.status === "disabled"
            ? "Envío de correos desactivado: usa la contraseña para dársela tú."
            : "El email no salió: usa la contraseña para dársela tú.",
          "error",
        );
      } else {
        toast.push("No se pudo enviar el acceso", "error");
      }
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo enviar el acceso", "error");
    } finally {
      setResending(false);
    }
  }

  function copy(text: string) {
    navigator.clipboard.writeText(text);
    toast.push("Enlace copiado");
  }

  // Abre WhatsApp del cliente con el acceso al portal ya escrito. Necesita el
  // teléfono (el que se puso en el alta); si no hay, avisa.
  function sendPortalWhatsApp() {
    if (!created) return;
    const digits = waPhone(created.client.phone ?? phone);
    if (!digits) {
      toast.push("Añade el teléfono del cliente para enviarlo por WhatsApp", "error");
      return;
    }
    openWhatsApp(digits, portalAccessMessage(created.client.full_name, created.links.portal_url));
    toast.push("WhatsApp abierto con el acceso al portal — dale a enviar");
  }

  const [sendingOnb, setSendingOnb] = useState(false);
  // Envío combinado de ARRANQUE: enlace de pago + anamnesis en un solo mensaje,
  // por WhatsApp (Pro) o email (Start/Full) según el plan del cliente.
  async function sendOnboarding() {
    if (!created || sendingOnb) return;
    const info = pkg(created.client.package_tier);
    const payUrl = api.payLinkUrl(created.links.portal_token);
    if (info.delivery === "whatsapp") {
      const digits = waPhone(created.client.phone ?? phone);
      if (!digits) {
        toast.push("Añade el teléfono del cliente para enviarlo por WhatsApp", "error");
        return;
      }
      openWhatsApp(digits, onboardingMessage(
        created.client.full_name, info.label, payUrl,
        `${window.location.origin}/anamnesis/${created.links.portal_token}`));
      toast.push("WhatsApp abierto con el pago y la anamnesis — dale a enviar");
      return;
    }
    setSendingOnb(true);
    try {
      const r = await api.sendOnboarding(created.client.id);
      if (r.status === "sent") toast.push("Enviado por email: pago + anamnesis");
      else if (r.status === "disabled") toast.push("El email está desactivado: no se envió", "error");
      else toast.push("No se pudo enviar el email", "error");
    } catch {
      toast.push("No se pudo enviar", "error");
    } finally {
      setSendingOnb(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Nuevo cliente"
        // COLUMNA flex con cabecera fija, cuerpo desplazable y BOTONES fijos
        // abajo: el modal nunca supera la altura de la ventana y "Crear cliente"
        // queda SIEMPRE visible (centrar un modal más alto que la pantalla
        // recortaba arriba y abajo aunque tuviera scroll).
        className="card animate-rise flex max-h-[calc(100dvh-2rem)] w-full max-w-md flex-col overflow-hidden"
        style={{ background: "var(--surface-raised)" }}
      >
        {!created ? (
          <>
            <div className="shrink-0 p-6 pb-3">
              <h3 className="text-base font-semibold text-zinc-100">Nuevo cliente</h3>
              <p className="mt-1 text-sm text-zinc-500">
                Al crearlo se le enviará por email su acceso al portal (usuario, contraseña
                y enlace). Solo necesitas nombre y email; el teléfono es para WhatsApp.
              </p>
            </div>
            <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-6 py-1">
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
              <div>
                <label className="label">Plan contratado</label>
                <div className="mt-1 space-y-2">
                  {PACKAGE_ORDER.map((t) => {
                    const p = PACKAGES[t];
                    const sel = tier === t;
                    return (
                      <button
                        key={t}
                        type="button"
                        onClick={() => setTier(t)}
                        aria-pressed={sel}
                        className="flex w-full items-start gap-2.5 rounded-xl border p-3 text-left transition-colors"
                        style={{
                          borderColor: sel ? p.color : "var(--line-strong)",
                          background: sel ? `color-mix(in srgb, ${p.color} 8%, transparent)` : "transparent",
                        }}
                      >
                        <span
                          className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border"
                          style={{ borderColor: sel ? p.color : "var(--line-strong)" }}
                        >
                          {sel && <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />}
                        </span>
                        <span className="min-w-0">
                          <span className="flex flex-wrap items-center gap-x-1.5">
                            <span className="text-sm font-semibold text-zinc-100">{p.label}</span>
                            <span className="text-xs text-zinc-500">· {p.tagline}</span>
                          </span>
                          <span className="mt-0.5 block text-xs text-zinc-500">{p.includes}</span>
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
              <div>
                <label className="label">Duración</label>
                <p className="text-xs text-zinc-500">
                  Cómo contrata el plan: decide el precio que pagará en su enlace de pago.
                </p>
                <div className="mt-1.5 grid grid-cols-3 gap-2">
                  {BILLING_PERIODS.map((b) => {
                    const sel = period === b.value;
                    return (
                      <button
                        key={b.value}
                        type="button"
                        onClick={() => setPeriod(b.value)}
                        aria-pressed={sel}
                        className="rounded-xl border px-2 py-2 text-sm font-medium transition-colors"
                        style={{
                          borderColor: sel ? "var(--brand-accent)" : "var(--line-strong)",
                          background: sel ? "color-mix(in srgb, var(--brand-accent) 10%, transparent)" : "transparent",
                          color: sel ? "var(--brand-accent)" : undefined,
                        }}
                      >
                        {b.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
            {/* Pie FIJO: los botones quedan siempre a la vista, no dependen del
                scroll del formulario. */}
            <div className="shrink-0 flex justify-end gap-2 border-t p-6 pt-4"
              style={{ borderColor: "var(--line)" }}>
              <button className="btn btn-ghost" onClick={onClose}>
                Cancelar
              </button>
              <button className="btn btn-primary" disabled={busy || !name || !email} onClick={submit}>
                Crear cliente
              </button>
            </div>
          </>
        ) : (
          <div className="min-h-0 flex-1 overflow-y-auto p-6">
            <h3 className="text-base font-semibold text-zinc-100">Cliente creado</h3>

            {/* Envío COMBINADO de arranque: pago del plan + anamnesis en un solo
                mensaje, por WhatsApp (Pro) o email (Start/Full) según el plan. */}
            <div className="mt-3 rounded-xl border p-3"
              style={{ borderColor: "var(--brand-accent)", background: "color-mix(in srgb, var(--brand-accent) 8%, transparent)" }}>
              <p className="text-sm font-semibold text-zinc-100">Enviar pago + anamnesis</p>
              <p className="mt-0.5 text-xs text-zinc-500">
                Un solo mensaje con el enlace de pago de su plan ({pkg(created.client.package_tier).short})
                y el de la anamnesis, con la instrucción de devolverla rellena.
              </p>
              <button onClick={sendOnboarding} disabled={sendingOnb} className="btn btn-primary mt-2 w-full justify-center">
                {pkg(created.client.package_tier).delivery === "whatsapp"
                  ? <><MessageCircle size={15} /> Enviar por WhatsApp</>
                  : <><Mail size={15} /> {sendingOnb ? "Enviando…" : "Enviar por email"}</>}
              </button>
            </div>

            {/* Correo de acceso al portal, enviado AUTOMÁTICAMENTE al crear */}
            <div className="mt-3">
              <PortalAccessResult status={accessStatus} email={created.client.email} password={password} />
              <button className="btn btn-ghost mt-2 text-xs" disabled={resending} onClick={resendEmail}>
                <Send size={13} className="text-zinc-500" />
                {resending ? "Enviando…" : accessStatus === "sent" ? "Reenviar correo" : "Enviar correo de nuevo"}
              </button>
            </div>

            {/* Enlace del PORTAL del cliente (su app / web): para enviarlo también
                por WhatsApp además del correo automático. Es el enlace de la web,
                donde el cliente primero rellena la anamnesis y luego hace el
                seguimiento y ve su planificación. */}
            <p className="mt-4 text-xs text-zinc-500">
              Enlace del portal del cliente (para enviarlo también por WhatsApp, opcional):
            </p>
            <div className="mt-1.5 flex items-center gap-2 rounded-xl border p-3" style={{ borderColor: "var(--line-strong)" }}>
              <code className="flex-1 truncate text-xs text-zinc-300">{created.links.portal_url}</code>
              <button className="btn btn-ghost px-2.5 py-1.5" aria-label="Copiar enlace" onClick={() => copy(created.links.portal_url)}>
                <Copy size={14} />
              </button>
            </div>
            <button className="btn btn-ghost mt-2 w-full justify-center text-xs" onClick={sendPortalWhatsApp}>
              <MessageCircle size={14} style={{ color: "#25D366" }} /> Enviar por WhatsApp
            </button>

            <div className="mt-6 flex justify-end">
              <button className="btn btn-primary" onClick={onClose}>
                Hecho
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/** Resultado del envío del acceso al portal en el modal de alta: verde si salió,
 *  ámbar/rojo si está desactivado o falló (con la contraseña para dictarla). */
function PortalAccessResult({
  status, email, password,
}: { status: ClientCreatedOut["portal_access"]; email: string; password: string | null }) {
  const ok = status === "sent";
  const color = ok ? "var(--brand-accent)" : "#C2453A";
  const Icon = ok ? CheckCircle2 : AlertTriangle;
  const text = ok
    ? `Acceso al portal enviado a ${email}: usuario, contraseña y enlace.`
    : status === "disabled"
    ? "El envío de correos está desactivado en el servidor. Pulsa 'Enviar correo de nuevo' para ver la contraseña y dársela tú."
    : status === "no_email"
    ? "El cliente no tiene email, así que no se pudo enviar el acceso."
    : "El acceso se generó pero el email no salió. Reenvíalo o revisa la configuración de correo.";
  return (
    <div
      className="flex items-start gap-2 rounded-xl border p-3"
      style={{
        borderColor: `color-mix(in srgb, ${color} 45%, var(--line-strong))`,
        background: `color-mix(in srgb, ${color} 8%, transparent)`,
      }}
    >
      <Icon size={16} style={{ color }} className="mt-0.5 shrink-0" />
      <div className="min-w-0 text-xs text-zinc-300">
        {text}
        {password && (
          <div className="mt-1.5">
            Contraseña del cliente:{" "}
            <code className="font-mono text-sm font-semibold text-zinc-100">{password}</code>
          </div>
        )}
      </div>
    </div>
  );
}
