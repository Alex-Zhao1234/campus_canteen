import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // WSL 下允许从 Windows 浏览器访问
    port: 5173,
    proxy: { "/api": "http://localhost:8000" },
  },
});
