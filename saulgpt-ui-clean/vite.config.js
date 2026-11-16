import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// SaulGPT "Clean" frontend — same backend, simpler UI.
// Runs on port 5174 so it can live side by side with the classic UI (5173).
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../dist-clean',
    emptyOutDir: true,
  },
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
