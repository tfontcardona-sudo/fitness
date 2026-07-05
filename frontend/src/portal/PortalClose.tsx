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
        <div className="portal-neon-accent flex h-24 w-24 items-center justify-center rounded-full border-2"
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
