import { useEffect, useRef, useState } from "react";
import { Dumbbell, Plus, Trash2, PlayCircle, Check, Sparkles, CalendarRange } from "lucide-react";
import type { PlanChanges, PortalBrand, TodaySession, TrainingWeek } from "../types";
import { usePortalToast } from "./PortalToast";
import { Loading, Empty, localToday } from "./PortalUi";
import { useDismiss } from "../lib/useDismiss";
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
  const today = localToday();
  const [sessions, setSessions] = useState<TodaySession[] | null>(null);
  const [planChanges, setPlanChanges] = useState<PlanChanges | null>(null);
  const [week, setWeek] = useState<TrainingWeek | null>(null);
  const [newsOpen, setNewsOpen] = useState(false);
  const newsRef = useRef<HTMLDetailsElement>(null);
  useDismiss(newsRef, () => setNewsOpen(false), newsOpen); // fuera/ESC → se cierra
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [todayDay, setTodayDay] = useState<string | null>(null);
  const [sets, setSets] = useState<Record<number, SetRow[]>>({});
  const [history, setHistory] = useState<Record<string, HistSession[]>>({});
  const saveTimer = useRef<number | null>(null);

  useEffect(() => {
    Promise.all([api.training(), api.today(), api.getDiary(today), api.workoutHistory()]).then(([tr, t, diary, hist]) => {
      const ss = tr.sessions ?? [];
      setSessions(ss);
      setPlanChanges(tr.plan_changes ?? null);
      setWeek(tr.week ?? null);
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

  // Guardado con debounce PERO sin pérdidas: lo pendiente se vuelca al instante
  // si el cliente sale de la app, bloquea el móvil o cambia de pestaña, y un
  // fallo de red AVISA (antes fallaba en silencio con "se guarda solo" puesto).
  const pendingRef = useRef<Record<number, SetRow[]> | null>(null);
  const saveNowRef = useRef<() => void>(() => {});
  saveNowRef.current = () => {
    const data = pendingRef.current;
    if (!data) return;
    pendingRef.current = null;
    if (saveTimer.current) window.clearTimeout(saveTimer.current);
    const workout_sets: any[] = [];
    Object.entries(data).forEach(([exId, rows]) => {
      rows.forEach((r, i) => {
        if (r.weight_kg != null || r.reps != null) {
          workout_sets.push({ exercise_id: Number(exId), set_number: i + 1, reps: r.reps, weight_kg: r.weight_kg });
        }
      });
    });
    api.saveDiary({ log_date: today, workout_sets })
      .then(() => toast.push("Entreno guardado"))
      .catch(() => toast.push("No se pudo guardar el último cambio — revisa tu conexión"));
  };

  function flush(next: Record<number, SetRow[]>) {
    pendingRef.current = next;
    if (saveTimer.current) window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(() => saveNowRef.current(), 800);
  }

  useEffect(() => {
    const onHide = () => {
      if (document.visibilityState === "hidden") saveNowRef.current();
    };
    document.addEventListener("visibilitychange", onHide);
    window.addEventListener("pagehide", onHide);
    return () => {
      document.removeEventListener("visibilitychange", onHide);
      window.removeEventListener("pagehide", onHide);
      saveNowRef.current(); // al cambiar de pestaña (desmontaje) no se pierde nada
    };
  }, []);

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

      {/* SEMANA del mesociclo: en qué fase estás, qué toca y POR QUÉ. Los pesos
          sugeridos de abajo ya vienen ajustados a esta semana. */}
      {week && (
        <div
          className="portal-card overflow-hidden border-l-4 p-3.5"
          style={{ borderLeftColor: brand.color_secondary }}
        >
          <div className="flex flex-wrap items-center gap-2 text-sm font-semibold">
            <CalendarRange size={16} style={{ color: brand.color_secondary }} />
            Semana {week.week} de {week.total_weeks}
            {week.intent && (
              <span
                className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white"
                style={{ background: brand.color_secondary }}
              >
                {week.intent}
              </span>
            )}
            <span className="ml-auto text-xs font-normal opacity-60">
              Carga {week.load_pct}%{week.rir_target ? ` · RIR ${week.rir_target}` : ""}
            </span>
          </div>
          <p className="mt-1.5 text-xs opacity-70">{week.why}</p>
          {week.load_factor !== 1 && (
            <p className="mt-1 text-[11px] opacity-50">
              Los pesos sugeridos de tus ejercicios ya están ajustados a esta semana.
            </p>
          )}
        </div>
      )}

      {/* Novedades del plan: qué cambió en la última revisión, dónde y por qué */}
      {planChanges?.items?.length ? (
        <details
          ref={newsRef}
          open={newsOpen}
          onToggle={(e) => setNewsOpen((e.target as HTMLDetailsElement).open)}
          className="portal-card overflow-hidden"
        >
          <summary className="tap flex cursor-pointer items-center gap-2 p-3.5 text-sm font-semibold">
            <Sparkles size={16} style={{ color: brand.color_primary }} />
            Novedades de tu plan
            <span
              className="ml-auto rounded-full px-2 py-0.5 text-[10px] font-bold text-white"
              style={{ background: brand.color_secondary }}
            >
              revisión #{planChanges.period_index}
            </span>
          </summary>
          <div className="space-y-2 px-3.5 pb-3.5">
            {planChanges.items.map((it, i) => (
              <div key={i} className="rounded-xl border p-2.5" style={{ borderColor: "rgba(128,128,128,0.18)" }}>
                <div className="flex flex-wrap items-center gap-1.5 text-xs font-semibold">
                  <span
                    className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white"
                    style={{ background: /entren/i.test(it.area) ? brand.color_secondary : brand.color_primary }}
                  >
                    {/entren/i.test(it.area) ? "Entreno" : /diet|nutri/i.test(it.area) ? "Dieta" : it.area}
                  </span>
                  {it.detail ?? it.change}
                </div>
                {it.reason && <p className="mt-1 text-xs opacity-70">{it.reason}</p>}
              </div>
            ))}
            <p className="pt-0.5 text-[11px] opacity-50">
              {[
                planChanges.items.some((it) => /diet|nutri/i.test(it.area)) && "Los cambios de dieta ya están en tu PDF actualizado",
                planChanges.items.some((it) => /entren/i.test(it.area)) && "los de entreno, aplicados en tus sesiones de aquí abajo",
              ].filter(Boolean).join("; ") || "Tu coach los ha dejado anotados en tu plan."}
              .
            </p>
          </div>
        </details>
      ) : null}

      {/* Selector de sesión */}
      <div className="flex flex-wrap gap-2">
        {sessions.map((s, i) => {
          const active = i === selectedIdx;
          const isToday = todayDay && s.day === todayDay;
          return (
            <button
              key={i}
              onClick={() => setSelectedIdx(i)}
              className="relative rounded-xl border px-3 py-2 text-left text-xs transition-colors"
              style={
                active
                  ? { borderColor: brand.color_primary, background: `${brand.color_primary}1f` }
                  : isToday
                    ? { borderColor: `${brand.color_secondary}88` } // azul: info "toca hoy"
                    : { borderColor: "rgba(128,128,128,0.22)" }
              }
            >
              <span className="block font-semibold">{s.name || `Sesión ${i + 1}`}</span>
              <span className="opacity-60">{s.day}</span>
              {isToday && <span className="portal-today-pill">HOY</span>}
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
                      {(ex.week_weight_hint_kg ?? ex.start_weight_hint_kg)
                        ? ` · ~${ex.week_weight_hint_kg ?? ex.start_weight_hint_kg} kg${
                            week && ex.week_weight_hint_kg != null && ex.week_weight_hint_kg !== ex.start_weight_hint_kg
                              ? ` (sem ${week.week})` : ""
                          }`
                        : ""}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {doneCount > 0 && (
                      <span className="flex items-center gap-1 text-xs" style={{ color: brand.color_primary }}>
                        <Check size={13} /> {doneCount}/{rows.length}
                      </span>
                    )}
                    {ex.video_url && (
                      <a
                        href={ex.video_url} target="_blank" rel="noreferrer"
                        aria-label={`Vídeo de ${ex.name}`}
                        className="tap flex items-center justify-center"
                        style={{ color: brand.color_secondary }}
                      >
                        <PlayCircle size={18} />
                      </a>
                    )}
                  </div>
                </div>

                <div className="mt-3 space-y-1.5">
                  <div className="grid grid-cols-[28px_1fr_1fr_40px] items-center gap-2 px-1 text-[10px] uppercase tracking-wide opacity-40">
                    <span>Set</span><span>Peso (kg)</span><span>Reps</span><span></span>
                  </div>
                  {rows.map((r, i) => {
                    const done = r.weight_kg != null && r.reps != null;
                    return (
                      <div key={i} className="grid grid-cols-[28px_1fr_1fr_40px] items-center gap-2">
                        <span className="text-center text-xs font-semibold tabular-nums" style={{ color: done ? brand.color_primary : undefined, opacity: done ? 1 : 0.5 }}>{i + 1}</span>
                        <SetInput value={r.weight_kg} step={0.5} placeholder={(ex.week_weight_hint_kg ?? ex.start_weight_hint_kg) ? String(ex.week_weight_hint_kg ?? ex.start_weight_hint_kg) : "—"} accent={brand.color_secondary} onChange={(v) => setRow(ex.exercise_id, i, { weight_kg: v })} />
                        <SetInput value={r.reps} step={1} placeholder="—" accent={brand.color_secondary} onChange={(v) => setRow(ex.exercise_id, i, { reps: v })} />
                        <button onClick={() => removeSet(ex.exercise_id, i)} aria-label={`Borrar serie ${i + 1}`} className="flex h-11 w-11 items-center justify-center justify-self-center rounded-lg opacity-40 hover:opacity-100"><Trash2 size={15} /></button>
                      </div>
                    );
                  })}
                  <button onClick={() => addSet(ex.exercise_id)} className="tap mt-1 flex w-full items-center justify-center gap-1 rounded-xl border border-dashed py-2 text-xs opacity-70" style={{ borderColor: "rgba(128,128,128,0.3)" }}>
                    <Plus size={13} /> Añadir serie
                  </button>
                </div>
                {history[String(ex.exercise_id)]?.length ? (
                  // Azul: el historial es consulta de datos, no acción
                  <ExHistory sessions={history[String(ex.exercise_id)]} accent={brand.color_secondary} />
                ) : null}
                {ex.technique_cue && <p className="mt-2 text-xs opacity-50">💡 {ex.technique_cue}</p>}
              </div>
            );
          })}
          {selected.cooldown && (
            <div className="portal-card p-4 text-xs opacity-60">
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
      className="min-h-[44px] w-full rounded-xl border bg-transparent px-3 py-2 text-center text-sm font-semibold outline-none"
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
      <button onClick={() => setOpen((o) => !o)} aria-expanded={open} className="flex min-h-[44px] w-full items-center justify-between opacity-70">
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

