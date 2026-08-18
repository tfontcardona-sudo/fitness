/** Planes de la asesoría: qué incluye cada uno y cómo se adapta la app.
 *  ESPEJO de backend/app/services/packages.py — si cambias uno, cambia el otro.
 *
 *  Catálogo REAL de la marca — los tres son de PAGO ÚNICO:
 *   - nutri → Dieta (70 €): plan de nutrición a medida.
 *   - train → Entrenamiento (70 €): plan de entrenamiento a medida.
 *   - full  → Pack completo (130 €): dieta + entrenamiento + cuota del gimnasio.
 *
 *  Los tres comparten la MISMA maquinaria (anamnesis → plan → portal →
 *  feedback); solo cambia qué se le entrega al cliente y qué ve en su portal.
 */
import type { BillingPeriod, PackageTier, PublicBillingPeriod } from "../types";

export interface PackageInfo {
  tier: PackageTier;
  label: string; // "Professional Nutri"
  short: string; // "Nutri"
  tagline: string; // "solo nutrición"
  includes: string; // resumen de qué incluye (para el selector del alta)
  hasNutrition: boolean; // incluye dieta
  hasTraining: boolean; // incluye entrenamiento
  /** Precio de referencia al mes (€). El COBRO real lo fija Stripe. */
  priceMonthEur: number;
  color: string; // color de la etiqueta
}

export const PACKAGES: Record<PackageTier, PackageInfo> = {
  train: {
    tier: "train",
    label: "Entrenamiento",
    short: "Entreno",
    tagline: "plan de entrenamiento a medida",
    includes: "Plan de entrenamiento a medida + app para registrar tus entrenos y tu evolución.",
    hasNutrition: false,
    hasTraining: true,
    priceMonthEur: 70, // PAGO ÚNICO
    color: "#37474F",
  },
  nutri: {
    tier: "nutri",
    label: "Dieta",
    short: "Dieta",
    tagline: "plan de nutrición a medida",
    includes: "Plan de nutrición a medida + app para registrar peso y medidas.",
    hasNutrition: true,
    hasTraining: false,
    priceMonthEur: 70, // PAGO ÚNICO
    color: "#5C7A3A",
  },
  full: {
    tier: "full",
    label: "Pack completo",
    short: "Pack",
    tagline: "dieta + entrenamiento + cuota del gimnasio",
    includes:
      "Dieta y entrenamiento a medida, la cuota del gimnasio incluida y la app con todo tu seguimiento.",
    hasNutrition: true,
    hasTraining: true,
    priceMonthEur: 130, // PAGO ÚNICO
    color: "#E9A90F",
  },
};

export const PACKAGE_ORDER: PackageTier[] = ["nutri", "train", "full"];

/** Nombres antiguos → nuevos (espejo de LEGACY_TIERS del backend). */
const LEGACY: Record<string, PackageTier> = { start: "nutri", pro: "full" };

/** Info del paquete de un cliente. Traduce los nombres antiguos; por defecto full. */
export function pkg(tier: string | null | undefined): PackageInfo {
  const t = (tier ?? "").trim().toLowerCase();
  return PACKAGES[(LEGACY[t] ?? t) as PackageTier] ?? PACKAGES.full;
}

/** Professional vende PAGO ÚNICO: una sola "duración" y sin conmutador. */
export const BILLING_PERIODS: { value: PublicBillingPeriod; label: string }[] = [
  { value: "unico", label: "Pago único" },
];

/** Oferta de captación (solo plan Full): 1 € el primer mes → 120 €/mes en
 *  SUSCRIPCIÓN de Stripe (renovación automática). Espejo de las constantes
 *  OFFER_* de backend/app/services/stripe_service.py. */
export const OFFER_PERIOD: BillingPeriod = "oferta";
export const OFFER_FIRST_EUR = 1;
export const OFFER_MONTHLY_EUR = 120;

/** Etiqueta de una duración. En esta marca todo es pago único. */
export function billingLabel(period: string | null | undefined): string {
  if (period === OFFER_PERIOD) return "Oferta 1 €";
  const legado: Record<string, string> = { "1m": "Mensual", "3m": "Trimestral", "6m": "Semestral" };
  return BILLING_PERIODS.find((b) => b.value === period)?.label
    ?? legado[period ?? ""] ?? "Pago único";
}
