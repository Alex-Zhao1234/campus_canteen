import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    // 与 tsconfig.json 的 paths 保持一致
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    host: true, // WSL 下允许从 Windows 浏览器访问
    port: 5173,
    proxy: { "/api": "http://localhost:8000" },
  },
});
