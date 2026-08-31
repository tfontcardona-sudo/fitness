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

/** Gráfica de peso del portal, EN SU PROPIO MÓDULO.
 *
 *  recharts pesa ~106 KB gzip y entraba en la primera carga del portal por ser
 *  un import estático: el cliente que solo abre "Mi día" en el móvil se
 *  tragaba más de la mitad del JS de la app para nada. Aquí dentro, solo baja
 *  cuando de verdad se abre "Progreso".
 */
export default function GraficaPeso({ series, accent, accent2, goalKg }: {
  series: { label: string; kg: number }[];
  accent: string;
  accent2: string;
  goalKg?: number | null;
}) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={series} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="pesoPortal" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={accent} stopOpacity={0.35} />
            <stop offset="100%" stopColor={accent} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="var(--p-line)" vertical={false} />
        <XAxis dataKey="label" stroke="var(--p-ink-soft)" fontSize={11} tickLine={false} axisLine={false} minTickGap={24} interval="preserveStartEnd" />
        <YAxis stroke="var(--p-ink-soft)" fontSize={11} tickLine={false} axisLine={false} domain={["dataMin - 1", "dataMax + 1"]} width={30} allowDecimals={false} tickFormatter={(v) => `${Math.round(Number(v))}`} />
        <Tooltip
          formatter={(v: number | string) => [`${v} kg`, "Peso"]}
          contentStyle={{ background: "var(--p-card-top)", border: "1px solid var(--p-line)", borderRadius: 12, fontSize: 13, color: "var(--p-ink)" }}
          labelStyle={{ color: "var(--p-ink-soft)" }}
        />
        {goalKg != null && (
          <ReferenceLine y={goalKg} stroke={accent2} strokeDasharray="4 4" strokeOpacity={0.6}
            label={{ value: "Objetivo", fill: "var(--p-ink-soft)", fontSize: 11, position: "insideTopRight" }} />
        )}
        <Area type="monotone" dataKey="kg" stroke={accent} strokeWidth={2.5} fill="url(#pesoPortal)" />
      </AreaChart>
    </ResponsiveContainer>

  );
}
