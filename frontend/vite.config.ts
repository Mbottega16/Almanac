import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Proxies /api to the FastAPI backend during local dev (`npm run dev`).
// In production the frontend is deployed to Vercel and talks to the Render
// backend via VITE_API_BASE_URL (see .env.production).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
