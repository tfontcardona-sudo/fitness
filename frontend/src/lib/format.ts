/**
 * Utilidades de presentación compartidas.
 *
 * Mapas de etiquetas en castellano (todo lo de cara al usuario va en español),
 * formateadores de fecha/número y helpers de color de estado. Centralizar esto
 * evita que cada vista invente sus propias traducciones.
 */

import type { ClientStatus, DietMode, GoalType, Level, TrainingPlace } from "../types";

export const STATUS_LABEL: Record<ClientStatus, string> = {
  onboarding: "Onboarding",
  active: "Activo",
  awaiting_feedback: "Esperando cierre",
  at_risk: "En riesgo",
  review_pending: "Revisión pendiente",
  inactive: "Inactivo",
};

// Color de acento por estado (para badges y puntos). Tonos con contraste sobre crema.
export const STATUS_TONE: Record<ClientStatus, string> = {
  onboarding: "#4C66C9", // índigo: aún configurándose
  active: "#C96A1E", // naranja marca (oscurecido para texto): todo en marcha
  awaiting_feedback: "#9A6B15", // ámbar: requiere acción próxima
  at_risk: "#C2453A", // rojo: atención
  review_pending: "#7B4FC9", // violeta: en cola del coach
  inactive: "#8B8172", // gris cálido: dormido
};

export const GOAL_LABEL: Record<GoalType, string> = {
  fat_loss: "Pérdida de grasa",
  muscle_gain: "Ganancia muscular",
  recomp: "Recomposición",
  maintenance: "Mantenimiento",
  injury_recovery: "Recuperación de lesión",
};

export const LEVEL_LABEL: Record<Level, string> = {
  beginner: "Principiante",
  intermediate: "Intermedio",
  advanced: "Avanzado",
};

export const PLACE_LABEL: Record<TrainingPlace, string> = {
  gym: "Gimnasio",
  home: "Casa",
  outdoor: "Exterior",
};

export const ACTIVITY_LABEL: Record<string, string> = {
  sedentary: "Sedentaria (oficina)",
  light: "Ligera (de pie a ratos)",
  active: "Activa (trabajo físico)",
  very_active: "Muy activa (físico intenso)",
};

export const DIET_LABEL: Record<DietMode, string> = {
  flexible_7: "Flexible (7 opciones)",
  strict: "Estricta",
};

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" });
}

/** Mes natural en que se hizo el plan ("julio 2026") a partir de su fecha de
 *  activación (o creación). Es el TÍTULO de la planificación: el mes real, no
 *  el número de asesoría. Primera letra en mayúscula. */
export function planMonthLabel(iso: string | null | undefined): string {
  if (!iso) return "—";
  const s = new Date(iso).toLocaleDateString("es-ES", { month: "long", year: "numeric" });
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function relativeDays(iso: string | null | undefined): string {
  if (!iso) return "—";
  const diff = Math.round((Date.now() - new Date(iso).getTime()) / 86400000);
  if (diff === 0) return "hoy";
  if (diff === 1) return "ayer";
  if (diff < 0) return `en ${-diff} días`;
  return `hace ${diff} días`;
}

export function ageFrom(birthIso: string | null): number | null {
  if (!birthIso) return null;
  const b = new Date(birthIso);
  const now = new Date();
  let age = now.getFullYear() - b.getFullYear();
  const m = now.getMonth() - b.getMonth();
  if (m < 0 || (m === 0 && now.getDate() < b.getDate())) age--;
  return age;
}

export function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

// ---- Etapa del objetivo (45 días) ------------------------------------------
export const GOAL_REVIEW_DAYS = 45;

/** Días que lleva el cliente en su objetivo si TOCA valorarlo (≥45 y sin
 *  posponer reciente); null si aún no toca. */
export function goalReviewDue(c: {
  goal_started_on: string | null;
  goal_review_snoozed_on: string | null;
}): number | null {
  if (!c.goal_started_on) return null;
  const days = Math.floor((Date.now() - new Date(c.goal_started_on + "T00:00:00").getTime()) / 86400000);
  if (days < GOAL_REVIEW_DAYS) return null;
  if (c.goal_review_snoozed_on) {
    const sn = Math.floor((Date.now() - new Date(c.goal_review_snoozed_on + "T00:00:00").getTime()) / 86400000);
    if (sn < GOAL_REVIEW_DAYS) return null;
  }
  return days;
}

/** Días transcurridos en el objetivo actual (para mostrar "X días"). */
export function goalDays(c: { goal_started_on: string | null }): number | null {
  if (!c.goal_started_on) return null;
  return Math.floor((Date.now() - new Date(c.goal_started_on + "T00:00:00").getTime()) / 86400000);
}
