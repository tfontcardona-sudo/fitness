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

/** Curva de peso del Resumen del cliente, EN SU PROPIO MÓDULO.
 *
 *  recharts pesa ~106 KB gzip y, como import estático, bajaba al abrir
 *  CUALQUIER ficha aunque el coach no pasara por el Resumen. Aquí solo baja
 *  cuando la gráfica se pinta de verdad.
 */
export default function GraficaPesoCoach({ series, accent, goalKg }: {
  series: { label: string; peso: number }[];
  accent: string;
  goalKg?: number | null;
}) {
  return (
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
        {goalKg != null && (
          <ReferenceLine
            y={goalKg}
            stroke={accent}
            strokeDasharray="4 4"
            strokeOpacity={0.5}
            label={{ value: "Objetivo", fill: "#6E6455", fontSize: 11, position: "right" }}
          />
        )}
        <Area type="monotone" dataKey="peso" stroke={accent} strokeWidth={2} fill="url(#pesoFill)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}
