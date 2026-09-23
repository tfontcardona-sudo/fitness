/**
 * TODO lo del dinero de UN cliente, en un sitio: lo que ha pagado, lo que
 * debe, cómo paga y cuándo le toca el siguiente.
 *
 * Aquí viven las tres piezas que lo cuentan, y las tres leen el MISMO bloque
 * que calcula el backend (`services/payment_profile`, que viaja en
 * `ClientOut.pago` y en `GET /clients/{id}/pago`). Ninguna deduce nada por su
 * cuenta: el panel llegó a tener tres corazonadas distintas sobre "¿está
 * pagado?" y se contradecían entre ellas.
 *
 *   ResumenDePago   la tarjeta de la ficha: total pagado, último cobro con su
 *                   método, cadencia y próximo pago.
 *   CobroManual     anotar un cobro de FUERA de Stripe, con memoria: llega con
 *                   el importe de su plan puesto y diciendo cuándo tocará el
 *                   siguiente.
 *   BloqueoPorPago  la pantalla que sustituye a la ficha cuando el cliente no
 *                   ha pagado, con todo lo necesario para cobrarle allí mismo.
 */
import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CalendarClock, CreditCard, Eye, MessageCircle, Wallet } from "lucide-react";
import { api } from "../lib/api";
import { copiarConAviso } from "../lib/clipboard";
import { openWhatsApp, waPhone } from "../lib/whatsapp";
import { useToast } from "./ui";
import type { ClientOut, EstadoDePagoOut, PagoDelCliente } from "../types";

/** Céntimos → "129,00 €". Mismo formato que el backend (`payment_profile.euros`). */
export function euros(cents: number | null | undefined): string {
  return ((cents ?? 0) / 100).toLocaleString("es-ES", {
    style: "currency", currency: "EUR",
  });
}

function fecha(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-ES", {
    day: "2-digit", month: "short", year: "numeric",
  });
}

/** HOY en la zona del navegador, para el `max` del selector de fecha. Con la
 *  de UTC, de madrugada el coach no podía anotar un cobro de hoy. */
export function hoyLocal(): string {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
    .toISOString().slice(0, 10);
}

/** El estado de pago con todo lo necesario para cobrar (enlace incluido). Se
 *  pide una vez y se puede refrescar tras anotar un cobro. */
export function useEstadoDePago(clientId: number, activo = true) {
  const [pago, setPago] = useState<EstadoDePagoOut | null>(null);
  const [error, setError] = useState(false);
  const cargar = useCallback(() => {
    if (!activo) return;
    setError(false);
    api.estadoDePago(clientId)
      .then(setPago)
      .catch(() => setError(true));
  }, [clientId, activo]);
  useEffect(cargar, [cargar]);
  return { pago, error, recargar: cargar };
}

// ---------------------------------------------------------------- resumen ---

/** La tarjeta del dinero en la ficha: cuánto lleva pagado, cuándo fue el
 *  último, POR DÓNDE entró y cuándo toca el siguiente.
 *
 *  La ficha solo decía "Pagado" o "Pago pendiente": delante de un cliente que
 *  pregunta "¿cuánto llevo?" o "¿cuándo me toca?", el coach tenía que abrir el
 *  libro de caja y sumar a ojo. */
export function ResumenDePago({ pago }: { pago: PagoDelCliente }) {
  const alDia = pago.situacion === "al_dia";
  const filas: [string, string][] = [];
  if (pago.total_cents != null && (pago.num_pagos ?? 0) > 0) {
    filas.push(["Lleva pagado", `${euros(pago.total_cents)} · ${pago.num_pagos} ${(pago.num_pagos ?? 0) === 1 ? "cobro" : "cobros"}`]);
  }
  if (pago.ultimo_pago_en) {
    const via = pago.metodo_label ? ` · ${pago.metodo_label}` : "";
    const cuanto = pago.ultimo_importe_cents ? `${euros(pago.ultimo_importe_cents)} · ` : "";
    filas.push(["Último cobro", `${cuanto}${fecha(pago.ultimo_pago_en)}${via}`]);
  }
  filas.push(["Paga", pago.cadencia_label]);
  if (pago.domiciliado) {
    filas.push(["Próximo", "se cobra solo (suscripción activa)"]);
  } else if (pago.proximo_pago) {
    const d = pago.dias_para_pago;
    const cola = d == null ? "" : d < 0 ? ` · vencido hace ${-d} d`
      : d === 0 ? " · hoy" : ` · en ${d} d`;
    filas.push(["Próximo", `${fecha(pago.proximo_pago)}${cola}`]);
  }

  return (
    <div className="rounded-xl border p-3" style={{
      borderColor: alDia ? "var(--line-strong)" : "#C2453A",
      background: alDia ? undefined : "color-mix(in srgb, #C2453A 8%, transparent)",
    }}>
      <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold"
         style={{ color: alDia ? undefined : "#C2453A" }}>
        <Wallet size={13} className="shrink-0" />
        {alDia ? "Sus pagos" : `Falta pago · ${pago.motivo_corto}`}
      </p>
      {!alDia && (
        <p className="mb-2 text-[11px] leading-snug" style={{ color: "#C2453A" }}>
          {pago.motivo_texto}
          {pago.desde ? ` Desde el ${fecha(pago.desde)}.` : ""}
        </p>
      )}
      <dl className="space-y-1">
        {filas.map(([k, v]) => (
          <div key={k} className="flex items-baseline justify-between gap-3">
            <dt className="shrink-0 text-[11px] text-zinc-500">{k}</dt>
            <dd className="text-right text-[11px] font-medium text-zinc-300">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

// ----------------------------------------------------------- cobro a mano ---

/** Anotar un cobro que NO pasó por Stripe (efectivo, transferencia, Bizum).
 *
 *  Con MEMORIA: llega con el importe de SU plan escrito, dice cuál fue el
 *  último cobro y cuándo tocará el siguiente. El formulario anterior pedía un
 *  importe a secas, así que el coach tenía que acordarse de la tarifa de cada
 *  cliente — y un 1290 en vez de 129 entraba en el total del mes, en la
 *  gráfica y en el CSV de la gestoría. */
export function CobroManual({ client, onDone, abiertoPorDefecto = false }: {
  client: ClientOut; onDone: () => void; abiertoPorDefecto?: boolean;
}) {
  const toast = useToast();
  const [abierto, setAbierto] = useState(abiertoPorDefecto);
  const { pago, recargar } = useEstadoDePago(client.id, abierto);
  const [importe, setImporte] = useState("");
  const [tocado, setTocado] = useState(false);
  const [metodo, setMetodo] = useState<"efectivo" | "transferencia" | "bizum" | "otro">("transferencia");
  const [fechaCobro, setFechaCobro] = useState(hoyLocal);
  // El 409 de duplicado pide "añádele una nota que los distinga" y el
  // formulario no tenía dónde escribirla: la instrucción era imposible de
  // seguir (el campo ya viajaba en el schema).
  const [nota, setNota] = useState("");
  const [guardando, setGuardando] = useState(false);

  // El importe de SU plan, puesto solo mientras el coach no haya tecleado: si
  // lo pisáramos al recargar, le borraríamos lo que está escribiendo.
  useEffect(() => {
    if (tocado || !pago?.importe_previsto_cents) return;
    setImporte((pago.importe_previsto_cents / 100).toFixed(2).replace(".", ","));
  }, [pago, tocado]);

  // Coma o punto: en España se teclea "129,50".
  const eur = Number((importe || "").replace(",", "."));
  const valido = Number.isFinite(eur) && eur > 0;
  const previsto = pago?.importe_previsto_cents ?? null;
  // Aviso, NUNCA reescritura: el coach puede cobrar un importe distinto del de
  // tarifa (un extra, un descuento acordado) y corregírselo en silencio sería
  // falsear su libro de caja. Pero un 1290 tecleado por 129 tiene que cantar.
  const descuadre = valido && previsto != null &&
    Math.abs(Math.round(eur * 100) - previsto) >= Math.max(500, previsto * 0.2);

  async function registrar() {
    if (!valido || guardando) return;
    setGuardando(true);
    try {
      await api.registrarCobroManual({
        client_id: client.id, amount_eur: eur, method: metodo, paid_on: fechaCobro,
        note: nota.trim() || undefined,
      });
      toast.push(`Cobro de ${euros(Math.round(eur * 100))} anotado · ya está en Pagos`);
      setAbierto(false);
      setImporte("");
      setTocado(false);
      setNota("");
      recargar();
      onDone();
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo anotar el cobro", "error");
    } finally {
      setGuardando(false);
    }
  }

  if (!abierto) {
    return (
      <button
        onClick={() => setAbierto(true)}
        className="min-h-[40px] w-full py-2 text-center text-xs text-zinc-500 underline-offset-2 hover:text-zinc-300 hover:underline"
      >
        {client.pago?.situacion === "al_dia"
          ? "Anotar otro cobro (renovación, extra…)"
          : "¿Te pagó por otra vía? Anotar el cobro"}
      </button>
    );
  }

  return (
    <div className="rounded-xl border p-3" style={{ borderColor: "var(--line-strong)" }}>
      <p className="mb-1 text-xs font-semibold text-zinc-200">Cobro fuera de Stripe</p>
      {/* LA MEMORIA: qué plan tiene, cuánto le toca y cuándo fue el último.
          Sin esto el coach tenía que abrir el libro de caja en otra pestaña. */}
      {pago && (
        <p className="mb-2 text-[11px] leading-snug text-zinc-500">
          {pago.plan_label} · {pago.cadencia_label}
          {previsto != null ? ` · le tocan ${euros(previsto)}` : ""}
          {pago.ultimo_pago_en
            ? ` · último: ${euros(pago.ultimo_importe_cents)} el ${fecha(pago.ultimo_pago_en)}`
            : " · primer cobro"}
        </p>
      )}
      <div className="flex gap-2">
        <label className="flex-1">
          <span className="mb-1 block text-[11px] text-zinc-500">Importe (€)</span>
          <input
            type="text" inputMode="decimal" autoFocus value={importe}
            onChange={(e) => { setTocado(true); setImporte(e.target.value); }}
            onKeyDown={(e) => { if (e.key === "Enter") registrar(); }}
            placeholder="129,00" className="input w-full"
          />
        </label>
        <label className="flex-1">
          <span className="mb-1 block text-[11px] text-zinc-500">Cómo</span>
          <select value={metodo} onChange={(e) => setMetodo(e.target.value as typeof metodo)} className="input w-full">
            <option value="transferencia">Transferencia</option>
            <option value="efectivo">Efectivo</option>
            <option value="bizum">Bizum</option>
            <option value="otro">Otro</option>
          </select>
        </label>
      </div>
      {descuadre && (
        <p className="mt-1.5 text-[11px] font-medium" style={{ color: "#D98324" }}>
          ⚠ Su tarifa es {euros(previsto)}. Si de verdad te pagó {euros(Math.round(eur * 100))}, adelante.
        </p>
      )}
      <label className="mt-2 block">
        <span className="mb-1 block text-[11px] text-zinc-500">Fecha del cobro</span>
        <input type="date" value={fechaCobro} max={hoyLocal()}
          onChange={(e) => setFechaCobro(e.target.value)} className="input w-full" />
      </label>
      <label className="mt-2 block">
        <span className="mb-1 block text-[11px] text-zinc-500">Nota (opcional)</span>
        <input type="text" value={nota} maxLength={120}
          onChange={(e) => setNota(e.target.value)}
          placeholder="Ej.: segunda mensualidad" className="input w-full" />
      </label>
      <div className="mt-3 flex justify-end gap-2">
        <button onClick={() => setAbierto(false)} className="btn btn-ghost !py-1.5 text-xs">Cancelar</button>
        <button onClick={registrar} disabled={!valido || guardando} className="btn btn-primary !py-1.5 text-xs">
          {guardando ? "Anotando…" : "Anotar cobro"}
        </button>
      </div>
      <p className="mt-2 text-[11px] text-zinc-500">
        Suma en el total del mes junto a los de Stripe
        {pago?.proximo_si_cobro_hoy
          ? ` · el próximo le tocaría el ${fecha(pago.proximo_si_cobro_hoy)}`
          : ""}.
      </p>
    </div>
  );
}

// ------------------------------------------------------------- el bloqueo ---

/** La ficha de un cliente que NO ha pagado: en vez de las pestañas, esto.
 *
 *  Es una regla de NEGOCIO —que no se trabaje gratis—, y por eso trae todo lo
 *  necesario para deshacerla aquí mismo: su enlace de Stripe para mandárselo,
 *  y el formulario de cobro si pagó por otra vía. En cuanto entra el cobro, la
 *  ficha se abre sola.
 *
 *  Y trae SALIDA, a un clic y registrada: hay cosas que el coach tiene que
 *  poder hacer aunque el cliente deba dinero —leer su historial clínico,
 *  atender una petición suya y sobre todo exportar o borrar sus datos, que son
 *  obligaciones legales con plazo—. Un bloqueo sin salida convierte un impago
 *  en un incumplimiento. */
export function BloqueoPorPago({ client, onCobrado, onEntrarIgual }: {
  client: ClientOut;
  onCobrado: () => void;
  onEntrarIgual: () => void;
}) {
  const toast = useToast();
  const { pago } = useEstadoDePago(client.id);
  const estado = pago ?? client.pago;
  const previsto = estado?.importe_previsto_cents ?? null;
  const telefono = waPhone(client.phone);
  const enlace = pago?.enlace_pago ?? "";

  const mensaje = `Hola ${client.full_name.split(" ")[0]}, te paso el enlace para `
    + `${estado?.motivo === "alta" ? "activar" : "renovar"} tu plan`
    + `${previsto ? ` (${euros(previsto)})` : ""}: ${enlace}`;

  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      <div className="rounded-2xl border-2 p-6" style={{
        borderColor: "#C2453A",
        background: "color-mix(in srgb, #C2453A 8%, transparent)",
      }}>
        <p className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide"
           style={{ color: "#C2453A" }}>
          <AlertTriangle size={18} className="shrink-0" /> Falta pago
        </p>
        <h1 className="mt-2 text-xl font-semibold text-zinc-100">{client.full_name}</h1>
        <p className="mt-1 text-sm text-zinc-400">
          {estado?.motivo_texto ?? "Falta el pago de su plan."}
          {estado?.desde ? ` Debe desde el ${fecha(estado.desde)}.` : ""}
        </p>

        {/* Lo que hay que cobrar, en grande: es el dato de la pantalla. */}
        <div className="mt-4 rounded-xl border p-4" style={{ borderColor: "var(--line-strong)", background: "var(--surface)" }}>
          <p className="text-[11px] uppercase tracking-wide text-zinc-500">Le toca pagar</p>
          <p className="text-2xl font-bold text-zinc-100">
            {previsto != null ? euros(previsto) : "—"}
            <span className="ml-2 text-sm font-medium text-zinc-500">
              {estado?.cadencia_label ?? ""}
            </span>
          </p>
          <p className="mt-1 text-xs text-zinc-500">
            {pago?.plan_label ?? client.plan_label ?? ""}
            {estado?.ultimo_pago_en
              ? ` · su último cobro fue ${euros(estado.ultimo_importe_cents)} el ${fecha(estado.ultimo_pago_en)}`
              : " · aún no ha pagado ninguna vez"}
            {(estado?.num_pagos ?? 0) > 0 ? ` · lleva ${euros(estado?.total_cents)} en total` : ""}
          </p>
        </div>

        {/* Cobrarle SIN salir de aquí: su enlace de Stripe o el cobro a mano. */}
        <div className="mt-4 space-y-2">
          <button
            onClick={() => { if (enlace) void copiarConAviso(enlace, toast, "Enlace de pago copiado — mándaselo"); }}
            disabled={!enlace}
            className="flex w-full items-center gap-3 rounded-xl border-2 px-4 py-3 text-left transition-transform active:scale-[0.98] disabled:opacity-50"
            style={{ borderColor: "#2E7D46", color: "#2E7D46", background: "color-mix(in srgb, #2E7D46 7%, transparent)" }}
          >
            <CreditCard size={22} className="shrink-0" />
            <span className="min-w-0">
              <span className="block text-sm font-semibold">Copiar su enlace de pago</span>
              <span className="block text-xs opacity-80">abre Stripe con su precio ya puesto</span>
            </span>
          </button>
          {telefono && enlace && (
            <button
              onClick={() => openWhatsApp(telefono, mensaje)}
              className="flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left text-zinc-300 transition-transform active:scale-[0.98]"
              style={{ borderColor: "var(--line-strong)" }}
            >
              <MessageCircle size={20} className="shrink-0" />
              <span className="text-sm font-medium">Reclamárselo por WhatsApp</span>
            </button>
          )}
          <CobroManual client={client} onDone={onCobrado} />
        </div>

        {/* La salida. Registrada, y diciendo POR QUÉ existe: si no se explica,
            el coach la usa siempre y el bloqueo deja de significar nada. */}
        <div className="mt-5 border-t pt-4" style={{ borderColor: "var(--line)" }}>
          <button
            onClick={async () => {
              try { await api.accesoSinPago(client.id); } catch { /* el acceso no depende del registro */ }
              onEntrarIgual();
            }}
            className="inline-flex min-h-[40px] items-center gap-2 text-xs text-zinc-500 underline-offset-2 hover:text-zinc-300 hover:underline"
          >
            <Eye size={14} /> Ver la ficha igualmente
          </button>
          <p className="mt-1 text-[11px] leading-snug text-zinc-600">
            Queda registrado. Úsalo para lo que no puede esperar a un cobro:
            atender algo suyo, su historial clínico, o exportar y borrar sus
            datos si te lo pide (RGPD).
          </p>
        </div>
      </div>

      <p className="mt-4 flex items-center justify-center gap-1.5 text-[11px] text-zinc-600">
        <CalendarClock size={12} />
        En cuanto entre el cobro —por Stripe o anotado aquí— la ficha se abre sola.
      </p>
    </div>
  );
}
