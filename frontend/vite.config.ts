import path from "node:path";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// VITE_API_PROXY_TARGET가 .env.local에 있으면 그쪽으로, 없으면 배포 서버로 프록시.
// 로컬 백엔드 개발 중: .env.local에 VITE_API_PROXY_TARGET=http://localhost:8000
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxyTarget = env.VITE_API_PROXY_TARGET || "https://vulnerable-groups-rag.onrender.com";

  return {
  plugins: [react()],
  json: {
    stringify: true,
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          icons: ['lucide-react'],
        },
      },
    },
  },
  };
});
