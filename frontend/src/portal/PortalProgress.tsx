import { useEffect, useState } from "react";
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
import { CameraOff, Dumbbell, LineChart, Ruler, Sparkles } from "lucide-react";
import type { PortalBrand, PortalProgress as Progress } from "../types";
import { portalApi, PortalError } from "./portalApi";

type Api = ReturnType<typeof portalApi>;

/**
 * "Mi progreso": la pantalla que el propio cliente ve para comprobar que avanza
 * (el mayor motor de motivación y de que siga con la asesoría). Reúne lo que ya
 * registra: peso, medidas, adherencia, fuerza y sus fotos antes/ahora. Solo
 * lectura y solo lo suyo (autenticado por su token).
 */
export function PortalProgress({ api, brand }: { api: Api; brand: PortalBrand }) {
  const [data, setData] = useState<Progress | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .progress()
      .then(setData)
      .catch((e) => setErr(e instanceof PortalError ? e.message : "No se pudo cargar tu progreso"));
  }, [api]);

  if (err) return <div className="portal-card p-4 text-sm opacity-80">{err}</div>;
  if (!data) {
    return (
      <div className="flex justify-center py-16">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-current border-t-transparent opacity-40" />
      </div>
    );
  }

  const accent = brand.color_primary;
  const accent2 = brand.color_secondary;
  const w = data.weight;
  const series = w.series.map((p) => ({ label: shortDate(p.d), kg: p.kg }));
  const hasWeight = series.length >= 2;   // la GRÁFICA necesita ≥2 puntos
  const anyWeight = series.length >= 1;   // con 1 ya se muestra "Peso ahora"
  const bestLift = data.strength[0] ?? null;
  const meanAdh = adherenceMean(data.adherence);

  // "Vacío" solo si NO hay NINGÚN dato: con un único peso del día 1 ya se enseñan
  // las cajas (antes pedía registrar un peso que el cliente ya había puesto).
  const empty =
    !anyWeight &&
    data.measurements.length === 0 &&
    data.adherence.length === 0 &&
    data.strength.length === 0 &&
    data.photos.first.length === 0;

  if (empty) {
    return (
      <div className="portal-card p-6 text-center">
        <Sparkles size={26} className="mx-auto mb-2" style={{ color: accent }} />
        <p className="text-base font-semibold">Aquí verás cómo avanzas</p>
        <p className="mx-auto mt-1 max-w-xs text-sm opacity-70">
          En cuanto registres tu <b>peso</b> en el Diario y subas tus <b>fotos</b> en la revisión
          quincenal, esta pantalla te mostrará tu evolución.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Titulares: lo que quieres ver de un vistazo */}
      <div className="grid grid-cols-2 gap-2">
        <Stat
          accent={accent2}
          label="Peso ahora"
          value={w.current_kg != null ? `${round1(w.current_kg)} kg` : "—"}
          sub={deltaLabel(w.delta_kg)}
        />
        <Stat
          accent={accent2}
          label="Objetivo"
          value={w.goal_kg != null ? `${round1(w.goal_kg)} kg` : "—"}
          sub={toGoalLabel(w.current_kg, w.goal_kg)}
        />
        {bestLift && (
          <Stat
            accent={accent}
            label="Fuerza (mejor)"
            value={`+${bestLift.gain_pct}%`}
            sub={truncate(bestLift.exercise, 18)}
          />
        )}
        {meanAdh != null && (
          <Stat accent={accent} label="Constancia" value={`${meanAdh}/10`} sub="media de tus quincenas" />
        )}
      </div>

      {/* Peso: gráfica */}
      {hasWeight && (
        <section className="portal-card p-3">
          <Header icon={LineChart} title="Tu peso" />
          <div className="h-52">
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
                {w.goal_kg != null && (
                  <ReferenceLine y={w.goal_kg} stroke={accent2} strokeDasharray="4 4" strokeOpacity={0.6}
                    label={{ value: "Objetivo", fill: "var(--p-ink-soft)", fontSize: 11, position: "insideTopRight" }} />
                )}
                <Area type="monotone" dataKey="kg" stroke={accent} strokeWidth={2.5} fill="url(#pesoPortal)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          {w.weekly_rate_kg != null && Math.abs(w.weekly_rate_kg) >= 0.01 && (
            <p className="mt-1 text-center text-xs opacity-60">
              Ritmo: {w.weekly_rate_kg < 0 ? "−" : "+"}
              {Math.abs(w.weekly_rate_kg)} kg por semana
            </p>
          )}
        </section>
      )}

      {/* Fuerza: lo que más motiva ver subir */}
      {data.strength.length > 0 && (
        <section className="portal-card p-4">
          <Header icon={Dumbbell} title="Tu fuerza sube" />
          <div className="space-y-2">
            {data.strength.map((s) => (
              <div key={s.exercise} className="flex items-center justify-between gap-2 text-sm">
                <span className="min-w-0 flex-1 truncate">{s.exercise}</span>
                <span className="tabular-nums opacity-60">{round1(s.first_e1rm)} → {round1(s.best_e1rm)} kg</span>
                <span className="rounded-full px-2 py-0.5 text-xs font-semibold tabular-nums"
                  style={{ background: "color-mix(in srgb, var(--p-accent) 16%, transparent)", color: "var(--p-accent)" }}>
                  +{s.gain_pct}%
                </span>
              </div>
            ))}
          </div>
          <p className="mt-2 text-xs opacity-55">Estimación de tu fuerza máxima (1RM) según lo que registras en Entreno.</p>
        </section>
      )}

      {/* Medidas por quincena */}
      {data.measurements.length > 0 && (
        <section className="portal-card p-4">
          <Header icon={Ruler} title="Tus medidas" />
          <div className="-mx-1 overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="opacity-55">
                  <th className="px-1 py-1 text-left font-medium">Fecha</th>
                  <th className="px-1 py-1 text-right font-medium">Peso</th>
                  <th className="px-1 py-1 text-right font-medium">Cintura</th>
                  <th className="px-1 py-1 text-right font-medium">Cadera</th>
                  <th className="px-1 py-1 text-right font-medium">Brazo</th>
                  <th className="px-1 py-1 text-right font-medium">Muslo</th>
                </tr>
              </thead>
              <tbody>
                {data.measurements.map((m) => (
                  <tr key={m.label} className="border-t" style={{ borderColor: "var(--p-line)" }}>
                    <td className="px-1 py-1.5">{shortDate(m.label)}</td>
                    <td className="px-1 py-1.5 text-right tabular-nums">{cell(m.weight_kg, "kg")}</td>
                    <td className="px-1 py-1.5 text-right tabular-nums">{cell(m.waist_cm)}</td>
                    <td className="px-1 py-1.5 text-right tabular-nums">{cell(m.hip_cm)}</td>
                    <td className="px-1 py-1.5 text-right tabular-nums">{cell(m.arm_cm)}</td>
                    <td className="px-1 py-1.5 text-right tabular-nums">{cell(m.thigh_cm)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-xs opacity-55">Medidas en cm. Bajar de cintura suele indicar pérdida de grasa aunque el peso se mueva poco.</p>
        </section>
      )}

      {/* Fotos antes / ahora */}
      {data.photos.first.length > 0 && (
        <section className="portal-card p-4">
          <Header icon={undefined} title="Antes y ahora" />
          {data.photos.last.length > 0 ? (
            <div className="grid grid-cols-2 gap-3">
              <PhotoColumn api={api} title="Antes" date={data.photos.first_date} photos={data.photos.first} />
              <PhotoColumn api={api} title="Ahora" date={data.photos.last_date} photos={data.photos.last} />
            </div>
          ) : (
            <>
              <PhotoColumn api={api} title="Tus fotos" date={data.photos.first_date} photos={data.photos.first} wide />
              <p className="mt-2 flex items-center gap-1.5 text-xs opacity-60">
                <CameraOff size={13} /> Sube fotos en tu próxima revisión quincenal para verte "antes / ahora".
              </p>
            </>
          )}
        </section>
      )}
    </div>
  );
}

// -------------------------------------------------------------- subcomponentes
function Stat({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent: string }) {
  return (
    <div className="portal-card p-3">
      <p className="text-[11px] uppercase tracking-wide opacity-55">{label}</p>
      <p className="mt-0.5 text-xl font-bold tabular-nums" style={{ color: accent }}>{value}</p>
      {sub && <p className="mt-0.5 text-xs opacity-60">{sub}</p>}
    </div>
  );
}

function Header({ icon: Icon, title }: { icon?: typeof Dumbbell; title: string }) {
  return (
    <div className="mb-2 flex items-center gap-2">
      {Icon && <Icon size={16} style={{ color: "var(--p-accent)" }} />}
      <h3 className="text-sm font-semibold">{title}</h3>
    </div>
  );
}

function PhotoColumn({
  api, title, date, photos, wide = false,
}: {
  api: Api; title: string; date: string | null; photos: { id: number; kind: string }[]; wide?: boolean;
}) {
  return (
    <div>
      <p className="mb-1 text-xs font-semibold opacity-70">
        {title}
        {date && <span className="ml-1 font-normal opacity-60">· {shortDate(date)}</span>}
      </p>
      <div className={wide ? "grid grid-cols-3 gap-2" : "space-y-2"}>
        {photos.map((p) => (
          <img
            key={p.id}
            src={api.photoUrl(p.id)}
            alt={kindLabel(p.kind)}
            loading="lazy"
            className="w-full rounded-lg object-cover"
            style={{ aspectRatio: "3 / 4", border: "1px solid var(--p-line)" }}
          />
        ))}
      </div>
    </div>
  );
}

// --------------------------------------------------------------------- helpers
function round1(n: number): number {
  return Math.round(n * 10) / 10;
}
function shortDate(iso: string): string {
  const d = new Date(iso + (iso.length === 10 ? "T00:00:00" : ""));
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("es-ES", { day: "2-digit", month: "short" });
}
function deltaLabel(delta: number | null): string | undefined {
  if (delta == null || delta === 0) return "desde que empezaste";
  const s = delta < 0 ? "−" : "+";
  return `${s}${Math.abs(round1(delta))} kg desde el inicio`;
}
function toGoalLabel(current: number | null, goal: number | null): string | undefined {
  if (current == null || goal == null) return undefined;
  const diff = round1(current - goal);
  if (Math.abs(diff) < 0.1) return "¡objetivo alcanzado! 🎯";
  return `te faltan ${Math.abs(diff)} kg`;
}
function adherenceMean(rows: { diet_0_10: number | null; training_0_10: number | null }[]): number | null {
  const vals: number[] = [];
  for (const r of rows) {
    if (r.diet_0_10 != null) vals.push(r.diet_0_10);
    if (r.training_0_10 != null) vals.push(r.training_0_10);
  }
  if (!vals.length) return null;
  return Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 10) / 10;
}
function cell(v: number | null, unit = ""): string {
  return v == null ? "—" : `${round1(v)}${unit ? " " + unit : ""}`;
}
function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}
function kindLabel(kind: string): string {
  return { front: "frontal", side: "perfil", back: "espalda", detail: "detalle" }[kind] ?? kind;
}
