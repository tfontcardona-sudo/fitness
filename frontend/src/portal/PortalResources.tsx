import { useEffect, useState } from "react";
import { Dumbbell, ExternalLink, Package, Pill, PlayCircle, ShoppingBag } from "lucide-react";
import type { PortalBrand, PortalResources as Resources, ResourceProduct } from "../types";
import { Empty, Loading } from "./PortalUi";
import type { portalApi } from "./portalApi";

type Api = ReturnType<typeof portalApi>;

/**
 * Recursos: los vídeos de los ejercicios de SU rutina (título + imagen + vídeo)
 * y los productos que el coach recomienda (suplementos, material…), cada uno con
 * su título, imagen y enlace. Todo de solo lectura: se abre en una pestaña nueva.
 */
export function PortalResources({ api, brand, hasTraining = true }: { api: Api; brand: PortalBrand; hasTraining?: boolean }) {
  const [data, setData] = useState<Resources | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.resources().then(setData).catch(() => setError(true));
  }, [api]);

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
          <div className="grid grid-cols-2 gap-3">
            {videos.map((v) => (
              <a
                key={v.exercise_id}
                href={v.video_url}
                target="_blank"
                rel="noreferrer"
                className="portal-card tap group flex flex-col overflow-hidden"
                aria-label={`Ver vídeo de ${v.title}`}
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
              </a>
            ))}
          </div>
        </section>
      )}

      {products.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-center gap-2">
            <ShoppingBag size={16} style={{ color: brand.color_primary }} />
            <h3 className="text-sm font-semibold">Productos recomendados</h3>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {products.map((p) => (
              <ProductCard key={p.id} product={p} accent={brand.color_primary} />
            ))}
          </div>
          <p className="text-[11px] opacity-40">
            Recomendaciones de tu coach. Los enlaces se abren fuera de la app.
          </p>
        </section>
      )}
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
  return (
    <a
      href={p.url}
      target="_blank"
      rel="noreferrer"
      className="portal-card tap group flex flex-col overflow-hidden"
      aria-label={`Ver ${p.title}`}
    >
      <Thumb src={p.image_url} ratio="square" accent={accent} fallbackIcon={cat.icon} />
      <div className="flex flex-1 flex-col p-2.5">
        <div className="flex items-center gap-1 text-[10px] uppercase tracking-wide opacity-50">
          <cat.icon size={11} />
          {cat.label}
        </div>
        <p className="mt-0.5 line-clamp-2 text-xs font-semibold leading-snug">{p.title}</p>
        {p.description && (
          <p className="mt-1 line-clamp-2 text-[11px] leading-snug opacity-60">{p.description}</p>
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
