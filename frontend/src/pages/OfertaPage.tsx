import { MessageCircle, ShieldCheck, Zap } from "lucide-react";
import { waPhone, waUrl } from "../lib/whatsapp";
import MarcaLogo from "../components/MarcaLogo";
import { useMarcaPublica } from "../hooks/useMarcaPublica";
import { coloresDeMarca, MARCA_POR_DEFECTO, pielDe } from "../lib/marca";

/**
 * Página PÚBLICA de la OFERTA (el enlace de la bio en la campaña de story/post):
 * PROGRAMA CERRADO de 3 meses del plan completo — 1 € el primer mes y 120 € el
 * segundo y el tercero (total 241 €). Dos formas de pagarlo (3 pagos con el
 * gancho del euro, o 2 pagos de 120,50 €) y en ambas el cobro SE DETIENE SOLO:
 * sin renovación automática ni sorpresas. Tercera salida: preguntar por
 * WhatsApp.
 */

const WA_MESSAGE =
  "¡Hola! He visto la oferta del primer mes por 1 € y quiero saber más antes de empezar.";

const INCLUYE = [
  "Entrenamiento 100 % a tu medida: tu material, tu horario, tus lesiones y tu nivel",
  "Nutrición 100 % a tu medida: tus gustos, tus horarios, tus alergias",
  "Conmigo en WhatsApp todos los días",
  "App con tu rutina, tu dieta y tu seguimiento",
  "Videollamada de revisión conmigo",
];

export default function OfertaPage() {
  const landing = useMarcaPublica();

  const coachDigits = waPhone(landing?.contact_phone);
  const waHref = coachDigits ? waUrl(coachDigits, WA_MESSAGE) : null;
  const payHref = "/api/pay/plan/full/oferta";
  // La MISMA oferta en 2 pagos de 120,50 € (hoy y al mes): tras el segundo
  // cobro no hay más cargos — el backend cancela la suscripción solo.
  const pay2Href = "/api/pay/plan/full/oferta2";

  const bg = landing?.color_bg ?? MARCA_POR_DEFECTO.bg;
  // La atmósfera de la página con el color que le toca a esta piel (el
  // "segundo" de Professional es su negro de estructura: sobre negro no pinta).
  const atmosfera = coloresDeMarca(
    pielDe(landing?.skin), landing?.color_primary ?? MARCA_POR_DEFECTO.primary,
    landing?.color_secondary ?? MARCA_POR_DEFECTO.secondary).secondary;
  // ESTA MARCA NO TIENE OFERTA. La página existe para la campaña de DQR y
  // anuncia un primer mes a 1 €; con el switch en un negocio que no la vende,
  // enseñarla es ofrecer un precio que nadie va a cobrar — y sus botones
  // llevan a un checkout que el backend no tiene montado para esa marca.
  if (landing && !landing.has_offer) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center px-8 text-center"
        style={{ background: bg, color: "#fff" }}>
        <MarcaLogo logoUrl={landing.logo_url} skin={landing.skin} nombre={landing.name} alto={56} />
        <h1 className="mt-5 text-2xl font-bold">Esta oferta no está disponible</h1>
        <p className="mt-2 max-w-md text-sm text-white/80">
          {landing.name} no tiene ninguna promoción abierta ahora mismo. Mira lo
          que sí ofrecemos y sus precios.
        </p>
        <a href="/planes" className="mt-5 rounded-xl px-5 py-3 text-sm font-bold"
          style={{ background: "var(--brand-accent)", color: "#1A1405" }}>
          Ver lo que ofrecemos
        </a>
      </div>
    );
  }

  return (
    <div className="relative" style={{ minHeight: "100vh", background: bg, color: "#26211a" }}>
      {landing?.plans_photo_url ? (
        <>
          <img src={landing.plans_photo_url} alt=""
            className="pointer-events-none fixed inset-0 h-full w-full object-cover" />
          <div className="pointer-events-none fixed inset-0"
            style={{ background: `linear-gradient(180deg, ${bg}66 0%, ${bg}D9 55%, ${bg}F5 100%)` }} />
        </>
      ) : (
        <div className="pointer-events-none fixed inset-0"
          style={{ background: `radial-gradient(120% 80% at 50% 0%, ${atmosfera}55 0%, ${bg} 60%)` }} />
      )}

      <div className="relative mx-auto max-w-xl px-5 py-10">
        <header className="flex flex-col items-center text-center text-white"
          style={{ textShadow: "0 2px 12px rgba(0,0,0,0.55), 0 1px 3px rgba(0,0,0,0.7)" }}>
          <MarcaLogo logoUrl={landing?.logo_url} skin={landing?.skin} nombre={landing?.name} alto={56} />
          <span className="mt-4 inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-extrabold uppercase tracking-widest text-white"
            style={{ background: "#C2453A" }}>
            <Zap size={12} /> Oferta de lanzamiento · plazas limitadas este mes
          </span>
          <h1 className="pub-h1 mt-3 text-4xl font-extrabold leading-tight tracking-tight">
            Tu primer mes,
            <br />
            <span style={{ color: "var(--brand-accent-hi)" }}>por 1 €</span>
          </h1>
          <p className="mt-3 max-w-md text-sm text-white/90">
            El plan completo: entrenamiento y nutrición hechos SOLO para ti,
            conmigo cada día por WhatsApp. Un programa de 3 meses: empiezas hoy
            por 1 €, y el segundo y el tercer mes son 120 € cada uno. Después,
            nada más.
          </p>
        </header>

        {/* Qué incluye + garantía */}
        <div className="mt-6 rounded-2xl bg-white p-5 shadow-lg">
          <p className="text-sm font-extrabold uppercase tracking-wide opacity-70">
            Todo esto, desde el primer día
          </p>
          <ul className="mt-3 space-y-2">
            {INCLUYE.map((b) => (
              <li key={b} className="flex gap-2 text-sm leading-snug">
                <span className="shrink-0 font-bold" style={{ color: "#2E7D46" }}>✓</span>
                <span>{b}</span>
              </li>
            ))}
          </ul>
          <div className="mt-4 rounded-xl border p-3 text-[13px] leading-snug"
            style={{ borderColor: "#cfe3cf", background: "#f4faf4" }}>
            <p className="flex items-center gap-1.5 font-bold" style={{ color: "#2E7D46" }}>
              <ShieldCheck size={15} /> Sin sorpresas, garantizado
            </p>
            <p className="mt-1 opacity-80">
              Programa cerrado de 3 meses: 1 € hoy, 120 € el segundo mes y 120 €
              el tercero (241 € en total, por debajo de lo que cuestan el plan de
              entrenamiento y el de nutrición por separado). Después el cobro se
              detiene SOLO: sin renovación automática ni permanencia escondida.
            </p>
          </div>
        </div>

        {/* CTA doble: pagar ya o preguntar */}
        <div className="mt-5 space-y-2.5">
          <a href={payHref}
            className="flex items-center justify-center gap-2 rounded-xl px-6 py-4 text-base font-extrabold text-white shadow-lg transition-transform hover:brightness-110 active:scale-[0.98]"
            style={{ background: "var(--brand-accent)" }}>
            Empezar hoy por 1 € →
          </a>
          {/* La MISMA oferta, en 2 pagos: para quien prefiere dejarlo cerrado. */}
          <a href={pay2Href}
            className="block rounded-xl bg-white/95 px-5 py-3 text-center shadow-md transition-transform hover:brightness-105 active:scale-[0.98]">
            <span className="block text-sm font-extrabold">
              ¿Lo prefieres en solo 2 pagos? 120,50 € hoy y 120,50 € en un mes →
            </span>
            <span className="mt-0.5 block text-[12px] opacity-70">
              Mismo programa y mismo total. Tras el segundo pago no se te cobra
              nada más: se detiene solo.
            </span>
          </a>
          {waHref && (
            <a href={waHref} target="_blank" rel="noopener"
              className="flex items-center justify-center gap-2 rounded-xl px-6 py-3.5 text-sm font-bold text-white shadow-md transition-transform hover:brightness-110 active:scale-[0.98]"
              style={{ background: "#25D366" }}>
              <MessageCircle size={16} /> Tengo dudas — escríbeme
            </a>
          )}
        </div>

        {/* Cómo funciona, en 3 pasos */}
        <div className="mt-6 rounded-2xl bg-white/95 p-5 shadow-sm">
          <p className="text-center text-sm font-extrabold uppercase tracking-wide opacity-70">
            Así empieza tu cambio
          </p>
          <div className="mt-3 space-y-3 text-sm">
            {[
              ["1", "Pagas 1 € y ya estás dentro", "Pago seguro con Stripe. Al momento recibes tu acceso y tu cuestionario inicial."],
              ["2", "Estudio tu caso a fondo", "Salud, lesiones, gustos, horarios y material: de ahí sale TU plan, no una plantilla."],
              ["3", "Empezamos y te acompaño a diario", "Tu plan en tu app y yo contigo cada día por WhatsApp, ajustando según tu progreso real."],
            ].map(([n, titulo, texto]) => (
              <div key={n} className="flex gap-3">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm font-extrabold text-white"
                  style={{ background: "var(--brand-accent-2)" }}>
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

        <p className="mt-6 text-center text-xs text-white/60"
          style={{ textShadow: "0 1px 3px rgba(0,0,0,0.6)" }}>
          Pago seguro con Stripe · Programa de 3 meses (1 € + 120 € + 120 €) ·
          El cobro se detiene solo · Te respondo personalmente
        </p>
      </div>
    </div>
  );
}
