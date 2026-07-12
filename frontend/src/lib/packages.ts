/** Paquetes/planes DQR: qué incluye cada uno y cómo se adapta la app.
 *  Fuente única de capacidades para la web del coach y (más adelante) el portal.
 *
 *  - start: solo nutrición. Portal y planificación solo de dieta. Entrega email.
 *  - full:  nutrición + entreno. Sin contacto directo. Entrega email.
 *  - pro:   full + contacto directo (WhatsApp + videollamada). Entrega WhatsApp.
 */
import type { PackageTier } from "../types";

export interface PackageInfo {
  tier: PackageTier;
  label: string; // "DQR Start"
  short: string; // "Start"
  tagline: string; // "solo dieta"
  includes: string; // resumen de qué incluye (para el selector del alta)
  hasTraining: boolean; // incluye entrenamiento
  directContact: boolean; // WhatsApp directo + videollamada
  delivery: "email" | "whatsapp"; // vía por defecto para enviar plan/feedback
  color: string; // color de la etiqueta
}

export const PACKAGES: Record<PackageTier, PackageInfo> = {
  start: {
    tier: "start",
    label: "DQR Start",
    short: "Start",
    tagline: "solo dieta",
    includes: "Solo nutrición: dieta, revisión y portal. Entrega por email.",
    hasTraining: false,
    directContact: false,
    delivery: "email",
    color: "#4A7BA8",
  },
  full: {
    tier: "full",
    label: "DQR Full",
    short: "Full",
    tagline: "dieta + entreno",
    includes: "Dieta + entrenamiento completos. Sin contacto directo. Entrega por email.",
    hasTraining: true,
    directContact: false,
    delivery: "email",
    color: "#8B1A2B",
  },
  pro: {
    tier: "pro",
    label: "DQR Pro",
    short: "Pro",
    tagline: "acompañamiento directo",
    includes: "Todo lo de Full + WhatsApp directo y videollamada de revisión.",
    hasTraining: true,
    directContact: true,
    delivery: "whatsapp",
    color: "#E8833A",
  },
};

export const PACKAGE_ORDER: PackageTier[] = ["start", "full", "pro"];

/** Info del paquete de un cliente. Sin plan conocido → 'pro' (sistema completo). */
export function pkg(tier: string | null | undefined): PackageInfo {
  return PACKAGES[(tier as PackageTier)] ?? PACKAGES.pro;
}
