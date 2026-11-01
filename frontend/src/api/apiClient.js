// src/api/apiClient.js
import axios from 'axios'
import { userManager } from './oidc'

const DEV_API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'
const PROD_API_BASE = import.meta.env.VITE_API_BASE_URL || 'https://localhost:8080'
const API_BASE_URL = import.meta.env.DEV ? DEV_API_BASE : PROD_API_BASE

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

// The access token is held in memory by the OIDC UserManager; nothing is read from storage.
apiClient.interceptors.request.use(async (config) => {
  const user = await userManager.getUser()

  if (!user || user.expired) {
    return config
  }

  config.headers = config.headers ?? {}
  config.headers.Authorization = `Bearer ${user.access_token}`

  return config
})

export default apiClient
