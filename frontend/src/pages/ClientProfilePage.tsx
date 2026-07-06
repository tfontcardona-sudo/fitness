import { useCallback, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft, Check, ExternalLink, BellRing, Pencil } from "lucide-react";
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
  // Aviso "revisión cerrada": solo mientras el feedback de la última revisión
  // NO exista todavía. En cuanto el coach lo genera, el aviso desaparece.
  const [feedbackPending, setFeedbackPending] = useState(false);

  const load = useCallback(() => {
    api.getClient(clientId).then(setClient).catch(() => setClient(null));
  }, [clientId]);

  useEffect(load, [load]);

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
  }, [client, clientId]);

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
              <PhoneRow client={client} onSaved={load} />
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

          {tab === "resumen" && <ClientSummaryTab client={client} />}
          {tab === "anamnesis" && <ClientAnamnesisTab client={client} onSaved={load} />}
          {tab === "planificacion" && <ClientPlanPanel client={client} onClientChanged={load} />}
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
