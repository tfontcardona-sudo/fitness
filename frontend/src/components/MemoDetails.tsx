import { useEffect, useRef, useState } from "react";
import { ChevronRight } from "lucide-react";

/** <details> con MEMORIA: recuerda si el usuario lo abrió o cerró (localStorage
 *  por `memoKey`), incluso al recargar la página. Con animación suave de
 *  apertura y un chevron que gira. Si nunca se ha tocado, usa `defaultOpen`. */
export function MemoDetails({
  memoKey, defaultOpen = false, summary, children, className, style, summaryClassName,
}: {
  memoKey: string;
  defaultOpen?: boolean;
  summary: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  summaryClassName?: string;
}) {
  const storeKey = `dq_open_${memoKey}`;
  const [open, setOpen] = useState<boolean>(() => {
    try {
      const v = localStorage.getItem(storeKey);
      return v === null ? defaultOpen : v === "1";
    } catch {
      return defaultOpen;
    }
  });
  const first = useRef(true);

  // Persistir SOLO cuando el usuario cambia el estado (no en el montaje): así
  // `defaultOpen` sigue mandando hasta que se toca, y un bloque que pasa a
  // tener contenido crítico se auto-expande aunque antes existiera sin tocar.
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    try { localStorage.setItem(storeKey, open ? "1" : "0"); } catch { /* almacenamiento bloqueado */ }
  }, [open, storeKey]);

  return (
    <div className={className} style={style} data-open={open}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className={`flex w-full cursor-pointer items-center gap-2 text-left ${summaryClassName ?? ""}`}
      >
        <ChevronRight
          size={14}
          className="shrink-0 opacity-60 transition-transform duration-200"
          style={{ transform: open ? "rotate(90deg)" : "none" }}
        />
        <span className="min-w-0 flex-1">{summary}</span>
      </button>
      <div
        className="grid transition-[grid-template-rows] duration-200 ease-out"
        style={{ gridTemplateRows: open ? "1fr" : "0fr" }}
      >
        <div className="overflow-hidden">{open && children}</div>
      </div>
    </div>
  );
}
