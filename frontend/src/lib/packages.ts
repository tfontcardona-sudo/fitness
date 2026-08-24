/** Planes DQR: qué incluye cada uno y cómo se adapta la app.
 *  ESPEJO de backend/app/services/packages.py — si cambias uno, cambia el otro.
 *
 *  Los tres comparten la MISMA maquinaria interna (anamnesis → plan → portal →
 *  seguimiento → revisión); solo cambian los servicios:
 *   - nutri: solo nutrición.
 *   - train: solo entrenamiento.
 *   - full:  las dos cosas + videollamada de revisión.
 *
 *  El WhatsApp diario está en los TRES: es el canal con el cliente, no un extra.
 */
import type { BillingPeriod, PackageTier, PublicBillingPeriod } from "../types";

export interface PackageInfo {
  tier: PackageTier;
  label: string; // "DQR Nutri"
  short: string; // "Nutri"
  tagline: string; // "solo nutrición"
  includes: string; // resumen de qué incluye (para el selector del alta)
  hasNutrition: boolean; // incluye dieta
  hasTraining: boolean; // incluye entrenamiento
  directContact: boolean; // WhatsApp diario (los tres)
  hasVideoCall: boolean; // videollamada de revisión (solo full)
  delivery: "email" | "whatsapp"; // vía por defecto para enviar plan/feedback
  /** Precio de referencia al mes (€). El COBRO real lo fija Stripe. */
  priceMonthEur: number;
  color: string; // color de la etiqueta
}

export const PACKAGES: Record<PackageTier, PackageInfo> = {
  train: {
    tier: "train",
    label: "DQR Train",
    short: "Train",
    tagline: "solo entrenamiento",
    includes: "Entrenamiento completo + WhatsApp diario. Sin plan de dieta.",
    hasNutrition: false,
    hasTraining: true,
    directContact: true,
    hasVideoCall: false,
    delivery: "whatsapp",
    priceMonthEur: 69,
    color: "#4A7BA8",
  },
  nutri: {
    tier: "nutri",
    label: "DQR Nutri",
    short: "Nutri",
    tagline: "solo nutrición",
    includes: "Plan de nutrición completo + WhatsApp diario. Sin entrenamiento.",
    hasNutrition: true,
    hasTraining: false,
    directContact: true,
    hasVideoCall: false,
    delivery: "whatsapp",
    priceMonthEur: 79,
    color: "#8B1A2B",
  },
  full: {
    tier: "full",
    label: "DQR Full",
    short: "Full",
    tagline: "nutrición + entrenamiento",
    includes:
      "Nutrición y entrenamiento + WhatsApp diario + videollamada de revisión.",
    hasNutrition: true,
    hasTraining: true,
    directContact: true,
    hasVideoCall: true,
    delivery: "whatsapp",
    priceMonthEur: 129,
    color: "#E8833A",
  },
};

export const PACKAGE_ORDER: PackageTier[] = ["train", "nutri", "full"];

/** Nombres antiguos → nuevos (espejo de LEGACY_TIERS del backend). */
const LEGACY: Record<string, PackageTier> = { start: "nutri", pro: "full" };

/** Info del paquete de un cliente. Traduce los nombres antiguos; por defecto full. */
export function pkg(tier: string | null | undefined): PackageInfo {
  const t = (tier ?? "").trim().toLowerCase();
  return PACKAGES[(LEGACY[t] ?? t) as PackageTier] ?? PACKAGES.full;
}

/** Duraciones contratables de cada plan (cada una con su precio en Stripe).
 *  La OFERTA va aparte (no es una duración pública del conmutador de /planes). */
export const BILLING_PERIODS: { value: PublicBillingPeriod; label: string }[] = [
  { value: "1m", label: "Mensual" },
  { value: "3m", label: "Trimestral" },
  { value: "6m", label: "Semestral" },
];

/** Oferta de captación (solo plan Full): 1 € el primer mes → 120 €/mes en
 *  SUSCRIPCIÓN de Stripe (renovación automática). Espejo de las constantes
 *  OFFER_* de backend/app/services/stripe_service.py. */
export const OFFER_PERIOD: BillingPeriod = "oferta";
export const OFFER_FIRST_EUR = 1;
export const OFFER_MONTHLY_EUR = 120;

/** La MISMA oferta en 2 pagos: 120,50 € hoy y 120,50 € al mes (total 241 €,
 *  igual que 1 + 120 + 120). La suscripción se cancela sola al segundo cobro. */
export const OFFER2_PERIOD: BillingPeriod = "oferta2";
export const OFFER2_EACH_EUR = 120.5;
export const OFFER2_CHARGES = 2;

/** Etiqueta de una duración ("1m" → "Mensual"). Desconocida → mensual. */
export function billingLabel(period: string | null | undefined): string {
  if (period === OFFER_PERIOD) return "Oferta 1 €";
  if (period === OFFER2_PERIOD) return "Oferta 2 pagos";
  return BILLING_PERIODS.find((b) => b.value === period)?.label ?? "Mensual";
}
