import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // l'appel /api/* est redirigé vers le backend FastAPI
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
