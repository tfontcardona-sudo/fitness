import { useEffect, useRef, useState } from "react";
import { ExternalLink, Upload } from "lucide-react";
import { api } from "../lib/api";
import { PUBLIC_SLUG } from "../lib/branding";
import { PageLoader, useToast } from "../components/ui";
import type { BrandConfigOut } from "../types";

/**
 * ENLACES — la página pública del perfil de Instagram y sus dos fotos.
 *
 * Es lo único que el coach configura fuera del ciclo de clientes: la dirección
 * que pone en su bio, la foto de fondo de esa página y la de la página de
 * planes (a donde lleva "Trabaja conmigo").
 */
export default function EnlacesPage() {
  const toast = useToast();
  const [brand, setBrand] = useState<BrandConfigOut | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadingPlans, setUploadingPlans] = useState(false);
  const photoRef = useRef<HTMLInputElement>(null);
  const plansPhotoRef = useRef<HTMLInputElement>(null);

  const publicUrl = `${window.location.origin}/${PUBLIC_SLUG}`;

  useEffect(() => {
    api.getBrand().then(setBrand).catch(() => toast.push("No se pudo cargar la marca", "error"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function subirFoto(file: File | undefined, cual: "enlaces" | "planes") {
    if (!file) return;
    const setBusy = cual === "enlaces" ? setUploading : setUploadingPlans;
    setBusy(true);
    try {
      const updated = cual === "enlaces"
        ? await api.uploadLinksPhoto(file)
        : await api.uploadPlansPhoto(file);
      setBrand(updated);
      toast.push("Foto actualizada");
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo subir la foto", "error");
    } finally {
      setBusy(false);
    }
  }

  if (!brand) return <PageLoader />;

  return (
    <div className="mx-auto max-w-2xl px-4 py-6 md:px-8 md:py-8">
      <header className="mb-5">
        <p className="text-xs uppercase tracking-widest text-zinc-500">Público</p>
        <h1 className="mt-1 text-2xl font-semibold text-zinc-100">Enlaces</h1>
        <p className="mt-1 text-sm text-zinc-400">
          La página que enlazas desde Instagram y las fotos que la visten.
        </p>
      </header>

      <div className="space-y-4">
        {/* El enlace público para el perfil de Instagram */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-zinc-200">Tu enlace para Instagram</h3>
          <p className="mt-1 text-sm text-zinc-500">
            Pon esta dirección en el perfil. El cliente verá vuestra foto y el
            botón "Trabaja conmigo", que lleva a los tres servicios con su pago.
          </p>
          <div className="mt-3 flex items-center gap-2">
            <code className="flex-1 truncate rounded-lg border px-3 py-2 text-sm"
              style={{ borderColor: "var(--line-strong)" }}>{publicUrl}</code>
            <button
              className="btn btn-primary shrink-0"
              onClick={() => {
                navigator.clipboard.writeText(publicUrl).catch(() => {});
                toast.push("Enlace copiado — pégalo en tu perfil de Instagram");
              }}
            >
              Copiar
            </button>
            <a className="btn btn-ghost shrink-0" href={publicUrl} target="_blank" rel="noopener noreferrer">
              <ExternalLink size={15} /> Ver
            </a>
          </div>
        </div>

        {/* Foto de fondo de la página de enlaces */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-zinc-200">Foto de fondo</h3>
          <p className="mt-1 text-sm text-zinc-500">
            Una foto del centro en vertical (como fondo de pantalla). JPG/PNG, máx. 5 MB.
          </p>
          {api.mediaUrl(brand.links_photo_path) && (
            <img src={api.mediaUrl(brand.links_photo_path)!} alt="Foto de fondo actual"
              className="mt-3 h-40 w-28 rounded-xl border object-cover"
              style={{ borderColor: "var(--line-strong)" }} />
          )}
          <input ref={photoRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden"
            onChange={(e) => subirFoto(e.target.files?.[0], "enlaces")} />
          <button className="btn btn-ghost mt-3" disabled={uploading} onClick={() => photoRef.current?.click()}>
            <Upload size={15} className="text-zinc-500" />
            {uploading ? "Subiendo…" : brand.links_photo_path ? "Cambiar foto" : "Subir foto"}
          </button>
        </div>

        {/* Segunda foto: fondo de la página de PLANES */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-zinc-200">Foto de fondo de los planes</h3>
          <p className="mt-1 text-sm text-zinc-500">
            Segunda foto, para la página donde se contratan los servicios (/planes).
            JPG/PNG, máx. 5 MB.
          </p>
          {api.mediaUrl(brand.plans_photo_path) && (
            <img src={api.mediaUrl(brand.plans_photo_path)!} alt="Foto de los planes actual"
              className="mt-3 h-28 w-44 rounded-xl border object-cover"
              style={{ borderColor: "var(--line-strong)" }} />
          )}
          <input ref={plansPhotoRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden"
            onChange={(e) => subirFoto(e.target.files?.[0], "planes")} />
          <button className="btn btn-ghost mt-3" disabled={uploadingPlans} onClick={() => plansPhotoRef.current?.click()}>
            <Upload size={15} className="text-zinc-500" />
            {uploadingPlans ? "Subiendo…" : brand.plans_photo_path ? "Cambiar foto" : "Subir foto"}
          </button>
        </div>
      </div>
    </div>
  );
}
