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
  hint: string;
  action?: ReactNode;
}) {
  // Un estado vacío es una invitación a actuar (skill): título + siguiente paso.
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed py-16 text-center"
      style={{ borderColor: "var(--line-strong)" }}>
      <p className="text-sm font-medium text-zinc-200">{title}</p>
      <p className="mt-1 max-w-xs text-sm text-zinc-500">{hint}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

/* ---------------------------------------------------------------- Toast ---- */

type Toast = { id: number; message: string; tone: "ok" | "error" };
type ToastCtx = { push: (message: string, tone?: "ok" | "error") => void };

const ToastContext = createContext<ToastCtx | null>(null);

export function useToast(): ToastCtx {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast fuera de ToastProvider");
  return ctx;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const push = useCallback((message: string, tone: "ok" | "error" = "ok") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, message, tone }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000);
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
          </div>
        ))}
      </div>
    </ToastContext.Provider>
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
