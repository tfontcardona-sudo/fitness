import { useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { CheckCircle2, Download, FileUp, Loader2 } from "lucide-react";

/**
 * Página PÚBLICA de la anamnesis (/anamnesis/{token}) — llega por el email o
 * WhatsApp de arranque. Dos pasos: descargar el PDF editable oficial y subir la
 * versión rellenada. La subida se ingiere sola en el sistema (se lee con IA y
 * se envía al cliente su acceso al portal por email).
 */
export default function AnamnesisPage() {
  const { token } = useParams();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [state, setState] = useState<"idle" | "uploading" | "done">("idle");
  const [error, setError] = useState<string | null>(null);

  const templateUrl = `/api/p/${token}/anamnesis-template`;

  async function upload() {
    if (!file || state === "uploading") return;
    setError(null);
    setState("uploading");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await fetch(`/api/p/${token}/anamnesis-pdf`, { method: "POST", body: fd });
      if (!r.ok) {
        let msg = "No se pudo subir. Inténtalo de nuevo en un momento.";
        try {
          const data = await r.json();
          if (typeof data?.detail === "string") msg = data.detail;
        } catch { /* respuesta sin cuerpo JSON */ }
        throw new Error(msg);
      }
      setState("done");
    } catch (e: any) {
      setError(e?.message ?? "No se pudo subir. Inténtalo de nuevo en un momento.");
      setState("idle");
    }
  }

  return (
    <div style={{ minHeight: "100vh", background: "#f6f1e7", color: "#26211a" }}>
      <div className="mx-auto max-w-lg px-5 py-10">
        <header className="mb-8 flex flex-col items-center text-center">
          <img src="/dq-logo.png" alt="" className="h-14 w-auto rounded-xl shadow-sm" />
          <h1 className="mt-4 text-2xl font-bold">Tu cuestionario inicial</h1>
          <p className="mt-1 max-w-md text-sm opacity-70">
            Con esta anamnesis preparamos tu plan a medida. Son dos pasos y puedes
            hacerlos desde el móvil o el ordenador.
          </p>
        </header>

        {state === "done" ? (
          <div className="rounded-2xl border bg-white p-6 text-center shadow-sm" style={{ borderColor: "#cfe3cf" }}>
            <CheckCircle2 size={40} className="mx-auto" style={{ color: "#2E7D46" }} />
            <h2 className="mt-3 text-lg font-bold">¡Anamnesis recibida!</h2>
            <p className="mt-2 text-sm opacity-75">
              Ya la tenemos. Revisa tu correo (también la carpeta de spam): te hemos
              enviado el acceso a tu portal. Tu coach preparará tu plan con esta
              información y te avisará en cuanto esté listo.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Paso 1: descargar el PDF editable */}
            <div className="rounded-2xl border bg-white p-5 shadow-sm" style={{ borderColor: "#e6ddca" }}>
              <p className="text-sm font-bold">1 · Descarga tu anamnesis (PDF editable)</p>
              <p className="mt-1 text-sm opacity-70">
                Ábrela con cualquier lector de PDF y rellena todos los campos con calma.
              </p>
              <a href={templateUrl}
                className="mt-3 inline-flex items-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold text-white transition-transform active:scale-[0.98]"
                style={{ background: "#2E5E8C" }}>
                <Download size={16} /> Descargar anamnesis
              </a>
            </div>

            {/* Paso 2: subir el PDF rellenado */}
            <div className="rounded-2xl border bg-white p-5 shadow-sm" style={{ borderColor: "#e6ddca" }}>
              <p className="text-sm font-bold">2 · Sube aquí el PDF rellenado</p>
              <p className="mt-1 text-sm opacity-70">
                Cuando lo tengas completo, súbelo y listo: nosotros hacemos el resto.
              </p>
              <input ref={fileRef} type="file" accept="application/pdf" className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
              <button onClick={() => fileRef.current?.click()}
                className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed px-4 py-4 text-sm font-medium transition-colors"
                style={{ borderColor: file ? "#2E7D46" : "#cbbfa5", color: file ? "#2E7D46" : undefined }}>
                <FileUp size={17} />
                {file ? file.name : "Elegir el PDF rellenado"}
              </button>
              {error && (
                <p className="mt-3 rounded-xl border p-3 text-center text-sm"
                  style={{ borderColor: "#C2453A", background: "#fdecea", color: "#8B1A2B" }}>
                  {error}
                </p>
              )}
              <button onClick={upload} disabled={!file || state === "uploading"}
                className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold text-white transition-transform active:scale-[0.98] disabled:opacity-60"
                style={{ background: "#E8833A" }}>
                {state === "uploading"
                  ? <><Loader2 size={16} className="animate-spin" /> Subiendo…</>
                  : "Enviar mi anamnesis"}
              </button>
            </div>

            <p className="text-center text-xs opacity-50">
              Tus datos se usan solo para preparar y seguir tu asesoría.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
