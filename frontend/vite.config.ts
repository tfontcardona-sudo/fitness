import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En dev, las llamadas a /api se proxyean al backend (hot-reload completo).
// En producción, Caddy hace este papel.
export default defineConfig({
  plugins: [react()],
  server: {
    // En Windows + Docker el watcher nativo no detecta cambios del bind mount;
    // el polling garantiza que el hot-reload SIEMPRE recoja las ediciones.
    watch: { usePolling: true, interval: 300 },
    proxy: {
      "/api": {
        target: process.env.VITE_API_URL || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
