import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Copy,
  Download,
  FileText,
  Mail,
  Power,
  RefreshCw,
} from "lucide-react";
import { api, getToken } from "../lib/api";
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
import { ageFrom, DIET_LABEL, GOAL_LABEL, LEVEL_LABEL, PLACE_LABEL } from "../lib/format";

type Tab = "resumen" | "anamnesis";

export default function ClientProfilePage() {
  const { id } = useParams();
  const clientId = Number(id);
  const toast = useToast();
  const [client, setClient] = useState<ClientOut | null>(null);
  const [tab, setTab] = useState<Tab>("resumen");
  const [confirmRegen, setConfirmRegen] = useState(false);

  const load = useCallback(() => {
    api.getClient(clientId).then(setClient).catch(() => setClient(null));
  }, [clientId]);

  useEffect(load, [load]);

  async function toggle(field: "auto_pilot" | "emails_enabled") {
    if (!client) return;
    const next = !client[field];
    setClient({ ...client, [field]: next }); // optimista
    try {
      await api.updateClient(client.id, { [field]: next });
    } catch {
      setClient({ ...client, [field]: !next });
      toast.push("No se pudo actualizar", "error");
    }
  }

  async function copyPortal() {
    if (!client) return;
    const link = await api.portalLink(client.id);
    navigator.clipboard.writeText(link.portal_url);
    toast.push("Enlace del portal copiado");
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

  function downloadAll() {
    if (!client) return;
    // El endpoint exige JWT; abrimos con fetch→blob para adjuntar el header.
    fetch(api.exportClientUrl(client.id), {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `export_${client.full_name.replace(/\s+/g, "_").toLowerCase()}.zip`;
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch(() => toast.push("No se pudo exportar", "error"));
  }

  async function downloadPlanDoc() {
    if (!client) return;
    try {
      const plans = await api.listPlans(client.id);
      const published = plans.find((p) => p.status === "published") ?? plans[0];
      if (!published) {
        toast.push("Este cliente aún no tiene plan", "error");
        return;
      }
      const r = await fetch(api.planDocumentUrl(published.id), {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `plan_${client.full_name.replace(/\s+/g, "_").toLowerCase()}.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.push("No se pudo generar el documento", "error");
    }
  }

  if (client === null) return <PageLoader />;

  const age = ageFrom(client.birth_date);

  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <Link to="/clientes" className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-300">
        <ArrowLeft size={15} /> Clientes
      </Link>

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

          {/* Toggles */}
          <div className="card p-5">
            <Toggle
              label="Auto-pilot"
              hint="Publica ajustes sin tu aprobación"
              icon={Power}
              on={client.auto_pilot}
              onClick={() => toggle("auto_pilot")}
            />
            <div className="my-3 border-t" style={{ borderColor: "var(--line)" }} />
            <Toggle
              label="Emails"
              hint="Notificaciones automáticas al cliente"
              icon={Mail}
              on={client.emails_enabled}
              onClick={() => toggle("emails_enabled")}
            />
          </div>

          {/* Acciones rápidas */}
          <div className="card space-y-1 p-3">
            <ActionRow icon={Copy} label="Copiar enlace del portal" onClick={copyPortal} />
            <ActionRow icon={RefreshCw} label="Regenerar enlace" onClick={() => setConfirmRegen(true)} />
            <ActionRow icon={FileText} label="Descargar plan (Word)" onClick={downloadPlanDoc} />
            <ActionRow icon={Download} label="Descargar todo (ZIP)" onClick={downloadAll} />
          </div>

          {/* Anamnesis: enviar enlace + subir PDF rellenado */}
          <ClientDocuments client={client} />
        </aside>

        {/* CONTENIDO con tabs */}
        <div>
          <div className="mb-5 flex gap-1 border-b" style={{ borderColor: "var(--line)" }}>
            {(["resumen", "anamnesis"] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className="relative px-4 py-2.5 text-sm font-medium capitalize transition-colors"
                style={{ color: tab === t ? "#e7e7ea" : "var(--text-faint)" }}
              >
                {t === "resumen" ? "Resumen" : "Anamnesis"}
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

function Toggle({
  label,
  hint,
  icon: Icon,
  on,
  onClick,
}: {
  label: string;
  hint: string;
  icon: typeof Power;
  on: boolean;
  onClick: () => void;
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2.5">
        <Icon size={16} className="text-zinc-500" />
        <div>
          <p className="text-sm font-medium text-zinc-200">{label}</p>
          <p className="text-xs text-zinc-600">{hint}</p>
        </div>
      </div>
      <button
        onClick={onClick}
        role="switch"
        aria-checked={on}
        className="relative h-6 w-10 rounded-full transition-colors"
        style={{ background: on ? "var(--brand-accent)" : "var(--surface-raised)" }}
      >
        <span
          className="absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform"
          style={{ transform: on ? "translateX(18px)" : "translateX(2px)" }}
        />
      </button>
    </div>
  );
}

function ActionRow({ icon: Icon, label, onClick }: { icon: typeof Copy; label: string; onClick: () => void }) {
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
