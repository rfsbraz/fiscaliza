import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: './dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          charts: ['recharts'],
          animation: ['framer-motion'],
        }
      }
    }
  },
  server: {
    host: true, // Allow external access
    allowedHosts: [
      'localhost',
      '.ngrok.io',
      '.ngrok-free.app',
      'f440ec437a42.ngrok-free.app'
    ],
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      }
    },
    watch: {
      ignored: [
        '../data/**',
        '../database/**',
        '../logs/**',
        '**/*.db',
        '**/*.log'
      ]
    }
  }
})
