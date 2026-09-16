/**
 * LA ESTRUCTURA DE SU PLANIFICACIÓN, en un solo sitio.
 *
 * Hasta ahora la rutina era SIEMPRE una semana de lunes a domingo con un
 * mesociclo de cuatro semanas y una revisión de catorce días: tres decisiones
 * de entrenador tomadas por el sistema, sin preguntar y sin poder cambiarlas.
 * Eso obliga a encajar a la persona dentro del split en vez de al revés — con
 * siete días no se puede dar más frecuencia a una espalda que la necesita sin
 * quitársela a otra cosa.
 *
 * Aquí se decide, arriba de la pestaña Planificación y antes de generar nada:
 *   · cuántos días dura una vuelta al split (2-10),
 *   · cuántas vueltas dura el mesociclo (1-8) y cómo progresa,
 *   · qué grupos van con PRIORIDAD y cuáles en mantenimiento,
 *   · cuántos días dura su revisión (7-31).
 *
 * ⚠️ Las CIFRAS no se calculan aquí. El volumen y la frecuencia por grupo
 * salen de `GET /clients/{id}/training-structure`, que es el MISMO contrato que
 * recibe la IA y que después validan los guardarraíles. Una cuenta hecha en la
 * pantalla acabaría enseñando un número y generando otro.
 */
import { useCallback, useEffect, useState } from "react";
import { Layers, Loader2, Pencil, RotateCw, Sparkles, Target } from "lucide-react";

import { api } from "../lib/api";
import { ancla } from "../lib/anchors";
// La MISMA puerta que el resto del sistema para leer el ciclo de un plan
// (`lib/ciclo` ⇄ `services/training_cycle`): dos formas de deducirlo dan
// dos respuestas y la tarjeta acabaría contradiciendo al plan.
import { diasDeCiclo, etiquetaDeBloque } from "../lib/ciclo";
import type { ClientOut, TrainingStructureOut } from "../types";
import { SectionHeader, Spinner, useToast } from "./ui";

const GRUPO_ES: Record<string, string> = {
  pecho: "Pecho", espalda: "Espalda", hombros: "Hombros", biceps: "Bíceps",
  triceps: "Tríceps", cuadriceps: "Cuádriceps", isquios: "Isquios",
  gluteos: "Glúteos", gemelos: "Gemelos", core: "Core",
};

/** El ciclo de un grupo: normal → prioridad → mantenimiento → normal. Un solo
 *  control con tres estados: dos listas de casillas por grupo serían dieciséis
 *  casillas y la posibilidad de marcar las dos a la vez. */
type Papel = "normal" | "prioridad" | "mantenimiento";

function siguientePapel(p: Papel): Papel {
  return p === "normal" ? "prioridad" : p === "prioridad" ? "mantenimiento" : "normal";
}

export default function EstructuraEntrenamiento({
  client, onSaved, hasTraining = true, training, generating = false, onAplicar,
}: {
  client: ClientOut;
  /** Para que la ficha se refresque: el ciclo cambia lo que se genera. */
  onSaved?: () => void;
  /** Un cliente de SOLO DIETA no tiene entrenamiento que estructurar: se le
   *  enseña únicamente el ritmo de revisión, que sí es suyo. */
  hasTraining?: boolean;
  /** El `training_json` del plan VIGENTE, para poder decir si lo que hay
   *  publicado ya sigue esta estructura o todavía es el anterior. */
  training?: any;
  generating?: boolean;
  /** Aplicar la estructura nueva rehaciendo el plan (con IA o a mano). Sin
   *  esto, cambiar el ciclo no tenía NINGUNA salida con un plan ya publicado. */
  onAplicar?: (conIa: boolean) => void;
}) {
  const toast = useToast();
  const [data, setData] = useState<TrainingStructureOut | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [abierto, setAbierto] = useState(false);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      setData(await api.trainingStructure(client.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo cargar");
    } finally {
      setCargando(false);
    }
  }, [client.id]);

  useEffect(() => { void cargar(); }, [cargar]);

  async function guardar(patch: Partial<ClientOut>) {
    setGuardando(true);
    try {
      await api.updateClient(client.id, patch);
      await cargar();
      onSaved?.();
    } catch (e) {
      toast.push(e instanceof Error ? e.message : "No se pudo guardar", "error");
    } finally {
      setGuardando(false);
    }
  }

  if (cargando && !data) {
    return (
      <div className="card flex items-center gap-2 p-4 text-sm text-zinc-500">
        <Spinner /> Cargando la estructura…
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="card p-4 text-sm">
        <p className="text-zinc-400">{error || "No se pudo cargar la estructura."}</p>
        <button type="button" className="btn-ghost mt-2" onClick={() => void cargar()}>
          <RotateCw size={14} /> Reintentar
        </button>
      </div>
    );
  }

  const papelDe = (g: string): Papel =>
    data.muscle_priority.includes(g) ? "prioridad"
      : data.muscle_deprioritized.includes(g) ? "mantenimiento" : "normal";

  function cambiarPapel(g: string) {
    if (!data) return;
    const nuevo = siguientePapel(papelDe(g));
    const prio = data.muscle_priority.filter((x) => x !== g);
    const baja = data.muscle_deprioritized.filter((x) => x !== g);
    if (nuevo === "prioridad") prio.push(g);
    if (nuevo === "mantenimiento") baja.push(g);
    void guardar({ muscle_priority: prio, muscle_deprioritized: baja });
  }

  const conPapel = data.muscle_priority.length + data.muscle_deprioritized.length;
  const resumen = (hasTraining ? [
    data.semanal ? "Semana (7 días)" : `Ciclo de ${data.cycle_days} días`,
    `${data.sessions_target} sesion${data.sessions_target === 1 ? "" : "es"}`,
    `${data.mesocycle_blocks} ${data.block_label.toLowerCase()}${data.mesocycle_blocks === 1 ? "" : "s"}`,
  ] : []).concat(`revisión ${data.review_days} d`).join(" · ");

  // ¿LO PUBLICADO YA SIGUE ESTA ESTRUCTURA? La tarjeta decía «Ciclo de 10 días ·
  // 6 sesiones» mientras el cliente tenía delante un plan de lunes a viernes:
  // describía una rutina que no existe, sin avisar y sin forma de aplicarla.
  // Exige SESIONES de verdad: con `training = {}` (un plan sin entreno) se
  // deduciría "ciclo 7" y se avisaría de un desfase contra una rutina que no
  // existe.
  const delPlan = hasTraining && training && (training.sessions ?? []).length > 0 ? {
    ciclo: diasDeCiclo(training),
    bloques: (training.weekly_progression ?? []).length || null,
    sesiones: (training.sessions ?? []).length,
  } : null;
  const desfase: string[] = [];
  if (delPlan) {
    if (delPlan.ciclo !== data.cycle_days) {
      desfase.push(delPlan.ciclo === 7
        ? "va por semanas (lunes a domingo)"
        : `es un ciclo de ${delPlan.ciclo} días`);
    }
    if (delPlan.bloques && delPlan.bloques !== data.mesocycle_blocks) {
      desfase.push(`tiene ${delPlan.bloques} ${etiquetaDeBloque(delPlan.ciclo).toLowerCase()}`
        + `${delPlan.bloques === 1 ? "" : "s"}`);
    }
  }

  return (
    <div className="card p-4" {...ancla("plan.estructura")}>
      <SectionHeader
        title={hasTraining ? "Estructura del entrenamiento" : "Ritmo de revisión"}
        icon={Layers}
        count={hasTraining && conPapel > 0 ? `${conPapel} con prioridad` : undefined}
        right={
          <button
            type="button"
            // shrink-0 + nowrap: a 390 px el título, el chip y el botón
            // comparten fila y el botón se comprimía hasta partir su palabra.
            className="btn-ghost shrink-0 whitespace-nowrap text-xs"
            data-desplegable-toggle
            aria-expanded={abierto}
            onClick={() => setAbierto((v) => !v)}
          >
            {abierto ? "Cerrar" : "Cambiar"}
          </button>
        }
      />
      <p className="text-sm text-zinc-300">{resumen}</p>
      {hasTraining && (
        <p className="mt-1 text-xs text-zinc-500">
          {data.semanal
            ? "Su rutina va de lunes a domingo, como siempre."
            : `Su rutina NO va por semanas: ${data.cycle_days} días que se repiten. `
              + `El mesociclo completo son ${data.total_days} días.`}
        </p>
      )}

      {/* EL DESFASE, DICHO Y CON SALIDA. Cambiar el ciclo con un plan ya
          publicado no tocaba nada y no lo avisaba nadie: la tarjeta describía
          una rutina y debajo había otra. La dieta sí tenía sus dos botones
          («Estructura de comidas del día»); el entreno no tenía ninguno, y un
          cliente de SOLO ENTRENO se quedaba sin ningún camino de rehacer. */}
      {desfase.length > 0 && (
        <div
          className="mt-3 rounded-lg border p-3"
          style={{ borderColor: "rgba(154,107,21,0.45)", background: "rgba(154,107,21,0.09)" }}
        >
          <p className="text-xs font-medium text-amber-300">
            El plan que tiene el cliente todavía {desfase.join(" y ")}.
          </p>
          <p className="mt-1 text-xs text-zinc-400">
            Esta estructura se aplica al rehacer el plan. Hasta entonces, lo que
            ve el cliente es lo anterior.
          </p>
          {onAplicar && (
            <div className="mt-2.5 flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="btn btn-primary text-xs"
                disabled={generating}
                onClick={() => {
                  if (!window.confirm(
                    "¿Rehacer el plan con esta estructura? Gasta créditos de IA y "
                    + "sustituye la versión actual, ediciones manuales incluidas "
                    + "(queda en el historial).")) return;
                  onAplicar(true);
                }}
              >
                <Sparkles size={14} /> {generating ? "Rehaciendo…" : "Rehacer con IA"}
              </button>
              <button
                type="button"
                className="btn btn-ghost text-xs"
                disabled={generating}
                title="Rehace la base con esta estructura y la deja en borrador para que la termines tú"
                onClick={() => onAplicar(false)}
              >
                <Pencil size={14} /> Rehacer a mano · 0 créditos
              </button>
            </div>
          )}
        </div>
      )}

      {abierto && (
        <div className="mt-4 space-y-4" data-open="true">
          {/* Ciclo, mesociclo y prioridad muscular son del ENTRENAMIENTO: a un
              cliente de solo dieta no se le enseñan —no cambian nada de lo
              suyo— igual que a uno de solo entreno no se le enseña la
              estructura de comidas. La revisión sí es de todos. */}
          {hasTraining && (<>
          {/* --- CICLO --------------------------------------------------- */}
          <div>
            <label className="block text-xs font-medium text-zinc-400" htmlFor="ciclo-dias">
              Días que dura una vuelta al split
            </label>
            <div className="mt-1.5 flex flex-wrap items-center gap-2">
              <select
                id="ciclo-dias"
                className="input h-11 w-auto"
                value={data.cycle_days}
                disabled={guardando}
                onChange={(e) => void guardar({ cycle_days: Number(e.target.value) })}
              >
                {Array.from(
                  { length: data.cycle_max - data.cycle_min + 1 },
                  (_, i) => data.cycle_min + i,
                ).map((n) => (
                  <option key={n} value={n}>
                    {n} días{n === data.cycle_default ? " · semana" : ""}
                  </option>
                ))}
              </select>
              <span className="text-xs text-zinc-500">
                Con {data.training_days ?? "—"} día(s)/semana declarados, caben{" "}
                <strong className="text-zinc-300">{data.sessions_target}</strong> sesiones
                en el ciclo.
              </span>
            </div>
          </div>

          {/* --- MESOCICLO ----------------------------------------------- */}
          <div>
            <label className="block text-xs font-medium text-zinc-400" htmlFor="meso-bloques">
              {data.block_label}s del mesociclo
            </label>
            <div className="mt-1.5 flex flex-wrap items-center gap-2">
              <select
                id="meso-bloques"
                className="input h-11 w-auto"
                value={data.mesocycle_blocks}
                disabled={guardando}
                onChange={(e) => void guardar({ mesocycle_blocks: Number(e.target.value) })}
              >
                {Array.from(
                  { length: data.blocks_max - data.blocks_min + 1 },
                  (_, i) => data.blocks_min + i,
                ).map((n) => (
                  <option key={n} value={n}>
                    {n} {data.block_label.toLowerCase()}{n === 1 ? "" : "s"}
                    {n === data.blocks_default ? " · por defecto" : ""}
                  </option>
                ))}
              </select>
              <span className="text-xs text-zinc-500">
                {data.mesocycle_blocks >= 3
                  ? "Adaptación, progresión y descarga al final."
                  : "Demasiado corto para una descarga: no se programa."}
              </span>
            </div>
          </div>

          {/* --- PRIORIDAD MUSCULAR -------------------------------------- */}
          <div>
            <p className="text-xs font-medium text-zinc-400">
              Prioridad por grupo muscular
            </p>
            <p className="mt-0.5 text-xs text-zinc-500">
              Pulsa un grupo para subirlo a prioridad, bajarlo a mantenimiento o
              dejarlo normal. El volumen es finito: subir uno significa que otro baja.
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {data.muscle_groups.map((g) => {
                const papel = papelDe(g);
                const v = data.volume.groups[g];
                const color = papel === "prioridad" ? "var(--brand-accent)"
                  : papel === "mantenimiento" ? "#7A7F8A" : "#4A5160";
                return (
                  <button
                    key={g}
                    type="button"
                    disabled={guardando}
                    onClick={() => cambiarPapel(g)}
                    className="rounded-lg border px-2.5 py-2 text-left text-xs"
                    style={{
                      minHeight: 44,
                      borderColor: color,
                      background: papel === "normal" ? "transparent"
                        : `color-mix(in srgb, ${color} 14%, transparent)`,
                    }}
                    title={`${GRUPO_ES[g] || g}: ${v?.target ?? "—"} series por ciclo`}
                  >
                    <span className="block font-medium text-zinc-200">
                      {GRUPO_ES[g] || g}
                    </span>
                    <span className="block tabular-nums" style={{ color }}>
                      {v ? `${v.target} series · ${v.min_frequency}×` : "—"}
                      {papel === "prioridad" ? " ▲" : papel === "mantenimiento" ? " ▼" : ""}
                    </span>
                  </button>
                );
              })}
            </div>
            <p className="mt-1.5 text-[11px] text-zinc-500">
              Series por {data.semanal ? "semana" : `ciclo de ${data.cycle_days} días`} y
              frecuencia mínima. Las calcula el sistema a partir de su nivel
              ({data.volume.level}) y su objetivo; son las mismas que se le entregan a
              la IA y las que validan los guardarraíles.
            </p>
          </div>

          </>)}

          {/* --- REVISIÓN ------------------------------------------------ */}
          <div>
            <label className="block text-xs font-medium text-zinc-400" htmlFor="revision-dias">
              Días que dura su revisión
            </label>
            <div className="mt-1.5 flex flex-wrap items-center gap-2">
              <input
                id="revision-dias"
                type="number"
                className="input h-11 w-28"
                min={data.review_min}
                max={data.review_max}
                defaultValue={data.review_days}
                disabled={guardando}
                onBlur={(e) => {
                  const n = Number(e.target.value);
                  if (!Number.isFinite(n) || n === data.review_days) return;
                  if (n < data.review_min || n > data.review_max) {
                    toast.push(
                      `La revisión va de ${data.review_min} a ${data.review_max} días`,
                      "error");
                    e.target.value = String(data.review_days);
                    return;
                  }
                  void guardar({ review_days: n });
                }}
              />
              <span className="text-xs text-zinc-500">
                Afecta al PRÓXIMO período: el que está abierto conserva sus fechas.
              </span>
            </div>
          </div>

          {guardando && (
            <p className="flex items-center gap-1.5 text-xs text-zinc-500">
              <Loader2 size={13} className="animate-spin" /> Guardando…
            </p>
          )}
          {hasTraining && (
            <p className="flex items-start gap-1.5 text-xs text-zinc-500">
              <Target size={13} className="mt-0.5 shrink-0" />
              Cambiar la estructura NO toca el plan que ya tiene: cuando no
              coincidan te lo digo aquí arriba, con el botón para rehacerlo.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
