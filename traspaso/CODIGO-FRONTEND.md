# Código FRONTEND — Fitness System

> Snapshot completo del código (un bloque por archivo, con su ruta). Generado para traspaso. Total: 36 archivos.


## `frontend/index.html`

```html
<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="robots" content="noindex" />
    <title>Asesorías Fitness</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
      rel="stylesheet"
    />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>

```


## `frontend/package.json`

```json
{
  "name": "fitness-system-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "date-fns": "^3.6.0",
    "lucide-react": "^0.383.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.0",
    "recharts": "^2.12.7"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.39",
    "tailwindcss": "^3.4.6",
    "typescript": "^5.5.3",
    "vite": "^5.3.4"
  }
}

```


## `frontend/src/App.tsx`

```tsx
import { BrowserRouter, Navigate, Route, Routes, useParams } from "react-router-dom";
import { useAuth } from "./hooks/useAuth";
import { PageLoader } from "./components/ui";
import LoginPage from "./pages/LoginPage";
import AppShell from "./components/AppShell";
import DashboardPage from "./pages/DashboardPage";
import ClientsPage from "./pages/ClientsPage";
import ClientProfilePage from "./pages/ClientProfilePage";
import BrandPage from "./pages/BrandPage";
import PortalApp from "./portal/PortalApp";

/**
 * Raíz. El portal del cliente (/p/:token) es público y se resuelve ANTES del
 * gate de autenticación del coach; el resto de rutas exigen sesión.
 */
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/p/:token" element={<PortalRoute />} />
        <Route path="/*" element={<CoachApp />} />
      </Routes>
    </BrowserRouter>
  );
}

function PortalRoute() {
  const { token } = useParams();
  return <PortalApp token={token!} />;
}

function CoachApp() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <PageLoader />
      </div>
    );
  }
  if (!user) return <LoginPage />;

  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="clientes" element={<ClientsPage />} />
        <Route path="clientes/:id" element={<ClientProfilePage />} />
        <Route path="marca" element={<BrandPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

```


## `frontend/src/components/AppShell.tsx`

```tsx
import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Dumbbell,
  LayoutDashboard,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  Users,
} from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { useBrand } from "../hooks/useBrand";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/clientes", label: "Clientes", icon: Users, end: false },
  { to: "/marca", label: "Marca", icon: Settings, end: false },
];

export default function AppShell() {
  const { user, logout } = useAuth();
  const { brand } = useBrand();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar colapsable (H.2) */}
      <aside
        className="flex flex-col border-r transition-all duration-200"
        style={{ borderColor: "var(--line)", width: collapsed ? 64 : 232, background: "var(--surface)" }}
      >
        <div className="flex h-16 items-center gap-3 px-4">
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
            style={{ background: "var(--brand-accent)" }}
          >
            <Dumbbell size={18} color="#0a0a0f" />
          </div>
          {!collapsed && (
            <span className="truncate text-sm font-semibold text-zinc-100">
              {brand?.name ?? "Asesorías"}
            </span>
          )}
        </div>

        <nav className="mt-2 flex-1 space-y-1 px-2.5">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${
                  isActive ? "text-zinc-100" : "text-zinc-500 hover:text-zinc-200"
                }`
              }
              style={({ isActive }) =>
                isActive ? { background: "var(--surface-raised)" } : undefined
              }
            >
              <Icon size={18} className="shrink-0" />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>

        <div className="border-t p-2.5" style={{ borderColor: "var(--line)" }}>
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-zinc-500 hover:text-zinc-200"
          >
            {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
            {!collapsed && <span>Contraer</span>}
          </button>
          <button
            onClick={() => {
              logout();
              navigate("/");
            }}
            className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-zinc-500 hover:text-zinc-200"
          >
            <LogOut size={18} />
            {!collapsed && <span className="truncate">Salir ({user?.username})</span>}
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto" style={{ background: "var(--bg)" }}>
        <Outlet />
      </main>
    </div>
  );
}

```


## `frontend/src/components/ClientAnamnesisTab.tsx`

```tsx
import { useEffect, useState } from "react";
import { FileText, Save, Sparkles } from "lucide-react";
import { api, ApiError, getToken } from "../lib/api";
import type { ClientOut, GoalType, Level } from "../types";
import { Spinner, useToast } from "./ui";

/**
 * Tab Anamnesis: ficha estructurada del cliente. Es la fuente de datos que la
 * IA usa para generar el plan. Puede rellenarse de dos formas:
 *  1. "Leer anamnesis con IA": lee el PDF subido y pre-rellena estos campos.
 *  2. A mano.
 * En ambos casos el coach revisa y corrige antes de generar (seguridad). El
 * PATCH del backend registra el diff campo a campo (audit trail).
 */
export function ClientAnamnesisTab({ client, onSaved }: { client: ClientOut; onSaved: () => void }) {
  const toast = useToast();
  const [draft, setDraft] = useState<Partial<ClientOut>>({});
  const [busy, setBusy] = useState(false);
  const [reading, setReading] = useState(false);
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [pdfName, setPdfName] = useState<string | null>(null);

  // Nombre del PDF de anamnesis subido (para poder verlo/descargarlo desde aquí).
  useEffect(() => {
    api.listClientDocuments(client.id)
      .then((docs) => setPdfName(docs[0]?.name ?? null))
      .catch(() => setPdfName(null));
  }, [client.id]);

  function openPdf() {
    if (!pdfName) return;
    fetch(api.clientDocumentUrl(client.id, pdfName), { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        window.open(url, "_blank");
        setTimeout(() => URL.revokeObjectURL(url), 60000);
      })
      .catch(() => toast.push("No se pudo abrir el PDF", "error"));
  }

  function set<K extends keyof ClientOut>(key: K, value: ClientOut[K]) {
    setDraft((d) => ({ ...d, [key]: value }));
  }
  function current<K extends keyof ClientOut>(key: K): ClientOut[K] {
    return (key in draft ? draft[key] : client[key]) as ClientOut[K];
  }
  const dirty = Object.keys(draft).length > 0;

  async function save() {
    if (!dirty || busy) return;
    setBusy(true);
    try {
      await api.updateClient(client.id, draft);
      toast.push("Anamnesis actualizada");
      setDraft({});
      onSaved();
    } catch (e) {
      toast.push(e instanceof ApiError ? e.message : "No se pudo guardar", "error");
    } finally {
      setBusy(false);
    }
  }

  async function readWithAI() {
    if (reading) return;
    setReading(true);
    try {
      const res = await api.readAnamnesis(client.id);
      setAnalysis(res.deep_analysis);
      setDraft({});
      toast.push("Anamnesis leída. Revisa los datos antes de generar.");
      onSaved();
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push(detail?.message ?? e?.message ?? "No se pudo leer el PDF", "error");
    } finally {
      setReading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="card flex flex-wrap items-center justify-between gap-3 p-4">
        <div className="flex items-center gap-2.5">
          <Sparkles size={17} style={{ color: "var(--brand-accent)" }} />
          <div>
            <p className="text-sm font-medium text-zinc-200">Leer anamnesis con IA</p>
            <p className="text-xs text-zinc-500">Lee el PDF subido y rellena estos campos automáticamente.</p>
          </div>
        </div>
        <div className="flex gap-2">
          {pdfName && (
            <button onClick={openPdf} className="btn btn-ghost" title={pdfName}>
              <FileText size={15} /> Ver PDF
            </button>
          )}
          <button onClick={readWithAI} disabled={reading} className="btn btn-primary">
            <Sparkles size={15} /> {reading ? "Leyendo PDF…" : "Leer con IA"}
          </button>
        </div>
      </div>

      {analysis && (
        <div className="card p-4">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">Análisis de la IA</p>
          <p className="text-sm text-zinc-300">{analysis}</p>
        </div>
      )}

      <Section title="Datos personales">
        <Select label="Sexo" value={(current("sex") as string) ?? ""} onChange={(v) => set("sex", v as any)}
          options={[["", "—"], ["male", "Hombre"], ["female", "Mujer"]]} />
        <Field label="Fecha de nacimiento" type="date" value={(current("birth_date") as string) ?? ""}
          onChange={(v) => set("birth_date", v as any)} />
      </Section>

      <Section title="Antropometría inicial">
        <Num label="Altura (cm)" value={current("height_cm") as number} onChange={(v) => set("height_cm", v as any)} />
        <Num label="Peso actual (kg)" value={current("start_weight_kg") as number} onChange={(v) => set("start_weight_kg", v as any)} />
        <Num label="% graso (opcional)" value={current("body_fat_pct") as number} onChange={(v) => set("body_fat_pct", v as any)} />
        <Num label="Peso objetivo (kg)" value={current("goal_weight_kg") as number} onChange={(v) => set("goal_weight_kg", v as any)} />
      </Section>

      <Section title="Objetivo y nivel">
        <Select label="Objetivo" value={(current("goal_type") as string) ?? ""} onChange={(v) => set("goal_type", v as GoalType)}
          options={[["", "—"], ["fat_loss", "Pérdida de grasa"], ["muscle_gain", "Ganancia muscular"], ["recomp", "Recomposición"]]} />
        <Select label="Nivel" value={(current("level") as string) ?? ""} onChange={(v) => set("level", v as Level)}
          options={[["", "—"], ["beginner", "Principiante"], ["intermediate", "Intermedio"], ["advanced", "Avanzado"]]} />
      </Section>

      <Section title="Entrenamiento">
        <Num label="Días por semana" value={current("training_days") as number} onChange={(v) => set("training_days", v as any)} />
        <Num label="Duración sesión (min)" value={current("session_max_min") as number} onChange={(v) => set("session_max_min", v as any)} />
        <Select label="Dónde entrena" value={(current("training_place") as string) ?? ""} onChange={(v) => set("training_place", v as any)}
          options={[["", "—"], ["gym", "Gimnasio"], ["home", "Casa"], ["outdoor", "Exterior"]]} />
        <CSV label="Material (solo casa/exterior)" value={current("equipment") as string[]} onChange={(v) => set("equipment", v as any)} />
      </Section>

      <Section title="Experiencia y otros deportes">
        <Area label="Experiencia con pesas y otros deportes" value={(current("sport_history") as string) ?? ""} onChange={(v) => set("sport_history", v as any)} />
      </Section>

      <Section title="Dieta">
        <Select label="Modo de dieta" value={(current("diet_mode") as string) ?? ""} onChange={(v) => set("diet_mode", v as any)}
          options={[["", "—"], ["flexible_7", "Flexible (equivalencias)"], ["strict", "Menú cerrado"]]} />
        <Num label="Comidas al día" value={current("meals_per_day") as number} onChange={(v) => set("meals_per_day", v as any)} />
        <CSV label="Alimentos que le gustan" value={current("food_likes") as string[]} onChange={(v) => set("food_likes", v as any)} />
        <CSV label="Alimentos que evita" value={current("food_dislikes") as string[]} onChange={(v) => set("food_dislikes", v as any)} />
        <CSV label="Alergias" value={current("food_allergies") as string[]} onChange={(v) => set("food_allergies", v as any)} />
      </Section>

      <Section title="Historia clínica y salud">
        <Area label="Historia clínica (patologías, antecedentes, digestivo, salud femenina…)"
          value={(current("medical_notes") as string) ?? ""} onChange={(v) => set("medical_notes", v as any)} />
        <Area label="Medicación actual (nombre, dosis, frecuencia)"
          value={(current("medication_notes") as string) ?? ""} onChange={(v) => set("medication_notes", v as any)} />
        <Area label="Suplementación actual"
          value={(current("current_supplements") as string) ?? ""} onChange={(v) => set("current_supplements", v as any)} />
      </Section>

      <Section title="Lesiones y movilidad">
        <Area label="Lesiones / molestias (zona, lado y qué evitar)" value={(current("injuries_notes") as string) ?? ""} onChange={(v) => set("injuries_notes", v as any)} />
      </Section>

      <Section title="Estilo de vida">
        <Area label="Hábitos, sueño, estrés, hidratación, conducta alimentaria, motivo y objetivos"
          value={(current("lifestyle_notes") as string) ?? ""} onChange={(v) => set("lifestyle_notes", v as any)} />
      </Section>

      <div className="flex items-center gap-3">
        <button onClick={save} disabled={!dirty || busy} className="btn btn-primary">
          {busy ? <Spinner /> : <Save size={15} />} Guardar cambios
        </button>
        {dirty && <span className="text-xs text-zinc-500">Tienes cambios sin guardar</span>}
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card p-5">
      <h4 className="mb-3 text-sm font-semibold text-zinc-200">{title}</h4>
      <div className="grid grid-cols-2 gap-3">{children}</div>
    </div>
  );
}
function Field({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (v: string) => void; type?: string }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-zinc-500">{label}</span>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} className="input w-full" />
    </label>
  );
}
function Num({ label, value, onChange }: { label: string; value: number | null | undefined; onChange: (v: number | null) => void }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-zinc-500">{label}</span>
      <input type="number" value={value ?? ""} onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))} className="input w-full" />
    </label>
  );
}
function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: [string, string][] }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-zinc-500">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} className="input w-full">
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </label>
  );
}
function Area({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="col-span-2 block">
      <span className="mb-1 block text-xs text-zinc-500">{label}</span>
      <textarea value={value} onChange={(e) => onChange(e.target.value)} rows={3} className="input w-full resize-y" />
    </label>
  );
}
function CSV({ label, value, onChange }: { label: string; value: string[] | null | undefined; onChange: (v: string[]) => void }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-zinc-500">{label}</span>
      <input type="text" value={(value ?? []).join(", ")}
        onChange={(e) => onChange(e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
        placeholder="separa por comas" className="input w-full" />
    </label>
  );
}

```


## `frontend/src/components/ClientDocuments.tsx`

```tsx
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
          style={{ background: "rgba(110,231,183,0.10)", border: "1px solid rgba(110,231,183,0.25)" }}
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
          background: dragOver ? "rgba(110,231,183,0.06)" : "transparent",
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

```


## `frontend/src/components/ClientFeedbackTab.tsx`

```tsx
import { useCallback, useEffect, useState } from "react";
import { Sparkles, Download, AlertTriangle, MessageSquare, Target, TrendingUp, BarChart3, Image as ImageIcon, Send, CheckCircle2 } from "lucide-react";
import { api, getToken } from "../lib/api";
import { Spinner, useToast } from "./ui";
import type { ClientOut } from "../types";

interface Period {
  id: number;
  period_index: number;
  starts_on: string;
  ends_on: string;
  status: string;
  closing_weight_kg: number | null;
  closing_rating: number | null;
  closing_hardest: string | null;
  closing_questions: string | null;
  closing_waist_cm: number | null;
  closing_hip_cm: number | null;
  closing_arm_cm: number | null;
  closing_thigh_cm: number | null;
  feedback_id: number | null;
}

/**
 * Feedback: cierra el ciclo de la asesoría. Cuando el cliente cierra un período
 * (peso final, perímetros, valoración, dudas), el coach genera aquí el informe
 * de feedback con IA (análisis + recomendaciones) sobre las métricas calculadas
 * por el backend, lo revisa, y lo descarga en Word para enviarlo.
 */
export function ClientFeedbackTab({ client, onClientChanged }: { client: ClientOut; onClientChanged?: () => void }) {
  const toast = useToast();
  const [periods, setPeriods] = useState<Period[] | null>(null);
  const [contents, setContents] = useState<Record<number, any>>({});
  const [generating, setGenerating] = useState<number | null>(null);
  const [sending, setSending] = useState<number | null>(null);
  const [metrics, setMetrics] = useState<Record<number, any>>({});
  const [loadingMetrics, setLoadingMetrics] = useState<number | null>(null);
  const [photos, setPhotos] = useState<{ id: number; kind: string; period_id: number | null; taken_at: string }[]>([]);

  async function loadMetrics(periodId: number) {
    if (loadingMetrics) return;
    setLoadingMetrics(periodId);
    try {
      const m = await api.getPeriodMetrics(periodId);
      setMetrics((prev) => ({ ...prev, [periodId]: m }));
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push(detail?.message ?? e?.message ?? "No se pudo cargar el resumen", "error");
    } finally {
      setLoadingMetrics(null);
    }
  }

  const load = useCallback(() => {
    api.listPeriods(client.id)
      .then(async (ps) => {
        setPeriods(ps);
        // Carga el contenido de los feedbacks ya existentes para mostrarlo.
        const withFb = ps.filter((p) => p.feedback_id);
        const entries = await Promise.all(
          withFb.map((p) =>
            api.getFeedback(p.feedback_id as number)
              .then((f) => [p.feedback_id, { content: f.content, sent_at: f.sent_at }] as const)
              .catch(() => null),
          ),
        );
        const map: Record<number, any> = {};
        entries.forEach((e) => e && (map[e[0] as number] = e[1]));
        setContents(map);
      })
      .catch(() => setPeriods([]));
    api.listClientPhotos(client.id).then(setPhotos).catch(() => setPhotos([]));
  }, [client.id]);

  useEffect(load, [load]);

  async function generate(periodId: number) {
    if (generating) return;
    setGenerating(periodId);
    try {
      await api.generateFeedback(periodId);
      toast.push("Feedback generado. Revísalo y descárgalo.");
      load();
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push(detail?.message ?? e?.message ?? "No se pudo generar el feedback", "error");
    } finally {
      setGenerating(null);
    }
  }

  async function send(feedbackId: number) {
    if (sending) return;
    setSending(feedbackId);
    try {
      await api.sendFeedback(feedbackId);
      toast.push("Feedback enviado: ya es visible en el portal del cliente");
      load();
      onClientChanged?.(); // refresca el perfil para cerrar la notificación
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo enviar el feedback", "error");
    } finally {
      setSending(null);
    }
  }

  function downloadDoc(docId: number) {
    fetch(api.feedbackDocumentUrl(docId), { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `feedback_${client.full_name.replace(/\s+/g, "_").toLowerCase()}.docx`;
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch(() => toast.push("No se pudo descargar", "error"));
  }

  if (periods === null) {
    return (
      <div className="card flex items-center justify-center gap-2 p-8 text-sm text-zinc-500">
        <Spinner /> Cargando feedback…
      </div>
    );
  }

  if (periods.length === 0) {
    return (
      <div className="card p-6">
        <h3 className="text-base font-semibold text-zinc-100">Feedback</h3>
        <p className="mt-1 text-sm text-zinc-400">
          Aún no hay períodos. El feedback se genera cuando el cliente cierra un período
          (publica un plan, crea el período y el cliente registra su diario y lo cierra).
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {periods.map((p) => {
        const fb = p.feedback_id ? contents[p.feedback_id] : null;
        const content = fb?.content;
        const sent: string | null = fb?.sent_at ?? null;
        const canGenerate = p.status !== "open"; // cerrado o analizado
        const daysElapsed = Math.floor((Date.now() - new Date(p.starts_on + "T00:00:00").getTime()) / 86400000) + 1;
        const ready = p.status !== "open" || daysElapsed >= 14; // resumen disponible a las 2 semanas
        const m = metrics[p.id];
        const periodPhotos = photos.filter((ph) => ph.period_id === p.id);
        return (
          <div key={p.id} className="card p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-semibold text-zinc-100">Período {p.period_index}</h3>
                  <span className="rounded-full px-2 py-0.5 text-xs font-medium" style={badge(p.status)}>
                    {STATUS_LABEL[p.status] ?? p.status}
                  </span>
                  {sent && (
                    <span className="flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium" style={{ background: "rgba(110,231,183,0.15)", color: "var(--brand-accent)" }}>
                      <CheckCircle2 size={12} /> Feedback enviado
                    </span>
                  )}
                </div>
                <p className="mt-0.5 text-xs text-zinc-500">{p.starts_on} → {p.ends_on}</p>
              </div>
              <div className="flex gap-2">
                {ready && (
                  <button onClick={() => loadMetrics(p.id)} disabled={loadingMetrics === p.id} className="btn btn-ghost">
                    <BarChart3 size={15} /> {loadingMetrics === p.id ? "Calculando…" : "Resumen"}
                  </button>
                )}
                {p.feedback_id && (
                  <button onClick={() => downloadDoc(p.feedback_id as number)} className="btn btn-ghost">
                    <Download size={15} /> Descargar Word
                  </button>
                )}
                {p.feedback_id && !sent && (
                  <button onClick={() => send(p.feedback_id as number)} disabled={sending === p.feedback_id} className="btn btn-primary">
                    <Send size={15} /> {sending === p.feedback_id ? "Enviando…" : "Enviar al cliente"}
                  </button>
                )}
                {canGenerate && (
                  <button onClick={() => generate(p.id)} disabled={generating === p.id} className="btn btn-primary">
                    <Sparkles size={15} />
                    {generating === p.id ? "Generando…" : p.feedback_id ? "Regenerar feedback" : "Generar feedback"}
                  </button>
                )}
              </div>
            </div>

            {p.status === "open" && (
              <div className="mt-3 flex items-center gap-2 rounded-lg p-2.5 text-xs" style={{ background: "rgba(247,201,110,0.08)", color: "#F7C96E" }}>
                <AlertTriangle size={14} /> El período aún está abierto: el cliente debe cerrarlo antes de generar el feedback.
              </div>
            )}

            {/* Datos del cierre */}
            {p.status !== "open" && (
              <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                {p.closing_weight_kg != null && <Stat label="Peso final" value={`${p.closing_weight_kg} kg`} />}
                {p.closing_rating != null && <Stat label="Valoración" value={`${p.closing_rating}/5`} />}
                {p.closing_waist_cm != null && <Stat label="Cintura" value={`${p.closing_waist_cm} cm`} />}
                {p.closing_hip_cm != null && <Stat label="Cadera" value={`${p.closing_hip_cm} cm`} />}
                {p.closing_arm_cm != null && <Stat label="Brazo" value={`${p.closing_arm_cm} cm`} />}
                {p.closing_thigh_cm != null && <Stat label="Muslo" value={`${p.closing_thigh_cm} cm`} />}
              </div>
            )}
            {p.closing_hardest && <p className="mt-2 text-xs text-zinc-400"><b className="text-zinc-300">Lo más difícil:</b> {p.closing_hardest}</p>}
            {p.closing_questions && <p className="mt-1 text-xs text-zinc-400"><b className="text-zinc-300">Dudas:</b> {p.closing_questions}</p>}

            {/* Resumen de métricas (sin IA): fuerza, peso, adherencia, objetivo */}
            {m && (
              <div className="mt-4 space-y-3 border-t pt-4" style={{ borderColor: "var(--line)" }}>
                <SubTitle icon={BarChart3} text="Resumen de las 2 semanas" />
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  <Stat label="Δ peso corporal" value={fmtDelta(m.weight?.delta_kg, "kg")} />
                  <Stat label="Peso actual" value={m.body_weight_now_kg != null ? `${m.body_weight_now_kg} kg` : "—"} />
                  <Stat label="A su objetivo" value={m.distance_to_goal_kg != null ? `${Math.abs(m.distance_to_goal_kg)} kg` : "—"} />
                  <Stat label="Adherencia dieta" value={`${m.adherence?.diet_pct ?? 0}%`} />
                  <Stat label="Días registrados" value={`${m.adherence?.days_logged ?? 0}/${m.adherence?.period_days ?? 0}`} />
                  <Stat label="Ritmo semanal" value={fmtDelta(m.weight?.weekly_rate_kg, "kg/sem")} />
                </div>
                {Array.isArray(m.strength) && m.strength.length > 0 && (
                  <div>
                    <SubTitle icon={TrendingUp} text="Fuerza ganada (e1RM)" />
                    <ul className="space-y-1 text-sm">
                      {m.strength.map((s: any, i: number) => (
                        <li key={i} className="flex items-center justify-between rounded-lg px-3 py-1.5" style={{ background: "var(--surface-raised)" }}>
                          <span className="truncate text-zinc-300">{s.name}</span>
                          <span className="whitespace-nowrap text-zinc-400">
                            {Math.round(s.e1rm_kg)} kg
                            {s.delta_kg != null && (
                              <span style={{ color: s.delta_kg >= 0 ? "var(--brand-accent)" : "#F77E7E" }}>
                                {" "}{s.delta_kg >= 0 ? "▲" : "▼"} {Math.abs(s.delta_kg)}
                              </span>
                            )}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {(!m.strength || m.strength.length === 0) && (
                  <p className="text-xs text-zinc-500">Sin series registradas aún para calcular la fuerza.</p>
                )}
              </div>
            )}

            {/* Fotos del cliente (subidas en el portal) */}
            {periodPhotos.length > 0 && (
              <div className="mt-4 border-t pt-4" style={{ borderColor: "var(--line)" }}>
                <SubTitle icon={ImageIcon} text="Fotos del cliente" />
                <div className="mt-1 flex flex-wrap gap-2">
                  {periodPhotos.map((ph) => (
                    <PhotoThumb key={ph.id} clientId={client.id} photo={ph} />
                  ))}
                </div>
              </div>
            )}

            {/* Contenido del feedback generado */}
            {content && (
              <div className="mt-4 space-y-3 border-t pt-4" style={{ borderColor: "var(--line)" }}>
                {content.natural_analysis && (
                  <div>
                    <SubTitle icon={TrendingUp} text="Análisis" />
                    <p className="text-sm text-zinc-300">{content.natural_analysis}</p>
                  </div>
                )}
                {Array.isArray(content.changes_bullets) && content.changes_bullets.length > 0 && (
                  <div>
                    <SubTitle icon={Sparkles} text="Cambios en el plan" />
                    <ul className="list-disc space-y-0.5 pl-5 text-sm text-zinc-400">
                      {content.changes_bullets.map((b: string, i: number) => <li key={i}>{b}</li>)}
                    </ul>
                  </div>
                )}
                {content.answers && (
                  <div>
                    <SubTitle icon={MessageSquare} text="Respuesta a sus dudas" />
                    <p className="text-sm text-zinc-300">{content.answers}</p>
                  </div>
                )}
                {Array.isArray(content.next_objectives) && content.next_objectives.length > 0 && (
                  <div>
                    <SubTitle icon={Target} text="Objetivos próximas 2 semanas" />
                    <ul className="list-disc space-y-0.5 pl-5 text-sm text-zinc-400">
                      {content.next_objectives.map((o: string, i: number) => <li key={i}>{o}</li>)}
                    </ul>
                  </div>
                )}
                {content.closing_message && <p className="text-sm italic text-zinc-400">{content.closing_message}</p>}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

const STATUS_LABEL: Record<string, string> = { open: "Abierto", closed: "Cerrado", analyzed: "Analizado" };
function badge(status: string): React.CSSProperties {
  if (status === "analyzed") return { background: "rgba(110,231,183,0.15)", color: "var(--brand-accent)" };
  if (status === "closed") return { background: "rgba(247,201,110,0.15)", color: "#F7C96E" };
  return { background: "rgba(255,255,255,0.08)", color: "#a1a1aa" };
}

function fmtDelta(v: number | null | undefined, unit: string): string {
  if (v == null) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v} ${unit}`;
}

function PhotoThumb({ clientId, photo }: { clientId: number; photo: { id: number; kind: string } }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    let obj: string | null = null;
    fetch(api.clientPhotoUrl(clientId, photo.id), { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => r.blob())
      .then((b) => { if (alive) { obj = URL.createObjectURL(b); setUrl(obj); } })
      .catch(() => {});
    return () => { alive = false; if (obj) URL.revokeObjectURL(obj); };
  }, [clientId, photo.id]);

  function download() {
    if (!url) return;
    const a = document.createElement("a");
    a.href = url;
    a.download = `foto_${photo.kind}_${photo.id}.jpg`;
    a.click();
  }

  return (
    <div className="overflow-hidden rounded-lg border" style={{ borderColor: "var(--line)", width: 96 }}>
      {url ? (
        <img src={url} alt={photo.kind} className="h-24 w-24 object-cover" />
      ) : (
        <div className="flex h-24 w-24 items-center justify-center text-xs text-zinc-600">…</div>
      )}
      <button onClick={download} className="flex w-full items-center justify-center gap-1 py-1 text-[10px] text-zinc-400 hover:text-zinc-200">
        <Download size={11} /> {photo.kind}
      </button>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg p-2.5 text-center" style={{ background: "var(--surface-raised)" }}>
      <div className="text-sm font-bold text-zinc-100">{value}</div>
      <div className="text-xs text-zinc-500">{label}</div>
    </div>
  );
}

function SubTitle({ icon: Icon, text }: { icon: typeof Target; text: string }) {
  return (
    <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">
      <Icon size={13} /> {text}
    </div>
  );
}

```


## `frontend/src/components/ClientPlanEditor.tsx`

```tsx
import { useState } from "react";
import { Save, X, Plus, Trash2, Utensils, Dumbbell } from "lucide-react";
import { api } from "../lib/api";
import { Spinner, useToast } from "./ui";

interface PlanData {
  id: number;
  month_index: number;
  version: number;
  status: string;
  guardrail_flags: string[];
  nutrition: any;
  training: any;
  education: any;
}

/**
 * Editor manual del plan (revisión del coach antes de enviar). Edita nutrición,
 * entrenamiento y educativo y los guarda (PATCH /plans/{id}). El banco de comidas
 * no se edita aquí (se muestra en la vista); cambiar un ejercicio por otro se hace
 * con el "swap". Guarda el JSON tal cual: los guardrails no se re-ejecutan (es
 * edición del coach bajo su criterio).
 */
export function ClientPlanEditor({
  plan, exMap, onSaved, onCancel,
}: {
  plan: PlanData;
  exMap: Record<number, string>;
  onSaved: (p: PlanData) => void;
  onCancel: () => void;
}) {
  const toast = useToast();
  const [draft, setDraft] = useState(() => ({
    nutrition: structuredClone(plan.nutrition ?? {}),
    training: structuredClone(plan.training ?? {}),
    education: structuredClone(plan.education ?? {}),
  }));
  const [saving, setSaving] = useState(false);

  function mutate(fn: (d: typeof draft) => void) {
    setDraft((d) => { const n = structuredClone(d); fn(n); return n; });
  }

  async function save() {
    if (saving) return;
    setSaving(true);
    try {
      const r = await api.updatePlan(plan.id, {
        nutrition_json: draft.nutrition,
        training_json: draft.training,
        education_json: draft.education,
      });
      toast.push("Plan actualizado");
      onSaved({
        ...plan,
        nutrition: r.nutrition_json, training: r.training_json, education: r.education_json,
        guardrail_flags: r.guardrail_flags ?? [], status: r.status, version: r.version,
      });
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo guardar el plan", "error");
    } finally {
      setSaving(false);
    }
  }

  const nut = draft.nutrition;
  const tr = draft.training;
  nut.macros = nut.macros ?? {};
  nut.supplements = nut.supplements ?? [];
  nut.flexibility_rules = nut.flexibility_rules ?? [];
  tr.weekly_progression = tr.weekly_progression ?? [];
  tr.sessions = tr.sessions ?? [];
  tr.cardio = tr.cardio ?? { daily_steps: 0, sessions: [] };

  return (
    <div className="space-y-4">
      <div className="card sticky top-2 z-10 flex items-center justify-between p-4">
        <h3 className="text-base font-semibold text-zinc-100">Editar plan · Mes {plan.month_index}</h3>
        <div className="flex gap-2">
          <button onClick={onCancel} className="btn btn-ghost"><X size={15} /> Cancelar</button>
          <button onClick={save} disabled={saving} className="btn btn-primary">
            {saving ? <Spinner /> : <Save size={15} />} Guardar cambios
          </button>
        </div>
      </div>

      {/* Nutrición */}
      <div className="card p-5">
        <Title icon={Utensils} text="Nutrición" />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Num label="Calorías objetivo" value={nut.target_kcal} onChange={(v) => mutate((d) => (d.nutrition.target_kcal = v))} />
          <Num label="Proteína (g)" value={nut.macros.protein_g} onChange={(v) => mutate((d) => (d.nutrition.macros.protein_g = v))} />
          <Num label="Carbohidratos (g)" value={nut.macros.carbs_g} onChange={(v) => mutate((d) => (d.nutrition.macros.carbs_g = v))} />
          <Num label="Grasas (g)" value={nut.macros.fat_g} onChange={(v) => mutate((d) => (d.nutrition.macros.fat_g = v))} />
        </div>
        <Area label="Justificación (rationale)" value={nut.rationale ?? ""} onChange={(v) => mutate((d) => (d.nutrition.rationale = v))} />
        <Area label="Reglas de flexibilidad (una por línea)" value={(nut.flexibility_rules ?? []).join("\n")}
          onChange={(v) => mutate((d) => (d.nutrition.flexibility_rules = v.split("\n").map((s) => s.trim()).filter(Boolean)))} />

        <Subhead text="Suplementos" onAdd={() => mutate((d) => d.nutrition.supplements.push({ name: "", dose: "", timing: "", evidence_note: "" }))} />
        {nut.supplements.map((s: any, i: number) => (
          <Row key={i} onRemove={() => mutate((d) => d.nutrition.supplements.splice(i, 1))}>
            <Text label="Nombre" value={s.name} onChange={(v) => mutate((d) => (d.nutrition.supplements[i].name = v))} />
            <Text label="Dosis" value={s.dose} onChange={(v) => mutate((d) => (d.nutrition.supplements[i].dose = v))} />
            <Text label="Momento" value={s.timing} onChange={(v) => mutate((d) => (d.nutrition.supplements[i].timing = v))} />
            <Text label="Nota" value={s.evidence_note ?? ""} onChange={(v) => mutate((d) => (d.nutrition.supplements[i].evidence_note = v))} />
          </Row>
        ))}
      </div>

      {/* Entrenamiento */}
      <div className="card p-5">
        <Title icon={Dumbbell} text="Entrenamiento" />
        <Text label="Nombre del split" value={tr.split_name ?? ""} onChange={(v) => mutate((d) => (d.training.split_name = v))} />
        <Area label="Justificación del split" value={tr.split_rationale ?? ""} onChange={(v) => mutate((d) => (d.training.split_rationale = v))} />

        <Subhead text="Progresión semanal" />
        {tr.weekly_progression.map((w: any, i: number) => (
          <div key={i} className="mt-2 grid grid-cols-2 gap-2 rounded-lg p-2 sm:grid-cols-4" style={{ background: "var(--surface-raised)" }}>
            <Text label={`Sem ${w.week ?? i + 1} · intención`} value={w.intent ?? ""} onChange={(v) => mutate((d) => (d.training.weekly_progression[i].intent = v))} />
            <Num label="Carga %" value={w.load_pct} onChange={(v) => mutate((d) => (d.training.weekly_progression[i].load_pct = v))} />
            <Text label="RIR" value={w.rir_target ?? ""} onChange={(v) => mutate((d) => (d.training.weekly_progression[i].rir_target = v))} />
            <Text label="Volumen" value={w.volume_note ?? ""} onChange={(v) => mutate((d) => (d.training.weekly_progression[i].volume_note = v))} />
          </div>
        ))}

        <Subhead text="Sesiones" />
        {tr.sessions.map((s: any, si: number) => (
          <div key={si} className="mt-2 rounded-lg p-3" style={{ background: "var(--surface-raised)" }}>
            <div className="grid grid-cols-2 gap-2">
              <Text label="Día" value={s.day ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].day = v))} />
              <Text label="Nombre" value={s.name ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].name = v))} />
            </div>
            <Area label="Calentamiento" value={s.warmup ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].warmup = v))} />
            {(s.exercises ?? []).map((ex: any, ei: number) => (
              <div key={ei} className="mt-2 rounded-md p-2" style={{ background: "var(--surface)" }}>
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-xs font-medium text-zinc-200">{exMap[ex.exercise_id] ?? `Ejercicio #${ex.exercise_id}`}</span>
                  <button onClick={() => mutate((d) => d.training.sessions[si].exercises.splice(ei, 1))} className="text-zinc-500 hover:text-red-400"><Trash2 size={14} /></button>
                </div>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <Num label="Series" value={ex.sets} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].sets = v))} />
                  <Text label="Reps" value={ex.rep_range ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].rep_range = v))} />
                  <Text label="RIR" value={ex.rir ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].rir = v))} />
                  <Num label="Descanso (s)" value={ex.rest_sec} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].rest_sec = v))} />
                  <Text label="Tempo" value={ex.tempo ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].tempo = v))} />
                  <Num label="Peso sug. (kg)" value={ex.start_weight_hint_kg} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].start_weight_hint_kg = v))} />
                </div>
                <Text label="Progresión" value={ex.progression_rule ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].progression_rule = v))} />
                <Text label="Cue técnica" value={ex.technique_cue ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].technique_cue = v))} />
              </div>
            ))}
            <Area label="Vuelta a la calma" value={s.cooldown ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].cooldown = v))} />
          </div>
        ))}

        <Subhead text="Cardio y descarga" />
        <div className="grid grid-cols-2 gap-2">
          <Num label="Pasos diarios" value={tr.cardio.daily_steps} onChange={(v) => mutate((d) => (d.training.cardio.daily_steps = v))} />
        </div>
        <Area label="Instrucciones de deload" value={tr.deload_instructions ?? ""} onChange={(v) => mutate((d) => (d.training.deload_instructions = v))} />
      </div>

      <p className="text-xs text-zinc-500">
        El banco de comidas no se edita aquí; para cambiar un ejercicio por otro usa el "swap" de la biblioteca.
      </p>
    </div>
  );
}

function Title({ icon: Icon, text }: { icon: typeof Utensils; text: string }) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <Icon size={16} style={{ color: "var(--brand-accent)" }} />
      <h4 className="text-sm font-semibold text-zinc-200">{text}</h4>
    </div>
  );
}
function Subhead({ text, onAdd }: { text: string; onAdd?: () => void }) {
  return (
    <div className="mt-4 mb-1 flex items-center justify-between">
      <h5 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{text}</h5>
      {onAdd && <button onClick={onAdd} className="flex items-center gap-1 text-xs text-[var(--brand-accent)]"><Plus size={13} /> Añadir</button>}
    </div>
  );
}
function Row({ children, onRemove }: { children: React.ReactNode; onRemove: () => void }) {
  return (
    <div className="mt-2 flex items-start gap-2 rounded-lg p-2" style={{ background: "var(--surface-raised)" }}>
      <div className="grid flex-1 grid-cols-1 gap-2 sm:grid-cols-2">{children}</div>
      <button onClick={onRemove} className="mt-5 text-zinc-500 hover:text-red-400"><Trash2 size={14} /></button>
    </div>
  );
}
function Text({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="block">
      <span className="mb-0.5 block text-xs text-zinc-500">{label}</span>
      <input type="text" value={value ?? ""} onChange={(e) => onChange(e.target.value)} className="input w-full" />
    </label>
  );
}
function Num({ label, value, onChange }: { label: string; value: number | null | undefined; onChange: (v: number | null) => void }) {
  return (
    <label className="block">
      <span className="mb-0.5 block text-xs text-zinc-500">{label}</span>
      <input type="number" value={value ?? ""} onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))} className="input w-full" />
    </label>
  );
}
function Area({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="mt-2 block">
      <span className="mb-0.5 block text-xs text-zinc-500">{label}</span>
      <textarea value={value ?? ""} onChange={(e) => onChange(e.target.value)} rows={2} className="input w-full resize-y" />
    </label>
  );
}

```


## `frontend/src/components/ClientPlanPanel.tsx`

```tsx
import { useEffect, useState } from "react";
import { Sparkles, Download, Send, AlertTriangle, Dumbbell, Utensils, Pill, CalendarDays, Pencil } from "lucide-react";
import { api, getToken } from "../lib/api";
import { Spinner, useToast } from "./ui";
import { ClientPlanEditor } from "./ClientPlanEditor";
import type { ClientOut } from "../types";

interface PlanData {
  id: number;
  month_index: number;
  version: number;
  status: string;
  guardrail_flags: string[];
  nutrition: any;
  training: any;
  education: any;
}

/** Normaliza un plan venga de generatePlan (nutrition/...) o de listPlans (nutrition_json/...). */
function normalize(p: any): PlanData {
  return {
    id: p.id,
    month_index: p.month_index,
    version: p.version,
    status: p.status,
    guardrail_flags: p.guardrail_flags ?? [],
    nutrition: p.nutrition ?? p.nutrition_json ?? null,
    training: p.training ?? p.training_json ?? null,
    education: p.education ?? p.education_json ?? null,
  };
}

/**
 * Planificación: genera el plan mensual con IA a partir de la anamnesis, lo
 * PERSISTE (al volver a la pestaña se recarga el último plan guardado), muestra
 * TODA la info (nutrición, banco de comidas, entrenamiento, educativo) y permite
 * publicarlo y descargarlo en Word.
 */
export function ClientPlanPanel({ client }: { client: ClientOut }) {
  const toast = useToast();
  const [plan, setPlan] = useState<PlanData | null>(null);
  const [exMap, setExMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [startingPeriod, setStartingPeriod] = useState(false);
  const [editing, setEditing] = useState(false);
  const [missing, setMissing] = useState<string[] | null>(null);
  const [periods, setPeriods] = useState<{ id: number; plan_id: number | null; starts_on: string; ends_on: string; status: string }[]>([]);

  // Al montar: carga el último plan guardado + el mapa de ejercicios + los períodos.
  useEffect(() => {
    let alive = true;
    Promise.all([
      api.listPlans(client.id),
      api.listExercises({ include_archived: true }),
      api.listPeriods(client.id),
    ])
      .then(([plans, exs, pds]) => {
        if (!alive) return;
        const map: Record<number, string> = {};
        exs.forEach((e) => (map[e.id] = e.canonical_name));
        setExMap(map);
        setPeriods(pds);
        if (plans.length) setPlan(normalize(plans[0])); // [0] = versión más reciente
      })
      .catch(() => {})
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [client.id]);

  async function startPeriod() {
    if (!plan || startingPeriod) return;
    setStartingPeriod(true);
    try {
      const today = new Date().toISOString().slice(0, 10);
      await api.createPeriod(client.id, plan.id, today, 14);
      setPeriods(await api.listPeriods(client.id));
      toast.push("Seguimiento iniciado (14 días). El cliente ya puede registrar su diario.");
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push(detail?.message ?? e?.message ?? "No se pudo iniciar el período", "error");
    } finally {
      setStartingPeriod(false);
    }
  }

  async function generate() {
    if (generating) return;
    setGenerating(true);
    setMissing(null);
    try {
      const p = await api.generatePlan(client.id, 1);
      setPlan(normalize(p));
      toast.push("Planificación generada");
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      if (detail?.missing) setMissing(detail.missing);
      else toast.push(detail?.message ?? e?.message ?? "No se pudo generar el plan", "error");
    } finally {
      setGenerating(false);
    }
  }

  async function publish() {
    if (!plan || publishing) return;
    setPublishing(true);
    try {
      await api.publishPlan(plan.id);
      setPlan({ ...plan, status: "published" });
      toast.push("Plan publicado: ya es visible en el portal del cliente");
    } catch {
      toast.push("No se pudo publicar", "error");
    } finally {
      setPublishing(false);
    }
  }

  function downloadWord() {
    if (!plan) return;
    fetch(api.planDocumentUrl(plan.id), { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `plan_${client.full_name.replace(/\s+/g, "_").toLowerCase()}_mes${plan.month_index}.docx`;
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch(() => toast.push("No se pudo descargar", "error"));
  }

  if (loading) {
    return (
      <div className="card flex items-center justify-center gap-2 p-8 text-sm text-zinc-500">
        <Spinner /> Cargando planificación…
      </div>
    );
  }

  // ---------- Sin plan generado todavía ----------
  if (!plan) {
    return (
      <div className="card p-6">
        <div className="flex items-start gap-3">
          <div className="rounded-xl p-2.5" style={{ background: "rgba(110,231,183,0.12)" }}>
            <Sparkles size={20} style={{ color: "var(--brand-accent)" }} />
          </div>
          <div className="flex-1">
            <h3 className="text-base font-semibold text-zinc-100">Planificación mensual</h3>
            <p className="mt-1 text-sm text-zinc-400">
              Genera el plan de dieta y entrenamiento con IA a partir de los datos de la
              anamnesis. Podrás revisarlo, publicarlo y descargarlo.
            </p>

            {missing && (
              <div className="mt-4 rounded-lg border p-3" style={{ borderColor: "#7a5b1a", background: "rgba(247,201,110,0.08)" }}>
                <div className="flex items-center gap-2 text-sm font-medium text-amber-300">
                  <AlertTriangle size={15} /> Faltan datos en la anamnesis
                </div>
                <p className="mt-1 text-xs text-zinc-400">
                  Completa estos campos en la pestaña <b>Anamnesis</b> antes de generar:
                </p>
                <ul className="mt-2 flex flex-wrap gap-1.5">
                  {missing.map((m) => (
                    <li key={m} className="rounded-md px-2 py-0.5 text-xs" style={{ background: "rgba(247,201,110,0.15)", color: "#F7C96E" }}>
                      {m}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <button onClick={generate} disabled={generating} className="btn btn-primary mt-4">
              <Sparkles size={16} />
              {generating ? "Generando… (puede tardar 1-2 min)" : "Generar planificación"}
            </button>
            {generating && (
              <p className="mt-2 text-xs text-zinc-500">
                La IA está creando el plan (núcleo, comidas y contenido educativo). No cierres la página.
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ---------- Modo edición ----------
  if (editing) {
    return (
      <ClientPlanEditor
        plan={plan}
        exMap={exMap}
        onSaved={(p) => { setPlan(p); setEditing(false); }}
        onCancel={() => setEditing(false)}
      />
    );
  }

  // ---------- Plan generado / guardado: vista completa ----------
  const nut = plan.nutrition ?? {};
  const tr = plan.training ?? {};
  const macros = nut.macros ?? {};
  const mealBank = nut.meal_bank ?? null;
  const exName = (id: number) => exMap[id] ?? `Ejercicio #${id}`;
  const currentPeriod = periods.find((p) => p.plan_id === plan.id);

  return (
    <div className="space-y-4">
      {/* Cabecera con acciones */}
      <div className="card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-zinc-100">Planificación · Mes {plan.month_index}</h3>
              <span
                className="rounded-full px-2 py-0.5 text-xs font-medium"
                style={
                  plan.status === "published"
                    ? { background: "rgba(110,231,183,0.15)", color: "var(--brand-accent)" }
                    : { background: "rgba(255,255,255,0.08)", color: "#a1a1aa" }
                }
              >
                {plan.status === "published" ? "Publicado" : "Borrador"} · v{plan.version}
              </span>
            </div>
            <p className="mt-0.5 text-xs text-zinc-500">
              Revisa el plan. Cuando esté listo, publícalo (lo verá el cliente) y descárgalo.
            </p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setEditing(true)} className="btn btn-ghost">
              <Pencil size={15} /> Editar
            </button>
            <button onClick={downloadWord} className="btn btn-ghost">
              <Download size={15} /> Descargar Word
            </button>
            {plan.status !== "published" && (
              <button onClick={publish} disabled={publishing} className="btn btn-primary">
                <Send size={15} /> {publishing ? "Publicando…" : "Publicar"}
              </button>
            )}
          </div>
        </div>

        {/* Seguimiento: tras publicar, iniciar el período para que el cliente
            registre el diario en el portal (cierra el ciclo hacia el feedback). */}
        {plan.status === "published" && (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-lg p-3" style={{ background: "var(--surface-raised)" }}>
            {currentPeriod ? (
              <span className="flex items-center gap-2 text-xs text-zinc-400">
                <CalendarDays size={14} style={{ color: "var(--brand-accent)" }} />
                Seguimiento activo · {currentPeriod.starts_on} → {currentPeriod.ends_on}
                <span className="rounded-full px-2 py-0.5" style={{ background: "rgba(110,231,183,0.12)", color: "var(--brand-accent)" }}>
                  {currentPeriod.status === "open" ? "abierto" : currentPeriod.status === "closed" ? "cerrado" : "analizado"}
                </span>
              </span>
            ) : (
              <>
                <span className="text-xs text-zinc-500">Inicia el seguimiento para que el cliente registre su diario y, al cerrarlo, puedas generar el feedback.</span>
                <button onClick={startPeriod} disabled={startingPeriod} className="btn btn-ghost">
                  <CalendarDays size={15} /> {startingPeriod ? "Iniciando…" : "Iniciar seguimiento (14 días)"}
                </button>
              </>
            )}
          </div>
        )}
      </div>

      {/* Nutrición */}
      <div className="card p-5">
        <SectionTitle icon={Utensils} title="Nutrición" />
        <div className="grid grid-cols-4 gap-2">
          {[
            ["Calorías", `${Math.round(nut.target_kcal ?? 0)}`],
            ["Proteína", `${Math.round(macros.protein_g ?? 0)} g`],
            ["Carbohid.", `${Math.round(macros.carbs_g ?? 0)} g`],
            ["Grasas", `${Math.round(macros.fat_g ?? 0)} g`],
          ].map(([label, val]) => (
            <Stat key={label} label={label} value={val} />
          ))}
        </div>
        {nut.tdee_kcal != null && (
          <p className="mt-2 text-xs text-zinc-500">TDEE estimado: {Math.round(nut.tdee_kcal)} kcal</p>
        )}
        {nut.rationale && <p className="mt-3 text-sm text-zinc-300">{nut.rationale}</p>}
        {nut.refeed_or_break && (
          <p className="mt-2 text-xs text-zinc-400"><b className="text-zinc-300">Recarga / descanso:</b> {nut.refeed_or_break}</p>
        )}

        {Array.isArray(nut.meals) && nut.meals.length > 0 && (
          <div className="mt-4">
            <h5 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">Objetivos por comida</h5>
            <div className="space-y-1.5">
              {nut.meals.map((m: any) => (
                <div key={m.slot} className="flex items-center justify-between rounded-lg px-3 py-2 text-xs" style={{ background: "var(--surface-raised)" }}>
                  <span className="text-zinc-300">{m.time} · {m.name}</span>
                  <span className="text-zinc-500">
                    {Math.round(m.target?.kcal ?? 0)} kcal · P{Math.round(m.target?.protein_g ?? 0)} / C{Math.round(m.target?.carbs_g ?? 0)} / G{Math.round(m.target?.fat_g ?? 0)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {Array.isArray(nut.flexibility_rules) && nut.flexibility_rules.length > 0 && (
          <div className="mt-3">
            <h5 className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">Reglas de flexibilidad</h5>
            <ul className="list-disc space-y-0.5 pl-5 text-xs text-zinc-400">
              {nut.flexibility_rules.map((r: string, i: number) => <li key={i}>{r}</li>)}
            </ul>
          </div>
        )}
      </div>

      {/* Suplementación */}
      {Array.isArray(nut.supplements) && nut.supplements.length > 0 && (
        <div className="card p-5">
          <SectionTitle icon={Pill} title="Suplementación" />
          <div className="space-y-1.5">
            {nut.supplements.map((s: any, i: number) => (
              <div key={i} className="rounded-lg px-3 py-2 text-xs" style={{ background: "var(--surface-raised)" }}>
                <span className="font-medium text-zinc-200">{s.name}</span>
                <span className="text-zinc-500"> · {s.dose} · {s.timing}</span>
                {s.evidence_note && <p className="mt-0.5 text-zinc-500">{s.evidence_note}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Banco de comidas */}
      {mealBank && (
        <div className="card p-5">
          <SectionTitle icon={Utensils} title={`Banco de comidas (${mealBank.mode === "strict" ? "menú cerrado" : "equivalencias"})`} />
          {mealBank.mode === "flexible_7" && Array.isArray(mealBank.slots) ? (
            <div className="space-y-3">
              {mealBank.slots.map((slot: any) => (
                <details key={slot.slot} className="rounded-lg" style={{ background: "var(--surface-raised)" }}>
                  <summary className="cursor-pointer px-3 py-2 text-sm font-medium text-zinc-200">
                    Comida {slot.slot} · {slot.options?.length ?? 0} opciones
                  </summary>
                  <div className="space-y-2 px-3 pb-3">
                    {slot.options?.map((o: any) => <MealOption key={o.key ?? o.title} o={o} />)}
                  </div>
                </details>
              ))}
            </div>
          ) : mealBank.mode === "strict" && Array.isArray(mealBank.days) ? (
            <div className="space-y-3">
              {mealBank.days.map((d: any) => (
                <details key={d.day} className="rounded-lg" style={{ background: "var(--surface-raised)" }}>
                  <summary className="cursor-pointer px-3 py-2 text-sm font-medium capitalize text-zinc-200">{d.day}</summary>
                  <div className="space-y-2 px-3 pb-3">
                    {d.meals?.map((m: any, i: number) => <MealOption key={i} o={m.dish} prefix={`Comida ${m.slot}: `} />)}
                  </div>
                </details>
              ))}
            </div>
          ) : (
            <p className="text-xs text-zinc-500">Sin banco de comidas.</p>
          )}
        </div>
      )}

      {/* Entrenamiento */}
      <div className="card p-5">
        <SectionTitle icon={Dumbbell} title={`Entrenamiento${tr.split_name ? ` · ${tr.split_name}` : ""}`} />
        {tr.split_rationale && <p className="mb-3 text-sm text-zinc-300">{tr.split_rationale}</p>}

        {Array.isArray(tr.weekly_progression) && tr.weekly_progression.length > 0 && (
          <div className="mb-4">
            <h5 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">Progresión semanal</h5>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {tr.weekly_progression.map((w: any) => (
                <div key={w.week} className="rounded-lg p-2.5 text-xs" style={{ background: "var(--surface-raised)" }}>
                  <div className="font-semibold text-zinc-200">Sem {w.week} · {w.intent}</div>
                  <div className="text-zinc-500">Carga {w.load_pct}% · RIR {w.rir_target}</div>
                  {w.volume_note && <div className="mt-0.5 text-zinc-500">{w.volume_note}</div>}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-3">
          {(tr.sessions ?? []).map((s: any, i: number) => (
            <div key={i} className="rounded-lg p-3" style={{ background: "var(--surface-raised)" }}>
              <div className="text-sm font-medium text-zinc-200">{s.day} · {s.name}</div>
              {s.warmup && <p className="mt-1 text-xs text-zinc-500"><b>Calentamiento:</b> {s.warmup}</p>}
              <div className="mt-2 space-y-2">
                {(s.exercises ?? []).map((ex: any, j: number) => (
                  <div key={j} className="rounded-md p-2 text-xs" style={{ background: "var(--surface)" }}>
                    <div className="flex flex-wrap items-baseline justify-between gap-1">
                      <span className="font-medium text-zinc-200">{exName(ex.exercise_id)}</span>
                      <span className="text-zinc-400">
                        {ex.sets}×{ex.rep_range} · RIR {ex.rir} · descanso {ex.rest_sec}s
                        {ex.tempo ? ` · tempo ${ex.tempo}` : ""}
                        {ex.start_weight_hint_kg != null ? ` · ~${ex.start_weight_hint_kg} kg` : ""}
                      </span>
                    </div>
                    {ex.progression_rule && <p className="mt-0.5 text-zinc-500"><b>Progresión:</b> {ex.progression_rule}</p>}
                    {ex.technique_cue && <p className="text-zinc-500"><b>Técnica:</b> {ex.technique_cue}</p>}
                    {ex.biomech_cue && <p className="text-zinc-500"><b>Biomecánica:</b> {ex.biomech_cue}</p>}
                  </div>
                ))}
              </div>
              {s.cooldown && <p className="mt-2 text-xs text-zinc-500"><b>Vuelta a la calma:</b> {s.cooldown}</p>}
            </div>
          ))}
        </div>

        {tr.cardio && (
          <div className="mt-3 rounded-lg p-3 text-xs" style={{ background: "var(--surface-raised)" }}>
            <div className="flex items-center gap-1.5 font-medium text-zinc-200"><CalendarDays size={13} /> Cardio y NEAT</div>
            <p className="mt-1 text-zinc-400">Pasos diarios objetivo: {tr.cardio.daily_steps}</p>
            {(tr.cardio.sessions ?? []).map((cs: any, i: number) => (
              <p key={i} className="text-zinc-500">{cs.type?.toUpperCase()} · {cs.minutes} min × {cs.times_per_week}/sem{cs.notes ? ` · ${cs.notes}` : ""}</p>
            ))}
          </div>
        )}
        {tr.deload_instructions && (
          <p className="mt-3 text-xs text-zinc-400"><b className="text-zinc-300">Descarga (deload):</b> {tr.deload_instructions}</p>
        )}
      </div>

      <button onClick={generate} disabled={generating} className="btn btn-ghost text-xs">
        <Sparkles size={14} /> {generating ? "Regenerando…" : "Regenerar plan (nueva versión)"}
      </button>
    </div>
  );
}

function SectionTitle({ icon: Icon, title }: { icon: typeof Utensils; title: string }) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <Icon size={16} style={{ color: "var(--brand-accent)" }} />
      <h4 className="text-sm font-semibold text-zinc-200">{title}</h4>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg p-3 text-center" style={{ background: "var(--surface-raised)" }}>
      <div className="text-lg font-bold" style={{ color: "var(--brand-accent)" }}>{value}</div>
      <div className="text-xs text-zinc-500">{label}</div>
    </div>
  );
}

function MealOption({ o, prefix = "" }: { o: any; prefix?: string }) {
  if (!o) return null;
  const m = o.macros ?? {};
  return (
    <div className="rounded-md p-2 text-xs" style={{ background: "var(--surface)" }}>
      <div className="flex flex-wrap items-baseline justify-between gap-1">
        <span className="font-medium text-zinc-200">
          {prefix}{o.key ? `${o.key}. ` : ""}{o.title}
        </span>
        <span className="text-zinc-500">
          {Math.round(m.kcal ?? 0)} kcal · P{Math.round(m.protein_g ?? 0)} / C{Math.round(m.carbs_g ?? 0)} / G{Math.round(m.fat_g ?? 0)}
          {o.prep_minutes != null ? ` · ${o.prep_minutes} min` : ""}
        </span>
      </div>
      {Array.isArray(o.ingredients) && o.ingredients.length > 0 && (
        <p className="mt-0.5 text-zinc-400">
          {o.ingredients.map((ing: any) => `${ing.food} ${ing.grams}g (${ing.household})`).join(" · ")}
        </p>
      )}
      {o.prep && <p className="mt-0.5 text-zinc-500">{o.prep}</p>}
      {Array.isArray(o.tags) && o.tags.length > 0 && (
        <p className="mt-0.5 text-zinc-600">{o.tags.join(" · ")}</p>
      )}
    </div>
  );
}

```


## `frontend/src/components/ClientSummaryTab.tsx`

```tsx
import { useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ClientOut } from "../types";
import { EmptyState } from "./ui";
import { formatDate } from "../lib/format";

/**
 * Tab Resumen: KPIs del cliente y evolución de peso hacia el objetivo.
 *
 * En Fase 5 el historial de períodos/logs aún no se expone por API (llega en
 * Fase 6 con el portal y los cierres), así que la gráfica usa los anclajes
 * disponibles: peso inicial → peso actual → objetivo. La estructura queda lista
 * para alimentarse de la serie real de períodos cuando exista.
 */
export function ClientSummaryTab({ client }: { client: ClientOut }) {
  const series = useMemo(() => {
    const pts: { label: string; peso: number }[] = [];
    if (client.start_weight_kg != null) pts.push({ label: "Inicio", peso: client.start_weight_kg });
    if (client.current_weight_kg != null && client.current_weight_kg !== client.start_weight_kg)
      pts.push({ label: "Actual", peso: client.current_weight_kg });
    return pts;
  }, [client]);

  const accent = getComputedStyle(document.documentElement)
    .getPropertyValue("--brand-accent")
    .trim() || "#6EE7B7";

  return (
    <div className="space-y-5">
      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Kpi label="Peso inicial" value={client.start_weight_kg} unit="kg" />
        <Kpi label="Peso actual" value={client.current_weight_kg} unit="kg" />
        <Kpi label="Objetivo" value={client.goal_weight_kg} unit="kg" />
        <Kpi
          label="Diferencia"
          value={
            client.current_weight_kg != null && client.start_weight_kg != null
              ? Number((client.current_weight_kg - client.start_weight_kg).toFixed(1))
              : null
          }
          unit="kg"
          signed
        />
      </div>

      {/* Gráfica de peso */}
      <div className="card p-5">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-zinc-200">Evolución de peso</h3>
          {client.goal_deadline && (
            <span className="text-xs text-zinc-500">Objetivo para {formatDate(client.goal_deadline)}</span>
          )}
        </div>

        {series.length < 2 ? (
          <EmptyState
            title="Aún no hay datos de seguimiento"
            hint="La curva de peso se construirá con los cierres de período del cliente."
          />
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={series} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <defs>
                  <linearGradient id="pesoFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={accent} stopOpacity={0.25} />
                    <stop offset="100%" stopColor={accent} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="label" stroke="#6b6b76" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#6b6b76" fontSize={12} tickLine={false} axisLine={false} domain={["dataMin - 2", "dataMax + 2"]} />
                <Tooltip
                  contentStyle={{
                    background: "#1a1a24",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 12,
                    fontSize: 13,
                  }}
                  labelStyle={{ color: "#9a9aa6" }}
                />
                {client.goal_weight_kg != null && (
                  <ReferenceLine
                    y={client.goal_weight_kg}
                    stroke={accent}
                    strokeDasharray="4 4"
                    strokeOpacity={0.5}
                    label={{ value: "Objetivo", fill: "#9a9aa6", fontSize: 11, position: "right" }}
                  />
                )}
                <Area type="monotone" dataKey="peso" stroke={accent} strokeWidth={2} fill="url(#pesoFill)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Notas de salud relevantes */}
      {(client.injuries_notes || client.medical_notes || client.food_allergies?.length) && (
        <div className="card p-5">
          <h3 className="mb-3 text-sm font-semibold text-zinc-200">Notas clínicas</h3>
          <div className="space-y-2.5 text-sm">
            {client.injuries_notes && <NoteRow label="Lesiones" value={client.injuries_notes} />}
            {client.medical_notes && <NoteRow label="Patologías" value={client.medical_notes} />}
            {client.food_allergies?.length ? (
              <NoteRow label="Alergias" value={client.food_allergies.join(", ")} />
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}

function Kpi({
  label,
  value,
  unit,
  signed,
}: {
  label: string;
  value: number | null | undefined;
  unit: string;
  signed?: boolean;
}) {
  const display =
    value == null ? "—" : `${signed && value > 0 ? "+" : ""}${value} ${unit}`;
  const tone = signed && value != null ? (value < 0 ? "#6EE7B7" : value > 0 ? "#F7C96E" : undefined) : undefined;
  return (
    <div className="card p-4">
      <p className="text-xl font-semibold" style={{ color: tone ?? "#e7e7ea" }}>
        {display}
      </p>
      <p className="mt-0.5 text-xs text-zinc-500">{label}</p>
    </div>
  );
}

function NoteRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-3">
      <span className="w-20 shrink-0 text-xs uppercase tracking-wide text-zinc-600">{label}</span>
      <span className="text-zinc-300">{value}</span>
    </div>
  );
}

```


## `frontend/src/components/ui.tsx`

```tsx
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { AlertTriangle, Check, Loader2, X } from "lucide-react";
import type { ClientStatus } from "../types";
import { STATUS_LABEL, STATUS_TONE } from "../lib/format";

/* ---------------------------------------------------------- StatusBadge ---- */

export function StatusBadge({ status }: { status: ClientStatus }) {
  const tone = STATUS_TONE[status];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
      style={{ background: `${tone}1a`, color: tone }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: tone }} />
      {STATUS_LABEL[status]}
    </span>
  );
}

/* -------------------------------------------------------------- Spinner ---- */

export function Spinner({ className = "" }: { className?: string }) {
  return <Loader2 className={`animate-spin ${className}`} size={18} />;
}

export function PageLoader() {
  return (
    <div className="flex h-full min-h-[300px] items-center justify-center text-zinc-500">
      <Spinner className="text-zinc-400" />
    </div>
  );
}

/* ----------------------------------------------------------- EmptyState ---- */

export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string;
  hint: string;
  action?: ReactNode;
}) {
  // Un estado vacío es una invitación a actuar (skill): título + siguiente paso.
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed py-16 text-center"
      style={{ borderColor: "var(--line-strong)" }}>
      <p className="text-sm font-medium text-zinc-200">{title}</p>
      <p className="mt-1 max-w-xs text-sm text-zinc-500">{hint}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

/* ---------------------------------------------------------------- Toast ---- */

type Toast = { id: number; message: string; tone: "ok" | "error" };
type ToastCtx = { push: (message: string, tone?: "ok" | "error") => void };

const ToastContext = createContext<ToastCtx | null>(null);

export function useToast(): ToastCtx {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast fuera de ToastProvider");
  return ctx;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const push = useCallback((message: string, tone: "ok" | "error" = "ok") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, message, tone }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000);
  }, []);

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="animate-rise flex items-center gap-2.5 rounded-xl border px-4 py-3 text-sm shadow-xl"
            style={{
              background: "var(--surface-raised)",
              borderColor: t.tone === "error" ? "#F77E7E55" : "var(--line-strong)",
            }}
          >
            <span
              className="flex h-5 w-5 items-center justify-center rounded-full"
              style={{ background: t.tone === "error" ? "#F77E7E22" : "#6EE7B722" }}
            >
              {t.tone === "error" ? (
                <AlertTriangle size={13} color="#F77E7E" />
              ) : (
                <Check size={13} color="#6EE7B7" />
              )}
            </span>
            <span className="text-zinc-100">{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/* -------------------------------------------------------- ConfirmDialog ---- */

export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel,
  destructive,
  requireText,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  body: ReactNode;
  confirmLabel: string;
  destructive?: boolean;
  requireText?: string; // si se define, hay que teclearlo para confirmar
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const [typed, setTyped] = useState("");

  useEffect(() => {
    if (open) setTyped("");
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onCancel();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  if (!open) return null;
  const canConfirm = !requireText || typed === requireText;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onCancel}>
      <div
        className="card animate-rise w-full max-w-md p-6"
        style={{ background: "var(--surface-raised)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <h3 className="text-base font-semibold text-zinc-100">{title}</h3>
          <button onClick={onCancel} className="text-zinc-500 hover:text-zinc-300">
            <X size={18} />
          </button>
        </div>
        <div className="mt-2 text-sm leading-relaxed text-zinc-400">{body}</div>
        {requireText && (
          <input
            autoFocus
            className="input mt-4"
            placeholder={requireText}
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
          />
        )}
        <div className="mt-6 flex justify-end gap-2">
          <button className="btn btn-ghost" onClick={onCancel}>
            Cancelar
          </button>
          <button
            className="btn btn-primary"
            style={destructive ? { background: "#F77E7E" } : undefined}
            disabled={!canConfirm}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

```


## `frontend/src/hooks/useAuth.tsx`

```tsx
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api, clearToken, getToken, setToken } from "../lib/api";
import type { MeOut } from "../types";

interface AuthState {
  user: MeOut | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth fuera de AuthProvider");
  return ctx;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeOut | null>(null);
  const [loading, setLoading] = useState(true);

  // Validación inicial: si hay token, confirma que sigue vigente con /me.
  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  // Sesión caducada (lanzado por la capa de API ante un 401).
  useEffect(() => {
    const onExpired = () => setUser(null);
    window.addEventListener("auth:expired", onExpired);
    return () => window.removeEventListener("auth:expired", onExpired);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const { access_token } = await api.login(username, password);
    setToken(access_token);
    const me = await api.me();
    setUser(me);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

```


## `frontend/src/hooks/useBrand.tsx`

```tsx
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../lib/api";
import type { BrandConfigOut } from "../types";

interface BrandState {
  brand: BrandConfigOut | null;
  reload: () => void;
}

const BrandContext = createContext<BrandState>({ brand: null, reload: () => {} });

export function useBrand(): BrandState {
  return useContext(BrandContext);
}

/**
 * Aplica la marca en runtime: el acento configurable se inyecta como variable
 * CSS (--brand-accent), de modo que toda la app y el portal reflejan al
 * instante los cambios de Settings (H.1), sin recompilar.
 */
export function BrandProvider({ children }: { children: ReactNode }) {
  const [brand, setBrand] = useState<BrandConfigOut | null>(null);

  const load = () => {
    api
      .getBrand()
      .then((b) => {
        setBrand(b);
        document.documentElement.style.setProperty("--brand-accent", b.color_primary);
      })
      .catch(() => {
        /* sin marca todavía: se mantienen los defaults del CSS */
      });
  };

  useEffect(load, []);

  return (
    <BrandContext.Provider value={{ brand, reload: load }}>{children}</BrandContext.Provider>
  );
}

```


## `frontend/src/index.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  /* Marca configurable en runtime (brand_config la sobreescribe) */
  --brand-accent: #6ee7b7;

  /* Paleta de la app de coaches (H.2) — fija, técnica */
  --bg: #0a0a0f;
  --surface: #111118;
  --surface-raised: #1a1a24;
  --line: rgba(255, 255, 255, 0.06);
  --line-strong: rgba(255, 255, 255, 0.1);
  --text-dim: #9a9aa6;
  --text-faint: #6b6b76;
}

* {
  box-sizing: border-box;
}

html,
body,
#root {
  height: 100%;
}

body {
  margin: 0;
  background: var(--bg);
  color: #e7e7ea;
  font-family: Inter, system-ui, -apple-system, sans-serif;
  font-feature-settings: "cv02", "cv03", "ss01";
  -webkit-font-smoothing: antialiased;
}

::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  border: 2px solid var(--bg);
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.16);
}

:focus-visible {
  outline: 2px solid var(--brand-accent);
  outline-offset: 2px;
  border-radius: 4px;
}

@layer components {
  .card {
    @apply rounded-2xl border bg-surface;
    border-color: var(--line);
  }
  .card-hover {
    transition: border-color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
  }
  .card-hover:hover {
    border-color: var(--line-strong);
    box-shadow: 0 0 0 1px rgba(110, 231, 183, 0.06), 0 8px 30px rgba(0, 0, 0, 0.3);
  }

  .btn {
    @apply inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold;
    transition: opacity 0.15s ease, background 0.15s ease, border-color 0.15s ease;
  }
  .btn-primary {
    background: var(--brand-accent);
    color: #0a0a0f;
  }
  .btn-primary:hover {
    opacity: 0.9;
  }
  .btn-ghost {
    @apply border;
    border-color: var(--line-strong);
    color: #e7e7ea;
    background: transparent;
  }
  .btn-ghost:hover {
    background: var(--surface-raised);
  }
  .btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .input {
    @apply w-full rounded-xl border bg-transparent px-3.5 py-2.5 text-sm;
    border-color: var(--line-strong);
    color: #e7e7ea;
  }
  .input::placeholder {
    color: var(--text-faint);
  }
  .input:focus {
    border-color: var(--brand-accent);
    outline: none;
  }

  .label {
    @apply mb-1.5 block text-xs font-medium uppercase tracking-wider;
    color: var(--text-dim);
  }
}

@keyframes rise {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-rise {
  animation: rise 0.32s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.pulse-dot {
  animation: pulse-dot 2s ease-in-out infinite;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.001ms !important;
    transition-duration: 0.001ms !important;
  }
}

```


## `frontend/src/lib/api.ts`

```ts
/**
 * Capa de acceso a la API.
 *
 * Un único cliente fetch que adjunta el JWT, parsea JSON y normaliza errores.
 * Cada método mapea a un endpoint real de las Fases 2–4. Los tipos vienen de
 * types.ts (espejo de los schemas Pydantic).
 */

import type {
  BrandConfigOut,
  ChangeRequestOut,
  ClientCreate,
  ClientCreatedOut,
  ClientOut,
  ClientStatus,
  ExerciseOut,
  MeOut,
  PortalLinkOut,
  TokenOut,
} from "../types";

const TOKEN_KEY = "fitness_coach_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  opts: { raw?: boolean } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let payload: BodyInit | undefined;
  if (body instanceof FormData) {
    payload = body;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(`/api${path}`, { method, headers, body: payload });

  if (res.status === 401) {
    clearToken();
    // Señaliza a la app que debe volver al login.
    window.dispatchEvent(new CustomEvent("auth:expired"));
    throw new ApiError(401, "Sesión caducada");
  }

  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") detail = data.detail;
      else if (Array.isArray(data.detail)) detail = data.detail.map((d: any) => d.msg).join("; ");
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new ApiError(res.status, detail);
  }

  if (opts.raw) return res as unknown as T;
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  // --- auth ---
  login: (username: string, password: string) =>
    request<TokenOut>("POST", "/auth/login", { username, password }),
  me: () => request<MeOut>("GET", "/auth/me"),

  // --- clients ---
  listClients: (params: { status?: ClientStatus; q?: string } = {}) => {
    const qs = new URLSearchParams();
    if (params.status) qs.set("status", params.status);
    if (params.q) qs.set("q", params.q);
    const suffix = qs.toString() ? `?${qs}` : "";
    return request<ClientOut[]>("GET", `/clients${suffix}`);
  },
  getClient: (id: number) => request<ClientOut>("GET", `/clients/${id}`),
  createClient: (body: ClientCreate) =>
    request<ClientCreatedOut>("POST", "/clients", body),
  updateClient: (id: number, patch: Partial<ClientOut>) =>
    request<ClientOut>("PATCH", `/clients/${id}`, patch),
  portalLink: (id: number) =>
    request<PortalLinkOut>("GET", `/clients/${id}/portal-link`),
  regeneratePortalToken: (id: number) =>
    request<PortalLinkOut>("POST", `/clients/${id}/portal-token/regenerate`),
  exportClientUrl: (id: number) => `/api/clients/${id}/export`,
  listPlans: (clientId: number) =>
    request<{
      id: number; month_index: number; version: number; status: string;
      nutrition_json: any; training_json: any; education_json: any;
      guardrail_flags: string[] | null;
    }[]>("GET", `/clients/${clientId}/plans`),
  planDocumentUrl: (planId: number) => `/api/plans/${planId}/document`,
  listClientDocuments: (clientId: number) =>
    request<{ name: string; size_kb: number; uploaded_at: number }[]>(
      "GET", `/clients/${clientId}/documents`),
  uploadClientDocument: (clientId: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<{ name: string; read_ok: boolean; read_error: string | null }>(
      "POST", `/clients/${clientId}/documents`, fd);
  },
  clientDocumentUrl: (clientId: number, name: string) =>
    `/api/clients/${clientId}/documents/${encodeURIComponent(name)}`,
  listClientPhotos: (clientId: number) =>
    request<{ id: number; kind: string; period_id: number | null; taken_at: string }[]>(
      "GET", `/clients/${clientId}/photos`),
  clientPhotoUrl: (clientId: number, photoId: number) =>
    `/api/clients/${clientId}/photos/${photoId}`,
  anamnesisTemplateUrl: () => `/api/anamnesis-template`,
  generatePlan: (clientId: number, monthIndex = 1) =>
    request<{
      id: number; month_index: number; version: number; status: string;
      guardrail_flags: string[];
      nutrition: any; training: any; education: any;
    }>("POST", `/clients/${clientId}/generate-plan?month_index=${monthIndex}`),
  publishPlan: (planId: number) =>
    request<{ status: string }>("POST", `/plans/${planId}/publish`),
  updatePlan: (planId: number, patch: { nutrition_json?: any; training_json?: any; education_json?: any }) =>
    request<{ id: number; status: string; nutrition_json: any; training_json: any; education_json: any; guardrail_flags: string[] | null; month_index: number; version: number }>(
      "PATCH", `/plans/${planId}`, patch),
  readAnamnesis: (clientId: number) =>
    request<{ extracted: any; deep_analysis: string | null; message: string }>(
      "POST", `/clients/${clientId}/read-anamnesis`),

  // --- feedback (cierre → informe) ---
  createPeriod: (clientId: number, planId: number, startsOn: string, days = 14) =>
    request<{ period_id: number; period_index: number; starts_on: string; ends_on: string }>(
      "POST", `/clients/${clientId}/periods`, { plan_id: planId, starts_on: startsOn, days }),
  listPeriods: (clientId: number) =>
    request<{
      id: number; plan_id: number | null; period_index: number; starts_on: string; ends_on: string; status: string;
      closing_weight_kg: number | null; closing_rating: number | null;
      closing_hardest: string | null; closing_questions: string | null;
      closing_waist_cm: number | null; closing_hip_cm: number | null;
      closing_arm_cm: number | null; closing_thigh_cm: number | null;
      feedback_id: number | null;
    }[]>("GET", `/clients/${clientId}/periods`),
  generateFeedback: (periodId: number) =>
    request<{ feedback_id: number; period_id: number; kind: string; content: any }>(
      "POST", `/periods/${periodId}/feedback`),
  getFeedback: (docId: number) =>
    request<{ id: number; period_id: number; kind: string; content: any; sent_at: string | null }>(
      "GET", `/feedback/${docId}`),
  sendFeedback: (docId: number) =>
    request<{ sent: boolean; sent_at: string }>("POST", `/feedback/${docId}/send`),
  getPeriodMetrics: (periodId: number) =>
    request<{
      period_index: number; status: string;
      weight: { start_kg: number | null; end_kg: number | null; delta_kg: number | null; weekly_rate_kg: number | null };
      body_weight_now_kg: number | null; goal_weight_kg: number | null; distance_to_goal_kg: number | null;
      adherence: { diet_pct: number; log_pct: number; days_logged: number; period_days: number };
      strength: { name: string; e1rm_kg: number; delta_kg: number | null }[];
    }>("GET", `/periods/${periodId}/metrics`),
  feedbackDocumentUrl: (docId: number) => `/api/feedback/${docId}/document`,

  // --- brand ---
  getBrand: () => request<BrandConfigOut>("GET", "/brand"),
  updateBrand: (body: Omit<BrandConfigOut, "id" | "logo_path">) =>
    request<BrandConfigOut>("PUT", "/brand", body),
  uploadLogo: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<BrandConfigOut>("POST", "/brand/logo", fd);
  },

  // --- exercises ---
  listExercises: (params: { q?: string; pattern?: string; muscle?: string; include_archived?: boolean } = {}) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.pattern) qs.set("pattern", params.pattern);
    if (params.muscle) qs.set("muscle", params.muscle);
    if (params.include_archived) qs.set("include_archived", "true");
    const suffix = qs.toString() ? `?${qs}` : "";
    return request<ExerciseOut[]>("GET", `/exercises${suffix}`);
  },
  archiveExercise: (id: number) =>
    request<ExerciseOut>("POST", `/exercises/${id}/archive`),
  restoreExercise: (id: number) =>
    request<ExerciseOut>("POST", `/exercises/${id}/restore`),
  updateExercise: (id: number, patch: Partial<ExerciseOut>) =>
    request<ExerciseOut>("PATCH", `/exercises/${id}`, patch),
};

export type { ChangeRequestOut };

```


## `frontend/src/lib/format.ts`

```ts
/**
 * Utilidades de presentación compartidas.
 *
 * Mapas de etiquetas en castellano (todo lo de cara al usuario va en español),
 * formateadores de fecha/número y helpers de color de estado. Centralizar esto
 * evita que cada vista invente sus propias traducciones.
 */

import type { ClientStatus, DietMode, GoalType, Level, TrainingPlace } from "../types";

export const STATUS_LABEL: Record<ClientStatus, string> = {
  onboarding: "Onboarding",
  active: "Activo",
  awaiting_feedback: "Esperando cierre",
  at_risk: "En riesgo",
  review_pending: "Revisión pendiente",
  inactive: "Inactivo",
};

// Color de acento por estado (para badges y puntos). Tonos sobrios sobre fondo oscuro.
export const STATUS_TONE: Record<ClientStatus, string> = {
  onboarding: "#8B9DF7", // índigo suave: aún configurándose
  active: "#6EE7B7", // acento de marca: todo en marcha
  awaiting_feedback: "#F7C96E", // ámbar: requiere acción próxima
  at_risk: "#F77E7E", // rojo: atención
  review_pending: "#C99EF7", // violeta: en cola del coach
  inactive: "#6B6B76", // gris: dormido
};

export const GOAL_LABEL: Record<GoalType, string> = {
  fat_loss: "Pérdida de grasa",
  muscle_gain: "Ganancia muscular",
  recomp: "Recomposición",
};

export const LEVEL_LABEL: Record<Level, string> = {
  beginner: "Principiante",
  intermediate: "Intermedio",
  advanced: "Avanzado",
};

export const PLACE_LABEL: Record<TrainingPlace, string> = {
  gym: "Gimnasio",
  home: "Casa",
  outdoor: "Exterior",
};

export const DIET_LABEL: Record<DietMode, string> = {
  flexible_7: "Flexible (7 opciones)",
  strict: "Estricta",
};

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" });
}

export function relativeDays(iso: string | null | undefined): string {
  if (!iso) return "—";
  const diff = Math.round((Date.now() - new Date(iso).getTime()) / 86400000);
  if (diff === 0) return "hoy";
  if (diff === 1) return "ayer";
  if (diff < 0) return `en ${-diff} días`;
  return `hace ${diff} días`;
}

export function ageFrom(birthIso: string | null): number | null {
  if (!birthIso) return null;
  const b = new Date(birthIso);
  const now = new Date();
  let age = now.getFullYear() - b.getFullYear();
  const m = now.getMonth() - b.getMonth();
  if (m < 0 || (m === 0 && now.getDate() < b.getDate())) age--;
  return age;
}

export function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

```


## `frontend/src/main.tsx`

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { AuthProvider } from "./hooks/useAuth";
import { BrandProvider } from "./hooks/useBrand";
import { ToastProvider } from "./components/ui";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrandProvider>
      <AuthProvider>
        <ToastProvider>
          <App />
        </ToastProvider>
      </AuthProvider>
    </BrandProvider>
  </React.StrictMode>
);

```


## `frontend/src/pages/BrandPage.tsx`

```tsx
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

```


## `frontend/src/pages/ClientProfilePage.tsx`

```tsx
import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ExternalLink, BellRing } from "lucide-react";
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
import { ageFrom, DIET_LABEL, GOAL_LABEL, LEVEL_LABEL, PLACE_LABEL } from "../lib/format";

type Tab = "resumen" | "anamnesis" | "planificacion" | "feedback";

export default function ClientProfilePage() {
  const { id } = useParams();
  const clientId = Number(id);
  const toast = useToast();
  const [client, setClient] = useState<ClientOut | null>(null);
  const [tab, setTab] = useState<Tab>("resumen");
  const [confirmRegen, setConfirmRegen] = useState(false);
  const [portalUrl, setPortalUrl] = useState<string | null>(null);

  const load = useCallback(() => {
    api.getClient(clientId).then(setClient).catch(() => setClient(null));
  }, [clientId]);

  useEffect(load, [load]);

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

      {/* Notificación: el cliente cerró su período → toca generar feedback */}
      {client.status === "review_pending" && (
        <div
          className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border p-3.5"
          style={{ borderColor: "var(--brand-accent)", background: "rgba(110,231,183,0.10)" }}
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
            {(["resumen", "anamnesis", "planificacion", "feedback"] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className="relative px-4 py-2.5 text-sm font-medium capitalize transition-colors"
                style={{ color: tab === t ? "#e7e7ea" : "var(--text-faint)" }}
              >
                {t === "resumen" ? "Resumen" : t === "anamnesis" ? "Anamnesis" : t === "planificacion" ? "Planificación" : "Feedback"}
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
          {tab === "planificacion" && <ClientPlanPanel client={client} />}
          {tab === "feedback" && <ClientFeedbackTab client={client} onClientChanged={load} />}
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

```


## `frontend/src/pages/ClientsPage.tsx`

```tsx
import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Copy, Search, UserPlus } from "lucide-react";
import { api, ApiError } from "../lib/api";
import type { ClientOut, ClientStatus, PortalLinkOut } from "../types";
import { EmptyState, PageLoader, StatusBadge, useToast } from "../components/ui";
import { Avatar } from "./DashboardPage";
import { GOAL_LABEL, relativeDays, STATUS_LABEL } from "../lib/format";

const STATUS_FILTERS: (ClientStatus | "all")[] = [
  "all", "active", "at_risk", "review_pending", "awaiting_feedback", "onboarding", "inactive",
];

export default function ClientsPage() {
  const [params, setParams] = useSearchParams();
  const [clients, setClients] = useState<ClientOut[] | null>(null);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<ClientStatus | "all">("all");
  const [showNew, setShowNew] = useState(params.get("nuevo") === "1");

  const load = useCallback(() => {
    api
      .listClients({
        status: filter === "all" ? undefined : filter,
        q: q.length >= 2 ? q : undefined,
      })
      .then(setClients)
      .catch(() => setClients([]));
  }, [filter, q]);

  useEffect(() => {
    const t = setTimeout(load, 200); // debounce de la búsqueda
    return () => clearTimeout(t);
  }, [load]);

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
          {STATUS_FILTERS.map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className="rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
              style={
                filter === s
                  ? { background: "var(--brand-accent)", color: "#0a0a0f" }
                  : { background: "var(--surface)", color: "var(--text-dim)" }
              }
            >
              {s === "all" ? "Todos" : STATUS_LABEL[s]}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-5">
        {clients === null ? (
          <PageLoader />
        ) : clients.length === 0 ? (
          <EmptyState
            title="Sin clientes que mostrar"
            hint="Da de alta tu primer cliente para generarle el enlace de anamnesis."
            action={
              <button className="btn btn-primary" onClick={() => setShowNew(true)}>
                <UserPlus size={16} /> Nuevo cliente
              </button>
            }
          />
        ) : (
          <ClientsTable clients={clients} />
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

function ClientsTable({ clients }: { clients: ClientOut[] }) {
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
            <tr
              key={c.id}
              className="border-t transition-colors hover:bg-[var(--surface-raised)]"
              style={{ borderColor: "var(--line)", background: i % 2 ? "rgba(255,255,255,0.012)" : undefined }}
            >
              <td className="px-4 py-3">
                <Link to={`/clientes/${c.id}`} className="flex items-center gap-3">
                  <Avatar name={c.full_name} size={32} />
                  <div>
                    <p className="font-medium text-zinc-100">{c.full_name}</p>
                    <p className="text-xs text-zinc-500">{c.email}</p>
                  </div>
                </Link>
              </td>
              <td className="px-4 py-3 text-zinc-400">
                {c.goal_type ? GOAL_LABEL[c.goal_type] : <span className="text-zinc-600">—</span>}
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={c.status} />
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
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<PortalLinkOut | null>(null);

  async function submit() {
    if (!name || !email || busy) return;
    setBusy(true);
    try {
      const res = await api.createClient({ full_name: name, email, phone: phone || null });
      setCreated(res.links);
      onCreated();
      toast.push("Cliente creado");
    } catch (e) {
      toast.push(e instanceof ApiError ? e.message : "No se pudo crear el cliente", "error");
      setBusy(false);
    }
  }

  function copy(text: string) {
    navigator.clipboard.writeText(text);
    toast.push("Enlace copiado");
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div
        className="card animate-rise w-full max-w-md p-6"
        style={{ background: "var(--surface-raised)" }}
        onClick={(e) => e.stopPropagation()}
      >
        {!created ? (
          <>
            <h3 className="text-base font-semibold text-zinc-100">Nuevo cliente</h3>
            <p className="mt-1 text-sm text-zinc-500">
              Solo necesitas nombre y email. El cliente completará su anamnesis desde el enlace.
            </p>
            <div className="mt-5 space-y-4">
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
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button className="btn btn-ghost" onClick={onClose}>
                Cancelar
              </button>
              <button className="btn btn-primary" disabled={busy || !name || !email} onClick={submit}>
                Crear cliente
              </button>
            </div>
          </>
        ) : (
          <>
            <h3 className="text-base font-semibold text-zinc-100">Cliente creado</h3>
            <p className="mt-1 text-sm text-zinc-500">
              Envía este enlace al cliente para que complete su anamnesis y consentimiento.
            </p>
            <div className="mt-4 flex items-center gap-2 rounded-xl border p-3" style={{ borderColor: "var(--line-strong)" }}>
              <code className="flex-1 truncate text-xs text-zinc-300">{created.anamnesis_url}</code>
              <button className="btn btn-ghost px-2.5 py-1.5" onClick={() => copy(created.anamnesis_url)}>
                <Copy size={14} />
              </button>
            </div>
            <div className="mt-6 flex justify-end">
              <button className="btn btn-primary" onClick={onClose}>
                Hecho
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

```


## `frontend/src/pages/DashboardPage.tsx`

```tsx
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, ArrowUpRight, CalendarClock, ClipboardList, UserPlus } from "lucide-react";
import { api } from "../lib/api";
import type { ClientOut } from "../types";
import { PageLoader, StatusBadge } from "../components/ui";
import { initials, relativeDays } from "../lib/format";

/**
 * Dashboard = puesto de mando. El brief pide que las acciones frecuentes estén
 * a 2 clics: por eso lo primero que ve el coach son las COLAS DE ACCIÓN
 * (clientes en riesgo y revisiones pendientes), no métricas decorativas.
 */
export default function DashboardPage() {
  const [clients, setClients] = useState<ClientOut[] | null>(null);

  useEffect(() => {
    api.listClients().then(setClients).catch(() => setClients([]));
  }, []);

  const groups = useMemo(() => {
    const c = clients ?? [];
    return {
      atRisk: c.filter((x) => x.status === "at_risk"),
      reviewPending: c.filter((x) => x.status === "review_pending"),
      awaiting: c.filter((x) => x.status === "awaiting_feedback"),
      onboarding: c.filter((x) => x.status === "onboarding"),
      active: c.filter((x) => x.status === "active"),
      total: c.length,
    };
  }, [clients]);

  if (clients === null) return <PageLoader />;

  const needsAttention = [...groups.atRisk, ...groups.reviewPending];

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <header className="flex items-end justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-zinc-500">Panel</p>
          <h1 className="mt-1 text-2xl font-semibold text-zinc-100">Hoy</h1>
        </div>
        <Link to="/clientes?nuevo=1" className="btn btn-primary">
          <UserPlus size={16} /> Nuevo cliente
        </Link>
      </header>

      {/* Tira de métricas: contexto, no protagonismo */}
      <div className="mt-7 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Metric label="Clientes activos" value={groups.active.length} />
        <Metric label="En riesgo" value={groups.atRisk.length} tone="#F77E7E" />
        <Metric label="Revisión pendiente" value={groups.reviewPending.length} tone="#C99EF7" />
        <Metric label="En onboarding" value={groups.onboarding.length} tone="#8B9DF7" />
      </div>

      {/* COLA DE ACCIÓN — el corazón del dashboard */}
      <section className="mt-8">
        <div className="mb-3 flex items-center gap-2">
          <AlertTriangle size={16} className="text-zinc-400" />
          <h2 className="text-sm font-semibold text-zinc-200">Requiere tu atención</h2>
        </div>

        {needsAttention.length === 0 ? (
          <div className="card p-8 text-center text-sm text-zinc-500">
            Todo en orden. No hay clientes en riesgo ni revisiones pendientes.
          </div>
        ) : (
          <div className="space-y-2">
            {needsAttention.map((c) => (
              <Link
                key={c.id}
                to={`/clientes/${c.id}`}
                className="card card-hover flex items-center justify-between p-4"
              >
                <div className="flex items-center gap-3">
                  <Avatar name={c.full_name} />
                  <div>
                    <p className="text-sm font-medium text-zinc-100">{c.full_name}</p>
                    <p className="text-xs text-zinc-500">
                      {c.status === "at_risk"
                        ? "Adherencia baja o período sin cerrar"
                        : "Cierre listo para revisar y publicar"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={c.status} />
                  <ArrowUpRight size={16} className="text-zinc-600" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Próximos cierres + onboarding pendientes en dos columnas */}
      <div className="mt-8 grid gap-5 lg:grid-cols-2">
        <Panel title="Esperando cierre" icon={CalendarClock} clients={groups.awaiting}
          emptyHint="Ningún período pendiente de cierre." />
        <Panel title="Onboarding en curso" icon={ClipboardList} clients={groups.onboarding}
          emptyHint="Ningún cliente en onboarding." />
      </div>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <div className="card p-4">
      <p className="text-2xl font-semibold" style={{ color: tone ?? "#e7e7ea" }}>
        {value}
      </p>
      <p className="mt-0.5 text-xs text-zinc-500">{label}</p>
    </div>
  );
}

function Panel({
  title,
  icon: Icon,
  clients,
  emptyHint,
}: {
  title: string;
  icon: typeof CalendarClock;
  clients: ClientOut[];
  emptyHint: string;
}) {
  return (
    <div className="card p-5">
      <div className="mb-3 flex items-center gap-2">
        <Icon size={15} className="text-zinc-400" />
        <h3 className="text-sm font-semibold text-zinc-200">{title}</h3>
        <span className="ml-auto text-xs text-zinc-600">{clients.length}</span>
      </div>
      {clients.length === 0 ? (
        <p className="py-4 text-sm text-zinc-600">{emptyHint}</p>
      ) : (
        <ul className="space-y-1">
          {clients.slice(0, 6).map((c) => (
            <li key={c.id}>
              <Link
                to={`/clientes/${c.id}`}
                className="flex items-center justify-between rounded-lg px-2 py-2 hover:bg-[var(--surface-raised)]"
              >
                <span className="flex items-center gap-2.5">
                  <Avatar name={c.full_name} size={28} />
                  <span className="text-sm text-zinc-200">{c.full_name}</span>
                </span>
                <span className="text-xs text-zinc-600">{relativeDays(c.updated_at)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function Avatar({ name, size = 34 }: { name: string; size?: number }) {
  return (
    <span
      className="flex shrink-0 items-center justify-center rounded-full text-xs font-semibold"
      style={{
        width: size,
        height: size,
        background: "var(--surface-raised)",
        color: "var(--brand-accent)",
        border: "1px solid var(--line-strong)",
      }}
    >
      {initials(name)}
    </span>
  );
}

```


## `frontend/src/pages/LoginPage.tsx`

```tsx
import { useState } from "react";
import { Dumbbell } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { useBrand } from "../hooks/useBrand";
import { Spinner } from "../components/ui";
import { ApiError } from "../lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const { brand } = useBrand();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!username || !password || busy) return;
    setBusy(true);
    setError("");
    try {
      await login(username, password);
    } catch (e) {
      // El error no se disculpa y es concreto (skill): credenciales o caída.
      setError(
        e instanceof ApiError && e.status === 401
          ? "Usuario o contraseña incorrectos."
          : "No se pudo conectar. Inténtalo de nuevo.",
      );
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      {/* Atmósfera: un halo tenue del color de marca, sin estridencias */}
      <div
        className="pointer-events-none fixed inset-0"
        style={{
          background:
            "radial-gradient(60% 50% at 50% 0%, rgba(110,231,183,0.06), transparent 70%)",
        }}
      />
      <div className="animate-rise card relative w-full max-w-sm p-8">
        <div
          className="mb-6 flex h-11 w-11 items-center justify-center rounded-xl"
          style={{ background: "var(--brand-accent)" }}
        >
          <Dumbbell size={22} color="#0a0a0f" />
        </div>
        <h1 className="text-xl font-semibold text-zinc-100">
          {brand?.name ?? "Asesorías Fitness"}
        </h1>
        <p className="mt-1 text-sm text-zinc-500">Panel del coach</p>

        <div className="mt-7 space-y-4">
          <div>
            <label className="label">Usuario</label>
            <input
              className="input"
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
          </div>
          <div>
            <label className="label">Contraseña</label>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
          </div>

          {error && (
            <p className="rounded-lg px-3 py-2 text-sm" style={{ background: "#F77E7E18", color: "#F7A0A0" }}>
              {error}
            </p>
          )}

          <button className="btn btn-primary w-full" disabled={busy} onClick={submit}>
            {busy ? <Spinner /> : "Entrar"}
          </button>
        </div>
      </div>
    </div>
  );
}

```


## `frontend/src/portal/PortalApp.tsx`

```tsx
import { useCallback, useEffect, useMemo, useState } from "react";
import { CalendarCheck, ClipboardList, Dumbbell, Home, LineChart, NotebookPen } from "lucide-react";
import { portalApi, PortalError } from "./portalApi";
import type { PortalState } from "../types";
import { PortalToday } from "./PortalToday";
import { PortalPlan } from "./PortalPlan";
import { PortalWorkout } from "./PortalWorkout";
import { PortalDiary } from "./PortalDiary";
import { PortalClose } from "./PortalClose";
import { PortalFeedback } from "./PortalFeedback";
import { PortalToastProvider } from "./PortalToast";

type Tab = "hoy" | "plan" | "entreno" | "diario" | "cierre" | "feedback";

/**
 * Portal del cliente: mobile-first, sin login. El token sale de la URL
 * (/p/:token). Aplica la marca como variables CSS sobre un contenedor propio,
 * de modo que el portal puede ser oscuro o claro según brand.portal_theme sin
 * afectar al resto.
 */
export default function PortalApp({ token }: { token: string }) {
  const apiClient = useMemo(() => portalApi(token), [token]);
  const [state, setState] = useState<PortalState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("hoy");

  const reload = useCallback(() => {
    apiClient
      .state()
      .then((s) => {
        setState(s);
        applyBrand(s);
      })
      .catch((e) => setError(e instanceof PortalError ? e.message : "No se pudo cargar tu portal"));
  }, [apiClient]);

  useEffect(reload, [reload]);

  if (error) {
    return (
      <Centered>
        <p className="text-lg font-semibold">Enlace no válido</p>
        <p className="mt-1 text-sm opacity-70">
          Este enlace no funciona o ha caducado. Pide a tu coach uno nuevo.
        </p>
      </Centered>
    );
  }

  if (!state) {
    return (
      <Centered>
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-current border-t-transparent opacity-50" />
      </Centered>
    );
  }

  const light = state.brand.portal_theme === "light";
  const canClose = state.period?.can_close ?? false;

  const TABS: { id: Tab; label: string; icon: typeof Home; show: boolean }[] = [
    { id: "hoy", label: "Hoy", icon: Home, show: true },
    { id: "plan", label: "Plan", icon: ClipboardList, show: state.has_plan },
    { id: "entreno", label: "Entreno", icon: Dumbbell, show: !!state.period },
    { id: "diario", label: "Diario", icon: NotebookPen, show: !!state.period },
    { id: "cierre", label: "Cierre", icon: CalendarCheck, show: canClose },
    { id: "feedback", label: "Progreso", icon: LineChart, show: true },
  ];
  const visibleTabs = TABS.filter((t) => t.show);

  return (
    <PortalToastProvider light={light}>
      <div
        className="portal-root mx-auto flex min-h-screen max-w-md flex-col"
        data-theme={light ? "light" : "dark"}
        style={{
          background: light ? "#fafaf9" : state.brand.color_bg,
          color: light ? "#1a1a24" : "#e7e7ea",
        }}
      >
        {/* Cabecera con marca */}
        <header className="flex items-center justify-between px-5 pb-2 pt-6">
          <div>
            <p className="text-xs uppercase tracking-widest opacity-50">{state.brand.name}</p>
            <h1 className="text-xl font-semibold">Hola, {state.first_name}</h1>
          </div>
          {state.period && (
            <div className="text-right">
              <p className="text-2xl font-bold" style={{ color: state.brand.color_primary }}>
                {state.period.days_left}
              </p>
              <p className="text-[11px] opacity-50">días restantes</p>
            </div>
          )}
        </header>

        <main className="flex-1 px-5 pb-28 pt-2">
          {tab === "hoy" && <PortalToday api={apiClient} brand={state.brand} onGoDiary={() => setTab("diario")} onGoWorkout={() => setTab("entreno")} onGoClose={() => setTab("cierre")} canClose={canClose} />}
          {tab === "plan" && <PortalPlan api={apiClient} brand={state.brand} />}
          {tab === "entreno" && <PortalWorkout api={apiClient} brand={state.brand} />}
          {tab === "diario" && <PortalDiary api={apiClient} brand={state.brand} />}
          {tab === "cierre" && <PortalClose api={apiClient} brand={state.brand} onClosed={reload} />}
          {tab === "feedback" && <PortalFeedback api={apiClient} brand={state.brand} />}
        </main>

        {/* Navegación inferior mobile-first */}
        <nav
          className="fixed inset-x-0 bottom-0 z-40 mx-auto flex max-w-md justify-around border-t px-2 py-2"
          style={{
            background: light ? "rgba(255,255,255,0.92)" : "rgba(17,17,24,0.92)",
            backdropFilter: "blur(12px)",
            borderColor: light ? "rgba(0,0,0,0.07)" : "rgba(255,255,255,0.07)",
          }}
        >
          {visibleTabs.map(({ id, label, icon: Icon }) => {
            const active = tab === id;
            return (
              <button
                key={id}
                onClick={() => setTab(id)}
                className="flex flex-1 flex-col items-center gap-0.5 rounded-xl py-1.5 transition-colors"
                style={{ color: active ? state.brand.color_primary : light ? "#9a9aa6" : "#6b6b76" }}
              >
                <Icon size={20} />
                <span className="text-[10px] font-medium">{label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </PortalToastProvider>
  );
}

function applyBrand(s: PortalState) {
  document.documentElement.style.setProperty("--brand-accent", s.brand.color_primary);
  document.title = `${s.brand.name} · Mi portal`;
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center px-8 text-center"
      style={{ background: "#0a0a0f", color: "#e7e7ea" }}>
      {children}
    </div>
  );
}

```


## `frontend/src/portal/PortalClose.tsx`

```tsx
import { useRef, useState } from "react";
import { Camera, Check } from "lucide-react";
import type { PortalBrand } from "../types";
import { usePortalToast } from "./PortalToast";
import type { portalApi } from "./portalApi";

type Api = ReturnType<typeof portalApi>;

/**
 * Cierre del período (desde día 14). Recoge peso final, perímetros opcionales
 * (con mini-guía de cómo medirse), hasta 4 fotos, valoración, qué costó más y
 * dudas. El submit dispara el pipeline de feedback (Fase 7) en el backend.
 */
export function PortalClose({ api, brand, onClosed }: { api: Api; brand: PortalBrand; onClosed: () => void }) {
  const toast = usePortalToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [weight, setWeight] = useState<string>("");
  const [rating, setRating] = useState(0);
  const [waist, setWaist] = useState("");
  const [hip, setHip] = useState("");
  const [arm, setArm] = useState("");
  const [thigh, setThigh] = useState("");
  const [hardest, setHardest] = useState("");
  const [questions, setQuestions] = useState("");
  const [photos, setPhotos] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const canSubmit = Number(weight) > 30 && rating > 0 && !busy;

  async function submit() {
    if (!canSubmit) return;
    setBusy(true);
    try {
      if (photos.length > 0) {
        await api.closePhotos(photos.slice(0, 4), "front");
      }
      await api.close({
        closing_weight_kg: Number(weight),
        closing_rating: rating,
        closing_hardest: hardest || null,
        closing_questions: questions || null,
        closing_waist_cm: waist ? Number(waist) : null,
        closing_hip_cm: hip ? Number(hip) : null,
        closing_arm_cm: arm ? Number(arm) : null,
        closing_thigh_cm: thigh ? Number(thigh) : null,
      });
      setDone(true);
      toast.push("Período cerrado");
      setTimeout(onClosed, 1500);
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo cerrar");
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="flex flex-col items-center py-20 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full" style={{ background: `${brand.color_primary}2a` }}>
          <Check size={32} style={{ color: brand.color_primary }} />
        </div>
        <p className="mt-4 text-lg font-semibold">¡Período cerrado!</p>
        <p className="mt-1 max-w-xs text-sm opacity-60">
          Tu coach revisará tus datos y te enviará tu informe con el plan actualizado.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold">Cerrar período</h2>
        <p className="mt-1 text-sm opacity-60">Estos datos preparan tu próximo plan.</p>
      </div>

      <Field label="Peso final (kg)" required>
        <input
          type="number" step={0.1} inputMode="decimal"
          className="w-full rounded-xl border bg-transparent p-3 text-lg font-semibold"
          style={{ borderColor: "rgba(128,128,128,0.2)" }}
          value={weight} onChange={(e) => setWeight(e.target.value)} placeholder="—"
        />
      </Field>

      <Field label="¿Cómo valoras el período?" required>
        <div className="flex justify-between gap-1.5">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              onClick={() => setRating(n)}
              className="flex-1 rounded-xl border py-3 text-xl"
              style={rating >= n ? { borderColor: brand.color_primary, background: `${brand.color_primary}1f` } : { borderColor: "rgba(128,128,128,0.2)" }}
            >
              {"⭐"}
            </button>
          ))}
        </div>
      </Field>

      <Field label="Perímetros (opcional)">
        <p className="mb-2 text-xs opacity-50">
          Mídete relajado, sin apretar la cinta, a primera hora. Cintura a la altura del ombligo.
        </p>
        <div className="grid grid-cols-2 gap-3">
          <Perimeter label="Cintura" value={waist} onChange={setWaist} />
          <Perimeter label="Cadera" value={hip} onChange={setHip} />
          <Perimeter label="Brazo" value={arm} onChange={setArm} />
          <Perimeter label="Muslo" value={thigh} onChange={setThigh} />
        </div>
      </Field>

      <Field label="Fotos de progreso (hasta 4)">
        <button
          onClick={() => fileRef.current?.click()}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed py-5 text-sm opacity-70"
          style={{ borderColor: "rgba(128,128,128,0.3)" }}
        >
          <Camera size={18} /> {photos.length ? `${photos.length} foto(s) seleccionada(s)` : "Añadir fotos"}
        </button>
        <input
          ref={fileRef} type="file" accept="image/*" multiple hidden
          onChange={(e) => setPhotos(Array.from(e.target.files ?? []).slice(0, 4))}
        />
      </Field>

      <Field label="¿Qué te costó más?">
        <textarea className="min-h-[64px] w-full rounded-xl border bg-transparent p-3 text-sm" style={{ borderColor: "rgba(128,128,128,0.2)" }}
          value={hardest} onChange={(e) => setHardest(e.target.value)} placeholder="Lo que se te resistió…" />
      </Field>

      <Field label="Dudas para tu coach">
        <textarea className="min-h-[64px] w-full rounded-xl border bg-transparent p-3 text-sm" style={{ borderColor: "rgba(128,128,128,0.2)" }}
          value={questions} onChange={(e) => setQuestions(e.target.value)} placeholder="Cualquier pregunta…" />
      </Field>

      <button
        onClick={submit}
        disabled={!canSubmit}
        className="w-full rounded-2xl py-4 font-semibold"
        style={{ background: brand.color_primary, color: "#0a0a0f", opacity: canSubmit ? 1 : 0.5 }}
      >
        {busy ? "Enviando…" : "Cerrar y enviar a mi coach"}
      </button>
    </div>
  );
}

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-2 text-sm font-medium opacity-80">
        {label} {required && <span style={{ color: "#F77E7E" }}>*</span>}
      </p>
      {children}
    </div>
  );
}

function Perimeter({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="rounded-xl border p-3" style={{ borderColor: "rgba(128,128,128,0.2)" }}>
      <p className="text-xs opacity-50">{label} (cm)</p>
      <input
        type="number" step={0.5} inputMode="decimal"
        className="mt-1 w-full bg-transparent text-lg font-semibold outline-none"
        value={value} onChange={(e) => onChange(e.target.value)} placeholder="—"
      />
    </div>
  );
}

```


## `frontend/src/portal/PortalDiary.tsx`

```tsx
import { useEffect, useRef, useState } from "react";
import type { DietAdherence, PortalBrand } from "../types";
import { usePortalToast } from "./PortalToast";
import { Loading } from "./PortalToday";
import type { portalApi } from "./portalApi";

type Api = ReturnType<typeof portalApi>;

const ADHERENCE: { value: DietAdherence; label: string; emoji: string }[] = [
  { value: "yes", label: "Sí", emoji: "✅" },
  { value: "partial", label: "Parcial", emoji: "🟡" },
  { value: "no", label: "No", emoji: "❌" },
];
const SCALE_EMOJI = ["😞", "😕", "😐", "🙂", "😄"];

interface DiaryForm {
  weight_kg: number | null;
  sleep_hours: number | null;
  diet_adherence: DietAdherence | null;
  energy_1_5: number | null;
  mood_1_5: number | null;
  fatigue_1_5: number | null;
  free_notes: string;
}

const EMPTY: DiaryForm = {
  weight_kg: null, sleep_hours: null, diet_adherence: null,
  energy_1_5: null, mood_1_5: null, fatigue_1_5: null, free_notes: "",
};

/**
 * Diario con autosave. El cliente solo introduce lo suyo (peso en ayunas,
 * sueño, adherencia y cómo se siente); los ejercicios del día ya van en HOY.
 * Cada cambio se guarda con debounce para no perder nada (G.4: autosave).
 */
export function PortalDiary({ api, brand }: { api: Api; brand: PortalBrand }) {
  const toast = usePortalToast();
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState<DiaryForm | null>(null);
  const saveTimer = useRef<number | null>(null);

  useEffect(() => {
    api.getDiary(today).then((d) => {
      if (d.exists) {
        setForm({
          weight_kg: d.weight_kg, sleep_hours: d.sleep_hours,
          diet_adherence: d.diet_adherence, energy_1_5: d.energy_1_5,
          mood_1_5: d.mood_1_5, fatigue_1_5: d.fatigue_1_5,
          free_notes: d.free_notes ?? "",
        });
      } else {
        setForm({ ...EMPTY });
      }
    });
  }, [api, today]);

  function update(patch: Partial<DiaryForm>) {
    setForm((f) => {
      const next = { ...(f as DiaryForm), ...patch };
      scheduleSave(next);
      return next;
    });
  }

  function scheduleSave(next: DiaryForm) {
    if (saveTimer.current) window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(() => {
      // Solo campos del diario: NO mandamos workout_sets para no borrar las
      // series registradas en la pestaña "Entreno" (upsert parcial en backend).
      api
        .saveDiary({ log_date: today, ...next })
        .then(() => toast.push("Guardado"))
        .catch(() => {});
    }, 800);
  }

  if (!form) return <Loading />;

  return (
    <div className="space-y-5">
      <h2 className="text-lg font-semibold">Mi día</h2>

      <div className="grid grid-cols-2 gap-3">
        <NumberCard label="Peso en ayunas" unit="kg" value={form.weight_kg} step={0.1}
          onChange={(v) => update({ weight_kg: v })} accent={brand.color_primary} />
        <NumberCard label="Horas de sueño" unit="h" value={form.sleep_hours} step={0.5}
          onChange={(v) => update({ sleep_hours: v })} accent={brand.color_primary} />
      </div>

      <Field label="¿Seguiste la dieta?">
        <div className="flex gap-2">
          {ADHERENCE.map((a) => (
            <button
              key={a.value}
              onClick={() => update({ diet_adherence: a.value })}
              className="flex flex-1 flex-col items-center gap-1 rounded-xl border py-3 text-sm"
              style={
                form.diet_adherence === a.value
                  ? { borderColor: brand.color_primary, background: `${brand.color_primary}1f` }
                  : { borderColor: "rgba(128,128,128,0.2)" }
              }
            >
              <span className="text-lg">{a.emoji}</span>
              {a.label}
            </button>
          ))}
        </div>
      </Field>

      <ScaleField label="Energía" value={form.energy_1_5} onChange={(v) => update({ energy_1_5: v })} accent={brand.color_primary} />
      <ScaleField label="Ánimo" value={form.mood_1_5} onChange={(v) => update({ mood_1_5: v })} accent={brand.color_primary} />
      <ScaleField label="Fatiga" value={form.fatigue_1_5} onChange={(v) => update({ fatigue_1_5: v })} accent={brand.color_primary} invert />

      <Field label="Notas (opcional)">
        <textarea
          className="min-h-[72px] w-full rounded-xl border bg-transparent p-3 text-sm"
          style={{ borderColor: "rgba(128,128,128,0.2)" }}
          placeholder="Cómo te has sentido, incidencias…"
          value={form.free_notes}
          onChange={(e) => update({ free_notes: e.target.value })}
        />
      </Field>

      <p className="pb-2 text-center text-xs opacity-40">Se guarda automáticamente</p>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-2 text-sm font-medium opacity-80">{label}</p>
      {children}
    </div>
  );
}

function NumberCard({
  label,
  unit,
  value,
  step,
  onChange,
  accent,
}: {
  label: string;
  unit: string;
  value: number | null;
  step: number;
  onChange: (v: number | null) => void;
  accent: string;
}) {
  return (
    <div className="rounded-2xl border p-4" style={{ borderColor: "rgba(128,128,128,0.2)" }}>
      <p className="text-xs opacity-50">{label}</p>
      <div className="mt-1 flex items-baseline gap-1">
        <input
          type="number"
          step={step}
          inputMode="decimal"
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
          placeholder="—"
          className="w-full bg-transparent text-2xl font-semibold outline-none"
          style={{ caretColor: accent }}
        />
        <span className="text-sm opacity-50">{unit}</span>
      </div>
    </div>
  );
}

function ScaleField({
  label,
  value,
  onChange,
  accent,
  invert,
}: {
  label: string;
  value: number | null;
  onChange: (v: number) => void;
  accent: string;
  invert?: boolean;
}) {
  return (
    <Field label={label}>
      <div className="flex justify-between gap-1.5">
        {[1, 2, 3, 4, 5].map((n) => {
          const emoji = invert ? SCALE_EMOJI[5 - n] : SCALE_EMOJI[n - 1];
          const active = value === n;
          return (
            <button
              key={n}
              onClick={() => onChange(n)}
              className="flex flex-1 items-center justify-center rounded-xl border py-2.5 text-xl transition-transform"
              style={
                active
                  ? { borderColor: accent, background: `${accent}1f`, transform: "scale(1.05)" }
                  : { borderColor: "rgba(128,128,128,0.2)" }
              }
            >
              {emoji}
            </button>
          );
        })}
      </div>
    </Field>
  );
}

```


## `frontend/src/portal/PortalFeedback.tsx`

```tsx
import { useEffect, useState } from "react";
import { LineChart, TrendingDown, Target, Sparkles } from "lucide-react";
import type { FeedbackDocOut, PortalBrand } from "../types";
import { Empty, Loading } from "./PortalToday";
import type { portalApi } from "./portalApi";

type Api = ReturnType<typeof portalApi>;

/**
 * Tu progreso: los informes que el coach ha ENVIADO. Muestra lo relevante para
 * el cliente — cambio de peso, adherencia, análisis, cambios del plan y objetivos.
 */
export function PortalFeedback({ api, brand }: { api: Api; brand: PortalBrand }) {
  const [docs, setDocs] = useState<FeedbackDocOut[] | null>(null);

  useEffect(() => {
    api.feedback().then(setDocs).catch(() => setDocs([]));
  }, [api]);

  if (docs === null) return <Loading />;
  if (docs.length === 0) {
    return (
      <Empty
        icon={LineChart}
        title="Aún no hay informes"
        hint="Cuando tu coach te envíe tu primer informe, aquí verás tu progreso: peso, adherencia y tus próximos objetivos."
      />
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Tu progreso</h2>
      {docs.map((d) => {
        const c = (d.content_json ?? {}) as any;
        const w = c.metrics?.weight ?? {};
        const adh = c.metrics?.adherence ?? {};
        const dietPct = adh.diet_adherence_ratio != null ? Math.round(adh.diet_adherence_ratio * 100) : null;
        return (
          <div key={d.id} className="space-y-3 rounded-2xl border p-4" style={cardStyle}>
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold">
                {d.kind === "monthly" ? "Informe mensual" : "Informe quincenal"}
              </p>
              <span className="text-xs opacity-50">
                {d.sent_at ? new Date(d.sent_at).toLocaleDateString("es-ES", { day: "numeric", month: "long" }) : ""}
              </span>
            </div>

            {/* Cifras clave */}
            <div className="grid grid-cols-2 gap-2">
              <Mini icon={TrendingDown} label="Cambio de peso" value={w.delta_kg != null ? `${w.delta_kg > 0 ? "+" : ""}${w.delta_kg} kg` : "—"} accent={brand.color_primary} />
              <Mini icon={Sparkles} label="Adherencia dieta" value={dietPct != null ? `${dietPct}%` : "—"} accent={brand.color_primary} />
            </div>

            {c.natural_analysis && <p className="text-sm opacity-90">{c.natural_analysis}</p>}

            {Array.isArray(c.changes_bullets) && c.changes_bullets.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide opacity-50">Cambios en tu plan</p>
                <ul className="list-disc space-y-0.5 pl-5 text-sm opacity-90">
                  {c.changes_bullets.map((b: string, i: number) => <li key={i}>{b}</li>)}
                </ul>
              </div>
            )}

            {c.answers && (
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide opacity-50">Respuesta a tus dudas</p>
                <p className="text-sm opacity-90">{c.answers}</p>
              </div>
            )}

            {Array.isArray(c.next_objectives) && c.next_objectives.length > 0 && (
              <div>
                <p className="mb-1 flex items-center gap-1 text-xs font-semibold uppercase tracking-wide opacity-50">
                  <Target size={12} /> Tus objetivos
                </p>
                <ul className="list-disc space-y-0.5 pl-5 text-sm opacity-90">
                  {c.next_objectives.map((o: string, i: number) => <li key={i}>{o}</li>)}
                </ul>
              </div>
            )}

            {c.closing_message && (
              <p className="text-sm italic" style={{ color: brand.color_primary }}>{c.closing_message}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}

function Mini({ icon: Icon, label, value, accent }: { icon: typeof Target; label: string; value: string; accent: string }) {
  return (
    <div className="rounded-xl border p-3" style={{ borderColor: "rgba(128,128,128,0.18)" }}>
      <div className="flex items-center gap-1.5 text-xs opacity-50">
        <Icon size={13} style={{ color: accent }} /> {label}
      </div>
      <div className="mt-1 text-lg font-bold" style={{ color: accent }}>{value}</div>
    </div>
  );
}

const cardStyle = {
  background: "var(--portal-card, rgba(255,255,255,0.03))",
  borderColor: "rgba(128,128,128,0.18)",
} as const;

```


## `frontend/src/portal/PortalPlan.tsx`

```tsx
import { useEffect, useState } from "react";
import { ChevronDown, GraduationCap, Salad, Dumbbell } from "lucide-react";
import type { PortalBrand, PortalPlanOut } from "../types";
import { Empty, Loading } from "./PortalToday";
import type { portalApi } from "./portalApi";

type Api = ReturnType<typeof portalApi>;

/** Plan completo navegable por secciones colapsables (G.4). */
export function PortalPlan({ api, brand }: { api: Api; brand: PortalBrand }) {
  const [plan, setPlan] = useState<PortalPlanOut | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    api.plan().then(setPlan).catch(() => setMissing(true));
  }, [api]);

  if (missing) return <Empty icon={Salad} title="Sin plan todavía" hint="Tu coach aún no ha publicado tu plan." />;
  if (!plan) return <Loading />;

  const nut = plan.nutrition;
  const tr = plan.training;
  const edu = plan.education;

  return (
    <div className="space-y-3">
      {nut && (
        <Section icon={Salad} title="Nutrición" accent={brand.color_primary} defaultOpen>
          <div className="grid grid-cols-2 gap-2">
            <Stat label="Calorías" value={`${Math.round(nut.target_kcal)} kcal`} />
            <Stat label="Proteína" value={`${Math.round(nut.macros.protein_g)} g`} />
            <Stat label="Carbohidratos" value={`${Math.round(nut.macros.carbs_g)} g`} />
            <Stat label="Grasas" value={`${Math.round(nut.macros.fat_g)} g`} />
          </div>
          {nut.rationale && <p className="mt-3 text-xs opacity-60">{nut.rationale}</p>}
          {Array.isArray(nut.supplements) && nut.supplements.length > 0 && (
            <div className="mt-3">
              <p className="mb-1 text-xs font-semibold opacity-70">Suplementación</p>
              <ul className="space-y-1 text-xs opacity-70">
                {nut.supplements.map((s: any, i: number) => (
                  <li key={i}>• {s.name} — {s.dose} ({s.timing})</li>
                ))}
              </ul>
            </div>
          )}
        </Section>
      )}

      {tr && (
        <Section icon={Dumbbell} title="Entrenamiento" accent={brand.color_primary}>
          <p className="text-sm font-medium">{tr.split_name}</p>
          <p className="mt-1 text-xs opacity-60">{tr.split_rationale}</p>
          <div className="mt-3 space-y-3">
            {tr.sessions.map((s: any, i: number) => (
              <div key={i} className="rounded-xl border p-3" style={{ borderColor: "rgba(128,128,128,0.18)" }}>
                <p className="text-sm font-semibold">{s.day} · {s.name}</p>
                <ul className="mt-2 space-y-1 text-xs opacity-70">
                  {s.exercises.map((e: any, j: number) => (
                    <li key={j}>• {e.sets}×{e.rep_range} — ej. #{e.exercise_id} (RIR {e.rir})</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Section>
      )}

      {edu && Array.isArray(edu.pills) && (
        <Section icon={GraduationCap} title="Aprende" accent={brand.color_primary}>
          <div className="space-y-3">
            {edu.pills.map((p: any, i: number) => (
              <div key={i}>
                <p className="text-sm font-medium">{p.topic}</p>
                <p className="mt-0.5 text-xs opacity-65">{p.for_client}</p>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}

function Section({
  icon: Icon,
  title,
  accent,
  defaultOpen,
  children,
}: {
  icon: typeof Salad;
  title: string;
  accent: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(!!defaultOpen);
  return (
    <div className="rounded-2xl border" style={{ borderColor: "rgba(128,128,128,0.18)" }}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-4 py-3.5"
      >
        <span className="flex items-center gap-2 text-sm font-semibold">
          <Icon size={16} style={{ color: accent }} /> {title}
        </span>
        <ChevronDown size={18} className="opacity-50 transition-transform" style={{ transform: open ? "rotate(180deg)" : "none" }} />
      </button>
      {open && <div className="px-4 pb-4">{children}</div>}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border p-3" style={{ borderColor: "rgba(128,128,128,0.18)" }}>
      <p className="text-base font-semibold">{value}</p>
      <p className="text-xs opacity-50">{label}</p>
    </div>
  );
}

```


## `frontend/src/portal/PortalToast.tsx`

```tsx
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type Toast = { id: number; message: string };
const Ctx = createContext<{ push: (m: string) => void }>({ push: () => {} });

export function usePortalToast() {
  return useContext(Ctx);
}

export function PortalToastProvider({ children, light }: { children: ReactNode; light: boolean }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((message: string) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, message }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 2800);
  }, []);

  return (
    <Ctx.Provider value={{ push }}>
      {children}
      <div className="fixed bottom-24 left-1/2 z-50 flex -translate-x-1/2 flex-col items-center gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="rounded-full px-4 py-2 text-sm font-medium shadow-lg"
            style={{
              background: light ? "#1a1a24" : "#fafaf9",
              color: light ? "#fafaf9" : "#1a1a24",
            }}
          >
            {t.message}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

```


## `frontend/src/portal/PortalToday.tsx`

```tsx
import { useEffect, useState } from "react";
import { Check, ChevronRight, Clock, Dumbbell, MessageCircle, NotebookPen, PlayCircle, Scale, UtensilsCrossed } from "lucide-react";
import type { OptionKey, PortalBrand, TodayMealSlot, TodayView } from "../types";
import { usePortalToast } from "./PortalToast";
import type { portalApi } from "./portalApi";

type Api = ReturnType<typeof portalApi>;

/**
 * Vista HOY: la pantalla estrella. Medidor del período, checklist del día (peso,
 * entreno, dieta, diario), qué comer y qué entrenar. Legible en <30 s.
 */
export function PortalToday({
  api,
  brand,
  onGoDiary,
  onGoWorkout,
  onGoClose,
  canClose,
}: {
  api: Api;
  brand: PortalBrand;
  onGoDiary: () => void;
  onGoWorkout: () => void;
  onGoClose: () => void;
  canClose: boolean;
}) {
  const toast = usePortalToast();
  const [data, setData] = useState<TodayView | null>(null);
  const [chosen, setChosen] = useState<Record<string, string>>({});
  const [diary, setDiary] = useState<any>(null);
  const [askOpen, setAskOpen] = useState(false);

  useEffect(() => {
    api.today().then((d) => {
      setData(d);
      const initial: Record<string, string> = {};
      d.meals.forEach((m) => m.chosen_key && (initial[String(m.slot)] = m.chosen_key));
      setChosen(initial);
      api.getDiary(d.date).then(setDiary).catch(() => setDiary({}));
    });
  }, [api]);

  if (!data) return <Loading />;

  if (!data.period && data.meals.length === 0) {
    return (
      <Empty
        icon={UtensilsCrossed}
        title="Aún no tienes un plan activo"
        hint="Cuando tu coach publique tu plan, aquí verás qué comer y entrenar cada día."
      />
    );
  }

  function pick(slot: number, key: string) {
    const next = { ...chosen, [String(slot)]: key };
    setChosen(next);
    // Persistimos solo la elección de comida (upsert parcial: no toca el resto)
    api
      .saveDiary({ log_date: data!.date, chosen_options_json: next as Record<string, OptionKey> })
      .then(() => toast.push("Opción guardada"))
      .catch(() => {});
  }

  const p = data.period;
  const isRest = !data.session;
  const pesoDone = diary?.weight_kg != null;
  const entrenoDone = (diary?.workout_sets?.length ?? 0) > 0;
  const dietaDone = diary?.diet_adherence != null;
  const diarioDone = diary?.energy_1_5 != null || diary?.mood_1_5 != null || diary?.sleep_hours != null;

  return (
    <div className="space-y-6">
      {/* Medidor del período */}
      {p && (
        <div className="rounded-2xl border p-4" style={cardStyle}>
          <div className="flex items-center justify-between text-sm">
            <span className="font-semibold">Día {p.days_elapsed} de {p.days_total}</span>
            <span className="opacity-60">{p.days_left} días para el cierre</span>
          </div>
          <div className="mt-2 h-2 w-full overflow-hidden rounded-full" style={{ background: "rgba(128,128,128,0.2)" }}>
            <div className="h-full rounded-full" style={{ width: `${Math.min(100, Math.round((p.days_elapsed / Math.max(1, p.days_total)) * 100))}%`, background: brand.color_primary }} />
          </div>
          {canClose && (
            <button onClick={onGoClose} className="mt-3 flex w-full items-center justify-center gap-1 rounded-xl py-2 text-sm font-semibold" style={{ background: brand.color_primary, color: "#0a0a0f" }}>
              Ya puedes cerrar tu período <ChevronRight size={16} />
            </button>
          )}
        </div>
      )}

      {/* Checklist del día */}
      {p && (
        <div className="rounded-2xl border p-4" style={cardStyle}>
          <p className="mb-3 text-sm font-semibold">Tu registro de hoy</p>
          <div className="space-y-1.5">
            <ChecklistRow icon={Scale} label="Peso" done={pesoDone} onClick={onGoDiary} accent={brand.color_primary} />
            <ChecklistRow icon={Dumbbell} label={isRest ? "Entreno · hoy descanso" : "Entreno (series)"} done={isRest || entrenoDone} muted={isRest} onClick={onGoWorkout} accent={brand.color_primary} />
            <ChecklistRow icon={UtensilsCrossed} label="Dieta (¿la seguiste?)" done={dietaDone} onClick={onGoDiary} accent={brand.color_primary} />
            <ChecklistRow icon={NotebookPen} label="Diario (cómo te sientes)" done={diarioDone} onClick={onGoDiary} accent={brand.color_primary} />
          </div>
        </div>
      )}

      {/* Comidas */}
      <section>
        <SectionTitle icon={UtensilsCrossed} text="Qué como hoy" accent={brand.color_primary} />
        <div className="mt-3 space-y-3">
          {data.meals.map((meal) => (
            <MealCard key={meal.slot} meal={meal} chosen={chosen[String(meal.slot)]} brand={brand} onPick={pick} />
          ))}
        </div>
      </section>

      {/* Entrenamiento */}
      <section>
        <SectionTitle icon={Dumbbell} text="Qué entreno hoy" accent={brand.color_primary} />
        {data.session ? (
          <div className="mt-3 rounded-2xl border p-4" style={cardStyle}>
            <p className="text-sm font-semibold">{data.session.name}</p>
            {data.session.warmup && (
              <p className="mt-1 text-xs opacity-60">Calentamiento: {data.session.warmup}</p>
            )}
            <ul className="mt-3 space-y-2.5">
              {data.session.exercises.map((ex) => (
                <li key={ex.exercise_id} className="flex items-center justify-between">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{ex.name}</p>
                    <p className="text-xs opacity-60">
                      {ex.sets} × {ex.rep_range} · RIR {ex.rir}
                      {ex.start_weight_hint_kg ? ` · ~${ex.start_weight_hint_kg} kg` : ""}
                    </p>
                  </div>
                  {ex.video_url && (
                    <a href={ex.video_url} target="_blank" rel="noreferrer"
                      style={{ color: brand.color_primary }}>
                      <PlayCircle size={20} />
                    </a>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="mt-3 rounded-2xl border p-4 text-sm opacity-60" style={cardStyle}>
            Hoy toca descanso. Aprovecha para recuperar.
          </div>
        )}
      </section>

      {/* Acciones */}
      <div className="space-y-2">
        <button
          onClick={onGoDiary}
          className="flex w-full items-center justify-between rounded-2xl px-4 py-3.5 font-semibold"
          style={{ background: brand.color_primary, color: "#0a0a0f" }}
        >
          {data.already_logged ? "Editar mi registro de hoy" : "Registrar mi día"}
          <ChevronRight size={18} />
        </button>
        {canClose && (
          <button onClick={onGoClose} className="flex w-full items-center justify-between rounded-2xl border px-4 py-3.5 font-medium" style={cardStyle}>
            Cerrar mi período <ChevronRight size={18} />
          </button>
        )}
        <button
          onClick={() => setAskOpen(true)}
          className="flex w-full items-center justify-center gap-2 py-2 text-sm opacity-60"
        >
          <MessageCircle size={15} /> Solicitar un ajuste
        </button>
      </div>

      {askOpen && <AskAdjustment api={api} brand={brand} onClose={() => setAskOpen(false)} />}
    </div>
  );
}

function MealCard({
  meal,
  chosen,
  brand,
  onPick,
}: {
  meal: TodayMealSlot;
  chosen?: string;
  brand: PortalBrand;
  onPick: (slot: number, key: string) => void;
}) {
  const single = meal.options.length <= 1;
  return (
    <div className="rounded-2xl border p-4" style={cardStyle}>
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold">{meal.name}</p>
        <span className="flex items-center gap-1 text-xs opacity-50">
          <Clock size={12} /> {meal.time} · {Math.round(meal.target.kcal)} kcal
        </span>
      </div>
      <div className="mt-3 space-y-1.5">
        {meal.options.map((opt) => {
          const active = single || chosen === opt.key;
          return (
            <button
              key={opt.key}
              disabled={single}
              onClick={() => onPick(meal.slot, opt.key)}
              className="flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left transition-colors"
              style={{
                background: active ? `${brand.color_primary}1f` : "transparent",
                border: `1px solid ${active ? brand.color_primary : "transparent"}`,
              }}
            >
              <span className="min-w-0">
                <span className="block truncate text-sm">{opt.title}</span>
                <span className="text-xs opacity-50">
                  {Math.round(opt.macros.protein_g)}P · {Math.round(opt.macros.carbs_g)}C · {Math.round(opt.macros.fat_g)}G
                  {opt.prep_minutes ? ` · ${opt.prep_minutes} min` : ""}
                </span>
              </span>
              {active && !single && <Check size={16} style={{ color: brand.color_primary }} />}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function AskAdjustment({ api, brand, onClose }: { api: Api; brand: PortalBrand; onClose: () => void }) {
  const toast = usePortalToast();
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function send() {
    if (msg.trim().length < 5 || busy) return;
    setBusy(true);
    try {
      await api.changeRequest(msg.trim());
      toast.push("Solicitud enviada a tu coach");
      onClose();
    } catch {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-0" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-t-3xl p-6"
        style={{ background: cardStyle.background }}
        onClick={(e) => e.stopPropagation()}
      >
        <p className="text-base font-semibold">Solicitar un ajuste</p>
        <p className="mt-1 text-sm opacity-60">
          Cuéntale a tu coach qué quieres cambiar. Lo revisará y actualizará tu plan.
        </p>
        <textarea
          autoFocus
          className="mt-4 min-h-[96px] w-full rounded-xl border bg-transparent p-3 text-sm"
          style={{ borderColor: "rgba(128,128,128,0.3)" }}
          placeholder="Por ejemplo: la sentadilla me molesta la rodilla…"
          value={msg}
          onChange={(e) => setMsg(e.target.value)}
        />
        <div className="mt-4 flex gap-2">
          <button className="flex-1 rounded-xl border py-3 text-sm font-medium" style={{ borderColor: "rgba(128,128,128,0.3)" }} onClick={onClose}>
            Cancelar
          </button>
          <button
            className="flex-1 rounded-xl py-3 text-sm font-semibold"
            style={{ background: brand.color_primary, color: "#0a0a0f", opacity: msg.trim().length < 5 ? 0.5 : 1 }}
            disabled={busy || msg.trim().length < 5}
            onClick={send}
          >
            Enviar
          </button>
        </div>
      </div>
    </div>
  );
}

const cardStyle = {
  background: "var(--portal-card, rgba(255,255,255,0.03))",
  borderColor: "rgba(128,128,128,0.18)",
} as const;

function ChecklistRow({ icon: Icon, label, done, muted, onClick, accent }: {
  icon: typeof Clock; label: string; done: boolean; muted?: boolean; onClick: () => void; accent: string;
}) {
  const active = done && !muted;
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center justify-between rounded-xl border px-3 py-2.5 text-left text-sm"
      style={{ borderColor: active ? accent : "rgba(128,128,128,0.2)", background: active ? `${accent}14` : "transparent" }}
    >
      <span className="flex items-center gap-2.5">
        <Icon size={16} className="opacity-70" />
        {label}
      </span>
      {done ? <Check size={16} style={{ color: accent, opacity: muted ? 0.4 : 1 }} /> : <span className="text-xs opacity-40">pendiente</span>}
    </button>
  );
}

export function SectionTitle({ icon: Icon, text, accent }: { icon: typeof Clock; text: string; accent: string }) {
  return (
    <div className="flex items-center gap-2">
      <Icon size={16} style={{ color: accent }} />
      <h2 className="text-sm font-semibold">{text}</h2>
    </div>
  );
}

export function Loading() {
  return (
    <div className="flex justify-center py-16">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-current border-t-transparent opacity-40" />
    </div>
  );
}

export function Empty({ icon: Icon, title, hint }: { icon: typeof Clock; title: string; hint: string }) {
  return (
    <div className="flex flex-col items-center py-16 text-center">
      <Icon size={32} className="opacity-30" />
      <p className="mt-3 text-sm font-medium">{title}</p>
      <p className="mt-1 max-w-xs text-sm opacity-50">{hint}</p>
    </div>
  );
}

```


## `frontend/src/portal/PortalWorkout.tsx`

```tsx
import { useEffect, useRef, useState } from "react";
import { Dumbbell, Plus, Trash2, PlayCircle, Check } from "lucide-react";
import type { PortalBrand, TodaySession } from "../types";
import { usePortalToast } from "./PortalToast";
import { Loading, Empty } from "./PortalToday";
import type { portalApi } from "./portalApi";

type Api = ReturnType<typeof portalApi>;
interface SetRow { weight_kg: number | null; reps: number | null }

/**
 * Entreno: el cliente registra SU rutina — series con peso y reps por ejercicio.
 * Estilo de tracker. Puede elegir QUÉ sesión ha hecho (selector), no solo la de
 * hoy. Todo se guarda solo en el backend (workout_sets) y el coach lo ve al
 * instante. Las series se conservan aunque cambie de sesión o guarde el diario.
 */
export function PortalWorkout({ api, brand }: { api: Api; brand: PortalBrand }) {
  const toast = usePortalToast();
  const today = new Date().toISOString().slice(0, 10);
  const [sessions, setSessions] = useState<TodaySession[] | null>(null);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [todayDay, setTodayDay] = useState<string | null>(null);
  const [sets, setSets] = useState<Record<number, SetRow[]>>({});
  const saveTimer = useRef<number | null>(null);

  useEffect(() => {
    Promise.all([api.training(), api.today(), api.getDiary(today)]).then(([tr, t, diary]) => {
      const ss = tr.sessions ?? [];
      setSessions(ss);
      setTodayDay(t.session?.day ?? null);
      if (t.session) {
        const i = ss.findIndex((s) => s.day === t.session!.day && s.name === t.session!.name);
        if (i >= 0) setSelectedIdx(i);
      }
      const logged: Record<number, SetRow[]> = {};
      ((diary?.workout_sets as any[]) ?? []).forEach((ws) => {
        (logged[ws.exercise_id] ??= [])[ws.set_number - 1] = { weight_kg: ws.weight_kg, reps: ws.reps };
      });
      Object.keys(logged).forEach((k) => {
        logged[+k] = Array.from(logged[+k], (r) => r ?? { weight_kg: null, reps: null });
      });
      setSets(logged);
    });
  }, [api, today]);

  const selected = sessions?.[selectedIdx] ?? null;

  // Garantiza filas objetivo para los ejercicios de la sesión elegida (sin pisar
  // lo ya registrado en otras sesiones del mismo día).
  useEffect(() => {
    if (!selected) return;
    setSets((s) => {
      let changed = false;
      const next = { ...s };
      for (const ex of selected.exercises) {
        if (!next[ex.exercise_id]) {
          next[ex.exercise_id] = Array.from({ length: Math.max(1, Math.min(20, ex.sets || 3)) }, () => ({ weight_kg: null, reps: null }));
          changed = true;
        }
      }
      return changed ? next : s;
    });
  }, [selected]);

  function flush(next: Record<number, SetRow[]>) {
    const workout_sets: any[] = [];
    Object.entries(next).forEach(([exId, rows]) => {
      rows.forEach((r, i) => {
        if (r.weight_kg != null || r.reps != null) {
          workout_sets.push({ exercise_id: Number(exId), set_number: i + 1, reps: r.reps, weight_kg: r.weight_kg });
        }
      });
    });
    if (saveTimer.current) window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(() => {
      api.saveDiary({ log_date: today, workout_sets }).then(() => toast.push("Entreno guardado")).catch(() => {});
    }, 800);
  }

  function setRow(exId: number, idx: number, patch: Partial<SetRow>) {
    setSets((s) => {
      const next = { ...s, [exId]: s[exId].map((r, i) => (i === idx ? { ...r, ...patch } : r)) };
      flush(next);
      return next;
    });
  }
  function addSet(exId: number) {
    setSets((s) => {
      if ((s[exId]?.length ?? 0) >= 20) return s;
      const next = { ...s, [exId]: [...(s[exId] ?? []), { weight_kg: null, reps: null }] };
      flush(next);
      return next;
    });
  }
  function removeSet(exId: number, idx: number) {
    setSets((s) => {
      const next = { ...s, [exId]: s[exId].filter((_, i) => i !== idx) };
      flush(next);
      return next;
    });
  }

  if (sessions === null) return <Loading />;
  if (sessions.length === 0) {
    return <Empty icon={Dumbbell} title="Aún no tienes plan" hint="Cuando tu coach publique tu plan, aquí registrarás tus entrenamientos." />;
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold">Registrar entreno</h2>
        <p className="mt-0.5 text-xs opacity-60">Elige la sesión que has hecho y anota tus series. Se guarda solo.</p>
      </div>

      {/* Selector de sesión */}
      <div className="flex flex-wrap gap-2">
        {sessions.map((s, i) => {
          const active = i === selectedIdx;
          const isToday = todayDay && s.day === todayDay;
          return (
            <button
              key={i}
              onClick={() => setSelectedIdx(i)}
              className="rounded-xl border px-3 py-2 text-left text-xs transition-colors"
              style={active ? { borderColor: brand.color_primary, background: `${brand.color_primary}1f` } : { borderColor: "rgba(128,128,128,0.22)" }}
            >
              <span className="block font-semibold">{s.name || `Sesión ${i + 1}`}</span>
              <span className="opacity-60">{s.day}{isToday ? " · hoy" : ""}</span>
            </button>
          );
        })}
      </div>

      {selected && (
        <>
          {selected.warmup && <p className="text-xs opacity-60">Calentamiento: {selected.warmup}</p>}
          {selected.exercises.map((ex) => {
            const rows = sets[ex.exercise_id] ?? [];
            const doneCount = rows.filter((r) => r.weight_kg != null && r.reps != null).length;
            return (
              <div key={ex.exercise_id} className="rounded-2xl border p-4" style={cardStyle}>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold">{ex.name}</p>
                    <p className="text-xs opacity-60">
                      Objetivo: {ex.sets} × {ex.rep_range} · RIR {ex.rir}
                      {ex.start_weight_hint_kg ? ` · ~${ex.start_weight_hint_kg} kg` : ""}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {doneCount > 0 && (
                      <span className="flex items-center gap-1 text-xs" style={{ color: brand.color_primary }}>
                        <Check size={13} /> {doneCount}/{rows.length}
                      </span>
                    )}
                    {ex.video_url && (
                      <a href={ex.video_url} target="_blank" rel="noreferrer" style={{ color: brand.color_primary }}>
                        <PlayCircle size={18} />
                      </a>
                    )}
                  </div>
                </div>

                <div className="mt-3 space-y-1.5">
                  <div className="grid grid-cols-[28px_1fr_1fr_28px] items-center gap-2 px-1 text-[10px] uppercase tracking-wide opacity-40">
                    <span>Set</span><span>Peso (kg)</span><span>Reps</span><span></span>
                  </div>
                  {rows.map((r, i) => {
                    const done = r.weight_kg != null && r.reps != null;
                    return (
                      <div key={i} className="grid grid-cols-[28px_1fr_1fr_28px] items-center gap-2">
                        <span className="text-center text-xs font-semibold tabular-nums" style={{ color: done ? brand.color_primary : undefined, opacity: done ? 1 : 0.5 }}>{i + 1}</span>
                        <SetInput value={r.weight_kg} step={0.5} placeholder={ex.start_weight_hint_kg ? String(ex.start_weight_hint_kg) : "—"} accent={brand.color_primary} onChange={(v) => setRow(ex.exercise_id, i, { weight_kg: v })} />
                        <SetInput value={r.reps} step={1} placeholder="—" accent={brand.color_primary} onChange={(v) => setRow(ex.exercise_id, i, { reps: v })} />
                        <button onClick={() => removeSet(ex.exercise_id, i)} className="flex justify-center opacity-40 hover:opacity-100"><Trash2 size={14} /></button>
                      </div>
                    );
                  })}
                  <button onClick={() => addSet(ex.exercise_id)} className="mt-1 flex w-full items-center justify-center gap-1 rounded-xl border border-dashed py-2 text-xs opacity-70" style={{ borderColor: "rgba(128,128,128,0.3)" }}>
                    <Plus size={13} /> Añadir serie
                  </button>
                </div>
                {ex.technique_cue && <p className="mt-2 text-xs opacity-50">💡 {ex.technique_cue}</p>}
              </div>
            );
          })}
          {selected.cooldown && (
            <div className="rounded-2xl border p-4 text-xs opacity-60" style={cardStyle}>
              Vuelta a la calma: {selected.cooldown}
            </div>
          )}
        </>
      )}
      <p className="pb-2 text-center text-xs opacity-40">Se guarda automáticamente</p>
    </div>
  );
}

function SetInput({ value, step, placeholder, accent, onChange }: {
  value: number | null; step: number; placeholder: string; accent: string; onChange: (v: number | null) => void;
}) {
  return (
    <input
      type="number"
      inputMode="decimal"
      step={step}
      value={value ?? ""}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
      className="w-full rounded-xl border bg-transparent px-3 py-2 text-center text-sm font-semibold outline-none"
      style={{ borderColor: "rgba(128,128,128,0.22)", caretColor: accent }}
    />
  );
}

const cardStyle = {
  background: "var(--portal-card, rgba(255,255,255,0.03))",
  borderColor: "rgba(128,128,128,0.18)",
} as const;

```


## `frontend/src/portal/portalApi.ts`

```ts
/**
 * API del portal del cliente. Sin JWT: el token firmado va en la URL.
 *
 * Todas las llamadas cuelgan de /api/p/{token}. El token se captura de la ruta
 * del navegador (/p/:token) y se pasa a cada método.
 */

import type {
  ChangeRequestOut,
  DailyLogUpsert,
  FeedbackDocOut,
  PeriodCloseIn,
  PortalPlanOut,
  PortalState,
  TodaySession,
  TodayView,
} from "../types";

export class PortalError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  let payload: BodyInit | undefined;
  if (body instanceof FormData) {
    payload = body;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(`/api${path}`, { method, headers, body: payload });
  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try {
      const d = await res.json();
      if (typeof d.detail === "string") detail = d.detail;
      else if (Array.isArray(d.detail)) detail = d.detail.map((x: any) => x.msg).join("; ");
    } catch {
      /* sin cuerpo */
    }
    throw new PortalError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export function portalApi(token: string) {
  const base = `/p/${token}`;
  return {
    state: () => req<PortalState>("GET", `${base}/state`),
    today: () => req<TodayView>("GET", `${base}/today`),
    training: () => req<{ sessions: TodaySession[] }>("GET", `${base}/training`),
    plan: () => req<PortalPlanOut>("GET", `${base}/plan`),
    getDiary: (logDate: string) =>
      req<Record<string, any>>("GET", `${base}/diary/${logDate}`),
    saveDiary: (body: Partial<DailyLogUpsert> & { log_date: string }) =>
      req<{ saved: boolean }>("PUT", `${base}/diary`, body),
    close: (body: PeriodCloseIn) => req<{ closed: boolean }>("POST", `${base}/close`, body),
    closePhotos: (files: File[], kind: string) => {
      const fd = new FormData();
      files.forEach((f) => fd.append("files", f));
      return req<unknown[]>("POST", `${base}/close/photos?kind=${kind}`, fd);
    },
    feedback: () => req<FeedbackDocOut[]>("GET", `${base}/feedback`),
    changeRequest: (message: string) =>
      req<ChangeRequestOut>("POST", `${base}/change-request`, { message }),
  };
}

```


## `frontend/src/types.ts`

```ts
/**
 * types.ts — espejo manual de los schemas Pydantic del backend (regla A.1.5).
 *
 * Fuente de verdad: backend/app/schemas/ai.py y backend/app/schemas/entities.py.
 * Si cambia un schema en el backend, este archivo se actualiza en el mismo commit.
 */

// ===================================================== literales comunes ====
export type Sex = "male" | "female";
export type GoalType = "fat_loss" | "muscle_gain" | "recomp";
export type Level = "beginner" | "intermediate" | "advanced";
export type TrainingPlace = "gym" | "home" | "outdoor";
export type DietMode = "flexible_7" | "strict";
export type ClientStatus =
  | "onboarding"
  | "active"
  | "awaiting_feedback"
  | "at_risk"
  | "review_pending"
  | "inactive";
export type DietAdherence = "yes" | "partial" | "no";
export type PhotoKind = "front" | "side" | "back" | "detail";
export type Theme = "light" | "dark";
export type PlanStatus = "draft" | "published" | "superseded";
export type PeriodStatus = "open" | "closed" | "analyzed";
export type OptionKey = "A" | "B" | "C" | "D" | "E" | "F" | "G";

// ========================================== salida IA ① — núcleo del plan ====
export interface Macros {
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface MealSlotTarget {
  kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface MealSlotDef {
  slot: number;
  name: string;
  time: string;
  target: MealSlotTarget;
}

export interface Supplement {
  name: string;
  dose: string;
  timing: string;
  evidence_note: string;
}

export interface NutritionCore {
  tdee_kcal: number;
  target_kcal: number;
  rationale: string;
  macros: Macros;
  meals: MealSlotDef[];
  supplements: Supplement[];
  flexibility_rules: string[];
  refeed_or_break: string | null;
}

export interface WeeklyProgressionWeek {
  week: 1 | 2 | 3 | 4;
  intent: string;
  load_pct: number;
  rir_target: string;
  volume_note: string;
}

export interface PlannedExercise {
  exercise_id: number;
  sets: number;
  rep_range: string;
  rir: string;
  tempo: string | null;
  rest_sec: number;
  start_weight_hint_kg: number | null;
  progression_rule: string;
  technique_cue: string;
  biomech_cue: string;
}

export interface TrainingSession {
  day: string;
  name: string;
  warmup: string;
  exercises: PlannedExercise[];
  cooldown: string;
}

export interface CardioSession {
  type: "liss" | "hiit";
  minutes: number;
  times_per_week: number;
  notes: string | null;
}

export interface CardioPlan {
  daily_steps: number;
  sessions: CardioSession[];
}

export interface TrainingCore {
  split_name: string;
  split_rationale: string;
  weekly_progression: WeeklyProgressionWeek[];
  sessions: TrainingSession[];
  cardio: CardioPlan;
  deload_instructions: string;
}

export interface PlanCoreOutput {
  nutrition: NutritionCore;
  training: TrainingCore;
}

// ======================================= salida IA ② — banco de comidas ====
export interface Ingredient {
  food: string;
  grams: number; // siempre en CRUDO
  household: string;
}

export interface OptionMacros {
  kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface MealOption {
  key: OptionKey | null; // null en modo strict
  title: string;
  ingredients: Ingredient[];
  prep: string;
  prep_minutes: number;
  macros: OptionMacros;
  tags: string[];
}

export interface FlexibleSlot {
  slot: number;
  options: MealOption[]; // exactamente 7, keys A-G
}

export interface MealsFlexibleOutput {
  mode: "flexible_7";
  slots: FlexibleSlot[];
}

export interface StrictDayMeal {
  slot: number;
  dish: MealOption;
}

export interface StrictDay {
  day:
    | "lunes"
    | "martes"
    | "miercoles"
    | "jueves"
    | "viernes"
    | "sabado"
    | "domingo";
  meals: StrictDayMeal[];
}

export interface MealsStrictOutput {
  mode: "strict";
  days: StrictDay[]; // exactamente 7, lunes→domingo
  free_meal_guidelines: string | null;
}

export type MealsOutput = MealsFlexibleOutput | MealsStrictOutput;

// ==================================== salida IA ③ — contenido educativo ====
export interface EducationPill {
  topic: string;
  for_client: string;
}

export interface BiomechPattern {
  pattern: string;
  cues: string[];
  why: string;
}

export interface FaqItem {
  q: string;
  a: string;
}

export interface EducationOutput {
  pills: EducationPill[];
  biomech_by_pattern: BiomechPattern[];
  faq: FaqItem[];
}

// ================================================== entidades de la API ====
export interface MealScheduleItem {
  slot: number;
  name: string;
  time: string;
}

export interface ClientCreate {
  full_name: string;
  email: string;
  phone?: string | null;
}

export interface AnamnesisSubmit {
  sex: Sex;
  birth_date: string; // ISO date
  height_cm: number;
  start_weight_kg: number;
  body_fat_pct?: number | null;
  injuries_notes?: string | null;
  medical_notes?: string | null;
  medication_notes?: string | null;
  sport_history?: string | null;
  level: Level;
  goal_type: GoalType;
  goal_weight_kg?: number | null;
  goal_deadline?: string | null;
  priority_zones?: string | null;
  training_days: number;
  session_max_min: number;
  training_place: TrainingPlace;
  equipment: string[];
  meals_per_day: number;
  meal_schedule: MealScheduleItem[];
  food_allergies: string[];
  food_dislikes: string[];
  food_likes: string[];
  lifestyle_notes?: string | null;
  current_supplements?: string | null;
  diet_mode: DietMode;
  strict_free_meal_enabled: boolean;
  consent_accepted: true;
}

export interface ClientOut {
  id: number;
  full_name: string;
  email: string;
  phone: string | null;
  sex: Sex | null;
  birth_date: string | null;
  height_cm: number | null;
  start_weight_kg: number | null;
  current_weight_kg: number | null;
  body_fat_pct: number | null;
  goal_type: GoalType | null;
  goal_weight_kg: number | null;
  goal_deadline: string | null;
  level: Level | null;
  training_days: number | null;
  session_max_min: number | null;
  training_place: TrainingPlace | null;
  equipment: string[] | null;
  excluded_exercise_ids: number[] | null;
  injuries_notes: string | null;
  medical_notes: string | null;
  medication_notes: string | null;
  sport_history: string | null;
  meals_per_day: number | null;
  meal_schedule: MealScheduleItem[] | null;
  food_allergies: string[] | null;
  food_dislikes: string[] | null;
  food_likes: string[] | null;
  lifestyle_notes: string | null;
  current_supplements: string | null;
  diet_mode: DietMode | null;
  strict_free_meal_enabled: boolean;
  status: ClientStatus;
  auto_pilot: boolean;
  emails_enabled: boolean;
  consent_signed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExerciseOut {
  id: number;
  canonical_name: string;
  aliases: string[];
  muscle_primary: string;
  muscle_secondary: string[];
  movement_pattern: string;
  equipment: string[];
  level_min: 1 | 2 | 3;
  video_url: string | null;
  technique_notes: string | null;
  biomechanics_notes: string | null;
  contraindications: string[];
  archived: boolean;
}

export interface BrandConfigOut {
  id: number;
  name: string;
  logo_path: string | null;
  color_primary: string;
  color_secondary: string;
  color_bg: string;
  font_family: "Inter" | "Montserrat" | "Poppins" | "DM Sans" | "Plus Jakarta Sans";
  tagline: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  contact_web: string | null;
  docs_theme: Theme;
  portal_theme: Theme;
}

export interface WorkoutSetIn {
  exercise_id: number;
  set_number: number;
  reps?: number | null;
  weight_kg?: number | null;
  rpe?: number | null;
  notes?: string | null;
}

export interface DailyLogUpsert {
  log_date: string;
  weight_kg?: number | null;
  sleep_hours?: number | null;
  diet_adherence?: DietAdherence | null;
  diet_notes?: string | null;
  energy_1_5?: number | null;
  mood_1_5?: number | null;
  fatigue_1_5?: number | null;
  free_notes?: string | null;
  chosen_options_json?: Record<string, OptionKey> | null;
  option_feedback_json?: Record<string, "up" | "down"> | null;
  workout_sets: WorkoutSetIn[];
}

export interface PeriodCloseIn {
  closing_weight_kg: number;
  closing_rating: number;
  closing_hardest?: string | null;
  closing_questions?: string | null;
  closing_waist_cm?: number | null;
  closing_hip_cm?: number | null;
  closing_arm_cm?: number | null;
  closing_thigh_cm?: number | null;
}

export interface ChangeRequestOut {
  id: number;
  client_id: number;
  message: string;
  status: "open" | "resolved";
  created_at: string;
  resolved_at: string | null;
}

export interface LoginIn {
  username: string;
  password: string;
}

export interface TokenOut {
  access_token: string;
  token_type: "bearer";
}

// --- Respuestas compuestas de la API (Fase 2) ---
export interface PortalLinkOut {
  portal_token: string;
  portal_url: string;
  anamnesis_url: string;
}

export interface ClientCreatedOut {
  client: ClientOut;
  links: PortalLinkOut;
}

export interface MeOut {
  id: number;
  username: string;
}

// --- Portal del cliente (Fase 6) ---
export interface PortalBrand {
  name: string;
  color_primary: string;
  color_secondary: string;
  color_bg: string;
  font_family: string;
  portal_theme: Theme;
  logo_path: string | null;
}

export interface PortalPeriodInfo {
  period_id: number;
  period_index: number;
  starts_on: string;
  ends_on: string;
  days_total: number;
  days_elapsed: number;
  days_left: number;
  can_close: boolean;
  status: PeriodStatus;
}

export interface PortalState {
  first_name: string;
  status: ClientStatus;
  diet_mode: DietMode | null;
  has_plan: boolean;
  period: PortalPeriodInfo | null;
  brand: PortalBrand;
}

export interface TodayMealOption {
  key: string;
  title: string;
  macros: { kcal: number; protein_g: number; carbs_g: number; fat_g: number };
  prep_minutes: number | null;
  tags: string[];
}

export interface TodayMealSlot {
  slot: number;
  name: string;
  time: string;
  target: { kcal: number; protein_g: number; carbs_g: number; fat_g: number };
  options: TodayMealOption[];
  chosen_key: string | null;
}

export interface TodayExercise {
  exercise_id: number;
  name: string;
  sets: number;
  rep_range: string;
  rir: string;
  rest_sec: number;
  start_weight_hint_kg: number | null;
  technique_cue: string | null;
  video_url: string | null;
}

export interface TodaySession {
  day: string;
  name: string;
  warmup: string | null;
  exercises: TodayExercise[];
  cooldown: string | null;
}

export interface TodayView {
  date: string;
  day_label: string;
  period: PortalPeriodInfo | null;
  meals: TodayMealSlot[];
  session: TodaySession | null;
  already_logged: boolean;
}

export interface PortalPlanOut {
  month_index: number;
  nutrition: NutritionCore & { meal_bank?: MealsOutput } | null;
  training: TrainingCore | null;
  education: EducationOutput | null;
  diet_mode: DietMode | null;
}

export interface FeedbackDocOut {
  id: number;
  kind: string;
  sent_at: string | null;
  content_json: Record<string, unknown> | null;
}

```


## `frontend/vite.config.ts`

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En dev, las llamadas a /api se proxyean al backend (hot-reload completo).
// En producción, Caddy hace este papel.
export default defineConfig({
  plugins: [react()],
  server: {
    // En Windows + Docker el watcher nativo no detecta cambios del bind mount;
    // el polling garantiza que el hot-reload SIEMPRE recoja las ediciones.
    watch: { usePolling: true, interval: 300 },
    proxy: {
      "/api": {
        target: process.env.VITE_API_URL || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});

```


## `frontend/postcss.config.js`

```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};

```


## `frontend/tailwind.config.ts`

```ts
import type { Config } from "tailwindcss";

// Tokens de la PARTE H: app oscura técnica.
// Los colores de marca configurables (brand_config) se aplican en runtime
// vía variables CSS; estos son los defaults premium.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0A0A0F",
        surface: { DEFAULT: "#111118", raised: "#1A1A24" },
        accent: "var(--brand-accent, #6EE7B7)",
        line: "rgba(255,255,255,0.06)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;

```


## `frontend/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}

```
