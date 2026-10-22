import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const viteEnv = loadEnv(mode, ".", "");
  const backendTarget = viteEnv.VITE_DEV_BACKEND_URL || "http://localhost:8000";

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        "@": "/src"
      }
    },
    server: {
      proxy: {
        "/api": {
          target: backendTarget,
          changeOrigin: true
        },
        "/ws": {
          target: backendTarget,
          ws: true,
          changeOrigin: true
        }
      }
    }
  };
});
