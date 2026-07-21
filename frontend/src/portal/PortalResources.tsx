import { useEffect, useRef, useState } from "react";
import { Check, Copy, Dumbbell, ExternalLink, Package, Pill, PlayCircle, ShoppingBag, X } from "lucide-react";
import type { PortalBrand, PortalResources as Resources, ResourceExerciseVideo, ResourceProduct } from "../types";
import { Empty, Loading } from "./PortalUi";
import { InlineVideo, isEmbeddable } from "./InlineVideo";
import { usePortalToast } from "./PortalToast";
import type { portalApi } from "./portalApi";

type Api = ReturnType<typeof portalApi>;

/**
 * Recursos: los vídeos de los ejercicios de SU rutina (título + imagen + vídeo)
 * y los productos que el coach recomienda (suplementos, material…), cada uno con
 * su título, imagen y enlace. Los vídeos se reproducen AQUÍ MISMO (tocar la
 * tarjeta abre el reproductor; otro toque o la ✕ lo cierra); los productos se
 * abren en la tienda con el código de descuento listo.
 */
export function PortalResources({ api, brand, hasTraining = true }: { api: Api; brand: PortalBrand; hasTraining?: boolean }) {
  const [data, setData] = useState<Resources | null>(null);
  const [error, setError] = useState(false);
  // Vídeo en reproducción (uno como mucho): el reproductor sale a ancho completo
  // encima de la galería; tocar otra tarjeta cambia de vídeo.
  const [playing, setPlaying] = useState<ResourceExerciseVideo | null>(null);
  const playerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.resources().then(setData).catch(() => setError(true));
  }, [api]);

  // El reproductor vive encima de la galería: si el cliente toca una tarjeta del
  // fondo, se le lleva hasta él (si no, parecería que el toque no hizo nada).
  useEffect(() => {
    if (playing) playerRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [playing]);

  if (error) {
    return (
      <div className="space-y-5">
        <h2 className="text-lg font-semibold">Recursos</h2>
        <div className="portal-card p-4 text-sm opacity-70">
          No se pudieron cargar los recursos. Inténtalo de nuevo en un momento.
        </div>
      </div>
    );
  }
  if (data === null) return <Loading />;

  // Paquete Start = solo nutrición: CERO entreno visible. Ni la sección de
  // vídeos de ejercicios ni ninguna mención a ellos en los textos.
  const videos = hasTraining ? data.exercise_videos : [];
  const { products } = data;
  const isEmpty = videos.length === 0 && products.length === 0;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Recursos</h2>
        <p className="mt-0.5 text-xs opacity-60">
          {hasTraining
            ? "Vídeos de tus ejercicios y productos recomendados por tu coach."
            : "Productos recomendados por tu coach."}
        </p>
      </div>

      {isEmpty && (
        <Empty
          icon={hasTraining ? PlayCircle : ShoppingBag}
          title="Aún no hay recursos"
          hint={
            hasTraining
              ? "Cuando tu coach añada vídeos de tus ejercicios o productos recomendados, aparecerán aquí."
              : "Cuando tu coach añada productos recomendados, aparecerán aquí."
          }
        />
      )}

      {videos.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-center gap-2">
            <PlayCircle size={16} style={{ color: brand.color_secondary }} />
            <h3 className="text-sm font-semibold">Vídeos de tus ejercicios</h3>
          </div>

          {/* Reproductor EN la misma pantalla: sale al tocar una tarjeta */}
          {playing && (
            <div ref={playerRef} className="portal-card overflow-hidden scroll-mt-4">
              <div className="flex items-center gap-2 p-2.5 pb-2">
                <p className="min-w-0 flex-1 truncate text-xs font-semibold">{playing.title}</p>
                <button
                  type="button"
                  onClick={() => setPlaying(null)}
                  aria-label="Cerrar vídeo"
                  className="tap -m-1 shrink-0 rounded-lg p-1 opacity-50 hover:opacity-90"
                >
                  <X size={16} />
                </button>
              </div>
              <div className="px-2.5 pb-2.5">
                <InlineVideo url={playing.video_url} title={playing.title} />
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            {videos.map((v) => {
              const active = playing?.exercise_id === v.exercise_id;
              const embeddable = isEmbeddable(v.video_url);
              const open = () => {
                if (!embeddable) {
                  window.open(v.video_url, "_blank", "noopener");
                  return;
                }
                setPlaying(active ? null : v); // toque en la activa = cerrar
              };
              return (
                <button
                  type="button"
                  key={v.exercise_id}
                  onClick={open}
                  aria-pressed={active}
                  className="portal-card tap group flex flex-col overflow-hidden text-left"
                  style={active ? { outline: `2px solid ${brand.color_secondary}` } : undefined}
                  aria-label={active ? `Cerrar vídeo de ${v.title}` : `Ver vídeo de ${v.title}`}
                >
                  <Thumb src={v.image_url} ratio="video" accent={brand.color_secondary}>
                    <span
                      className="absolute inset-0 flex items-center justify-center text-white transition-transform group-active:scale-95"
                      style={{ background: "rgba(0,0,0,0.18)" }}
                    >
                      <PlayCircle size={34} className="drop-shadow-lg" />
                    </span>
                  </Thumb>
                  <div className="flex flex-1 flex-col p-2.5">
                    <p className="line-clamp-2 text-xs font-semibold leading-snug">{v.title}</p>
                    {v.muscle && (
                      <span className="mt-1 text-[10px] uppercase tracking-wide opacity-50">
                        {v.muscle}
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </section>
      )}

      {products.length > 0 && (() => {
        // Los productos que salen EN su planificación (suplementos pautados)
        // van primero y destacados; el resto, como recomendaciones generales.
        const inPlan = products.filter((p) => p.in_plan);
        const rest = products.filter((p) => !p.in_plan);
        return (
          <>
            {inPlan.length > 0 && (
              <section className="space-y-3">
                <div className="flex items-center gap-2">
                  <Pill size={16} style={{ color: "#16A34A" }} />
                  <h3 className="text-sm font-semibold">De tu planificación</h3>
                  <span className="rounded-full px-2 py-0.5 text-[10px] font-bold"
                    style={{
                      background: "rgba(57, 255, 20, 0.14)", color: "#16A34A",
                      boxShadow: "0 0 8px rgba(57, 255, 20, 0.4)",
                    }}>
                    pautado
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {inPlan.map((p) => (
                    <ProductCard key={p.id} product={p} accent={brand.color_primary} />
                  ))}
                </div>
              </section>
            )}
            {rest.length > 0 && (
              <section className="space-y-3">
                <div className="flex items-center gap-2">
                  <ShoppingBag size={16} style={{ color: brand.color_secondary }} />
                  <h3 className="text-sm font-semibold">Productos seleccionados por {brand.name}</h3>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {rest.map((p) => (
                    <ProductCard key={p.id} product={p} accent={brand.color_primary} />
                  ))}
                </div>
              </section>
            )}
            <p className="text-[11px] opacity-40">
              Recomendaciones de tu coach. Al abrir un producto tu código de
              descuento se copia solo, para pegarlo al pagar.
            </p>
          </>
        );
      })()}
    </div>
  );
}

const CAT: Record<string, { label: string; icon: typeof Pill }> = {
  suplemento: { label: "Suplemento", icon: Pill },
  material: { label: "Material", icon: Dumbbell },
  otro: { label: "Otro", icon: Package },
};

function ProductCard({ product: p, accent }: { product: ResourceProduct; accent: string }) {
  const cat = CAT[p.category] ?? CAT.otro;
  const toast = usePortalToast();
  const [copied, setCopied] = useState(false);

  // Copiar el código SIN abrir el enlace del producto (la tarjeta entera es un <a>).
  async function copyCode(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!p.discount_code) return;
    try {
      await navigator.clipboard.writeText(p.discount_code);
      setCopied(true);
      toast.push(`Código ${p.discount_code} copiado — pégalo al pagar`);
      window.setTimeout(() => setCopied(false), 2500);
    } catch {
      // Sin permiso de portapapeles (raro): el código está visible igualmente.
      toast.push(`Usa el código ${p.discount_code} al pagar`);
    }
  }

  // Al abrir el producto: se copia el código SOLO (mejor esfuerzo) y, si la
  // tienda del partner lo soporta, buy_url ya lo lleva aplicado al carrito.
  function onOpen() {
    if (p.discount_code) navigator.clipboard.writeText(p.discount_code).catch(() => {});
  }

  return (
    <a
      href={p.buy_url || p.url}
      target="_blank"
      rel="noreferrer"
      onClick={onOpen}
      className="portal-card tap group flex flex-col overflow-hidden"
      aria-label={`Ver ${p.title}`}
    >
      <Thumb src={p.image_url} ratio="square" accent={accent} fallbackIcon={cat.icon} />
      <div className="flex flex-1 flex-col p-2.5">
        <div className="flex items-center gap-1 text-[10px] uppercase tracking-wide opacity-50">
          <cat.icon size={11} />
          {cat.label}
          {p.in_plan && (
            // Verde NEÓN: este producto está pautado en SU planificación.
            <span className="ml-auto rounded px-1.5 py-0.5 text-[9px] font-bold normal-case tracking-normal"
              style={{
                background: "rgba(57, 255, 20, 0.14)", color: "#16A34A",
                boxShadow: "0 0 8px rgba(57, 255, 20, 0.45), inset 0 0 0 1px rgba(57, 255, 20, 0.35)",
              }}>
              En tu planificación
            </span>
          )}
        </div>
        <p className="mt-0.5 line-clamp-2 text-xs font-semibold leading-snug">{p.title}</p>
        {p.description && (
          <p className="mt-1 line-clamp-2 text-[11px] leading-snug opacity-60">{p.description}</p>
        )}
        {p.discount_code && (
          // Código de descuento del coach: DESTACADO y copiable de un toque —
          // el cliente lo pega al pagar en la web de la marca.
          <button
            type="button"
            onClick={copyCode}
            aria-label={`Copiar código de descuento ${p.discount_code}`}
            className="tap mt-2 flex items-center justify-between gap-1 rounded-lg px-2 py-1.5 text-left"
            style={{ background: `color-mix(in srgb, ${accent} 12%, transparent)` }}
          >
            <span className="min-w-0">
              <span className="block text-[9px] uppercase tracking-wide opacity-60">Tu código de descuento</span>
              <span className="block truncate text-[11px] font-bold tracking-wide" style={{ color: accent }}>
                {p.discount_code}
              </span>
            </span>
            {copied
              ? <Check size={13} className="shrink-0" style={{ color: accent }} />
              : <Copy size={13} className="shrink-0 opacity-60" />}
          </button>
        )}
        <span
          className="mt-2 inline-flex items-center gap-1 text-[11px] font-semibold"
          style={{ color: accent }}
        >
          Ver <ExternalLink size={11} />
        </span>
      </div>
    </a>
  );
}

/** Miniatura con relación de aspecto fija y respaldo si la imagen no carga. */
function Thumb({
  src,
  ratio,
  accent,
  fallbackIcon: Icon = PlayCircle,
  children,
}: {
  src: string | null;
  ratio: "video" | "square";
  accent: string;
  fallbackIcon?: typeof PlayCircle;
  children?: React.ReactNode;
}) {
  const [ok, setOk] = useState(Boolean(src));
  useEffect(() => setOk(Boolean(src)), [src]); // re-sincroniza si cambia la imagen
  const aspect = ratio === "video" ? "aspect-video" : "aspect-square";
  return (
    <div className={`relative w-full ${aspect} overflow-hidden`} style={{ background: `${accent}14` }}>
      {ok && src ? (
        <img
          src={src}
          alt=""
          loading="lazy"
          onError={() => setOk(false)}
          className="h-full w-full object-cover"
        />
      ) : (
        <span className="absolute inset-0 flex items-center justify-center opacity-30" style={{ color: accent }}>
          <Icon size={28} />
        </span>
      )}
      {children}
    </div>
  );
}
