import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../lib/api";
import type { ClientOut } from "../types";
import { EmptyState } from "./ui";
import { formatDate } from "../lib/format";

/**
 * Tab Resumen: KPIs del cliente y evolución de peso hacia el objetivo.
 *
 * En Fase 5 el historial de períodos/logs aún no se expone por API (llega en
 * Fase 6 con el portal y los cierres), así que la gráfica usa los anclajes
 * disponibles: peso inicial → peso actual → objetivo. La estructura queda lista
 * para alimentarse de la serie real de períodos cuando exista.
 */
export function ClientSummaryTab({ client }: { client: ClientOut }) {
  const [history, setHistory] = useState<Awaited<ReturnType<typeof api.getClientHistory>> | null>(null);

  useEffect(() => {
    api.getClientHistory(client.id).then(setHistory).catch(() => setHistory(null));
  }, [client.id]);

  // Peso actual real: del historial (último cierre/registro), no del campo fijo.
  const currentWeight = history?.current_weight_kg ?? client.current_weight_kg ?? null;

  // Curva real: peso inicial + el cierre de cada período.
  const series = useMemo(() => {
    const pts: { label: string; peso: number }[] = [];
    if (client.start_weight_kg != null) pts.push({ label: "Inicio", peso: client.start_weight_kg });
    (history?.periods ?? []).forEach((p) => {
      if (p.closing_weight_kg != null) pts.push({ label: `P${p.period_index}`, peso: p.closing_weight_kg });
    });
    if (pts.length === 1 && currentWeight != null && currentWeight !== client.start_weight_kg)
      pts.push({ label: "Actual", peso: currentWeight });
    return pts;
  }, [client.start_weight_kg, history, currentWeight]);

  const accent = getComputedStyle(document.documentElement)
    .getPropertyValue("--brand-accent")
    .trim() || "#E8833A";

  return (
    <div className="space-y-5">
      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Kpi label="Peso inicial" value={client.start_weight_kg} unit="kg" />
        <Kpi label="Peso actual" value={currentWeight} unit="kg" />
        <Kpi label="Objetivo" value={client.goal_weight_kg} unit="kg" />
        <Kpi
          label="Diferencia"
          value={
            currentWeight != null && client.start_weight_kg != null
              ? Number((currentWeight - client.start_weight_kg).toFixed(1))
              : null
          }
          unit="kg"
          signed
          // Bajar solo es "bueno" si el objetivo es perder; en ganancia
          // muscular el color se invierte (subir = progreso).
          lowerBetter={client.goal_type !== "muscle_gain"}
        />
      </div>

      {/* Gráfica de peso */}
      <div className="card p-5">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-zinc-200">Evolución de peso</h3>
          {client.goal_deadline && (
            <span className="text-xs text-zinc-500">Objetivo para {formatDate(client.goal_deadline)}</span>
          )}
        </div>

        {series.length < 2 ? (
          <EmptyState
            title="Aún no hay datos de seguimiento"
            hint="La curva de peso se construirá con los cierres de período del cliente."
          />
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={series} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <defs>
                  <linearGradient id="pesoFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={accent} stopOpacity={0.25} />
                    <stop offset="100%" stopColor={accent} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(38,33,26,0.08)" vertical={false} />
                <XAxis dataKey="label" stroke="#8B8172" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#8B8172" fontSize={12} tickLine={false} axisLine={false} domain={["dataMin - 2", "dataMax + 2"]} />
                <Tooltip
                  contentStyle={{
                    background: "#fffdf9",
                    border: "1px solid rgba(38,33,26,0.15)",
                    borderRadius: 12,
                    fontSize: 13,
                  }}
                  labelStyle={{ color: "#6E6455" }}
                />
                {client.goal_weight_kg != null && (
                  <ReferenceLine
                    y={client.goal_weight_kg}
                    stroke={accent}
                    strokeDasharray="4 4"
                    strokeOpacity={0.5}
                    label={{ value: "Objetivo", fill: "#6E6455", fontSize: 11, position: "right" }}
                  />
                )}
                <Area type="monotone" dataKey="peso" stroke={accent} strokeWidth={2} fill="url(#pesoFill)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Notas clínicas: SOLO lo relevante (los "no/ninguna" fuera), por
          secciones separadas y con el color de cada área. */}
      <ClinicalNotesCard client={client} />
    </div>
  );
}

// Línea IRRELEVANTE (negación pura): "No refiere…", "Anticonceptivos: no.",
// "Sin alergias", "no aplica". OJO: "lesión no resuelta" SÍ es relevante.
const IRRELEVANT_LINE = /^(no|sin|ninguna?)\b|:\s*no\.?$|no aplica|\bniega\b/i;

const NOTE_SECTIONS: { label: string; color: string; get: (c: ClientOut) => string | null | undefined }[] = [
  { label: "Lesiones", color: "#B3261E", get: (c) => c.injuries_notes },
  { label: "Patologías y salud", color: "#9A6B15", get: (c) => c.medical_notes },
  { label: "Medicación", color: "#3D6E9E", get: (c) => c.medication_notes },
  { label: "Alergias e intolerancias", color: "#B3261E", get: (c) => c.food_allergies?.length ? c.food_allergies.join(", ") : null },
];

function ClinicalNotesCard({ client }: { client: ClientOut }) {
  const sections = NOTE_SECTIONS
    .map((s) => ({
      ...s,
      items: toBullets(s.get(client) ?? "").filter((l) => !IRRELEVANT_LINE.test(l.trim())),
    }))
    .filter((s) => s.items.length > 0);
  if (!sections.length) return null;
  return (
    <div className="card p-5">
      <h3 className="mb-1 text-sm font-semibold text-zinc-200">Notas clínicas</h3>
      <p className="mb-3 text-xs text-zinc-500">Solo lo relevante para el plan; el resto queda en la anamnesis.</p>
      <div className="space-y-3 text-sm">
        {sections.map((s) => (
          <div
            key={s.label}
            className="rounded-lg border-l-2 px-3 py-2.5"
            style={{ background: "var(--surface-raised)", borderLeftColor: s.color }}
          >
            <p
              className="mb-1 inline-block rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide"
              style={{ background: `color-mix(in srgb, ${s.color} 14%, transparent)`, color: s.color }}
            >
              {s.label}
            </p>
            <ul className="list-disc space-y-0.5 pl-5 text-zinc-300">
              {s.items.map((it, i) => <li key={i}>{it}</li>)}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

function Kpi({
  label,
  value,
  unit,
  signed,
  lowerBetter = true,
}: {
  label: string;
  value: number | null | undefined;
  unit: string;
  signed?: boolean;
  lowerBetter?: boolean;
}) {
  const display =
    value == null ? "—" : `${signed && value > 0 ? "+" : ""}${value} ${unit}`;
  const improving = value != null && (lowerBetter ? value < 0 : value > 0);
  const tone = signed && value != null && value !== 0 ? (improving ? "#E8833A" : "#9A6B15") : undefined;
  return (
    <div className="card p-4">
      <p className="text-xl font-semibold" style={{ color: tone ?? "#26211A" }}>
        {display}
      </p>
      <p className="mt-0.5 text-xs text-zinc-500">{label}</p>
    </div>
  );
}

/** Convierte una nota (prosa o líneas con "- ") en puntos para verla ordenada. */
function toBullets(text: string): string[] {
  const t = (text ?? "").trim();
  if (!t) return [];
  // 1) Si ya viene en líneas (formato en puntos de la IA): una por línea.
  let parts = t.split(/\n+/).map((s) => s.replace(/^[-•*]\s*/, "").trim()).filter(Boolean);
  if (parts.length > 1) return parts;
  // 2) Prosa: divide por frases ("… . Siguiente" / "… ; Siguiente").
  parts = t.split(/(?<=[.;])\s+(?=[A-ZÁÉÍÓÚÑ¿¡])/).map((s) => s.trim()).filter(Boolean);
  return parts;
}

