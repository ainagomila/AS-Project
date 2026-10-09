<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <header class="modal-header">
        <h3>Add Card</h3>
        <button class="close" @click="$emit('close')">✕</button>
      </header>

      <form class="modal-body" @submit.prevent="submit">
        <!-- PAN (full width) -->
        <div class="field field--full">
          <label>Card Number</label>
          <input
            v-model="form.cardNumber"
            placeholder="1234 5678 9012 3456"
            maxlength="19"
            data-testid="add-card-number-input"
            @input="onCardNumberInput"
            required
          />
          <small v-if="errors.cardNumber" class="err">{{ errors.cardNumber }}</small>
        </div>

        <!-- PIN -->
        <div class="field">
          <label>PIN (4 digits)</label>
          <input
            v-model="form.pin"
            type="password"
            maxlength="4"
            placeholder="••••"
            data-testid="add-card-pin-input"
            @input="validatePin"
            required
          />
          <small v-if="errors.pin" class="err">{{ errors.pin }}</small>
        </div>

        <!-- CVV -->
        <div class="field">
          <label>CVV</label>
          <input
            v-model="form.cvv"
            type="password"
            maxlength="3"
            placeholder="123"
            data-testid="add-card-cvv-input"
            @input="validateCvv"
            required
          />
          <small v-if="errors.cvv" class="err">{{ errors.cvv }}</small>
        </div>

        <!-- Expiration -->
        <div class="field">
          <label>Expiration date</label>

          <div class="expiry-row">
            <input
              v-model="form.expireMonth"
              placeholder="MM"
              maxlength="2"
              class="expiry-input expiry-mm"
              data-testid="add-card-expire-month-input"
              @input="validateExpire"
              required
            />
            <span class="expiry-separator">/</span>
            <input
              v-model="form.expireYear"
              placeholder="YY"
              maxlength="4"
              class="expiry-input expiry-yy"
              data-testid="add-card-expire-year-input"
              @input="validateExpire"
              required
            />
          </div>

          <small v-if="errors.expireDate" class="err">{{ errors.expireDate }}</small>
        </div>

        <!-- Card Type -->
        <div class="field">
          <label>Card Type</label>
          <select
            v-model="form.type"
            data-testid="add-card-type-select"
            @change="validateType"
            required
          >
            <option value="">Select type...</option>
            <option value="DEBIT">Debit</option>
            <option value="CREDIT">Credit</option>
          </select>
          <small v-if="errors.type" class="err">{{ errors.type }}</small>
        </div>

        <!-- Alias -->
        <div class="field">
        <label>Alias</label>
        <input
          v-model.trim="form.alias"
          placeholder="Travel, Groceries..."
          data-testid="add-card-alias-input"
          maxlength="14"           
          @input="validateAlias"   
        />
        <small v-if="errors.alias" class="err">{{ errors.alias }}</small>
      </div>


        <!-- Bank (readonly) -->
        <div class="field">
          <label>Bank</label>
          <input
            class="readonly-input"
            :value="form.bank"
            placeholder="Select an account first"
            data-testid="add-card-bank-input"
            readonly
            @keydown.prevent
            @input.prevent
          />
          <small class="hint">
            Bank is automatically set from the selected account.
          </small>
        </div>

        <!-- Link to Account (IBAN) -->
        <div class="field field--full">
          <label>Link to Account</label>
          <select
            v-model="form.accountIban"
            @change="onAccountChange"
            data-testid="add-card-account-select"
            required
          >
            <option value="">Select account...</option>
            <option
              v-for="account in accounts"
              :key="account.iban"
              :value="account.iban"
            >
              {{ account.name }} - {{ account.iban }}
            </option>
          </select>
          <small v-if="errors.accountIban" class="err">{{ errors.accountIban }}</small>
        </div>

        <footer class="modal-footer">
          <button
            type="button"
            class="btn ghost"
            @click="$emit('close')"
          >
            Cancel
          </button>
          <button
            type="submit"
            class="btn primary"
            :disabled="saving || !canSubmit"
            data-testid="add-card-submit-btn"
          >
            {{ saving ? 'Adding...' : 'Add Card' }}
          </button>
        </footer>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed } from 'vue'

const props = defineProps({
  saving: Boolean,
  accounts: { type: Array, default: () => [] },
})

const emit = defineEmits(['close', 'submit'])

const form = reactive({
  cardNumber: '',
  alias: '',
  pin: '',
  expireMonth: '',
  expireYear: '',
  cvv: '',
  type: '',
  bank: '',
  accountIban: '',
})

const errors = reactive({})

/* ======== FORMATO Y VALIDACIONES ======== */

function formatCardNumber() {
  let value = form.cardNumber.replace(/\s/g, '').replace(/\D/g, '')
  form.cardNumber = value.match(/.{1,4}/g)?.join(' ') || value
}

function validateCardNumber() {
  const raw = form.cardNumber.replace(/\s/g, '')
  if (!raw) {
    errors.cardNumber = 'Card number is required.'
  } else if (!/^\d{16}$/.test(raw)) {
    errors.cardNumber = 'Card number must be 16 digits.'
  } else {
    delete errors.cardNumber
  }
}

function onCardNumberInput() {
  formatCardNumber()
  validateCardNumber()
}

function validatePin() {
  const v = form.pin || ''
  if (!v) {
    errors.pin = 'PIN is required.'
  } else if (!/^\d{4}$/.test(v)) {
    errors.pin = 'PIN must be 4 digits.'
  } else {
    delete errors.pin
  }
}

function validateCvv() {
  const v = form.cvv || ''
  if (!v) {
    errors.cvv = 'CVV is required.'
  } else if (!/^\d{3}$/.test(v)) {
    errors.cvv = 'CVV must be 3 digits.'
  } else {
    delete errors.cvv
  }
}

function validateExpire() {
  delete errors.expireDate

  const m = Number(form.expireMonth)
  const yStr = (form.expireYear || '').trim()
  if (!(m >= 1 && m <= 12)) {
    errors.expireDate = 'Invalid expiration month.'
    return
  }

  if (!yStr) {
    errors.expireDate = 'Invalid expiration year.'
    return
  }

  let fullYear
  if (yStr.length === 2) {
    fullYear = Number('20' + yStr)
  } else if (yStr.length === 4) {
    fullYear = Number(yStr)
  } else {
    errors.expireDate = 'Invalid expiration year.'
    return
  }

  const now = new Date()
  const thisYear = now.getFullYear()
  const thisMonth = now.getMonth() + 1

  if (
    !fullYear ||
    fullYear < thisYear ||
    (fullYear === thisYear && m < thisMonth)
  ) {
    errors.expireDate = 'Card is expired.'
  }
}

function validateType() {
  if (!form.type) {
    errors.type = 'Select card type.'
  } else {
    delete errors.type
  }
}

function validateAccountIban() {
  if (!form.accountIban) {
    errors.accountIban = 'Select an account.'
  } else {
    delete errors.accountIban
  }
}

function syncBank() {
  const acc = props.accounts.find((a) => a.iban === form.accountIban)
  form.bank = acc ? acc.bank : ''
}

function onAccountChange() {
  syncBank()
  validateAccountIban()
}

function validateAll() {
  Object.keys(errors).forEach((k) => delete errors[k])
  validateCardNumber()
  validatePin()
  validateCvv()
  validateExpire()
  validateType()
  validateAccountIban()
  return Object.keys(errors).length === 0
}

/* ======== BOTÓN HABILITADO / DESHABILITADO ======== */

const canSubmit = computed(() => {
  const raw = form.cardNumber.replace(/\s/g, '')
  const basicFilled =
    raw &&
    form.pin &&
    form.cvv &&
    form.expireMonth &&
    form.expireYear &&
    form.type &&
    form.accountIban

  if (!basicFilled) return false

  // Chequeos rápidos de formato
  if (!/^\d{16}$/.test(raw)) return false
  if (!/^\d{4}$/.test(form.pin)) return false
  if (!/^\d{3}$/.test(form.cvv)) return false

  const m = Number(form.expireMonth)
  if (!(m >= 1 && m <= 12)) return false

  const yStr = (form.expireYear || '').trim()
  if (!(yStr.length === 2 || yStr.length === 4)) return false

  // Si ya hay errores registrados, tampoco dejamos
  if (Object.keys(errors).length > 0) return false

  return true
})

/* ======== SUBMIT ======== */

function submit() {
  if (!validateAll()) return

  const raw = form.cardNumber.replace(/\s/g, '')
  const month = form.expireMonth.trim().padStart(2, '0')
  let year = form.expireYear.trim()
  if (year.length === 4) {
    year = year.slice(-2) // "2025" -> "25"
  }
  const expireDate = `${month}/${year}` // MM/yy

  emit('submit', {
    iban: form.accountIban,
    body: {
      pan: raw,
      expireDate,
      alias: form.alias || null,
      cvv: form.cvv,
      pin: form.pin,
      type: form.type,
      bank: form.bank,
    },
  })
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.modal {
  width: min(560px, 92vw);
  background: #1e1e1e;
  color: #f5f5f5;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  box-shadow: 0 20px 80px rgba(0, 0, 0, 0.6);
  overflow: hidden;
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

/* GRID 2 columnas */
.modal-body {
  padding: 18px 20px 20px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  column-gap: 16px;
  row-gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field--full {
  grid-column: 1 / -1;
}

.field label {
  font-size: 0.9rem;
  color: #e8e8e8;
}

.field input,
.field select,
.expiry-input {
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

/* PLACEHOLDER */
.field input::placeholder,
.expiry-input::placeholder {
  color: #bfbfbf;
  opacity: 0.55;
  font-style: italic;
}

/* Al enfocar se atenúa el placeholder */
.field input:focus::placeholder,
.expiry-input:focus::placeholder {
  color: rgba(191, 191, 191, 0.3);
}

/* Focus dorado */
.field input:focus,
.field select:focus,
.expiry-input:focus {
  border-color: #c9b26a;
  background: rgba(255, 255, 255, 0.08);
  box-shadow: 0 0 0 2px rgba(201, 178, 106, 0.35);
}

.field select {
  cursor: pointer;
}

.field select option {
  background: #1e1e1e;
  color: #f5f5f5;
}

/* Expiration compacta */
.expiry-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.expiry-mm {
  width: 70px !important;
}

.expiry-yy {
  width: 110px !important;
}

.expiry-separator {
  color: #ccc;
  font-size: 1.2rem;
  margin-top: 2px;
}

/* Bank readonly */
.readonly-input {
  background: rgba(255, 255, 255, 0.03);
  border-style: dashed;
  cursor: not-allowed;
}

.err {
  color: #ffb4b4;
  font-size: 0.8rem;
}

.hint {
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.75rem;
}

/* Footer ocupa toda la grid */
.modal-footer {
  grid-column: 1 / -1;
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
}

.btn.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Responsive: una columna en móvil */
@media (max-width: 640px) {
  .modal-body {
    grid-template-columns: 1fr;
  }

  .field--full {
    grid-column: 1 / 2;
  }

  .modal {
    width: 95vw;
  }
}
</style>
