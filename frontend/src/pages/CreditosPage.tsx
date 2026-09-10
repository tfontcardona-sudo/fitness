import { useCallback, useEffect, useState } from "react";
import { Coins, ExternalLink, Plus, RefreshCw } from "lucide-react";
import { api, ApiError } from "../lib/api";
import type { AiCreditHistoryOut, AiCreditOut } from "../types";
import { EmptyState, PageLoader, Spinner, useToast } from "../components/ui";

/**
 * EL LIBRO DE LOS CRÉDITOS: cuánto queda, EN QUÉ se fue y qué se ha pagado.
 *
 * El botón del sidebar decía "quedan 12 $" y poco más. Con eso no se puede
 * decidir nada: que el mes se vaya en generar planes, en leer anamnesis o en el
 * panel de revisión son tres conclusiones distintas y tres acciones distintas.
 *
 * Aquí está el desglose por propósito (de más a menos caro, que es como se lee
 * para recortar), el extracto llamada a llamada y las recargas pagadas.
 *
 * Sobre lo "automático": Anthropic NO publica el saldo por API, así que el
 * sistema no puede leerlo solo — decir lo contrario sería mentir. Lo que sí
 * hace es la cuenta: tecleas lo que has PAGADO (la cifra del recibo) y el saldo
 * pasa a ser lo que quedaba más lo nuevo.
 */
export default function CreditosPage() {
  const toast = useToast();
  const [credit, setCredit] = useState<AiCreditOut | null>(null);
  const [hist, setHist] = useState<AiCreditHistoryOut | null>(null);
  const [error, setError] = useState(false);
  const [intento, setIntento] = useState(0);
  const [dias, setDias] = useState(30);
  const [recarga, setRecarga] = useState("");
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(async () => {
    setError(false);
    try {
      const [c, h] = await Promise.all([api.getAiCredit(), api.aiCreditHistory(dias)]);
      setCredit(c);
      setHist(h);
    } catch {
      setError(true);
    }
  }, [dias]);

  useEffect(() => { void cargar(); }, [cargar, intento]);

  async function recargar() {
    const valor = Number(recarga.replace(",", "."));
    if (!Number.isFinite(valor) || valor <= 0) {
      toast.push("Escribe lo que has pagado (p. ej. 25 o 12,50)", "error");
      return;
    }
    setGuardando(true);
    try {
      const c = await api.topUpAiCredit(valor);
      setCredit(c);
      setRecarga("");
      toast.push(`Saldo actualizado · ${fmt(c.remaining_usd)}`);
      void cargar();
    } catch (e) {
      toast.push(e instanceof ApiError ? e.message : "No se pudo anotar la recarga", "error");
    } finally {
      setGuardando(false);
    }
  }

  if (error && !credit) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-6 md:px-8 md:py-8">
        <EmptyState
          title="No se pudieron cargar los créditos"
          hint="Puede ser un fallo de conexión."
          action={<button className="btn-secondary" onClick={() => setIntento((n) => n + 1)}>Reintentar</button>}
        />
      </div>
    );
  }
  if (!credit || !hist) return <PageLoader />;

  const quedan = credit.remaining_usd;
  const bajo = quedan !== null && quedan < 5;

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 md:px-8 md:py-8">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold text-zinc-100">
            <Coins size={20} /> Créditos de IA
          </h1>
          <p className="mt-1 text-sm text-zinc-500">Cuánto queda, en qué se va y qué has pagado</p>
        </div>
        <button className="btn-secondary" onClick={() => setIntento((n) => n + 1)}>
          <RefreshCw size={15} /> Actualizar
        </button>
      </header>

      {/* --- Saldo y recarga ------------------------------------------------ */}
      <div className="card p-5">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wider text-zinc-500">Disponible</p>
            <p className="text-3xl font-bold tabular-nums"
               style={{ color: bajo ? "#e05252" : "var(--text)" }}>
              {quedan !== null ? fmt(quedan) : "—"}
            </p>
            <p className="mt-1 text-sm text-zinc-500">
              {quedan !== null
                ? `Gastado desde el último apunte: ${fmt(credit.spent_usd)}`
                : "Apunta lo que has pagado y el sistema lleva la cuenta"}
              {credit.plans_left !== null && quedan !== null && ` · ~${credit.plans_left} planes`}
            </p>
          </div>
          <div className="flex items-end gap-2">
            <label className="text-sm">
              <span className="mb-1 block text-xs text-zinc-500">He recargado ($)</span>
              <input
                inputMode="decimal"
                value={recarga}
                onChange={(e) => setRecarga(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") void recargar(); }}
                placeholder="25"
                className="input w-28"
              />
            </label>
            <button className="btn-primary" onClick={() => void recargar()} disabled={guardando}>
              {guardando ? <Spinner /> : <Plus size={15} />} Sumar al saldo
            </button>
            <button className="btn-secondary"
                    onClick={() => window.open(credit.recharge_url, "_blank", "noopener")}>
              <ExternalLink size={15} /> Recargar en Anthropic
            </button>
          </div>
        </div>
        <p className="mt-3 text-xs text-zinc-600">
          Anthropic no publica el saldo por su API, así que el sistema no puede leerlo solo:
          escribe lo que has pagado y él hace la suma con lo que quedaba.
        </p>
      </div>

      {/* --- En qué se va --------------------------------------------------- */}
      <div className="card mt-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-zinc-100">En qué se va</h2>
          <div className="flex gap-1">
            {[7, 30, 90].map((d) => (
              <button key={d} onClick={() => setDias(d)}
                className="rounded-lg px-2.5 py-1 text-xs font-semibold"
                style={dias === d
                  ? { background: "var(--surface-raised)", color: "var(--brand-accent)" }
                  : { color: "var(--text-faint)" }}>
                {d} días
              </button>
            ))}
          </div>
        </div>

        {hist.breakdown.length === 0 ? (
          <p className="mt-4 text-sm text-zinc-500">Sin gasto en este periodo.</p>
        ) : (
          <ul className="mt-4 space-y-2">
            {hist.breakdown.map((b) => (
              <li key={b.purpose}>
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <span className="min-w-0 flex-1 truncate text-zinc-200">{b.label}</span>
                  <span className="shrink-0 text-xs text-zinc-500">{b.calls} llamadas</span>
                  <span className="shrink-0 font-semibold tabular-nums text-zinc-100">
                    {fmt(b.cost_usd)}
                  </span>
                </div>
                {/* La barra hace visible de un vistazo dónde está el dinero. */}
                <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full"
                     style={{ background: "var(--surface-raised)" }}>
                  <div className="h-full rounded-full"
                       style={{ width: `${b.share}%`, background: "var(--brand-accent)" }} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* --- Extracto ------------------------------------------------------- */}
      <div className="card mt-4 p-5">
        <h2 className="text-base font-semibold text-zinc-100">Últimas llamadas</h2>
        {hist.events.length === 0 ? (
          <p className="mt-3 text-sm text-zinc-500">Todavía no hay llamadas anotadas.</p>
        ) : (
          <div className="tab-strip mt-3">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wider text-zinc-500">
                  <th className="py-2 pr-3 font-semibold">Cuándo</th>
                  <th className="py-2 pr-3 font-semibold">Para qué</th>
                  <th className="py-2 pr-3 font-semibold">Cliente</th>
                  <th className="py-2 pl-3 text-right font-semibold">Coste</th>
                </tr>
              </thead>
              <tbody>
                {hist.events.map((e) => (
                  <tr key={e.id} className="border-t" style={{ borderColor: "var(--line)" }}>
                    <td className="py-2 pr-3 text-zinc-500">{cuando(e.at)}</td>
                    <td className="py-2 pr-3 text-zinc-200">{e.label}</td>
                    <td className="py-2 pr-3 text-zinc-500">{e.client_name ?? "—"}</td>
                    <td className="py-2 pl-3 text-right tabular-nums text-zinc-100">
                      {fmt(e.cost_usd)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* --- Recargas ------------------------------------------------------- */}
      {hist.topups.length > 0 && (
        <div className="card mt-4 p-5">
          <h2 className="text-base font-semibold text-zinc-100">Recargas</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {hist.topups.map((t) => (
              <li key={t.id} className="flex items-baseline justify-between gap-3">
                <span className="text-zinc-500">{cuando(t.at)}</span>
                <span className="min-w-0 flex-1 truncate text-zinc-400">
                  {t.balance_before_usd !== null
                    ? `quedaban ${fmt(t.balance_before_usd)}`
                    : ""}
                </span>
                <span className="font-semibold tabular-nums" style={{ color: "#4ade80" }}>
                  +{fmt(t.amount_usd)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/** Importes pequeños con los decimales que hacen falta: 0,004 $ no es "0 $". */
function fmt(v: number | null): string {
  if (v === null || !Number.isFinite(v)) return "—";
  const abs = Math.abs(v);
  const dec = abs >= 10 ? 2 : abs >= 1 ? 2 : abs >= 0.01 ? 3 : 4;
  return `${v.toFixed(dec).replace(".", ",")} $`;
}

function cuando(iso: string): string {
  try {
    return new Date(iso).toLocaleString("es-ES",
      { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  } catch {
    return "—";
  }
}
