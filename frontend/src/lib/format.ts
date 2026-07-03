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

// Color de acento por estado (para badges y puntos). Tonos sobrios sobre fondo oscuro.
export const STATUS_TONE: Record<ClientStatus, string> = {
  onboarding: "#8B9DF7", // índigo suave: aún configurándose
  active: "#6EE7B7", // acento de marca: todo en marcha
  awaiting_feedback: "#F7C96E", // ámbar: requiere acción próxima
  at_risk: "#F77E7E", // rojo: atención
  review_pending: "#C99EF7", // violeta: en cola del coach
  inactive: "#6B6B76", // gris: dormido
};

export const GOAL_LABEL: Record<GoalType, string> = {
  fat_loss: "Pérdida de grasa",
  muscle_gain: "Ganancia muscular",
  recomp: "Recomposición",
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

export const DIET_LABEL: Record<DietMode, string> = {
  flexible_7: "Flexible (7 opciones)",
  strict: "Estricta",
};

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" });
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
