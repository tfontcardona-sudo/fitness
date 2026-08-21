import { useEffect, useState } from "react";
import { ancla } from "../lib/anchors";
import { ChevronDown, Eye, FileText, Pencil, Save, Sparkles } from "lucide-react";
import { api, ApiError, getToken } from "../lib/api";
import type { ClientOut } from "../types";
import { ExpandableArea, Spinner, useToast } from "./ui";
import { ACTIVITY_LABEL, ageFrom, DIET_LABEL, DIET_PATTERN_LABEL, GOAL_LABEL, LEVEL_LABEL, PLACE_LABEL } from "../lib/format";
import { isCriticalLine, isRelevantClinical } from "../lib/clinical";

/**
 * Tab Anamnesis: ficha estructurada del cliente. Es la fuente de datos que la
 * IA usa para generar el plan. Puede rellenarse de dos formas:
 *  1. "Leer anamnesis con IA": lee el PDF subido y pre-rellena estos campos.
 *  2. A mano.
 * En ambos casos el coach revisa y corrige antes de generar (seguridad). El
 * PATCH del backend registra el diff campo a campo (audit trail).
 */
export function ClientAnamnesisTab({ client, onSaved, onDirtyChange }: { client: ClientOut; onSaved: () => void; onDirtyChange?: (dirty: boolean) => void }) {
  const toast = useToast();
  const [draft, setDraft] = useState<Partial<ClientOut>>({});
  const [busy, setBusy] = useState(false);
  const [reading, setReading] = useState(false);
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [pdfName, setPdfName] = useState<string | null>(null);
  // Por defecto la ficha se VE (ordenada por colores, sin campos editables);
  // el formulario solo aparece si el coach pulsa "Editar datos".
  const [editMode, setEditMode] = useState(false);

  // Nombre del PDF de anamnesis subido (para poder verlo/descargarlo desde aquí).
  useEffect(() => {
    api.listClientDocuments(client.id)
      .then((docs) => setPdfName(docs[0]?.name ?? null))
      .catch(() => setPdfName(null));
  }, [client.id]);

  function openPdf() {
    if (!pdfName) return;
    fetch(api.clientDocumentUrl(client.id, pdfName), { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => {
        // Sin esto, un 401/500 abría una pestaña con el JSON del error.
        if (!r.ok) throw new Error(`Error ${r.status}`);
        return r.blob();
      })
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
  // Avisa al perfil de si hay cambios sin guardar, para que confirme antes de
  // cambiar de pestaña (el panel se re-monta y perdería el borrador).
  useEffect(() => { onDirtyChange?.(dirty); }, [dirty, onDirtyChange]);

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
    if (reading || !pdfName) return;
    // Con la ficha ya rellenada, releer PISA campos y gasta créditos: se avisa.
    if (client.goal_type &&
        !window.confirm("La IA sobrescribirá los campos de la ficha con lo que lea del PDF y gastará créditos. ¿Seguir?")) {
      return;
    }
    setReading(true);
    try {
      const res = await api.readAnamnesis(client.id);
      setAnalysis(res.deep_analysis);
      setDraft({});
      toast.push("Anamnesis leída. Revisa los datos antes de generar.");
      onSaved();
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push([detail?.message ?? e?.message ?? "No se pudo leer el PDF", detail?.error].filter(Boolean).join(" — "), "error");
    } finally {
      setReading(false);
    }
  }

  return (
    <div className="space-y-4">
      {/* Barra fina: el 95% del tiempo el coach viene a LEER la ficha — la
          explicación de "Leer con IA" solo aparece cuando aún no hay datos. */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Sparkles size={15} style={{ color: "var(--brand-accent)" }} />
          <p className="text-sm font-medium text-zinc-200">Anamnesis</p>
          {!client.goal_type && !pdfName && (
            <span className="text-xs text-zinc-500">Sube el PDF y púlsalo para rellenar la ficha con IA.</span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {/* Aviso de borrador SIEMPRE visible (también al volver a "Ver ficha"):
              los cambios del formulario siguen vivos hasta guardarlos. */}
          {dirty && (
            <>
              <span className="text-xs font-medium" style={{ color: "#9A6B15" }}>
                Cambios sin guardar
              </span>
              <button onClick={save} disabled={busy} className="btn btn-primary">
                {busy ? <Spinner /> : <Save size={15} />} Guardar cambios
              </button>
            </>
          )}
          {pdfName && (
            <button onClick={openPdf} className="btn btn-ghost" title={pdfName}>
              <FileText size={15} /> Ver PDF
            </button>
          )}
          <button onClick={() => setEditMode((e) => !e)} className="btn btn-ghost">
            {editMode ? <Eye size={15} /> : <Pencil size={15} />}
            {editMode ? "Ver ficha" : "Editar datos"}
          </button>
          <button
            onClick={readWithAI}
            disabled={reading || !pdfName}
            title={!pdfName ? "Sube antes el PDF de la anamnesis" : undefined}
            className="btn btn-primary"
          >
            <Sparkles size={15} /> {reading ? "Leyendo PDF…" : "Leer con IA"}
          </button>
          <span {...ancla("anamnesis.revision")} aria-hidden className="sr-only" />
        </div>
      </div>

      {analysis && (
        <div className="card p-4">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">Análisis de la IA</p>
          {/* La síntesis viene en puntos ("- …"): se muestra como lista, no
              como párrafo corrido. Si es prosa antigua, cae a texto normal. */}
          {splitNote(analysis).length > 1 ? (
            <ul className="list-disc space-y-0.5 pl-4 text-sm text-zinc-300">
              {splitNote(analysis).map((l, i) => <li key={i}>{l}</li>)}
            </ul>
          ) : (
            <p className="text-sm text-zinc-300">{analysis}</p>
          )}
        </div>
      )}

      {!editMode && <AnamnesisView client={client} />}

      {editMode && (<>
      <Section title="Datos personales">
        <Select label="Sexo" value={(current("sex") as string) ?? ""} onChange={(v) => set("sex", (v || null) as any)}
          options={[["", "—"], ["male", "Hombre"], ["female", "Mujer"]]} />
        {/* Vaciar la fecha emite "" que el backend rechaza con un 422 críptico:
            se mapea a null (= sin fecha). */}
        <Field label="Fecha de nacimiento" type="date" value={(current("birth_date") as string) ?? ""}
          onChange={(v) => set("birth_date", (v || null) as any)} />
      </Section>

      <Section title="Antropometría inicial">
        <Num label="Altura (cm)" value={current("height_cm") as number} onChange={(v) => set("height_cm", v as any)} />
        <Num label="Peso inicial (kg)" value={current("start_weight_kg") as number} onChange={(v) => set("start_weight_kg", v as any)} />
        <Num label="% graso (opcional)" value={current("body_fat_pct") as number} onChange={(v) => set("body_fat_pct", v as any)} />
        <Num label="Peso objetivo (kg)" value={current("goal_weight_kg") as number} onChange={(v) => set("goal_weight_kg", v as any)} />
      </Section>

      <Section title="Objetivo y nivel" ancla="anamnesis.campo.goal_type">
        <Select label="Objetivo" value={(current("goal_type") as string) ?? ""} onChange={(v) => set("goal_type", (v || null) as any)}
          options={[["", "—"], ["fat_loss", "Pérdida de grasa"], ["muscle_gain", "Ganancia muscular"], ["recomp", "Recomposición"], ["maintenance", "Mantenimiento"], ["injury_recovery", "Recuperación de lesión"]]} />
        <Select label="Nivel" value={(current("level") as string) ?? ""} onChange={(v) => set("level", (v || null) as any)}
          options={[["", "—"], ["beginner", "Principiante"], ["intermediate", "Intermedio"], ["advanced", "Avanzado"]]} />
      </Section>

      <Section title="Entrenamiento">
        <Num label="Días por semana" value={current("training_days") as number} onChange={(v) => set("training_days", v as any)} />
        <Select label="Actividad diaria (fuera del entreno)" value={(current("daily_activity_level") as string) ?? ""} onChange={(v) => set("daily_activity_level", (v || null) as any)}
          options={[
            ["", "—"],
            ["sedentary", "Sedentaria — oficina, sentado casi todo el día"],
            ["light", "Ligera — de pie o caminando a ratos"],
            ["active", "Activa — trabajo físico, muchos pasos"],
            ["very_active", "Muy activa — trabajo físico intenso"],
          ]} />
        <Num label="Duración sesión (min)" value={current("session_max_min") as number} onChange={(v) => set("session_max_min", v as any)} />
        <Select label="Dónde entrena" value={(current("training_place") as string) ?? ""} onChange={(v) => set("training_place", (v || null) as any)}
          options={[["", "—"], ["gym", "Gimnasio"], ["home", "Casa"], ["outdoor", "Exterior"]]} />
        <CSV label="Material (solo casa/exterior)" value={current("equipment") as string[]} onChange={(v) => set("equipment", v as any)} />
      </Section>

      <Section title="Experiencia y otros deportes">
        <Area label="Experiencia con pesas y otros deportes" value={(current("sport_history") as string) ?? ""} onChange={(v) => set("sport_history", v as any)} />
      </Section>

      <Section title="Dieta">
        <Select label="Modo de dieta" value={(current("diet_mode") as string) ?? ""} onChange={(v) => set("diet_mode", (v || null) as any)}
          options={[["", "—"], ["flexible_7", "Flexible (equivalencias)"], ["strict", "Menú cerrado"]]} />
        {/* Patrón ético/religioso: se respeta al 100% en generación, banco de
            emergencia, Revisor 0 y alertas (violación = veto, no aviso). */}
        <Select label="Patrón dietético (ético/religioso)"
          value={(current("diet_pattern") as string) ?? ""} onChange={(v) => set("diet_pattern", (v || null) as any)}
          options={[["", "Ninguno"], ...Object.entries(DIET_PATTERN_LABEL)]} />
        <CSV label="Alimentos que le gustan" value={current("food_likes") as string[]} onChange={(v) => set("food_likes", v as any)} />
        <CSV label="Alimentos que evita" value={current("food_dislikes") as string[]} onChange={(v) => set("food_dislikes", v as any)} />
        <CSV label="Alergias" value={current("food_allergies") as string[]} onChange={(v) => set("food_allergies", v as any)} />
        <MealsPlanner
          mealsPerDay={current("meals_per_day") as number | null}
          schedule={current("meal_schedule") as { slot: number; name: string; time: string }[] | null}
          onChange={(meals, schedule) => {
            set("meals_per_day", meals as any);
            set("meal_schedule", schedule as any);
          }}
        />
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
      </>)}
    </div>
  );
}

// ------------------------- FICHA VISUAL (solo lectura) -----------------------
// La anamnesis se LEE por secciones de color; no hay campos que tocar sin
// querer. Cada color agrupa un tipo de dato (datos, cuerpo, entreno, dieta,
// clínica en rojo/ámbar, vida). "Editar datos" abre el formulario clásico.

const V_COLORS = {
  datos: "#3D6E9E",      // azul: identidad
  cuerpo: "#E8833A",     // naranja: cuerpo y objetivo
  entreno: "#2E5E8C",    // azul marca: entrenamiento
  dieta: "#3F7446",      // verde: alimentación
  clinica: "#9A6B15",    // ámbar: salud
  lesiones: "#B3261E",   // rojo: lo crítico
  vida: "#63519E",       // morado: estilo de vida
};

function splitNote(text: string | null | undefined): string[] {
  const t = (text ?? "").trim();
  if (!t) return [];
  return t.split(/\n+/).map((s) => s.replace(/^[-•*]\s*/, "").trim()).filter(Boolean);
}

/** Ficha ordenada por lo que el coach necesita: (1) qué respetar — alergias,
 *  patrón, lesiones, clínica —, (2) quién es y su objetivo, (3) entreno y
 *  dieta, (4) contexto de vida. Lo vacío se COLAPSA a una línea (no roba
 *  espacio) y lo largo se pliega dejando lo crítico siempre a la vista. */
function AnamnesisView({ client }: { client: ClientOut }) {
  const age = ageFrom(client.birth_date);
  const pairs = (rows: [string, string | null | undefined][]) =>
    rows.filter(([, v]) => v != null && v !== "");
  const meals = client.meal_schedule?.length
    ? client.meal_schedule.map((m: any) => `${m.name} (${m.time})`).join(" · ")
    : client.meals_per_day == null
      ? "Lo decide el equipo (reparto óptimo para su objetivo)"
      : `${client.meals_per_day} al día`;
  const allergies = client.food_allergies ?? [];
  // Sin anamnesis, "sin lesiones" NO es un visto bueno: es que no hay datos.
  const fichaRellenada = Boolean(client.goal_type || client.height_cm || client.start_weight_kg);
  const pattern = client.diet_pattern ? DIET_PATTERN_LABEL[client.diet_pattern] ?? client.diet_pattern : null;
  return (
    <div className="space-y-3">
      {/* QUÉ RESPETAR — chips de seguridad, siempre lo primero que se ve. */}
      {(allergies.length > 0 || pattern) && (
        <div className="flex flex-wrap items-center gap-2">
          {allergies.map((a) => (
            <span key={a} className="rounded-full px-2.5 py-1 text-xs font-semibold"
              style={{ background: "color-mix(in srgb, #B3261E 14%, transparent)", color: "#B3261E" }}>
              ⚠ Alergia: {a}
            </span>
          ))}
          {pattern && (
            <span className="rounded-full px-2.5 py-1 text-xs font-semibold"
              style={{ background: "color-mix(in srgb, #9A6B15 14%, transparent)", color: "#9A6B15" }}>
              Patrón: {pattern}
            </span>
          )}
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {/* 1ª fila: SEGURIDAD (lo crítico nunca se pliega ni baja). */}
        <VNotes color={V_COLORS.lesiones} title="Lesiones y movilidad" text={client.injuries_notes}
          emptyLabel={fichaRellenada ? "Sin lesiones declaradas ✓" : "Anamnesis pendiente"} />
        <VNotes color={V_COLORS.clinica} title="Historia clínica y salud" text={client.medical_notes}
          emptyLabel={fichaRellenada ? "Sin patologías declaradas ✓" : "Anamnesis pendiente"} />

        {/* 2ª fila: quién es + su entrenamiento. */}
        <VCard color={V_COLORS.cuerpo} title="Perfil y objetivo" rows={pairs([
          ["Sexo · edad", [client.sex === "male" ? "Hombre" : client.sex === "female" ? "Mujer" : null,
                           age ? `${age} años` : null].filter(Boolean).join(" · ") || null],
          ["Altura", client.height_cm ? `${client.height_cm} cm` : null],
          ["Peso inicial", client.start_weight_kg ? `${client.start_weight_kg} kg` : null],
          ["% graso", client.body_fat_pct ? `${client.body_fat_pct}%` : null],
          ["Peso objetivo", client.goal_weight_kg ? `${client.goal_weight_kg} kg` : null],
          ["Objetivo", client.goal_type ? GOAL_LABEL[client.goal_type] : null],
          ["Nivel", client.level ? LEVEL_LABEL[client.level] : null],
        ])} />
        <VCard color={V_COLORS.entreno} title="Entrenamiento" rows={pairs([
          ["Días / semana", client.training_days ? String(client.training_days) : null],
          ["Actividad diaria", client.daily_activity_level ? ACTIVITY_LABEL[client.daily_activity_level] ?? client.daily_activity_level : null],
          ["Duración sesión", client.session_max_min ? `${client.session_max_min} min` : null],
          ["Dónde", client.training_place ? PLACE_LABEL[client.training_place] : null],
          ["Material", client.equipment?.length ? client.equipment.join(", ") : null],
        ])} note={client.sport_history} noteLabel="Experiencia y otros deportes" />

        {/* 3ª fila: dieta + medicación/suplementación (fusionadas: fragmentaban
            la parrilla con tarjetas casi vacías). */}
        <VCard color={V_COLORS.dieta} title="Dieta" rows={pairs([
          ["Modo", client.diet_mode ? DIET_LABEL[client.diet_mode] : null],
          ["Patrón", pattern],
          ["Comidas del día", meals],
          ["Le gustan", client.food_likes?.length ? client.food_likes.join(", ") : null],
          ["Evita", client.food_dislikes?.length ? client.food_dislikes.join(", ") : null],
          ["Alergias", allergies.length ? allergies.join(", ") : null],
        ])} />
        <VDouble
          color={V_COLORS.clinica}
          a={{ title: "Medicación", text: client.medication_notes, empty: "Sin medicación" }}
          b={{ title: "Suplementación actual", text: client.current_supplements, empty: "Sin suplementación" }}
        />

        {/* 4ª fila: contexto de vida (plegado; los temas salen como subtítulos). */}
        <div className="sm:col-span-2">
          <VNotes color={V_COLORS.vida} title="Estilo de vida, motivo y objetivos" text={client.lifestyle_notes} />
        </div>
      </div>
    </div>
  );
}

/** Dos sub-bloques cortos en UNA tarjeta (medicación + suplementación): juntos
 *  ocupan una celda en vez de dos tarjetas casi vacías. */
function VDouble({ color, a, b }: {
  color: string;
  a: { title: string; text: string | null | undefined; empty: string };
  b: { title: string; text: string | null | undefined; empty: string };
}) {
  const la = splitNote(a.text);
  const lb = splitNote(b.text);
  return (
    <div className="card border-l-2 p-4" style={{ borderLeftColor: color }}>
      {[{ ...a, lines: la }, { ...b, lines: lb }].map((s, i) => (
        <div key={s.title} className={i === 1 ? "mt-3" : ""}>
          <p
            className="mb-1 inline-block rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide"
            style={{ background: `color-mix(in srgb, ${color} 13%, transparent)`, color }}
          >
            {s.title}
          </p>
          {s.lines.length ? (
            <ul className="list-disc space-y-0.5 pl-4 text-sm text-zinc-300">
              {s.lines.map((l, j) => <li key={j}><NoteLine line={l} /></li>)}
            </ul>
          ) : (
            <p className="text-xs text-zinc-500">{s.empty}</p>
          )}
        </div>
      ))}
    </div>
  );
}

/** Una línea de nota. Si la IA la prefijó por tema ("Sueño: 6 h…"), el tema se
 *  pinta como subtítulo en negrita para que el ojo encuentre cada bloque. */
function NoteLine({ line }: { line: string }) {
  const m = /^([A-ZÁÉÍÓÚÑ][\wáéíóúñüö/ ]{1,24}):\s+(.+)$/.exec(line);
  if (!m) return <>{line}</>;
  return (<><span className="font-medium text-zinc-200">{m[1]}:</span> {m[2]}</>);
}

function VCard({ color, title, rows, note, noteLabel }: {
  color: string; title: string; rows: [string, string | null | undefined][];
  note?: string | null; noteLabel?: string;
}) {
  const [noteOpen, setNoteOpen] = useState(false);
  const noteLines = splitNote(note);
  if (!rows.length && !noteLines.length) return null;
  return (
    <div className="card border-l-2 p-4" style={{ borderLeftColor: color }}>
      <p
        className="mb-2 inline-block rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide"
        style={{ background: `color-mix(in srgb, ${color} 13%, transparent)`, color }}
      >
        {title}
      </p>
      <dl className="space-y-1.5 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="flex items-start justify-between gap-3">
            <dt className="shrink-0 text-zinc-500">{k}</dt>
            <dd className="text-right font-medium text-zinc-200">{v}</dd>
          </div>
        ))}
      </dl>
      {noteLines.length > 0 && (
        <>
          {noteLabel && <p className="mt-2 text-xs text-zinc-500">{noteLabel}</p>}
          <ul className="mt-1 list-disc space-y-0.5 pl-4 text-xs text-zinc-400">
            {(noteOpen ? noteLines : noteLines.slice(0, VISIBLE_LINES)).map((l, i) => <li key={i}>{l}</li>)}
          </ul>
          {noteLines.length > VISIBLE_LINES && !noteOpen && (
            <button onClick={() => setNoteOpen(true)}
              className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-zinc-500 hover:text-zinc-300">
              <ChevronDown size={13} /> Ver todo ({noteLines.length - VISIBLE_LINES} más)
            </button>
          )}
        </>
      )}
    </div>
  );
}

/** Nº de líneas visibles por tarjeta antes de plegar. Lo crítico va SIEMPRE
 *  arriba y nunca queda oculto: el plegado solo esconde lo informativo. */
const VISIBLE_LINES = 4;

function VNotes({ color, title, text, emptyLabel }: {
  color: string; title: string; text: string | null | undefined; emptyLabel?: string;
}) {
  const [showAll, setShowAll] = useState(false);
  const raw = splitNote(text);
  // Prioridad de lectura: crítico (rojo) → relevante → resto (negaciones,
  // "sin cambios"…). El orden ORIGINAL se conserva dentro de cada grupo.
  const critical = raw.filter((l) => isCriticalLine(l));
  const relevant = raw.filter((l) => !isCriticalLine(l) && isRelevantClinical(l));
  const rest = raw.filter((l) => !isCriticalLine(l) && !isRelevantClinical(l));
  const ordered = [...critical, ...relevant, ...rest];
  // Nunca se pliega una línea crítica: el corte visible respeta el bloque rojo.
  const cut = Math.max(VISIBLE_LINES, critical.length);
  const visible = showAll ? ordered : ordered.slice(0, cut);
  const hidden = ordered.length - visible.length;
  return (
    <div className="card border-l-2 p-4" style={{ borderLeftColor: color }}>
      <p
        className="mb-2 inline-block rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide"
        style={{ background: `color-mix(in srgb, ${color} 13%, transparent)`, color }}
      >
        {title}
      </p>
      {ordered.length ? (
        <>
          <ul className="list-disc space-y-0.5 pl-4 text-sm text-zinc-300">
            {visible.map((l, i) => (
              <li
                key={i}
                className={isCriticalLine(l) ? "font-medium" : ""}
                style={isCriticalLine(l) ? { color } : undefined}
              >
                <NoteLine line={l} />
              </li>
            ))}
          </ul>
          {hidden > 0 && (
            <button
              onClick={() => setShowAll(true)}
              className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-zinc-500 hover:text-zinc-300"
            >
              <ChevronDown size={13} /> Ver todo ({hidden} más)
            </button>
          )}
          {showAll && ordered.length > cut && (
            <button
              onClick={() => setShowAll(false)}
              className="mt-2 block text-xs font-medium text-zinc-500 hover:text-zinc-300"
            >
              Mostrar menos
            </button>
          )}
        </>
      ) : (
        <p className="text-xs text-zinc-500">{emptyLabel ?? "Sin datos."}</p>
      )}
    </div>
  );
}

/** Comidas del día: el cliente elige CUÁLES quiere (desayuno, media mañana,
 *  pre-cama…) — el nº de comidas se deriva solo — o lo DELEGA en el equipo
 *  ("lo decidimos nosotros" → la IA reparte el óptimo para su objetivo). */
const MEAL_PRESETS: { name: string; time: string }[] = [
  { name: "Desayuno", time: "08:00" },
  { name: "Media mañana", time: "11:00" },
  { name: "Comida", time: "14:00" },
  { name: "Merienda", time: "18:00" },
  { name: "Cena", time: "21:00" },
  { name: "Pre-cama", time: "23:00" },
];

function MealsPlanner({ mealsPerDay, schedule, onChange }: {
  mealsPerDay: number | null;
  schedule: { slot: number; name: string; time: string }[] | null;
  onChange: (meals: number | null, schedule: { slot: number; name: string; time: string }[] | null) => void;
}) {
  const delegated = mealsPerDay == null && !(schedule?.length);
  const chosen = new Set((schedule ?? []).map((m) => m.name.toLowerCase()));

  function toggle(preset: { name: string; time: string }) {
    const key = preset.name.toLowerCase();
    // Reconstruye el horario en el orden natural del día
    const names = new Set(chosen);
    if (names.has(key)) names.delete(key);
    else names.add(key);
    const next = MEAL_PRESETS.filter((p) => names.has(p.name.toLowerCase()))
      .map((p, i) => ({ slot: i + 1, name: p.name, time: p.time }));
    onChange(next.length ? next.length : null, next.length ? next : null);
  }

  return (
    <div className="col-span-2">
      <span className="mb-1 block text-xs text-zinc-500">Comidas del día</span>
      <div className="rounded-xl border p-3" style={{ borderColor: "var(--line-strong)" }}>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => onChange(null, null)}
            className="rounded-full border px-3 py-1.5 text-xs font-medium transition-colors"
            style={delegated
              ? { borderColor: "var(--brand-accent-2)", background: "color-mix(in srgb, var(--brand-accent-2) 12%, transparent)", color: "var(--brand-accent-2)" }
              : { borderColor: "var(--line-strong)", color: "var(--text-dim)" }}
          >
            Lo decidimos nosotros
          </button>
          <span className="self-center text-xs text-zinc-600">o elige cuáles:</span>
          {MEAL_PRESETS.map((p) => {
            const active = chosen.has(p.name.toLowerCase());
            return (
              <button
                key={p.name}
                onClick={() => toggle(p)}
                className="rounded-full border px-3 py-1.5 text-xs font-medium transition-colors"
                style={active
                  ? { borderColor: "var(--brand-accent)", background: "color-mix(in srgb, var(--brand-accent) 14%, transparent)", color: "var(--brand-accent)" }
                  : { borderColor: "var(--line-strong)", color: "var(--text-dim)" }}
              >
                {p.name}
              </button>
            );
          })}
        </div>
        <p className="mt-2 text-xs text-zinc-500">
          {delegated
            ? "El plan repartirá las comidas de forma óptima para su objetivo (3-5 al día)."
            : `${chosen.size} comida${chosen.size === 1 ? "" : "s"} al día: ${(schedule ?? []).map((m) => m.name).join(", ")}.`}
        </p>
      </div>
    </div>
  );
}

function Section({ title, children, ancla: nombreAncla }: {
  title: string; children: React.ReactNode;
  /** Ancla del apartado: un aviso puede señalarlo y quedará marcado. */
  ancla?: string;
}) {
  return (
    <div className="card p-5" {...(nombreAncla ? ancla(nombreAncla) : {})}>
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
  return <ExpandableArea label={label} value={value} onChange={onChange} rows={3} className="col-span-2" />;
}
function CSV({ label, value, onChange }: { label: string; value: string[] | null | undefined; onChange: (v: string[]) => void }) {
  // BUFFER de texto mientras el campo tiene el foco: derivar lo mostrado del
  // valor parseado en cada pulsación reescribía el campo al instante y se
  // COMÍA comas y espacios ("frutos secos" era imposible de teclear; en
  // ALERGIAS, que alimenta los guardrails, era grave). La lista se emite en
  // vivo (el borrador siempre está al día para Guardar) pero lo que se VE es
  // exactamente lo tecleado hasta soltar el foco.
  const [raw, setRaw] = useState<string | null>(null);
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-zinc-500">{label}</span>
      <input type="text"
        value={raw !== null ? raw : (value ?? []).join(", ")}
        onChange={(e) => {
          const s = e.target.value;
          setRaw(s);
          onChange(s.split(",").map((x) => x.trim()).filter(Boolean));
        }}
        onBlur={() => setRaw(null)}
        placeholder="separa por comas" className="input w-full" />
    </label>
  );
}
