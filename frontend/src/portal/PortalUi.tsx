import type { LucideIcon } from "lucide-react";

/** Piezas de UI compartidas del portal: carga (skeleton) y estados vacíos. */

/** Fecha de HOY en horario LOCAL del cliente (YYYY-MM-DD).
 *  OJO: toISOString() da la fecha UTC — en España, a partir de las 22-23 h
 *  cambia de día y el registro caería en la fecha equivocada. */
export function localToday(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
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
