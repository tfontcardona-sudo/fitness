import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  ArrowDownLeft,
  ArrowUpRight,
  CheckCheck,
  Download,
  RefreshCw,
} from "lucide-react";
import { ALERTS_REFRESH_MS, api, ApiError, getToken, keepIfSame } from "../lib/api";
import { EmptyState, PageLoader, Spinner, useToast } from "../components/ui";
import type { PaymentOut, PaymentsSummaryOut } from "../types";

/**
 * PAGOS — el libro de caja de Stripe, con cara de app de banco.
 *
 * Responde a las tres preguntas del coach: quién pagó, cuánto y cuándo. Los
 * movimientos los anota el webhook de Stripe (tabla `payments`); aquí solo se
 * leen. Lo que llega nuevo aparece marcado con un punto, como una notificación
 * del banco, y se sella como leído al abrir la pantalla (apaga el badge de la
 * barra pero mantiene el resaltado mientras estás mirando).
 *
 * Los importes vienen en CÉNTIMOS de Stripe: se dividen entre 100 al pintar,
 * nunca se recalculan desde la tabla de precios (un cupón o un reprecio
 * histórico harían mentir a la cifra).
 */

const PAGE = 50;

/** Formateador de dinero por moneda (es-ES: 1.234,50 €). */
const fmtMoney = (cents: number, currency: string) => {
  try {
    return new Intl.NumberFormat("es-ES", {
      style: "currency",
      currency: (currency || "eur").toUpperCase(),
    }).format(cents / 100);
  } catch {
    return `${(cents / 100).toFixed(2)} €`;
  }
};

/** Etiqueta del día para agrupar el feed: Hoy / Ayer / 12 de agosto. */
function dayLabel(iso: string): string {
  const d = new Date(iso);
  const hoy = new Date();
  const ayer = new Date();
  ayer.setDate(hoy.getDate() - 1);
  const mismoDia = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  if (mismoDia(d, hoy)) return "Hoy";
  if (mismoDia(d, ayer)) return "Ayer";
  return d.toLocaleDateString("es-ES", {
    day: "numeric",
    month: "long",
    ...(d.getFullYear() !== hoy.getFullYear() ? { year: "numeric" } : {}),
  });
}

const hora = (iso: string) =>
  new Date(iso).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });

/** Inicial para el círculo del movimiento (como el avatar de la app del banco). */
const inicial = (nombre: string) => (nombre.trim()[0] || "?").toUpperCase();

type Filtro = "todos" | "paid" | "failed" | "refunded" | "orphan";

/** Traduce el filtro de la pantalla a los parámetros del backend. */
function filtroApi(f: Filtro): { status?: string; orphan?: boolean } {
  if (f === "todos") return {};
  if (f === "orphan") return { orphan: true };
  return { status: f };
}

const FILTROS: { id: Filtro; label: string }[] = [
  { id: "todos", label: "Todos" },
  { id: "paid", label: "Cobrados" },
  { id: "failed", label: "Fallidos" },
  { id: "refunded", label: "Devoluciones" },
];

export default function PagosPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [items, setItems] = useState<PaymentOut[] | null>(null);
  const [total, setTotal] = useState(0);
  const [resumen, setResumen] = useState<PaymentsSummaryOut | null>(null);
  const [filtro, setFiltro] = useState<Filtro>("todos");
  const [cargando, setCargando] = useState(false);
  const [falloCarga, setFalloCarga] = useState(false);
  const [sincronizando, setSincronizando] = useState(false);
  const [exportando, setExportando] = useState(false);
  // Los que estaban SIN LEER al entrar: se resaltan mientras dura la visita
  // aunque ya se hayan sellado como leídos (si no, el punto azul desaparecería
  // ante los ojos del coach y no sabría qué era nuevo).
  const [nuevos, setNuevos] = useState<Set<number>>(new Set());
  const [meses, setMeses] = useState<{ month: string; total_cents: number; count: number }[] | null>(null);
  const selladoRef = useRef(false);

  // Gráfica de ingresos: 6 meses netos (cobrado − devuelto, sin pagos de
  // prueba). Se carga una vez y se refresca junto al feed.
  useEffect(() => {
    api.paymentsMonthly(6).then((r) => setMeses(r.months)).catch(() => {});
  }, []);

  const cargar = useCallback(
    (opts: { silencioso?: boolean } = {}) => {
      if (!opts.silencioso) setCargando(true);
      const { status, orphan } = filtroApi(filtro);
      return Promise.all([
        api.listPayments({ limit: PAGE, status, orphan }),
        api.paymentsSummary(),
      ])
        .then(([lista, sum]) => {
          setItems((prev) => {
            // Refresco de fondo: se FUSIONA la primera página con lo que ya hay
            // en pantalla en vez de reemplazarlo. Si no, un cobro nuevo (o el
            // simple polling) tiraba abajo las páginas que el coach había
            // cargado con "Ver más" y la lista saltaba sola al principio.
            if (!opts.silencioso || prev === null) return lista.items;
            const vistos = new Set(prev.map((p) => p.id));
            const recien = lista.items.filter((p) => !vistos.has(p.id));
            if (!recien.length) return prev;
            // Lo que ENTRA mientras miras también se resalta y se sella: si no,
            // el cobro nuevo se colaba sin punto azul y el badge de la barra se
            // quedaba encendido para siempre.
            const sinLeer = recien.filter((p) => !p.seen_at).map((p) => p.id);
            if (sinLeer.length) {
              setNuevos((s) => new Set([...s, ...sinLeer]));
              api.markPaymentsSeen(sinLeer)
                .then((r) => setResumen((s) => (s ? { ...s, unseen: r.unseen } : s)))
                .catch(() => {});
            }
            // Reordenado por fecha REAL de Stripe: una reentrega tardía crea una
            // fila con fecha VIEJA que no puede quedarse pegada arriba (el
            // backend ordena igual: paid_at desc, id desc).
            return [...recien, ...prev].sort((a, b) =>
              a.paid_at === b.paid_at ? b.id - a.id : (a.paid_at < b.paid_at ? 1 : -1));
          });
          setTotal(lista.count);
          setResumen((prev) => keepIfSame(prev, sum));
          setFalloCarga(false);
          // Al abrir la pantalla se sella lo que está A LA VISTA (como al abrir
          // la app del banco): se guarda cuáles eran para seguir resaltándolos
          // mientras dura la visita. Lo que quede en páginas siguientes NO se
          // marca solo — el badge seguiría contándolo y el coach tiene el botón
          // "Marcar todo como leído" para eso.
          if (!selladoRef.current) {
            selladoRef.current = true;
            const sinLeer = lista.items.filter((p) => !p.seen_at).map((p) => p.id);
            if (sinLeer.length) {
              setNuevos(new Set(sinLeer));
              api.markPaymentsSeen(sinLeer)
                .then((r) => setResumen((s) => (s ? { ...s, unseen: r.unseen } : s)))
                .catch(() => {});
            }
          }
        })
        .catch(() => setFalloCarga(true))
        .finally(() => setCargando(false));
    },
    [filtro],
  );

  useEffect(() => {
    cargar();
  }, [cargar]);

  // Refresco de fondo: un cobro nuevo aparece solo, sin recargar la página.
  useEffect(() => {
    const t = window.setInterval(() => {
      if (!document.hidden) cargar({ silencioso: true });
    }, ALERTS_REFRESH_MS);
    return () => window.clearInterval(t);
  }, [cargar]);

  /** Le da salida a un cobro SIN FICHA. El aviso "N sin ficha" no tenía forma
   *  de apagarse: `adopt_orphans` solo reasocia por email y dentro de 30 días,
   *  así que un cobro de otro producto de la cuenta —o uno con el email mal
   *  escrito en el checkout— contaba para siempre. Un aviso que no se puede
   *  resolver se acaba ignorando, y con él los que sí importan. */
  async function descartarHuerfano(id: number) {
    try {
      await api.resolverHuerfano(id);
      setItems((prev) => (prev ? prev.filter((p) => p.id !== id) : prev));
      setTotal((n) => Math.max(0, n - 1));
      setResumen((s) => (s ? { ...s, orphan_count: Math.max(0, s.orphan_count - 1) } : s));
      toast.push("Marcado como ajeno a la asesoría");
    } catch (e) {
      toast.push(e instanceof ApiError ? e.message : "No se pudo marcar", "error");
    }
  }

  async function verMas() {
    if (!items) return;
    setCargando(true);
    try {
      const { status, orphan } = filtroApi(filtro);
      const mas = await api.listPayments({ limit: PAGE, offset: items.length, status, orphan });
      // Si entró un cobro nuevo entre la primera página y esta, el offset se
      // desplaza y Stripe devuelve una fila repetida: se descarta por id (si no,
      // React pintaría dos veces el mismo movimiento con la misma key).
      const vistos = new Set(items.map((p) => p.id));
      const nuevosItems = mas.items.filter((p) => !vistos.has(p.id));
      setItems([...items, ...nuevosItems]);
      setTotal(mas.count);
      // Lo recién mostrado también se da por visto (ya está en pantalla).
      const sinLeer = nuevosItems.filter((p) => !p.seen_at).map((p) => p.id);
      if (sinLeer.length) {
        setNuevos((prev) => new Set([...prev, ...sinLeer]));
        api.markPaymentsSeen(sinLeer)
          .then((r) => setResumen((s) => (s ? { ...s, unseen: r.unseen } : s)))
          .catch(() => {});
      }
    } catch (e) {
      toast.push(e instanceof ApiError ? e.message : "No se pudieron cargar más movimientos", "error");
    } finally {
      setCargando(false);
    }
  }

  async function exportarCsv() {
    // Descarga con JWT en la cabecera (fetch → blob), como los Word del panel.
    setExportando(true);
    try {
      const res = await fetch("/api/payments/export.csv", {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (!res.ok) throw new Error();
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "pagos_dqr.csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      toast.push("No se pudo exportar", "error");
    } finally {
      setExportando(false);
    }
  }

  // Ventana del barrido. El aviso "prueba con menos días" pedía algo que la
  // web no dejaba hacer: no había ningún control de días (auditoría). Ahora
  // sí, y al cortarse el barrido se propone la ventana corta de un clic.
  const [diasSync, setDiasSync] = useState<number | null>(null);

  async function sincronizar(dias?: number) {
    const ventana = dias ?? diasSync ?? undefined;
    setSincronizando(true);
    try {
      const r = await api.syncPayments(ventana ?? undefined);
      // Repetir el mismo barrido lee lo mismo: solo estrechar la ventana avanza.
      const reintenta = !!r.partial && (ventana ?? 0) !== 7;
      if (r.created > 0) {
        // Recarga COMPLETA, no fusión: lo recuperado lleva su fecha real de
        // Stripe, así que entra POR EN MEDIO de la lista (o más abajo de la
        // primera página) y el refresco silencioso —que solo mira la página 1—
        // no lo vería nunca.
        setItems(null);
        selladoRef.current = false;
        await cargar();
      } else {
        await cargar({ silencioso: true });
      }
      if (r.created > 0) {
        toast.push(`${r.created} movimiento${r.created === 1 ? "" : "s"} recuperado${r.created === 1 ? "" : "s"} de Stripe`);
      } else if (r.partial) {
        // La sincronización es LA red de seguridad cuando se pierde un
        // webhook: decir "sin cobros pendientes" cuando ni siquiera ha mirado
        // todo el rango deja al coach tranquilo con facturas sin repescar.
        // Y repetir el MISMO barrido no avanza (vuelve a leer lo mismo): lo
        // que sirve es estrechar la ventana, así que se hace solo una vez.
        toast.push(
          reintenta
            ? "Stripe tiene más movimientos de los que caben en un barrido: repaso los últimos 7 días"
            : "Stripe tiene más movimientos de los que caben en un barrido: revisa los cobros de este rango en tu panel de Stripe",
          "error");
      } else {
        toast.push("Sin cobros pendientes de registrar");
      }
      if (reintenta) {
        setDiasSync(7);
        setSincronizando(false);
        await sincronizar(7);
        return;
      }
      if (r.errors?.length) {
        toast.push(`Stripe no devolvió todo: ${r.errors[0]}`, "error");
      }
    } catch (e) {
      toast.push(e instanceof ApiError ? e.message : "No se pudo sincronizar con Stripe", "error");
    } finally {
      setSincronizando(false);
    }
  }

  async function marcarLeidos() {
    try {
      await api.markPaymentsSeen();
      setNuevos(new Set());
      await cargar({ silencioso: true });
    } catch {
      toast.push("No se pudo marcar como leído", "error");
    }
  }

  // Agrupación por día (cabeceras "Hoy" / "Ayer" / fecha), respetando el orden.
  const grupos = useMemo(() => {
    const out: { dia: string; pagos: PaymentOut[] }[] = [];
    for (const p of items ?? []) {
      const dia = dayLabel(p.paid_at);
      const ultimo = out[out.length - 1];
      if (ultimo && ultimo.dia === dia) ultimo.pagos.push(p);
      else out.push({ dia, pagos: [p] });
    }
    return out;
  }, [items]);

  if (items === null && !falloCarga) return <PageLoader />;

  const mes = resumen?.month_total_cents ?? 0;
  const prev = resumen?.prev_month_total_cents ?? 0;
  const variacion = prev > 0 ? Math.round(((mes - prev) / prev) * 100) : null;
  const mesActual = new Date().toLocaleDateString("es-ES", { month: "long" });

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 md:px-8 md:py-8">
      <header className="mb-6 flex items-end justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-widest text-zinc-500">Pagos</p>
          <h1 className="mt-1 text-2xl font-semibold text-zinc-100">Cobros de Stripe</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={exportarCsv}
            disabled={exportando}
            className="btn btn-ghost"
            title="CSV completo para la gestoría"
          >
            {exportando ? <Spinner /> : <Download size={15} />} Exportar
          </button>
          <button
            onClick={() => sincronizar()}
            disabled={sincronizando}
            className="btn btn-ghost"
            title="Recupera cobros perdidos de Stripe"
          >
            {sincronizando ? <Spinner /> : <RefreshCw size={15} />} Sincronizar
          </button>
          <select
            value={diasSync ?? ""}
            onChange={(e) => setDiasSync(e.target.value ? Number(e.target.value) : null)}
            disabled={sincronizando}
            title="Cuántos días atrás mira el barrido"
            className="input h-9 w-auto text-xs"
          >
            <option value="">todo el rango</option>
            <option value="7">últimos 7 días</option>
            <option value="30">últimos 30 días</option>
            <option value="90">últimos 90 días</option>
          </select>
        </div>
      </header>

      {falloCarga && (
        <div className="card mb-4 flex items-center justify-between gap-3 p-4">
          <span className="text-sm text-zinc-300">No se pudieron cargar</span>
          <button onClick={() => cargar()} className="btn btn-ghost">Reintentar</button>
        </div>
      )}

      {/* Cabecera tipo banco: lo cobrado este mes, de un vistazo. */}
      <div className="card mb-5 p-5">
        <p className="text-xs uppercase tracking-widest text-zinc-500">
          Cobrado en {mesActual}
        </p>
        {/* SIN RESUMEN no se inventa un 0: mientras carga (o si falla) decía
            "0,00 € · 0 cobros" con toda la autoridad de una cifra real, y lo
            primero que mira el coach al abrir Pagos es justo ese número. */}
        <p className="mt-1 text-3xl font-semibold text-zinc-100">
          {resumen ? fmtMoney(mes, resumen.currency ?? "eur") : "—"}
        </p>
        <p className="mt-1 text-sm text-zinc-500">
          {resumen ? (
            <>
              {resumen.month_count} cobro{resumen.month_count === 1 ? "" : "s"}
              {" · mes anterior "}
              {fmtMoney(prev, resumen.currency ?? "eur")}
              {variacion !== null && (
                <span style={{ color: variacion >= 0 ? "#2E7D46" : "#C2453A" }}>
                  {" "}({variacion >= 0 ? "+" : ""}{variacion}%)
                </span>
              )}
            </>
          ) : falloCarga ? "no se pudo cargar el resumen" : "cargando…"}
        </p>
        {/* Neto real tras comisiones de Stripe (solo si hay fee consultado). */}
        {(resumen?.month_fee_cents ?? 0) > 0 && (
          <p className="mt-0.5 text-sm text-zinc-500">
            comisiones Stripe −{fmtMoney(resumen!.month_fee_cents, resumen?.currency ?? "eur")}
            {" · neto "}
            <span className="font-medium text-zinc-300">
              {fmtMoney(mes - resumen!.month_fee_cents, resumen?.currency ?? "eur")}
            </span>
          </p>
        )}
        {/* Gráfica de 6 meses: la tendencia del negocio de un vistazo. Barras
            puras (sin librerías): mes actual en naranja de marca. */}
        {meses && meses.some((m) => m.total_cents > 0) && (
          <div className="mt-4 flex items-end gap-2" style={{ height: 72 }}>
            {(() => {
              const max = Math.max(...meses.map((m) => m.total_cents), 1);
              return meses.map((m, i) => {
                const actual = i === meses.length - 1;
                const alto = Math.max(4, Math.round((Math.max(0, m.total_cents) / max) * 56));
                const etiqueta = new Date(`${m.month}-01T12:00:00`)
                  .toLocaleDateString("es-ES", { month: "short" }).replace(".", "");
                return (
                  <div key={m.month} className="flex flex-1 flex-col items-center gap-1"
                       title={`${etiqueta}: ${fmtMoney(m.total_cents, resumen?.currency ?? "eur")} · ${m.count} cobro${m.count === 1 ? "" : "s"}`}>
                    <div className="w-full rounded-t-md transition-all duration-500"
                         style={{
                           height: alto,
                           background: actual
                             ? "var(--brand-accent)"
                             : "color-mix(in srgb, var(--brand-accent) 25%, transparent)",
                         }} />
                    <span className="text-[10px]" style={{ color: actual ? "var(--brand-accent)" : "var(--text-faint)" }}>
                      {etiqueta}
                    </span>
                  </div>
                );
              });
            })()}
          </div>
        )}
        {/* Avisos que el coach debe perseguir, no un adorno. */}
        <div className="mt-3 flex flex-wrap gap-2">
          {(resumen?.failed_month ?? 0) > 0 && (
            <Chip
              tone="#C2453A"
              icon={AlertTriangle}
              title="Ver solo los cobros fallidos"
              // El chip APLICA el filtro: un clic y el feed enseña solo lo fallido.
              onClick={() => {
                setFiltro("failed");
                setItems(null);
              }}
            >
              {resumen!.failed_month} cobro{resumen!.failed_month === 1 ? "" : "s"} fallido{resumen!.failed_month === 1 ? "" : "s"} este mes
            </Chip>
          )}
          {(resumen?.orphan_count ?? 0) > 0 && (
            <Chip tone="#9A6B15" icon={AlertTriangle}
              title="Ver solo los cobros sin ficha"
              onClick={() => { setFiltro("orphan"); setItems(null); }}>
              {resumen!.orphan_count} sin ficha
            </Chip>
          )}
          {(resumen?.test_count ?? 0) > 0 && (
            <Chip tone="#8B8172">
              {resumen!.test_count} de prueba (no suman)
            </Chip>
          )}
          {resumen && !resumen.stripe_enabled && (
            <Chip tone="#8B8172">Stripe no configurado en este servidor</Chip>
          )}
        </div>
      </div>

      {/* Filtros + marcar leído */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        {/* Con el filtro "Sin ficha" a la vista son cinco chips: en un móvil el
            último quedaba fuera de la pantalla. La tira se desliza sola. */}
        <div className="tab-strip min-w-0">
        <div className="inline-flex rounded-xl border p-1" style={{ borderColor: "var(--line-strong)" }}>
          {[...FILTROS, ...(((resumen?.orphan_count ?? 0) > 0 || filtro === "orphan")
              ? [{ id: "orphan" as Filtro, label: "Sin ficha" }] : [])].map((f) => (
            <button
              key={f.id}
              onClick={() => {
                setFiltro(f.id);
                setItems(null);
              }}
              className="rounded-lg px-3 py-1.5 text-sm font-medium transition-colors"
              style={
                filtro === f.id
                  ? { background: "var(--surface-raised)", color: "var(--brand-accent)" }
                  : { color: "var(--text-faint)" }
              }
            >
              {f.label}
            </button>
          ))}
        </div>
        </div>
        {(resumen?.unseen ?? 0) > 0 && (
          <button onClick={marcarLeidos} className="btn btn-ghost">
            <CheckCheck size={15} /> Marcar todo como leído
          </button>
        )}
      </div>

      {items && items.length === 0 ? (
        <EmptyState
          title="Todavía no hay movimientos"
          hint={
            resumen?.stripe_enabled
              ? "Sincroniza para traer el histórico"
              : "Configura Stripe en el servidor"
          }
        />
      ) : (
        <div className="space-y-5">
          {grupos.map((g) => (
            <section key={g.dia}>
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
                {g.dia}
              </h2>
              <div className="card divide-y overflow-hidden p-0" style={{ borderColor: "var(--line)" }}>
                {g.pagos.map((p) => (
                  <Movimiento
                    key={p.id}
                    pago={p}
                    nuevo={nuevos.has(p.id)}
                    onClick={() => p.client_id && navigate(`/clientes/${p.client_id}`)}
                    // Solo en la vista de huérfanos: ahí es donde el aviso
                    // "N sin ficha" necesita una salida.
                    onDescartar={filtro === "orphan"
                      ? () => descartarHuerfano(p.id)
                      : undefined}
                  />
                ))}
              </div>
            </section>
          ))}

          {items && items.length < total && (
            <button onClick={verMas} disabled={cargando} className="btn btn-ghost w-full">
              {cargando ? <Spinner /> : null} Ver más ({total - items.length} restantes)
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function Chip({ tone, icon: Icon, children, onClick, title }: {
  tone: string; icon?: typeof AlertTriangle; children: React.ReactNode;
  /** Con onClick el chip es un BOTÓN (p. ej. aplicar un filtro del feed). */
  onClick?: () => void; title?: string;
}) {
  const cls = "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium";
  const style = { background: `color-mix(in srgb, ${tone} 14%, transparent)`, color: tone };
  if (onClick) {
    return (
      <button onClick={onClick} title={title} className={cls} style={style}>
        {Icon && <Icon size={13} />}
        {children}
      </button>
    );
  }
  return (
    <span title={title} className={cls} style={style}>
      {Icon && <Icon size={13} />}
      {children}
    </span>
  );
}

/** Una línea del feed: quién, qué plan, a qué hora y cuánto. */
function Movimiento({ pago, nuevo, onClick, onDescartar }: {
  pago: PaymentOut; nuevo: boolean; onClick: () => void;
  onDescartar?: () => void;
}) {
  const cobrado = pago.status === "paid";
  const devuelto = pago.status === "refunded";
  // Baja de suscripción: hecho informativo sin dinero — gris neutro, sin signo.
  const baja = pago.status === "canceled";
  const tono = cobrado ? "#2E7D46" : devuelto ? "#9A6B15" : baja ? "#8B8172" : "#C2453A";
  const signo = cobrado ? "+" : "−";
  const Icono = cobrado ? ArrowUpRight : devuelto ? ArrowDownLeft : AlertTriangle;
  const sinFicha = pago.client_id === null;

  const fila = (
    <button
      onClick={onClick}
      disabled={sinFicha}
      className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors"
      style={{
        background: nuevo ? "color-mix(in srgb, var(--brand-accent) 7%, transparent)" : undefined,
        cursor: sinFicha ? "default" : "pointer",
      }}
    >
      {/* Círculo con la inicial, como el avatar de un movimiento del banco */}
      <span
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-semibold"
        style={{ background: `color-mix(in srgb, ${tono} 14%, transparent)`, color: tono }}
      >
        {sinFicha ? <Icono size={16} /> : inicial(pago.display_name)}
      </span>

      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-2">
          {nuevo && (
            <span
              className="h-2 w-2 shrink-0 rounded-full"
              style={{ background: "var(--brand-accent)" }}
              aria-label="sin leer"
            />
          )}
          <span className="truncate text-sm font-medium text-zinc-100">{pago.display_name}</span>
          {!pago.livemode && (
            <span className="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase"
                  style={{ background: "color-mix(in srgb, #8B8172 18%, transparent)", color: "#8B8172" }}>
              prueba
            </span>
          )}
        </span>
        <span className="mt-0.5 block truncate text-xs text-zinc-500">
          {hora(pago.paid_at)}
          {pago.description ? ` · ${pago.description}` : ""}
          {!cobrado && !devuelto && !baja ? " · no se pudo cobrar" : ""}
          {sinFicha ? " · sin ficha asociada" : ""}
        </span>
      </span>

      <span className="shrink-0 text-right">
        <span className="block text-sm font-semibold" style={{ color: tono }}>
          {baja ? "baja" : `${signo}${fmtMoney(pago.amount_cents, pago.currency)}`}
        </span>
      </span>
    </button>
  );

  // El botón de descartar no puede ir DENTRO del <button> de la fila (un botón
  // dentro de otro no es HTML válido y el clic se lo come el de fuera).
  if (!onDescartar) return fila;
  return (
    <div className="flex items-center gap-2 pr-3">
      <span className="min-w-0 flex-1">{fila}</span>
      <button
        onClick={onDescartar}
        className="btn btn-ghost shrink-0 !px-2 !py-1 text-xs"
        title="Este cobro no es de la asesoría: deja de contar en el aviso"
      >
        No es mío
      </button>
    </div>
  );
}
