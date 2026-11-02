<template>
  <div class="signup-page">
    <HeaderLayout title="Kofre" />

    <div class="signup-content">
      <div class="signup-wrapper">
        <h2 class="signup-title">Create your account</h2>
        <p class="signup-sub">Join Kofre and start managing your finances today.</p>

        <form class="signup-form" @submit.prevent="register">
          <!-- GRID 2 COLUMNAS -->
          <div class="form-grid">
            <!-- Full name -->
            <div class="form-field">
              <label for="name">Full Name</label>
              <div class="input-box">
                <input
                  id="name"
                  v-model="form.name"
                  type="text"
                  placeholder="e.g. Duna Soler"
                  @input="validateName"
                  required
                  data-testid="signup-name-input"
                />
                <span class="border-anim"></span>
              </div>
              <p v-if="nameError" class="error-message">{{ nameError }}</p>
            </div>

            <!-- DNI -->
            <div class="form-field">
              <label for="dni">DNI</label>
              <div class="input-box">
                <input
                  id="dni"
                  v-model="form.dni"
                  type="text"
                  placeholder="12345678A"
                  @input="validateDni"
                  required
                  data-testid="signup-dni-input"
                />
                <span class="border-anim"></span>
              </div>
              <p v-if="dniError" class="error-message">{{ dniError }}</p>
            </div>

            <!-- Email -->
            <div class="form-field">
              <label for="email">Email</label>
              <div class="input-box">
                <input
                  id="email"
                  v-model="form.email"
                  type="email"
                  placeholder="you@example.com"
                  @input="validateEmail"
                  required
                  data-testid="signup-email-input"
                />
                <span class="border-anim"></span>
              </div>
              <p v-if="emailError" class="error-message">{{ emailError }}</p>
            </div>

            <!-- Phone -->
            <div class="form-field">
              <label for="phone">Mobile Number</label>
              <div class="input-box">
                <input
                  id="phone"
                  v-model="form.phone"
                  type="tel"
                  placeholder="Spanish mobile number"
                  @input="validatePhone"
                  required
                  data-testid="signup-phone-input"
                />
                <span class="border-anim"></span>
              </div>
              <p v-if="phoneError" class="error-message">{{ phoneError }}</p>
            </div>

            <!-- Password -->
            <div class="form-field">
              <label for="password">Password</label>
              <div class="input-box with-eye">
                <input
                  id="password"
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  placeholder="••••••••"
                  @input="validatePassword"
                  required
                  data-testid="signup-password-input"
                />
                <button type="button" class="eye-btn" @click="showPassword = !showPassword">
                  <component :is="showPassword ? EyeOff : Eye" class="eye-icon" />
                </button>
                <span class="border-anim"></span>
              </div>
              <p v-if="passwordError" class="error-message">{{ passwordError }}</p>
            </div>

            <!-- Confirm Password -->
            <div class="form-field">
              <label for="confirmPassword">Confirm Password</label>
              <div class="input-box with-eye">
                <input
                  id="confirmPassword"
                  v-model="form.confirmPassword"
                  :type="showConfirmPassword ? 'text' : 'password'"
                  placeholder="••••••••"
                  @input="validateConfirmPassword"
                  required
                  data-testid="signup-confirm-password-input"
                />
                <button type="button" class="eye-btn" @click="showConfirmPassword = !showConfirmPassword">
                  <component :is="showConfirmPassword ? EyeOff : Eye" class="eye-icon" />
                </button>
                <span class="border-anim"></span>
              </div>
              <p v-if="confirmPasswordError" class="error-message">{{ confirmPasswordError }}</p>
            </div>

            <!-- PIN -->
            <div class="form-field">
              <label for="pin">6-digit Security PIN</label>
              <div class="input-box with-eye">
                <input
                  id="pin"
                  v-model="form.pin"
                  maxlength="6"
                  :type="showPin ? 'text' : 'password'"
                  class="pin-input"
                  placeholder="••••••"
                  @input="validatePin"
                  required
                  data-testid="signup-pin-input"
                />
                <button type="button" class="eye-btn" @click="showPin = !showPin">
                  <component :is="showPin ? EyeOff : Eye" class="eye-icon" />
                </button>
                <span class="border-anim"></span>
              </div>
              <p v-if="pinError" class="error-message">{{ pinError }}</p>
            </div>

            <!-- Birthdate -->
            <div class="form-field">
              <label for="birthday">Birthday (DD/MM/YYYY)</label>
              <div class="input-box">
                <input
                  id="birthday"
                  v-model="formattedDate"
                  type="text"
                  placeholder="31/12/1990"
                  @input="autoFormatBirthday"
                  required
                  data-testid="signup-birthday-input"
                />
                <span class="border-anim"></span>
              </div>
              <p v-if="birthdayError" class="error-message">{{ birthdayError }}</p>
            </div>

            <!-- Gender -->
            <div class="form-field full-width">
              <label>Gender</label>
              <div class="select-wrapper">
                <select v-model="form.gender" required data-testid="signup-gender-select">
                  <option disabled value="">Select gender</option>
                  <option value="female">Female</option>
                  <option value="male">Male</option>
                  <option value="other">Other</option>
                </select>

                <svg class="select-icon" xmlns="http://www.w3.org/2000/svg" width="20" height="20"
                  viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </div>
            </div>

            <!-- TERMS -->
            <div class="form-field full-width terms-field">
              <label class="checkbox-line">
                <input id="terms" type="checkbox" v-model="termsAccepted" data-testid="signup-terms-checkbox" />
                <span>
                  I accept the <RouterLink to="/terms" class="link">terms and conditions</RouterLink>.
                </span>
              </label>
            </div>
          </div>

          <!-- SUBMIT -->
          <button class="signup-btn" :disabled="!isFormValid" data-testid="signup-submit-btn">
            Sign Up
          </button>

          <p class="footer-text">
            Already have an account?
            <RouterLink to="/login" class="link">Log In</RouterLink>
          </p>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import HeaderLayout from '@/components/layout/HeaderLayout.vue'
  import { ref, computed } from 'vue'
  import { signupUser } from '@/api/authService'
  import { userManager } from '@/api/oidc'
  import { Eye, EyeOff } from '@lucide/vue'

  /* ============================
     FORM DATA
  ============================ */
  const form = ref({
    name: '',
    dni: '',
    email: '',
    phone: '', // ✅ ← ANTES: "+34 " — AHORA VACÍO PARA NO VERLO FEO
    password: '',
    confirmPassword: '',
    pin: '',
    birthdate: undefined as Date | undefined,
    gender: '',
  })

  const termsAccepted = ref(false)
  const rawDateInput = ref('')

  /* ojos */
  const showPassword = ref(false)
  const showConfirmPassword = ref(false)
  const showPin = ref(false)

  /* ============================
     VALIDATION STATE
  ============================ */
  const nameError = ref('')
  const dniError = ref('')
  const emailError = ref('')
  const phoneError = ref('')
  const passwordError = ref('')
  const confirmPasswordError = ref('')
  const pinError = ref('')
  const birthdayError = ref('')

  /* ============================
     FORMATTED BIRTHDAY
  ============================ */
  const formattedDate = computed({
    get: () => rawDateInput.value,
    set: (val: string) => {
      rawDateInput.value = val
      validateBirthday()
      const datePattern = /^(\d{2})\/(\d{2})\/(\d{4})$/

      if (datePattern.test(val)) {
        const [dd, mm, yyyy] = val.split('/')
        const parsed = new Date(`${yyyy}-${mm}-${dd}`)
        if (!isNaN(parsed.getTime())) form.value.birthdate = parsed
        else form.value.birthdate = undefined
      } else {
        form.value.birthdate = undefined
      }
    },
  })

  /* ============================
     VALIDATION FUNCTIONS
  ============================ */
  function autoFormatBirthday(e: Event) {
    let input = (e.target as HTMLInputElement).value
    input = input.replace(/\D/g, '')

    if (input.length >= 1 && input.length <= 2) {
      if (input.length === 2) input = input + '/'
    } else if (input.length > 2 && input.length <= 4) {
      input = input.slice(0, 2) + '/' + input.slice(2)
      if (input.length === 5) input = input + '/'
    } else if (input.length > 4) {
      input = input.slice(0, 2) + '/' + input.slice(2, 4) + '/' + input.slice(4, 8)
    }

    rawDateInput.value = input
  }

  const validateName = () => {
    nameError.value = form.value.name.length < 2 ? 'Please enter a valid name.' : ''
  }

  const validateDni = () => {
    const dni = form.value.dni
    const dniRegex = /^\d{8}[A-Za-z]$/

    if (!dniRegex.test(dni)) {
      dniError.value = 'Invalid DNI format.'
      return
    }

    if (!validateRealDni(dni)) {
      dniError.value = 'DNI letter does not match the number.'
      return
    }

    dniError.value = ''
  }

  function validateRealDni(dni: string) {
    const letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
    const number = parseInt(dni.substring(0, 8))
    const letter = dni.charAt(8).toUpperCase()
    if (isNaN(number)) return false
    return letters[number % 23] === letter
  }

  const validateEmail = () => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    emailError.value = emailRegex.test(form.value.email) ? '' : 'Invalid email.'
  }

  const validatePhone = () => {
    let value = form.value.phone

    // Auto añadir +34 cuando escriben SIN él
    if (!value.startsWith('+34')) {
      value = '+34 ' + value.replace(/\D/g, '')
    }

    // Extraer dígitos
    let digits = value.replace(/\D/g, '')

    // Quitar 34 inicial si aparece repetido
    if (digits.startsWith('34')) digits = digits.slice(2)

    // Limitar a 9 dígitos
    digits = digits.slice(0, 9)

    // Re-formatear bonito
    let formatted = '+34'


    if (digits.length < 4) formatted += ' '
    if (digits.length > 0) formatted += ' ' + digits.slice(0, 3)
    if (digits.length > 3) formatted += ' ' + digits.slice(3, 6)
    if (digits.length > 6) formatted += ' ' + digits.slice(6, 9)

    form.value.phone = formatted

    // Validación
    if (digits.length !== 9) {
      phoneError.value = 'Phone must be a Spanish number (+34, 9 digits).'
      return
    }

    phoneError.value = ''
  }

  const validatePassword = () => {
    const value = form.value.password

    const hasLetter = /[a-z]/.test(value)
    const hasUpper = /[A-Z]/.test(value)
    const hasNumber = /\d/.test(value)
    const hasSpecial = /[^A-Za-z0-9]/.test(value)
    const longEnough = value.length >= 6

    if (!longEnough) passwordError.value = 'At least 8 characters.'
    else if (!hasLetter) passwordError.value = 'Must include at least one lowercase letter.'
    else if (!hasUpper) passwordError.value = 'Must include at least one uppercase letter.'
    else if (!hasNumber) passwordError.value = 'Must include at least one number.'
    else if (!hasSpecial) passwordError.value = 'Must include at least one special character.'
    else passwordError.value = ''

    validateConfirmPassword()
  }

  const validateConfirmPassword = () => {
    const pass = form.value.password
    const confirm = form.value.confirmPassword
    confirmPasswordError.value = confirm && confirm !== pass ? 'Passwords do not match.' : ''
  }

  const validatePin = () => {
    pinError.value = /^\d{6}$/.test(form.value.pin) ? '' : 'PIN must be 6 digits.'
  }

  /* valida también fecha futura y edad máxima (120) */
  const validateBirthday = () => {
    const datePattern = /^(\d{2})\/(\d{2})\/(\d{4})$/

    if (!datePattern.test(rawDateInput.value)) {
      birthdayError.value = 'Use DD/MM/YYYY format.'
      return
    }

    const [dd, mm, yyyy] = rawDateInput.value.split('/')
    const parsed = new Date(`${yyyy}-${mm}-${dd}`)

    if (isNaN(parsed.getTime())) {
      birthdayError.value = 'Invalid date.'
      return
    }

    const today = new Date()

    // no puede ser una fecha futura
    if (parsed > today) {
      birthdayError.value = 'Birthdate cannot be in the future.'
      return
    }

    // límite máximo de edad
    const maxAge = 120
    const oldestAllowed = new Date(
      today.getFullYear() - maxAge,
      today.getMonth(),
      today.getDate(),
    )

    if (parsed < oldestAllowed) {
      birthdayError.value = `Invalid date.`
      return
    }

    const adultDate = new Date(parsed.getFullYear() + 18, parsed.getMonth(), parsed.getDate())
    birthdayError.value = today >= adultDate ? '' : 'You must be 18 or older.'
  }

  /* ============================
     FORM VALID
  ============================ */
  const isFormValid = computed(
    () =>
      !nameError.value &&
      !dniError.value &&
      !emailError.value &&
      !phoneError.value &&
      !passwordError.value &&
      !confirmPasswordError.value &&
      !pinError.value &&
      !birthdayError.value &&
      form.value.gender &&
      termsAccepted.value,
  )

  /* ============================
     NORMALIZE PHONE
  ============================ */
  function normalizePhone(rawPhone: string): string | null {
    let digits = rawPhone.replace(/\D/g, '')

    if (digits.startsWith('34')) digits = digits.slice(2)
    if (!/^\d{9}$/.test(digits)) return null

    return `+34${digits}`
  }

  /* ============================
     SUBMIT
  ============================ */
  const register = async () => {
    if (!isFormValid.value) return alert('Please fix the errors.')

    try {
      const normalizedPhone = normalizePhone(form.value.phone)
      if (!normalizedPhone) return alert('Invalid phone.')

      const signupData = {
        name: form.value.name,
        dni: form.value.dni,
        email: form.value.email,
        phone: normalizedPhone,
        password: form.value.password,
        birthdate: form.value.birthdate!.toISOString().split('T')[0],
        gender: form.value.gender,
        pin: form.value.pin,
      }
      await signupUser(signupData)
      // The new user signs in through the OAuth login page.
      await userManager.signinRedirect({ state: { redirect: '/dashboard' } })
    } catch (error) {
      console.error('Registration failed', error?.message)
      alert('Registration failed.')
    }
  }
  </script>


<style scoped>
  /* PAGE */
  .signup-page {
    background: #1a1a1a;
    min-height: 100vh;
    color: #fff;
  }

  /* Centro el wrapper bajo el header  */
  .signup-content {
    min-height: calc(100vh - 65px);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 80px 16px 40px;
  }

  /* Caja  */
  .signup-wrapper {
    width: 760px;
    max-width: 100%;
    padding: 32px 40px;
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

  .signup-wrapper:hover {
    background: rgba(255, 255, 255, 0.1);
    transform: translateY(-3px);
  }

  /* Títulos */
  .signup-title {
    text-align: center;
    font-size: 2rem;
    font-weight: 600;
  }

  .signup-sub {
    text-align: center;
    margin-top: 4px;
    margin-bottom: 28px;
    color: #cccccc;
  }

  /* GRID 2 columnas */
  .form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 18px 28px;
  }

  /* Fila completa */
  .full-width {
    grid-column: span 2;
  }

  /* Campos */
  .form-field {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  label {
    font-size: 0.95rem;
    color: #ffffffd9;
  }

  /* Input  */
  .input-box {
    position: relative;
    width: 100%;
  }

  .input-box input,
  .select-wrapper select {
    appearance: none;
    -moz-appearance: none;
    -webkit-appearance: none;

    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;

    height: 42px;
    width: 100%;
    padding: 0 36px 0 12px;
    color: #fff;
    font-size: 0.95rem;

    outline: none !important;
    transition:
      border-color 0.2s ease,
      background-color 0.2s ease,
      box-shadow 0.2s ease;
  }

  .input-box input:focus,
  .input-box input:focus-visible {
    outline: none !important;
    box-shadow: none !important;
  }

  .input-box input::placeholder {
    color: #bfbfbf;
    opacity: 0.85;
    font-style: italic;
  }

  .pin-input {
    letter-spacing: 6px;
    text-align: center;
  }

  .pin-input::placeholder {
    color: #bfbfbf;
    opacity: 0.85;
    font-style: italic;
  }

  .border-anim {
    pointer-events: none;
    position: absolute;
    inset: 0;
    border-radius: 10px;
    border: 2px solid #b79b58;
    clip-path: inset(0 100% 0 0);
    transition: clip-path 0.4s ease-in-out;
  }

  .input-box input:focus {
    border-color: transparent;
    background: rgba(0, 0, 0, 0.15);
  }

  .input-box input:focus + .border-anim {
    clip-path: inset(0 0 0 0);
  }

  .select-wrapper {
    position: relative;
  }

  .select-wrapper select {
    cursor: pointer;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    color: #ffffff;
    font-size: 0.95rem;
    padding: 0 36px 0 12px;
    height: 42px;
    width: 100%;
    outline: none;
    transition:
      border-color 0.2s ease,
      background-color 0.2s ease,
      box-shadow 0.2s ease;
  }

  .select-wrapper select option[disabled][value=""] {
    color: #bfbfbf;
    font-style: italic;
  }

  .select-wrapper select option {
    background: #1e1e1e;
    color: #f5f5f5;
  }

  .select-wrapper select:focus {
    border-color: #c9b26a;
    background: rgba(255, 255, 255, 0.08);
    box-shadow: 0 0 0 2px rgba(201, 178, 106, 0.35);
  }

  .select-icon {
    position: absolute;
    right: 12px;
    top: 50%;
    transform: translateY(-50%);
    pointer-events: none;
    color: #bfbfbf;
  }

  .select-wrapper select:focus + .select-icon {
    color: #b79b58;
  }

  .checkbox-line {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.9rem;
  }

  .checkbox-line input {
    accent-color: #b79b58;
  }

  .signup-btn {
    margin-top: 22px;
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

  .signup-btn:hover:not(:disabled) {
    background: #b79b58;
    border-color: #b79b58;
    color: #000;
    transform: translateY(-2px);
    box-shadow: 0 4px 14px rgba(183, 155, 88, 0.4);
  }

  .signup-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .footer-text {
    text-align: center;
    margin-top: 14px;
    font-size: 0.9rem;
  }

  .link {
    color: #b79b58;
    text-decoration: none;
  }

  .link:hover {
    text-decoration: underline;
  }

  .error-message {
    font-size: 0.8rem;
    color: #f87171;
    margin-top: 4px;
  }

  @media (max-width: 768px) {
    .signup-wrapper {
      padding: 24px 20px;
    }

    .form-grid {
      grid-template-columns: 1fr;
    }

    .full-width {
      grid-column: span 1;
    }
  }

  /* === solo para icono ojo, igual que en login === */
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
