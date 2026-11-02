import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// Session state lives in memory only. The access token is held by the
// OIDC UserManager (src/api/oidc.js), never stored by the app itself.
export const useUserStore = defineStore('user', () => {
  const dni = ref(null)
  const isAuthenticated = ref(false)
  const userData = ref(null)

  const name = computed(() => userData.value?.name ?? '')
  const email = computed(() => userData.value?.email ?? '')
  const phone = computed(() => userData.value?.phone ?? '')
  const birthday = computed(() => userData.value?.birthday ?? '')
  const gender = computed(() => userData.value?.gender ?? '')
  const pin = computed(() => userData.value?.pin ?? '')
  // Display only: what each role may do is decided by the backend's XACML policy.
  const role = computed(
    () => userData.value?.role ?? (userData.value?.admin === true ? 'admin' : 'customer'),
  )
  const isAdmin = computed(() => role.value === 'admin')
  const isAuditor = computed(() => role.value === 'auditor')
  const isOperations = computed(() => role.value === 'operations')
  const isStaff = computed(() => isAdmin.value || isAuditor.value || isOperations.value)

  /**
   * Marks the user as signed in.
   * @param {string} userDni
   * @param {object} profile
   */
  function login(userDni, profile) {
    dni.value = userDni
    userData.value = profile ?? null
    isAuthenticated.value = true
  }

  /** Clears the in-memory session. The full sign-out (revocation) comes in step 6. */
  function logout() {
    dni.value = null
    userData.value = null
    isAuthenticated.value = false
  }

  return {
    dni,
    isAuthenticated,
    userData,
    name,
    email,
    phone,
    birthday,
    gender,
    pin,
    role,
    isAdmin,
    isAuditor,
    isOperations,
    isStaff,
    login,
    logout,
  }
})
