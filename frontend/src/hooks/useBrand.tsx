import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../lib/api";
import type { BrandConfigOut } from "../types";

interface BrandState {
  brand: BrandConfigOut | null;
  reload: () => void;
}

const BrandContext = createContext<BrandState>({ brand: null, reload: () => {} });

export function useBrand(): BrandState {
  return useContext(BrandContext);
}

/**
 * Aplica la marca en runtime: el acento configurable se inyecta como variable
 * CSS (--brand-accent), de modo que toda la app y el portal reflejan al
 * instante los cambios de Settings (H.1), sin recompilar.
 */
export function BrandProvider({ children }: { children: ReactNode }) {
  const [brand, setBrand] = useState<BrandConfigOut | null>(null);

  const load = () => {
    api
      .getBrand()
      .then((b) => {
        setBrand(b);
        document.documentElement.style.setProperty("--brand-accent", b.color_primary);
      })
      .catch(() => {
        /* sin marca todavía: se mantienen los defaults del CSS */
      });
  };

  useEffect(load, []);

  return (
    <BrandContext.Provider value={{ brand, reload: load }}>{children}</BrandContext.Provider>
  );
}
