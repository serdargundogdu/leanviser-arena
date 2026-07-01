import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// v0.1: 2D placeholder lobby only. No Three.js / 3D (deferred to v2.x).
export default defineConfig({
  plugins: [react()],
});
