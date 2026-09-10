import { Check, CalendarCheck, Dumbbell, NotebookPen } from "lucide-react";
import type { PortalSemana } from "../types";

/**
 * LO DE HOY: qué toca ahora y qué ya está hecho.
 *
 * El portal abría con una pila de tarjetas informativas y media pantalla en
 * blanco. Lo primero que quiere saber quien lo abre es «¿qué tengo que hacer
 * ahora?», y eso no estaba escrito en ninguna parte: había que deducirlo de las
 * pestañas.
 *
 * Tres líneas como mucho, cada una con su estado. Lo hecho se marca con un
 * visto verde y se queda a la vista — tacharlo y esconderlo quita la
 * recompensa, que es justo lo que hace volver al día siguiente.
 *
 * Todo lo decide el backend (`portal_semana.lo_de_hoy`) con las mismas reglas
 * que el panel del coach: aquí no se calcula nada.
 */
export default function PortalHoy({
  hoy, onIr,
}: {
  hoy: NonNullable<PortalSemana["hoy"]>;
  onIr: (tab: "entreno" | "diario" | "cierre") => void;
}) {
  const filas: {
    id: "entreno" | "diario" | "cierre";
    icono: typeof Dumbbell;
    titulo: string;
    sub: string;
    hecho: boolean;
  }[] = [];

  if (hoy.entrena_hoy) {
    filas.push({
      id: "entreno", icono: Dumbbell,
      titulo: hoy.sesion ? `Entrenar · ${hoy.sesion}` : "Entrenar",
      sub: hoy.entreno_hecho ? "Series registradas ✓" : "Registra tus series al terminar",
      hecho: hoy.entreno_hecho,
    });
  }
  filas.push({
    id: "diario", icono: NotebookPen,
    titulo: "Tu diario de hoy",
    sub: hoy.diario_hecho ? "Registrado ✓" : "Peso, sueño, sensaciones… un minuto",
    hecho: hoy.diario_hecho,
  });
  if (hoy.toca_revision) {
    filas.push({
      id: "cierre", icono: CalendarCheck,
      titulo: "Tu revisión quincenal",
      sub: "Ya puedes enviarla a tu coach",
      hecho: false,
    });
  }
  if (!filas.length) return null;

  const pendientes = filas.filter((f) => !f.hecho).length;

  return (
    <section className="portal-hoy mb-3" aria-label="Lo de hoy">
      <div className="flex items-center justify-between gap-2 px-4 pb-1 pt-3">
        <h2 className="p-eyebrow">Lo de hoy</h2>
        <span className="text-xs font-semibold"
              style={{ color: pendientes ? "var(--p-accent-ink)" : "var(--p-ok)" }}>
          {pendientes === 0 ? "Todo hecho ✓"
            : pendientes === 1 ? "1 cosa" : `${pendientes} cosas`}
        </span>
      </div>
      {filas.map((f) => (
        <button key={f.id} type="button" onClick={() => onIr(f.id)} className="portal-hoy-fila">
          <span className="portal-hoy-ico" data-hecho={f.hecho}>
            {f.hecho ? <Check size={18} /> : <f.icono size={18} />}
          </span>
          <span className="portal-hoy-texto">
            <span className="portal-hoy-titulo">{f.titulo}</span>
            <span className="portal-hoy-sub">{f.sub}</span>
          </span>
        </button>
      ))}
    </section>
  );
}
