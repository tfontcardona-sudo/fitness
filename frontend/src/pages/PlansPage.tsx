import { useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";
import { api } from "../lib/api";
import { BILLING_PERIODS, PACKAGES, PACKAGE_ORDER, billingLabel } from "../lib/packages";
import type { BillingPeriod, PackageTier, PlanPricesOut } from "../types";

/** "49" o "49,50" — precios sin decimales de relleno. */
function euros(n: number): string {
  return (Number.isInteger(n) ? String(n) : n.toFixed(2).replace(".", ",")) + " €";
}

/**
 * Página PÚBLICA de planes (registro personal del cliente). El cliente elige la
 * duración (mensual/trimestral/semestral) y el plan, deja sus datos (nombre,
 * email y teléfono) y: (1) se crea su ficha en el sistema, (2) recibe por email
 * su anamnesis (PDF editable) y (3) va directo a la pantalla de pago de Stripe.
 * El webhook marca el pago; la anamnesis subida se ingiere sola.
 */
export default function PlansPage() {
  const [period, setPeriod] = useState<BillingPeriod>("1m");
  // Importes reales leídos de Stripe (total + equivalente al mes).
  const [prices, setPrices] = useState<PlanPricesOut | null>(null);
  // Marca pública: foto de fondo propia de esta página.
  const [landing, setLanding] = useState<import("../types").LandingOut | null>(null);
  // Plan elegido → abre el mini-formulario de datos antes del pago.
  const [formTier, setFormTier] = useState<PackageTier | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Registro hecho pero sin URL de pago (Stripe caído/incompleto): el email de
  // arranque ya lleva su enlace de pago, se lo decimos y no se pierde nada.
  const [registeredNoPay, setRegisteredNoPay] = useState(false);

  useEffect(() => {
    api.publicPlanPrices().then(setPrices).catch(() => setPrices(null));
    api.publicLanding().then(setLanding).catch(() => setLanding(null));
  }, []);

  /** % de ahorro del período elegido frente a pagar mes a mes. */
  function savingsPct(tier: PackageTier): number | null {
    const pr = prices?.tiers?.[tier]?.[period];
    const monthly = prices?.tiers?.[tier]?.["1m"];
    if (!pr || !monthly || pr.months <= 1 || monthly.per_month <= 0) return null;
    const pct = Math.round((1 - pr.per_month / monthly.per_month) * 100);
    return pct >= 3 ? pct : null;
  }

  function choose(tier: PackageTier) {
    setError(null);
    setFormTier(tier);
  }

  async function submit() {
    if (!formTier || busy) return;
    if (name.trim().length < 2 || !email.includes("@") || phone.trim().length < 6) {
      setError("Rellena tu nombre, un email válido y tu teléfono.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const r = await api.publicRegister({
        full_name: name.trim(), email: email.trim(), phone: phone.trim(),
        tier: formTier, period,
      });
      if (r.url) {
        window.location.href = r.url;
        return;
      }
      setRegisteredNoPay(true);
      setBusy(false);
    } catch (e: any) {
      setError(e?.message ?? "No se pudo completar el registro. Inténtalo de nuevo en un momento.");
      setBusy(false);
    }
  }

  return (
    <div className="relative" style={{ minHeight: "100vh", background: "#f6f1e7", color: "#26211a" }}>
      {/* Foto de fondo propia (Recursos → Página de enlaces → Foto de los
          planes) con velo crema para que todo se lea. */}
      {landing?.plans_photo_url && (
        <>
          <img src={landing.plans_photo_url} alt=""
            className="pointer-events-none fixed inset-0 h-full w-full object-cover" />
          <div className="pointer-events-none fixed inset-0"
            style={{ background: "linear-gradient(180deg, rgba(246,241,231,.62) 0%, rgba(246,241,231,.8) 45%, rgba(246,241,231,.9) 100%)" }} />
        </>
      )}
      <div className="relative mx-auto max-w-4xl px-5 py-10">
        {/* textShadow: halo claro alrededor del texto oscuro — se lee bien pase
            lo que pase debajo (foto clara, oscura, con textura...). */}
        <header className="mb-6 flex flex-col items-center text-center"
          style={{ textShadow: "0 0 14px #f6f1e7, 0 0 6px #f6f1e7, 0 1px 2px #f6f1e7" }}>
          <img src="/dq-logo.png" alt="" className="h-14 w-auto rounded-xl shadow-sm" />
          <h1 className="mt-4 text-3xl font-extrabold tracking-tight">
            Empieza tu cambio <span style={{ color: "#E8833A" }}>hoy</span>
          </h1>
          <p className="mt-1 max-w-lg text-sm opacity-80">
            Plan de dieta y entreno 100 % a tu medida, con seguimiento real de tu coach.
          </p>
          {/* Gancho de confianza: qué incluye SIEMPRE, de un vistazo */}
          <div className="mt-3 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-xs font-medium">
            <span style={{ color: "#2E7D46" }}>✓ Plan personalizado</span>
            <span style={{ color: "#2E7D46" }}>✓ Revisión quincenal</span>
            <span style={{ color: "#2E7D46" }}>✓ App de seguimiento</span>
            <span style={{ color: "#2E7D46" }}>✓ Pago seguro</span>
          </div>
        </header>

        {error && (
          <div className="mx-auto mb-5 max-w-lg rounded-xl border p-3 text-center text-sm"
            style={{ borderColor: "#C2453A", background: "#fdecea", color: "#8B1A2B" }}>
            {error}
          </div>
        )}

        {/* Duración: un conmutador común a los 3 planes (cada combinación tiene
            su precio en Stripe; se muestra en la pantalla de pago). */}
        <div className="mb-6 flex justify-center">
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

        {registeredNoPay ? (
          <div className="mx-auto max-w-lg rounded-2xl border bg-white p-6 text-center shadow-sm"
            style={{ borderColor: "#cfe3cf" }}>
            <h2 className="text-lg font-bold">¡Registro completado!</h2>
            <p className="mt-2 text-sm opacity-75">
              Revisa tu correo: te hemos enviado tu cuestionario inicial (anamnesis)
              y tu enlace de pago para terminar la contratación.
            </p>
          </div>
        ) : (
        <div className="grid gap-4 sm:grid-cols-3">
          {PACKAGE_ORDER.map((t) => {
            const p = PACKAGES[t];
            const destacado = t === "full"; // el equilibrio dieta+entreno: el más elegido
            const pr = prices?.tiers?.[t]?.[period];
            const ahorro = savingsPct(t);
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
                <p className="mt-3 text-sm font-medium">{p.tagline}</p>
                <p className="mt-1 flex-1 text-sm opacity-70">{p.includes}</p>
                {/* Precio REAL siempre visible (leído de Stripe): total del pago,
                    equivalente al mes y % de ahorro frente a mensual. */}
                {pr && (
                  // Precio en una sola línea (whitespace-nowrap: el € nunca
                  // salta de línea) y el ahorro alineado a la derecha.
                  <div className="mt-3 flex items-end justify-between gap-2">
                    <div className="min-w-0">
                      <p className="whitespace-nowrap text-3xl font-extrabold leading-none" style={{ color: p.color }}>
                        {euros(pr.total)}
                        <span className="ml-1 align-baseline text-xs font-medium opacity-60">
                          / {billingLabel(period).toLowerCase()}
                        </span>
                      </p>
                      {pr.months > 1 && (
                        <p className="mt-1 whitespace-nowrap text-xs font-semibold" style={{ color: "#2E7D46" }}>
                          sale a {euros(pr.per_month)} al mes
                        </p>
                      )}
                    </div>
                    {ahorro && (
                      <span className="shrink-0 whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-bold text-white"
                        style={{ background: "#2E7D46" }}>
                        Ahorra {ahorro}%
                      </span>
                    )}
                  </div>
                )}
                <button
                  onClick={() => choose(t)}
                  className="mt-4 rounded-xl px-4 py-3.5 text-sm font-bold text-white shadow-md transition-transform hover:brightness-110 active:scale-[0.98]"
                  style={{ background: p.color }}
                >
                  Empezar ahora →
                </button>
              </div>
            );
          })}
        </div>
        )}

        <p className="mt-8 text-center text-xs opacity-50">
          {prices
            ? "Pago seguro con Stripe."
            : "Pago seguro con Stripe. El precio de cada plan se muestra en la pantalla de pago."}
        </p>
      </div>

      {/* Mini-formulario previo al pago: nombre + email + teléfono. Con esto se
          crea la ficha, se envía la anamnesis por email y se va directo a Stripe. */}
      {formTier && !registeredNoPay && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-4 sm:items-center"
          onClick={() => !busy && setFormTier(null)}>
          <div className="w-full max-w-md rounded-2xl bg-white p-5 shadow-2xl"
            role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold">
                  {PACKAGES[formTier].label} · {billingLabel(period)}
                  {(() => {
                    const pr = prices?.tiers?.[formTier]?.[period];
                    return pr ? (
                      <span className="ml-2" style={{ color: PACKAGES[formTier].color }}>
                        {euros(pr.total)}
                      </span>
                    ) : null;
                  })()}
                </h2>
                <p className="mt-0.5 text-sm opacity-70">
                  Déjanos tus datos: te enviamos tu cuestionario inicial por email
                  y pasas directo al pago seguro.
                </p>
              </div>
              <button onClick={() => !busy && setFormTier(null)} aria-label="Cerrar"
                className="rounded-lg p-1.5 opacity-60 transition-colors hover:opacity-100">
                <X size={18} />
              </button>
            </div>

            <div className="mt-4 space-y-3">
              <input value={name} onChange={(e) => setName(e.target.value)} autoFocus
                placeholder="Nombre y apellidos"
                className="w-full rounded-xl border px-3.5 py-3 text-base outline-none focus:border-[#2E5E8C]"
                style={{ borderColor: "#cbbfa5" }} />
              <input value={email} onChange={(e) => setEmail(e.target.value)} type="email"
                placeholder="Tu email"
                className="w-full rounded-xl border px-3.5 py-3 text-base outline-none focus:border-[#2E5E8C]"
                style={{ borderColor: "#cbbfa5" }} />
              <input value={phone} onChange={(e) => setPhone(e.target.value)} type="tel"
                placeholder="Tu teléfono (WhatsApp)"
                className="w-full rounded-xl border px-3.5 py-3 text-base outline-none focus:border-[#2E5E8C]"
                style={{ borderColor: "#cbbfa5" }} />
            </div>

            {error && (
              <p className="mt-3 rounded-xl border p-3 text-center text-sm"
                style={{ borderColor: "#C2453A", background: "#fdecea", color: "#8B1A2B" }}>
                {error}
              </p>
            )}

            <button onClick={submit} disabled={busy}
              className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3.5 text-sm font-bold text-white transition-transform active:scale-[0.98] disabled:opacity-60"
              style={{ background: PACKAGES[formTier].color }}>
              {busy ? <><Loader2 size={16} className="animate-spin" /> Un momento…</> : "Continuar al pago"}
            </button>
            <p className="mt-3 text-center text-xs opacity-50">
              Usamos tus datos solo para gestionar tu asesoría.
            </p>
          </div>
        </div>
      )}
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
        réllenalo y súbelo desde el enlace del email para que preparemos tu plan.
        Revisa también la carpeta de spam.
      </p>
    </div>
  );
}
