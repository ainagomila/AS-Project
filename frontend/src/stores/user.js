import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const AUTH_TOKEN_KEY = 'authToken'

/**
 * Persists the provided auth token or clears it when absent.
 * @param {string | null} value
 */
function persistToken(value) {
  if (value) {
    localStorage.setItem(AUTH_TOKEN_KEY, value)
    return
  }
  localStorage.removeItem(AUTH_TOKEN_KEY)
}

export const useUserStore = defineStore('user', () => {
  const dni = ref(null)
  const isAuthenticated = ref(false)
  const userData = ref(null)
  const token = ref(null)

  /* ================================
     GETTERS (derivados del perfil)
  ==================================*/
  const name = computed(() => userData.value?.name ?? '')
  const email = computed(() => userData.value?.email ?? '')
  const phone = computed(() => userData.value?.phone ?? '')
  const birthday = computed(() => userData.value?.birthday ?? '')
  const gender = computed(() => userData.value?.gender ?? '')
  const pin = computed(() => userData.value?.pin ?? '')
  const isAdmin = computed(() => userData.value?.admin === true)

  /**
   * Logs in a user updating the store and localStorage snapshots.
   * @param {string} userDni
   * @param {object} sessionPayload
   */
  function login(userDni, sessionPayload) {
    dni.value = userDni
    token.value = sessionPayload?.token ?? null
    userData.value = sessionPayload?.user ?? sessionPayload ?? null
    isAuthenticated.value = true

    localStorage.setItem('userDni', userDni)
    localStorage.setItem('isAuthenticated', 'true')
    persistToken(token.value)

    if (userData.value) {
      localStorage.setItem('userData', JSON.stringify(userData.value))
      return
    }

    localStorage.removeItem('userData')
  }

  /**
   * Logs out clearing store state and persisted session data.
   */
  function logout() {
    dni.value = null
    token.value = null
    userData.value = null
    isAuthenticated.value = false

    localStorage.removeItem('userDni')
    localStorage.removeItem('isAuthenticated')
    localStorage.removeItem('userData')
    persistToken(null)
  }

  /**
   * Hydrates the store from storage if a session snapshot exists.
   */
  function initFromStorage() {
    const storedDni = localStorage.getItem('userDni')
    const storedAuth = localStorage.getItem('isAuthenticated')

    if (!storedDni || storedAuth !== 'true') {
      return
    }

    dni.value = storedDni
    isAuthenticated.value = true
    token.value = localStorage.getItem(AUTH_TOKEN_KEY)

    const storedUserData = localStorage.getItem('userData')

    if (!storedUserData) {
      userData.value = null
      return
    }

    try {
      userData.value = JSON.parse(storedUserData)
    } catch (e) {
      userData.value = null
      console.error('Error parsing stored user data:', e)
    }
  }

  return {
    dni,
    isAuthenticated,
    userData,
    token,

    // getters
    name,
    email,
    phone,
    birthday,
    gender,
    pin,
    isAdmin,

    login,
    logout,
    initFromStorage,
  }
})
