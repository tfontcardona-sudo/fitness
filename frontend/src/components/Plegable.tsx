import type { ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { MemoDetails } from "./MemoDetails";

/**
 * DESPLEGABLE QUE SE VE QUE SE PUEDE PULSAR.
 *
 * Queja del dueño sobre Recursos: «los botones donde sale el historial no se
 * ven bien marcados, y es difícil interactuar». Tenía razón: un título con un
 * chevron de 14 px al lado no parece un control, parece un título. Quien no
 * sabe que ahí hay algo, no pulsa.
 *
 * Esto es la cabecera COMO BARRA: ancho completo, borde, fondo propio, altura
 * de dedo (44 px), cambio al pasar por encima y el chevron girando. A la
 * derecha caben un dato (cuántos hay, cuánto suma) y una acción suelta.
 *
 * Hereda de `MemoDetails`: recuerda si lo abriste y participa en el acordeón
 * global (abrir uno cierra el que estaba abierto) sin nada más que hacer.
 */
export function Plegable({
  memoKey, titulo, sub, dato, defaultOpen = false, children, className, acciones, ...resto
}: {
  memoKey: string;
  titulo: ReactNode;
  /** Una línea bajo el título: para qué sirve lo de dentro. */
  sub?: ReactNode;
  /** El dato de un vistazo SIN abrir: «12 movimientos», «48,20 $». */
  dato?: ReactNode;
  defaultOpen?: boolean;
  children: ReactNode;
  className?: string;
  /** Botones propios de la sección (van fuera del área pulsable). */
  acciones?: ReactNode;
} & Record<string, unknown>) {
  return (
    <div className={`plegable ${className ?? ""}`} {...resto}>
      <MemoDetails
        memoKey={memoKey}
        defaultOpen={defaultOpen}
        sinChevron
        summaryClassName="plegable-barra"
        summary={
          <span className="plegable-cabecera">
            <span className="min-w-0">
              <span className="plegable-titulo">{titulo}</span>
              {sub ? <span className="plegable-sub">{sub}</span> : null}
            </span>
            {dato ? <span className="plegable-dato">{dato}</span> : null}
            <ChevronDown size={16} className="plegable-chevron" aria-hidden />
          </span>
        }
      >
        <div className="plegable-cuerpo">{children}</div>
      </MemoDetails>
      {acciones ? <div className="plegable-acciones">{acciones}</div> : null}
    </div>
  );
}
