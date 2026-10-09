import apiClient from './apiClient'

const AUTH_TOKEN_KEY = 'authToken'

/**
 * Persists or clears the auth token so every request can reuse it.
 * @param {string | null | undefined} token
 */
function persistToken(token) {
  if (!globalThis.localStorage) return

  if (!token) {
    globalThis.localStorage.removeItem(AUTH_TOKEN_KEY)
    return
  }

  globalThis.localStorage.setItem(AUTH_TOKEN_KEY, token)
}

/**
 * Reads the stored auth token if it exists.
 * @returns {string | null}
 */
function readStoredToken() {
  if (!globalThis.localStorage) return null
  return globalThis.localStorage.getItem(AUTH_TOKEN_KEY)
}

/**
 * Checks whether a user exists for the provided DNI.
 * @param {string} dni
 * @returns {Promise<boolean>}
 */
export async function checkUserExists(dni) {
  try {
    await apiClient.get(`/auth/exists/${encodeURIComponent(dni)}`)
    return true
  } catch (error) {
    if (error.response?.status === 404) {
      return false
    }

    console.error('Error checking user existence:', error)
    throw error
  }
}

/**
 * Authenticates a user and stores the issued token.
 * @param {string} dni
 * @param {string} password
 * @returns {Promise<{token: string, user: object}>}
 */
export async function loginUser(dni, password) {
  try {
    const { data } = await apiClient.post('/auth/login', {
      dni,
      password,
    })

    persistToken(data?.token)
    return data
  } catch (error) {
    console.error('Login fallit:', error.response?.data || error.message)
    throw error
  }
}

// Cambiar contraseña cuando NO puedes hacer login (flujo "Forgot password")
export async function resetPassword(dni, pin, newPassword) {
  try {
    const res = await apiClient.post('/auth/reset-password', {
      dni,
      pin,
      newPassword,
    })

    // El contrato dice 204 No Content → no hay body útil
    return res
  } catch (error) {
    console.error('Error resetting password:', error.response?.data || error.message)
    throw error
  }
}


/**
 * Normaliza el teléfono al formato que espera el BE:
 * +34XXXXXXXXX (sin espacios, 9 dígitos detrás del +34)
 *
 * Acepta entradas tipo:
 *  - "600123456"
 *  - "600 123 456"
 *  - "+34 600 123 456"
 *  - "+34600123456"
 */
function normalizePhoneForBackend(rawPhone) {
  if (!rawPhone) return null

  // 1. Quitamos espacios, guiones y paréntesis
  let cleaned = String(rawPhone).replace(/[\s\-()]/g, '')

  // 2. Si ya está en formato +34XXXXXXXXX
  if (/^\+34\d{9}$/.test(cleaned)) {
    return cleaned
  }

  // 3. Si empieza por +34 pero tiene cosas raras, lo consideramos inválido
  if (cleaned.startsWith('+34') && !/^\+34\d{9}$/.test(cleaned)) {
    return null
  }

  // 4. Si son 9 dígitos, asumimos número español sin prefijo
  if (/^\d{9}$/.test(cleaned)) {
    return `+34${cleaned}`
  }

  // 5. Cualquier otra cosa → inválido para nuestro caso
  return null
}

/**
 * Registers a new user and stores the issued token.
 * @param {object} formData
 * @returns {Promise<{message: string, token: string}>}
 */
export async function signupUser(formData) {
  // Normalizamos aquí sí o sí, tanto si la vista lo hace bien como si no
  const normalizedPhone = normalizePhoneForBackend(formData.phone)

  if (!normalizedPhone) {
    // Lanzamos un error claro para el componente (por ahora caerá en el catch general)
    throw new Error('INVALID_PHONE_FORMAT_FE')
  }

  const requestBody = {
    name: formData.name,
    dni: formData.dni,
    email: formData.email,
    phone: normalizedPhone, // SIEMPRE +34XXXXXXXXX
    password: formData.password,
    birthdate: formData.birthdate,
    gender: formData.gender,
    pin: formData.pin,
  }

  console.log('Request enviado a /auth/register:', requestBody)
  console.log('phone:', normalizedPhone)

  try {
    const { data } = await apiClient.post('/auth/register', requestBody)

    // Store token
    persistToken(data?.token)

    return data
  } catch (error) {
    console.error('Error registering user:', error.response?.data || error.message)
    const serverMessage = error.response?.data?.message || 'Unknown signup error.'
    throw new Error(serverMessage)
  }
}

/**
 * Logs out from the current session and clears the stored token.
 * @param {string} dni
 * @param {string} [token]
 * @returns {Promise<void>}
 */
export async function logoutSession(dni, token = readStoredToken()) {
  if (!token) return

  await apiClient.post('/auth/logout', { dni, token })
  persistToken(null)
}

/**
 * Validates the current session token with the backend.
 * @param {string} dni
 * @param {string} [token]
 * @returns {Promise<boolean>}
 */
export async function validateSession(dni, token = readStoredToken()) {
  if (!token) throw new Error('Missing session token.')

  await apiClient.post('/auth/validate', { dni, token })
  return true
}
