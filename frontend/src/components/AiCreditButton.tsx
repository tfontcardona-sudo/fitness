import { useCallback, useEffect, useState } from "react";
import { Coins, Pencil } from "lucide-react";
import { api, keepIfSame } from "../lib/api";
import type { AiCreditOut } from "../types";

const fmtUsd = (n: number) =>
  `$${n.toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/** Botón del sidebar (bajo "Recursos"): créditos restantes de la API de
 * Anthropic. Anthropic no expone el saldo por API, así que funciona en local:
 * el coach apunta el saldo con el lápiz al recargar y el sistema descuenta el
 * coste real de cada generación de plan. Pulsar el botón abre la página de
 * recarga de la consola de Anthropic. */
export function AiCreditButton({ collapsed }: { collapsed: boolean }) {
  const [credit, setCredit] = useState<AiCreditOut | null>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);

  const refresh = useCallback(() => {
    api.getAiCredit().then((c) => setCredit((prev) => keepIfSame(prev, c))).catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    // El saldo baja mientras se generan planes: refresco suave en segundo plano.
    const t = window.setInterval(refresh, 60_000);
    return () => window.clearInterval(t);
  }, [refresh]);

  const remaining = credit?.remaining_usd ?? null;
  const low = remaining !== null && remaining < 5;

  const save = async () => {
    const value = Number(draft.replace(",", "."));
    if (!Number.isFinite(value) || value < 0) return;
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

  return (
    <div className="relative">
      <button
        onClick={() => {
          window.open(
            credit?.recharge_url ?? "https://console.anthropic.com/settings/billing",
            "_blank",
            "noopener",
          );
        }}
        title={
          collapsed
            ? "Créditos IA — pulsar para recargar"
            : "Abre la página de recarga de Anthropic"
        }
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
              {remaining !== null ? `Quedan ${fmtUsd(remaining)}` : "Saldo sin apuntar"}
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
              setDraft(remaining !== null ? String(remaining) : "");
              setEditing((v) => !v);
            }}
            className="tap shrink-0 rounded-lg p-1.5 text-zinc-600 hover:text-zinc-200"
          >
            <Pencil size={13} />
          </span>
        )}
      </button>

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
    </div>
  );
}
