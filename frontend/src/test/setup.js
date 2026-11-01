import { afterEach, beforeEach, vi } from 'vitest'

const REMOTE_API_BASE_URL = 'https://localhost:8080/'

if (typeof import.meta !== 'undefined' && import.meta?.env) {
  import.meta.env.VITE_API_BASE_URL = REMOTE_API_BASE_URL
  import.meta.env.DEV = false
  import.meta.env.PROD = true
  import.meta.env.MODE = 'production'
}

if (typeof process !== 'undefined') {
  process.env.VITE_API_BASE_URL = REMOTE_API_BASE_URL
  process.env.NODE_ENV = process.env.NODE_ENV ?? 'test'
}

// Ensure alert calls stay assertable during tests
const alertMock = vi.fn()
globalThis.alert = alertMock

// ResizeObserver stub for components relying on it
if (!('ResizeObserver' in globalThis)) {
  globalThis.ResizeObserver = class {
    observe() {
      /* noop */
    }
    unobserve() {
      /* noop */
    }
    disconnect() {
      /* noop */
    }
  }
}

// requestAnimationFrame fallback to timers
if (!('requestAnimationFrame' in globalThis)) {
  globalThis.requestAnimationFrame = (cb) => setTimeout(cb, 0)
}

if (!('cancelAnimationFrame' in globalThis)) {
  globalThis.cancelAnimationFrame = (id) => clearTimeout(id)
}

// Basic matchMedia stub for components that may query it
if (!('matchMedia' in globalThis)) {
  globalThis.matchMedia = () => ({
    matches: false,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  })
}

if (!('localStorage' in globalThis) || typeof globalThis.localStorage?.clear !== 'function') {
  const storage = new Map()

  globalThis.localStorage = {
    getItem: (key) => (storage.has(key) ? storage.get(key) : null),
    setItem: (key, value) => {
      storage.set(key, String(value))
    },
    removeItem: (key) => {
      storage.delete(key)
    },
    clear: () => {
      storage.clear()
    },
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  alertMock.mockClear()
})

afterEach(() => {
  localStorage.clear()
})
