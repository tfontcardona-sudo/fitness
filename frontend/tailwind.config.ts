import type { Config } from "tailwindcss";

// Tokens de la PARTE H: app oscura técnica.
// Los colores de marca configurables (brand_config) se aplican en runtime
// vía variables CSS; estos son los defaults premium.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0A0A0F",
        surface: { DEFAULT: "#111118", raised: "#1A1A24" },
        accent: "var(--brand-accent, #6EE7B7)",
        line: "rgba(255,255,255,0.06)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
