import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { AlertTriangle, Check, Loader2, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ClientStatus } from "../types";
import { STATUS_LABEL, STATUS_TONE } from "../lib/format";
import { useDismiss, useModalFocus } from "../lib/useDismiss";

/* ---------------------------------------------------------- StatusBadge ---- */

export function StatusBadge({ status }: { status: ClientStatus }) {
  const tone = STATUS_TONE[status];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
      style={{ background: `${tone}1a`, color: tone }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: tone }} />
      {STATUS_LABEL[status]}
    </span>
  );
}

/* -------------------------------------------------------------- Spinner ---- */

export function Spinner({ className = "" }: { className?: string }) {
  return <Loader2 className={`animate-spin ${className}`} size={18} />;
}

export function PageLoader() {
  return (
    <div className="flex h-full min-h-[300px] items-center justify-center text-zinc-500">
      <Spinner className="text-zinc-400" />
    </div>
  );
}

/* ----------------------------------------------------------- EmptyState ---- */

export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string;
  // OPCIONAL: obligarlo forzaba a cada pantalla a inventarse una frase de
  // relleno bajo un título que ya lo decía todo.
  hint?: string;
  action?: ReactNode;
}) {
  // Un estado vacío es una invitación a actuar (skill): título + siguiente paso.
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed py-12 text-center"
      style={{ borderColor: "var(--line-strong)" }}>
      <p className="text-sm font-medium text-zinc-200">{title}</p>
      {hint && <p className="mt-1 max-w-xs text-sm text-zinc-500">{hint}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

/* ---------------------------------------------------------------- Toast ---- */

/** Acción opcional del aviso: si el mensaje habla de OTRO sitio, el aviso
 *  lleva ahí de un clic en vez de decirle al coach dónde buscarlo. */
type ToastAction = { label: string; onClick: () => void };
type Toast = { id: number; message: string; tone: "ok" | "error"; action?: ToastAction };
type ToastCtx = {
  push: (message: string, tone?: "ok" | "error", action?: ToastAction) => void;
};

const ToastContext = createContext<ToastCtx | null>(null);

export function useToast(): ToastCtx {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast fuera de ToastProvider");
  return ctx;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const push = useCallback((message: string, tone: "ok" | "error" = "ok",
                           action?: ToastAction) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, message, tone, action }]);
    // Con acción dura más: hay que darle tiempo a leerla y pulsarla.
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)),
               action ? 8000 : 4000);
  }, []);

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      {/* pointer-events-none: informa sin robar clics; role=status → accesible */}
      <div
        className="pointer-events-none fixed bottom-5 right-5 z-50 flex flex-col gap-2"
        role="status"
        aria-live="polite"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className="animate-rise flex items-center gap-2.5 rounded-xl border px-4 py-3 text-sm shadow-xl"
            style={{
              background: "var(--surface-raised)",
              borderColor: t.tone === "error" ? "#C2453A55" : "var(--line-strong)",
            }}
          >
            <span
              className="flex h-5 w-5 items-center justify-center rounded-full"
              style={{ background: t.tone === "error" ? "#C2453A22" : "#E8833A22" }}
            >
              {t.tone === "error" ? (
                <AlertTriangle size={13} color="#C2453A" />
              ) : (
                <Check size={13} color="#E8833A" />
              )}
            </span>
            <span className="text-zinc-100">{t.message}</span>
            {t.action && (
              <button
                onClick={() => {
                  t.action?.onClick();
                  setToasts((x) => x.filter((y) => y.id !== t.id));
                }}
                className="pointer-events-auto shrink-0 text-sm font-semibold hover:opacity-80"
                style={{ color: "var(--brand-accent)" }}
              >
                {t.action.label} →
              </button>
            )}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/* ------------------------------------------------------- SectionHeader ---- */

/**
 * Cabecera de un apartado del panel: raíl de color, título y contador. Una
 * sola pieza para que TODOS los apartados se marquen igual — antes cada
 * pantalla se inventaba su cabecera y el panel se leía como una lista plana.
 */
export function SectionHeader({
  title, tone = "var(--brand-accent)", count, right, icon: Icon,
}: {
  title: string;
  tone?: string;
  count?: number | string;
  right?: ReactNode;
  icon?: LucideIcon;
}) {
  return (
    <div className="mb-3 flex items-center justify-between gap-3">
      <h2 className="flex items-center gap-2 text-sm font-semibold text-zinc-200">
        <span aria-hidden className="h-4 w-1 rounded-full" style={{ background: tone }} />
        {Icon && <Icon size={15} style={{ color: tone }} />}
        {title}
        {count != null && count !== "" && (
          <span className="rounded-full px-1.5 py-0.5 text-[11px] font-bold tabular-nums"
            style={{ background: `color-mix(in srgb, ${tone} 12%, transparent)`, color: tone }}>
            {count}
          </span>
        )}
      </h2>
      {right}
    </div>
  );
}

/* -------------------------------------------------------- ConfirmDialog ---- */

export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel,
  destructive,
  requireText,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  body: ReactNode;
  confirmLabel: string;
  destructive?: boolean;
  requireText?: string; // si se define, hay que teclearlo para confirmar
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const [typed, setTyped] = useState("");
  const dialogRef = useRef<HTMLDivElement>(null);
  // Cierre unificado (fuera + ESC) y foco: atrapado dentro mientras está
  // abierto, devuelto al elemento que lo abrió al cerrarse.
  useDismiss(dialogRef, onCancel, open);
  useModalFocus(dialogRef, open);

  useEffect(() => {
    if (open) setTyped("");
  }, [open]);

  if (!open) return null;
  const canConfirm = !requireText || typed === requireText;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="card animate-rise w-full max-w-md p-6"
        style={{ background: "var(--surface-raised)" }}
      >
        <div className="flex items-start justify-between">
          <h3 className="text-base font-semibold text-zinc-100">{title}</h3>
          <button onClick={onCancel} aria-label="Cerrar" className="text-zinc-500 hover:text-zinc-300">
            <X size={18} />
          </button>
        </div>
        <div className="mt-2 text-sm leading-relaxed text-zinc-400">{body}</div>
        {requireText && (
          <input
            autoFocus
            className="input mt-4"
            placeholder={requireText}
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
          />
        )}
        <div className="mt-6 flex justify-end gap-2">
          <button className="btn btn-ghost" onClick={onCancel}>
            Cancelar
          </button>
          <button
            className="btn btn-primary"
            style={destructive ? { background: "#C2453A" } : undefined}
            disabled={!canConfirm}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------- ExpandableArea ---- */

/** Textarea de texto largo (justificación, notas, "por qué"…) que en su tamaño
 *  compacto no deja leer ni editar bien. Al enfocarlo se abre un modal grande
 *  con el texto entero; "Hecho"/Esc/click fuera lo cierra. Mismo value/onChange
 *  que el compacto: no hay borrador aparte que pueda desincronizarse. */
export function ExpandableArea({
  label, value, onChange, rows = 2, className,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  rows?: number;
  className?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);
  useDismiss(modalRef, () => setExpanded(false), expanded);
  useModalFocus(modalRef, expanded);

  return (
    <label className={className ? `block ${className}` : "block"}>
      <span className="mb-1 block text-xs text-zinc-500">{label}</span>
      <textarea
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setExpanded(true)}
        readOnly
        rows={rows}
        className="input w-full cursor-pointer resize-none"
      />
      {expanded && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="presentation">
          <div ref={modalRef} role="dialog" aria-modal="true" aria-label={label}
            className="card flex w-full max-w-xl flex-col gap-2 p-4" style={{ maxHeight: "80vh" }}>
            <span className="text-sm font-semibold text-zinc-200">{label}</span>
            <textarea
              value={value ?? ""}
              onChange={(e) => onChange(e.target.value)}
              autoFocus
              className="input w-full flex-1 resize-none"
              style={{ minHeight: "40vh" }}
            />
            <button onClick={() => setExpanded(false)} className="btn btn-primary self-end">
              <Check size={14} /> Hecho
            </button>
          </div>
        </div>
      )}
    </label>
  );
}

/** Prosa larga de la IA recortada a `lines` líneas con "ver más".
 *
 *  Los planes YA generados llevan párrafos largos guardados (los topes nuevos
 *  del prompt solo afectan a lo que se genere a partir de ahora), así que el
 *  recorte vive también en la vista. El botón solo aparece si de verdad hay
 *  texto oculto: se mide el desbordamiento real, nunca por nº de caracteres.
 */
export function ProseClamp({
  text, lines = 2, className, moreLabel = "ver más",
}: { text: string; lines?: number; className?: string; moreLabel?: string }) {
  const [open, setOpen] = useState(false);
  const [clipped, setClipped] = useState(false);
  const ref = useRef<HTMLParagraphElement | null>(null);

  // La medida se repite con ResizeObserver: dentro de un <details> CERRADO el
  // elemento mide 0 y una medición única concluía "no hay recorte", dejando el
  // texto cortado sin botón para desplegarlo.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const medir = () => {
      if (el.clientHeight > 0) setClipped(el.scrollHeight > el.clientHeight + 1);
    };
    medir();
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(medir);
    ro.observe(el);
    return () => ro.disconnect();
  }, [text, open, lines]);

  if (!text) return null;
  return (
    <>
      <p
        ref={ref}
        className={className}
        style={open ? undefined : {
          display: "-webkit-box",
          WebkitBoxOrient: "vertical",
          WebkitLineClamp: lines,
          overflow: "hidden",
        }}
      >
        {text}
      </p>
      {(clipped || open) && (
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="mt-0.5 text-xs font-medium text-zinc-500 hover:text-zinc-300"
        >
          {open ? "ver menos" : moreLabel}
        </button>
      )}
    </>
  );
}
