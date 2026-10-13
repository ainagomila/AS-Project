<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <header class="modal-header">
        <h3>Add Bank Account</h3>
        <button class="close" @click="$emit('close')">✕</button>
      </header>

      <form class="modal-body" @submit.prevent="submit">
        
        <!-- IBAN -->
        <div class="field">
          <label>Account Number (IBAN)</label>
          <input
            v-model="form.number"
            placeholder="ES34 6788 1234 5678 9012 3456"
            data-testid="add-account-iban-input"
            @input="onIbanInput"
            maxlength="29"
            required
          />
          <small v-if="errors.number" class="err">{{ errors.number }}</small>
        </div>

        <!-- Account name -->
        <div class="field">
          <label>Account Name</label>
          <input
            v-model.trim="form.name"
            placeholder="Main account, Savings..."
            data-testid="add-account-name-input"
            @input="validateName"
            maxlength="16"       
            required
          />
          <small v-if="errors.name" class="err">{{ errors.name }}</small>
        </div>

        <!-- Bank -->
        <div class="field">
          <label>Bank</label>
          <input
            v-model.trim="form.bank"
            placeholder="Santander, Abanca, BBVA..."
            data-testid="add-account-bank-input"
            @input="validateBank"
            maxlength="16"       
            required
          />
          <small v-if="errors.bank" class="err">{{ errors.bank }}</small>
        </div>

        <!-- Amount -->
        <div class="field">
          <label>Amount</label>
          <input
            v-model.number="form.amount"
            type="number"
            min="0"
            :max="MAX_AMOUNT"
            step="0.01"
            placeholder="1000"
            data-testid="add-account-balance-input"
            @input="validateAmount"
            required
          />
          <small v-if="errors.amount" class="err">{{ errors.amount }}</small>
        </div>

        <!-- Currency -->
        <div class="field">
          <label>Currency</label>
          <select
            v-model="form.currency"
            data-testid="add-account-currency-select"
            @change="validateCurrency"
            required
          >
            <option value="EUR">EUR (€)</option>
            <option value="USD">USD ($)</option>
            <option value="GBP">GBP (£)</option>
          </select>
          <small v-if="errors.currency" class="err">{{ errors.currency }}</small>
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
            data-testid="add-account-submit-btn"
          >
            {{ saving ? 'Saving...' : 'Add Account' }}
          </button>
        </footer>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed } from 'vue'

const MAX_AMOUNT = 1_000_000_000 // 1 billón (1.000.000.000)

defineProps({
  saving: { type: Boolean, default: false }
})

const emit = defineEmits(['close', 'submit'])

const form = reactive({
  number: '',
  name: '',
  bank: '',
  amount: null,
  currency: 'EUR'
})

const errors = reactive({})

/* ========== IBAN CHECKSUM ========== */
function isValidSpanishIban(rawValue) {
  const iban = (rawValue || '').replace(/\s+/g, '').toUpperCase()
  if (!/^ES\d{22}$/.test(iban)) return false

  const rearranged = iban.slice(4) + iban.slice(0, 4)

  let numeric = ''
  for (const ch of rearranged) {
    const code = ch.charCodeAt(0)
    numeric += (code >= 65 && code <= 90) ? (code - 55).toString() : ch
  }

  let remainder = 0
  for (let i = 0; i < numeric.length; i += 7) {
    const block = remainder.toString() + numeric.slice(i, i + 7)
    remainder = Number(block) % 97
  }

  return remainder === 1
}

/* ========== VALIDADORES ========== */

function validateIban() {
  let raw = form.number.replace(/\s+/g, '').toUpperCase()

  if (!raw) {
    errors.number = 'IBAN is required.'
    return
  }

  if (!raw.startsWith('ES')) {
    errors.number = 'IBAN must start with "ES" (Spanish accounts only).'
    return
  }

  if (!/^ES\d{22}$/.test(raw)) {
    errors.number = 'Invalid Spanish IBAN format (ES + 22 digits).'
    return
  }

  if (!isValidSpanishIban(raw)) {
    errors.number = 'Invalid IBAN (checksum failed).'
    return
  }

  delete errors.number
}

function formatIbanLive() {
  let raw = form.number.replace(/\s+/g, '').toUpperCase()

  if (raw.length > 24) raw = raw.slice(0, 24)

  form.number = raw.replace(/(.{4})/g, '$1 ').trim()
}

function onIbanInput() {
  formatIbanLive()
  validateIban()
}

function validateName() {
  const v = (form.name || '').trim()
  if (!v) errors.name = 'Please provide a descriptive name.'
  else if (v.length < 2) errors.name = 'Name is too short.'
  else delete errors.name
}

function validateBank() {
  const v = (form.bank || '').trim()

  if (!v) {
    errors.bank = 'Please specify the bank.'
    return
  }

  if (v.length < 2) {
    errors.bank = 'Bank name is too short.'
    return
  }

  // RESTRICCIÓN: no permitir "Kofre Bank" en ninguna forma
  if (/kofre\s*bank/i.test(v)) {
    errors.bank = 'Incorrect bank name.'
    return
  }

  delete errors.bank
}

function validateAmount() {
  const v = form.amount

  if (v === null || v === '' || isNaN(v)) {
    errors.amount = 'Amount must be a number.'
    return
  }

  const num = Number(v)

  if (num < 0) {
    errors.amount = 'Amount must be ≥ 0.'
    return
  }

  if (num > MAX_AMOUNT) {
    errors.amount = `Amount must be ≤ ${MAX_AMOUNT.toLocaleString('en-US')}.`
    return
  }

  delete errors.amount
}

function validateCurrency() {
  const curr = (form.currency || '').trim().toUpperCase()

  if (!curr) {
    errors.currency = 'Currency is required.'
    return
  }

  if (curr !== 'EUR') {
    errors.currency = 'Only EUR accounts are enabled at the moment.'
    return
  }

  delete errors.currency
}

/* ========== VALIDACIÓN GLOBAL ========== */
function validateAll() {
  validateIban()
  validateName()
  validateBank()
  validateAmount()
  validateCurrency()
  return Object.keys(errors).length === 0
}

/* ========== BOTÓN SUBMIT ========== */
const canSubmit = computed(() => {
  const raw = form.number.replace(/\s+/g, '').toUpperCase()

  const nameOk = (form.name || '').trim().length >= 2
  const bankOk = (form.bank || '').trim().length >= 2 && !errors.bank

  const amountNumeric =
    form.amount !== null &&
    form.amount !== '' &&
    !isNaN(form.amount)

  const amountOk =
    amountNumeric &&
    Number(form.amount) >= 0 &&
    Number(form.amount) <= MAX_AMOUNT &&
    !errors.amount

  const currOk = form.currency === 'EUR' && !errors.currency
  const ibanOk = /^ES\d{22}$/.test(raw) && !errors.number

  return (
    ibanOk &&
    nameOk &&
    bankOk &&
    amountOk &&
    currOk &&
    Object.keys(errors).length === 0
  )
})

/* ========== SUBMIT ========== */
function submit() {
  if (!validateAll()) return

  const rawIban = form.number.replace(/\s+/g, '').toUpperCase()

  emit('submit', {
    iban: rawIban,
    name: form.name.trim(),
    bank: form.bank.trim(),
    balance: Number(form.amount),
    currency: form.currency.trim().toUpperCase()
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
  
  .modal-body {
    padding: 18px 20px 20px;
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
  
  /* === INPUTS y SELECTS  === */
  .field input,
  .field select {
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
  
  .field select {
    cursor: pointer;
  }
  
  .field select option {
    background: #1e1e1e;
    color: #f5f5f5;
  }
  
  /* PLACEHOLDERS */
  .field input::placeholder {
    color: #bfbfbf;
    opacity: 0.55;
    font-style: italic;
  }
  
  .field input:focus::placeholder {
    color: rgba(191, 191, 191, 0.3);
  }
  
  /* === Focus dorado === */
  .field input:focus,
  .field select:focus {
    border-color: #c9b26a;
    background: rgba(255, 255, 255, 0.08);
    box-shadow: 0 0 0 2px rgba(201, 178, 106, 0.35);
    outline: none;
  }
  
  /* Errores */
  .err {
    color: #ffb4b4;
    font-size: 0.8rem;
  }
  
  /* Footer botones */
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
  }
  
  .btn.primary:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  </style>
  