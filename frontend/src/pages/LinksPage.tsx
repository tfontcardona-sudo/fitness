import { useMemo, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { Copy, Dumbbell, Search, ShoppingBag } from "lucide-react";
import { copiar } from "../lib/clipboard";
import MarcaLogo from "../components/MarcaLogo";
import { useMarcaPublica } from "../hooks/useMarcaPublica";
import { coloresDeMarca, MARCA_POR_DEFECTO, pielDe, usaLaMarca } from "../lib/marca";

/**
 * Página PÚBLICA de enlaces (/dq) — el link del perfil de Instagram del coach.
 * Foto del coach de fondo (configurable en Recursos → Página de enlaces) y dos
 * accesos: "Trabaja conmigo" (planes DQR con pago) y la tienda del partner (ESN)
 * con el código de descuento del coach.
 */
export default function LinksPage() {
  // La marca del escaparate, con su PIEL ya aplicada a la página.
  const data = useMarcaPublica();
  const [copied, setCopied] = useState(false);
  // Buscador de productos: cuando el catálogo es largo, filtra por nombre.
  const [q, setQ] = useState("");

  const filteredProducts = useMemo(() => {
    const all = data?.products ?? [];
    const needle = q.trim().toLowerCase();
    if (!needle) return all;
    return all.filter((p) =>
      p.title.toLowerCase().includes(needle)
      || (p.category ?? "").toLowerCase().includes(needle));
  }, [data, q]);

  // Los dos colores, ya repartidos por el PAPEL que juegan en esta piel: el
  // "segundo" de Professional es su negro de estructura, y pintar con él la
  // atmósfera de una página negra es no pintar nada.
  const { primary, secondary } = coloresDeMarca(
    pielDe(data?.skin), data?.color_primary ?? MARCA_POR_DEFECTO.primary,
    data?.color_secondary ?? MARCA_POR_DEFECTO.secondary);
  const bg = data?.color_bg ?? MARCA_POR_DEFECTO.bg;

  // ESTA PÁGINA ES DE QUIEN VENDE POR INSTAGRAM. Un centro con local no la
  // usa: tiene su dirección y su propia web, y aquí solo encontraría una foto
  // que nadie ha configurado y una tienda de afiliación que no es suya. Como
  // es una URL PÚBLICA que puede estar enlazada desde fuera, no se rompe: se
  // lleva a lo que ese negocio sí vende.
  const usaEstaPagina = usaLaMarca(data?.usa, "enlaces");

  async function copyCode() {
    if (!data?.partner_discount_code) return;
    // El "Copiado ✓" salía aunque la copia fallara (esta página se ve mucho
    // desde el navegador de Instagram, donde el portapapeles es caprichoso):
    // ahora solo se canta si de verdad se copió.
    if (await copiar(data.partner_discount_code)) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } else {
      window.prompt("Copia el código a mano:", data.partner_discount_code);
    }
  }

  // Ya cargada la marca, si no usa esta página se va a lo que sí vende. Se
  // espera a `data` a propósito: desviar antes de saberlo dejaría a DQR sin su
  // propia página de enlaces en cada primera carga.
  if (data && !usaEstaPagina) return <Navigate to="/planes" replace />;

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6 py-10"
      style={{ background: bg }}>
      {/* Fondo: foto del coach (si está configurada) con velo oscuro para que
          los botones se lean siempre; sin foto, degradado de marca. */}
      {data?.links_photo_url ? (
        <>
          <img src={data.links_photo_url} alt=""
            className="absolute inset-0 h-full w-full object-cover" />
          <div className="absolute inset-0"
            style={{ background: `linear-gradient(180deg, ${bg}55 0%, ${bg}CC 55%, ${bg}F2 100%)` }} />
        </>
      ) : (
        <div className="absolute inset-0"
          style={{ background: `radial-gradient(120% 80% at 50% 0%, ${secondary}44 0%, ${bg} 60%)` }} />
      )}

      <div className="relative z-10 flex w-full max-w-sm flex-col items-center text-center">
        <MarcaLogo logoUrl={data?.logo_url} skin={data?.skin} nombre={data?.name} alto={64} />
        <h1 className="mt-4 text-2xl font-bold text-white drop-shadow">{data?.name ?? "DQR Assessories"}</h1>
        {data?.tagline && <p className="mt-1 text-sm text-white/80">{data.tagline}</p>}

        <div className="mt-8 w-full space-y-3">
          {/* OFERTA de la campaña de story/post ("link en la bio" → aquí):
              arriba del todo y con su gancho, para que el que viene del
              carrusel la encuentre al primer toque. */}
          {/* Solo si la marca TIENE oferta: estaba clavada, y en una marca sin
              ella el botón llevaba a un checkout que no existe. */}
          {data?.has_offer !== false && (
          <Link to="/oferta"
            className="flex w-full flex-col items-center justify-center rounded-2xl px-5 py-4 text-white shadow-xl transition-transform active:scale-[0.97]"
            style={{ background: "#C2453A" }}>
            <span className="text-base font-extrabold">⚡ Oferta: tu primer mes por 1 €</span>
            <span className="mt-0.5 text-xs font-semibold text-white/85">
              Plan completo · plazas limitadas
            </span>
          </Link>)}

          {/* Trabaja conmigo → página de planes con pago */}
          <Link to="/planes"
            className="flex w-full items-center justify-center gap-2.5 rounded-2xl px-5 py-4 text-base font-bold text-white shadow-xl transition-transform active:scale-[0.97]"
            style={{ background: primary }}>
            <Dumbbell size={20} /> Trabaja conmigo
          </Link>

          {/* Tienda del partner (ESN) + código de descuento */}
          {data?.partner_store_url && (
            <a href={data.partner_store_url} target="_blank" rel="noopener noreferrer"
              className="flex w-full items-center justify-center gap-2.5 rounded-2xl px-5 py-4 text-base font-bold text-white shadow-xl transition-transform active:scale-[0.97]"
              style={{ background: secondary }}>
              <ShoppingBag size={20} /> Suplementos ESN
            </a>
          )}
          {data?.partner_discount_code && (
            <button onClick={copyCode}
              className="mx-auto flex items-center gap-2 rounded-full border border-white/30 bg-white/10 px-4 py-2 text-sm font-semibold text-white backdrop-blur transition-transform active:scale-[0.97]">
              <Copy size={14} />
              {copied ? "¡Código copiado!" : <>Código de descuento: <span style={{ color: primary }}>{data.partner_discount_code}</span></>}
            </button>
          )}
        </div>

        {/* Productos recomendados: los mismos del portal, comprables aquí con
            el código de descuento de arriba. */}
        {data && data.products.length > 0 && (
          <div className="mt-10 w-full">
            <p className="mb-3 text-sm font-bold uppercase tracking-wider text-white/70">
              Productos que recomiendo
            </p>
            {/* Buscador: solo cuando hay catálogo suficiente para que ayude */}
            {data.products.length > 4 && (
              <div className="relative mb-3">
                <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/50" />
                <input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Buscar producto…"
                  className="w-full rounded-xl border border-white/20 bg-white/10 py-2.5 pl-9 pr-3 text-sm text-white placeholder-white/50 outline-none backdrop-blur focus:border-white/40"
                />
              </div>
            )}
            {filteredProducts.length === 0 ? (
              <p className="py-4 text-sm text-white/50">No hay productos que coincidan con «{q}».</p>
            ) : (
            <div className="grid grid-cols-2 gap-3">
              {filteredProducts.map((p, i) => (
                <a key={i} href={p.url} target="_blank" rel="noopener noreferrer"
                  className="overflow-hidden rounded-2xl border border-white/15 bg-white/10 text-left backdrop-blur transition-transform active:scale-[0.97]">
                  {p.image_url ? (
                    <img src={p.image_url} alt="" className="aspect-square w-full object-cover" />
                  ) : (
                    <div className="flex aspect-square w-full items-center justify-center"
                      style={{ background: `${secondary}33` }}>
                      <ShoppingBag size={28} className="text-white/50" />
                    </div>
                  )}
                  <div className="p-2.5">
                    <p className="truncate text-xs font-semibold text-white">{p.title}</p>
                    <p className="mt-0.5 text-[11px] font-semibold" style={{ color: primary }}>
                      Comprar{data.partner_discount_code ? ` · código ${data.partner_discount_code}` : ""}
                    </p>
                  </div>
                </a>
              ))}
            </div>
            )}
          </div>
        )}

        {/* Dónde está el centro: una marca con local tiene que decirlo. */}
        {data?.contact_address && (
          <p className="mt-8 text-xs text-white/60">{data.contact_address}</p>
        )}
        <p className="mt-4 text-xs text-white/50">Pago seguro con Stripe</p>
      </div>
    </div>
  );
}
