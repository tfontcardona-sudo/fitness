import { useEffect, useState } from "react";
import { Flame, TrendingDown, TrendingUp } from "lucide-react";
import type { PortalSemana as Semana } from "../types";
import type { portalApi } from "./portalApi";

/**
 * "TU SEMANA": lo que el cliente ha hecho, no lo que le queda por hacer.
 *
 * El portal era una lista de tareas. Un cliente que ve su progreso vuelve; uno
 * que solo ve deberes, se cansa. Aquí van sus cifras —días registrados, series,
 * cómo va el peso—, el recordatorio de su última sesión con los kilos que movió
 * y, como mucho, tres consejos que salen de SUS datos (no frases de ánimo al
 * azar: un consejo que no mira tus datos es ruido y se aprende a ignorar).
 *
 * Todo lo calcula el backend de forma determinista, con las mismas reglas que
 * ve el coach: las dos pantallas no pueden contradecirse.
 */
/** Una sola petición para las DOS tarjetas que salen de `/semana` («Lo de hoy»
 *  y «Tu semana»): pedirlo dos veces era pagar dos viajes por los mismos datos
 *  y arriesgarse a que las dos tarjetas contaran cosas distintas. */
export function useSemana(api: ReturnType<typeof portalApi>): Semana | null {
  const [datos, setDatos] = useState<Semana | null>(null);
  useEffect(() => {
    let vivo = true;
    api.semana()
      .then((d) => { if (vivo) setDatos(d); })
      // Silencio a propósito: esto es un extra. Si falla, el portal sigue
      // entero — no se le enseña un error por una tarjeta de resumen.
      .catch(() => { /* sin resumen, sin ruido */ });
    return () => { vivo = false; };
  }, [api]);
  return datos;
}

export default function PortalSemanaCard({ datos }: { datos: Semana | null }) {
  if (!datos) return null;
  const { dias_registrados: dias, dias_objetivo: meta, series, peso_delta_kg: delta } = datos;
  const nada = dias === 0 && series === 0 && !datos.ultima_sesion;
  if (nada && datos.consejos.length === 0) return null;

  return (
    <section className="portal-card portal-semana mb-3 p-4" aria-label="Tu semana">
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="p-eyebrow">Tu semana</h2>
        {datos.racha >= 2 && (
          <span className="flex items-center gap-1 text-xs font-semibold"
                style={{ color: "var(--p-accent-ink)" }}>
            <Flame size={13} /> {datos.racha} días seguidos
          </span>
        )}
      </div>

      {!nada && (
        <div className="mt-3 grid grid-cols-3 gap-2">
          <Cifra valor={`${dias}/${meta}`} etiqueta="días" />
          <Cifra valor={String(series)} etiqueta={series === 1 ? "serie" : "series"} />
          <Cifra
            valor={delta === null ? "—" : `${delta > 0 ? "+" : "−"}${fmtKgCorto(Math.abs(delta))}`}
            etiqueta="kg de peso"
            icono={delta === null ? null : delta > 0 ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
          />
        </div>
      )}

      {/* El recordatorio con datos: llegar al gimnasio sabiendo de dónde vienes. */}
      {datos.ultima_sesion && (
        <p className="mt-3 text-sm" style={{ color: "var(--p-ink-soft)" }}>
          El <b style={{ color: "var(--p-ink)" }}>{datos.ultima_sesion.dia}</b> hiciste{" "}
          <b style={{ color: "var(--p-ink)" }}>{datos.ultima_sesion.series} series</b>
          {datos.ultima_sesion.top_ejercicio && datos.ultima_sesion.top_peso_kg !== null && (
            <>
              {" · lo más pesado, "}
              <b style={{ color: "var(--p-ink)" }}>
                {datos.ultima_sesion.top_ejercicio} {fmtKg(datos.ultima_sesion.top_peso_kg)}
                {datos.ultima_sesion.top_reps ? ` × ${datos.ultima_sesion.top_reps}` : ""}
              </b>
            </>
          )}
          .
        </p>
      )}

      {datos.consejos.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {datos.consejos.map((c, i) => (
            <li key={i} className="flex gap-2 text-sm" style={{ color: "var(--p-ink-soft)" }}>
              <span aria-hidden className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full"
                    style={{ background: tono(c.tono) }} />
              <span className="min-w-0">{c.texto}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** Una cifra de un vistazo. La clave está en `p-tile-valor`: la cifra NO puede
 *  partirse. «−1,4 kg» salía en dos líneas («−1,4» / «kg») y una cifra rota se
 *  lee peor que una cifra pequeña. */
function Cifra({ valor, etiqueta, icono }: {
  valor: string; etiqueta: string; icono?: React.ReactNode;
}) {
  return (
    <div className="p-tile">
      <div className="p-tile-valor">
        {icono}
        <span>{valor}</span>
      </div>
      <div className="p-tile-etiqueta">{etiqueta}</div>
    </div>
  );
}

/** Los kilos SIN unidad, para una tarjeta estrecha: la etiqueta ya la dice. */
function fmtKgCorto(n: number): string {
  const r = Math.round(n * 10) / 10;
  return (Number.isInteger(r) ? String(r) : r.toFixed(1)).replace(".", ",");
}

/** Los kilos, en español y sin decimales de más: "62,5 kg", "60 kg". */
function fmtKg(n: number): string {
  const r = Math.round(n * 10) / 10;
  return `${(Number.isInteger(r) ? String(r) : r.toFixed(1)).replace(".", ",")} kg`;
}

function tono(t: string): string {
  if (t === "bien") return "var(--p-ok)";
  if (t === "ojo") return "var(--p-warn)";
  return "var(--p-accent)";
}
