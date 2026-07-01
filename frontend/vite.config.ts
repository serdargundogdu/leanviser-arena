import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// v0.2: 2D debrief UI. No Three.js / 3D (deferred to v2.x).
// Dev proxy forwards /api to the FastAPI backend so the browser stays
// same-origin (no CORS needed). Backend must run on :8000.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
