<template>
  <div class="modal-overlay" @click.self="emit('close')">
    <div class="modal">
      <header class="modal-header">
        <h3>Reset password</h3>
        <button class="close" type="button" @click="emit('close')">✕</button>
      </header>

      <form class="modal-body" @submit.prevent="submit">
        <!-- DNI -->
        <div class="field field--full">
          <label>DNI</label>
          <div class="input-box">
            <input
              v-model.trim="form.dni"
              placeholder="12345678A"
              @input="validateDni"
              required
            />
            <span class="border-anim"></span>
          </div>
          <small v-if="errors.dni" class="err">{{ errors.dni }}</small>
        </div>

        <!-- Nueva contraseña -->
        <div class="field field--full">
          <label>New password</label>
          <div class="input-box">
            <input
              v-model="form.password"
              type="password"
              placeholder="••••••••"
              @input="validatePassword"
              required
            />
            <span class="border-anim"></span>
          </div>
          <small v-if="errors.password" class="err">{{ errors.password }}</small>
        </div>

        <!-- Confirmar contraseña -->
        <div class="field field--full">
          <label>Confirm new password</label>
          <div class="input-box">
            <input
              v-model="form.confirmPassword"
              type="password"
              placeholder="••••••••"
              @input="validateConfirmPassword"
              required
            />
            <span class="border-anim"></span>
          </div>
          <small v-if="errors.confirmPassword" class="err">
            {{ errors.confirmPassword }}
          </small>
        </div>

        <!-- PIN -->
        <div class="field field--full">
          <label>6-digit Security PIN</label>
          <div class="input-box">
            <input
              v-model.trim="form.pin"
              type="password"
              maxlength="6"
              placeholder="••••••"
              @input="validatePin"
              required
            />
            <span class="border-anim"></span>
          </div>
          <small v-if="errors.pin" class="err">{{ errors.pin }}</small>
        </div>

        <footer class="modal-footer">
          <button type="button" class="btn ghost" @click="emit('close')">
            Cancel
          </button>
          <button
            type="submit"
            class="btn primary"
            :disabled="saving || !canSubmit"
          >
            {{ saving ? 'Saving...' : 'Save new password' }}
          </button>
        </footer>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed, toRef } from 'vue'

const props = defineProps({
  saving: { type: Boolean, default: false },
})
const saving = toRef(props, 'saving')

const emit = defineEmits(['close', 'submit'])

const form = reactive({
  dni: '',
  password: '',
  confirmPassword: '',
  pin: '',
})

const errors = reactive({
  dni: '',
  password: '',
  confirmPassword: '',
  pin: '',
})

/* ==================== VALIDADORES ==================== */

function validateDni() {
  const dniRegex = /^\d{8}[A-Za-z]$/
  const value = (form.dni || '').trim()
  form.dni = value

  if (!dniRegex.test(value)) {
    errors.dni = 'Invalid DNI format.'
  } else {
    errors.dni = ''
  }
}

function validatePassword() {
  const value = form.password || ''

  const hasLower = /[a-z]/.test(value)          // al menos una minúscula
  const hasUpper = /[A-Z]/.test(value)          // al menos una MAYÚSCULA
  const hasNumber = /\d/.test(value)            // al menos un número
  const hasSpecial = /[^A-Za-z0-9]/.test(value) // al menos un carácter especial
  const longEnough = value.length >= 6          // mínimo 6 caracteres

  if (!longEnough)
    errors.password = 'At least 8 characters.'
  else if (!hasLower)
    errors.password = 'Must include at least one lowercase letter.'
  else if (!hasUpper)
    errors.password = 'Must include at least one uppercase letter.'
  else if (!hasNumber)
    errors.password = 'Must include at least one number.'
  else if (!hasSpecial)
    errors.password = 'Must include at least one special character.'
  else
    errors.password = ''

  // Mantener sincronizada la confirmación
  if (form.confirmPassword) {
    validateConfirmPassword()
  }
}

function validateConfirmPassword() {
  const pass = form.password || ''
  const confirm = form.confirmPassword || ''

  if (confirm.length > 0 && confirm !== pass) {
    errors.confirmPassword = 'Passwords do not match.'
  } else {
    errors.confirmPassword = ''
  }
}

function validatePin() {
  const value = (form.pin || '').trim()
  form.pin = value

  if (!/^\d{6}$/.test(value)) {
    errors.pin = 'PIN must be 6 digits.'
  } else {
    errors.pin = ''
  }
}

function validateAll() {
  validateDni()
  validatePassword()
  validateConfirmPassword()
  validatePin()

  return !errors.dni && !errors.password && !errors.confirmPassword && !errors.pin
}

/* ==================== CAN SUBMIT ==================== */

const canSubmit = computed(() => {
  const dniOk = /^\d{8}[A-Za-z]$/.test((form.dni || '').trim())
  const passVal = form.password || ''

  const hasLower = /[a-z]/.test(passVal)
  const hasUpper = /[A-Z]/.test(passVal)
  const hasNumber = /\d/.test(passVal)
  const hasSpecial = /[^A-Za-z0-9]/.test(passVal)
  const longEnough = passVal.length >= 6

  const passOk = longEnough && hasLower && hasUpper && hasNumber && hasSpecial

  const confirmOk =
    (form.confirmPassword || '').length > 0 &&
    form.confirmPassword === form.password

  const pinOk = /^\d{6}$/.test((form.pin || '').trim())

  const noErrors =
    !errors.dni && !errors.password && !errors.confirmPassword && !errors.pin

  return dniOk && passOk && confirmOk && pinOk && noErrors
})

/* ==================== SUBMIT ==================== */

function submit() {
  if (!validateAll()) return

  emit('submit', {
    dni: form.dni.trim(),
    newPassword: form.password,
    pin: form.pin.trim(),
  })
}
</script>

<style scoped>
/* Overlay */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

/* Card */
.modal {
  width: min(560px, 92vw);
  background: #1e1e1e;
  color: #f5f5f5;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  box-shadow: 0 20px 80px rgba(0, 0, 0, 0.6);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.close {
  background: transparent;
  border: 0;
  color: #aaa;
  font-size: 18px;
  cursor: pointer;
}

.modal-body {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field label {
  font-size: 0.9rem;
  color: #e8e8e8;
}

/* Wrapper para animación */
.input-box {
  position: relative;
}

.field input {
  width: 100%;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  color: #fff;
  padding: 10px 12px;
  outline: none;
  font-size: 0.95rem;
  transition:
    border-color 0.2s ease,
    background-color 0.2s ease,
    box-shadow 0.2s ease;
}

/* Placeholder estilo signup/login */
.field input::placeholder {
  color: #bfbfbf;
  opacity: 0.55;
  font-style: italic;
}

.field input:focus::placeholder {
  color: rgba(191, 191, 191, 0.3);
}

/* Borde dorado animado: aparece ascendente, desaparece de golpe */
.border-anim {
  pointer-events: none;
  position: absolute;
  inset: 0;
  border-radius: 10px;
  border: 2px solid #b79b58;
  clip-path: inset(0 100% 0 0); /* oculto hacia la derecha */
  transition: none;             /* sin animación por defecto */
}

/* cuando el input está en foco, mostramos el borde animado */
.input-box:focus-within .border-anim {
  clip-path: inset(0 0 0 0);
  transition: clip-path 0.4s ease-in-out;
}

/* además puedes mantener el foco dorado suave */
.field input:focus {
  border-color: transparent;
  background: rgba(255, 255, 255, 0.08);
  box-shadow: 0 0 0 2px rgba(201, 178, 106, 0.35);
}

.err {
  color: #ffb4b4;
  font-size: 0.8rem;
}

.modal-footer {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn {
  padding: 10px 14px;
  border-radius: 999px;
  border: 1px solid transparent;
  cursor: pointer;
  font-size: 0.9rem;
}

.btn.ghost {
  background: transparent;
  color: #ddd;
  border-color: rgba(255, 255, 255, 0.2);
}

.btn.primary {
  background: #fff;
  color: #111;
  font-weight: 700;
  transition:
    background-color 0.25s ease,
    color 0.25s ease,
    transform 0.2s ease,
    box-shadow 0.25s ease;
}

/* HOVER dorado */
.btn.primary:hover:not(:disabled) {
  background: #b79b58;       /* dorado */
  color: #000;
  transform: translateY(-2px);
  box-shadow: 0 4px 14px rgba(183, 155, 88, 0.4);
}

.btn.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}
</style>
