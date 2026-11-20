import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', ['API_PROXY_TARGET', 'WATCH_POLLING'])
  const apiTarget = env.API_PROXY_TARGET || 'http://127.0.0.1:8000'
  return {
    plugins: [react(), tailwindcss()],
    base: './',
    server: {
      allowedHosts: ['frontend'],
      watch: {
        usePolling: env.WATCH_POLLING === 'true',
        interval: 750,
        ignored: ['**/.npm-cache/**', '**/.tmp/**', '**/dist/**', '**/*.tsbuildinfo'],
      },
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          timeout: 60000,
          proxyTimeout: 60000,
        },
        '/health': apiTarget,
      },
    },
  }
})
