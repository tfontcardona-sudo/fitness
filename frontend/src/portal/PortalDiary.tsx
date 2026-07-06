import { useEffect, useRef, useState } from "react";
import type { DietAdherence, PortalBrand } from "../types";
import { usePortalToast } from "./PortalToast";
import { Loading } from "./PortalUi";
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

      <Field label="Pasos / cardio del día" htmlFor="diary-steps">
        <input
          id="diary-steps"
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

      <Field label="Notas (opcional)" htmlFor="diary-notes">
        <textarea
          id="diary-notes"
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

/** Grupo con título. OJO: div, no <label> — algunos hijos son grupos de
 *  botones y un label activaría el primero al tocar el texto. Para campos de
 *  texto se pasa htmlFor y el título sí actúa de etiqueta real. */
function Field({ label, htmlFor, children }: { label: string; htmlFor?: string; children: React.ReactNode }) {
  return (
    <div role="group" aria-label={htmlFor ? undefined : label}>
      <label htmlFor={htmlFor} className="mb-2 block text-sm font-medium opacity-80">{label}</label>
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
    <label className="block rounded-2xl border p-4" style={{ borderColor: "rgba(128,128,128,0.2)" }}>
      <span className="block text-xs opacity-50">{label}</span>
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
    </label>
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
