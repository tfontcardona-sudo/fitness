import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Bell, Check, Smartphone } from "lucide-react";
import { api } from "../lib/api";
import { useAlertas } from "../lib/alertasCompartidas";
import {
  coachPushActive,
  coachPushSubscribed,
  disableCoachPush,
  enableCoachPush,
  resyncCoachPushIfGranted,
} from "../lib/coachPush";
import { hrefCliente } from "../lib/anchors";
import { pin, pinId, syncScope } from "../lib/pins";
import { useDismiss } from "../lib/useDismiss";
import { useToast } from "./ui";
import type { CoachAlert } from "../types";

/**
 * Campana de ALERTAS del coach — preventiva e inteligente. Las alertas se
 * calculan del estado real de cada cliente (backend /api/alerts): en cuanto
 * la acción se hace, la alerta desaparece sola. Nada que marcar como leído.
 */
export function AlertsBell() {
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  // "Ver con más claridad todas": el centro de notificaciones se puede
  // ampliar SIN un icono aparte — pulsando la campana OTRA VEZ mientras ya
  // está abierta (ver el onClick de abajo). Cerrar sigue siendo clic fuera o
  // Escape (`useDismiss`), así que la campana nunca "atrapa" al coach.
  const [expanded, setExpanded] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  useDismiss(panelRef, () => setOpen(false), open);

  // Push al MÓVIL del coach: estado local del interruptor + resuscripción
  // silenciosa al abrir la web (si el permiso ya estaba concedido).
  const [pushOn, setPushOn] = useState(coachPushActive);
  const [pushBusy, setPushBusy] = useState(false);
  useEffect(() => {
    // Tras la resuscripción silenciosa, el interruptor refleja el estado REAL
    // (suscripción viva), no solo el permiso.
    resyncCoachPushIfGranted().finally(() => {
      coachPushSubscribed().then(setPushOn).catch(() => {});
    });
  }, []);

  async function togglePush() {
    if (pushBusy) return;
    setPushBusy(true);
    try {
      if (pushOn) {
        await disableCoachPush();
        setPushOn(false);
        toast.push("Avisos desactivados en este dispositivo");
      } else {
        await enableCoachPush();
        setPushOn(true);
        toast.push("Avisos activados en este dispositivo · cada 3 h");
      }
    } catch (e) {
      toast.push(e instanceof Error ? e.message : "No se pudo cambiar", "error");
    } finally {
      setPushBusy(false);
    }
  }

  // Los recordatorios anclados heredan la verdad del backend: los que ya no
  // están en la lista es que están RESUELTOS y se borran solos. Solo se
  // sincroniza tras una petición BUENA (un fallo de red no puede barrer
  // recordatorios vivos), que es lo que garantiza la fuente compartida.
  const sincronizarPins = useCallback((as: CoachAlert[]) => {
    syncScope("alerts", as.map((a) => a.key).filter(Boolean));
  }, []);

  // FUENTE COMPARTIDA: un solo temporizador y una sola petición para todo el
  // panel. `/api/alerts` recorre la cartera entera, y con la barra de "lo
  // siguiente" en la ficha había vuelto a haber dos barridos por el mismo dato
  // (el fallo que ya costó una auditoría).
  const { alerts, recargar: load } = useAlertas(sincronizarPins);

  // Al navegar (una acción resuelta debe apagar su alerta al instante) y al
  // abrir la campana.
  useEffect(load, [load, location.pathname, location.search]);
  useEffect(() => { if (open) load(); }, [open, load]);

  const count = alerts?.length ?? 0;
  const high = alerts?.filter((a) => a.severity === "alta").length ?? 0;
  // El backend ya entrega la lista ordenada "de menos recientes a más
  // recientes" (quien lleva más tiempo pendiente, primero). Agrupar por
  // cliente CONSERVANDO ese orden basta para que también los GRUPOS salgan
  // en ese orden: el primer aviso de cada cliente en la lista ya es el suyo
  // más antiguo. Los avisos de SISTEMA (client_id 0) llevan `since` al
  // mínimo posible, así que su grupo sale siempre el primero sin necesitar
  // un caso aparte.
  const grupos = agruparPorCliente(alerts ?? []);

  // Pulsar un aviso hace DOS cosas: lleva al sitio exacto (y lo marca al
  // llegar, vía ?ir=) y deja un RECORDATORIO de lo que ibas a arreglar, para
  // que el desvío de dos minutos no se lleve por delante la intención. El
  // recordatorio se borra solo cuando el aviso desaparece.
  const go = useCallback((a: CoachAlert) => {
    setOpen(false);
    const destino = a.to || hrefCliente(a.client_id, a.tab, a.target || undefined);
    pin({
      id: pinId("alerts", a.key),
      scope: "alerts",
      key: a.key,
      clientId: a.client_id,
      clientName: a.client_name,
      label: a.action,
      motivo: a.message,
      hint: a.fix || a.message,
      href: destino,
      target: a.target || undefined,
      severity: a.severity,
    });
    navigate(destino);
  }, [navigate]);

  const irAFicha = useCallback((clientId: number) => {
    setOpen(false);
    navigate(hrefCliente(clientId, "resumen"));
  }, [navigate]);

  async function snooze(a: CoachAlert) {
    try {
      await api.snoozeGoalReview(a.client_id);
      toast.push("Objetivo mantenido: se volverá a valorar en 45 días");
      load();
    } catch {
      toast.push("No se pudo posponer", "error");
    }
  }

  return (
    <div className="alerts-bell fixed right-5 top-4 z-40" ref={panelRef}>
      <button
        onClick={(e) => {
          e.stopPropagation();
          if (open) {
            // Ya estaba abierta: esta pulsación es la de "verla más grande"
            // (no la cierra — para eso está el clic fuera o Escape).
            setExpanded((v) => !v);
          } else {
            // Recién abierta: siempre en compacto, para que exista ese
            // "segundo toque" que la amplía.
            setOpen(true);
            setExpanded(false);
          }
        }}
        aria-label={!open ? (count ? `${count} alertas pendientes` : "Sin alertas")
          : expanded ? "Ver la campana en tamaño normal" : "Ampliar para ver todas con más claridad"}
        aria-expanded={open}
        className="card relative flex h-11 w-11 items-center justify-center rounded-full"
        style={{ boxShadow: "0 4px 16px rgba(38,33,26,0.12)" }}
      >
        <Bell size={18} style={{ color: count ? (high ? "var(--brand-accent)" : "var(--brand-accent-2)") : "var(--text-faint)" }} />
        {count > 0 && (
          <span
            className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-[11px] font-bold text-white"
            style={{ background: high ? "#C2453A" : "var(--brand-accent-2)" }}
          >
            {count}
          </span>
        )}
      </button>

      {open && (
        <div
          className={`card absolute right-0 mt-2 flex max-w-[calc(100vw-40px)] flex-col overflow-hidden max-sm:fixed max-sm:inset-x-3 max-sm:top-14 max-sm:bottom-14 max-sm:mt-0 max-sm:w-auto max-sm:max-w-none ${
            expanded ? "w-[640px]" : "w-[380px]"
          }`}
          role="dialog"
          aria-label="Alertas del coach"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex shrink-0 items-center justify-between border-b px-4 py-3" style={{ borderColor: "var(--line)" }}>
            <span className="text-sm font-semibold text-zinc-100">Alertas</span>
            {count > 0 && (
              <span className="text-xs text-zinc-500">
                {count} pendiente{count === 1 ? "" : "s"}
              </span>
            )}
          </div>
          {/* En escritorio la altura es un % del viewport (crece hacia abajo
              desde la campana). En MÓVIL el panel va encajado entre top-14 y
              bottom-14 —ampliar no puede empujar nada fuera de la pantalla:
              la campana, que es lo que amplía/reduce, vive FUERA del panel—,
              así que ahí la altura la da flex-1 (lo que sobre entre cabecera
              y pie), no un % fijo. */}
          <div className={`overflow-y-auto max-sm:max-h-none max-sm:flex-1 ${expanded ? "sm:max-h-[78vh]" : "sm:max-h-[60vh]"}`}>
            {count === 0 ? (
              <div className="flex items-center justify-center gap-2 px-4 py-8 text-sm text-zinc-500">
                <Check size={16} style={{ color: "var(--brand-accent)" }} /> Todo al día
              </div>
            ) : (
              // AGRUPADAS POR CLIENTE: cada uno con sus avisos pendientes
              // juntos, en el orden real de antigüedad (backend). Antes se
              // agrupaba por ÁMBITO (nutrición, pagos…) y un mismo cliente con
              // tres problemas distintos aparecía en tres sitios separados de
              // la lista, sin verse que era el mismo caso.
              grupos.map((g) => renderGrupo(g))
            )}
          </div>
          {/* Interruptor: recibir todo esto también en el MÓVIL (push cada 3 h) */}
          <div className="flex shrink-0 items-center justify-between gap-2 border-t px-4 py-2.5"
            style={{ borderColor: "var(--line)" }}>
            <span className="flex items-center gap-1.5 text-xs text-zinc-400">
              <Smartphone size={13} /> Avisos en el móvil
            </span>
            <button
              onClick={togglePush}
              disabled={pushBusy}
              className="text-xs font-semibold hover:opacity-80 disabled:opacity-50"
              style={{ color: pushOn ? "var(--brand-accent)" : "var(--text-faint)" }}
            >
              {pushBusy ? "…" : pushOn ? "Activados · desactivar" : "Activar"}
            </button>
          </div>
        </div>
      )}
    </div>
  );

  function renderGrupo(g: GrupoDeCliente) {
    const esSistema = g.clientId === 0;
    const peor = g.items.some((a) => a.severity === "alta") ? "alta" : "media";
    const antiguedad = hace(g.items[0]?.since);
    return (
      <div key={g.clientId}>
        <div
          className="flex items-center gap-2 px-4 pb-1 pt-2.5"
          style={{ background: `color-mix(in srgb, ${peor === "alta" ? "#C2453A" : "var(--brand-accent-2)"} 6%, transparent)` }}
        >
          <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: peor === "alta" ? "#C2453A" : "var(--brand-accent-2)" }} />
          {/* Nombres largos SALTAN de línea (min-w-0 en el flex item) en vez de
              recortarse: un botón con el texto cortado es justo lo que
              check:botones vigila que no vuelva a pasar. */}
          {esSistema ? (
            <span className="min-w-0 text-[11px] font-bold uppercase tracking-wide text-zinc-400">{g.clientName}</span>
          ) : (
            <button
              onClick={() => irAFicha(g.clientId)}
              className="min-w-0 text-left text-[11px] font-bold uppercase tracking-wide text-zinc-200 hover:opacity-80"
            >
              {g.clientName}
            </button>
          )}
          {g.items.length > 1 && <span className="shrink-0 text-[11px] text-zinc-500">{g.items.length}</span>}
          {antiguedad && <span className="ml-auto shrink-0 text-[10px] text-zinc-500">{antiguedad}</span>}
        </div>
        {g.items.map((a, i) => renderAlert(a, i))}
      </div>
    );
  }

  function renderAlert(a: CoachAlert, i: number) {
    return (
      <div
        key={`${a.client_id}-${a.kind}-${i}`}
        className="flex items-start gap-2.5 border-b px-4 py-3 last:border-b-0"
        style={{ borderColor: "var(--line)" }}
      >
        {/* Hueco invisible del tamaño del punto de color: alinea el texto
            bajo el de la cabecera del grupo (que sí lo lleva), en vez de
            colarse más a la izquierda. */}
        <span aria-hidden className="mt-1.5 h-2 w-2 shrink-0 rounded-full opacity-0" />
        <div className="min-w-0 flex-1">
          {/* El mensaje lleva a la misma pestaña donde hay que actuar que el
              botón de acción: el nombre ya lo dice la cabecera del grupo. */}
          <button onClick={() => go(a)} className="group block w-full text-left">
            <span className="block text-xs text-zinc-400 group-hover:text-zinc-200">{a.message}</span>
          </button>
          <div className="mt-1.5 flex flex-wrap gap-2">
            <button
              onClick={() => go(a)}
              className="text-xs font-semibold hover:opacity-80"
              style={{ color: "var(--brand-accent)" }}
            >
              {a.action} →
            </button>
            {a.kind === "goal_review" && (
              <button onClick={() => snooze(a)} className="text-xs text-zinc-500 hover:text-zinc-200">
                Mantener objetivo
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }
}

interface GrupoDeCliente {
  clientId: number;
  clientName: string;
  items: CoachAlert[];
}

/** Agrupa la lista PLANA (ya ordenada por el backend, `since` ascendente) por
 *  cliente, conservando el orden de PRIMERA aparición: como esa lista ya sale
 *  "de menos recientes a más recientes", el primer aviso de cada cliente ya es
 *  el más antiguo suyo — agrupar así basta para que los GRUPOS salgan en ese
 *  mismo orden, sin recalcular nada. */
function agruparPorCliente(alerts: CoachAlert[]): GrupoDeCliente[] {
  const porId = new Map<number, GrupoDeCliente>();
  const orden: number[] = [];
  for (const a of alerts) {
    let g = porId.get(a.client_id);
    if (!g) {
      g = { clientId: a.client_id, clientName: a.client_id === 0 ? "Sistema" : a.client_name, items: [] };
      porId.set(a.client_id, g);
      orden.push(a.client_id);
    }
    g.items.push(a);
  }
  return orden.map((id) => porId.get(id)!);
}

// El backend sella los avisos de SISTEMA con `date.min` (año 1) para que
// salgan SIEMPRE primero, sin ser una fecha real que mostrar — enseñarla tal
// cual daría "hace 739.870 días". No es una espera: es el mínimo posible.
const SIN_FECHA_REAL = "0001-01-01";

/** "hace N días", para que el orden de la campana se entienda de un vistazo.
 *  `null` si el aviso no tiene un "desde cuándo" real (un choque estructural,
 *  o un centinela de sistema) — no se inventa una edad que no existe. */
function hace(since: string | null | undefined): string | null {
  if (!since || since === SIN_FECHA_REAL) return null;
  const dias = Math.floor((Date.now() - new Date(`${since}T00:00:00`).getTime()) / 86_400_000);
  if (Number.isNaN(dias)) return null;
  if (dias <= 0) return "hoy";
  if (dias === 1) return "hace 1 día";
  return `hace ${dias} días`;
}
