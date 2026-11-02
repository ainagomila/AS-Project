import { fileURLToPath, URL } from 'node:url'
import fs from 'node:fs'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

const HTTPS_CERT = process.env.VITE_HTTPS_CERT || '../backend/.certs/localhost.pem'
const HTTPS_KEY = process.env.VITE_HTTPS_KEY || '../backend/.certs/localhost-key.pem'
const configuredApiProxyTarget = process.env.VITE_API_PROXY_TARGET
const ROOT_CA = path.join(path.dirname(HTTPS_CERT), 'rootCA.pem')
const PROXY_CA = fs.existsSync(ROOT_CA) ? ROOT_CA : HTTPS_CERT
const certificateFilesExist =
  fs.existsSync(HTTPS_CERT) && fs.existsSync(HTTPS_KEY)
const httpsRequested =
  process.env.VITE_HTTPS === 'true' ||
  configuredApiProxyTarget?.startsWith('https://') ||
  (!configuredApiProxyTarget &&
    process.env.VITE_HTTPS !== 'false' &&
    certificateFilesExist)

if (httpsRequested && !certificateFilesExist) {
  throw new Error(
    `HTTPS is enabled, but the certificate files were not found: ${HTTPS_CERT} and ${HTTPS_KEY}`,
  )
}

const httpsEnabled = httpsRequested
const API_PROXY_TARGET =
  configuredApiProxyTarget ||
  (httpsEnabled ? 'https://localhost:8080' : 'http://localhost:8080')

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
        secure: httpsEnabled,
        ...(httpsEnabled ? { ca: fs.readFileSync(PROXY_CA) } : {}),
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
    ...(httpsEnabled
      ? {
          https: {
            cert: fs.readFileSync(HTTPS_CERT),
            key: fs.readFileSync(HTTPS_KEY),
          },
        }
      : {}),
  },

  test: {
    environment: 'jsdom',
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
