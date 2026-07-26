import { useEffect, useRef, useState } from "react";
import { Play } from "lucide-react";
import { videoSource } from "../lib/video";

/**
 * Reproductor DENTRO del portal: YouTube/Vimeo por iframe, archivos subidos por
 * el coach (o directos) por <video>.
 *
 * Se comporta como una demostración de técnica, no como una película:
 * arranca SOLO, en BUCLE y en silencio (así el navegador permite el autoplay y
 * no suena nada en mitad del gimnasio), y un toque encima lo pausa/reanuda.
 * Se monta solo mientras está abierto — al cerrarlo el componente se desmonta y
 * la reproducción para sola.
 *
 * Para fuentes "external" (una página que no sabemos embeber) los llamantes no
 * montan esto: abren el enlace fuera.
 */
export function InlineVideo({ url, title }: { url: string; title: string }) {
  const src = videoSource(url);

  if (src.kind === "youtube" || src.kind === "vimeo") {
    // El propio reproductor de YouTube/Vimeo ya pausa al tocarlo.
    const sep = src.embedUrl.includes("?") ? "&" : "?";
    const loop =
      src.kind === "youtube"
        ? `${sep}autoplay=1&mute=1&loop=1&playlist=${src.id}`
        : `${sep}autoplay=1&muted=1&loop=1`;
    return (
      <div className="aspect-video w-full overflow-hidden rounded-xl bg-black">
        <iframe
          src={src.embedUrl + loop}
          title={`Vídeo: ${title}`}
          className="h-full w-full"
          allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
          allowFullScreen
        />
      </div>
    );
  }
  if (src.kind === "file") return <FileVideo src={src.src} title={title} />;
  return null;
}

/** Vídeo subido por el coach: bucle silencioso + toque para pausar/reanudar. */
function FileVideo({ src, title }: { src: string; title: string }) {
  const ref = useRef<HTMLVideoElement>(null);
  const [paused, setPaused] = useState(false);

  // `muted` como PROPIEDAD (no solo atributo): es la condición que exigen los
  // navegadores para dejar arrancar el vídeo solo. Y el play explícito cubre a
  // los que ignoran el autoplay del atributo.
  useEffect(() => {
    const v = ref.current;
    if (!v) return;
    v.muted = true;
    v.play().catch(() => setPaused(true)); // si el navegador lo bloquea, se ve el ▶
  }, [src]);

  const toggle = () => {
    const v = ref.current;
    if (!v) return;
    if (v.paused) v.play().catch(() => {});
    else v.pause();
  };

  // El toque se atiende en el CONTENEDOR: así da igual que caiga sobre el vídeo
  // o sobre la capa de "pausado" — un solo gesto, siempre el mismo resultado.
  return (
    <div
      onClick={toggle}
      onKeyDown={(e) => {
        if (e.key === " " || e.key === "Enter") {
          e.preventDefault();
          toggle();
        }
      }}
      role="button"
      tabIndex={0}
      aria-label={`Vídeo de ${title}. Toca para pausar o reanudar`}
      className="relative cursor-pointer"
    >
      <video
        ref={ref}
        src={src}
        loop
        muted
        autoPlay
        playsInline
        preload="metadata"
        tabIndex={-1}
        onPlay={() => setPaused(false)}
        onPause={() => setPaused(true)}
        className="aspect-video w-full rounded-xl bg-black object-contain"
      />
      {paused && (
        // Señal de "está pausado": otro toque lo reanuda.
        <span
          aria-hidden="true"
          className="absolute inset-0 flex items-center justify-center rounded-xl"
          style={{ background: "rgba(0,0,0,0.35)" }}
        >
          <Play size={34} className="text-white drop-shadow-lg" fill="currentColor" />
        </span>
      )}
    </div>
  );
}

/** ¿Se puede reproducir dentro del portal? (si no, se abre fuera). */
export function isEmbeddable(url: string | null): url is string {
  return !!url && videoSource(url).kind !== "external";
}
