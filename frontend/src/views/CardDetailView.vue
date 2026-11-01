<template>
  <div class="page-container">
    <HeaderLayout title="Kofre" />

    <div class="scroll-content">
      <div class="sections-container">
        <section class="dashboard__section combined-header-card">
          <header class="detail-header in-card">
            <div class="header-left">
              <button class="back-btn" @click="$router.push('/dashboard')">
                <ArrowLeft class="icon" /> Back
              </button>

              <h1 class="title">
                <CreditCard class="icon-sm" />
                <span class="bank">{{ card.bank }}</span>
                <span class="dot">·</span>

                <!-- Alias editable -->
                <span class="name" v-if="!editingName">
                  {{ card.alias }}
                  <button class="edit-inline" @click="startEditName" aria-label="Edit alias">
                    <Pencil class="icon" />
                  </button>
                </span>

                <span class="name edit" v-else>
                  <input
                    ref="nameInput"
                    v-model.trim="editName"
                    class="edit-input"
                    @keyup.enter="saveName"
                    @keyup.esc="cancelEdit"
                    maxlength="20"
                  />
                  <button class="edit-accept" @click="saveName" aria-label="Save alias">
                    <Check class="icon" />
                  </button>
                  <button class="edit-cancel" @click="cancelEdit" aria-label="Cancel">
                    <X class="icon" />
                  </button>
                </span>
              </h1>
            </div>

            <div class="header-actions">
              <button class="pill delete" @click="openDeleteConfirmModal">
                <Trash2 class="icon" /> Delete
              </button>
            </div>
          </header>

          <!-- Cards row -->
          <div class="cards-row">
            <!-- Card pública -->
            <div class="card-visual-wrapper">
              <div :class="['virtual-card', cardTypeClass]">
                <div class="card-shine"></div>

                <div class="card-top">
                  <div class="card-logo">
                    <CreditCard class="logo-icon" />
                  </div>
                  <div class="card-status">
                    <span :class="['status-badge', cardStatus.toLowerCase()]">
                      {{ cardStatus }}
                    </span>
                  </div>
                </div>

                <div class="card-chip">
                  <div class="chip-line"></div>
                  <div class="chip-line"></div>
                </div>

                <div class="card-number">
                  <span v-for="i in 4" :key="i" class="number-group">
                    {{ i < 4 ? '••••' : card.last4 }}
                  </span>
                </div>

                <div class="card-bottom">
                  <div class="card-holder">
                    <div class="label">CARD HOLDER</div>
                    <div class="value">{{ cardHolder }}</div>
                  </div>
                  <div class="card-expiry">
                    <div class="label">EXPIRES</div>
                    <div class="value">{{ expiryDate }}</div>
                  </div>
                  <div class="card-brand">
                    <div class="brand-logo">{{ card.type }}</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Card sensible -->
            <div class="card-visual-wrapper">
              <div
                :class="['virtual-card', cardTypeClass, { locked: !isUnlocked }]"
                @click="!isUnlocked && openUnlockPinModal()"
              >
                <div class="card-shine"></div>

                <div v-if="!isUnlocked" class="card-locked-overlay">
                  <Lock class="lock-icon" />
                  <p>Tap to Unlock</p>
                </div>

                <template v-else>
                  <div class="card-top">
                    <div class="card-logo"><CreditCard class="logo-icon" /></div>
                  </div>

                  <div class="card-number">
                    <span>
                      {{ card.pan.slice(-16, -12) }}
                      {{ card.pan.slice(-12, -8) }}
                      {{ card.pan.slice(-8, -4) }}
                      {{ card.pan.slice(-4) }}
                    </span>
                  </div>

                  <div class="card-bottom sensitive-info">
                    <div class="info-field">
                      <div class="label">Expires</div>
                      <div class="value">{{ expiryDate }}</div>
                    </div>
                  </div>

                  <button class="lock-btn" @click.stop="lockCard">
                    <Lock class="icon" /> Lock Card
                  </button>
                </template>
              </div>
            </div>
          </div>

          <!-- Modal PIN ver datos (UNLOCK) -->
          <div v-if="showUnlockPinModal" class="modal-overlay" @click.self="closeUnlockPinModal">
            <div
              class="modal-card pin-modal"
              :class="{ shake: unlockPinError }"
              data-testid="unlock-card-pin-modal"
            >
              <div class="modal-header">
                <Lock class="modal-icon" />
                <h3 class="modal-title">Confirm with PIN</h3>
              </div>

              <p class="modal-text">Enter your 6-digit PIN to unlock card details.</p>

              <div class="pin-input">
                <input
                  v-for="(digit, index) in unlockPin"
                  :key="index"
                  ref="unlockPinBoxes"
                  class="pin-box"
                  type="password"
                  maxlength="1"
                  inputmode="numeric"
                  pattern="[0-9]*"
                  v-model="unlockPin[index]"
                  @input="handleUnlockPinInput(index, $event)"
                  @keyup.backspace="handleUnlockBackspace(index, $event)"
                />
              </div>

              <p v-if="unlockPinErrorMessage" class="modal-error">
                {{ unlockPinErrorMessage }}
              </p>

              <div class="modal-actions">
                <button class="pill subtle" @click="closeUnlockPinModal">Cancel</button>
                <button class="pill" @click="verifyUnlockPin">Unlock</button>
              </div>
            </div>
          </div>

          <!-- Stats -->
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-label">Available Balance</div>
              <div class="stat-value primary">{{ availableBalance }}</div>
              
            </div>

            <div class="stat-item">
              <div class="stat-label">Security</div>
              <div class="stat-value small">
                <Shield class="icon" style="margin-right: 6px" />
                Active
              </div>
              <div class="stat-subtext">All protections enabled</div>
            </div>
          </div>

          <!-- Quick actions -->
          <div class="quick-actions-section">
            <div class="quick-actions-row">
              <button class="action-btn" @click="freezeCard">
                <Shield class="icon" />
                <span>Freeze</span>
              </button>
              <button class="action-btn" @click="reportIssue">
                <AlertTriangle class="icon" />
                <span>Report</span>
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>

    <!-- Modal 1: confirmar delete (sin PIN) -->
    <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3 class="modal-title">Delete card</h3>
        </div>

        <p class="modal-text">
          You are about to delete
          <strong>{{ card.bank }} · {{ card.alias }}</strong
          >. This action cannot be undone.
        </p>

        <div class="modal-actions">
          <button class="pill subtle" @click="showDeleteConfirm = false">Cancel</button>
          <button class="pill danger" @click="openDeletePinModal">
            <Trash2 class="icon" /> Delete permanently
          </button>
        </div>
      </div>
    </div>

    <!-- Modal 2: PIN para borrar -->
    <div v-if="showDeletePinModal" class="modal-overlay" @click.self="closeDeletePinModal">
      <div
        class="modal-card pin-modal"
        :class="{ shake: deletePinError }"
        data-testid="delete-card-pin-modal"
      >
        <div class="modal-header">
          <Lock class="modal-icon" />
          <h3 class="modal-title">Confirm with PIN</h3>
        </div>

        <p class="modal-text">Please enter your 6-digit PIN to delete this card.</p>

        <div class="pin-input">
          <input
            v-for="(digit, i) in deletePin"
            :key="i"
            ref="deletePinBoxes"
            class="pin-box"
            type="password"
            maxlength="1"
            inputmode="numeric"
            pattern="[0-9]*"
            v-model="deletePin[i]"
            @input="handleDeletePinInput(i, $event)"
            @keyup.backspace="handleDeleteBackspace(i, $event)"
          />
        </div>

        <p v-if="deleteErrorMessage" class="modal-error">{{ deleteErrorMessage }}</p>

        <div class="modal-actions">
          <button class="pill subtle" @click="closeDeletePinModal" :disabled="isDeleting">
            Cancel
          </button>
          <button class="pill danger" @click="confirmDelete" :disabled="isDeleting">
            <Trash2 class="icon" />
            {{ isDeleting ? 'Deleting...' : 'Delete permanently' }}
          </button>
        </div>
      </div>
    </div>

    <!-- TOAST -->
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
  CreditCard,
  Trash2,
  Pencil,
  Check,
  X,
  Lock,
  Shield,
  AlertTriangle,
} from 'lucide-vue-next'
import { ref, computed, nextTick, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import HeaderLayout from '@/components/layout/HeaderLayout.vue'

import { getCardByPan, getAccount, deleteCard, verifyCard, updateCard } from '@/api/userService'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// --- PAN como identificador de tarjeta (cardId) ---
const cardPan = String(route.params.id || '')

// --- Loading / error ---
const loading = ref(true)
const error = ref(null)

// --- Datos básicos de tarjeta ---
const card = ref({
  pan: cardPan,
  type: '',
  last4: cardPan.slice(-4),
  bank: '',
  alias: '',
})

// --- Datos derivados ---
const cardHolder = computed(() => userStore.name || '')
const expiryDate = ref('')
const cardStatus = ref('')
const availableBalance = ref('')

// --- Cuenta asociada ---
const account = ref({
  id: '',
  bank: '',
  name: '',
  iban: '—',
  balance: 0,
})

const normalizeAccountReference = (value) =>
  String(value ?? '')
    .replace(/\s+/g, '')
    .toUpperCase()

// ===============================================================
// --- CARGA INICIAL
// ===============================================================
onMounted(async () => {
  try {
    loading.value = true
    error.value = null

    if (!userStore.isAuthenticated || !userStore.dni) {
      router.push('/login')
      return
    }

    const cardData = await getCardByPan(userStore.dni, cardPan)
    if (!cardData) throw new Error('Card not found')

    card.value.bank = cardData.bank || ''
    card.value.type = cardData.type || ''
    cardStatus.value = cardData.status || ''
    card.value.alias = cardData.alias || 'My Card'
    card.value.last4 = String(cardData.pan || cardPan).slice(-4)
    expiryDate.value = parseExpireDate(cardData.expiryDate)

    const accountRef = normalizeAccountReference(cardData.iban)
    if (!accountRef) throw new Error('Missing account reference for card')

    const acc = await getAccount(userStore.dni, accountRef)
    if (!acc) throw new Error('Account not found')

    account.value = {
      id: acc.id ?? accountRef,
      bank: acc.bank ?? acc.entity ?? '—',
      name: acc.name ?? acc.alias ?? acc.bank ?? '—',
      iban: String(acc.iban ?? acc.number ?? acc.id ?? '')
        .replace(/\s+/g, '')
        .replace(/(.{4})/g, '$1 ')
        .trim(),
      balance: Number(acc.balance ?? 0),
    }

    availableBalance.value = formatEUR(account.value.balance || 0)
  } catch (err) {
    console.error('[CardDetail] Failed to load card:', err)
    error.value = 'Failed to load card data'
  } finally {
    loading.value = false
  }
})

// Toast
const toast = ref({ visible: false, message: '', type: 'info' })
function showToast(message, type = 'info') {
  toast.value = { visible: true, message, type }
  setTimeout(() => (toast.value.visible = false), 2500)
}

// --- Alias editable ---
const editingName = ref(false)
const editName = ref('')
const nameInput = ref(null)
const savingName = ref(false)

function startEditName() {
  editingName.value = true
  editName.value = card.value.alias
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
    await updateCard(userStore.dni, account.value.id, cardPan, { alias: n })
    card.value.alias = n
    editingName.value = false
    showToast('Alias actualizado', 'success')
  } catch (e) {
    console.error('[saveName] Failed to update card alias:', e)
    showToast('No se pudo actualizar el alias de la tarjeta', 'error')
  } finally {
    savingName.value = false
  }
}

function cancelEdit() {
  editingName.value = false
}

// ===============================================================
// --- DELETE CARD: 2 MODALES (confirm + PIN) ---
// ===============================================================
const showDeleteConfirm = ref(false)
const showDeletePinModal = ref(false)
const isDeleting = ref(false)

const deletePin = ref(['', '', '', '', '', ''])
const deletePinBoxes = ref([])
const deletePinError = ref(false)
const deleteErrorMessage = ref('')

function resetDeletePin() {
  deletePin.value = ['', '', '', '', '', '']
  deletePinError.value = false
  deleteErrorMessage.value = ''
}

function openDeleteConfirmModal() {
  resetDeletePin()
  showDeleteConfirm.value = true
}

function openDeletePinModal() {
  showDeleteConfirm.value = false
  resetDeletePin()
  showDeletePinModal.value = true
  nextTick(() => deletePinBoxes.value[0]?.focus())
}

function closeDeletePinModal() {
  showDeletePinModal.value = false
  resetDeletePin()
}

function handleDeletePinInput(index, event) {
  const value = event.target.value.replace(/[^0-9]/g, '')
  deletePin.value[index] = value.slice(-1)

  if (deletePin.value[index] && index < 5) {
    deletePinBoxes.value[index + 1]?.focus()
  }
}

function handleDeleteBackspace(index, event) {
  if (event.key === 'Backspace' && !deletePin.value[index] && index > 0) {
    deletePinBoxes.value[index - 1]?.focus()
  }
}

async function confirmDelete() {
  if (isDeleting.value) return

  const pin = deletePin.value.join('')

  if (pin.length !== 6) {
    deletePinError.value = true
    deleteErrorMessage.value = 'Please enter your 6-digit PIN.'
    setTimeout(() => (deletePinError.value = false), 600)
    return
  }

  try {
    isDeleting.value = true
    deleteErrorMessage.value = ''

    await deleteCard(userStore.dni, account.value.id, cardPan, pin)

    showDeletePinModal.value = false
    showToast('Card deleted', 'success')
    router.push('/dashboard')
  } catch (e) {
    console.error('[confirmDelete] Failed to delete card:', e)

    const status = e?.response?.status
    const code = e?.response?.data?.code

    if (code === 'CARD_NOT_FOUND') {
      deleteErrorMessage.value = 'Card not found (CARD_NOT_FOUND).'
    } else if (status === 422 && code === 'INVALID_PIN') {
      deleteErrorMessage.value = 'Incorrect PIN. Unable to delete the card.'
    } else {
      deleteErrorMessage.value = 'Unexpected error. Could not delete the card.'
    }

    deletePinError.value = true
    setTimeout(() => (deletePinError.value = false), 600)
  } finally {
    isDeleting.value = false
  }
}

// ===============================================================
// --- PIN UNLOCK MODAL (para ver datos sensibles) ---
// ===============================================================
const showUnlockPinModal = ref(false)
const unlockPin = ref(['', '', '', '', '', ''])
const unlockPinBoxes = ref([])
const isUnlocked = ref(false)
const unlockPinError = ref(false)
const unlockPinErrorMessage = ref('')

function openUnlockPinModal() {
  unlockPin.value = ['', '', '', '', '', '']
  unlockPinError.value = false
  unlockPinErrorMessage.value = ''
  showUnlockPinModal.value = true
  nextTick(() => unlockPinBoxes.value[0]?.focus())
}

function closeUnlockPinModal() {
  showUnlockPinModal.value = false
  unlockPin.value = ['', '', '', '', '', '']
  unlockPinError.value = false
  unlockPinErrorMessage.value = ''
}

function handleUnlockPinInput(index, event) {
  const value = event.target.value.replace(/[^0-9]/g, '')
  unlockPin.value[index] = value.slice(-1)

  if (unlockPin.value[index] && index < 5) {
    unlockPinBoxes.value[index + 1]?.focus()
  }
}

function handleUnlockBackspace(index, event) {
  if (event.key === 'Backspace' && !unlockPin.value[index] && index > 0) {
    unlockPinBoxes.value[index - 1]?.focus()
  }
}

function parseExpireDate(raw) {
  if (!raw) return 'MM/YY'

  try {
    const v = String(raw).trim()

    if (/^\d{2}\/\d{2}$/.test(v)) return v

    const date = new Date(v)
    if (isNaN(date.getTime())) return v

    const month = String(date.getMonth() + 1).padStart(2, '0')
    const year = String(date.getFullYear()).slice(-2)

    return `${month}/${year}`
  } catch (e) {
    console.error('Date parsing failed:', e)
    return 'MM/YY'
  }
}

async function verifyUnlockPin() {
  const pin = unlockPin.value.join('')
  if (pin.length !== 6) {
    unlockPinError.value = true
    unlockPinErrorMessage.value = 'Please enter your 6-digit PIN.'
    setTimeout(() => (unlockPinError.value = false), 600)
    return
  }

  try {
    const data = await verifyCard(userStore.dni, account.value.id, cardPan, pin)

    card.value.pan = data.pan
    card.value.last4 = data.pan.slice(-4)
    card.value.type = data.type || card.value.type
    card.value.bank = data.bank || card.value.bank

    if (data.expireDate) {
      expiryDate.value = parseExpireDate(data.expireDate)
    }

    isUnlocked.value = true
    closeUnlockPinModal()
  } catch (err) {
    console.error('Failed to verify card:', err)
    unlockPinError.value = true
    unlockPinErrorMessage.value = 'Incorrect PIN. Unable to unlock the card.'
    setTimeout(() => (unlockPinError.value = false), 600)
  }
}

function lockCard() {
  isUnlocked.value = false
}

// ===============================================================
// --- Utils & extra acciones ---
// ===============================================================
function formatEUR(num) {
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
  }).format(num)
}

async function freezeCard() {
  if (cardStatus.value === 'DEAD') {
    showToast('Card is reported and cannot be changed', 'error')
    return
  }
  try {
    const nextStatus = cardStatus.value === 'ACTIVE' ? 'FREEZED' : 'ACTIVE'
    await updateCard(userStore.dni, account.value.id, cardPan, { status: nextStatus })
    cardStatus.value = nextStatus
    showToast(nextStatus === 'FREEZED' ? 'Card frozen' : 'Card activated', 'success')
  } catch (e) {
    console.error('[freezeCard] Failed:', e)
    showToast('Could not update card status', 'error')
  }
}

async function reportIssue() {
  if (cardStatus.value === 'DEAD') {
    showToast('Card is already reported', 'error')
    return
  }
  try {
    await updateCard(userStore.dni, account.value.id, cardPan, { status: 'DEAD' })
    cardStatus.value = 'DEAD'
    showToast('Card reported', 'success')
  } catch (e) {
    console.error('[reportIssue] Failed:', e)
    showToast('Unable to report card', 'error')
  }
}

const cardTypeClass = computed(() => {
  const t = (card.value.type || '').toUpperCase()
  return t === 'DEBIT' ? 'debit' : t === 'CREDIT' ? 'credit' : ''
})
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

/* Header dentro del card */
.detail-header.in-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 14px;
  margin-bottom: 20px;
  border-bottom: 1px solid #3a3a3a;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.virtual-card.debit {
  background: linear-gradient(135deg, #007bff 0%, #3399ff 100%);
}

.virtual-card.credit {
  background: linear-gradient(135deg, #ff4b4b 0%, #ff1a1a 100%);
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

.icon {
  width: 16px;
  height: 16px;
}

.icon-sm {
  width: 18px;
  height: 18px;
}

/* CARD VISUAL */
.cards-row {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 40px;
  margin: 24px 0 32px;
}

.card-visual-wrapper {
  margin: 0;
  flex: 1;
  min-width: 300px;
  max-width: 450px;
  display: flex;
  justify-content: center;
}

.virtual-card {
  position: relative;
  width: 100%;
  max-width: 450px;
  height: 280px;
  background: linear-gradient(135deg, #2d3436 0%, #1a1a1a 100%);
  border-radius: 20px;
  padding: 28px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: transform 0.4s ease;
}

.virtual-card:hover {
  transform: translateY(-6px) scale(1.02);
}

.virtual-card.visa {
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
}

.virtual-card.mastercard {
  background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
}

.card-shine {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(
    45deg,
    transparent 30%,
    rgba(255, 255, 255, 0.08) 50%,
    transparent 70%
  );
  transform: rotate(45deg);
  animation: shine 4s infinite;
}

@keyframes shine {
  0% {
    transform: translateX(-100%) translateY(-100%) rotate(45deg);
  }
  100% {
    transform: translateX(100%) translateY(100%) rotate(45deg);
  }
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.card-logo {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  padding: 8px;
  backdrop-filter: blur(10px);
}

.logo-icon {
  width: 28px;
  height: 28px;
  color: #f0d785;
}

.status-badge {
  background: rgba(76, 175, 80, 0.25);
  border: 1px solid rgba(76, 175, 80, 0.5);
  color: #81c784;
  padding: 5px 12px;
  border-radius: 16px;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
}

.status-badge.locked {
  background: rgba(244, 67, 54, 0.25);
  border-color: rgba(244, 67, 54, 0.5);
  color: #e57373;
}

.status-badge.frozen {
  background: rgba(7, 168, 255, 0.25);
  border-color: rgba(7, 172, 255, 0.5);
  color: #4fc7ff;
}

.status-badge.reported {
  background: rgba(255, 251, 7, 0.25);
  border-color: rgba(255, 230, 7, 0.5);
  color: #ffed4f;
}

.card-chip {
  width: 54px;
  height: 40px;
  background: linear-gradient(135deg, #f0d785 0%, #d5b76f 100%);
  border-radius: 7px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 7px;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.4);
}

.chip-line {
  height: 2.5px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 2px;
}

.card-number {
  display: flex;
  gap: 14px;
  font-size: 1.4rem;
  font-weight: 600;
  letter-spacing: 2px;
  color: #ffffff;
  text-shadow: 0 2px 6px rgba(0, 0, 0, 0.4);
}

.number-group {
  display: block;
}

.card-bottom {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}

.card-holder,
.card-expiry {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.card-bottom .label {
  font-size: 0.6rem;
  color: rgba(255, 255, 255, 0.65);
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 600;
}

.card-bottom .value {
  font-size: 0.9rem;
  font-weight: 600;
  color: #ffffff;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
}

.brand-logo {
  font-size: 1.4rem;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.95);
  font-style: italic;
  text-shadow: 0 2px 6px rgba(0, 0, 0, 0.5);
}

/* STATS GRID */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-item {
  background: #333;
  border: 1px solid #3a3a3a;
  border-radius: 14px;
  padding: 18px;
  transition: all 0.3s ease;
}

.stat-item:hover {
  background: #383838;
  border-color: #444;
  transform: translateY(-2px);
}

.stat-label {
  font-size: 0.8rem;
  color: #c9c9c9;
  letter-spacing: 0.03em;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #f5f5f5;
  display: flex;
  align-items: center;
  gap: 8px;
}

.stat-value.primary {
  color: #d5b76f;
  font-size: 1.8rem;
}

.stat-value.small {
  font-size: 1.1rem;
}

.stat-trend {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  color: #81c784;
  margin-top: 8px;
}

.trend-icon {
  width: 14px;
  height: 14px;
}

.stat-subtext {
  font-size: 0.85rem;
  color: #aaa;
  margin-top: 4px;
}

/* QUICK ACTIONS ROW */
.quick-actions-section {
  margin-top: 40px;
}

.quick-actions-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  padding-top: 20px;
  border-top: 1px solid #3a3a3a;
}

.action-btn {
  flex: 1;
  min-width: 110px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 12px;
  background: #333;
  border: 1px solid #3a3a3a;
  border-radius: 14px;
  color: #fff;
  cursor: pointer;
  transition: all 0.25s ease;
  font-size: 0.9rem;
  font-weight: 500;
}

.action-btn:hover {
  background: #3d3d3d;
  border-color: #555;
  transform: translateY(-2px);
}

.action-btn .icon {
  width: 22px;
  height: 22px;
  color: #d5b76f;
}

/* Modal, PIN & lockable card */
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

.modal-card.pin-modal {
  border-color: #b79b58;
}

.modal-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.modal-icon {
  width: 22px;
  height: 22px;
  color: #b79b58;
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

/* PIN inputs unificados */
.pin-modal {
  text-align: center;
  animation: fadeIn 0.3s ease;
}

.pin-modal.shake {
  animation: shake 0.4s ease;
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
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.pin-box:focus {
  border-color: #f1d48a;
  box-shadow: 0 0 4px rgba(213, 183, 111, 0.8);
}

.modal-error {
  margin-top: 8px;
  font-size: 0.85rem;
  color: #ff7a7a;
}

@keyframes shake {
  0%,
  100% {
    transform: translateX(0);
  }
  20%,
  60% {
    transform: translateX(-6px);
  }
  40%,
  80% {
    transform: translateX(6px);
  }
}

.virtual-card.locked {
  border: 2px dashed rgba(255, 255, 255, 0.3);
  filter: brightness(0.7);
  cursor: pointer;
  position: relative;
}

.card-locked-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #f0d785;
  font-weight: 600;
  font-size: 1rem;
  backdrop-filter: blur(3px);
}

.card-locked-overlay .lock-icon {
  width: 36px;
  height: 36px;
  margin-bottom: 10px;
}

.lock-btn {
  margin-top: 16px;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid #444;
  background: #333;
  color: #fff;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
}

.lock-btn:hover {
  background: #444;
}

/* Toast */
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

  .stats-grid {
    grid-template-columns: 1fr 1fr;
  }

  .quick-actions-row {
    gap: 8px;
  }

  .action-btn {
    min-width: 90px;
    padding: 14px 10px;
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

  .virtual-card {
    max-width: 100%;
    height: 230px;
    padding: 22px;
  }

  .card-number {
    font-size: 1.1rem;
    gap: 10px;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .quick-actions-row {
    gap: 8px;
  }

  .action-btn {
    min-width: 80px;
    font-size: 0.85rem;
  }
}

.status-badge.freezed,
.status-badge.frozen {
  background: rgba(0, 1, 3, 0.25); /* dark blue */
  border-color: rgba(0, 51, 153, 0.5);
  color: #92b6ff;

}

.status-badge.dead,
.status-badge.reported {
  background: rgba(255, 215, 0, 0.28); /* yellow */
  border-color: rgba(255, 217, 0, 0.5);
  color: #fff5cb;
}

</style>
