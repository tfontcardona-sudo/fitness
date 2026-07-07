import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  ClipboardCheck,
  Flag,
  HeartPulse,
  Hourglass,
  Sparkles,
  UserPlus,
} from "lucide-react";
import { api } from "../lib/api";
import type { ClientOut } from "../types";
import { PageLoader, StatusBadge } from "../components/ui";
import { goalReviewDue, initials, relativeDays } from "../lib/format";

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
  detail: string;            // qué hay que hacer
  cta: string;               // texto del botón
  tab: string;               // pestaña destino del perfil
  tone: string;              // color del indicador
  icon: typeof Sparkles;
}

function nextAction(c: ClientOut): Accion | null {
  if (c.status === "review_pending")
    return {
      client: c, prio: 1, tone: "#7B4FC9", icon: ClipboardCheck, category: "Revisión",
      title: `Revisión quincenal #${c.review_period_index ?? c.pending_review_period ?? ""} subida`,
      detail: "El cliente ha cerrado sus 2 semanas: revisa los datos y genera su feedback.",
      cta: "Generar feedback", tab: "feedback",
    };
  if (c.status === "at_risk")
    return {
      client: c, prio: 1, tone: "#C2453A", icon: HeartPulse, category: "Riesgo",
      title: "Adherencia baja",
      detail: "Lleva días sin registrar o con adherencia baja: revisa su seguimiento y contáctalo.",
      cta: "Ver seguimiento", tab: "seguimiento",
    };
  if (c.pending_review)
    return {
      client: c, prio: 2, tone: "#C96A1E", icon: Sparkles, category: "Adaptar",
      title: `Feedback de la revisión #${c.pending_review_period ?? ""} listo`,
      detail: "Revisa los cambios propuestos (dieta y entreno) y adapta su planificación.",
      cta: "Adaptar planificación", tab: "planificacion",
    };
  if (c.status === "onboarding" && !c.goal_type)
    // Aún SIN anamnesis: el botón lleva a completarla/leerla (lo que falta)
    return {
      client: c, prio: 3, tone: "#4C66C9", icon: UserPlus, category: "Pendiente",
      title: "Cliente nuevo · falta su anamnesis",
      detail: "Reenvíale el enlace si hace falta y, cuando llegue el PDF, léelo con la IA.",
      cta: "Abrir anamnesis", tab: "anamnesis",
    };
  if (c.status === "onboarding")
    return {
      client: c, prio: 3, tone: "#4C66C9", icon: UserPlus, category: "Pendiente",
      title: "Anamnesis lista · falta su planificación",
      detail: "Revisa los datos y genera su primera planificación con la IA.",
      cta: "Crear planificación", tab: "planificacion",
    };
  // 45 días en la misma etapa de objetivo → valorar cambio (posponible)
  const dueDays = goalReviewDue(c);
  if (dueDays != null)
    return {
      client: c, prio: 3, tone: "#2E5E8C", icon: Flag, category: "Objetivo",
      title: `${dueDays} días con el mismo objetivo`,
      detail: "Genera el análisis de la etapa y valora con el cliente si toca cambiar de objetivo.",
      cta: "Valorar objetivo", tab: "planificacion",
    };
  if (c.status === "awaiting_feedback")
    return {
      client: c, prio: 4, tone: "#9A6B15", icon: Hourglass, category: "En espera",
      title: "Esperando su cierre quincenal",
      detail: "El período está en marcha: puedes seguir sus registros diarios en tiempo real.",
      cta: "Ver seguimiento", tab: "seguimiento",
    };
  return null; // activo y al día
}

export default function DashboardPage() {
  const [clients, setClients] = useState<ClientOut[] | null>(null);

  useEffect(() => {
    const load = () => api.listClients().then(setClients).catch(() => setClients((c) => c ?? []));
    load();
    // Refresco cada 30 s (solo con la pestaña visible): el panel siempre al día
    const t = window.setInterval(() => {
      if (!document.hidden) load();
    }, 30000);
    return () => window.clearInterval(t);
  }, []);

  const { acciones, alDia } = useMemo(() => {
    const c = clients ?? [];
    const acciones = c
      .map(nextAction)
      .filter((a): a is Accion => a !== null)
      .sort((a, b) => a.prio - b.prio);
    const conAccion = new Set(acciones.map((a) => a.client.id));
    return { acciones, alDia: c.filter((x) => !conAccion.has(x.id) && x.status !== "inactive") };
  }, [clients]);

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

      {/* QUÉ TOCA HACER — el corazón del panel (naranja: acción) */}
      <section className="mt-7">
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-zinc-200">
            <span aria-hidden className="h-3.5 w-1 rounded-full" style={{ background: "var(--brand-accent)" }} />
            Qué toca hacer
          </h2>
          <span className="text-xs text-zinc-500">
            {urgentes.length === 0 ? "nada pendiente" : `${urgentes.length} acción${urgentes.length === 1 ? "" : "es"}`}
          </span>
        </div>

        {urgentes.length === 0 ? (
          <div className="card flex items-center justify-center gap-2.5 p-10 text-sm text-zinc-500">
            <CheckCircle2 size={18} style={{ color: "var(--brand-accent)" }} />
            Todo al día. Ninguna acción pendiente con tus clientes.
          </div>
        ) : (
          <div className="space-y-2.5">
            {urgentes.map((a) => (
              <ActionCard key={a.client.id} a={a} />
            ))}
          </div>
        )}
      </section>

      {/* EN ESPERA — informativo, sin urgencia (azul: información) */}
      {enEspera.length > 0 && (
        <section className="mt-8">
          <h2 className="mb-3 flex items-center gap-1.5 text-sm font-semibold text-zinc-200">
            <span aria-hidden className="h-3.5 w-1 rounded-full" style={{ background: "var(--brand-accent-2)" }} />
            En espera del cliente
          </h2>
          <div className="space-y-2">
            {enEspera.map((a) => (
              <ActionCard key={a.client.id} a={a} quiet />
            ))}
          </div>
        </section>
      )}

      {/* AL DÍA — compacto */}
      {alDia.length > 0 && (
        <section className="mt-8">
          <h2 className="mb-3 text-sm font-semibold text-zinc-200">
            Al día <span className="ml-1 text-xs font-normal text-zinc-500">{alDia.length}</span>
          </h2>
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
                      <span className="w-20 text-right text-xs text-zinc-600">{relativeDays(c.updated_at)}</span>
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
  return (
    <Link
      to={`/clientes/${a.client.id}?tab=${a.tab}`}
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
        <p className="mt-0.5 text-xs text-zinc-500">{a.detail}</p>
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
