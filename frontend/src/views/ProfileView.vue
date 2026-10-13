<template>
  <div class="profile-page">
    <HeaderLayout title="Kofre" @click:title="goBack">
      <template #left>
        <button class="header-terms-btn" @click="goToTerms">
          Terms & Conditions
        </button>
      </template>
    </HeaderLayout>

    <div class="profile-content">
      <!-- CARD: PERSONAL INFORMATION -->
      <div class="profile-wrapper">
        <h2 class="profile-title">Personal Information</h2>
        <p class="profile-sub">
          Review your personal details. Some fields are locked for security reasons.
        </p>

        <div class="form-grid">
          <!-- Full name (readonly) -->
          <div class="form-field">
            <label>Full name</label>
            <div class="input-box readonly">
              <input v-model="form.name" type="text" disabled />
              <span class="border-anim"></span>
            </div>
          </div>

          <!-- DNI (readonly) -->
          <div class="form-field">
            <label>DNI</label>
            <div class="input-box readonly">
              <input v-model="form.dni" type="text" disabled />
              <span class="border-anim"></span>
            </div>
          </div>

          <!-- Email -->
          <div class="form-field">
            <label>Email</label>
            <div class="input-box">
              <input
                v-model="form.email"
                type="email"
                placeholder="you@example.com"
                @input="validateEmail"
              />
              <span class="border-anim"></span>
            </div>
            <p v-if="emailError" class="error-message">{{ emailError }}</p>
          </div>

          <!-- Phone -->
          <div class="form-field">
            <label>Phone Number</label>
            <div class="input-box">
              <input
                v-model="form.phone"
                type="tel"
                placeholder="+34 600 000 000"
                @input="validatePhone"
              />
              <span class="border-anim"></span>
            </div>
            <p v-if="phoneError" class="error-message">{{ phoneError }}</p>
          </div>

          <!-- Birthday -->
          <div class="form-field">
            <label>Birthday</label>
            <div class="input-box readonly">
              <input v-model="form.birthday" type="date" disabled />
              <span class="border-anim"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- CARD: SECURITY -->
      <div class="profile-wrapper">
        <h2 class="profile-title">Security</h2>
        <p class="profile-sub">
          Manage your password and PIN. Some actions require your security PIN.
        </p>

        <div class="form-grid security-grid">
          <!-- LEFT COLUMN (PASSWORDS) -->
          <div class="security-col">
            <!-- Current Password -->
            <div class="form-field">
              <label>Current Password</label>
              <div class="input-box with-eye readonly">
                <input
                  :type="showPwd.current ? 'text' : 'password'"
                  :value="showPwd.current ? currentPasswordValue : '********'"
                  disabled
                />
                <button
                  class="eye-btn"
                  @click="handleCurrentPasswordEyeClick"
                  :disabled="pinPrompt.open || savePrompt.open || isSaving"
                >
                  <component :is="showPwd.current ? EyeOff : Eye" class="eye-icon" />
                </button>
                <span class="border-anim"></span>
              </div>
            </div>

            <!-- New Password -->
            <div class="form-field">
              <label>New Password</label>
              <div class="input-box with-eye">
                <input
                  :type="showPwd.new ? 'text' : 'password'"
                  v-model="password.new"
                  placeholder="••••••••"
                  @input="validateNewPassword"
                />
                <button class="eye-btn" @click="showPwd.new = !showPwd.new">
                  <component :is="showPwd.new ? EyeOff : Eye" class="eye-icon" />
                </button>
                <span class="border-anim"></span>
              </div>
              <p v-if="passwordFormatError" class="error-message">{{ passwordFormatError }}</p>
            </div>

            <!-- Confirm Password -->
            <div class="form-field">
              <label>Confirm New Password</label>
              <div class="input-box with-eye">
                <input
                  :type="showPwd.confirm ? 'text' : 'password'"
                  v-model="password.confirm"
                  placeholder="••••••••"
                />
                <button class="eye-btn" @click="showPwd.confirm = !showPwd.confirm">
                  <component :is="showPwd.confirm ? EyeOff : Eye" class="eye-icon" />
                </button>
                <span class="border-anim"></span>
              </div>
              <p v-if="passwordMismatch" class="error-message">Passwords must match.</p>
            </div>
          </div>

          <!-- RIGHT COLUMN (PIN) -->
          <div class="security-col">
            <!-- New PIN -->
            <div class="form-field">
              <label>New PIN (6 digits)</label>
              <div class="input-box with-eye">
                <input
                  :type="showPin.new ? 'text' : 'password'"
                  v-model="pin.new"
                  maxlength="6"
                  placeholder="••••••"
                  @input="validateNewPin"
                />
                <button class="eye-btn" @click="showPin.new = !showPin.new">
                  <component :is="showPin.new ? EyeOff : Eye" class="eye-icon" />
                </button>
                <span class="border-anim"></span>
              </div>
              <p v-if="pinFormatError" class="error-message">{{ pinFormatError }}</p>
            </div>

            <!-- Confirm PIN -->
            <div class="form-field">
              <label>Confirm New PIN</label>
              <div class="input-box with-eye">
                <input
                  :type="showPin.confirm ? 'text' : 'password'"
                  v-model="pin.confirm"
                  maxlength="6"
                  placeholder="••••••"
                />
                <button class="eye-btn" @click="showPin.confirm = !showPin.confirm">
                  <component :is="showPin.confirm ? EyeOff : Eye" class="eye-icon" />
                </button>
                <span class="border-anim"></span>
              </div>
              <p v-if="pinMismatch" class="error-message">PINs must match.</p>
            </div>
          </div>
        </div>

        <!-- ACTIONS -->
        <div class="actions">
          <button
            class="btn-secondary delete-profile-btn"
            type="button"
            @click="openDeletePrompt"
            :disabled="isSaving"
          >
            Delete profile
          </button>

          <button class="btn-secondary" @click="onCancel" :disabled="isSaving">
            Cancel
          </button>

          <button
            class="btn-primary"
            @click="openSavePrompt"
            :disabled="
              isSaving ||
              !isDirty ||
              passwordMismatch ||
              pinMismatch ||
              hasFormatErrors
            "
          >
            Save changes
          </button>
        </div>
      </div>
    </div>

    <FooterLayout />

    <!-- MODAL: Reveal -->
    <div v-if="pinPrompt.open" class="modal-overlay" @click.self="closePinPrompt">
      <div class="modal modal-card pin-modal pinpad" :class="{ shake: pinRevealError }">
        <div class="modal-header">
          <Lock class="modal-icon" />
          <h3 class="modal-title">Enter 6-digit PIN</h3>
        </div>
        <p class="modal-text">Enter your PIN to reveal this field.</p>

        <div class="pin-input pin-inputs">
          <input
            v-for="(_, i) in 6"
            :key="'reveal-'+i"
            :ref="el => (pinRevealBoxes[i] = el)"
            class="pin-box"
            type="password"
            maxlength="1"
            inputmode="numeric"
            v-model="enteredPinReveal[i]"
            @input="handlePinInputReveal(i, $event)"
            @keydown.backspace.prevent="handlePinBackspaceReveal(i, $event)"
          />
        </div>

        <p v-if="pinPrompt.error" class="modal-error">{{ pinPrompt.error }}</p>

        <div class="modal-actions">
          <button class="btn-secondary" @click="closePinPrompt">Cancel</button>
          <button class="btn-primary" @click="confirmPinReveal" :disabled="isSaving">
            Reveal
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL: Save changes -->
    <div v-if="savePrompt.open" class="modal-overlay" @click.self="closeSavePrompt">
      <div class="modal modal-card pin-modal pinpad" :class="{ shake: pinSaveError }">
        <div class="modal-header">
          <Shield class="modal-icon" />
          <h3 class="modal-title">Confirm changes</h3>
        </div>
        <p class="modal-text">Enter your 6-digit PIN to save changes.</p>

        <div class="pin-input pin-inputs">
          <input
            v-for="(_, i) in 6"
            :key="'save-'+i"
            :ref="el => (pinSaveBoxes[i] = el)"
            class="pin-box"
            type="password"
            maxlength="1"
            inputmode="numeric"
            v-model="enteredPinSave[i]"
            @input="handlePinInputSave(i, $event)"
            @keydown.backspace.prevent="handlePinBackspaceSave(i, $event)"
          />
        </div>

        <p v-if="savePrompt.error" class="modal-error">{{ savePrompt.error }}</p>

        <div class="modal-actions">
          <button class="btn-secondary" @click="closeSavePrompt">Cancel</button>
          <button class="btn-primary" @click="confirmSave" :disabled="isSaving">
            Save
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL: DELETE PROFILE -->
    <div v-if="deletePrompt.open" class="modal-overlay" @click.self="closeDeletePrompt">
      <div
        class="modal modal-card pin-modal pinpad"
        :class="{ shake: pinDeleteError }"
      >
        <div class="modal-header">
          <Shield class="modal-icon" />
          <h3 class="modal-title">Delete profile</h3>
        </div>

        <p class="modal-text">
          This action is <strong>permanent</strong>. All your data, accounts, and profile
          information will be permanently deleted.<br /><br />
          Enter your 6-digit PIN to confirm.
        </p>

        <div class="pin-input pin-inputs">
          <input
            v-for="(_, i) in 6"
            :key="'delete-'+i"
            :ref="el => (pinDeleteBoxes[i] = el)"
            class="pin-box"
            type="password"
            maxlength="1"
            inputmode="numeric"
            v-model="enteredPinDelete[i]"
            @input="handlePinInputDelete(i, $event)"
            @keydown.backspace.prevent="handlePinBackspaceDelete(i, $event)"
          />
        </div>

        <p v-if="deletePrompt.error" class="modal-error">{{ deletePrompt.error }}</p>

        <div class="modal-actions">
          <button class="btn-secondary" @click="closeDeletePrompt">Cancel</button>
          <button class="btn-primary" @click="confirmDelete" :disabled="isSaving">
            Delete profile
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import HeaderLayout from '@/components/layout/HeaderLayout.vue'
import FooterLayout from '@/components/layout/FooterLayout.vue'
import { ref, nextTick, onMounted, onUnmounted, computed } from 'vue'
import { useUserStore } from '@/stores/user'
import { Eye, EyeOff, Lock, Shield } from 'lucide-vue-next'
import {
  getUser,
  updateUser,
  verifyPin,
  verifyPassword,
  changePassword,
  changePin,
  deleteUser,
} from '@/api/userService'
import { useRouter } from 'vue-router'

const router = useRouter()
const userStore = useUserStore()
const showToast = (msg, type = 'info') => alert(`${type.toUpperCase()}: ${msg}`)

const isSaving = ref(false)

const goToTerms = () => router.push('/terms')
const goBack = () => router.back()

const form = ref({ name: '', dni: '', email: '', phone: '', birthday: '' })

const password = ref({ new: '', confirm: '' })
const pin = ref({ new: '', confirm: '' })

const showPwd = ref({ current: false, new: false, confirm: false })
const showPin = ref({ current: false, new: false, confirm: false })

const currentPasswordValue = ref('********')
const currentPinValue = ref('******')

const original = ref({})

const emailError = ref('')
const phoneError = ref('')
const passwordFormatError = ref('')
const pinFormatError = ref('')

function snapshotFromUser(u) {
  return {
    name: u?.name ?? '',
    dni: u?.dni ?? '',
    email: u?.email ?? '',
    phone: u?.phone ?? '',
    birthday: u?.birthday ?? u?.birthdate ?? '',
  }
}

onMounted(async () => {
  try {
    const u = await getUser(userStore.dni)
    userStore.user = u

    const snap = snapshotFromUser(u)
    form.value = { ...snap }
    original.value = { ...snap }
  } catch (e) {
    console.error('Error cargando perfil:', e)
    showToast('No se pudo cargar el perfil.', 'error')
  }
})

const isFormChanged = () =>
  form.value.email.trim() !== (original.value.email ?? '').trim() ||
  (form.value.phone ?? '').trim() !== (original.value.phone ?? '').trim()

const isDirty = computed(
  () =>
    isFormChanged() ||
    !!password.value.new ||
    !!password.value.confirm ||
    !!pin.value.new ||
    !!pin.value.confirm,
)

const passwordMismatch = computed(
  () =>
    !!password.value.new &&
    !!password.value.confirm &&
    password.value.new !== password.value.confirm,
)

const pinMismatch = computed(
  () =>
    !!pin.value.new &&
    !!pin.value.confirm &&
    pin.value.new !== pin.value.confirm,
)

const hasFormatErrors = computed(
  () =>
    !!emailError.value ||
    !!phoneError.value ||
    !!passwordFormatError.value ||
    !!pinFormatError.value,
)
function extractRawPhone(phone) {
  return phone
    .replace(/^\+34/, '')   // treu el prefix només si és +34
    .replace(/\D/g, '')     // treu tot el que no és dígit
}

function validateEmail() {
  const value = form.value.email.trim()
  if (!value) {
    emailError.value = 'Email is required.'
    return
  }
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  emailError.value = emailRegex.test(value) ? '' : 'Invalid email format.'
}

const validatePhone = () => {
  let value = form.value.phone ?? '';

  // Remove all non-digits
  let digits = value.replace(/\D/g, '');

  // If user starts typing without +34, do NOT force-rewrite until needed
  if (digits.startsWith('34')) {
    digits = digits.slice(2);
  }

  // Limit to 9 digits
  digits = digits.slice(0, 9);

  // Build formatted output
  let formatted = '+34';
  if (digits.length <4) formatted += ' ';
  if (digits.length > 0) formatted += ' ' + digits.slice(0, 3);
  if (digits.length > 3) formatted += ' ' + digits.slice(3, 6);
  if (digits.length > 6) formatted += ' ' + digits.slice(6, 9);

  // Assign only if value has changed → prevents cursor jumping
  if (formatted !== form.value.phone) {
    form.value.phone = formatted;
  }

  // Validation
  phoneError.value =
    digits.length === 9 ? '' : 'Phone must be 9 digits.';
};


/**
 * Validación fuerte de la nueva contraseña:
 * - Min 6 caracteres
 * - Minúscula, mayúscula, número y carácter especial
 */
function validateNewPassword() {
  const value = password.value.new || ''

  if (!value) {
    passwordFormatError.value = ''
    validateConfirmPassword()
    return
  }

  const hasLower = /[a-z]/.test(value)
  const hasUpper = /[A-Z]/.test(value)
  const hasNumber = /\d/.test(value)
  const hasSpecial = /[^A-Za-z0-9]/.test(value)
  const longEnough = value.length >= 6

  if (!longEnough) {
    passwordFormatError.value = 'At least 6 characters.'
  } else if (!hasLower) {
    passwordFormatError.value = 'Must include at least one lowercase letter.'
  } else if (!hasUpper) {
    passwordFormatError.value = 'Must include at least one uppercase letter.'
  } else if (!hasNumber) {
    passwordFormatError.value = 'Must include at least one number.'
  } else if (!hasSpecial) {
    passwordFormatError.value = 'Must include at least one special character.'
  } else {
    passwordFormatError.value = ''
  }

  validateConfirmPassword()
}

function validateConfirmPassword() {
  // hook por si quieres lógica extra en el futuro
}

function validateNewPin() {
  const value = pin.value.new
  if (!value) {
    pinFormatError.value = ''
    return
  }
  pinFormatError.value = /^\d{6}$/.test(value)
    ? ''
    : 'PIN must be 6 digits.'
}

function resetLocalChanges() {
  form.value = { ...original.value }
  password.value = { new: '', confirm: '' }
  pin.value = { new: '', confirm: '' }
  pinPrompt.value.error = ''
  savePrompt.value.error = ''
  emailError.value = ''
  phoneError.value = ''
  passwordFormatError.value = ''
  pinFormatError.value = ''
}

function onCancel() {
  if (isDirty.value) {
    resetLocalChanges()
    showToast('All changes have been undone.', 'info')
  } else {
    router.push('/dashboard')
  }
}

/**
 * Eye button para el password actual:
 * - Si está visible => solo lo oculta (no pide PIN).
 * - Si está oculto => abre el modal para pedir PIN y revelar.
 */
function handleCurrentPasswordEyeClick() {
  if (showPwd.value.current) {
    showPwd.value.current = false
    return
  }

  if (pinPrompt.value.open || savePrompt.value.open || isSaving.value) return

  requestPinToReveal('currentPwd')
}

/* REVEAL PIN MODAL */
const pinPrompt = ref({ open: false, target: '', error: '' })
const enteredPinReveal = ref(['', '', '', '', '', ''])
const pinRevealBoxes = ref([])
const pinRevealError = ref(false)

function requestPinToReveal(target) {
  pinPrompt.value.open = true
  pinPrompt.value.target = target
  pinPrompt.value.error = ''
  enteredPinReveal.value = ['', '', '', '', '', '']
  nextTick(() => pinRevealBoxes.value?.[0]?.focus())
}

function handlePinInputReveal(i, event) {
  let value = event.target.value.replace(/\D/g, '')

  if (value.length > 1) {
    const digits = value.split('')
    digits.forEach((d, offset) => {
      const idx = i + offset
      if (idx < 6) {
        enteredPinReveal.value[idx] = d
        if (pinRevealBoxes.value[idx]) {
          pinRevealBoxes.value[idx].value = d
        }
      }
    })
    const lastIdx = Math.min(i + digits.length, 5)
    pinRevealBoxes.value[lastIdx]?.focus()
    return
  }

  enteredPinReveal.value[i] = value
  if (value && i < 5) {
    pinRevealBoxes.value[i + 1]?.focus()
  }
}

function handlePinBackspaceReveal(i) {
  if (enteredPinReveal.value[i]) {
    enteredPinReveal.value[i] = ''
    return
  }
  if (i > 0) {
    enteredPinReveal.value[i - 1] = ''
    pinRevealBoxes.value[i - 1]?.focus()
  }
}

function closePinPrompt() {
  pinPrompt.value.open = false
  pinPrompt.value.error = ''
  enteredPinReveal.value = ['', '', '', '', '', '']
}

async function confirmPinReveal() {
  const pinTyped = enteredPinReveal.value.join('')
  if (pinTyped.length !== 6) {
    pinPrompt.value.error = 'Enter your 6-digit PIN.'
    return
  }

  try {
    if (pinPrompt.value.target === 'currentPwd') {
      const data = await verifyPassword(userStore.dni, pinTyped)
      currentPasswordValue.value = data?.password ?? '********'
      showPwd.value.current = !showPwd.value.current
    } else if (pinPrompt.value.target === 'currentPin') {
      const data = await verifyPin(userStore.dni, pinTyped)
      currentPinValue.value = data?.pin ?? '******'
      showPin.value.current = !showPin.value.current
    }
    closePinPrompt()
  } catch (e) {
    console.error('Error verifying PIN (reveal):', e)

    // Preferimos el contrato del BE: { error: { message: "..."} }
    let msg =
      e?.response?.data?.error?.message ||
      e?.response?.data?.message ||
      e.message ||
      'Unexpected error while verifying PIN.'

    pinPrompt.value.error = msg
    pinRevealError.value = true
    setTimeout(() => (pinRevealError.value = false), 600)
  }
}

/* SAVE MODAL */
const savePrompt = ref({ open: false, error: '' })
const enteredPinSave = ref(['', '', '', '', '', ''])
const pinSaveBoxes = ref([])
const pinSaveError = ref(false)

function openSavePrompt() {
  savePrompt.value.open = true
  savePrompt.value.error = ''
  enteredPinSave.value = ['', '', '', '', '', '']
  nextTick(() => pinSaveBoxes.value?.[0]?.focus())
}

function closeSavePrompt() {
  savePrompt.value.open = false
  savePrompt.value.error = ''
  enteredPinSave.value = ['', '', '', '', '', '']
}

function handlePinInputSave(i, event) {
  let value = event.target.value.replace(/\D/g, '')

  if (value.length > 1) {
    const digits = value.split('')
    digits.forEach((d, offset) => {
      const idx = i + offset
      if (idx < 6) {
        enteredPinSave.value[idx] = d
        if (pinSaveBoxes.value[idx]) {
          pinSaveBoxes.value[idx].value = d
        }
      }
    })
    const lastIdx = Math.min(i + digits.length, 5)
    pinSaveBoxes.value[lastIdx]?.focus()
    return
  }

  enteredPinSave.value[i] = value
  if (value && i < 5) {
    pinSaveBoxes.value[i + 1]?.focus()
  }
}

function handlePinBackspaceSave(i) {
  if (enteredPinSave.value[i]) {
    enteredPinSave.value[i] = ''
    return
  }
  if (i > 0) {
    pinSaveBoxes.value[i - 1]?.focus()
  }
}

async function confirmSave() {
  const typed = enteredPinSave.value.join('')
  if (typed.length !== 6) {
    savePrompt.value.error = 'Enter your 6-digit PIN.'
    return
  }

  validateEmail()
  validatePhone()
  validateNewPassword()
  validateNewPin()
  if (hasFormatErrors.value) {
    savePrompt.value.error = 'Please fix the highlighted fields.'
    return
  }

  if (password.value.new && password.value.new !== password.value.confirm) {
    savePrompt.value.error = 'Passwords do not match.'
    return
  }
  if (pin.value.new && pin.value.new !== pin.value.confirm) {
    savePrompt.value.error = 'PINs must match.'
    return
  }

  try {
    isSaving.value = true

    // Verificar PIN primero
    await verifyPin(userStore.dni, typed)

    const updatePayload = {}
    if (form.value.email.trim() !== (userStore.user?.email ?? '').trim()) {
      updatePayload.email = form.value.email.trim()
    }
    if ((form.value.phone ?? '').trim() !== (userStore.user?.phone ?? '').trim()) {
      updatePayload.phone = (form.value.phone ?? '').trim()
    }

    if (Object.keys(updatePayload).length) {
      updatePayload.pin = typed
      await updateUser(userStore.dni, updatePayload)
    }

    if (password.value.new) {
      await changePassword(userStore.dni, {
        pin: typed,
        newPassword: password.value.new,
      })
    }

    if (pin.value.new) {
      await changePin(userStore.dni, {
        pin: typed,
        newPin: pin.value.new,
      })
    }

    const u = await getUser(userStore.dni)
    userStore.user = u
    const snap = snapshotFromUser(u)
    form.value = { ...snap }
    original.value = { ...snap }

    password.value = { new: '', confirm: '' }
    pin.value = { new: '', confirm: '' }

    closeSavePrompt()
    showToast('Changes saved.', 'success')
  } catch (e) {
    console.error('Error saving security changes:', e)

    const msg =
      e?.response?.data?.error?.message ||
      e?.response?.data?.message ||
      e.message ||
      'No changes have been made.'

    savePrompt.value.error = msg
    pinSaveError.value = true
    setTimeout(() => (pinSaveError.value = false), 600)
  } finally {
    isSaving.value = false
  }
}

/* DELETE PROFILE MODAL */
const deletePrompt = ref({ open: false, error: '' })
const enteredPinDelete = ref(['', '', '', '', '', ''])
const pinDeleteBoxes = ref([])
const pinDeleteError = ref(false)

function openDeletePrompt() {
  deletePrompt.value.open = true
  deletePrompt.value.error = ''
  enteredPinDelete.value = ['', '', '', '', '', '']
  nextTick(() => pinDeleteBoxes.value?.[0]?.focus())
}

function closeDeletePrompt() {
  deletePrompt.value.open = false
  deletePrompt.value.error = ''
  enteredPinDelete.value = ['', '', '', '', '', '']
}

function handlePinInputDelete(i, event) {
  let value = event.target.value.replace(/\D/g, '')

  if (value.length > 1) {
    const digits = value.split('')
    digits.forEach((d, offset) => {
      const idx = i + offset
      if (idx < 6) {
        enteredPinDelete.value[idx] = d
        if (pinDeleteBoxes.value[idx]) {
          pinDeleteBoxes.value[idx].value = d
        }
      }
    })
    const lastIdx = Math.min(i + digits.length, 5)
    pinDeleteBoxes.value[lastIdx]?.focus()
    return
  }

  enteredPinDelete.value[i] = value
  if (value && i < 5) {
    pinDeleteBoxes.value[i + 1]?.focus()
  }
}

function handlePinBackspaceDelete(i) {
  if (enteredPinDelete.value[i]) {
    enteredPinDelete.value[i] = ''
    return
  }
  if (i > 0) {
    pinDeleteBoxes.value[i - 1]?.focus()
  }
}

async function confirmDelete() {
  const typed = enteredPinDelete.value.join('')
  if (typed.length !== 6) {
    deletePrompt.value.error = 'Enter your 6-digit PIN.'
    return
  }

  try {
    isSaving.value = true

    await deleteUser(userStore.dni, { pin: typed })

    deletePrompt.value.open = false
    deletePrompt.value.error = ''
    enteredPinDelete.value = ['', '', '', '', '', '']

    if (typeof userStore.logout === 'function') {
      await userStore.logout()
    } else {
      userStore.user = null
    }

    showToast('Your profile has been deleted.', 'success')

    router.push('/')
  } catch (e) {
    console.error('Error deleting user:', e)
    const msg =
      e?.response?.data?.error?.message ||
      e?.response?.data?.message ||
      e.message ||
      'Could not delete profile.'
    deletePrompt.value.error = msg
    pinDeleteError.value = true
    setTimeout(() => (pinDeleteError.value = false), 600)
  } finally {
    isSaving.value = false
  }
}

/* beforeunload protection */
onMounted(() => {
  const handler = (e) => {
    if (isDirty.value) {
      e.preventDefault()
      e.returnValue = ''
    }
  }
  window.addEventListener('beforeunload', handler)
  onUnmounted(() => window.removeEventListener('beforeunload', handler))
})
</script>

<style scoped>
.profile-page {
  background: #1a1a1a;
  min-height: 100vh;
  color: #fff;
}

.profile-content {
  min-height: calc(100vh - 65px);
  max-width: 900px;
  margin: 0 auto;
  padding: 80px 16px 40px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.profile-wrapper {
  width: 100%;
  padding: 24px 28px;
  background: rgba(255, 255, 255, 0.05);
  border: 2px solid #b79b58;
  border-radius: 22px;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow:
    0 6px 26px rgba(183, 155, 88, 0.2),
    0 0 0 1px rgba(255, 255, 255, 0.03);
  transition:
    background-color 0.25s ease,
    transform 0.25s ease;
}

.profile-wrapper:hover,
.profile-wrapper:focus-within {
  background: rgba(255, 255, 255, 0.1);
  transform: translateY(-3px);
}

.profile-title {
  font-size: 1.4rem;
  font-weight: 600;
  margin: 0 0 4px;
}

.profile-sub {
  margin: 0 0 20px;
  font-size: 0.9rem;
  color: #cccccc;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px 28px;
}

.form-grid.security-grid {
  grid-template-columns: 1fr 1fr;
}

.security-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

@media (max-width: 768px) {
  .form-grid,
  .form-grid.security-grid {
    grid-template-columns: 1fr;
  }
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-field label {
  font-size: 0.95rem;
  color: #ffffffd9;
}

.input-box {
  position: relative;
  width: 100%;
}

.input-box input,
.input-box select {
  width: 100%;
  height: 42px;
  background: transparent;
  border-radius: 10px;
  border: 2px solid rgba(255, 255, 255, 0.25);
  padding: 0 12px;
  font-size: 16px;
  color: #fff;
  transition:
    border-color 0.25s ease,
    background-color 0.25s ease;
  outline: none !important;
}

.input-box input::placeholder,
.input-box select::placeholder {
  color: #bfbfbf !important;
  opacity: 0.45 !important;
  font-style: italic;
}

.input-box:focus-within input,
.input-box:focus-within select {
  border-color: transparent;
  background: rgba(0, 0, 0, 0.15);
}

.border-anim {
  pointer-events: none;
  position: absolute;
  inset: 0;
  border-radius: 10px;
  border: 2px solid #b79b58;
  clip-path: inset(0 100% 0 0);
  transition: none;
}

.input-box:focus-within .border-anim {
  clip-path: inset(0 0 0 0);
  transition: clip-path 0.4s ease-in-out;
}

.input-box.readonly input {
  cursor: not-allowed;
  color: #dddddd;
  border-color: rgba(255, 255, 255, 0.15);
}

.input-box.readonly input[type='date'] {
  color: #dddddd;
  -webkit-text-fill-color: #dddddd;
}

input[type='date']::-webkit-datetime-edit,
input[type='date']::-webkit-datetime-edit-text,
input[type='date']::-webkit-datetime-edit-year-field,
input[type='date']::-webkit-datetime-edit-month-field,
input[type='date']::-webkit-datetime-edit-day-field {
  color: #dddddd;
}

input[type='date']:disabled {
  -webkit-text-fill-color: #dddddd;
  opacity: 1;
}

.input-box.with-eye {
  padding-right: 40px;
}

.eye-btn {
  position: absolute;
  top: 50%;
  right: 8px;
  transform: translateY(-50%);
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.eye-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.eye-icon {
  width: 18px;
  height: 18px;
  color: #ffffffd9;
}

.error-message {
  font-size: 0.8rem;
  color: #f87171;
  margin-top: 4px;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 22px;
}

.btn-primary {
  border-radius: 10px;
  border: 2px solid rgba(183, 155, 88, 0.45);
  background: transparent;
  color: #fff;
  font-size: 0.95rem;
  font-weight: 600;
  padding: 10px 18px;
  cursor: pointer;
  transition:
    background-color 0.25s ease,
    border-color 0.25s ease,
    color 0.25s ease,
    transform 0.2s ease,
    box-shadow 0.25s ease;
}

.btn-primary:hover:not(:disabled) {
  background: #b79b58;
  border-color: #b79b58;
  color: #000;
  transform: translateY(-2px);
  box-shadow: 0 4px 14px rgba(183, 155, 88, 0.4);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  background: transparent;
  color: #fff;
  font-size: 0.95rem;
  padding: 10px 18px;
  cursor: pointer;
  transition:
    background-color 0.25s ease,
    border-color 0.25s ease,
    color 0.25s ease,
    transform 0.2s ease;
}

.btn-secondary:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-1px);
}


.delete-profile-btn {
  margin-right: auto;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: grid;
  place-items: center;
  z-index: 60;
}

.modal-card {
  width: min(520px, 92vw);
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 18px;
  padding: 20px;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.5);
}

.modal-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.modal-title {
  font-size: 1.05rem;
  font-weight: 700;
  margin: 0;
}

.modal-icon {
  width: 22px;
  height: 22px;
  color: #b79b58;
}

.modal-text {
  color: #dcdcdc;
  margin: 6px 0 12px 0;
  font-size: 0.95rem;
}

.modal-error {
  color: #ff8a8a;
  font-size: 0.92rem;
  margin-top: 8px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 14px;
}

.pin-input {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin: 20px 0;
}

.pin-box {
  width: 42px;
  height: 48px;
  font-size: 24px;
  text-align: center;
  border-radius: 8px;
  border: 1px solid #d5b76f;
  background: #1f1f1f;
  color: #fff;
  outline: none;
  transition: 0.2s ease;
}

.pin-box:focus {
  border-color: #d5b76f !important;
  box-shadow: 0 0 0 3px rgba(213, 183, 111, 0.35);
  background: rgba(0, 0, 0, 0.2);
}

.shake {
  animation: shake 0.45s ease;
}

@keyframes shake {
  10%, 90% { transform: translateX(-2px); }
  20%, 80% { transform: translateX(4px); }
  30%, 50%, 70% { transform: translateX(-6px); }
  40%, 60% { transform: translateX(6px); }
}

.header-terms-btn {
  background: none;
  border: none;
  color: #ffffff;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  padding: 6px 10px;
  margin-left: 16px;
  transition:
    color 0.25s ease,
    transform 0.25s ease;
}

.header-terms-btn:hover {
  color: #c9b26a;
  transform: scale(1.08);
}

.delete-profile-btn {
  margin-right: auto;
  border-color: rgba(255, 80, 80, 0.35);
  color: #ff9090;
  transition: 0.25s ease;
}

.delete-profile-btn:hover:not(:disabled) {
  background: rgba(255, 60, 60, 0.2);
  border-color: rgba(255, 60, 60, 0.7);
  color: #ffb3b3;
  transform: translateY(-2px);
  box-shadow: 0 4px 14px rgba(255, 60, 60, 0.35);
}

</style>
