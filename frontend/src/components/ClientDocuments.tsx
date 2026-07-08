import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Download, FileText, Send, Upload } from "lucide-react";
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
  const [sending, setSending] = useState(false);
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
      } else {
        toast.push("Anamnesis subida. Pulsa 'Leer con IA' en la pestaña Anamnesis.");
      }
      // Acceso al portal enviado automáticamente la primera vez.
      if (res.portal_access === "sent") toast.push("Acceso al portal enviado al cliente por email 📧");
      else if (res.portal_access === "disabled") toast.push("Acceso generado (email desactivado). Usa 'Reenviar acceso' para ver la contraseña.");
      onUploaded?.();
      load();
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo subir el documento", "error");
    } finally {
      setBusy(false);
    }
  }

  async function resendAccess() {
    if (sending) return;
    setSending(true);
    try {
      const res = await api.sendPortalAccess(client.id);
      if (res.status === "sent") {
        toast.push("Acceso reenviado al cliente por email 📧");
      } else if (res.status === "disabled" && res.password) {
        toast.push(`Email desactivado. Contraseña del cliente: ${res.password}`);
      } else if (res.password) {
        toast.push(`Acceso generado. Contraseña: ${res.password}`);
      } else {
        toast.push("No se pudo enviar el acceso", "error");
      }
      onUploaded?.();
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo enviar el acceso", "error");
    } finally {
      setSending(false);
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
    // DESPLEGABLE: abierto solo mientras falte la anamnesis (hay que actuar);
    // una vez subida queda plegado y el check lo resume de un vistazo.
    <details className="card p-5" open={!docs || docs.length === 0}>
      <summary className="flex cursor-pointer items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-200">Anamnesis</h3>
        {docs && docs.length > 0 && (
          <span
            className="flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium"
            style={{ background: "color-mix(in srgb, var(--brand-accent) 12%, transparent)", color: "var(--brand-accent)" }}
          >
            <CheckCircle2 size={13} /> subida
          </span>
        )}
      </summary>
      <p className="mt-1 mb-4 text-xs text-zinc-500">
        Descarga la anamnesis, envíala por correo y sube aquí la versión rellenada.
      </p>

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
          background: dragOver ? "color-mix(in srgb, var(--brand-accent) 6%, transparent)" : "transparent",
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

      {/* Acceso al portal del cliente (usuario = su email + contraseña por email).
          Se envía solo al subir la anamnesis; aquí el coach puede reenviarlo. */}
      <div className="mt-4 border-t pt-3" style={{ borderColor: "var(--line)" }}>
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs text-zinc-500">
            {client.portal_access_sent_at
              ? `Acceso enviado el ${new Date(client.portal_access_sent_at).toLocaleDateString("es-ES")}`
              : "Aún no se ha enviado el acceso al portal"}
          </span>
          <button onClick={resendAccess} disabled={sending} className="btn btn-ghost shrink-0 text-xs">
            <Send size={13} className="text-zinc-500" />
            {sending ? "Enviando…" : client.portal_access_sent_at ? "Reenviar acceso" : "Enviar acceso"}
          </button>
        </div>
      </div>
    </details>
  );
}
