import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import {
  Dumbbell,
  ExternalLink,
  GripVertical,
  Image as ImageIcon,
  Package,
  Pencil,
  Pill,
  Plus,
  Search,
  Sparkles,
  Trash2,
  Upload,
  Video,
  X,
} from "lucide-react";
import { api, ApiError } from "../lib/api";
import { youtubeId } from "../lib/video";
import type {
  ExerciseOut,
  ProductCategory,
  RecommendedProductOut,
} from "../types";
import { ConfirmDialog, EmptyState, PageLoader, Spinner, useToast } from "../components/ui";

/**
 * Recursos del portal (coach): gestiona el catálogo de PRODUCTOS recomendados
 * (suplementos, material…) y los VÍDEOS/imágenes de los ejercicios. Lo que aquí
 * se configura es lo que el cliente ve en la pestaña "Recursos" de su portal.
 */
export default function RecursosPage() {
  const [tab, setTab] = useState<"productos" | "videos" | "enlaces">("productos");
  return (
    <div className="mx-auto max-w-4xl px-4 py-6 md:px-8 md:py-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold text-zinc-100">Recursos del portal</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Productos recomendados y vídeos de los ejercicios que verán tus clientes en su portal.
        </p>
      </header>

      <div className="mb-6 inline-flex rounded-xl border p-1" style={{ borderColor: "var(--line-strong)" }}>
        {([["productos", "Productos", Package], ["videos", "Vídeos de ejercicios", Video], ["enlaces", "Página de enlaces", ExternalLink]] as const).map(
          ([id, label, Icon]) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
              style={
                tab === id
                  ? { background: "var(--surface-raised)", color: "var(--brand-accent)" }
                  : { color: "var(--text-faint)" }
              }
            >
              <Icon size={16} />
              {label}
            </button>
          ),
        )}
      </div>

      {tab === "productos" ? <ProductsManager /> : tab === "videos" ? <ExerciseVideosManager /> : <LinksPageManager />}
    </div>
  );
}

/* ============================================ Página de enlaces (Instagram) ============================================ */

/** Gestión de la landing pública /dq (el link del perfil de Instagram): foto de
 *  fondo del coach + tienda del partner (ESN) con su código de descuento. */
function LinksPageManager() {
  const toast = useToast();
  const [brand, setBrand] = useState<import("../types").BrandConfigOut | null>(null);
  const [storeUrl, setStoreUrl] = useState("");
  const [code, setCode] = useState("");
  const [meetUrl, setMeetUrl] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadingPlans, setUploadingPlans] = useState(false);
  const photoRef = useRef<HTMLInputElement>(null);
  const plansPhotoRef = useRef<HTMLInputElement>(null);
  const publicUrl = `${window.location.origin}/dq`;

  useEffect(() => {
    api.getBrand()
      .then((b) => {
        setBrand(b);
        setStoreUrl(b.partner_store_url ?? "");
        setCode(b.partner_discount_code ?? "");
        setMeetUrl(b.meet_url ?? "");
      })
      .catch(() => toast.push("No se pudo cargar la configuración", "error"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function save() {
    if (!brand || saving) return;
    setSaving(true);
    try {
      // Base FRESCA de la marca: guardar aquí no puede pisar con una copia
      // vieja los cambios hechos entre medias en Ajustes u otra pestaña.
      const fresh = await api.getBrand().catch(() => brand);
      const { id, logo_path, links_photo_path, video_cover_path, plans_photo_path,
              ...body } = fresh;
      const updated = await api.updateBrand({
        ...body,
        partner_store_url: storeUrl.trim() || null,
        partner_discount_code: code.trim() || null,
        meet_url: meetUrl.trim() || null,
      });
      setBrand(updated);
      toast.push("Página de enlaces guardada");
    } catch (e) {
      toast.push(e instanceof ApiError ? e.message : "No se pudo guardar", "error");
    } finally {
      setSaving(false);
    }
  }

  async function uploadPhoto(file: File | undefined) {
    if (!file || uploading) return;
    setUploading(true);
    try {
      const updated = await api.uploadLinksPhoto(file);
      setBrand(updated);
      toast.push("Foto de fondo actualizada");
    } catch (e) {
      toast.push(e instanceof ApiError ? e.message : "No se pudo subir la foto", "error");
    } finally {
      setUploading(false);
    }
  }

  async function uploadPlansPhoto(file: File | undefined) {
    if (!file || uploadingPlans) return;
    setUploadingPlans(true);
    try {
      const updated = await api.uploadPlansPhoto(file);
      setBrand(updated);
      toast.push("Foto de los planes actualizada");
    } catch (e) {
      toast.push(e instanceof ApiError ? e.message : "No se pudo subir la foto", "error");
    } finally {
      setUploadingPlans(false);
    }
  }

  if (!brand) return <PageLoader />;

  return (
    <div className="max-w-2xl space-y-4">
      {/* El enlace público para el perfil de Instagram */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-zinc-200">Tu enlace para Instagram</h3>
        <p className="mt-1 text-sm text-zinc-500">
          Pon esta dirección en el perfil de Instagram. El cliente verá tu foto,
          el botón "Trabaja conmigo" (planes con pago) y la tienda ESN con tu código.
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

      {/* Foto de fondo */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-zinc-200">Foto de fondo</h3>
        <p className="mt-1 text-sm text-zinc-500">
          Una foto tuya en vertical (como fondo de pantalla). JPG/PNG, máx. 5 MB.
        </p>
        {api.mediaUrl(brand.links_photo_path) && (
          <img src={api.mediaUrl(brand.links_photo_path)!} alt="Foto de fondo actual"
            className="mt-3 h-40 w-28 rounded-xl border object-cover"
            style={{ borderColor: "var(--line-strong)" }} />
        )}
        <input ref={photoRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden"
          onChange={(e) => uploadPhoto(e.target.files?.[0])} />
        <button className="btn btn-ghost mt-3" disabled={uploading} onClick={() => photoRef.current?.click()}>
          <Upload size={15} className="text-zinc-500" />
          {uploading ? "Subiendo…" : brand.links_photo_path ? "Cambiar foto" : "Subir foto"}
        </button>
      </div>

      {/* Segunda foto: fondo de la página de PLANES (a donde va "Trabaja conmigo") */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-zinc-200">Foto de fondo de los planes</h3>
        <p className="mt-1 text-sm text-zinc-500">
          Segunda foto, para la página de contratación de planes (/planes). JPG/PNG, máx. 5 MB.
        </p>
        {api.mediaUrl(brand.plans_photo_path) && (
          <img src={api.mediaUrl(brand.plans_photo_path)!} alt="Foto de los planes actual"
            className="mt-3 h-28 w-44 rounded-xl border object-cover"
            style={{ borderColor: "var(--line-strong)" }} />
        )}
        <input ref={plansPhotoRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden"
          onChange={(e) => uploadPlansPhoto(e.target.files?.[0])} />
        <button className="btn btn-ghost mt-3" disabled={uploadingPlans} onClick={() => plansPhotoRef.current?.click()}>
          <Upload size={15} className="text-zinc-500" />
          {uploadingPlans ? "Subiendo…" : brand.plans_photo_path ? "Cambiar foto" : "Subir foto"}
        </button>
      </div>

      {/* Afiliación ESN */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-zinc-200">Tienda ESN (afiliación)</h3>
        <p className="mt-1 text-sm text-zinc-500">
          Enlace al catálogo de ESN y tu código de descuento. Si los dejas vacíos,
          la landing solo muestra "Trabaja conmigo".
        </p>
        <div className="mt-3 space-y-3">
          <div>
            <label className="label">Enlace de la tienda</label>
            <input className="input" placeholder="https://www.esn.com/..." value={storeUrl}
              onChange={(e) => setStoreUrl(e.target.value)} />
          </div>
          <div>
            <label className="label">Código de descuento</label>
            <input className="input" placeholder="DAVIDQUICENO" value={code}
              onChange={(e) => setCode(e.target.value)} />
          </div>
        </div>
        <button className="btn btn-primary mt-4" disabled={saving} onClick={save}>
          {saving ? "Guardando…" : "Guardar"}
        </button>
      </div>

      {/* Enlace de reservas de la videollamada quincenal (plan Pro) */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-zinc-200">Videollamadas (plan Pro)</h3>
        <p className="mt-1 text-sm text-zinc-500">
          Tu enlace de reservas (Google Calendar con Meet, Calendly…). Al proponer la
          videollamada quincenal por WhatsApp, el mensaje lo incluye para que el
          cliente elija día y hora él mismo.
        </p>
        <div className="mt-3">
          <label className="label">Enlace de reservas</label>
          <input className="input" placeholder="https://calendar.app.google/…" value={meetUrl}
            onChange={(e) => setMeetUrl(e.target.value)} />
        </div>
        <button className="btn btn-primary mt-4" disabled={saving} onClick={save}>
          {saving ? "Guardando…" : "Guardar"}
        </button>
      </div>
    </div>
  );
}

/* ==================================================== Productos ==================================================== */

const CATS: { id: ProductCategory; label: string; icon: typeof Pill }[] = [
  { id: "suplemento", label: "Suplemento", icon: Pill },
  { id: "material", label: "Material", icon: Dumbbell },
  { id: "otro", label: "Otro", icon: Package },
];

type Draft = {
  id: number | null;
  title: string;
  category: ProductCategory;
  url: string;
  description: string;
  image_url: string;        // URL de imagen EXTERNA (input de texto)
  uploaded: string | null;  // URL servida de una imagen YA subida (modo edición)
  discount_code: string;    // código de la marca (afiliación) — opcional
  active: boolean;
  file: File | null;        // nueva imagen elegida, pendiente de subir al guardar
};

const EMPTY_DRAFT: Draft = {
  id: null, title: "", category: "suplemento", url: "", description: "",
  image_url: "", uploaded: null, discount_code: "", active: true, file: null,
};

function ProductsManager() {
  const toast = useToast();
  const [products, setProducts] = useState<RecommendedProductOut[] | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [saving, setSaving] = useState(false);
  const [toDelete, setToDelete] = useState<RecommendedProductOut | null>(null);
  // Buscador del catálogo (útil cuando hay muchos productos que gestionar).
  const [q, setQ] = useState("");

  const [loadFailed, setLoadFailed] = useState(false);
  const load = useCallback(() => {
    setLoadFailed(false);
    // Un fallo de red NO se disfraza de catálogo vacío: banner + Reintentar.
    api.listProducts().then(setProducts).catch(() => { setProducts([]); setLoadFailed(true); });
  }, []);
  useEffect(load, [load]);

  const startNew = () => setDraft({ ...EMPTY_DRAFT });
  const startEdit = (p: RecommendedProductOut) =>
    setDraft({
      id: p.id, title: p.title, category: (p.category as ProductCategory) || "otro",
      url: p.url, description: p.description ?? "",
      // Si tiene imagen subida, p.image_url es su URL servida; se guarda aparte
      // (uploaded) y el input de URL externa queda vacío.
      image_url: p.has_upload ? "" : p.image_url ?? "",
      uploaded: p.has_upload ? p.image_url : null,
      discount_code: p.discount_code ?? "",
      active: p.active, file: null,
    });

  async function removeUpload() {
    if (!draft?.id) return;
    try {
      await api.removeProductImage(draft.id);
      setDraft({ ...draft, uploaded: null });
      toast.push("Imagen quitada");
      load();
    } catch {
      toast.push("No se pudo quitar la imagen", "error");
    }
  }

  async function save() {
    if (!draft) return;
    if (!draft.title.trim() || !draft.url.trim()) {
      toast.push("El título y el enlace son obligatorios", "error");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        title: draft.title.trim(),
        category: draft.category,
        url: draft.url.trim(),
        description: draft.description.trim() || null,
        image_url: draft.image_url.trim() || null,
        discount_code: draft.discount_code.trim() || null,
      };
      // Con imagen SUBIDA y el campo de URL externa vacío (el editor lo muestra
      // vacío a propósito), el PATCH NO manda image_url: conserva la URL externa
      // guardada, que vuelve a usarse si un día se quita la subida.
      const keepExternal = Boolean(draft.id && draft.uploaded && !draft.image_url.trim());
      const saved = draft.id
        ? await api.updateProduct(draft.id, {
            ...(keepExternal ? (({ image_url: _omit, ...rest }) => rest)(payload) : payload),
            active: draft.active,
          })
        : await api.createProduct(payload);
      if (draft.file) {
        try {
          await api.uploadProductImage(saved.id, draft.file);
        } catch (e) {
          // El producto YA está guardado: ancla el borrador a su id (reintentar
          // ACTUALIZA, nunca crea un duplicado) y explica que lo que falló fue
          // solo la imagen. El editor queda abierto para corregirla.
          setDraft({ ...draft, id: saved.id });
          load();
          toast.push(
            `Producto guardado, pero la imagen no se pudo subir${e instanceof ApiError ? `: ${e.message}` : ""}`,
            "error",
          );
          return;
        }
      }
      toast.push(draft.id ? "Producto actualizado" : "Producto añadido");
      setDraft(null);
      load();
    } catch (e) {
      toast.push(e instanceof ApiError ? e.message : "No se pudo guardar el producto", "error");
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(p: RecommendedProductOut) {
    try {
      await api.updateProduct(p.id, { active: !p.active });
      load();
    } catch {
      toast.push("No se pudo cambiar la visibilidad", "error");
    }
  }

  async function move(index: number, dir: -1 | 1) {
    if (!products) return;
    const j = index + dir;
    if (j < 0 || j >= products.length) return;
    const a = products[index];
    const b = products[j];
    try {
      await Promise.all([
        api.updateProduct(a.id, { sort_order: b.sort_order }),
        api.updateProduct(b.id, { sort_order: a.sort_order }),
      ]);
      load();
    } catch {
      toast.push("No se pudo reordenar", "error");
    }
  }

  // Guard con ref (no estado): un doble clic en "Eliminar" del diálogo no puede
  // disparar DOS DELETE (el segundo daría 404 y enseñaría un error falso).
  const deletingRef = useRef(false);
  async function confirmDelete() {
    if (deletingRef.current) return;
    deletingRef.current = true;
    try {
      await doDelete();
    } finally {
      deletingRef.current = false;
    }
  }

  async function doDelete() {
    if (!toDelete) return;
    try {
      await api.deleteProduct(toDelete.id);
      toast.push("Producto eliminado");
      setToDelete(null);
      load();
    } catch {
      toast.push("No se pudo eliminar", "error");
    }
  }

  if (products === null) return <PageLoader />;

  // Filtro por texto (nombre/categoría/enlace). Con búsqueda activa se ocultan
  // las flechas de reordenar (moverían el índice equivocado de la lista filtrada).
  const searching = q.trim().length > 0;
  const needle = q.trim().toLowerCase();
  const visible = searching
    ? products.filter((p) =>
        p.title.toLowerCase().includes(needle)
        || (p.category ?? "").toLowerCase().includes(needle)
        || (p.description ?? "").toLowerCase().includes(needle)
        || p.url.toLowerCase().includes(needle))
    : products;

  return (
    <div className="space-y-4">
      {loadFailed && (
        <div className="card flex flex-wrap items-center justify-between gap-3 p-3 text-sm text-zinc-300">
          <span>No se pudieron cargar los productos.</span>
          <button className="btn btn-ghost !px-3 !py-1.5 text-xs" onClick={load}>Reintentar</button>
        </div>
      )}
      {draft ? (
        <ProductEditor
          draft={draft}
          setDraft={setDraft}
          onSave={save}
          onCancel={() => setDraft(null)}
          onRemoveUpload={removeUpload}
          saving={saving}
        />
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          <button className="btn btn-primary" onClick={startNew}>
            <Plus size={16} /> Nuevo producto
          </button>
          {products.length > 4 && (
            <div className="relative min-w-48 flex-1">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
              <input className="input !py-2 !pl-9 text-sm" placeholder="Buscar producto…"
                value={q} onChange={(e) => setQ(e.target.value)} />
            </div>
          )}
        </div>
      )}

      {products.length === 0 && !draft ? (
        <EmptyState
          title="Aún no hay productos"
          hint="Añade suplementos o material que recomiendas; tus clientes los verán en la sección Recursos de su portal."
          action={
            <button className="btn btn-primary" onClick={startNew}>
              <Plus size={16} /> Nuevo producto
            </button>
          }
        />
      ) : visible.length === 0 ? (
        <EmptyState title="Sin resultados" hint="Prueba con otro término de búsqueda." />
      ) : (
        <ul className="space-y-2.5">
          {visible.map((p, i) => {
            const cat = CATS.find((c) => c.id === p.category) ?? CATS[2];
            return (
              <li
                key={p.id}
                className="card flex items-center gap-3 p-3"
                style={{ opacity: p.active ? 1 : 0.55 }}
              >
                {/* Reordenar solo sin búsqueda: con la lista filtrada el índice
                    no corresponde al del catálogo completo. */}
                {!searching && (
                  <div className="flex flex-col text-zinc-500">
                    <button
                      aria-label="Subir"
                      disabled={i === 0}
                      onClick={() => move(i, -1)}
                      className="tap -my-0.5 disabled:opacity-25"
                    >
                      <GripVertical size={14} className="rotate-90" />
                    </button>
                  </div>
                )}
                <ProductThumb src={p.image_url} icon={cat.icon} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center gap-1 text-[11px] uppercase tracking-wide text-zinc-500">
                      <cat.icon size={12} /> {cat.label}
                    </span>
                    {!p.active && <span className="text-[11px] text-zinc-500">· Oculto</span>}
                    {p.discount_code && (
                      <span
                        className="rounded px-1.5 py-0.5 text-[10px] font-semibold tracking-wide"
                        style={{ background: "color-mix(in srgb, var(--brand-accent) 12%, transparent)", color: "var(--brand-accent)" }}
                      >
                        código {p.discount_code}
                      </span>
                    )}
                  </div>
                  <p className="truncate text-sm font-semibold text-zinc-100">{p.title}</p>
                  <a
                    href={p.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex max-w-full items-center gap-1 truncate text-xs text-zinc-500 hover:text-zinc-300"
                  >
                    <ExternalLink size={11} className="shrink-0" />
                    <span className="truncate">{p.url}</span>
                  </a>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <button
                    onClick={() => toggleActive(p)}
                    className="rounded-lg px-2 py-1 text-xs text-zinc-400 hover:text-zinc-200"
                    title={p.active ? "Ocultar del portal" : "Mostrar en el portal"}
                  >
                    {p.active ? "Ocultar" : "Mostrar"}
                  </button>
                  <button
                    onClick={() => startEdit(p)}
                    aria-label="Editar"
                    className="rounded-lg p-2 text-zinc-400 hover:text-zinc-200"
                  >
                    <Pencil size={15} />
                  </button>
                  <button
                    onClick={() => setToDelete(p)}
                    aria-label="Eliminar"
                    className="rounded-lg p-2 text-zinc-400 hover:text-red-400"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <ConfirmDialog
        open={toDelete !== null}
        title="Eliminar producto"
        body={<>¿Seguro que quieres eliminar <strong>{toDelete?.title}</strong>? Dejará de verse en el portal.</>}
        confirmLabel="Eliminar"
        destructive
        onConfirm={confirmDelete}
        onCancel={() => setToDelete(null)}
      />
    </div>
  );
}

function ProductEditor({
  draft, setDraft, onSave, onCancel, onRemoveUpload, saving,
}: {
  draft: Draft;
  setDraft: Dispatch<SetStateAction<Draft | null>>;
  onSave: () => void;
  onCancel: () => void;
  onRemoveUpload: () => void;
  saving: boolean;
}) {
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  // La object-URL de la imagen elegida se crea en un efecto (no en el render) y se
  // revoca al cambiar/desmontar: sin fugas ni impureza en el render (StrictMode).
  const [preview, setPreview] = useState<string | null>(
    draft.image_url || draft.uploaded || null,
  );
  // Si la URL externa no carga (rota, host caído), el hueco cae al icono en vez
  // de quedarse con el "broken image" del navegador (mismo patrón que ProductThumb).
  const [previewOk, setPreviewOk] = useState(true);
  useEffect(() => setPreviewOk(true), [preview]);
  useEffect(() => {
    if (draft.file) {
      const url = URL.createObjectURL(draft.file);
      setPreview(url);
      return () => URL.revokeObjectURL(url);
    }
    setPreview(draft.image_url || draft.uploaded || null);
  }, [draft.file, draft.image_url, draft.uploaded]);

  const hasUpload = draft.uploaded !== null || draft.file !== null;

  // AUTORRELLENO desde el enlace: con pegar la URL del producto, el título, la
  // descripción y la imagen se leen de la propia página (metadatos OpenGraph).
  // En automático (al pegar/salir del campo) solo rellena lo VACÍO; el botón
  // manual sobreescribe con lo que traiga la página.
  const [scraping, setScraping] = useState(false);
  const scrapedUrl = useRef<string | null>(null);

  async function fillFromUrl(auto: boolean) {
    const url = draft.url.trim();
    if (!/^https?:\/\//i.test(url) || scraping) return;
    if (auto && scrapedUrl.current === url) return; // la misma URL no se relee sola
    scrapedUrl.current = url;
    setScraping(true);
    try {
      const meta = await api.scrapeProduct(url);
      if (!meta.title && !meta.description && !meta.image_url) {
        if (!auto) toast.push("La página no trae datos legibles: rellénalo a mano", "error");
        return;
      }
      // Merge sobre el borrador VIGENTE (update funcional): lo que el coach
      // teclee MIENTRAS se lee la página no se pisa, y si el editor ya se
      // cerró (guardó durante la lectura) no se reabre con datos viejos.
      setDraft((prev) => {
        if (!prev) return prev;
        const hasUp = prev.uploaded !== null || prev.file !== null;
        return {
          ...prev,
          title: auto && prev.title.trim() ? prev.title : (meta.title ?? prev.title),
          description: auto && prev.description.trim() ? prev.description : (meta.description ?? prev.description),
          image_url: hasUp || (auto && prev.image_url.trim())
            ? prev.image_url
            : (meta.image_url ?? prev.image_url),
        };
      });
      toast.push("Datos del producto rellenados desde el enlace");
    } catch (e) {
      if (!auto) toast.push(e instanceof ApiError ? e.message : "No se pudo leer la página del producto", "error");
    } finally {
      setScraping(false);
    }
  }

  return (
    <div className="card space-y-4 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-100">
          {draft.id ? "Editar producto" : "Nuevo producto"}
        </h3>
        <button onClick={onCancel} aria-label="Cerrar" className="text-zinc-500 hover:text-zinc-300">
          <X size={18} />
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-[120px_1fr]">
        {/* Imagen */}
        <div>
          <span className="label">Imagen</span>
          <div className="mt-1 flex flex-col items-center gap-2">
            <div
              className="flex h-24 w-24 items-center justify-center overflow-hidden rounded-xl border"
              style={{ borderColor: "var(--line-strong)", background: "var(--surface-raised)" }}
            >
              {preview && previewOk ? (
                <img src={preview} alt="" onError={() => setPreviewOk(false)} className="h-full w-full object-cover" />
              ) : (
                <ImageIcon size={22} className="text-zinc-500" />
              )}
            </div>
            <input
              ref={fileRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={(e) => setDraft({ ...draft, file: e.target.files?.[0] ?? null })}
            />
            <button className="btn btn-ghost !px-3 !py-1.5 text-xs" onClick={() => fileRef.current?.click()}>
              <Upload size={13} /> {draft.uploaded || draft.file ? "Cambiar" : "Subir"}
            </button>
            {draft.file ? (
              <button
                className="text-xs text-zinc-500 hover:text-zinc-300"
                onClick={() => { if (fileRef.current) fileRef.current.value = ""; setDraft({ ...draft, file: null }); }}
              >
                Descartar
              </button>
            ) : draft.uploaded ? (
              <button className="text-xs text-zinc-500 hover:text-red-400" onClick={onRemoveUpload}>
                Quitar imagen
              </button>
            ) : null}
          </div>
        </div>

        {/* Campos */}
        <div className="space-y-3">
          <div>
            <span className="label">Título *</span>
            <input
              className="input mt-1"
              value={draft.title}
              maxLength={160}
              placeholder="Proteína Whey"
              onChange={(e) => setDraft({ ...draft, title: e.target.value })}
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <span className="label">Categoría</span>
              <select
                className="input mt-1"
                value={draft.category}
                onChange={(e) => setDraft({ ...draft, category: e.target.value as ProductCategory })}
              >
                {CATS.map((c) => (
                  <option key={c.id} value={c.id}>{c.label}</option>
                ))}
              </select>
            </div>
            <div>
              <span className="label">Descripción</span>
              <input
                className="input mt-1"
                value={draft.description}
                maxLength={300}
                placeholder="30 g por toma"
                onChange={(e) => setDraft({ ...draft, description: e.target.value })}
              />
            </div>
          </div>
          <div>
            <span className="label">Enlace (URL) *</span>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <input
                className="input min-w-48 flex-1"
                value={draft.url}
                placeholder="https://tienda.com/producto"
                onChange={(e) => setDraft({ ...draft, url: e.target.value })}
                onBlur={() => fillFromUrl(true)}
              />
              <button
                className="btn btn-ghost shrink-0 !px-3 !py-2 text-xs"
                disabled={scraping || !/^https?:\/\//i.test(draft.url.trim())}
                onClick={() => fillFromUrl(false)}
                title="Lee la página del producto y rellena título, descripción e imagen"
              >
                {scraping ? <Spinner /> : <Sparkles size={13} />} Rellenar desde el enlace
              </button>
            </div>
            <p className="mt-1 text-[11px] text-zinc-500">
              Pega el enlace del producto y el resto de campos se rellenan solos.
            </p>
          </div>
          <p className="rounded-lg border px-3 py-2 text-[11px] text-zinc-500"
            style={{ borderColor: "var(--line-strong)" }}>
            El <strong>código de descuento es ÚNICO y global</strong>: se configura una
            sola vez en la pestaña <strong>Página de enlaces</strong> y se aplica solo
            a todos los productos (portal del cliente y landing de Instagram).
            Cambiarlo allí lo cambia en todas partes.
          </p>
          <div>
            <span className="label">…o URL de imagen externa (opcional)</span>
            <input
              className="input mt-1"
              value={draft.image_url}
              placeholder="https://…/imagen.jpg"
              disabled={hasUpload}
              onChange={(e) => setDraft({ ...draft, image_url: e.target.value })}
            />
            <p className="mt-1 text-[11px] text-zinc-500">
              {hasUpload
                ? "Tienes una imagen subida (tiene prioridad). Quítala para usar una URL externa."
                : "Si subes una imagen, tendrá prioridad sobre la URL externa."}
            </p>
          </div>
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <button className="btn btn-ghost" onClick={onCancel} disabled={saving}>Cancelar</button>
        <button className="btn btn-primary" onClick={onSave} disabled={saving}>
          {saving ? <Spinner className="text-white" /> : draft.id ? "Guardar" : "Añadir"}
        </button>
      </div>
    </div>
  );
}

function ProductThumb({ src, icon: Icon }: { src: string | null; icon: typeof Pill }) {
  const [ok, setOk] = useState(Boolean(src));
  useEffect(() => setOk(Boolean(src)), [src]); // tras subir/editar imagen, refleja el nuevo src
  return (
    <div
      className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-lg border"
      style={{ borderColor: "var(--line-strong)", background: "var(--surface-raised)" }}
    >
      {ok && src ? (
        <img src={src} alt="" className="h-full w-full object-cover" onError={() => setOk(false)} />
      ) : (
        <Icon size={18} className="text-zinc-500" />
      )}
    </div>
  );
}

/* =========================================== Vídeos de ejercicios =========================================== */

function ExerciseVideosManager() {
  const toast = useToast();
  const [all, setAll] = useState<ExerciseOut[] | null>(null);
  const [q, setQ] = useState("");
  const [onlySet, setOnlySet] = useState(false);

  const [loadFailed, setLoadFailed] = useState(false);
  const load = useCallback(() => {
    setLoadFailed(false);
    api.listExercises().then(setAll).catch(() => { setAll([]); setLoadFailed(true); });
  }, []);
  useEffect(load, [load]);

  const filtered = useMemo(() => {
    if (!all) return [];
    const needle = q.trim().toLowerCase();
    return all.filter((e) => {
      if (onlySet && !e.video_url && !e.image_url && !e.video_path) return false;
      if (!needle) return true;
      return (
        e.canonical_name.toLowerCase().includes(needle) ||
        (e.muscle_primary || "").toLowerCase().includes(needle) ||
        (e.aliases || []).some((a) => a.toLowerCase().includes(needle))
      );
    });
  }, [all, q, onlySet]);

  if (all === null) return <PageLoader />;

  const configured = all.filter((e) => e.video_url || e.image_url || e.video_path).length;

  return (
    <div className="space-y-4">
      {loadFailed && (
        <div className="card flex flex-wrap items-center justify-between gap-3 p-3 text-sm text-zinc-300">
          <span>No se pudieron cargar los ejercicios.</span>
          <button className="btn btn-ghost !px-3 !py-1.5 text-xs" onClick={load}>Reintentar</button>
        </div>
      )}
      <VideoCoverCard />
      <p className="text-sm text-zinc-500">
        Sube el <strong>vídeo de cada ejercicio</strong> (archivo MP4/MOV/WebM…) o pega un enlace
        (YouTube…). En el portal, el cliente verá los vídeos de los ejercicios de{" "}
        <strong>su</strong> rutina, todos con la portada de arriba.{" "}
        <span className="text-zinc-400">{configured} con vídeo/imagen.</span>
      </p>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1" style={{ minWidth: 220 }}>
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            className="input !pl-9"
            placeholder="Buscar ejercicio…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-zinc-400">
          <input type="checkbox" checked={onlySet} onChange={(e) => setOnlySet(e.target.checked)} />
          Solo configurados
        </label>
      </div>

      {filtered.length === 0 ? (
        <EmptyState title="Sin resultados" hint="Prueba con otro término de búsqueda." />
      ) : (
        <ul className="space-y-2.5">
          {filtered.map((ex) => (
            <ExerciseVideoRow key={ex.id} exercise={ex} onSaved={load} toast={toast} />
          ))}
        </ul>
      )}
    </div>
  );
}

/** Portada ÚNICA de todos los vídeos de ejercicios (la ve el cliente como
 *  miniatura de cada vídeo en su portal y su rutina). */
function VideoCoverCard() {
  const toast = useToast();
  const [brand, setBrand] = useState<import("../types").BrandConfigOut | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.getBrand().then(setBrand).catch(() => {});
  }, []);

  async function upload(file: File | undefined) {
    if (!file || uploading) return;
    setUploading(true);
    try {
      setBrand(await api.uploadVideoCover(file));
      toast.push("Portada de los vídeos actualizada");
    } catch (e) {
      toast.push(e instanceof ApiError ? e.message : "No se pudo subir la portada", "error");
    } finally {
      setUploading(false);
    }
  }

  const cover = api.mediaUrl(brand?.video_cover_path);
  return (
    <div className="card flex items-center gap-4 p-4">
      <div className="flex h-16 w-28 shrink-0 items-center justify-center overflow-hidden rounded-lg border"
        style={{ borderColor: "var(--line-strong)", background: "var(--surface-raised)" }}>
        {cover ? (
          <img src={cover} alt="Portada de los vídeos" className="h-full w-full object-cover" />
        ) : (
          <ImageIcon size={20} className="text-zinc-500" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <h3 className="text-sm font-semibold text-zinc-200">Portada de los vídeos</h3>
        <p className="mt-0.5 text-xs text-zinc-500">
          Una sola imagen como miniatura de TODOS los vídeos de ejercicios (JPG/PNG, máx. 5 MB).
        </p>
      </div>
      <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden"
        onChange={(e) => upload(e.target.files?.[0])} />
      <button className="btn btn-ghost shrink-0 !px-3 !py-1.5 text-xs" disabled={uploading}
        onClick={() => fileRef.current?.click()}>
        <Upload size={14} className="text-zinc-500" />
        {uploading ? "Subiendo…" : cover ? "Cambiar" : "Subir portada"}
      </button>
    </div>
  );
}

function ExerciseVideoRow({
  exercise: ex, onSaved, toast,
}: {
  exercise: ExerciseOut;
  onSaved: () => void;
  toast: ReturnType<typeof useToast>;
}) {
  const [video, setVideo] = useState(ex.video_url ?? "");
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [imgOk, setImgOk] = useState(true);
  const fileRef = useRef<HTMLInputElement>(null);

  const dirty = (video.trim() || null) !== (ex.video_url || null);

  const previewSrc = (ex.image_url ?? "").trim() || youtubeThumb(video.trim());
  useEffect(() => setImgOk(true), [previewSrc]); // al corregir la URL, reintenta cargar

  async function save() {
    setSaving(true);
    try {
      await api.updateExercise(ex.id, { video_url: video.trim() || null });
      toast.push("Ejercicio actualizado");
      onSaved();
    } catch (e) {
      toast.push(e instanceof ApiError ? e.message : "No se pudo guardar", "error");
    } finally {
      setSaving(false);
    }
  }

  async function uploadVideo(file: File | undefined) {
    if (!file || uploading) return;
    setUploading(true);
    try {
      await api.uploadExerciseVideo(ex.id, file);
      toast.push(`Vídeo de "${ex.canonical_name}" subido`);
      onSaved();
    } catch (e) {
      toast.push(e instanceof ApiError ? e.message : "No se pudo subir el vídeo", "error");
    } finally {
      setUploading(false);
    }
  }

  async function removeVideo() {
    if (uploading) return;
    setUploading(true);
    try {
      await api.deleteExerciseVideo(ex.id);
      toast.push("Vídeo quitado");
      onSaved();
    } catch (e) {
      toast.push(e instanceof ApiError ? e.message : "No se pudo quitar", "error");
    } finally {
      setUploading(false);
    }
  }

  return (
    <li className="card p-3">
      <div className="flex items-start gap-3">
        <div
          className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-lg border"
          style={{
            borderColor: ex.video_path ? "#2E7D46" : "var(--line-strong)",
            background: "var(--surface-raised)",
          }}
        >
          {ex.video_path ? (
            <Video size={18} style={{ color: "#2E7D46" }} />
          ) : previewSrc && imgOk ? (
            <img src={previewSrc} alt="" className="h-full w-full object-cover"
              onError={() => setImgOk(false)} />
          ) : (
            <Video size={18} className="text-zinc-500" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="truncate text-sm font-semibold text-zinc-100">{ex.canonical_name}</p>
            {ex.video_path && (
              <span className="rounded px-1.5 py-0.5 text-[10px] font-semibold"
                style={{ background: "color-mix(in srgb, #2E7D46 14%, transparent)", color: "#2E7D46" }}>
                Vídeo subido
              </span>
            )}
          </div>
          <p className="text-[11px] uppercase tracking-wide text-zinc-500">{ex.muscle_primary}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <input ref={fileRef} type="file" className="hidden"
              accept="video/*,.mp4,.mov,.webm,.m4v,.avi,.mkv,.wmv,.3gp"
              onChange={(e) => { uploadVideo(e.target.files?.[0]); e.target.value = ""; }} />
            <button className="btn btn-ghost !px-3 !py-1.5 text-xs" disabled={uploading}
              onClick={() => fileRef.current?.click()}>
              <Upload size={13} className="text-zinc-500" />
              {uploading ? "Subiendo…" : ex.video_path ? "Cambiar vídeo" : "Subir vídeo"}
            </button>
            {ex.video_path && (
              <button className="btn btn-ghost !px-2 !py-1.5 text-xs text-zinc-500"
                disabled={uploading} onClick={removeVideo}>
                <Trash2 size={13} /> Quitar
              </button>
            )}
            <input
              className="input min-w-40 flex-1 !py-1.5 text-xs"
              placeholder="…o URL del vídeo (YouTube)"
              value={video}
              onChange={(e) => setVideo(e.target.value)}
            />
          </div>
        </div>
        <button
          className="btn btn-primary !px-3 !py-1.5 text-xs"
          disabled={!dirty || saving}
          onClick={save}
        >
          {saving ? <Spinner className="text-white" /> : "Guardar"}
        </button>
      </div>
    </li>
  );
}

/** Portada de YouTube para la vista previa del coach — misma detección (host
 *  anclado, lib/video.ts) que usa el reproductor del portal: la vista previa
 *  enseña EXACTAMENTE lo que verá el cliente. */
function youtubeThumb(url: string): string | null {
  const id = youtubeId(url);
  return id ? `https://img.youtube.com/vi/${id}/hqdefault.jpg` : null;
}
