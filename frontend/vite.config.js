import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.SECUREPAY_API_TARGET || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: false,
      },
    },
  },
});
