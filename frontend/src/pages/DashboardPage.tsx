import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  AlertTriangle,
  BadgeEuro,
  CalendarPlus,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  ClipboardList,
  Flag,
  CreditCard,
  HeartPulse,
  Hourglass,
  Package,
  Send,
  Sparkles,
  UserPlus,
  Video,
} from "lucide-react";
import { ALERTS_REFRESH_MS, api, keepIfSame, REFRESH_MS } from "../lib/api";
import type { ClientOut, CoachAlert, VideoCallAgendaItem } from "../types";
import { PageLoader, SectionHeader, StatusBadge } from "../components/ui";
import { hrefCliente } from "../lib/anchors";
import { pin, pinId } from "../lib/pins";
import { goalReviewDue, initials, relativeDays } from "../lib/format";
import { WhatsAppRound } from "../components/WhatsAppRound";
import { AiCreditButton } from "../components/AiCreditButton";

/**
 * Dashboard = "qué toca hacer AHORA con cada cliente". Cada cliente se traduce
 * en su siguiente acción concreta (generar feedback, adaptar planificación,
 * crear planificación…) con un botón que lleva directo a la pestaña adecuada.
 * Lo que está al día se aparta abajo, sin ruido.
 */

interface Accion {
  client: ClientOut;
  prio: number;              // 1 = lo más urgente
  category: string;          // etiqueta de la categoría (chip de color)
  title: string;             // qué ha pasado
  detail?: string;           // contexto extra (solo si aporta algo al título)
  cta: string;               // texto del botón
  tab: string;               // pestaña destino del perfil
  tone: string;              // color del indicador
  icon: typeof Sparkles;
  to?: string;               // destino explícito (si no es el perfil del cliente)
  /** El aviso del backend que originó esta acción, si lo hubo. Lleva el ANCLA
   *  del sitio exacto, la nota de cómo se arregla y la clave estable con la
   *  que el recordatorio se borra solo. Las acciones derivadas del ESTADO del
   *  cliente (nextAction) no tienen aviso: no se anclan, porque sin clave no
   *  hay forma honesta de retirar el recordatorio. */
  alert?: CoachAlert;
}

function nextAction(c: ClientOut, avisoPlan?: CoachAlert): Accion | null {
  if (c.status === "review_pending")
    return {
      client: c, prio: 1, tone: "#7B4FC9", icon: ClipboardCheck, category: "Revisión",
      title: `Revisión #${c.review_period_index ?? c.pending_review_period ?? ""} cerrada`,
      cta: "Generar feedback", tab: "feedback",
    };
  if (c.status === "at_risk")
    return {
      client: c, prio: 1, tone: "#C2453A", icon: HeartPulse, category: "Riesgo",
      title: "Sin registros o adherencia baja",
      cta: "Ver seguimiento", tab: "seguimiento",
    };
  // (La tarjeta "Adaptar planificación" YA NO se deriva de pending_review: ese
  // flag se apaga en cuanto el coach ABRE la pestaña Seguimiento, así que la
  // tarea desaparecía de "Hoy" sin haberse hecho. Ahora viene de la alerta
  // adapt_plan del backend, anclada al período analizado — auditoría.)
  if (c.status === "onboarding") {
    // "Falta su anamnesis" y "llegó pero la IA no pudo leerla" son cosas MUY
    // distintas y aquí se fundían en una sola: con la anamnesis ya en el
    // sistema, el panel decía "falta su anamnesis" y la metía en "En espera
    // del cliente", cuando la pelota estaba en el tejado del coach. La verdad
    // la tiene el backend (aviso `create_plan`, que distingue las dos vías);
    // aquí solo se consume — incluidos sus días de espera.
    const recibida = c.consent_signed_at != null
      || avisoPlan?.action === "Revisar anamnesis";
    if (!recibida)
      return {
        // prio 4 = "En espera del cliente": el coach solo puede recordárselo.
        client: c, prio: 4, tone: "#6366F1", icon: ClipboardList, category: "Falta anamnesis",
        title: "Cliente nuevo · falta su anamnesis",
        detail: avisoPlan?.message,
        cta: avisoPlan?.action ?? "Abrir anamnesis", tab: "anamnesis",
        alert: avisoPlan,
      };
    if (!c.goal_type)
      return {
        // Ya está en casa: le toca al COACH rellenar lo que la IA no sacó.
        client: c, prio: 2, tone: "#6366F1", icon: ClipboardList, category: "Revisar anamnesis",
        title: "Anamnesis recibida · revísala y genera el plan",
        detail: avisoPlan?.message,
        cta: "Revisar anamnesis", tab: "anamnesis",
        alert: avisoPlan,
      };
    return {
      client: c, prio: 3, tone: "#E8833A", icon: CalendarPlus, category: "Falta planificación",
      title: "Anamnesis lista · falta su planificación",
      cta: "Crear planificación", tab: "planificacion",
    };
  }
  // 45 días en la misma etapa de objetivo → valorar cambio (posponible)
  const dueDays = goalReviewDue(c);
  if (dueDays != null)
    return {
      client: c, prio: 3, tone: "#2E5E8C", icon: Flag, category: "Objetivo",
      title: `${dueDays} días con el mismo objetivo`,
      cta: "Valorar objetivo", tab: "planificacion",
    };
  // ("awaiting_feedback" eliminado: estado muerto que nada asignaba — auditoría.)
  return null; // activo y al día
}

/** "Hoy"/"Mañana" si la videollamada cae en esos días (hora local); null si no. */
function agendaDayTag(iso: string): "Hoy" | "Mañana" | null {
  const d = new Date(iso);
  const hoy = new Date();
  const manana = new Date();
  manana.setDate(hoy.getDate() + 1);
  const mismoDia = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  if (mismoDia(d, hoy)) return "Hoy";
  if (mismoDia(d, manana)) return "Mañana";
  return null;
}

const agendaHora = (iso: string) =>
  new Date(iso).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });

export default function DashboardPage() {
  const [clients, setClients] = useState<ClientOut[] | null>(null);
  const [alerts, setAlerts] = useState<CoachAlert[]>([]);
  const alertasDeSistema = alerts.filter((a) => a.client_id === 0);
  const [agenda, setAgenda] = useState<VideoCallAgendaItem[]>([]);
  // Un fallo de red NO se disfraza de "Todo al día": banner explícito.
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    const load = () => {
      // `light`: esta pantalla se refresca sola cada 3 s y no pinta ni una
      // de las notas de la anamnesis (son la mayor parte del peso de la lista).
      api.listClients({ light: true })
        .then((cs) => { setLoadFailed(false); setClients((prev) => keepIfSame(prev, cs)); })
        .catch(() => { setLoadFailed(true); setClients((c) => c ?? []); });
    };
    // Alertas + agenda: barrido pesado (todos los clientes con sus planes y
    // períodos), aparte y más espaciado que el refresco de la lista.
    const loadSlow = () => {
      api.listAlerts()
        .then((r) => setAlerts((prev) => keepIfSame(prev, r.alerts)))
        .catch(() => {});
      api.videoCallsAgenda()
        .then((r) => setAgenda((prev) => keepIfSame(prev, r.calls)))
        .catch(() => {});
    };
    load();
    loadSlow();
    // Refresco cada 3 s (solo con la pestaña visible): el panel siempre al día
    const t = window.setInterval(() => {
      if (!document.hidden) load();
    }, REFRESH_MS);
    const tSlow = window.setInterval(() => {
      if (!document.hidden) loadSlow();
    }, ALERTS_REFRESH_MS);
    return () => { window.clearInterval(t); window.clearInterval(tSlow); };
  }, []);

  const { acciones, alDia } = useMemo(() => {
    const c = clients ?? [];
    // Feedback YA generado y sin enviar: su tarjeta correcta es "Enviar" (de la
    // alerta send_feedback), no la genérica "Generar feedback" del estado.
    const sendFbIds = new Set(alerts.filter((a) => a.kind === "send_feedback").map((a) => a.client_id));
    // Con un borrador pendiente de activar, la tarea NO es "crear planificación"
    // (eso generaría otra y gastaría créditos): es revisarlo y activarlo.
    const draftIds = new Set(alerts.filter((a) => a.kind === "publish_plan").map((a) => a.client_id));
    const avisoPlanPorCliente = new Map(
      alerts.filter((a) => a.kind === "create_plan").map((a) => [a.client_id, a]));
    const acciones = c
      .map((cl) => nextAction(cl, avisoPlanPorCliente.get(cl.id)))
      .filter((a): a is Accion => a !== null)
      .filter((a) => !(a.category === "Revisión" && sendFbIds.has(a.client.id)))
      .filter((a) => !(a.category === "Falta planificación" && draftIds.has(a.client.id)));
    // Falta recurso/producto y videollamadas: vienen del centro de alertas
    // (mismo dato), cada tipo con su grupo, color e icono propios.
    for (const al of alerts) {
      // Avisos DEL SISTEMA (client_id 0, "Sistema"): no cuelgan de ninguna
      // ficha, así que el `find` los descartaba y el aviso más grave del
      // panel —"los automatismos están parados"— no se veía en Hoy.
      if (al.client_id === 0) continue;
      const cli = c.find((x) => x.id === al.client_id);
      if (!cli) continue;
      if (al.kind === "missing_products") {
        // El botón dice "Abrir Recursos" → lleva DE VERDAD a Recursos (donde
        // se sube el producto), no a la planificación del cliente.
        acciones.push({
          client: cli, alert: al, prio: 3, tone: "#28707C", icon: Package, category: "Falta recurso/producto",
          title: "Suplemento sin producto",
          detail: al.message,
          cta: "Abrir Recursos", tab: "planificacion", to: "/recursos",
        });
      } else if (al.kind === "change_request") {
        // El cliente escribió una petición/duda desde su portal: al coach.
        acciones.push({
          client: cli, alert: al, prio: 1, tone: "#C2453A", icon: HeartPulse, category: "Petición del cliente",
          title: "Duda desde su portal",
          detail: al.message,
          cta: al.action, tab: al.tab,
        });
      } else if (al.kind === "send_feedback") {
        acciones.push({
          client: cli, alert: al, prio: 1, tone: "#7B4FC9", icon: Send, category: "Revisión",
          title: "Feedback generado · falta enviarlo",
          detail: al.message, cta: "Enviar feedback", tab: "feedback",
        });
      } else if (al.kind === "regenerate_goal") {
        acciones.push({
          client: cli, alert: al, prio: 1, tone: "#C96A1E", icon: Sparkles, category: "Objetivo",
          title: "Plan con objetivo anterior",
          detail: al.message, cta: al.action, tab: al.tab,
        });
      } else if (al.kind === "plan_allergen_conflict" || al.kind === "plan_dislike_conflict") {
        // Alergia/aversión añadida DESPUÉS de generar: el plan activo puede
        // seguir sirviendo ese alimento en portal y PDF.
        acciones.push({
          client: cli, alert: al, prio: al.kind === "plan_allergen_conflict" ? 1 : 3,
          tone: "#C2453A", icon: Sparkles, category: "Planificación",
          title: al.kind === "plan_allergen_conflict"
            ? "⚠ Alérgeno en el plan activo" : "Alimento no tolerado en plan",
          detail: al.message, cta: al.action, tab: al.tab,
        });
      } else if (al.kind === "adapt_plan" || al.kind === "publish_plan") {
        // Adaptar el plan a la última revisión: viene del backend (anclado al
        // período ANALIZADO), así que no se apaga por abrir una pestaña.
        acciones.push({
          client: cli, alert: al, prio: 2, tone: "#C96A1E", icon: Sparkles, category: "Adaptar",
          title: al.kind === "adapt_plan"
            ? "Plan sin adaptar a revisión"
            : "Borrador sin activar",
          detail: al.message, cta: al.action, tab: al.tab,
        });
      } else if (al.kind === "plan_stale_inputs") {
        acciones.push({
          client: cli, alert: al, prio: 2, tone: "#C96A1E", icon: Sparkles, category: "Planificación",
          title: "Ficha cambiada tras generar",
          detail: al.message, cta: al.action, tab: al.tab,
        });
      } else if (al.kind === "client_inactive") {
        acciones.push({
          client: cli, alert: al, prio: 3, tone: "#7A7A7A", icon: Hourglass, category: "Inactivo",
          title: "Cliente inactivo",
          detail: al.message, cta: al.action, tab: al.tab,
        });
      } else if (al.kind === "payment_pending") {
        acciones.push({
          client: cli, alert: al, prio: 3, tone: "#9A6B15", icon: CreditCard, category: "Pago",
          title: "Pago pendiente",
          detail: al.message, cta: al.action, tab: al.tab,
        });
      } else if (al.kind === "renewal_due") {
        // Renovación: el plan contratado se agota y nadie lo recordaba.
        acciones.push({
          client: cli, alert: al, prio: al.severity === "alta" ? 2 : 3, tone: "#9A6B15",
          icon: CreditCard, category: "Pago",
          title: al.severity === "alta" ? "Plan vencido · sigue activo" : "Le toca renovar",
          detail: al.message, cta: al.action, tab: al.tab,
        });
      } else if (al.kind === "period_overdue") {
        acciones.push({
          client: cli, alert: al, prio: 4, tone: "#C2453A", icon: Hourglass,
          category: "Revisión",
          title: "Revisión vencida sin cerrar",
          detail: al.message, cta: al.action, tab: al.tab,
        });
      } else if (al.kind === "no_logs") {
        acciones.push({
          client: cli, alert: al, prio: 4, tone: "#C2453A", icon: HeartPulse, category: "Seguimiento",
          title: "Sin registros varios días",
          detail: al.message, cta: al.action, tab: al.tab,
        });
      } else if (al.kind.startsWith("video_call_")) {
        // Videollamada quincenal (Pro): propuesta → aceptar/modificar → agendada
        // → mañana → confirmar. El cliente propone; el coach acepta o modifica.
        acciones.push({
          client: cli, alert: al, prio: al.severity === "alta" ? 1 : 3, tone: "#0EA5E9", icon: Video,
          category: "Videollamada",
          title: al.kind === "video_call_proposed" ? "Propuesta de videollamada"
            : al.kind === "video_call_tomorrow" ? "Videollamada mañana"
            : al.kind === "video_call_confirm" ? "Confirmar videollamada"
            : al.kind === "video_call_manual" ? "Agendar videollamada"
            : "Videollamada",
          detail: al.message,
          cta: al.action, tab: al.tab,
        });
      }
    }
    acciones.sort((a, b) => a.prio - b.prio);
    const conAccion = new Set(
      acciones.filter((a) => a.category !== "Falta recurso/producto").map((a) => a.client.id));
    return { acciones, alDia: c.filter((x) => !conAccion.has(x.id) && x.status !== "inactive") };
  }, [clients, alerts]);

  if (clients === null) return <PageLoader />;

  const urgentes = acciones.filter((a) => a.prio <= 3);
  const enEspera = acciones.filter((a) => a.prio > 3);

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <header className="flex items-end justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-zinc-500">Panel</p>
          <h1 className="mt-1 text-2xl font-semibold text-zinc-100">Hoy</h1>
        </div>
        <Link to="/clientes?nuevo=1" className="btn btn-primary">
          <UserPlus size={16} /> Nuevo cliente
        </Link>
      </header>

      {/* Créditos IA: en móvil no hay barra lateral (nav inferior), así que el
          widget del saldo/gasto vive aquí, arriba del panel. En escritorio se
          oculta: ya está en el sidebar. */}
      <div className="card mt-4 px-1.5 py-1 md:hidden">
        <AiCreditButton collapsed={false} />
      </div>

      {/* Seguimiento diario: el mensaje del día para cada cliente activo. */}
      <div className="mt-4">
        <WhatsAppRound />
      </div>

      {/* VENDER: el kit de ventas vive ahora en su propia pantalla (ofertas en
          tarjetas grandes, enlace comprobado antes de enviarlo). Aquí queda el
          acceso directo: es lo que se usa cuando alguien acaba de escribir. */}
      <Link to="/vender" className="card card-hover mt-4 flex items-center justify-between gap-3 p-4">
        <span className="flex items-center gap-2.5">
          <BadgeEuro size={20} style={{ color: "var(--brand-accent)" }} />
          <span>
            <span className="block text-sm font-semibold" style={{ color: "var(--text)" }}>
              Vender: ofertas y enlaces de pago
            </span>
            <span className="block text-xs" style={{ color: "var(--text-faint)" }}>
              Elige la oferta y manda el enlace de Stripe
            </span>
          </span>
        </span>
        <ChevronRight size={18} style={{ color: "var(--text-faint)" }} />
      </Link>

      {loadFailed && (
        <div className="card mt-4 p-3 text-sm text-zinc-300">
          Sin conexión · datos incompletos, reintentando…
        </div>
      )}

      {/* AVISO DEL SISTEMA: lo más grave que puede pasar (los automatismos
          parados = ni períodos, ni recordatorios, ni cortes de suscripción).
          Banda propia arriba del todo, sin ficha ni avatar. */}
      {alertasDeSistema.map((al) => (
        <div key={al.key} role="alert"
          className="card mt-4 flex items-start gap-2.5 border p-3.5 text-sm"
          style={{ borderColor: "#C2453A66", background: "#C2453A14" }}>
          <AlertTriangle size={18} style={{ color: "#C2453A" }} className="mt-0.5 shrink-0" />
          <span className="min-w-0">
            <span className="block font-semibold" style={{ color: "#E0685C" }}>
              Aviso del sistema
            </span>
            <span className="mt-0.5 block text-zinc-300">{al.message}</span>
            {al.fix && <span className="mt-1 block text-xs text-zinc-500">{al.fix}</span>}
          </span>
        </div>
      ))}

      {/* QUÉ TOCA HACER — el corazón del panel (naranja: acción) */}
      <section className="mt-7">
        <SectionHeader title="Qué toca hacer" count={urgentes.length || undefined}
          right={urgentes.length === 0
            ? <span className="text-xs text-zinc-500">nada pendiente</span> : undefined} />

        {urgentes.length === 0 ? (
          <div className="card flex items-center justify-center gap-2.5 p-10 text-sm text-zinc-500">
            <CheckCircle2 size={18} style={{ color: "var(--brand-accent)" }} />
            Todo al día
          </div>
        ) : (
          // AGRUPADO por tipo de acción (como las carpetas de Clientes): cada
          // grupo con su cabecera, color e icono propios.
          <div className="space-y-4">
            {Array.from(new Set(urgentes.map((a) => a.category))).map((cat) => {
              const items = urgentes.filter((a) => a.category === cat);
              const { tone, icon: Icon } = items[0];
              return (
                <div key={cat}>
                  <div className="mb-1.5 flex items-center gap-1.5">
                    <span className="flex h-5 w-5 items-center justify-center rounded-md"
                      style={{ background: `color-mix(in srgb, ${tone} 14%, transparent)` }}>
                      <Icon size={12} style={{ color: tone }} />
                    </span>
                    <span className="text-xs font-bold uppercase tracking-wide" style={{ color: tone }}>
                      {cat}
                    </span>
                    <span className="text-xs text-zinc-500">{items.length}</span>
                  </div>
                  <div className="space-y-2.5">
                    {items.map((a) => (
                      <ActionCard key={`${a.client.id}-${a.category}-${a.title}`} a={a} />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* AGENDA DE VIDEOLLAMADAS — las agendadas (con Meet), hasta realizarlas */}
      {agenda.length > 0 && (
        <section className="mt-8">
          <SectionHeader title="Videollamadas agendadas" tone="#0EA5E9" icon={Video}
            count={agenda.length} />
          <div className="card p-2">
            <ul className="divide-y" style={{ borderColor: "var(--line)" }}>
              {agenda.map((v) => {
                // "Hoy · 17:00" / "Mañana · 17:00" destacados; el resto conserva
                // el when_label largo. Las de HOY llevan la fila resaltada.
                const tag = agendaDayTag(v.scheduled_at);
                const esHoy = tag === "Hoy";
                return (
                  <li key={v.id} className="flex items-center justify-between gap-3 rounded-lg px-3 py-2.5"
                    style={esHoy ? {
                      background: "color-mix(in srgb, #0EA5E9 8%, transparent)",
                      boxShadow: "inset 3px 0 0 #0EA5E9",
                    } : undefined}>
                    <Link to={`/clientes/${v.client_id}?tab=feedback`}
                      className="flex min-w-0 items-center gap-2.5 hover:opacity-80">
                      <Avatar name={v.client_name} size={30} />
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium text-zinc-200">{v.client_name}</span>
                        <span className="block truncate text-xs capitalize text-zinc-500">
                          {tag ? (
                            <span className="font-semibold" style={{ color: "#0EA5E9" }}>
                              {tag} · {agendaHora(v.scheduled_at)}
                            </span>
                          ) : v.when_label}
                          {v.duration_min ? ` · ${v.duration_min} min` : ""}
                          {v.is_past ? " · pendiente de confirmar" : ""}
                        </span>
                      </span>
                    </Link>
                    {v.meet_url && (
                      <a href={v.meet_url} target="_blank" rel="noopener noreferrer"
                        title="Unirme a Google Meet" aria-label="Unirme a Google Meet"
                        className="tap flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
                        style={{ background: "color-mix(in srgb, #0EA5E9 14%, transparent)", color: "#0EA5E9" }}>
                        <Video size={17} />
                      </a>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        </section>
      )}

      {/* EN ESPERA — informativo, sin urgencia (azul: información) */}
      {enEspera.length > 0 && (
        <section className="mt-8">
          <SectionHeader title="En espera del cliente" tone="var(--brand-accent-2)"
            count={enEspera.length} />
          <div className="space-y-2">
            {enEspera.map((a) => (
              <ActionCard key={`${a.client.id}-${a.category}-${a.title}`} a={a} quiet />
            ))}
          </div>
        </section>
      )}

      {/* AL DÍA — compacto */}
      {alDia.length > 0 && (
        <section className="mt-8">
          <SectionHeader title="Al día" tone="#1B7F4D" count={alDia.length} />
          <div className="card p-2">
            <ul className="divide-y" style={{ borderColor: "var(--line)" }}>
              {alDia.map((c) => (
                <li key={c.id}>
                  <Link
                    to={`/clientes/${c.id}?tab=seguimiento`}
                    className="flex items-center justify-between rounded-lg px-3 py-2.5 hover:bg-[var(--surface-raised)]"
                  >
                    <span className="flex items-center gap-2.5">
                      <Avatar name={c.full_name} size={30} />
                      <span className="text-sm font-medium text-zinc-200">{c.full_name}</span>
                    </span>
                    <span className="flex items-center gap-3">
                      <StatusBadge status={c.status} />
                      <span className="w-20 text-right text-xs text-zinc-600"
                        title="Ficha editada · no es actividad">
                        {relativeDays(c.updated_at)}
                      </span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}
    </div>
  );
}

function ActionCard({ a, quiet }: { a: Accion; quiet?: boolean }) {
  const Icon = a.icon;
  // Destino: el del aviso (con su ancla, para marcar el sitio al llegar) o,
  // sin aviso, la pestaña de siempre.
  const destino = a.alert
    ? (a.alert.to || hrefCliente(a.alert.client_id, a.alert.tab, a.alert.target || undefined))
    : (a.to ?? `/clientes/${a.client.id}?tab=${a.tab}`);
  const anclar = () => {
    const al = a.alert;
    if (!al) return;
    pin({
      id: pinId("alerts", al.key), scope: "alerts", key: al.key,
      clientId: al.client_id, clientName: al.client_name,
      label: al.action, hint: al.fix || al.message,
      href: destino, target: al.target || undefined, severity: al.severity,
    });
  };
  return (
    <Link
      onClick={anclar}
      to={destino}
      className="card card-hover flex flex-wrap items-center gap-x-4 gap-y-2.5 p-4 active:scale-[0.995]"
      style={quiet ? undefined : { borderLeft: `3px solid ${a.tone}` }}
    >
      <span
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
        style={{ background: `${a.tone}14`, color: a.tone }}
      >
        <Icon size={19} />
      </span>
      <div className="min-w-0 flex-1 basis-52">
        <p className="text-sm text-zinc-100">
          <span
            className="mr-1.5 inline-block rounded-full px-1.5 py-0.5 align-middle text-[10px] font-bold uppercase tracking-wide"
            style={{ background: `${a.tone}18`, color: a.tone }}
          >
            {a.category}
          </span>
          <b>{a.client.full_name}</b>
          <span className="mx-1.5 text-zinc-600">·</span>
          {a.title}
        </p>
        {a.detail && <p className="mt-0.5 text-xs text-zinc-500">{a.detail}</p>}
      </div>
      {/* En el móvil el botón ocupa toda la fila: pulsación fácil con el pulgar */}
      <span className={`${quiet ? "btn btn-ghost" : "btn btn-primary"} pointer-events-none w-full justify-center px-3.5 py-2 text-xs sm:w-auto`}>
        {a.cta} <ArrowRight size={13} />
      </span>
    </Link>
  );
}

/** Avatar con la inicial: degradado de marca (naranja→azul) con un matiz
 *  propio por cliente, brillo y volumen — nada plano. */
export function Avatar({ name, size = 34 }: { name: string; size?: number }) {
  const hash = Array.from(name).reduce((a, c) => a + c.charCodeAt(0), 0);
  const angle = 115 + (hash % 130); // ángulo estable por nombre
  return (
    <span
      className="relative flex shrink-0 select-none items-center justify-center overflow-hidden rounded-full font-bold text-white"
      style={{
        width: size,
        height: size,
        fontSize: Math.max(11, Math.round(size * 0.38)),
        background: `linear-gradient(${angle}deg, var(--brand-accent) 0%, #D96F2E 45%, var(--brand-accent-2) 100%)`,
        boxShadow:
          "inset 0 1px 1px rgba(255,255,255,0.45), inset 0 -2px 4px rgba(0,0,0,0.18), 0 1px 3px rgba(38,33,26,0.25)",
        textShadow: "0 1px 2px rgba(0,0,0,0.25)",
      }}
    >
      <span
        className="pointer-events-none absolute inset-x-0 top-0"
        style={{ height: "48%", background: "linear-gradient(rgba(255,255,255,0.28), rgba(255,255,255,0))" }}
      />
      {initials(name)}
    </span>
  );
}
