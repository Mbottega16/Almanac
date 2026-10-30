import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Proxies /api to the FastAPI backend during local dev (`npm run dev`).
// In production one Render web service serves both the API and the built
// frontend, so calls are same-origin (VITE_API_BASE_URL is empty; see
// backend/scripts/build_frontend.py).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
