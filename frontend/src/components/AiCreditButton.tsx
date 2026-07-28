import { useCallback, useEffect, useRef, useState } from "react";
import { Coins, ExternalLink, Pencil } from "lucide-react";
import { api, keepIfSame } from "../lib/api";
import { useDismiss } from "../lib/useDismiss";
import type { AiCreditOut } from "../types";

const fmtUsd = (n: number) =>
  `$${n.toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/** Un gasto real de $0,004 no debe verse como "$0,00" (parecería que no gasta). */
const fmtSmall = (n: number) => (n > 0 && n < 0.01 ? "<$0,01" : fmtUsd(n));

const fmtWhen = (iso: string | null) => {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  const mins = Math.round((Date.now() - d.getTime()) / 60_000);
  if (mins < 1) return "hace un momento";
  if (mins < 60) return `hace ${mins} min`;
  const h = Math.round(mins / 60);
  if (h < 24) return `hace ${h} h`;
  return d.toLocaleDateString("es-ES", { day: "numeric", month: "short" });
};

/**
 * Botón del sidebar (bajo "Recursos"): créditos de la API de Anthropic EN VIVO.
 *
 * Anthropic NO expone el saldo por API, así que el saldo de partida lo apunta el
 * coach al recargar (lápiz) y el sistema descuenta el coste REAL de cada llamada
 * (tokens de la respuesta × precio oficial del modelo). El GASTO sí es en vivo
 * siempre, incluso sin saldo apuntado. Al pulsar se abre el detalle: disponible,
 * planes que quedan, gasto de hoy y de los últimos 30 días.
 */
export function AiCreditButton({ collapsed }: { collapsed: boolean }) {
  const [credit, setCredit] = useState<AiCreditOut | null>(null);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const wrapRef = useRef<HTMLDivElement | null>(null);

  const refresh = useCallback(() => {
    api.getAiCredit().then((c) => setCredit((prev) => keepIfSame(prev, c))).catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    // El saldo baja mientras se generan planes: refresco en segundo plano y al
    // volver a la pestaña (así el número está fresco justo cuando lo miras).
    const t = window.setInterval(refresh, 30_000);
    const onFocus = () => refresh();
    window.addEventListener("focus", onFocus);
    return () => {
      window.clearInterval(t);
      window.removeEventListener("focus", onFocus);
    };
  }, [refresh]);

  // Con el detalle abierto, refresco más ágil: se ve consumir en vivo.
  useEffect(() => {
    if (!open) return;
    const t = window.setInterval(refresh, 8_000);
    return () => window.clearInterval(t);
  }, [open, refresh]);

  const closeAll = useCallback(() => {
    setOpen(false);
    setEditing(false);
  }, []);
  useDismiss(wrapRef, closeAll, open || editing);

  const remaining = credit?.remaining_usd ?? null;
  const balance = credit?.balance_usd ?? null;
  const spent = credit?.spent_usd ?? 0;
  const plansLeft = credit?.plans_left ?? null;
  const low = remaining !== null && remaining < 5;
  // % consumido del saldo apuntado (para la barra).
  const usedPct =
    balance && balance > 0 ? Math.min(100, Math.max(0, (spent / balance) * 100)) : null;

  const [inputError, setInputError] = useState<string | null>(null);
  const save = async () => {
    // Campo vacío = CANCELAR, no "saldo $0" (Number("") es 0 y apuntaba el
    // saldo a cero sin querer); entrada inválida avisa en vez de no responder.
    if (draft.trim() === "") { setEditing(false); setInputError(null); return; }
    const value = Number(draft.replace(",", "."));
    if (!Number.isFinite(value) || value < 0) {
      setInputError("Escribe un número válido (p. ej. 25 o 12,50)");
      return;
    }
    setInputError(null);
    setSaving(true);
    try {
      setCredit(await api.setAiCredit(value));
      setEditing(false);
    } catch {
      // se mantiene el editor abierto para reintentar
    } finally {
      setSaving(false);
    }
  };

  const startEdit = () => {
    setDraft(remaining !== null ? String(remaining) : "");
    setEditing(true);
    setOpen(true);
  };

  // Subtítulo: si hay saldo, disponible (+ planes). Si no, el gasto REAL
  // acumulado, que ya es en vivo sin apuntar nada.
  const subtitle =
    remaining !== null
      ? `Quedan ${fmtUsd(remaining)}${plansLeft !== null ? ` · ~${plansLeft} planes` : ""}`
      : spent > 0
        ? `Gastado ${fmtSmall(spent)} · apunta tu saldo`
        : "Apunta tu saldo para verlo";

  return (
    <div className="relative" ref={wrapRef}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        title="Créditos IA — consumo en vivo"
        className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-zinc-500 transition-colors hover:text-zinc-200"
      >
        <Coins size={18} className="shrink-0" style={low ? { color: "#e05252" } : undefined} />
        {!collapsed && (
          <span className="min-w-0 flex-1 text-left leading-tight">
            <span className="block">Créditos IA</span>
            <span
              className="block truncate text-[11px] font-normal"
              style={{ color: low ? "#e05252" : "var(--text-faint)" }}
            >
              {subtitle}
            </span>
          </span>
        )}
        {!collapsed && (
          <span
            role="button"
            aria-label="Apuntar saldo actual"
            title="Apunta aquí tu saldo tras recargar"
            onClick={(e) => {
              e.stopPropagation();
              startEdit();
            }}
            className="tap shrink-0 rounded-lg p-1.5 text-zinc-600 hover:text-zinc-200"
          >
            <Pencil size={13} />
          </span>
        )}
      </button>

      {/* Barra de consumo del saldo apuntado (solo si hay saldo). */}
      {!collapsed && usedPct !== null && (
        <div
          className="mx-3 mb-1 h-1 overflow-hidden rounded-full"
          style={{ background: "var(--line)" }}
        >
          <div
            className="h-full rounded-full transition-all"
            style={{ width: `${usedPct}%`, background: low ? "#e05252" : "var(--brand-accent)" }}
          />
        </div>
      )}

      {open && !collapsed && credit && (
        <div
          className="mx-3 mb-1 space-y-2 rounded-xl border px-3 py-2.5 text-xs"
          style={{ borderColor: "var(--line)", background: "var(--surface-raised)" }}
        >
          {remaining !== null ? (
            <div>
              <div
                className="text-lg font-bold"
                style={{ color: low ? "#e05252" : "var(--text)" }}
              >
                {fmtUsd(remaining)}
              </div>
              <div style={{ color: "var(--text-faint)" }}>
                disponible de {fmtUsd(balance ?? 0)} apuntados
                {plansLeft !== null && ` · dan para ~${plansLeft} planes`}
              </div>
            </div>
          ) : (
            <div style={{ color: "var(--text-faint)" }}>
              Anthropic no publica el saldo por API. Apunta con el lápiz lo que te
              queda en la consola y aquí verás el disponible en vivo.
            </div>
          )}

          <div className="space-y-1 border-t pt-2" style={{ borderColor: "var(--line)" }}>
            <Row label="Hoy" value={fmtSmall(credit.spent_today_usd)} />
            <Row
              label={`Últimos ${credit.window_days} días`}
              value={`${fmtSmall(credit.spent_window_usd)} · ${credit.calls_window} llamadas`}
            />
            {credit.avg_cost_per_plan_usd !== null && (
              <Row label="Coste medio por plan" value={fmtSmall(credit.avg_cost_per_plan_usd)} />
            )}
            {remaining !== null && (
              <Row label="Gastado desde que lo apuntaste" value={fmtSmall(spent)} />
            )}
            {fmtWhen(credit.last_call_at) && (
              <Row label="Última llamada" value={fmtWhen(credit.last_call_at)!} />
            )}
          </div>

          <div
            className="flex items-center gap-2 border-t pt-2"
            style={{ borderColor: "var(--line)" }}
          >
            <button
              onClick={() => window.open(credit.recharge_url, "_blank", "noopener")}
              className="tap flex items-center gap-1.5 rounded-lg px-2 py-1 font-semibold"
              style={{ color: "var(--brand-accent)" }}
            >
              <ExternalLink size={12} /> Recargar
            </button>
            <button
              onClick={startEdit}
              className="tap rounded-lg px-2 py-1 font-semibold"
              style={{ color: "var(--text-faint)" }}
            >
              Apuntar saldo
            </button>
          </div>
        </div>
      )}

      {editing && !collapsed && (
        <div
          className="mx-3 mb-1 flex items-center gap-2 rounded-xl border px-2.5 py-2"
          style={{ borderColor: "var(--line)", background: "var(--surface-raised)" }}
        >
          <input
            autoFocus
            inputMode="decimal"
            placeholder="Saldo en $"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void save();
              if (e.key === "Escape") setEditing(false);
            }}
            className="w-full min-w-0 bg-transparent text-sm text-zinc-100 outline-none placeholder:text-zinc-600"
          />
          <button
            onClick={() => void save()}
            disabled={saving}
            className="tap shrink-0 rounded-lg px-2 py-1 text-xs font-semibold"
            style={{ color: "var(--brand-accent)" }}
          >
            {saving ? "…" : "OK"}
          </button>
        </div>
      )}
      {editing && inputError && (
        <p className="mt-1 text-[11px]" style={{ color: "#C2453A" }}>{inputError}</p>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <span style={{ color: "var(--text-faint)" }}>{label}</span>
      <span className="font-medium" style={{ color: "var(--text)" }}>
        {value}
      </span>
    </div>
  );
}
