import { useMemo } from "react";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import { useAlertasDeCliente } from "../lib/alertasCompartidas";
import type { CoachAlert } from "../types";

/**
 * "LO SIGUIENTE": qué toca hacer AHORA con este cliente, en la cabecera de su
 * ficha y visible desde cualquier pestaña.
 *
 * El coach entraba a una ficha y tenía que deducir en qué estado estaba
 * abriendo pestañas: ¿le falta la anamnesis? ¿tiene revisión sin contestar?
 * ¿le he generado el plan? La información existía —el backend ya calcula las
 * alertas de cada cliente— pero solo se veía agregada en la campana, mezclada
 * con la de los otros treinta.
 *
 * Aquí se filtra a ESTE cliente, se pone la más grave delante con su botón, y
 * cuando no queda nada se dice también: "al día" es información, no vacío.
 */
/**
 * UN SOLO barrido de alertas para la ficha: de él salen la barra de "lo
 * siguiente" Y los puntos de las pestañas.
 *
 * ⚠️ Con dos hooks separados eran dos peticiones a `/api/alerts` cada 20 s por
 * el MISMO dato, y ese endpoint recorre la cartera entera. Ya pasó una vez
 * (`/api/alerts` se pedía desde dos sitios a la vez) y costó una auditoría.
 */
/**
 * Los avisos de ESTE cliente y las pestañas que los tienen.
 *
 * Sin petición propia: sale de la fuente COMPARTIDA del panel. `/api/alerts`
 * recorre la cartera entera, y con un hook propio aquí la ficha habría hecho un
 * segundo barrido cada 20 s por el mismo dato — el fallo que ya costó una
 * auditoría cuando la campana y el seguimiento lo pedían por separado.
 */
export function useAvisosDelCliente(clientId: number): {
  alertas: CoachAlert[] | null;
  tabs: Set<string>;
} {
  const alertas = useAlertasDeCliente(clientId);
  const tabs = useMemo(
    () => new Set((alertas ?? []).map((a) => a.tab)), [alertas]);
  return { alertas, tabs };
}


export function LoSiguiente({ alertas, onIr }: {
  alertas: CoachAlert[] | null;
  /** Cambia de pestaña Y, si el aviso trae un punto exacto (`target`), lo
   *  marca y deja su nota — mismo camino que la campana (`AlertsBell`) y el
   *  dashboard. Antes este botón se quedaba SOLO con la pestaña del aviso y
   *  tiraba el resto (`target`/`fix`): el coach llegaba al sitio correcto sin
   *  nada señalado ni explicado. Recibe el AVISO ENTERO, no su nombre de
   *  pestaña suelto, precisamente para no poder repetir ese recorte. */
  onIr: (a: CoachAlert) => void;
}) {
  if (alertas === null) return null;

  if (alertas.length === 0) {
    return (
      <div className="mb-4 flex items-center gap-2 rounded-xl border px-4 py-2.5 text-sm"
           style={{ borderColor: "var(--line)", color: "var(--text-faint)" }}>
        <CheckCircle2 size={15} style={{ color: "#2E7D46" }} />
        Al día: no hay nada pendiente con este cliente.
      </div>
    );
  }

  // La más grave primero: es la que decide qué hace el coach al entrar.
  const orden = [...alertas].sort(
    (a, b) => (a.severity === "alta" ? 0 : 1) - (b.severity === "alta" ? 0 : 1));
  const principal = orden[0];
  const resto = orden.slice(1);

  return (
    <div className="mb-4 rounded-xl border p-4"
         style={{ borderColor: principal.severity === "alta" ? "#C2453A" : "var(--line-strong)",
                  background: "var(--surface-raised)" }}>
      <div className="flex flex-wrap items-center gap-3">
        <span className="min-w-0 flex-1">
          <span className="block text-xs font-bold uppercase tracking-wider"
                style={{ color: principal.severity === "alta" ? "#C2453A" : "var(--text-faint)" }}>
            Lo siguiente
          </span>
          <span className="mt-0.5 block text-sm text-zinc-100">{principal.message}</span>
        </span>
        <button
          onClick={() => onIr(principal)}
          className="btn-primary shrink-0"
        >
          {principal.action} <ArrowRight size={15} />
        </button>
      </div>

      {resto.length > 0 && (
        <ul className="mt-3 space-y-1 border-t pt-3" style={{ borderColor: "var(--line)" }}>
          {resto.slice(0, 3).map((a) => (
            <li key={a.key}>
              <button
                onClick={() => onIr(a)}
                className="flex w-full items-center gap-2 text-left text-sm"
                style={{ color: "var(--text-faint)" }}
              >
                <span aria-hidden className="h-1.5 w-1.5 shrink-0 rounded-full"
                      style={{ background: a.severity === "alta" ? "#C2453A" : "var(--brand-accent)" }} />
                <span className="min-w-0 flex-1 truncate">{a.message}</span>
                <span className="shrink-0 text-xs">{a.action}</span>
              </button>
            </li>
          ))}
          {resto.length > 3 && (
            <li className="text-xs" style={{ color: "var(--text-faint)" }}>
              …y {resto.length - 3} más
            </li>
          )}
        </ul>
      )}
    </div>
  );
}
