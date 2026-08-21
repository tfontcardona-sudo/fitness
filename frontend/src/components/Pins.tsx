import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import { ChevronDown, Pin as PinIcon, X } from "lucide-react";
import { desmarcarTodo, irYMarcar } from "../lib/anchors";
import { useDismiss } from "../lib/useDismiss";
import { getPins, subscribePins, unpin, type Pin } from "../lib/pins";

/* ------------------------------------------------------------------ hook --- */

export function usePins(): Pin[] {
  const [pins, setPins] = useState<Pin[]>(getPins);
  useEffect(() => subscribePins(setPins), []);
  return pins;
}

/* ------------------------------------------------------- nota del marcador --- */

/**
 * La nota pegada al elemento marcado: QUÉ pasa aquí y CÓMO se arregla.
 *
 * Va en un portal al body y se posiciona por la caja del elemento: meterla
 * dentro del elemento rompería maquetaciones ajenas (rejillas, tablas, flex) y
 * React podría barrerla en el siguiente render del componente anfitrión.
 */
function NotaDeAncla({ pin, el, onClose }: { pin: Pin; el: HTMLElement; onClose: () => void }) {
  const [caja, setCaja] = useState<DOMRect | null>(null);

  useEffect(() => {
    const alTeclear = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", alTeclear);
    return () => document.removeEventListener("keydown", alTeclear);
  }, [onClose]);

  useLayoutEffect(() => {
    const medir = () => setCaja(el.getBoundingClientRect());
    medir();
    // El elemento puede moverse por scroll, por abrirse un desplegable encima,
    // por un refresco de datos o por rotar el móvil.
    const ro = new ResizeObserver(medir);
    ro.observe(el);
    ro.observe(document.body);
    window.addEventListener("scroll", medir, true);
    window.addEventListener("resize", medir);
    const reloj = window.setInterval(medir, 500);
    return () => {
      ro.disconnect();
      window.removeEventListener("scroll", medir, true);
      window.removeEventListener("resize", medir);
      window.clearInterval(reloj);
    };
  }, [el]);

  if (!caja) return null;
  // Si el elemento se ha ido de la pantalla, la nota se esconde (no flota
  // huérfana en una esquina apuntando a nada).
  const fuera = caja.bottom < 0 || caja.top > window.innerHeight;
  if (fuera) return null;

  const ANCHO = 288;
  const izquierda = Math.min(
    Math.max(8, caja.left),
    Math.max(8, window.innerWidth - ANCHO - 8),
  );
  const cabeDebajo = caja.bottom + 140 < window.innerHeight;
  const arriba = cabeDebajo ? caja.bottom + 8 : Math.max(8, caja.top - 140);

  return createPortal(
    <div
      role="status"
      className="card animate-rise fixed z-[60] p-3"
      style={{
        left: izquierda, top: arriba, width: ANCHO,
        borderColor: "color-mix(in srgb, var(--brand-accent) 55%, transparent)",
        boxShadow: "var(--shadow-2)",
      }}
    >
      <div className="flex items-start gap-2">
        <PinIcon size={14} className="mt-0.5 shrink-0" style={{ color: "var(--brand-accent)" }} />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-zinc-100">{pin.label}</p>
          {pin.hint && <p className="mt-1 text-xs text-zinc-400">{pin.hint}</p>}
          <p className="mt-2 text-[11px] text-zinc-500">
            El recordatorio se irá solo en cuanto lo arregles.
          </p>
        </div>
        <button onClick={onClose} aria-label="Cerrar la marca"
          className="tap -m-1 shrink-0 rounded-lg p-1 text-zinc-500 hover:text-zinc-200">
          <X size={14} />
        </button>
      </div>
    </div>,
    document.body,
  );
}

/* --------------------------------------------------- marcar al llegar (?ir=) --- */

/**
 * Lee `?ir=<ancla>` y, cuando el elemento existe, lo abre, lo centra y lo
 * marca con su nota. Se monta UNA vez en la ficha del cliente.
 */
export function MarcadorDeAncla({ clientId, target }: { clientId: number; target: string | null }) {
  const [el, setEl] = useState<HTMLElement | null>(null);
  const pins = usePins();
  const pin = target ? pins.find((p) => p.clientId === clientId && p.target === target) : undefined;
  const cerrado = useRef<string | null>(null);

  useEffect(() => {
    let vivo = true;
    setEl(null);
    if (!target || cerrado.current === target) return;
    irYMarcar(target).then((encontrado) => {
      // La búsqueda puede tardar segundos (los datos llegan por red): si para
      // entonces ya cambiaste de ancla o saliste, la marca que acaba de
      // encenderse se apaga — si no, se quedaba pegada en la pantalla nueva.
      if (vivo) setEl(encontrado);
      else desmarcarTodo();
    });
    return () => {
      vivo = false;
      desmarcarTodo();
    };
  }, [target, clientId]);

  // El problema se RESOLVIÓ mientras mirabas: fuera la marca, sin ceremonia.
  // Solo si llegó a haber recordatorio: un enlace pegado a mano (con ?ir= pero
  // sin recordatorio) debe poder señalar el sitio igual, y con esta regla mal
  // puesta la marca se encendía y se apagaba en el mismo instante.
  const huboPin = useRef(false);
  useEffect(() => { if (pin) huboPin.current = true; }, [pin]);
  useEffect(() => {
    if (target && !pin && huboPin.current) { desmarcarTodo(); setEl(null); }
  }, [target, pin]);
  useEffect(() => { huboPin.current = false; }, [target]);

  if (!el || !pin) return null;
  return (
    <NotaDeAncla
      pin={pin}
      el={el}
      onClose={() => { cerrado.current = target; desmarcarTodo(); setEl(null); }}
    />
  );
}

/* ------------------------------------------------------------------ dock --- */

/**
 * La lista de recordatorios, siempre a mano. Colapsada es una píldora con el
 * número; abierta, las tareas ancladas con su cliente. Un clic vuelve al sitio
 * exacto y lo vuelve a marcar.
 */
export function PinDock() {
  const pins = usePins();
  const [abierto, setAbierto] = useState(false);
  const navigate = useNavigate();
  // Mismas reglas de cierre que el resto de la web: Escape, clic fuera y el
  // foco de vuelta a donde estaba.
  const caja = useRef<HTMLDivElement>(null);
  useDismiss(caja, () => setAbierto(false), abierto);

  const ir = useCallback((p: Pin) => {
    setAbierto(false);
    // Si ya estás en esa misma dirección, React Router no cambia nada y el
    // marcador no se entera: se vuelve a marcar a mano. Sin esto, pulsar un
    // recordatorio estando ya en la pantalla no hacía absolutamente nada.
    const aqui = window.location.pathname + window.location.search;
    if (aqui === p.href && p.target) { void irYMarcar(p.target); return; }
    navigate(p.href);
  }, [navigate]);

  // Sin recordatorios no hay dock: un contenedor vacío permanente es ruido.
  if (!pins.length) return null;

  return (
    <div ref={caja}
      className="fixed bottom-4 left-4 z-40 max-sm:bottom-[calc(4.75rem+env(safe-area-inset-bottom))] print:hidden">
      {abierto && (
        <div className="card animate-rise mb-2 w-[320px] max-w-[calc(100vw-2rem)] overflow-hidden">
          <div className="flex items-center justify-between border-b px-3 py-2"
            style={{ borderColor: "var(--line)" }}>
            <span className="text-xs font-semibold uppercase tracking-wide text-zinc-300">
              Lo que ibas a arreglar
            </span>
            <button onClick={() => setAbierto(false)} aria-label="Cerrar recordatorios"
              className="tap -m-1 rounded-lg p-1 text-zinc-500 hover:text-zinc-200">
              <X size={14} />
            </button>
          </div>
          <ul className="max-h-[50vh] overflow-y-auto">
            {pins.map((p) => (
              <li key={p.id} className="flex items-start gap-2 border-b px-3 py-2.5 last:border-b-0"
                style={{ borderColor: "var(--line)" }}>
                <span aria-hidden className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
                  style={{ background: p.severity === "alta" ? "#C2453A" : "var(--brand-accent-2)" }} />
                <button onClick={() => ir(p)} className="min-w-0 flex-1 text-left group">
                  <span className="block truncate text-sm font-medium text-zinc-100 group-hover:opacity-80">
                    {p.label}
                  </span>
                  <span className="mt-0.5 block truncate text-xs text-zinc-500">{p.clientName}</span>
                </button>
                <button onClick={() => unpin(p.id)} aria-label={`Quitar recordatorio de ${p.clientName}`}
                  title="Quitar de la lista (el aviso sigue si el problema sigue)"
                  className="tap -m-1 shrink-0 rounded-lg p-1 text-zinc-600 hover:text-zinc-300">
                  <X size={13} />
                </button>
              </li>
            ))}
          </ul>
          <p className="px-3 py-2 text-[11px] text-zinc-500">
            Cada uno se borra solo al quedar resuelto.
          </p>
        </div>
      )}
      <button
        onClick={() => setAbierto((o) => !o)}
        aria-expanded={abierto}
        className="card flex items-center gap-2 rounded-full px-3.5 py-2 text-sm font-semibold text-zinc-100"
        style={{ boxShadow: "var(--shadow-2)" }}
      >
        <PinIcon size={15} style={{ color: "var(--brand-accent)" }} />
        {pins.length} por arreglar
        <ChevronDown size={14} className="text-zinc-500 transition-transform"
          style={{ transform: abierto ? "rotate(180deg)" : undefined }} />
      </button>
    </div>
  );
}
