import { useEffect, useRef, useState } from "react";
import { Play, Check, Lightbulb, Sparkles, CalendarRange, Timer, X } from "lucide-react";
import type { PlanChanges, PortalBrand, TodaySession, TrainingWeek } from "../types";
import { usePortalToast } from "./PortalToast";
import { fmt1, Loading, localToday, shortDate, useDecimalField } from "./PortalUi";
import { InlineVideo, isEmbeddable } from "./InlineVideo";
import { useDismiss } from "../lib/useDismiss";
import { PortalError } from "./portalApi";
import type { portalApi } from "./portalApi";

type Api = ReturnType<typeof portalApi>;
interface SetRow { weight_kg: number | null; reps: number | null }
interface HistSet { set: number; weight_kg: number | null; reps: number | null }
interface HistSession { date: string; sets: HistSet[] }
interface ExRecord { e1rm_kg: number; weight_kg: number; reps: number; date: string }

/**
 * Entreno: el cliente registra SU rutina — series con peso y reps por ejercicio.
 * Estilo de tracker. Puede elegir QUÉ sesión ha hecho (selector), no solo la de
 * hoy. Todo se guarda solo en el backend (workout_sets) y el coach lo ve al
 * instante. Las series se conservan aunque cambie de sesión o guarde el diario.
 */
/* ---- Lo que tiene que sobrevivir a cambiar de pestaña -------------------
   PortalApp remonta el contenido al cambiar de pestaña, así que cualquier
   cosa viva en el estado de esta pantalla MUERE ahí. Estas dos cosas no
   pueden morir: una serie que no llegó a guardarse y un descanso en marcha.
   `sessionStorage`: sobreviven a la navegación pero no a cerrar la app días
   después (un descanso de anteayer no tiene ningún sentido). */

const K_PENDIENTE = "dqr.entreno.pendiente";
const K_DESCANSO = "dqr.entreno.descanso";

function _guardarPendiente(fecha: string, sets: unknown[]): void {
  try {
    sessionStorage.setItem(K_PENDIENTE, JSON.stringify({ fecha, sets, ts: Date.now() }));
  } catch { /* sin almacenamiento: se pierde, como antes */ }
}
function _limpiarPendiente(): void {
  try { sessionStorage.removeItem(K_PENDIENTE); } catch { /* nada que hacer */ }
}
function _leerPendiente(fecha: string): unknown[] | null {
  try {
    const raw = sessionStorage.getItem(K_PENDIENTE);
    if (!raw) return null;
    const d = JSON.parse(raw);
    // Solo del MISMO día: reenviar las series de ayer pisaría las de hoy.
    if (d?.fecha !== fecha || !Array.isArray(d.sets)) return null;
    if (Date.now() - (d.ts ?? 0) > 24 * 3600 * 1000) return null;
    return d.sets;
  } catch { return null; }
}

function _guardarDescanso(d: { fin: number; total: number; exName: string }): void {
  try { sessionStorage.setItem(K_DESCANSO, JSON.stringify(d)); } catch { /* ídem */ }
}
function _limpiarDescanso(): void {
  try { sessionStorage.removeItem(K_DESCANSO); } catch { /* ídem */ }
}
function _leerDescanso(): { fin: number; total: number; exName: string } | null {
  try {
    const raw = sessionStorage.getItem(K_DESCANSO);
    if (!raw) return null;
    const d = JSON.parse(raw);
    return typeof d?.fin === "number" && typeof d?.total === "number"
      ? { fin: d.fin, total: d.total, exName: String(d.exName ?? "") } : null;
  } catch { return null; }
}

export function PortalWorkout({ api, brand, periodStatus = null, businessToday = null,
  hasPeriod = true }: {
  api: Api; brand: PortalBrand; periodStatus?: string | null; businessToday?: string | null;
  /** ¿Hay período de seguimiento? Sin él, el backend rechaza el guardado. */
  hasPeriod?: boolean;
}) {
  // Con la revisión ya ENVIADA (período cerrado) el backend rechaza el
  // guardado: mejor avisar y no dejar teclear datos que no se guardarían.
  // MISMO guardarraíl que el Diario: sin período abierto el backend rechaza
  // el guardado, así que dejar la pantalla editable hacía que el cliente
  // apuntara una sesión entera para nada.
  const readOnly = (periodStatus != null && periodStatus !== "open") || !hasPeriod;
  const toast = usePortalToast();
  // Fecha CONGELADA al montar (ver PortalDiary): pasada la medianoche, un
  // re-render no debe refetchear el día nuevo pisando lo tecleado. Manda la
  // fecha de NEGOCIO del backend (zona del coach) sobre la del dispositivo.
  const [today] = useState(() => businessToday || localToday());
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
  // Récord histórico por ejercicio (mejor e1RM de sesiones previas, lo sirve el
  // backend): al completar una serie que lo supera, se celebra al momento.
  const [records, setRecords] = useState<Record<string, ExRecord>>({});
  // Temporizador de DESCANSO entre series: arranca al completar una serie
  // (peso + reps) con el rest_sec prescrito para ese ejercicio.
  const [rest, setRest] = useState<{ left: number; total: number; exName: string } | null>(null);
  // Cierre APLAZADO de la serie (ver setRow): último valor y su temporizador.
  const pendientes = useRef<Record<number, SetRow>>({});
  const cierres = useRef<Record<number, number>>({});
  useEffect(() => () => {
    for (const t of Object.values(cierres.current)) window.clearTimeout(t);
  }, []);
  const restTimer = useRef<number | null>(null);
  // Vídeo abierto EN la propia pantalla (uno como mucho: abrir otro cierra el
  // anterior, y cerrar el que está abierto devuelve al cliente a su rutina).
  const [openVideoId, setOpenVideoId] = useState<number | null>(null);
  // Un toque FUERA del vídeo (o ESC) lo cierra sin moverse de la rutina: el
  // reproductor va DEBAJO del nombre, así que al quitarlo el ejercicio se queda
  // exactamente donde estaba en pantalla.
  const videoBoxRef = useRef<HTMLDivElement>(null);
  useDismiss(videoBoxRef, () => setOpenVideoId(null), openVideoId !== null);
  const saveTimer = useRef<number | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [loadTry, setLoadTry] = useState(0);
  // Estado VIVO del autosave para el pie ("Guardando…" / "Guardado ✓ HH:MM"):
  // el toast queda solo para errores — cada serie tecleada no puede disparar
  // un aviso.
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");
  const [savedAt, setSavedAt] = useState<Date | null>(null);

  // Al cambiar de sesión, el vídeo abierto deja de tener contexto: se cierra.
  useEffect(() => setOpenVideoId(null), [selectedIdx]);

  useEffect(() => {
    setLoadError(false);
    Promise.all([api.training(), api.today(), api.getDiary(today), api.workoutHistory()]).then(([tr, t, diary, hist]) => {
      const ss = tr.sessions ?? [];
      setSessions(ss);
      setPlanChanges(tr.plan_changes ?? null);
      setWeek(tr.week ?? null);
      setHistory(hist.history ?? {});
      setRecords(hist.records ?? {});
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
    }).catch(() => {
      // Sin esto, un fallo de red dejaba el skeleton girando para siempre.
      setLoadError(true);
    });
  }, [api, today, loadTry]);

  const selected = sessions?.[selectedIdx] ?? null;

  // Garantiza filas objetivo para los ejercicios de la sesión elegida (sin pisar
  // lo ya registrado en otras sesiones del mismo día). Como el cliente ya no
  // puede añadir series, las filas SOLO pueden venir de aquí: si el coach sube
  // las series a mitad de quincena, se completan las que falten. Nunca se
  // recortan (eso borraría lo ya registrado).
  useEffect(() => {
    if (!selected) return;
    setSets((s) => {
      let changed = false;
      const next = { ...s };
      for (const ex of selected.exercises) {
        const objetivo = Math.max(1, Math.min(20, ex.sets || 3));
        const filas = next[ex.exercise_id] ?? [];
        if (filas.length < objetivo) {
          next[ex.exercise_id] = [
            ...filas,
            ...Array.from({ length: objetivo - filas.length },
                          () => ({ weight_kg: null, reps: null })),
          ];
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
    setSaveState("saving");
    api.saveDiary({ log_date: today, workout_sets })
      .then(() => { _limpiarPendiente(); setSavedAt(new Date()); setSaveState("saved"); })
      .catch((e) => {
        // RE-ENCOLA lo no guardado para que el siguiente flush lo reintente
        // (antes el pendiente se descartaba y solo otro tecleo re-enviaba).
        pendingRef.current = pendingRef.current ?? data;
        // Y lo GUARDA fuera del componente: el volcado de última hora ocurre
        // al desmontar (cambiar de pestaña), así que re-encolarlo en un ref ya
        // muerto era perderlo. Aquí sobrevive al desmontaje y al cierre.
        _guardarPendiente(today, workout_sets);
        setSaveState("idle");
        toast.push(
          e instanceof PortalError ? e.message : "Sin guardar · revisa tu conexión",
        );
      });
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

  function startRest(sec: number, exName: string, finAbsoluto?: number) {
    if (restTimer.current) window.clearInterval(restTimer.current);
    const fin = finAbsoluto ?? Date.now() + sec * 1000;
    _guardarDescanso({ fin, total: sec, exName });
    setRest({ left: Math.max(0, Math.round((fin - Date.now()) / 1000)), total: sec, exName });
    restTimer.current = window.setInterval(() => {
      setRest((r) => {
        if (!r) return r;
        if (r.left <= 1) {
          if (restTimer.current) window.clearInterval(restTimer.current);
          restTimer.current = null;
          _limpiarDescanso();
          try { navigator.vibrate?.([200, 100, 200]); } catch { /* sin soporte */ }
          toast.push("💪 Descanso terminado · siguiente serie");
          return null;
        }
        // Por RELOJ, no por conteo: en segundo plano el navegador estrangula
        // los intervalos y el descanso se quedaba corto o clavado.
        return { ...r, left: Math.max(0, Math.round((fin - Date.now()) / 1000)) };
      });
    }, 1000);
  }
  function cancelRest() {
    if (restTimer.current) window.clearInterval(restTimer.current);
    restTimer.current = null;
    _limpiarDescanso();
    setRest(null);
  }

  // Cambiar de pestaña DESMONTA esta pantalla (PortalApp la remonta por `key`):
  // lo que quedó sin guardar se reintenta y el descanso en marcha se retoma
  // donde iba, en vez de morir los dos en silencio.
  useEffect(() => {
    const sinGuardar = _leerPendiente(today);
    if (sinGuardar && sinGuardar.length) {
      api.saveDiary({ log_date: today, workout_sets: sinGuardar as any })
        .then(() => { _limpiarPendiente(); setSavedAt(new Date()); setSaveState("saved"); })
        .catch(() => { /* sigue guardado: se reintenta al volver */ });
    }
    const guardado = _leerDescanso();
    if (guardado && guardado.fin > Date.now() + 1000) {
      startRest(guardado.total, guardado.exName, guardado.fin);
    } else if (guardado) {
      _limpiarDescanso();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => () => { if (restTimer.current) window.clearInterval(restTimer.current); }, []);

  // Serie COMPLETADA (transición a peso+reps rellenos): récord + descanso.
  function serieCompletada(exId: number, row: SetRow) {
    const ex = selected?.exercises.find((e) => e.exercise_id === exId);
    const w = row.weight_kg ?? 0;
    const reps = row.reps ?? 0;
    // Mismo criterio que el backend (metrics.epley_1rm, series ≤15 reps). Solo
    // se celebra si YA había récord previo: la primera sesión no es un desfile
    // de confeti, es la línea base.
    if (w > 0 && reps > 0 && reps <= 15) {
      const e1 = reps === 1 ? w : w * (1 + reps / 30);
      const rec = records[String(exId)];
      if (rec && e1 > rec.e1rm_kg + 0.01) {
        try { navigator.vibrate?.([100, 60, 100, 60, 250]); } catch { /* sin soporte */ }
        toast.push(`🎉 Récord en ${ex?.name ?? "este ejercicio"}: ${w} kg × ${reps}`);
        setRecords((r) => ({
          ...r,
          [String(exId)]: { e1rm_kg: e1, weight_kg: w, reps, date: today },
        }));
      }
    }
    if (ex?.rest_sec) startRest(ex.rest_sec, ex.name);
  }

  /** ¿Serie HECHA? Con carga hacen falta kg y reps; en los ejercicios de peso
   *  corporal (flexiones, dominadas, plancha) no hay kg que apuntar y con la
   *  regla anterior no contaban nunca: ni descanso, ni récord, ni "Anterior".
   *  Se reconocen porque el plan no les pauta ningún peso de referencia. */
  function _completa(fila: SetRow, exId: number): boolean {
    if (fila.reps == null) return false;
    if (fila.weight_kg != null) return true;
    const ex = selected?.exercises.find((e) => e.exercise_id === exId);
    return (ex?.week_weight_hint_kg ?? ex?.start_weight_hint_kg) == null;
  }

  function setRow(exId: number, idx: number, patch: Partial<SetRow>) {
    if (readOnly) return;
    const prevRow = sets[exId]?.[idx];
    const nuevoRow = { ...(prevRow ?? { weight_kg: null, reps: null }), ...patch };
    const transicion = prevRow != null && !_completa(prevRow, exId)
      && _completa(nuevoRow, exId);
    setSets((s) => {
      const next = { ...s, [exId]: s[exId].map((r, i) => (i === idx ? { ...r, ...patch } : r)) };
      flush(next);
      return next;
    });
    // El campo emite en CADA pulsación: tecleando "12" reps, la transición
    // salta con el "1" y arrancaba el descanso (y celebraba un récord falso)
    // a mitad de escribir. Se espera a que el cliente deje de teclear.
    if (transicion) {
      window.clearTimeout(cierres.current[exId]);
      cierres.current[exId] = window.setTimeout(() => {
        const fila = pendientes.current[exId];
        if (fila && _completa(fila, exId)) serieCompletada(exId, fila);
      }, 1100);
    }
    pendientes.current[exId] = nuevoRow;
  }
  // (No hay añadir ni borrar series: las filas las fija el plan del coach —
  //  `ex.sets`. El cliente registra lo que hizo, no reescribe la pauta.)

  if (loadError && sessions === null) {
    return (
      <div className="py-10 text-center">
        <p className="text-sm opacity-70">No se pudo cargar tu entreno.</p>
        <button onClick={() => setLoadTry((n) => n + 1)}
          className="portal-btn3d mt-3 rounded-xl px-4 py-2 text-sm font-semibold">
          Reintentar
        </button>
      </div>
    );
  }
  if (sessions === null) return <Loading />;
  if (sessions.length === 0) {
    // Aún sin plan publicado: en vez de un vacío seco, avisamos de que se está
    // preparando y de que recibirá una notificación cuando esté listo.
    return (
      <div className="space-y-5">
        <div>
          <h2 className="p-title">Tu entreno</h2>
        </div>
        <div className="portal-card portal-card--rail p-4" style={{ "--rail": brand.color_primary } as React.CSSProperties}>
          <div className="flex items-center gap-2">
            <Sparkles size={18} style={{ color: brand.color_primary }} />
            <p className="text-sm font-semibold">Se está creando tu planificación</p>
          </div>
          <p className="mt-1.5 text-xs leading-relaxed opacity-70">
            Te avisamos al estar listo
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="p-title">Registrar entreno</h2>
      </div>

      {readOnly && (
        <div className="portal-card portal-card--rail p-3.5 text-sm" style={{ "--rail": brand.color_primary } as React.CSSProperties}>
          {hasPeriod ? (
            <>
              <p className="font-semibold">Revisión enviada — registro en pausa</p>
              <p className="mt-1 text-xs opacity-70">Se reabre con tu feedback</p>
            </>
          ) : (
            <>
              <p className="font-semibold">Tu seguimiento aún no ha empezado</p>
              <p className="mt-1 text-xs opacity-70">
                Puedes ver la rutina; al arrancar podrás registrar tus series
              </p>
            </>
          )}
        </div>
      )}

      {/* SEMANA del mesociclo: en qué fase estás, qué toca y POR QUÉ. Los pesos
          sugeridos de abajo ya vienen ajustados a esta semana. */}
      {week && (
        <div
          className="portal-card portal-card--rail overflow-hidden p-3.5"
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
          {week.why && (
            <details className="mt-1.5">
              <summary className="cursor-pointer text-[11px] opacity-60">por qué</summary>
              <p className="mt-1 text-xs opacity-70">{week.why}</p>
            </details>
          )}
          {week.load_factor !== 1 && (
            <p className="mt-1 text-[11px] opacity-50">
              Pesos ya ajustados a esta semana
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
                planChanges.items.some((it) => /diet|nutri/i.test(it.area)) && "Dieta → tu PDF",
                planChanges.items.some((it) => /entren/i.test(it.area)) && "Entreno → tus sesiones",
              ].filter(Boolean).join(" · ") || "Anotados en tu plan."}
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
          {selected.warmup && (
            <div className="portal-card mt-1 p-4">
              <p className="text-[10px] font-semibold uppercase tracking-wider opacity-45">Calentamiento</p>
              <p className="mt-1 text-xs leading-relaxed opacity-70">{selected.warmup}</p>
            </div>
          )}
          {selected.exercises.map((ex) => {
            const rows = sets[ex.exercise_id] ?? [];
            const doneCount = rows.filter((r) => r.weight_kg != null && r.reps != null).length;
            const embeddable = isEmbeddable(ex.video_url);
            const videoOpen = embeddable && openVideoId === ex.exercise_id;
            const hintKg = ex.week_weight_hint_kg ?? ex.start_weight_hint_kg;
            // Sesión ANTERIOR de este ejercicio: la referencia que el cliente
            // necesita para elegir el peso de hoy.
            const previa = history[String(ex.exercise_id)]?.[0];
            return (
              <div key={ex.exercise_id} className="portal-card p-4">
                {/* Zona del vídeo: nombre + botón + reproductor. Un toque FUERA de
                    esta zona lo cierra y te deja en la rutina, justo donde estabas. */}
                <div ref={videoOpen ? videoBoxRef : undefined}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <p className="truncate text-sm font-semibold">{ex.name}</p>
                        {/* El vídeo del ejercicio, JUNTO AL NOMBRE: azul (consulta,
                            no acción de registro) y siempre visible si lo tiene. */}
                        {ex.video_url && (embeddable ? (
                          // El círculo se ve discreto (26 px) pero el área que se
                          // pulsa son los 44 px de `tap`: el -my-2 evita que ese
                          // área infle la altura de la fila del nombre.
                          <button
                            type="button"
                            onClick={() => setOpenVideoId(videoOpen ? null : ex.exercise_id)}
                            aria-expanded={videoOpen}
                            aria-label={videoOpen ? `Cerrar vídeo de ${ex.name}` : `Ver vídeo de ${ex.name}`}
                            title={videoOpen ? "Cerrar vídeo" : "Ver vídeo"}
                            className="tap -my-2 flex shrink-0 items-center justify-center"
                          >
                            <span
                              className="flex h-[26px] w-[26px] items-center justify-center rounded-full"
                              style={
                                videoOpen
                                  ? { background: brand.color_secondary, color: "#fff" }
                                  : {
                                      background: `color-mix(in srgb, ${brand.color_secondary} 16%, transparent)`,
                                      color: brand.color_secondary,
                                    }
                              }
                            >
                              {videoOpen ? <X size={13} /> : <Play size={12} fill="currentColor" />}
                            </span>
                          </button>
                        ) : (
                          // Página que no sabemos embeber (ni YouTube/Vimeo ni
                          // archivo): se abre fuera, como antes.
                          <a
                            href={ex.video_url} target="_blank" rel="noreferrer"
                            aria-label={`Ver vídeo de ${ex.name}`}
                            title="Ver vídeo"
                            className="tap -my-2 flex shrink-0 items-center justify-center"
                          >
                            <span
                              className="flex h-[26px] w-[26px] items-center justify-center rounded-full"
                              style={{
                                background: `color-mix(in srgb, ${brand.color_secondary} 16%, transparent)`,
                                color: brand.color_secondary,
                              }}
                            >
                              <Play size={12} fill="currentColor" />
                            </span>
                          </a>
                        ))}
                      </div>
                      {/* Pauta del día: cifras destacadas y etiquetas discretas.
                          Antes era una frase corrida donde todo pesaba igual. */}
                      <p className="mt-0.5 flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-xs opacity-70">
                        <span className="font-semibold tabular-nums">{ex.sets} × {ex.rep_range}</span>
                        <span className="opacity-60">RIR {ex.rir}</span>
                        {hintKg ? (
                          <span className="opacity-60">
                            ~{fmt1(hintKg)} kg
                            {week && ex.week_weight_hint_kg != null && ex.week_weight_hint_kg !== ex.start_weight_hint_kg
                              ? ` · sem ${week.week}` : ""}
                          </span>
                        ) : null}
                        {ex.rest_sec ? <span className="opacity-60">{ex.rest_sec}s descanso</span> : null}
                      </p>
                      {records[String(ex.exercise_id)] && (
                        <p className="text-[11px] font-medium" style={{ color: brand.color_secondary }}>
                          Tu récord · {fmt1(records[String(ex.exercise_id)].weight_kg)} kg × {records[String(ex.exercise_id)].reps}
                        </p>
                      )}
                    </div>
                    {doneCount > 0 && (
                      <span className="flex shrink-0 items-center gap-1 text-xs" style={{ color: brand.color_primary }}>
                        <Check size={13} /> {doneCount}/{rows.length}
                      </span>
                    )}
                  </div>

                  {videoOpen && ex.video_url && (
                    <div className="mt-3">
                      <InlineVideo url={ex.video_url} title={ex.name} />
                    </div>
                  )}
                </div>

                <div className="mt-3 space-y-1.5">
                  {/* "Anterior" delante de los campos: el cliente ve qué movió la
                      última vez en ESA serie ANTES de apuntar, que es cuando le
                      sirve para decidir el peso. */}
                  <div className="grid grid-cols-[24px_minmax(64px,0.9fr)_1fr_1fr] items-center gap-2 px-1 text-[10px] font-semibold uppercase tracking-wider opacity-45">
                    <span>#</span><span>Anterior</span><span>Peso (kg)</span><span>Reps</span>
                  </div>
                  {rows.map((r, i) => {
                    const done = r.weight_kg != null && r.reps != null;
                    const prev = previa?.sets?.find((ps) => ps.set === i + 1);
                    const prevTxt = prev && prev.weight_kg != null
                      ? `${fmt1(prev.weight_kg)}${prev.reps != null ? ` × ${prev.reps}` : ""}`
                      : "—";
                    return (
                      <div key={i} className="grid grid-cols-[24px_minmax(64px,0.9fr)_1fr_1fr] items-center gap-2">
                        <span className="text-center text-xs font-semibold tabular-nums" style={{ color: done ? brand.color_primary : undefined, opacity: done ? 1 : 0.45 }}>{i + 1}</span>
                        <span className="truncate text-xs tabular-nums opacity-55" title={previa ? `Sesión del ${shortDate(previa.date)}` : undefined}>
                          {prevTxt}
                        </span>
                        {/* Rangos espejo del backend (WorkoutSetIn): 0-600 kg, 0-100 reps */}
                        <SetInput value={r.weight_kg} min={0} max={600} placeholder={hintKg ? String(hintKg) : "—"} accent={brand.color_secondary} onChange={(v) => setRow(ex.exercise_id, i, { weight_kg: v })} />
                        <SetInput value={r.reps} min={0} max={100} integer placeholder="—" accent={brand.color_secondary} onChange={(v) => setRow(ex.exercise_id, i, { reps: v })} />
                      </div>
                    );
                  })}
                  {/* Descanso a demanda: además de arrancar solo al completar una
                      serie, el cliente puede lanzarlo cuando quiera. */}
                  {!readOnly && ex.rest_sec ? (
                    <button
                      type="button"
                      onClick={() => startRest(ex.rest_sec as number, ex.name)}
                      className="mt-1 inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold"
                      style={{
                        background: `color-mix(in srgb, ${brand.color_secondary} 10%, transparent)`,
                        color: brand.color_secondary,
                      }}
                    >
                      <Timer size={13} /> Descansar {ex.rest_sec}s
                    </button>
                  ) : null}
                </div>
                {history[String(ex.exercise_id)]?.length ? (
                  // Azul: el historial es consulta de datos, no acción
                  <ExHistory sessions={history[String(ex.exercise_id)]} accent={brand.color_secondary} />
                ) : null}
                {ex.technique_cue && (
                  <p className="mt-2.5 flex items-start gap-1.5 text-xs leading-relaxed opacity-60">
                    <Lightbulb size={13} className="mt-px shrink-0" style={{ color: brand.color_secondary }} />
                    <span><span className="font-semibold">Técnica.</span> {ex.technique_cue}</span>
                  </p>
                )}
                {ex.coach_notes && (
                  // Indicación PERSONAL del coach (limitaciones/adaptación): destacada,
                  // no un consejo genérico — el cliente debe leerla antes de la serie.
                  <p
                    className="mt-2 rounded-lg px-3 py-2 text-xs font-medium"
                    style={{
                      background: `color-mix(in srgb, ${brand.color_primary} 10%, transparent)`,
                      color: brand.color_primary,
                    }}
                  >
                    Indicación de tu coach: <span className="font-normal opacity-90">{ex.coach_notes}</span>
                  </p>
                )}
              </div>
            );
          })}
          {selected.cooldown && (
            <div className="portal-card p-4">
              <p className="text-[10px] font-semibold uppercase tracking-wider opacity-45">Vuelta a la calma</p>
              <p className="mt-1 text-xs leading-relaxed opacity-70">{selected.cooldown}</p>
            </div>
          )}
        </>
      )}
      <p className="pb-2 text-center text-xs opacity-40" aria-live="polite">
        {saveState === "saving"
          ? "Guardando…"
          : saveState === "saved" && savedAt
            ? `Guardado ✓ ${savedAt.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })}`
            : "Se guarda automáticamente"}
      </p>

      {/* Temporizador de DESCANSO: píldora flotante sobre la barra de pestañas.
          Arranca sola al completar una serie —o a mano con "Descansar"— con el
          descanso prescrito. Se salta con la X y vibra al terminar. */}
      {rest && (
        <div
          className="fixed bottom-20 left-1/2 z-40 flex -translate-x-1/2 items-center gap-3 rounded-full px-4 py-2.5 shadow-lg"
          style={{ background: brand.color_primary, color: "var(--p-on-accent)" }}
          role="timer"
          aria-label={`Descanso: ${rest.left} segundos`}
        >
          <span className="text-lg font-bold tabular-nums">
            {Math.floor(rest.left / 60)}:{String(rest.left % 60).padStart(2, "0")}
          </span>
          <div className="h-1.5 w-24 overflow-hidden rounded-full bg-white/25">
            <div
              className="h-full rounded-full bg-white transition-all duration-1000 ease-linear"
              style={{ width: `${Math.max(2, Math.round((rest.left / rest.total) * 100))}%` }}
            />
          </div>
          <span className="max-w-[90px] truncate text-[11px] opacity-80">{rest.exName}</span>
          <button onClick={cancelRest} aria-label="Saltar descanso"
            className="flex h-7 w-7 items-center justify-center rounded-full bg-white/20">
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}

function SetInput({ value, placeholder, accent, onChange, min = 0, max, integer }: {
  value: number | null; placeholder: string; accent: string; onChange: (v: number | null) => void;
  min?: number; max?: number; integer?: boolean;
}) {
  // A prueba de móvil (useDecimalField): acepta coma ("62,5" es media placa) —
  // antes una coma no reconocida viajaba como null y la serie se BORRABA del
  // servidor mientras el cliente la veía en pantalla. Fuera de rango no viaja.
  const { invalid, inputProps } = useDecimalField(value, onChange, { min, max, integer });
  return (
    <input
      {...inputProps}
      placeholder={placeholder}
      className="min-h-[44px] w-full rounded-xl border bg-transparent px-3 py-2 text-center text-sm font-semibold outline-none"
      style={{
        borderColor: invalid ? "#C2453A" : "rgba(128,128,128,0.22)",
        caretColor: accent,
        ...(invalid ? { color: "#C2453A" } : {}),
      }}
      title={invalid ? "No válido · no se guarda" : undefined}
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
        <span className="truncate">Historial · {sessions.length} sesion{sessions.length === 1 ? "" : "es"}</span>
        <span className="ml-2 shrink-0 tabular-nums" style={{ color: accent }}>
          {shortDate(last.date)} {open ? "▾" : "▸"}
        </span>
      </button>
      {open && (
        <div className="mt-1.5 space-y-1">
          {sessions.map((s) => (
            <div key={s.date} className="flex justify-between opacity-60">
              <span>{shortDate(s.date)}</span>
              <span>{s.sets.map(fmt).join(" · ")}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

