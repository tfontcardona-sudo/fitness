import { useState } from "react";
import { Camera, Ruler, Save } from "lucide-react";
import type { PortalBrand } from "../types";
import { useDecimalField } from "./PortalUi";
import { usePortalToast } from "./PortalToast";
import type { portalApi } from "./portalApi";

type Api = ReturnType<typeof portalApi>;

/**
 * EVOLUCIÓN — la pantalla del seguimiento continuo.
 *
 * El cliente actualiza su cuerpo cuando le toca medirse: peso, perímetros y
 * cómo se encuentra. No cierra nada ni hay cuenta atrás; con esto el informe
 * del coach se pone al día y las recomendaciones se afinan.
 *
 * Es TODO lo que ve quien solo ha contratado la dieta (junto con su diario):
 * su evolución corporal.
 */

const SENSACIONES: { key: string; label: string }[] = [
  { key: "energia", label: "Energía" },
  { key: "hambre", label: "Hambre" },
  { key: "sueno", label: "Descanso" },
  { key: "animo", label: "Ánimo" },
  { key: "digestiones", label: "Digestiones" },
];

export function PortalEvolution({ api, brand, onSaved, hasTraining = true }: {
  api: Api; brand: PortalBrand; onSaved?: () => void; hasTraining?: boolean;
}) {
  const toast = usePortalToast();
  const [peso, setPeso] = useState<number | null>(null);
  const [cintura, setCintura] = useState<number | null>(null);
  const [cadera, setCadera] = useState<number | null>(null);
  const [brazo, setBrazo] = useState<number | null>(null);
  const [muslo, setMuslo] = useState<number | null>(null);
  const [notas, setNotas] = useState("");
  const [sens, setSens] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);

  const num = (v: number | null): number | undefined => v ?? undefined;

  async function guardar() {
    if (busy) return;
    const body: Record<string, unknown> = {
      weight_kg: num(peso), waist_cm: num(cintura), hip_cm: num(cadera),
      arm_cm: num(brazo), thigh_cm: num(muslo),
      feelings_json: Object.keys(sens).length ? sens : undefined,
      notes: notas.trim() || undefined,
    };
    Object.keys(body).forEach((k) => body[k] === undefined && delete body[k]);
    if (Object.keys(body).length === 0) {
      toast.push("Rellena al menos una medida");
      return;
    }
    setBusy(true);
    try {
      await api.saveMeasurements(body);
      toast.push("Medidas guardadas. Tu coach las verá en tu informe.");
      onSaved?.();
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudieron guardar las medidas");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold">Tu evolución</h2>
        <p className="mt-0.5 text-xs opacity-60">
          Actualiza tus medidas cuando te peses (una vez por semana está bien).
          {hasTraining ? " Con esto y tus entrenos" : " Con esto y tu diario"} tu
          coach ajusta el plan.
        </p>
      </div>

      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <Ruler size={16} style={{ color: brand.color_secondary }} />
          <h3 className="text-sm font-semibold">Peso y perímetros</h3>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Campo label="Peso (kg)" value={peso} onChange={setPeso} min={30} max={300} />
          <Campo label="Cintura (cm)" value={cintura} onChange={setCintura} min={30} max={250} />
          <Campo label="Cadera (cm)" value={cadera} onChange={setCadera} min={30} max={250} />
          <Campo label="Brazo (cm)" value={brazo} onChange={setBrazo} min={10} max={80} />
          <Campo label="Muslo (cm)" value={muslo} onChange={setMuslo} min={20} max={120} />
        </div>
        <p className="text-[11px] opacity-45">
          Mídete siempre igual: en ayunas, sin ropa y con la cinta sin apretar.
        </p>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold">¿Cómo te encuentras?</h3>
        <div className="space-y-2">
          {SENSACIONES.map((s) => (
            <div key={s.key} className="portal-card flex items-center justify-between p-3">
              <span className="text-sm">{s.label}</span>
              <div className="flex gap-1.5">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button key={n} type="button"
                    onClick={() => setSens((prev) => ({ ...prev, [s.key]: n }))}
                    aria-label={`${s.label}: ${n} de 5`}
                    aria-pressed={sens[s.key] === n}
                    className="tap h-8 w-8 rounded-lg text-sm font-semibold"
                    style={sens[s.key] === n
                      ? { background: brand.color_primary, color: "#111" }
                      : { background: "rgba(127,127,127,0.14)" }}>
                    {n}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-2">
        <h3 className="text-sm font-semibold">¿Algo que contarle a tu coach?</h3>
        <textarea
          className="portal-card w-full bg-transparent p-3 text-sm outline-none"
          rows={3} maxLength={2000} value={notas}
          onChange={(e) => setNotas(e.target.value)}
          placeholder="Viajes, cambios de horario, molestias, lo que se te resiste…"
        />
      </section>

      <button type="button" onClick={guardar} disabled={busy}
        className="portal-btn3d w-full rounded-2xl px-4 py-3 text-sm font-semibold">
        <span className="flex items-center justify-center gap-2">
          <Save size={16} /> {busy ? "Guardando…" : "Guardar mis medidas"}
        </span>
      </button>

      <div className="portal-card flex items-start gap-2 p-3 text-xs opacity-70">
        <Camera size={15} className="mt-0.5 shrink-0" />
        <span>
          Si quieres, envía por email a tu coach 3 fotos (frontal, lateral y de
          espalda) con la misma luz y postura cada vez: es la mejor forma de ver
          los cambios que la báscula no cuenta.
        </span>
      </div>
    </div>
  );
}

/** Campo decimal a prueba de móvil (coma o punto; fuera de rango no viaja). */
function Campo({ label, value, onChange, min, max }: {
  label: string; value: number | null; onChange: (v: number | null) => void;
  min: number; max: number;
}) {
  const { invalid, inputProps } = useDecimalField(value, onChange, { min, max });
  return (
    <label className="portal-card block p-3">
      <span className="block text-xs opacity-50">{label}</span>
      <input {...inputProps} type="text" inputMode="decimal" placeholder="—"
        className="mt-1 w-full bg-transparent text-lg font-semibold outline-none"
        style={{ caretColor: "var(--p-accent-2)", color: invalid ? "#C2453A" : undefined }} />
    </label>
  );
}
