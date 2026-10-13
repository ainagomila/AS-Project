const DEFAULT_FRONTEND_URL = 'http://127.0.0.1:4173'
const DEFAULT_API_URL = 'http://localhost:8080'

export const FRONTEND_BASE_URL = (process.env.E2E_BASE_URL ?? DEFAULT_FRONTEND_URL).replace(/\/$/, '')
export const API_BASE_URL = (process.env.E2E_API_BASE_URL ?? DEFAULT_API_URL).replace(/\/$/, '')

