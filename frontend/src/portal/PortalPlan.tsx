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
