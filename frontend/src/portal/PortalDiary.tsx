import { useEffect, useRef, useState } from "react";
import type { DietAdherence, Macros, PlanChanges, PortalBrand } from "../types";
import { usePortalToast } from "./PortalToast";
import { fmt1, Loading, localToday, useDecimalField } from "./PortalUi";
import { PortalError } from "./portalApi";
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
/* LO TECLEADO NO SE PIERDE (mismo criterio que Entreno).
   El portal remonta el contenido al cambiar de pestaña, así que re-encolar el
   guardado fallido en un ref del componente era perderlo: bastaba un tramo sin
   cobertura (gimnasio en sótano, metro) para que el peso en ayunas, el sueño o
   la nota del día se esfumaran… mientras el banner prometía "lo que apuntes se
   guardará al volver". `sessionStorage`: sobrevive a la navegación pero no a
   cerrar la app días después (un diario de anteayer no se reenvía). */

const K_DIARIO_PENDIENTE = "dqr.diario.pendiente";

function _guardarPendiente(fecha: string, datos: unknown): void {
  try {
    sessionStorage.setItem(K_DIARIO_PENDIENTE,
      JSON.stringify({ fecha, datos, ts: Date.now() }));
  } catch { /* sin almacenamiento: se pierde, como antes */ }
}
function _limpiarPendiente(): void {
  try { sessionStorage.removeItem(K_DIARIO_PENDIENTE); } catch { /* nada que hacer */ }
}
function _leerPendiente(fecha: string): Record<string, unknown> | null {
  try {
    const raw = sessionStorage.getItem(K_DIARIO_PENDIENTE);
    if (!raw) return null;
    const d = JSON.parse(raw);
    // Solo del MISMO día: reenviar el diario de ayer pisaría el de hoy.
    if (d?.fecha !== fecha || !d.datos || typeof d.datos !== "object") return null;
    if (Date.now() - (d.ts ?? 0) > 24 * 3600 * 1000) return null;
    return d.datos as Record<string, unknown>;
  } catch { return null; }
}

export function PortalDiary({ api, brand, periodStatus = null, businessToday = null,
  hasPeriod = true, hasNutrition = true, hasTraining = true }: {
  api: Api; brand: PortalBrand; periodStatus?: string | null; businessToday?: string | null;
  hasPeriod?: boolean; hasNutrition?: boolean;
  // Con entreno contratado las Novedades ya viven en la pestaña Entreno; el
  // cliente SOLO-DIETA no abre esa pantalla y se le enseñan aquí.
  hasTraining?: boolean;
}) {
  const toast = usePortalToast();
  // Fecha CONGELADA al montar: recalcularla en cada render hacía que, pasada
  // la medianoche, cualquier re-render refetcheara el día nuevo pisando lo
  // tecleado y guardara lo pendiente con la fecha del día siguiente.
  // Manda la fecha de NEGOCIO del backend (zona del coach): un cliente de
  // viaje con el móvil en otra zona ya no registra en el día equivocado.
  const [today] = useState(() => businessToday || localToday());
  // Revisión enviada (período cerrado): el backend rechazaría el guardado —
  // se avisa y no se programan guardados. SIN período (onboarding, plan aún
  // sin activar) el backend también rechaza con 409: el diario se muestra
  // igual pero deshabilitado, con su explicación — antes era editable y lo
  // tecleado se perdía en silencio (auditoría crítica).
  const readOnly = (periodStatus != null && periodStatus !== "open") || !hasPeriod;
  const [form, setForm] = useState<DiaryForm | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [loadTry, setLoadTry] = useState(0);
  const saveTimer = useRef<number | null>(null);
  // Estado VIVO del autosave para el pie ("Guardando…" / "Guardado ✓ HH:MM"):
  // el toast queda solo para errores — guardar cada pocos segundos no puede
  // ser una lluvia de avisos.
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  // Objetivo nutricional del día (solo lectura, si el paquete lleva dieta).
  const [target, setTarget] = useState<{ kcal: number; macros: Macros } | null>(null);
  // Novedades de la última adaptación, SOLO para el cliente sin entreno: antes
  // un cliente de solo dieta no veía nunca qué le cambió la revisión.
  const [planChanges, setPlanChanges] = useState<PlanChanges | null>(null);

  // Tira compacta con el objetivo del día: sale del plan publicado. Se carga
  // junto al fetch inicial, sin spinner propio; si falla, simplemente no se
  // muestra (el diario funciona igual).
  useEffect(() => {
    if (!hasNutrition) return;
    api.plan().then((p) => {
      const n = p.nutrition;
      if (n && n.target_kcal != null && n.macros) setTarget({ kcal: n.target_kcal, macros: n.macros });
      if (!hasTraining) setPlanChanges(p.plan_changes ?? null);
    }).catch(() => { /* sin tira: el objetivo es un extra, no bloquea nada */ });
  }, [api, hasNutrition, hasTraining]);

  useEffect(() => {
    setLoadError(false);
    api.getDiary(today).then((d) => {
      const base: DiaryForm = d.exists
        ? {
          weight_kg: d.weight_kg, sleep_hours: d.sleep_hours,
          steps: d.steps ?? "", satiety_1_10: d.satiety_1_10, water_liters: d.water_liters,
          diet_adherence: d.diet_adherence, energy_1_5: d.energy_1_5,
          mood_1_5: d.mood_1_5, fatigue_1_5: d.fatigue_1_5,
          free_notes: d.free_notes ?? "",
        }
        : { ...EMPTY };
      // Lo que quedó sin guardar (sin cobertura) MANDA sobre lo del servidor:
      // si no, la pantalla enseñaría los valores viejos y el siguiente tecleo
      // los volvería a guardar, borrando lo que el cliente ya había apuntado.
      const pendiente = _leerPendiente(today) as Partial<DiaryForm> | null;
      setForm(pendiente ? { ...base, ...pendiente } : base);
    }).catch(() => {
      // Sin esto, un fallo de red dejaba el skeleton girando para siempre.
      setLoadError(true);
    });
  }, [api, today, loadTry]);

  function update(patch: Partial<DiaryForm>) {
    // Con el período cerrado el diario está EN PAUSA: no aceptamos cambios (antes
    // el campo cambiaba en pantalla pero no se guardaba, engañando al cliente).
    if (readOnly) return;
    setForm((f) => {
      const next = { ...(f as DiaryForm), ...patch };
      scheduleSave(next);
      return next;
    });
  }

  // Debounce SIN pérdidas: lo pendiente se vuelca al instante al salir de la
  // app o cambiar de pestaña, y un fallo de red avisa (no falla en silencio).
  const pendingRef = useRef<DiaryForm | null>(null);
  const saveNowRef = useRef<() => void>(() => {});
  saveNowRef.current = () => {
    const data = pendingRef.current;
    if (!data) return;
    pendingRef.current = null;
    if (saveTimer.current) window.clearTimeout(saveTimer.current);
    // Solo campos del diario: NO mandamos workout_sets para no borrar las
    // series registradas en la pestaña "Entreno" (upsert parcial en backend).
    setSaveState("saving");
    api
      .saveDiary({ log_date: today, ...data })
      .then(() => { _limpiarPendiente(); setSavedAt(new Date()); setSaveState("saved"); })
      .catch((e) => {
        // RE-ENCOLA lo no guardado: el siguiente flush (o el de salida de la
        // app) lo reintenta — antes el dato pendiente se descartaba y solo
        // otro tecleo volvía a enviarlo. Y lo guarda FUERA del componente: el
        // volcado de última hora ocurre al desmontar (cambiar de pestaña), así
        // que un ref ya muerto no servía de nada.
        pendingRef.current = pendingRef.current ?? data;
        _guardarPendiente(today, data);
        setSaveState("idle");
        toast.push(
          e instanceof PortalError ? e.message : "Sin guardar · revisa tu conexión",
        );
      });
  };

  function scheduleSave(next: DiaryForm) {
    if (readOnly) return;
    pendingRef.current = next;
    if (saveTimer.current) window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(() => saveNowRef.current(), 800);
  }

  useEffect(() => {
    const onHide = () => {
      if (document.visibilityState === "hidden") saveNowRef.current();
    };
    // Al VOLVER LA COBERTURA se reintenta solo: la recuperación no puede
    // depender de que el cliente cambie de pestaña (es lo que promete el
    // banner "sin conexión").
    const onOnline = () => saveNowRef.current();
    document.addEventListener("visibilitychange", onHide);
    window.addEventListener("pagehide", onHide);
    window.addEventListener("online", onOnline);
    return () => {
      document.removeEventListener("visibilitychange", onHide);
      window.removeEventListener("pagehide", onHide);
      window.removeEventListener("online", onOnline);
      saveNowRef.current();
    };
  }, []);

  // Lo que quedó sin guardar en una visita anterior se reenvía al entrar.
  useEffect(() => {
    const sinGuardar = _leerPendiente(today);
    if (!sinGuardar) return;
    api.saveDiary({ log_date: today, ...(sinGuardar as any) })
      .then(() => { _limpiarPendiente(); setSavedAt(new Date()); setSaveState("saved"); })
      .catch(() => { /* sigue guardado: se reintenta al volver */ });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, today]);

  if (loadError && !form) {
    return (
      <div className="py-10 text-center">
        <p className="text-sm opacity-70">No se pudo cargar tu diario.</p>
        <button onClick={() => setLoadTry((n) => n + 1)}
          className="portal-btn3d mt-3 rounded-xl px-4 py-2 text-sm font-semibold">
          Reintentar
        </button>
      </div>
    );
  }
  if (!form) return <Loading />;

  return (
    <div className="space-y-5">
      {readOnly && (
        <div className="portal-card portal-card--rail p-3.5 text-sm" style={{ "--rail": brand.color_primary } as React.CSSProperties}>
          {hasPeriod ? (
            <>
              <p className="font-semibold">Revisión enviada — diario en pausa</p>
              <p className="mt-1 text-xs opacity-70">Se reabre con tu feedback</p>
            </>
          ) : (
            <>
              <p className="font-semibold">Seguimiento aún no activo</p>
              <p className="mt-1 text-xs opacity-70">Te avisaremos al activarse.</p>
            </>
          )}
        </div>
      )}
      <div>
        <h2 className="p-title">Mi día</h2>
        {/* Objetivo del día (solo lectura): el cliente no tiene que rebuscar
            sus números en el PDF para saber a qué apunta hoy. */}
        {hasNutrition && target && (
          <p className="mt-0.5 text-xs font-medium tabular-nums" style={{ color: brand.color_secondary }}>
            {fmt1(target.kcal)} kcal · P {fmt1(target.macros.protein_g)} g · C {fmt1(target.macros.carbs_g)} g · G {fmt1(target.macros.fat_g)} g
          </p>
        )}
      </div>

      {/* Novedades del plan para el cliente SOLO-DIETA: qué cambió en su última
          revisión y por qué (con entreno, esto vive en la pantalla Entreno). */}
      {planChanges?.items?.length ? (
        <details className="portal-card overflow-hidden">
          <summary className="tap flex cursor-pointer items-center gap-2 p-3.5 text-sm font-semibold">
            Novedades de tu plan
            <span className="ml-auto rounded-full px-2 py-0.5 text-[10px] font-bold text-white"
              style={{ background: brand.color_secondary }}>
              revisión #{planChanges.period_index}
            </span>
          </summary>
          <div className="space-y-2 px-3.5 pb-3.5">
            {planChanges.items.map((it, i) => (
              <div key={i} className="rounded-xl border p-2.5" style={{ borderColor: "rgba(128,128,128,0.18)" }}>
                <div className="flex flex-wrap items-center gap-1.5 text-xs font-semibold">
                  <span className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white"
                    style={{ background: brand.color_primary }}>
                    {/diet|nutri/i.test(it.area) ? "Dieta" : it.area}
                  </span>
                  {it.detail ?? it.change}
                </div>
                {it.reason && <p className="mt-1 text-xs opacity-70">{it.reason}</p>}
              </div>
            ))}
            <p className="pt-0.5 text-[11px] opacity-50">Ya aplicado en tu plan y en tu PDF.</p>
          </div>
        </details>
      ) : null}

      <div className="grid grid-cols-2 gap-3">
        {/* Cursor azul: entrada de DATOS (el naranja queda para acciones).
            Rangos ESPEJO del backend (DailyLogUpsert): un valor fuera de rango
            no viaja (se marca en rojo) — antes un "8" a medio teclear en el
            flush al bloquear el móvil tumbaba TODO el guardado con un 422. */}
        <NumberCard label="Peso en ayunas" unit="kg" value={form.weight_kg} min={31} max={299}
          onChange={(v) => update({ weight_kg: v })} accent={brand.color_secondary} />
        <NumberCard label="Horas de sueño" unit="h" value={form.sleep_hours} min={0} max={16}
          onChange={(v) => update({ sleep_hours: v })} accent={brand.color_secondary} />
        <NumberCard label="Saciedad (1-10)" unit="" value={form.satiety_1_10} min={0} max={10}
          onChange={(v) => update({ satiety_1_10: v })} accent={brand.color_secondary} />
        <NumberCard label="Agua" unit="L" value={form.water_liters} min={0} max={15}
          onChange={(v) => update({ water_liters: v })} accent={brand.color_secondary} />
      </div>

      <Field label="Pasos / cardio del día" htmlFor="diary-steps">
        <input
          id="diary-steps"
          type="text"
          maxLength={160}
          className="w-full rounded-xl border bg-transparent p-3 text-sm"
          style={{ borderColor: "rgba(128,128,128,0.2)" }}
          placeholder="Ej.: 8000 pasos + 30' cardio"
          value={form.steps}
          onChange={(e) => update({ steps: e.target.value })}
        />
      </Field>

      {hasNutrition && (
      <Field label="¿Seguiste la dieta?">
        <div className="flex gap-2">
          {ADHERENCE.map((a) => (
            <button
              key={a.value}
              type="button"
              onClick={() => update({ diet_adherence: a.value })}
              aria-label={`¿Seguiste la dieta?: ${a.label}`}
              aria-pressed={form.diet_adherence === a.value}
              className="flex flex-1 flex-col items-center gap-1 rounded-xl border py-3 text-sm"
              style={
                form.diet_adherence === a.value
                  ? { borderColor: brand.color_primary, background: `${brand.color_primary}1f` }
                  : { borderColor: "rgba(128,128,128,0.2)" }
              }
            >
              <span className="text-lg" aria-hidden="true">{a.emoji}</span>
              {a.label}
            </button>
          ))}
        </div>
      </Field>
      )}

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

      {!readOnly && (
        <p className="pb-2 text-center text-xs opacity-40" aria-live="polite">
          {saveState === "saving"
            ? "Guardando…"
            : saveState === "saved" && savedAt
              ? `Guardado ✓ ${savedAt.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })}`
              : "Se guarda automáticamente"}
        </p>
      )}
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
  onChange,
  accent,
  min,
  max,
}: {
  label: string;
  unit: string;
  value: number | null;
  onChange: (v: number | null) => void;
  accent: string;
  min?: number;
  max?: number;
}) {
  // A prueba de móvil (useDecimalField): acepta coma o punto, lo tecleado no
  // se pisa, y un valor inválido o fuera de rango NO viaja al autosave (antes
  // "82,5" no reconocido enviaba null y BORRABA el peso ya guardado).
  const { invalid, inputProps } = useDecimalField(value, onChange, { min, max });
  return (
    <label className="portal-card block p-4">
      <span className="block text-xs opacity-50">{label}</span>
      <div className="mt-1 flex items-baseline gap-1">
        <input
          {...inputProps}
          placeholder="—"
          className="w-full bg-transparent text-2xl font-semibold outline-none"
          style={{ caretColor: accent, ...(invalid ? { color: "#C2453A" } : {}) }}
        />
        <span className="text-sm opacity-50">{unit}</span>
      </div>
      {invalid && (
        <span className="mt-1 block text-[11px] font-medium" style={{ color: "#C2453A" }}>
          {min != null && max != null ? `Entre ${min} y ${max}` : "Valor no válido"}
        </span>
      )}
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
              type="button"
              onClick={() => onChange(n)}
              aria-label={`${label}: ${n} de 5`}
              aria-pressed={active}
              className="flex flex-1 items-center justify-center rounded-xl border py-2.5 text-xl transition-transform"
              style={
                active
                  ? { borderColor: accent, background: `${accent}1f`, transform: "scale(1.05)" }
                  : { borderColor: "rgba(128,128,128,0.2)" }
              }
            >
              <span aria-hidden="true">{emoji}</span>
            </button>
          );
        })}
      </div>
    </Field>
  );
}
