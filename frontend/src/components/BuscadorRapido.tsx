import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CreditCard, Library, Search, Users, Wallet } from "lucide-react";
import { api, keepIfSame } from "../lib/api";
import type { ClientOut } from "../types";
import { StatusBadge } from "./ui";

/**
 * BUSCADOR RÁPIDO (⌘K / Ctrl+K): saltar a cualquier cliente desde donde sea.
 *
 * Era la friccón más cara del panel y la más invisible: para pasar del cliente
 * A al B había que volver a la cartera, buscar, entrar. Diez revisiones un
 * lunes son treinta clics que no hacen nada. Ahora se teclea el nombre y se
 * entra, sin salir de donde estás.
 *
 * Se abre con teclado (⌘K) o con la lupa de la barra. En móvil, donde no hay
 * teclado físico, la lupa es la puerta.
 */
export function BuscadorRapido({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [clients, setClients] = useState<ClientOut[] | null>(null);
  const [sel, setSel] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // La cartera se pide UNA vez al abrir (ligera, sin las notas largas) y se
  // filtra en el navegador: teclear no puede disparar una petición por letra.
  useEffect(() => {
    if (!open) return;
    let vivo = true;
    api.listClients({ light: true })
      .then((cs) => { if (vivo) setClients((prev) => keepIfSame(prev, cs)); })
      .catch(() => { if (vivo) setClients((prev) => prev ?? []); });
    return () => { vivo = false; };
  }, [open]);

  useEffect(() => {
    if (open) {
      setQ("");
      setSel(0);
      // El foco, tras el pintado: enfocar un input aún sin montar no hace nada.
      const t = window.setTimeout(() => inputRef.current?.focus(), 20);
      return () => window.clearTimeout(t);
    }
  }, [open]);

  const atajos = useMemo(() => ([
    { id: "clientes", label: "Cartera de clientes", to: "/clientes", icon: Users },
    { id: "pagos", label: "Pagos", to: "/pagos", icon: CreditCard },
    { id: "creditos", label: "Créditos de IA", to: "/creditos", icon: Wallet },
    { id: "recursos", label: "Recursos del portal", to: "/recursos", icon: Library },
  ]), []);

  const norm = (s: string) =>
    s.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();

  const termino = norm(q.trim());
  const resultados = useMemo(() => {
    const cs = (clients ?? []).filter((c) =>
      !termino
      || norm(c.full_name).includes(termino)
      || norm(c.email ?? "").includes(termino));
    return cs.slice(0, 8);
  }, [clients, termino]);

  const accesos = useMemo(
    () => atajos.filter((a) => !termino || norm(a.label).includes(termino)),
    [atajos, termino]);

  const total = resultados.length + accesos.length;

  const ir = useCallback((indice: number) => {
    if (indice < resultados.length) {
      const c = resultados[indice];
      if (c) navigate(`/clientes/${c.id}`);
    } else {
      const a = accesos[indice - resultados.length];
      if (a) navigate(a.to);
    }
    onClose();
  }, [resultados, accesos, navigate, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-start justify-center px-4 pt-[12vh]"
      style={{ background: "rgba(6,8,12,.55)", backdropFilter: "blur(2px)" }}
      onClick={onClose}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Buscar cliente o sección"
        className="w-full max-w-lg overflow-hidden rounded-2xl border shadow-2xl"
        style={{ borderColor: "var(--line-strong)", background: "var(--surface-raised)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 border-b px-4 py-3"
             style={{ borderColor: "var(--line)" }}>
          <Search size={17} style={{ color: "var(--text-faint)" }} />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => { setQ(e.target.value); setSel(0); }}
            onKeyDown={(e) => {
              if (e.key === "Escape") { onClose(); return; }
              if (e.key === "ArrowDown") { e.preventDefault(); setSel((s) => Math.min(s + 1, total - 1)); }
              if (e.key === "ArrowUp") { e.preventDefault(); setSel((s) => Math.max(s - 1, 0)); }
              if (e.key === "Enter") { e.preventDefault(); ir(sel); }
            }}
            placeholder="Busca un cliente o una sección…"
            className="w-full bg-transparent text-base text-zinc-100 outline-none placeholder:text-zinc-600"
          />
          <kbd className="hidden shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold sm:block"
               style={{ background: "var(--surface)", color: "var(--text-faint)" }}>
            esc
          </kbd>
        </div>

        <div className="max-h-[52vh] overflow-y-auto py-1">
          {clients === null && (
            <p className="px-4 py-6 text-center text-sm text-zinc-500">Cargando…</p>
          )}
          {clients !== null && total === 0 && (
            <p className="px-4 py-6 text-center text-sm text-zinc-500">
              Nada con «{q}».
            </p>
          )}

          {resultados.map((c, i) => (
            <button
              key={c.id}
              onMouseEnter={() => setSel(i)}
              onClick={() => ir(i)}
              className="flex w-full items-center gap-3 px-4 py-2.5 text-left"
              style={sel === i ? { background: "var(--surface)" } : undefined}
            >
              <span className="min-w-0 flex-1 truncate text-sm text-zinc-100">{c.full_name}</span>
              <StatusBadge status={c.status} />
            </button>
          ))}

          {accesos.length > 0 && (
            <>
              {resultados.length > 0 && (
                <div className="mx-4 my-1 border-t" style={{ borderColor: "var(--line)" }} />
              )}
              {accesos.map((a, j) => {
                const i = resultados.length + j;
                const Icon = a.icon;
                return (
                  <button
                    key={a.id}
                    onMouseEnter={() => setSel(i)}
                    onClick={() => ir(i)}
                    className="flex w-full items-center gap-3 px-4 py-2.5 text-left"
                    style={sel === i ? { background: "var(--surface)" } : undefined}
                  >
                    <Icon size={15} style={{ color: "var(--text-faint)" }} />
                    <span className="min-w-0 flex-1 truncate text-sm text-zinc-300">{a.label}</span>
                  </button>
                );
              })}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/** Estado del buscador + su atajo de teclado, para montarlo una sola vez. */
export function useBuscadorRapido() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      // ⌘K en Mac, Ctrl+K en el resto. No se roba el atajo si el coach está
      // escribiendo en un campo… salvo que sea el propio buscador.
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return { open, abrir: () => setOpen(true), cerrar: () => setOpen(false) };
}
