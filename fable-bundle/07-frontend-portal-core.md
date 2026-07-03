

===== FILE: frontend/src/portal/PortalApp.tsx =====

import { useCallback, useEffect, useMemo, useState } from "react";
import { CalendarCheck, Dumbbell, NotebookPen } from "lucide-react";
import { portalApi, PortalError } from "./portalApi";
import type { PortalState } from "../types";
import { PortalWorkout } from "./PortalWorkout";
import { PortalDiary } from "./PortalDiary";
import { PortalClose } from "./PortalClose";
import { PortalToastProvider } from "./PortalToast";

// El portal del cliente es SOLO seguimiento: 3 pestañas abajo (Entreno, Diario,
// Quincenal). Nada más (ni Hoy, ni Plan, ni Feedback): la dieta va en el PDF.
type Tab = "entreno" | "diario" | "cierre";

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
  const [tab, setTab] = useState<Tab>("entreno");

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

  const TABS: { id: Tab; label: string; icon: typeof Dumbbell }[] = [
    { id: "entreno", label: "Entreno", icon: Dumbbell },
    { id: "diario", label: "Diario", icon: NotebookPen },
    { id: "cierre", label: "Quincenal", icon: CalendarCheck },
  ];
  const visibleTabs = TABS;

  return (
    <PortalToastProvider light={light}>
      <div className="portal-root mx-auto flex min-h-screen max-w-md flex-col">
        {/* Cabecera con marca */}
        <header className="relative z-[1] flex items-center justify-between px-5 pb-2 pt-6">
          <div>
            <p className="text-xs uppercase tracking-widest opacity-50">{state.brand.name}</p>
            <h1 className="text-xl font-semibold">Hola, {state.first_name}</h1>
          </div>
          {state.period && (
            <div className="text-right">
              <p className="text-2xl font-bold" style={{ color: state.brand.color_primary, textShadow: `0 0 12px ${state.brand.color_primary}55` }}>
                {state.period.days_left}
              </p>
              <p className="text-[11px] opacity-50">días restantes</p>
            </div>
          )}
        </header>

        <main className="relative z-[1] flex-1 px-5 pb-28 pt-2">
          {tab === "entreno" && <PortalWorkout api={apiClient} brand={state.brand} />}
          {tab === "diario" && <PortalDiary api={apiClient} brand={state.brand} />}
          {tab === "cierre" && (
            <PortalClose
              api={apiClient}
              brand={state.brand}
              onClosed={reload}
              canClose={canClose}
              daysLeft={state.period?.days_left ?? null}
              closeDate={state.period?.ends_on ?? null}
            />
          )}
        </main>

        {/* Navegación inferior: 3 pestañas, relieve + neón */}
        <nav className="portal-nav fixed inset-x-0 bottom-0 z-40 mx-auto flex max-w-md justify-around px-2 py-2"
          style={{ backdropFilter: "blur(12px)" }}>
          {visibleTabs.map(({ id, label, icon: Icon }) => {
            const active = tab === id;
            const alert = id === "cierre" && canClose;  // "!" el día que ya se puede rellenar
            return (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={`relative flex flex-1 flex-col items-center gap-0.5 rounded-xl py-1.5 transition-colors ${active ? "nav-active" : ""}`}
                style={{ color: active ? undefined : "#9a8f7d" }}
              >
                <span className="nav-ico p-1"><Icon size={20} /></span>
                <span className="text-[10px] font-medium">{label}</span>
                {alert && <span className="portal-tab-badge">!</span>}
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
  document.documentElement.style.setProperty("--brand-accent-2", s.brand.color_secondary);
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


===== FILE: frontend/src/portal/PortalClose.tsx =====

import { useState } from "react";
import { Check, MessageCircle } from "lucide-react";
import type { PortalBrand } from "../types";
import { usePortalToast } from "./PortalToast";
import type { portalApi } from "./portalApi";

type Api = ReturnType<typeof portalApi>;

// Sección 2 de la revisión quincenal: sensaciones (1 muy mal → 5 excelente)
const FEELINGS: { key: string; label: string }[] = [
  { key: "energia", label: "Energía en el entreno" },
  { key: "hambre", label: "Hambre / saciedad" },
  { key: "sueno", label: "Calidad del sueño" },
  { key: "recuperacion", label: "Recuperación muscular" },
  { key: "animo", label: "Ánimo / estado general" },
  { key: "digestiones", label: "Digestiones" },
];

/**
 * REVISIÓN QUINCENAL (cierre de período, desde el día 14). Réplica del documento
 * del coach: medidas, sensaciones (1-5), adherencia (0-10), comidas libres,
 * cambios, qué cuesta, objetivo. Al enviar dispara el feedback de adaptación IA.
 * Las fotos de progreso se envían por WhatsApp (no se suben aquí).
 */
export function PortalClose({ api, brand, onClosed, canClose, daysLeft, closeDate }: {
  api: Api; brand: PortalBrand; onClosed: () => void; canClose: boolean;
  daysLeft: number | null; closeDate: string | null;
}) {
  const fechaCae = closeDate
    ? new Date(closeDate + "T00:00:00").toLocaleDateString("es-ES", { day: "2-digit", month: "long" })
    : null;
  const toast = usePortalToast();
  const [weight, setWeight] = useState("");
  const [waist, setWaist] = useState("");
  const [hip, setHip] = useState("");
  const [arm, setArm] = useState("");
  const [thigh, setThigh] = useState("");
  const [feelings, setFeelings] = useState<Record<string, number>>({});
  const [adhDiet, setAdhDiet] = useState("");
  const [adhTrain, setAdhTrain] = useState("");
  const [freeMeals, setFreeMeals] = useState("");
  const [changes, setChanges] = useState("");
  const [hardest, setHardest] = useState("");
  const [nextGoal, setNextGoal] = useState("");
  const [questions, setQuestions] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const allFeelings = FEELINGS.every((f) => feelings[f.key] > 0);
  const canSubmit = Number(weight) > 30 && allFeelings && adhDiet !== "" && adhTrain !== "" && !busy;

  async function submit() {
    if (!canSubmit) return;
    setBusy(true);
    try {
      const vals = FEELINGS.map((f) => feelings[f.key]);
      const avg = Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
      await api.close({
        closing_weight_kg: Number(weight),
        closing_rating: avg,
        closing_hardest: hardest || null,
        closing_questions: questions || null,
        closing_waist_cm: waist ? Number(waist) : null,
        closing_hip_cm: hip ? Number(hip) : null,
        closing_arm_cm: arm ? Number(arm) : null,
        closing_thigh_cm: thigh ? Number(thigh) : null,
        closing_feelings_json: feelings,
        adherence_diet_0_10: adhDiet === "" ? null : Number(adhDiet),
        adherence_training_0_10: adhTrain === "" ? null : Number(adhTrain),
        free_meals_count: freeMeals === "" ? null : Number(freeMeals),
        closing_changes: changes || null,
        closing_next_goal: nextGoal || null,
      });
      setDone(true);
      toast.push("Revisión enviada");
      setTimeout(onClosed, 1600);
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo enviar");
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="flex flex-col items-center py-20 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full" style={{ background: `${brand.color_primary}2a` }}>
          <Check size={32} style={{ color: brand.color_primary }} />
        </div>
        <p className="mt-4 text-lg font-semibold">¡Revisión enviada!</p>
        <p className="mt-1 max-w-xs text-sm opacity-60">
          Tu coach analizará tus datos y te enviará el informe con el plan actualizado.
        </p>
      </div>
    );
  }

  // Bloqueada hasta el día 15: contador de días restantes.
  if (!canClose) {
    return (
      <div className="flex flex-col items-center py-16 text-center">
        <div className="portal-neon-wine flex h-24 w-24 items-center justify-center rounded-full border-2"
          style={{ borderColor: brand.color_primary, color: brand.color_primary }}>
          <span className="text-4xl font-bold">{daysLeft != null && daysLeft > 0 ? daysLeft : "—"}</span>
        </div>
        <p className="mt-4 text-lg font-semibold">Revisión quincenal</p>
        <p className="mt-1 max-w-xs text-sm opacity-70">
          {daysLeft != null && daysLeft > 0
            ? `Podrás rellenarla en ${daysLeft} día${daysLeft === 1 ? "" : "s"}.`
            : "Se desbloquea al completar tus 2 semanas."}
        </p>
        {fechaCae && (
          <p className="mt-1 text-sm font-semibold" style={{ color: brand.color_primary }}>
            Se activa el {fechaCae}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Revisión quincenal</h2>
        <p className="mt-1 text-sm opacity-60">Rellénala al terminar tus 2 semanas. Prepara tu próximo plan.</p>
      </div>

      {/* 1 · Medidas */}
      <Section n={1} title="Medidas corporales">
        <p className="mb-2 text-xs opacity-50">Mide por la mañana en ayunas, cinta blanda sin apretar.</p>
        <Field label="Peso (kg)" required>
          <input type="number" step={0.1} inputMode="decimal"
            className="w-full rounded-xl border bg-transparent p-3 text-lg font-semibold"
            style={{ borderColor: "rgba(128,128,128,0.2)" }}
            value={weight} onChange={(e) => setWeight(e.target.value)} placeholder="—" />
        </Field>
        <div className="mt-3 grid grid-cols-2 gap-3">
          <Perimeter label="Cintura" value={waist} onChange={setWaist} />
          <Perimeter label="Cadera" value={hip} onChange={setHip} />
          <Perimeter label="Brazo" value={arm} onChange={setArm} />
          <Perimeter label="Muslo" value={thigh} onChange={setThigh} />
        </div>
      </Section>

      {/* 2 · Sensaciones */}
      <Section n={2} title="¿Cómo te has sentido estas 2 semanas?">
        <p className="mb-2 text-xs opacity-50">1 = muy mal · 5 = excelente</p>
        <div className="space-y-3">
          {FEELINGS.map((f) => (
            <div key={f.key}>
              <p className="mb-1.5 text-sm">{f.label}</p>
              <div className="flex justify-between gap-1.5">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button key={n} onClick={() => setFeelings((s) => ({ ...s, [f.key]: n }))}
                    className="flex-1 rounded-lg border py-2 text-sm font-semibold"
                    style={feelings[f.key] === n
                      ? { borderColor: brand.color_primary, background: `${brand.color_primary}1f`, color: brand.color_primary }
                      : { borderColor: "rgba(128,128,128,0.2)" }}>
                    {n}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* 3 · Adherencia */}
      <Section n={3} title="Adherencia al plan">
        <div className="grid grid-cols-2 gap-3">
          <NumField label="Dieta (0-10)" value={adhDiet} onChange={setAdhDiet} min={0} max={10} required />
          <NumField label="Entreno (0-10)" value={adhTrain} onChange={setAdhTrain} min={0} max={10} required />
        </div>
        <div className="mt-3">
          <NumField label="Comidas libres o saltadas (nº aprox.)" value={freeMeals} onChange={setFreeMeals} min={0} max={50} />
        </div>
      </Section>

      {/* 4 · Cambios */}
      <Section n={4} title="¿Algún cambio importante?">
        <textarea className="min-h-[64px] w-full rounded-xl border bg-transparent p-3 text-sm" style={{ borderColor: "rgba(128,128,128,0.2)" }}
          value={changes} onChange={(e) => setChanges(e.target.value)}
          placeholder="Lesiones, dolores, cambios de horario, viajes, estrés, sueño irregular…" />
      </Section>

      {/* 5 · Qué cuesta */}
      <Section n={5} title="¿Qué te está costando más?">
        <textarea className="min-h-[64px] w-full rounded-xl border bg-transparent p-3 text-sm" style={{ borderColor: "rgba(128,128,128,0.2)" }}
          value={hardest} onChange={(e) => setHardest(e.target.value)}
          placeholder="Comidas difíciles, ejercicios que no te convencen, momentos complicados…" />
      </Section>

      {/* 6 · Objetivo */}
      <Section n={6} title="Tu objetivo para las próximas 2 semanas">
        <textarea className="min-h-[56px] w-full rounded-xl border bg-transparent p-3 text-sm" style={{ borderColor: "rgba(128,128,128,0.2)" }}
          value={nextGoal} onChange={(e) => setNextGoal(e.target.value)}
          placeholder='Algo concreto: "bajar 0,5 kg", "dormir 7 h", "mejorar técnica de sentadilla"…' />
      </Section>

      {/* 7 · Fotos (WhatsApp) */}
      <Section n={7} title="Fotos de progreso">
        <div className="flex items-start gap-2 rounded-xl border p-3 text-sm" style={{ borderColor: `${brand.color_primary}55`, background: `${brand.color_primary}10` }}>
          <MessageCircle size={18} style={{ color: brand.color_primary }} className="mt-0.5 shrink-0" />
          <p className="opacity-80">
            Envía 3 fotos (<b>frontal</b>, <b>lateral</b> y <b>espalda</b>) a tu coach por <b>WhatsApp</b>.
            Fondo neutro, buena luz, misma hora y lugar que la vez anterior, sin filtros.
          </p>
        </div>
      </Section>

      <Field label="Dudas para tu coach (opcional)">
        <textarea className="min-h-[56px] w-full rounded-xl border bg-transparent p-3 text-sm" style={{ borderColor: "rgba(128,128,128,0.2)" }}
          value={questions} onChange={(e) => setQuestions(e.target.value)} placeholder="Cualquier pregunta…" />
      </Field>

      <button onClick={submit} disabled={!canSubmit} className="portal-btn3d w-full py-4 text-sm uppercase tracking-wide">
        {busy ? "Enviando…" : "Enviar revisión a mi coach"}
      </button>
      {!canSubmit && !busy && (
        <p className="text-center text-xs opacity-40">Completa peso, las 6 sensaciones y la adherencia.</p>
      )}
    </div>
  );
}

function Section({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-2 text-sm font-semibold">
        <span className="opacity-40">{n}.</span> {title}
      </p>
      {children}
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
      <input type="number" step={0.5} inputMode="decimal"
        className="mt-1 w-full bg-transparent text-lg font-semibold outline-none"
        value={value} onChange={(e) => onChange(e.target.value)} placeholder="—" />
    </div>
  );
}

function NumField({ label, value, onChange, min, max, required }: {
  label: string; value: string; onChange: (v: string) => void; min: number; max: number; required?: boolean;
}) {
  return (
    <div className="rounded-xl border p-3" style={{ borderColor: "rgba(128,128,128,0.2)" }}>
      <p className="text-xs opacity-50">{label} {required && <span style={{ color: "#F77E7E" }}>*</span>}</p>
      <input type="number" step={1} min={min} max={max} inputMode="numeric"
        className="mt-1 w-full bg-transparent text-lg font-semibold outline-none"
        value={value} onChange={(e) => onChange(e.target.value)} placeholder="—" />
    </div>
  );
}


===== FILE: frontend/src/portal/PortalDiary.tsx =====

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
  steps: string;
  satiety_1_10: number | null;
  water_liters: number | null;
  diet_adherence: DietAdherence | null;
  energy_1_5: number | null;
  mood_1_5: number | null;
  fatigue_1_5: number | null;
  free_notes: string;
}

const EMPTY: DiaryForm = {
  weight_kg: null, sleep_hours: null, steps: "", satiety_1_10: null, water_liters: null,
  diet_adherence: null, energy_1_5: null, mood_1_5: null, fatigue_1_5: null, free_notes: "",
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
          steps: d.steps ?? "", satiety_1_10: d.satiety_1_10, water_liters: d.water_liters,
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
        <NumberCard label="Saciedad (1-10)" unit="" value={form.satiety_1_10} step={0.5}
          onChange={(v) => update({ satiety_1_10: v })} accent={brand.color_primary} />
        <NumberCard label="Agua" unit="L" value={form.water_liters} step={0.5}
          onChange={(v) => update({ water_liters: v })} accent={brand.color_primary} />
      </div>

      <Field label="Pasos / cardio del día">
        <input
          type="text"
          className="w-full rounded-xl border bg-transparent p-3 text-sm"
          style={{ borderColor: "rgba(128,128,128,0.2)" }}
          placeholder="Ej.: 8000 pasos + 30' cardio"
          value={form.steps}
          onChange={(e) => update({ steps: e.target.value })}
        />
      </Field>

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


===== FILE: frontend/src/portal/PortalFeedback.tsx =====

import { useEffect, useState } from "react";
import { LineChart, TrendingDown, Target, Sparkles, MessageSquare } from "lucide-react";
import type { FeedbackDocOut, PortalBrand } from "../types";
import { Empty, Loading } from "./PortalToday";
import type { portalApi } from "./portalApi";

type Api = ReturnType<typeof portalApi>;

/**
 * Tu progreso: informes ENVIADOS por el coach, en formato visual y por puntos:
 * cifras clave + gráfica de peso + análisis breve + cambios y objetivos.
 */
export function PortalFeedback({ api, brand }: { api: Api; brand: PortalBrand }) {
  const [docs, setDocs] = useState<FeedbackDocOut[] | null>(null);
  const accent = brand.color_primary;

  useEffect(() => {
    api.feedback().then(setDocs).catch(() => setDocs([]));
  }, [api]);

  if (docs === null) return <Loading />;
  if (docs.length === 0) {
    return (
      <Empty
        icon={LineChart}
        title="Aún no hay informes"
        hint="Cuando tu coach te envíe tu informe, aquí verás tu progreso con cifras, gráfica y objetivos."
      />
    );
  }

  return (
    <div className="space-y-5">
      <h2 className="text-lg font-semibold">Tu progreso</h2>
      {docs.map((d) => {
        const c = (d.content_json ?? {}) as any;
        const w = c.metrics?.weight ?? {};
        const adh = c.metrics?.adherence ?? {};
        const dietPct = adh.diet_adherence_ratio != null ? Math.round(adh.diet_adherence_ratio * 100) : null;
        const points: [string, number][] = Array.isArray(c.weight_points) ? c.weight_points : [];
        return (
          <div key={d.id} className="space-y-4 rounded-2xl border p-4" style={cardStyle}>
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold">{d.kind === "monthly" ? "Informe mensual" : "Informe quincenal"}</p>
              <span className="text-xs opacity-50">
                {d.sent_at ? new Date(d.sent_at).toLocaleDateString("es-ES", { day: "numeric", month: "long" }) : ""}
              </span>
            </div>

            {/* Cifras clave (grandes, con color) */}
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-xl border p-3" style={{ borderColor: "rgba(128,128,128,0.18)" }}>
                <div className="flex items-center gap-1.5 text-xs opacity-50"><TrendingDown size={13} style={{ color: accent }} /> Cambio de peso</div>
                <div className="mt-1 text-2xl font-bold" style={{ color: accent }}>
                  {w.delta_kg != null ? `${w.delta_kg > 0 ? "+" : ""}${w.delta_kg} kg` : "—"}
                </div>
                {w.weekly_rate_kg != null && <div className="text-xs opacity-50">{w.weekly_rate_kg} kg/semana</div>}
              </div>
              <div className="rounded-xl border p-3" style={{ borderColor: "rgba(128,128,128,0.18)" }}>
                <div className="flex items-center gap-1.5 text-xs opacity-50"><Sparkles size={13} style={{ color: accent }} /> Adherencia dieta</div>
                <div className="mt-1 text-2xl font-bold" style={{ color: accent }}>{dietPct != null ? `${dietPct}%` : "—"}</div>
                {dietPct != null && (
                  <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full" style={{ background: "rgba(128,128,128,0.2)" }}>
                    <div className="h-full rounded-full" style={{ width: `${dietPct}%`, background: accent }} />
                  </div>
                )}
              </div>
            </div>

            {/* Gráfica de peso */}
            {points.length >= 2 && <WeightChart points={points} goal={c.goal_weight_kg ?? null} accent={accent} />}

            {/* Análisis (breve) */}
            {c.natural_analysis && <p className="text-sm opacity-90">{c.natural_analysis}</p>}

            {/* Cambios en el plan */}
            {Array.isArray(c.changes_bullets) && c.changes_bullets.length > 0 && (
              <Section icon={Sparkles} title="Cambios en tu plan" accent={accent} items={c.changes_bullets} />
            )}

            {/* Respuesta a dudas */}
            {c.answers && (
              <div>
                <Head icon={MessageSquare} title="Respuesta a tus dudas" accent={accent} />
                <p className="text-sm opacity-90">{c.answers}</p>
              </div>
            )}

            {/* Objetivos */}
            {Array.isArray(c.next_objectives) && c.next_objectives.length > 0 && (
              <Section icon={Target} title="Tus objetivos" accent={accent} items={c.next_objectives} />
            )}

            {c.closing_message && <p className="text-sm font-medium italic" style={{ color: accent }}>{c.closing_message}</p>}
          </div>
        );
      })}
    </div>
  );
}

function Head({ icon: Icon, title, accent }: { icon: typeof Target; title: string; accent: string }) {
  return (
    <p className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide opacity-60">
      <Icon size={13} style={{ color: accent }} /> {title}
    </p>
  );
}

function Section({ icon, title, accent, items }: { icon: typeof Target; title: string; accent: string; items: string[] }) {
  return (
    <div>
      <Head icon={icon} title={title} accent={accent} />
      <ul className="list-disc space-y-0.5 pl-5 text-sm opacity-90">
        {items.map((it, i) => <li key={i}>{it}</li>)}
      </ul>
    </div>
  );
}

function WeightChart({ points, goal, accent }: { points: [string, number][]; goal: number | null; accent: string }) {
  const vals = points.map((p) => p[1]);
  const w = 300, h = 90, pad = 10;
  const lo = Math.min(...vals, goal ?? Infinity);
  const hi = Math.max(...vals, goal ?? -Infinity);
  const range = hi - lo || 1;
  const x = (i: number) => pad + (i / (points.length - 1)) * (w - 2 * pad);
  const y = (v: number) => pad + (1 - (v - lo) / range) * (h - 2 * pad);
  const line = points.map((p, i) => `${x(i)},${y(p[1])}`).join(" ");
  const last = points[points.length - 1];
  return (
    <div>
      <Head icon={TrendingDown} title="Evolución de tu peso" accent={accent} />
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ maxHeight: 110 }} preserveAspectRatio="none">
        {goal != null && (
          <line x1={pad} y1={y(goal)} x2={w - pad} y2={y(goal)} stroke={accent} strokeWidth="1" strokeDasharray="4 4" opacity="0.4" />
        )}
        <polyline points={line} fill="none" stroke={accent} strokeWidth="2.5" />
        <circle cx={x(points.length - 1)} cy={y(last[1])} r="3.5" fill={accent} />
      </svg>
      <div className="flex justify-between text-xs opacity-50">
        <span>{points[0][0]}: {points[0][1]} kg</span>
        <span>{last[0]}: {last[1]} kg{goal != null ? ` · objetivo ${goal}` : ""}</span>
      </div>
    </div>
  );
}

const cardStyle = {
  background: "var(--portal-card, rgba(255,255,255,0.03))",
  borderColor: "rgba(128,128,128,0.18)",
} as const;


===== FILE: frontend/src/portal/PortalPlan.tsx =====

import { useEffect, useState } from "react";
import { ChevronDown, Salad, Dumbbell } from "lucide-react";
import type { PortalBrand, PortalPlanOut, TodaySession } from "../types";
import { Empty, Loading } from "./PortalToday";
import type { portalApi } from "./portalApi";

type Api = ReturnType<typeof portalApi>;

/** Plan completo navegable por secciones colapsables (G.4). */
export function PortalPlan({ api, brand }: { api: Api; brand: PortalBrand }) {
  const [plan, setPlan] = useState<PortalPlanOut | null>(null);
  const [sessions, setSessions] = useState<TodaySession[]>([]);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    api.plan().then(setPlan).catch(() => setMissing(true));
    api.training().then((t) => setSessions(t.sessions ?? [])).catch(() => setSessions([]));
  }, [api]);

  if (missing) return <Empty icon={Salad} title="Sin plan todavía" hint="Tu coach aún no ha publicado tu plan." />;
  if (!plan) return <Loading />;

  const nut = plan.nutrition;
  const tr = plan.training;

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
          <div className="mt-3 space-y-3">
            {(sessions.length ? sessions : tr.sessions).map((s: any, i: number) => (
              <div key={i} className="rounded-xl border p-3" style={{ borderColor: "rgba(128,128,128,0.18)" }}>
                <p className="text-sm font-semibold">{s.day} · {s.name}</p>
                <ul className="mt-2 space-y-1.5 text-xs">
                  {s.exercises.map((e: any, j: number) => (
                    <li key={j} className="flex items-baseline justify-between gap-2">
                      <span className="opacity-90">{e.name ?? `Ejercicio #${e.exercise_id}`}</span>
                      <span className="shrink-0 opacity-55">{e.sets}×{e.rep_range} · RIR {e.rir}</span>
                    </li>
                  ))}
                </ul>
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


===== FILE: frontend/src/portal/PortalToast.tsx =====

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


===== FILE: frontend/src/portal/PortalToday.tsx =====

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


===== FILE: frontend/src/portal/PortalWorkout.tsx =====

import { useEffect, useRef, useState } from "react";
import { Dumbbell, Plus, Trash2, PlayCircle, Check } from "lucide-react";
import type { PortalBrand, TodaySession } from "../types";
import { usePortalToast } from "./PortalToast";
import { Loading, Empty } from "./PortalToday";
import type { portalApi } from "./portalApi";

type Api = ReturnType<typeof portalApi>;
interface SetRow { weight_kg: number | null; reps: number | null }
interface HistSet { set: number; weight_kg: number | null; reps: number | null }
interface HistSession { date: string; sets: HistSet[] }

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
  const [history, setHistory] = useState<Record<string, HistSession[]>>({});
  const saveTimer = useRef<number | null>(null);

  useEffect(() => {
    Promise.all([api.training(), api.today(), api.getDiary(today), api.workoutHistory()]).then(([tr, t, diary, hist]) => {
      const ss = tr.sessions ?? [];
      setSessions(ss);
      setHistory(hist.history ?? {});
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
              <div key={ex.exercise_id} className="portal-card p-4">
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
                {history[String(ex.exercise_id)]?.length ? (
                  <ExHistory sessions={history[String(ex.exercise_id)]} accent={brand.color_primary} />
                ) : null}
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

function ExHistory({ sessions, accent }: { sessions: HistSession[]; accent: string }) {
  const [open, setOpen] = useState(false);
  const fmt = (s: HistSet) => `${s.weight_kg ?? "—"}×${s.reps ?? "—"}`;
  const last = sessions[0];
  return (
    <div className="mt-2 border-t pt-2 text-xs" style={{ borderColor: "rgba(128,128,128,0.15)" }}>
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center justify-between opacity-70">
        <span className="truncate">Última vez: {last.sets.map(fmt).join(" · ")}</span>
        <span className="ml-2 shrink-0" style={{ color: accent }}>{open ? "▾" : "▸"} historial</span>
      </button>
      {open && (
        <div className="mt-1.5 space-y-1">
          {sessions.map((s) => (
            <div key={s.date} className="flex justify-between opacity-60">
              <span>{s.date}</span>
              <span>{s.sets.map(fmt).join(" · ")}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const cardStyle = {
  background: "var(--portal-card, rgba(255,255,255,0.03))",
  borderColor: "rgba(128,128,128,0.18)",
} as const;


===== FILE: frontend/src/portal/portalApi.ts =====

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
    workoutHistory: () =>
      req<{ history: Record<string, { date: string; sets: { set: number; weight_kg: number | null; reps: number | null }[] }[]> }>(
        "GET", `${base}/workout-history`,
      ),
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


===== FILE: frontend/src/types.ts =====

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
  pending_review?: boolean;
  pending_review_period?: number | null;
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
  steps?: string | null;
  satiety_1_10?: number | null;
  water_liters?: number | null;
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
  closing_rating?: number | null;
  closing_hardest?: string | null;
  closing_questions?: string | null;
  closing_waist_cm?: number | null;
  closing_hip_cm?: number | null;
  closing_arm_cm?: number | null;
  closing_thigh_cm?: number | null;
  closing_feelings_json?: Record<string, number> | null;
  adherence_diet_0_10?: number | null;
  adherence_training_0_10?: number | null;
  free_meals_count?: number | null;
  closing_changes?: string | null;
  closing_next_goal?: string | null;
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


===== FILE: frontend/src/index.css =====

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

/* ================= PORTAL DEL CLIENTE — crema + neón + 3D ================= */
.portal-root {
  --p-cream: #f5f0e8;
  --p-cream-2: #efe6d6;
  --p-ink: #2b2118;          /* texto cálido oscuro */
  --p-ink-soft: #6b5f4f;
  --p-wine: var(--brand-accent, #8b1a2b);
  --p-blue: var(--brand-accent-2, #4a7ba8);
  --p-line: rgba(43, 33, 24, 0.12);
  background:
    radial-gradient(120% 55% at 50% -8%, rgba(74, 123, 168, 0.12), transparent 60%),
    radial-gradient(120% 55% at 50% 108%, rgba(139, 26, 43, 0.10), transparent 60%),
    var(--p-cream) !important;
  color: var(--p-ink) !important;
}
/* textura sutil de papel */
.portal-root::before {
  content: "";
  position: fixed; inset: 0; pointer-events: none; z-index: 0; opacity: 0.5;
  background-image: radial-gradient(rgba(43, 33, 24, 0.04) 1px, transparent 1px);
  background-size: 22px 22px;
}
.portal-root .opacity-60, .portal-root .opacity-50, .portal-root .opacity-40 { color: var(--p-ink-soft); }

/* Botón 3D con textura y neón de marca */
.portal-btn3d {
  position: relative;
  border-radius: 14px;
  background: linear-gradient(180deg, var(--p-wine) 0%, #6d1422 100%);
  color: #fff; font-weight: 700; border: none;
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.35) inset,
    0 -2px 0 rgba(0, 0, 0, 0.28) inset,
    0 6px 16px rgba(139, 26, 43, 0.38),
    0 0 0 1px rgba(139, 26, 43, 0.4),
    0 0 18px rgba(139, 26, 43, 0.22);
  transition: transform 0.12s ease, box-shadow 0.2s ease, filter 0.2s ease;
}
.portal-btn3d:hover { filter: brightness(1.06); }
.portal-btn3d:active {
  transform: translateY(2px);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.2) inset, 0 2px 6px rgba(139, 26, 43, 0.3);
}
.portal-btn3d:disabled { filter: grayscale(0.4) opacity(0.55); }

/* Tarjeta con relieve suave sobre crema */
.portal-card {
  background: linear-gradient(180deg, #ffffff, var(--p-cream-2));
  border: 1px solid var(--p-line);
  border-radius: 16px;
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.7) inset, 0 6px 18px rgba(43, 33, 24, 0.07);
}
/* Neón de detalle (marca) */
.portal-neon-wine { box-shadow: 0 0 0 1px rgba(139, 26, 43, 0.55), 0 0 12px rgba(139, 26, 43, 0.5), 0 0 26px rgba(139, 26, 43, 0.25); }
.portal-neon-blue { box-shadow: 0 0 0 1px rgba(74, 123, 168, 0.55), 0 0 12px rgba(74, 123, 168, 0.5), 0 0 26px rgba(74, 123, 168, 0.25); }

/* Nav inferior con relieve */
.portal-nav {
  background: linear-gradient(180deg, #ffffff, var(--p-cream-2)) !important;
  border-top: 1px solid var(--p-line) !important;
  box-shadow: 0 -4px 18px rgba(43, 33, 24, 0.08);
}
.portal-nav .nav-active {
  color: var(--p-wine);
  text-shadow: 0 0 10px rgba(139, 26, 43, 0.35);
}
.portal-nav .nav-active .nav-ico {
  border-radius: 10px;
  box-shadow: 0 0 0 1px rgba(139, 26, 43, 0.35), 0 0 14px rgba(139, 26, 43, 0.35);
}
/* Badge "!" en pestaña */
.portal-tab-badge {
  position: absolute; top: -2px; right: 50%; transform: translateX(16px);
  min-width: 16px; height: 16px; padding: 0 4px;
  display: flex; align-items: center; justify-content: center;
  background: var(--p-wine); color: #fff;
  border-radius: 999px; font-size: 10px; font-weight: 800; line-height: 1;
  box-shadow: 0 0 10px rgba(139, 26, 43, 0.6);
}
@keyframes portal-badge-pop { 0% { transform: translateX(16px) scale(0); } 60% { transform: translateX(16px) scale(1.25); } 100% { transform: translateX(16px) scale(1); } }
.portal-tab-badge { animation: portal-badge-pop 0.4s cubic-bezier(0.16, 1, 0.3, 1); }


===== FILE: frontend/src/App.tsx =====

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


===== FILE: frontend/src/main.tsx =====

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
