import { useCallback, useEffect, useState } from "react";
import { BadgeEuro, Check, Copy, MessageCircle, Send } from "lucide-react";
import { api } from "../lib/api";
import { BRAND_SHORT, OFFER_ENABLED, PT_RATES, PUBLIC_TIERS } from "../lib/branding";
import { OFFER_FIRST_EUR, OFFER_MONTHLY_EUR, PACKAGES, PACKAGE_ORDER, billingLabel } from "../lib/packages";
import { openWhatsApp, waPhone } from "../lib/whatsapp";
import { useToast } from "./ui";
import type { PackageTier, PlanPricesOut, PublicBillingPeriod } from "../types";

/**
 * Kit de ventas: cuando un interesado escribe por WhatsApp (desde /planes),
 * el coach le responde en DOS CLICS con lo que toque:
 *  - el CATÁLOGO completo de precios (importes reales leídos de Stripe), o
 *  - el mensaje de venta de UN plan × duración con su ENLACE DE PAGO directo
 *    (/api/pay/plan/{plan}/{duración}: abre Stripe, y al pagar el sistema crea
 *    la ficha, marca el pago y envía portal + anamnesis solo).
 * Los textos van sin emojis (WhatsApp los corrompe en algunos móviles) y con
 * *negrita* de WhatsApp. Todo es editable antes de copiar/enviar.
 */

const PERIODS: PublicBillingPeriod[] = ["1m", "3m", "6m"];

/** "69" o "110,50" — importes sin decimales de relleno. */
function euros(n: number): string {
  return (Number.isInteger(n) ? String(n) : n.toFixed(2).replace(".", ",")) + " €";
}

/** Línea de precio de una duración: "Trimestral: 330 € (sale a 110 €/mes)". */
function priceLine(prices: PlanPricesOut, tier: PackageTier, period: PublicBillingPeriod): string {
  const pr = prices.tiers?.[tier]?.[period];
  if (!pr) return "";
  const extra = pr.months > 1 ? ` (sale a ${euros(pr.per_month)}/mes)` : "";
  return `${billingLabel(period)}: ${euros(pr.total)}${extra}`;
}

const PLAN_SELL: Record<PackageTier, string> = {
  train: "Entrenamiento 100 % a tu medida (material, horario, lesiones y nivel), progresión clara semana a semana, app con tu rutina y yo contigo a diario por WhatsApp.",
  nutri: "Nutrición 100 % a tu medida (tus gustos, tus horarios, tus alergias), objetivos calculados sobre tu caso, app de seguimiento y yo contigo a diario por WhatsApp.",
  full: "Entrenamiento y nutrición coordinados y 100 % a tu medida, revisión quincenal con informe, app de seguimiento y yo contigo a diario por WhatsApp.",
};

function catalogText(prices: PlanPricesOut): string {
  // Solo los planes con venta online llevan precios de Stripe; el entreno
  // personal va con sus tarifas presenciales (branding.PT_RATES).
  const bloques = PACKAGE_ORDER.filter((t) => PUBLIC_TIERS.includes(t)).map((t) => {
    const lineas = PERIODS.map((p) => priceLine(prices, t, p))
      .filter(Boolean)
      .map((l) => `· ${l}`)
      .join("\n");
    return `*${PACKAGES[t].label}* - ${PACKAGES[t].tagline}\n${lineas}`;
  }).join("\n\n");
  const entreno =
    `*${PACKAGES.train.label}* - sesiones presenciales en el centro\n` +
    PT_RATES.map((r) => `· ${r.label}: ${r.price}`).join("\n");
  return (
    `*${BRAND_SHORT} - catálogo*\n\n${bloques}\n\n${entreno}\n\n` +
    "La preparación incluye plan 100 % a tu medida, seguimiento en tu app y tu " +
    "preparador por WhatsApp; las sesiones se reservan por aquí y se pagan en el centro.\n" +
    "Dime qué te encaja y te paso el siguiente paso."
  );
}

/** Mensaje de tarifas del entreno personal (reserva por WhatsApp, cobro en el centro). */
function entrenoText(): string {
  return (
    `*${PACKAGES.train.label}* - sesiones 1:1 en el centro\n` +
    PT_RATES.map((r) => `· ${r.label}: ${r.price}`).join("\n") +
    "\n\nIncluye tu rutina y tu progreso en la app, y seguimiento de composición " +
    "corporal para ajustar con datos.\n" +
    "Dime qué día y hora te va bien y lo reservamos; el pago se hace en el centro."
  );
}

/** Mensaje de la OFERTA (1 € el primer mes → 120 €/mes en suscripción). */
function offerText(): string {
  const link = `${window.location.origin}/api/pay/plan/full/oferta`;
  return (
    `*Oferta ${PACKAGES.full.label}* - tu primer mes por ${OFFER_FIRST_EUR} €\n` +
    `Después, ${OFFER_MONTHLY_EUR} €/mes en suscripción (menos de lo que cuestan ` +
    "entreno y nutrición por separado) y sin permanencia: cancelas cuando quieras.\n" +
    "Incluye el plan completo: entrenamiento y nutrición 100 % a tu medida, " +
    "WhatsApp conmigo a diario, app de seguimiento y revisión quincenal con informe.\n\n" +
    `Empieza hoy por ${OFFER_FIRST_EUR} €: ${link}\n` +
    "Pago seguro con Stripe; la renovación es automática cada mes."
  );
}

function planText(prices: PlanPricesOut, tier: PackageTier, period: PublicBillingPeriod): string {
  const pr = prices.tiers?.[tier]?.[period];
  const dur = billingLabel(period).toLowerCase();
  const precio = pr
    ? ` - ${euros(pr.total)}${pr.months > 1 ? ` (sale a ${euros(pr.per_month)}/mes)` : ""}`
    : "";
  const link = `${window.location.origin}/api/pay/plan/${tier}/${period}`;
  return (
    `*${PACKAGES[tier].label} ${dur}*${precio}\n` +
    `${PLAN_SELL[tier]}\n\n` +
    `Pago seguro con Stripe: ${link}\n` +
    "Al completar el pago te llega al momento el acceso a tu app y tu cuestionario " +
    "inicial, y nos ponemos en marcha."
  );
}

export function SalesKit() {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [prices, setPrices] = useState<PlanPricesOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Qué hay en el cuadro: el catálogo, la oferta 1 € o un plan concreto.
  const [sel, setSel] = useState<{ tier: PackageTier; period: PublicBillingPeriod } | "catalog" | "oferta" | "entreno" | null>(null);
  const [text, setText] = useState("");
  const [phone, setPhone] = useState("");
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const p = await api.publicPlanPrices();
      setPrices(p);
    } catch {
      setError("No se pudieron cargar los precios. Reintenta en un momento.");
    }
  }, []);

  useEffect(() => {
    if (open && prices === null) void load();
  }, [open, prices, load]);

  function pick(next: { tier: PackageTier; period: PublicBillingPeriod } | "catalog" | "oferta" | "entreno") {
    if (!prices) return;
    // Re-pulsar el chip YA seleccionado no regenera el texto: machacaría en
    // silencio lo que el coach haya editado en el cuadro.
    const same = typeof next === "string"
      ? sel === next
      : typeof sel !== "string" && sel?.tier === next.tier && sel?.period === next.period;
    if (same) return;
    setSel(next);
    setCopied(false);
    setText(next === "catalog" ? catalogText(prices)
      : next === "oferta" ? offerText()
      : next === "entreno" ? entrenoText()
      : planText(prices, next.tier, next.period));
  }

  async function copy() {
    let ok = true;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Safari/HTTP antiguos: selección manual como reserva — comprobando el
      // resultado de verdad (un "Copiado" en falso haría pegar un chat vacío).
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      ta.setSelectionRange(0, text.length);
      ok = document.execCommand("copy");
      ta.remove();
    }
    setCopied(ok);
    toast.push(ok
      ? "Mensaje copiado — pégalo en el chat de WhatsApp"
      : "No se pudo copiar: selecciona el texto del cuadro y cópialo a mano");
  }

  function sendWhatsApp() {
    const digits = waPhone(phone);
    if (!digits) {
      toast.push("Escribe el teléfono del interesado (o usa Copiar y pégalo en su chat)");
      return;
    }
    openWhatsApp(digits, text);
  }

  return (
    <div className="card p-5">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 text-left"
        aria-expanded={open}
      >
        <span className="flex items-center gap-2">
          <BadgeEuro size={18} style={{ color: "var(--brand-accent)" }} />
          <span className="text-base font-semibold" style={{ color: "var(--text)" }}>
            Vender: precios y enlaces de pago
          </span>
        </span>
        <span className="text-xs" style={{ color: "var(--text-faint)" }}>
          catálogo + pago por plan
        </span>
      </button>

      {open && (
        <div className="mt-3 space-y-3">
          <p className="text-xs" style={{ color: "var(--text-faint)" }}>
            Te escriben desde la página de planes: elige qué responder. El enlace
            de pago de la preparación abre Stripe con el importe correcto y, al
            pagar, el sistema crea la ficha del cliente y le envía automáticamente
            el acceso y la anamnesis. Las sesiones de entreno se cobran en el centro.
          </p>

          {error && (
            <div className="flex items-center justify-between gap-3 rounded-xl border p-3 text-sm"
              style={{ borderColor: "#F0716A", color: "#8B1A2B" }}>
              <span>{error}</span>
              <button onClick={() => void load()} className="tap font-semibold underline">
                Reintentar
              </button>
            </div>
          )}

          {!prices && !error && (
            <p className="text-sm" style={{ color: "var(--text-faint)" }}>
              Cargando precios…
            </p>
          )}

          {prices && (
            <>
              {/* Elegir contenido: catálogo completo o plan × duración */}
              <div className="flex flex-wrap items-center gap-2">
                <button
                  onClick={() => pick("catalog")}
                  className="tap rounded-lg border px-3 py-1.5 text-xs font-bold"
                  style={sel === "catalog"
                    ? { background: "var(--brand-accent)", color: "white", borderColor: "var(--brand-accent)" }
                    : { borderColor: "var(--line)", color: "var(--text)" }}
                >
                  Catálogo completo
                </button>
                {OFFER_ENABLED && (
                  <button
                    onClick={() => pick("oferta")}
                    className="tap rounded-lg border px-3 py-1.5 text-xs font-bold"
                    style={sel === "oferta"
                      ? { background: "#2E7D46", color: "white", borderColor: "#2E7D46" }
                      : { borderColor: "#2E7D46", color: "#2E7D46" }}
                    title={`Primer mes ${OFFER_FIRST_EUR} € y después ${OFFER_MONTHLY_EUR} €/mes en suscripción (solo Full)`}
                  >
                    Oferta 1 €
                  </button>
                )}
                <button
                  onClick={() => pick("entreno")}
                  className="tap rounded-lg border px-3 py-1.5 text-xs font-bold"
                  style={sel === "entreno"
                    ? { background: PACKAGES.train.color, color: "white", borderColor: PACKAGES.train.color }
                    : { borderColor: PACKAGES.train.color, color: PACKAGES.train.color }}
                  title="Tarifas de las sesiones presenciales (se pagan en el centro)"
                >
                  Entreno (tarifas)
                </button>
                <span className="text-xs" style={{ color: "var(--text-faint)" }}>o un plan:</span>
              </div>
              <div className="space-y-1.5">
                {PACKAGE_ORDER.filter((t) => PUBLIC_TIERS.includes(t)).map((t) => (
                  <div key={t} className="flex flex-wrap items-center gap-1.5">
                    <span className="w-24 shrink-0 rounded-full px-2 py-0.5 text-center text-[11px] font-bold text-white"
                      style={{ background: PACKAGES[t].color }}>
                      {PACKAGES[t].short}
                    </span>
                    {PERIODS.map((p) => {
                      const activo = typeof sel !== "string" && sel?.tier === t && sel?.period === p;
                      return (
                        <button
                          key={p}
                          onClick={() => pick({ tier: t, period: p })}
                          className="tap rounded-lg border px-2.5 py-1 text-xs font-semibold"
                          style={activo
                            ? { background: PACKAGES[t].color, color: "white", borderColor: PACKAGES[t].color }
                            : { borderColor: "var(--line)", color: "var(--text)" }}
                        >
                          {billingLabel(p)}
                        </button>
                      );
                    })}
                  </div>
                ))}
              </div>

              {sel !== null && (
                <>
                  <textarea
                    value={text}
                    onChange={(e) => { setText(e.target.value); setCopied(false); }}
                    rows={sel === "catalog" ? 14 : sel === "oferta" || sel === "entreno" ? 8 : 6}
                    className="w-full resize-y rounded-lg border bg-transparent p-2.5 font-mono text-xs outline-none"
                    style={{ borderColor: "var(--line)", color: "var(--text)" }}
                  />
                  <div className="flex flex-wrap items-center gap-2">
                    <button onClick={() => void copy()}
                      className="tap flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-bold text-white"
                      style={{ background: copied ? "#15803D" : "var(--brand-accent)" }}>
                      {copied ? <><Check size={13} /> Copiado</> : <><Copy size={13} /> Copiar mensaje</>}
                    </button>
                    <input
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      type="tel"
                      placeholder="Tel. del interesado (opcional)"
                      className="w-52 rounded-lg border bg-transparent px-2.5 py-2 text-xs outline-none"
                      style={{ borderColor: "var(--line)", color: "var(--text)" }}
                    />
                    <button onClick={sendWhatsApp}
                      className="tap flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-bold"
                      style={{ borderColor: "#25D366", color: "#128C4B" }}>
                      <Send size={13} /> Abrir WhatsApp
                    </button>
                  </div>
                  <p className="flex items-center gap-1.5 text-[11px]" style={{ color: "var(--text-faint)" }}>
                    <MessageCircle size={12} />
                    Lo normal: el interesado ya te ha escrito — pulsa Copiar y pégalo
                    en su chat. El teléfono solo hace falta para abrir un chat nuevo.
                  </p>
                </>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
