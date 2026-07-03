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
