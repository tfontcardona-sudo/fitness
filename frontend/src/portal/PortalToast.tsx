import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type Toast = { id: number; message: string };
const Ctx = createContext<{ push: (m: string) => void }>({ push: () => {} });

export function usePortalToast() {
  return useContext(Ctx);
}

export function PortalToastProvider({ children, light }: { children: ReactNode; light: boolean }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((message: string) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, message }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 2800);
  }, []);

  return (
    <Ctx.Provider value={{ push }}>
      {children}
      {/* pointer-events-none: el toast informa, nunca roba el tap a la nav
          inferior; role=status para que los lectores de pantalla lo anuncien. */}
      <div
        className="pointer-events-none fixed bottom-24 left-1/2 z-50 flex -translate-x-1/2 flex-col items-center gap-2"
        role="status"
        aria-live="polite"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className="animate-rise rounded-full px-4 py-2 text-sm font-medium shadow-lg"
            style={{
              background: light ? "#1a1a24" : "#fafaf9",
              color: light ? "#fafaf9" : "#1a1a24",
            }}
          >
            {t.message}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
