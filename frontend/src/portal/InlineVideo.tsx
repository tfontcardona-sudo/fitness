import { videoSource } from "../lib/video";

/**
 * Reproductor DENTRO del portal: YouTube/Vimeo por iframe, archivos subidos o
 * directos por <video>. Se monta solo mientras está abierto — al cerrarlo el
 * componente se desmonta y la reproducción PARA sola (el cliente sigue con su
 * rutina sin audio de fondo).
 *
 * Para fuentes "external" (una página que no sabemos embeber) los llamantes no
 * montan esto: abren el enlace fuera.
 */
export function InlineVideo({ url, title }: { url: string; title: string }) {
  const src = videoSource(url);
  if (src.kind === "youtube" || src.kind === "vimeo") {
    return (
      <div className="aspect-video w-full overflow-hidden rounded-xl bg-black">
        <iframe
          src={src.embedUrl}
          title={`Vídeo: ${title}`}
          className="h-full w-full"
          allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
          allowFullScreen
        />
      </div>
    );
  }
  if (src.kind === "file") {
    return (
      <video
        src={src.src}
        controls
        playsInline
        preload="metadata"
        className="aspect-video w-full rounded-xl bg-black object-contain"
        aria-label={`Vídeo: ${title}`}
      />
    );
  }
  return null;
}

/** ¿Se puede reproducir dentro del portal? (si no, se abre fuera). */
export function isEmbeddable(url: string | null): url is string {
  return !!url && videoSource(url).kind !== "external";
}
