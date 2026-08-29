import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle, BadgeEuro, Check, Copy, ExternalLink, Link2, MessageCircle,
  RefreshCw, Send, ShieldCheck,
} from "lucide-react";
import { api } from "../lib/api";
import { PACKAGES } from "../lib/packages";
import { openWhatsApp, waPhone } from "../lib/whatsapp";
import { useToast, PageLoader } from "../components/ui";
import type { PackageTier, SalesCatalogOut, SalesItem } from "../types";

/**
 * VENDER — la pantalla desde la que el coach manda el enlace de pago.
 *
 * Antes era un desplegable dentro del panel "Hoy" con chips pequeños: no se
 * veía qué estabas eligiendo, ni cuánto cobraba, ni si el enlace funcionaba.
 * Ahora, de arriba abajo:
 *  · el ESTADO de la pasarela siempre visible (activo / prueba / apagado);
 *  · LA OFERTA como una sola cosa —programa cerrado de 3 meses, 241 € en
 *    total— y dentro las DOS formas de pagarla, cada una con su línea de
 *    tiempo de cobros y su final marcado ("se detiene sola");
 *  · los planes sueltos en una tabla plan × duración;
 *  · y la zona de ENVIAR, con el enlace a la vista, lo que va a cobrar y las
 *    acciones (copiar enlace, copiar mensaje, WhatsApp, probar).
 * Lo elegido se marca con tick, borde y un resumen en la zona de envío: en
 * ningún momento se manda algo distinto de lo que se cree.
 */

const VERDE = "#2E7D46";
const AMBAR = "#B45309";
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
  if (item.kind === "oferta") {
    // El calendario lo manda el backend con los importes reales: aquí no se
    // reconstruye ninguna cifra.
    const cobros = item.schedule.map((c) => `${c.when.toLowerCase()} ${eur(c.eur)}`).join(", ");
    return (
      `*Oferta DQR Full* - programa de 3 meses (${eur(item.total_eur)} en total)\n` +
      `Pagas: ${cobros}. Después NO se te cobra nada más: el cobro se detiene solo.\n` +
      "Incluye el plan completo: entrenamiento y nutrición 100 % a tu medida, " +
      "WhatsApp conmigo a diario, app de seguimiento y videollamada de revisión.\n\n" +
      `Empieza aquí: ${item.url}\n` +
      "Pago seguro con Stripe. Sin renovación automática ni sorpresas."
    );
  }
  const tier = item.tier as PackageTier;
  return (
    `*${item.tier_label} ${item.period_label.toLowerCase()}* - ${eur(item.total_eur)}` +
    (item.per_month_eur ? ` (sale a ${eur(item.per_month_eur)}/mes)` : "") + "\n" +
    `${PLAN_SELL[tier] ?? ""}\n\n` +
    `Pago seguro con Stripe: ${item.url}\n` +
    "Es un pago único: no se renueva solo. Al completarlo te llega al momento el " +
    "acceso a tu app y tu cuestionario inicial, y nos ponemos en marcha."
  );
}

/** Catálogo completo de precios, para quien pregunta "¿qué tienes?". */
function mensajeCatalogo(items: SalesItem[]): string {
  const planes = items.filter((i) => i.kind === "plan");
  const bloques = (["train", "nutri", "full"] as PackageTier[]).map((t) => {
    const lineas = planes.filter((i) => i.tier === t)
      .map((i) => `· ${i.period_label}: ${eur(i.total_eur)}`
        + (i.per_month_eur ? ` (sale a ${eur(i.per_month_eur)}/mes)` : ""))
      .join("\n");
    return `*${PACKAGES[t].label}* - ${PACKAGES[t].tagline}\n${lineas}`;
  }).join("\n\n");
  return (
    `*Asesorías DQ - catálogo de planes*\n\n${bloques}\n\n` +
    "Los tres incluyen plan 100 % a tu medida, WhatsApp conmigo a diario y app de seguimiento.\n" +
    "Dime cuál te encaja y te paso el enlace de pago seguro (Stripe) para empezar hoy mismo."
  );
}

/** Línea de tiempo de cobros: cuándo, cuánto y dónde SE ACABA. */
function Cobros({ item, color }: { item: SalesItem; color: string }) {
  return (
    <span className="mt-2 flex flex-wrap items-center gap-1 text-[11px]">
      {item.schedule.map((c, i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 && <span aria-hidden style={{ color: "var(--text-faint)" }}>→</span>}
          <span className="rounded-md px-1.5 py-0.5 font-semibold tabular-nums"
            style={{ background: "var(--surface-raised)", color: "var(--text)" }}>
            {c.when}: {eur(c.eur)}
          </span>
        </span>
      ))}
      {item.auto_stop && (
        <span className="flex items-center gap-1">
          <span aria-hidden style={{ color: "var(--text-faint)" }}>→</span>
          <span className="flex items-center gap-1 rounded-md px-1.5 py-0.5 font-bold"
            style={{ background: `color-mix(in srgb, ${color} 14%, transparent)`, color }}>
            <ShieldCheck size={11} /> Fin
          </span>
        </span>
      )}
    </span>
  );
}

/** Una FORMA DE PAGAR la oferta. La superficie de elección es un radio y los
 *  botones de acción son HERMANOS suyos: un botón dentro de otro no es HTML
 *  válido y los clics se solapan. */
function FormaDePago({ item, activa, testMode, onElegir, onCopiar, onProbar }: {
  item: SalesItem; activa: boolean; testMode: boolean;
  onElegir: () => void; onCopiar: () => void; onProbar: () => void;
}) {
  const color = item.ready ? VERDE : ROJO;
  return (
    <div className="card relative p-4"
      style={{
        borderColor: activa ? color : "var(--line-strong)",
        borderWidth: activa ? 2 : 1,
        background: activa ? `color-mix(in srgb, ${color} 8%, var(--surface))` : "var(--surface)",
      }}>
      <button type="button" role="radio" aria-checked={activa} onClick={onElegir}
        className="tap block w-full text-left">
        {activa && (
          <span className="absolute right-3 top-3 flex h-6 w-6 items-center justify-center rounded-full text-white"
            style={{ background: color }}>
            <Check size={14} />
          </span>
        )}
        <span className="block text-sm font-extrabold" style={{ color: "var(--text)" }}>
          {item.period_label}
        </span>
        <span className="mt-1.5 block text-3xl font-extrabold leading-none tabular-nums"
          style={{ color }}>
          {eur(item.first_eur)}
          <span className="ml-1.5 text-xs font-bold" style={{ color: "var(--text-faint)" }}>hoy</span>
        </span>
        <Cobros item={item} color={color} />
        <span className="mt-2 block text-[11px]" style={{ color: "var(--text-faint)" }}>
          Se detiene sola: no hay {item.charges + 1}º cobro. Al pagar se crea su
          ficha y le llegan el acceso a la app y su cuestionario.
        </span>
        {testMode && (
          <span className="mt-2 inline-block rounded-md px-1.5 py-0.5 text-[10px] font-bold"
            style={{ background: `color-mix(in srgb, ${AMBAR} 14%, transparent)`, color: AMBAR }}>
            MODO PRUEBA · no cobra dinero real
          </span>
        )}
        {!item.ready && (
          <span className="mt-2 flex items-start gap-1.5 text-[11px] font-semibold" style={{ color: ROJO }}>
            <AlertTriangle size={12} className="mt-0.5 shrink-0" /> No se puede enviar: {item.issue}
          </span>
        )}
      </button>
      <div className="mt-3 flex flex-wrap gap-2">
        <button onClick={onCopiar} disabled={!item.ready} className="btn btn-primary !py-1.5 text-xs">
          <Copy size={13} /> Copiar mensaje
        </button>
        <button onClick={onProbar} disabled={!item.ready} className="btn btn-ghost !py-1.5 text-xs"
          title="Abre en otra pestaña la MISMA página de pago que verá el cliente. No cobra nada.">
          <ExternalLink size={13} /> Probar
        </button>
      </div>
    </div>
  );
}

export default function VenderPage() {
  const toast = useToast();
  const [cat, setCat] = useState<SalesCatalogOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refrescando, setRefrescando] = useState(false);
  const [comprobado, setComprobado] = useState<Date | null>(null);
  // Qué se va a enviar: una cosa del catálogo, o el catálogo de precios entero.
  const [sel, setSel] = useState<string | "catalogo" | null>(null);
  const [texto, setTexto] = useState("");
  const [tel, setTel] = useState("");
  // Confirmación de QUÉ se copió: detectar el clic equivocado antes de pegarlo.
  const [copia, setCopia] = useState<string | null>(null);

  const cargar = useCallback(async (refresh = false) => {
    setError(null);
    try {
      const c = await api.salesCatalog(refresh);
      setCat(c);
      setComprobado(new Date());
    } catch {
      setError("No se pudo cargar el catálogo. Reinténtalo en un momento.");
    }
  }, []);

  useEffect(() => { void cargar(); }, [cargar]);

  // En DESARROLLO el backend no tiene dominio y devuelve http://localhost (sin
  // el puerto de Vite): el enlace no abriría. Solo entonces manda el origen del
  // navegador; en producción el enlace lo da el backend.
  const items = useMemo(() => {
    const base = cat?.base_url ?? "";
    const esLocal = base.startsWith("http://localhost") || base.startsWith("http://127.");
    const arreglar = esLocal && window.location.origin !== base;
    return (cat?.items ?? []).map((i) => (arreglar
      ? { ...i, url: i.url.replace(base, window.location.origin) } : i));
  }, [cat]);

  const ofertas = useMemo(() => items.filter((i) => i.kind === "oferta"), [items]);
  const planes = useMemo(() => items.filter((i) => i.kind === "plan"), [items]);
  const elegido = useMemo(
    () => (sel && sel !== "catalogo" ? items.find((i) => i.key === sel) ?? null : null),
    [sel, items]);

  const envioRef = useRef<HTMLElement | null>(null);

  function elegir(key: string | "catalogo") {
    if (key === sel) return;         // no machaca lo que el coach haya editado
    setSel(key);
    setCopia(null);
    if (key === "catalogo") setTexto(mensajeCatalogo(items));
    else {
      const it = items.find((i) => i.key === key);
      setTexto(it ? mensajeDe(it) : "");
    }
    // El bloque de envío se trae a la vista: en el móvil quedaba debajo del
    // pliegue y parecía que elegir no hacía nada.
    setTimeout(() => {
      envioRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }, 60);
  }

  async function alPortapapeles(valor: string): Promise<boolean> {
    try {
      await navigator.clipboard.writeText(valor);
      return true;
    } catch {
      // Safari antiguo / http: selección manual, comprobando el resultado real
      // (un "Copiado" en falso haría pegar un chat vacío).
      const ta = document.createElement("textarea");
      ta.value = valor;
      document.body.appendChild(ta);
      ta.focus(); ta.select(); ta.setSelectionRange(0, valor.length);
      const ok = document.execCommand("copy");
      ta.remove();
      return ok;
    }
  }

  /** Copia y CONFIRMA qué se ha copiado (nombre + dinero): así se pilla el
   *  clic equivocado antes de pegarlo en el chat del cliente. */
  async function copiar(que: "enlace" | "mensaje", item?: SalesItem) {
    const it = item ?? elegido;
    const valor = que === "enlace" ? (it?.url ?? "") : (item ? mensajeDe(item) : texto);
    if (!valor) return;
    const ok = await alPortapapeles(valor);
    const nombre = it
      ? `${it.tier_label} · ${it.period_label} (${eur(it.first_eur)} hoy · ${eur(it.total_eur)} en total)`
      : "el catálogo de precios";
    setCopia(ok ? `Copiado ${que === "enlace" ? "el enlace" : "el mensaje"} de: ${nombre}` : null);
    toast.push(ok
      ? (que === "enlace" ? "Enlace copiado" : "Mensaje copiado — pégalo en su chat")
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
  const estado = !cat?.stripe_enabled
    ? { color: ROJO, texto: "Stripe apagado · los enlaces no funcionan" }
    : cat.test_mode
      ? { color: AMBAR, texto: "Stripe en PRUEBA · estos enlaces no cobran" }
      : { color: VERDE, texto: "Stripe activo · cobra de verdad" };

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 pb-28 sm:pb-8">
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
        <div className="flex flex-col items-start gap-1.5 sm:items-end">
          {/* Estado SIEMPRE a la vista (no solo cuando falla): saber que está
              bien es tan importante como enterarse de que está roto. */}
          <span className="rounded-full px-2.5 py-1 text-[11px] font-bold"
            style={{ background: `color-mix(in srgb, ${estado.color} 12%, transparent)`, color: estado.color }}>
            {estado.texto}
          </span>
          <span className="flex items-center gap-2 text-[11px]" style={{ color: "var(--text-faint)" }}>
            {comprobado && `Precios comprobados a las ${comprobado.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })}`}
            <button onClick={async () => { setRefrescando(true); await cargar(true); setRefrescando(false); }}
              disabled={refrescando} className="btn btn-ghost !px-2 !py-1 text-[11px]">
              <RefreshCw size={12} className={refrescando ? "animate-spin" : ""} /> Comprobar
            </button>
          </span>
        </div>
      </header>

      {error && (
        <div className="card mt-4 flex items-center justify-between gap-3 p-3 text-sm"
          style={{ borderColor: ROJO, color: ROJO }}>
          <span>{error}</span>
          <button onClick={() => void cargar()} className="tap font-semibold underline">Reintentar</button>
        </div>
      )}

      {/* LA OFERTA — una sola cosa, con dos formas de pagarla */}
      {ofertas.length > 0 && (
        <section className="card mt-6 p-5"
          style={{
            borderColor: "var(--brand-accent)", borderWidth: 2,
            background: "color-mix(in srgb, var(--brand-accent) 6%, var(--surface))",
          }}>
          <p className="text-[11px] font-extrabold uppercase tracking-widest"
            style={{ color: "var(--brand-accent)" }}>
            La oferta · programa cerrado de 3 meses · {ofertas[0].tier_label}
          </p>
          <p className="mt-1 text-4xl font-extrabold leading-none tabular-nums"
            style={{ color: "var(--text)" }}>
            {eur(ofertas[0].total_eur)}
            <span className="ml-2 text-sm font-bold" style={{ color: "var(--text-faint)" }}>en total</span>
          </p>
          <p className="mt-1.5 text-xs" style={{ color: "var(--text-faint)" }}>
            Las dos formas cuestan lo mismo. Solo cambia cómo lo paga.
          </p>

          <p className="mt-4 text-xs font-bold" style={{ color: "var(--text)" }}>Elige cómo lo paga:</p>
          <div role="radiogroup" aria-label="Cómo paga la oferta"
            className="mt-2 grid gap-3 sm:grid-cols-2">
            {ofertas.map((o) => (
              <FormaDePago
                key={o.key} item={o} activa={sel === o.key} testMode={!!cat?.test_mode}
                onElegir={() => elegir(o.key)}
                onCopiar={() => { if (sel !== o.key) elegir(o.key); void copiar("mensaje", o); }}
                onProbar={() => window.open(o.url, "_blank", "noopener")}
              />
            ))}
          </div>
        </section>
      )}

      {/* PLANES SUELTOS — tabla plan × duración, un pago cada uno */}
      <section className="mt-6">
        <h2 className="text-sm font-extrabold uppercase tracking-wide" style={{ color: "var(--text-faint)" }}>
          Planes sueltos · un solo pago, no se renuevan
        </h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[30rem] border-separate" style={{ borderSpacing: "0 0.4rem" }}>
            <thead>
              <tr className="text-[11px] uppercase tracking-wide" style={{ color: "var(--text-faint)" }}>
                <th className="w-24 text-left font-bold">Plan</th>
                {["Mensual", "Trimestral", "Semestral"].map((d) => (
                  <th key={d} className="text-left font-bold">{d}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(["train", "nutri", "full"] as PackageTier[]).map((t) => (
                <tr key={t}>
                  <th scope="row" className="text-left">
                    <span className="flex items-center gap-2 text-xs font-bold" style={{ color: "var(--text)" }}>
                      <span className="inline-block h-5 w-1 rounded-full"
                        style={{ background: PACKAGES[t].color }} aria-hidden />
                      {PACKAGES[t].short}
                    </span>
                  </th>
                  {planes.filter((p) => p.tier === t).map((p) => {
                    const activa = sel === p.key;
                    return (
                      <td key={p.key} className="pr-2">
                        <button type="button" aria-pressed={activa} onClick={() => elegir(p.key)}
                          title={p.ready ? p.subtitle : `No se puede enviar: ${p.issue}`}
                          className="tap w-full rounded-xl border px-2.5 py-1.5 text-left text-xs"
                          style={activa
                            ? { background: PACKAGES[t].color, color: "white", borderColor: PACKAGES[t].color }
                            : { borderColor: p.ready ? "var(--line-strong)" : ROJO, color: p.ready ? "var(--text)" : ROJO }}>
                          <span className="flex items-center gap-1 font-extrabold tabular-nums">
                            {activa && <Check size={12} />}
                            {eur(p.total_eur)}
                            {!p.ready && <AlertTriangle size={12} />}
                          </span>
                          {p.per_month_eur && (
                            <span className="block opacity-75">{eur(p.per_month_eur)}/mes</span>
                          )}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <button type="button" onClick={() => elegir("catalogo")} aria-pressed={sel === "catalogo"}
          className="tap mt-2 rounded-xl border border-dashed px-3 py-1.5 text-xs font-bold"
          style={sel === "catalogo"
            ? { background: "var(--brand-accent)", color: "white", borderColor: "var(--brand-accent)" }
            : { borderColor: "var(--line-strong)", color: "var(--text)" }}>
          Mandar el catálogo entero (sin enlace)
        </button>
      </section>

      {/* ENVIAR — qué se manda, el enlace a la vista y el mensaje editable */}
      {sel !== null && (
        <section ref={envioRef} className="card mt-6 p-4"
          style={{ borderColor: "var(--brand-accent)", borderWidth: 2 }}>
          <p className="text-[11px] font-bold uppercase tracking-wide" style={{ color: "var(--text-faint)" }}>
            Vas a mandar
          </p>
          <h2 className="flex items-center gap-2 text-sm font-extrabold" style={{ color: "var(--text)" }}>
            <Send size={15} style={{ color: "var(--brand-accent)" }} />
            {sel === "catalogo" ? "El catálogo de precios (sin enlace de pago)"
              : `${elegido?.tier_label} · ${elegido?.period_label}`}
          </h2>
          {elegido && (
            <p aria-live="polite" className="mt-0.5 text-xs" style={{ color: "var(--text-faint)" }}>
              {eur(elegido.first_eur)} hoy · {elegido.charges} {elegido.charges === 1 ? "cobro" : "cobros"} ·{" "}
              {eur(elegido.total_eur)} en total{elegido.auto_stop ? " · se detiene sola" : " · no se renueva"}
            </p>
          )}

          {elegido && (
            <>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Link2 size={14} style={{ color: "var(--text-faint)" }} />
                <input readOnly value={elegido.url} onFocus={(e) => e.currentTarget.select()}
                  aria-label="Enlace de pago" className="input min-w-0 flex-1 font-mono text-xs" />
                <button onClick={() => void copiar("enlace")} className="btn btn-ghost"
                  disabled={!elegido.ready}>
                  <Copy size={14} /> Copiar enlace
                </button>
                <a href={elegido.url} target="_blank" rel="noopener" className="btn btn-ghost"
                  title="Abre en otra pestaña la MISMA página de pago que verá el cliente. No cobra nada: la sesión caduca sola en Stripe.">
                  <ExternalLink size={14} /> Probar
                </a>
              </div>
              <p className="mt-1.5 text-[11px]" style={{ color: elegido.ready ? "var(--text-faint)" : ROJO }}>
                {elegido.ready
                  ? "Al abrirlo, el cliente va directo a la página de pago de Stripe. Al pagar se crea su ficha y se le envía el acceso y la anamnesis."
                  : `No lo mandes: ${elegido.issue}`}
              </p>
            </>
          )}

          <textarea value={texto} onChange={(e) => { setTexto(e.target.value); setCopia(null); }}
            rows={sel === "catalogo" ? 14 : 9} aria-label="Mensaje para el cliente"
            className="input mt-3 w-full resize-y font-mono text-xs" />

          <div className="mt-2 flex flex-wrap items-center gap-2">
            <button onClick={() => void copiar("mensaje")} disabled={bloqueado} className="btn btn-primary">
              <Copy size={14} /> Copiar mensaje
            </button>
            <input value={tel} onChange={(e) => setTel(e.target.value)} type="tel"
              placeholder="Tel. del interesado (opcional)" aria-label="Teléfono del interesado"
              className="input w-52 text-xs" />
            <button onClick={enviarWhatsApp} disabled={bloqueado} className="btn btn-ghost"
              style={{ borderColor: "#25D366", color: "#128C4B" }}>
              <MessageCircle size={14} /> Abrir WhatsApp
            </button>
          </div>

          {/* Confirmación de QUÉ se copió: pilla el clic equivocado antes de
              pegarlo en el chat del cliente. */}
          {copia && (
            <p aria-live="polite" className="mt-2 flex items-center gap-1.5 text-xs font-semibold"
              style={{ color: VERDE }}>
              <Check size={14} /> {copia}
            </p>
          )}
          <p className="mt-2 text-[11px]" style={{ color: "var(--text-faint)" }}>
            Lo normal: ya te ha escrito él — pulsa Copiar y pégalo en su chat. El
            teléfono solo hace falta para abrir un chat nuevo.
          </p>
        </section>
      )}

      {/* BARRA PEGAJOSA (móvil): las dos acciones de verdad, siempre a mano */}
      {sel !== null && (
        <div className="fixed inset-x-0 z-30 border-t px-3 py-2 sm:hidden"
          style={{
            bottom: "calc(3.75rem + env(safe-area-inset-bottom))",
            background: "var(--surface)", borderColor: "var(--line-strong)",
            boxShadow: "0 -6px 18px rgba(38,33,26,0.10)",
          }}>
          <div className="flex items-center gap-2">
            <span className="min-w-0 flex-1">
              <span className="block truncate text-xs font-bold" style={{ color: "var(--text)" }}>
                {sel === "catalogo" ? "Catálogo de precios" : `${elegido?.tier_label} · ${elegido?.period_label}`}
              </span>
              <span className="block truncate text-[11px]" style={{ color: "var(--text-faint)" }}>
                {sel === "catalogo" ? "sin enlace de pago" : elegido?.subtitle}
              </span>
            </span>
            <button onClick={() => void copiar("mensaje")} disabled={bloqueado}
              className="btn btn-primary !px-3 !py-2 text-xs">
              <Copy size={14} /> Copiar
            </button>
            <button onClick={enviarWhatsApp} disabled={bloqueado} aria-label="Abrir WhatsApp"
              className="btn btn-ghost !px-3 !py-2"
              style={{ borderColor: "#25D366", color: "#128C4B" }}>
              <MessageCircle size={15} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
