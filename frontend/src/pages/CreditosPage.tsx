import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, BatteryLow, Check, Coins, ExternalLink, Plus, RefreshCw } from "lucide-react";
import { api, ApiError } from "../lib/api";
import type { AiCreditHistoryOut, AiCreditOut } from "../types";
import { EmptyState, PageLoader, Spinner, useToast } from "../components/ui";
import { Plegable } from "../components/Plegable";

/**
 * EL LIBRO DE LOS CRÉDITOS: si queda, EN QUÉ se fue y qué se ha pagado.
 *
 * Tres cosas que aquí NO se adivinan:
 *
 *  1. **Que se han acabado** lo dice la propia API de Anthropic cuando falla
 *     («credit balance is too low»). El sistema lo sella, lo canta en grande y
 *     lo apaga SOLO en cuanto una llamada vuelve a funcionar. Antes esto se
 *     descubría pulsando «Generar» y leyendo un error en inglés.
 *  2. **Cuánto se ha gastado** sale del informe de coste de Anthropic si hay
 *     clave de administración en el `.env` (`ANTHROPIC_ADMIN_KEY`): la cifra
 *     que factura, no una estimación. Sin clave se sigue estimando por tokens y
 *     se dice que es una estimación.
 *  3. **Cuánto se ha recargado** NO lo publica Anthropic por API — ni el saldo
 *     ni los pagos. Así que lo confirma el coach, pero de UN toque: el importe
 *     de la última recarga ya viene puesto, porque casi siempre es el mismo.
 */
export default function CreditosPage() {
  const toast = useToast();
  const [credit, setCredit] = useState<AiCreditOut | null>(null);
  const [hist, setHist] = useState<AiCreditHistoryOut | null>(null);
  const [error, setError] = useState(false);
  const [intento, setIntento] = useState(0);
  const [dias, setDias] = useState(30);
  const [recarga, setRecarga] = useState("");
  const [tocado, setTocado] = useState(false);
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(async () => {
    setError(false);
    try {
      const [c, h] = await Promise.all([api.getAiCredit(), api.aiCreditHistory(dias)]);
      setCredit(c);
      setHist(h);
      // El importe de la última recarga viene ya escrito: recargar deja de ser
      // "busca el recibo, teclea la cifra" y pasa a ser un toque. Solo mientras
      // el coach no haya escrito nada él.
      if (!tocado && c.ultima_recarga_usd) {
        setRecarga(String(c.ultima_recarga_usd).replace(".", ","));
      }
    } catch {
      setError(true);
    }
  }, [dias, tocado]);

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
      setTocado(false);
      toast.push(`Saldo al día · ${fmt(c.remaining_usd)}`);
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
          action={<button className="btn btn-ghost" onClick={() => setIntento((n) => n + 1)}>Reintentar</button>}
        />
      </div>
    );
  }
  if (!credit || !hist) return <PageLoader />;

  const quedan = credit.remaining_usd;
  const agotado = credit.sin_credito_desde !== null;
  const bajo = !agotado && quedan !== null && quedan < 5;

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 md:px-8 md:py-8">
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="flex items-center gap-2 text-xl font-semibold" style={{ color: "var(--ink)" }}>
            <Coins size={20} /> Créditos de IA
          </h1>
          <p className="mt-1 text-sm" style={{ color: "var(--text-faint)" }}>
            Si queda, en qué se va y qué has pagado
          </p>
        </div>
        <button className="btn btn-ghost" onClick={() => setIntento((n) => n + 1)}>
          <RefreshCw size={15} /> Actualizar
        </button>
      </header>

      {/* --- SE HAN ACABADO: lo primero de la pantalla ----------------------- */}
      {agotado && (
        <div className="card mb-4 p-5" data-ancla="creditos.agotados"
             style={{ borderColor: "#e05252", background: "rgba(224,82,82,0.06)" }}>
          <div className="flex items-start gap-3">
            <BatteryLow size={22} style={{ color: "#e05252" }} className="mt-0.5 shrink-0" />
            <div className="min-w-0">
              <p className="text-base font-semibold" style={{ color: "#b93a3a" }}>
                Se han acabado los créditos
              </p>
              <p className="mt-1 text-sm" style={{ color: "var(--text-dim)" }}>
                Desde {cuando(credit.sin_credito_desde!)}. Hasta que recargues no se puede
                generar un plan, leer una anamnesis ni sacar un informe.
              </p>
              <p className="mt-2 text-xs" style={{ color: "var(--text-faint)" }}>
                Recarga en Anthropic y confirma abajo lo que has pagado. El aviso se apaga
                solo en cuanto una llamada vuelva a funcionar.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* --- Saldo y recarga ------------------------------------------------ */}
      <div className="card p-5" data-ancla="creditos.saldo">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs uppercase tracking-wider" style={{ color: "var(--text-faint)" }}>
              Disponible
            </p>
            <p className="text-3xl font-bold tabular-nums"
               style={{ color: agotado || bajo ? "#e05252" : "var(--ink)" }}>
              {agotado ? "0 $" : quedan !== null ? fmt(quedan) : "—"}
            </p>
            <p className="mt-1 text-sm" style={{ color: "var(--text-faint)" }}>
              {quedan !== null
                ? `Gastado desde la última recarga: ${fmt(credit.gasto_desde_recarga_usd)}`
                : "Confirma lo que has pagado y el sistema lleva la cuenta"}
              {credit.plans_left !== null && quedan !== null && !agotado
                && ` · ~${credit.plans_left} planes`}
            </p>
            <p className="mt-1.5 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs"
               style={{
                 background: "var(--surface-raised)",
                 color: credit.gasto_es_real ? "#3f7a4e" : "var(--text-faint)",
               }}>
              {credit.gasto_es_real
                ? <><Check size={12} /> Cifra real de Anthropic</>
                : <><AlertTriangle size={12} /> Estimado por tokens</>}
            </p>
          </div>
          <div className="flex flex-wrap items-end gap-2">
            <label className="text-sm">
              <span className="mb-1 block text-xs" style={{ color: "var(--text-faint)" }}>
                He recargado ($)
              </span>
              <input
                inputMode="decimal"
                value={recarga}
                onChange={(e) => { setTocado(true); setRecarga(e.target.value); }}
                onKeyDown={(e) => { if (e.key === "Enter") void recargar(); }}
                placeholder="25"
                aria-label="Importe recargado en dólares"
                className="input w-28"
              />
            </label>
            <button className="btn btn-primary" onClick={() => void recargar()} disabled={guardando}>
              {guardando ? <Spinner /> : <Plus size={15} />} Sumar al saldo
            </button>
            <button className="btn btn-ghost"
                    onClick={() => window.open(credit.recharge_url, "_blank", "noopener")}>
              <ExternalLink size={15} /> Recargar en Anthropic
            </button>
          </div>
        </div>
        <p className="mt-3 text-xs" style={{ color: "var(--text-faint)" }}>
          {credit.informe_de_coste
            ? "El gasto lo lee el sistema del informe de coste de Anthropic. El saldo lo confirmas tú al recargar porque Anthropic no publica ni el saldo ni los pagos por su API."
            : "Anthropic no publica el saldo por su API: el gasto se estima con los tokens de cada respuesta. Para leer la cifra REAL que factura, añade ANTHROPIC_ADMIN_KEY al .env del servidor."}
        </p>
      </div>

      {/* --- En qué se va (abierto: es lo que se viene a mirar) -------------- */}
      <div className="card mt-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-semibold" style={{ color: "var(--ink)" }}>En qué se va</h2>
          <div className="flex gap-1.5" role="group" aria-label="Periodo">
            {[7, 30, 90].map((d) => (
              <button key={d} onClick={() => setDias(d)} aria-pressed={dias === d}
                className="rounded-lg border px-3 py-1.5 text-xs font-semibold"
                style={dias === d
                  ? { background: "var(--surface-raised)", color: "var(--brand-accent)",
                      borderColor: "var(--brand-accent)" }
                  : { color: "var(--text-dim)", borderColor: "var(--line-strong)" }}>
                {d} días
              </button>
            ))}
          </div>
        </div>

        {hist.breakdown.length === 0 ? (
          <p className="mt-4 text-sm" style={{ color: "var(--text-faint)" }}>
            Sin gasto en este periodo.
          </p>
        ) : (
          <ul className="mt-4 space-y-2.5">
            {hist.breakdown.map((b) => (
              <li key={b.purpose}>
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <span className="min-w-0 flex-1" style={{ color: "var(--ink)" }}>{b.label}</span>
                  <span className="shrink-0 text-xs" style={{ color: "var(--text-faint)" }}>
                    {b.calls} llamadas
                  </span>
                  <span className="shrink-0 font-semibold tabular-nums" style={{ color: "var(--ink)" }}>
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

      {/* --- Historial: DESPLEGABLES marcados (petición del dueño) ----------- */}
      <div className="mt-4 space-y-3">
        <Plegable
          memoKey="creditos.extracto"
          titulo="Últimas llamadas"
          sub="Cuándo, para qué, de quién y cuánto"
          dato={`${hist.events.length}`}
        >
          {hist.events.length === 0 ? (
            <p className="text-sm" style={{ color: "var(--text-faint)" }}>
              Todavía no hay llamadas anotadas.
            </p>
          ) : (
            <div className="tab-strip">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wider"
                      style={{ color: "var(--text-faint)" }}>
                    <th className="py-2 pr-3 font-semibold">Cuándo</th>
                    <th className="py-2 pr-3 font-semibold">Para qué</th>
                    <th className="py-2 pr-3 font-semibold">Cliente</th>
                    <th className="py-2 pl-3 text-right font-semibold">Coste</th>
                  </tr>
                </thead>
                <tbody>
                  {hist.events.map((e) => (
                    <tr key={e.id} className="border-t" style={{ borderColor: "var(--line)" }}>
                      <td className="py-2 pr-3" style={{ color: "var(--text-faint)" }}>{cuando(e.at)}</td>
                      <td className="py-2 pr-3" style={{ color: "var(--ink)" }}>{e.label}</td>
                      <td className="py-2 pr-3" style={{ color: "var(--text-faint)" }}>{e.client_name ?? "—"}</td>
                      <td className="py-2 pl-3 text-right tabular-nums" style={{ color: "var(--ink)" }}>
                        {fmt(e.cost_usd)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Plegable>

        <Plegable
          memoKey="creditos.recargas"
          titulo="Recargas pagadas"
          sub="Lo que has ido metiendo, y qué quedaba entonces"
          dato={hist.topups.length ? `${hist.topups.length}` : "0"}
        >
          {hist.topups.length === 0 ? (
            <p className="text-sm" style={{ color: "var(--text-faint)" }}>
              Aún no has confirmado ninguna recarga.
            </p>
          ) : (
            <ul className="space-y-2 text-sm">
              {hist.topups.map((t) => (
                <li key={t.id} className="flex items-baseline justify-between gap-3">
                  <span style={{ color: "var(--text-faint)" }}>{cuando(t.at)}</span>
                  <span className="min-w-0 flex-1" style={{ color: "var(--text-dim)" }}>
                    {t.balance_before_usd !== null ? `quedaban ${fmt(t.balance_before_usd)}` : ""}
                  </span>
                  <span className="font-semibold tabular-nums" style={{ color: "#3f7a4e" }}>
                    +{fmt(t.amount_usd)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Plegable>
      </div>
    </div>
  );
}

/** Importes pequeños con los decimales que hacen falta: 0,004 $ no es "0 $". */
function fmt(v: number | null): string {
  if (v === null || !Number.isFinite(v)) return "—";
  const abs = Math.abs(v);
  const dec = abs >= 0.01 ? 2 : 4;
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
