// src/api/apiClient.js
import axios from 'axios'

const DEV_API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'
const PROD_API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'
const API_BASE_URL = import.meta.env.DEV ? DEV_API_BASE : PROD_API_BASE

console.log('[apiClient] BASE URL →', API_BASE_URL)

const apiClient = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use((config) => {
  const url = config.url || ''
  const isAbsolute = /^https?:\/\//i.test(url) || url.startsWith('//')
  if (!isAbsolute) {
    const normalizedBase = API_BASE_URL.replace(/\/+$/, '') || ''
    const normalizedPath = url.startsWith('/') ? url : `/${url}`
    config.url = `${normalizedBase}${normalizedPath}` || normalizedPath
  }

  return config
})

apiClient.interceptors.request.use((config) => {
  if (!globalThis.localStorage) {
    return config
  }

  const token = globalThis.localStorage.getItem('authToken')

  if (!token) {
    return config
  }

  config.headers = config.headers ?? {}
  config.headers.Authorization = `Bearer ${token}`

  return config
})

export default apiClient
