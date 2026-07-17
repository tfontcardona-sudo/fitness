import { useCallback, useEffect, useState } from "react";
import { Link, useParams, useSearchParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Check, BellRing, Pencil, Smartphone, ClipboardCheck, Trash2, CreditCard } from "lucide-react";
import { api, keepIfSame, REFRESH_MS } from "../lib/api";
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
import { ageFrom, GOAL_LABEL, LEVEL_LABEL, PLACE_LABEL } from "../lib/format";
import { BILLING_PERIODS, PACKAGES, PACKAGE_ORDER, billingLabel, pkg } from "../lib/packages";

type Tab = "resumen" | "anamnesis" | "planificacion" | "seguimiento" | "feedback" | "historial";

export default function ClientProfilePage() {
  const { id } = useParams();
  const clientId = Number(id);
  const toast = useToast();
  const navigate = useNavigate();
  const [client, setClient] = useState<ClientOut | null>(null);
  const [searchParams] = useSearchParams();
  const initialTab = (["resumen", "anamnesis", "planificacion", "seguimiento", "feedback", "historial"] as Tab[])
    .includes(searchParams.get("tab") as Tab) ? (searchParams.get("tab") as Tab) : "resumen";
  const [tab, setTab] = useState<Tab>(initialTab);
  const [confirmRegen, setConfirmRegen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [portalUrl, setPortalUrl] = useState<string | null>(null);
  const [payUrl, setPayUrl] = useState<string | null>(null);
  // Aviso "revisión cerrada": solo mientras el feedback de la última revisión
  // NO exista todavía. En cuanto el coach lo genera, el aviso desaparece.
  const [feedbackPending, setFeedbackPending] = useState(false);
  // La pestaña Anamnesis tiene edición local; avisamos si se sale con cambios sin
  // guardar (el panel se re-monta al cambiar de pestaña y perdería el borrador).
  const [anamnesisDirty, setAnamnesisDirty] = useState(false);

  function changeTab(next: Tab) {
    if (next === tab) return;
    if (tab === "anamnesis" && anamnesisDirty &&
        !window.confirm("Tienes cambios sin guardar en la anamnesis. ¿Descartarlos?")) {
      return;
    }
    if (tab === "anamnesis") setAnamnesisDirty(false);
    setTab(next);
  }

  const [loadError, setLoadError] = useState(false);
  const load = useCallback(() => {
    api.getClient(clientId)
      // keepIfSame: solo cambia la referencia (y re-renderiza) si los datos han
      // cambiado de verdad. Evita el parpadeo y el re-fetch de "Dieta"/feedback
      // cada 3 s cuando la ficha no ha cambiado.
      .then((c) => { setClient((prev) => keepIfSame(prev, c)); setLoadError(false); })
      .catch(() => setLoadError(true));
  }, [clientId]);

  useEffect(load, [load]);

  // Recarga EXPLÍCITA tras una acción del coach (editar/adaptar/generar plan,
  // guardar anamnesis, subir documento…): además de refrescar la ficha, sube un
  // contador que re-sincroniza la "Dieta" y el aviso de feedback aunque la fila
  // del cliente no haya cambiado (el plan vive aparte). El polling de 3 s NO sube
  // este contador, así que no re-consulta esos datos si nada cambió.
  const [reloadKey, setReloadKey] = useState(0);
  const reload = useCallback(() => {
    load();
    setReloadKey((k) => k + 1);
  }, [load]);

  // Refresco cada 3 s (pestaña visible): la ficha siempre al día. Se PAUSA
  // mientras se edita la anamnesis (borrador sin guardar): un refresco en medio
  // de la edición sería una fuente de desincronización y despiste.
  useEffect(() => {
    if (anamnesisDirty) return;
    const t = window.setInterval(() => {
      if (!document.hidden) load();
    }, REFRESH_MS);
    return () => window.clearInterval(t);
  }, [load, anamnesisDirty]);

  // La pestaña SIGUE a la URL: navegar desde una alerta (o el botón atrás)
  // cambia de pestaña aunque ya estemos en el perfil de este cliente.
  useEffect(() => {
    const t = searchParams.get("tab") as Tab | null;
    const valid: Tab[] = ["resumen", "anamnesis", "planificacion", "seguimiento", "feedback", "historial"];
    if (t && valid.includes(t)) setTab(t);
  }, [searchParams]);

  useEffect(() => {
    if (client?.status !== "review_pending") {
      setFeedbackPending(false);
      return;
    }
    api.listPeriods(clientId)
      .then((ps: any[]) => {
        const latest = ps
          .filter((p) => p.status !== "open")
          .reduce<any>((a, b) => (!a || b.period_index > a.period_index ? b : a), null);
        setFeedbackPending(latest != null && !latest.feedback_id);
      })
      .catch(() => setFeedbackPending(true));
  }, [client, clientId, reloadKey]);

  // Precargamos el enlace del portal con el ORIGEN actual del navegador (en dev
  // :5173, en prod el dominio) para poder abrirlo de forma síncrona (sin que el
  // navegador bloquee la pestaña) y que el enlace funcione siempre.
  useEffect(() => {
    api.portalLink(clientId)
      .then((l) => {
        setPortalUrl(`${window.location.origin}/p/${l.portal_token}`);
        setPayUrl(api.payLinkUrl(l.portal_token));
      })
      .catch(() => { setPortalUrl(null); setPayUrl(null); });
  }, [clientId]);

  // "Dieta" de la info básica = la dieta GENERADA con IA (kcal y macros del
  // plan activo). Hasta que no hay planificación, el apartado queda vacío.
  // Depende de `client` (objeto nuevo en cada load()): así CUALQUIER acción
  // que llame a onClientChanged (generar, adaptar, editar…) la resincroniza,
  // aunque la fila del cliente no cambie.
  const [planDiet, setPlanDiet] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    api.listPlans(clientId)
      .then((plans: any[]) => {
        if (!alive) return;
        const active = plans.find((p) => p.status === "published");
        const n = active?.nutrition_json;
        if (n?.target_kcal) {
          const m = n.macros ?? {};
          const nMeals = Array.isArray(n.meals) ? n.meals.length : null;
          setPlanDiet(
            `${Math.round(n.target_kcal)} kcal · P${Math.round(m.protein_g ?? 0)} ` +
            `C${Math.round(m.carbs_g ?? 0)} G${Math.round(m.fat_g ?? 0)}` +
            (nMeals ? ` · ${nMeals} comidas/día` : ""),
          );
        } else setPlanDiet(null);
      })
      .catch(() => setPlanDiet(null));
    return () => { alive = false; };
  }, [clientId, client, reloadKey]);

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

  async function deleteClient() {
    if (!client || deleting) return;
    setDeleting(true);
    try {
      await api.deleteClient(client.id, client.full_name);
      setConfirmDelete(false);
      toast.push(`${client.full_name} eliminado definitivamente`);
      navigate("/clientes");
    } catch {
      toast.push("No se pudo borrar el cliente", "error");
      setDeleting(false);
    }
  }

  if (loadError && client === null) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-16 text-center">
        <p className="text-lg font-semibold text-zinc-200">No se pudo cargar el cliente</p>
        <p className="mt-1 text-sm text-zinc-500">Puede que se haya eliminado o que el enlace no sea válido.</p>
        <Link to="/clientes" className="btn btn-ghost mt-4 inline-flex">Volver a Clientes</Link>
      </div>
    );
  }
  if (client === null) return <PageLoader />;

  const age = ageFrom(client.birth_date);
  // Paquete solo-nutrición (Start): sin nada de entreno en la ficha.
  const hasTraining = pkg(client.package_tier).hasTraining;

  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <Link to="/clientes" className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-300">
        <ArrowLeft size={15} /> Clientes
      </Link>

      {/* Notificación: el cliente cerró su período → toca generar feedback.
          Se oculta en cuanto el feedback ya está generado. */}
      {client.status === "review_pending" && feedbackPending && (
        <div
          className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border p-3.5"
          style={{ borderColor: "var(--brand-accent)", background: "color-mix(in srgb, var(--brand-accent) 10%, transparent)" }}
        >
          <div className="flex items-center gap-2.5 text-sm text-zinc-200">
            <BellRing size={18} style={{ color: "var(--brand-accent)" }} />
            <span><b>El cliente ha cerrado su período.</b> Revisa los datos y genera el feedback.</span>
          </div>
          <button onClick={() => changeTab("feedback")} className="btn btn-primary">
            Ir a Feedback
          </button>
        </div>
      )}

      {/* Rejilla con filas: en MÓVIL el orden es identidad → contenido →
          extras (el coach llega a las pestañas sin scrollear toda la barra);
          en ESCRITORIO la columna izquierda tiene la ficha arriba y las
          tarjetas extra debajo, con el contenido a la derecha. */}
      <div className="mt-4 grid gap-4 lg:gap-6 lg:grid-cols-[300px_1fr] lg:grid-rows-[auto_1fr] lg:items-start">
        {/* 1) Identidad + info + Diario (arriba también en móvil) */}
        <aside className="min-w-0 space-y-4 lg:col-start-1 lg:row-start-1">
          <div className="card p-5">
            <div className="flex items-center gap-3">
              <Avatar name={client.full_name} size={48} />
              <div className="min-w-0">
                <h1 className="truncate text-lg font-semibold text-zinc-100">{client.full_name}</h1>
                <p className="truncate text-xs text-zinc-500">{client.email}</p>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <StatusBadge status={client.status} />
            </div>

            <dl className="mt-5 space-y-2.5 text-sm">
              <PlanRow client={client} onSaved={reload} />
              <BillingRow client={client} onSaved={reload} />
              <div className="flex items-center justify-between gap-2">
                <dt className="text-zinc-500">Pago</dt>
                <dd>
                  <span
                    className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold"
                    style={{
                      background: `color-mix(in srgb, ${client.payment_status === "paid" ? "#2E7D46" : "#C2453A"} 14%, transparent)`,
                      color: client.payment_status === "paid" ? "#2E7D46" : "#C2453A",
                    }}
                  >
                    {client.payment_status === "paid" ? "Pagado" : "Pago pendiente"}
                  </span>
                </dd>
              </div>
              <PhoneRow client={client} onSaved={reload} />
              <Row label="Edad" value={age ? `${age} años` : "—"} />
              <Row label="Objetivo" value={client.goal_type ? GOAL_LABEL[client.goal_type] : "—"} />
              <Row label="Nivel" value={client.level ? LEVEL_LABEL[client.level] : "—"} />
              {hasTraining && (
                <Row label="Entreno" value={client.training_place ? PLACE_LABEL[client.training_place] : "—"} />
              )}
              {/* Dieta = la generada con IA; vacía hasta que exista planificación */}
              <Row label="Dieta" value={planDiet ?? "—"} faint={planDiet == null ? "se llena al generar la planificación" : undefined} />
            </dl>
          </div>

          {/* DIARIO DEL CLIENTE (su app del móvil): botón destacado y distinto. */}
          <button
            onClick={openPortal}
            className="flex w-full items-center gap-3 rounded-xl px-4 py-3.5 text-left text-white shadow-md transition-transform hover:brightness-110 active:scale-[0.98]"
            style={{ background: "linear-gradient(135deg, var(--brand-accent-2) 0%, #234B72 100%)" }}
          >
            <span className="relative shrink-0">
              <Smartphone size={26} />
              <ClipboardCheck
                size={14}
                className="absolute -bottom-1 -right-1.5 rounded-full p-0.5"
                style={{ background: "var(--brand-accent)", color: "white" }}
              />
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-semibold">Diario del cliente</span>
              <span className="block text-xs opacity-75">abrir y copiar el enlace de su app</span>
            </span>
          </button>

          {/* ENLACE DE PAGO (Stripe): color diferenciado (verde), debajo del
              portal. Copia el enlace para mandárselo al cliente y que pague. */}
          {payUrl && client.payment_status !== "paid" && (
            <button
              onClick={() => {
                navigator.clipboard.writeText(payUrl).catch(() => {});
                toast.push("Enlace de pago copiado — mándaselo al cliente");
              }}
              className="flex w-full items-center gap-3 rounded-xl border-2 px-4 py-3 text-left transition-transform active:scale-[0.98]"
              style={{ borderColor: "#2E7D46", color: "#2E7D46", background: "color-mix(in srgb, #2E7D46 7%, transparent)" }}
            >
              <CreditCard size={22} className="shrink-0" />
              <span className="min-w-0">
                <span className="block text-sm font-semibold">Enlace de pago</span>
                <span className="block text-xs opacity-80">
                  copiar y enviar al cliente — cobra su plan {billingLabel(client.billing_period).toLowerCase()}
                </span>
              </span>
            </button>
          )}
        </aside>

        {/* 3) Extras: anamnesis + regenerar enlace (debajo del contenido en
            móvil; columna izquierda-abajo en escritorio) */}
        <aside className="order-last min-w-0 space-y-3 lg:order-none lg:col-start-1 lg:row-start-2">
          {/* Anamnesis: enviar enlace + subir PDF rellenado */}
          <ClientDocuments client={client} onUploaded={reload} portalUrl={portalUrl} />
          <button
            onClick={() => setConfirmRegen(true)}
            className="w-full text-center text-xs text-zinc-500 underline-offset-2 hover:text-zinc-300 hover:underline"
          >
            Regenerar enlace del portal (el actual dejará de funcionar)
          </button>
          {/* Zona peligrosa: borrado total del cliente. Botón claramente en ROJO
              (borde + texto + fondo tenue) y separado del resto; el modal exige
              teclear el nombre completo antes de confirmar, así que verse rojo no
              lo hace peligroso de pulsar. */}
          <button
            onClick={() => setConfirmDelete(true)}
            className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-lg border py-2.5 text-xs font-semibold text-white transition-colors"
            style={{ background: "#C2453A", borderColor: "#C2453A" }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "#A93A30")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "#C2453A")}
          >
            <Trash2 size={13} /> Borrar cliente
          </button>
        </aside>

        {/* 2) CONTENIDO con tabs (a la derecha, ocupa ambas filas en desktop) */}
        <div className="min-w-0 lg:col-start-2 lg:row-start-1 lg:row-span-2">
          {/* Barra de pestañas PEGAJOSA: al hacer scroll de un plan largo, la
              navegación entre secciones sigue siempre accesible. */}
          <div className="profile-tabs mb-5 flex gap-1 border-b" style={{ borderColor: "var(--line)", position: "sticky", top: 0, zIndex: 10, background: "var(--bg)" }}>
            {(["resumen", "anamnesis", "planificacion", "seguimiento", "feedback", "historial"] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => changeTab(t)}
                className="tab-btn relative px-4 py-2.5 text-sm font-medium capitalize transition-colors"
                style={{ color: tab === t ? "#26211A" : "var(--text-faint)" }}
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

          {/* key=tab: el panel se re-monta y hace su micro-animación al cambiar */}
          <div key={tab} className="tab-panel">
            {tab === "resumen" && <ClientSummaryTab client={client} />}
            {tab === "anamnesis" && <ClientAnamnesisTab client={client} onSaved={reload} onDirtyChange={setAnamnesisDirty} />}
            {tab === "planificacion" && <ClientPlanPanel client={client} onClientChanged={reload} />}
            {tab === "seguimiento" && <ClientTrackingTab client={client} />}
            {tab === "feedback" && <ClientFeedbackTab client={client} onClientChanged={reload} onGoPlan={() => changeTab("planificacion")} />}
            {tab === "historial" && <ClientHistoryTab client={client} />}
          </div>
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

      <ConfirmDialog
        open={confirmDelete}
        title="Borrar cliente"
        destructive
        requireText={client.full_name}
        body={
          <>
            Se borrará <b>para siempre</b> todo lo de <b>{client.full_name}</b>:
            ficha, anamnesis, planificaciones, seguimiento, fotos y feedbacks.
            <b> No se puede deshacer.</b>
            <br />
            <br />
            Para confirmar, escribe el nombre completo del cliente:
          </>
        }
        confirmLabel={deleting ? "Borrando…" : "Borrar definitivamente"}
        onConfirm={deleteClient}
        onCancel={() => !deleting && setConfirmDelete(false)}
      />
    </div>
  );
}

/** Plan/paquete del cliente: badge + desplegable para cambiarlo (upgrade/downgrade).
 *  Cambiarlo adapta toda la app (portal, planificación, envíos) a ese plan. */
function PlanRow({ client, onSaved }: { client: ClientOut; onSaved: () => void }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const info = pkg(client.package_tier);

  async function change(next: string) {
    if (busy || next === client.package_tier) return;
    setBusy(true);
    try {
      await api.updateClient(client.id, { package_tier: next as ClientOut["package_tier"] });
      toast.push(`Plan cambiado a ${PACKAGES[next as keyof typeof PACKAGES].label}`);
      onSaved();
    } catch {
      toast.push("No se pudo cambiar el plan", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center justify-between gap-2">
      <dt className="text-zinc-500">Plan</dt>
      <dd className="flex items-center gap-1.5">
        <span
          className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold"
          style={{ background: `color-mix(in srgb, ${info.color} 14%, transparent)`, color: info.color }}
        >
          {info.label}
        </span>
        <select
          aria-label="Cambiar plan del cliente"
          disabled={busy}
          value={client.package_tier}
          onChange={(e) => change(e.target.value)}
          className="input h-7 w-auto px-1.5 py-0 text-xs"
        >
          {PACKAGE_ORDER.map((t) => (
            <option key={t} value={t}>{PACKAGES[t].short}</option>
          ))}
        </select>
      </dd>
    </div>
  );
}

/** Duración contratada (mensual/trimestral/semestral): decide el precio de
 *  Stripe que abre el enlace de pago del cliente. Cambiarla aquí y reenviar el
 *  enlace basta para cobrar la duración nueva. */
function BillingRow({ client, onSaved }: { client: ClientOut; onSaved: () => void }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);

  async function change(next: string) {
    if (busy || next === client.billing_period) return;
    setBusy(true);
    try {
      await api.updateClient(client.id, { billing_period: next as ClientOut["billing_period"] });
      toast.push(`Duración cambiada a ${billingLabel(next)} — su enlace de pago ya cobra ese precio`);
      onSaved();
    } catch {
      toast.push("No se pudo cambiar la duración", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center justify-between gap-2">
      <dt className="text-zinc-500">Duración</dt>
      <dd>
        <select
          aria-label="Cambiar duración del plan del cliente"
          disabled={busy}
          value={client.billing_period}
          onChange={(e) => change(e.target.value)}
          className="input h-7 w-auto px-1.5 py-0 text-xs"
        >
          {BILLING_PERIODS.map((b) => (
            <option key={b.value} value={b.value}>{b.label}</option>
          ))}
        </select>
      </dd>
    </div>
  );
}

/** Teléfono editable en línea: imprescindible para los envíos por WhatsApp
 *  (feedback y plan). Lápiz → escribir → Enter o ✓ para guardar. */
function PhoneRow({ client, onSaved }: { client: ClientOut; onSaved: () => void }) {
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(client.phone ?? "");
  const [busy, setBusy] = useState(false);

  useEffect(() => setValue(client.phone ?? ""), [client.phone]);

  async function save() {
    if (busy) return;
    setBusy(true);
    try {
      await api.updateClient(client.id, { phone: value.trim() || null });
      toast.push("Teléfono guardado");
      setEditing(false);
      onSaved();
    } catch {
      toast.push("No se pudo guardar el teléfono", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center justify-between gap-2">
      <dt className="text-zinc-500">Teléfono</dt>
      {editing ? (
        <dd className="flex items-center gap-1.5">
          <input
            autoFocus
            type="tel"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") save();
              if (e.key === "Escape") setEditing(false);
            }}
            placeholder="612 345 678"
            className="input w-36 px-2 py-1 text-sm"
          />
          <button onClick={save} disabled={busy} aria-label="Guardar teléfono" className="p-1 text-zinc-500 hover:text-zinc-200">
            <Check size={16} />
          </button>
        </dd>
      ) : (
        <dd className="flex items-center gap-1.5 font-medium text-zinc-200">
          {client.phone || <span className="font-normal text-zinc-500">añádelo para WhatsApp</span>}
          <button onClick={() => setEditing(true)} aria-label="Editar teléfono" className="p-1 text-zinc-500 hover:text-zinc-200">
            <Pencil size={13} />
          </button>
        </dd>
      )}
    </div>
  );
}

function Row({ label, value, faint }: { label: string; value: string; faint?: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <dt className="text-zinc-500">{label}</dt>
      <dd className="text-right font-medium text-zinc-200">
        {value}
        {faint && <span className="block text-[11px] font-normal text-zinc-500">{faint}</span>}
      </dd>
    </div>
  );
}
