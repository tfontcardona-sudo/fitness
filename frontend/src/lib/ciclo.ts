/**
 * EL CICLO DE ENTRENAMIENTO, en el front.
 *
 * Espejo de `backend/app/services/training_cycle.py`. Aquí solo vive lo que la
 * PANTALLA necesita para pintar y para editar: cuántos días dura una vuelta al
 * split, qué día del ciclo es cada sesión y cómo se llama un bloque. Nada que
 * decida contenido del plan — eso lo calcula el backend, como los macros.
 *
 * ⚠️ Si cambian los topes (2-10 días, 1-8 bloques), cámbialos en los DOS: el
 * backend los valida en el esquema Pydantic y un desajuste se manifiesta como
 * un 422 que el coach no entiende.
 */
export const SEMANA = 7;
export const MIN_DIAS_CICLO = 2;
export const MAX_DIAS_CICLO = 10;
export const MIN_BLOQUES = 1;
export const MAX_BLOQUES = 8;

/** Cómo se llama cada día de la semana delante del cliente. */
export const DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes",
                            "Sábado", "Domingo"];

const DIAS_SLUG = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"];

function sinAcentos(t: string): string {
  return t.normalize("NFKD").replace(/[̀-ͯ]/g, "");
}

/** Cuántos días dura una vuelta al split. Sin dato, la semana de siempre. */
export function diasDeCiclo(training: { cycle_days?: number | null } | null | undefined): number {
  const n = Number(training?.cycle_days);
  if (!Number.isFinite(n)) return SEMANA;
  return Math.max(MIN_DIAS_CICLO, Math.min(MAX_DIAS_CICLO, Math.trunc(n)));
}

export function esSemanal(ciclo: number): boolean {
  return ciclo === SEMANA;
}

/** Cómo se llama una vuelta al ciclo: «Semana» cuando ES la semana (que es como
 *  lo llama todo el mundo) y «Bloque» cuando rota. */
export function etiquetaDeBloque(ciclo: number): string {
  return esSemanal(ciclo) ? "Semana" : "Bloque";
}

/** Qué día del ciclo (1…ciclo) es esta sesión, o null si no se sabe.
 *  Mismo orden de preferencia que el backend: `day_index` explícito, nombre del
 *  día de la semana, y por último «Día 3» (o un número suelto si el ciclo rota). */
export function diaDeSesion(
  sess: { day_index?: number | null; day?: string | null } | null | undefined,
  ciclo: number,
): number | null {
  if (!sess) return null;
  const idx = Number(sess.day_index);
  if (Number.isFinite(idx) && idx >= 1 && idx <= ciclo) return Math.trunc(idx);
  const texto = sinAcentos(String(sess.day ?? "").trim().toLowerCase());
  const pos = DIAS_SLUG.indexOf(texto);
  if (pos >= 0) return pos + 1 <= ciclo ? pos + 1 : null;
  const re = esSemanal(ciclo) ? /^d(?:ia)?\s*(\d{1,2})$/ : /^(?:d(?:ia)?\s*)?(\d{1,2})$/;
  const m = re.exec(texto);
  if (m) {
    const n = Number(m[1]);
    if (n >= 1 && n <= ciclo) return n;
  }
  return null;
}

/** El primer día del ciclo que no tenga sesión, o null si están todos ocupados. */
export function primerDiaLibre(
  sesiones: Array<{ day_index?: number | null; day?: string | null }>,
  ciclo: number,
): number | null {
  const ocupados = new Set(sesiones.map((s) => diaDeSesion(s, ciclo)).filter((n): n is number => n != null));
  for (let n = 1; n <= ciclo; n += 1) if (!ocupados.has(n)) return n;
  return null;
}
