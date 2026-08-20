import { useRef, useState } from "react";
import type { LucideIcon } from "lucide-react";

/** Piezas de UI compartidas del portal: carga (skeleton) y estados vacíos. */

/** Fecha de HOY en horario LOCAL del cliente (YYYY-MM-DD).
 *  OJO: toISOString() da la fecha UTC — en España, a partir de las 22-23 h
 *  cambia de día y el registro caería en la fecha equivocada. */
export function localToday(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Número en formato es-ES (coma decimal, punto de miles), máx. 1 decimal:
 *  82.5 → "82,5" · 2150 → "2.150". Evita colas de coma flotante en pantalla
 *  ("0.30000000000000004"). */
export function fmt1(n: number): string {
  return n.toLocaleString("es-ES", { maximumFractionDigits: 1 });
}

/** Fecha corta legible "14 ago" (es-ES, sin el punto de la abreviatura del
 *  mes). Acepta "YYYY-MM-DD" o un ISO completo; si no se puede interpretar,
 *  devuelve el texto tal cual. */
export function shortDate(iso: string): string {
  const d = new Date(iso + (iso.length === 10 ? "T00:00:00" : ""));
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("es-ES", { day: "numeric", month: "short" }).replace(/\./g, "");
}

/** Skeleton de carga: la interfaz nunca parece congelada ni "salta" al cargar. */
export function Loading() {
  return (
    <div className="animate-pulse space-y-4" aria-hidden="true">
      <div className="h-5 w-40 rounded-lg" style={{ background: "var(--p-line)" }} />
      <div className="flex gap-2">
        <div className="h-14 w-28 rounded-xl" style={{ background: "var(--p-line)" }} />
        <div className="h-14 w-28 rounded-xl" style={{ background: "var(--p-line)" }} />
      </div>
      <div className="portal-card h-44 opacity-60" />
      <div className="portal-card h-44 opacity-40" />
    </div>
  );
}

export function Empty({ icon: Icon, title, hint }: { icon: LucideIcon; title: string; hint: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="portal-card flex h-14 w-14 items-center justify-center rounded-2xl">
        <Icon size={24} className="opacity-40" />
      </div>
      <p className="mt-4 text-base font-semibold">{title}</p>
      <p className="mt-1 max-w-xs text-sm opacity-60">{hint}</p>
    </div>
  );
}

/**
 * Campo numérico del portal A PRUEBA DE MÓVIL. Reglas:
 *  - `type="text"` + inputMode decimal: acepta COMA o punto ("82,5" vale) —
 *    con type="number", una coma no localizada dejaba e.target.value en "" y
 *    el autosave enviaba null, BORRANDO el dato ya guardado en el servidor.
 *  - Lo tecleado se conserva mientras el campo tiene el foco (nada lo pisa).
 *  - Un valor inválido o fuera de rango NO se emite (no viaja al autosave):
 *    se marca en rojo hasta corregirlo; vaciar el campo sí emite null
 *    (intención clara de borrar el dato).
 */
export function useDecimalField(
  value: number | null | undefined,
  onChange: (v: number | null) => void,
  opts: { min?: number; max?: number; integer?: boolean } = {},
) {
  const [raw, setRaw] = useState<string | null>(null);
  const focused = useRef(false);

  const parse = (s: string): number | null => {
    const t = s.trim().replace(",", ".");
    if (t === "") return null;
    const n = Number(t);
    if (!Number.isFinite(n)) return NaN as unknown as number; // inválido
    return n;
  };
  const outOfRange = (n: number) =>
    (opts.min != null && n < opts.min) || (opts.max != null && n > opts.max)
    || (opts.integer === true && !Number.isInteger(n));

  const parsed = raw !== null ? parse(raw) : null;
  const invalid = raw !== null && raw.trim() !== ""
    && (parsed === null || Number.isNaN(parsed) || outOfRange(parsed as number));

  return {
    invalid,
    inputProps: {
      type: "text" as const,
      inputMode: "decimal" as const,
      value: raw !== null ? raw : (value ?? ""),
      onFocus: () => { focused.current = true; },
      onChange: (e: { target: { value: string } }) => {
        const s = e.target.value;
        setRaw(s);
        const n = parse(s);
        if (n === null) { onChange(null); return; }        // vaciado deliberado
        if (Number.isNaN(n) || outOfRange(n)) return;      // inválido: no viaja
        onChange(n);
      },
      onBlur: () => {
        focused.current = false;
        // Con texto inválido se CONSERVA lo tecleado y la marca roja (borrarlo
        // sería mentir al cliente); con valor válido se muestra el canónico.
        setRaw((r) => {
          if (r === null) return null;
          const n = parse(r);
          const bad = r.trim() !== "" && (Number.isNaN(n) || (n !== null && outOfRange(n)));
          return bad ? r : null;
        });
      },
    },
  };
}
