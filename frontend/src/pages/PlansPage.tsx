import { useState } from "react";
import { Loader2, X } from "lucide-react";
import { api } from "../lib/api";
import { BILLING_PERIODS, PACKAGES, PACKAGE_ORDER, billingLabel } from "../lib/packages";
import type { BillingPeriod, PackageTier } from "../types";

/**
 * Página PÚBLICA de planes (registro personal del cliente). El cliente elige la
 * duración (mensual/trimestral/semestral) y el plan, deja sus datos (nombre,
 * email y teléfono) y: (1) se crea su ficha en el sistema, (2) recibe por email
 * su anamnesis (PDF editable) y (3) va directo a la pantalla de pago de Stripe.
 * El webhook marca el pago; la anamnesis subida se ingiere sola.
 */
export default function PlansPage() {
  const [period, setPeriod] = useState<BillingPeriod>("1m");
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
                  className="mt-4 rounded-xl px-4 py-3 text-sm font-semibold text-white transition-transform active:scale-[0.98]"
                  style={{ background: p.color }}
                >
                  Contratar y pagar
                </button>
              </div>
            );
          })}
        </div>
        )}

        <p className="mt-8 text-center text-xs opacity-50">
          Pago seguro con Stripe. El precio de cada plan se muestra en la pantalla de pago.
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
