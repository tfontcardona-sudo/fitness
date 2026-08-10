/** Planes de la asesoría: qué incluye cada uno y cómo se adapta la app.
 *  ESPEJO de backend/app/services/packages.py — si cambias uno, cambia el otro.
 *
 *  Catálogo REAL de la marca (professionalgirona.com):
 *   - full  → Génesis.99 (99 €/mes): preparación personal completa, ONLINE.
 *   - train → Entreno Personal: sesiones presenciales (tarifas por hora/pack
 *     en branding.PT_RATES); se cobran en el centro, sin pago online.
 *   - nutri → interno (la marca no vende nutrición suelta).
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
import { FEATURE_VIDEO_CALLS } from "./branding";

export interface PackageInfo {
  tier: PackageTier;
  label: string; // "Professional Nutri"
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
    label: "Entreno Personal",
    short: "Entreno",
    tagline: "sesiones presenciales en el centro",
    includes: "Sesiones 1:1 en el centro + rutina y progreso en la app. Sin plan de dieta.",
    hasNutrition: false,
    hasTraining: true,
    directContact: true,
    hasVideoCall: false,
    delivery: "whatsapp",
    priceMonthEur: 0, // se cobra por sesión/pack en el centro (branding.PT_RATES)
    color: "#37474F",
  },
  nutri: {
    tier: "nutri",
    label: "Plan Nutrición",
    short: "Nutrición",
    tagline: "solo nutrición (uso interno)",
    includes: "Plan de nutrición completo + WhatsApp diario. Sin entrenamiento.",
    hasNutrition: true,
    hasTraining: false,
    directContact: true,
    hasVideoCall: false,
    delivery: "whatsapp",
    priceMonthEur: 79, // interno: la marca no lo vende suelto
    color: "#5C7A3A",
  },
  full: {
    tier: "full",
    label: "Génesis.99",
    short: "Génesis",
    tagline: "preparación personal: nutrición + entrenamiento",
    includes:
      "Nutrición y entrenamiento + WhatsApp diario + revisión quincenal.",
    hasNutrition: true,
    hasTraining: true,
    directContact: true,
    // La videollamada solo existe si la instancia la tiene encendida.
    hasVideoCall: FEATURE_VIDEO_CALLS,
    delivery: "whatsapp",
    priceMonthEur: 99,
    color: "#E9A90F",
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

/** Etiqueta de una duración ("1m" → "Mensual"). Desconocida → mensual. */
export function billingLabel(period: string | null | undefined): string {
  if (period === OFFER_PERIOD) return "Oferta 1 €";
  return BILLING_PERIODS.find((b) => b.value === period)?.label ?? "Mensual";
}
