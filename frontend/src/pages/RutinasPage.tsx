import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Copy, Download, FileUp, FolderOpen, Pencil, Plus, Search, Send, Trash2, X,
} from "lucide-react";
import { api, getToken } from "../lib/api";
import { rankTemplates } from "../lib/poolSearch";
import { LEVEL_LABEL, PLACE_LABEL } from "../lib/format";
import { PACKAGES, PACKAGE_ORDER } from "../lib/packages";
import { ConfirmDialog, PageLoader, Spinner, useToast } from "../components/ui";
import type {
  ClientOut, ExerciseOut, TemplateCategory, TemplateListItem, TemplateOut,
  TemplateSession,
} from "../types";

/**
 * RUTINAS — el pool de rutinas/planificaciones del coach, por carpetas.
 *
 * · Cada carpeta trae 20 rutinas de fábrica (casos reales de gimnasio) y admite
 *   subir documentos externos (PDF/Word): la IA los lee y quedan re-maquetados
 *   con el diseño de la marca.
 * · "Usar" copia la rutina a un cliente (nuevo → crea el perfil en el momento;
 *   existente → se añade como plan borrador) y lleva a su Planificación.
 * · El editor es deliberadamente SIMPLE: título, caso y la tabla de sesiones
 *   (ejercicio/series/reps/RIR/descanso). Nada más.
 */

const DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

/** Los tres servicios del centro: el pool se mira con las gafas de lo que el
 *  cliente ha contratado (dieta, entrenamiento o el pack). */
const SERVICES = [
  { key: "", label: "Todo" },
  { key: "nutri", label: "Dieta" },
  { key: "train", label: "Entrenamiento" },
  { key: "full", label: "Pack completo" },
] as const;

/** Descarga autenticada (fetch → blob), mismo patrón que el dossier del plan. */
async function downloadDoc(templateId: number, title: string, toast: ReturnType<typeof useToast>,
                           service = "full") {
  try {
    const res = await fetch(`/api/templates/${templateId}/document?format=pdf&service=${service}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    if (!res.ok) throw new Error(`Error ${res.status}`);
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    const safe = title.toLowerCase().replace(/[^a-z0-9]+/gi, "_");
    const pref = service === "nutri" ? "dieta" : service === "train" ? "entreno" : "plan";
    a.download = `${pref}_${safe}.${blob.type.includes("pdf") ? "pdf" : "docx"}`;
    a.click();
    URL.revokeObjectURL(a.href);
  } catch {
    toast.push("No se pudo descargar el documento", "error");
  }
}

export default function RutinasPage() {
  const toast = useToast();
  const [cats, setCats] = useState<TemplateCategory[] | null>(null);
  const [cat, setCat] = useState<string>("");
  const [service, setService] = useState<string>("");   // "" = todo
  const [items, setItems] = useState<TemplateListItem[] | null>(null);
  const [editing, setEditing] = useState<TemplateOut | "new" | null>(null);
  const [using, setUsing] = useState<TemplateListItem | null>(null);
  const [toDelete, setToDelete] = useState<TemplateListItem | null>(null);
  const [uploading, setUploading] = useState(false);
  const [exercises, setExercises] = useState<ExerciseOut[]>([]);
  // Buscador inteligente: busca en TODAS las carpetas a la vez.
  const [q, setQ] = useState("");
  const [allItems, setAllItems] = useState<TemplateListItem[] | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const loadCats = useCallback(() => {
    api.templateCategories().then((cs) => {
      setCats(cs);
      setCat((prev) => prev || cs[0]?.key || "");
    }).catch(() => setCats([]));
  }, []);
  useEffect(loadCats, [loadCats]);

  const loadItems = useCallback(() => {
    if (!cat) return;
    api.listTemplates(cat, service || undefined).then(setItems).catch(() => setItems([]));
    setAllItems(null); // invalida el índice del buscador (datos cambiados)
  }, [cat, service]);
  useEffect(() => { setItems(null); loadItems(); }, [loadItems]);

  // Biblioteca de ejercicios: para el editor (nombres) y las filas nuevas.
  useEffect(() => {
    api.listExercises({}).then(setExercises).catch(() => {});
  }, []);

  // Índice del buscador (todas las carpetas): se carga al primer tecleo y se
  // refresca tras cualquier alta/edición/borrado (loadItems lo invalida).
  const searching = q.trim().length >= 2;
  useEffect(() => {
    if (searching && allItems === null) {
      api.listTemplates(undefined, service || undefined)
        .then(setAllItems).catch(() => setAllItems([]));
    }
  }, [searching, allItems, service]);
  const catLabels = useMemo(() => new Map(cats?.map((c) => [c.key, c.label]) ?? []), [cats]);
  const results = useMemo(
    () => (searching && allItems ? rankTemplates(allItems, catLabels, q) : null),
    [searching, allItems, catLabels, q]);
  async function onUpload(f: File | null) {
    if (!f || !cat || uploading) return;
    setUploading(true);
    try {
      await api.importTemplate(cat, f);
      toast.push("Rutina importada y re-maquetada con el diseño de la marca");
      loadItems(); loadCats();
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo importar el documento", "error");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function onDelete() {
    if (!toDelete) return;
    try {
      await api.deleteTemplate(toDelete.id);
      toast.push("Rutina eliminada");
      setToDelete(null);
      loadItems(); loadCats();
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo eliminar", "error");
    }
  }

  if (cats === null) return <PageLoader />;

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 md:px-8 md:py-8">
      <header className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-widest text-zinc-500">Biblioteca</p>
          <h1 className="mt-1 text-2xl font-semibold text-zinc-100">Rutinas</h1>
        </div>
        <div className="flex gap-2">
          <input ref={fileRef} type="file" accept=".pdf,.docx" className="hidden"
            onChange={(e) => onUpload(e.target.files?.[0] ?? null)} />
          <button className="btn btn-ghost" disabled={uploading}
            onClick={() => fileRef.current?.click()}
            title="Sube un PDF o Word externo: se lee, se mapea a tu biblioteca y queda con el diseño de la marca">
            {uploading ? <Spinner /> : <FileUp size={15} />} Subir rutina
          </button>
          <button className="btn btn-primary" onClick={() => setEditing("new")}>
            <Plus size={15} /> Nueva rutina
          </button>
        </div>
      </header>

      {/* Buscador inteligente: escribe el caso como lo piensas ("adelgazar
          barriga 3 días", "señora 55 espalda", "volumen brazos en casa") y
          busca en TODAS las carpetas, con sinónimos y tolerancia a erratas. */}
      <div className="relative mb-4">
        <Search size={16} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500" />
        <input
          className="input !py-3 !pl-10"
          placeholder="Busca el caso: «adelgazar barriga 3 días», «señora 55 espalda», «volumen en casa»…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        {q && (
          <button onClick={() => setQ("")} aria-label="Limpiar búsqueda"
            className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-200">
            <X size={16} />
          </button>
        )}
      </div>

      {/* Qué se va a entregar: el pool se filtra por el servicio contratado */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="text-xs uppercase tracking-widest text-zinc-500">Servicio</span>
        {SERVICES.map((sv) => (
          <button key={sv.key} onClick={() => setService(sv.key)}
            className="rounded-lg border px-3 py-1.5 text-xs font-semibold transition-colors"
            style={service === sv.key
              ? { background: "var(--surface-raised)", borderColor: "var(--brand-accent)", color: "var(--brand-accent)" }
              : { borderColor: "var(--line-strong)", color: "var(--text-faint)" }}>
            {sv.label}
          </button>
        ))}
      </div>

      {/* Carpetas (elegir una limpia la búsqueda) */}
      <div className="mb-5 flex flex-wrap gap-2" style={searching ? { opacity: 0.55 } : undefined}>
        {cats.map((c) => (
          <button key={c.key} onClick={() => { setQ(""); setCat(c.key); }} title={c.blurb}
            className="flex items-center gap-2 rounded-xl border px-3.5 py-2 text-sm font-medium transition-colors"
            style={cat === c.key && !searching
              ? { background: "var(--surface-raised)", borderColor: "var(--brand-accent)", color: "var(--ink)" }
              : { borderColor: "var(--line-strong)", color: "var(--text-dim)" }}>
            <FolderOpen size={15} style={cat === c.key && !searching ? { color: "var(--brand-accent)" } : undefined} />
            {c.label}
            <span className="text-xs text-zinc-500">{c.count}</span>
          </button>
        ))}
      </div>

      {searching ? (
        results === null ? (
          <PageLoader />
        ) : results.length === 0 ? (
          <div className="card p-10 text-center text-sm text-zinc-500">
            Nada parecido a «{q}». Prueba con otras palabras (objetivo, zona,
            días, casa/gimnasio) o crea la rutina nueva.
          </div>
        ) : (
          <div className="space-y-2.5">
            <p className="text-xs text-zinc-500">
              {results.length} {results.length === 1 ? "rutina afín" : "rutinas afines"} en todas las carpetas, la más parecida primero
            </p>
            {results.map((t) => (
              <RoutineRow key={t.id} t={t} folderLabel={catLabels.get(t.category)} service={service}
                onUse={() => setUsing(t)}
                onDownload={() => downloadDoc(t.id, t.title, toast, service || "full")}
                onEdit={() => api.getTemplate(t.id).then(setEditing).catch(() => toast.push("No se pudo abrir", "error"))}
                onDelete={() => setToDelete(t)} />
            ))}
          </div>
        )
      ) : items === null ? (
        <PageLoader />
      ) : items.length === 0 ? (
        <div className="card p-10 text-center text-sm text-zinc-500">
          Esta carpeta está vacía. Sube una rutina o crea una nueva.
        </div>
      ) : (
        <div className="space-y-2.5">
          {items.map((t) => (
            <RoutineRow key={t.id} t={t} service={service}
              onUse={() => setUsing(t)}
              onDownload={() => downloadDoc(t.id, t.title, toast, service || "full")}
              onEdit={() => api.getTemplate(t.id).then(setEditing).catch(() => toast.push("No se pudo abrir", "error"))}
              onDelete={() => setToDelete(t)} />
          ))}
        </div>
      )}

      {editing && (
        <TemplateEditor
          tpl={editing === "new" ? null : editing}
          category={cat}
          cats={cats}
          exercises={exercises}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); loadItems(); loadCats(); }}
        />
      )}
      {using && <UseDialog tpl={using} onClose={() => setUsing(null)} />}
      <ConfirmDialog
        open={toDelete !== null}
        title={toDelete ? `¿Eliminar «${toDelete.title}»?` : ""}
        body="Se quita del pool. Los planes ya asignados a clientes no se tocan."
        confirmLabel="Eliminar"
        destructive
        onConfirm={onDelete}
        onCancel={() => setToDelete(null)}
      />
    </div>
  );
}

/** Tarjeta de una rutina (lista de carpeta y resultados del buscador). */
function RoutineRow({ t, folderLabel, service, onUse, onDownload, onEdit, onDelete }: {
  t: TemplateListItem;
  folderLabel?: string;
  service?: string;
  onUse: () => void;
  onDownload: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="card flex flex-wrap items-center gap-3 p-4">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-zinc-100">{t.title}</span>
          {folderLabel && <Chip tone="var(--brand-accent)">{folderLabel}</Chip>}
          {service !== "nutri" && t.level && <Chip>{LEVEL_LABEL[t.level as keyof typeof LEVEL_LABEL] ?? t.level}</Chip>}
          {service !== "nutri" && t.days_per_week != null && <Chip>{t.days_per_week} días</Chip>}
          {service !== "nutri" && t.training_place && <Chip>{PLACE_LABEL[t.training_place as keyof typeof PLACE_LABEL] ?? t.training_place}</Chip>}
          {service !== "train" && t.meals_per_day != null && <Chip>{t.meals_per_day} comidas</Chip>}
          {service !== "train" && t.diet_pattern && <Chip tone="var(--brand-accent)">{t.diet_pattern}</Chip>}
          {t.source === "upload" && <Chip tone="var(--brand-accent)">subida</Chip>}
          {t.source === "manual" && <Chip tone="var(--brand-accent-2-hi)">propia</Chip>}
        </div>
        {t.case_note && <p className="mt-1 text-sm text-zinc-500">{t.case_note}</p>}
        {service !== "train" && t.diet_focus && (
          <p className="mt-1 text-sm" style={{ color: "var(--text-dim)" }}>Dieta: {t.diet_focus}</p>
        )}
      </div>
      <div className="flex shrink-0 items-center gap-1.5">
        <button className="btn btn-primary !px-3 !py-2" onClick={onUse}
          title="Crear el perfil de un cliente (o elegir uno existente) con esta rutina">
          <Send size={14} /> Usar
        </button>
        <IconBtn title={service === "nutri" ? "Descargar solo la dieta (PDF de la marca)"
          : service === "train" ? "Descargar solo el entrenamiento (PDF de la marca)"
          : "Descargar el plan completo (PDF de la marca)"} onClick={onDownload}>
          <Download size={15} />
        </IconBtn>
        <IconBtn title="Editar" onClick={onEdit}><Pencil size={15} /></IconBtn>
        <IconBtn title="Eliminar" onClick={onDelete}><Trash2 size={15} /></IconBtn>
      </div>
    </div>
  );
}

function Chip({ children, tone }: { children: React.ReactNode; tone?: string }) {
  return (
    <span className="rounded-md px-1.5 py-0.5 text-[11px] font-semibold"
      style={{ background: "color-mix(in srgb, var(--ink) 8%, transparent)", color: tone ?? "var(--text-dim)" }}>
      {children}
    </span>
  );
}

function IconBtn({ title, onClick, children }: { title: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} title={title} aria-label={title}
      className="flex h-9 w-9 items-center justify-center rounded-lg border text-zinc-400 transition-colors hover:text-zinc-200"
      style={{ borderColor: "var(--line-strong)" }}>
      {children}
    </button>
  );
}

/* ================================ USAR CON UN CLIENTE ================================ */

function UseDialog({ tpl, onClose }: { tpl: TemplateListItem; onClose: () => void }) {
  const toast = useToast();
  const nav = useNavigate();
  const [mode, setMode] = useState<"nuevo" | "existente">("nuevo");
  const [clients, setClients] = useState<ClientOut[]>([]);
  const [clientId, setClientId] = useState<number | "">("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [tier, setTier] = useState("train");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.listClients().then((cs) =>
      setClients([...cs].sort((a, b) => a.full_name.localeCompare(b.full_name)))
    ).catch(() => {});
  }, []);

  async function submit() {
    if (busy) return;
    setBusy(true);
    try {
      const r = mode === "existente"
        ? await api.useTemplate(tpl.id, { client_id: Number(clientId) })
        : await api.useTemplate(tpl.id, {
            new_client: { full_name: name.trim(), email: email.trim(), phone: phone.trim() || undefined, package_tier: tier },
          });
      toast.push(r.created_client
        ? "Perfil creado con la rutina como plan borrador"
        : "Rutina añadida como plan borrador");
      nav(`/clientes/${r.client_id}?tab=planificacion`);
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo asignar la rutina", "error");
      setBusy(false);
    }
  }

  const valid = mode === "existente" ? clientId !== "" : name.trim().length >= 2 && /\S+@\S+\.\S+/.test(email);

  return (
    <Overlay onClose={onClose}>
      <h2 className="text-lg font-semibold text-zinc-100">Usar «{tpl.title}»</h2>
      <p className="mt-1 text-sm text-zinc-500">
        La rutina se copia como plan en BORRADOR: la revisas en su ficha y la publicas.
      </p>

      <div className="mt-4 inline-flex rounded-xl border p-1" style={{ borderColor: "var(--line-strong)" }}>
        {(["nuevo", "existente"] as const).map((m) => (
          <button key={m} onClick={() => setMode(m)}
            className="rounded-lg px-4 py-1.5 text-sm font-medium"
            style={mode === m
              ? { background: "var(--surface-raised)", color: "var(--brand-accent)" }
              : { color: "var(--text-faint)" }}>
            {m === "nuevo" ? "Cliente nuevo" : "Cliente existente"}
          </button>
        ))}
      </div>

      {mode === "nuevo" ? (
        <div className="mt-4 space-y-3">
          <div>
            <label className="label">Nombre completo</label>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="label">Email</label>
              <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div>
              <label className="label">Teléfono (opcional)</label>
              <input className="input" value={phone} onChange={(e) => setPhone(e.target.value)} />
            </div>
          </div>
          <div>
            <label className="label">Plan</label>
            <select className="input" value={tier} onChange={(e) => setTier(e.target.value)}>
              {PACKAGE_ORDER.map((k) => (
                <option key={k} value={k}>
                  {PACKAGES[k].label} — {PACKAGES[k].priceMonthEur} €
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-zinc-500">
              Decide qué recibe: solo la dieta, solo el entrenamiento o ambos.
            </p>
          </div>
        </div>
      ) : (
        <div className="mt-4">
          <label className="label">Cliente</label>
          <select className="input" value={clientId}
            onChange={(e) => setClientId(e.target.value === "" ? "" : Number(e.target.value))}>
            <option value="">— Elige —</option>
            {clients.map((c) => <option key={c.id} value={c.id}>{c.full_name}</option>)}
          </select>
        </div>
      )}

      <div className="mt-5 flex justify-end gap-2">
        <button className="btn btn-ghost" onClick={onClose}>Cancelar</button>
        <button className="btn btn-primary" disabled={!valid || busy} onClick={submit}>
          {busy ? <Spinner /> : mode === "nuevo" ? "Crear perfil con esta rutina" : "Asignar la rutina"}
        </button>
      </div>
    </Overlay>
  );
}

/* ==================================== EDITOR ====================================
   Deliberadamente SIMPLE: título + caso + la tabla de cada sesión
   (ejercicio / series / reps / RIR / descanso). La progresión semanal, el
   cardio y la descarga se conservan tal cual (o con valores estándar). */

type EditExercise = { exercise_id: number | ""; sets: number; rep_range: string; rir: string; rest_sec: number; technique_cue: string };
type EditSession = { day: string; name: string; warmup: string; cooldown: string; exercises: EditExercise[] };

function TemplateEditor({ tpl, category, cats, exercises, onClose, onSaved }: {
  tpl: TemplateOut | null;
  category: string;
  cats: TemplateCategory[];
  exercises: ExerciseOut[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const toast = useToast();
  const [title, setTitle] = useState(tpl?.title ?? "");
  const [caseNote, setCaseNote] = useState(tpl?.case_note ?? "");
  const [cat, setCat] = useState(tpl?.category ?? category);
  const [level, setLevel] = useState(tpl?.level ?? "beginner");
  const [place, setPlace] = useState(tpl?.training_place ?? "gym");
  const [meals, setMeals] = useState<number>(tpl?.meals_per_day ?? 4);
  const [pattern, setPattern] = useState(tpl?.diet_pattern ?? "");
  const [dietFocus, setDietFocus] = useState(tpl?.diet_focus ?? "");
  const [sessions, setSessions] = useState<EditSession[]>(() => {
    const src = (tpl?.training_json?.sessions ?? []) as TemplateSession[];
    if (src.length === 0) {
      return [{ day: "Lunes", name: "Sesión A", warmup: "", cooldown: "", exercises: [blankRow()] }];
    }
    return src.map((s) => ({
      day: s.day, name: s.name, warmup: s.warmup ?? "", cooldown: s.cooldown ?? "",
      exercises: s.exercises.map((e) => ({
        exercise_id: e.exercise_id, sets: e.sets, rep_range: e.rep_range,
        rir: e.rir, rest_sec: e.rest_sec, technique_cue: e.technique_cue ?? "",
      })),
    }));
  });
  const [busy, setBusy] = useState(false);

  const sorted = useMemo(
    () => [...exercises].sort((a, b) => a.canonical_name.localeCompare(b.canonical_name)),
    [exercises]);

  function blankRow(): EditExercise {
    return { exercise_id: "", sets: 3, rep_range: "8-10", rir: "2", rest_sec: 120, technique_cue: "" };
  }

  function patchSession(i: number, patch: Partial<EditSession>) {
    setSessions((ss) => ss.map((s, j) => (j === i ? { ...s, ...patch } : s)));
  }
  function patchRow(i: number, k: number, patch: Partial<EditExercise>) {
    setSessions((ss) => ss.map((s, j) => j !== i ? s
      : { ...s, exercises: s.exercises.map((e, l) => (l === k ? { ...e, ...patch } : e)) }));
  }

  async function save(asCopy = false) {
    if (busy) return;
    const clean = sessions.map((s) => ({
      ...s, exercises: s.exercises.filter((e) => e.exercise_id !== ""),
    })).filter((s) => s.exercises.length > 0);
    if (!title.trim() || clean.length === 0) {
      toast.push("Pon un título y al menos una sesión con ejercicios", "error");
      return;
    }
    setBusy(true);
    // Como copia con el título sin cambiar → se distingue sola.
    const finalTitle = asCopy && tpl && title.trim() === tpl.title
      ? `${title.trim()} (copia)` : title.trim();
    const body = {
      category: cat, title: finalTitle, case_note: caseNote, level,
      training_place: place, days_per_week: clean.length,
      meals_per_day: meals, diet_pattern: pattern, diet_focus: dietFocus,
      training_json: {
        // El resto del shape (progresión, cardio, descarga) lo conserva/normaliza
        // el backend: el editor solo toca lo esencial.
        ...(tpl?.training_json ?? {}),
        split_name: tpl?.training_json?.split_name ?? finalTitle,
        sessions: clean,
      },
    };
    try {
      if (tpl && !asCopy) await api.updateTemplate(tpl.id, body);
      else await api.createTemplate(body);
      toast.push(asCopy ? `Guardada como «${finalTitle}» (la original queda intacta)` : "Rutina guardada");
      onSaved();
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo guardar", "error");
      setBusy(false);
    }
  }

  return (
    <Overlay onClose={onClose} wide>
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-zinc-100">{tpl ? "Editar rutina" : "Nueva rutina"}</h2>
        <button onClick={onClose} aria-label="Cerrar" className="text-zinc-500 hover:text-zinc-200"><X size={18} /></button>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label className="label">Título</label>
          <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} autoFocus />
        </div>
        <div className="sm:col-span-2">
          <label className="label">Caso (para quién es)</label>
          <input className="input" value={caseNote ?? ""} onChange={(e) => setCaseNote(e.target.value)}
            placeholder="P. ej.: hombre 40 años, oficina, 3 días, rodilla delicada" />
        </div>
        <div>
          <label className="label">Carpeta</label>
          <select className="input" value={cat} onChange={(e) => setCat(e.target.value)}>
            {cats.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Nivel</label>
            <select className="input" value={level ?? "beginner"} onChange={(e) => setLevel(e.target.value)}>
              <option value="beginner">Principiante</option>
              <option value="intermediate">Intermedio</option>
              <option value="advanced">Avanzado</option>
            </select>
          </div>
          <div>
            <label className="label">Lugar</label>
            <select className="input" value={place ?? "gym"} onChange={(e) => setPlace(e.target.value)}>
              <option value="gym">Gimnasio</option>
              <option value="home">Casa</option>
            </select>
          </div>
        </div>
      </div>

      {/* Eje DIETA del caso: es lo que distingue una planificación de otra
          cuando el cliente solo contrata la dieta. Cambiar comidas o patrón
          RECONSTRUYE la dieta de referencia (el backend la recalcula). */}
      <div className="mt-4 rounded-xl border p-3.5" style={{ borderColor: "var(--line-strong)" }}>
        <p className="mb-2.5 text-xs uppercase tracking-widest text-zinc-500">Dieta del caso</p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <label className="label">Comidas al día</label>
            <select className="input" value={meals} onChange={(e) => setMeals(Number(e.target.value))}>
              <option value={3}>3 comidas</option>
              <option value={4}>4 comidas</option>
              <option value={5}>5 comidas</option>
            </select>
          </div>
          <div>
            <label className="label">Patrón</label>
            <select className="input" value={pattern ?? ""} onChange={(e) => setPattern(e.target.value)}>
              <option value="">Sin restricción</option>
              <option value="vegetariano">Vegetariano</option>
              <option value="vegano">Vegano</option>
              <option value="pescetariano">Pescetariano</option>
              <option value="sin_cerdo">Sin cerdo</option>
              <option value="halal">Halal</option>
              <option value="kosher">Kosher</option>
            </select>
          </div>
          <div>
            <label className="label">En qué se centra</label>
            <input className="input" value={dietFocus ?? ""} maxLength={200}
              onChange={(e) => setDietFocus(e.target.value)}
              placeholder="P. ej.: 3 comidas y nada entre horas" />
          </div>
        </div>
      </div>

      <div className="mt-5 space-y-4">
        {sessions.map((s, i) => (
          <div key={i} className="rounded-xl border p-3.5" style={{ borderColor: "var(--line-strong)" }}>
            <div className="mb-2.5 flex flex-wrap items-center gap-2">
              <select className="input !w-36" value={s.day} onChange={(e) => patchSession(i, { day: e.target.value })}>
                {DAYS.map((d) => <option key={d}>{d}</option>)}
              </select>
              <input className="input !w-56" value={s.name} placeholder="Nombre de la sesión"
                onChange={(e) => patchSession(i, { name: e.target.value })} />
              <div className="flex-1" />
              {sessions.length > 1 && (
                <button className="text-xs text-zinc-500 hover:text-red-400"
                  onClick={() => setSessions((ss) => ss.filter((_, j) => j !== i))}>
                  Quitar sesión
                </button>
              )}
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[11px] uppercase tracking-wide text-zinc-500">
                    <th className="pb-1.5 pr-2">Ejercicio</th>
                    <th className="w-16 pb-1.5 pr-2">Series</th>
                    <th className="w-20 pb-1.5 pr-2">Reps</th>
                    <th className="w-16 pb-1.5 pr-2">RIR</th>
                    <th className="w-24 pb-1.5 pr-2">Descanso</th>
                    <th className="w-8 pb-1.5" />
                  </tr>
                </thead>
                <tbody>
                  {s.exercises.map((e, k) => (
                    <tr key={k}>
                      <td className="pr-2 pt-1">
                        <select className="input !py-1.5" value={e.exercise_id}
                          onChange={(ev) => patchRow(i, k, { exercise_id: ev.target.value === "" ? "" : Number(ev.target.value) })}>
                          <option value="">— Elige ejercicio —</option>
                          {sorted.map((x) => <option key={x.id} value={x.id}>{x.canonical_name}</option>)}
                        </select>
                      </td>
                      <td className="pr-2 pt-1">
                        <input className="input !py-1.5" type="number" min={1} max={10} value={e.sets}
                          onChange={(ev) => patchRow(i, k, { sets: Number(ev.target.value) || 1 })} />
                      </td>
                      <td className="pr-2 pt-1">
                        <input className="input !py-1.5" value={e.rep_range}
                          onChange={(ev) => patchRow(i, k, { rep_range: ev.target.value })} />
                      </td>
                      <td className="pr-2 pt-1">
                        <input className="input !py-1.5" value={e.rir}
                          onChange={(ev) => patchRow(i, k, { rir: ev.target.value })} />
                      </td>
                      <td className="pr-2 pt-1">
                        <input className="input !py-1.5" type="number" min={15} max={600} step={15} value={e.rest_sec}
                          onChange={(ev) => patchRow(i, k, { rest_sec: Number(ev.target.value) || 60 })} />
                      </td>
                      <td className="pt-1 text-right">
                        <button className="text-zinc-600 hover:text-red-400" aria-label="Quitar ejercicio"
                          onClick={() => patchSession(i, { exercises: s.exercises.filter((_, l) => l !== k) })}>
                          <X size={15} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <button className="mt-2 text-xs font-medium text-zinc-500 hover:text-zinc-200"
              onClick={() => patchSession(i, { exercises: [...s.exercises, blankRow()] })}>
              + Añadir ejercicio
            </button>
          </div>
        ))}
      </div>

      <div className="mt-3 flex items-center justify-between">
        <button className="btn btn-ghost"
          onClick={() => setSessions((ss) => [...ss, {
            day: DAYS[Math.min(ss.length, 6)], name: `Sesión ${String.fromCharCode(65 + ss.length)}`,
            warmup: "", cooldown: "", exercises: [blankRow()],
          }])}>
          <Plus size={14} /> Añadir sesión
        </button>
        <div className="flex gap-2">
          <button className="btn btn-ghost" onClick={onClose}>Cancelar</button>
          {tpl && (
            <button className="btn btn-ghost" disabled={busy} onClick={() => save(true)}
              title="Crea una rutina NUEVA con estos cambios y deja la original tal cual">
              <Copy size={14} /> Guardar como copia
            </button>
          )}
          <button className="btn btn-primary" disabled={busy} onClick={() => save(false)}>
            {busy ? <Spinner /> : "Guardar"}
          </button>
        </div>
      </div>
    </Overlay>
  );
}

/* Overlay compartido (fondo oscurecido + tarjeta centrada, scrollable) */
function Overlay({ children, onClose, wide }: { children: React.ReactNode; onClose: () => void; wide?: boolean }) {
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4 py-10"
      onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`card w-full ${wide ? "max-w-3xl" : "max-w-md"} p-5`}>{children}</div>
    </div>
  );
}
