import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle, BadgeEuro, Check, Copy, ExternalLink, Link2, MessageCircle,
  RefreshCw, Send, ShieldCheck, Sparkles,
} from "lucide-react";
import { api } from "../lib/api";
import { PACKAGES } from "../lib/packages";
import { openWhatsApp, waPhone } from "../lib/whatsapp";
import { useToast, PageLoader } from "../components/ui";
import type { PackageTier, SalesCatalogOut, SalesItem } from "../types";

/**
 * VENDER — la pantalla desde la que el coach manda el enlace de pago.
 *
 * Antes esto era un desplegable dentro del panel "Hoy" con chips pequeños: no
 * se veía qué oferta estabas eligiendo, ni cuánto cobraba, ni si el enlace iba
 * a funcionar. Ahora:
 *  · LA OFERTA arriba, en tarjetas grandes con su color propio: lo que paga
 *    hoy, los cobros que habrá, el total y que el cobro SE DETIENE SOLO.
 *  · Los planes sueltos debajo, en una rejilla compacta por plan × duración.
 *  · La elegida se marca con un tick y un borde grueso: siempre sabes qué vas
 *    a mandar.
 *  · El ENLACE se ve entero antes de enviarlo, lo da el BACKEND (dominio
 *    oficial) y lleva su semáforo: si a Stripe le falta el precio o el cupón,
 *    la tarjeta sale en rojo y no deja mandarlo.
 *  · "Probar" abre el enlace en otra pestaña: acaba en la página de pago de
 *    Stripe, que es exactamente lo que recibirá el cliente.
 */

const VERDE = "#2E7D46";
const ROJO = "#C2453A";

/** "120,50 €" · "1 €" — sin decimales de relleno. */
function eur(n: number): string {
  return (Number.isInteger(n) ? String(n) : n.toFixed(2).replace(".", ",")) + " €";
}

const PLAN_SELL: Record<PackageTier, string> = {
  train: "Entrenamiento 100 % a tu medida (material, horario, lesiones y nivel), progresión clara semana a semana, app con tu rutina y yo contigo a diario por WhatsApp.",
  nutri: "Nutrición 100 % a tu medida (tus gustos, tus horarios, tus alergias), objetivos calculados sobre tu caso, app de seguimiento y yo contigo a diario por WhatsApp.",
  full: "Entrenamiento y nutrición coordinados y 100 % a tu medida, videollamada de revisión, app de seguimiento y yo contigo a diario por WhatsApp.",
};

/** Mensaje de WhatsApp de lo elegido. Sin emojis (algunos móviles los rompen)
 *  y con *negrita* de WhatsApp. El coach puede editarlo antes de mandarlo. */
function mensajeDe(item: SalesItem): string {
  const inc =
    "Incluye el plan completo: entrenamiento y nutrición 100 % a tu medida, " +
    "WhatsApp conmigo a diario, app de seguimiento y videollamada de revisión.";
  if (item.kind === "oferta") {
    const cobros = item.key === "oferta"
      ? `Pagas ${eur(item.first_eur)} hoy y los otros dos meses ${eur((item.total_eur - item.first_eur) / 2)} cada uno.`
      : `Son dos pagos de ${eur(item.first_eur)}: el primero hoy y el segundo dentro de un mes.`;
    return (
      `*Oferta DQR Full* - programa de 3 meses (${eur(item.total_eur)} en total)\n` +
      `${cobros} Después NO se te cobra nada más: el cobro se detiene solo.\n` +
      `${inc}\n\n` +
      `Empieza aquí: ${item.url}\n` +
      "Pago seguro con Stripe. Sin renovación automática ni sorpresas."
    );
  }
  const tier = item.tier as PackageTier;
  return (
    `*${item.title}* - ${eur(item.total_eur)}\n` +
    `${PLAN_SELL[tier] ?? ""}\n\n` +
    `Pago seguro con Stripe: ${item.url}\n` +
    "Al completar el pago te llega al momento el acceso a tu app y tu cuestionario " +
    "inicial, y nos ponemos en marcha."
  );
}

/** Catálogo completo de precios, para quien pregunta "¿qué tienes?". */
function mensajeCatalogo(items: SalesItem[]): string {
  const planes = items.filter((i) => i.kind === "plan");
  const bloques = (["train", "nutri", "full"] as PackageTier[]).map((t) => {
    const lineas = planes.filter((i) => i.tier === t)
      .map((i) => `· ${i.title.split("·")[1]?.trim() ?? i.title}: ${eur(i.total_eur)}`)
      .join("\n");
    return `*${PACKAGES[t].label}* - ${PACKAGES[t].tagline}\n${lineas}`;
  }).join("\n\n");
  return (
    `*Asesorías DQ - catálogo de planes*\n\n${bloques}\n\n` +
    "Los tres incluyen plan 100 % a tu medida, WhatsApp conmigo a diario y app de seguimiento.\n" +
    "Dime cuál te encaja y te paso el enlace de pago seguro (Stripe) para empezar hoy mismo."
  );
}

/** Tarjeta grande de una OFERTA: lo que paga hoy, los cobros y el total. */
function TarjetaOferta({ item, activa, onElegir }: {
  item: SalesItem; activa: boolean; onElegir: () => void;
}) {
  const color = item.ready ? VERDE : ROJO;
  return (
    <button
      type="button"
      onClick={onElegir}
      aria-pressed={activa}
      className="tap card card-hover relative w-full p-4 text-left"
      style={{
        borderColor: activa ? color : "var(--line-strong)",
        borderWidth: activa ? 2 : 1,
        background: activa ? `color-mix(in srgb, ${color} 8%, var(--surface))` : "var(--surface)",
      }}
    >
      {activa && (
        <span className="absolute right-3 top-3 flex h-6 w-6 items-center justify-center rounded-full text-white"
          style={{ background: color }}>
          <Check size={14} />
        </span>
      )}
      <span className="flex items-center gap-1.5 text-[11px] font-extrabold uppercase tracking-wider"
        style={{ color }}>
        <Sparkles size={12} /> Oferta
      </span>
      <p className="mt-1 text-base font-extrabold" style={{ color: "var(--text)" }}>
        {item.title.replace("Oferta · ", "")}
      </p>
      <p className="mt-2 text-3xl font-extrabold leading-none tabular-nums" style={{ color }}>
        {eur(item.first_eur)}
        <span className="ml-1.5 text-xs font-bold" style={{ color: "var(--text-faint)" }}>hoy</span>
      </p>
      <p className="mt-1.5 text-xs" style={{ color: "var(--text-faint)" }}>{item.subtitle}</p>
      <div className="mt-2.5 flex flex-wrap gap-1.5">
        <span className="rounded-full px-2 py-0.5 text-[11px] font-bold"
          style={{ background: "var(--surface-raised)", color: "var(--text)" }}>
          {item.charges} cobros · {eur(item.total_eur)} en total
        </span>
        {item.auto_stop && (
          <span className="flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-bold"
            style={{ background: `color-mix(in srgb, ${VERDE} 14%, transparent)`, color: VERDE }}>
            <ShieldCheck size={11} /> se detiene solo
          </span>
        )}
      </div>
      {!item.ready && (
        <p className="mt-2 flex items-start gap-1.5 text-[11px] font-semibold" style={{ color: ROJO }}>
          <AlertTriangle size={12} className="mt-0.5 shrink-0" /> No se puede enviar: {item.issue}
        </p>
      )}
    </button>
  );
}

export default function VenderPage() {
  const toast = useToast();
  const [cat, setCat] = useState<SalesCatalogOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refrescando, setRefrescando] = useState(false);
  // Qué se va a enviar: una cosa del catálogo, o el catálogo de precios entero.
  const [sel, setSel] = useState<string | "catalogo" | null>(null);
  const [texto, setTexto] = useState("");
  const [tel, setTel] = useState("");
  const [copiado, setCopiado] = useState<"" | "enlace" | "mensaje">("");

  const cargar = useCallback(async (refresh = false) => {
    setError(null);
    try {
      const c = await api.salesCatalog(refresh);
      setCat(c);
    } catch {
      setError("No se pudo cargar el catálogo. Reinténtalo en un momento.");
    }
  }, []);

  useEffect(() => { void cargar(); }, [cargar]);

  // En DESARROLLO el backend no tiene dominio configurado y devuelve
  // http://localhost (sin el puerto del Vite): el enlace no abriría. Solo en
  // ese caso se usa el origen del navegador. En producción manda el backend.
  const items = useMemo(() => {
    const base = cat?.base_url ?? "";
    const esLocal = base.startsWith("http://localhost") || base.startsWith("http://127.");
    const arreglar = esLocal && window.location.origin !== base;
    return (cat?.items ?? []).map((i) => (arreglar
      ? { ...i, url: i.url.replace(base, window.location.origin) }
      : i));
  }, [cat]);
  const ofertas = useMemo(() => items.filter((i) => i.kind === "oferta"), [items]);
  const planes = useMemo(() => items.filter((i) => i.kind === "plan"), [items]);
  const elegido = useMemo(
    () => (sel && sel !== "catalogo" ? items.find((i) => i.key === sel) ?? null : null),
    [sel, items]);

  function elegir(key: string | "catalogo") {
    if (key === sel) return;         // no machaca lo que el coach haya editado
    setSel(key);
    setCopiado("");
    if (key === "catalogo") { setTexto(mensajeCatalogo(items)); return; }
    const it = items.find((i) => i.key === key);
    setTexto(it ? mensajeDe(it) : "");
  }

  async function copiar(que: "enlace" | "mensaje") {
    const valor = que === "enlace" ? (elegido?.url ?? "") : texto;
    if (!valor) return;
    let ok = true;
    try {
      await navigator.clipboard.writeText(valor);
    } catch {
      // Safari antiguo / http: selección manual, comprobando el resultado real.
      const ta = document.createElement("textarea");
      ta.value = valor;
      document.body.appendChild(ta);
      ta.focus(); ta.select(); ta.setSelectionRange(0, valor.length);
      ok = document.execCommand("copy");
      ta.remove();
    }
    setCopiado(ok ? que : "");
    toast.push(ok
      ? (que === "enlace" ? "Enlace copiado — pégalo donde quieras" : "Mensaje copiado — pégalo en su chat")
      : "No se pudo copiar: selecciona el texto y cópialo a mano");
  }

  function enviarWhatsApp() {
    const digits = waPhone(tel);
    if (!digits) {
      toast.push("Escribe el teléfono, o usa Copiar y pégalo tú en su chat");
      return;
    }
    openWhatsApp(digits, texto);
  }

  if (!cat && !error) return <PageLoader />;

  const bloqueado = sel !== "catalogo" && elegido != null && !elegido.ready;

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-widest" style={{ color: "var(--text-faint)" }}>Panel</p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-semibold" style={{ color: "var(--text)" }}>
            <BadgeEuro size={22} style={{ color: "var(--brand-accent)" }} /> Vender
          </h1>
          <p className="mt-1 text-sm" style={{ color: "var(--text-faint)" }}>
            Elige qué vender y manda el enlace: abre directamente la página de pago de Stripe.
          </p>
        </div>
        <button onClick={async () => { setRefrescando(true); await cargar(true); setRefrescando(false); }}
          disabled={refrescando} className="btn btn-ghost">
          <RefreshCw size={15} className={refrescando ? "animate-spin" : ""} /> Comprobar precios
        </button>
      </header>

      {error && (
        <div className="card mt-4 flex items-center justify-between gap-3 p-3 text-sm"
          style={{ borderColor: ROJO, color: ROJO }}>
          <span>{error}</span>
          <button onClick={() => void cargar()} className="tap font-semibold underline">Reintentar</button>
        </div>
      )}

      {/* Estado de la pasarela: sin esto, el coach no sabía si sus enlaces
          cobran de verdad hasta que un cliente se estrellaba. */}
      {cat && !cat.stripe_enabled && (
        <div className="card mt-4 p-3 text-sm font-semibold" style={{ borderColor: ROJO, color: ROJO }}>
          <AlertTriangle size={15} className="mr-1.5 inline" />
          Stripe no está configurado en el servidor: los enlaces de pago no funcionan.
        </div>
      )}
      {cat?.test_mode && (
        <div className="card mt-4 p-3 text-sm font-semibold" style={{ borderColor: "#B45309", color: "#B45309" }}>
          <AlertTriangle size={15} className="mr-1.5 inline" />
          Stripe está en modo PRUEBA: estos enlaces no cobran dinero real.
        </div>
      )}

      {/* LA OFERTA — lo que más se manda, arriba y con su color propio */}
      <section className="mt-6">
        <h2 className="text-sm font-extrabold uppercase tracking-wide" style={{ color: "var(--text-faint)" }}>
          La oferta · programa de 3 meses
        </h2>
        <p className="mt-0.5 text-xs" style={{ color: "var(--text-faint)" }}>
          Las dos son la MISMA oferta y cuestan lo mismo en total: cambia cómo la paga.
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {ofertas.map((o) => (
            <TarjetaOferta key={o.key} item={o} activa={sel === o.key} onElegir={() => elegir(o.key)} />
          ))}
        </div>
      </section>

      {/* PLANES SUELTOS — rejilla compacta: plan × duración con su importe */}
      <section className="mt-6">
        <h2 className="text-sm font-extrabold uppercase tracking-wide" style={{ color: "var(--text-faint)" }}>
          Planes sueltos · un solo pago
        </h2>
        <div className="mt-3 space-y-2">
          {(["train", "nutri", "full"] as PackageTier[]).map((t) => (
            <div key={t} className="card flex flex-wrap items-center gap-2 p-2.5">
              <span className="w-20 shrink-0 rounded-full px-2 py-0.5 text-center text-[11px] font-bold text-white"
                style={{ background: PACKAGES[t].color }}>
                {PACKAGES[t].short}
              </span>
              {planes.filter((p) => p.tier === t).map((p) => {
                const activa = sel === p.key;
                return (
                  <button key={p.key} type="button" onClick={() => elegir(p.key)} aria-pressed={activa}
                    className="tap flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-semibold"
                    title={p.ready ? p.subtitle : `No se puede enviar: ${p.issue}`}
                    style={activa
                      ? { background: PACKAGES[t].color, color: "white", borderColor: PACKAGES[t].color }
                      : { borderColor: p.ready ? "var(--line-strong)" : ROJO, color: p.ready ? "var(--text)" : ROJO }}>
                    {activa && <Check size={12} />}
                    {p.title.split("·")[1]?.trim()}
                    <span className="font-extrabold tabular-nums">{eur(p.total_eur)}</span>
                    {!p.ready && <AlertTriangle size={12} />}
                  </button>
                );
              })}
            </div>
          ))}
          <button type="button" onClick={() => elegir("catalogo")} aria-pressed={sel === "catalogo"}
            className="tap rounded-xl border px-3 py-1.5 text-xs font-bold"
            style={sel === "catalogo"
              ? { background: "var(--brand-accent)", color: "white", borderColor: "var(--brand-accent)" }
              : { borderColor: "var(--line-strong)", color: "var(--text)" }}>
            Mandar el catálogo entero (sin enlace)
          </button>
        </div>
      </section>

      {/* ENVIAR — el enlace a la vista, comprobable, y el mensaje editable */}
      {sel !== null && (
        <section className="card mt-6 p-4" style={{ borderColor: "var(--brand-accent)" }}>
          <h2 className="flex items-center gap-2 text-sm font-extrabold" style={{ color: "var(--text)" }}>
            <Send size={15} style={{ color: "var(--brand-accent)" }} />
            {sel === "catalogo" ? "Enviar el catálogo de precios" : `Enviar: ${elegido?.title ?? ""}`}
          </h2>

          {elegido && (
            <>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Link2 size={14} style={{ color: "var(--text-faint)" }} />
                <input
                  readOnly
                  value={elegido.url}
                  onFocus={(e) => e.currentTarget.select()}
                  aria-label="Enlace de pago"
                  className="input min-w-0 flex-1 font-mono text-xs"
                />
                <button onClick={() => void copiar("enlace")} className="btn btn-ghost"
                  disabled={!elegido.ready}>
                  {copiado === "enlace" ? <><Check size={14} /> Copiado</> : <><Copy size={14} /> Copiar enlace</>}
                </button>
                <a href={elegido.url} target="_blank" rel="noopener"
                  className="btn btn-ghost"
                  title="Se abre en otra pestaña la MISMA página de pago que verá el cliente">
                  <ExternalLink size={14} /> Probar
                </a>
              </div>
              <p className="mt-1.5 text-[11px]" style={{ color: elegido.ready ? "var(--text-faint)" : ROJO }}>
                {elegido.ready
                  ? "Este enlace abre la página de pago de Stripe con el importe correcto. Al pagar se crea la ficha del cliente y se le envía el acceso y la anamnesis."
                  : `No lo mandes: ${elegido.issue}`}
              </p>
            </>
          )}

          <textarea
            value={texto}
            onChange={(e) => { setTexto(e.target.value); setCopiado(""); }}
            rows={sel === "catalogo" ? 14 : 8}
            aria-label="Mensaje para el cliente"
            className="input mt-3 w-full resize-y font-mono text-xs"
          />

          <div className="mt-2 flex flex-wrap items-center gap-2">
            <button onClick={() => void copiar("mensaje")} disabled={bloqueado} className="btn btn-primary">
              {copiado === "mensaje" ? <><Check size={14} /> Copiado</> : <><Copy size={14} /> Copiar mensaje</>}
            </button>
            <input value={tel} onChange={(e) => setTel(e.target.value)} type="tel"
              placeholder="Tel. del interesado (opcional)" aria-label="Teléfono del interesado"
              className="input w-52 text-xs" />
            <button onClick={enviarWhatsApp} disabled={bloqueado} className="btn btn-ghost"
              style={{ borderColor: "#25D366", color: "#128C4B" }}>
              <MessageCircle size={14} /> Abrir WhatsApp
            </button>
          </div>
          <p className="mt-2 text-[11px]" style={{ color: "var(--text-faint)" }}>
            Lo normal: ya te ha escrito él — pulsa Copiar y pégalo en su chat. El
            teléfono solo hace falta para abrir un chat nuevo.
          </p>
        </section>
      )}
    </div>
  );
}
