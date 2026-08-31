import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, getToken } from "../lib/api";
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

  const aplica = (colorPrimary: string, colorSecondary: string) => {
    document.documentElement.style.setProperty("--brand-accent", colorPrimary);
    document.documentElement.style.setProperty("--brand-accent-2", colorSecondary);
  };

  const load = () => {
    // SIN SESIÓN (pantalla de login) se pide la marca PÚBLICA: el endpoint del
    // panel exige JWT, así que antes devolvía 401 —dos por carga, ensuciando
    // el log— y el login salía con los colores y el nombre por defecto en vez
    // de con la marca del coach.
    if (!getToken()) {
      api.publicLanding()
        .then((l) => {
          setBrand({ ...(l as any), portal_theme: "dark" } as BrandConfigOut);
          aplica(l.color_primary, l.color_secondary);
        })
        .catch(() => { /* sin marca todavía: quedan los defaults del CSS */ });
      return;
    }
    api
      .getBrand()
      .then((b) => {
        setBrand(b);
        aplica(b.color_primary, b.color_secondary);
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
