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
          style={{ background: "color-mix(in srgb, var(--brand-accent) 10%, transparent)", border: "1px solid color-mix(in srgb, var(--brand-accent) 25%, transparent)" }}
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
    </div>
  );
}
