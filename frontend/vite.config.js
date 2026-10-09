import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

const API_PROXY_TARGET = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8080'

// https://vite.dev/config/
// TODO: Re‑enable `vite-plugin-vue-devtools` once it is safe to use in the current Node/Vite setup.
export default defineConfig({
  plugins: [
    vue({
      template: {
        compilerOptions: {
          // Preserve data-testid and other data attributes in production builds
          isCustomElement: (_tag) => false, // Don't skip any elements
          nodeTransforms: [],
        },
      },
    }),
    tailwindcss(),
  ],
  build: {
    // Ensure attributes are not removed during minification
    minify: 'terser',
    terserOptions: {
      compress: {
        // Preserve attribute values
        keep_fargs: true,
        keep_fnames: true,
      },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  server: {
    proxy: {
      '/api': {
        target: API_PROXY_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },

  test: {
    environment: 'jsdom',
    environmentMatchGlobs: [
      ['src/test/integration/**', 'node'],
    ],
    globals: true,
    setupFiles: ['./src/test/setup.js'],
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/cypress/**',
      '**/.{idea,git,cache,output,temp}/**',
      '**/{karma,rollup,webpack,vite,vitest,jest,ava,babel,nyc,cypress,tsup,build}.config.*',
      '**/e2e/**',
    ],
  },
})
