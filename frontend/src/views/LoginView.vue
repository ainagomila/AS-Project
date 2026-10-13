<template>
  <div class="login-page">
    <!-- HEADER -->
    <HeaderLayout title="Kofre">
      <!-- Sobrescribo el slot "right" para que NO muestre los iconos por defecto -->
      <template #right></template>
    </HeaderLayout>

    <div class="login-content">
      <div class="wrapper">
        <form @submit.prevent="login">
          <h2>Log in</h2>

          <!-- DNI -->
          <div class="input-field">
            <label for="dni-input">Enter your dni</label>
            <div class="input-box">
              <input
                id="dni-input"
                data-testid="login-dni-input"
                v-model="dni"
                type="text"
                placeholder="e.g. 12345678A"
                required
              />
              <span class="border-anim"></span>
            </div>
          </div>

          <!-- PASSWORD -->
          <div class="input-field">
            <label for="password-input">Enter your password</label>
            <div class="input-box with-eye">
              <input
                id="password-input"
                data-testid="login-password-input"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                placeholder="••••••••"
                required
              />
              <button
                type="button"
                class="eye-btn"
                @click="showPassword = !showPassword"
              >
                <component :is="showPassword ? EyeOff : Eye" class="eye-icon" />
              </button>
              <span class="border-anim"></span>
            </div>
          </div>

          <!-- Remember + Forgot password -->
          <div class="forget">
            <label for="remember">
              <input id="remember" v-model="remember" type="checkbox" />
              <p>Remember me</p>
            </label>

            <button type="button" class="forgot-btn" @click="openForgot">
              Forgot password?
            </button>
          </div>

          <!-- Login button -->
          <button
            type="submit"
            class="login-btn"
            data-testid="login-submit-btn"
          >
            Log In
          </button>

          <!-- Register -->
          <div class="register">
            <p>
              Don't have an account?
              <RouterLink to="/signup">Register</RouterLink>
            </p>
          </div>
        </form>
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
import { RouterLink, useRouter } from 'vue-router'
import HeaderLayout from '@/components/layout/HeaderLayout.vue'
import ForgotPasswordModal from '@/components/modals/ForgotPasswordModal.vue'
import { loginUser, resetPassword } from '@/api/authService'
import { useUserStore } from '@/stores/user'
import { Eye, EyeOff } from 'lucide-vue-next'

const dni = ref('')
const password = ref('')
const remember = ref(false)
const showPassword = ref(false)

const showForgot = ref(false)
const resetSaving = ref(false)

const router = useRouter()
const userStore = useUserStore()

/* ==================== REMEMBER INIT ==================== */
onMounted(() => {
  if (localStorage.getItem('remember') === '1') {
    remember.value = true

    const savedDni = localStorage.getItem('lastDni')
    if (savedDni) {
      dni.value = savedDni
    }
  }
})

/* ==================== LOGIN ==================== */

async function login() {
  try {
    if (!dni.value || !password.value) {
      alert('Please enter your credentials')
      return
    }

    const trimmedDni = dni.value.trim()

    const loginRes = await loginUser(trimmedDni, password.value)
    userStore.login(trimmedDni, loginRes)

    // Guardar flag de remember
    localStorage.setItem('remember', remember.value ? '1' : '0')

    // Guardar o borrar el DNI según el checkbox
    if (remember.value) {
      localStorage.setItem('lastDni', trimmedDni)
    } else {
      localStorage.removeItem('lastDni')
    }

    router.push('/dashboard')
  } catch (error) {
    console.error('Login error:', error)
    alert(error?.response?.data?.message || 'Invalid credentials')
  }
}

/* ==================== FORGOT PASSWORD ==================== */

function openForgot() {
  showForgot.value = true
}

function closeForgot() {
  showForgot.value = false
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

    // 1) Cambiar la contraseña vía BE
    await resetPassword(modalDni, pin, newPassword)

    // 2) Login automático con la nueva contraseña
    const loginRes = await loginUser(modalDni, newPassword)
    userStore.login(modalDni, loginRes)

    // 3) Opcional: sincronizar campo de DNI del formulario
    dni.value = modalDni
    password.value = '' // por seguridad, no dejamos la nueva en el input

    // 4) Cerrar modal y redirigir al dashboard
    closeForgot()
    router.push('/dashboard')
  } catch (error) {
    console.error('Error resetting password', error)

    const status = error?.response?.status

    if (status === 404) {
      // ALWAYS English
      alert('User not found.')
    } else if (status === 400 || status === 401 || status === 403 || status === 422) {
      // ALWAYS English, ignore backend message
      alert('The PIN is incorrect.')
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

/* INPUT FIELD */
.input-field {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  margin: 12px 0;
}

/* Input container */
.input-box {
  width: 100%;
  position: relative;
}

/* Input */
.input-box input {
  width: 100%;
  height: 42px;
  background: transparent;
  border-radius: 10px;
  border: 2px solid rgba(255, 255, 255, 0.25);
  padding: 0 12px;
  color: #fff;
  outline: none;
  transition:
    border-color 0.25s ease,
    background-color 0.25s ease;
}

/* Focus input (blanco a negro suave) */
.input-box input:focus {
  border-color: transparent;
  background: rgba(0, 0, 0, 0.15);
}

/* Borde dorado animado */
.border-anim {
  pointer-events: none;
  position: absolute;
  inset: 0;
  border-radius: 10px;
  border: 2px solid #b79b58;
  clip-path: inset(0 100% 0 0);
  transition: clip-path 0.4s ease-in-out;
}

.input-box input:focus + .border-anim {
  clip-path: inset(0 0 0 0);
}

/* ===========================
   PLACEHOLDERS ITALIAN STYLE
   =========================== */

/* Placeholder  */
.input-box input::placeholder {
  color: rgba(255, 255, 255, 0.45);
  font-size: 0.9rem;
  opacity: 1;
  font-style: italic;
}

/* Atenuación al hacer focus */
.input-box input:focus::placeholder {
  color: rgba(255, 255, 255, 0.25);
}

/* Placeholder password con separación */
.input-box input[type='password']::placeholder {
  letter-spacing: 3px;
}

/* REMEMBER + FORGOT */
.forget {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 25px 0 35px;
}

.forget label {
  display: flex;
  align-items: center;
}

.forget p {
  margin-left: 8px;
}

/* Botón "Forgot password?" */
.forgot-btn {
  background: transparent;
  border: none;
  color: #efefef;
  cursor: pointer;
  font-size: 0.95rem;
  padding: 0;
}

.forgot-btn:hover {
  text-decoration: underline;
}

/* LOGIN BUTTON */
.login-btn {
  width: 100%;
  height: 48px;
  border-radius: 10px;
  border: 2px solid rgba(183, 155, 88, 0.45);
  background: transparent;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition:
    background-color 0.25s ease,
    border-color 0.25s ease,
    color 0.25s ease,
    transform 0.2s ease,
    box-shadow 0.25s ease;
}

.login-btn:hover {
  background: #b79b58;
  border-color: #b79b58;
  color: #000;
  transform: translateY(-2px);
  box-shadow: 0 4px 14px rgba(183, 155, 88, 0.4);
}

/* REGISTER */
.register {
  margin-top: 20px;
  font-size: 0.85rem;
}

.register a {
  color: #efefef;
}

.register a:hover {
  text-decoration: underline;
}

/* ======================
   SOLO AÑADIDO PARA EL OJO
   ====================== */

.input-box.with-eye {
  position: relative;
}

.eye-btn {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  border: none;
  padding: 0;
  cursor: pointer;
}

.eye-icon {
  width: 20px;
  height: 20px;
  display: block;
}
</style>
