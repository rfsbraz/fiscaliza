import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { copyFileSync } from 'fs'

// Deep links (/deputados/123) must load the app on any static host. Most hosts serve 404.html
// for a path with no file (GitHub Pages, Cloudflare Pages, S3 or CloudFront error document,
// nginx error_page), so the build writes index.html again as 404.html. See docs/STATIC_EXPORT.md.
const spaFallback = () => ({
  name: 'spa-fallback-404',
  apply: 'build',
  writeBundle(options) {
    copyFileSync(path.join(options.dir, 'index.html'), path.join(options.dir, '404.html'))
  },
})

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), spaFallback()],
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
    // Vite's default host check applies (localhost and IP addresses). To reach the dev server
    // through a tunnel, add its host to server.allowedHosts locally and don't commit it.
    // No proxy: the site reads the static export. Render it into public/api (gitignored) and
    // the dev server serves it at /api, as the static host does. See docs/STATIC_EXPORT.md.
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
