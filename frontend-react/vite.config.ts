import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      // El manifest es el estático de public/manifest.webmanifest (enlazado en
      // index.html); el plugin solo genera el service worker.
      manifest: false,
      devOptions: { enabled: true },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,webp,webmanifest}'],
        // Las hojas de diseño de la mascota (public/mascota/*.png) son assets de
        // marketing >1 MB que la app no usa en pantalla (solo consume los .webp
        // y favicon-64.png). Se excluyen del precache para no superar el ~2 MiB
        // del límite de Workbox; siguen sirviéndose por red. Se enlistan
        // explícitamente para no tocar favicon-64.png ni los .webp.
        globIgnores: [
          '**/mascota/Design_Sheet.png',
          '**/mascota/Facial_Expressions.png',
          '**/mascota/Illustrations_Sheet.png',
          '**/mascota/Interactions_Sheet.png',
          '**/mascota/Marketing_Sheet.png',
          '**/mascota/Poses_Sheet.png',
          '**/mascota/Smarty v1.0.png',
          '**/mascota/Smarty_404.png',
          '**/mascota/Smarty_favicon.png',
          '**/mascota/Smarty_waving.png',
        ],
        navigateFallback: '/index.html',
        cleanupOutdatedCaches: true,
      },
    }),
  ],
})
