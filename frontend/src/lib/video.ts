/**
 * Detección de la FUENTE de un vídeo para reproducirlo DENTRO del portal
 * (sin echar al cliente a una pestaña nueva):
 * - YouTube/Vimeo → URL de embed para un <iframe>.
 * - Archivo directo (subido por el coach a /api/media, o .mp4/.webm externo)
 *   → <video controls>.
 * - Cualquier otra página → "external": se abre fuera (no sabemos embeberla).
 *
 * El parseo usa la API URL con el host anclado (nada de subcadenas: un
 * "notyoutube.com/watch?v=…" no es YouTube). Espejo del criterio del backend
 * (services/portal.youtube_thumbnail).
 */

export type VideoSource =
  | { kind: "youtube"; id: string; embedUrl: string }
  | { kind: "vimeo"; id: string; embedUrl: string }
  | { kind: "file"; src: string }
  | { kind: "external"; url: string };

const YT_HOSTS = new Set([
  "youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com",
  "youtube-nocookie.com", "www.youtube-nocookie.com",
]);
const YT_ID = /^[A-Za-z0-9_-]{11}$/;

export function youtubeId(url: string): string | null {
  let u: URL;
  try {
    u = new URL(url);
  } catch {
    return null;
  }
  const host = u.hostname.toLowerCase();
  let id: string | null = null;
  if (host === "youtu.be" || host === "www.youtu.be") {
    id = u.pathname.split("/").filter(Boolean)[0] ?? null;
  } else if (YT_HOSTS.has(host)) {
    const segs = u.pathname.split("/").filter(Boolean);
    if (segs[0] === "watch") id = u.searchParams.get("v");
    else if (["embed", "shorts", "v", "live"].includes(segs[0] ?? "")) id = segs[1] ?? null;
  }
  return id && YT_ID.test(id) ? id : null;
}

/** Segundos de inicio de un enlace de YouTube ("?t=90", "?t=1m30s", "?start=75"). */
function youtubeStart(url: string): number {
  let raw: string | null = null;
  try {
    const u = new URL(url);
    raw = u.searchParams.get("t") ?? u.searchParams.get("start");
  } catch {
    return 0;
  }
  if (!raw) return 0;
  if (/^\d+s?$/.test(raw)) return parseInt(raw, 10);
  const m = raw.match(/^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$/);
  if (!m || (!m[1] && !m[2] && !m[3])) return 0;
  return (+(m[1] ?? 0)) * 3600 + (+(m[2] ?? 0)) * 60 + (+(m[3] ?? 0));
}

function vimeoId(url: string): string | null {
  let u: URL;
  try {
    u = new URL(url);
  } catch {
    return null;
  }
  const host = u.hostname.toLowerCase();
  if (host !== "vimeo.com" && host !== "www.vimeo.com" && host !== "player.vimeo.com") return null;
  const seg = u.pathname.split("/").filter(Boolean).pop() ?? "";
  return /^\d{6,12}$/.test(seg) ? seg : null;
}

const FILE_EXT = /\.(mp4|webm|mov|m4v|ogv)(\?.*)?$/i;

export function videoSource(url: string): VideoSource {
  const yt = youtubeId(url);
  if (yt) {
    // nocookie + playsinline (iOS no salta a pantalla completa) + rel=0 (sin
    // sugerencias de otros canales al pausar). Conserva el minuto de inicio
    // si el coach enlazó con "?t=…" (empieza justo donde señala la técnica).
    const start = youtubeStart(url);
    return {
      kind: "youtube", id: yt,
      embedUrl: `https://www.youtube-nocookie.com/embed/${yt}?playsinline=1&rel=0`
        + (start > 0 ? `&start=${start}` : ""),
    };
  }
  const vm = vimeoId(url);
  if (vm) {
    return { kind: "vimeo", id: vm, embedUrl: `https://player.vimeo.com/video/${vm}` };
  }
  // Vídeo subido por el coach (servido por la propia API) o archivo directo.
  // El chequeo de /api/media/ va sobre el PATH parseado (no sobre la URL cruda,
  // donde la subcadena podría aparecer en la query de cualquier otra página).
  let pathname = "";
  try {
    pathname = new URL(url).pathname;
  } catch {
    /* URL rara: cae al chequeo de extensión */
  }
  if (pathname.includes("/api/media/") || FILE_EXT.test(url)) {
    return { kind: "file", src: url };
  }
  return { kind: "external", url };
}
