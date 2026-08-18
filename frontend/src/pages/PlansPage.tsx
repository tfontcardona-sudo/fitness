import { useEffect, useState } from "react";
import { Clock, Mail, MapPin, MessageCircle } from "lucide-react";
import { api } from "../lib/api";
import {
  CENTER_ADDRESS, CENTER_EMAIL, CENTER_SCHEDULE, CENTER_WHATSAPP_DISPLAY,
} from "../lib/branding";
import { PACKAGES } from "../lib/packages";

/**
 * Página PÚBLICA de servicios — el catálogo REAL de la marca, los tres de
 * PAGO ÚNICO y sin permanencia:
 *
 *   · Dieta (70 €)            → plan de nutrición a medida.
 *   · Entrenamiento (70 €)    → plan de entrenamiento a medida.
 *   · Pack completo (130 €)   → los dos + la cuota del gimnasio incluida.
 *
 * Los tres se pagan online (Stripe) o se contratan por WhatsApp. Al pagar, el
 * cliente recibe por email su cuestionario inicial y su acceso a la app.
 */

const BULLETS: Record<string, string[]> = {
  nutri: [
    "Plan de nutrición hecho a partir de tu cuestionario inicial",
    "Tus horarios, tus gustos y tus alergias, no una plantilla",
    "Tres opciones por comida para que no te canses",
    "App para registrar peso y medidas y ver tu evolución",
  ],
  train: [
    "Plan de entrenamiento a partir de tu cuestionario inicial",
    "Adaptado a tus días, tu material y tus molestias",
    "App para registrar cada serie y ver tu progreso",
    "Progresión semanal clara: sabes qué hacer cada día",
  ],
  full: [
    "Dieta y entrenamiento coordinados, los dos a tu medida",
    "La cuota del gimnasio incluida",
    "App con tu plan, tu registro y tu evolución",
    "Informe de seguimiento con el análisis de tus datos",
  ],
};

const PRICE: Record<string, string> = { nutri: "70 €", train: "70 €", full: "130 €" };

const WA: Record<string, string> = {
  nutri: "¡Hola! Me interesa el plan de dieta (70 €). ¿Cómo empezamos?",
  train: "¡Hola! Me interesa el plan de entrenamiento (70 €). ¿Cómo empezamos?",
  full: "¡Hola! Me interesa el pack completo de 130 € (dieta, entrenamiento y cuota). ¿Cómo empezamos?",
};

const GENERIC_MESSAGE =
  "¡Hola! He visto vuestros servicios en la página y me gustaría saber más. " +
  "¿Os cuento mi caso y me decís qué me encaja mejor?";

export default function PlansPage() {
  const [landing, setLanding] = useState<import("../types").LandingOut | null>(null);

  useEffect(() => {
    api.publicLanding().then(setLanding).catch(() => setLanding(null));
  }, []);

  // Teléfono público del centro en formato wa.me (dígitos con prefijo de país;
  // 9 dígitos → España). Es el ÚNICO uso de WhatsApp que queda: el contacto
  // comercial de la web pública, no un canal de entrega.
  const digits = (landing?.contact_phone || CENTER_WHATSAPP_DISPLAY).replace(/\D/g, "");
  const coachDigits = digits ? (digits.length === 9 ? `34${digits}` : digits) : null;
  const contactHref = (text: string): string | null =>
    coachDigits ? `https://wa.me/${coachDigits}?text=${encodeURIComponent(text)}` : null;

  const gold = PACKAGES.full.color;
  const bg = landing?.color_bg ?? "#0F0E0C";

  return (
    <div className="relative" style={{ minHeight: "100vh", background: bg, color: "#26211a" }}>
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

      <div className="relative mx-auto max-w-5xl px-5 py-10">
        <header className="mb-8 flex flex-col items-center text-center text-white"
          style={{ textShadow: "0 2px 12px rgba(0,0,0,0.55), 0 1px 3px rgba(0,0,0,0.7)" }}>
          <img src="/brand-logo.png" alt="Professional Girona" className="h-16 w-auto rounded-xl shadow-lg" />
          <h1 className="mt-4 text-3xl font-extrabold tracking-tight">
            Tu plan, hecho para <span style={{ color: gold }}>ti</span>
          </h1>
          <p className="mt-2 max-w-lg text-sm text-white/90">
            Más de 25 años cuidando la salud y el entreno en Girona. Elige el
            servicio que necesitas: pago único, sin cuotas ni permanencia.
          </p>
        </header>

        {/* Los tres servicios */}
        <div className="grid gap-5 md:grid-cols-3">
          {(["nutri", "train", "full"] as const).map((tier) => {
            const destacado = tier === "full";
            const info = PACKAGES[tier];
            const pagar = `${window.location.origin}/api/pay/plan/${tier}/unico`;
            const href = contactHref(WA[tier]);
            return (
              <div key={tier}
                className={`relative flex flex-col rounded-2xl bg-white p-6 ${destacado ? "border-2 shadow-lg" : "border shadow-sm"}`}
                style={{ borderColor: destacado ? gold : "#e6ddca" }}>
                {destacado && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full px-3 py-0.5 text-[11px] font-bold shadow"
                    style={{ background: gold, color: "#241C04" }}>
                    ⭐ El más completo
                  </span>
                )}
                <span className="inline-flex w-fit items-center rounded-full px-2.5 py-0.5 text-xs font-bold"
                  style={{ background: `color-mix(in srgb, ${info.color} 16%, transparent)`, color: info.color }}>
                  {info.label}
                </span>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="text-4xl font-extrabold tracking-tight">{PRICE[tier]}</span>
                  <span className="text-sm font-semibold opacity-60">pago único</span>
                </div>
                <p className="mt-1 text-[13px] font-medium italic opacity-75">{info.tagline}</p>
                <ul className="mt-4 flex-1 space-y-2">
                  {BULLETS[tier].map((b) => (
                    <li key={b} className="flex gap-2 text-[13px] leading-snug opacity-85">
                      <span className="mt-[1px] shrink-0 font-bold" style={{ color: "#B58910" }}>✓</span>
                      <span>{b}</span>
                    </li>
                  ))}
                </ul>
                <a href={pagar}
                  className="mt-5 flex items-center justify-center gap-2 rounded-xl px-4 py-3.5 text-sm font-bold shadow-md transition-transform hover:brightness-105 active:scale-[0.98]"
                  style={destacado
                    ? { background: gold, color: "#241C04" }
                    : { background: "#37474F", color: "#fff" }}>
                  Contratar por {PRICE[tier]}
                </a>
                {href && (
                  <a href={href} target="_blank" rel="noopener"
                    className="mt-2 text-center text-xs font-semibold underline opacity-60 hover:opacity-90">
                    o pregúntanos por WhatsApp
                  </a>
                )}
              </div>
            );
          })}
        </div>

        {/* Cómo funciona: tres pasos, sin letra pequeña */}
        <div className="mt-8 rounded-2xl bg-white/95 p-5 shadow-sm">
          <h2 className="text-center text-sm font-extrabold uppercase tracking-wide opacity-70">
            Así de fácil es empezar
          </h2>
          <div className="mt-4 grid gap-4 text-sm sm:grid-cols-3">
            {[
              ["1", "Contratas tu servicio", "Pago único online o por WhatsApp. Al momento te llega tu cuestionario inicial al correo."],
              ["2", "Rellenas el cuestionario", "Cinco minutos: tus datos, tu objetivo, tu salud y tus horarios. De ahí sale TU plan."],
              ["3", "Recibes tu plan y tu app", "Te lo enviamos por correo y entras en la app para registrar tu evolución."],
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

        {/* CTA final: para quien duda */}
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

        {/* El centro */}
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
          Pago único y seguro a través de Stripe. Sin cuotas ni permanencia.
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
        Gracias. Ya tienes en tu correo tu cuestionario inicial: rellénalo desde
        el enlace del email y preparamos tu plan. Revisa también la carpeta de
        spam.
      </p>
    </div>
  );
}
