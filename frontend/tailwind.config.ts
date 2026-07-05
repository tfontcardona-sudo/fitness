import type { Config } from "tailwindcss";

// Tokens de la PARTE H: app oscura técnica.
// Los colores de marca configurables (brand_config) se aplican en runtime
// vía variables CSS; estos son los defaults premium.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: { DEFAULT: "var(--surface)", raised: "var(--surface-raised)" },
        accent: "var(--brand-accent, #E8833A)",
        line: "var(--line)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
