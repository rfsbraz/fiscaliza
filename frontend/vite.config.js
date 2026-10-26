import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
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
  plugins: [react(), tailwindcss(), spaFallback()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  build: {
    outDir: './dist',
    emptyOutDir: true,
    // Fonts stay files: the CSP's font-src is 'self' only, which blocks a data: URI font.
    assetsInlineLimit: (file) => (file.endsWith('.woff2') ? false : undefined),
    // Vite 8 bundles with Rolldown, which dropped the object form of manualChunks.
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            { name: 'vendor', test: /[\\/]node_modules[\\/](react|react-dom|react-router|react-router-dom)[\\/]/, priority: 3 },
            { name: 'charts', test: /[\\/]node_modules[\\/]recharts[\\/]/, priority: 2 },
            { name: 'animation', test: /[\\/]node_modules[\\/]framer-motion[\\/]/, priority: 1 },
          ],
        },
      },
    },
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
