import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { useParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Camera,
  CheckCircle2,
  Download,
  FileUp,
  Loader2,
} from "lucide-react";

/**
 * Página PÚBLICA de la anamnesis (/anamnesis/{token}) — llega por el email o
 * WhatsApp de arranque. La vía PRINCIPAL es el formulario digital por pasos
 * (se guarda directo en la ficha, sin papel ni lectura por IA); el PDF de
 * siempre queda como alternativa plegada al pie para quien lo prefiera.
 */

// ---- Tipos y opciones (espejo de AnamnesisSubmit del backend) ----

interface FormState {
  sex: "" | "male" | "female";
  birth_date: string;
  height_cm: string;
  start_weight_kg: string;
  body_fat_pct: string;
  goal_type: string;
  goal_weight_kg: string;
  goal_deadline: string;
  priority_zones: string;
  level: string;
  training_days: string;
  session_max_min: string;
  training_place: string;
  equipment: string;          // CSV → lista al enviar
  daily_activity_level: string;
  sport_history: string;
  injuries_notes: string;
  medical_notes: string;
  medication_notes: string;
  current_supplements: string;
  diet_mode: string;
  diet_pattern: string;
  meals_per_day: string;
  food_allergies: string;     // CSV
  food_dislikes: string;      // CSV
  food_likes: string;         // CSV
  strict_free_meal_enabled: boolean;
  lifestyle_notes: string;
  consent_accepted: boolean;
}

const VACIO: FormState = {
  sex: "", birth_date: "", height_cm: "", start_weight_kg: "", body_fat_pct: "",
  goal_type: "", goal_weight_kg: "", goal_deadline: "", priority_zones: "",
  level: "", training_days: "", session_max_min: "60", training_place: "",
  equipment: "", daily_activity_level: "", sport_history: "",
  injuries_notes: "", medical_notes: "", medication_notes: "",
  current_supplements: "", diet_mode: "", diet_pattern: "", meals_per_day: "",
  food_allergies: "", food_dislikes: "", food_likes: "",
  strict_free_meal_enabled: false, lifestyle_notes: "", consent_accepted: false,
};

const GOALS = [
  ["fat_loss", "Perder grasa"],
  ["muscle_gain", "Ganar músculo"],
  ["recomp", "Recomposición (perder grasa y ganar músculo)"],
  ["maintenance", "Mantener mi peso y mejorar hábitos"],
  ["injury_recovery", "Recuperarme de una lesión"],
] as const;

const LEVELS = [
  ["beginner", "Principiante (menos de 1 año entrenando)"],
  ["intermediate", "Intermedio (1–3 años)"],
  ["advanced", "Avanzado (más de 3 años)"],
] as const;

const PLACES = [
  ["gym", "Gimnasio"],
  ["home", "En casa"],
  ["outdoor", "Al aire libre"],
] as const;

const ACTIVITY = [
  ["sedentary", "Sedentario (trabajo sentado, poco movimiento)"],
  ["light", "Ligera (camino a diario, trabajo de pie a ratos)"],
  ["active", "Activa (trabajo en movimiento)"],
  ["very_active", "Muy activa (trabajo físico exigente)"],
] as const;

const DIET_MODES = [
  ["flexible_7", "Flexible: opciones para elegir en cada comida"],
  ["strict", "Menú cerrado: dime exactamente qué comer cada día"],
] as const;

const PATTERNS = [
  ["", "Como de todo"],
  ["vegano", "Vegano"],
  ["vegetariano", "Vegetariano"],
  ["pescetariano", "Pescetariano (pescado sí, carne no)"],
  ["sin_cerdo", "Sin cerdo"],
  ["halal", "Halal"],
  ["kosher", "Kosher"],
] as const;

const PASOS = ["Tú", "Objetivo", "Entreno", "Salud", "Comida", "Enviar"] as const;

// Campos → etiqueta en español para traducir los 422 del backend.
const FIELD_ES: Record<string, string> = {
  sex: "Sexo", birth_date: "Fecha de nacimiento", height_cm: "Altura",
  start_weight_kg: "Peso actual", body_fat_pct: "% graso",
  goal_type: "Objetivo", goal_weight_kg: "Peso objetivo",
  goal_deadline: "Fecha objetivo", level: "Nivel",
  training_days: "Días de entreno", session_max_min: "Duración de sesión",
  training_place: "Dónde entrenas", daily_activity_level: "Actividad diaria",
  meals_per_day: "Comidas al día", diet_mode: "Tipo de dieta",
  diet_pattern: "Patrón dietético", consent_accepted: "Consentimiento",
};

const csv = (s: string) =>
  s.split(/[,;\n]/).map((x) => x.trim()).filter(Boolean);

const num = (s: string): number | null => {
  const v = parseFloat(s.replace(",", "."));
  return Number.isFinite(v) ? v : null;
};

export default function AnamnesisPage() {
  const { token } = useParams();
  const fileRef = useRef<HTMLInputElement>(null);
  const fotosRef = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState<FormState>(VACIO);
  const [paso, setPaso] = useState(0);
  const [enviando, setEnviando] = useState(false);
  const [hecho, setHecho] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tokenBad, setTokenBad] = useState(false);
  // Vía PDF alternativa (plegada al pie).
  const [file, setFile] = useState<File | null>(null);
  const [pdfState, setPdfState] = useState<"idle" | "uploading" | "done">("idle");
  const [pdfError, setPdfError] = useState<string | null>(null);
  // Fotos iniciales opcionales tras enviar.
  const [fotosSubidas, setFotosSubidas] = useState(0);
  const [subiendoFotos, setSubiendoFotos] = useState(false);
  const [fotosError, setFotosError] = useState<string | null>(null);

  useEffect(() => {
    // Estado del enlace + pre-relleno con lo que el coach ya apuntó en el alta.
    fetch(`/api/p/${token}`)
      .then((r) => {
        if (r.status === 404) { setTokenBad(true); return null; }
        return r.json();
      })
      .then((st) => {
        if (st?.anamnesis_done) setHecho(true);
        // Contador REAL de fotos ya subidas: sin esto, quien volvía al enlace
        // veía "Subir mis fotos" a cero y el rechazo por límite era invisible.
        if (typeof st?.photos_count === "number") setFotosSubidas(st.photos_count);
      })
      .catch(() => { /* fallo de red: el backend re-valida al enviar */ });
    fetch(`/api/p/${token}/anamnesis/prefill`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setForm((f) => ({
          ...f,
          sex: d.sex ?? f.sex,
          birth_date: d.birth_date ?? f.birth_date,
          height_cm: d.height_cm != null ? String(d.height_cm) : f.height_cm,
          start_weight_kg: d.start_weight_kg != null ? String(d.start_weight_kg) : f.start_weight_kg,
          body_fat_pct: d.body_fat_pct != null ? String(d.body_fat_pct) : f.body_fat_pct,
          goal_type: d.goal_type ?? f.goal_type,
          goal_weight_kg: d.goal_weight_kg != null ? String(d.goal_weight_kg) : f.goal_weight_kg,
          level: d.level ?? f.level,
          training_days: d.training_days != null ? String(d.training_days) : f.training_days,
          session_max_min: d.session_max_min != null ? String(d.session_max_min) : f.session_max_min,
          training_place: d.training_place ?? f.training_place,
          daily_activity_level: d.daily_activity_level ?? f.daily_activity_level,
          equipment: Array.isArray(d.equipment) ? d.equipment.join(", ") : f.equipment,
          meals_per_day: d.meals_per_day != null ? String(d.meals_per_day) : f.meals_per_day,
          food_allergies: Array.isArray(d.food_allergies) ? d.food_allergies.join(", ") : f.food_allergies,
          food_dislikes: Array.isArray(d.food_dislikes) ? d.food_dislikes.join(", ") : f.food_dislikes,
          food_likes: Array.isArray(d.food_likes) ? d.food_likes.join(", ") : f.food_likes,
          sport_history: d.sport_history ?? f.sport_history,
          injuries_notes: d.injuries_notes ?? f.injuries_notes,
          medical_notes: d.medical_notes ?? f.medical_notes,
          medication_notes: d.medication_notes ?? f.medication_notes,
          current_supplements: d.current_supplements ?? f.current_supplements,
          diet_mode: d.diet_mode ?? f.diet_mode,
          diet_pattern: d.diet_pattern ?? f.diet_pattern,
          lifestyle_notes: d.lifestyle_notes ?? f.lifestyle_notes,
          strict_free_meal_enabled: d.strict_free_meal_enabled ?? f.strict_free_meal_enabled,
        }));
      })
      .catch(() => {});
  }, [token]);

  const set = (patch: Partial<FormState>) => {
    setError(null);
    setForm((f) => ({ ...f, ...patch }));
  };

  // Validación por paso ANTES de avanzar: mismos rangos que el backend.
  const faltaEnPaso = useMemo(() => {
    const f = form;
    const falta: Record<number, string | null> = { 0: null, 1: null, 2: null, 3: null, 4: null, 5: null };
    if (!f.sex) falta[0] = "Elige tu sexo";
    else if (!f.birth_date) falta[0] = "Falta tu fecha de nacimiento";
    else {
      const h = num(f.height_cm);
      const w = num(f.start_weight_kg);
      const bf = f.body_fat_pct ? num(f.body_fat_pct) : null;
      if (h === null || h <= 80 || h >= 250) falta[0] = "Altura en cm (entre 81 y 249)";
      else if (w === null || w <= 30 || w >= 300) falta[0] = "Peso en kg (entre 31 y 299)";
      else if (f.body_fat_pct && (bf === null || bf <= 2 || bf >= 60)) falta[0] = "% graso entre 3 y 59 (o déjalo vacío)";
    }
    if (!f.goal_type) falta[1] = "Elige tu objetivo";
    else if (f.goal_weight_kg) {
      const gw = num(f.goal_weight_kg);
      if (gw === null || gw <= 30 || gw >= 300) falta[1] = "Peso objetivo en kg (o déjalo vacío)";
    }
    if (!f.level) falta[2] = "Elige tu experiencia";
    else if (!f.training_days || +f.training_days < 2 || +f.training_days > 6) falta[2] = "Días de entreno: de 2 a 6";
    else if (!f.session_max_min || +f.session_max_min < 30 || +f.session_max_min > 180) falta[2] = "Duración de sesión: de 30 a 180 min";
    else if (!f.training_place) falta[2] = "¿Dónde entrenarás?";
    if (!f.diet_mode) falta[4] = "Elige cómo prefieres tu dieta";
    else if (f.meals_per_day && (+f.meals_per_day < 2 || +f.meals_per_day > 6)) falta[4] = "Comidas al día: de 2 a 6 (o déjalo vacío)";
    if (!f.consent_accepted) falta[5] = "Debes aceptar el consentimiento para enviar";
    return falta;
  }, [form]);

  async function enviar() {
    if (enviando || faltaEnPaso[5]) return;
    setEnviando(true);
    setError(null);
    const f = form;
    const body = {
      sex: f.sex,
      birth_date: f.birth_date,
      height_cm: num(f.height_cm),
      start_weight_kg: num(f.start_weight_kg),
      body_fat_pct: f.body_fat_pct ? num(f.body_fat_pct) : null,
      goal_type: f.goal_type,
      goal_weight_kg: f.goal_weight_kg ? num(f.goal_weight_kg) : null,
      goal_deadline: f.goal_deadline || null,
      priority_zones: f.priority_zones.trim() || null,
      level: f.level,
      training_days: +f.training_days,
      session_max_min: +f.session_max_min,
      training_place: f.training_place,
      equipment: f.training_place === "gym" ? [] : csv(f.equipment),
      daily_activity_level: f.daily_activity_level || null,
      sport_history: f.sport_history.trim() || null,
      injuries_notes: f.injuries_notes.trim() || null,
      medical_notes: f.medical_notes.trim() || null,
      medication_notes: f.medication_notes.trim() || null,
      current_supplements: f.current_supplements.trim() || null,
      diet_mode: f.diet_mode,
      diet_pattern: f.diet_pattern || null,
      meals_per_day: f.meals_per_day ? +f.meals_per_day : null,
      food_allergies: csv(f.food_allergies),
      food_dislikes: csv(f.food_dislikes),
      food_likes: csv(f.food_likes),
      strict_free_meal_enabled: f.strict_free_meal_enabled,
      lifestyle_notes: f.lifestyle_notes.trim() || null,
      consent_accepted: true,
    };
    try {
      const r = await fetch(`/api/p/${token}/anamnesis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        let msg = "No se pudo enviar. Revisa los datos e inténtalo de nuevo.";
        try {
          const data = await r.json();
          if (typeof data?.detail === "string") msg = data.detail;
          else if (Array.isArray(data?.detail) && data.detail[0]) {
            const d0 = data.detail[0];
            const campo = FIELD_ES[String(d0?.loc?.[d0.loc.length - 1])] ?? "un campo";
            msg = `Revisa ${campo}: ${d0?.msg ?? "valor no válido"}`;
          }
        } catch { /* sin cuerpo JSON */ }
        throw new Error(msg);
      }
      setHecho(true);
      window.scrollTo({ top: 0 });
    } catch (e: any) {
      setError(e?.message ?? "No se pudo enviar. Inténtalo de nuevo en un momento.");
    } finally {
      setEnviando(false);
    }
  }

  async function subirFotos(files: FileList | null) {
    if (!files || !files.length || subiendoFotos) return;
    setSubiendoFotos(true);
    setFotosError(null);
    try {
      const fd = new FormData();
      Array.from(files).slice(0, 4).forEach((f) => fd.append("files", f));
      const r = await fetch(`/api/p/${token}/anamnesis/photos`, { method: "POST", body: fd });
      if (r.ok) {
        const creadas = await r.json();
        setFotosSubidas((n) => n + (Array.isArray(creadas) ? creadas.length : 0));
      } else {
        // El rechazo (límite de 4, formato, tamaño) debe VERSE: antes el
        // spinner se apagaba sin mensaje y el cliente creía que subió.
        let msg = "No se pudieron subir las fotos. Inténtalo de nuevo.";
        try {
          const data = await r.json();
          if (typeof data?.detail === "string") msg = data.detail;
        } catch { /* sin cuerpo JSON */ }
        setFotosError(msg);
      }
    } catch {
      setFotosError("No se pudieron subir las fotos — revisa tu conexión.");
    }
    setSubiendoFotos(false);
  }

  async function uploadPdf() {
    if (!file || pdfState === "uploading") return;
    setPdfError(null);
    setPdfState("uploading");
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
      setPdfState("done");
      setHecho(true);
    } catch (e: any) {
      setPdfError(e?.message ?? "No se pudo subir. Inténtalo de nuevo en un momento.");
      setPdfState("idle");
    }
  }

  // ---- estilos base (página pública, sin el CSS del panel) ----
  const card: CSSProperties = {
    background: "#fff", borderRadius: 16, border: "1px solid #e6ddca",
    padding: 20, boxShadow: "0 1px 2px rgba(0,0,0,.04)",
  };
  const inputCls =
    "mt-1 w-full rounded-xl border px-3 py-2.5 text-[15px] outline-none focus:ring-2";
  const inputStyle: CSSProperties = { borderColor: "#d8cdb4", background: "#fffdf8" };
  const label = (t: string, opcional = false) => (
    <span className="text-[13px] font-semibold opacity-80">
      {t}{opcional && <span className="font-normal opacity-60"> · opcional</span>}
    </span>
  );
  const radioCard = (activo: boolean): CSSProperties => ({
    display: "block", borderRadius: 12, padding: "10px 12px", cursor: "pointer",
    border: `2px solid ${activo ? "#E8833A" : "#e2d8c2"}`,
    background: activo ? "#fdf1e6" : "#fffdf8", fontSize: 14,
  });

  const avanzar = () => {
    const msg = faltaEnPaso[paso];
    if (msg) { setError(msg); return; }
    setError(null);
    setPaso((p) => Math.min(p + 1, PASOS.length - 1));
    window.scrollTo({ top: 0 });
  };

  return (
    <div style={{ minHeight: "100vh", background: "#f6f1e7", color: "#26211a" }}>
      <div className="mx-auto max-w-lg px-5 py-8">
        <header className="mb-6 flex flex-col items-center text-center">
          <img src="/dq-logo.png" alt="" className="h-12 w-auto rounded-xl shadow-sm" />
          <h1 className="mt-3 text-2xl font-bold">Tu cuestionario inicial</h1>
          {!hecho && !tokenBad && (
            <p className="mt-1 max-w-md text-sm opacity-70">6 pasos · unos minutos</p>
          )}
        </header>

        {tokenBad ? (
          <div style={card} className="text-center">
            <h2 className="text-lg font-bold">Este enlace no es válido</h2>
            <p className="mt-2 text-sm opacity-75">Pide uno nuevo a tu coach.</p>
          </div>
        ) : hecho ? (
          <div className="space-y-4">
            <div style={{ ...card, borderColor: "#cfe3cf" }} className="text-center">
              <CheckCircle2 size={40} className="mx-auto" style={{ color: "#2E7D46" }} />
              <h2 className="mt-3 text-lg font-bold">¡Anamnesis recibida!</h2>
              <p className="mt-2 text-sm opacity-75">
                Te hemos enviado el acceso a tu portal por email (mira también el spam).
                Tu coach prepara tu plan.
              </p>
            </div>
            {pdfState !== "done" && fotosSubidas < 4 && (
              <div style={card}>
                <p className="text-sm font-bold">
                  <Camera size={15} className="mr-1 inline" style={{ verticalAlign: "-2px" }} />
                  Fotos iniciales (opcional, máximo 4)
                </p>
                <p className="mt-1 text-sm opacity-70">
                  Frontal · perfil · espalda, con ropa ajustada. Solo las ve tu coach.
                </p>
                <input ref={fotosRef} type="file" accept="image/*" multiple className="hidden"
                  onChange={(e) => subirFotos(e.target.files)} />
                <button onClick={() => fotosRef.current?.click()} disabled={subiendoFotos}
                  className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed px-4 py-3 text-sm font-medium"
                  style={{ borderColor: "#cbbfa5" }}>
                  {subiendoFotos ? <Loader2 size={16} className="animate-spin" /> : <Camera size={16} />}
                  {fotosSubidas > 0 ? `${fotosSubidas} foto${fotosSubidas === 1 ? "" : "s"} subida${fotosSubidas === 1 ? "" : "s"} · añadir más` : "Subir mis fotos"}
                </button>
                {fotosError && (
                  <p className="mt-3 rounded-xl border p-3 text-center text-sm"
                    style={{ borderColor: "#C2453A", background: "#fdecea", color: "#8B1A2B" }}>
                    {fotosError}
                  </p>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {/* Barra de pasos */}
            <div className="flex items-center gap-1.5">
              {PASOS.map((p, i) => (
                <button key={p} onClick={() => i < paso && setPaso(i)}
                  className="flex-1 rounded-full text-[11px] font-semibold"
                  style={{
                    padding: "5px 0",
                    background: i === paso ? "#E8833A" : i < paso ? "#f0c9a4" : "#e9e1cf",
                    color: i === paso ? "#fff" : "#26211a",
                    cursor: i < paso ? "pointer" : "default",
                  }}>
                  {p}
                </button>
              ))}
            </div>

            <div style={card} className="space-y-4">
              {paso === 0 && (<>
                <p className="text-base font-bold">Sobre ti</p>
                <div>
                  {label("Sexo")}
                  <div className="mt-1 grid grid-cols-2 gap-2">
                    <label style={radioCard(form.sex === "male")}>
                      <input type="radio" className="mr-2" checked={form.sex === "male"} onChange={() => set({ sex: "male" })} />
                      Hombre
                    </label>
                    <label style={radioCard(form.sex === "female")}>
                      <input type="radio" className="mr-2" checked={form.sex === "female"} onChange={() => set({ sex: "female" })} />
                      Mujer
                    </label>
                  </div>
                </div>
                <div>
                  {label("Fecha de nacimiento")}
                  <input type="date" className={inputCls} style={inputStyle}
                    value={form.birth_date} onChange={(e) => set({ birth_date: e.target.value })} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    {label("Altura (cm)")}
                    <input type="text" inputMode="decimal" placeholder="p. ej. 175" className={inputCls} style={inputStyle}
                      value={form.height_cm} onChange={(e) => set({ height_cm: e.target.value })} />
                  </div>
                  <div>
                    {label("Peso actual (kg)")}
                    <input type="text" inputMode="decimal" placeholder="p. ej. 78,5" className={inputCls} style={inputStyle}
                      value={form.start_weight_kg} onChange={(e) => set({ start_weight_kg: e.target.value })} />
                  </div>
                </div>
                <div>
                  {label("% de grasa corporal", true)}
                  <input type="text" inputMode="decimal" placeholder="si lo sabes" className={inputCls} style={inputStyle}
                    value={form.body_fat_pct} onChange={(e) => set({ body_fat_pct: e.target.value })} />
                </div>
              </>)}

              {paso === 1 && (<>
                <p className="text-base font-bold">Tu objetivo</p>
                <div className="space-y-2">
                  {GOALS.map(([v, t]) => (
                    <label key={v} style={radioCard(form.goal_type === v)}>
                      <input type="radio" className="mr-2" checked={form.goal_type === v} onChange={() => set({ goal_type: v })} />
                      {t}
                    </label>
                  ))}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    {label("Peso objetivo (kg)", true)}
                    <input type="text" inputMode="decimal" className={inputCls} style={inputStyle}
                      value={form.goal_weight_kg} onChange={(e) => set({ goal_weight_kg: e.target.value })} />
                  </div>
                  <div>
                    {label("¿Para cuándo?", true)}
                    <input type="date" className={inputCls} style={inputStyle}
                      value={form.goal_deadline} onChange={(e) => set({ goal_deadline: e.target.value })} />
                  </div>
                </div>
                <div>
                  {label("Zonas que quieres priorizar", true)}
                  <input type="text" placeholder="p. ej. glúteo, abdomen, hombros" className={inputCls} style={inputStyle}
                    value={form.priority_zones} onChange={(e) => set({ priority_zones: e.target.value })} />
                </div>
              </>)}

              {paso === 2 && (<>
                <p className="text-base font-bold">Tu entrenamiento</p>
                <div className="space-y-2">
                  {LEVELS.map(([v, t]) => (
                    <label key={v} style={radioCard(form.level === v)}>
                      <input type="radio" className="mr-2" checked={form.level === v} onChange={() => set({ level: v })} />
                      {t}
                    </label>
                  ))}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    {label("Días por semana")}
                    <select className={inputCls} style={inputStyle} value={form.training_days}
                      onChange={(e) => set({ training_days: e.target.value })}>
                      <option value="">Elige…</option>
                      {[2, 3, 4, 5, 6].map((n) => <option key={n} value={n}>{n} días</option>)}
                    </select>
                  </div>
                  <div>
                    {label("Minutos por sesión")}
                    <select className={inputCls} style={inputStyle} value={form.session_max_min}
                      onChange={(e) => set({ session_max_min: e.target.value })}>
                      {[45, 60, 75, 90, 120].map((n) => <option key={n} value={n}>{n} min</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  {label("¿Dónde entrenarás?")}
                  <div className="mt-1 grid grid-cols-3 gap-2">
                    {PLACES.map(([v, t]) => (
                      <label key={v} style={{ ...radioCard(form.training_place === v), textAlign: "center" }}>
                        <input type="radio" className="hidden" checked={form.training_place === v} onChange={() => set({ training_place: v })} />
                        {t}
                      </label>
                    ))}
                  </div>
                </div>
                {form.training_place && form.training_place !== "gym" && (
                  <div>
                    {label("Material del que dispones")}
                    <input type="text" placeholder="p. ej. mancuernas, bandas, barra" className={inputCls} style={inputStyle}
                      value={form.equipment} onChange={(e) => set({ equipment: e.target.value })} />
                  </div>
                )}
                <div>
                  {label("Tu actividad diaria (fuera del entreno)")}
                  <select className={inputCls} style={inputStyle} value={form.daily_activity_level}
                    onChange={(e) => set({ daily_activity_level: e.target.value })}>
                    <option value="">Elige…</option>
                    {ACTIVITY.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
                  </select>
                </div>
                <div>
                  {label("Tu experiencia deportiva", true)}
                  <textarea rows={2} placeholder="Qué has entrenado antes, otros deportes…" className={inputCls} style={inputStyle}
                    value={form.sport_history} onChange={(e) => set({ sport_history: e.target.value })} />
                </div>
              </>)}

              {paso === 3 && (<>
                <p className="text-base font-bold">Tu salud</p>
                <p className="text-sm opacity-70">
                  Cuéntalo todo, aunque parezca poco importante: tu seguridad va primero.
                </p>
                <div>
                  {label("Lesiones o molestias", true)}
                  <textarea rows={2} placeholder="p. ej. lumbalgia, rodilla derecha…" className={inputCls} style={inputStyle}
                    value={form.injuries_notes} onChange={(e) => set({ injuries_notes: e.target.value })} />
                </div>
                <div>
                  {label("Patologías o temas médicos", true)}
                  <textarea rows={2} placeholder="p. ej. hipotiroidismo, digestiones pesadas…" className={inputCls} style={inputStyle}
                    value={form.medical_notes} onChange={(e) => set({ medical_notes: e.target.value })} />
                </div>
                <div>
                  {label("Medicación actual", true)}
                  <textarea rows={2} className={inputCls} style={inputStyle}
                    value={form.medication_notes} onChange={(e) => set({ medication_notes: e.target.value })} />
                </div>
                <div>
                  {label("Suplementos que tomas", true)}
                  <textarea rows={2} placeholder="p. ej. creatina, omega 3…" className={inputCls} style={inputStyle}
                    value={form.current_supplements} onChange={(e) => set({ current_supplements: e.target.value })} />
                </div>
              </>)}

              {paso === 4 && (<>
                <p className="text-base font-bold">Tu alimentación</p>
                <div className="space-y-2">
                  {DIET_MODES.map(([v, t]) => (
                    <label key={v} style={radioCard(form.diet_mode === v)}>
                      <input type="radio" className="mr-2" checked={form.diet_mode === v} onChange={() => set({ diet_mode: v })} />
                      {t}
                    </label>
                  ))}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    {label("Patrón dietético")}
                    <select className={inputCls} style={inputStyle} value={form.diet_pattern}
                      onChange={(e) => set({ diet_pattern: e.target.value })}>
                      {PATTERNS.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
                    </select>
                  </div>
                  <div>
                    {label("Comidas al día", true)}
                    <select className={inputCls} style={inputStyle} value={form.meals_per_day}
                      onChange={(e) => set({ meals_per_day: e.target.value })}>
                      <option value="">Lo decidís vosotros</option>
                      {[2, 3, 4, 5, 6].map((n) => <option key={n} value={n}>{n} comidas</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  {label("Alergias o intolerancias", true)}
                  <input type="text" placeholder="p. ej. lactosa, frutos secos (separa con comas)" className={inputCls} style={inputStyle}
                    value={form.food_allergies} onChange={(e) => set({ food_allergies: e.target.value })} />
                </div>
                <div>
                  {label("Alimentos que NO te gustan", true)}
                  <input type="text" placeholder="p. ej. pescado azul, coliflor" className={inputCls} style={inputStyle}
                    value={form.food_dislikes} onChange={(e) => set({ food_dislikes: e.target.value })} />
                </div>
                <div>
                  {label("Alimentos que te encantan", true)}
                  <input type="text" placeholder="p. ej. arroz, pollo, chocolate" className={inputCls} style={inputStyle}
                    value={form.food_likes} onChange={(e) => set({ food_likes: e.target.value })} />
                </div>
                {form.diet_mode === "strict" && (
                  <label style={radioCard(form.strict_free_meal_enabled)}>
                    <input type="checkbox" className="mr-2" checked={form.strict_free_meal_enabled}
                      onChange={(e) => set({ strict_free_meal_enabled: e.target.checked })} />
                    Quiero una comida libre a la semana
                  </label>
                )}
              </>)}

              {paso === 5 && (<>
                <p className="text-base font-bold">Último paso</p>
                <div>
                  {label("Tu día a día", true)}
                  <textarea rows={3}
                    placeholder="Horarios, trabajo, sueño, estrés, con quién comes… todo lo que nos ayude a que el plan encaje en tu vida."
                    className={inputCls} style={inputStyle}
                    value={form.lifestyle_notes} onChange={(e) => set({ lifestyle_notes: e.target.value })} />
                </div>
                <label style={radioCard(form.consent_accepted)}>
                  <input type="checkbox" className="mr-2" checked={form.consent_accepted}
                    onChange={(e) => set({ consent_accepted: e.target.checked })} />
                  Acepto que mis datos se usen únicamente para preparar y seguir
                  mi asesoría (RGPD). Se generará un justificante de este
                  consentimiento.
                </label>
              </>)}

              {error && (
                <p className="rounded-xl border p-3 text-center text-sm"
                  style={{ borderColor: "#C2453A", background: "#fdecea", color: "#8B1A2B" }}>
                  {error}
                </p>
              )}

              <div className="flex items-center justify-between gap-3 pt-1">
                <button onClick={() => { setError(null); setPaso((p) => Math.max(0, p - 1)); }}
                  disabled={paso === 0}
                  className="flex items-center gap-1 rounded-xl px-3 py-2.5 text-sm font-semibold disabled:opacity-40">
                  <ArrowLeft size={15} /> Atrás
                </button>
                {paso < PASOS.length - 1 ? (
                  <button onClick={avanzar}
                    className="flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold text-white transition-transform active:scale-[0.98]"
                    style={{ background: "#E8833A" }}>
                    Siguiente <ArrowRight size={15} />
                  </button>
                ) : (
                  <button onClick={enviar} disabled={enviando || !form.consent_accepted}
                    className="flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold text-white transition-transform active:scale-[0.98] disabled:opacity-60"
                    style={{ background: "#2E7D46" }}>
                    {enviando ? <><Loader2 size={16} className="animate-spin" /> Enviando…</> : "Enviar mi anamnesis"}
                  </button>
                )}
              </div>
            </div>

            {/* Vía alternativa: el PDF de siempre, plegado para no estorbar. */}
            <details className="rounded-2xl border bg-white/60 px-5 py-4" style={{ borderColor: "#e6ddca" }}>
              <summary className="cursor-pointer text-sm font-semibold opacity-80">
                ¿Prefieres rellenarla en PDF?
              </summary>
              <div className="mt-3 space-y-3">
                <a href={`/api/p/${token}/anamnesis-template`}
                  className="inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white"
                  style={{ background: "#2E5E8C" }}>
                  <Download size={15} /> Descargar la anamnesis en PDF
                </a>
                <input ref={fileRef} type="file" accept="application/pdf" className="hidden"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
                <button onClick={() => fileRef.current?.click()}
                  className="flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed px-4 py-3 text-sm font-medium"
                  style={{ borderColor: file ? "#2E7D46" : "#cbbfa5", color: file ? "#2E7D46" : undefined }}>
                  <FileUp size={16} />
                  {file ? file.name : "Elegir el PDF rellenado"}
                </button>
                {pdfError && (
                  <p className="rounded-xl border p-3 text-center text-sm"
                    style={{ borderColor: "#C2453A", background: "#fdecea", color: "#8B1A2B" }}>
                    {pdfError}
                  </p>
                )}
                <button onClick={uploadPdf} disabled={!file || pdfState === "uploading"}
                  className="flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
                  style={{ background: "#E8833A" }}>
                  {pdfState === "uploading"
                    ? <><Loader2 size={16} className="animate-spin" /> Subiendo…</>
                    : "Enviar el PDF"}
                </button>
              </div>
            </details>

          </div>
        )}
      </div>
    </div>
  );
}
