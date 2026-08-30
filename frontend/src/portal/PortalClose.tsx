import { useEffect, useState } from "react";
import { ancla, irYMarcar } from "../lib/anchors";
import { Camera, Check, Loader2, Mail, MessageCircle } from "lucide-react";
import type { PortalBrand } from "../types";
import { usePortalToast } from "./PortalToast";
import type { portalApi } from "./portalApi";

type Api = ReturnType<typeof portalApi>;

/** BORRADOR persistente de la revisión: es el formulario más largo del portal
 *  y el cliente puede salir a mirar su diario a mitad — nada debe perderse.
 *  Se guarda en el móvil (localStorage) POR CLIENTE (token) y período: en un
 *  móvil compartido, el borrador de un cliente no puede aparecer (ni pisarse)
 *  en el portal de otro — son datos de salud privados. */
const DRAFT_KEY = (token: string, closeDate: string | null) =>
  `portal_close_draft_${token.slice(0, 16)}_${closeDate ?? "actual"}`;

function loadDraft(token: string, closeDate: string | null): Record<string, any> {
  try {
    return JSON.parse(localStorage.getItem(DRAFT_KEY(token, closeDate)) ?? "{}");
  } catch {
    return {};
  }
}

// Sección 2 de la revisión quincenal: sensaciones (1 muy mal → 5 excelente).
// Las claves se guardan y el coach las lee (lib FEELING_LABEL); en el paquete
// solo-nutrición se quitan las de entreno ("Energía en el entreno" pasa a "en el
// día" y desaparece "Recuperación muscular").
const FEELINGS_TRAINING: { key: string; label: string }[] = [
  { key: "energia", label: "Energía en el entreno" },
  { key: "hambre", label: "Hambre / saciedad" },
  { key: "sueno", label: "Calidad del sueño" },
  { key: "recuperacion", label: "Recuperación muscular" },
  { key: "animo", label: "Ánimo / estado general" },
  { key: "digestiones", label: "Digestiones" },
];
const FEELINGS_NUTRITION: { key: string; label: string }[] = [
  { key: "energia", label: "Energía en el día" },
  { key: "hambre", label: "Hambre / saciedad" },
  { key: "sueno", label: "Calidad del sueño" },
  { key: "animo", label: "Ánimo / estado general" },
  { key: "digestiones", label: "Digestiones" },
];

/**
 * REVISIÓN QUINCENAL (cierre de período, desde el día 14). Réplica del documento
 * del coach: medidas, sensaciones (1-5), adherencia (0-10), comidas libres,
 * cambios, qué cuesta, objetivo. Al enviar dispara el feedback de adaptación IA.
 * Las fotos de progreso se suben AQUÍ (sección 7); mandarlas por WhatsApp
 * sigue valiendo para quien lo prefiera.
 */
export function PortalClose({ api, token, brand, onClosed, canClose, daysLeft, closeDate, periodStatus, hasTraining = true, hasNutrition = true, directContact = true }: {
  api: Api; token: string; brand: PortalBrand; onClosed: () => void; canClose: boolean;
  daysLeft: number | null; closeDate: string | null; periodStatus?: string | null;
  // Paquete solo-nutrición (Start): sin adherencia ni sensaciones de entreno.
  hasTraining?: boolean;
  hasNutrition?: boolean;
  // Contacto directo (Pro): la vía alternativa de las fotos es WhatsApp; si
  // no, el email. (Lo normal es subirlas en la sección 7.)
  directContact?: boolean;
}) {
  const FEELINGS = hasTraining ? FEELINGS_TRAINING : FEELINGS_NUTRITION;
  const fechaCae = closeDate
    ? new Date(closeDate + "T00:00:00").toLocaleDateString("es-ES", { day: "2-digit", month: "long" })
    : null;
  const toast = usePortalToast();
  const draft = loadDraft(token, closeDate);
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
    const d = loadDraft(token, closeDate);
    setWeight(d.weight ?? ""); setWaist(d.waist ?? ""); setHip(d.hip ?? "");
    setArm(d.arm ?? ""); setThigh(d.thigh ?? ""); setFeelings(d.feelings ?? {});
    setAdhDiet(d.adhDiet ?? ""); setAdhTrain(d.adhTrain ?? "");
    setFreeMeals(d.freeMeals ?? ""); setChanges(d.changes ?? "");
    setHardest(d.hardest ?? ""); setNextGoal(d.nextGoal ?? "");
    setQuestions(d.questions ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, closeDate]);

  // Cada cambio queda guardado en el móvil: volver a la pestaña lo restaura.
  useEffect(() => {
    if (done) return;
    try {
      localStorage.setItem(DRAFT_KEY(token, closeDate), JSON.stringify({
        weight, waist, hip, arm, thigh, feelings,
        adhDiet, adhTrain, freeMeals, changes, hardest, nextGoal, questions,
      }));
    } catch { /* almacenamiento lleno o bloqueado: seguimos sin borrador */ }
  }, [weight, waist, hip, arm, thigh, feelings, adhDiet, adhTrain, freeMeals,
      changes, hardest, nextGoal, questions, token, closeDate, done]);

  const [confirmSend, setConfirmSend] = useState(false);
  // FOTOS de la revisión: el endpoint existía desde el principio y ninguna
  // pantalla lo llamaba, así que las fotos acababan sueltas en el WhatsApp del
  // coach y el "antes y ahora" del portal y del informe no se llenaba NUNCA.
  const [fotos, setFotos] = useState(0);
  const [subiendoFotos, setSubiendoFotos] = useState(false);
  const [errorFotos, setErrorFotos] = useState<string | null>(null);

  /** Sube hasta 4 fotos del período (el backend valida formato, 10 MB y tope).
   *  El `kind` va por orden: frontal, lateral, espalda y una extra de detalle,
   *  que es como las pide el propio cuestionario. */
  async function subirFotos(files: FileList | null) {
    if (!files || !files.length || subiendoFotos) return;
    const tipos = ["front", "side", "back", "detail"];
    const restantes = Math.max(0, 4 - fotos);
    const lote = Array.from(files).slice(0, restantes);
    if (!lote.length) {
      setErrorFotos("Ya has subido el máximo de 4 fotos.");
      return;
    }
    setSubiendoFotos(true);
    setErrorFotos(null);
    let subidas = 0;
    try {
      for (const f of lote) {
        await api.closePhotos([f], tipos[Math.min(fotos + subidas, 3)]);
        subidas += 1;
        setFotos(fotos + subidas);
      }
      toast.push(`${subidas} foto${subidas === 1 ? "" : "s"} subida${subidas === 1 ? "" : "s"} 📸`);
    } catch (e: any) {
      // Lo ya subido SE QUEDA: se dice cuántas entraron y qué falló.
      setErrorFotos(e?.message ?? "No se pudieron subir. Inténtalo de nuevo.");
    } finally {
      setSubiendoFotos(false);
    }
  }
  const allFeelings = FEELINGS.every((f) => feelings[f.key] > 0);
  // Coma o punto valen ("82,5"): el número se normaliza en un único sitio.
  const num = (v: string): number => Number(v.trim().replace(",", "."));
  // Validación de RANGOS en el móvil, ESPEJO EXACTO del backend (PeriodCloseIn):
  // si algo se sale, se avisa del campo concreto ANTES de enviar — el backend
  // rechazaría todo el cierre. Antes los rangos locales diferían de los del
  // servidor (brazo 90 cm pasaba aquí y reventaba allí con error críptico).
  const rangeError = (() => {
    const w = num(weight);
    if (weight !== "" && !(Number.isFinite(w) && w > 30 && w < 300)) return "Peso final: 30-300 kg";
    const per = (v: string, name: string, lo: number, hi: number) => {
      const n = num(v);
      return v !== "" && !(Number.isFinite(n) && n > lo && n < hi)
        ? `${name}: ${lo}-${hi} cm` : null;
    };
    const perErr = per(waist, "Cintura", 30, 250) ?? per(hip, "Cadera", 30, 250)
      ?? per(arm, "Brazo", 10, 80) ?? per(thigh, "Muslo", 20, 120);
    if (perErr) return perErr;
    const adh = (v: string, name: string) => {
      const n = num(v);
      // ENTERO 0-10: el backend lo exige (422 si llega "7,5") — mejor avisar
      // aquí que perder el envío de la revisión (auditoría crítica).
      return v !== "" && !(Number.isFinite(n) && Number.isInteger(n) && n >= 0 && n <= 10)
        ? `${name}: 0-10 sin decimales` : null;
    };
    const adhErr = (hasNutrition ? adh(adhDiet, "Adherencia dieta") : null)
      ?? (hasTraining ? adh(adhTrain, "Adherencia entreno") : null);
    if (adhErr) return adhErr;
    const fm = num(freeMeals);
    if (freeMeals !== "" && !(Number.isFinite(fm) && Number.isInteger(fm) && fm >= 0 && fm <= 50))
      return "Comidas libres: 0-50 entero";
    return null;
  })();
  // La dieta solo se exige si el plan la INCLUYE: al cliente de solo entreno
  // (tier train) se le obligaba a puntuar una dieta que no existe (auditoría).
  const canSubmit = num(weight) > 30 && allFeelings
    && (!hasNutrition || adhDiet !== "")
    && (!hasTraining || adhTrain !== "") && !rangeError && !busy;

  async function submit() {
    if (!canSubmit) return;
    setBusy(true);
    try {
      const vals = FEELINGS.map((f) => feelings[f.key]);
      const avg = Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
      await api.close({
        closing_weight_kg: num(weight),
        closing_rating: avg,
        closing_hardest: hardest || null,
        closing_questions: questions || null,
        closing_waist_cm: waist ? num(waist) : null,
        closing_hip_cm: hip ? num(hip) : null,
        closing_arm_cm: arm ? num(arm) : null,
        closing_thigh_cm: thigh ? num(thigh) : null,
        closing_feelings_json: feelings,
        adherence_diet_0_10: adhDiet === "" ? null : num(adhDiet),
        adherence_training_0_10: adhTrain === "" ? null : num(adhTrain),
        free_meals_count: freeMeals === "" ? null : num(freeMeals),
        closing_changes: changes || null,
        closing_next_goal: nextGoal || null,
      });
      setDone(true);
      try { localStorage.removeItem(DRAFT_KEY(token, closeDate)); } catch { /* sin borrador */ }
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
        <p className="mt-4 p-title">¡Revisión enviada!</p>
        <p className="mt-1 max-w-xs text-sm opacity-60">Recibirás informe y plan nuevo</p>
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
        <p className="mt-4 p-title">Revisión enviada</p>
        <p className="mt-1 max-w-xs text-sm opacity-60">
          Analizando · recibirás informe y plan
        </p>
      </div>
    );
  }

  // Bloqueada hasta el día 15: contador de días restantes.
  // Azul de marca: es información del ciclo (cuenta atrás), no una acción.
  if (!canClose) {
    return (
      <div className="flex flex-col items-center py-16 text-center">
        <div className="portal-ring-blue flex h-24 w-24 items-center justify-center rounded-full border-2"
          style={{ borderColor: brand.color_secondary, color: brand.color_secondary }}>
          <span className="text-4xl font-bold">{daysLeft != null && daysLeft > 0 ? daysLeft : "—"}</span>
        </div>
        <p className="mt-4 p-title">Revisión quincenal</p>
        <p className="mt-1 max-w-xs text-sm opacity-70">
          {daysLeft != null && daysLeft > 0
            ? `Disponible en ${daysLeft} día${daysLeft === 1 ? "" : "s"}`
            : "Disponible al día 14"}
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
        <h2 className="p-title">Revisión quincenal</h2>
        <p className="mt-0.5 text-xs opacity-60">Se va guardando sola.</p>
      </div>

      {/* 1 · Medidas */}
      <Section n={1} title="Medidas corporales">
        <p className="mb-2 text-xs opacity-50">En ayunas · cinta sin apretar</p>
        <Field label="Peso (kg)" required ancla="cierre.peso">
          <input type="text" inputMode="decimal"
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
      <Section n={2} title="¿Cómo te has sentido?" ancla="cierre.sensaciones">
        <p className="mb-2 text-xs opacity-50">1 = muy mal · 5 = excelente</p>
        <div className="space-y-3">
          {FEELINGS.map((f) => (
            <div key={f.key}>
              <p className="mb-1.5 text-sm">{f.label}</p>
              <div className="flex justify-between gap-1.5" role="radiogroup" aria-label={f.label}>
                {[1, 2, 3, 4, 5].map((n) => (
                  <button key={n} type="button" onClick={() => setFeelings((s) => ({ ...s, [f.key]: n }))}
                    aria-label={`${f.label}: ${n} de 5`}
                    aria-pressed={feelings[f.key] === n}
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

      {/* 3 · Adherencia. En solo-nutrición no se pregunta la del entreno (el
          cliente no tiene rutina): en su lugar van dieta + comidas libres. */}
      <Section n={3} title="Adherencia al plan">
        <div className="grid grid-cols-2 gap-3">
          {hasNutrition && (
            <NumField label="Dieta (0-10)" value={adhDiet} onChange={setAdhDiet} min={0} max={10} required ancla="cierre.adherencia.dieta" />
          )}
          {hasTraining ? (
            <NumField label="Entreno (0-10)" value={adhTrain} onChange={setAdhTrain} min={0} max={10} required ancla="cierre.adherencia.entreno" />
          ) : (
            <NumField label="Comidas libres (nº aprox.)" value={freeMeals} onChange={setFreeMeals} min={0} max={50} />
          )}
        </div>
        {hasTraining && hasNutrition && (
          <div className="mt-3">
            <NumField label="Comidas libres o saltadas" value={freeMeals} onChange={setFreeMeals} min={0} max={50} />
          </div>
        )}
      </Section>

      {/* 4 · Cambios */}
      <Section n={4} title="¿Algún cambio importante?">
        <textarea className="min-h-[64px] w-full rounded-xl border bg-transparent p-3 text-sm" style={{ borderColor: "rgba(128,128,128,0.2)" }}
          value={changes} onChange={(e) => setChanges(e.target.value)}
          placeholder="Lesiones · dolores · viajes · estrés · sueño" />
      </Section>

      {/* 5 · Qué cuesta */}
      <Section n={5} title="¿Qué te está costando más?">
        <textarea className="min-h-[64px] w-full rounded-xl border bg-transparent p-3 text-sm" style={{ borderColor: "rgba(128,128,128,0.2)" }}
          value={hardest} onChange={(e) => setHardest(e.target.value)}
          placeholder={hasTraining ? "Comidas · ejercicios · momentos difíciles" : "Comidas · antojos · momentos difíciles"} />
      </Section>

      {/* 6 · Objetivo */}
      <Section n={6} title="Tu objetivo · próximas 2 semanas">
        <textarea className="min-h-[56px] w-full rounded-xl border bg-transparent p-3 text-sm" style={{ borderColor: "rgba(128,128,128,0.2)" }}
          value={nextGoal} onChange={(e) => setNextGoal(e.target.value)}
          placeholder={hasTraining ? 'Ej.: "bajar 0,5 kg" · "mejorar sentadilla"' : 'Ej.: "bajar 0,5 kg" · "dormir 7 h"'} />
      </Section>

      {/* 7 · Fotos — banner informativo en azul de marca; icono y canal según
          cómo recibe este cliente sus entregas (Pro → WhatsApp; resto → email). */}
      <Section n={7} title="Fotos de progreso">
        <p className="text-sm opacity-80">
          3 fotos: <b>frontal · lateral · espalda</b>
          <span className="mt-0.5 block opacity-70">Fondo neutro · sin filtros · mismo sitio</span>
        </p>
        <input id="fotos-cierre" type="file" accept="image/*" multiple className="hidden"
          onChange={(e) => { subirFotos(e.target.files); e.target.value = ""; }} />
        <button
          onClick={() => document.getElementById("fotos-cierre")?.click()}
          disabled={subiendoFotos || fotos >= 4}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed px-4 py-3 text-sm font-medium disabled:opacity-60"
          style={{ borderColor: `${brand.color_secondary}77` }}
        >
          {subiendoFotos ? <Loader2 size={16} className="animate-spin" /> : <Camera size={16} />}
          {fotos > 0
            ? `${fotos} foto${fotos === 1 ? "" : "s"} subida${fotos === 1 ? "" : "s"}${fotos >= 4 ? "" : " · añadir más"}`
            : "Subir mis fotos aquí"}
        </button>
        {errorFotos && (
          <p role="alert" className="mt-2 text-sm" style={{ color: "var(--p-danger)" }}>{errorFotos}</p>
        )}
        {/* La vía de siempre sigue disponible: quien prefiera mandarlas por su
            canal habitual no se queda fuera. */}
        <div className="mt-3 flex items-start gap-2 rounded-xl border p-3 text-sm" style={{ borderColor: `${brand.color_secondary}55`, background: `${brand.color_secondary}10` }}>
          {directContact
            ? <MessageCircle size={18} style={{ color: brand.color_secondary }} className="mt-0.5 shrink-0" />
            : <Mail size={18} style={{ color: brand.color_secondary }} className="mt-0.5 shrink-0" />}
          <p className="opacity-80">
            ¿Prefieres mandarlas por <b>{directContact ? "WhatsApp" : "email"}</b>? También vale.
          </p>
        </div>
      </Section>

      <Field label="Dudas para tu coach (opcional)">
        <textarea className="min-h-[56px] w-full rounded-xl border bg-transparent p-3 text-sm" style={{ borderColor: "rgba(128,128,128,0.2)" }}
          value={questions} onChange={(e) => setQuestions(e.target.value)} placeholder="Cualquier pregunta…" />
      </Field>

      {/* Envío en DOS toques: cierra el período y deja Diario/Entreno en
          pausa — un roce accidental no puede costar la quincena. */}
      {!confirmSend ? (
        <button onClick={() => { if (canSubmit) { setConfirmSend(true); window.setTimeout(() => setConfirmSend(false), 6000); } }}
          disabled={!canSubmit} className="portal-btn3d w-full py-4 text-sm uppercase tracking-wide">
          Enviar revisión a mi coach
        </button>
      ) : (
        <div className="space-y-2">
          <p className="text-center text-xs opacity-70">
            Sin edición · diario en pausa
          </p>
          <div className="flex gap-2">
            <button onClick={() => setConfirmSend(false)} className="w-1/3 rounded-xl border py-3 text-sm" style={{ borderColor: "rgba(128,128,128,0.3)" }}>
              Aún no
            </button>
            <button onClick={() => { setConfirmSend(false); submit(); }} disabled={!canSubmit}
              className="portal-btn3d w-2/3 py-3 text-sm uppercase tracking-wide">
              {busy ? "Enviando…" : "Sí, enviar"}
            </button>
          </div>
        </div>
      )}
      {!canSubmit && !busy && (
        <p className="text-center text-xs opacity-40">
          {rangeError ?? (() => {
            // Decir QUÉ falta, no un genérico: con 7 secciones el bloqueo era
            // invisible (una sensación sin puntuar dejaba el botón gris mudo).
            // Cada cosa que falta se PULSA y te lleva al campo, marcado.
            // Decirle al cliente "falta la adherencia" y que la busque entre
            // seis secciones es la mitad del trabajo.
            const faltan: { texto: string; ancla: string }[] = [];
            if (!(num(weight) > 30)) faltan.push({ texto: "peso final", ancla: "cierre.peso" });
            const sinPuntuar = FEELINGS.filter((f) => !(feelings[f.key] > 0)).length;
            if (sinPuntuar > 0) faltan.push({
              texto: sinPuntuar === 1 ? "1 sensación" : `${sinPuntuar} sensaciones`,
              ancla: "cierre.sensaciones",
            });
            if (hasNutrition && adhDiet === "") faltan.push({ texto: "adherencia dieta", ancla: "cierre.adherencia.dieta" });
            if (hasTraining && adhTrain === "") faltan.push({ texto: "adherencia entreno", ancla: "cierre.adherencia.entreno" });
            if (!faltan.length) return <>Falta: peso · sensaciones · adherencia</>;
            return (
              <>
                Falta:{" "}
                {faltan.map((f, i) => (
                  <span key={f.ancla}>
                    {i > 0 && " · "}
                    <button type="button" onClick={() => void irYMarcar(f.ancla)}
                      className="underline decoration-dotted underline-offset-2">
                      {f.texto}
                    </button>
                  </span>
                ))}
              </>
            );
          })()}
        </p>
      )}
    </div>
  );
}

function Section({ n, title, children, ancla: nombreAncla }: {
  n: number; title: string; children: React.ReactNode; ancla?: string;
}) {
  return (
    <div {...(nombreAncla ? ancla(nombreAncla) : {})}>
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

function Field({ label, required, children, ancla: nombreAncla }: {
  label: string; required?: boolean; children: React.ReactNode; ancla?: string;
}) {
  return (
    <div {...(nombreAncla ? ancla(nombreAncla) : {})}>
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
      <input type="text" inputMode="decimal"
        className="mt-1 w-full bg-transparent text-lg font-semibold outline-none"
        style={{ caretColor: "var(--p-accent-2)" }}
        value={value} onChange={(e) => onChange(e.target.value)} placeholder="—" />
    </label>
  );
}

function NumField({ label, value, onChange, min, max, required, ancla: nombreAncla }: {
  label: string; value: string; onChange: (v: string) => void; min: number; max: number;
  required?: boolean; ancla?: string;
}) {
  // min/max informan la etiqueta y el rango se valida en `rangeError` (mismo
  // rango que el backend); el input es text para que la coma no vacíe el valor.
  void min; void max;
  return (
    <label className="portal-card block p-3" {...(nombreAncla ? ancla(nombreAncla) : {})}>
      <span className="block text-xs opacity-50">{label} {required && <span style={{ color: "#C2453A" }}>*</span>}</span>
      <input type="text" inputMode="numeric"
        className="mt-1 w-full bg-transparent text-lg font-semibold outline-none"
        style={{ caretColor: "var(--p-accent-2)" }}
        value={value} onChange={(e) => onChange(e.target.value)} placeholder="—" />
    </label>
  );
}
