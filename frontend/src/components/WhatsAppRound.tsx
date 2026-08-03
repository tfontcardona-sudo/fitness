import { useCallback, useEffect, useState } from "react";
import { Check, MessageCircle, RefreshCw, Send } from "lucide-react";
import { api } from "../lib/api";
import { openWhatsApp, waPhone } from "../lib/whatsapp";
import { pkg } from "../lib/packages";
import { useToast } from "./ui";
import type { WhatsAppRoundOut } from "../types";

/**
 * Ronda diaria de seguimiento por WhatsApp.
 *
 * Cada día toca un mensaje distinto del pool de 100 (sin repetir hasta
 * completarlo). La IA lo redacta para CADA cliente según su plan, cómo le va,
 * la hora y el día. El coach revisa y va enviando: al pulsar se abre WhatsApp
 * con el texto escrito y se marca como enviado.
 */
export function WhatsAppRound() {
  const toast = useToast();
  const [round, setRound] = useState<WhatsAppRoundOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Texto editable por cliente: el coach puede retocar antes de enviar.
  const [drafts, setDrafts] = useState<Record<number, string>>({});

  const load = useCallback(async (force = false) => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.getWhatsAppRound(true, force);
      setRound(r);
      setDrafts(Object.fromEntries(r.items.map((i) => [i.client_id, i.text])));
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo preparar la ronda");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open && round === null && !loading) void load();
  }, [open, round, loading, load]);

  const send = async (clientId: number, phone: string | null) => {
    const text = drafts[clientId] ?? "";
    const digits = waPhone(phone);
    if (!digits) {
      toast.push("Este cliente no tiene teléfono guardado");
      return;
    }
    openWhatsApp(digits, text);
    try {
      if (round) await api.markWhatsAppSent(round.round_id, clientId, text);
      setRound((r) =>
        r ? { ...r, items: r.items.map((i) => (i.client_id === clientId ? { ...i, already_sent: true } : i)), pending: Math.max(0, r.pending - 1) } : r,
      );
    } catch {
      toast.push("Se abrió WhatsApp, pero no se pudo marcar como enviado");
    }
  };

  const pending = round?.pending ?? 0;

  return (
    <div className="card p-5">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 text-left"
        aria-expanded={open}
      >
        <span className="flex items-center gap-2">
          <MessageCircle size={18} style={{ color: "var(--brand-accent)" }} />
          <span className="text-base font-semibold" style={{ color: "var(--text)" }}>
            Seguimiento del día por WhatsApp
          </span>
        </span>
        {round && (
          <span
            className="shrink-0 rounded-full px-2.5 py-0.5 text-xs font-bold"
            style={
              pending > 0
                ? { background: "rgba(232,131,58,0.15)", color: "#B45309" }
                : { background: "rgba(22,163,74,0.12)", color: "#15803D" }
            }
          >
            {pending > 0 ? `${pending} por enviar` : "Ronda completada"}
          </span>
        )}
      </button>

      {open && (
        <div className="mt-3 space-y-3">
          {loading && (
            <p className="text-sm" style={{ color: "var(--text-faint)" }}>
              Preparando los mensajes de hoy…
            </p>
          )}

          {error && (
            <div className="flex items-center justify-between gap-3 rounded-xl border p-3 text-sm"
              style={{ borderColor: "#C2453A", color: "#8B1A2B" }}>
              <span>{error}</span>
              <button onClick={() => void load()} className="tap font-semibold underline">
                Reintentar
              </button>
            </div>
          )}

          {round && !loading && (
            <>
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs"
                style={{ color: "var(--text-faint)" }}>
                <span>
                  Mensaje {round.brief_index + 1} de {round.pool_size} ·{" "}
                  <strong style={{ color: "var(--text)" }}>{round.brief_tema}</strong>
                </span>
                <button
                  onClick={() => void load(true)}
                  className="tap flex items-center gap-1.5 font-semibold"
                  style={{ color: "var(--brand-accent)" }}
                  title="Vuelve a redactar todos los mensajes de hoy con IA"
                >
                  <RefreshCw size={12} /> Reescribir
                </button>
              </div>

              {round.items.length === 0 && (
                <p className="text-sm" style={{ color: "var(--text-faint)" }}>
                  No hay clientes activos con teléfono para escribir hoy.
                </p>
              )}

              {round.items.map((it) => (
                <div
                  key={it.client_id}
                  className="rounded-xl border p-3"
                  style={{
                    borderColor: "var(--line)",
                    opacity: it.already_sent ? 0.6 : 1,
                  }}
                >
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span className="flex items-center gap-2 text-sm font-semibold"
                      style={{ color: "var(--text)" }}>
                      {it.name}
                      <span className="rounded-full px-2 py-0.5 text-[10px] font-bold text-white"
                        style={{ background: pkg(it.tier).color }}>
                        {pkg(it.tier).short}
                      </span>
                    </span>
                    {it.already_sent ? (
                      <span className="flex items-center gap-1 text-xs font-semibold"
                        style={{ color: "#15803D" }}>
                        <Check size={13} /> Enviado
                      </span>
                    ) : (
                      <button
                        onClick={() => void send(it.client_id, it.phone)}
                        className="tap flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold text-white"
                        style={{ background: "var(--brand-accent)" }}
                      >
                        <Send size={12} /> Enviar
                      </button>
                    )}
                  </div>
                  <textarea
                    value={drafts[it.client_id] ?? ""}
                    onChange={(e) =>
                      setDrafts((d) => ({ ...d, [it.client_id]: e.target.value }))
                    }
                    rows={3}
                    className="w-full resize-y rounded-lg border bg-transparent p-2 text-sm outline-none"
                    style={{ borderColor: "var(--line)", color: "var(--text)" }}
                  />
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
