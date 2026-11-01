<template>
  <div class="page-container">
    <!-- Header global -->
    <HeaderLayout title="Kofre" />

    <div class="scroll-content">
      <div class="sections-container">
        <!-- Mensajes de carga o error -->
        <section v-if="loading" class="dashboard__section">
          <p>Cargando cuenta...</p>
        </section>
        <section v-else-if="error" class="dashboard__section">
          <p>{{ error }}</p>
        </section>

        <section v-else class="dashboard__section combined-header-balance">
          <header class="detail-header in-card">
            <div class="header-left">
              <button class="back-btn" @click="$router.push('/dashboard')">
                <ArrowLeft class="icon" /> Back
              </button>

              <h1 class="title">
                <Wallet class="icon-sm" />
                <span class="bank">{{ account.bank }}</span>
                <span class="dot">·</span>

                <!-- Alias editable -->
                <span class="name" v-if="!editingName">
                  {{ account.name }}
                  <button class="edit-inline" @click="startEditName" aria-label="Edit alias">
                    <Pencil class="icon" />
                  </button>
                </span>

                <span class="name edit" v-else>
                  <input
                    ref="nameInput"
                    v-model.trim="editName"
                    class="edit-input"
                    maxlength="20"
                    @keyup.enter="saveName"
                    @keyup.esc="cancelEdit"
                  />
                  <button
                    class="edit-accept"
                    :disabled="savingName"
                    @click="saveName"
                    aria-label="Save alias"
                  >
                    <Check class="icon" />
                  </button>
                  <button
                    class="edit-cancel"
                    :disabled="savingName"
                    @click="cancelEdit"
                    aria-label="Cancel"
                  >
                    <X class="icon" />
                  </button>
                </span>
              </h1>
            </div>

            <div class="header-actions">
              <button class="pill" @click="startTransfer">
                <Send class="icon" /> New Transfer
              </button>
              <button class="pill" @click="exportCSV">
                <Download class="icon" /> Export
              </button>
              <button class="pill delete" :disabled="account.bank === 'Kofre Bank'" @click="account.bank !== 'Kofre Bank' && (showDelete = true)">
                <Trash2 class="icon" /> Delete
              </button>
            </div>
          </header>

          <!-- Balance + IBAN -->
          <div
            class="balance-row"
            style="
              display: flex;
              justify-content: space-between;
              align-items: center;
              gap: 20px;
              flex-wrap: wrap;
            "
          >
            <div class="balance-block">
              <div class="label">Available Balance</div>
              <div class="balance">{{ formatCurrency(account.balance, account.currency) }}</div>

            </div>

            <div class="iban-block" style="text-align: right">
              <div class="label">IBAN</div>
              <div class="iban">
                <span>{{ account.iban }}</span>
                <button class="copy" @click="copyIban">
                  <Copy class="icon" /> {{ copied ? 'Copied' : 'Copy' }}
                </button>
              </div>
            </div>
          </div>
        </section>

        <!-- TRANSACCIONES -->
        <section class="dashboard__section" v-if="!loading && !error">
          <div class="tx-card">
            <div class="tx-toolbar">
              <h2 class="tx-title">Transactions</h2>
              <div class="toolbar-actions">
                <div class="search">
                  <Search class="icon" />
                  <input v-model="query" placeholder="Search by title..." />
                </div>
                <button class="pill subtle" @click="toggleOnlyNeg">
                  <Filter class="icon" />
                  {{ onlyExpenses ? 'All' : 'Only expenses' }}
                </button>
              </div>
            </div>

            <div class="tx-list">
              <div v-for="(tx, i) in filteredTx" :key="i" class="tx-row">
                <div class="tx-left">
                  <div class="tx-title">
                    <span class="badge" :class="tx.amount > 0 ? 'in' : 'out'">
                      {{ tx.amount > 0 ? 'IN' : 'OUT' }}
                    </span>
                    {{ tx.title }}
                  </div>
                  <div class="tx-date">{{ formatDate(tx.date) }}</div>
                </div>

                <div class="tx-right">
                  <span :class="tx.amount > 0 ? 'amt in' : 'amt out'">
                    {{ signedCurrency(tx.amount, account.currency) }}
                  </span>
                </div>
              </div>

              <div v-if="filteredTx.length === 0" class="empty">
                <span>No transactions found</span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>

    <!-- Modal 1: confirmar que quieres borrar -->
    <div v-if="showDelete" class="modal-overlay" @click.self="showDelete = false">
      <div class="modal-card">
        <h3 class="modal-title">Delete account</h3>
        <p class="modal-text">
          You are about to delete
          <strong>{{ account.bank }} · {{ account.name }}</strong
          >. This action cannot be undone.
        </p>
        <div class="modal-actions">
          <button class="pill subtle" @click="showDelete = false">Cancel</button>
          <button class="pill danger" @click="openPinModal">
            <Trash2 class="icon" /> Delete permanently
          </button>
        </div>
      </div>
    </div>

    <!-- Modal 2: PIN de 6 cifras con pads -->
    <div v-if="showPinModal" class="modal-overlay" @click.self="closePinModal">
      <div class="modal-card pin-modal">
        <div class="modal-header">
          <Lock class="modal-icon" />
          <h3 class="modal-title">Confirm with PIN</h3>
        </div>

        <p class="modal-text">Enter your 6-digit PIN to delete this account.</p>

        <div class="pin-input">
          <input
            v-for="(digit, index) in pinDigits"
            :key="index"
            class="pin-box"
            type="password"
            maxlength="1"
            inputmode="numeric"
            pattern="[0-9]*"
            v-model="pinDigits[index]"
            @input="handlePinInput(index, $event)"
            @keyup.backspace="handleBackspace(index, $event)"
          />
        </div>

        <div class="modal-actions">
          <button class="pill subtle" @click="closePinModal">Cancel</button>
          <button
            class="pill danger"
            :disabled="pinDigits.join('').length !== 6 || deleting"
            @click="confirmDelete"
          >
            <Trash2 class="icon" />
            <span v-if="!deleting">Confirm delete</span>
            <span v-else>Deleting...</span>
          </button>
        </div>
      </div>
    </div>

    <!-- TOAST (mensaje flotante) -->
    <transition name="fade">
      <div v-if="toast.visible" class="toast" :class="toast.type">
        {{ toast.message }}
      </div>
    </transition>
  </div>
</template>

<script setup>
import {
  ArrowLeft,
  Wallet,
  Download,
  Send,
  Copy,
  Search,
  Filter,
  Pencil,
  Trash2,
  Check,
  X,
  Lock,
} from 'lucide-vue-next'
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import HeaderLayout from '@/components/layout/HeaderLayout.vue'

import { useUserStore } from '@/stores/user'
import { getAccount, updateAccount, deleteAccount, getTransfers } from '@/api/userService.js'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// Estado principal
const loading = ref(true)
const error = ref(null)

const account = ref({
  id: route.params.id,
  bank: '',
  name: '',
  iban: '',
  balance: 0,
})

// Transacciones (transferencias)
const transactions = ref([])

// --- Filtros ---
const query = ref('')
const onlyExpenses = ref(false)

const filteredTx = computed(() => {
  let list = transactions.value

  if (onlyExpenses.value) {
    list = list.filter((t) => t.amount < 0)
  }

  if (query.value.trim()) {
    const q = query.value.toLowerCase()
    list = list.filter((t) => t.title.toLowerCase().includes(q))
  }

  return list
})

const copied = ref(false)

async function copyIban() {
  try {
    await navigator.clipboard.writeText(account.value.iban)
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch {
    showToast('Error copying IBAN', 'error')
  }
}

function toggleOnlyNeg() {
  onlyExpenses.value = !onlyExpenses.value
}

/**
 * Carga movimientos:
 *  - Transferencias de la cuenta (getTransfers)
 * y los mezcla en `transactions`.
 */
async function loadMovements() {
  if (!userStore.isAuthenticated || !userStore.dni || !account.value.iban) {
    console.log('Missing required data:', {
      authenticated: userStore.isAuthenticated,
      dni: userStore.dni,
      iban: account.value.iban,
    })
    return
  }

  try {
    console.log('Loading movements for:', {
      dni: userStore.dni,
      accountId: account.value.id,
      iban: account.value.iban,
      query: query.value,
      onlyExpenses: onlyExpenses.value,
    })

    const ibanClean = account.value.iban.replace(/\s+/g, '')

    // Siempre cargamos transferencias de esta cuenta
    const transfers = await getTransfers(userStore.dni, ibanClean, {
      q: query.value || undefined,
      onlyExpenses: onlyExpenses.value,
      sort: 'date,desc',
    })

    const transferTx = (transfers || []).map((tx) => ({
      title: tx.title || 'Transfer',
      date: tx.date,
      amount: Number(tx.amount) || 0,
      currency: tx.currency || 'EUR',
      kind: 'transfer',
    }))

    transactions.value = [...transferTx].sort(
      (a, b) => new Date(b.date) - new Date(a.date),
    )
  } catch (e) {
    console.error('Failed to load movements:', e)
    showToast('No se pudieron cargar los movimientos', 'error')
    transactions.value = []
  }
}

// recargar cuando cambian filtros
watch([query, onlyExpenses], loadMovements)

// Toast simple
const toast = ref({ visible: false, message: '', type: 'info' })
function showToast(message, type = 'info') {
  toast.value = { visible: true, message, type }
  setTimeout(() => (toast.value.visible = false), 2500)
}

// Cargar cuenta del BE
async function loadAccount() {
  loading.value = true
  error.value = null
  copied.value = false

  try {
    if (!userStore.isAuthenticated || !userStore.dni) {
      showToast('Inicia sesión para ver tu cuenta', 'error')
      router.push('/login')
      return
    }
    const id = String(route.params.id)
    const a = await getAccount(userStore.dni, id)
    if (!a) throw new Error('Account not found')

    account.value = {
      id: a.id ?? id,
      bank: a.bank ?? a.entity ?? '—',
      name: a.name ?? a.alias ?? a.bank ?? '—',
      iban: String(a.iban ?? a.number ?? a.id ?? '')
        .replaceAll(/\s+/g, '')
        .replaceAll(/(.{4})/g, '$1 ')
        .trim(),
      balance: Number(a.balance ?? 0),
      currency: a.currency || 'EUR',
    }

    await loadMovements()
  } catch (e) {
    console.error(e)
    error.value = 'No se pudo cargar la cuenta'
    showToast('No se pudo cargar la cuenta', 'error')
  } finally {
    loading.value = false
  }
}

onMounted(loadAccount)
watch(
  () => route.params.id,
  () => {
    loadAccount()
  },
)

// --- Alias editable (PATCH BE) ---
const editingName = ref(false)
const editName = ref('')
const nameInput = ref(null)
const savingName = ref(false)

function startEditName() {
  editingName.value = true
  editName.value = account.value.name
  nextTick(() => {
    nameInput.value?.focus()
    nameInput.value?.select()
  })
}

async function saveName() {
  const n = editName.value.trim()
  if (!n) return cancelEdit()
  try {
    savingName.value = true
    await updateAccount(userStore.dni, account.value.id, { name: n, alias: n })
    account.value.name = n
    editingName.value = false
    showToast('Alias actualizado', 'success')
  } catch (e) {
    console.error(e)
    showToast('No se pudo actualizar el alias', 'error')
  } finally {
    savingName.value = false
  }
}
function cancelEdit() {
  editingName.value = false
}

// --- Delete + PIN ---
const showDelete = ref(false)
const showPinModal = ref(false)
const pinDigits = ref(['', '', '', '', '', ''])
const deleting = ref(false)

function resetPin() {
  pinDigits.value = ['', '', '', '', '', '']
}

function openPinModal() {
  showDelete.value = false
  resetPin()
  showPinModal.value = true
  nextTick(() => {
    const first = document.querySelector('.pin-box')
    first?.focus()
  })
}

function closePinModal() {
  showPinModal.value = false
  resetPin()
}

function handlePinInput(index, event) {
  const value = event.target.value.replace(/[^0-9]/g, '')
  pinDigits.value[index] = value.slice(-1)

  if (pinDigits.value[index] && index < 5) {
    const boxes = document.querySelectorAll('.pin-box')
    boxes[index + 1]?.focus()
  }
}

function handleBackspace(index, event) {
  if (event.key === 'Backspace' && !pinDigits.value[index] && index > 0) {
    const boxes = document.querySelectorAll('.pin-box')
    boxes[index - 1]?.focus()
  }
}

async function confirmDelete() {
  const pin = pinDigits.value.join('')

  if (pin.length !== 6) {
    showToast('Introduce tu PIN de 6 dígitos', 'error')
    return
  }

  try {
    deleting.value = true
    await deleteAccount(userStore.dni, account.value.id, pin)
    showPinModal.value = false
    showToast('Cuenta eliminada', 'success')
    router.push('/dashboard')
  } catch (e) {
    console.error(e)
    showToast('Incorrect PIN. Could not delete the account.', 'error')
  } finally {
    deleting.value = false
  }
}

// --- Utils ---
function formatCurrency(num, curr) {
  return new Intl.NumberFormat('es-ES', { style: 'currency', currency: curr }).format(num)
}


function signedCurrency(num, curr) {
  const s = formatCurrency(Math.abs(num), curr)
  return (num >= 0 ? '+' : '−') + s
}

function formatDate(d) {
  if (!d) return ''

  let dt = new Date(d)

  if (Number.isNaN(dt.getTime())) {
    const base = String(d).slice(0, 10)
    dt = new Date(base + 'T00:00:00')
  }

  if (Number.isNaN(dt.getTime())) {
    return String(d)
  }

  return dt.toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  })
}


function startTransfer() {
  const id = account.value?.id ?? route.params.id
  router.push({ name: 'AccountTransfer', params: { id } })
}
function exportCSV() {
  const rows = [
    ['title', 'date', 'amount'],
    ...transactions.value.map((t) => [t.title, t.date, t.amount]),
  ]
  const csv = rows.map((r) => r.join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `transactions_${account.value.id}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
</script>


<style scoped>
/* Fondo global */
:global(html, body) {
  background-color: #222;
  margin: 0;
  padding: 0;
}

/* Layout base*/
.page-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  font-family: 'Satoshi', sans-serif;
  color: #f5f5f5;
  overflow: hidden;
  background-color: #222;
}
.scroll-content {
  flex: 1;
  overflow-y: auto;
  scroll-behavior: smooth;
  padding-top: 30px;
}
.sections-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  padding: 40px 20px;
  gap: 40px;
}

/* Card contenedor */
.dashboard__section {
  max-width: 1200px;
  width: 100%;
  border-radius: 20px;
  background: #2a2a2a;
  border: 1px solid #333;
  box-shadow: 0 4px 40px rgba(0, 0, 0, 0.3);
  padding: 22px 22px 24px;
  transition:
    border-color 0.3s ease,
    box-shadow 0.3s ease;
}
.dashboard__section:hover {
  border-color: #444;
  box-shadow: 0 4px 60px rgba(0, 0, 0, 0.45);
}

/* Header dentro del card combinado */
.detail-header.in-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 14px;
  margin-bottom: 12px;
  border-bottom: 1px solid #3a3a3a;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 1.6rem;
  font-weight: 700;
  color: #fff;
}
.title .bank {
  color: #e2e2e2;
  font-weight: 600;
}
.title .dot {
  opacity: 0.7;
}
.title .name {
  color: #fff;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

/* Inline edit */
.edit-inline {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  border: 1px solid #444;
  background: #333;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-left: 4px;
}
.edit-inline:hover {
  background: #555;
}

.name.edit {
  gap: 8px;
}
.edit-input {
  background: #1f1f1f;
  border: 1px solid #555;
  color: #fff;
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 1rem;
  min-width: 200px;
  outline: none;
  transition: all 0.2s ease;
}

/* Modificar input */
.edit-input:focus {
  border-color: #d5b76f;
  box-shadow: 0 0 6px 1px rgba(213, 183, 111, 0.5);
}
.edit-accept,
.edit-cancel {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  border: 1px solid #555;
  background: #333;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
}
.edit-accept:hover {
  background: #2e4a30;
  border-color: #2e4a30;
}
.edit-cancel:hover {
  background: #4a2e2e;
  border-color: #4a2e2e;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid #444;
  background: #333;
  color: #fff;
  cursor: pointer;
  transition: all 0.25s ease;
}
.back-btn:hover {
  background: #555;
}

.header-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

/* === BOTONES === */
.pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 999px;
  border: 1px solid #fff;
  background: #fff;
  color: #111;
  font-weight: 650;
  cursor: pointer;
  transition: all 0.25s ease;
  font-size: 0.95rem;
}
.pill:hover {
  background: #d5b76f;
  border-color: #d5b76f;
  color: #111;
}
.pill.subtle {
  background: transparent;
  color: #fff;
  border: 1px solid #555;
}
.pill.subtle:hover {
  background: #444;
  border-color: #777;
}

/* Delete blanco -> rojo al hover */
.pill.delete {
  background: #fff;
  color: #111;
  border-color: #fff;
}
.pill.delete:hover {
  background: #c73a3a;
  border-color: #c73a3a;
  color: #fff;
}

.icon {
  width: 16px;
  height: 16px;
}
.icon-sm {
  width: 18px;
  height: 18px;
}

.balance-row {
  margin-top: 4px;
  margin-bottom: 10px;
}
.label {
  font-size: 0.8rem;
  color: #c9c9c9;
  letter-spacing: 0.03em;
}
.balance {
  font-size: 2rem;
  font-weight: 800;
  color: #d5b76f;
}

.meta-row {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.meta-item .value {
  margin-top: 4px;
  font-weight: 600;
}
.iban-block .iban {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #ddd;
  letter-spacing: 0.04em;
  flex-wrap: wrap;
}
.copy {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid #444;
  background: #333;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.85rem;
}
.copy:hover {
  background: #555;
}

/* Transacciones */
.tx-card {
  padding: 0;
  overflow: hidden;
}
.tx-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0 16px;
  border-bottom: 1px solid #3a3a3a;
  margin-bottom: 6px;
}
.tx-title {
  font-size: 1.05rem;
  font-weight: 700;
}
.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.search {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 12px;
  background: #333;
  border: 1px solid #555;
}
.search input {
  background: transparent;
  border: none;
  outline: none;
  color: #fff;
  font-size: 0.95rem;
  width: 220px;
}

.tx-list {
  max-height: 360px;
  overflow-y: auto;
  padding: 10px 14px 14px 14px;
  scrollbar-width: thin;
}
.tx-list::-webkit-scrollbar {
  width: 8px;
}
.tx-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 999px;
}
.tx-list:hover::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
}

.tx-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 8px;
  border-bottom: 1px solid #333;
}
.tx-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.tx-title {
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
}
.tx-date {
  font-size: 0.8rem;
  color: #aaa;
}
.badge {
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  padding: 4px 8px;
  border-radius: 999px;
}
.badge.in {
  background: #284f2a;
  color: #7aff9a;
}
.badge.out {
  background: #4a2323;
  color: #ff7a7a;
}
.tx-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.amt {
  font-weight: 800;
  letter-spacing: 0.02em;
}
.amt.in {
  color: #7aff9a;
}
.amt.out {
  color: #ff7a7a;
}

/* Modal delete */
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
.modal-title {
  font-size: 1.15rem;
  font-weight: 800;
  margin: 0 0 6px 0;
}
.modal-text {
  color: #dcdcdc;
  margin: 0 0 14px 0;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.pill.danger {
  background: #c73a3a;
  border-color: #c73a3a;
  color: #fff;
}
.pill.danger:hover {
  background: #a72b2b;
  border-color: #a72b2b;
  color: #fff;
}
.pill.delete:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  background: #444 !important;
  border-color: #444 !important;
  color: #888 !important;
}

/* Header del modal con icono */
.modal-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.modal-icon {
  width: 22px;
  height: 22px;
  color: #b79b58; /* doradito */
}

/* Borde dorado solo para el modal de PIN */
.modal-card.pin-modal {
  border-color: #b79b58;
}

/* Toast gris oscuro */
.toast {
  position: fixed;
  bottom: 30px;
  left: 50%;
  transform: translateX(-50%);
  background-color: #2d2d2d;
  color: #fff;
  padding: 12px 22px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
  font-size: 0.95rem;
  z-index: 9999;
  opacity: 0.95;
  border: 1px solid #999;
}
.toast.error {
  border-color: #ff5252;
  background-color: #3a3a3a;
}
.toast.success {
  border-color: #4caf50;
  background-color: #2f2f2f;
}

/* Animación suave */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Responsive */
@media (max-width: 900px) {
  .meta-row {
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }
  .detail-header.in-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  .header-actions {
    width: 100%;
    gap: 8px;
  }
  .header-actions .pill {
    flex: 1;
    justify-content: center;
  }
}
@media (max-width: 600px) {
  .sections-container {
    padding: 28px 14px;
    gap: 28px;
  }
  .dashboard__section {
    padding: 18px;
    border-radius: 16px;
  }
  .meta-row {
    grid-template-columns: 1fr;
  }
  .tx-toolbar {
    flex-direction: column;
    gap: 10px;
  }
  .toolbar-actions {
    width: 100%;
    justify-content: space-between;
  }
  .search input {
    width: 120px;
  }
}

.pin-modal .modal-text {
  margin-top: 8px;
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
  border: 1px solid #ccc;
  border-radius: 8px;
  border-color: #d5b76f;
}
</style>
