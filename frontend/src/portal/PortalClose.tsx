import { useEffect, useState } from "react";
import { Check, MessageCircle } from "lucide-react";
import type { PortalBrand } from "../types";
import { usePortalToast } from "./PortalToast";
import type { portalApi } from "./portalApi";

type Api = ReturnType<typeof portalApi>;

/** BORRADOR persistente de la revisión: es el formulario más largo del portal
 *  y el cliente puede salir a mirar su diario a mitad — nada debe perderse.
 *  Se guarda en el móvil (localStorage) por período y se limpia al enviar. */
const DRAFT_KEY = (closeDate: string | null) => `portal_close_draft_${closeDate ?? "actual"}`;

function loadDraft(closeDate: string | null): Record<string, any> {
  try {
    return JSON.parse(localStorage.getItem(DRAFT_KEY(closeDate)) ?? "{}");
  } catch {
    return {};
  }
}

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
export function PortalClose({ api, brand, onClosed, canClose, daysLeft, closeDate, periodStatus }: {
  api: Api; brand: PortalBrand; onClosed: () => void; canClose: boolean;
  daysLeft: number | null; closeDate: string | null; periodStatus?: string | null;
}) {
  const fechaCae = closeDate
    ? new Date(closeDate + "T00:00:00").toLocaleDateString("es-ES", { day: "2-digit", month: "long" })
    : null;
  const toast = usePortalToast();
  const draft = loadDraft(closeDate);
  const [weight, setWeight] = useState<string>(draft.weight ?? "");
  const [waist, setWaist] = useState<string>(draft.waist ?? "");
  const [hip, setHip] = useState<string>(draft.hip ?? "");
  const [arm, setArm] = useState<string>(draft.arm ?? "");
  const [thigh, setThigh] = useState<string>(draft.thigh ?? "");
  const [feelings, setFeelings] = useState<Record<string, number>>(draft.feelings ?? {});
  const [adhDiet, setAdhDiet] = useState<string>(draft.adhDiet ?? "");
  const [adhTrain, setAdhTrain] = useState<string>(draft.adhTrain ?? "");
  const [freeMeals, setFreeMeals] = useState<string>(draft.freeMeals ?? "");
  const [changes, setChanges] = useState<string>(draft.changes ?? "");
  const [hardest, setHardest] = useState<string>(draft.hardest ?? "");
  const [nextGoal, setNextGoal] = useState<string>(draft.nextGoal ?? "");
  const [questions, setQuestions] = useState<string>(draft.questions ?? "");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  // Si cambia el período con la pestaña montada (rollover), se recarga SU
  // borrador — sin volcar el del período anterior sobre la clave nueva.
  useEffect(() => {
    const d = loadDraft(closeDate);
    setWeight(d.weight ?? ""); setWaist(d.waist ?? ""); setHip(d.hip ?? "");
    setArm(d.arm ?? ""); setThigh(d.thigh ?? ""); setFeelings(d.feelings ?? {});
    setAdhDiet(d.adhDiet ?? ""); setAdhTrain(d.adhTrain ?? "");
    setFreeMeals(d.freeMeals ?? ""); setChanges(d.changes ?? "");
    setHardest(d.hardest ?? ""); setNextGoal(d.nextGoal ?? "");
    setQuestions(d.questions ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [closeDate]);

  // Cada cambio queda guardado en el móvil: volver a la pestaña lo restaura.
  useEffect(() => {
    if (done) return;
    try {
      localStorage.setItem(DRAFT_KEY(closeDate), JSON.stringify({
        weight, waist, hip, arm, thigh, feelings,
        adhDiet, adhTrain, freeMeals, changes, hardest, nextGoal, questions,
      }));
    } catch { /* almacenamiento lleno o bloqueado: seguimos sin borrador */ }
  }, [weight, waist, hip, arm, thigh, feelings, adhDiet, adhTrain, freeMeals,
      changes, hardest, nextGoal, questions, closeDate, done]);

  const allFeelings = FEELINGS.every((f) => feelings[f.key] > 0);
  // Validación de RANGOS en el móvil: si algo se sale (300 kg, 60 comidas
  // libres…), se avisa del campo concreto ANTES de enviar — el backend
  // rechazaría todo el cierre con un error genérico.
  const rangeError = (() => {
    const w = Number(weight);
    if (weight !== "" && (w <= 30 || w >= 300)) return "Revisa el peso final (kg reales)";
    const per = (v: string, name: string) =>
      v !== "" && (Number(v) < 20 || Number(v) > 250) ? `Revisa ${name} (cm reales)` : null;
    const perErr = per(waist, "la cintura") ?? per(hip, "la cadera") ?? per(arm, "el brazo") ?? per(thigh, "el muslo");
    if (perErr) return perErr;
    if (freeMeals !== "" && (Number(freeMeals) < 0 || Number(freeMeals) > 50))
      return "Revisa las comidas libres (0-50)";
    return null;
  })();
  const canSubmit = Number(weight) > 30 && allFeelings && adhDiet !== "" && adhTrain !== ""
    && !rangeError && !busy;

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
      try { localStorage.removeItem(DRAFT_KEY(closeDate)); } catch { /* sin borrador */ }
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

  // Ya enviada (el período dejó de estar "abierto"): NO mostrar la cuenta atrás
  // de "se desbloquea en 2 semanas", que contradecía al resto de pestañas ("en
  // pausa"). Estado propio de "revisión enviada".
  if (!canClose && periodStatus && periodStatus !== "open") {
    return (
      <div className="flex flex-col items-center py-20 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full" style={{ background: `${brand.color_primary}2a` }}>
          <Check size={32} style={{ color: brand.color_primary }} />
        </div>
        <p className="mt-4 text-lg font-semibold">Revisión enviada</p>
        <p className="mt-1 max-w-xs text-sm opacity-60">
          Tu coach está analizando tus datos. Te avisará con tu informe y el plan actualizado.
        </p>
      </div>
    );
  }

  // Bloqueada hasta el día 15: contador de días restantes.
  // Azul de marca: es información del ciclo (cuenta atrás), no una acción.
  if (!canClose) {
    return (
      <div className="flex flex-col items-center py-16 text-center">
        <div className="portal-neon-blue flex h-24 w-24 items-center justify-center rounded-full border-2"
          style={{ borderColor: brand.color_secondary, color: brand.color_secondary }}>
          <span className="text-4xl font-bold">{daysLeft != null && daysLeft > 0 ? daysLeft : "—"}</span>
        </div>
        <p className="mt-4 text-lg font-semibold">Revisión quincenal</p>
        <p className="mt-1 max-w-xs text-sm opacity-70">
          {daysLeft != null && daysLeft > 0
            ? `Podrás rellenarla en ${daysLeft} día${daysLeft === 1 ? "" : "s"}.`
            : "Se desbloquea al completar tus 2 semanas."}
        </p>
        {fechaCae && (
          <p className="mt-1 text-sm font-semibold" style={{ color: brand.color_secondary }}>
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
        <p className="mt-0.5 text-xs opacity-60">
          Rellénala al terminar tus 2 semanas. Prepara tu próximo plan — lo que escribas se guarda en tu móvil.
        </p>
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
                    className="tap flex-1 rounded-lg border py-2 text-sm font-semibold"
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

      {/* 7 · Fotos (WhatsApp) — banner informativo en azul de marca */}
      <Section n={7} title="Fotos de progreso">
        <div className="flex items-start gap-2 rounded-xl border p-3 text-sm" style={{ borderColor: `${brand.color_secondary}55`, background: `${brand.color_secondary}10` }}>
          <MessageCircle size={18} style={{ color: brand.color_secondary }} className="mt-0.5 shrink-0" />
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
        <p className="text-center text-xs opacity-40">
          {rangeError ?? "Completa peso, las 6 sensaciones y la adherencia."}
        </p>
      )}
    </div>
  );
}

function Section({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-2 flex items-center gap-2 text-sm font-semibold">
        {/* Número de sección en azul de marca: guía la estructura del formulario */}
        <span
          className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-white"
          style={{ background: "var(--p-accent-2)" }}
        >
          {n}
        </span>
        {title}
      </p>
      {children}
    </div>
  );
}

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-2 text-sm font-medium opacity-80">
        {label} {required && <span style={{ color: "#C2453A" }}>*</span>}
      </p>
      {children}
    </div>
  );
}

function Perimeter({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="portal-card block p-3">
      <span className="block text-xs opacity-50">{label} (cm)</span>
      <input type="number" step={0.5} inputMode="decimal"
        className="mt-1 w-full bg-transparent text-lg font-semibold outline-none"
        style={{ caretColor: "var(--p-accent-2)" }}
        value={value} onChange={(e) => onChange(e.target.value)} placeholder="—" />
    </label>
  );
}

function NumField({ label, value, onChange, min, max, required }: {
  label: string; value: string; onChange: (v: string) => void; min: number; max: number; required?: boolean;
}) {
  return (
    <label className="portal-card block p-3">
      <span className="block text-xs opacity-50">{label} {required && <span style={{ color: "#C2453A" }}>*</span>}</span>
      <input type="number" step={1} min={min} max={max} inputMode="numeric"
        className="mt-1 w-full bg-transparent text-lg font-semibold outline-none"
        style={{ caretColor: "var(--p-accent-2)" }}
        value={value} onChange={(e) => onChange(e.target.value)} placeholder="—" />
    </label>
  );
}
