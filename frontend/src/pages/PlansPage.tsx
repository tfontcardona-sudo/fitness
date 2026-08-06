import { useEffect, useState } from "react";
import { MessageCircle } from "lucide-react";
import { api } from "../lib/api";
import { BILLING_PERIODS, PACKAGES, PACKAGE_ORDER, billingLabel } from "../lib/packages";
import { waPhone, waUrl } from "../lib/whatsapp";
import type { PackageTier, PublicBillingPeriod } from "../types";

/**
 * Página PÚBLICA de asesorías (el enlace del perfil). SIN PRECIOS a propósito:
 * cada plan × duración (9 combinaciones) se presenta con una descripción que
 * invita a pedir información, y los botones "Contacta conmigo" abren WhatsApp
 * con el mensaje ya escrito. El precio se habla en la conversación (el coach
 * responde con el kit de ventas del panel: catálogo + enlace de pago directo).
 */

/** Descripción propia de cada plan × duración (los "9 planes"). */
const DURATION_PITCH: Record<PackageTier, Record<PublicBillingPeriod, string>> = {
  train: {
    "1m": "Un mes para probarlo en serio: en 4 semanas notas lo que es entrenar con un plan pensado solo para ti.",
    "3m": "12 semanas: un ciclo completo de progresión. Resultados que se ven en el espejo y se sienten en cada sesión.",
    "6m": "6 meses de progresión planificada: fuerza y físico a otro nivel, con las mejores condiciones al comprometerte.",
  },
  nutri: {
    "1m": "Un mes para ordenar tu alimentación y comprobar que se puede comer bien sin pasar hambre ni vivir a dieta.",
    "3m": "12 semanas: margen real para ver resultados y consolidar hábitos, ajustando tu plan con datos, no con sensaciones.",
    "6m": "6 meses para transformar tu relación con la comida: resultados que se quedan contigo, con las mejores condiciones.",
  },
  full: {
    "1m": "Un mes para arrancar con todo: entrenamiento y dieta coordinados desde el primer día, y primeros cambios visibles.",
    "3m": "12 semanas de trabajo conjunto: la opción favorita de quien busca un cambio visible y que se mantenga.",
    "6m": "6 meses de asesoría completa: la transformación de verdad, con las mejores condiciones de todas.",
  },
};

/** "Para ti si…": que cada visitante se reconozca en un plan al primer vistazo. */
const PLAN_FOR_YOU: Record<PackageTier, string> = {
  train: "Para ti si con la comida te apañas, pero en el gimnasio vas sin rumbo y quieres progresar de verdad.",
  nutri: "Para ti si tu punto débil está en la comida: picas, no sabes cuánto comer o las dietas nunca te duran.",
  full: "Para ti si quieres el cambio completo, con todo pensado y conmigo pendiente de ti cada día.",
};

/** Qué incluye cada plan. */
const PLAN_BULLETS: Record<PackageTier, string[]> = {
  train: [
    "Entrenamiento 100 % a tu medida: tu material, tu horario, tus lesiones y tu nivel",
    "Progresión clara semana a semana, con ajustes según tu evolución real",
    "Tu coach en WhatsApp todos los días",
    "App con tu rutina, registro de series y progreso",
  ],
  nutri: [
    "Nutrición 100 % a tu medida: tus gustos, tus horarios, tus alergias",
    "Objetivos calculados sobre TU caso, no plantillas",
    "Tu coach en WhatsApp todos los días",
    "App con tu plan y tu seguimiento diario",
  ],
  full: [
    "Entrenamiento + nutrición coordinados: todo empuja en la misma dirección",
    "Videollamada de revisión con tu coach",
    "Tu coach en WhatsApp todos los días",
    "App con rutina, dieta y seguimiento",
  ],
};

/** Mensaje prellenado del botón (sin emojis: WhatsApp los corrompe a veces). */
function contactMessage(tier: PackageTier, period: PublicBillingPeriod): string {
  const dur = billingLabel(period).toLowerCase();
  return (
    `¡Hola! He visto la asesoría ${PACKAGES[tier].label} (${dur}) en tu página ` +
    `y me gustaría saber más: cómo funciona, el precio y cómo empezar.`
  );
}

const GENERIC_MESSAGE =
  "¡Hola! He visto tus asesorías en la página y me gustaría saber más. " +
  "¿Te cuento mi caso y me dices qué plan me encaja y su precio?";

export default function PlansPage() {
  const [period, setPeriod] = useState<PublicBillingPeriod>("3m");
  // Marca pública: foto de fondo + teléfono de contacto del coach (WhatsApp).
  const [landing, setLanding] = useState<import("../types").LandingOut | null>(null);

  useEffect(() => {
    api.publicLanding().then(setLanding).catch(() => setLanding(null));
  }, []);

  const coachDigits = waPhone(landing?.contact_phone);

  /** Enlace de contacto: WhatsApp si hay teléfono; email de reserva. */
  function contactHref(text: string, subject: string): string | null {
    if (coachDigits) return waUrl(coachDigits, text);
    if (landing?.contact_email) {
      return `mailto:${landing.contact_email}?subject=${encodeURIComponent(subject)}`;
    }
    return null;
  }

  const bg = landing?.color_bg ?? "#0B111C";
  return (
    <div className="relative" style={{ minHeight: "100vh", background: bg, color: "#26211a" }}>
      {/* Foto de fondo propia (Recursos → Página de enlaces → Foto de los
          planes), visible como en /dq. Sin foto: degradado de marca. */}
      {landing?.plans_photo_url ? (
        <>
          <img src={landing.plans_photo_url} alt=""
            className="pointer-events-none fixed inset-0 h-full w-full object-cover" />
          <div className="pointer-events-none fixed inset-0"
            style={{ background: `linear-gradient(180deg, ${bg}55 0%, ${bg}CC 55%, ${bg}F2 100%)` }} />
        </>
      ) : (
        <div className="pointer-events-none fixed inset-0"
          style={{ background: `radial-gradient(120% 80% at 50% 0%, ${(landing?.color_secondary ?? "#2E5E8C")}44 0%, ${bg} 60%)` }} />
      )}
      <div className="relative mx-auto max-w-4xl px-5 py-10">
        {/* Cabecera en BLANCO sobre la foto (como /dq), con sombra para leerse. */}
        <header className="mb-6 flex flex-col items-center text-center text-white"
          style={{ textShadow: "0 2px 12px rgba(0,0,0,0.55), 0 1px 3px rgba(0,0,0,0.7)" }}>
          <img src="/dq-logo.png" alt="" className="h-14 w-auto rounded-xl shadow-lg" />
          <h1 className="mt-4 text-3xl font-extrabold tracking-tight">
            Empieza tu cambio <span style={{ color: "#F6A560" }}>hoy</span>
          </h1>
          <p className="mt-2 max-w-lg text-sm text-white/90">
            Nada de plantillas: estudio tu caso a fondo, monto tu plan a tu medida
            y me tienes <strong>cada día</strong> en WhatsApp durante todo el proceso.
          </p>
          {/* Gancho de confianza: qué incluye SIEMPRE, de un vistazo */}
          <div className="mt-3 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-xs font-semibold">
            <span style={{ color: "#6FE39A" }}>✓ Plan 100 % a tu medida</span>
            <span style={{ color: "#6FE39A" }}>✓ Tu coach a diario por WhatsApp</span>
            <span style={{ color: "#6FE39A" }}>✓ App de seguimiento</span>
          </div>
        </header>

        {/* Duración: cada plan tiene su versión mensual, trimestral y semestral
            (9 opciones). Las duraciones largas, con mejores condiciones. */}
        <div className="mb-2 flex justify-center">
          <div className="inline-flex rounded-xl border bg-white p-1 shadow-sm" style={{ borderColor: "#e6ddca" }}>
            {BILLING_PERIODS.map((b) => {
              const sel = period === b.value;
              return (
                <button
                  key={b.value}
                  type="button"
                  onClick={() => setPeriod(b.value)}
                  aria-pressed={sel}
                  className="rounded-lg px-4 py-2 text-sm font-semibold transition-colors"
                  style={sel
                    ? { background: "#2E5E8C", color: "white" }
                    : { color: "#26211a", opacity: 0.65 }}
                >
                  {b.label}
                </button>
              );
            })}
          </div>
        </div>
        <p className="mb-6 text-center text-xs font-semibold text-white/75"
          style={{ textShadow: "0 1px 3px rgba(0,0,0,0.6)" }}>
          Trimestral y semestral con condiciones especiales — pregúntame sin compromiso.
        </p>

        <div className="grid gap-4 sm:grid-cols-3">
          {PACKAGE_ORDER.map((t) => {
            const p = PACKAGES[t];
            const destacado = t === "full"; // el pack completo: el más elegido
            const href = contactHref(
              contactMessage(t, period),
              `Información ${p.label} (${billingLabel(period)})`,
            );
            return (
              <div key={t}
                className={`relative flex flex-col rounded-2xl border bg-white p-5 shadow-sm ${destacado ? "shadow-lg sm:-mt-2 sm:mb-[-8px]" : ""}`}
                style={{
                  borderColor: destacado ? p.color : `color-mix(in srgb, ${p.color} 40%, #e6ddca)`,
                  borderWidth: destacado ? 2 : 1,
                }}>
                {destacado && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full px-3 py-0.5 text-[11px] font-bold text-white shadow"
                    style={{ background: p.color }}>
                    ⭐ El más elegido
                  </span>
                )}
                <span className="inline-flex w-fit items-center rounded-full px-2.5 py-0.5 text-xs font-semibold"
                  style={{ background: `color-mix(in srgb, ${p.color} 14%, transparent)`, color: p.color }}>
                  {p.label}
                </span>
                <p className="mt-2 text-[13px] font-medium italic opacity-75">
                  {PLAN_FOR_YOU[t]}
                </p>
                {/* La descripción de ESTA duración: el gancho de la combinación. */}
                <p className="mt-2 text-sm font-semibold leading-snug" style={{ color: p.color }}>
                  {DURATION_PITCH[t][period]}
                </p>
                <ul className="mt-3 flex-1 space-y-1.5">
                  {PLAN_BULLETS[t].map((b) => (
                    <li key={b} className="flex gap-2 text-[13px] leading-snug opacity-80">
                      <span className="mt-[1px] shrink-0 font-bold" style={{ color: "#2E7D46" }}>✓</span>
                      <span>{b}</span>
                    </li>
                  ))}
                </ul>
                {href ? (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener"
                    className="mt-4 flex items-center justify-center gap-2 rounded-xl px-4 py-3.5 text-sm font-bold text-white shadow-md transition-transform hover:brightness-110 active:scale-[0.98]"
                    style={{ background: p.color }}
                  >
                    <MessageCircle size={16} /> Contacta conmigo
                  </a>
                ) : (
                  <p className="mt-4 rounded-xl border p-3 text-center text-xs opacity-70"
                    style={{ borderColor: "#e6ddca" }}>
                    Escríbeme por redes para saber más.
                  </p>
                )}
              </div>
            );
          })}
        </div>

        {/* Cómo funciona: 3 pasos — quita el miedo a "¿y ahora qué?". */}
        <div className="mt-8 rounded-2xl bg-white/95 p-5 shadow-sm">
          <h2 className="text-center text-sm font-extrabold uppercase tracking-wide opacity-70">
            Así de fácil es empezar
          </h2>
          <div className="mt-4 grid gap-4 text-sm sm:grid-cols-3">
            {[
              ["1", "Me escribes por WhatsApp", "Me cuentas tu caso y tu objetivo. Te respondo yo, no un bot: te digo el precio y resolvemos tus dudas."],
              ["2", "Estudio tu caso a fondo", "Cuestionario inicial completo: salud, lesiones, gustos, horarios y material. De ahí sale TU plan, no una plantilla."],
              ["3", "Empezamos y te acompaño", "Tu plan en tu app, seguimiento diario por WhatsApp y ajustes según tu progreso real."],
            ].map(([n, titulo, texto]) => (
              <div key={n} className="flex gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-extrabold text-white"
                  style={{ background: "#2E5E8C" }}>
                  {n}
                </span>
                <div>
                  <p className="font-bold">{titulo}</p>
                  <p className="mt-0.5 text-[13px] leading-snug opacity-75">{texto}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CTA final: para quien duda entre planes. */}
        <div className="mt-6 rounded-2xl border-2 bg-white p-5 text-center shadow-lg"
          style={{ borderColor: "#F6A560" }}>
          <p className="text-base font-extrabold">¿No tienes claro cuál es para ti?</p>
          <p className="mx-auto mt-1 max-w-md text-sm opacity-75">
            Escríbeme, me cuentas tu caso en dos líneas y te digo yo qué plan te
            encaja y su precio. Sin compromiso: preguntar es gratis.
          </p>
          {(() => {
            const href = contactHref(GENERIC_MESSAGE, "Información asesorías DQ");
            return href ? (
              <a href={href} target="_blank" rel="noopener"
                className="mx-auto mt-3 inline-flex items-center justify-center gap-2 rounded-xl px-6 py-3.5 text-sm font-bold text-white shadow-md transition-transform hover:brightness-110 active:scale-[0.98]"
                style={{ background: "#25D366" }}>
                <MessageCircle size={16} /> Escríbeme por WhatsApp
              </a>
            ) : null;
          })()}
        </div>

        <p className="mt-8 text-center text-xs text-white/60"
          style={{ textShadow: "0 1px 3px rgba(0,0,0,0.6)" }}>
          Te respondo personalmente. Cuando lo tengas claro, pagas de forma segura
          con Stripe a través de tu enlace personal.
        </p>
      </div>
    </div>
  );
}

/** Página de gracias tras un pago correcto (success_url de Stripe). */
export function PaymentOkPage() {
  return (
    <div style={{ minHeight: "100vh", background: "#f6f1e7", color: "#26211a" }}
      className="flex flex-col items-center justify-center px-8 text-center">
      <img src="/dq-logo.png" alt="" className="h-14 w-auto rounded-xl shadow-sm" />
      <h1 className="mt-5 text-2xl font-bold">¡Pago recibido!</h1>
      <p className="mt-2 max-w-md text-sm opacity-75">
        Gracias. Ya tienes en tu correo tu cuestionario inicial (anamnesis):
        rellénalo y súbelo desde el enlace del email para que preparemos tu plan.
        Revisa también la carpeta de spam.
      </p>
    </div>
  );
}
