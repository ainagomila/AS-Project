<template>
  <div class="page-container">
    <header class="fixed-header">
      <HeaderLayout title="Kofre" />
    </header>

    <main class="scroll-content">
      <div class="admin-heading">
        <h2 class="admin-title">Administration console</h2>
        <span class="role-badge" :class="isAdmin ? 'role-admin' : 'role-auditor'">
          {{ isAdmin ? 'Administrator' : 'Auditor (read-only)' }}
        </span>
      </div>

      <p v-if="error" class="admin-error" data-testid="admin-error">{{ error }}</p>

      <nav class="tabs" data-testid="admin-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="tab"
          :class="{ active: activeTab === tab.id }"
          @click="switchTab(tab.id)"
        >
          {{ tab.label }}
        </button>
      </nav>

      <!-- ======================= OVERVIEW ======================= -->
      <section v-if="activeTab === 'overview'" class="admin-section">
        <div v-if="stats" class="stats-grid">
          <div v-for="card in statCards" :key="card.label" class="stat-card">
            <span class="stat-value">{{ card.value }}</span>
            <span class="stat-label">{{ card.label }}</span>
          </div>
        </div>
      </section>

      <!-- ======================= USERS ======================= -->
      <section v-if="activeTab === 'users'" class="admin-section">
        <form v-if="isAdmin" class="create-form" @submit.prevent="submitNewUser">
          <h3 class="section-subtitle">Create user</h3>
          <div class="form-grid">
            <input v-model="newUser.name" placeholder="Name" required />
            <input v-model="newUser.dni" placeholder="DNI (e.g. 12345678Z)" required />
            <input v-model="newUser.email" placeholder="Email" type="email" required />
            <input v-model="newUser.phone" placeholder="Phone (+34600000000)" required />
            <input v-model="newUser.password" placeholder="Password" type="password" required />
            <input v-model="newUser.birthdate" placeholder="Birthdate (yyyy-mm-dd)" required />
            <input v-model="newUser.pin" placeholder="PIN (6 digits)" required />
            <select v-model="newUser.gender" required>
              <option value="MALE">Male</option>
              <option value="FEMALE">Female</option>
              <option value="OTHER">Other</option>
            </select>
            <select v-model="newUser.role">
              <option value="USER">USER</option>
              <option value="AUDITOR">AUDITOR</option>
              <option value="ADMIN">ADMIN</option>
            </select>
            <label class="checkbox-label">
              <input v-model="newUser.active" type="checkbox" /> Active
            </label>
          </div>
          <button class="admin-btn primary" type="submit">Create</button>
          <span v-if="formMessage" class="form-message">{{ formMessage }}</span>
        </form>

        <table class="admin-table" data-testid="admin-users">
          <thead>
            <tr>
              <th>DNI</th>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Accounts</th>
              <th>Cards</th>
              <th v-if="isAdmin"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.dni">
              <td>{{ user.dni }}</td>
              <td>{{ user.name }}</td>
              <td>{{ user.email }}</td>
              <td>
                <select
                  v-if="isAdmin && user.dni !== userStore.dni"
                  :value="user.role"
                  @change="changeRole(user, $event.target.value)"
                >
                  <option value="USER">USER</option>
                  <option value="AUDITOR">AUDITOR</option>
                  <option value="ADMIN">ADMIN</option>
                </select>
                <span v-else>{{ user.role }}</span>
              </td>
              <td>
                <span v-if="user.locked" class="badge badge-locked">Locked</span>
                <span v-else-if="user.active" class="badge badge-active">Active</span>
                <span v-else class="badge badge-disabled">Disabled</span>
              </td>
              <td>{{ user.accountCount }}</td>
              <td>{{ user.cardCount }}</td>
              <td v-if="isAdmin" class="actions-cell">
                <button
                  class="admin-btn"
                  :disabled="user.dni === userStore.dni"
                  @click="toggleActive(user)"
                >
                  {{ user.active ? 'Disable' : 'Enable' }}
                </button>
                <button
                  class="admin-btn"
                  :disabled="user.dni === userStore.dni"
                  @click="askResetPassword(user)"
                >
                  Reset password
                </button>
                <button
                  class="admin-btn danger"
                  :disabled="user.dni === userStore.dni"
                  @click="removeUser(user)"
                >
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- ======================= ACCOUNTS ======================= -->
      <section v-if="activeTab === 'accounts'" class="admin-section">
        <table class="admin-table" data-testid="admin-accounts">
          <thead>
            <tr>
              <th>IBAN</th>
              <th>Name</th>
              <th>Bank</th>
              <th>Balance</th>
              <th>Status</th>
              <th>Owner</th>
              <th v-if="isAdmin"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="account in accounts" :key="account.iban">
              <td>{{ account.iban }}</td>
              <td>{{ account.name }}</td>
              <td>{{ account.bank }}</td>
              <td>{{ formatAmount(account.balance, account.currency) }}</td>
              <td>
                <span :class="account.status === 'ACTIVE' ? 'badge badge-active' : 'badge badge-locked'">
                  {{ account.status }}
                </span>
              </td>
              <td>{{ account.owner?.name }} ({{ account.owner?.dni }})</td>
              <td v-if="isAdmin">
                <button class="admin-btn" @click="toggleAccountStatus(account)">
                  {{ account.status === 'ACTIVE' ? 'Freeze' : 'Unfreeze' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- ======================= CARDS ======================= -->
      <section v-if="activeTab === 'cards'" class="admin-section">
        <table class="admin-table" data-testid="admin-cards">
          <thead>
            <tr>
              <th>PAN</th>
              <th>IBAN</th>
              <th>Alias</th>
              <th>Bank</th>
              <th>Type</th>
              <th>Status</th>
              <th>Expiry</th>
              <th>Owner</th>
              <th v-if="isAdmin"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="card in cards" :key="card.pan">
              <td>{{ card.pan }}</td>
              <td>{{ card.iban }}</td>
              <td>{{ card.alias }}</td>
              <td>{{ card.bank }}</td>
              <td>{{ card.type }}</td>
              <td>{{ card.status }}</td>
              <td>{{ card.expiryDate }}</td>
              <td>{{ card.owner?.name }} ({{ card.owner?.dni }})</td>
              <td v-if="isAdmin" class="actions-cell">
                <button class="admin-btn" @click="blockCard(card)">Block</button>
                <button class="admin-btn danger" @click="removeCard(card)">Delete</button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- ======================= TRANSFERS ======================= -->
      <section v-if="activeTab === 'transfers'" class="admin-section">
        <table class="admin-table" data-testid="admin-transfers">
          <thead>
            <tr>
              <th>Date</th>
              <th>Emitter</th>
              <th>Receiver</th>
              <th>Concept</th>
              <th>Amount</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="transfer in transfers" :key="transfer.id">
              <td>{{ formatDate(transfer.date) }}</td>
              <td>{{ transfer.emitter }}</td>
              <td>{{ transfer.receiver }}</td>
              <td>{{ transfer.concept }}</td>
              <td>{{ formatAmount(transfer.amount, transfer.currency) }}</td>
              <td>{{ transfer.status }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- ======================= AUDIT ======================= -->
      <section v-if="activeTab === 'audit'" class="admin-section">
        <table class="admin-table" data-testid="admin-audit">
          <thead>
            <tr>
              <th>When</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Target</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="entry in auditLogs" :key="entry.id">
              <td>{{ formatDate(entry.createdAt) }}</td>
              <td>{{ entry.actorDni }}</td>
              <td>{{ entry.action }}</td>
              <td>{{ entry.targetType }} {{ entry.targetId }}</td>
              <td class="detail-cell">{{ JSON.stringify(entry.detail) }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- ======================= SETTINGS ======================= -->
      <section v-if="activeTab === 'settings'" class="admin-section">
        <div v-for="setting in settings" :key="setting.key" class="setting-row">
          <div class="setting-info">
            <span class="setting-key">{{ setting.key }}</span>
            <span class="setting-desc">{{ setting.description }}</span>
          </div>
          <div class="setting-control">
            <template v-if="isBoolSetting(setting.key)">
              <input
                type="checkbox"
                :checked="setting.value === true"
                :disabled="!isAdmin"
                @change="toggleSetting(setting, $event.target.checked)"
              />
            </template>
            <template v-else>
              <input
                v-model="settingsInputs[setting.key]"
                :disabled="!isAdmin"
                class="setting-input"
              />
              <button
                v-if="isAdmin"
                class="admin-btn"
                @click="saveSetting(setting)"
              >
                Save
              </button>
            </template>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import HeaderLayout from '@/components/layout/HeaderLayout.vue'
import { useUserStore } from '@/stores/user'
import {
  getAllUsers,
  createUser,
  setUserActive,
  setUserRole,
  deleteUser,
  resetUserPassword,
  getAllAccounts,
  setAccountStatus,
  getAllCards,
  setCardStatus,
  deleteCard,
  getAllTransfers,
  getAuditLogs,
  getSettings,
  updateSetting,
  getStats,
} from '@/api/adminService.js'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)

const tabs = [
  { id: 'overview', label: 'Overview' },
  { id: 'users', label: 'Users' },
  { id: 'accounts', label: 'Accounts' },
  { id: 'cards', label: 'Cards' },
  { id: 'transfers', label: 'Transfers' },
  { id: 'audit', label: 'Audit log' },
  { id: 'settings', label: 'Settings' },
]

const activeTab = ref('overview')
const stats = ref(null)
const users = ref([])
const accounts = ref([])
const cards = ref([])
const transfers = ref([])
const auditLogs = ref([])
const settings = ref([])
const settingsInputs = reactive({})
const error = ref('')
const formMessage = ref('')

const newUser = reactive({
  name: '',
  dni: '',
  email: '',
  phone: '',
  password: '',
  birthdate: '',
  gender: 'MALE',
  pin: '',
  role: 'USER',
  active: true,
})

const statCards = computed(() => {
  if (!stats.value) return []
  return [
    { label: 'Users', value: stats.value.users },
    { label: 'Active users', value: stats.value.activeUsers },
    { label: 'Admins', value: stats.value.admins },
    { label: 'Auditors', value: stats.value.auditors },
    { label: 'Accounts', value: stats.value.accounts },
    { label: 'Cards', value: stats.value.cards },
    { label: 'Transfers', value: stats.value.transfers },
    { label: 'Total balance', value: formatAmount(stats.value.totalBalance, 'EUR') },
  ]
})

function describe(e) {
  return e.response?.data?.message || e.message || 'Unexpected error'
}

function formatAmount(amount, currency) {
  return `${Number(amount ?? 0).toFixed(2)} ${currency || 'EUR'}`
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : ''
}

function isBoolSetting(key) {
  return key === 'REGISTRATION_ENABLED' || key === 'MAINTENANCE_MODE'
}

async function run(fn) {
  error.value = ''
  try {
    await fn()
  } catch (e) {
    console.error(e)
    error.value = describe(e)
  }
}

async function switchTab(tab) {
  activeTab.value = tab
  if (tab === 'overview') await run(loadStats)
  if (tab === 'users') await run(loadUsers)
  if (tab === 'accounts') await run(loadAccounts)
  if (tab === 'cards') await run(loadCards)
  if (tab === 'transfers') await run(loadTransfers)
  if (tab === 'audit') await run(loadAudit)
  if (tab === 'settings') await run(loadSettings)
}

async function loadStats() {
  stats.value = await getStats()
}

async function loadUsers() {
  users.value = await getAllUsers()
}

async function loadAccounts() {
  accounts.value = await getAllAccounts()
}

async function loadCards() {
  cards.value = await getAllCards()
}

async function loadTransfers() {
  transfers.value = await getAllTransfers()
}

async function loadAudit() {
  auditLogs.value = await getAuditLogs()
}

async function loadSettings() {
  settings.value = await getSettings()
  for (const s of settings.value) {
    settingsInputs[s.key] = s.value === null ? '' : String(s.value)
  }
}

async function submitNewUser() {
  formMessage.value = ''
  error.value = ''
  try {
    await createUser({ ...newUser })
    formMessage.value = 'User created'
    for (const key of Object.keys(newUser)) {
      if (key === 'active') newUser[key] = true
      else if (key === 'gender') newUser[key] = 'MALE'
      else if (key === 'role') newUser[key] = 'USER'
      else newUser[key] = ''
    }
    await loadUsers()
  } catch (e) {
    console.error(e)
    formMessage.value = describe(e)
  }
}

async function toggleActive(user) {
  await run(async () => {
    const updated = await setUserActive(user.dni, !user.active)
    user.active = updated.active
  })
}

async function changeRole(user, role) {
  await run(async () => {
    const updated = await setUserRole(user.dni, role)
    user.role = updated.role
    user.admin = updated.admin
  })
}

function askResetPassword(user) {
  const newPassword = window.prompt(`New password for ${user.dni}:`)
  if (!newPassword) return
  run(async () => {
    await resetUserPassword(user.dni, newPassword)
  })
}

function removeUser(user) {
  if (!window.confirm(`Delete user ${user.dni}? This removes accounts, cards and transfers.`)) return
  run(async () => {
    await deleteUser(user.dni)
    await loadUsers()
  })
}

async function toggleAccountStatus(account) {
  await run(async () => {
    const updated = await setAccountStatus(account.iban, account.status === 'ACTIVE' ? 'FROZEN' : 'ACTIVE')
    account.status = updated.status
  })
}

async function blockCard(card) {
  await run(async () => {
    const updated = await setCardStatus(card.pan, 'DEAD')
    card.status = updated.status
  })
}

function removeCard(card) {
  if (!window.confirm(`Delete card ${card.pan}?`)) return
  run(async () => {
    await deleteCard(card.pan)
    await loadCards()
  })
}

function toggleSetting(setting, checked) {
  run(async () => {
    const updated = await updateSetting(setting.key, checked)
    setting.value = updated.value
  })
}

async function saveSetting(setting) {
  await run(async () => {
    const raw = (settingsInputs[setting.key] ?? '').trim()
    let value
    if (setting.key === 'TRANSFER_MAX_AMOUNT') {
      value = raw === '' ? null : Number(raw)
    } else {
      value = Number(raw)
    }
    const updated = await updateSetting(setting.key, value)
    setting.value = updated.value
    settingsInputs[setting.key] = updated.value === null ? '' : String(updated.value)
  })
}

onMounted(() => switchTab('overview'))
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  font-family: 'Satoshi', sans-serif;
  background-color: #222;
  color: #fff;
}

.scroll-content {
  flex: 1;
  padding: 24px 32px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.admin-heading {
  display: flex;
  align-items: center;
  gap: 16px;
  max-width: 1000px;
  width: 100%;
  margin: 0 auto;
}

.admin-title {
  margin: 0;
  font-size: 1.4rem;
  font-weight: 700;
  color: #f0d785;
}

.role-badge {
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
}
.role-admin {
  background: rgba(240, 215, 133, 0.15);
  color: #f0d785;
  border: 1px solid #d5b76f;
}
.role-auditor {
  background: rgba(120, 180, 255, 0.12);
  color: #9fc3ff;
  border: 1px solid #7aa4e8;
}

.tabs {
  display: flex;
  gap: 8px;
  max-width: 1000px;
  width: 100%;
  margin: 0 auto;
  flex-wrap: wrap;
}

.tab {
  padding: 8px 16px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: transparent;
  color: #ddd;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}
.tab:hover {
  border-color: rgba(255, 255, 255, 0.3);
}
.tab.active {
  background: linear-gradient(90deg, #d5b76f, #f0d785, #d5b76f);
  color: #000;
  border-color: transparent;
}

.admin-section {
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px 24px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-sizing: border-box;
  overflow-x: auto;
}

.section-subtitle {
  margin: 0 0 12px;
  font-size: 1rem;
  font-weight: 700;
  color: #f0d785;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 14px;
}

.stat-card {
  padding: 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #f0d785;
}
.stat-label {
  font-size: 0.8rem;
  opacity: 0.7;
}

.create-form {
  margin-bottom: 20px;
  padding: 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 10px;
}

.form-grid input,
.form-grid select,
.setting-input {
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(0, 0, 0, 0.25);
  color: #fff;
  font-size: 0.85rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
}

.form-message {
  font-size: 0.85rem;
  color: #9fc3ff;
}

.admin-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.admin-table th,
.admin-table td {
  padding: 8px 10px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  vertical-align: middle;
}

.admin-table tbody tr:hover {
  background: rgba(255, 255, 255, 0.06);
}

.admin-table select {
  padding: 4px 6px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(0, 0, 0, 0.3);
  color: #fff;
  font-size: 0.8rem;
}

.badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
}
.badge-active {
  background: rgba(120, 220, 140, 0.15);
  color: #8ee6a0;
}
.badge-disabled {
  background: rgba(255, 255, 255, 0.1);
  color: #bbb;
}
.badge-locked {
  background: rgba(255, 140, 120, 0.15);
  color: #ff9a8a;
}

.actions-cell {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.admin-btn {
  padding: 4px 12px;
  border-radius: 12px;
  border: 1px solid #d5b76f;
  background: transparent;
  color: #f0d785;
  cursor: pointer;
  font-size: 0.8rem;
}
.admin-btn:hover {
  background: rgba(240, 215, 133, 0.12);
}
.admin-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.admin-btn.primary {
  background: linear-gradient(90deg, #d5b76f, #f0d785, #d5b76f);
  color: #000;
  border: none;
  font-weight: 700;
}
.admin-btn.danger {
  border-color: #ff8a80;
  color: #ff8a80;
}

.admin-error {
  color: #ff8a80;
  margin: 0;
  max-width: 1000px;
  width: 100%;
  margin-inline: auto;
}

.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.setting-row:last-child {
  border-bottom: none;
}
.setting-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.setting-key {
  font-weight: 700;
  color: #f0d785;
}
.setting-desc {
  font-size: 0.8rem;
  opacity: 0.7;
}
.setting-control {
  display: flex;
  align-items: center;
  gap: 10px;
}
.setting-input {
  width: 180px;
}
.detail-cell {
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
