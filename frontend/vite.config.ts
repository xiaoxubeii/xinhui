import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import { inspectAttr } from 'kimi-plugin-inspect-react'

// https://vite.dev/config/
const devBase = process.env.VITE_DEV_BASE || '/'
const hmrDisabled = process.env.VITE_HMR === '0'
const usePolling = process.env.VITE_POLLING === '1' || process.env.CHOKIDAR_USEPOLLING === '1'
const pollingInterval = Number(process.env.VITE_POLLING_INTERVAL ?? process.env.CHOKIDAR_INTERVAL ?? '1000')

export default defineConfig(({ command }) => ({
  base: command === 'serve' ? devBase : '/app/',
  plugins: [inspectAttr(), react()],
  server: {
    allowedHosts: [".ngrok-free.app"],
    hmr: hmrDisabled ? false : undefined,
    watch: usePolling
      ? {
          usePolling: true,
          interval: pollingInterval,
        }
      : undefined,
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
