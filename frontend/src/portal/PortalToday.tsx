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
