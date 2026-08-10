import { useEffect, useState } from "react";
import { Clock, Mail, MapPin, MessageCircle } from "lucide-react";
import { api } from "../lib/api";
import {
  CENTER_ADDRESS,
  CENTER_EMAIL,
  CENTER_SCHEDULE,
  CENTER_WHATSAPP_DISPLAY,
  PT_RATES,
} from "../lib/branding";
import { PACKAGES } from "../lib/packages";
import { waPhone, waUrl } from "../lib/whatsapp";

/**
 * Página PÚBLICA de planes — catálogo REAL de la marca (professionalgirona.com):
 *
 *  · Génesis.99 (99 €/mes): preparación personal COMPLETA (nutrición +
 *    entrenamiento), el producto online del sistema. Precio visible (es público
 *    en su web) + CTA de WhatsApp y pago online con Stripe.
 *  · Entreno Personal: sesiones presenciales en el centro, con las tarifas
 *    por hora y pack tal cual las publica el sitio; se reservan por WhatsApp
 *    y se cobran en el centro (sin pago online, el backend lo veta).
 */

const GENESIS_BULLETS = [
  "Nutrición y entrenamiento 100 % a tu medida, a partir de tu cuestionario inicial",
  "Tu app personal: plan, diario, registro de entrenos y progreso",
  "Revisión cada 15 días con ajustes sobre tus datos reales",
  "Informe de progreso de tu preparador en cada revisión",
  "Tu preparador en WhatsApp durante todo el proceso",
];

const PT_BULLETS = [
  "Sesiones 1:1 con nuestros entrenadores en el centro",
  "Tu rutina y tus marcas siempre contigo en la app",
  "Seguimiento de composición corporal para ajustar con datos",
];

const GENESIS_MESSAGE =
  "¡Hola! He visto la preparación Génesis.99 en vuestra página y me gustaría " +
  "empezar: ¿me contáis cómo funciona y los siguientes pasos?";

const PT_MESSAGE =
  "¡Hola! Quiero reservar una sesión de entreno personal. ¿Qué disponibilidad tenéis?";

const GENERIC_MESSAGE =
  "¡Hola! He visto vuestros planes en la página y me gustaría saber más. " +
  "¿Os cuento mi caso y me decís qué me encaja mejor?";

export default function PlansPage() {
  // Marca pública: foto de fondo + contacto del centro (WhatsApp).
  const [landing, setLanding] = useState<import("../types").LandingOut | null>(null);

  useEffect(() => {
    api.publicLanding().then(setLanding).catch(() => setLanding(null));
  }, []);

  // WhatsApp del centro: el de la página Marca manda; si aún no cargó la
  // marca, el número público del centro (branding.ts) evita botones muertos.
  const coachDigits = waPhone(landing?.contact_phone) || waPhone(CENTER_WHATSAPP_DISPLAY.startsWith("+") ? CENTER_WHATSAPP_DISPLAY : `+34 ${CENTER_WHATSAPP_DISPLAY}`);
  const contactHref = (text: string): string | null =>
    coachDigits ? waUrl(coachDigits, text) : null;

  const gold = PACKAGES.full.color;
  const slate = PACKAGES.train.color;
  const bg = landing?.color_bg ?? "#0F0E0C";
  const payOnline = `${window.location.origin}/api/pay/plan/full/1m`;

  return (
    <div className="relative" style={{ minHeight: "100vh", background: bg, color: "#26211a" }}>
      {/* Foto de fondo propia (Recursos → Página de enlaces → Foto de los
          planes), visible como en la página de enlaces. Sin foto: degradado de marca. */}
      {landing?.plans_photo_url ? (
        <>
          <img src={landing.plans_photo_url} alt=""
            className="pointer-events-none fixed inset-0 h-full w-full object-cover" />
          <div className="pointer-events-none fixed inset-0"
            style={{ background: `linear-gradient(180deg, ${bg}55 0%, ${bg}CC 55%, ${bg}F2 100%)` }} />
        </>
      ) : (
        <div className="pointer-events-none fixed inset-0"
          style={{ background: `radial-gradient(120% 80% at 50% 0%, ${gold}2E 0%, ${bg} 60%)` }} />
      )}
      <div className="relative mx-auto max-w-4xl px-5 py-10">
        {/* Cabecera en BLANCO sobre la foto, con sombra para leerse. */}
        <header className="mb-8 flex flex-col items-center text-center text-white"
          style={{ textShadow: "0 2px 12px rgba(0,0,0,0.55), 0 1px 3px rgba(0,0,0,0.7)" }}>
          <img src="/brand-logo.png" alt="Professional Girona" className="h-16 w-auto rounded-xl shadow-lg" />
          <h1 className="mt-4 text-3xl font-extrabold tracking-tight">
            Tu cambio empieza en <span style={{ color: gold }}>Professional</span>
          </h1>
          <p className="mt-2 max-w-lg text-sm text-white/90">
            Más de 25 años cuidando la salud y el entreno en Girona. Elige cómo
            quieres que te acompañemos: preparación completa o sesiones con
            nuestros entrenadores.
          </p>
          <div className="mt-3 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-xs font-semibold">
            <span style={{ color: "#F7C33A" }}>✓ Plan 100 % a tu medida</span>
            <span style={{ color: "#F7C33A" }}>✓ Tu app de seguimiento</span>
            <span style={{ color: "#F7C33A" }}>✓ Tu preparador por WhatsApp</span>
          </div>
        </header>

        <div className="grid gap-5 md:grid-cols-2">
          {/* ============== GÉNESIS.99 — preparación personal completa ============== */}
          <div className="relative flex flex-col rounded-2xl border-2 bg-white p-6 shadow-lg"
            style={{ borderColor: gold }}>
            <span className="absolute -top-3 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full px-3 py-0.5 text-[11px] font-bold shadow"
              style={{ background: gold, color: "#241C04" }}>
              ⭐ Preparación personal
            </span>
            <span className="inline-flex w-fit items-center rounded-full px-2.5 py-0.5 text-xs font-bold"
              style={{ background: `color-mix(in srgb, ${gold} 16%, transparent)`, color: "#8A6403" }}>
              {PACKAGES.full.label}
            </span>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-4xl font-extrabold tracking-tight">99 €</span>
              <span className="text-sm font-semibold opacity-60">/ mes</span>
            </div>
            <p className="mt-1 text-[13px] font-medium italic opacity-75">
              Nutrición y entrenamiento coordinados, contigo de principio a fin.
              Para quien quiere el cambio completo.
            </p>
            <ul className="mt-4 flex-1 space-y-2">
              {GENESIS_BULLETS.map((b) => (
                <li key={b} className="flex gap-2 text-[13px] leading-snug opacity-85">
                  <span className="mt-[1px] shrink-0 font-bold" style={{ color: "#B58910" }}>✓</span>
                  <span>{b}</span>
                </li>
              ))}
            </ul>
            {(() => {
              const href = contactHref(GENESIS_MESSAGE);
              return href ? (
                <a href={href} target="_blank" rel="noopener"
                  className="mt-5 flex items-center justify-center gap-2 rounded-xl px-4 py-3.5 text-sm font-bold shadow-md transition-transform hover:brightness-105 active:scale-[0.98]"
                  style={{ background: gold, color: "#241C04" }}>
                  <MessageCircle size={16} /> Empezar — hablamos por WhatsApp
                </a>
              ) : null;
            })()}
            {/* Pago online directo (Stripe). Sin Stripe configurado, el backend
                redirige de vuelta a esta página: el enlace nunca rompe. */}
            <a href={payOnline} className="mt-2 text-center text-xs font-semibold underline opacity-60 hover:opacity-90">
              o empieza ya con pago online seguro (Stripe)
            </a>
          </div>

          {/* ============== ENTRENO PERSONAL — sesiones en el centro ============== */}
          <div className="flex flex-col rounded-2xl border bg-white p-6 shadow-sm"
            style={{ borderColor: `color-mix(in srgb, ${slate} 45%, #e6ddca)` }}>
            <span className="inline-flex w-fit items-center rounded-full px-2.5 py-0.5 text-xs font-bold text-white"
              style={{ background: slate }}>
              Entreno Personal
            </span>
            <p className="mt-3 text-[13px] font-medium italic opacity-75">
              Sesiones presenciales 1:1 en el centro, a tu ritmo y con tu
              entrenador. Reserva por WhatsApp y paga en el centro.
            </p>
            {/* Tarifas tal cual las publica la web: etiqueta + chip dorado. */}
            <div className="mt-4 space-y-2">
              {PT_RATES.map((r) => (
                <div key={r.label} className="flex items-center justify-between gap-3 border-b pb-2"
                  style={{ borderColor: "#eee7d7" }}>
                  <span className="text-[13px] font-medium opacity-85">{r.label}</span>
                  <span className="shrink-0 rounded-md px-2.5 py-1 text-[13px] font-extrabold"
                    style={{ background: gold, color: "#241C04" }}>
                    {r.price}
                  </span>
                </div>
              ))}
            </div>
            <ul className="mt-4 flex-1 space-y-2">
              {PT_BULLETS.map((b) => (
                <li key={b} className="flex gap-2 text-[13px] leading-snug opacity-85">
                  <span className="mt-[1px] shrink-0 font-bold" style={{ color: "#B58910" }}>✓</span>
                  <span>{b}</span>
                </li>
              ))}
            </ul>
            {(() => {
              const href = contactHref(PT_MESSAGE);
              return href ? (
                <a href={href} target="_blank" rel="noopener"
                  className="mt-5 flex items-center justify-center gap-2 rounded-xl px-4 py-3.5 text-sm font-bold text-white shadow-md transition-transform hover:brightness-110 active:scale-[0.98]"
                  style={{ background: slate }}>
                  <MessageCircle size={16} /> Reserva tu sesión
                </a>
              ) : null;
            })()}
          </div>
        </div>

        {/* Cómo funciona: 3 pasos — quita el miedo a "¿y ahora qué?". */}
        <div className="mt-8 rounded-2xl bg-white/95 p-5 shadow-sm">
          <h2 className="text-center text-sm font-extrabold uppercase tracking-wide opacity-70">
            Así de fácil es empezar
          </h2>
          <div className="mt-4 grid gap-4 text-sm sm:grid-cols-3">
            {[
              ["1", "Escríbenos por WhatsApp", "Nos cuentas tu caso y tu objetivo. Te respondemos nosotros, no un bot, y resolvemos tus dudas."],
              ["2", "Estudiamos tu caso a fondo", "Cuestionario inicial completo: salud, lesiones, gustos, horarios. De ahí sale TU plan, no una plantilla."],
              ["3", "Empezamos y te acompañamos", "Tu plan en tu app, seguimiento diario y revisión cada 15 días con ajustes según tu progreso real."],
            ].map(([n, titulo, texto]) => (
              <div key={n} className="flex gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-extrabold"
                  style={{ background: gold, color: "#241C04" }}>
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

        {/* CTA final: para quien duda. */}
        <div className="mt-6 rounded-2xl border-2 bg-white p-5 text-center shadow-lg"
          style={{ borderColor: gold }}>
          <p className="text-base font-extrabold">¿No tienes claro qué te encaja?</p>
          <p className="mx-auto mt-1 max-w-md text-sm opacity-75">
            Escríbenos, nos cuentas tu caso en dos líneas y te decimos qué opción
            es para ti. Sin compromiso: preguntar es gratis.
          </p>
          {(() => {
            const href = contactHref(GENERIC_MESSAGE);
            return href ? (
              <a href={href} target="_blank" rel="noopener"
                className="mx-auto mt-3 inline-flex items-center justify-center gap-2 rounded-xl px-6 py-3.5 text-sm font-bold text-white shadow-md transition-transform hover:brightness-110 active:scale-[0.98]"
                style={{ background: "#25D366" }}>
                <MessageCircle size={16} /> Escríbenos por WhatsApp
              </a>
            ) : null;
          })()}
        </div>

        {/* El centro: dirección, horario y contacto (professionalgirona.com). */}
        <div className="mt-6 grid gap-4 rounded-2xl bg-white/95 p-5 text-sm shadow-sm sm:grid-cols-3">
          <div className="flex gap-2.5">
            <MapPin size={16} className="mt-0.5 shrink-0" style={{ color: "#8A6403" }} />
            <div>
              <p className="font-bold">El centro</p>
              <p className="mt-0.5 text-[13px] leading-snug opacity-75">{CENTER_ADDRESS}</p>
            </div>
          </div>
          <div className="flex gap-2.5">
            <Clock size={16} className="mt-0.5 shrink-0" style={{ color: "#8A6403" }} />
            <div>
              <p className="font-bold">Horario</p>
              {CENTER_SCHEDULE.map(([dias, horas]) => (
                <p key={dias} className="mt-0.5 text-[13px] leading-snug opacity-75">
                  {dias}: {horas}
                </p>
              ))}
            </div>
          </div>
          <div className="flex gap-2.5">
            <Mail size={16} className="mt-0.5 shrink-0" style={{ color: "#8A6403" }} />
            <div>
              <p className="font-bold">Contacto</p>
              <p className="mt-0.5 text-[13px] leading-snug opacity-75">
                WhatsApp {landing?.contact_phone ?? CENTER_WHATSAPP_DISPLAY}
              </p>
              <p className="mt-0.5 break-all text-[13px] leading-snug opacity-75">
                {landing?.contact_email ?? CENTER_EMAIL}
              </p>
            </div>
          </div>
        </div>

        <p className="mt-8 text-center text-xs text-white/60"
          style={{ textShadow: "0 1px 3px rgba(0,0,0,0.6)" }}>
          Te respondemos personalmente. El pago online es seguro a través de Stripe;
          las sesiones de entreno personal se abonan en el centro.
        </p>
      </div>
    </div>
  );
}

/** Página de gracias tras un pago correcto (success_url de Stripe). */
export function PaymentOkPage() {
  return (
    <div style={{ minHeight: "100vh", background: "#0F0E0C", color: "#F5F3EE" }}
      className="flex flex-col items-center justify-center px-8 text-center">
      <img src="/brand-logo.png" alt="" className="h-14 w-auto rounded-xl shadow-sm" />
      <h1 className="mt-5 text-2xl font-bold">¡Pago recibido!</h1>
      <p className="mt-2 max-w-md text-sm opacity-75">
        Gracias. Ya tienes en tu correo tu cuestionario inicial (anamnesis):
        rellénalo y súbelo desde el enlace del email para que preparemos tu plan.
        Revisa también la carpeta de spam.
      </p>
    </div>
  );
}
