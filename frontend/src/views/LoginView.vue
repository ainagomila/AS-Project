<template>
  <div class="login-page">
    <!-- HEADER -->
    <HeaderLayout title="Kofre">
      <!-- Sobrescribo el slot "right" para que NO muestre los iconos por defecto -->
      <template #right></template>
    </HeaderLayout>

    <div class="login-content">
      <div class="wrapper">
        <h2>Log in</h2>
        <p class="login-hint">Redirecting to the secure sign-in page…</p>
      </div>
    </div>

    <!-- MODAL FORGOT PASSWORD -->
    <ForgotPasswordModal
      v-if="showForgot"
      :saving="resetSaving"
      @close="closeForgot"
      @submit="handleForgotSubmit"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import HeaderLayout from '@/components/layout/HeaderLayout.vue'
import ForgotPasswordModal from '@/components/modals/ForgotPasswordModal.vue'
import { resetPassword } from '@/api/authService'
import { userManager } from '@/api/oidc'

const showForgot = ref(false)
const resetSaving = ref(false)

const route = useRoute()

/* ==================== LOGIN ==================== */

// Only same-site paths are accepted, so the query cannot send people elsewhere.
function safeRedirect(value) {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//')
    ? value
    : '/dashboard'
}

async function login() {
  try {
    await userManager.signinRedirect({ state: { redirect: safeRedirect(route.query.redirect) } })
  } catch (error) {
    console.error('Login error:', error?.message)
    alert('Could not start the sign-in. Please try again.')
  }
}

// /login goes straight to the sign-in page; /login?forgot=1 opens the reset modal first.
onMounted(() => {
  if (route.query.forgot) {
    showForgot.value = true
    return
  }
  login()
})

/* ==================== FORGOT PASSWORD ==================== */

function closeForgot() {
  showForgot.value = false
  login()
}

/**
 * payload viene del modal:
 * {
 *   dni: string,
 *   newPassword: string,
 *   pin: string
 * }
 */
async function handleForgotSubmit(payload) {
  const { dni: modalDni, newPassword, pin } = payload

  try {
    resetSaving.value = true

    await resetPassword(modalDni, pin, newPassword)

    showForgot.value = false
    alert('Password updated. Please log in with your new password.')
    await login()
  } catch (error) {
    console.error('Error resetting password', error?.message)

    const status = error?.response?.status

    if (status === 429) {
      alert('Too many attempts. Try again later.')
    } else if (status === 400 || status === 401 || status === 403 || status === 422) {
      alert('The DNI or PIN is incorrect.')
    } else {
      alert('Unexpected error while resetting password.')
    }
  } finally {
    resetSaving.value = false
  }
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@200;300;400;500;600;700&display=swap');

:root {
  --header-h: 65px;
}

/* RESET */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  font-family: 'Open Sans', sans-serif;
}

/* PAGE */
.login-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: #171717;
  color: #fff;
}

.login-content {
  min-height: calc(100vh - var(--header-h));
  display: flex;
  align-items: center;
  justify-content: center;
  padding-top: 100px;
}

/* WRAPPER */
.wrapper {
  width: 450px;
  padding: 40px;
  text-align: center;
  border: 2px solid #b79b58;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(12px);
  border-radius: 22px;
  box-shadow:
    0 6px 26px rgba(183, 155, 88, 0.2),
    0 0 0 1px rgba(255, 255, 255, 0.03);
  transition:
    background-color 0.25s ease,
    transform 0.25s ease;
}

.wrapper:hover,
.wrapper:focus-within {
  background: rgba(255, 255, 255, 0.1);
  transform: translateY(-3px);
}

/* TITLE */
h2 {
  font-size: 2rem;
  margin-bottom: 20px;
  font-weight: 600;
}
</style>
