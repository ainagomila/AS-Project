<template>
  <div class="transfer-page">
    <HeaderLayout title="Kofre" />

    <div class="transfer-content">
      <div class="transfer-wrapper">
        <h2 class="transfer-title">New transfer</h2>
        <p class="transfer-sub">
          Review the source account and fill the beneficiary data to proceed.
        </p>

        <form class="form-grid" @submit.prevent="openVerifyModal">
          <!-- FROM -->
          <div class="form-field full">
            <label>From (source account)</label>
            <div class="input-box readonly">
              <input
                :value="fromLabel"
                type="text"
                readonly
                aria-readonly="true"
                data-testid="transfer-source-account-display"
              />
              <span class="border-anim"></span>
            </div>
            <p
              v-if="account && !loadingAccount"
              class="hint"
              data-testid="transfer-available-balance"
            >
              Available balance:
              {{ account.balance?.toLocaleString('es-ES', { minimumFractionDigits: 2 }) ?? '—' }}
              {{ account.currency || 'EUR' }}
            </p>
            <p v-if="accountError" class="hint error" data-testid="transfer-account-error">
              {{ accountError }}
            </p>
          </div>

          <!-- Beneficiary full name -->
          <div class="form-field full">
            <label for="beneficiary">Beneficiary full name</label>
            <div class="input-box">
              <input
                id="beneficiary"
                v-model.trim="form.beneficiary"
                type="text"
                placeholder="Enter full name"
                maxlength="30"
                required
                data-testid="transfer-beneficiary-input"
              />
              <span class="border-anim"></span>
            </div>
          </div>

          <!-- Destination IBAN -->
          <div class="form-field full">
            <label for="iban">Destination IBAN</label>
            <div class="input-box">
              <input
                id="iban"
                v-model="form.destinationIban"
                type="text"
                placeholder="Enter destination IBAN"
                @input="normalizeIban"
                required
                data-testid="transfer-iban-input"
              />
              <span class="border-anim"></span>
            </div>
            <p
              v-if="ibanStatus !== 'empty'"
              class="hint"
              :class="{ error: ibanStatus === 'invalid', ok: ibanStatus === 'valid' }"
              data-testid="transfer-iban-status"
            >
              {{
  isSameAccount
    ? 'You cannot transfer money to the same account'
    : ibanStatus === 'valid'
      ? `IBAN format OK (${ibanCountry || '—'})`
      : 'Invalid IBAN (use country code + digits, e.g. ESkk …)'
}}
            </p>
          </div>

          <!-- Amount -->
          <div class="form-field">
            <label for="amount">Amount (EUR)</label>
            <div class="input-box">
              <input
                id="amount"
                v-model="form.amount"
                inputmode="decimal"
                type="text"
                placeholder="Amount"
                @input="sanitizeAmount"
                required
                data-testid="transfer-amount-input"
              />
              <span class="border-anim"></span>
            </div>
            <p v-if="amountError" class="hint error" data-testid="transfer-amount-error">
              {{ amountError }}
            </p>
          </div>



          <!-- Concept -->
          <div class="form-field full">
            <label for="concept">Concept</label>
            <div class="input-box">
              <input
                id="concept"
                v-model.trim="form.concept"
                type="text"
                placeholder="Enter concept"
                maxlength="80"
                required
                data-testid="transfer-concept-input"
              />
              <span class="border-anim"></span>
            </div>
          </div>

          <!-- Actions -->
          <div class="actions full">
            <RouterLink :to="`/accounts/${route.params.id}`" class="btn-secondary back-link-btn">
              Back to account
            </RouterLink>

            <button
              type="submit"
              class="btn-primary"
              :disabled="!isFormValid"
              data-testid="transfer-submit-btn"
            >
              Send transfer
            </button>
          </div>
        </form>
      </div>

      <p class="back-link-mobile">
        <RouterLink :to="`/accounts/${route.params.id}`">← Back to account</RouterLink>
      </p>
    </div>

    <!-- MODAL PIN -->
    <div v-if="showVerify" class="modal-overlay" @click.self="closeVerifyModal">
      <div class="modal-card pin-modal" :class="{ shake: codeError }" role="dialog" aria-modal="true">
        <div class="modal-header">
          <h3 class="modal-title">Confirm transfer</h3>
        </div>

        <p class="modal-text">
          You are about to send <strong>{{ formattedAmount }}</strong> {{ form.currency }}
          to <strong>{{ form.beneficiary || 'the beneficiary' }}</strong>.
        </p>

        <p class="modal-text">Enter your 6-digit PIN to confirm:</p>

        <div class="pin-input" @paste.stop.prevent="handlePastePin">
          <input
            v-for="(_, i) in 6"
            :key="'pin-' + i"
            :ref="(el) => (pinBoxes[i] = el)"
            class="pin-box"
            type="password"
            maxlength="1"
            inputmode="numeric"
            v-model="enteredPin[i]"
            @input="handlePinInput(i)"
            @keydown="handlePinKey(i, $event)"
            data-testid="transfer-pin-input"
          />
        </div>

        <p v-if="codeError" class="modal-error" data-testid="transfer-pin-error">
          Invalid PIN. Please try again.
        </p>
        <p v-else class="modal-text small" data-testid="transfer-pin-hint">
          This PIN is required to validate your operation.
        </p>

        <div class="modal-actions">
          <button class="btn-secondary" @click="closeVerifyModal">Cancel</button>
          <button class="btn-primary" @click="confirmTransfer" data-testid="transfer-pin-confirm-btn">
            Confirm
          </button>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <div v-if="toast.open" class="toast">
  <div class="toast-inner" :class="toast.type">
    <div class="toast-icon" :class="toast.type">
      {{ toast.type === 'error' ? '!' : '✓' }}
    </div>

    <div class="toast-texts">
      <p class="toast-title">
        {{ toast.type === 'error' ? 'Error' : 'Transfer sent' }}
      </p>
      <p class="toast-message">{{ toast.text }}</p>
    </div>

    <button class="toast-close" @click="handleToastClose">✕</button>
  </div>
</div>
  </div>
</template>

<script setup>
import HeaderLayout from '@/components/layout/HeaderLayout.vue'
import { ref, computed, nextTick, onMounted } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getAccount, createTransfer } from '@/api/userService'

/* ---- ROUTER + STORE ---- */
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

/* ---- ACCOUNT ---- */
const account = ref(null)
const loadingAccount = ref(true)
const accountError = ref(null)

function formatGroups4(s) {
  return String(s)
    .replace(/(.{4})/g, '$1 ')
    .trim()
}

const isSameAccount = computed(() => {
  if (!account.value) return false
  const source = account.value.iban.replace(/\s/g, '').toUpperCase()
  const dest = (form.value.destinationIban || '').replace(/\s/g, '').toUpperCase()
  return dest.length >= 4 && dest === source
})

onMounted(async () => {
  loadingAccount.value = true
  accountError.value = null

  try {
    if (!userStore.isAuthenticated || !userStore.dni) {
      router.push('/login')
      return
    }

    const iban = String(route.params.id)
    const data = await getAccount(userStore.dni, iban)

    account.value = {
      bank: data.bank,
      name: data.name,
      iban: data.iban,
      balance: Number(data.balance ?? 0),
      currency: (data.currency || 'EUR').toUpperCase(),
    }
  } catch (err) {
    console.error('Error fetching account:', err)
    accountError.value = 'Unable to load account information.'
  } finally {
    loadingAccount.value = false
  }
})

/* ---- FROM LABEL ---- */
const fromLabel = computed(() => {
  if (loadingAccount.value) return 'Loading account...'
  if (accountError.value) return 'Error loading account'
  if (!account.value) return 'No account selected'

  const a = account.value
  const left = [a.bank, a.name].filter(Boolean).join(' · ')
  const iban = a.iban ? formatGroups4(a.iban.toUpperCase()) : ''
  return iban ? `${left} · ${iban}` : left
})

/* ---- FORM DATA ---- */
const form = ref({
  beneficiary: '',
  destinationIban: '',
  amount: '',
  currency: 'EUR',
  concept: '',
})

/* ---- IBAN ---- */
function normalizeIban() {
  let raw = (form.value.destinationIban || '')
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, '')
    .slice(0, 34)
  form.value.destinationIban = formatGroups4(raw)

}

function isValidIbanGeneric(iban) {
  const clean = (iban || '').toUpperCase().replace(/\s+/g, '')
  if (!/^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$/.test(clean)) return false

  const rearranged = clean.slice(4) + clean.slice(0, 4)
  const numeric = rearranged.replace(/[A-Z]/g, (ch) => String(ch.charCodeAt(0) - 55))

  let remainder = '0'
  let i = 0
  while (i < numeric.length) {
    const block = remainder + numeric.substr(i, 9)
    remainder = String(parseInt(block, 10) % 97)
    i += 9
  }
  return parseInt(remainder, 10) === 1
}

const ibanCountry = computed(() => {
  const clean = (form.value.destinationIban || '').replace(/\s+/g, '').toUpperCase()
  return clean.length >= 2 ? clean.slice(0, 2) : ''
})

const ibanStatus = computed(() => {
  const v = form.value.destinationIban?.trim()
  if (!v) return 'empty'

  // ❌ No permetre transferències al mateix compte
  if (isSameAccount.value) return 'invalid'

  return isValidIbanGeneric(v) ? 'valid' : 'invalid'
})

/* ---- AMOUNT ---- */
function sanitizeAmount(evt) {
  let s = String(evt?.target?.value ?? form.value.amount ?? '')
  s = s.replace(/[^0-9.,]/g, '').replace(',', '.')
  const firstDot = s.indexOf('.')
  if (firstDot !== -1) s =
    s.slice(0, firstDot + 1) + s.slice(firstDot + 1).replace(/\./g, '')
  if (s.startsWith('.')) s = '0' + s
  const parts = s.split('.')
  if (parts.length > 1) {
    parts[1] = parts[1].slice(0, 2)
    s = parts[0] + '.' + parts[1]
  }
  form.value.amount = s
}

const amountNumber = computed(() => {
  const n = Number(form.value.amount?.replace(',', '.') || '0')
  return Number.isFinite(n) ? n : NaN
})

const amountError = computed(() => {
  if (!form.value.amount) return ''
  if (Number.isNaN(amountNumber.value) || amountNumber.value <= 0) return 'Enter a positive amount'

  if (form.value.currency === 'EUR' && account.value?.balance != null) {
    if (amountNumber.value > Number(account.value.balance))
      return 'Amount exceeds available balance'
  }
  return ''
})

const formattedAmount = computed(() => {
  const n = amountNumber.value
  if (!Number.isFinite(n)) return '—'
  return n.toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
})

const isFormValid = computed(
  () =>
    !!form.value.beneficiary &&
    ibanStatus.value === 'valid' &&
    !!form.value.amount &&
    !amountError.value &&
    !!form.value.currency &&
    !isSameAccount.value &&
    !!form.value.concept,
)

/* ---- PIN MODAL ---- */
const showVerify = ref(false)
const enteredPin = ref(['', '', '', '', '', ''])
const pinBoxes = ref([])
const codeError = ref(false)

function openVerifyModal() {
  if (!isFormValid.value) return
  codeError.value = false
  enteredPin.value = ['', '', '', '', '', '']
  showVerify.value = true
  nextTick(() => pinBoxes.value?.[0]?.focus())
}

function closeVerifyModal() {
  showVerify.value = false
}

function handlePinInput(i) {
  let v = enteredPin.value[i] ?? ''
  if (!/^\d?$/.test(v)) {
    enteredPin.value[i] = ''
    return
  }
  if (v && i < 5) pinBoxes.value[i + 1]?.focus()
}

function handlePinKey(i, e) {
  if (e.key === 'Backspace') {
    if (enteredPin.value[i]) {
      enteredPin.value[i] = ''
    } else if (i > 0) {
      pinBoxes.value[i - 1]?.focus()
      enteredPin.value[i - 1] = ''
    }
  }
}

function handlePastePin(e) {
  const txt = (e.clipboardData?.getData('text') || '').replace(/\D/g, '').slice(0, 6)
  if (!txt) return
  enteredPin.value = Array.from({ length: 6 }, (_, i) => txt[i] || '')
  nextTick(() => {
    const filled = enteredPin.value.findIndex((ch) => !ch)
    const idx = filled === -1 ? 5 : filled
    pinBoxes.value[idx]?.focus()
  })
}

/* ---- TOAST ---- */
const toast = ref({
  open: false,
  text: '',
  actionText: 'Close',
  persist: false,
  onClose: null,
  type: 'success',
})

function showToast(message, { actionText = 'Close', persist = false, onClose = null, type='success' } = {}) {
  toast.value.open = true
  toast.value.text = message
  toast.value.actionText = actionText
  toast.value.persist = persist
  toast.value.onClose = typeof onClose === 'function' ? onClose : null
  toast.value.type = type

  // auto-cierra y, si hay callback, también navega
  if (!persist) {
    const cb = toast.value.onClose
    setTimeout(() => {
      // si ya se cerró manualmente, no hacemos nada
      if (!toast.value.open) return
      toast.value.open = false
      if (cb) cb()
    }, 2000)
  }
}

function handleToastClose() {
  const cb = toast.value.onClose
  toast.value.open = false
  if (cb) cb()
}

/* ---- CONFIRM TRANSFER ---- */
async function confirmTransfer() {
  const typed = enteredPin.value.join('')

  if (!/^\d{6}$/.test(typed)) {
    codeError.value = true
    setTimeout(() => (codeError.value = false), 1200)
    return
  }
  if (form.value.destinationIban.replace(/\s/g, '') === form.value.beneficiary.trim()) {
    showToast('No pots fer una transferència al mateix compte', 'error')
    return
  }
  console.log(account.value.currency)


  const payload = {
    beneficiary: form.value.beneficiary.trim(),
    destinationIban: form.value.destinationIban.replace(/\s+/g, ''),
    amount: Number(form.value.amount),
    currency: account.value.currency,
    concept: form.value.concept.trim(),
    pin: typed,
  }

  console.log('Payload transfer:', payload)

  try {
    await createTransfer(
      userStore.dni,
      route.params.id,
      payload,
    )

    showVerify.value = false

    showToast(
      `Transfer sent to ${form.value.beneficiary} (${formattedAmount.value} ${form.value.currency}).`,
      {
        persist: false,
        actionText: 'Close',
        onClose: () => router.push(`/accounts/${route.params.id}`),
      },
    )
  }  catch (err) {
  console.error("ERROR EN TRANSFERENCIA:", err);

  const status = err?.response?.status;
  const code = err?.response?.data?.code;

  // --- 400 INVALID PIN (shake modal) ---
  if (status === 400) {
    showToast("You can't send transfers between accounts with different currency.", {
      persist: false, type: 'error',
    });
    setTimeout(() => (codeError.value = false), 2000);
    return;
  }

  // --- 422 Different currency accounts ---
  if (status === 422) {
    showToast("Invalid pin.", {
      persist: false, type: 'error',
    });
    setTimeout(() => (codeError.value = false), 2000);
    return;
  }

  // --- Optional: insufficient balance ---
  if (status === 409 && code === "INSUFFICIENT_FUNDS") {
    showToast("Insufficient balance to complete the transfer.", {
      persist: false, type: 'error',
    });
    setTimeout(() => (codeError.value = false), 2000);
    return;
  }

  // --- Fallback generic error ---
  showToast("An unexpected error occurred. Please try again.", {
    persist: false, type: 'error',
  });
  setTimeout(() => (codeError.value = false), 2000);
}
}
</script>

<style scoped>
/* === LAYOUT GENERAL === */
.transfer-page {
  background: #1a1a1a;
  min-height: 100vh;
  color: #fff;
}

.transfer-content {
  min-height: calc(100vh - 65px);
  max-width: 900px;
  margin: 0 auto;
  padding: 80px 16px 40px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Card principal */
.transfer-wrapper {
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

.transfer-wrapper:hover,
.transfer-wrapper:focus-within {
  background: rgba(255, 255, 255, 0.1);
  transform: translateY(-3px);
}

.transfer-title {
  font-size: 1.4rem;
  font-weight: 600;
  margin: 0 0 4px;
}

.transfer-sub {
  margin: 0 0 20px;
  font-size: 0.9rem;
  color: #cccccc;
}

/* GRID */
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px 28px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-field.full {
  grid-column: 1 / -1;
}

.form-field label {
  font-size: 0.95rem;
  color: #ffffffd9;
}

@media (max-width: 768px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}

/* INPUT BOX */
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

.input-box input:focus,
.input-box select:focus {
  border-color: transparent;
  background: rgba(0, 0, 0, 0.15);
}

.input-box input:focus + .border-anim,
.input-box select:focus + .border-anim {
  clip-path: inset(0 0 0 0);
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

/* Readonly (From account): sin animación */
.input-box.readonly input[readonly] {
  cursor: not-allowed;
  color: #dddddd;
  border-color: rgba(255, 255, 255, 0.15);
}

.input-box.readonly input[readonly]:focus {
  border-color: rgba(255, 255, 255, 0.15);
  background: transparent;
}

.input-box.readonly input[readonly]:focus + .border-anim {
  clip-path: inset(0 100% 0 0);
  transition: none;
}

/* Hints */
.hint {
  font-size: 0.8rem;
  color: #d1d5db;
  margin-top: 2px;
}

.hint.ok {
  color: #8be59b;
}
.hint.error {
  color: #f87171;
}

/* Actions */
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn-primary {
  border-radius: 10px;
  border: 2px solid rgba(183, 155, 88, 0.45);
  background: transparent;
  color: #fff;
  padding: 10px 18px;
  cursor: pointer;
  font-weight: 600;
  transition: 0.25s ease;
}

.btn-primary:hover:not(:disabled) {
  background: #b79b58;
  color: #000;
  border-color: #b79b58;
  transform: translateY(-2px);
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
  padding: 10px 18px;
  cursor: pointer;
  transition: 0.25s ease;
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.08);
}

/* Back link mobile */
.back-link-mobile {
  display: none;
  font-size: 0.85rem;
  color: #9ca3af;
}

@media (max-width: 480px) {
  .actions {
    flex-direction: column-reverse;
    align-items: stretch;
  }
  .back-link-mobile {
    display: block;
    margin-top: 8px;
  }
  .back-link-btn {
    display: none;
  }
  .btn-primary,
  .btn-secondary {
    width: 100%;
  }
}

/* MODAL PIN */
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
  margin-bottom: 6px;
}

.modal-title {
  font-size: 1.05rem;
  font-weight: 700;
  margin: 0;
}

.modal-text {
  color: #dcdcdc;
  margin: 6px 0;
}

.modal-text.small {
  font-size: 0.85rem;
  color: #bababa;
}

.modal-error {
  color: #ff9696;
}

/* PIN boxes */
.pin-input {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin: 16px 0;
}

.pin-box {
  width: 42px;
  height: 48px;
  border-radius: 8px;
  background: #1f1f1f;
  border: 1px solid #d5b76f;
  color: #fff;
  text-align: center;
  font-size: 24px;
  outline: none;
}

.pin-box:focus {
  border-color: #f0cc7a;
  box-shadow: 0 0 0 2px rgba(240, 204, 122, 0.3);
}

/* Shake */
.shake {
  animation: shake 0.45s ease;
}

@keyframes shake {
  10%, 90% { transform: translateX(-2px); }
  20%, 80% { transform: translateX(4px); }
  30%, 50%, 70% { transform: translateX(-6px); }
  40%, 60% { transform: translateX(6px); }
}

/* Toast */
.toast {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 3000;
}

.toast-inner {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #222;
  color: #e5e7eb;
  border-radius: 999px;
  padding: 10px 16px 10px 12px;
  border: 1px solid #c9b26a;
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.5);
}

.toast-icon {
  width: 26px;
  height: 26px;
  border-radius: 999px;
  background: #10b981;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
  color: #f9fafb;
}

.toast-texts {
  display: flex;
  flex-direction: column;
}

.toast-title {
  font-size: 0.9rem;
  font-weight: 600;
}

.toast-message {
  font-size: 0.8rem;
  color: #d1d5db;
}

.toast-close {
  margin-left: 6px;
  border: none;
  background: transparent;
  color: #9ca3af;
  cursor: pointer;
  font-size: 14px;
}

.toast-close:hover {
  color: #f9fafb;
}
/* --- SUCCESS (default) --- */
.toast-inner.success {
  background: #222;
  border-color: #c9b26a;
}
.toast-icon.success {
  background: #10b981;
}

/* --- ERROR --- */
.toast-inner.error {
  background: #2a0000;
  border-color: #ff7070;
  box-shadow: 0 18px 40px rgba(255, 0, 0, 0.25);
}

.toast-icon.error {
  background: #ef4444;
  color: white;
}

.toast-inner.error .toast-title {
  color: #ff9b9b;
}

.toast-inner.error .toast-message {
  color: #ffcdcd;
}

</style>
