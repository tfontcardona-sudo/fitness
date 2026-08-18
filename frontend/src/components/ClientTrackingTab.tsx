import { useEffect, useRef, useState } from "react";
import { api, keepIfSame, REFRESH_MS } from "../lib/api";
import { pkg } from "../lib/packages";
import type { ClientOut } from "../types";

type Tracking = Awaited<ReturnType<typeof api.getClientTracking>>;
type ChangeRequest = Awaited<ReturnType<typeof api.listChangeRequests>>[number];

/** Peticiones/dudas que el cliente escribió desde su portal. Las abiertas
 *  mantienen viva la alerta "Te ha escrito…" hasta marcarlas resueltas: este
 *  bloque es el único sitio donde el coach puede LEERLAS y cerrarlas (antes el
 *  texto solo viajaba por email y la alerta no se podía apagar nunca). */
function ChangeRequestsCard({ clientId }: { clientId: number }) {
  const [crs, setCrs] = useState<ChangeRequest[] | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

  const load = () => api.listChangeRequests(clientId).then(setCrs).catch(() => {});
  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [clientId]);

  const open = (crs ?? []).filter((c) => c.status === "open");
  if (!open.length) return null;

  async function resolve(id: number) {
    setBusy(id);
    try {
      await api.resolveChangeRequest(id);
      await load();
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="card border border-amber-500/30 p-4">
      <h4 className="text-sm font-semibold text-amber-300">
        Peticiones del cliente sin responder ({open.length})
      </h4>
      <ul className="mt-2 space-y-2">
        {open.map((c) => (
          <li key={c.id} className="flex items-start justify-between gap-3 rounded-lg bg-zinc-900/60 p-3">
            <div className="min-w-0">
              <p className="whitespace-pre-wrap text-sm text-zinc-200">{c.message}</p>
              <p className="mt-1 text-[11px] text-zinc-500">
                {new Date(c.created_at).toLocaleString("es-ES", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
              </p>
            </div>
            <button
              onClick={() => resolve(c.id)}
              disabled={busy === c.id}
              className="btn-secondary shrink-0 text-xs"
              title="Al marcarla resuelta se apaga su alerta"
            >
              {busy === c.id ? "…" : "Marcar resuelta"}
            </button>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-[11px] text-zinc-500">
        Respóndele o aplica el cambio en su planificación; después márcala resuelta.
      </p>
    </div>
  );
}

/**
 * Seguimiento del cliente EN TIEMPO REAL para el coach. Hace polling cada 3 s:
 * lo que el cliente registra (diario con series) aparece
 * en cuanto guarda; lo que falta se muestra como "pendiente".
 */
export function ClientTrackingTab({ client }: { client: ClientOut }) {
  const [data, setData] = useState<Tracking | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () =>
      api
        .getClientTracking(client.id)
        // keepIfSame: no re-renderiza la tabla cada 3 s si los datos son idénticos.
        .then((d) => alive && setData((prev) => keepIfSame(prev, d)))
        .catch((e) => alive && setErr(e?.message ?? "Error"));
    load();
    timer.current = window.setInterval(load, REFRESH_MS); // polling → tiempo real
    return () => {
      alive = false;
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [client.id]);

  if (err) return <div className="card p-5 text-sm text-red-400">No se pudo cargar el seguimiento: {err}</div>;
  if (!data) return <div className="card p-5 text-sm opacity-60">Cargando seguimiento…</div>;
  if (!data.has_period)
    return (
      <div className="space-y-4">
        <ChangeRequestsCard clientId={client.id} />
        <div className="card p-5 text-sm opacity-60">
          El cliente aún no tiene un período activo. Se abre solo al activarse la
          planificación, al enviar el feedback o cuando el cliente entra en su portal.
        </div>
      </div>
    );

  // Paquete solo-nutrición (Start): sin columnas ni métricas de entreno.
  const hasTraining = pkg(client.package_tier).hasTraining;
  const p = data.period!;
  const daily = data.daily ?? [];
  const avg = data.daily_averages;

  return (
    <div className="space-y-4">
      <ChangeRequestsCard clientId={client.id} />
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-100">Seguimiento en tiempo real</h3>
        <span className="text-xs text-zinc-500">se actualiza solo</span>
      </div>

      {/* El seguimiento es CONTINUO: no hay cuenta atrás ni barra de progreso
          hacia un cierre — lo que importa es desde cuándo dura y con qué
          constancia registra. */}
      <div className="card p-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2 text-xs text-zinc-400">
          <span>Desde el {p.starts_on}</span>
          <span>día {p.days_elapsed} de seguimiento</span>
        </div>
        <div className="mt-2 text-xs text-zinc-300">
          Días registrados: <b>{data.days_logged ?? 0}</b> ·{" "}
          Hoy:{" "}
          {data.today_logged
            ? <span className="text-emerald-400">registrado</span>
            : <span className="text-amber-400">pendiente</span>}
        </div>
      </div>

      <div className="card overflow-hidden p-0">
        <div className="border-b border-white/5 px-4 py-2 text-xs font-semibold text-zinc-300">Registros diarios</div>
        {daily.length === 0 ? (
          <p className="p-4 text-sm text-amber-400">Sin registros todavía (pendiente).</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="text-zinc-500">
                <tr className="text-left">
                  <th className="px-3 py-2">Fecha</th><th>Peso</th><th>Sueño</th>
                  <th>Pasos</th><th>Sac.</th><th>Agua</th><th>Dieta</th>{hasTraining && <th>Series</th>}
                </tr>
              </thead>
              <tbody className="text-zinc-200">
                {daily.map((d) => (
                  <tr key={d.date} className="border-t border-white/5">
                    <td className="px-3 py-2">{d.date}</td>
                    <td>{fmt1(d.weight_kg)}</td>
                    <td>{fmt1(d.sleep_hours)}</td>
                    <td className="max-w-[130px] truncate">{d.steps ?? "—"}</td>
                    <td>{d.satiety_1_10 ?? "—"}</td>
                    <td>{fmt1(d.water_liters)}</td>
                    <td>{ADHERENCE_LABEL[d.diet_adherence ?? ""] ?? d.diet_adherence ?? "—"}</td>
                    {hasTraining && <td>{d.workout_sets || "—"}</td>}
                  </tr>
                ))}
              </tbody>
              {avg && (
                <tfoot>
                  <tr className="border-t border-white/10 font-semibold text-zinc-100" style={{ background: "var(--surface-raised)" }}>
                    <td className="px-3 py-2">Media</td>
                    <td>{fmt1(avg.weight_kg)}</td>
                    <td>{fmt1(avg.sleep_hours)}</td>
                    <td className="max-w-[130px] truncate">{avg.steps != null ? Math.round(avg.steps) : "—"}</td>
                    <td>{avg.satiety_1_10 ?? "—"}</td>
                    <td>{avg.water_liters ?? "—"}</td>
                    <td>{avg.diet_adherence_pct != null ? `${avg.diet_adherence_pct}%` : "—"}</td>
                    {hasTraining && <td>{avg.workout_sets ?? "—"}</td>}
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        )}
      </div>

    </div>
  );
}

/** Peso/sueño/agua con un decimal como mucho (evita 83.60000000000001). */
function fmt1(v: number | null | undefined): string | number {
  return v == null ? "—" : Math.round(v * 10) / 10;
}

const ADHERENCE_LABEL: Record<string, string> = { yes: "sí", partial: "parcial", no: "no" };
