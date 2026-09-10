import { useCallback, useEffect, useState } from "react";
import { ALERTS_REFRESH_MS, api } from "./api";
import type { CoachAlert } from "../types";

/**
 * UNA sola fuente de alertas para todo el panel.
 *
 * `/api/alerts` recorre la cartera ENTERA en cada llamada. Cuando dos pantallas
 * lo pedían por su cuenta —ya pasó: la campana y el panel de seguimiento— el
 * servidor hacía el doble de trabajo por el mismo dato, y costó una auditoría
 * descubrirlo. Con la barra de "lo siguiente" en la ficha habría vuelto a
 * pasar: campana + barra = dos barridos cada 20 s.
 *
 * Aquí hay UN temporizador y UNA petición en vuelo; los consumidores se
 * suscriben. El primero que se monta arranca el reloj, el último que se
 * desmonta lo para.
 */
type Escucha = (alerts: CoachAlert[]) => void;

let ultimas: CoachAlert[] | null = null;
let enVuelo: Promise<void> | null = null;
let timer: number | null = null;
const escuchas = new Set<Escucha>();
// Tras una petición buena se avisa a quien quiera hacer algo con la lista
// completa (la campana sincroniza con ella sus recordatorios anclados).
const posteriores = new Set<Escucha>();

/** Fuerza un refresco (tras una acción del coach, al navegar, al abrir…). */
export function refrescarAlertas(): Promise<void> {
  if (enVuelo) return enVuelo;
  enVuelo = api.listAlerts()
    .then((r) => {
      ultimas = r.alerts;
      escuchas.forEach((f) => f(r.alerts));
      posteriores.forEach((f) => f(r.alerts));
    })
    // Un fallo de red NO borra lo que había: la pantalla conserva las alertas
    // anteriores en vez de quedarse en blanco.
    .catch(() => { /* se reintenta en el siguiente ciclo */ })
    .finally(() => { enVuelo = null; });
  return enVuelo;
}

function arrancar() {
  if (timer !== null) return;
  timer = window.setInterval(() => {
    if (!document.hidden) void refrescarAlertas();
  }, ALERTS_REFRESH_MS);
}

function parar() {
  if (escuchas.size === 0 && timer !== null) {
    window.clearInterval(timer);
    timer = null;
  }
}

/**
 * Las alertas vivas. `alSincronizar` se llama solo tras una petición BUENA
 * (la campana la usa para retirar los recordatorios ya resueltos: con un fallo
 * de red barrería recordatorios vivos).
 */
export function useAlertas(alSincronizar?: Escucha): {
  alerts: CoachAlert[] | null;
  recargar: () => void;
} {
  const [alerts, setAlerts] = useState<CoachAlert[] | null>(ultimas);

  useEffect(() => {
    const f: Escucha = (a) => setAlerts(a);
    escuchas.add(f);
    if (alSincronizar) posteriores.add(alSincronizar);
    arrancar();
    void refrescarAlertas();
    return () => {
      escuchas.delete(f);
      if (alSincronizar) posteriores.delete(alSincronizar);
      parar();
    };
    // `alSincronizar` se pasa memoizado por el llamador; incluirlo aquí
    // re-suscribiría en cada render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const recargar = useCallback(() => { void refrescarAlertas(); }, []);
  return { alerts, recargar };
}

/** Solo lo de UN cliente: la barra de "lo siguiente" y los puntos de sus
 *  pestañas salen de aquí, sin una petición propia. */
export function useAlertasDeCliente(clientId: number): CoachAlert[] | null {
  const { alerts } = useAlertas();
  if (alerts === null) return null;
  return alerts.filter((a) => a.client_id === clientId);
}
