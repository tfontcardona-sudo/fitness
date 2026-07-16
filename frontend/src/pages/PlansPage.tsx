import { useState } from "react";
import { api } from "../lib/api";
import { BILLING_PERIODS, PACKAGES, PACKAGE_ORDER } from "../lib/packages";
import type { BillingPeriod, PackageTier } from "../types";

/**
 * Página PÚBLICA de planes (registro personal del cliente). El cliente elige la
 * duración (mensual/trimestral/semestral) y el plan; se crea la sesión de pago
 * de Stripe de esa combinación y se le redirige. Al pagar, el webhook crea el
 * perfil del cliente y le envía el acceso a su portal.
 */
export default function PlansPage() {
  const [period, setPeriod] = useState<BillingPeriod>("1m");
  const [busy, setBusy] = useState<PackageTier | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function choose(tier: PackageTier) {
    if (busy) return;
    setBusy(tier);
    setError(null);
    try {
      const { url } = await api.publicCheckout(tier, period);
      window.location.href = url;
    } catch (e: any) {
      setError(e?.message ?? "No se pudo iniciar el pago. Inténtalo de nuevo en un momento.");
      setBusy(null);
    }
  }

  return (
    <div style={{ minHeight: "100vh", background: "#f6f1e7", color: "#26211a" }}>
      <div className="mx-auto max-w-4xl px-5 py-10">
        <header className="mb-8 flex flex-col items-center text-center">
          <img src="/dq-logo.png" alt="" className="h-14 w-auto rounded-xl shadow-sm" />
          <h1 className="mt-4 text-2xl font-bold">Elige tu plan</h1>
          <p className="mt-1 max-w-lg text-sm opacity-70">
            Escoge el acompañamiento que mejor encaje contigo. Tras el pago recibirás
            en tu correo el acceso a tu portal para empezar.
          </p>
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

        <div className="grid gap-4 sm:grid-cols-3">
          {PACKAGE_ORDER.map((t) => {
            const p = PACKAGES[t];
            const loading = busy === t;
            return (
              <div key={t} className="flex flex-col rounded-2xl border bg-white p-5 shadow-sm"
                style={{ borderColor: `color-mix(in srgb, ${p.color} 40%, #e6ddca)` }}>
                <span className="inline-flex w-fit items-center rounded-full px-2.5 py-0.5 text-xs font-semibold"
                  style={{ background: `color-mix(in srgb, ${p.color} 14%, transparent)`, color: p.color }}>
                  {p.label}
                </span>
                <p className="mt-3 text-sm font-medium">{p.tagline}</p>
                <p className="mt-1 flex-1 text-sm opacity-70">{p.includes}</p>
                <button
                  onClick={() => choose(t)}
                  disabled={busy != null}
                  className="mt-4 rounded-xl px-4 py-3 text-sm font-semibold text-white transition-transform active:scale-[0.98] disabled:opacity-60"
                  style={{ background: p.color }}
                >
                  {loading ? "Redirigiendo a pago…" : "Contratar y pagar"}
                </button>
              </div>
            );
          })}
        </div>

        <p className="mt-8 text-center text-xs opacity-50">
          Pago seguro con Stripe. El precio de cada plan se muestra en la pantalla de pago.
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
        Gracias. En unos minutos recibirás en tu correo el acceso a tu portal para
        rellenar tu cuestionario inicial y empezar. Revisa también la carpeta de spam.
      </p>
    </div>
  );
}
